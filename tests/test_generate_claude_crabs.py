import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import generate_claude_crabs


class GenerateClaudeCrabsTests(unittest.TestCase):
    def test_build_crab_command_uses_hunyuan1_save_folder(self):
        command = generate_claude_crabs.build_crab_command("a small crab", "outputs/crab")

        self.assertEqual(command[0], sys.executable)
        self.assertIn(str(Path("Hunyuan3D-1") / "main.py"), command[1])
        self.assertIn("--text_prompt", command)
        self.assertIn("a small crab", command)
        self.assertIn("--save_folder", command)
        self.assertIn("outputs/crab", command)
        self.assertNotIn("--output_dir", command)
        self.assertIn("--use_lite", command)
        self.assertIn("--save_memory", command)


if __name__ == "__main__":
    unittest.main()
