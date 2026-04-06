# 🎯 拓竹3D打印机 AI模型生成方案

> 用AI从文字/图片生成3D模型，直接打印！

**一句话说明**：这是一个本地部署的3D生成AI，可以为你的拓竹(Bambu Lab)打印机创建独特的3D模型。

---

## ⚡ 快速开始

### 方式一：手动打印

```bash
# 1️⃣ 生成模型 - 文字描述
python scripts/hunyuan_quick.py text "一只可爱的兔子"

# 2️⃣ 收集到模型库
python scripts/model_collector.py add ./outputs/model.stl animals my_rabbit

# 3️⃣ 导出打印
python scripts/model_collector.py export my_rabbit
# → 文件在 models/ready-to-print/ 文件夹中

# 4️⃣ 用Bambu Studio打开STL文件，开始打印！
```

### 方式二：一键自动打印 (推荐!)

```bash
# 1️⃣ 配置打印机（只需一次）
python scripts/auto_print.py config \
    --host 192.168.1.100 \
    --access-code YOUR_CODE \
    --serial SNXXX

# 2️⃣ AI生成 + 自动打印
python scripts/ai_to_print.py text "一只可爱的兔子"

# 完成！模型生成后自动发送到打印机打印
```

---

## 📦 项目包含什么

| 模块 | 用途 | 位置 |
|------|------|------|
| **Hunyuan3D-1** | 文字生成3D (Text-to-3D) | `Hunyuan3D-1/` |
| **Hunyuan3D-2** | 图片生成3D (Image-to-3D) | `Hunyuan3D-2/` |
| **scripts/** | 工具脚本 | 模型收集、格式转换 |
| **models/** | 模型库 | 收藏的3D模型 |

---

## 🔥 两种生成方式

### 方式一：文字 → 3D模型 (V1)
```bash
cd Hunyuan3D-1
python main.py --text_prompt "一只卡通龙" --use_lite
```
- 优点：不需要图片，直接描述即可
- 速度：约10秒
- 适合：快速创意验证

### 方式二：图片 → 3D模型 (V2)
```bash
cd Hunyuan3D-2
python minimal_demo.py
```
- 优点：质量更高，有PBR纹理
- 速度：约20-40秒
- 适合：高精度打印

---

## 🛠️ 工具脚本

| 脚本 | 命令 | 功能 |
|------|------|------|
| 一键生成 | `hunyuan_quick.py text "描述"` | 文字生成 |
| 一键生成 | `hunyuan_quick.py image 图片路径` | 图片生成 |
| 模型收集 | `model_collector.py add 文件 分类 名称` | 添加到库 |
| 模型收集 | `model_collector.py list` | 查看模型库 |
| 格式转换 | `model_converter.py repair 文件` | 修复模型 |
| 格式转换 | `model_converter.py convert 文件 stl` | 转换为STL |
| **自动打印** | `auto_print.py config` | 配置打印机 |
| **自动打印** | `auto_print.py add <file>` | 添加打印任务 |
| **自动打印** | `auto_print.py start` | 启动打印 |
| **自动打印** | `auto_print.py watch` | 监控进度 |
| **AI+打印** | `ai_to_print.py text "描述"` | AI生成+自动打印 |
| **AI+打印** | `ai_to_print.py image <图片>` | AI图片+自动打印 |
| **持续生成** | `continuous_print.py generate` | 单次生成+打印 |
| **持续生成** | `continuous_print.py watch` | 监控文件夹模式 |
| **持续生成** | `continuous_print.py prompts` | 提示词列表模式 |
| **持续生成** | `continuous_print.py status` | 查看状态 |

---

## 📁 目录结构

```
d:/projects/3d/
├── Hunyuan3D-1/              # 文字→3D (快速)
├── Hunyuan3D-2/              # 图片→3D (高质量)
├── bambu_print/              # 拓竹自动打印模块
│   ├── printer_client.py    # 打印机客户端
│   └── print_queue.py       # 打印队列管理
├── scripts/                  # 工具脚本
│   ├── hunyuan_quick.py     # 一键生成
│   ├── model_collector.py   # 模型管理
│   ├── model_converter.py   # 格式转换/修复
│   └── auto_print.py        # 自动打印工具
├── models/
│   ├── collection/          # 收藏的模型
│   └── ready-to-print/      # 可直接打印的STL
├── outputs/                  # 临时输出
└── config/                   # 配置文件
    └── printer.json         # 打印机配置
```

---

## 🖨️ 拓竹打印设置建议

| 类型 | 层高 | 填充 | 适用场景 |
|------|------|------|----------|
| 标准 | 0.2mm | 15-20% | 日常打印 |
| 高精度 | 0.12mm | 15-20% | 精细模型 |
| 机械零件 | 0.16mm | 40-60% | 功能件 |

---

## 🤖 自动打印 (新增!)

通过 `bambu_print` 模块，可以实现**AI生成模型后自动打印**，无需手动操作！

### 安装依赖

```bash
pip install -r requirements-print.txt
```

### 配置打印机

```bash
# 方式1: 使用命令行配置
python scripts/auto_print.py config \
    --host 192.168.1.100 \
    --access-code YOUR_ACCESS_CODE \
    --serial SNXXX

# 方式2: 直接编辑配置文件
# 编辑 config/printer.json
```

**获取打印机信息:**
- **IP**: 在打印机屏幕 → 设置 → WiFi → 查看IP
- **Access Code**: 设置 → WiFi → Access Code
- **Serial**: 设置 → 设备信息 → 序列号

### 快速开始

```bash
# 1. 发现打印机
python scripts/auto_print.py discover

# 2. 配置打印机
python scripts/auto_print.py config \
    --host 192.168.1.100 \
    --access-code YOUR_CODE \
    --serial SNXXX

# 3. 添加打印任务
python scripts/auto_print.py add ./model.stl --name "我的模型"

# 4. 查看队列
python scripts/auto_print.py list

# 5. 启动打印
python scripts/auto_print.py start

# 6. 监控进度
python scripts/auto_print.py watch
```

### 命令参考

| 命令 | 功能 |
|------|------|
| `config` | 配置打印机 |
| `discover` | 发现局域网打印机 |
| `add <file>` | 添加打印任务 |
| `list` | 列出队列 |
| `status` | 查看状态 |
| `history` | 查看打印历史 |
| `start` | 启动队列 |
| `pause` | 暂停队列 |
| `resume` | 继续队列 |
| `stop` | 停止队列 |
| `watch` | 实时监控进度 |
| `remove <id>` | 移除任务 |
| `cancel <id>` | 取消任务 |
| `clear` | 清空队列 |

### Python API 使用

```python
from bambu_print import PrintQueue, ConnectionType

# 创建队列
queue = PrintQueue(
    printer_host="192.168.1.100",
    access_code="YOUR_ACCESS_CODE",
    serial="SNXXX",
    connection_type=ConnectionType.MQTT
)

# 添加任务
queue.add("./model.stl", name="我的模型", priority=5)

# 注册回调
def on_complete(job):
    print(f"打印完成: {job.name}")

queue.on_job_complete(on_complete)

# 启动队列
queue.start()

# 查看状态
print(queue.get_status())
```

### 完整自动化工作流

```python
# AI生成 + 自动打印
from bambu_print import PrintQueue

# 1. 生成模型 (使用你的AI模型)
# ... 生成代码 ...

# 2. 创建打印队列
queue = PrintQueue(
    printer_host="192.168.1.100",
    access_code="xxx",
    serial="SNXXX"
)

# 3. 添加任务
queue.add("./outputs/model.stl", name="AI生成模型")

# 4. 启动
queue.start()

# 5. 监控直到完成
while queue.status.value in ['running', 'printing']:
    status = queue.get_status()
    if status['current_job']:
        print(f"进度: {status['current_job']['progress']:.1f}%")
    time.sleep(5)
```

### 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                   自动化打印工作流                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI生成模型 → STL修复 → 自动发送到打印机 → 自动开始打印         │
│                                    ↓                         │
│                              实时进度监控                      │
│                                    ↓                         │
│                              打印完成通知                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**支持的文件格式**: `.stl`, `.obj`, `.3mf`, `.amf`, `.gltf`, `.glb`

---

## 🔥 持续生成 + 自动打印 (无人值守)

这是最强大的功能！可以实现**24小时无人值守持续生成+打印**。

### 📋 四种工作模式

| 模式 | 命令 | 适用场景 |
|------|------|----------|
| **单次生成** | `generate --prompt "描述"` | 快速测试 |
| **监控文件夹** | `watch --folder ./watch` | 有新图片自动处理 |
| **提示词列表** | `prompts --file list.txt` | 批量创意生成 |
| **API服务** | `server --port 8080` | 远程控制 |

### 模式1: 单次生成 + 打印

```bash
# 文字生成 + 打印
python scripts/continuous_print.py generate --prompt "一只可爱的卡通兔子"

# 图片生成 + 打印
python scripts/continuous_print.py generate --image ./photo.png

# 仅生成，不打印
python scripts/continuous_print.py generate --prompt "一只恐龙" --no-print
```

### 模式2: 监控文件夹 (推荐!)

当文件夹中有新图片时，自动生成模型并打印：

```bash
# 创建监控文件夹
mkdir -p watch_folder

# 启动监控
python scripts/continuous_print.py watch --folder ./watch_folder

# 现在只需把图片放进 watch_folder:
# 1. AI自动识别图片
# 2. 生成3D模型
# 3. 发送到打印机打印
# 4. 完成后自动处理下一张
```

### 模式3: 提示词列表 (批量创意)

创建 `prompts.txt`：

```text
# 动物系列
一只可爱的小猫
一只凶猛的霸王龙
一只蓝色的小鸟
一只胖胖的柯基犬

# 物品系列
一个蓝色的马克杯
一把红色的雨伞
一个木头书架
一个玻璃花瓶

# 人物系列
一个宇航员
一个小巫师
一个骑士头盔
```

运行：

```bash
# 每60秒生成一个模型并打印
python scripts/continuous_print.py prompts --file prompts.txt --delay 60
```

### 模式4: 查看状态

```bash
# 查看生成和打印状态
python scripts/continuous_print.py status
```

### 🚀 24小时无人值守工作流

```
┌────────────────────────────────────────────────────────────────────┐
│                     持续生成 + 自动打印 工作流                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ 提示词列表 │ → │ AI生成   │ → │ 模型修复  │ → │ 发送打印  │     │
│  │ 或文件夹  │    │ Hunyuan3D│    │ Trimesh  │    │ MQTT     │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│                                                            ↓       │
│                                                    ┌──────────┐    │
│                                                    │ 打印机    │    │
│                                                    │ P1S/X1C  │    │
│                                                    └──────────┘    │
│                                                            ↓       │
│                                                    ┌──────────┐    │
│                                                    │ 监控进度  │    │
│                                                    │ 回调通知  │    │
│                                                    └──────────┘    │
│                                                            ↓       │
│                                                         等待完成     │
│                                                            ↓       │
│  ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←       │
│                                                                    │
│                       循环处理下一个                                │
└────────────────────────────────────────────────────────────────────┘
```

### 配置示例

```bash
# 完整的配置文件: config/printer.json
{
    "host": "192.168.1.100",
    "access_code": "你的访问码",
    "serial": "序列号"
}
```

### 高级用法: Python API

```python
from scripts.continuous_print import ContinuousPrinter

# 创建持续打印机
printer = ContinuousPrinter(
    printer_host="192.168.1.100",
    access_code="xxx",
    serial="SNXXX",
    output_dir="./outputs/continuous"
)

# 设置打印完成回调
def on_complete(job):
    print(f"✓ {job.name} 打印完成！")
    # 发送通知、记录日志等
    printer.set_print_callback(on_complete)

# 启动监控文件夹模式
printer.run_folder_watch("./watch_folder")

# 或者运行提示词列表模式
printer.run_prompt_list("./prompts.txt", delay=60)
```

### 命令行工具总览

| 命令 | 功能 |
|------|------|
| `generate --prompt "文字"` | 文字生成+打印 |
| `generate --image ./a.png` | 图片生成+打印 |
| `watch --folder ./path` | 监控文件夹模式 |
| `prompts --file list.txt` | 提示词列表模式 |
| `status` | 查看状态 |
| `stop` | 停止服务 |

---

## 🎨 ComfyUI + Hunyuan3D (推荐!)

ComfyUI 是最推荐的方案，已原生支持 Hunyuan3D-2，专为 RTX 50 系列 Blackwell 显卡优化！

### 优势

| 优势 | 说明 |
|------|------|
| **Blackwell 原生支持** | 专为 RTX 5060 Ti 等新显卡优化 |
| **低显存要求** | 最低只需 1GB VRAM |
| **智能显存管理** | 自动卸载模型到内存 |
| **丰富工作流** | 社区提供完整 Hunyuan3D 工作流 |

### 安装位置

```
d:/projects/3d/ComfyUI/
d:/projects/3d/ComfyUI-Win-Blackwell/
```

### 启动方式

```bash
# Windows
cd d:/projects/3d/ComfyUI
run_blackwell.bat

# 或手动启动 (禁用xformers)
python main.py --disable-xformers --use-pytorch-cross-attention
```

### 显存模式

| 模式 | 命令 | 适用场景 |
|------|------|----------|
| 高显存 | `--highvram` | 速度最快 |
| 自动卸载 | `--async-offload` | 平衡模式 |
| 低显存 | `--lowvram` | 显存不够时 |

### 访问地址

启动后打开浏览器访问：**http://localhost:8188**

### 模型位置

```
d:/projects/3d/ComfyUI/models/checkpoints/
├── hunyuan3d-dit-v2.safetensors      # 单视角版本
└── hunyuan3d-dit-v2-mv.safetensors   # 多视角版本
```

---

## 📥 安装依赖

```bash
# 基础环境 (V2)
cd Hunyuan3D-2
pip install -r requirements.txt

# 拓竹支持（格式转换用）
pip install trimesh numpy

# 可选：V1文字生成
cd Hunyuan3D-1
bash env_install.sh

# 自动打印支持（新增！）
pip install -r requirements-print.txt
```

---

## ❓ 常见问题

**Q: 显存不够 (OOM)?**
```bash
# V1 添加 --save_memory
# V2 添加 --low_vram_mode
```

**Q: 模型有裂缝/破面？**
```bash
python scripts/model_converter.py repair 模型.stl
```

**Q: 生成速度慢？**
- V1的Lite模式更快（质量略低）
- V2的Turbo版本更快

---

**Q: 自动打印连接失败？**
1. 确保打印机和电脑在同一网络
2. 检查IP、Access Code、Serial是否正确
3. 在打印机设置中确认"本地网络控制"已开启

**Q: 如何获取Access Code？**
- 打印机屏幕 → 设置 → WiFi → Access Code

**Q: 文件上传失败？**
- 部分固件版本可能需要先通过Bambu Studio导入一次文件
- 或将文件放入SD卡插入打印机

---

## 🔗 相关文档

- [拓竹打印工作流](./PRINT_WORKFLOW.md) - 完整流程详解
- [自动打印模块](./bambu_print/README.md) - 打印API详解
- [Hunyuan3D-1 中文文档](./Hunyuan3D-1/README_zh_cn.md)
- [Hunyuan3D-2 中文文档](./Hunyuan3D-2/README_zh_cn.md)

---

<div align="center">

**🎉 开始为你的拓竹打印机创造独特的3D模型吧！**

</div>
