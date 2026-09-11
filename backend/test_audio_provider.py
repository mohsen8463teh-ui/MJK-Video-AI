from pathlib import Path

import pytest

from audio_provider import AudioProviderError, AudioRouter, KokoroHTTPProvider
from audio_renderer import AudioRenderError, render_voice_plan


class FakeProvider:
    provider_id = "fake"

    def __init__(self):
        self.calls = []

    def generate(self, *, text, output_path, language, voice=None):
        self.calls.append((text, language, voice))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-wav")
        return {
            "provider": self.provider_id,
            "output_path": str(output_path),
            "size_bytes": 8,
        }


def make_plan():
    return {
        "version": 1,
        "language": "English",
        "duration_seconds": 10,
        "segments": [
            {
                "id": "voice_0001",
                "start_seconds": 0,
                "duration_seconds": 5,
                "end_seconds": 5,
                "text": "Hello world.",
                "status": "pending",
            },
            {
                "id": "voice_0002",
                "start_seconds": 5,
                "duration_seconds": 5,
                "end_seconds": 10,
                "text": "",
                "status": "not_required",
            },
        ],
    }


def test_router_is_free_of_required_api_keys():
    router = AudioRouter()
    assert router.select() is None
    assert router.status()["provider_available"] is False


def test_kokoro_provider_requires_url():
    provider = KokoroHTTPProvider("")
    assert provider.configured() is False
    with pytest.raises(AudioProviderError):
        provider.generate(
            text="hello",
            output_path=Path("/tmp/mjk-test.wav"),
            language="English",
        )


def test_renderer_creates_audio_and_marks_segment_ready(tmp_path):
    provider = FakeProvider()
    plan = make_plan()
    result = render_voice_plan(
        voice_plan=plan,
        provider=provider,
        output_dir=tmp_path,
        voice="test",
    )
    assert result["status"] == "ready"
    assert result["rendered_segments"] == 1
    assert result["segments"][0]["status"] == "ready"
    assert Path(result["segments"][0]["audio_path"]).is_file()
    assert provider.calls == [("Hello world.", "English", "test")]


def test_renderer_is_resumable_and_skips_ready_segments(tmp_path):
    provider = FakeProvider()
    plan = make_plan()
    plan["segments"][0]["status"] = "ready"
    plan["segments"][0]["audio_path"] = str(tmp_path / "already.wav")

    result = render_voice_plan(
        voice_plan=plan,
        provider=provider,
        output_dir=tmp_path,
    )
    assert result["rendered_segments"] == 0
    assert provider.calls == []


def test_renderer_requires_provider(tmp_path):
    with pytest.raises(AudioRenderError, match="no_audio_provider"):
        render_voice_plan(
            voice_plan=make_plan(),
            provider=None,
            output_dir=tmp_path,
        )


def test_renderer_does_not_call_network(tmp_path):
    provider = FakeProvider()
    plan = make_plan()
    render_voice_plan(
        voice_plan=plan,
        provider=provider,
        output_dir=tmp_path,
    )
    assert provider.calls
