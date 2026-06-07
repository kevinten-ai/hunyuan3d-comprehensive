import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RequirementsTests(unittest.TestCase):
    def test_print_requirements_cover_root_orchestration_dependencies(self):
        requirement_names = set()
        for line in (PROJECT_ROOT / "requirements-print.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = line.split(";", 1)[0].strip()
            for separator in ("==", ">=", "<=", "~=", "!=", ">", "<"):
                name = name.split(separator, 1)[0].strip()
            requirement_names.add(name.lower())

        for package in [
            "paho-mqtt",
            "requests",
            "trimesh",
            "numpy-stl",
            "numpy",
        ]:
            with self.subTest(package=package):
                self.assertIn(package, requirement_names)


if __name__ == "__main__":
    unittest.main()
