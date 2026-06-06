import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import ai_to_print


class AiToPrintTests(unittest.TestCase):
    def test_text_generation_requires_mock_mode_for_placeholder(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_text_to_3d("a rabbit", output_dir=tmp, mock=False)

            self.assertIsNone(result)

    def test_text_generation_mock_mode_returns_expected_path(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_text_to_3d("a rabbit", output_dir=tmp, mock=True)

            self.assertTrue(result.endswith("model.stl"))
            self.assertTrue(Path(result).exists())

    def test_image_generation_requires_mock_mode_for_placeholder(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_image_to_3d("input.png", output_dir=tmp, mock=False)

            self.assertIsNone(result)

    def test_image_generation_mock_mode_returns_expected_path(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_image_to_3d("input.png", output_dir=tmp, mock=True)

            self.assertTrue(result.endswith("model.stl"))
            self.assertTrue(Path(result).exists())

    def test_repair_model_returns_existing_path(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text(
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

            result = ai_to_print.repair_model(str(source))

            self.assertTrue(Path(result).exists())


if __name__ == "__main__":
    unittest.main()
