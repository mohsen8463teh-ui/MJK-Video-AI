"""Canonical media timeline for MJK Video AI."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List

TRACKS = ("video", "voice", "music", "sfx", "captions")
STATUSES = ("pending", "generating", "ready", "failed")


class TimelineError(ValueError):
    pass


def _nonnegative(value: Any, field: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise TimelineError(f"invalid_{field}") from exc
    if n < 0:
        raise TimelineError(f"negative_{field}")
    return n


def _make_asset(
    *,
    asset_id: str,
    asset_type: str,
    start_seconds: float,
    duration_seconds: float,
    status: str = "pending",
    scene_index: int | None = None,
    shot_index: int | None = None,
    relative_path: str | None = None,
    provider: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if not asset_id:
        raise TimelineError("asset_id_required")
    if asset_type not in TRACKS:
        raise TimelineError(f"unsupported_asset_type: {asset_type}")
    if status not in STATUSES:
        raise TimelineError(f"unsupported_status: {status}")
    start = _nonnegative(start_seconds, "start_seconds")
    duration = _nonnegative(duration_seconds, "duration_seconds")
    if duration <= 0:
        raise TimelineError("duration_must_be_positive")

    asset: Dict[str, Any] = {
        "id": asset_id,
        "type": asset_type,
        "start_seconds": start,
        "duration_seconds": duration,
        "end_seconds": start + duration,
        "status": status,
    }
    if scene_index is not None:
        asset["scene_index"] = int(scene_index)
    if shot_index is not None:
        asset["shot_index"] = int(shot_index)
    if relative_path:
        asset["relative_path"] = relative_path
    if provider:
        asset["provider"] = provider
    if metadata:
        asset["metadata"] = metadata
    return asset


def build_media_timeline(
    *,
    project_duration_seconds: int,
    shots: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        total = int(project_duration_seconds)
    except (TypeError, ValueError) as exc:
        raise TimelineError("invalid_project_duration") from exc
    if total <= 0:
        raise TimelineError("project_duration_must_be_positive")

    ordered = sorted(list(shots), key=lambda item: int(item.get("shot_index", 0)))
    if not ordered:
        raise TimelineError("timeline_requires_video_shots")

    tracks: Dict[str, List[Dict[str, Any]]] = {track: [] for track in TRACKS}
    cursor = 0.0
    expected_index = 1

    for shot in ordered:
        shot_index = int(shot.get("shot_index", 0))
        if shot_index != expected_index:
            raise TimelineError("shot_indices_must_be_contiguous")
        expected_index += 1

        duration = _nonnegative(shot.get("duration_seconds"), "shot_duration_seconds")
        if duration <= 0:
            raise TimelineError("shot_duration_must_be_positive")

        file_info = shot.get("file") or {}
        provider_result = shot.get("provider_result") or {}
        tracks["video"].append(
            _make_asset(
                asset_id=f"shot_{shot_index:04d}",
                asset_type="video",
                start_seconds=cursor,
                duration_seconds=duration,
                status="ready" if file_info.get("relative_path") else "pending",
                scene_index=shot.get("scene_index"),
                shot_index=shot_index,
                relative_path=file_info.get("relative_path"),
                provider=provider_result.get("provider"),
                metadata={
                    "scene_shot_index": shot.get("scene_shot_index"),
                    "scene_shot_count": shot.get("scene_shot_count"),
                },
            )
        )
        cursor += duration

    if abs(cursor - total) > 1e-6:
        raise TimelineError(f"video_timeline_duration_mismatch: {cursor} != {total}")

    timeline = {
        "version": 1,
        "duration_seconds": total,
        "tracks": tracks,
        "audio_ready": False,
        "captions_ready": False,
    }
    validate_media_timeline(timeline)
    return timeline


def validate_media_timeline(timeline: Dict[str, Any]) -> None:
    try:
        total = float(timeline["duration_seconds"])
        tracks = timeline["tracks"]
    except (KeyError, TypeError, ValueError) as exc:
        raise TimelineError("invalid_timeline") from exc

    if total <= 0 or not isinstance(tracks, dict):
        raise TimelineError("invalid_timeline")

    for track in TRACKS:
        items = tracks.get(track)
        if not isinstance(items, list):
            raise TimelineError(f"invalid_track: {track}")
        previous_end = 0.0
        for item in items:
            start = _nonnegative(item.get("start_seconds"), "start_seconds")
            duration = _nonnegative(item.get("duration_seconds"), "duration_seconds")
            end = _nonnegative(item.get("end_seconds"), "end_seconds")
            if duration <= 0 or abs(start + duration - end) > 1e-6:
                raise TimelineError("invalid_asset_timing")
            if start + 1e-6 < previous_end:
                raise TimelineError(f"overlapping_assets: {track}")
            if end > total + 1e-6:
                raise TimelineError(f"asset_outside_project: {track}")
            previous_end = end

    video = tracks["video"]
    if not video:
        raise TimelineError("timeline_requires_video_track")

    expected_start = 0.0
    for item in video:
        if abs(float(item["start_seconds"]) - expected_start) > 1e-6:
            raise TimelineError("video_track_has_gap")
        expected_start = float(item["end_seconds"])

    if abs(expected_start - total) > 1e-6:
        raise TimelineError("video_track_does_not_cover_project")
