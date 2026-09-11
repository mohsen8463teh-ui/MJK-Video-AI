"""Provider-agnostic TTS adapters for MJK Video AI.

The backend never stores provider secrets in the Android app.
A local Kokoro-compatible HTTP service can be used for zero per-minute API cost.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


class AudioProviderError(RuntimeError):
    pass


class AudioProvider:
    provider_id = "base"

    def configured(self) -> bool:
        raise NotImplementedError

    def generate(
        self,
        *,
        text: str,
        output_path: Path,
        language: str,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

class PiperProvider(AudioProvider):
    provider_id = "piper_local"

    def __init__(
        self, *, python_bin: Optional[str] = None,
        model_fa: Optional[str] = None, model_en: Optional[str] = None,
        data_dir: Optional[str] = None,
    ) -> None:
        self.python_bin = python_bin or os.environ.get("PIPER_PYTHON", "python3")
        self.model_fa = model_fa or os.environ.get("PIPER_MODEL_FA", "")
        self.model_en = model_en or os.environ.get("PIPER_MODEL_EN", "")
        self.data_dir = data_dir or os.environ.get("PIPER_DATA_DIR", "")

    @staticmethod
    def _is_persian(language: str) -> bool:
        v = (language or "").strip().lower()
        return "فارسی" in v or "persian" in v or "farsi" in v or v.startswith("fa")

    def _model_for(self, language: str) -> str:
        return self.model_fa if self._is_persian(language) else self.model_en

    def configured(self) -> bool:
        return bool(self.model_fa or self.model_en)

    def supports_language(self, language: str) -> bool:
        return bool(self._model_for(language))

    def _command(self, *, text: str, output_path: Path, language: str):
        model = self._model_for(language)
        if not model:
            raise AudioProviderError("piper_model_not_configured_for_language")
        command = [
            self.python_bin, "-m", "piper", "-m", model,
            "-f", str(output_path),
        ]
        if self.data_dir:
            command += ["--data-dir", self.data_dir]
        command += ["--", text]
        return command

    def generate(self, *, text: str, output_path: Path,
                 language: str, voice: Optional[str] = None) -> Dict[str, Any]:
        del voice
        if not text.strip():
            raise AudioProviderError("empty_tts_text")
        if not self._model_for(language):
            raise AudioProviderError("piper_model_not_configured_for_language")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                self._command(text=text, output_path=output_path, language=language),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=int(os.environ.get("PIPER_TIMEOUT_SECONDS", "600")),
                check=False,
            )
        except FileNotFoundError as exc:
            raise AudioProviderError("piper_python_not_found") from exc
        except subprocess.TimeoutExpired as exc:
            raise AudioProviderError("piper_timeout") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise AudioProviderError(f"piper_failed: {detail[-1000:] or 'unknown_error'}")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise AudioProviderError("piper_output_missing")
        return {
            "provider": self.provider_id,
            "size_bytes": output_path.stat().st_size,
            "output_path": str(output_path),
        }


class KokoroHTTPProvider(AudioProvider):
    """Adapter for a locally/self-hosted Kokoro TTS HTTP service.

    Expected endpoint contract:
      POST {base_url}/tts/generate
      JSON: text, voice, language (when available)
      Response: raw audio bytes (WAV/MP3/etc.)
    """

    provider_id = "kokoro_http"

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url or os.environ.get("MJK_KOKORO_TTS_URL", "")
        ).rstrip("/")

    def configured(self) -> bool:
        return bool(self.base_url)

    def generate(
        self,
        *,
        text: str,
        output_path: Path,
        language: str,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.configured():
            raise AudioProviderError("kokoro_not_configured")
        if not text.strip():
            raise AudioProviderError("empty_tts_text")

        payload: Dict[str, Any] = {
            "text": text,
            "language": language,
        }
        if voice:
            payload["voice"] = voice

        import json

        request = urllib.request.Request(
            f"{self.base_url}/tts/generate",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=int(os.environ.get("MJK_TTS_TIMEOUT_SECONDS", "600")),
            ) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.URLError as exc:
            raise AudioProviderError(f"tts_request_failed: {exc}") from exc

        if not data:
            raise AudioProviderError("tts_empty_response")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)

        return {
            "provider": self.provider_id,
            "content_type": content_type,
            "size_bytes": len(data),
            "output_path": str(output_path),
        }


class AudioRouter:
    def __init__(self) -> None:
        self.providers = {
            "piper_local": PiperProvider(),
            "kokoro_http": KokoroHTTPProvider(),
        }

    def select(self, preferred: Optional[str] = None, *, language: Optional[str] = None):
        if preferred:
            provider = self.providers.get(preferred)
            if provider and provider.configured():
                if language is None or not hasattr(provider, "supports_language") or provider.supports_language(language):
                    return provider
        for provider in self.providers.values():
            if not provider.configured():
                continue
            if language is not None and hasattr(provider, "supports_language") and not provider.supports_language(language):
                continue
            return provider
        return None

    def status(self) -> Dict[str, Any]:
        return {
            "router": "MJK Audio Router",
            "provider_available": self.select() is not None,
            "providers": [
                {
                    "id": provider.provider_id,
                    "configured": provider.configured(),
                    "status": "ready" if provider.configured() else "not_configured",
                }
                for provider in self.providers.values()
            ],
        }
