import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prepare_comfyui_workflow_assets import (
    link_or_copy,
    prepare_assets,
    prepare_input_images,
    validate_size,
)


class PrepareComfyUIWorkflowAssetsTests(unittest.TestCase):
    def test_link_or_copy_materializes_target(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.bin"
            target = root / "nested" / "target.bin"
            source.write_bytes(b"model")

            action = link_or_copy(source, target)

            self.assertIn(action, {"linked", "copied"})
            self.assertEqual(target.read_bytes(), b"model")
            self.assertEqual(link_or_copy(source, target), "exists")

    def test_validate_size_rejects_incomplete_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.bin"
            path.write_bytes(b"short")

            with self.assertRaisesRegex(ValueError, "unexpected size"):
                validate_size(path, 100, "checkpoint")

    def test_prepare_input_images_uses_bundled_examples(self):
        with TemporaryDirectory() as tmp:
            from PIL import Image

            root = Path(tmp)
            comfyui = root / "ComfyUI"
            hunyuan2 = root / "Hunyuan3D-2"
            assets = hunyuan2 / "assets"
            mv = assets / "example_mv_images" / "1"
            mv.mkdir(parents=True)
            for name in ("front.png", "back.png", "left.png"):
                Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(mv / name)
            Image.new("RGBA", (2, 2), (0, 255, 0, 255)).save(assets / "demo.png")

            prepare_input_images(comfyui, hunyuan2)

            self.assertTrue((comfyui / "input" / "pasted" / "image (734).png").is_file())
            self.assertTrue((comfyui / "input" / "pasted" / "image (735).png").is_file())
            self.assertTrue((comfyui / "input" / "pasted" / "image (736).png").is_file())
            jpeg = comfyui / "input" / "s-l1600 - 2022-02-25T095119.012.jpg"
            self.assertTrue(jpeg.is_file())
            with Image.open(jpeg) as image:
                self.assertEqual(image.format, "JPEG")

    def test_prepare_assets_reuses_local_normal_model(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            comfyui = root / "ComfyUI"
            hunyuan2 = root / "Hunyuan3D-2"
            comfyui.mkdir()
            (comfyui / "main.py").write_text("", encoding="utf-8")
            source = root / "normal.safetensors"
            source.write_bytes(b"model")

            with (
                patch(
                    "scripts.prepare_comfyui_workflow_assets.find_normal_model",
                    return_value=source,
                ),
                patch("scripts.prepare_comfyui_workflow_assets.validate_size"),
                patch(
                    "scripts.prepare_comfyui_workflow_assets.download_required_models",
                    return_value=[],
                ),
                patch(
                    "scripts.prepare_comfyui_workflow_assets.prepare_input_images",
                    return_value=[],
                ),
            ):
                actions = prepare_assets(comfyui, hunyuan2, offline=True)

            target = (
                comfyui
                / "models"
                / "diffusion_models"
                / "hy3dgen"
                / "hunyuan3d-dit-v2-0-fp16.safetensors"
            )
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), b"model")
            self.assertEqual(len(actions), 1)


if __name__ == "__main__":
    unittest.main()
