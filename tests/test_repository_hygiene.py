import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class RepositoryHygieneTests(unittest.TestCase):
    def test_local_runtime_and_model_artifacts_are_ignored(self):
        ignored_paths = [
            ".env",
            "config/printer.json",
            ".3d_print_queue/jobs.json",
            "ComfyUI/models/diffusion_models/hy3dgen/model.safetensors",
            "models/checkpoints/pytorch_model.bin",
            "models/checkpoints/model.onnx",
            "outputs/validation/hunyuan2_image/validation.glb",
            "models/converted/validation.3mf",
        ]

        for path in ignored_paths:
            with self.subTest(path=path):
                result = git("check-ignore", "-q", path)

                self.assertEqual(result.returncode, 0, result.stderr)

    def test_tracked_templates_are_not_ignored(self):
        for path in ["config/env.example", "config/printer.json.example"]:
            with self.subTest(path=path):
                result = git("check-ignore", "-q", path)

                self.assertEqual(result.returncode, 1, result.stderr)

    def test_no_tracked_file_exceeds_model_weight_threshold(self):
        result = git("ls-files")
        self.assertEqual(result.returncode, 0, result.stderr)

        too_large = []
        for relative_path in result.stdout.splitlines():
            path = PROJECT_ROOT / relative_path
            if path.is_file() and path.stat().st_size > 100_000_000:
                too_large.append(relative_path)

        self.assertEqual(too_large, [])


if __name__ == "__main__":
    unittest.main()
