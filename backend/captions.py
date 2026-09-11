"""Deterministic caption cue planning from the canonical voice timeline."""
from __future__ import annotations

import re
from typing import Any, Dict, List


class CaptionPlanError(ValueError):
    pass


_WORD_RE = re.compile(r"\S+")


def _split_text(text: str, max_words: int = 10) -> List[str]:
    words = _WORD_RE.findall(text.strip())
    return [
        " ".join(words[i:i + max_words])
        for i in range(0, len(words), max_words)
    ]


def build_caption_plan(
    *,
    voice_plan: Dict[str, Any],
    max_words_per_caption: int = 10,
) -> Dict[str, Any]:
    if max_words_per_caption < 1:
        raise CaptionPlanError("max_words_per_caption_must_be_positive")

    duration = float(voice_plan["duration_seconds"])
    cues = []

    for segment in voice_plan.get("segments", []):
        text = str(segment.get("text") or "").strip()
        if not text:
            continue

        start = float(segment["start_seconds"])
        end = float(segment["end_seconds"])
        pieces = _split_text(text, max_words_per_caption)
        if not pieces:
            continue

        span = (end - start) / len(pieces)
        for index, piece in enumerate(pieces):
            cue_start = start + span * index
            cue_end = end if index == len(pieces) - 1 else start + span * (index + 1)
            cues.append({
                "id": f"caption_{len(cues) + 1:04d}",
                "start_seconds": cue_start,
                "end_seconds": cue_end,
                "duration_seconds": cue_end - cue_start,
                "text": piece,
                "scene_index": segment.get("scene_index"),
                "voice_segment_id": segment.get("id"),
            })

    previous_end = 0.0
    for cue in cues:
        if cue["start_seconds"] < previous_end - 1e-6:
            raise CaptionPlanError("caption_cues_overlap")
        if cue["end_seconds"] > duration + 1e-6:
            raise CaptionPlanError("caption_outside_project")
        previous_end = cue["end_seconds"]

    return {
        "version": 1,
        "duration_seconds": duration,
        "max_words_per_caption": max_words_per_caption,
        "cues": cues,
        "format": "srt-ready",
        "status": "planned",
    }
