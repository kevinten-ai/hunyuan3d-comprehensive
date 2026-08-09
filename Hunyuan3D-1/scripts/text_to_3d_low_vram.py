#!/usr/bin/env python3
"""Run the Hunyuan3D-1 lite pipeline in isolated low-VRAM stages."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGES = ("text", "background", "views", "mesh")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--output", default="outputs/docker-low-vram")
    parser.add_argument("--t2i-steps", type=int, default=25)
    parser.add_argument("--gen-steps", type=int, default=50)
    parser.add_argument("--max-faces", type=int, default=90000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--texture-mapping", action="store_true")
    parser.add_argument("--start-stage", choices=STAGES, default="text")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def build_stage_commands(
    args: argparse.Namespace,
    python_executable: str = sys.executable,
) -> list[tuple[str, list[str]]]:
    output = Path(args.output)
    common_seed = str(args.seed)
    return [
        (
            "text",
            [
                python_executable,
                "infer/text_to_image.py",
                "--text2image_path",
                "weights/hunyuanDiT",
                "--text_prompt",
                args.prompt,
                "--output_img_path",
                str(output / "img.jpg"),
                "--seed",
                common_seed,
                "--steps",
                str(args.t2i_steps),
                "--device",
                args.device,
            ],
        ),
        (
            "background",
            [
                python_executable,
                "infer/removebg.py",
                "--rgb_path",
                str(output / "img.jpg"),
                "--output_rgba_path",
                str(output / "img_nobg.png"),
            ],
        ),
        (
            "views",
            [
                python_executable,
                "infer/image_to_views.py",
                "--rgba_path",
                str(output / "img_nobg.png"),
                "--output_views_path",
                str(output / "views.jpg"),
                "--output_cond_path",
                str(output / "cond.jpg"),
                "--seed",
                common_seed,
                "--steps",
                str(args.gen_steps),
                "--device",
                args.device,
                "--use_lite",
                "true",
            ],
        ),
        (
            "mesh",
            [
                python_executable,
                "infer/views_to_mesh.py",
                "--views_path",
                str(output / "views.jpg"),
                "--cond_path",
                str(output / "cond.jpg"),
                "--save_folder",
                str(output),
                "--max_faces_num",
                str(args.max_faces),
                "--mv23d_cfg_path",
                "svrm/configs/svrm.yaml",
                "--mv23d_ckt_path",
                "weights/svrm/svrm.safetensors",
                "--device",
                args.device,
                "--use_lite",
                "true",
                "--do_texture_mapping",
                str(args.texture_mapping).lower(),
            ],
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = PROJECT_ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)

    start_index = STAGES.index(args.start_stage)
    commands = build_stage_commands(args)
    for stage, command in commands[start_index:]:
        print(f"[{stage}] {shlex.join(command)}", flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    final_name = "mesh.glb" if args.texture_mapping else "mesh_vertex_colors.obj"
    print(f"Output: {output / final_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
