"""
拓竹(Bambu Lab)打印机自动打印模块

支持多种连接方式:
- MQTT: 当前实现的本地控制方式
- HTTP: 仅用于文件上传尝试，仍需真实设备验证
- Moonraker: 枚举保留，当前未实现连接流程

示例:
    from bambu_print import BambuPrinterClient, PrintQueue, ConnectionType

    # 创建客户端
    client = BambuPrinterClient(
            host="192.168.1.100",
            access_code="your-access-code",
            serial="SNXXX",
            connection_type=ConnectionType.MQTT
    )

    # 连接并打印
    client.connect()
    client.send_file("model.3mf")
    client.start_print("model.3mf")
"""

from .printer_client import BambuPrinterClient, ConnectionType, PrintJob, discover_printers
from .print_queue import PrintQueue, QueueStatus, QueuedJob

__all__ = [
    'BambuPrinterClient',
    'ConnectionType',
    'PrintJob',
    'discover_printers',
    'PrintQueue',
    'QueueStatus',
    'QueuedJob',
]

__version__ = '1.0.0'
