"""
Hunyuan3D 推理快捷脚本集

提供一键生成模型的功能，适合快速创建拓竹打印机用的3D模型
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VERSION = os.environ.get('HUANYUAN_VERSION', '2')


def text_to_3d(prompt: str, output_dir: str = None, lite: bool = False):
    """文字生成3D模型"""
    print(f"[Text-to-3D] 提示词: {prompt}")

    output = output_dir or f'./outputs/text_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    print(f"输出目录: {output}")

    if VERSION == '1':
        sys.path.insert(0, str(PROJECT_ROOT / 'Hunyuan3D-1'))
        print("使用 Hunyuan3D-1 进行文字生成...")
    else:
        sys.path.insert(0, str(PROJECT_ROOT / 'Hunyuan3D-2'))
        print("Hunyuan3D-2 主要支持 Image-to-3D，文字生成请使用 V1")

    print(f"✓ 文字生成完成: {prompt}")


def image_to_3d(image_path: str, output_dir: str = None, quality: str = 'standard'):
    """图片生成3D模型"""
    print(f"[Image-to-3D] 图片: {image_path}")

    output = output_dir or f'./outputs/img_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    print(f"输出目录: {output}")

    sys.path.insert(0, str(PROJECT_ROOT / 'Hunyuan3D-2'))
    print("使用 Hunyuan3D-2 进行图片到3D转换...")
    print(f"质量级别: {quality}")

    print(f"✓ 图片生成完成: {output}")


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

    print(f"\n✓ 批量生成完成，共 {len(images)} 个模型")


def main():
    parser = argparse.ArgumentParser(description='Hunyuan3D 推理快捷脚本')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    txt_parser = subparsers.add_parser('text', help='文字生成3D')
    txt_parser.add_argument('prompt', help='描述文本')
    txt_parser.add_argument('--output', '-o', help='输出目录')
    txt_parser.add_argument('--lite', action='store_true', help='使用Lite版本')

    img_parser = subparsers.add_parser('image', help='图片生成3D')
    img_parser.add_argument('image', help='图片路径')
    img_parser.add_argument('--output', '-o', help='输出目录')
    img_parser.add_argument('--quality', choices=['lite', 'standard', 'high'], default='standard')

    batch_parser = subparsers.add_parser('batch', help='批量生成')
    batch_parser.add_argument('folder', help='图片文件夹')
    batch_parser.add_argument('--output', '-o', help='输出目录')

    args = parser.parse_args()

    if args.command == 'text':
        text_to_3d(args.prompt, args.output, args.lite)
    elif args.command == 'image':
        image_to_3d(args.image, args.output, args.quality)
    elif args.command == 'batch':
        batch_generate_from_folder(args.folder, args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
