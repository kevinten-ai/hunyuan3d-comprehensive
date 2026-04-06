# 拓竹自动打印模块

> 通过 Python 控制拓竹(Bambu Lab) 3D 打印机，支持本地局域网控制和自动打印队列管理。

## 特性

- **本地局域网控制** - 无需云端，直接通过 MQTT 协议控制打印机
- **打印队列管理** - 支持队列添加、暂停、继续、取消
- **实时进度监控** - 支持回调函数和状态监控
- **持久化存储** - 队列和配置自动保存
- **多文件格式支持** - STL, OBJ, 3MF, AMF, GLTF, GLB

## 安装

```bash
pip install -r requirements-print.txt
```

依赖:
- `paho-mqtt>=1.6.1` - MQTT 客户端
- `requests>=2.28.0` - HTTP 文件上传

## 快速开始

### 1. 获取打印机信息

在打印机屏幕上查看:
- **IP**: 设置 → WiFi → IP地址
- **Access Code**: 设置 → WiFi → Access Code
- **Serial**: 设置 → 设备信息 → 序列号

### 2. 命令行使用

```bash
# 配置打印机
python scripts/auto_print.py config \
    --host 192.168.1.100 \
    --access-code YOUR_CODE \
    --serial SNXXX

# 添加打印任务
python scripts/auto_print.py add ./model.stl --name "我的模型"

# 启动打印
python scripts/auto_print.py start

# 监控进度
python scripts/auto_print.py watch
```

### 3. Python API 使用

```python
from bambu_print import PrintQueue

# 创建队列
queue = PrintQueue(
    printer_host="192.168.1.100",
    access_code="YOUR_ACCESS_CODE",
    serial="SNXXX"
)

# 添加任务
queue.add("./model.stl", name="我的模型")

# 注册回调
def on_complete(job):
    print(f"打印完成: {job.name}")

queue.on_job_complete(on_complete)

# 启动
queue.start()
```

## API 参考

### BambuPrinterClient

打印机客户端类。

```python
from bambu_print import BambuPrinterClient, ConnectionType

client = BambuPrinterClient(
    host="192.168.1.100",
    access_code="xxx",
    serial="SNXXX",
    connection_type=ConnectionType.MQTT
)
```

#### 方法

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到打印机 |
| `disconnect()` | 断开连接 |
| `is_connected()` | 检查连接状态 |
| `get_status()` | 获取打印机状态 |
| `send_file(filepath)` | 发送文件到打印机 |
| `start_print(filename)` | 开始打印 |
| `pause_print()` | 暂停打印 |
| `resume_print()` | 恢复打印 |
| `stop_print()` | 停止打印 |
| `on_status_change(callback)` | 注册状态变化回调 |

#### 状态对象

```python
status = client.get_status()
# status.print_status: str  # idle, printing, paused, completed, failed
# status.progress: float    # 0.0 - 100.0
# status.layer: int         # 当前层
# status.total_layers: int   # 总层数
# status.bed_temp: float     # 热床温度
# status.nozzle_temp: float # 喷嘴温度
```

### PrintQueue

打印队列管理器。

```python
from bambu_print import PrintQueue

queue = PrintQueue(
    printer_host="192.168.1.100",
    access_code="xxx",
    serial="SNXXX"
)
```

#### 方法

| 方法 | 说明 |
|------|------|
| `add(filepath, name, priority)` | 添加打印任务 |
| `remove(job_id)` | 移除任务 |
| `cancel(job_id)` | 取消正在打印的任务 |
| `start()` | 启动队列 |
| `pause()` | 暂停队列 |
| `resume()` | 继续队列 |
| `stop()` | 停止队列 |
| `clear()` | 清空队列 |
| `get_status()` | 获取队列状态 |
| `list_queue()` | 列出队列中的任务 |
| `get_history(limit)` | 获取打印历史 |
| `on_job_start(callback)` | 注册任务开始回调 |
| `on_job_complete(callback)` | 注册任务完成回调 |
| `on_job_fail(callback)` | 注册任务失败回调 |
| `on_progress(callback)` | 注册进度更新回调 |

#### 任务对象

```python
job = queue.add("./model.stl", name="我的模型", priority=5)
# job.id: str       # 任务ID
# job.name: str      # 任务名称
# job.status: str    # queued, printing, completed, failed
# job.progress: float # 进度 0.0-100.0
```

### 便捷函数

```python
from bambu_print import discover_printers

# 发现局域网内的打印机
printers = discover_printers(timeout=3.0)
# 返回: [{'ip': '192.168.1.100', 'name': 'Bambu Printer'}, ...]
```

## 命令行工具

```bash
# 配置
python scripts/auto_print.py config --host IP --access-code CODE --serial SN

# 发现打印机
python scripts/auto_print.py discover

# 添加任务
python scripts/auto_print.py add ./model.stl [--name NAME] [--priority N]

# 查看队列
python scripts/auto_print.py list

# 查看状态
python scripts/auto_print.py status

# 控制队列
python scripts/auto_print.py start
python scripts/auto_print.py pause
python scripts/auto_print.py resume
python scripts/auto_print.py stop

# 监控进度
python scripts/auto_print.py watch [--interval SEC]

# 历史和清理
python scripts/auto_print.py history [--limit N]
python scripts/auto_print.py remove <job_id>
python scripts/auto_print.py cancel <job_id>
python scripts/auto_print.py clear [--force]
```

## 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                    MQTT 协议通信                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Python Client ←→ MQTT Broker ←→ 拓竹打印机                   │
│                      (port 8883)                            │
│                                                             │
│  主题格式: p/{serial}/report/#     # 接收打印机状态           │
│  主题格式: p/{serial}/request      # 发送控制命令            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 控制命令

通过 MQTT 发送 JSON 命令:

```python
# 开始打印
{"print": {"command": "project_file", "param": "model.3mf", ...}}

# 暂停
{"pause": {"command": "pause"}}

# 恢复
{"resume": {"command": "resume"}}

# 停止
{"stop": {"command": "stop"}}

# 设置热床温度
{"bed": {"command": "set_bed", "temp": 60}}

# 设置风扇
{"fan": {"command": "set_fan", "fan": "part", "speed": 100}}
```

## 故障排除

### 连接失败

1. 确保打印机和电脑在同一网络
2. 检查 IP 地址是否正确
3. 检查 Access Code 是否正确
4. 检查防火墙是否阻止了 8883 端口

### 文件上传失败

拓竹打印机需要先通过 Bambu Studio 或 SD 卡导入文件。自动上传功能可能因固件版本而异。

### MQTT 连接被拒绝

部分固件版本可能禁用了 MQTT。请检查打印机设置。

## 许可证

MIT License