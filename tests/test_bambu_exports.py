import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class BambuExportsTests(unittest.TestCase):
    def test_discover_printers_is_exported(self):
        from bambu_print import discover_printers

        self.assertTrue(callable(discover_printers))


if __name__ == "__main__":
    unittest.main()
