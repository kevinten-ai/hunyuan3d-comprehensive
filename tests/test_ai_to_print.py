import sys
import json
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import ai_to_print


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
            source.write_text("ready", encoding="ascii")

            class FakeConverter:
                def __init__(self, output_dir=None):
                    raise AssertionError("ready files should not be converted")

            result = ai_to_print.prepare_ready_to_print_model(
                str(source),
                converter_cls=FakeConverter,
            )

            self.assertEqual(result, str(source))

    def test_prepare_ready_to_print_model_converts_source_model_to_3mf(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")
            converted = Path(tmp) / "converted" / "model_print_ready.3mf"

            class FakeConverter:
                def __init__(self, output_dir=None):
                    self.output_dir = Path(output_dir)

                def to_3mf(self, input_path, output_name=None):
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    self.assert_input = input_path
                    converted.write_text("ready", encoding="ascii")
                    return converted

            result = ai_to_print.prepare_ready_to_print_model(
                str(source),
                output_dir=str(converted.parent),
                converter_cls=FakeConverter,
            )

            self.assertEqual(result, str(converted))

    def test_add_to_print_queue_queues_converted_ready_file(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")
            converted = Path(tmp) / "model_print_ready.3mf"
            converted.write_text("ready", encoding="ascii")

            class FakeQueue:
                def __init__(self):
                    self.added_path = None

                def add(self, path, name=None):
                    self.added_path = path
                    return "job-1"

            queue = FakeQueue()

            with patch.object(
                ai_to_print,
                "prepare_ready_to_print_model",
                return_value=str(converted),
            ) as prepare:
                result = ai_to_print.add_to_print_queue(queue, str(source), "demo")

            self.assertEqual(result, "job-1")
            self.assertEqual(queue.added_path, str(converted))
            prepare.assert_called_once_with(str(source))

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
