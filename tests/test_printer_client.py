import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bambu_print.printer_client import BambuPrinterClient, PrinterStatus


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class FakeRequests:
    def __init__(self, response: FakeResponse | None = None,
                 error: Exception | None = None):
        self.response = response
        self.error = error

    def post(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


class PrinterClientTests(unittest.TestCase):
    def make_client(self) -> BambuPrinterClient:
        return BambuPrinterClient(
            host="192.0.2.10",
            access_code="dummy",
            serial="SN000",
        )

    def test_default_status_includes_remaining_time(self):
        status = PrinterStatus()

        self.assertEqual(status.remaining_time, 0)

    def test_parse_status_report_updates_print_fields(self):
        client = self.make_client()

        client._parse_status_report(
            {
                "print": {
                    "state": "printing",
                    "progress": 42.5,
                    "layer": 12,
                    "total_layers": 80,
                    "remain_time": 3600,
                },
                "device": {"ip": "192.0.2.10"},
            }
        )

        status = client.get_status()
        self.assertEqual(status.print_status, "printing")
        self.assertEqual(status.progress, 42.5)
        self.assertEqual(status.layer, 12)
        self.assertEqual(status.total_layers, 80)
        self.assertEqual(status.remaining_time, 3600)
        self.assertEqual(status.ip_address, "192.0.2.10")

    def test_start_print_uses_explicit_filename_without_uploaded_file_cache(self):
        client = self.make_client()
        client._mqtt_connected = True
        captured = {}

        def capture(command):
            captured["command"] = command
            return True

        with patch.object(client, "_send_mqtt_command", side_effect=capture):
            self.assertTrue(client.start_print("plate.3mf"))

        self.assertEqual(captured["command"]["print"]["command"], "project_file")
        self.assertEqual(captured["command"]["print"]["param"], "plate.3mf")

    def test_start_print_defaults_to_first_cached_file(self):
        client = self.make_client()
        client._print_files["cached.3mf"] = "C:/tmp/cached.3mf"

        command = client._build_start_print_command()

        self.assertEqual(command["print"]["param"], "cached.3mf")

    def test_send_file_caches_remote_file_only_after_successful_upload(self):
        client = self.make_client()

        with TemporaryDirectory() as tmp:
            model = Path(tmp) / "plate.3mf"
            model.write_text("3mf", encoding="utf-8")

            fake_requests = FakeRequests(response=FakeResponse(201))
            with patch.dict(sys.modules, {"requests": fake_requests}):
                self.assertTrue(client.send_file(str(model), filename="plate.3mf"))

        self.assertEqual(client._print_files["plate.3mf"], str(model))

    def test_send_file_returns_false_when_http_upload_fails(self):
        client = self.make_client()

        with TemporaryDirectory() as tmp:
            model = Path(tmp) / "plate.3mf"
            model.write_text("3mf", encoding="utf-8")

            fake_requests = FakeRequests(response=FakeResponse(500))
            with patch.dict(sys.modules, {"requests": fake_requests}):
                self.assertFalse(client.send_file(str(model), filename="plate.3mf"))

        self.assertNotIn("plate.3mf", client._print_files)

    def test_send_file_returns_false_when_http_upload_raises(self):
        client = self.make_client()

        with TemporaryDirectory() as tmp:
            model = Path(tmp) / "plate.3mf"
            model.write_text("3mf", encoding="utf-8")

            fake_requests = FakeRequests(error=OSError("network down"))
            with patch.dict(sys.modules, {"requests": fake_requests}):
                self.assertFalse(client.send_file(str(model), filename="plate.3mf"))

        self.assertNotIn("plate.3mf", client._print_files)


if __name__ == "__main__":
    unittest.main()
