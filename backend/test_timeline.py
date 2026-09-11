from timeline import TimelineError, build_media_timeline, validate_media_timeline


def make_shots(durations):
    return [
        {
            "shot_index": i,
            "scene_index": 1,
            "scene_shot_index": i,
            "scene_shot_count": len(durations),
            "duration_seconds": duration,
            "file": {"relative_path": f"scenes/shot_{i:04d}.mp4"},
        }
        for i, duration in enumerate(durations, 1)
    ]


def test_30_seconds_exact():
    timeline = build_media_timeline(project_duration_seconds=30, shots=make_shots([5] * 6))
    assert len(timeline["tracks"]["video"]) == 6
    assert timeline["tracks"]["video"][-1]["end_seconds"] == 30


def test_30_minutes_exact():
    timeline = build_media_timeline(project_duration_seconds=1800, shots=make_shots([5] * 360))
    assert len(timeline["tracks"]["video"]) == 360
    assert timeline["tracks"]["video"][-1]["end_seconds"] == 1800


def test_future_tracks_are_present_and_empty():
    timeline = build_media_timeline(project_duration_seconds=10, shots=make_shots([5, 5]))
    assert set(timeline["tracks"]) == {"video", "voice", "music", "sfx", "captions"}
    for track in ("voice", "music", "sfx", "captions"):
        assert timeline["tracks"][track] == []


def test_video_track_has_no_gaps():
    timeline = build_media_timeline(project_duration_seconds=9, shots=make_shots([2, 3, 4]))
    assert [x["start_seconds"] for x in timeline["tracks"]["video"]] == [0, 2, 5]
    assert [x["end_seconds"] for x in timeline["tracks"]["video"]] == [2, 5, 9]


def test_noncontiguous_shots_fail():
    bad = make_shots([5, 5])
    bad[1]["shot_index"] = 3
    try:
        build_media_timeline(project_duration_seconds=10, shots=bad)
    except TimelineError as exc:
        assert str(exc) == "shot_indices_must_be_contiguous"
    else:
        raise AssertionError("expected TimelineError")


def test_duration_mismatch_fails():
    try:
        build_media_timeline(project_duration_seconds=11, shots=make_shots([5, 5]))
    except TimelineError as exc:
        assert "video_timeline_duration_mismatch" in str(exc)
    else:
        raise AssertionError("expected TimelineError")


def test_overlap_validation_fails():
    timeline = build_media_timeline(project_duration_seconds=10, shots=make_shots([5, 5]))
    timeline["tracks"]["voice"] = [
        {"id": "voice_1", "type": "voice", "start_seconds": 0, "duration_seconds": 4,
         "end_seconds": 4, "status": "ready"},
        {"id": "voice_2", "type": "voice", "start_seconds": 3, "duration_seconds": 2,
         "end_seconds": 5, "status": "ready"},
    ]
    try:
        validate_media_timeline(timeline)
    except TimelineError as exc:
        assert str(exc) == "overlapping_assets: voice"
    else:
        raise AssertionError("expected TimelineError")
