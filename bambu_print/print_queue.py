"""
打印队列管理器

支持:
- 队列添加/删除/暂停/继续
- 持久化队列到文件
- 打印进度监控
- 打印完成通知
"""

import os
import time
import json
import uuid
import threading
import zipfile
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

from .printer_client import BambuPrinterClient, ConnectionType, PrinterStatus


PRINT_READY_EXTENSIONS = ('.3mf', '.gcode', '.bgcode')
BAMBU_PROJECT_3MF_MARKERS = (
    'Metadata/project_settings.config',
    'Metadata/slice_info.config',
)


def is_bambu_project_3mf(filepath: str) -> bool:
    """Return True when a 3MF looks like a sliced Bambu/Orca project package."""
    try:
        with zipfile.ZipFile(filepath) as package:
            names = {name.replace('\\', '/') for name in package.namelist()}
    except (OSError, zipfile.BadZipFile):
        return False

    return any(marker in names for marker in BAMBU_PROJECT_3MF_MARKERS)


class QueueStatus(Enum):
    """队列状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    PRINTING = "printing"   # 正在打印
    PAUSED = "paused"       # 暂停
    ERROR = "error"         # 错误
    STOPPED = "stopped"      # 已停止


@dataclass
class QueuedJob:
    """队列中的任务"""
    id: str
    filepath: str
    name: str
    priority: int = 0
    added_time: float = field(default_factory=time.time)
    status: str = "queued"  # queued, printing, completed, failed, cancelled
    progress: float = 0.0
    error_message: str = ""
    print_result: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'filepath': self.filepath,
            'name': self.name,
            'priority': self.priority,
            'added_time': self.added_time,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'QueuedJob':
        return cls(
            id=data['id'],
            filepath=data['filepath'],
            name=data['name'],
            priority=data.get('priority', 0),
            added_time=data.get('added_time', time.time()),
            status=data.get('status', 'queued'),
            progress=data.get('progress', 0.0),
            error_message=data.get('error_message', ''),
            print_result=data.get('print_result')
        )


class PrintQueue:
    """
    打印队列管理器

    示例:
        queue = PrintQueue(
            printer_host="YOUR_PRINTER_IP",
            access_code="YOUR_ACCESS_CODE",
            serial="YOUR_PRINTER_SERIAL"
        )

        # 添加任务
        queue.add("bambu_project.3mf", name="我的模型")

        # 启动队列
        queue.start()

        # 查看状态
        print(queue.get_status())
    """

    def __init__(
        self,
        printer_host: str,
        access_code: str,
        serial: str,
        connection_type: ConnectionType = ConnectionType.MQTT,
        queue_dir: Optional[str] = None,
        auto_start: bool = False,
        printer_options: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化打印队列

        Args:
            printer_host: 打印机IP
            access_code: 访问码
            serial: 序列号
            connection_type: 连接类型
            queue_dir: 队列存储目录
            auto_start: 是否自动启动队列
            printer_options: AMS、延时摄影和网络超时等客户端选项
        """
        self.printer = BambuPrinterClient(
            host=printer_host,
            access_code=access_code,
            serial=serial,
            connection_type=connection_type,
            **(printer_options or {}),
        )

        # 队列目录
        if queue_dir is None:
            queue_dir = Path.home() / ".3d_print_queue"
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        self.queue_file = self.queue_dir / "queue.json"
        self.history_file = self.queue_dir / "history.json"
        self.config_file = self.queue_dir / "config.json"
        self.runtime_file = self.queue_dir / "runtime.json"

        # 队列状态
        self.queue: List[QueuedJob] = []
        self.status = QueueStatus.IDLE
        self.current_job: Optional[QueuedJob] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self.auto_start = auto_start

        # 回调函数
        self._on_job_start: Optional[Callable] = None
        self._on_job_complete: Optional[Callable] = None
        self._on_job_fail: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None

        # 加载队列
        self._load_queue()
        self._load_config()

        # 自动启动
        if auto_start:
            self.start()

    def _load_queue(self):
        """从文件加载队列"""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.queue = [QueuedJob.from_dict(j) for j in data]
                print(f"[队列] 已加载 {len(self.queue)} 个任务")
            except Exception as e:
                print(f"[队列] 加载队列失败: {e}")
                self.queue = []

    def _save_queue(self):
        """保存队列到文件"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump([j.to_dict() for j in self.queue], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[队列] 保存队列失败: {e}")

    def _load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._on_job_start = config.get('callbacks', {}).get('on_job_start')
                    self._on_job_complete = config.get('callbacks', {}).get('on_job_complete')
                    self._on_job_fail = config.get('callbacks', {}).get('on_job_fail')
            except Exception as e:
                print(f"[队列] 加载配置失败: {e}")

    def _save_config(self):
        """保存配置"""
        try:
            config = {
                'callbacks': {
                    'on_job_start': self._on_job_start,
                    'on_job_complete': self._on_job_complete,
                    'on_job_fail': self._on_job_fail
                }
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"[队列] 保存配置失败: {e}")

    def _read_runtime(self) -> Dict[str, Any]:
        """Read cross-process queue control state."""
        default = {
            'worker_pid': None,
            'current_job_id': None,
            'desired_state': 'stopped',
        }
        if not self.runtime_file.exists():
            return default
        try:
            with open(self.runtime_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {**default, **data} if isinstance(data, dict) else default
        except (OSError, json.JSONDecodeError):
            return default

    def _update_runtime(self, **updates) -> Dict[str, Any]:
        """Atomically merge queue runtime state for another CLI process."""
        state = self._read_runtime()
        state.update(updates)
        state['updated_at'] = datetime.now().isoformat()
        temp_file = self.runtime_file.with_name(
            f"{self.runtime_file.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, self.runtime_file)
        return state

    @staticmethod
    def _pid_is_running(pid: Any) -> bool:
        try:
            pid = int(pid)
            if pid <= 0:
                return False
            os.kill(pid, 0)
            return True
        except (TypeError, ValueError, OSError):
            return False

    def _external_worker_state(self) -> Optional[Dict[str, Any]]:
        state = self._read_runtime()
        pid = state.get('worker_pid')
        if pid == os.getpid() or not self._pid_is_running(pid):
            return None
        return state

    def _desired_state_for_worker(self) -> str:
        state = self._read_runtime()
        if state.get('worker_pid') != os.getpid():
            return 'running'
        return str(state.get('desired_state', 'running'))

    def _begin_processing(self) -> bool:
        if self._worker_thread and self._worker_thread.is_alive():
            print("[队列] 队列已在运行")
            return False

        external = self._external_worker_state()
        if external:
            print(f"[队列] 队列已由进程 {external['worker_pid']} 运行")
            return False

        self._stop_event.clear()
        self._pause_event.clear()
        self.status = QueueStatus.RUNNING
        self._update_runtime(
            worker_pid=os.getpid(),
            current_job_id=None,
            desired_state='running',
        )
        return True

    def _run_worker(self, exit_when_empty: bool = False):
        try:
            self._process_queue(exit_when_empty=exit_when_empty)
        finally:
            if self.printer.is_connected():
                self.printer.disconnect()
            self._update_runtime(worker_pid=None, current_job_id=None)

    def _connect_for_external_control(self) -> bool:
        if self.printer.is_connected():
            return True
        return self.printer.connect()

    def _disconnect_external_control(self):
        if self.printer.is_connected():
            self.printer.disconnect()

    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_history(self, history: List[Dict]):
        """保存历史记录"""
        try:
            # 只保留最近100条
            history = history[-100:]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[队列] 保存历史失败: {e}")

    def _add_to_history(self, job: QueuedJob):
        """添加任务到历史"""
        history = self._load_history()
        history.append({
            **job.to_dict(),
            'completed_at': datetime.now().isoformat()
        })
        self._save_history(history)

    def add(
        self,
        filepath: str,
        name: Optional[str] = None,
        priority: int = 0,
        category: str = "default"
    ) -> str:
        """
        添加打印任务到队列

        Args:
            filepath: 模型文件路径
            name: 任务名称（可选）
            priority: 优先级（数字越大优先级越高）
            category: 分类

        Returns:
            任务ID
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        # 验证文件格式
        ext = Path(filepath).suffix.lower()
        if ext not in PRINT_READY_EXTENSIONS:
            supported = ', '.join(PRINT_READY_EXTENSIONS)
            raise ValueError(
                f"不支持的打印文件格式: {ext}。打印队列只接受 ready-to-print 文件: {supported}。"
                "请先用 Bambu Studio 或 OrcaSlicer 切片。"
            )

        if ext == '.3mf' and not is_bambu_project_3mf(filepath):
            raise ValueError(
                "3MF 文件缺少 Bambu/OrcaSlicer 项目或切片元数据，不能作为 sliced ready-to-print 文件入队。"
                "请先用 Bambu Studio 或 OrcaSlicer 打开源模型并导出打印项目，或使用 .gcode/.bgcode。"
            )

        job_id = str(uuid.uuid4())[:8]
        job = QueuedJob(
            id=job_id,
            filepath=filepath,
            name=name or Path(filepath).stem,
            priority=priority
        )

        # 按优先级插入到队列
        inserted = False
        for i, qj in enumerate(self.queue):
            if priority > qj.priority:
                self.queue.insert(i, job)
                inserted = True
                break
        if not inserted:
            self.queue.append(job)

        self._save_queue()
        print(f"[队列] 添加任务: {job.name} (ID: {job_id}, 优先级: {priority})")

        # Only connect to the printer automatically when explicitly requested.
        if self.auto_start and self.status == QueueStatus.IDLE and not self._worker_thread:
            self.start()

        return job_id

    def remove(self, job_id: str) -> bool:
        """
        从队列中移除任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功移除
        """
        for i, job in enumerate(self.queue):
            if job.id == job_id:
                self.queue.pop(i)
                self._save_queue()
                print(f"[队列] 已移除任务: {job.name}")
                return True
        return False

    def cancel(self, job_id: str) -> bool:
        """
        取消正在打印的任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功取消
        """
        if self.current_job and self.current_job.id == job_id:
            if not self.printer.stop_print():
                print(f"[队列] 取消任务失败: {job_id}")
                return False
            self.current_job.status = "cancelled"
            self._add_to_history(self.current_job)
            self.queue = [job for job in self.queue if job.id != job_id]
            self._save_queue()
            self.current_job = None
            return True
        return self.remove(job_id)

    def start(self) -> bool:
        """启动队列处理"""
        if not self._begin_processing():
            return False

        self._worker_thread = threading.Thread(
            target=self._run_worker,
            daemon=True,
            name="PrintQueueWorker"
        )
        self._worker_thread.start()
        print("[队列] 队列已启动")
        return True

    def run_foreground(self) -> bool:
        """Process the queue in this process until it is empty or stopped."""
        if not self.queue:
            print("[队列] 队列为空")
            return False
        if not self._begin_processing():
            return False
        self._run_worker(exit_when_empty=True)
        return self.status != QueueStatus.ERROR

    def pause(self):
        """暂停队列"""
        if self.status == QueueStatus.RUNNING or self.status == QueueStatus.PRINTING:
            if self.current_job:
                if not self.printer.pause_print():
                    print("[队列] 暂停打印失败")
                    return False
            self._pause_event.set()
            self.status = QueueStatus.PAUSED
            self._update_runtime(desired_state='paused')
            print("[队列] 队列已暂停")
            return True

        external = self._external_worker_state()
        if external:
            if external.get('desired_state') == 'paused':
                return True
            if external.get('current_job_id'):
                if not self._connect_for_external_control():
                    return False
                try:
                    status = self.printer.get_status()
                    if status.print_status == 'printing' and not self.printer.pause_print():
                        return False
                    if status.print_status not in {'printing', 'paused'}:
                        print(f"[队列] 打印机当前无法暂停: {status.print_status}")
                        return False
                finally:
                    self._disconnect_external_control()
            self._update_runtime(desired_state='paused')
            print("[队列] 队列已暂停")
            return True
        return False

    def resume(self):
        """继续队列"""
        if self.status == QueueStatus.PAUSED:
            if self.current_job:
                if not self.printer.resume_print():
                    print("[队列] 恢复打印失败")
                    return False
            self._pause_event.clear()
            self.status = (
                QueueStatus.PRINTING if self.current_job else QueueStatus.RUNNING
            )
            self._update_runtime(desired_state='running')
            print("[队列] 队列已继续")
            return True

        external = self._external_worker_state()
        if external and external.get('desired_state') == 'paused':
            if external.get('current_job_id'):
                if not self._connect_for_external_control():
                    return False
                try:
                    status = self.printer.get_status()
                    if status.print_status == 'paused' and not self.printer.resume_print():
                        return False
                    if status.print_status not in {'paused', 'printing'}:
                        print(f"[队列] 打印机当前无法继续: {status.print_status}")
                        return False
                finally:
                    self._disconnect_external_control()
            self._update_runtime(desired_state='running')
            print("[队列] 队列已继续")
            return True
        return False

    def stop(self) -> bool:
        """停止队列"""
        external = self._external_worker_state()
        if external:
            if external.get('current_job_id'):
                if not self._connect_for_external_control():
                    return False
                try:
                    status = self.printer.get_status()
                    if (
                        status.print_status in {'printing', 'paused'}
                        and not self.printer.stop_print()
                    ):
                        return False
                finally:
                    self._disconnect_external_control()
            self._update_runtime(desired_state='stopped')
            print("[队列] 队列已停止")
            return True

        if self.current_job:
            if not self.printer.stop_print():
                print("[队列] 停止打印失败")
                return False
            stopped_job = self.current_job
            stopped_job.status = "cancelled"
            stopped_job.error_message = "队列已停止"
            self._add_to_history(stopped_job)
            self.queue = [job for job in self.queue if job.id != stopped_job.id]
            self._save_queue()
            self.current_job = None
        self._stop_event.set()
        self.status = QueueStatus.STOPPED
        self._update_runtime(desired_state='stopped')
        print("[队列] 队列已停止")
        return True

    def clear(self) -> bool:
        """清空队列"""
        if not self.stop():
            print("[队列] 清空队列失败")
            return False
        self.queue.clear()
        self._save_queue()
        print("[队列] 队列已清空")
        return True

    def _process_queue(self, exit_when_empty: bool = False):
        """队列处理线程"""
        # 连接打印机
        print("[队列] 正在连接打印机...")
        if not self.printer.connect():
            print("[队列] 无法连接到打印机")
            self.status = QueueStatus.ERROR
            return

        print("[队列] 已连接到打印机")

        # 注册状态回调
        def on_status_change(status: PrinterStatus):
            if self.current_job:
                self.current_job.progress = status.progress
                if self._on_progress:
                    self._on_progress(self.current_job, status)

        self.printer.on_status_change(on_status_change)

        while not self._stop_event.is_set():
            desired_state = self._desired_state_for_worker()
            if desired_state == 'stopped':
                self._stop_event.set()
                break
            if desired_state == 'paused':
                self.status = QueueStatus.PAUSED
                time.sleep(0.5)
                continue

            # 检查是否暂停
            if self._pause_event.is_set():
                time.sleep(0.5)
                continue

            # 获取下一个任务
            if not self.queue:
                self.status = QueueStatus.IDLE
                if exit_when_empty:
                    break
                print("[队列] 队列为空，等待新任务...")
                time.sleep(5)
                continue

            self.current_job = self.queue[0]
            self.status = QueueStatus.PRINTING
            self._update_runtime(current_job_id=self.current_job.id)

            print(f"\n[队列] 开始打印: {self.current_job.name}")
            filename = Path(self.current_job.filepath).name
            remote_name = self.printer._normalize_remote_name(filename)
            adopting_active_print = self.current_job.status == "printing"

            if adopting_active_print:
                status = self.printer.get_status()
                active_name = Path(status.model_info).name if status.model_info else ""
                if (
                    status.print_status not in {'printing', 'paused'}
                    or active_name != remote_name
                ):
                    print(
                        "[队列] 无法安全接管之前的任务: "
                        f"打印机状态={status.print_status}, 文件={active_name or '(未知)'}"
                    )
                    self.status = QueueStatus.ERROR
                    break
                print(f"[队列] 已接管打印机上的活动任务: {remote_name}")
            elif not self.printer.send_file(self.current_job.filepath, remote_name):
                print(f"[队列] 文件发送失败: {self.current_job.filepath}")
                self.current_job.status = "failed"
                self.current_job.error_message = "文件发送失败"
                self._add_to_history(self.current_job)
                if self._on_job_fail:
                    self._on_job_fail(self.current_job)
                self.queue.pop(0)
                self._save_queue()
                self.current_job = None
                self._update_runtime(current_job_id=None)
                continue

            if not adopting_active_print:
                time.sleep(2)  # 等待文件上传完成

                # Use the exact ASCII remote name chosen by send_file().
                if not self.printer.start_print():
                    print(f"[队列] 打印命令发送失败")
                    self.current_job.status = "failed"
                    self.current_job.error_message = "打印命令发送失败"
                    self._add_to_history(self.current_job)
                    if self._on_job_fail:
                        self._on_job_fail(self.current_job)
                    self.queue.pop(0)
                    self._save_queue()
                    self.current_job = None
                    self._update_runtime(current_job_id=None)
                    continue

                self.current_job.status = "printing"
                self._save_queue()
                if self._on_job_start:
                    self._on_job_start(self.current_job)

            # 监控打印进度
            while not self._stop_event.is_set():
                if self.current_job is None:
                    break
                desired_state = self._desired_state_for_worker()
                if desired_state == 'stopped':
                    self.current_job.status = "cancelled"
                    self.current_job.error_message = "队列已停止"
                    self._add_to_history(self.current_job)
                    self.queue = [
                        job for job in self.queue if job.id != self.current_job.id
                    ]
                    self._save_queue()
                    self.current_job = None
                    self._stop_event.set()
                    break
                if desired_state == 'paused':
                    self.status = QueueStatus.PAUSED
                    time.sleep(0.5)
                    continue
                self.status = QueueStatus.PRINTING
                status = self.printer.get_status()

                if self.current_job:
                    self.current_job.progress = status.progress

                # 检查打印完成
                if status.print_status in ['completed', 'success', 'done']:
                    print(f"\n[队列] 打印完成: {self.current_job.name}")
                    self.current_job.status = "completed"
                    self.current_job.print_result = asdict(status)
                    self._add_to_history(self.current_job)

                    if self._on_job_complete:
                        self._on_job_complete(self.current_job)

                    self.queue.pop(0)
                    self._save_queue()
                    break

                # 检查打印失败
                if status.print_status in ['failed', 'error']:
                    print(f"\n[队列] 打印失败: {self.current_job.name}")
                    self.current_job.status = "failed"
                    self.current_job.error_message = "打印机报告失败"
                    self._add_to_history(self.current_job)

                    if self._on_job_fail:
                        self._on_job_fail(self.current_job)

                    self.queue.pop(0)
                    self._save_queue()
                    break

                # 打印进度
                remaining = status.remaining_time // 60 if status.remaining_time else 0
                print(f"\r[进度] {status.progress:.1f}% - "
                      f"层 {status.layer}/{status.total_layers} - "
                      f"剩余 {remaining}分钟", end="", flush=True)

                time.sleep(3)  # 每3秒检查一次

            self.current_job = None
            self._update_runtime(current_job_id=None)

        # 断开连接
        self.printer.disconnect()
        if self.status not in {QueueStatus.ERROR, QueueStatus.STOPPED}:
            self.status = QueueStatus.IDLE
        self._update_runtime(worker_pid=None, current_job_id=None)
        print("\n[队列] 已停止")

    def get_status(self) -> Dict[str, Any]:
        """
        获取队列状态

        Returns:
            状态字典
        """
        printer_status = self.printer.get_status()
        runtime = self._read_runtime()
        worker_active = self._pid_is_running(runtime.get('worker_pid'))
        current_job = self.current_job
        if current_job is None and worker_active and runtime.get('current_job_id'):
            current_job = next(
                (job for job in self.queue if job.id == runtime['current_job_id']),
                None,
            )

        queue_status = self.status.value
        if worker_active:
            if runtime.get('desired_state') == 'paused':
                queue_status = QueueStatus.PAUSED.value
            elif current_job:
                queue_status = QueueStatus.PRINTING.value
            else:
                queue_status = QueueStatus.RUNNING.value

        return {
            'status': queue_status,
            'queue_length': len(self.queue),
            'current_job': {
                'id': current_job.id,
                'name': current_job.name,
                'status': current_job.status,
                'progress': current_job.progress,
                'filepath': current_job.filepath
            } if current_job else None,
            'printer': {
                'print_status': printer_status.print_status,
                'progress': printer_status.progress,
                'layer': printer_status.layer,
                'total_layers': printer_status.total_layers,
                'bed_temp': printer_status.bed_temp,
                'nozzle_temp': printer_status.nozzle_temp,
                'remaining_time': printer_status.remaining_time,
                'ip_address': printer_status.ip_address,
                'print_error': printer_status.print_error,
                'hms': list(printer_status.hms),
            }
        }

    def list_queue(self) -> List[Dict]:
        """
        列出队列中的任务

        Returns:
            任务列表
        """
        result = []
        for i, job in enumerate(self.queue):
            result.append({
                'index': i + 1,
                **job.to_dict()
            })
        return result

    def get_history(self, limit: int = 20) -> List[Dict]:
        """
        获取打印历史

        Args:
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        history = self._load_history()
        return history[-limit:]

    def on_job_start(self, callback: Callable[[QueuedJob], None]):
        """注册任务开始回调"""
        self._on_job_start = callback

    def on_job_complete(self, callback: Callable[[QueuedJob], None]):
        """注册任务完成回调"""
        self._on_job_complete = callback

    def on_job_fail(self, callback: Callable[[QueuedJob], None]):
        """注册任务失败回调"""
        self._on_job_fail = callback

    def on_progress(self, callback: Callable[[QueuedJob, PrinterStatus], None]):
        """注册进度更新回调"""
        self._on_progress = callback

    def reorder(self, job_id: str, new_priority: int):
        """
        重新排序任务

        Args:
            job_id: 任务ID
            new_priority: 新优先级
        """
        for job in self.queue:
            if job.id == job_id:
                self.remove(job_id)
                self.add(job.filepath, job.name, new_priority)
                break

    def __len__(self):
        """返回队列长度"""
        return len(self.queue)

    def __repr__(self):
        return f"PrintQueue(status={self.status.value}, queue_len={len(self.queue)})"
