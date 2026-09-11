from __future__ import annotations
from typing import Any, Dict, List

def _int(value: Any, default: int) -> int:
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return default

def _partition(seconds: int, maximum: int) -> List[int]:
    seconds = max(2, seconds)
    maximum = max(2, maximum)
    if seconds <= maximum:
        return [seconds]
    count = (seconds + maximum - 1) // maximum
    while count >= 2:
        base, rem = divmod(seconds, count)
        parts = [base + (1 if i < rem else 0) for i in range(count)]
        if min(parts) >= 2 and max(parts) <= maximum:
            return parts
        count -= 1
    raise ValueError("cannot_partition_duration")

def _prompt(scene: Any) -> str:
    if isinstance(scene, str):
        return scene.strip()
    if not isinstance(scene, dict):
        return str(scene)
    parts = []
    for key in ("prompt", "description", "visual", "action", "camera",
                "lighting", "environment", "continuity"):
        value = scene.get(key)
        if value:
            parts.append(f"{key}: {value}")
    return "\n".join(parts).strip()

def build_generation_shots(
    plan: Dict[str, Any],
    total_duration_seconds: int,
    max_clip_duration_seconds: int,
) -> List[Dict[str, Any]]:
    scenes = plan.get("scenes") or []
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Director plan contains no scenes")

    total = max(2, _int(total_duration_seconds, 30))
    maximum = max(2, _int(max_clip_duration_seconds, 5))

    weights = []
    for scene in scenes:
        value = scene.get("duration_seconds", scene.get("duration")) if isinstance(scene, dict) else None
        try:
            weights.append(max(2, int(float(value))) if value is not None else 0)
        except (TypeError, ValueError):
            weights.append(0)
    if not any(weights):
        weights = [1] * len(scenes)

    weight_sum = sum(weights)
    durations = [max(2, int(total * w / weight_sum)) for w in weights]

    diff = total - sum(durations)
    i = 0
    while diff > 0:
        durations[i % len(durations)] += 1
        diff -= 1
        i += 1

    i = 0
    while diff < 0:
        idx = i % len(durations)
        if durations[idx] > 2:
            durations[idx] -= 1
            diff += 1
        i += 1
        if i > len(durations) * (total + 1):
            raise ValueError("unable_to_allocate_scene_duration")

    shots = []
    shot_index = 1
    for scene_index, (scene, scene_duration) in enumerate(
        zip(scenes, durations), start=1
    ):
        prompt = _prompt(scene)
        chunks = _partition(scene_duration, maximum)
        for local_index, duration in enumerate(chunks, start=1):
            shots.append({
                "shot_index": shot_index,
                "scene_index": scene_index,
                "scene_shot_index": local_index,
                "scene_shot_count": len(chunks),
                "duration_seconds": duration,
                "prompt": prompt,
            })
            shot_index += 1
    return shots
