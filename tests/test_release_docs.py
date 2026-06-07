import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseDocsTests(unittest.TestCase):
    def test_handoff_document_covers_release_summary_topics(self):
        handoff = PROJECT_ROOT / "docs" / "HANDOFF.md"

        self.assertTrue(handoff.exists())

        content = handoff.read_text(encoding="utf-8")
        for heading in [
            "## Current Capability",
            "## Install And Run",
            "## Generate Models",
            "## Print Workflow",
            "## Remaining Risks",
        ]:
            self.assertIn(heading, content)

        for required_path in [
            "YOUR_PRINTER_IP",
            "config/printer.json.example",
            "config/env.example",
            "docs/VERIFICATION.md",
            "docs/RELEASE_READINESS.md",
        ]:
            self.assertIn(required_path, content)


if __name__ == "__main__":
    unittest.main()
