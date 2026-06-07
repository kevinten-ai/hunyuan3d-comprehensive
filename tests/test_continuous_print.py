import sys
import json
import zipfile
import subprocess
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import ai_to_print, continuous_print
from scripts.continuous_print import ContinuousPrinter


def write_bambu_project_3mf(path: Path):
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("3D/3dmodel.model", "<model />")
        package.writestr("Metadata/project_settings.config", "{}")
        package.writestr("Metadata/slice_info.config", "<config />")


class ContinuousPrintTests(unittest.TestCase):
    def test_help_examples_use_supported_generate_arguments(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "continuous_print.py"), "--help"],
            cwd=str(Path(__file__).resolve().parents[1]),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generate --prompt", result.stdout)
        self.assertIn("--mock", result.stdout)
        self.assertNotIn('generate "一只可爱的兔子"', result.stdout)

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

    def test_add_to_print_queue_rejects_source_model_before_queueing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")

            class FakeQueue:
                def __init__(self):
                    self.added_path = None

                def add(self, path, name=None):
                    self.added_path = path
                    return "job-1"

            with patch.object(continuous_print, "PROJECT_ROOT", root):
                printer = ContinuousPrinter(output_dir=tmp, auto_start=False)
            printer.print_queue = FakeQueue()

            result = printer.add_to_print_queue(str(source), name="demo")

            self.assertIsNone(result)
            self.assertIsNone(printer.print_queue.added_path)

    def test_add_to_print_queue_uses_configured_external_slicer(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")
            commands = []

            class FakeQueue:
                def __init__(self):
                    self.added_path = None

                def add(self, path, name=None):
                    self.added_path = path
                    return "job-1"

            def fake_run(command, **kwargs):
                commands.append((command, kwargs))
                output = Path(command.rsplit(" ", 1)[-1])
                write_bambu_project_3mf(output)
                return subprocess.CompletedProcess(command, 0)

            with patch.object(continuous_print, "PROJECT_ROOT", root):
                printer = ContinuousPrinter(output_dir=tmp, auto_start=False)
            printer.print_queue = FakeQueue()

            with patch.dict(ai_to_print.os.environ, {"BAMBU_SLICER_COMMAND": "fake-slicer {input} {output}"}), \
                    patch.object(ai_to_print.subprocess, "run", side_effect=fake_run):
                result = printer.add_to_print_queue(str(source), name="demo")

            self.assertEqual(result, "job-1")
            self.assertTrue(commands)
            self.assertIn(str(source), commands[0][0])
            self.assertEqual(commands[0][1]["shell"], True)
            self.assertTrue(str(printer.print_queue.added_path).endswith("_sliced.3mf"))

    def test_main_returns_nonzero_without_prompt_or_image(self):
        stdout = StringIO()

        with patch.object(sys, "argv", ["continuous_print.py", "generate"]), \
                patch("sys.stdout", new=stdout):
            self.assertEqual(continuous_print.main(), 1)

        self.assertIn("请提供", stdout.getvalue())

    def test_main_status_returns_json_without_printer_config(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = StringIO()

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", ["continuous_print.py", "status"]), \
                    patch("sys.stdout", new=stdout):
                self.assertEqual(continuous_print.main(), 0)

            status = json.loads(stdout.getvalue())
            self.assertFalse(status["is_running"])
            self.assertFalse(status["printer_connected"])

    def test_main_returns_nonzero_when_generation_does_not_produce_model(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = StringIO()
            argv = ["continuous_print.py", "generate", "--prompt", "a rabbit", "--no-print"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv), \
                    patch("sys.stdout", new=stdout):
                self.assertEqual(continuous_print.main(), 1)

        self.assertIn("未生成模型", stdout.getvalue())

    def test_main_returns_zero_for_mock_no_print_flow(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            argv = ["continuous_print.py", "generate", "--prompt", "a rabbit", "--no-print", "--mock"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 0)

    def test_main_returns_nonzero_when_print_requested_without_printer_config(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            argv = ["continuous_print.py", "generate", "--prompt", "a rabbit", "--mock"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 1)

    def test_prompts_returns_nonzero_when_prompt_file_is_missing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_file = root / "missing-prompts.txt"
            argv = ["continuous_print.py", "prompts", "--file", str(missing_file), "--delay", "0"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 1)


if __name__ == "__main__":
    unittest.main()
