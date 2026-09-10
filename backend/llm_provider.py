import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict


class LLMProviderError(RuntimeError):
    pass


class OpenRouterProvider:
    """Dependency-free OpenRouter chat-completions client."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        ).rstrip("/")
        self.model = os.getenv(
            "OPENROUTER_MODEL",
            "openrouter/free",
        ).strip()

    @property
    def configured(self):
        return bool(self.api_key and self.model)

    def describe(self):
        return {
            "id": "openrouter",
            "configured": self.configured,
            "provider": "OpenRouter",
            "model": self.model if self.configured else None,
            "status": "ready" if self.configured else "not_configured",
        }

    def generate_json(
        self,
        system_instruction: str,
        user_request: Dict[str, Any],
        response_schema: Dict[str, Any],
    ):
        if not self.configured:
            raise LLMProviderError("LLM provider is not configured")

        schema_text = json.dumps(
            response_schema,
            ensure_ascii=False
        )
        user_text = json.dumps(
            user_request,
            ensure_ascii=False
        )

        prompt = (
            "Return ONLY valid JSON. "
            "Do not use Markdown fences.\n\n"
            "Required JSON schema description:\n"
            f"{schema_text}\n\n"
            "User video request:\n"
            f"{user_text}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.7,
        }

        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(
                req,
                timeout=90
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(
                "utf-8",
                errors="replace"
            )[:1000]
            raise LLMProviderError(
                f"provider_http_{exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LLMProviderError(
                f"provider_connection_error: {exc}"
            ) from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            raise LLMProviderError(
                "invalid provider response"
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError(
                "provider returned empty content"
            )

        text = content.strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(
                "provider returned non-JSON content"
            ) from exc

        if not isinstance(result, dict):
            raise LLMProviderError(
                "provider JSON root must be an object"
            )

        return result
