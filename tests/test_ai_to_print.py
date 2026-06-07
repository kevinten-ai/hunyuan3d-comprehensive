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

from scripts import ai_to_print


def write_bambu_project_3mf(path: Path):
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("3D/3dmodel.model", "<model />")
        package.writestr("Metadata/project_settings.config", "{}")
        package.writestr("Metadata/slice_info.config", "<config />")


class AiToPrintTests(unittest.TestCase):
    def test_text_generation_requires_mock_mode_for_placeholder(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_text_to_3d("a rabbit", output_dir=tmp, mock=False)

            self.assertIsNone(result)

    def test_text_generation_mock_mode_returns_expected_path(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_text_to_3d("a rabbit", output_dir=tmp, mock=True)

            self.assertTrue(result.endswith("model.stl"))
            self.assertTrue(Path(result).exists())

    def test_image_generation_requires_mock_mode_for_placeholder(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_image_to_3d("input.png", output_dir=tmp, mock=False)

            self.assertIsNone(result)

    def test_image_generation_mock_mode_returns_expected_path(self):
        with TemporaryDirectory() as tmp:
            result = ai_to_print.generate_image_to_3d("input.png", output_dir=tmp, mock=True)

            self.assertTrue(result.endswith("model.stl"))
            self.assertTrue(Path(result).exists())

    def test_repair_model_returns_existing_path(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text(
                "solid mock\n"
                "  facet normal 0 0 1\n"
                "    outer loop\n"
                "      vertex 0 0 0\n"
                "      vertex 1 0 0\n"
                "      vertex 0 1 0\n"
                "    endloop\n"
                "  endfacet\n"
                "endsolid mock\n",
                encoding="ascii",
            )

            result = ai_to_print.repair_model(str(source))

            self.assertTrue(Path(result).exists())

    def test_prepare_ready_to_print_model_keeps_ready_file(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.3mf"
            write_bambu_project_3mf(source)

            class FakeConverter:
                def __init__(self, output_dir=None):
                    raise AssertionError("ready files should not be converted")

            result = ai_to_print.prepare_ready_to_print_model(
                str(source),
                converter_cls=FakeConverter,
            )

            self.assertEqual(result, str(source))

    def test_prepare_ready_to_print_model_rejects_generic_3mf(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "geometry.3mf"
            with zipfile.ZipFile(source, "w") as package:
                package.writestr("3D/3dmodel.model", "<model />")

            with self.assertRaises(ValueError) as context:
                ai_to_print.prepare_ready_to_print_model(str(source))

            self.assertIn("Bambu", str(context.exception))
            self.assertIn("切片", str(context.exception))

    def test_prepare_ready_to_print_model_rejects_source_model_without_slicing(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")

            with self.assertRaises(ValueError) as context:
                ai_to_print.prepare_ready_to_print_model(str(source))

            self.assertIn("源模型", str(context.exception))
            self.assertIn("OrcaSlicer", str(context.exception))

    def test_prepare_ready_to_print_model_runs_configured_slicer_command(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "model.stl"
            output_dir = root / "sliced"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")
            commands = []

            def fake_runner(command, **kwargs):
                commands.append((command, kwargs))
                output = Path(command.rsplit(" ", 1)[-1])
                write_bambu_project_3mf(output)
                return subprocess.CompletedProcess(command, 0)

            result = ai_to_print.prepare_ready_to_print_model(
                str(source),
                output_dir=str(output_dir),
                slicer_command="fake-slicer {input} {output}",
                runner=fake_runner,
            )

            self.assertEqual(Path(result).suffix, ".3mf")
            self.assertIn("model_sliced.3mf", result)
            self.assertIn(str(source), commands[0][0])
            self.assertEqual(commands[0][1]["shell"], True)

    def test_prepare_ready_to_print_model_reports_slicer_command_failure(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")

            def fake_runner(command, **kwargs):
                return subprocess.CompletedProcess(command, 2)

            with self.assertRaises(RuntimeError) as context:
                ai_to_print.prepare_ready_to_print_model(
                    str(source),
                    slicer_command="fake-slicer {input} {output}",
                    runner=fake_runner,
                )

            self.assertIn("切片命令失败", str(context.exception))

    def test_add_to_print_queue_rejects_source_model_before_queueing(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")

            class FakeQueue:
                def __init__(self):
                    self.added_path = None

                def add(self, path, name=None):
                    self.added_path = path
                    return "job-1"

            queue = FakeQueue()

            result = ai_to_print.add_to_print_queue(queue, str(source), "demo")

            self.assertIsNone(result)
            self.assertIsNone(queue.added_path)

    def test_setup_printer_rejects_template_config(self):
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

            with patch.object(ai_to_print, "PROJECT_ROOT", root), \
                    patch.object(ai_to_print, "PrintQueue") as print_queue:
                result = ai_to_print.setup_printer()

            self.assertIsNone(result)
            print_queue.assert_not_called()

    def test_main_returns_nonzero_when_generation_does_not_produce_model(self):
        stdout = StringIO()

        with patch.object(sys, "argv", ["ai_to_print.py", "text", "a rabbit", "--no-print"]), \
                patch("sys.stdout", new=stdout):
            self.assertEqual(ai_to_print.main(), 1)

        self.assertIn("流程停止", stdout.getvalue())

    def test_main_returns_zero_for_mock_no_print_flow(self):
        with TemporaryDirectory() as tmp:
            stdout = StringIO()
            argv = ["ai_to_print.py", "text", "a rabbit", "--output", tmp, "--mock", "--no-print"]

            with patch.object(sys, "argv", argv), patch("sys.stdout", new=stdout):
                self.assertEqual(ai_to_print.main(), 0)

            self.assertIn("[OK]", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
