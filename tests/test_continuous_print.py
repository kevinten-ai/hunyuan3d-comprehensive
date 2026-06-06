import sys
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import continuous_print
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

    def test_template_printer_config_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "printer.json").write_text(
                json.dumps(
                    {
                        "host": "192.168.1.100",
                        "access_code": "YOUR_ACCESS_CODE",
                        "serial": "SNXXX",
                        "method": "mqtt",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(continuous_print, "PROJECT_ROOT", root):
                printer = ContinuousPrinter(output_dir=tmp, auto_start=False)

            self.assertIsNone(printer.printer_config)
            self.assertIsNone(printer.print_queue)


if __name__ == "__main__":
    unittest.main()
