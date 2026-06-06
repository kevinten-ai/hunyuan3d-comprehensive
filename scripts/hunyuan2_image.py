#!/usr/bin/env python3
"""
Command-line image-to-3D bridge for Hunyuan3D-2.

This wrapper keeps the upstream Hunyuan3D-2 examples unchanged while exposing a
stable CLI for the root project orchestration scripts.
"""

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HUNYUAN2_ROOT = PROJECT_ROOT / "Hunyuan3D-2"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a GLB model from an image with Hunyuan3D-2")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--output-name", default="model.glb", help="Output GLB file name")
    parser.add_argument("--model-path", default="tencent/Hunyuan3D-2", help="Model path or Hugging Face repo")
    parser.add_argument("--subfolder", default="hunyuan3d-dit-v2-0", help="Shape model subfolder")
    parser.add_argument("--variant", default="fp16", help="Model variant")
    parser.add_argument("--steps", type=int, default=50, help="Inference steps")
    parser.add_argument("--octree-resolution", type=int, default=380, help="Octree resolution")
    parser.add_argument("--num-chunks", type=int, default=20000, help="Number of chunks")
    parser.add_argument("--seed", type=int, default=12345, help="Torch random seed")
    parser.add_argument("--low-vram", action="store_true", help="Use lower-memory settings")
    return parser.parse_args()


def resolve_cli_paths(image_path: str, output_dir: str, model_path: str) -> tuple[Path, Path, str]:
    """Resolve local user paths before this script changes into the Hunyuan3D-2 folder."""
    resolved_model = str(Path(model_path).resolve()) if Path(model_path).exists() else model_path
    return Path(image_path).resolve(), Path(output_dir).resolve(), resolved_model


def main() -> int:
    args = parse_args()
    image_path, output_dir, model_path = resolve_cli_paths(args.image, args.output, args.model_path)

    if not image_path.exists():
        print(f"错误: 图片不存在: {image_path}", file=sys.stderr)
        return 2

    if args.low_vram:
        args.octree_resolution = min(args.octree_resolution, 256)
        args.num_chunks = min(args.num_chunks, 8000)

    sys.path.insert(0, str(HUNYUAN2_ROOT))
    os.chdir(HUNYUAN2_ROOT)

    from PIL import Image
    import torch
    from hy3dgen.rembg import BackgroundRemover
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

    image = Image.open(image_path).convert("RGBA")
    if image.mode == "RGB":
        rembg = BackgroundRemover()
        image = rembg(image)

    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        model_path,
        subfolder=args.subfolder,
        variant=args.variant,
    )

    mesh = pipeline(
        image=image,
        num_inference_steps=args.steps,
        octree_resolution=args.octree_resolution,
        num_chunks=args.num_chunks,
        generator=torch.manual_seed(args.seed),
        output_type="trimesh",
    )[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.output_name
    mesh.export(str(output_path))
    print(f"模型已保存: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
