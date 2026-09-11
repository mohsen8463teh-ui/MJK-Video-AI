from audio_plan import build_voice_plan
from captions import build_caption_plan


def timeline():
    return {
        "duration_seconds": 30,
        "tracks": {
            "video": [
                {"start_seconds": 0, "end_seconds": 5, "duration_seconds": 5, "scene_index": 1},
                {"start_seconds": 5, "end_seconds": 10, "duration_seconds": 5, "scene_index": 1},
                {"start_seconds": 10, "end_seconds": 20, "duration_seconds": 10, "scene_index": 2},
                {"start_seconds": 20, "end_seconds": 30, "duration_seconds": 10, "scene_index": 3},
            ]
        },
    }


def test_voice_plan_maps_one_segment_per_scene():
    plan = build_voice_plan(
        timeline=timeline(),
        director_plan={
            "voiceover": [
                {"text": "Hook text"},
                {"narration": "Middle text"},
                {"script": "Final text"},
            ]
        },
        language="فارسی",
    )
    assert len(plan["segments"]) == 3
    assert plan["segments"][0]["start_seconds"] == 0
    assert plan["segments"][0]["end_seconds"] == 10
    assert plan["segments"][1]["start_seconds"] == 10
    assert plan["segments"][2]["end_seconds"] == 30
    assert plan["segments"][0]["status"] == "pending"


def test_empty_voiceover_does_not_create_fake_audio():
    plan = build_voice_plan(
        timeline=timeline(),
        director_plan={"voiceover": []},
        language="فارسی",
    )
    assert all(x["status"] == "not_required" for x in plan["segments"])


def test_caption_plan_splits_without_leaving_timeline():
    voice = build_voice_plan(
        timeline=timeline(),
        director_plan={"voiceover": ["one two three four five six"]},
        language="English",
    )
    captions = build_caption_plan(
        voice_plan=voice,
        max_words_per_caption=3,
    )
    assert [x["text"] for x in captions["cues"]] == [
        "one two three", "four five six"
    ]
    assert captions["cues"][0]["start_seconds"] == 0
    assert captions["cues"][-1]["end_seconds"] == 10


def test_caption_empty_text_is_skipped():
    voice = build_voice_plan(
        timeline=timeline(),
        director_plan={"voiceover": ["", "", ""]},
        language="فارسی",
    )
    captions = build_caption_plan(voice_plan=voice)
    assert captions["cues"] == []


def test_caption_cues_are_ordered_and_non_overlapping():
    voice = build_voice_plan(
        timeline=timeline(),
        director_plan={"voiceover": [
            "a b c d e f g h i j k l",
            "m n o p",
            "q r s t",
        ]},
        language="English",
    )
    captions = build_caption_plan(
        voice_plan=voice,
        max_words_per_caption=4,
    )
    previous = 0
    for cue in captions["cues"]:
        assert cue["start_seconds"] >= previous
        assert cue["end_seconds"] > cue["start_seconds"]
        previous = cue["end_seconds"]
    assert previous <= 30


def test_voice_plan_preserves_project_duration():
    plan = build_voice_plan(
        timeline=timeline(),
        director_plan={"voiceover": "single narration"},
        language="English",
    )
    assert plan["duration_seconds"] == 30
    assert len(plan["segments"]) == 3
