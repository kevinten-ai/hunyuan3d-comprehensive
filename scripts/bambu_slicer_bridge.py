#!/usr/bin/env python3
"""Convert source geometry into a sliced Bambu project with Bambu Studio CLI."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bambu_print.print_queue import is_bambu_project_3mf
from scripts.local_env import load_project_env


PROJECT_SETTINGS_PATH = "Metadata/project_settings.config"


def resolve_slicer_executable(explicit: str | None = None) -> Path:
    candidates = [
        explicit,
        os.environ.get("BAMBU_SLICER_EXE"),
        str(PROJECT_ROOT / ".tools" / "BambuStudio-2.7.1.62" / "bambu-studio.exe"),
        r"D:\Bambu\Bambu Studio\bambu-studio.exe",
        shutil.which("bambu-studio"),
        shutil.which("bambu-studio.exe"),
    ]
    for value in candidates:
        if value and Path(value).is_file():
            return Path(value).resolve()
    raise FileNotFoundError(
        "Bambu Studio CLI was not found. Set BAMBU_SLICER_EXE or pass --slicer-exe."
    )


def read_project_settings(template: Path) -> bytes:
    template = Path(template)
    if not template.is_file():
        raise FileNotFoundError(f"Slicer template not found: {template}")
    if template.suffix.lower() == ".json":
        payload = template.read_bytes()
    else:
        with ZipFile(template) as archive:
            try:
                payload = archive.read(PROJECT_SETTINGS_PATH)
            except KeyError as exc:
                raise ValueError(
                    f"Template is not a Bambu project with {PROJECT_SETTINGS_PATH}: {template}"
                ) from exc
    try:
        settings = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Template project settings are invalid JSON: {template}") from exc
    required = ("printer_model", "nozzle_diameter", "layer_height", "filament_type")
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise ValueError(f"Template project settings are incomplete: {', '.join(missing)}")
    return json.dumps(settings, ensure_ascii=False, indent=4).encode("utf-8")


def merge_project_settings(geometry_project: Path, settings: bytes, target: Path) -> None:
    geometry_project = Path(geometry_project)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    replaced = False
    with ZipFile(geometry_project) as source, ZipFile(target, "w", ZIP_DEFLATED) as output:
        for entry in source.infolist():
            payload = source.read(entry.filename)
            if entry.filename == PROJECT_SETTINGS_PATH:
                payload = settings
                replaced = True
            output.writestr(entry, payload)
        if not replaced:
            output.writestr(PROJECT_SETTINGS_PATH, settings)


def calculate_scale(input_path: Path, target_size_mm: float) -> float:
    if target_size_mm <= 0:
        raise ValueError("target_size_mm must be greater than zero")
    try:
        import trimesh
    except ImportError as exc:
        raise RuntimeError("trimesh is required to calculate automatic model scale") from exc
    loaded = trimesh.load(input_path, force="mesh")
    extents = getattr(loaded, "extents", None)
    if extents is None:
        raise ValueError(f"Unable to determine model bounds: {input_path}")
    try:
        largest = float(max(extents))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unable to determine model bounds: {input_path}") from exc
    if not math.isfinite(largest) or largest <= 0:
        raise ValueError(f"Model has invalid or empty bounds: {input_path}")
    return target_size_mm / largest


def read_result(workdir: Path) -> dict:
    path = workdir / "result.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def run_cli(command: list[str], workdir: Path, timeout: float) -> tuple[int, dict]:
    result_path = workdir / "result.json"
    if result_path.exists():
        result_path.unlink()
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        creationflags=creationflags,
    )
    return completed.returncode, read_result(workdir)


def result_error(action: str, returncode: int, result: dict) -> RuntimeError:
    detail = result.get("error_string") or "Bambu Studio returned no result detail"
    return RuntimeError(f"{action} failed (exit {returncode}): {detail}")


def slice_model(
    input_path: Path,
    output_path: Path,
    template: Path,
    slicer_exe: Path,
    target_size_mm: float = 50,
    scale: float | None = None,
    timeout: float = 600,
) -> tuple[Path, dict, float]:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input model not found: {input_path}")
    settings = read_project_settings(template)
    applied_scale = scale if scale is not None else calculate_scale(input_path, target_size_mm)
    if applied_scale <= 0:
        raise ValueError("scale must be greater than zero")

    with TemporaryDirectory(prefix="bambu-slicer-") as tmp:
        workdir = Path(tmp)
        geometry_project = workdir / "geometry.3mf"
        merged_project = workdir / "geometry_with_settings.3mf"
        sliced_project = workdir / "sliced.gcode.3mf"

        export_command = [
            str(slicer_exe),
            "--export-3mf",
            str(geometry_project),
            str(input_path),
        ]
        returncode, result = run_cli(export_command, workdir, timeout)
        if returncode != 0 or not geometry_project.is_file():
            raise result_error("Geometry project export", returncode, result)

        merge_project_settings(geometry_project, settings, merged_project)
        slice_command = [
            str(slicer_exe),
            "--scale",
            f"{applied_scale:.8g}",
            "--orient",
            "1",
            "--arrange",
            "1",
            "--slice",
            "0",
            "--export-3mf",
            str(sliced_project),
            str(merged_project),
        ]
        returncode, result = run_cli(slice_command, workdir, timeout)
        if returncode != 0 or result.get("return_code") not in (None, 0):
            raise result_error("Bambu slicing", returncode, result)
        if not sliced_project.is_file() or not is_bambu_project_3mf(str(sliced_project)):
            raise RuntimeError("Bambu Studio did not create a validated sliced project 3MF")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sliced_project, output_path)
    return output_path, result, applied_scale


def result_summary(result: dict) -> str:
    plates = result.get("sliced_plates") or []
    if not plates:
        return "slice metadata unavailable"
    plate = plates[0]
    seconds = plate.get("total_predication")
    filaments = plate.get("filaments") or []
    grams = sum(float(item.get("total_used_g", 0)) for item in filaments)
    return f"estimated_seconds={seconds} filament_g={grams:.2f}"


def main() -> int:
    load_project_env(PROJECT_ROOT)
    parser = argparse.ArgumentParser(description="Slice source geometry with a known-good Bambu project template")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--template",
        type=Path,
        default=os.environ.get("BAMBU_SLICER_TEMPLATE"),
        help="Known-good Bambu project 3MF or exported project-settings JSON",
    )
    parser.add_argument("--slicer-exe", default=os.environ.get("BAMBU_SLICER_EXE"))
    parser.add_argument("--target-size-mm", type=float, default=50)
    parser.add_argument("--scale", type=float)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()

    if args.template is None:
        print(
            "BAMBU_SLICER_TEMPLATE or --template must point to a known-good sliced Bambu project.",
            file=sys.stderr,
        )
        return 1
    try:
        slicer_exe = resolve_slicer_executable(args.slicer_exe)
        output, result, scale = slice_model(
            args.input,
            args.output,
            args.template,
            slicer_exe,
            target_size_mm=args.target_size_mm,
            scale=args.scale,
            timeout=args.timeout,
        )
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"Bambu slicer bridge failed: {exc}", file=sys.stderr)
        return 1
    print(f"Sliced project: {output}")
    print(f"Scale: {scale:.6g}")
    print(f"Result: {result_summary(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
