import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.local_env import load_project_env


class LocalEnvTests(unittest.TestCase):
    def test_load_project_env_reads_values_without_overriding_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "\n".join([
                    "# local overrides",
                    "HUNYUAN3D1_PYTHON=C:\\tools\\python.exe",
                    "export HUNYUAN3D2_MODEL_PATH=local/model",
                    'BAMBU_SLICER_COMMAND="slicer --input {input} --output {output}"',
                    "MODEL_COLLECTOR_MODELS_DIR=from-env-file",
                ]),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"MODEL_COLLECTOR_MODELS_DIR": "from-shell"}, clear=True):
                loaded = load_project_env(tmp)

                self.assertEqual(os.environ["HUNYUAN3D1_PYTHON"], "C:\\tools\\python.exe")
                self.assertEqual(os.environ["HUNYUAN3D2_MODEL_PATH"], "local/model")
                self.assertEqual(
                    os.environ["BAMBU_SLICER_COMMAND"],
                    "slicer --input {input} --output {output}",
                )
                self.assertEqual(os.environ["MODEL_COLLECTOR_MODELS_DIR"], "from-shell")
                self.assertNotIn("MODEL_COLLECTOR_MODELS_DIR", loaded)

    def test_load_project_env_ignores_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(load_project_env(tmp), {})


if __name__ == "__main__":
    unittest.main()

