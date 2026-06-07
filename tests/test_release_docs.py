import unittest
import re
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

    def test_powershell_examples_do_not_use_angle_bracket_placeholders(self):
        for relative_path in ["README.md", "docs/HANDOFF.md"]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                code_blocks = re.findall(r"```powershell\n(.*?)```", content, flags=re.DOTALL)

                bad_blocks = [
                    block for block in code_blocks
                    if re.search(r"<[^>\r\n]+>", block)
                ]

                self.assertEqual(bad_blocks, [])


if __name__ == "__main__":
    unittest.main()
