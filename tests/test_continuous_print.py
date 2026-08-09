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

    def test_text_generation_runs_shared_backend_and_finds_obj(self):
        with TemporaryDirectory() as tmp:
            printer = ContinuousPrinter(
                output_dir=tmp,
                auto_start=False,
                run_generator=True,
            )

            def fake_generate(prompt, output_dir, lite, dry_run):
                Path(output_dir, "mesh_vertex_colors.obj").write_text(
                    "v 0 0 0\n",
                    encoding="ascii",
                )

            with patch(
                "scripts.hunyuan_quick.text_to_3d",
                side_effect=fake_generate,
            ) as generate:
                result = printer.generate_from_text("a rabbit")

            self.assertEqual(Path(result).name, "mesh_vertex_colors.obj")
            generate.assert_called_once()
            self.assertEqual(generate.call_args.args[0], "a rabbit")
            self.assertTrue(Path(generate.call_args.kwargs["output_dir"]).is_absolute())

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

            with patch.dict(
                ai_to_print.os.environ,
                {"BAMBU_SLICER_COMMAND": ""},
            ):
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

    def test_prompts_returns_nonzero_when_generation_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_file = root / "prompts.txt"
            prompt_file.write_text("a rabbit\n", encoding="utf-8")
            argv = ["continuous_print.py", "prompts", "--file", str(prompt_file), "--delay", "0"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 1)

            self.assertFalse((root / ".continuous_prompts.json").exists())

    def test_prompts_returns_nonzero_when_prompt_file_has_no_prompts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_file = root / "prompts.txt"
            prompt_file.write_text("# only comments\n\n", encoding="utf-8")
            argv = ["continuous_print.py", "prompts", "--file", str(prompt_file), "--delay", "0"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 1)

            self.assertFalse((root / ".continuous_prompts.json").exists())

    def test_prompts_returns_nonzero_when_print_requested_without_printer_config(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_file = root / "prompts.txt"
            prompt_file.write_text("a rabbit\n", encoding="utf-8")
            argv = ["continuous_print.py", "prompts", "--file", str(prompt_file), "--delay", "0", "--mock"]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 1)

            self.assertFalse((root / ".continuous_prompts.json").exists())

    def test_prompts_mock_no_print_returns_zero_and_marks_processed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_file = root / "prompts.txt"
            prompt_file.write_text("a rabbit\n", encoding="utf-8")
            argv = [
                "continuous_print.py",
                "prompts",
                "--file",
                str(prompt_file),
                "--delay",
                "0",
                "--mock",
                "--no-print",
            ]

            with patch.object(continuous_print, "PROJECT_ROOT", root), \
                    patch.object(sys, "argv", argv):
                self.assertEqual(continuous_print.main(), 0)

            processed = json.loads((root / ".continuous_prompts.json").read_text())
            self.assertEqual(processed, [0])

    def test_prompts_strip_utf8_bom_from_first_prompt(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_file = root / "prompts.txt"
            prompt_file.write_text("\ufeffa rabbit\n", encoding="utf-8")
            model_file = root / "model.stl"
            model_file.write_text("solid mock\nendsolid mock\n", encoding="ascii")
            prompts = []

            def fake_generate(prompt):
                prompts.append(prompt)
                return str(model_file)

            with patch.object(continuous_print, "PROJECT_ROOT", root):
                printer = ContinuousPrinter(output_dir=tmp, auto_start=False)
                with patch.object(printer, "generate_from_text", side_effect=fake_generate), \
                        patch.object(printer, "repair_model", return_value=str(model_file)):
                    self.assertTrue(printer.run_prompt_list(str(prompt_file), delay=0))

            self.assertEqual(prompts, ["a rabbit"])


if __name__ == "__main__":
    unittest.main()
