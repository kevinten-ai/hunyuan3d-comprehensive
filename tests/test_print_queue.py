import sys
import os
import zipfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bambu_print import PrintQueue, QueueStatus
from bambu_print.print_queue import QueuedJob
from bambu_print.printer_client import PrinterStatus


def write_bambu_project_3mf(path: Path):
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("3D/3dmodel.model", "<model />")
        package.writestr("Metadata/project_settings.config", "{}")
        package.writestr("Metadata/slice_info.config", "<config />")


class FakePrinter:
    def __init__(self, send_file_result: bool = True,
                 start_print_result: bool = True,
                 stop_print_result: bool = True,
                 pause_print_result: bool = True,
                 resume_print_result: bool = True):
        self.send_file_result = send_file_result
        self.start_print_result = start_print_result
        self.stop_print_result = stop_print_result
        self.pause_print_result = pause_print_result
        self.resume_print_result = resume_print_result
        self.start_print_called = False
        self.start_print_call_count = 0
        self.send_file_call_count = 0
        self.stop_print_called = False
        self.pause_print_called = False
        self.resume_print_called = False
        self.disconnected = False
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def is_connected(self):
        return self.connected

    @staticmethod
    def _normalize_remote_name(filename):
        return filename

    def on_status_change(self, _callback):
        return None

    def send_file(self, *_args, **_kwargs):
        self.send_file_call_count += 1
        return self.send_file_result

    def start_print(self, *_args, **_kwargs):
        self.start_print_called = True
        self.start_print_call_count += 1
        return self.start_print_result

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
        self.connected = False
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

    def test_add_rejects_source_model_formats_that_need_conversion(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.stl"
            source.write_text("solid test\nendsolid test\n", encoding="utf-8")
            queue = self.make_queue(tmp_path / "queue")

            with self.assertRaises(ValueError) as context:
                queue.add(str(source))

            self.assertIn("ready-to-print", str(context.exception))
            self.assertIn(".3mf", str(context.exception))

    def test_add_persists_supported_model_job(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.3mf"
            write_bambu_project_3mf(source)
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
            source = tmp_path / "model.3mf"
            write_bambu_project_3mf(source)
            queue = self.make_queue(tmp_path / "queue")

            queue.add(str(source), name="manual start model")

            self.assertEqual(queue.status, QueueStatus.IDLE)
            self.assertIsNone(queue._worker_thread)

    def test_add_rejects_generic_geometry_3mf_without_bambu_metadata(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "geometry.3mf"
            with zipfile.ZipFile(source, "w") as package:
                package.writestr("3D/3dmodel.model", "<model />")
            queue = self.make_queue(tmp_path / "queue")

            with self.assertRaises(ValueError) as context:
                queue.add(str(source), name="generic geometry")

            self.assertIn("Bambu Studio", str(context.exception))
            self.assertIn("sliced", str(context.exception))

    def test_add_accepts_gcode_without_3mf_metadata(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "plate.gcode"
            source.write_text("; gcode", encoding="ascii")
            queue = self.make_queue(tmp_path / "queue")

            job_id = queue.add(str(source), name="gcode plate")

            self.assertTrue(job_id)
            self.assertEqual(queue.list_queue()[0]["filepath"], str(source))

    def test_status_includes_printer_remaining_time(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")

            status = queue.get_status()

            self.assertIn("remaining_time", status["printer"])
            self.assertEqual(status["printer"]["remaining_time"], 0)

    def test_run_foreground_processes_queue_until_empty(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.3mf"
            write_bambu_project_3mf(source)
            queue = self.make_queue(tmp_path / "queue")
            printer = FakePrinter()
            printer.get_status = lambda: PrinterStatus(
                print_status="completed",
                progress=100.0,
                remaining_time=0,
            )
            queue.printer = printer
            queue.add(str(source), name="foreground model")

            self.assertTrue(queue.run_foreground())

            self.assertEqual(queue.list_queue(), [])
            self.assertEqual(queue.status, QueueStatus.IDLE)
            self.assertTrue(printer.start_print_called)
            self.assertTrue(printer.disconnected)

    def test_external_worker_pause_updates_device_and_runtime(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            printer = FakePrinter()
            printer.get_status = lambda: SimpleNamespace(print_status="printing")
            queue.printer = printer
            queue._update_runtime(
                worker_pid=os.getpid() + 1000,
                current_job_id="job123",
                desired_state="running",
            )

            with patch.object(queue, "_pid_is_running", return_value=True):
                self.assertTrue(queue.pause())

            self.assertTrue(printer.pause_print_called)
            self.assertTrue(printer.disconnected)
            self.assertEqual(queue._read_runtime()["desired_state"], "paused")

    def test_external_worker_resume_and_stop_control_device(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            printer = FakePrinter()
            queue.printer = printer
            queue._update_runtime(
                worker_pid=os.getpid() + 1000,
                current_job_id="job123",
                desired_state="paused",
            )

            with patch.object(queue, "_pid_is_running", return_value=True):
                printer.get_status = lambda: SimpleNamespace(print_status="paused")
                self.assertTrue(queue.resume())
                printer.get_status = lambda: SimpleNamespace(print_status="printing")
                self.assertTrue(queue.stop())

            self.assertTrue(printer.resume_print_called)
            self.assertTrue(printer.stop_print_called)
            self.assertEqual(queue._read_runtime()["desired_state"], "stopped")

    def test_foreground_restart_adopts_matching_active_print(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.3mf"
            write_bambu_project_3mf(source)
            queue = self.make_queue(tmp_path / "queue")
            printer = FakePrinter()
            statuses = iter([
                PrinterStatus(print_status="printing", model_info="model.3mf"),
                PrinterStatus(print_status="completed", progress=100.0),
            ])
            printer.get_status = lambda: next(statuses)
            queue.printer = printer
            queue.add(str(source), name="recoverable model")
            queue.queue[0].status = "printing"
            queue._save_queue()

            self.assertTrue(queue.run_foreground())

            self.assertEqual(printer.send_file_call_count, 0)
            self.assertEqual(printer.start_print_call_count, 0)
            self.assertEqual(queue.get_history()[0]["status"], "completed")

    def test_upload_failure_marks_job_failed_without_starting_print(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.3mf"
            write_bambu_project_3mf(source)
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

    def test_start_print_failure_marks_job_failed_without_monitoring(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "model.3mf"
            write_bambu_project_3mf(source)

            queue = self.make_queue(tmp_path / "queue")
            queue.printer = FakePrinter(start_print_result=False)
            failed_jobs = []

            def on_fail(job):
                failed_jobs.append(job)
                queue._stop_event.set()

            queue.on_job_fail(on_fail)

            queue.add(str(source), name="start failure")

            queue._process_queue()

            self.assertEqual(queue.status, QueueStatus.IDLE)
            self.assertEqual(queue.list_queue(), [])
            self.assertEqual(len(failed_jobs), 1)
            self.assertEqual(failed_jobs[0].status, "failed")
            self.assertTrue(queue.printer.start_print_called)
            self.assertTrue(queue.printer.disconnected)

            history = queue.get_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["status"], "failed")
            self.assertIn("打印命令", history[0]["error_message"])

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

    def test_resume_active_job_returns_to_printing_without_restarting_it(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter()
            queue.status = QueueStatus.PAUSED
            queue._pause_event.set()
            queue.current_job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )

            self.assertTrue(queue.resume())

            self.assertTrue(queue.printer.resume_print_called)
            self.assertEqual(queue.status, QueueStatus.PRINTING)
            self.assertFalse(queue._pause_event.is_set())
            self.assertEqual(queue.printer.start_print_call_count, 0)
            self.assertEqual(queue.printer.send_file_call_count, 0)

    def test_stop_current_job_fails_when_printer_stop_fails(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(stop_print_result=False)
            queue.status = QueueStatus.PRINTING
            queue.current_job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )

            self.assertFalse(queue.stop())

            self.assertTrue(queue.printer.stop_print_called)
            self.assertEqual(queue.status, QueueStatus.PRINTING)
            self.assertFalse(queue._stop_event.is_set())

    def test_stop_current_job_succeeds_after_printer_stop(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(stop_print_result=True)
            queue.status = QueueStatus.PRINTING
            queue.current_job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )

            self.assertTrue(queue.stop())

            self.assertTrue(queue.printer.stop_print_called)
            self.assertEqual(queue.status, QueueStatus.STOPPED)
            self.assertTrue(queue._stop_event.is_set())
            self.assertIsNone(queue.current_job)
            self.assertEqual(queue.get_history()[0]["status"], "cancelled")

    def test_clear_does_not_clear_when_stop_fails(self):
        with TemporaryDirectory() as tmp:
            queue = self.make_queue(Path(tmp) / "queue")
            queue.printer = FakePrinter(stop_print_result=False)
            queue.status = QueueStatus.PRINTING
            queue.current_job = QueuedJob(
                id="job123",
                filepath="model.3mf",
                name="active print",
                status="printing",
            )
            queued_job = QueuedJob(
                id="job456",
                filepath="queued.3mf",
                name="queued print",
                status="queued",
            )
            queue.queue.append(queued_job)

            self.assertFalse(queue.clear())

            self.assertTrue(queue.printer.stop_print_called)
            self.assertEqual(queue.status, QueueStatus.PRINTING)
            self.assertEqual(queue.queue, [queued_job])


if __name__ == "__main__":
    unittest.main()
