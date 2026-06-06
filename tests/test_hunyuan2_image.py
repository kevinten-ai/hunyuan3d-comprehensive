import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hunyuan2_image


class Hunyuan2ImageTests(unittest.TestCase):
    def test_resolve_paths_before_changing_working_directory(self):
        image, output, model = hunyuan2_image.resolve_cli_paths(
            "Hunyuan3D-2/assets/demo.png",
            "outputs/validation",
            "Hunyuan3D-2/tencent/Hunyuan3D-2",
        )

        self.assertTrue(image.is_absolute())
        self.assertTrue(output.is_absolute())
        self.assertTrue(Path(model).is_absolute())
        self.assertTrue(str(image).endswith(str(Path("Hunyuan3D-2") / "assets" / "demo.png")))
        self.assertTrue(str(output).endswith(str(Path("outputs") / "validation")))
        self.assertTrue(str(model).endswith(str(Path("Hunyuan3D-2") / "tencent" / "Hunyuan3D-2")))

    def test_model_path_defaults_to_environment_variable(self):
        with patch.dict(hunyuan2_image.os.environ, {"HUNYUAN3D2_MODEL_PATH": "custom/model/path"}):
            args = hunyuan2_image.parse_args([
                "--image",
                "Hunyuan3D-2/assets/demo.png",
                "--output",
                "outputs/unit-test",
            ])

        self.assertEqual(args.model_path, "custom/model/path")

    def test_explicit_model_path_overrides_environment_variable(self):
        with patch.dict(hunyuan2_image.os.environ, {"HUNYUAN3D2_MODEL_PATH": "custom/model/path"}):
            args = hunyuan2_image.parse_args([
                "--image",
                "Hunyuan3D-2/assets/demo.png",
                "--output",
                "outputs/unit-test",
                "--model-path",
                "explicit/model/path",
            ])

        self.assertEqual(args.model_path, "explicit/model/path")


if __name__ == "__main__":
    unittest.main()
