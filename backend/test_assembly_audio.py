from pathlib import Path
from assembly import build_ffmpeg_command


def _make_inputs(tmp_path):
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    a.write_bytes(b"placeholder")
    b.write_bytes(b"placeholder")
    return a, b


def test_build_command_without_audio(tmp_path):
    a, b = _make_inputs(tmp_path)
    command = build_ffmpeg_command([a, b], tmp_path / "out.mp4")
    joined = " ".join(command)
    assert "concat=n=2:v=1:a=0" in joined
    assert "-map [v]" in joined


def test_build_command_with_audio(tmp_path):
    a, b = _make_inputs(tmp_path)
    voice1 = tmp_path / "voice_0001.wav"
    voice2 = tmp_path / "voice_0002.wav"
    voice1.write_bytes(b"placeholder")
    voice2.write_bytes(b"placeholder")

    command = build_ffmpeg_command(
        [a, b],
        tmp_path / "out.mp4",
        voice_segments=[
            {"audio_path": str(voice1), "start_seconds": 0, "status": "ready"},
            {"audio_path": str(voice2), "start_seconds": 5, "status": "ready"},
        ],
        duration_seconds=10,
    )
    joined = " ".join(command)
    assert "adelay=0|0" in joined
    assert "adelay=5000|5000" in joined
    assert "amix=inputs=2" in joined
    assert "-map [a_mix]" in joined
