import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.bambu_slicer_bridge import (
    PROJECT_SETTINGS_PATH,
    calculate_scale,
    merge_project_settings,
    read_project_settings,
)


class BambuSlicerBridgeTests(unittest.TestCase):
    def _settings(self):
        return {
            "printer_model": "Bambu Lab P1S",
            "nozzle_diameter": ["0.4"],
            "layer_height": "0.2",
            "filament_type": ["PLA"],
        }

    def test_read_project_settings_accepts_json_and_3mf(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.dumps(self._settings()).encode()
            json_path = root / "settings.json"
            json_path.write_bytes(payload)
            project = root / "template.3mf"
            with ZipFile(project, "w") as archive:
                archive.writestr(PROJECT_SETTINGS_PATH, payload)

            self.assertEqual(json.loads(read_project_settings(json_path)), self._settings())
            self.assertEqual(json.loads(read_project_settings(project)), self._settings())

    def test_merge_project_settings_preserves_geometry(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "geometry.3mf"
            target = root / "merged.3mf"
            with ZipFile(source, "w") as archive:
                archive.writestr("3D/3dmodel.model", b"geometry")
                archive.writestr(PROJECT_SETTINGS_PATH, b"old")

            merge_project_settings(source, b"new", target)

            with ZipFile(target) as archive:
                self.assertEqual(archive.read("3D/3dmodel.model"), b"geometry")
                self.assertEqual(archive.read(PROJECT_SETTINGS_PATH), b"new")

    def test_calculate_scale_targets_largest_extent(self):
        with TemporaryDirectory() as tmp:
            import trimesh

            path = Path(tmp) / "box.stl"
            trimesh.creation.box(extents=(2, 4, 5)).export(path)

            self.assertAlmostEqual(calculate_scale(path, 50), 10.0)

    def test_calculate_scale_rejects_empty_mesh(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.stl"
            path.write_text("solid empty\nendsolid empty\n", encoding="ascii")

            with self.assertRaisesRegex(ValueError, "model bounds"):
                calculate_scale(path, 50)


if __name__ == "__main__":
    unittest.main()
