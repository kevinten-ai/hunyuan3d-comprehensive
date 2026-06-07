#!/usr/bin/env python3
"""
拓竹自动打印命令行工具

功能:
- 配置打印机连接
- 添加打印任务到队列
- 管理打印队列
- 监控打印进度

示例:
    # 从仓库根目录配置打印机
    python scripts/auto_print.py config --host YOUR_PRINTER_IP --access-code YOUR_ACCESS_CODE --serial YOUR_PRINTER_SERIAL

    # 添加打印任务
    python scripts/auto_print.py add ./model.stl --name "我的模型"

    # 查看队列
    python scripts/auto_print.py list

    # 查看状态
    python scripts/auto_print.py status

    # 控制队列
    python scripts/auto_print.py start
    python scripts/auto_print.py pause
    python scripts/auto_print.py resume
    python scripts/auto_print.py stop

    # 发现打印机
    python scripts/auto_print.py discover
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bambu_print import PrintQueue, ConnectionType, discover_printers

# 配置文件路径
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "printer.json"
SUPPORTED_QUEUE_METHODS = {"mqtt"}
PLACEHOLDER_VALUES = {
    "YOUR_PRINTER_IP",
    "YOUR_ACCESS_CODE",
    "YOUR_CODE",
    "SNXXX",
    "YOUR_SERIAL",
    "YOUR_PRINTER_SERIAL",
}


def load_config() -> Optional[dict]:
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict):
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def validate_printer_config(config: Optional[dict]) -> tuple[list[str], list[str]]:
    """Validate local printer config without opening a printer connection."""
    errors: list[str] = []
    warnings: list[str] = []

    if config is None:
        return ["未找到 config/printer.json，请先从 config/printer.json.example 创建本地配置。"], warnings

    if not isinstance(config, dict):
        return ["config/printer.json 必须是 JSON 对象。"], warnings

    required_fields = ("host", "access_code", "serial")
    for field in required_fields:
        value = str(config.get(field, "")).strip()
        if not value:
            errors.append(f"缺少必填字段: {field}")
        elif value in PLACEHOLDER_VALUES:
            errors.append(f"字段 {field} 仍是模板占位值: {value}")

    host = str(config.get("host", "")).strip()
    if host in {"192.168.1.100", "0.0.0.0", "127.0.0.1", "localhost"}:
        warnings.append(f"host 看起来像示例或本机地址，请确认它是真实打印机 IP: {host}")

    method = str(config.get("method", "mqtt")).strip().lower()
    if method not in SUPPORTED_QUEUE_METHODS:
        errors.append(
            f"method={method!r} 当前不能用于自动打印队列；请使用 mqtt。"
        )

    return errors, warnings


def print_config_validation(config: Optional[dict], show_success: bool = True) -> bool:
    """Print local config validation result. Returns True when usable."""
    errors, warnings = validate_printer_config(config)
    if errors:
        print("打印机配置检查未通过:")
        for error in errors:
            print(f"  - {error}")
    elif show_success:
        print("[OK] 打印机配置字段检查通过")

    if warnings:
        print("注意:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(
            "请运行: python scripts/auto_print.py config --host YOUR_PRINTER_IP "
            "--access-code YOUR_ACCESS_CODE --serial YOUR_PRINTER_SERIAL"
        )
        return False
    return True


def cmd_config(args):
    """配置打印机"""
    config = {
        'host': args.host,
        'access_code': args.access_code,
        'serial': args.serial,
        'method': args.method
    }

    if not print_config_validation(config, show_success=False):
        return 1

    save_config(config)
    print(f"[OK] 配置已保存到 {CONFIG_FILE}")
    print(f"  主机: {args.host}")
    print(f"  序列号: {args.serial}")
    print(f"  连接方式: {args.method}")


def cmd_check_config(args):
    """检查本地打印机配置，不连接打印机"""
    config = load_config()
    return 0 if print_config_validation(config) else 1


def cmd_discover(args):
    """发现打印机"""
    print("正在搜索局域网内的拓竹打印机...")
    printers = discover_printers(timeout=args.timeout)

    if not printers:
        print("未发现打印机，请确保打印机在同一网络且已开启")
        return 1

    print(f"\n发现 {len(printers)} 台打印机:")
    for i, p in enumerate(printers, 1):
        print(f"  {i}. IP: {p['ip']} - {p.get('name', 'Unknown')}")
    return 0


def get_queue() -> Optional[PrintQueue]:
    """获取队列实例"""
    config = load_config()
    if not print_config_validation(config, show_success=False):
        return None

    return PrintQueue(
        printer_host=config['host'],
        access_code=config['access_code'],
        serial=config['serial'],
        connection_type=ConnectionType(config.get('method', 'mqtt'))
    )


def cmd_add(args):
    """添加打印任务"""
    queue = get_queue()
    if queue is None:
        return 1

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"错误: 文件不存在: {filepath}")
        return 1

    try:
        job_id = queue.add(
            str(filepath.absolute()),
            name=args.name,
            priority=args.priority
        )
    except Exception as e:
        print(f"错误: 添加任务失败: {e}")
        return 1

    print(f"[OK] 任务已添加 (ID: {job_id})")
    return 0


def cmd_list(args):
    """列出队列"""
    queue = get_queue()
    if queue is None:
        return 1

    jobs = queue.list_queue()

    if not jobs:
        print("队列为空")
        return

    print(f"\n{'序号':<4} {'ID':<10} {'名称':<30} {'状态':<12} {'优先级'}")
    print("-" * 75)
    for job in jobs:
        print(f"{job['index']:<4} {job['id']:<10} {job['name']:<30} "
              f"{job['status']:<12} {job['priority']}")


def cmd_status(args):
    """查看状态"""
    queue = get_queue()
    if queue is None:
        return 1

    status = queue.get_status()

    print(f"\n队列状态: {status['status']}")
    print(f"队列长度: {status['queue_length']}")

    if status['current_job']:
        job = status['current_job']
        print(f"\n当前任务:")
        print(f"  名称: {job['name']}")
        print(f"  状态: {job['status']}")
        print(f"  进度: {job['progress']:.1f}%")
        print(f"  文件: {job['filepath']}")

    printer = status['printer']
    print(f"\n打印机状态:")
    print(f"  打印状态: {printer['print_status']}")
    print(f"  进度: {printer['progress']:.1f}%")
    print(f"  层: {printer['layer']}/{printer['total_layers']}")
    print(f"  热床温度: {printer['bed_temp']}°C")
    print(f"  喷嘴温度: {printer['nozzle_temp']}°C")


def cmd_history(args):
    """查看历史"""
    queue = get_queue()
    if queue is None:
        return 1

    history = queue.get_history(limit=args.limit)

    if not history:
        print("没有打印历史")
        return

    print(f"\n{'ID':<10} {'名称':<30} {'状态':<12} {'完成时间'}")
    print("-" * 80)
    for h in reversed(history):
        completed_at = h.get('completed_at', 'N/A')[:19] if h.get('completed_at') else 'N/A'
        print(f"{h['id']:<10} {h['name']:<30} {h['status']:<12} {completed_at}")


def cmd_start(args):
    """启动队列"""
    queue = get_queue()
    if queue is None:
        return 1

    queue.start()
    print("队列已启动")


def cmd_pause(args):
    """暂停队列"""
    queue = get_queue()
    if queue is None:
        return 1

    queue.pause()
    print("队列已暂停")


def cmd_resume(args):
    """继续队列"""
    queue = get_queue()
    if queue is None:
        return 1

    queue.resume()
    print("队列已继续")


def cmd_stop(args):
    """停止队列"""
    queue = get_queue()
    if queue is None:
        return 1

    queue.stop()
    print("队列已停止")


def cmd_clear(args):
    """清空队列"""
    queue = get_queue()
    if queue is None:
        return 1

    if args.force or input("确认清空队列? (y/N): ").lower() == 'y':
        queue.clear()
        print("队列已清空")


def cmd_remove(args):
    """移除任务"""
    queue = get_queue()
    if queue is None:
        return 1

    if queue.remove(args.job_id):
        print(f"已移除任务: {args.job_id}")
        return 0
    else:
        print(f"未找到任务: {args.job_id}")
        return 1


def cmd_cancel(args):
    """取消正在打印的任务"""
    queue = get_queue()
    if queue is None:
        return 1

    if queue.cancel(args.job_id):
        print(f"已取消任务: {args.job_id}")
        return 0
    else:
        print(f"未找到任务: {args.job_id}")
        return 1


def cmd_watch(args):
    """实时监控打印进度"""
    queue = get_queue()
    if queue is None:
        return 1

    print("开始监控打印进度，按 Ctrl+C 退出...\n")

    try:
        while True:
            status = queue.get_status()

            # 清除行
            print("\033[2K", end="")

            if status['current_job']:
                job = status['current_job']
                print(f"任务: {job['name']} | 状态: {job['status']} | 进度: {job['progress']:.1f}%")
            else:
                print(f"队列状态: {status['status']} | 队列长度: {status['queue_length']}")

            printer = status['printer']
            print(f"打印机: {printer['print_status']} | 层: {printer['layer']}/{printer['total_layers']} | "
                  f"热床: {printer['bed_temp']}°C | 喷嘴: {printer['nozzle_temp']}°C")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n监控已停止")


def main():
    parser = argparse.ArgumentParser(
        description='拓竹自动打印工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 首次使用需要配置打印机
  python scripts/auto_print.py config --host YOUR_PRINTER_IP --access-code YOUR_ACCESS_CODE --serial YOUR_PRINTER_SERIAL
  python scripts/auto_print.py check-config

  # 添加打印任务
  python scripts/auto_print.py add ./model.stl
  python scripts/auto_print.py add ./robot.obj --name my_robot --priority 5

  # 管理队列
  python scripts/auto_print.py list
  python scripts/auto_print.py status
  python scripts/auto_print.py start
  python scripts/auto_print.py pause
  python scripts/auto_print.py resume
  python scripts/auto_print.py stop

  # 监控进度
  python scripts/auto_print.py watch

  # 查看历史
  python scripts/auto_print.py history

  # 发现打印机
  python scripts/auto_print.py discover
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # config - 配置打印机
    config_parser = subparsers.add_parser('config', help='配置打印机连接')
    config_parser.add_argument('--host', required=True, help='打印机IP地址')
    config_parser.add_argument('--access-code', dest='access_code', required=True, help='访问码')
    config_parser.add_argument('--serial', required=True, help='序列号')
    config_parser.add_argument('--method', choices=sorted(SUPPORTED_QUEUE_METHODS),
                               default='mqtt', help='连接方式')

    # check-config - 本地配置检查
    subparsers.add_parser('check-config', help='检查本地打印机配置，不连接打印机')

    # discover - 发现打印机
    discover_parser = subparsers.add_parser('discover', help='发现局域网打印机')
    discover_parser.add_argument('--timeout', type=float, default=3.0, help='搜索超时时间')

    # add - 添加任务
    add_parser = subparsers.add_parser('add', help='添加打印任务')
    add_parser.add_argument('file', help='模型文件路径')
    add_parser.add_argument('--name', help='任务名称')
    add_parser.add_argument('--priority', type=int, default=0, help='优先级')

    # list - 列出队列
    list_parser = subparsers.add_parser('list', help='列出队列')

    # status - 查看状态
    status_parser = subparsers.add_parser('status', help='查看状态')

    # history - 查看历史
    history_parser = subparsers.add_parser('history', help='查看打印历史')
    history_parser.add_argument('--limit', type=int, default=20, help='显示数量')

    # start/pause/resume/stop - 控制队列
    subparsers.add_parser('start', help='启动队列')
    subparsers.add_parser('pause', help='暂停队列')
    subparsers.add_parser('resume', help='继续队列')
    subparsers.add_parser('stop', help='停止队列')

    # clear - 清空队列
    clear_parser = subparsers.add_parser('clear', help='清空队列')
    clear_parser.add_argument('--force', action='store_true', help='强制清空不询问')

    # remove - 移除任务
    remove_parser = subparsers.add_parser('remove', help='移除任务')
    remove_parser.add_argument('job_id', help='任务ID')

    # cancel - 取消任务
    cancel_parser = subparsers.add_parser('cancel', help='取消正在打印的任务')
    cancel_parser.add_argument('job_id', help='任务ID')

    # watch - 监控进度
    watch_parser = subparsers.add_parser('watch', help='实时监控打印进度')
    watch_parser.add_argument('--interval', type=float, default=3.0, help='更新间隔(秒)')

    args = parser.parse_args()

    # 如果没有命令，显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 根据命令调用对应的处理函数
    commands = {
        'config': cmd_config,
        'check-config': cmd_check_config,
        'discover': cmd_discover,
        'add': cmd_add,
        'list': cmd_list,
        'status': cmd_status,
        'history': cmd_history,
        'start': cmd_start,
        'pause': cmd_pause,
        'resume': cmd_resume,
        'stop': cmd_stop,
        'clear': cmd_clear,
        'remove': cmd_remove,
        'cancel': cmd_cancel,
        'watch': cmd_watch,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            result = cmd_func(args)
            return result if isinstance(result, int) else 0
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    # 添加time导入供watch命令使用
    import time
    sys.exit(main())
