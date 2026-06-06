import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_comfyui_workflow_assets import check_workflow_assets, summarize


class CheckComfyUIWorkflowAssetsTests(unittest.TestCase):
    def test_reports_required_and_downloadable_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            comfyui = root / "ComfyUI"
            workflow = root / "workflow.json"
            (comfyui / "models" / "diffusion_models" / "hy3dgen").mkdir(parents=True)
            (comfyui / "models" / "diffusion_models" / "hy3dgen" / "shape.safetensors").write_bytes(b"ok")
            (comfyui / "input").mkdir(parents=True)
            (comfyui / "input" / "input.png").write_bytes(b"ok")

            workflow.write_text(
                json.dumps(
                    {
                        "nodes": [
                            {
                                "id": 1,
                                "type": "Hy3DModelLoader",
                                "widgets_values": ["hy3dgen\\shape.safetensors"],
                            },
                            {"id": 2, "type": "LoadImage", "widgets_values": ["input.png", "image"]},
                            {
                                "id": 3,
                                "type": "UpscaleModelLoader",
                                "widgets_values": ["missing-upscale.pth"],
                            },
                            {
                                "id": 4,
                                "type": "DownloadAndLoadHy3DPaintModel",
                                "widgets_values": ["hunyuan3d-paint-v2-0"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            checks = check_workflow_assets(workflow, comfyui_dir=comfyui)
            summary = summarize(checks)

            self.assertEqual(summary["total"], 4)
            self.assertEqual(summary["required_missing"], 1)
            self.assertEqual(summary["optional_missing"], 1)
            self.assertEqual(summary["unique_required_missing"], 1)
            self.assertEqual(summary["unique_optional_missing"], 1)
            self.assertFalse(summary["ready"])

            missing_required = [row for row in checks if row.required and not row.exists]
            self.assertEqual(missing_required[0].asset, "missing-upscale.pth")

    def test_missing_hy3d_model_notes_checkpoint_candidates(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            comfyui = root / "ComfyUI"
            workflow = root / "workflow.json"
            checkpoints = comfyui / "models" / "checkpoints"
            checkpoints.mkdir(parents=True)
            (checkpoints / "hunyuan3d-dit-v2.safetensors").write_bytes(b"ok")
            workflow.write_text(
                json.dumps(
                    {
                        "nodes": [
                            {
                                "id": 1,
                                "type": "Hy3DModelLoader",
                                "widgets_values": ["hy3dgen\\hunyuan3d-dit-v2-0-fp16.safetensors"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            checks = check_workflow_assets(workflow, comfyui_dir=comfyui)

            self.assertIn("Candidate checkpoint", checks[0].note)


if __name__ == "__main__":
    unittest.main()
