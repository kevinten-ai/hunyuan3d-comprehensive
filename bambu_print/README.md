# 拓竹自动打印模块

> 通过 Python 控制拓竹(Bambu Lab) 3D 打印机，支持本地局域网控制和自动打印队列管理。

## 特性

- **本地局域网控制** - 无需云端，直接通过 MQTT 协议控制打印机
- **打印队列管理** - 支持队列添加、暂停、继续、取消
- **实时进度监控** - 支持回调函数和状态监控
- **持久化存储** - 队列和配置自动保存
- **Ready-to-print 队列** - 直接打印队列接收 Bambu/OrcaSlicer 项目 3MF、G-code、Bambu binary G-code；源模型需先转换给切片器打开，再切片导出

## 当前实现边界

- 文件通过隐式 FTPS（TCP 990）上传，状态和控制命令通过 MQTT/TLS（TCP 8883）传输。
- 打印机必须启用 LAN Only 模式或可选的 Developer Mode，并允许局域网控制。Bambu Lab 将 Developer Mode 的 MQTT/FTP 接口标记为不受官方支持，固件升级后可能变化。
- 本仓库已用单元测试验证 FTPS 命令构造、MQTT 主题、P1 状态字段、命令回执和失败路径；尚未使用本仓库客户端对真实打印机完成上传、启动、暂停、恢复和停止验证。
- `add` 只添加任务到队列，不会默认启动打印；请显式调用 `start()` 或运行 `python scripts/auto_print.py start`。

## 安装

```powershell
python -m pip install -r requirements-print.txt
```

依赖:
- `paho-mqtt>=1.6.1` - MQTT 客户端
- 系统 `curl` - 隐式 FTPS 文件上传（Windows 10/11 默认提供 `curl.exe`）

## 快速开始

### 1. 获取打印机信息

在打印机屏幕上查看:
- **IP**: 设置 → WiFi → IP地址
- **Access Code**: 设置 → WiFi → Access Code
- **Serial**: 设置 → 设备信息 → 序列号

### 2. 命令行使用

```powershell
# 配置打印机
python scripts/auto_print.py config --host YOUR_PRINTER_IP --serial YOUR_PRINTER_SERIAL --developer-mode
python scripts/auto_print.py check-config

# 添加打印任务
python scripts/auto_print.py add ./plate.gcode --name "我的模型"

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
    printer_host="YOUR_PRINTER_IP",
    access_code="YOUR_ACCESS_CODE",
    serial="YOUR_PRINTER_SERIAL"
)

# 添加任务
queue.add("./bambu_project.3mf", name="我的模型")

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
    host="YOUR_PRINTER_IP",
    access_code="YOUR_ACCESS_CODE",
    serial="YOUR_PRINTER_SERIAL",
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
| `send_file(filepath)` | 通过 FTPS 上传文件；只有 `curl` 成功退出后才缓存远程文件名 |
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
    printer_host="YOUR_PRINTER_IP",
    access_code="YOUR_ACCESS_CODE",
    serial="YOUR_PRINTER_SERIAL"
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
job = queue.add("./bambu_project.3mf", name="我的模型", priority=5)
# job.id: str       # 任务ID
# job.name: str      # 任务名称
# job.status: str    # queued, printing, completed, failed
# job.progress: float # 进度 0.0-100.0
```

### 便捷函数

```python
from bambu_print import discover_printers

# 发现局域网内的打印机
printers = discover_printers(timeout=6.0)
# 返回: [{'ip': '192.0.2.25', 'name': 'Bambu Printer'}, ...]
```

## 命令行工具

```powershell
# 配置
python scripts/auto_print.py config --host YOUR_PRINTER_IP --serial YOUR_PRINTER_SERIAL --developer-mode
python scripts/auto_print.py check-config

# 发现打印机
python scripts/auto_print.py discover

# 添加任务
python scripts/auto_print.py add ./plate.gcode --name demo --priority 1

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
python scripts/auto_print.py watch --interval 3

# 历史和清理
python scripts/auto_print.py history --limit 20
python scripts/auto_print.py remove JOB_ID
python scripts/auto_print.py cancel JOB_ID
python scripts/auto_print.py clear --force
```

`discover` 被动监听打印机约每五秒发送一次的 UDP 2021/1990 公告；默认监听六秒。若切片器占用了这两个端口，请关闭切片器后重试，或直接使用已知 IP 配置打印机。

## 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                  FTPS + MQTT 局域网通信                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  文件上传: Python Client → FTPS → 拓竹打印机 (port 990)       │
│  状态/控制: Python Client ↔ MQTT/TLS ↔ 拓竹打印机 (port 8883) │
│                                                             │
│  主题格式: device/{serial}/report   # 接收状态和命令回执       │
│  主题格式: device/{serial}/request  # 发送控制命令            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 控制命令

通过 MQTT 发送 JSON 命令:

```python
# 开始打印
{"print": {"command": "project_file", "param": "Metadata/plate_1.gcode", "url": "ftp:///bambu_project.3mf", ...}}

# 暂停
{"print": {"command": "pause"}}

# 恢复
{"print": {"command": "resume"}}

# 停止
{"print": {"command": "stop"}}

# 设置热床温度
{"print": {"command": "gcode_line", "param": "M140 S60\n"}}

# 设置风扇
{"print": {"command": "gcode_line", "param": "M106 P1 S255\n"}}
```

## 故障排除

### 连接失败

1. 确保打印机和电脑在同一网络
2. 检查 IP 地址是否正确
3. 检查 Access Code 是否正确
4. 确认打印机已启用 LAN Only 模式或 Developer Mode
5. 检查防火墙是否阻止了 TCP 990 或 8883 端口

### 文件上传失败

打印队列只接收 ready-to-print 文件，例如带 Bambu/OrcaSlicer 项目元数据的 `.3mf`、`.gcode` 或 `.bgcode`；STL/OBJ/GLB 和普通几何 3MF 等源模型需要先转换给切片器打开，再切片导出。请确认系统 `curl` 可用、Developer Mode 已开启且 TCP 990 可达。如果 FTPS 上传失败，`send_file()` 会返回 `False`，并且不会把该文件记录为可启动打印的远程文件。

### MQTT 连接被拒绝

确认 Developer Mode 已开启、TCP 8883 可达，并检查打印机 IP、Access Code 和序列号。客户端优先使用 `BAMBU_PRINTER_CA_CERT`，或自动查找 `BAMBU_SLICER_EXE` 旁的 `resources/cert/printer.cer` 来验证证书链；由于证书通常不匹配局域网 IP，主机名检查保持关闭。找不到 CA 时会明确警告并降级为加密但不认证设备证书的连接，只应在可信局域网内使用。

## 许可证

MIT License
