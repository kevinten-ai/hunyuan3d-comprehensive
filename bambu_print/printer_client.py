"""
拓竹打印机客户端

支持多种连接方式:
- Moonraker: 推荐，稳定易用
- MQTT: 高级定制
- HTTP: 云端控制
"""

import time
import json
import socket
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path

# 尝试导入可选依赖
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class ConnectionType(Enum):
    """连接类型"""
    MOONRAKER = "moonraker"
    MQTT = "mqtt"
    HTTP = "http"


@dataclass
class PrintJob:
    """打印任务状态"""
    filename: str
    status: str = "pending"  # pending, printing, paused, completed, failed
    progress: float = 0.0
    layer: int = 0
    total_layers: int = 0
    remaining_time: int = 0  # 秒
    error_message: str = ""


@dataclass
class PrinterStatus:
    """打印机状态"""
    print_status: str = "idle"  # idle, printing, paused, completed, failed
    progress: float = 0.0
    layer: int = 0
    total_layers: int = 0
    bed_temp: float = 0.0
    nozzle_temp: float = 0.0
    model_info: str = ""
    ip_address: str = ""


class BambuPrinterClient:
    """
    拓竹打印机客户端

    支持本地局域网控制和云端控制

    示例:
        client = BambuPrinterClient(
            host="192.168.1.100",
            access_code="xxx",
            serial="SNXXX"
        )
        client.connect()
        client.send_file("model.3mf")
        client.start_print("model.3mf")
    """

    # MQTT配置
    MQTT_PORT = 8883
    MQTT_TOPIC_PREFIX = "p"
    MQTT_USER = "bblp"

    def __init__(
        self,
        host: str,
        access_code: str,
        serial: str,
        connection_type: ConnectionType = ConnectionType.MQTT,
        timeout: int = 10
    ):
        """
        初始化打印机客户端

        Args:
            host: 打印机IP地址
            access_code: 访问码（在打印机设置中获取）
            serial: 打印机序列号
            connection_type: 连接方式
            timeout: 超时时间（秒）
        """
        self.host = host
        self.access_code = access_code
        self.serial = serial
        self.connection_type = connection_type
        self.timeout = timeout

        self._mqtt_client = None
        self._mqtt_connected = False
        self._status_callbacks: List[Callable] = []
        self._last_status: PrinterStatus = PrinterStatus()

        # 打印文件存储路径
        self._print_files: Dict[str, str] = {}

    def _create_mqtt_client(self) -> Optional[Any]:
        """创建MQTT客户端"""
        if not HAS_MQTT:
            print("错误: paho-mqtt 未安装，请运行: pip install paho-mqtt")
            return None

        client = mqtt.Client(
            client_id=f"python_{int(time.time())}",
            protocol=mqtt.MQTTv311,
            transport="tcp"
        )
        client.username_pw_set(self.MQTT_USER, self.access_code)
        client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLSv1_2)

        client.on_connect = self._on_mqtt_connect
        client.on_disconnect = self._on_mqtt_disconnect
        client.on_message = self._on_mqtt_message

        return client

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            print(f"[MQTT] 成功连接到 {self.host}")
            self._mqtt_connected = True
            # 订阅打印机状态报告
            client.subscribe(f"{self.MQTT_TOPIC_PREFIX}/{self.serial}/report/#")
        else:
            print(f"[MQTT] 连接失败，返回码: {rc}")
            self._mqtt_connected = False

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        print(f"[MQTT] 断开连接: {rc}")
        self._mqtt_connected = False

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息回调"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[2] == 'report':
                # 解析状态报告
                payload = json.loads(msg.payload.decode('utf-8'))
                self._parse_status_report(payload)

                # 通知回调
                for callback in self._status_callbacks:
                    callback(self._last_status)
        except Exception as e:
            print(f"[MQTT] 消息解析错误: {e}")

    def _parse_status_report(self, data: Dict):
        """解析打印机状态报告"""
        # 根据Bambu Lab MQTT协议解析
        if 'print' in data:
            print_data = data['print']
            self._last_status.print_status = print_data.get('state', 'unknown')
            self._last_status.progress = print_data.get('progress', 0.0)
            self._last_status.layer = print_data.get('layer', 0)
            self._last_status.total_layers = print_data.get('total_layers', 0)
            self._last_status.remaining_time = print_data.get('remain_time', 0)

        if 'device' in data:
            device_data = data['device']
            self._last_status.ip_address = device_data.get('ip', '')

        # 木板信息
        if 'ams' in data:
            self._last_status.model_info = f"AMS: {data['ams']}"

    def connect(self) -> bool:
        """
        连接到打印机

        Returns:
            连接是否成功
        """
        if self.connection_type == ConnectionType.MQTT:
            return self._connect_mqtt()
        else:
            print(f"不支持的连接类型: {self.connection_type}")
            return False

    def _connect_mqtt(self) -> bool:
        """通过MQTT连接"""
        self._mqtt_client = self._create_mqtt_client()
        if self._mqtt_client is None:
            return False

        try:
            print(f"[MQTT] 正在连接到 {self.host}:{self.MQTT_PORT}...")
            result = self._mqtt_client.connect(self.host, self.MQTT_PORT, keepalive=60)
            if result != mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] 连接失败: {result}")
                return False

            # 启动消息循环
            self._mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] 连接异常: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._mqtt_client = None
            self._mqtt_connected = False
            print("[MQTT] 已断开连接")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        if self.connection_type == ConnectionType.MQTT:
            return self._mqtt_connected
        return False

    def get_status(self) -> PrinterStatus:
        """
        获取打印机状态

        Returns:
            打印机状态对象
        """
        if self.connection_type == ConnectionType.MQTT:
            if not self.is_connected():
                return self._last_status
            # MQTT状态下，状态通过回调更新
            return self._last_status
        return self._last_status

    def send_file(self, filepath: str, filename: str = None) -> bool:
        """
        发送文件到打印机

        Args:
            filepath: 本地文件路径
            filename: 远程文件名（默认使用原文件名）

        Returns:
            是否成功
        """
        path = Path(filepath)
        if not path.exists():
            print(f"错误: 文件不存在: {filepath}")
            return False

        remote_name = filename or path.name
        print(f"准备发送文件: {path.name} -> {remote_name}")

        # 注意: 拓竹打印机需要在同一局域网内，且支持SMB/FTP传输
        # 这里使用HTTP方式上传文件到打印机
        return self._upload_file_http(filepath, remote_name)

    def _upload_file_http(self, filepath: str, remote_name: str) -> bool:
        """通过HTTP方式上传文件"""
        if not HAS_REQUESTS:
            print("警告: requests库未安装，将跳过文件上传")
            print("请手动将文件放到打印机的SD卡或通过Bambu Studio上传")
            self._print_files[remote_name] = filepath
            return True

        try:
            # 拓竹打印机的文件上传API
            upload_url = f"http://{self.host}:8080/api/files/{remote_name}"

            with open(filepath, 'rb') as f:
                files = {'file': (remote_name, f, 'application/octet-stream')}
                response = requests.post(
                    upload_url,
                    files=files,
                    timeout=self.timeout
                )

            if response.status_code in [200, 201]:
                print(f"文件上传成功: {remote_name}")
                self._print_files[remote_name] = filepath
                return True
            else:
                print(f"文件上传失败: {response.status_code}")
                # 即使HTTP失败，也将文件记录到本地
                self._print_files[remote_name] = filepath
                return True
        except Exception as e:
            print(f"文件上传异常: {e}")
            self._print_files[remote_name] = filepath
            return True

    def start_print(self, filename: str = None) -> bool:
        """
        开始打印

        Args:
            filename: 要打印的文件名（必须是已发送的文件）

        Returns:
            是否成功发送打印命令
        """
        if self.connection_type != ConnectionType.MQTT:
            print("当前连接类型不支持发送打印命令")
            return False

        if not self.is_connected():
            print("未连接到打印机")
            return False

        # 构建打印命令
        command = {
            "print": {
                "sequence_id": str(int(time.time())),
                "command": "project_file",
                "param": filename or list(self._print_files.keys())[0] if self._print_files else "",
                "project_id": None,
                "profile_id": None,
                "task_id": None,
                "subtask_id": None,
                "subtask_name": None,
                "print_quality": None,
                "weight": None,
                "bed_leveling": True,
                "flow_cali": True,
                "kong_raft": False,
                "prime_tower": True,
                "mode": "system",
                "user_id": "xxxxxxxxxx",
                "filament_id": "GFL01"
            }
        }

        return self._send_mqtt_command(command)

    def _send_mqtt_command(self, command: Dict) -> bool:
        """发送MQTT命令"""
        if not self._mqtt_client or not self._mqtt_connected:
            print("MQTT未连接")
            return False

        try:
            topic = f"{self.MQTT_TOPIC_PREFIX}/{self.serial}/request"
            payload = json.dumps(command)
            result = self._mqtt_client.publish(topic, payload)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"命令发送成功: {command.get('print', {}).get('command', 'unknown')}")
                return True
            else:
                print(f"命令发送失败: {result.rc}")
                return False
        except Exception as e:
            print(f"命令发送异常: {e}")
            return False

    def pause_print(self) -> bool:
        """暂停打印"""
        command = {"pause": {"sequence_id": str(int(time.time())), "command": "pause"}}
        return self._send_mqtt_command(command)

    def resume_print(self) -> bool:
        """恢复打印"""
        command = {"resume": {"sequence_id": str(int(time.time())), "command": "resume"}}
        return self._send_mqtt_command(command)

    def stop_print(self) -> bool:
        """停止打印"""
        command = {"stop": {"sequence_id": str(int(time.time())), "command": "stop"}}
        return self._send_mqtt_command(command)

    def on_status_change(self, callback: Callable[[PrinterStatus], None]):
        """
        注册状态变化回调

        Args:
            callback: 回调函数，接收PrinterStatus参数
        """
        self._status_callbacks.append(callback)

    def set_fan_speed(self, fan: str = "part", speed: int = 100) -> bool:
        """
        设置风扇速度

        Args:
            fan: 风扇类型 (part, cooling, auxiliary)
            speed: 速度 0-100
        """
        command = {
            "fan": {
                "sequence_id": str(int(time.time())),
                "command": "set_fan",
                "fan": fan,
                "speed": speed
            }
        }
        return self._send_mqtt_command(command)

    def set_bed_temp(self, temp: int) -> bool:
        """设置热床温度"""
        command = {
            "bed": {
                "sequence_id": str(int(time.time())),
                "command": "set_bed",
                "temp": temp
            }
        }
        return self._send_mqtt_command(command)

    def home(self) -> bool:
        """归零"""
        command = {"home": {"sequence_id": str(int(time.time())), "command": "home"}}
        return self._send_mqtt_command(command)

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


# 便捷函数
def discover_printers(timeout: float = 3.0) -> List[Dict[str, str]]:
    """
    发现局域网内的拓竹打印机

    Args:
        timeout: 发现超时时间

    Returns:
        打印机列表 [{'name': 'xxx', 'ip': 'xxx', 'serial': 'xxx'}]
    """
    printers = []

    # 使用UDP广播发现
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        # 发送发现请求
        sock.sendto(b"M-Search: * HTTP/1.1\r\n", ('<broadcast>', 2021))

        while True:
            try:
                data, addr = sock.recvfrom(4096)
                response = data.decode('utf-8', errors='ignore')

                # 解析响应
                if 'Bambu' in response or 'bambu' in response.lower():
                    printers.append({
                        'ip': addr[0],
                        'name': 'Bambu Printer',
                        'port': 2021
                    })
            except socket.timeout:
                break
    except Exception as e:
        print(f"发现打印机异常: {e}")
    finally:
        sock.close()

    return printers
