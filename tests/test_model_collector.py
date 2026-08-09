import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_collector import ModelCollector


class ModelCollectorTests(unittest.TestCase):
    def test_add_and_export_use_configurable_model_directory(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.stl"
            source.write_text(
                "solid mock\n"
                "  facet normal 0 0 1\n"
                "    outer loop\n"
                "      vertex 0 0 0\n"
                "      vertex 1 0 0\n"
                "      vertex 0 1 0\n"
                "    endloop\n"
                "  endfacet\n"
                "endsolid mock\n",
                encoding="ascii",
            )
            collector = ModelCollector(models_dir=tmp_path / "models")

            stored = collector.add_model(str(source), category="toys", name="robot")
            exported = collector.export_for_slicing("robot")

            self.assertTrue(stored.exists())
            self.assertTrue(exported.exists())
            self.assertIn("models", str(stored))
            self.assertIn("slicer-input", str(exported))
            self.assertEqual(len(collector.list_models("toys")), 1)

    def test_export_for_print_alias_uses_slicer_input_directory(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.stl"
            source.write_text("solid mock\nendsolid mock\n", encoding="ascii")
            collector = ModelCollector(models_dir=tmp_path / "models")

            collector.add_model(str(source), category="toys", name="robot")
            exported = collector.export_for_print("robot")

            self.assertIn("slicer-input", str(exported))


if __name__ == "__main__":
    unittest.main()
