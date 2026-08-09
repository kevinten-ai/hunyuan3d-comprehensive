#!/usr/bin/env python3
"""Local prerequisite audit for the complete 3D-to-print workflow."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_comfyui_workflow_assets import (
    check_workflow_assets,
    default_workflows,
    summarize as summarize_workflow_assets,
)
from scripts.local_env import load_project_env


PRINT_READY_EXTENSIONS = {".3mf", ".gcode", ".bgcode"}
WEIGHT_EXTENSIONS = {".safetensors", ".bin", ".ckpt", ".pt"}


@dataclass(frozen=True)
class PreflightCheck:
    check_id: str
    area: str
    status: str
    message: str
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "id": self.check_id,
            "area": self.area,
            "status": self.status,
            "message": self.message,
            "evidence": list(self.evidence),
        }


def _has_weight_file(path: Path) -> bool:
    if not path.exists():
        return False
    return any(
        candidate.is_file() and candidate.suffix.lower() in WEIGHT_EXTENSIONS
        for candidate in path.rglob("*")
    )


def _runtime_exists(value: str) -> bool:
    candidate = Path(value)
    return candidate.is_file() or shutil.which(value) is not None


def _probe_hunyuan1_runtime(runtime: str) -> tuple[bool, str, tuple[str, ...]]:
    probe = """
import importlib.util
import json
import torch

payload = {
    "torch": torch.__version__,
    "cuda_runtime": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "nvdiffrast": importlib.util.find_spec("nvdiffrast") is not None,
}
if payload["cuda_available"]:
    payload["capability"] = list(torch.cuda.get_device_capability(0))
    payload["arches"] = torch.cuda.get_arch_list()
    payload["kernel"] = float(torch.ones(32, device="cuda").sum().item())
print(json.dumps(payload))
"""
    try:
        result = subprocess.run(
            [runtime, "-c", probe],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Hunyuan3D-1 运行时探测失败: {exc}", (runtime,)
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown error"
        return False, f"Hunyuan3D-1 运行时探测失败: {detail}", (runtime,)
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return False, f"Hunyuan3D-1 运行时探测输出无效: {exc}", (runtime,)

    evidence = (
        runtime,
        f"torch={payload.get('torch')} cuda={payload.get('cuda_runtime')}",
        f"capability={payload.get('capability')} arches={payload.get('arches')}",
    )
    if not payload.get("cuda_available") or payload.get("kernel") != 32.0:
        return False, "Hunyuan3D-1 运行时未通过 CUDA 实算。", evidence
    capability = payload.get("capability")
    if not isinstance(capability, list) or len(capability) != 2:
        return False, "无法确定 Hunyuan3D-1 当前 GPU 的 CUDA compute capability。", evidence
    required_arch = f"sm_{capability[0]}{capability[1]}"
    if required_arch not in payload.get("arches", []):
        return False, f"当前 Hunyuan3D-1 Torch 构建不包含本机 GPU 架构 {required_arch}。", evidence
    if not payload.get("nvdiffrast"):
        return (
            False,
            "缺少核心网格重建依赖 nvdiffrast；Windows 需要 CUDA Toolkit 和 MSVC 后从源码编译。",
            evidence,
        )
    return True, f"CUDA {required_arch} 与 nvdiffrast 运行时探测通过。", evidence


def _probe_hunyuan1_docker(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    compose_file = root / "docker-compose.yml"
    dockerfile = root / "Dockerfile"
    evidence = (str(compose_file), str(dockerfile))
    if shutil.which("docker") is None:
        return False, "Docker CLI is unavailable.", evidence
    if not compose_file.is_file() or not dockerfile.is_file():
        return False, "Hunyuan3D-1 Docker configuration is incomplete.", evidence

    probe = """
import json
import torch
import nvdiffrast.torch as dr
import xformers

ctx = dr.RasterizeCudaContext()
pos = torch.tensor([[[-0.8, -0.8, 0.0, 1.0], [0.8, -0.8, 0.0, 1.0], [0.0, 0.8, 0.0, 1.0]]], device="cuda")
tri = torch.tensor([[0, 1, 2]], device="cuda", dtype=torch.int32)
rast, _ = dr.rasterize(ctx, pos, tri, resolution=[16, 16])
torch.cuda.synchronize()
payload = {
    "torch": torch.__version__,
    "cuda_runtime": torch.version.cuda,
    "capability": list(torch.cuda.get_device_capability(0)),
    "covered_pixels": int((rast[..., 3] > 0).sum().item()),
    "xformers": xformers.__version__,
}
print("HUNYUAN_DOCKER_PROBE=" + json.dumps(payload))
"""
    try:
        result = subprocess.run(
            ["docker", "compose", "run", "--rm", "hunyuan3d", "python", "-c", probe],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Docker runtime probe failed: {exc}", evidence
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown error"
        return False, f"Docker runtime probe failed: {detail}", evidence

    marker = "HUNYUAN_DOCKER_PROBE="
    payload_line = next(
        (line for line in result.stdout.splitlines() if line.startswith(marker)),
        "",
    )
    try:
        payload = json.loads(payload_line.removeprefix(marker))
    except json.JSONDecodeError as exc:
        return False, f"Docker runtime probe output is invalid: {exc}", evidence

    runtime_evidence = evidence + (
        f"torch={payload.get('torch')} cuda={payload.get('cuda_runtime')}",
        f"capability={payload.get('capability')} xformers={payload.get('xformers')}",
        f"nvdiffrast_covered_pixels={payload.get('covered_pixels')}",
    )
    if payload.get("capability") != [12, 0] or payload.get("covered_pixels", 0) <= 0:
        return False, "Docker CUDA/nvdiffrast execution probe failed.", runtime_evidence
    return True, "Docker CUDA 13, sm_120, nvdiffrast, and xFormers probe passed.", runtime_evidence


def _check_hunyuan1(
    project_root: Path,
    environ: Mapping[str, str],
    runtime_probe=_probe_hunyuan1_runtime,
    docker_probe=_probe_hunyuan1_docker,
) -> PreflightCheck:
    root = project_root / "Hunyuan3D-1"
    weights = root / "weights"
    runtime = environ.get("HUNYUAN3D1_PYTHON", "").strip()
    if not runtime:
        runtime = str(root / "venv" / "Scripts" / "python.exe")

    missing: list[str] = []
    if not (root / "main.py").is_file():
        missing.append("Hunyuan3D-1/main.py")
    has_docker_config = (root / "Dockerfile").is_file() and (root / "docker-compose.yml").is_file()
    runtime_exists = _runtime_exists(runtime)
    if not runtime_exists and not has_docker_config:
        missing.append(f"Python runtime ({runtime}) or Docker configuration")

    text_weights = weights / "hunyuanDiT"
    if not (text_weights / "model_index.json").is_file() or not _has_weight_file(text_weights):
        missing.append("weights/hunyuanDiT Diffusers snapshot")
    if not (weights / "mvd_lite" / "model_index.json").is_file():
        missing.append("weights/mvd_lite")
    if not (weights / "svrm" / "svrm.safetensors").is_file():
        missing.append("weights/svrm/svrm.safetensors")

    if missing:
        return PreflightCheck(
            "hunyuan1",
            "Hunyuan3D-1 text-to-3D",
            "blocked",
            "缺少本地前置条件: " + ", ".join(missing),
            (str(root),),
        )

    if runtime_exists:
        runtime_ready, runtime_message, runtime_evidence = runtime_probe(runtime)
    else:
        runtime_ready = False
        runtime_message = f"Native Python runtime is unavailable: {runtime}"
        runtime_evidence = (runtime,)
    if not runtime_ready and has_docker_config:
        docker_ready, docker_message, docker_evidence = docker_probe(root)
        if docker_ready:
            runtime_ready, runtime_message, runtime_evidence = (
                docker_ready,
                docker_message,
                docker_evidence,
            )
        else:
            runtime_message = f"{runtime_message} Docker fallback: {docker_message}"
            runtime_evidence = runtime_evidence + docker_evidence
    if not runtime_ready:
        return PreflightCheck(
            "hunyuan1",
            "Hunyuan3D-1 text-to-3D",
            "blocked",
            runtime_message,
            runtime_evidence + (str(text_weights),),
        )

    smoke_mesh = root / "outputs" / "docker-smoke" / "mesh_vertex_colors.obj"
    if smoke_mesh.is_file() and smoke_mesh.stat().st_size > 0:
        ready_message = "运行入口、必需权重和 CUDA 核心依赖已就位；低步数文本到网格证据已存在。"
        ready_evidence = runtime_evidence + (str(text_weights), str(smoke_mesh))
    else:
        ready_message = "运行入口、必需权重和 CUDA 核心依赖已就位；仍需执行真实低步数生成验证。"
        ready_evidence = runtime_evidence + (str(text_weights),)

    return PreflightCheck(
        "hunyuan1",
        "Hunyuan3D-1 text-to-3D",
        "ready",
        ready_message,
        ready_evidence,
    )


def _check_hunyuan2(project_root: Path, environ: Mapping[str, str]) -> PreflightCheck:
    model_root = Path(
        environ.get(
            "HUNYUAN3D2_MODEL_PATH",
            str(project_root / "Hunyuan3D-2" / "tencent" / "Hunyuan3D-2"),
        )
    )
    configs = list(model_root.rglob("config.yaml")) if model_root.exists() else []
    has_weights = _has_weight_file(model_root)
    missing: list[str] = []
    if not model_root.exists():
        missing.append("model snapshot directory")
    if not configs:
        missing.append("config.yaml")
    if not has_weights:
        missing.append("model weight file")

    if missing:
        return PreflightCheck(
            "hunyuan2",
            "Hunyuan3D-2 image-to-3D",
            "blocked",
            "缺少本地模型快照内容: " + ", ".join(missing),
            (str(model_root),),
        )

    return PreflightCheck(
        "hunyuan2",
        "Hunyuan3D-2 image-to-3D",
        "ready",
        "本地模型配置和权重已就位；preflight 不代表完整质量生成已验证。",
        (str(model_root), str(configs[0])),
    )


def _check_comfyui(project_root: Path) -> PreflightCheck:
    comfyui = project_root / "ComfyUI"
    workflow_dir = (
        comfyui
        / "custom_nodes"
        / "ComfyUI-Hunyuan3DWrapper"
        / "example_workflows"
    )
    workflows = default_workflows(workflow_dir)
    if not (comfyui / "main.py").is_file() or not workflows:
        return PreflightCheck(
            "comfyui",
            "ComfyUI Hunyuan3D workflow",
            "blocked",
            "缺少 ComfyUI 入口或 Hunyuan3D 示例工作流。",
            (str(comfyui), str(workflow_dir)),
        )

    asset_checks = []
    for workflow in workflows:
        asset_checks.extend(check_workflow_assets(workflow, comfyui_dir=comfyui))
    asset_summary = summarize_workflow_assets(asset_checks)
    if not asset_checks:
        return PreflightCheck(
            "comfyui",
            "ComfyUI Hunyuan3D workflow",
            "blocked",
            "工作流存在，但未识别到可验证的模型或输入资产。",
            tuple(str(path) for path in workflows),
        )
    if asset_summary["required_missing"]:
        return PreflightCheck(
            "comfyui",
            "ComfyUI Hunyuan3D workflow",
            "blocked",
            (
                f"缺少 {asset_summary['unique_required_missing']} 个唯一必需资产；"
                "运行 check_comfyui_workflow_assets.py 查看明细。"
            ),
            tuple(str(path) for path in workflows),
        )
    if asset_summary["optional_missing"]:
        return PreflightCheck(
            "comfyui",
            "ComfyUI Hunyuan3D workflow",
            "warning",
            (
                "必需资产已就位，但仍有 "
                f"{asset_summary['unique_optional_missing']} 个可下载资产尚未缓存。"
            ),
            tuple(str(path) for path in workflows),
        )
    return PreflightCheck(
        "comfyui",
        "ComfyUI Hunyuan3D workflow",
        "ready",
        "示例工作流引用的本地资产已就位；仍需实际执行工作流图。",
        tuple(str(path) for path in workflows),
    )


def _template_fields(command: str) -> tuple[set[str], str | None]:
    try:
        fields = {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(command)
            if field_name
        }
    except ValueError as exc:
        return set(), str(exc)
    return fields, None


def _check_slicer(environ: Mapping[str, str]) -> PreflightCheck:
    command = environ.get("BAMBU_SLICER_COMMAND", "").strip()
    output_ext = environ.get("BAMBU_SLICER_OUTPUT_EXT", ".3mf").strip().lower()
    if output_ext and not output_ext.startswith("."):
        output_ext = "." + output_ext
    if not command:
        return PreflightCheck(
            "slicer",
            "Bambu/OrcaSlicer bridge",
            "blocked",
            "未配置 BAMBU_SLICER_COMMAND；生成的 STL/OBJ/GLB 不能自动进入打印队列。",
        )
    fields, parse_error = _template_fields(command)
    allowed_fields = {"input", "output", "output_dir"}
    if parse_error or "input" not in fields or not ({"output", "output_dir"} & fields):
        return PreflightCheck(
            "slicer",
            "Bambu/OrcaSlicer bridge",
            "blocked",
            "切片器命令模板无效，必须包含 {input} 以及 {output} 或 {output_dir}。",
            (command,),
        )
    unknown_fields = fields - allowed_fields
    if unknown_fields:
        return PreflightCheck(
            "slicer",
            "Bambu/OrcaSlicer bridge",
            "blocked",
            "切片器命令包含未知占位符: " + ", ".join(sorted(unknown_fields)),
            (command,),
        )
    if output_ext not in PRINT_READY_EXTENSIONS:
        return PreflightCheck(
            "slicer",
            "Bambu/OrcaSlicer bridge",
            "blocked",
            f"BAMBU_SLICER_OUTPUT_EXT={output_ext!r} 不是可验证的打印输出格式。",
            (command,),
        )

    normalized_command = command.replace("\\", "/").lower()
    if "bambu_slicer_bridge.py" in normalized_command:
        bridge_inputs = {
            "BAMBU_SLICER_EXE": environ.get("BAMBU_SLICER_EXE", "").strip(),
            "BAMBU_SLICER_TEMPLATE": environ.get("BAMBU_SLICER_TEMPLATE", "").strip(),
        }
        missing = [name for name, value in bridge_inputs.items() if not value]
        invalid = [
            f"{name} ({value})"
            for name, value in bridge_inputs.items()
            if value and not Path(value).is_file()
        ]
        if missing or invalid:
            details = []
            if missing:
                details.append("未配置 " + ", ".join(missing))
            if invalid:
                details.append("文件不存在 " + ", ".join(invalid))
            return PreflightCheck(
                "slicer",
                "Bambu/OrcaSlicer bridge",
                "blocked",
                "Bambu 切片桥接配置无效: " + "; ".join(details),
                (command,),
            )
        return PreflightCheck(
            "slicer",
            "Bambu/OrcaSlicer bridge",
            "ready",
            "Bambu 切片桥接脚本、切片器和已知可用工程模板均已配置。",
            (
                command,
                output_ext,
                bridge_inputs["BAMBU_SLICER_EXE"],
                bridge_inputs["BAMBU_SLICER_TEMPLATE"],
            ),
        )
    return PreflightCheck(
        "slicer",
        "Bambu/OrcaSlicer bridge",
        "ready",
        "切片器命令模板和输出扩展名通过静态检查；仍需真实切片输出验证。",
        (command, output_ext),
    )


def _check_printer(project_root: Path) -> PreflightCheck:
    config_path = project_root / "config" / "printer.json"
    if not config_path.is_file():
        return PreflightCheck(
            "printer",
            "Bambu Lab printer",
            "blocked",
            "缺少本地 config/printer.json。",
            (str(config_path),),
        )
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return PreflightCheck(
            "printer",
            "Bambu Lab printer",
            "blocked",
            f"printer.json 不是可读取的 JSON: {exc}",
            (str(config_path),),
        )

    try:
        from scripts.auto_print import validate_printer_config

        errors, warnings = validate_printer_config(config)
    except Exception as exc:
        return PreflightCheck(
            "printer",
            "Bambu Lab printer",
            "blocked",
            f"无法加载打印机配置校验器: {exc}",
            (str(config_path),),
        )
    if errors:
        return PreflightCheck(
            "printer",
            "Bambu Lab printer",
            "blocked",
            "打印机配置未通过检查: " + "; ".join(errors),
            (str(config_path),),
        )
    if warnings:
        return PreflightCheck(
            "printer",
            "Bambu Lab printer",
            "warning",
            "打印机配置字段通过，但存在提示: " + "; ".join(warnings),
            (str(config_path),),
        )
    return PreflightCheck(
        "printer",
        "Bambu Lab printer",
        "ready",
        "打印机配置字段通过本地检查；preflight 不连接真实打印机。",
        (str(config_path),),
    )


def collect_preflight(
    project_root: Path = PROJECT_ROOT,
    environ: Mapping[str, str] | None = None,
    runtime_probe=_probe_hunyuan1_runtime,
    docker_probe=_probe_hunyuan1_docker,
) -> list[PreflightCheck]:
    root = Path(project_root).resolve()
    values = os.environ if environ is None else environ
    return [
        _check_hunyuan1(
            root,
            values,
            runtime_probe=runtime_probe,
            docker_probe=docker_probe,
        ),
        _check_hunyuan2(root, values),
        _check_comfyui(root),
        _check_slicer(values),
        _check_printer(root),
    ]


def summarize(checks: list[PreflightCheck]) -> dict:
    counts = {
        status: sum(check.status == status for check in checks)
        for status in ("ready", "warning", "blocked")
    }
    return {
        "total": len(checks),
        "ready_count": counts["ready"],
        "warning": counts["warning"],
        "blocked": counts["blocked"],
        "ready": counts["blocked"] == 0,
    }


def print_text_report(checks: list[PreflightCheck]) -> None:
    summary = summarize(checks)
    print("Hunyuan3D + ComfyUI + Bambu system preflight")
    print("---------------------------------------------")
    for check in checks:
        print(f"[{check.status.upper()}] {check.area}: {check.message}")
        for item in check.evidence:
            print(f"  evidence: {item}")
    print(
        "\nSummary: "
        f"{summary['ready_count']} ready, {summary['warning']} warning, "
        f"{summary['blocked']} blocked"
    )
    print(f"Known local prerequisites complete: {'YES' if summary['ready'] else 'NO'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only local preflight for the Hunyuan3D-to-Bambu workflow"
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Exit 0 even when known local prerequisites are blocked",
    )
    args = parser.parse_args(argv)

    load_project_env(args.project_root)
    checks = collect_preflight(args.project_root)
    summary = summarize(checks)
    if args.json:
        print(
            json.dumps(
                {
                    "summary": summary,
                    "checks": [check.as_dict() for check in checks],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print_text_report(checks)
    if summary["blocked"] and not args.allow_incomplete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
