import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ModelConverterCliTests(unittest.TestCase):
    def test_info_output_formats_volume_without_template_text(self):
        with TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.stl"
            model.write_text(
                "solid mock\n"
                "  facet normal 0 0 1\n"
                "    outer loop\n"
                "      vertex 0 0 0\n"
                "      vertex 1 0 0\n"
                "      vertex 0 1 0\n"
                "    endloop\n"
                "  endfacet\n"
                "endsolid mock\n",
                encoding="ascii",
            )

            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "model_converter.py"), "info", str(model)],
                cwd=str(PROJECT_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("体积:", result.stdout)
            self.assertNotIn("if info", result.stdout)


if __name__ == "__main__":
    unittest.main()
