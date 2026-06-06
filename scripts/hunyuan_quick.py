"""
Hunyuan3D 推理快捷脚本集

提供一键生成模型的功能，适合快速创建拓竹打印机用的3D模型
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _default_output(prefix: str) -> str:
    return str(PROJECT_ROOT / "outputs" / f'{prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')


def hunyuan1_python_executable() -> str:
    configured = os.environ.get("HUNYUAN3D1_PYTHON")
    if configured:
        return configured

    venv_python = PROJECT_ROOT / "Hunyuan3D-1" / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)

    return sys.executable


def _run_command(command: list[str], cwd: Optional[Path], dry_run: bool, mode: str) -> dict:
    result = {
        "mode": mode,
        "command": command,
        "cwd": str(cwd) if cwd else None,
        "dry_run": dry_run,
        "returncode": None,
    }
    print("命令:", " ".join(command))
    if dry_run:
        print("[Dry run] 未执行生成命令")
        return result

    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
    result["returncode"] = completed.returncode
    if completed.returncode != 0:
        raise RuntimeError(f"Hunyuan3D {mode} generation failed with exit code {completed.returncode}")
    return result


def build_text_command(prompt: str, output_dir: str, lite: bool = False, save_memory: bool = False) -> list[str]:
    """Build a real Hunyuan3D-1 text-to-3D command."""
    command = [
        hunyuan1_python_executable(),
        str(PROJECT_ROOT / "Hunyuan3D-1" / "main.py"),
        "--text_prompt",
        prompt,
        "--save_folder",
        output_dir,
    ]
    if lite:
        command.append("--use_lite")
    if save_memory:
        command.append("--save_memory")
    return command


def build_image_command(image_path: str, output_dir: str, quality: str = 'standard') -> list[str]:
    """Build a real Hunyuan3D-2 image-to-3D command through the project CLI wrapper."""
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "hunyuan2_image.py"),
        "--image",
        image_path,
        "--output",
        output_dir,
    ]
    if quality == 'lite':
        command.append("--low-vram")
    elif quality == 'high':
        command.extend(["--steps", "75", "--octree-resolution", "512"])
    return command


def text_to_3d(prompt: str, output_dir: str = None, lite: bool = False,
               dry_run: bool = False, save_memory: bool = False) -> dict:
    """文字生成3D模型"""
    print(f"[Text-to-3D] 提示词: {prompt}")

    output = output_dir or _default_output("text")
    print(f"输出目录: {output}")

    command = build_text_command(prompt, output, lite=lite, save_memory=save_memory)
    return _run_command(command, cwd=PROJECT_ROOT / "Hunyuan3D-1", dry_run=dry_run, mode="text")


def image_to_3d(image_path: str, output_dir: str = None, quality: str = 'standard',
                dry_run: bool = False) -> dict:
    """图片生成3D模型"""
    print(f"[Image-to-3D] 图片: {image_path}")

    output = output_dir or _default_output("img")
    print(f"输出目录: {output}")

    print(f"质量级别: {quality}")
    command = build_image_command(image_path, output, quality=quality)
    return _run_command(command, cwd=PROJECT_ROOT, dry_run=dry_run, mode="image")


def batch_generate_from_folder(folder_path: str, output_base: str = None):
    """批量从文件夹中的图片生成3D模型"""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"错误: 文件夹不存在 {folder}")
        return

    image_exts = ['.png', '.jpg', '.jpeg', '.webp']
    images = [f for f in folder.iterdir() if f.suffix.lower() in image_exts]

    if not images:
        print(f"在 {folder} 中未找到图片")
        return

    output_base = output_base or f'./outputs/batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    print(f"找到 {len(images)} 张图片，开始批量生成...")

    for i, img in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] 处理: {img.name}")
        img_output = f"{output_base}/{img.stem}"
        try:
            image_to_3d(str(img), img_output)
        except Exception as e:
            print(f"  错误: {e}")

    print(f"\n[OK] 批量生成完成，共 {len(images)} 个模型")


def main():
    parser = argparse.ArgumentParser(description='Hunyuan3D 推理快捷脚本')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    txt_parser = subparsers.add_parser('text', help='文字生成3D')
    txt_parser.add_argument('prompt', help='描述文本')
    txt_parser.add_argument('--output', '-o', help='输出目录')
    txt_parser.add_argument('--lite', action='store_true', help='使用Lite版本')
    txt_parser.add_argument('--save-memory', action='store_true', help='启用Hunyuan3D-1省显存模式')
    txt_parser.add_argument('--dry-run', action='store_true', help='只打印将要执行的命令，不运行模型')

    img_parser = subparsers.add_parser('image', help='图片生成3D')
    img_parser.add_argument('image', help='图片路径')
    img_parser.add_argument('--output', '-o', help='输出目录')
    img_parser.add_argument('--quality', choices=['lite', 'standard', 'high'], default='standard')
    img_parser.add_argument('--dry-run', action='store_true', help='只打印将要执行的命令，不运行模型')

    batch_parser = subparsers.add_parser('batch', help='批量生成')
    batch_parser.add_argument('folder', help='图片文件夹')
    batch_parser.add_argument('--output', '-o', help='输出目录')

    args = parser.parse_args()

    if args.command == 'text':
        text_to_3d(args.prompt, args.output, args.lite, args.dry_run, args.save_memory)
    elif args.command == 'image':
        image_to_3d(args.image, args.output, args.quality, args.dry_run)
    elif args.command == 'batch':
        batch_generate_from_folder(args.folder, args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
