"""Resumable rendering of voice segments onto the canonical media plan."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class AudioRenderError(RuntimeError):
    pass


def render_voice_plan(
    *,
    voice_plan: Dict[str, Any],
    provider: Any,
    output_dir: Path,
    voice: str | None = None,
) -> Dict[str, Any]:
    if provider is None:
        raise AudioRenderError("no_audio_provider")

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = 0

    for segment in voice_plan.get("segments", []):
        if segment.get("status") in {"not_required", "ready"}:
            continue

        text = str(segment.get("text") or "").strip()
        if not text:
            segment["status"] = "not_required"
            continue

        segment_id = str(segment["id"])
        output_path = output_dir / f"{segment_id}.wav"

        try:
            result = provider.generate(
                text=text,
                output_path=output_path,
                language=str(voice_plan.get("language") or ""),
                voice=voice,
            )
        except Exception as exc:
            segment["status"] = "failed"
            segment["error"] = str(exc)
            raise AudioRenderError(
                f"voice_segment_failed: {segment_id}: {exc}"
            ) from exc

        segment["status"] = "ready"
        segment["audio_path"] = str(result["output_path"])
        segment["provider"] = result.get("provider")
        segment["size_bytes"] = result.get("size_bytes")
        rendered += 1

    voice_plan["status"] = (
        "ready"
        if all(
            item.get("status") in {"ready", "not_required"}
            for item in voice_plan.get("segments", [])
        )
        else "partial"
    )
    voice_plan["rendered_segments"] = rendered
    return voice_plan
