#!/usr/bin/env python3
"""
AI生成 + 自动打印 完整工作流

这个脚本演示了如何将Hunyuan3D模型生成与自动打印结合。

使用方式:
    # 文字生成 + 打印
    python scripts/ai_to_print.py text "一只可爱的兔子"

    # 图片生成 + 打印
    python scripts/ai_to_print.py image ./photo.jpg

    # 仅添加到打印队列
    python scripts/ai_to_print.py add ./model.stl --name "我的模型"

    # 仅生成模型，不打印
    python scripts/ai_to_print.py text "一只恐龙" --no-print
"""

import sys
import os
import time
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 尝试导入打印模块
try:
    from bambu_print import PrintQueue, discover_printers
    HAS_PRINT = True
except ImportError as e:
    print(f"警告: 无法导入打印模块: {e}")
    print("请运行: pip install -r requirements-print.txt")
    HAS_PRINT = False


def load_printer_config():
    """加载打印机配置"""
    config_file = PROJECT_ROOT / "config" / "printer.json"
    if not config_file.exists():
        return None
    import json
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def setup_printer():
    """设置打印机连接"""
    if not HAS_PRINT:
        print("错误: 打印模块不可用")
        return None

    config = load_printer_config()
    if not config:
        print("错误: 未配置打印机")
        print("请运行: python scripts/auto_print.py config --host <ip> --access-code <code> --serial <sn>")
        return None

    try:
        queue = PrintQueue(
            printer_host=config['host'],
            access_code=config['access_code'],
            serial=config['serial']
        )
        print(f"[OK] 已连接到打印机: {config['host']}")
        return queue
    except Exception as e:
        print(f"错误: 无法连接到打印机: {e}")
        return None


def _find_model_file(output_dir: str):
    """Find a generated model in an output directory."""
    output_path = Path(output_dir)
    if not output_path.exists():
        return None
    for pattern in ("*.stl", "*.3mf", "*.glb", "*.obj", "*.ply"):
        matches = sorted(output_path.rglob(pattern))
        if matches:
            return str(matches[0])
    return None


def _write_mock_stl(output_dir: str) -> str:
    """Write a tiny ASCII STL so mock mode produces a real local file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    model_file = output_path / "model.stl"
    model_file.write_text(
        "solid mock\n"
        "  facet normal 0 0 1\n"
        "    outer loop\n"
        "      vertex 0 0 0\n"
        "      vertex 1 0 0\n"
        "      vertex 0 1 0\n"
        "    endloop\n"
        "  endfacet\n"
        "endsolid mock\n",
        encoding="ascii",
    )
    return str(model_file)


def generate_text_to_3d(prompt: str, output_dir: str = None, mock: bool = False,
                        run_generator: bool = False, lite: bool = True):
    """
    文字生成3D模型

    Args:
        prompt: 描述文本
        output_dir: 输出目录

    Returns:
        模型文件路径
    """
    print(f"\n[AI] 文字生成: {prompt}")

    output = output_dir or f'./outputs/text_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    os.makedirs(output, exist_ok=True)

    if mock:
        model_file = _write_mock_stl(output)
        print(f"[AI] Mock 模式: 已创建演示模型 {model_file}")
        return model_file

    if not run_generator:
        print("[AI] 未执行真实生成。请使用 --run-generator 调用 Hunyuan3D-1，或使用 --mock 做演示。")
        return None

    from scripts import hunyuan_quick

    hunyuan_quick.text_to_3d(prompt, output_dir=output, lite=lite, dry_run=False)
    model_file = _find_model_file(output)
    if not model_file:
        print(f"[AI] 未在输出目录找到模型文件: {output}")
        return None
    return model_file


def generate_image_to_3d(image_path: str, output_dir: str = None, quality: str = 'standard',
                         mock: bool = False, run_generator: bool = False):
    """
    图片生成3D模型

    Args:
        image_path: 图片路径
        output_dir: 输出目录
        quality: 质量级别

    Returns:
        模型文件路径
    """
    print(f"\n[AI] 图片生成: {image_path}")

    output = output_dir or f'./outputs/img_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    os.makedirs(output, exist_ok=True)

    if mock:
        model_file = _write_mock_stl(output)
        print(f"[AI] Mock 模式: 已创建演示模型 {model_file}")
        return model_file

    if not run_generator:
        print("[AI] 未执行真实生成。请使用 --run-generator 调用 Hunyuan3D-2，或使用 --mock 做演示。")
        return None

    from scripts import hunyuan_quick

    hunyuan_quick.image_to_3d(image_path, output_dir=output, quality=quality, dry_run=False)
    model_file = _find_model_file(output)
    if not model_file:
        print(f"[AI] 未在输出目录找到模型文件: {output}")
        return None
    return model_file


def repair_model(model_path: str) -> str:
    """
    修复模型

    Args:
        model_path: 模型文件路径

    Returns:
        修复后的模型路径
    """
    print(f"\n[修复] 检查模型: {model_path}")

    model_file = Path(model_path)
    if not model_file.exists():
        print(f"[修复] 警告: 文件不存在，跳过修复")
        return model_path

    try:
        from scripts.model_converter import ModelConverter

        converter = ModelConverter(output_dir=str(model_file.parent))
        repaired_file = converter.repair_mesh(str(model_file), f"{model_file.stem}_repaired")
        if Path(repaired_file).exists():
            print(f"[修复] 修复完成: {repaired_file}")
            return str(repaired_file)
    except Exception as e:
        print(f"[修复] 无法自动修复，保留原文件: {e}")

    fallback_file = model_file.parent / f"{model_file.stem}_checked{model_file.suffix}"
    if not fallback_file.exists():
        shutil.copy2(model_file, fallback_file)
    print(f"[修复] 已保留可用模型: {fallback_file}")
    return str(fallback_file)


def add_to_print_queue(queue: PrintQueue, model_path: str, name: str = None):
    """
    添加到打印队列

    Args:
        queue: 打印队列
        model_path: 模型路径
        name: 任务名称

    Returns:
        任务ID
    """
    print(f"\n[打印] 添加到队列: {model_path}")

    if not Path(model_path).exists():
        print(f"[打印] 警告: 文件不存在，将跳过实际打印")
        return None

    try:
        job_id = queue.add(model_path, name=name or Path(model_path).stem)
        print(f"[打印] 任务已添加: {job_id}")
        return job_id
    except Exception as e:
        print(f"[打印] 添加失败: {e}")
        return None


def wait_for_completion(queue: PrintQueue, check_interval: float = 5.0):
    """
    等待打印完成

    Args:
        queue: 打印队列
        check_interval: 检查间隔（秒）
    """
    print("\n[监控] 开始监控打印进度...")

    try:
        while True:
            status = queue.get_status()

            if status['current_job']:
                job = status['current_job']
                print(f"\r[进度] {job['name']}: {job['progress']:.1f}% | "
                      f"层 {status['printer']['layer']}/{status['printer']['total_layers']} | "
                      f"状态: {status['status']}", end="", flush=True)

                # 检查是否完成
                if status['status'] in ['idle', 'stopped']:
                    print("\n[监控] 打印已完成")
                    break

            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n[监控] 用户中断")


def main():
    parser = argparse.ArgumentParser(
        description='AI生成 + 自动打印工作流',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 文字生成 + 打印
  python scripts/ai_to_print.py text "一只可爱的兔子"

  # 图片生成 + 打印
  python scripts/ai_to_print.py image ./photo.jpg

  # 仅添加到打印队列
  python scripts/ai_to_print.py add ./model.stl --name "我的模型"

  # 仅生成，不打印
  python scripts/ai_to_print.py text "一只恐龙" --no-print

  # 查看队列
  python scripts/ai_to_print.py status

  # 发现打印机
  python scripts/ai_to_print.py discover
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # text - 文字生成
    text_parser = subparsers.add_parser('text', help='文字生成3D')
    text_parser.add_argument('prompt', help='描述文本')
    text_parser.add_argument('--output', '-o', help='输出目录')
    text_parser.add_argument('--no-print', action='store_true', help='仅生成，不打印')
    text_parser.add_argument('--name', help='打印任务名称')
    text_parser.add_argument('--mock', action='store_true', help='演示模式：不调用模型，只返回预期模型路径')
    text_parser.add_argument('--run-generator', action='store_true', help='调用真实 Hunyuan3D-1 生成命令')
    text_parser.add_argument('--lite', action='store_true', help='使用 Hunyuan3D-1 Lite 模式')

    # image - 图片生成
    image_parser = subparsers.add_parser('image', help='图片生成3D')
    image_parser.add_argument('image', help='图片路径')
    image_parser.add_argument('--output', '-o', help='输出目录')
    image_parser.add_argument('--quality', choices=['lite', 'standard', 'high'],
                             default='standard', help='质量级别')
    image_parser.add_argument('--no-print', action='store_true', help='仅生成，不打印')
    image_parser.add_argument('--name', help='打印任务名称')
    image_parser.add_argument('--mock', action='store_true', help='演示模式：不调用模型，只返回预期模型路径')
    image_parser.add_argument('--run-generator', action='store_true', help='调用真实 Hunyuan3D-2 生成命令')

    # add - 添加到队列
    add_parser = subparsers.add_parser('add', help='添加文件到打印队列')
    add_parser.add_argument('file', help='模型文件路径')
    add_parser.add_argument('--name', help='任务名称')
    add_parser.add_argument('--priority', type=int, default=0, help='优先级')

    # status - 查看状态
    status_parser = subparsers.add_parser('status', help='查看队列状态')

    # discover - 发现打印机
    discover_parser = subparsers.add_parser('discover', help='发现打印机')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 发现打印机
    if args.command == 'discover':
        print("正在搜索拓竹打印机...")
        printers = discover_printers(timeout=3.0)
        if printers:
            print(f"发现 {len(printers)} 台打印机:")
            for p in printers:
                print(f"  - {p['ip']}")
        else:
            print("未发现打印机")
        return

    # 查看状态
    if args.command == 'status':
        queue = setup_printer()
        if queue:
            status = queue.get_status()
            print(f"\n队列状态: {status['status']}")
            print(f"队列长度: {status['queue_length']}")
            if status['current_job']:
                print(f"当前任务: {status['current_job']['name']}")
                print(f"进度: {status['current_job']['progress']:.1f}%")
        return

    # 添加到队列
    if args.command == 'add':
        queue = setup_printer()
        if queue:
            add_to_print_queue(queue, args.file, args.name)
        return

    # 文字生成
    if args.command == 'text':
        model_path = generate_text_to_3d(
            args.prompt,
            args.output,
            mock=args.mock,
            run_generator=args.run_generator,
            lite=args.lite,
        )

    # 图片生成
    elif args.command == 'image':
        model_path = generate_image_to_3d(
            args.image,
            args.output,
            args.quality,
            mock=args.mock,
            run_generator=args.run_generator,
        )

    else:
        return

    if not model_path:
        print("\n未生成模型文件；流程停止。")
        return

    # 修复模型
    repaired_path = repair_model(model_path)

    # 打印
    if not args.no_print:
        queue = setup_printer()
        if queue:
            job_id = add_to_print_queue(queue, repaired_path, args.name)
            if job_id:
                # 启动队列
                queue.start()
                print("\n[OK] 已启动打印队列")
                print("使用 'python scripts/ai_to_print.py status' 查看进度")
                print("使用 'python scripts/auto_print.py watch' 实时监控")
        else:
            print("\n注意: 模型已生成，但无法自动打印")
            print(f"模型位置: {repaired_path}")
            print("请手动使用 Bambu Studio 打印，或配置打印机后重试")
    else:
        print(f"\n[OK] 模型已生成: {repaired_path}")
        print("去掉 --no-print 后可自动添加到打印队列")


if __name__ == '__main__':
    main()
