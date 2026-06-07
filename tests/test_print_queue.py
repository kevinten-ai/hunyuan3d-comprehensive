import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bambu_print import PrintQueue, QueueStatus
from bambu_print.print_queue import QueuedJob


class FakePrinter:
    def __init__(self, send_file_result: bool = True,
                 stop_print_result: bool = True,
                 pause_print_result: bool = True,
                 resume_print_result: bool = True):
        self.send_file_result = send_file_result
        self.stop_print_result = stop_print_result
        self.pause_print_result = pause_print_result
        self.resume_print_result = resume_print_result
        self.start_print_called = False
        self.stop_print_called = False
        self.pause_print_called = False
        self.resume_print_called = False
        self.disconnected = False

    def connect(self):
        return True

    def on_status_change(self, _callback):
        return None

    def send_file(self, *_args, **_kwargs):
        return self.send_file_result

    def start_print(self, *_args, **_kwargs):
        self.start_print_called = True
        return True

    def stop_print(self):
        self.stop_print_called = True
        return self.stop_print_result

    def pause_print(self):
        self.pause_print_called = True
        return self.pause_print_result

    def resume_print(self):
        self.resume_print_called = True
        return self.resume_print_result

    def get_status(self):
        raise AssertionError("get_status should not run when upload fails")

    def disconnect(self):
        self.disconnected = True


class PrintQueueTests(unittest.TestCase):
    def make_queue(self, queue_dir: Path) -> PrintQueue:
        return PrintQueue(
            printer_host="192.0.2.10",
            access_code="dummy",
            serial="SN000",
            queue_dir=str(queue_dir),
        )

    def test_add_rejects_unsupported_file_extension(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "bad.txt"
            source.write_text("not a model", encoding="utf-8")
            queue = self.make_queue(tmp_path / "queue")

            with self.assertRaises(ValueError):
                queue.add(str(source))

    def test_add_persists_supported_model_job(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.stl"
            source.write_text("solid test\nendsolid test\n", encoding="utf-8")
            queue_dir = tmp_path / "queue"
            queue = self.make_queue(queue_dir)

            job_id = queue.add(str(source), name="test model", priority=5)
            reloaded = self.make_queue(queue_dir)
            jobs = reloaded.list_queue()

            self.assertTrue(job_id)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["name"], "test model")
            self.assertEqual(jobs[0]["priority"], 5)

    def test_add_does_not_start_queue_by_default(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.stl"
            source.write_text("solid test\nendsolid test\n", encoding="utf-8")
            queue = self.make_queue(tmp_path / "queue")

            queue.add(str(source), name="manual start model")

            self.assertEqual(queue.status, QueueStatus.IDLE)
            self.assertIsNone(queue._worker_thread)

    def test_status_includes_printer_remaining_time(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")

            status = queue.get_status()

            self.assertIn("remaining_time", status["printer"])
            self.assertEqual(status["printer"]["remaining_time"], 0)

    def test_upload_failure_marks_job_failed_without_starting_print(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.3mf"
            source.write_text("3mf", encoding="utf-8")
            queue = self.make_queue(tmp_path / "queue")
            queue.printer = FakePrinter(send_file_result=False)
            failed_jobs = []

            def on_fail(job):
                failed_jobs.append(job)
                queue._stop_event.set()

            queue.on_job_fail(on_fail)
            queue.add(str(source), name="upload failure")

            queue._process_queue()

            self.assertEqual(queue.status, QueueStatus.IDLE)
            self.assertEqual(queue.list_queue(), [])
            self.assertEqual(len(failed_jobs), 1)
            self.assertEqual(failed_jobs[0].status, "failed")
            self.assertFalse(queue.printer.start_print_called)
            self.assertTrue(queue.printer.disconnected)

            history = queue.get_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["status"], "failed")
            self.assertIn("文件", history[0]["error_message"])

    def test_cancel_current_job_fails_when_printer_stop_fails(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(stop_print_result=False)
            job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )
            queue.current_job = job

            self.assertFalse(queue.cancel("job123"))

            self.assertTrue(queue.printer.stop_print_called)
            self.assertIs(queue.current_job, job)
            self.assertEqual(job.status, "printing")
            self.assertEqual(queue.get_history(), [])

    def test_cancel_current_job_records_history_after_printer_stop(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(stop_print_result=True)
            job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )
            queue.current_job = job

            self.assertTrue(queue.cancel("job123"))

            self.assertTrue(queue.printer.stop_print_called)
            self.assertIsNone(queue.current_job)
            self.assertEqual(job.status, "cancelled")

            history = queue.get_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["status"], "cancelled")

    def test_pause_current_job_fails_when_printer_pause_fails(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(pause_print_result=False)
            queue.status = QueueStatus.PRINTING
            queue.current_job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )

            self.assertFalse(queue.pause())

            self.assertTrue(queue.printer.pause_print_called)
            self.assertEqual(queue.status, QueueStatus.PRINTING)
            self.assertFalse(queue._pause_event.is_set())

    def test_resume_current_job_fails_when_printer_resume_fails(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(resume_print_result=False)
            queue.status = QueueStatus.PAUSED
            queue._pause_event.set()
            queue.current_job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )

            self.assertFalse(queue.resume())

            self.assertTrue(queue.printer.resume_print_called)
            self.assertEqual(queue.status, QueueStatus.PAUSED)
            self.assertTrue(queue._pause_event.is_set())


if __name__ == "__main__":
    unittest.main()
