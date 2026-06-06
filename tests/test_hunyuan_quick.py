import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hunyuan_quick


class HunyuanQuickTests(unittest.TestCase):
    def test_build_text_command_targets_hunyuan1_main(self):
        command = hunyuan_quick.build_text_command("a small robot", "out/text", lite=True)

        self.assertEqual(command[0], sys.executable)
        self.assertIn(str(Path("Hunyuan3D-1") / "main.py"), command[1])
        self.assertIn("--text_prompt", command)
        self.assertIn("a small robot", command)
        self.assertIn("--save_folder", command)
        self.assertIn("out/text", command)
        self.assertIn("--use_lite", command)

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
        result = hunyuan_quick.text_to_3d("a cup", output_dir=output_dir, lite=True, dry_run=True)

        self.assertEqual(result["mode"], "text")
        self.assertTrue(result["dry_run"])
        self.assertIsNone(result["returncode"])
        self.assertIn("--text_prompt", result["command"])


if __name__ == "__main__":
    unittest.main()
