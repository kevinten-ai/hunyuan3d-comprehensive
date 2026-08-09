import sys
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hunyuan_quick


class HunyuanQuickTests(unittest.TestCase):
    def test_build_text_command_targets_hunyuan1_main(self):
        with patch.dict(hunyuan_quick.os.environ, {"HUNYUAN3D1_PYTHON": "custom-python"}):
            command = hunyuan_quick.build_text_command(
                "a small robot",
                "out/text",
                lite=True,
                backend="native",
            )

        self.assertEqual(command[0], "custom-python")
        self.assertIn(str(Path("Hunyuan3D-1") / "main.py"), command[1])
        self.assertIn("--text_prompt", command)
        self.assertIn("a small robot", command)
        self.assertIn("--save_folder", command)
        self.assertIn("out/text", command)
        self.assertIn("--use_lite", command)

    def test_hunyuan1_python_prefers_project_venv_when_present(self):
        command = hunyuan_quick.build_text_command(
            "a small robot",
            "out/text",
            backend="native",
        )
        venv_python = hunyuan_quick.PROJECT_ROOT / "Hunyuan3D-1" / "venv" / "Scripts" / "python.exe"
        expected = str(venv_python) if venv_python.exists() else sys.executable

        self.assertEqual(command[0], expected)

    def test_auto_text_backend_prefers_docker_over_legacy_native_setting(self):
        with patch.dict(
            hunyuan_quick.os.environ,
            {"HUNYUAN3D1_PYTHON": "custom-python", "HUNYUAN3D1_BACKEND": "auto"},
            clear=False,
        ), patch.object(hunyuan_quick.shutil, "which", return_value="docker"):
            self.assertEqual(hunyuan_quick.resolve_text_backend(), "docker")

    def test_build_text_command_uses_low_vram_docker_pipeline(self):
        with TemporaryDirectory() as tmp:
            command = hunyuan_quick.build_text_command(
                "a small robot",
                tmp,
                backend="docker",
            )

        self.assertEqual(command[:4], ["docker", "compose", "run", "--rm"])
        self.assertIn("--volume", command)
        self.assertIn(f"{Path(tmp).resolve()}:/output", command)
        self.assertIn("scripts/text_to_3d_low_vram.py", command)
        self.assertIn("a small robot", command)
        self.assertIn("/output", command)

    def test_auto_text_backend_uses_docker_when_available(self):
        with patch.dict(
            hunyuan_quick.os.environ,
            {"HUNYUAN3D1_BACKEND": "auto", "HUNYUAN3D1_PYTHON": ""},
            clear=False,
        ), patch.object(hunyuan_quick.shutil, "which", return_value="docker"):
            self.assertEqual(hunyuan_quick.resolve_text_backend(), "docker")

    def test_invalid_text_backend_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "HUNYUAN3D1_BACKEND"):
            hunyuan_quick.resolve_text_backend("remote")

    def test_build_image_command_targets_project_hunyuan2_cli(self):
        command = hunyuan_quick.build_image_command("input.png", "out/image", quality="lite")

        self.assertEqual(command[0], sys.executable)
        self.assertIn(str(Path("scripts") / "hunyuan2_image.py"), command[1])
        self.assertIn("--image", command)
        self.assertIn("input.png", command)
        self.assertIn("--output", command)
        self.assertIn("out/image", command)
        self.assertIn("--low-vram", command)

    def test_dry_run_returns_command_without_running_process(self):
        output_dir = str(Path("outputs") / "unit-test-dry-run")
        result = hunyuan_quick.text_to_3d(
            "a cup",
            output_dir=output_dir,
            lite=True,
            dry_run=True,
            backend="native",
        )

        self.assertEqual(result["mode"], "text")
        self.assertTrue(result["dry_run"])
        self.assertIsNone(result["returncode"])
        self.assertIn("--text_prompt", result["command"])
        self.assertEqual(result["backend"], "native")

    def test_main_returns_nonzero_without_traceback_when_generation_fails(self):
        stdout = StringIO()

        with patch.object(sys, "argv", ["hunyuan_quick.py", "text", "a cup"]), \
                patch.object(hunyuan_quick, "text_to_3d", side_effect=RuntimeError("backend failed")), \
                patch("sys.stdout", new=stdout):
            self.assertEqual(hunyuan_quick.main(), 1)

        output = stdout.getvalue()
        self.assertIn("错误", output)
        self.assertNotIn("Traceback", output)

    def test_batch_missing_folder_returns_nonzero(self):
        stdout = StringIO()

        with patch("sys.stdout", new=stdout):
            self.assertEqual(hunyuan_quick.batch_generate_from_folder("definitely-missing-folder"), 1)

        self.assertIn("文件夹不存在", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
