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


if __name__ == "__main__":
    unittest.main()
