import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from llm_provider import LLMProviderError
from video_provider import VideoProviderError


class JobManager:
    """Durable project state + in-process execution.

    The database is the source of truth for job state. The executor can later
    be replaced by Redis/Celery or another production queue without changing
    the HTTP API.
    """

    def __init__(self, storage, llm_router, video_router) -> None:
        self.storage = storage
        self.llm_router = llm_router
        self.video_router = video_router
        self.executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="mjk-job",
        )

    def submit_director_job(self, project: Dict[str, Any]) -> Dict[str, Any]:
        self.executor.submit(self._run_director, project["id"])
        return self.storage.get_project(project["id"])

    def submit_video_job(
        self,
        project_id: str,
        preferred_provider: str | None = None,
    ) -> Dict[str, Any]:
        self.executor.submit(
            self._run_video,
            project_id,
            preferred_provider,
        )
        return self.storage.get_project(project_id)

    def _run_director(self, project_id: str) -> None:
        try:
            project = self.storage.get_project(project_id)
            self.storage.update_project(
                project_id,
                status="planning",
            )

            plan = self.llm_router.generate_director_plan(
                prompt=project["prompt"],
                duration_seconds=project["duration_seconds"],
                style=project["style"],
                language=project["language"],
                aspect_ratio=project["aspect_ratio"],
                output_type=project["output_type"],
            )

            self.storage.update_project(
                project_id,
                status="awaiting_video_provider",
                plan=plan,
            )

        except (LLMProviderError, ValueError, KeyError) as exc:
            self.storage.update_project(
                project_id,
                status="failed",
                error=str(exc),
            )
        except Exception as exc:
            self.storage.update_project(
                project_id,
                status="failed",
                error=f"internal_error: {exc}",
            )

    @staticmethod
    def _scene_prompt(scene: Any) -> str:
        if isinstance(scene, str):
            return scene.strip()

        if not isinstance(scene, dict):
            return str(scene)

        parts = []
        for key in (
            "prompt",
            "description",
            "visual",
            "action",
            "camera",
            "lighting",
            "environment",
            "continuity",
        ):
            value = scene.get(key)
            if value:
                parts.append(f"{key}: {value}")

        return "\n".join(parts).strip()

    @staticmethod
    def _scene_duration(
        scene: Any,
        total_duration: int,
        scene_count: int,
    ) -> int:
        if isinstance(scene, dict):
            value = scene.get(
                "duration_seconds",
                scene.get("duration"),
            )
            try:
                if value is not None:
                    return max(2, min(int(float(value)), 10))
            except (TypeError, ValueError):
                pass

        fallback = max(2, round(total_duration / max(scene_count, 1)))
        return min(fallback, 10)

    def _run_video(
        self,
        project_id: str,
        preferred_provider: str | None,
    ) -> None:
        try:
            project = self.storage.get_project(project_id)
            plan = project.get("plan") or {}
            scenes = plan.get("scenes") or []

            if not scenes:
                raise VideoProviderError(
                    "Director plan contains no scenes"
                )

            provider = self.video_router.select(preferred_provider)

            self.storage.update_project(
                project_id,
                status="video_generating",
            )

            manifest = {
                "provider": provider.provider_id,
                "model": getattr(provider, "model", None),
                "scenes": [],
            }

            for index, scene in enumerate(scenes, start=1):
                prompt = self._scene_prompt(scene)
                if not prompt:
                    raise VideoProviderError(
                        f"Scene {index} has no usable prompt"
                    )

                duration = self._scene_duration(
                    scene,
                    project["duration_seconds"],
                    len(scenes),
                )

                result = provider.generate_text_to_video(
                    prompt=prompt,
                    duration_seconds=duration,
                    aspect_ratio=project["aspect_ratio"],
                )

                relative_path = f"scenes/scene_{index:03d}.mp4"
                destination = self.storage.project_file_path(
                    project_id,
                    relative_path,
                )
                size = provider.download_output(
                    result["output_url"],
                    destination,
                )

                file_info = self.storage._register_file(
                    project_id,
                    relative_path,
                    "video_scene",
                    size,
                )

                manifest["scenes"].append({
                    "index": index,
                    "duration_seconds": duration,
                    "prompt": prompt,
                    "provider_result": {
                        key: value
                        for key, value in result.items()
                        if key != "output_url"
                    },
                    "file": file_info,
                })

            self.storage.write_json(
                project_id,
                "scenes/manifest.json",
                manifest,
                "video_scene_manifest",
            )

            self.storage.update_project(
                project_id,
                status="awaiting_assembly",
            )

        except (VideoProviderError, KeyError, ValueError) as exc:
            self.storage.update_project(
                project_id,
                status="failed",
                error=str(exc),
            )
        except Exception as exc:
            self.storage.update_project(
                project_id,
                status="failed",
                error=f"internal_error: {exc}",
            )
