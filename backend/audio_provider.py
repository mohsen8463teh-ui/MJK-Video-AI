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
            "kokoro_http": KokoroHTTPProvider(),
        }

    def select(self, preferred: Optional[str] = None) -> Optional[AudioProvider]:
        if preferred:
            provider = self.providers.get(preferred)
            if provider and provider.configured():
                return provider

        for provider in self.providers.values():
            if provider.configured():
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
