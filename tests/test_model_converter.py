import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_converter import ModelConverter


class ModelConverterTests(unittest.TestCase):
    def test_get_info_handles_glb_scene(self):
        import trimesh

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scene = trimesh.Scene()
            scene.add_geometry(trimesh.creation.box(extents=(1, 1, 1)))
            scene.add_geometry(trimesh.creation.icosphere(subdivisions=1, radius=0.5))
            source = tmp_path / "scene.glb"
            scene.export(str(source))

            info = ModelConverter(output_dir=str(tmp_path / "converted")).get_info(str(source))

            self.assertEqual(info["file"], "scene.glb")
            self.assertGreater(info["vertices"], 0)
            self.assertGreater(info["faces"], 0)
            self.assertIsInstance(info["is_watertight"], bool)


if __name__ == "__main__":
    unittest.main()
