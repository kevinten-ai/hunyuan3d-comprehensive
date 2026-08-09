#!/usr/bin/env python3
"""Run a low-cost Hunyuan3D shape workflow through the ComfyUI HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMFYUI_DIR = PROJECT_ROOT / "ComfyUI"
DEFAULT_INPUT_NAME = "s-l1600 - 2022-02-25T095119.012.jpg"
DEFAULT_MODEL_NAME = r"hy3dgen\hunyuan3d-dit-v2-0-fp16.safetensors"


def build_prompt(
    input_name: str = DEFAULT_INPUT_NAME,
    model_name: str = DEFAULT_MODEL_NAME,
    steps: int = 5,
    octree_resolution: int = 128,
    num_chunks: int = 4000,
    max_faces: int = 5000,
    seed: int = 123,
    output_prefix: str = "validation/comfyui_hunyuan2_lowstep",
) -> dict:
    return {
        "13": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "52": {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["13", 0],
                "width": 518,
                "height": 518,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        },
        "10": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": model_name,
                "attention_mode": "sdpa",
                "cublas_ops": False,
            },
        },
        "141": {
            "class_type": "Hy3DGenerateMesh",
            "inputs": {
                "pipeline": ["10", 0],
                "image": ["52", 0],
                "guidance_scale": 5.5,
                "steps": steps,
                "seed": seed,
                "force_offload": True,
            },
        },
        "140": {
            "class_type": "Hy3DVAEDecode",
            "inputs": {
                "vae": ["10", 1],
                "latents": ["141", 0],
                "box_v": 1.01,
                "octree_resolution": octree_resolution,
                "num_chunks": num_chunks,
                "mc_level": 0.0,
                "mc_algo": "mc",
                "enable_flash_vdm": False,
                "force_offload": True,
            },
        },
        "59": {
            "class_type": "Hy3DPostprocessMesh",
            "inputs": {
                "trimesh": ["140", 0],
                "remove_floaters": True,
                "remove_degenerate_faces": True,
                "reduce_faces": True,
                "max_facenum": max_faces,
                "smooth_normals": False,
            },
        },
        "17": {
            "class_type": "Hy3DExportMesh",
            "inputs": {
                "trimesh": ["59", 0],
                "filename_prefix": output_prefix,
                "file_format": "glb",
                "save_file": True,
            },
        },
    }


def get_json(url: str, timeout: float = 30) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.load(response)


def post_json(url: str, payload: dict, timeout: float = 30) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def wait_for_server(server_url: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return get_json(f"{server_url}/system_stats", timeout=3)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(1)
    raise TimeoutError(f"ComfyUI server did not become ready: {last_error}")


def queue_prompt(server_url: str, prompt: dict) -> str:
    response = post_json(
        f"{server_url}/prompt",
        {"prompt": prompt, "client_id": str(uuid.uuid4())},
    )
    errors = response.get("node_errors") or {}
    if errors:
        raise RuntimeError(f"ComfyUI rejected workflow nodes: {json.dumps(errors)}")
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return a prompt ID: {response}")
    return str(prompt_id)


def wait_for_prompt(server_url: str, prompt_id: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = get_json(f"{server_url}/history/{prompt_id}")
        if prompt_id in history:
            item = history[prompt_id]
            status = item.get("status", {})
            if status.get("status_str") != "success":
                messages = status.get("messages", [])
                raise RuntimeError(f"ComfyUI workflow failed: {json.dumps(messages)}")
            return item
        time.sleep(2)
    raise TimeoutError(f"ComfyUI workflow timed out after {timeout:.0f} seconds")


def find_generated_glb(comfyui_dir: Path, output_prefix: str, started_at: float) -> Path:
    prefix = Path(output_prefix.replace("\\", "/"))
    output_dir = comfyui_dir / "output" / prefix.parent
    matches = [
        path
        for path in output_dir.glob(f"{prefix.name}*.glb")
        if path.stat().st_mtime >= started_at - 1
    ]
    if not matches:
        raise FileNotFoundError(f"ComfyUI reported success but no new GLB matched: {output_dir}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def inspect_mesh(path: Path) -> str:
    try:
        import trimesh
    except ImportError:
        return f"bytes={path.stat().st_size}"
    mesh = trimesh.load(path, force="mesh")
    return (
        f"bytes={path.stat().st_size} vertices={len(mesh.vertices)} "
        f"faces={len(mesh.faces)} watertight={mesh.is_watertight}"
    )


def start_server(comfyui_dir: Path, port: int, log_path: Path) -> tuple[subprocess.Popen, object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    command = [
        sys.executable,
        str(comfyui_dir / "main.py"),
        "--listen",
        "127.0.0.1",
        "--port",
        str(port),
        "--disable-auto-launch",
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    return process, log_handle


def stop_server(process: subprocess.Popen, log_handle: object) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    log_handle.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a low-step Hunyuan3D ComfyUI smoke test")
    parser.add_argument("--comfyui-dir", type=Path, default=DEFAULT_COMFYUI_DIR)
    parser.add_argument("--server-url", default="http://127.0.0.1:8191")
    parser.add_argument("--start-server", action="store_true")
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--octree-resolution", type=int, default=128)
    parser.add_argument("--num-chunks", type=int, default=4000)
    parser.add_argument("--max-faces", type=int, default=5000)
    parser.add_argument(
        "--seed",
        type=int,
        help="Fixed seed. Defaults to a new seed so ComfyUI cannot reuse a cached smoke run",
    )
    parser.add_argument("--input-name", default=DEFAULT_INPUT_NAME)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument(
        "--output-prefix",
        default="validation/comfyui_hunyuan2_lowstep",
    )
    args = parser.parse_args()

    comfyui_dir = args.comfyui_dir.resolve()
    server_url = f"http://127.0.0.1:{args.port}" if args.start_server else args.server_url.rstrip("/")
    process = None
    log_handle = None
    try:
        if args.start_server:
            try:
                get_json(f"{server_url}/system_stats", timeout=2)
            except (HTTPError, URLError, TimeoutError, OSError):
                pass
            else:
                raise RuntimeError(
                    f"A ComfyUI server is already listening at {server_url}; "
                    "omit --start-server to reuse it"
                )
            process, log_handle = start_server(
                comfyui_dir,
                args.port,
                PROJECT_ROOT / "outputs" / "validation" / "comfyui_smoke_server.log",
            )
        stats = wait_for_server(server_url, min(args.timeout, 120))
        if process is not None and process.poll() is not None:
            raise RuntimeError(
                f"The managed ComfyUI server exited early with code {process.returncode}"
            )
        devices = stats.get("devices", [])
        print(f"ComfyUI ready: {server_url} devices={len(devices)}")

        seed = args.seed if args.seed is not None else time.time_ns() & 0xFFFFFFFF
        prompt = build_prompt(
            input_name=args.input_name,
            model_name=args.model_name,
            steps=args.steps,
            octree_resolution=args.octree_resolution,
            num_chunks=args.num_chunks,
            max_faces=args.max_faces,
            seed=seed,
            output_prefix=args.output_prefix,
        )
        started_at = time.time()
        prompt_id = queue_prompt(server_url, prompt)
        print(f"Queued prompt: {prompt_id}")
        wait_for_prompt(server_url, prompt_id, args.timeout)
        output = find_generated_glb(comfyui_dir, args.output_prefix, started_at)
        print(f"Generated GLB: {output}")
        print(f"Mesh: {inspect_mesh(output)}")
        return 0
    except (FileNotFoundError, HTTPError, RuntimeError, TimeoutError, URLError) as exc:
        print(f"ComfyUI smoke test failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if process is not None and log_handle is not None:
            stop_server(process, log_handle)


if __name__ == "__main__":
    raise SystemExit(main())
