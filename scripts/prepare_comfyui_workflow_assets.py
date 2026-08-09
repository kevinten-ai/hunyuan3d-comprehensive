#!/usr/bin/env python3
"""Prepare local assets referenced by the bundled Hunyuan3D ComfyUI workflows."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_comfyui_workflow_assets import (
    check_workflow_assets,
    default_workflows,
    summarize,
)


DEFAULT_COMFYUI_DIR = PROJECT_ROOT / "ComfyUI"
DEFAULT_HUNYUAN2_DIR = PROJECT_ROOT / "Hunyuan3D-2"

NORMAL_MODEL_NAME = "hunyuan3d-dit-v2-0-fp16.safetensors"
FAST_MV_MODEL_NAME = "hunyuan3d-dit-v2-0-mv-fast-fp16.safetensors"
UPSCALE_MODEL_NAME = "4x_foolhardy_Remacri.pth"

NORMAL_MODEL_SIZES = {4_928_151_562, 4_928_151_594}
FAST_MV_MODEL_SIZE = 4_930_777_530
UPSCALE_MODEL_SIZE = 67_025_055


def link_or_copy(source: Path, target: Path) -> str:
    source = Path(source).resolve()
    target = Path(target)
    if target.exists():
        return "exists"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
        return "linked"
    except OSError:
        shutil.copy2(source, target)
        return "copied"


def find_normal_model(comfyui_dir: Path, hunyuan2_dir: Path) -> Path:
    candidates = (
        comfyui_dir / "models" / "checkpoints" / "hunyuan3d-dit-v2.safetensors",
        hunyuan2_dir
        / "tencent"
        / "Hunyuan3D-2"
        / "hunyuan3d-dit-v2-0"
        / "model.fp16.safetensors",
        hunyuan2_dir / "tencent" / "Hunyuan3D-2" / "model.fp16.safetensors",
    )
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size in NORMAL_MODEL_SIZES:
            return candidate
    expected = "\n  - ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "No compatible local Hunyuan3D-2 normal checkpoint was found. Checked:\n  - "
        + expected
    )


def validate_size(path: Path, expected: int | set[int], label: str) -> None:
    accepted = {expected} if isinstance(expected, int) else expected
    actual = path.stat().st_size
    if actual not in accepted:
        values = ", ".join(f"{value:,}" for value in sorted(accepted))
        raise ValueError(f"{label} has unexpected size {actual:,}; expected {values}: {path}")


def download_required_models(comfyui_dir: Path, offline: bool = False) -> list[str]:
    model_root = comfyui_dir / "models"
    hy3d_dir = model_root / "diffusion_models" / "hy3dgen"
    hy3d_dir.mkdir(parents=True, exist_ok=True)
    actions: list[str] = []

    fast_target = hy3d_dir / FAST_MV_MODEL_NAME
    if not fast_target.exists():
        nested = hy3d_dir / "hunyuan3d-dit-v2-mv-fast" / "model.fp16.safetensors"
        if not nested.exists():
            if offline:
                raise FileNotFoundError(f"Offline mode: missing Fast multiview model: {fast_target}")
            from huggingface_hub import hf_hub_download

            nested = Path(
                hf_hub_download(
                    repo_id="tencent/Hunyuan3D-2mv",
                    filename="hunyuan3d-dit-v2-mv-fast/model.fp16.safetensors",
                    local_dir=hy3d_dir,
                )
            )
        actions.append(f"{link_or_copy(nested, fast_target)}: {fast_target}")
    validate_size(fast_target, FAST_MV_MODEL_SIZE, "Fast multiview checkpoint")

    upscale_target = model_root / "upscale_models" / UPSCALE_MODEL_NAME
    if not upscale_target.exists():
        if offline:
            raise FileNotFoundError(f"Offline mode: missing upscale model: {upscale_target}")
        from huggingface_hub import hf_hub_download

        downloaded = Path(
            hf_hub_download(
                repo_id="fofr/comfyui",
                filename=f"upscale_models/{UPSCALE_MODEL_NAME}",
                local_dir=model_root,
            )
        )
        actions.append(f"downloaded: {downloaded}")
    validate_size(upscale_target, UPSCALE_MODEL_SIZE, "Upscale model")
    return actions


def prepare_input_images(comfyui_dir: Path, hunyuan2_dir: Path) -> list[str]:
    input_dir = comfyui_dir / "input"
    mv_source = hunyuan2_dir / "assets" / "example_mv_images" / "1"
    mappings = (
        (mv_source / "front.png", input_dir / "pasted" / "image (734).png"),
        (mv_source / "back.png", input_dir / "pasted" / "image (735).png"),
        (mv_source / "left.png", input_dir / "pasted" / "image (736).png"),
    )
    actions: list[str] = []
    for source, target in mappings:
        if not source.is_file():
            raise FileNotFoundError(f"Missing bundled Hunyuan3D-2 example image: {source}")
        actions.append(f"{link_or_copy(source, target)}: {target}")

    single_source = hunyuan2_dir / "assets" / "demo.png"
    single_target = input_dir / "s-l1600 - 2022-02-25T095119.012.jpg"
    if not single_target.exists():
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required to prepare the single-view JPEG input") from exc
        single_target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(single_source) as image:
            image.convert("RGB").save(single_target, format="JPEG", quality=95)
        actions.append(f"converted: {single_target}")
    else:
        actions.append(f"exists: {single_target}")
    return actions


def download_optional_models(comfyui_dir: Path, offline: bool = False) -> list[str]:
    diffusers_dir = comfyui_dir / "models" / "diffusers"
    expected = (
        diffusers_dir / "hunyuan3d-delight-v2-0",
        diffusers_dir / "hunyuan3d-paint-v2-0",
    )
    if all(path.is_dir() for path in expected):
        return [f"exists: {path}" for path in expected]
    if offline:
        missing = ", ".join(str(path) for path in expected if not path.is_dir())
        raise FileNotFoundError(f"Offline mode: missing optional texture models: {missing}")

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id="tencent/Hunyuan3D-2",
        allow_patterns=["*hunyuan3d-delight-v2-0*", "*hunyuan3d-paint-v2-0*"],
        ignore_patterns=[
            "*hunyuan3d-paint-v2-0-turbo*",
            "*unet/diffusion_pytorch_model.bin",
            "*image_encoder*",
        ],
        local_dir=diffusers_dir,
    )
    return [f"downloaded: {path}" for path in expected]


def prepare_assets(
    comfyui_dir: Path,
    hunyuan2_dir: Path,
    include_optional: bool = False,
    offline: bool = False,
) -> list[str]:
    comfyui_dir = Path(comfyui_dir).resolve()
    hunyuan2_dir = Path(hunyuan2_dir).resolve()
    if not (comfyui_dir / "main.py").is_file():
        raise FileNotFoundError(f"ComfyUI entrypoint not found: {comfyui_dir / 'main.py'}")

    normal_target = (
        comfyui_dir / "models" / "diffusion_models" / "hy3dgen" / NORMAL_MODEL_NAME
    )
    actions: list[str] = []
    if not normal_target.exists():
        normal_source = find_normal_model(comfyui_dir, hunyuan2_dir)
        actions.append(f"{link_or_copy(normal_source, normal_target)}: {normal_target}")
    validate_size(normal_target, NORMAL_MODEL_SIZES, "Normal Hunyuan3D checkpoint")

    actions.extend(download_required_models(comfyui_dir, offline=offline))
    actions.extend(prepare_input_images(comfyui_dir, hunyuan2_dir))
    if include_optional:
        actions.extend(download_optional_models(comfyui_dir, offline=offline))
    return actions


def workflow_summary(comfyui_dir: Path) -> dict:
    workflow_dir = (
        comfyui_dir
        / "custom_nodes"
        / "ComfyUI-Hunyuan3DWrapper"
        / "example_workflows"
    )
    checks = []
    for workflow in default_workflows(workflow_dir):
        checks.extend(check_workflow_assets(workflow, comfyui_dir=comfyui_dir))
    return summarize(checks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Hunyuan3D ComfyUI workflow assets")
    parser.add_argument("--comfyui-dir", type=Path, default=DEFAULT_COMFYUI_DIR)
    parser.add_argument("--hunyuan2-dir", type=Path, default=DEFAULT_HUNYUAN2_DIR)
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Also cache the roughly 9 GiB Paint and Delight models used by texture branches",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Reuse local files only and fail instead of downloading missing assets",
    )
    args = parser.parse_args()

    try:
        actions = prepare_assets(
            args.comfyui_dir,
            args.hunyuan2_dir,
            include_optional=args.include_optional,
            offline=args.offline,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Asset preparation failed: {exc}", file=sys.stderr)
        return 1

    for action in actions:
        print(action)
    summary = workflow_summary(args.comfyui_dir.resolve())
    print(
        "Workflow assets: "
        f"required_missing={summary['unique_required_missing']} "
        f"optional_missing={summary['unique_optional_missing']}"
    )
    return 0 if summary["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
