from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class CaptionRenderError(ValueError):
    pass


def _timestamp(seconds: float) -> str:
    total_ms = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(*, caption_plan: Dict[str, Any], output_path: Path) -> int:
    lines = []
    for index, cue in enumerate(caption_plan.get("cues") or [], 1):
        text = str(cue.get("text") or "").strip()
        if not text:
            continue
        lines.extend([
            str(index),
            f"{_timestamp(cue['start_seconds'])} --> {_timestamp(cue['end_seconds'])}",
            text,
            "",
        ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path.stat().st_size
