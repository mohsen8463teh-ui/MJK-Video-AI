import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict


class VideoProviderError(RuntimeError):
    pass


class VideoProvider(ABC):
    provider_id = "unknown"

    @property
    @abstractmethod
    def configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_text_to_video(
        self,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class KIEProvider(VideoProvider):
    provider_id = "kie"

    def __init__(self):
        self.api_key = os.environ.get("KIE_API_KEY4", "").strip()
        self.base_url = os.environ.get("KIE_BASE_URL", "https://api.kie.ai").rstrip("/")
        self.model = os.environ.get("KIE_VIDEO_MODEL", "bytedance/v1-pro-text-to-video")
        self.resolution = os.environ.get("KIE_VIDEO_RESOLUTION", "720p")

    @property
    def configured(self):
        return bool(self.api_key)

    def status(self):
        return {"id": self.provider_id, "provider": "KIE.ai", "configured": self.configured, "model": self.model, "base_url": self.base_url, "resolution": self.resolution}

    @staticmethod
    def _ratio(aspect_ratio):
        return "9:16" if str(aspect_ratio).strip() in ("9:16", "720:1280") else "16:9"

    def _request(self, method, path, payload=None, query=None):
        if not self.configured:
            raise VideoProviderError("KIE API key is not configured")
        url=f"{self.base_url}{path}" + (f"?{query}" if query else "")
        body=json.dumps(payload).encode("utf-8") if payload is not None else None
        req=urllib.request.Request(url, data=body, headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json","User-Agent":"MJK-Video-AI/0.1"}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw=r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            details=e.read().decode("utf-8",errors="replace")
            raise VideoProviderError(f"KIE HTTP {e.code}: {details[:1000]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise VideoProviderError(f"KIE connection error: {e}") from e
        try: result=json.loads(raw)
        except json.JSONDecodeError as e: raise VideoProviderError("KIE returned invalid JSON") from e
        if result.get("code") not in (None,200):
            raise VideoProviderError(f"KIE API error {result.get('code')}: {result.get('msg','unknown error')}")
        return result

    def generate_text_to_video(self, prompt, duration_seconds, aspect_ratio):
        payload={"model":self.model,"input":{"prompt":prompt,"aspect_ratio":self._ratio(aspect_ratio),"resolution":self.resolution,"duration":"5","camera_fixed":False,"seed":-1,"enable_safety_checker":True,"nsfw_checker":False}}
        created=self._request("POST","/api/v1/jobs/createTask",payload)
        task_id=(created.get("data") or {}).get("taskId")
        if not task_id: raise VideoProviderError("KIE did not return a task id")
        deadline=time.time()+20*60
        while time.time()<deadline:
            task=self._request("GET","/api/v1/jobs/recordInfo",query=f"taskId={task_id}")
            data=task.get("data") or {}; state=str(data.get("state","")).lower()
            if state=="success":
                try: result=json.loads(data.get("resultJson") or "{}")
                except (TypeError,json.JSONDecodeError) as e: raise VideoProviderError("KIE returned invalid resultJson") from e
                urls=result.get("resultUrls") or result.get("urls") or []
                if not urls: raise VideoProviderError("KIE task succeeded without a result URL")
                return {"provider":"kie","model":self.model,"task_id":task_id,"status":state,"output_url":urls[0],"requested_duration_seconds":5,"ratio":self._ratio(aspect_ratio),"resolution":self.resolution}
            if state=="fail": raise VideoProviderError(f"KIE task failed: {data.get('failMsg') or data.get('failCode') or data}")
            time.sleep(3)
        raise VideoProviderError(f"KIE task timed out: {task_id}")

    def download_output(self, output_url, destination):
        req=urllib.request.Request(output_url,headers={"User-Agent":"MJK-Video-AI/0.1"},method="GET")
        try:
            with urllib.request.urlopen(req,timeout=120) as r: data=r.read()
        except (urllib.error.URLError,TimeoutError) as e: raise VideoProviderError(f"KIE output download failed: {e}") from e
        destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(data); return len(data)


class RunwayProvider(VideoProvider):
    provider_id = "runway"

    def __init__(self) -> None:
        self.api_key = os.environ.get("RUNWAYML_API_SECRET", "").strip()
        self.base_url = os.environ.get(
            "RUNWAY_BASE_URL",
            "https://api.dev.runwayml.com",
        ).rstrip("/")
        self.model = os.environ.get(
            "RUNWAY_VIDEO_MODEL",
            "gen4.5",
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> Dict[str, Any]:
        return {
            "id": self.provider_id,
            "provider": "Runway",
            "configured": self.configured,
            "model": self.model,
            "base_url": self.base_url,
        }

    @staticmethod
    def _ratio(aspect_ratio: str) -> str:
        value = str(aspect_ratio).strip()
        if value in ("9:16", "720:1280"):
            return "720:1280"
        return "1280:720"

    def _request(
        self,
        method: str,
        path: str,
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not self.configured:
            raise VideoProviderError("Runway API key is not configured")

        body = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise VideoProviderError(
                f"Runway HTTP {exc.code}: {details[:1000]}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise VideoProviderError(
                f"Runway connection error: {exc}"
            ) from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise VideoProviderError(
                "Runway returned invalid JSON"
            ) from exc

    def generate_text_to_video(
        self,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
    ) -> Dict[str, Any]:
        duration = max(2, min(int(duration_seconds), 10))

        created = self._request(
            "POST",
            "/v1/image_to_video",
            {
                "model": self.model,
                "promptText": prompt,
                "ratio": self._ratio(aspect_ratio),
                "duration": duration,
                "outputFormat": "mp4",
            },
        )

        task_id = created.get("id")
        if not task_id:
            raise VideoProviderError(
                "Runway did not return a task id"
            )

        deadline = time.time() + 20 * 60

        while time.time() < deadline:
            task = self._request(
                "GET",
                f"/v1/tasks/{task_id}",
            )
            status = str(task.get("status", "")).upper()

            if status == "SUCCEEDED":
                output = task.get("output") or []
                if not output:
                    raise VideoProviderError(
                        "Runway task succeeded without output"
                    )
                return {
                    "provider": self.provider_id,
                    "model": self.model,
                    "task_id": task_id,
                    "status": status,
                    "output_url": output[0],
                    "requested_duration_seconds": duration,
                    "ratio": self._ratio(aspect_ratio),
                }

            if status in {"FAILED", "CANCELLED"}:
                raise VideoProviderError(
                    f"Runway task {status.lower()}: "
                    f"{task.get('failure') or task.get('error') or task}"
                )

            time.sleep(3)

        raise VideoProviderError(
            f"Runway task timed out: {task_id}"
        )

    def download_output(self, output_url: str, destination) -> int:
        request = urllib.request.Request(
            output_url,
            headers={"User-Agent": "MJK-Video-AI/0.1"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise VideoProviderError(
                f"Runway output download failed: {exc}"
            ) from exc

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return len(data)


class VideoRouter:
    def __init__(self):
        self.kie = KIEProvider()
        self.runway = RunwayProvider()

    def providers(self):
        return [self.kie, self.runway]

    def status(self):
        selected=next((p for p in self.providers() if p.configured),None)
        return {"router":"MJK Video Router","provider_available":selected is not None,"selected_provider":selected.provider_id if selected else None,"providers":[p.status() for p in self.providers()]}

    def select(self, preferred=None):
        if preferred == "kie" and self.kie.configured: return self.kie
        if preferred == "runway" and self.runway.configured: return self.runway
        if self.kie.configured: return self.kie
        if self.runway.configured: return self.runway
        raise VideoProviderError("No video provider is configured")
