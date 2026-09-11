from caption_renderer import write_srt


def test_write_srt_uses_millisecond_timestamps(tmp_path):
    path = tmp_path / "captions.srt"
    size = write_srt(
        caption_plan={
            "cues": [{
                "start_seconds": 0,
                "end_seconds": 1.25,
                "text": "سلام دنیا",
            }]
        },
        output_path=path,
    )
    assert size > 0
    assert path.read_text(encoding="utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,250\nسلام دنیا\n"
    )
