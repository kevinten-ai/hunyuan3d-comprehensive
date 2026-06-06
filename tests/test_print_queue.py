import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bambu_print import PrintQueue, QueueStatus


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


if __name__ == "__main__":
    unittest.main()
