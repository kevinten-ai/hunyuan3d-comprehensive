#!/usr/bin/env python3
"""
Convert GLB/GLTF meshes to 3MF files for slicers such as Bambu Studio.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional


def _load_as_mesh(input_path: Path):
    try:
        import trimesh
    except ImportError as exc:
        raise RuntimeError("请先安装依赖: pip install trimesh numpy") from exc

    loaded = trimesh.load(str(input_path))
    if isinstance(loaded, trimesh.Scene):
        geometries = [
            geom for geom in loaded.geometry.values()
            if isinstance(geom, trimesh.Trimesh)
        ]
        if not geometries:
            raise ValueError("场景中未找到可导出的网格数据")
        return trimesh.util.concatenate(geometries)
    return loaded


def _resolve_output_path(input_path: Path, output_path: Optional[str]) -> Path:
    if output_path is None:
        return input_path.with_suffix(".3mf")

    resolved = Path(output_path)
    if resolved.suffix == "":
        return resolved.with_suffix(".3mf")
    if resolved.suffix.lower() != ".3mf":
        raise ValueError("输出文件必须使用 .3mf 扩展名")
    return resolved


def convert_glb_to_3mf(glb_path: str, output_path: Optional[str] = None) -> Path:
    """Convert a GLB or GLTF file to a real 3MF package."""
    input_path = Path(glb_path)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    if input_path.suffix.lower() not in {".glb", ".gltf"}:
        raise ValueError(f"输入文件必须是 .glb 或 .gltf: {input_path}")

    output = _resolve_output_path(input_path, output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"加载模型: {input_path}")
    mesh = _load_as_mesh(input_path)

    print(f"导出 3MF: {output}")
    mesh.export(str(output), file_type="3mf")

    print("[OK] 转换完成")
    print(f"  {input_path} -> {output}")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 GLB/GLTF 模型转换为 Bambu Studio 可打开的 3MF 文件。"
    )
    parser.add_argument("input", help="输入 .glb 或 .gltf 文件")
    parser.add_argument(
        "output",
        nargs="?",
        help="输出 .3mf 文件；省略时写到输入文件同目录同名 .3mf",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        convert_glb_to_3mf(args.input, args.output)
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
