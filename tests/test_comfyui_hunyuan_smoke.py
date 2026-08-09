import os
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.comfyui_hunyuan_smoke import build_prompt, find_generated_glb


class ComfyUIHunyuanSmokeTests(unittest.TestCase):
    def test_build_prompt_uses_low_cost_parameters(self):
        prompt = build_prompt(
            input_name="demo.png",
            steps=7,
            octree_resolution=192,
            num_chunks=1234,
            max_faces=4321,
            seed=987,
            output_prefix="validation/test",
        )

        self.assertEqual(prompt["13"]["inputs"]["image"], "demo.png")
        self.assertEqual(prompt["141"]["inputs"]["steps"], 7)
        self.assertEqual(prompt["140"]["inputs"]["octree_resolution"], 192)
        self.assertEqual(prompt["140"]["inputs"]["num_chunks"], 1234)
        self.assertEqual(prompt["59"]["inputs"]["max_facenum"], 4321)
        self.assertEqual(prompt["141"]["inputs"]["seed"], 987)
        self.assertEqual(prompt["17"]["inputs"]["filename_prefix"], "validation/test")

    def test_find_generated_glb_ignores_older_outputs(self):
        with TemporaryDirectory() as tmp:
            comfyui = Path(tmp)
            output = comfyui / "output" / "validation"
            output.mkdir(parents=True)
            old = output / "smoke_00001_.glb"
            new = output / "smoke_00002_.glb"
            old.write_bytes(b"old")
            old_time = time.time() - 10
            os.utime(old, (old_time, old_time))
            started_at = time.time() - 1
            new.write_bytes(b"new")

            result = find_generated_glb(comfyui, "validation/smoke", started_at)

            self.assertEqual(result, new)


if __name__ == "__main__":
    unittest.main()
