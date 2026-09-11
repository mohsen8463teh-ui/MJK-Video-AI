import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from assembly import AssemblyError, assemble_videos

class AssemblyTests(unittest.TestCase):
    def test_no_scenes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AssemblyError, "no_scene_files"):
                assemble_videos([], Path(tmp) / "final.mp4")

    def test_missing_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AssemblyError, "missing_scene_file"):
                assemble_videos([Path(tmp) / "missing.mp4"], Path(tmp) / "final.mp4")

    def test_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, out = root/"a.mp4", root/"b.mp4", root/"final.mp4"
            a.write_bytes(b"a")
            b.write_bytes(b"b")
            def fake_run(command, **kwargs):
                out.write_bytes(b"final")
                class R:
                    returncode = 0
                    stderr = ""
                return R()
            with patch("assembly.subprocess.run", side_effect=fake_run) as run:
                self.assertEqual(assemble_videos([a, b], out), 5)
            self.assertTrue(any("concat=n=2:v=1:a=0[v]" in x for x in run.call_args.args[0]))
            self.assertEqual(run.call_args.args[0][-1], str(out))

    def test_ffmpeg_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene = Path(tmp) / "scene.mp4"
            scene.write_bytes(b"scene")
            with patch("assembly.subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaisesRegex(AssemblyError, "ffmpeg_not_installed"):
                    assemble_videos([scene], Path(tmp) / "final.mp4")

if __name__ == "__main__":
    unittest.main()
