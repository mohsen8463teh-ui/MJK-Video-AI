import math


class AIDirector:

    def __init__(self):
        self.version = "0.1.0"

    def clean(self, value, default=""):
        if value is None:
            return default
        return str(value).strip()

    def duration(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 30
        return max(1, value)

    def scene_count(self, duration):
        return max(1, math.ceil(duration / 8))

    def detect_goal(self, prompt, output_type):
        text = f"{prompt} {output_type}".lower()

        if any(x in text for x in [
            "تبلیغ", "فروش", "مغازه", "محصول",
            "advert", "advertising", "product"
        ]):
            return "advertising"

        if any(x in text for x in [
            "youtube", "یوتیوب", "short", "شورت",
            "reels", "ریل", "اینستاگرام"
        ]):
            return "social_video"

        if any(x in text for x in [
            "داستان", "story", "فیلم", "cinematic",
            "سینمایی"
        ]):
            return "storytelling"

        return "general_video"

    def hook(self, goal):
        if goal == "advertising":
            return (
                "شروع بسیار قدرتمند در چند ثانیه اول با "
                "تصویر جذاب محصول یا نتیجه نهایی."
            )

        if goal == "social_video":
            return (
                "شروع سریع با سؤال، اتفاق غیرمنتظره یا "
                "یک وعده جذاب برای حفظ توجه مخاطب."
            )

        return (
            "شروع با قوی‌ترین لحظه یا سؤال داستانی "
            "برای ایجاد کنجکاوی فوری."
        )

    def story(self, goal, duration):
        if goal == "advertising":
            return (
                f"سناریوی تبلیغاتی {duration} ثانیه‌ای شامل "
                "Hook، معرفی نیاز، نمایش راه‌حل، ایجاد اعتماد "
                "و پایان با CTA."
            )

        if goal == "social_video":
            return (
                f"سناریوی {duration} ثانیه‌ای با Hook، "
                "توسعه سریع ایده، نقطه اوج و پایان به‌یادماندنی."
            )

        return (
            f"داستان {duration} ثانیه‌ای با شروع، توسعه، "
            "اوج و پایان مشخص."
        )

    def role(self, index, total, goal):
        if index == 1:
            return "HOOK"

        if index == total:
            return "CTA" if goal == "advertising" else "ENDING"

        progress = index / total

        if progress < 0.30:
            return "SETUP"

        if progress < 0.65:
            return "DEVELOPMENT"

        if progress < 0.90:
            return "CLIMAX"

        return "RESOLUTION"

    def camera(self, role):
        cameras = {
            "HOOK": "Dynamic close-up, dramatic opening and immediate visual impact.",
            "SETUP": "Cinematic medium shot with controlled camera movement.",
            "DEVELOPMENT": "Cinematic tracking or dolly movement with varied framing.",
            "CLIMAX": "Dynamic cinematic movement with strong perspective and energy.",
            "RESOLUTION": "Stable cinematic shot gradually revealing the final message.",
            "CTA": "Premium product hero shot with clean composition and CTA space.",
            "ENDING": "Memorable final cinematic shot with controlled movement."
        }

        return cameras.get(
            role,
            cameras["DEVELOPMENT"]
        )

    def visual_prompt(self, prompt, role, style):
        return (
            f"Create a high-quality video scene based on this idea: "
            f"{prompt}. "
            f"Scene role: {role}. "
            f"Visual style: {style}. "
            "Professional cinematic composition, realistic lighting, "
            "natural motion, coherent environment, consistent characters "
            "and objects, high visual quality, no unwanted watermark."
        )

    def voice(self, role, language):
        if language.lower() in [
            "بدون گوینده",
            "none",
            "no voice",
            "silent"
        ]:
            return None

        if role == "HOOK":
            return "Energetic opening narration matching the hook."

        if role == "CTA":
            return "Clear persuasive call-to-action narration."

        return "Natural narration synchronized with the scene."

    def music(self, goal):
        if goal == "advertising":
            return (
                "Premium modern commercial music, energetic "
                "but not overpowering narration."
            )

        if goal == "social_video":
            return "Modern energetic music with rhythmic transitions."

        return "Cinematic background score matching the story."

    def create(self, data):

        prompt = self.clean(data.get("prompt"))

        if len(prompt) < 3:
            raise ValueError("prompt is required")

        output_type = self.clean(
            data.get("output_type"),
            "general"
        )

        style = self.clean(
            data.get("style"),
            "cinematic"
        )

        language = self.clean(
            data.get("language"),
            "فارسی"
        )

        aspect_ratio = self.clean(
            data.get("aspect_ratio"),
            "16:9"
        )

        duration = self.duration(
            data.get("duration_seconds", 30)
        )

        goal = self.detect_goal(
            prompt,
            output_type
        )

        total_scenes = self.scene_count(duration)

        scenes = []

        remaining = duration

        for i in range(total_scenes):

            scene_number = i + 1

            scene_duration = min(
                8,
                remaining
            )

            role = self.role(
                scene_number,
                total_scenes,
                goal
            )

            scenes.append({
                "scene": scene_number,
                "role": role,
                "duration_seconds": scene_duration,
                "visual_prompt": self.visual_prompt(
                    prompt,
                    role,
                    style
                ),
                "camera": self.camera(role),
                "voice": self.voice(
                    role,
                    language
                ),
                "music": self.music(goal),
                "transition": (
                    "smooth cinematic transition"
                    if scene_number < total_scenes
                    else "clean final transition"
                )
            })

            remaining -= scene_duration

        return {
            "director": {
                "name": "MJK AI Director",
                "version": self.version,
                "goal": goal,
                "style": style,
                "language": language,
                "aspect_ratio": aspect_ratio,
                "duration_seconds": duration
            },

            "creative": {
                "original_prompt": prompt,
                "hook": self.hook(goal),
                "story": self.story(
                    goal,
                    duration
                ),
                "output_type": output_type
            },

            "production": {
                "total_duration_seconds": duration,
                "total_scenes": total_scenes,
                "unlimited_internal_duration": True,
                "scenes": scenes
            },

            "generation": {
                "status": "planned",
                "requires_external_model": True,
                "api_key_configured": False
            }
        }
