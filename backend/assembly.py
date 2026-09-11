import os
import subprocess
from pathlib import Path
from typing import List

class AssemblyError(RuntimeError):
    pass

def assemble_videos(input_paths: List[Path], output_path: Path, *, ffmpeg_bin: str | None = None) -> int:
    if not input_paths:
        raise AssemblyError("no_scene_files")
    missing = [str(path) for path in input_paths if not path.is_file()]
    if missing:
        raise AssemblyError(f"missing_scene_file: {missing[0]}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    binary = ffmpeg_bin or os.environ.get("FFMPEG_BIN", "ffmpeg")
    command = [binary, "-y"]
    for path in input_paths:
        command.extend(["-i", str(path)])
    inputs = "".join(f"[{i}:v:0]" for i in range(len(input_paths)))
    command.extend([
        "-filter_complex", f"{inputs}concat=n={len(input_paths)}:v=1:a=0[v]",
        "-map", "[v]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ])
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "3600")),
            check=False,
        )
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
