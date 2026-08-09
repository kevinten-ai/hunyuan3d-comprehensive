import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "Hunyuan3D-1" / "scripts" / "text_to_3d_low_vram.py"
SPEC = importlib.util.spec_from_file_location("hunyuan1_low_vram", SCRIPT_PATH)
LOW_VRAM = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(LOW_VRAM)


class Hunyuan1DockerTests(unittest.TestCase):
    def test_low_vram_pipeline_uses_isolated_lite_stages(self):
        args = LOW_VRAM.parse_args(
            [
                "a small robot",
                "--output",
                "outputs/test-low-vram",
                "--t2i-steps",
                "1",
                "--gen-steps",
                "2",
                "--max-faces",
                "1000",
            ]
        )

        commands = LOW_VRAM.build_stage_commands(args, python_executable="python")

        self.assertEqual([stage for stage, _ in commands], list(LOW_VRAM.STAGES))
        self.assertIn("infer/text_to_image.py", commands[0][1])
        self.assertIn("infer/image_to_views.py", commands[2][1])
        self.assertIn("true", commands[2][1])
        self.assertIn("infer/views_to_mesh.py", commands[3][1])
        self.assertIn("1000", commands[3][1])
        self.assertIn("false", commands[3][1])

    def test_docker_runtime_pins_blackwell_native_dependencies(self):
        dockerfile = (PROJECT_ROOT / "Hunyuan3D-1" / "Dockerfile").read_text(encoding="utf-8")
        requirements = (
            PROJECT_ROOT / "Hunyuan3D-1" / "requirements-core.txt"
        ).read_text(encoding="utf-8")
        compose = (PROJECT_ROOT / "Hunyuan3D-1" / "docker-compose.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("nvidia/cuda:13.0.2-runtime-ubuntu24.04", dockerfile)
        self.assertIn("xformers==0.0.35", dockerfile)
        self.assertIn("253ac4fcea7de5f396371124af597e6cc957bfae", dockerfile)
        self.assertNotIn("facebookresearch/pytorch3d", dockerfile)
        self.assertIn("fast-simplification==0.1.13", requirements)
        self.assertIn("./weights/rembg:/root/.u2net", compose)

        mesh_source = (
            PROJECT_ROOT / "Hunyuan3D-1" / "svrm" / "ldm" / "models" / "svrm.py"
        ).read_text(encoding="utf-8")
        self.assertIn("simplification_target = target_face_count", mesh_source)
        self.assertNotIn("target_face_count // 2", mesh_source)


if __name__ == "__main__":
    unittest.main()
