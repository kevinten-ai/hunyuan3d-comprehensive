import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.system_preflight import _check_slicer, collect_preflight, summarize


class SystemPreflightTests(unittest.TestCase):
    def _create_ready_layout(self, root: Path) -> dict[str, str]:
        h1 = root / "Hunyuan3D-1"
        (h1 / "venv" / "Scripts").mkdir(parents=True)
        (h1 / "venv" / "Scripts" / "python.exe").write_bytes(b"python")
        (h1 / "main.py").write_text("", encoding="utf-8")
        (h1 / "weights" / "hunyuanDiT").mkdir(parents=True)
        (h1 / "weights" / "hunyuanDiT" / "model_index.json").write_text("{}")
        (h1 / "weights" / "hunyuanDiT" / "model.safetensors").write_bytes(b"model")
        (h1 / "weights" / "mvd_lite").mkdir(parents=True)
        (h1 / "weights" / "mvd_lite" / "model_index.json").write_text("{}")
        (h1 / "weights" / "svrm").mkdir(parents=True)
        (h1 / "weights" / "svrm" / "svrm.safetensors").write_bytes(b"model")

        h2 = root / "Hunyuan3D-2" / "tencent" / "Hunyuan3D-2"
        (h2 / "hunyuan3d-dit-v2-0").mkdir(parents=True)
        (h2 / "hunyuan3d-dit-v2-0" / "config.yaml").write_text("model: test")
        (h2 / "hunyuan3d-dit-v2-0" / "model.fp16.safetensors").write_bytes(b"model")

        comfyui = root / "ComfyUI"
        workflow_dir = (
            comfyui
            / "custom_nodes"
            / "ComfyUI-Hunyuan3DWrapper"
            / "example_workflows"
        )
        workflow_dir.mkdir(parents=True)
        (comfyui / "input").mkdir(parents=True)
        (comfyui / "input" / "input.png").write_bytes(b"image")
        (comfyui / "main.py").write_text("", encoding="utf-8")
        (workflow_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": 1,
                            "type": "LoadImage",
                            "widgets_values": ["input.png", "image"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        config = root / "config"
        config.mkdir()
        (config / "printer.json").write_text(
            json.dumps(
                {
                    "host": "192.0.2.10",
                    "access_code": "real-code",
                    "serial": "real-serial",
                    "method": "mqtt",
                }
            ),
            encoding="utf-8",
        )

        return {
            "HUNYUAN3D2_MODEL_PATH": str(h2),
            "BAMBU_SLICER_COMMAND": 'slicer "{input}" --output "{output}"',
            "BAMBU_SLICER_OUTPUT_EXT": ".gcode",
        }

    def test_empty_layout_reports_known_end_to_end_blockers(self):
        with TemporaryDirectory() as tmp:
            checks = collect_preflight(Path(tmp), environ={})
            summary = summarize(checks)

            self.assertFalse(summary["ready"])
            self.assertGreaterEqual(summary["blocked"], 5)
            blocked_ids = {check.check_id for check in checks if check.status == "blocked"}
            self.assertIn("hunyuan1", blocked_ids)
            self.assertIn("hunyuan2", blocked_ids)
            self.assertIn("comfyui", blocked_ids)
            self.assertIn("slicer", blocked_ids)
            self.assertIn("printer", blocked_ids)

    def test_ready_layout_has_no_known_local_blockers(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            environ = self._create_ready_layout(root)

            checks = collect_preflight(
                root,
                environ=environ,
                runtime_probe=lambda runtime: (
                    True,
                    "runtime ready",
                    (runtime, "torch=test cuda=test", "capability=test arches=['sm_120']"),
                ),
            )
            summary = summarize(checks)

            self.assertTrue(summary["ready"])
            self.assertEqual(summary["blocked"], 0)

    def test_hunyuan1_runtime_dependency_failure_is_a_blocker(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            environ = self._create_ready_layout(root)

            checks = collect_preflight(
                root,
                environ=environ,
                runtime_probe=lambda runtime: (
                    False,
                    "missing nvdiffrast",
                    (runtime,),
                ),
            )
            hunyuan1 = next(check for check in checks if check.check_id == "hunyuan1")

            self.assertEqual(hunyuan1.status, "blocked")
            self.assertIn("nvdiffrast", hunyuan1.message)

    def test_hunyuan1_docker_runtime_can_replace_native_runtime(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            environ = self._create_ready_layout(root)
            h1 = root / "Hunyuan3D-1"
            (h1 / "Dockerfile").write_text("FROM test", encoding="utf-8")
            (h1 / "docker-compose.yml").write_text("services: {}", encoding="utf-8")

            checks = collect_preflight(
                root,
                environ=environ,
                runtime_probe=lambda runtime: (False, "missing nvdiffrast", (runtime,)),
                docker_probe=lambda docker_root: (
                    True,
                    "docker runtime ready",
                    (str(docker_root / "Dockerfile"), "capability=[12, 0]"),
                ),
            )
            hunyuan1 = next(check for check in checks if check.check_id == "hunyuan1")

            self.assertEqual(hunyuan1.status, "ready")
            self.assertIn("Dockerfile", " ".join(hunyuan1.evidence))

    def test_bambu_bridge_requires_explicit_executable(self):
        with TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.3mf"
            template.write_bytes(b"template")
            check = _check_slicer(
                {
                    "BAMBU_SLICER_COMMAND": 'python scripts/bambu_slicer_bridge.py "{input}" "{output}"',
                    "BAMBU_SLICER_OUTPUT_EXT": ".3mf",
                    "BAMBU_SLICER_TEMPLATE": str(template),
                }
            )

            self.assertEqual(check.status, "blocked")
            self.assertIn("BAMBU_SLICER_EXE", check.message)

    def test_bambu_bridge_requires_existing_template(self):
        with TemporaryDirectory() as tmp:
            executable = Path(tmp) / "bambu-studio.exe"
            executable.write_bytes(b"exe")
            check = _check_slicer(
                {
                    "BAMBU_SLICER_COMMAND": 'python scripts/bambu_slicer_bridge.py "{input}" "{output}"',
                    "BAMBU_SLICER_OUTPUT_EXT": ".3mf",
                    "BAMBU_SLICER_EXE": str(executable),
                    "BAMBU_SLICER_TEMPLATE": str(Path(tmp) / "missing.3mf"),
                }
            )

            self.assertEqual(check.status, "blocked")
            self.assertIn("BAMBU_SLICER_TEMPLATE", check.message)

    def test_bambu_bridge_is_ready_with_existing_inputs(self):
        with TemporaryDirectory() as tmp:
            executable = Path(tmp) / "bambu-studio.exe"
            template = Path(tmp) / "template.3mf"
            executable.write_bytes(b"exe")
            template.write_bytes(b"template")
            check = _check_slicer(
                {
                    "BAMBU_SLICER_COMMAND": 'python scripts/bambu_slicer_bridge.py "{input}" "{output}"',
                    "BAMBU_SLICER_OUTPUT_EXT": ".3mf",
                    "BAMBU_SLICER_EXE": str(executable),
                    "BAMBU_SLICER_TEMPLATE": str(template),
                }
            )

            self.assertEqual(check.status, "ready")
            self.assertIn(str(executable), check.evidence)
            self.assertIn(str(template), check.evidence)

    def test_malformed_printer_config_is_reported_without_exception(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config"
            config.mkdir()
            (config / "printer.json").write_text("{broken", encoding="utf-8")

            checks = collect_preflight(root, environ={})
            printer = next(check for check in checks if check.check_id == "printer")

            self.assertEqual(printer.status, "blocked")
            self.assertIn("JSON", printer.message)


if __name__ == "__main__":
    unittest.main()
