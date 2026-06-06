import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
