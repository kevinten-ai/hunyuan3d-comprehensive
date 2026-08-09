"""
拓竹(Bambu Lab)打印机自动打印模块

支持多种连接方式:
- MQTT/TLS: Bambu LAN Developer Mode 状态与控制
- FTPS: 通过系统 curl 上传 ready-to-print 文件
- Moonraker/HTTP: 枚举保留，当前未实现连接流程

示例:
    from bambu_print import BambuPrinterClient, PrintQueue, ConnectionType

    # 创建客户端
    client = BambuPrinterClient(
            host="YOUR_PRINTER_IP",
            access_code="YOUR_ACCESS_CODE",
            serial="YOUR_PRINTER_SERIAL",
            connection_type=ConnectionType.MQTT
    )

    # 连接并打印
    client.connect()
    client.send_file("bambu_project.3mf")
    client.start_print("bambu_project.3mf")
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
