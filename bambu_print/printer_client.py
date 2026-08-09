"""
拓竹打印机客户端

支持多种连接方式:
- MQTT: Bambu LAN Developer Mode 本地控制方式
- FTPS: 通过 curl 上传切片文件到打印机 SD 卡
- Moonraker/HTTP: 枚举保留，当前未实现连接流程
"""

import hashlib
import json
import os
import re
import select
import shutil
import socket
import ssl
import subprocess
import threading
import time
import unicodedata
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path
from urllib.parse import quote, urlparse

# 尝试导入可选依赖
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

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
    remaining_time: int = 0  # 秒


class BambuPrinterClient:
    """
    拓竹打印机客户端

    支持本地局域网 FTPS 上传和 MQTT 控制。现代固件通常需要在打印机
    上显式启用 LAN Developer Mode。

    示例:
        client = BambuPrinterClient(
            host="YOUR_PRINTER_IP",
            access_code="YOUR_ACCESS_CODE",
            serial="YOUR_PRINTER_SERIAL"
        )
        client.connect()
        client.send_file("bambu_project.3mf")
        client.start_print("bambu_project.3mf")
    """

    # MQTT配置
    MQTT_PORT = 8883
    MQTT_TOPIC_PREFIX = "device"
    MQTT_USER = "bblp"
    FTPS_PORT = 990
    FTPS_USER = "bblp"

    def __init__(
        self,
        host: str,
        access_code: str,
        serial: str,
        connection_type: ConnectionType = ConnectionType.MQTT,
        timeout: int = 10,
        upload_timeout: int = 600,
        use_ams: bool = False,
        ams_mapping: Optional[List[int]] = None,
        timelapse: bool = False,
        ca_cert: Optional[str] = None,
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
        self.upload_timeout = upload_timeout
        self.use_ams = use_ams
        self.ams_mapping = list(ams_mapping or [-1, -1, -1, -1, 0])
        self.timelapse = timelapse
        self.ca_cert = self._resolve_ca_cert(ca_cert)

        self._mqtt_client = None
        self._mqtt_connected = False
        self._mqtt_connect_event = threading.Event()
        self._status_callbacks: List[Callable] = []
        self._last_status: PrinterStatus = PrinterStatus()
        self._sequence_lock = threading.Lock()
        self._sequence_value = int(time.time() * 1000)
        self._pending_commands: Dict[str, Dict[str, Any]] = {}

        # 打印文件存储路径
        self._print_files: Dict[str, str] = {}
        self._last_uploaded_file: Optional[str] = None

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
        if self.ca_cert:
            client.tls_set(
                ca_certs=self.ca_cert,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
        else:
            print("[MQTT] 警告: 未找到 Bambu printer.cer，TLS 将不验证设备证书")
            client.tls_set(
                cert_reqs=ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
        # Printer certificates generally identify the device, not its LAN IP.
        # Keep hostname checks disabled; with printer.cer present the certificate
        # chain is still validated against Bambu's local printer CA.
        client.tls_insecure_set(True)

        client.on_connect = self._on_mqtt_connect
        client.on_disconnect = self._on_mqtt_disconnect
        client.on_message = self._on_mqtt_message

        return client

    @staticmethod
    def _resolve_ca_cert(explicit_path: Optional[str]) -> Optional[str]:
        """Find Bambu Studio's printer CA without copying it into the repository."""
        candidates = [explicit_path, os.environ.get('BAMBU_PRINTER_CA_CERT')]
        slicer_exe = os.environ.get('BAMBU_SLICER_EXE')
        if slicer_exe:
            candidates.append(
                str(Path(slicer_exe).expanduser().parent / 'resources' / 'cert' / 'printer.cer')
            )
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if path.is_file():
                return str(path.resolve())
        return None

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            print(f"[MQTT] 成功连接到 {self.host}")
            self._mqtt_connected = True
            # 订阅打印机状态报告
            client.subscribe(f"{self.MQTT_TOPIC_PREFIX}/{self.serial}/report")
        else:
            print(f"[MQTT] 连接失败，返回码: {rc}")
            self._mqtt_connected = False
        self._mqtt_connect_event.set()

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        print(f"[MQTT] 断开连接: {rc}")
        self._mqtt_connected = False

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息回调"""
        try:
            topic_parts = msg.topic.split('/')
            if (
                len(topic_parts) >= 3
                and topic_parts[0] == self.MQTT_TOPIC_PREFIX
                and topic_parts[2] == 'report'
            ):
                # 解析状态报告
                payload = json.loads(msg.payload.decode('utf-8'))
                self._parse_status_report(payload)
                self._resolve_command_response(payload)

                # 通知回调
                for callback in self._status_callbacks:
                    callback(self._last_status)
        except Exception as e:
            print(f"[MQTT] 消息解析错误: {e}")

    def _parse_status_report(self, data: Dict):
        """解析打印机状态报告"""
        # P1-series push_status uses gcode_state/mc_* and may send only deltas.
        # Keep the legacy aliases for older tests and captured payloads.
        if 'print' in data:
            print_data = data['print']
            state = print_data.get('gcode_state', print_data.get('state'))
            if state is not None:
                state_map = {
                    'IDLE': 'idle',
                    'RUNNING': 'printing',
                    'PREPARE': 'printing',
                    'PAUSE': 'paused',
                    'FINISH': 'completed',
                    'FAILED': 'failed',
                }
                self._last_status.print_status = state_map.get(
                    str(state).upper(), str(state).lower()
                )

            progress = print_data.get('mc_percent', print_data.get('progress'))
            if progress is not None:
                self._last_status.progress = float(progress)
            layer = print_data.get('layer_num', print_data.get('layer'))
            if layer is not None:
                self._last_status.layer = int(layer)
            total_layers = print_data.get('total_layer_num', print_data.get('total_layers'))
            if total_layers is not None:
                self._last_status.total_layers = int(total_layers)
            if 'mc_remaining_time' in print_data:
                # Firmware reports remaining time in minutes.
                self._last_status.remaining_time = int(
                    float(print_data['mc_remaining_time']) * 60
                )
            elif 'remain_time' in print_data:
                self._last_status.remaining_time = int(print_data['remain_time'])
            if 'bed_temper' in print_data:
                self._last_status.bed_temp = float(print_data['bed_temper'])
            if 'nozzle_temper' in print_data:
                self._last_status.nozzle_temp = float(print_data['nozzle_temper'])
            if print_data.get('gcode_file'):
                self._last_status.model_info = str(print_data['gcode_file'])

        if 'device' in data:
            device_data = data['device']
            self._last_status.ip_address = device_data.get('ip', '')

        # 木板信息
        if 'ams' in data:
            self._last_status.model_info = f"AMS: {data['ams']}"

    def _resolve_command_response(self, payload: Dict[str, Any]) -> None:
        """Wake a command waiter when the printer reports its sequence result."""
        for value in payload.values():
            if not isinstance(value, dict):
                continue
            sequence_id = str(value.get('sequence_id', ''))
            pending = self._pending_commands.get(sequence_id)
            if pending is None or 'result' not in value:
                continue
            pending['response'] = value
            pending['event'].set()

    def _next_sequence_id(self) -> str:
        with self._sequence_lock:
            self._sequence_value += 1
            return str(self._sequence_value)

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
        self._mqtt_connect_event.clear()
        self._mqtt_connected = False

        try:
            print(f"[MQTT] 正在连接到 {self.host}:{self.MQTT_PORT}...")
            result = self._mqtt_client.connect(self.host, self.MQTT_PORT, keepalive=60)
            if result != mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] 连接失败: {result}")
                return False

            # 启动消息循环
            self._mqtt_client.loop_start()
            if not self._mqtt_connect_event.wait(self.timeout):
                print("[MQTT] 连接确认超时")
                self._cleanup_failed_mqtt_connection()
                return False

            if not self._mqtt_connected:
                self._cleanup_failed_mqtt_connection()
                return False

            # P1 printers emit delta status objects. Request one full snapshot
            # after connecting, then rely on normal incremental reports.
            self.request_full_status()
            return True
        except Exception as e:
            print(f"[MQTT] 连接异常: {e}")
            self._cleanup_failed_mqtt_connection()
            return False

    def _cleanup_failed_mqtt_connection(self):
        """Clean up a failed MQTT connection attempt."""
        if not self._mqtt_client:
            return
        try:
            self._mqtt_client.loop_stop()
        except Exception:
            pass
        try:
            self._mqtt_client.disconnect()
        except Exception:
            pass
        self._mqtt_client = None
        self._mqtt_connected = False

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
        if not path.is_file():
            print(f"错误: 文件不存在: {filepath}")
            return False
        if path.stat().st_size <= 0:
            print(f"错误: 文件为空: {filepath}")
            return False

        try:
            remote_name = self._normalize_remote_name(filename or path.name)
        except ValueError as exc:
            print(f"错误: {exc}")
            return False
        print(f"准备发送文件: {path.name} -> {remote_name}")

        if not self._upload_file_ftps(path, remote_name):
            return False
        self._print_files[remote_name] = str(path)
        self._last_uploaded_file = remote_name
        return True

    @staticmethod
    def _normalize_remote_name(filename: str) -> str:
        """Return a simple ASCII SD-card filename accepted by Bambu FTPS."""
        basename = Path(filename).name
        lower = basename.lower()
        if lower.endswith('.gcode.3mf'):
            suffix = '.gcode.3mf'
            stem = basename[:-len(suffix)]
        else:
            suffix = Path(basename).suffix.lower()
            stem = basename[:-len(suffix)] if suffix else basename
        if suffix not in {'.3mf', '.gcode.3mf', '.gcode', '.bgcode'}:
            raise ValueError(f"不支持上传到打印机的文件扩展名: {suffix or '(none)'}")
        if re.fullmatch(r'[A-Za-z0-9._-]+', basename):
            return basename

        ascii_stem = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode()
        safe_stem = re.sub(r'[^A-Za-z0-9._-]+', '_', ascii_stem).strip('._-')
        digest = hashlib.sha256(basename.encode('utf-8')).hexdigest()[:8]
        return f"{(safe_stem or 'print')[:48]}_{digest}{suffix}"

    @staticmethod
    def _curl_config_value(value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '').replace('\n', '')

    def _upload_file_ftps(
        self,
        filepath: Path,
        remote_name: str,
        runner=subprocess.run,
    ) -> bool:
        """Upload through Bambu's implicit FTPS service without CLI secrets."""
        curl = shutil.which('curl.exe') or shutil.which('curl')
        if not curl:
            print("错误: 未找到 curl，无法通过 FTPS 上传文件")
            return False

        credentials = self._curl_config_value(f"{self.FTPS_USER}:{self.access_code}")
        local_path = self._curl_config_value(filepath.resolve().as_posix())
        remote_url = self._curl_config_value(
            f"ftps://{self.host}:{self.FTPS_PORT}/{quote(remote_name)}"
        )
        curl_config = "\n".join(
            [
                'fail',
                'silent',
                'show-error',
                'insecure',
                'ftp-pasv',
                'ssl-reqd',
                f'connect-timeout = "{self.timeout}"',
                f'max-time = "{self.upload_timeout}"',
                f'user = "{credentials}"',
                f'upload-file = "{local_path}"',
                f'url = "{remote_url}"',
            ]
        )
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            completed = runner(
                [curl, '--config', '-'],
                input=curl_config,
                capture_output=True,
                text=True,
                timeout=self.upload_timeout + 5,
                creationflags=creationflags,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"FTPS 上传异常: {exc}")
            return False
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()
            print(f"FTPS 上传失败: {detail[-1] if detail else f'exit {completed.returncode}'}")
            return False
        print(f"文件上传成功: {remote_name}")
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

        if not filename and not self._print_files:
            print("没有可打印文件，请先上传文件或显式指定打印文件名")
            return False

        try:
            command = self._build_start_print_command(filename)
        except ValueError as exc:
            print(f"错误: {exc}")
            return False
        return self._send_mqtt_command(command)

    def _build_start_print_command(self, filename: str = None) -> Dict[str, Any]:
        """Build a Bambu project_file command without sending it."""
        remote_file = filename or self._last_uploaded_file
        if remote_file is None:
            remote_file = next(iter(self._print_files), "")
        remote_file = self._normalize_remote_name(remote_file)
        sequence_id = self._next_sequence_id()
        if remote_file.lower().endswith(('.3mf', '.gcode.3mf')):
            return {
                "print": {
                    "sequence_id": sequence_id,
                    "command": "project_file",
                    "param": "Metadata/plate_1.gcode",
                    "project_id": "0",
                    "profile_id": "0",
                    "task_id": "0",
                    "subtask_id": "0",
                    "subtask_name": remote_file,
                    "file": remote_file,
                    "url": f"ftp:///{remote_file}",
                    "md5": "",
                    "timelapse": self.timelapse,
                    "bed_type": "auto",
                    "bed_leveling": True,
                    "bed_levelling": True,
                    "flow_cali": True,
                    "vibration_cali": True,
                    "layer_inspect": True,
                    "ams_mapping": self.ams_mapping if self.use_ams else [],
                    "use_ams": self.use_ams,
                }
            }
        return {
            "print": {
                "sequence_id": sequence_id,
                "command": "gcode_file",
                "param": remote_file,
            }
        }

    def _send_mqtt_command(self, command: Dict, wait_for_ack: bool = True) -> bool:
        """Publish a command and confirm the printer response when requested."""
        if not self._mqtt_client or not self._mqtt_connected:
            print("MQTT未连接")
            return False

        body = next((value for value in command.values() if isinstance(value, dict)), None)
        if body is None:
            print("MQTT命令结构无效")
            return False
        sequence_id = str(body.setdefault('sequence_id', self._next_sequence_id()))
        pending = {'event': threading.Event(), 'response': None}
        if wait_for_ack:
            self._pending_commands[sequence_id] = pending
        try:
            topic = f"{self.MQTT_TOPIC_PREFIX}/{self.serial}/request"
            payload = json.dumps(command)
            result = self._mqtt_client.publish(topic, payload)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"命令发送失败: {result.rc}")
                return False
            command_name = body.get('command', 'unknown')
            if not wait_for_ack:
                print(f"命令已发送: {command_name}")
                return True
            if not pending['event'].wait(self.timeout):
                print(f"命令确认超时: {command_name}")
                return False
            response = pending['response'] or {}
            if str(response.get('result', '')).lower() != 'success':
                reason = response.get('reason') or response.get('result') or 'unknown'
                print(f"打印机拒绝命令 {command_name}: {reason}")
                return False
            print(f"打印机已确认命令: {command_name}")
            return True
        except Exception as e:
            print(f"命令发送异常: {e}")
            return False
        finally:
            self._pending_commands.pop(sequence_id, None)

    def pause_print(self) -> bool:
        """暂停打印"""
        command = {"print": {"sequence_id": self._next_sequence_id(), "command": "pause"}}
        return self._send_mqtt_command(command)

    def resume_print(self) -> bool:
        """恢复打印"""
        command = {"print": {"sequence_id": self._next_sequence_id(), "command": "resume"}}
        return self._send_mqtt_command(command)

    def stop_print(self) -> bool:
        """停止打印"""
        command = {"print": {"sequence_id": self._next_sequence_id(), "command": "stop"}}
        return self._send_mqtt_command(command)

    def request_full_status(self) -> bool:
        """Request a full status snapshot without waiting for a command ack."""
        command = {
            "pushing": {
                "sequence_id": self._next_sequence_id(),
                "command": "pushall",
                "version": 1,
                "push_target": 1,
            }
        }
        return self._send_mqtt_command(command, wait_for_ack=False)

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
        fan_ports = {
            "part": 1,
            "cooling": 1,
            "auxiliary": 2,
            "chamber": 3,
        }
        if fan not in fan_ports:
            print(f"不支持的风扇类型: {fan}")
            return False
        if isinstance(speed, bool) or not isinstance(speed, int) or not 0 <= speed <= 100:
            print("风扇速度必须是 0..100 的整数")
            return False
        pwm = round(speed * 255 / 100)
        return self._send_gcode_line(f"M106 P{fan_ports[fan]} S{pwm}")

    def set_bed_temp(self, temp: int) -> bool:
        """设置热床温度"""
        if isinstance(temp, bool) or not isinstance(temp, int) or not 0 <= temp <= 120:
            print("热床温度必须是 0..120 的整数")
            return False
        return self._send_gcode_line(f"M140 S{temp}")

    def home(self) -> bool:
        """归零"""
        return self._send_gcode_line("G28")

    def _send_gcode_line(self, line: str) -> bool:
        """Send a single trusted G-code line through the printer command topic."""
        command = {
            "print": {
                "sequence_id": self._next_sequence_id(),
                "command": "gcode_line",
                "param": f"{line.rstrip()}\n",
            }
        }
        return self._send_mqtt_command(command)

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


# 便捷函数
def _parse_discovery_packet(
    data: bytes,
    source_ip: str,
) -> Optional[Dict[str, Any]]:
    """Parse one Bambu SSDP-style NOTIFY announcement."""
    response = data.decode('utf-8', errors='ignore')
    lines = response.replace('\r\n', '\n').split('\n')
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        headers[key.strip().lower()] = value.strip()

    device_type = headers.get('nt', '').lower()
    if (
        'bambulab-com:device:3dprinter' not in device_type
        and 'devmodel.bambu.com' not in headers
    ):
        return None

    location = headers.get('location', '')
    if '://' in location:
        location = urlparse(location).hostname or ''
    ip_address = location or source_ip

    return {
        'ip': ip_address,
        'name': headers.get('devname.bambu.com', 'Bambu Printer'),
        'serial': headers.get('usn', ''),
        'model': headers.get('devmodel.bambu.com', ''),
        'signal': headers.get('devsignal.bambu.com', ''),
        'connection': headers.get('devconnect.bambu.com', ''),
        'firmware': headers.get('devversion.bambu.com', ''),
        'port': 2021,
    }


def discover_printers(timeout: float = 6.0) -> List[Dict[str, Any]]:
    """
    发现局域网内的拓竹打印机

    Args:
        timeout: 发现超时时间

    Returns:
        打印机列表 [{'name': 'xxx', 'ip': 'xxx', 'serial': 'xxx'}]
    """
    printers: Dict[str, Dict[str, Any]] = {}
    sockets = []

    # Bambu printers announce themselves roughly every five seconds. Depending
    # on model/firmware, notifications arrive on UDP 2021 or 1990.
    for port in (2021, 1990):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
            sock.setblocking(False)
            sockets.append(sock)
        except OSError:
            sock.close()

    if not sockets:
        print("发现打印机失败: UDP 2021/1990 无法监听，端口可能被切片器占用")
        return []

    deadline = time.monotonic() + max(0.0, timeout)
    try:
        while sockets:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            readable, _, _ = select.select(sockets, [], [], remaining)
            if not readable:
                break
            for sock in readable:
                try:
                    data, addr = sock.recvfrom(8192)
                except (BlockingIOError, OSError):
                    continue
                printer = _parse_discovery_packet(data, addr[0])
                if printer is None:
                    continue
                key = printer['serial'] or printer['ip']
                printers[str(key)] = printer
    finally:
        for sock in sockets:
            sock.close()

    return list(printers.values())
