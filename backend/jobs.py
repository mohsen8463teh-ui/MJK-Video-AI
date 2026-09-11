from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from llm_provider import LLMProviderError


class JobManager:
    """Small persistent job runner for the first backend stage.

    The project record in SQLite is the durable job state. The in-process
    executor only performs work; a production deployment can later replace
    it with Redis/Celery/another queue without changing the HTTP contract.
    """

    def __init__(self, storage, llm_router) -> None:
        self.storage = storage
        self.llm_router = llm_router
        self.executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="mjk-job",
        )

    def submit_director_job(self, project: Dict[str, Any]) -> Dict[str, Any]:
        project_id = project["id"]
        self.executor.submit(self._run_director, project_id)
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
