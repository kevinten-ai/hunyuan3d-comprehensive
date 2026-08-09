import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class GlbTo3mfTests(unittest.TestCase):
    def test_help_returns_success(self):
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "glb_to_3mf.py"), "--help"],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3MF", result.stdout)

    def test_cli_converts_glb_to_3mf(self):
        import trimesh

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "box.glb"
            output = tmp_path / "box.3mf"
            trimesh.creation.box(extents=(1, 1, 1)).export(str(source))

            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "scripts" / "glb_to_3mf.py"),
                    str(source),
                    str(output),
                ],
                cwd=str(PROJECT_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)
            self.assertIn("[OK]", result.stdout)


if __name__ == "__main__":
    unittest.main()
