import os
import subprocess
from pathlib import Path
from typing import List

class AssemblyError(RuntimeError):
    pass

def _voice_segments(items):
    return [x for x in (items or []) if x.get("audio_path") and x.get("status") == "ready"]

def build_ffmpeg_command(input_paths: List[Path], output_path: Path, *, ffmpeg_bin: str | None = None,
                         voice_segments=None, duration_seconds: float | None = None,
                         subtitle_path: Path | None = None) -> List[str]:
    if not input_paths:
        raise AssemblyError("no_scene_files")
    missing = [str(p) for p in input_paths if not p.is_file()]
    if missing:
        raise AssemblyError(f"missing_scene_file: {missing[0]}")
    binary = ffmpeg_bin or os.environ.get("FFMPEG_BIN", "ffmpeg")
    audio = _voice_segments(voice_segments)
    command = [binary, "-y"]
    for p in input_paths:
        command += ["-i", str(p)]
    for item in audio:
        p = Path(item["audio_path"])
        if not p.is_file():
            raise AssemblyError(f"missing_voice_file: {p}")
        command += ["-i", str(p)]
    video_inputs = "".join(f"[{i}:v:0]" for i in range(len(input_paths)))
    filters = [f"{video_inputs}concat=n={len(input_paths)}:v=1:a=0[v]"]
    video_label = "[v]"
    if subtitle_path is not None:
        if not subtitle_path.is_file():
            raise AssemblyError(f"missing_subtitle_file: {subtitle_path}")
        escaped = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        filters.append(f"[v]subtitles='{escaped}':force_style='FontName=Noto Sans Arabic,FontSize=22'[v1]")
        video_label = "[v1]"
    audio_label = None
    if audio:
        if duration_seconds is None or float(duration_seconds) <= 0:
            raise AssemblyError("duration_required_for_audio_mix")
        duration = float(duration_seconds)
        base_index = len(input_paths)
        parts = []
        for offset, item in enumerate(audio):
            index = base_index + offset
            delay_ms = max(0, round(float(item.get("start_seconds", 0)) * 1000))
            label = f"[a{offset}]"
            parts.append(f"[{index}:a:0]adelay={delay_ms}|{delay_ms},aresample=async=1:first_pts=0,apad=whole_dur={duration},atrim=duration={duration}{label}")
        filters.extend(parts)
        if len(parts) == 1:
            audio_label = "[a0]"
        else:
            mix_inputs = "".join(f"[a{i}]" for i in range(len(parts)))
            filters.append(f"{mix_inputs}amix=inputs={len(parts)}:duration=longest:dropout_transition=0,atrim=duration={duration}[a_mix]")
            audio_label = "[a_mix]"
    command += ["-filter_complex", ";".join(filters), "-map", video_label,
                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    if audio_label:
        command += ["-map", audio_label, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"]
    else:
        command += ["-an"]
    command += ["-movflags", "+faststart", str(output_path)]
    return command

def assemble_videos(input_paths: List[Path], output_path: Path, *, ffmpeg_bin: str | None = None,
                    voice_segments=None, duration_seconds: float | None = None,
                    subtitle_path: Path | None = None) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(input_paths, output_path, ffmpeg_bin=ffmpeg_bin,
                                   voice_segments=voice_segments, duration_seconds=duration_seconds,
                                   subtitle_path=subtitle_path)
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "3600")), check=False)
    except FileNotFoundError as exc:
        raise AssemblyError("ffmpeg_not_installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise AssemblyError("ffmpeg_timeout") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().replace("\n", " ")
        raise AssemblyError(f"ffmpeg_failed: {detail[-1000:] or 'unknown_error'}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise AssemblyError("ffmpeg_output_missing")
    return output_path.stat().st_size
