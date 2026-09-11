from scene_planner import build_generation_shots


def make_plan(durations=None, count=3):
    scenes = []
    for i in range(count):
        item = {"prompt": f"test scene {i + 1}"}
        if durations is not None:
            item["duration_seconds"] = durations[i]
        scenes.append(item)
    return {"scenes": scenes}


def assert_plan(total, max_clip, expected_count=None):
    shots = build_generation_shots(
        make_plan(),
        total_duration_seconds=total,
        max_clip_duration_seconds=max_clip,
    )

    assert shots
    assert sum(x["duration_seconds"] for x in shots) == total
    assert max(x["duration_seconds"] for x in shots) <= max_clip
    assert min(x["duration_seconds"] for x in shots) >= 2
    assert [x["shot_index"] for x in shots] == list(range(1, len(shots) + 1))

    if expected_count is not None:
        assert len(shots) == expected_count

    scene_ids = [x["scene_index"] for x in shots]
    assert scene_ids == sorted(scene_ids)
    assert scene_ids[0] == 1
    assert scene_ids[-1] == 3


def test_30_seconds_exact():
    assert_plan(30, 5, 6)


def test_5_minutes_exact():
    assert_plan(300, 5, 60)


def test_30_minutes_exact():
    assert_plan(1800, 5, 360)


def test_scene_duration_weights_are_preserved():
    shots = build_generation_shots(
        make_plan([10, 20, 30]),
        total_duration_seconds=60,
        max_clip_duration_seconds=5,
    )
    by_scene = {}
    for shot in shots:
        by_scene.setdefault(shot["scene_index"], 0)
        by_scene[shot["scene_index"]] += shot["duration_seconds"]

    assert by_scene == {1: 10, 2: 20, 3: 30}
    assert sum(x["duration_seconds"] for x in shots) == 60


def test_non_divisible_duration_is_exact():
    assert_plan(31, 5)


def test_single_scene_long_duration_is_partitioned():
    shots = build_generation_shots(
        {"scenes": [{"prompt": "one scene"}]},
        total_duration_seconds=17,
        max_clip_duration_seconds=5,
    )
    assert [x["duration_seconds"] for x in shots] == [5, 4, 4, 4]
    assert sum(x["duration_seconds"] for x in shots) == 17


def test_missing_scenes_fails_cleanly():
    try:
        build_generation_shots(
            {"scenes": []},
            total_duration_seconds=30,
            max_clip_duration_seconds=5,
        )
    except ValueError as exc:
        assert str(exc) == "Director plan contains no scenes"
    else:
        raise AssertionError("Expected missing-scenes validation error")


def test_shot_metadata_is_consistent():
    shots = build_generation_shots(
        make_plan(),
        total_duration_seconds=30,
        max_clip_duration_seconds=5,
    )

    for scene_index in (1, 2, 3):
        scene_shots = [x for x in shots if x["scene_index"] == scene_index]
        assert scene_shots
        count = len(scene_shots)
        assert all(x["scene_shot_count"] == count for x in scene_shots)
        assert [x["scene_shot_index"] for x in scene_shots] == list(
            range(1, count + 1)
        )
