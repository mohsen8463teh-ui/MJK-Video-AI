from typing import Any, Dict, List, Optional

from llm_provider import OpenRouterProvider, LLMProviderError


class LLMRouter:
    """
    MJK LLM Router

    یک قرارداد استاندارد برای مدل‌های زبانی.
    هیچ وابستگی اجباری به یک Provider ندارد.

    Providerها بعداً می‌توانند:
    - Gemini
    - OpenAI-compatible APIs
    - مدل‌های دیگر
    را پیاده‌سازی کنند.
    """

    def __init__(self):
        self.providers = {
            "primary": {
                "id": "primary",
                "configured": False,
                "provider": None,
                "model": None,
                "status": "not_configured",
            }
        }

        self.openrouter = OpenRouterProvider()

        self.register_provider(
            "openrouter",
            "OpenRouter",
            self.openrouter.model,
            self.openrouter.configured,
        )

    def register_provider(
        self,
        provider_id: str,
        provider_name: str,
        model: str,
        configured: bool = False,
    ):
        self.providers[provider_id] = {
            "id": provider_id,
            "configured": configured,
            "provider": provider_name,
            "model": model,
            "status": (
                "ready"
                if configured
                else "not_configured"
            ),
        }

    def list_providers(self) -> List[Dict[str, Any]]:
        return list(self.providers.values())

    def select_provider(
        self,
        preferred: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        if preferred:
            provider = self.providers.get(preferred)

            if provider and provider["configured"]:
                return provider

        for provider in self.providers.values():
            if provider["configured"]:
                return provider

        return None

    def build_director_request(
        self,
        prompt: str,
        duration_seconds: int,
        style: str,
        language: str,
        aspect_ratio: str,
        output_type: str,
    ) -> Dict[str, Any]:

        system_instruction = """
You are the MJK AI Director.

Your job is to transform a user's video idea into a
professional production plan.

You must reason about:

1. Audience
2. Objective
3. Hook
4. Story structure
5. Scene continuity
6. Characters
7. Locations
8. Camera language
9. Lighting
10. Visual style
11. Voice-over
12. Music
13. Sound effects
14. Captions
15. Call to action when appropriate

Never invent facts about a real product unless the user
provided them.

Never guarantee views, sales, virality, or profit.

Return structured JSON suitable for downstream video
generation.
"""

        user_request = {
            "prompt": prompt,
            "duration_seconds": duration_seconds,
            "style": style,
            "language": language,
            "aspect_ratio": aspect_ratio,
            "output_type": output_type,
        }

        return {
            "system_instruction": system_instruction.strip(),
            "user_request": user_request,
            "response_schema": {
                "type": "object",
                "required": [
                    "concept",
                    "hook",
                    "audience",
                    "story",
                    "characters",
                    "locations",
                    "scenes",
                    "voiceover",
                    "music",
                    "sound_effects",
                    "captions",
                    "cta",
                ],
            },
        }

    def normalize_response(
        self,
        response: Dict[str, Any],
    ) -> Dict[str, Any]:

        required = [
            "concept",
            "hook",
            "audience",
            "story",
            "characters",
            "locations",
            "scenes",
            "voiceover",
            "music",
            "sound_effects",
            "captions",
            "cta",
        ]

        normalized = {}

        for key in required:
            normalized[key] = response.get(
                key,
                [] if key in [
                    "characters",
                    "locations",
                    "scenes",
                ] else "",
            )

        return normalized

    def generate_director_plan(self, **kwargs) -> Dict[str, Any]:
        request = self.build_director_request(**kwargs)

        if not self.openrouter.configured:
            raise LLMProviderError(
                "No LLM provider is configured"
            )

        response = self.openrouter.generate_json(
            system_instruction=request["system_instruction"],
            user_request=request["user_request"],
            response_schema=request["response_schema"],
        )

        return self.normalize_response(response)

    def status(self) -> Dict[str, Any]:
        selected = self.select_provider()

        return {
            "router": "MJK LLM Router",
            "version": "0.1.0",
            "provider_available": selected is not None,
            "selected_provider": selected,
            "providers": self.list_providers(),
        }
