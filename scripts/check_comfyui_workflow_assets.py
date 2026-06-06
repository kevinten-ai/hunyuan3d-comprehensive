"""
Check ComfyUI workflow files for local assets required by Hunyuan3D examples.

The script is intentionally read-only. It does not copy model weights, create
links, download files, or modify ComfyUI state.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMFYUI_DIR = PROJECT_ROOT / "ComfyUI"
DEFAULT_WORKFLOW_DIR = (
    DEFAULT_COMFYUI_DIR
    / "custom_nodes"
    / "ComfyUI-Hunyuan3DWrapper"
    / "example_workflows"
)


REQUIRED_MODEL_NODES = {
    "Hy3DModelLoader": ("diffusion_models", 0),
    "Hy3D_2_1SimpleMeshGen": ("diffusion_models", 0),
    "Hy3DVAELoader": ("vae", 0),
    "UpscaleModelLoader": ("upscale_models", 0),
}

INPUT_FILE_NODES = {
    "LoadImage": 0,
    "Hy3DLoadMesh": 0,
}

DOWNLOADABLE_DIFFUSER_NODES = {
    "DownloadAndLoadHy3DDelightModel": 0,
    "DownloadAndLoadHy3DPaintModel": 0,
}


@dataclass(frozen=True)
class AssetCheck:
    workflow: Path
    node_id: int | str
    node_type: str
    asset: str
    expected_path: Path
    exists: bool
    required: bool
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "workflow": str(self.workflow),
            "node_id": self.node_id,
            "node_type": self.node_type,
            "asset": self.asset,
            "expected_path": str(self.expected_path),
            "exists": self.exists,
            "required": self.required,
            "note": self.note,
        }


def _widget_value(node: dict, index: int) -> str | None:
    values = node.get("widgets_values")
    if not isinstance(values, list) or len(values) <= index:
        return None
    value = values[index]
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _asset_path(comfyui_dir: Path, folder: str, asset: str) -> Path:
    return comfyui_dir / "models" / folder / Path(asset.replace("\\", "/"))


def _input_path(comfyui_dir: Path, asset: str) -> Path:
    return comfyui_dir / "input" / Path(asset.replace("\\", "/"))


def _candidate_note(comfyui_dir: Path, node_type: str, asset: str, expected: Path) -> str:
    if node_type in {"Hy3DModelLoader", "Hy3D_2_1SimpleMeshGen"} and not expected.exists():
        checkpoints = comfyui_dir / "models" / "checkpoints"
        if checkpoints.exists():
            wants_multiview = "mv" in asset.lower()
            candidates = [
                path
                for path in checkpoints.glob("*.safetensors")
                if "hunyuan3d" in path.name.lower()
                and ("mv" in path.name.lower()) == wants_multiview
            ]
            if candidates:
                joined = ", ".join(str(path) for path in candidates[:3])
                return f"Candidate checkpoint file(s) found outside diffusion_models: {joined}"
    return ""


def check_workflow_assets(workflow_path: Path, comfyui_dir: Path = DEFAULT_COMFYUI_DIR) -> list[AssetCheck]:
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    checks: list[AssetCheck] = []

    for node in data.get("nodes", []):
        node_type = str(node.get("type", ""))
        node_id = node.get("id", "")

        if node_type in REQUIRED_MODEL_NODES:
            folder, index = REQUIRED_MODEL_NODES[node_type]
            asset = _widget_value(node, index)
            if asset:
                expected = _asset_path(comfyui_dir, folder, asset)
                checks.append(
                    AssetCheck(
                        workflow=workflow_path,
                        node_id=node_id,
                        node_type=node_type,
                        asset=asset,
                        expected_path=expected,
                        exists=expected.exists(),
                        required=True,
                        note=_candidate_note(comfyui_dir, node_type, asset, expected),
                    )
                )

        if node_type in INPUT_FILE_NODES:
            asset = _widget_value(node, INPUT_FILE_NODES[node_type])
            if asset:
                expected = _input_path(comfyui_dir, asset)
                checks.append(
                    AssetCheck(
                        workflow=workflow_path,
                        node_id=node_id,
                        node_type=node_type,
                        asset=asset,
                        expected_path=expected,
                        exists=expected.exists(),
                        required=True,
                    )
                )

        if node_type in DOWNLOADABLE_DIFFUSER_NODES:
            asset = _widget_value(node, DOWNLOADABLE_DIFFUSER_NODES[node_type])
            if asset:
                expected = comfyui_dir / "models" / "diffusers" / asset
                checks.append(
                    AssetCheck(
                        workflow=workflow_path,
                        node_id=node_id,
                        node_type=node_type,
                        asset=asset,
                        expected_path=expected,
                        exists=expected.exists(),
                        required=False,
                        note="Node can download this model from Hugging Face if network access is available.",
                    )
                )

    return checks


def default_workflows(workflow_dir: Path = DEFAULT_WORKFLOW_DIR) -> list[Path]:
    if not workflow_dir.exists():
        return []
    return sorted(workflow_dir.glob("*.json"))


def summarize(checks: Iterable[AssetCheck]) -> dict:
    rows = list(checks)
    required_missing = [row for row in rows if row.required and not row.exists]
    optional_missing = [row for row in rows if not row.required and not row.exists]
    unique_required_missing = {str(row.expected_path) for row in required_missing}
    unique_optional_missing = {str(row.expected_path) for row in optional_missing}
    return {
        "total": len(rows),
        "required_missing": len(required_missing),
        "optional_missing": len(optional_missing),
        "unique_required_missing": len(unique_required_missing),
        "unique_optional_missing": len(unique_optional_missing),
        "ready": not required_missing,
    }


def print_text_report(checks: list[AssetCheck]) -> None:
    summary = summarize(checks)
    print("ComfyUI workflow asset check")
    print("---------------------------")
    print(f"Assets checked: {summary['total']}")
    print(f"Required missing: {summary['required_missing']}")
    print(f"Unique required missing: {summary['unique_required_missing']}")
    print(f"Optional/downloadable missing: {summary['optional_missing']}")
    print(f"Unique optional/downloadable missing: {summary['unique_optional_missing']}")
    print(f"Ready to execute required assets: {'YES' if summary['ready'] else 'NO'}")

    missing = [row for row in checks if not row.exists]
    if not missing:
        return

    print("\nMissing assets:")
    for row in missing:
        kind = "required" if row.required else "downloadable"
        print(f"- [{kind}] {row.workflow.name} node {row.node_id} {row.node_type}")
        print(f"  asset: {row.asset}")
        print(f"  expected: {row.expected_path}")
        if row.note:
            print(f"  note: {row.note}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ComfyUI Hunyuan3D workflow assets")
    parser.add_argument(
        "--comfyui-dir",
        type=Path,
        default=DEFAULT_COMFYUI_DIR,
        help="Path to the local ComfyUI checkout",
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        action="append",
        help="Workflow JSON file to check. Defaults to Hunyuan3DWrapper example workflows.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Exit 0 even when required assets are missing",
    )
    args = parser.parse_args()

    workflows = args.workflow or default_workflows(
        args.comfyui_dir / "custom_nodes" / "ComfyUI-Hunyuan3DWrapper" / "example_workflows"
    )
    checks: list[AssetCheck] = []
    for workflow in workflows:
        checks.extend(check_workflow_assets(workflow, comfyui_dir=args.comfyui_dir))

    summary = summarize(checks)
    if args.json:
        print(json.dumps({"summary": summary, "checks": [row.as_dict() for row in checks]}, indent=2))
    else:
        print_text_report(checks)

    if summary["required_missing"] and not args.allow_missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
