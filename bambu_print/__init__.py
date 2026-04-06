"""
拓竹(Bambu Lab)打印机自动打印模块

支持多种连接方式:
- Moonraker: 推荐，稳定易用
- MQTT: 高级定制
- HTTP: 云端控制

示例:
    from bambu_print import BambuPrinterClient, PrintQueue, ConnectionType

    # 创建客户端
    client = BambuPrinterClient(
        host="192.168.1.100",
        access_code="your-access-code",
        serial="SNXXX",
        connection_type=ConnectionType.MOONRAKER
    )

    # 连接并打印
    client.connect()
    client.send_file("model.3mf")
    client.start_print("model.3mf")
"""

from .printer_client import BambuPrinterClient, ConnectionType, PrintJob
from .print_queue import PrintQueue, QueueStatus, QueuedJob

__all__ = [
    'BambuPrinterClient',
    'ConnectionType',
    'PrintJob',
    'PrintQueue',
    'QueueStatus',
    'QueuedJob',
]

__version__ = '1.0.0'
