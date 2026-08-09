# Bambu Lab 打印工作流

本文档描述根项目当前支持的安全打印流程。

## 工作流

```text
文字/图片输入
  -> Hunyuan3D 真实生成或 mock 演示
  -> STL/GLB/OBJ 模型文件
  -> 模型修复或检查，必要时转换为 slicer-input 3MF
  -> Bambu Studio / OrcaSlicer 手动切片，或 Bambu Studio CLI 桥接自动切片
  -> 添加 ready-to-print 文件到 Bambu 打印队列
  -> 显式启动队列
  -> FTPS 上传文件，MQTT/TLS 启动并监控打印状态
```

## 1. 验证生成命令

先用 dry run 确认命令，不加载模型:

```powershell
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
```

## 2. 生成模型

真实文字生成:

```powershell
python scripts/hunyuan_quick.py text "a small robot"
```

真实图片生成:

```powershell
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --quality lite
```

文字入口的 `auto` 后端在 Docker 可用时优先使用 CUDA 13 低显存容器；可通过 `--backend docker` 或 `--backend native` 显式选择。两类命令都需要对应模型权重和可用硬件。

演示端到端流程可以使用 mock 模式:

```powershell
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
```

## 3. 修复、转换和切片模型

查看模型信息:

```powershell
python scripts/model_converter.py info outputs/demo/demo.stl
```

修复模型:

```powershell
python scripts/model_converter.py repair outputs/demo/demo.stl
```

转换格式:

```powershell
python scripts/model_converter.py convert outputs/demo/demo.glb stl demo_from_glb
python scripts/model_converter.py convert outputs/demo/demo.glb 3mf demo_from_glb
python scripts/glb_to_3mf.py outputs/demo/demo.glb models/converted/demo_from_glb.3mf
```

这些转换结果是给切片器打开的源模型或 slicer-input 3MF，不是 Bambu 队列可直接打印的文件。入队前需要用 Bambu Studio 或 OrcaSlicer 切片导出 Bambu/OrcaSlicer 项目 `.3mf`、`.gcode` 或 `.bgcode`。

## 4. 配置打印机

复制配置模板:

```powershell
copy config\printer.json.example config\printer.json
```

编辑本地配置:

```json
{
  "host": "YOUR_PRINTER_IP",
  "access_code": "YOUR_ACCESS_CODE",
  "serial": "YOUR_PRINTER_SERIAL",
  "method": "mqtt",
  "lan_developer_mode": false,
  "use_ams": false,
  "ams_mapping": [-1, -1, -1, -1, 0],
  "timelapse": false
}
```

也可以用 CLI 写入:

```powershell
python scripts/auto_print.py config --host YOUR_PRINTER_IP --serial YOUR_PRINTER_SERIAL --developer-mode
```

命令会隐藏输入 Access Code，避免凭据出现在 shell 历史和进程参数中。`config/printer.json` 包含本地设备信息，不能提交到 Git。使用 AMS 时增加 `--use-ams --ams-slot 0`。直接局域网控制要求打印机启用 LAN Only 模式或 Developer Mode；Developer Mode 的 MQTT/FTP 接口不受 Bambu Lab 官方支持，固件升级后可能变化。

## 5. 添加和启动 ready-to-print 文件

添加任务只会入队，不会自动连接或启动打印机:

```powershell
python scripts/auto_print.py add path\to\plate.gcode --name demo
python scripts/auto_print.py list
```

打印队列只接收 ready-to-print 文件，例如 Bambu/OrcaSlicer 项目 `.3mf`、`.gcode` 或 `.bgcode`。`outputs/demo/demo.stl` 这类源模型可以先用本仓库转换脚本生成切片器可打开的 `.3mf`，但仍需要通过 Bambu Studio 或 OrcaSlicer 切片导出后再入队。

显式启动队列:

```powershell
python scripts/auto_print.py start
```

查看状态:

```powershell
python scripts/auto_print.py status
python scripts/auto_print.py watch
```

## 6. AI 到打印

演示模式:

```powershell
python scripts/ai_to_print.py text "a rabbit" --mock
```

真实生成并尝试切片后入队:

```powershell
python scripts/ai_to_print.py text "a rabbit" --run-generator
python scripts/ai_to_print.py image Hunyuan3D-2/assets/demo.png --run-generator
```

去掉 `--no-print` 时，AI-to-print 仍只会把 ready-to-print 文件加入队列。生成器输出 STL/OBJ/GLB 或普通几何 3MF 时，需要先配置并验证 `BAMBU_SLICER_COMMAND`，或手动用 Bambu Studio / OrcaSlicer 切片导出后再入队。

如果只想生成和修复模型，不加入打印队列:

```powershell
python scripts/ai_to_print.py text "a rabbit" --run-generator --no-print
```

## 推荐打印设置

| 类型 | 层高 | 填充 | 壁厚 |
|---|---:|---:|---:|
| 标准模型 | 0.20 mm | 15-25% | 0.8 mm |
| 高精度模型 | 0.12 mm | 20% | 1.2 mm |
| 功能件 | 0.16 mm | 40-60% | 1.6 mm |

## 外部验证门槛

- 真实生成需要模型权重、依赖和兼容 GPU/CPU 环境。
- 自动打印需要 Bambu 打印机与电脑在同一局域网。
- 打印机需要启用 LAN Only 模式或 Developer Mode，并提供正确 IP、Access Code 和 Serial。
- 本地已经实跑验证 Bambu Studio CLI 自动切片，生成包含 `Metadata/plate_1.gcode` 的 P1S 工程。
- 仓库客户端的 FTPS 上传（TCP 990）、MQTT/TLS 状态/命令（TCP 8883）及真实打印闭环仍需要在真实设备上验证。
