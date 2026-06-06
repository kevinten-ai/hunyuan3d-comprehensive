import sys
import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import auto_print
from scripts.auto_print import validate_printer_config


class AutoPrintConfigTests(unittest.TestCase):
    def test_missing_config_is_not_valid(self):
        errors, warnings = validate_printer_config(None)

        self.assertTrue(errors)
        self.assertFalse(warnings)
        self.assertIn("config/printer.json", errors[0])

    def test_template_placeholders_are_not_valid(self):
        errors, warnings = validate_printer_config(
            {
                "host": "192.168.1.100",
                "access_code": "YOUR_ACCESS_CODE",
                "serial": "SNXXX",
                "method": "mqtt",
            }
        )

        self.assertTrue(any("access_code" in error for error in errors))
        self.assertTrue(any("serial" in error for error in errors))
        self.assertTrue(any("host" in warning for warning in warnings))

    def test_valid_mqtt_config_passes(self):
        errors, warnings = validate_printer_config(
            {
                "host": "192.0.2.25",
                "access_code": "12345678",
                "serial": "01S00A000000000",
                "method": "mqtt",
            }
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_unsupported_queue_method_is_not_valid(self):
        errors, _warnings = validate_printer_config(
            {
                "host": "192.0.2.25",
                "access_code": "12345678",
                "serial": "01S00A000000000",
                "method": "http",
            }
        )

        self.assertTrue(any("method" in error for error in errors))

    def test_check_config_command_returns_nonzero_when_missing(self):
        with TemporaryDirectory() as tmp:
            missing_config = Path(tmp) / "printer.json"
            with patch.object(auto_print, "CONFIG_FILE", missing_config), \
                    patch.object(sys, "argv", ["auto_print.py", "check-config"]), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 1)

    def test_config_command_rejects_template_values_before_save(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "printer.json"
            argv = [
                "auto_print.py",
                "config",
                "--host",
                "192.168.1.100",
                "--access-code",
                "YOUR_ACCESS_CODE",
                "--serial",
                "SNXXX",
            ]
            with patch.object(auto_print, "CONFIG_FILE", config_file), \
                    patch.object(sys, "argv", argv), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 1)

            self.assertFalse(config_file.exists())

    def test_config_command_saves_valid_values(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "printer.json"
            argv = [
                "auto_print.py",
                "config",
                "--host",
                "192.0.2.25",
                "--access-code",
                "12345678",
                "--serial",
                "01S00A000000000",
            ]
            with patch.object(auto_print, "CONFIG_FILE", config_file), \
                    patch.object(auto_print, "CONFIG_DIR", config_file.parent), \
                    patch.object(sys, "argv", argv), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 0)

            self.assertTrue(config_file.exists())
            saved = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["host"], "192.0.2.25")
            self.assertEqual(saved["method"], "mqtt")

    def test_status_command_returns_nonzero_when_config_missing(self):
        with TemporaryDirectory() as tmp:
            missing_config = Path(tmp) / "printer.json"
            with patch.object(auto_print, "CONFIG_FILE", missing_config), \
                    patch.object(sys, "argv", ["auto_print.py", "status"]), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 1)


if __name__ == "__main__":
    unittest.main()
