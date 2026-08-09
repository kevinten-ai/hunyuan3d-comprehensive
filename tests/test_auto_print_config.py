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
                "host": "YOUR_PRINTER_IP",
                "access_code": "YOUR_ACCESS_CODE",
                "serial": "SNXXX",
                "method": "mqtt",
            }
        )

        self.assertTrue(any("host" in error for error in errors))
        self.assertTrue(any("access_code" in error for error in errors))
        self.assertTrue(any("serial" in error for error in errors))
        self.assertEqual(warnings, [])

    def test_tracked_printer_template_is_not_valid_as_runtime_config(self):
        template = Path(__file__).resolve().parents[1] / "config" / "printer.json.example"
        config = json.loads(template.read_text(encoding="utf-8"))

        errors, warnings = validate_printer_config(config)

        self.assertTrue(errors)
        self.assertEqual(warnings, [])

    def test_documented_command_placeholders_are_not_valid(self):
        errors, warnings = validate_printer_config(
            {
                "host": "YOUR_PRINTER_IP",
                "access_code": "YOUR_ACCESS_CODE",
                "serial": "YOUR_PRINTER_SERIAL",
                "method": "mqtt",
            }
        )

        self.assertTrue(any("host" in error for error in errors))
        self.assertTrue(any("access_code" in error for error in errors))
        self.assertTrue(any("serial" in error for error in errors))
        self.assertEqual(warnings, [])

    def test_valid_mqtt_config_passes(self):
        errors, warnings = validate_printer_config(
            {
                "host": "192.0.2.25",
                "access_code": "12345678",
                "serial": "01S00A000000000",
                "method": "mqtt",
                "lan_developer_mode": True,
            }
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_config_warns_when_developer_mode_is_not_confirmed(self):
        errors, warnings = validate_printer_config(
            {
                "host": "192.0.2.25",
                "access_code": "12345678",
                "serial": "01S00A000000000",
                "method": "mqtt",
            }
        )

        self.assertEqual(errors, [])
        self.assertTrue(any("Developer Mode" in warning for warning in warnings))

    def test_invalid_ams_mapping_is_rejected(self):
        errors, _warnings = validate_printer_config(
            {
                "host": "192.0.2.25",
                "access_code": "12345678",
                "serial": "01S00A000000000",
                "method": "mqtt",
                "lan_developer_mode": True,
                "use_ams": True,
                "ams_mapping": [0, 1],
            }
        )

        self.assertTrue(any("ams_mapping" in error for error in errors))

    def test_invalid_network_timeout_is_rejected(self):
        errors, _warnings = validate_printer_config(
            {
                "host": "192.0.2.25",
                "access_code": "12345678",
                "serial": "01S00A000000000",
                "method": "mqtt",
                "lan_developer_mode": True,
                "timeout": 0,
            }
        )

        self.assertTrue(any("timeout" in error for error in errors))

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
            stdout = StringIO()
            with patch.object(auto_print, "CONFIG_FILE", missing_config), \
                    patch.object(sys, "argv", ["auto_print.py", "check-config"]), \
                    patch("sys.stdout", new=stdout):
                self.assertEqual(auto_print.main(), 1)

            output = stdout.getvalue()
            self.assertIn("YOUR_PRINTER_IP", output)
            self.assertNotIn("<ip>", output)

    def test_config_command_rejects_template_values_before_save(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "printer.json"
            argv = [
                "auto_print.py",
                "config",
                "--host",
                "YOUR_PRINTER_IP",
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
            self.assertFalse(saved["lan_developer_mode"])
            self.assertEqual(saved["ams_mapping"], [-1, -1, -1, -1, 0])

    def test_config_command_prompts_for_access_code_without_cli_secret(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "printer.json"
            argv = [
                "auto_print.py",
                "config",
                "--host",
                "192.0.2.25",
                "--serial",
                "01S00A000000000",
            ]
            with patch.object(auto_print, "CONFIG_FILE", config_file), \
                    patch.object(auto_print, "CONFIG_DIR", config_file.parent), \
                    patch.object(sys, "argv", argv), \
                    patch.object(sys.stdin, "isatty", return_value=True), \
                    patch.object(auto_print.getpass, "getpass", return_value="12345678"), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 0)

            saved = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_code"], "12345678")

    def test_config_command_requires_explicit_secret_when_noninteractive(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "printer.json"
            argv = [
                "auto_print.py",
                "config",
                "--host",
                "192.0.2.25",
                "--serial",
                "01S00A000000000",
            ]
            with patch.object(auto_print, "CONFIG_FILE", config_file), \
                    patch.object(sys, "argv", argv), \
                    patch.object(sys.stdin, "isatty", return_value=False), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 1)

            self.assertFalse(config_file.exists())

    def test_status_command_returns_nonzero_when_config_missing(self):
        with TemporaryDirectory() as tmp:
            missing_config = Path(tmp) / "printer.json"
            with patch.object(auto_print, "CONFIG_FILE", missing_config), \
                    patch.object(sys, "argv", ["auto_print.py", "status"]), \
                    patch("sys.stdout", new=StringIO()):
                self.assertEqual(auto_print.main(), 1)


if __name__ == "__main__":
    unittest.main()
