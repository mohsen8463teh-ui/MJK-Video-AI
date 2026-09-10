import json
import os
import urllib.error
import urllib.request


class LLMProviderError(Exception):
    pass


class OpenRouterProvider:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        self.configured = bool(self.api_key)

    def generate_json(
        self,
        system_instruction,
        user_request,
        response_schema=None,
    ):
        if not self.configured:
            raise LLMProviderError("OPENROUTER_API_KEY is not configured")

        schema_text = json.dumps(
            response_schema or {},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        prompt = (
            "Return ONLY valid JSON. Do not use Markdown fences. "
            "Do not add explanations before or after the JSON.\n\n"
            "Required JSON schema description:\n"
            f"{schema_text}\n\n"
            "User video request:\n"
            f"{user_request}"
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
            "response_format": {
                "type": "json_object"
            },
        }

        data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode("utf-8")

        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")
            except Exception:
                detail = ""
            raise LLMProviderError(
                f"provider_http_{exc.code}: {detail}"
            ) from exc

        except urllib.error.URLError as exc:
            raise LLMProviderError(
                f"provider_network_error: {exc}"
            ) from exc

        except TimeoutError as exc:
            raise LLMProviderError(
                "provider_timeout"
            ) from exc

        try:
            response_data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(
                "provider returned invalid API JSON"
            ) from exc

        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                "provider response missing message content"
            ) from exc

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                elif isinstance(item, str):
                    parts.append(item)
            content = "".join(parts)

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError(
                "provider returned empty content"
            )

        content = content.strip()

        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(
                "provider returned non-JSON content"
            ) from exc

        if not isinstance(result, dict):
            raise LLMProviderError(
                "provider JSON root must be an object"
            )

        return result
