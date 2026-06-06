import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.continuous_print import ContinuousPrinter


class ContinuousPrintTests(unittest.TestCase):
    def test_text_generation_does_not_mock_by_default(self):
        with TemporaryDirectory() as tmp:
            printer = ContinuousPrinter(output_dir=tmp, auto_start=False)

            result = printer.generate_from_text("a rabbit")

            self.assertIsNone(result)

    def test_text_generation_mock_mode_creates_model_file(self):
        with TemporaryDirectory() as tmp:
            printer = ContinuousPrinter(output_dir=tmp, auto_start=False, mock=True)

            result = printer.generate_from_text("a rabbit")

            self.assertIsNotNone(result)
            self.assertTrue(Path(result).exists())
            self.assertEqual(Path(result).suffix, ".stl")

    def test_image_generation_does_not_run_by_default(self):
        with TemporaryDirectory() as tmp:
            printer = ContinuousPrinter(output_dir=tmp, auto_start=False)

            result = printer.generate_from_image("input.png")

            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
