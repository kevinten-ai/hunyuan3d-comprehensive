import re
import json
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

    def test_powershell_examples_do_not_use_angle_bracket_placeholders(self):
        for relative_path in ["README.md", "docs/HANDOFF.md", "bambu_print/README.md"]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                code_blocks = re.findall(r"```powershell\n(.*?)```", content, flags=re.DOTALL)

                bad_blocks = [
                    block for block in code_blocks
                    if re.search(r"<[^>\r\n]+>", block)
                ]

                self.assertEqual(bad_blocks, [])

    def test_release_text_does_not_contain_common_mojibake_fragments(self):
        mojibake_fragments = [
            "鎵",
            "鍛",
            "涓€",
            "鈹",
            "绋",
            "锛",
            "€?",
        ]

        for relative_path in ["README.md", "scripts/auto_print.py"]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                found = [
                    fragment for fragment in mojibake_fragments
                    if fragment in content
                ]

                self.assertEqual(found, [])

    def test_printer_template_uses_documented_placeholder_values(self):
        template = json.loads(
            (PROJECT_ROOT / "config" / "printer.json.example").read_text(
                encoding="utf-8"
            )
        )
        expected_placeholders = {
            "host": "YOUR_PRINTER_IP",
            "access_code": "YOUR_ACCESS_CODE",
            "serial": "YOUR_PRINTER_SERIAL",
        }

        for key, expected_value in expected_placeholders.items():
            self.assertEqual(template[key], expected_value)

        for relative_path in ["README.md", "PRINT_WORKFLOW.md", "docs/HANDOFF.md"]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                for expected_value in expected_placeholders.values():
                    self.assertIn(expected_value, content)

    def test_env_template_documents_external_slicer_hook(self):
        content = (PROJECT_ROOT / "config" / "env.example").read_text(encoding="utf-8")

        self.assertIn("BAMBU_SLICER_COMMAND", content)
        self.assertIn("BAMBU_SLICER_OUTPUT_EXT", content)
        self.assertIn("auto-load .env", content)
        self.assertIn("{input}", content)
        self.assertIn("{output}", content)
        self.assertIn("{output_dir}", content)
        self.assertNotRegex(content, r"<[^>\r\n]+>")

    def test_release_docs_explain_local_env_auto_loading(self):
        for relative_path in [
            "README.md",
            "docs/HANDOFF.md",
            "docs/PROJECT_STATUS.md",
            "docs/RELEASE_READINESS.md",
            "docs/VERIFICATION.md",
        ]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

                self.assertIn(".env", content)
                self.assertTrue("auto-load" in content or "自动加载" in content)

    def test_release_docs_cover_slicer_output_extension_validation(self):
        for relative_path in [
            "README.md",
            "docs/HANDOFF.md",
            "docs/PROJECT_STATUS.md",
            "docs/RELEASE_READINESS.md",
            "docs/VERIFICATION.md",
        ]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

                self.assertIn("BAMBU_SLICER_OUTPUT_EXT", content)
                self.assertIn("output extension", content)
                self.assertIn("reject", content.lower())

    def test_bambu_package_examples_use_copy_safe_placeholders(self):
        old_example_values = [
            "192.168.1.100",
            "YOUR_CODE",
            "your-access-code",
            "SNXXX",
        ]

        for relative_path in [
            "bambu_print/README.md",
            "bambu_print/__init__.py",
            "bambu_print/printer_client.py",
            "bambu_print/print_queue.py",
        ]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                found = [
                    old_value for old_value in old_example_values
                    if old_value in content
                ]

                self.assertEqual(found, [])

    def test_auto_print_examples_use_ready_to_print_files(self):
        source_model_extensions = (".stl", ".obj", ".amf", ".gltf", ".glb")
        ambiguous_or_slicer_input_examples = (
            "models/converted",
            "./model.3mf",
            r"path\to\model.3mf",
        )

        for relative_path in [
            "README.md",
            "PRINT_WORKFLOW.md",
            "bambu_print/README.md",
            "docs/HANDOFF.md",
            "scripts/ai_to_print.py",
            "scripts/auto_print.py",
        ]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                add_examples = re.findall(r"(?:auto_print|ai_to_print)\.py add[^\r\n]*", content)
                bad_examples = [
                    example for example in add_examples
                    if any(ext in example for ext in source_model_extensions)
                ]
                bad_examples.extend(
                    example for example in add_examples
                    if any(fragment in example for fragment in ambiguous_or_slicer_input_examples)
                )

                self.assertEqual(bad_examples, [])

    def test_print_workflow_routes_source_models_through_slicing_before_queueing(self):
        content = (PROJECT_ROOT / "PRINT_WORKFLOW.md").read_text(encoding="utf-8")

        self.assertIn("Bambu Studio", content)
        self.assertIn("OrcaSlicer", content)
        self.assertIn("ready-to-print", content)
        self.assertNotIn(
            "STL/GLB/OBJ 模型文件\n"
            "  -> 模型修复或检查\n"
            "  -> 添加到 Bambu 打印队列",
            content,
        )
        self.assertNotIn("真实生成并添加到队列", content)

    def test_release_docs_do_not_claim_source_models_auto_become_print_ready(self):
        forbidden_claims = [
            "source models are converted to queue-ready 3MF",
            "convert generated source geometry to 3MF before queueing",
            "convert source model files to queue-ready 3MF",
            "source-model-to-3MF preparation before AI/continuous queueing",
            "source models are converted to queue-ready 3MF before printing",
            "ready-to-print 导出",
        ]

        for relative_path in [
            "docs/PROJECT_STATUS.md",
            "docs/RELEASE_READINESS.md",
            "docs/VERIFICATION.md",
        ]:
            with self.subTest(path=relative_path):
                content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                found = [claim for claim in forbidden_claims if claim in content]

                self.assertEqual(found, [])

    def test_models_readme_documents_current_slicer_input_boundary(self):
        content = (PROJECT_ROOT / "models" / "README.md").read_text(encoding="utf-8")

        for expected in [
            "models/raw/",
            "models/collection/",
            "models/slicer-input/",
            "models/converted/",
            "Bambu Studio",
            "OrcaSlicer",
            "ready-to-print",
            ".gcode",
            ".bgcode",
        ]:
            self.assertIn(expected, content)

        for stale_claim in [
            "ready-to-print/         # 可直接打印的模型",
            "**STL**: 拓竹打印机原生支持",
            "本目录用于存储和管理可打印的3D模型文件",
        ]:
            self.assertNotIn(stale_claim, content)


if __name__ == "__main__":
    unittest.main()
