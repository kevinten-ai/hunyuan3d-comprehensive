#!/usr/bin/env python3
"""
拓竹自动打印命令行工具

功能:
- 配置打印机连接
- 添加打印任务到队列
- 管理打印队列
- 监控打印进度

示例:
    # 配置打印机
    python auto_print.py config --host 192.168.1.100 --access-code xxx --serial SNXXX

    # 添加打印任务
    python auto_print.py add ./model.stl --name "我的模型"

    # 查看队列
    python auto_print.py list

    # 查看状态
    python auto_print.py status

    # 控制队列
    python auto_print.py start
    python auto_print.py pause
    python auto_print.py resume
    python auto_print.py stop

    # 发现打印机
    python auto_print.py discover
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bambu_print import PrintQueue, ConnectionType, discover_printers

# 配置文件路径
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "printer.json"


def load_config() -> Optional[dict]:
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        return None
    import json
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict):
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import json
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def cmd_config(args):
    """配置打印机"""
    config = {
        'host': args.host,
        'access_code': args.access_code,
        'serial': args.serial,
        'method': args.method
    }
    save_config(config)
    print(f"✓ 配置已保存到 {CONFIG_FILE}")
    print(f"  主机: {args.host}")
    print(f"  序列号: {args.serial}")
    print(f"  连接方式: {args.method}")


def cmd_discover(args):
    """发现打印机"""
    print("正在搜索局域网内的拓竹打印机...")
    printers = discover_printers(timeout=args.timeout)

    if not printers:
        print("未发现打印机，请确保打印机在同一网络且已开启")
        return

    print(f"\n发现 {len(printers)} 台打印机:")
    for i, p in enumerate(printers, 1):
        print(f"  {i}. IP: {p['ip']} - {p.get('name', 'Unknown')}")


def get_queue() -> Optional[PrintQueue]:
    """获取队列实例"""
    config = load_config()
    if not config:
        print("错误: 请先配置打印机")
        print("运行: python auto_print.py config --host <ip> --access-code <code> --serial <sn>")
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
        return

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"错误: 文件不存在: {filepath}")
        return

    job_id = queue.add(
        str(filepath.absolute()),
        name=args.name,
        priority=args.priority
    )
    print(f"✓ 任务已添加 (ID: {job_id})")


def cmd_list(args):
    """列出队列"""
    queue = get_queue()
    if queue is None:
        return

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
        return

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
        return

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
        return

    queue.start()
    print("队列已启动")


def cmd_pause(args):
    """暂停队列"""
    queue = get_queue()
    if queue is None:
        return

    queue.pause()
    print("队列已暂停")


def cmd_resume(args):
    """继续队列"""
    queue = get_queue()
    if queue is None:
        return

    queue.resume()
    print("队列已继续")


def cmd_stop(args):
    """停止队列"""
    queue = get_queue()
    if queue is None:
        return

    queue.stop()
    print("队列已停止")


def cmd_clear(args):
    """清空队列"""
    queue = get_queue()
    if queue is None:
        return

    if args.force or input("确认清空队列? (y/N): ").lower() == 'y':
        queue.clear()
        print("队列已清空")


def cmd_remove(args):
    """移除任务"""
    queue = get_queue()
    if queue is None:
        return

    if queue.remove(args.job_id):
        print(f"已移除任务: {args.job_id}")
    else:
        print(f"未找到任务: {args.job_id}")


def cmd_cancel(args):
    """取消正在打印的任务"""
    queue = get_queue()
    if queue is None:
        return

    if queue.cancel(args.job_id):
        print(f"已取消任务: {args.job_id}")
    else:
        print(f"未找到任务: {args.job_id}")


def cmd_watch(args):
    """实时监控打印进度"""
    queue = get_queue()
    if queue is None:
        return

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
  python auto_print.py config --host 192.168.1.100 --access-code YOUR_CODE --serial SNXXX

  # 添加打印任务
  python auto_print.py add ./model.stl
  python auto_print.py add ./robot.obj --name my_robot --priority 5

  # 管理队列
  python auto_print.py list
  python auto_print.py status
  python auto_print.py start
  python auto_print.py pause
  python auto_print.py resume
  python auto_print.py stop

  # 监控进度
  python auto_print.py watch

  # 查看历史
  python auto_print.py history

  # 发现打印机
  python auto_print.py discover
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # config - 配置打印机
    config_parser = subparsers.add_parser('config', help='配置打印机连接')
    config_parser.add_argument('--host', required=True, help='打印机IP地址')
    config_parser.add_argument('--access-code', dest='access_code', required=True, help='访问码')
    config_parser.add_argument('--serial', required=True, help='序列号')
    config_parser.add_argument('--method', choices=['mqtt', 'http'],
                               default='mqtt', help='连接方式')

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
        return

    # 根据命令调用对应的处理函数
    commands = {
        'config': cmd_config,
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
            cmd_func(args)
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
    else:
        parser.print_help()


if __name__ == '__main__':
    # 添加time导入供watch命令使用
    import time
    main()
