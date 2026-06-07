import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import auto_print


class FakeQueue:
    def __init__(self, add_error: Exception | None = None):
        self.add_error = add_error

    def add(self, *_args, **_kwargs):
        if self.add_error:
            raise self.add_error
        return "job123"

    def remove(self, _job_id):
        return False

    def cancel(self, _job_id):
        return False


class AutoPrintCliTests(unittest.TestCase):
    def test_help_uses_repo_root_copy_safe_examples(self):
        stdout = StringIO()

        with patch.object(sys, "argv", ["auto_print.py", "--help"]), \
                patch("sys.stdout", new=stdout):
            with self.assertRaises(SystemExit) as exit_context:
                auto_print.main()

        self.assertEqual(exit_context.exception.code, 0)

        output = stdout.getvalue()
        self.assertIn(
            "python scripts/auto_print.py config --host YOUR_PRINTER_IP "
            "--access-code YOUR_ACCESS_CODE --serial YOUR_PRINTER_SERIAL",
            output,
        )
        self.assertNotIn("python auto_print.py config", output)
        self.assertNotIn("YOUR_CODE", output)
        self.assertNotIn("SNXXX", output)

    def test_add_returns_nonzero_without_traceback_when_queue_rejects_file(self):
        with TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.stl"
            model.write_text("solid test\nendsolid test\n", encoding="utf-8")
            stdout = StringIO()

            with patch.object(auto_print, "get_queue", return_value=FakeQueue(ValueError("bad model"))), \
                    patch.object(sys, "argv", ["auto_print.py", "add", str(model)]), \
                    patch("sys.stdout", new=stdout):
                self.assertEqual(auto_print.main(), 1)

            output = stdout.getvalue()
            self.assertIn("添加任务失败", output)
            self.assertNotIn("Traceback", output)

    def test_remove_returns_nonzero_when_job_is_missing(self):
        with patch.object(auto_print, "get_queue", return_value=FakeQueue()), \
                patch.object(sys, "argv", ["auto_print.py", "remove", "missing"]), \
                patch("sys.stdout", new=StringIO()):
            self.assertEqual(auto_print.main(), 1)

    def test_cancel_returns_nonzero_when_job_is_missing(self):
        with patch.object(auto_print, "get_queue", return_value=FakeQueue()), \
                patch.object(sys, "argv", ["auto_print.py", "cancel", "missing"]), \
                patch("sys.stdout", new=StringIO()):
            self.assertEqual(auto_print.main(), 1)

    def test_discover_returns_nonzero_when_no_printers_found(self):
        stdout = StringIO()

        with patch.object(auto_print, "discover_printers", return_value=[]), \
                patch.object(sys, "argv", ["auto_print.py", "discover"]), \
                patch("sys.stdout", new=stdout):
            self.assertEqual(auto_print.main(), 1)

        self.assertIn("未发现打印机", stdout.getvalue())

    def test_discover_returns_zero_when_printer_is_found(self):
        stdout = StringIO()
        printers = [{"ip": "192.0.2.25", "name": "Bambu Lab"}]

        with patch.object(auto_print, "discover_printers", return_value=printers), \
                patch.object(sys, "argv", ["auto_print.py", "discover"]), \
                patch("sys.stdout", new=stdout):
            self.assertEqual(auto_print.main(), 0)

        output = stdout.getvalue()
        self.assertIn("发现 1 台打印机", output)
        self.assertIn("192.0.2.25", output)


if __name__ == "__main__":
    unittest.main()
