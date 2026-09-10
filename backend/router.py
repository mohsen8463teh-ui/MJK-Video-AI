import math


class ModelRouter:
    """
    MJK Video AI Model Router

    این فایل فعلاً هیچ API Key لازم ندارد.
    وظیفه آن:
    - تحلیل نیاز پروژه
    - انتخاب موتور مناسب
    - تقسیم ویدئوی طولانی به Scene/Clip
    - آماده‌سازی ساختار برای اتصال موتورهای واقعی
    """

    MODELS = {
        "veo_3_1": {
            "provider": "Google",
            "model": "veo-3.1-generate-preview",
            "quality": 10,
            "audio": True,
            "image_to_video": True,
            "aspect_ratios": ["16:9", "9:16"],
            "max_clip_seconds": 8,
        },
        "veo_3_1_fast": {
            "provider": "Google",
            "model": "veo-3.1-fast-generate-preview",
            "quality": 9,
            "audio": True,
            "image_to_video": True,
            "aspect_ratios": ["16:9", "9:16"],
            "max_clip_seconds": 8,
        },
        "runway_gen4_5": {
            "provider": "Runway",
            "model": "gen4.5",
            "quality": 10,
            "audio": False,
            "image_to_video": True,
            "aspect_ratios": ["16:9", "9:16"],
            "max_clip_seconds": 10,
        },
    }

    def __init__(self):
        self.providers = {
            "Google": {
                "configured": False,
                "reason": "API key not configured",
            },
            "Runway": {
                "configured": False,
                "reason": "API key not configured",
            },
        }

    def available_models(self):
        result = []

        for key, model in self.MODELS.items():
            provider = model["provider"]
            configured = self.providers[provider]["configured"]

            result.append({
                "id": key,
                "provider": provider,
                "model": model["model"],
                "configured": configured,
                "quality": model["quality"],
                "audio": model["audio"],
                "image_to_video": model["image_to_video"],
                "aspect_ratios": model["aspect_ratios"],
                "max_clip_seconds": model["max_clip_seconds"],
            })

        return result

    def split_into_clips(self, duration_seconds, max_clip_seconds):
        """
        مدت کل را به کلیپ‌های قابل تولید تقسیم می‌کند.
        هیچ سقف داخلی برای مدت کل پروژه وجود ندارد.
        """

        duration_seconds = max(1, int(duration_seconds))

        count = math.ceil(duration_seconds / max_clip_seconds)

        clips = []

        remaining = duration_seconds

        for index in range(count):
            current = min(max_clip_seconds, remaining)

            clips.append({
                "scene": index + 1,
                "duration_seconds": current,
            })

            remaining -= current

        return clips

    def select_model(
        self,
        aspect_ratio="16:9",
        audio=True,
        image_to_video=False,
        quality="maximum",
        preferred_provider=None,
    ):
        candidates = []

        for key, model in self.MODELS.items():

            if aspect_ratio not in model["aspect_ratios"]:
                continue

            if audio and not model["audio"]:
                continue

            if image_to_video and not model["image_to_video"]:
                continue

            if preferred_provider:
                if model["provider"].lower() != preferred_provider.lower():
                    continue

            candidates.append((key, model))

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[1]["quality"],
            reverse=True
        )

        return candidates[0]

    def create_plan(self, data):
        prompt = str(data.get("prompt", "")).strip()

        if len(prompt) < 3:
            raise ValueError("prompt is required")

        aspect_ratio = str(
            data.get("aspect_ratio", "16:9")
        ).strip()

        duration_seconds = int(
            data.get("duration_seconds", 30)
        )

        audio = bool(data.get("audio", True))

        image_to_video = bool(
            data.get("image_to_video", False)
        )

        preferred_provider = data.get(
            "preferred_provider"
        )

        selected = self.select_model(
            aspect_ratio=aspect_ratio,
            audio=audio,
            image_to_video=image_to_video,
            preferred_provider=preferred_provider,
        )

        if selected is None:
            # اگر موتور صوت‌دار پیدا نشد، موتور تصویری انتخاب می‌شود.
            selected = self.select_model(
                aspect_ratio=aspect_ratio,
                audio=False,
                image_to_video=image_to_video,
                preferred_provider=preferred_provider,
            )

        if selected is None:
            raise ValueError(
                "No compatible video model found"
            )

        model_id, model = selected

        clips = self.split_into_clips(
            duration_seconds,
            model["max_clip_seconds"]
        )

        return {
            "project": {
                "prompt": prompt,
                "duration_seconds": duration_seconds,
                "aspect_ratio": aspect_ratio,
                "audio_requested": audio,
                "image_to_video": image_to_video,
            },

            "router": {
                "selected_model_id": model_id,
                "provider": model["provider"],
                "model": model["model"],
                "quality": model["quality"],
                "fallback_enabled": True,
            },

            "production": {
                "total_duration_seconds": duration_seconds,
                "total_clips": len(clips),
                "unlimited_internal_duration": True,
                "clips": clips,
            },

            "status": {
                "generation_ready": False,
                "reason": "Provider API key not configured",
            },
        }
