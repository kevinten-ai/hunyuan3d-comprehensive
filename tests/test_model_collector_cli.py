import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "model_collector.py"


class ModelCollectorCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        with TemporaryDirectory() as tmp:
            env = {
                **os.environ,
                "MODEL_COLLECTOR_MODELS_DIR": str(Path(tmp) / "models"),
            }
            return subprocess.run(
                [sys.executable, str(SCRIPT), *args],
                cwd=str(PROJECT_ROOT),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_unknown_command_returns_nonzero(self):
        result = self.run_cli("unknown")

        self.assertEqual(result.returncode, 1)
        self.assertIn("未知命令", result.stdout)

    def test_add_without_path_returns_nonzero(self):
        result = self.run_cli("add")

        self.assertEqual(result.returncode, 1)
        self.assertIn("请提供文件路径", result.stdout)

    def test_export_missing_model_returns_nonzero_without_traceback(self):
        result = self.run_cli("export", "definitely-missing-model")

        self.assertEqual(result.returncode, 1)
        self.assertIn("未找到模型", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
