"""Provider-agnostic voice and audio planning for MJK Video AI."""
from __future__ import annotations

from typing import Any, Dict, List


class AudioPlanError(ValueError):
    pass


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _extract_narration(voiceover: Any, scene_count: int) -> List[str]:
    if isinstance(voiceover, str):
        text = voiceover.strip()
        return [text] if text else [""] * scene_count

    if isinstance(voiceover, list):
        result = []
        for item in voiceover:
            if isinstance(item, dict):
                value = (
                    item.get("text")
                    or item.get("narration")
                    or item.get("script")
                    or item.get("content")
                )
            else:
                value = item
            result.append(_text(value))
        return result

    if isinstance(voiceover, dict):
        for key in ("segments", "scenes", "items", "narration"):
            if isinstance(voiceover.get(key), list):
                return _extract_narration(voiceover[key], scene_count)
        for key in ("text", "narration", "script", "content"):
            if voiceover.get(key):
                return [_text(voiceover[key])] + [""] * max(scene_count - 1, 0)

    return [""] * scene_count


def build_voice_plan(
    *,
    timeline: Dict[str, Any],
    director_plan: Dict[str, Any],
    language: str,
) -> Dict[str, Any]:
    tracks = timeline.get("tracks") or {}
    video = tracks.get("video") or []
    if not video:
        raise AudioPlanError("voice_plan_requires_video_timeline")

    scene_indices = sorted({
        int(item["scene_index"])
        for item in video
        if item.get("scene_index") is not None
    })
    if not scene_indices:
        raise AudioPlanError("voice_plan_requires_scene_indices")

    voiceover = _extract_narration(
        director_plan.get("voiceover"),
        len(scene_indices),
    )

    by_scene: Dict[int, List[Dict[str, Any]]] = {}
    for item in video:
        by_scene.setdefault(int(item["scene_index"]), []).append(item)

    segments = []
    for position, scene_index in enumerate(scene_indices):
        text = voiceover[position] if position < len(voiceover) else ""
        scene_video = by_scene[scene_index]
        start = float(scene_video[0]["start_seconds"])
        end = float(scene_video[-1]["end_seconds"])
        duration = end - start

        segments.append({
            "id": f"voice_{position + 1:04d}",
            "scene_index": scene_index,
            "start_seconds": start,
            "duration_seconds": duration,
            "end_seconds": end,
            "language": language,
            "text": text,
            "status": "pending" if text else "not_required",
            "audio_path": None,
            "provider": None,
        })

    return {
        "version": 1,
        "language": language,
        "duration_seconds": timeline["duration_seconds"],
        "segments": segments,
        "provider": None,
        "status": "planned",
    }
