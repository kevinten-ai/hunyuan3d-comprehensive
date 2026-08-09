# Hunyuan3D + Bambu Lab 3D 打印整合项目

本仓库是一个本地 3D 生成与打印编排层，目标是把 Hunyuan3D-1、Hunyuan3D-2、ComfyUI 和 Bambu Lab 打印机工作流连接起来。

GitHub 仓库: https://github.com/kevinten-ai/hunyuan3d-comprehensive

## 当前状态

这个项目已经包含可用的基础模块，但完整端到端打印仍依赖外部条件。

| 模块 | 当前状态 | 说明 |
|---|---|---|
| Hunyuan3D-1 | Docker 低步数实跑通过 | CUDA 13、`sm_120`、nvdiffrast、xFormers 及 1 步文本到约 1,000 面 OBJ 已验证 |
| Hunyuan3D-2 | 低步数实跑通过 | 本地图片生成 GLB 已通过；完整质量参数仍需继续验证 |
| ComfyUI | 工作流实跑通过 | 13 个工作流资产齐全，5 步 API 图已生成并验证 watertight GLB |
| 模型转换 | 已实现 | `scripts/model_converter.py` 使用 `trimesh` 转换/修复 STL、OBJ、GLB 等 |
| 模型收集 | 已实现 | `scripts/model_collector.py` 管理模型库和 slicer-input 导出 |
| Bambu 打印队列 | 运行与协议层已验证 | `bambu_print/` 通过 FTPS 上传、MQTT/TLS 读取状态并等待命令回执；真实设备已验证上传和暂停/恢复，生成模型的启动/停止仍受物理条件限制 |
| Bambu 自动切片 | 实跑通过 | `scripts/bambu_slicer_bridge.py` 已生成含 G-code 的 P1S 切片工程 |
| AI 到打印 | 已安全化 | 默认不再模拟成功；真实生成需 `--run-generator`，演示需 `--mock` |

更多状态细节见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## 目录结构

```text
D:/projects/3d/
├── Hunyuan3D-1/              # 腾讯 Hunyuan3D-1，上游文本/图片到多视角再重建流程
├── Hunyuan3D-2/              # 腾讯 Hunyuan3D-2，上游图片到 3D / 贴图流程
├── bambu_print/              # Bambu Lab 打印机客户端和打印队列
├── config/                   # 本地配置模板
├── docs/                     # 状态、验证和开发计划文档
├── models/                   # 模型库
├── outputs/                  # 生成输出
├── scripts/                  # 根项目命令行工具
└── tests/                    # 标准库 unittest 测试
```

## 安装

基础打印/编排依赖:

```powershell
pip install -r requirements-print.txt
```

Hunyuan3D-2:

```powershell
cd Hunyuan3D-2
pip install -r requirements.txt
pip install -e .
```

Hunyuan3D-1 推荐使用 `Hunyuan3D-1/docker-compose.yml` 的 CUDA 13 镜像；原生 Linux 安装参考 `Hunyuan3D-1/README_zh_cn.md` 和 `Hunyuan3D-1/env_install.sh`。真实生成还需要下载对应模型权重。

```powershell
cd Hunyuan3D-1
docker compose build
docker compose run --rm hunyuan3d python scripts/text_to_3d_low_vram.py "a small robot" --output outputs/docker-low-vram
```

可选环境变量模板:

```powershell
copy config\env.example .env
```

- `HUNYUAN3D1_BACKEND`: `auto`、`docker` 或 `native`；`auto` 在 Docker 可用时优先使用已验证的低显存容器。
- `HUNYUAN3D1_PYTHON`: 仅在 `native` 后端下指定 Hunyuan3D-1 Python，可覆盖默认的项目虚拟环境。
- `HUNYUAN3D2_MODEL_PATH`: 指定 Hunyuan3D-2 本地模型快照或 Hugging Face repo；未传 `--model-path` 时由 `scripts/hunyuan2_image.py` 使用。
- `MODEL_COLLECTOR_MODELS_DIR`: 指定 `scripts/model_collector.py` 使用的模型库根目录，便于把演示或测试集合放到仓库外。
- `BAMBU_SLICER_EXE`: 指向 Bambu Studio 可执行文件。
- `BAMBU_SLICER_TEMPLATE`: 指向已在 Bambu Studio 中验证过的工程 3MF 或导出的 project-settings JSON。
- `BAMBU_SLICER_COMMAND`: 为 AI-to-print / continuous-print 配置自动切片桥接命令。
- `BAMBU_PRINTER_CA_CERT`: 可选的 Bambu `printer.cer` 路径；未设置时会在 `BAMBU_SLICER_EXE` 旁自动查找。

根目录脚本会自动加载仓库根目录的 `.env`，但不会覆盖 shell 中已经设置的同名变量。`.env` 只用于本地运行，不能提交到 Git。

先运行统一系统前置检查，集中查看 Hunyuan 权重、ComfyUI 工作流资产、外部切片器和打印机配置门槛:

```powershell
python scripts/system_preflight.py --allow-incomplete
python scripts/system_preflight.py --json --allow-incomplete
```

不带 `--allow-incomplete` 时，只要存在已知阻塞项就返回非 0，适合作为发布门禁。Hunyuan3D-1 原生运行时不可用时，检查会创建一次性 Docker 容器执行 CUDA/nvdiffrast 小栅格化；它不加载模型、不运行切片器、不连接打印机，因此 “ready” 仍只表示前置条件已就位。

## 生成模型

### Dry run 验证命令

不会加载模型，只打印将执行的真实命令:

```powershell
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
```

`hunyuan_quick.py` 在真实后端命令失败、批量目录不存在或批量目录没有图片时会返回非 0，并输出普通错误信息。

### 真实文字生成

```powershell
python scripts/hunyuan_quick.py text "a small robot"
```

自动后端会在 Docker 可用时调用 `Hunyuan3D-1/scripts/text_to_3d_low_vram.py`，把文生图、去背景、多视图和网格重建放在独立进程中，适用于 16 GB 显卡。可用 `--backend docker` 或 `--backend native` 显式选择。默认生成 `mesh_vertex_colors.obj`。

### 真实图片生成

```powershell
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --quality lite
```

这会调用 `scripts/hunyuan2_image.py`，由该包装器加载 Hunyuan3D-2 pipeline 并导出 GLB。需要 Hunyuan3D-2 依赖、权重和兼容 GPU/CPU 环境。

## AI 到打印工作流

`scripts/ai_to_print.py` 用于把生成、修复、入队串起来。为了避免假成功，它默认不会调用真实生成器，也不会返回不存在的模型。
没有生成模型时命令会返回非 0；`--mock --no-print` 是本地演示成功路径。

演示模式:

```powershell
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
```

真实生成模式:

```powershell
python scripts/ai_to_print.py text "a rabbit" --run-generator --no-print
python scripts/ai_to_print.py image Hunyuan3D-2/assets/demo.png --run-generator --no-print
```

去掉 `--no-print` 后，脚本会尝试读取本地打印机配置并把模型加入打印队列。
`ai_to_print.py` 和 `continuous_print.py` 会复用同一套本地配置检查；如果 `config/printer.json` 缺失或仍是模板占位值，请求打印的命令会返回非 0，避免把“只生成、未打印”误报为端到端成功。
`continuous_print.py generate --no-print` 在没有生成模型时也会返回非 0；加 `--mock` 是本地连续生成演示成功路径。
提示词列表的本地批量演示也需要显式跳过打印，例如 `python scripts/continuous_print.py prompts --file prompts.txt --delay 0 --mock --no-print`。
生成得到的 STL/OBJ/GLB 或普通几何 3MF 不能直接进 Bambu 队列。配置 `BAMBU_SLICER_EXE`、`BAMBU_SLICER_TEMPLATE` 和示例中的 `BAMBU_SLICER_COMMAND` 后，桥接脚本会自动缩放、定向、摆盘、切片，并只返回通过 ready-to-print 校验的 Bambu 工程 `.3mf`。

本机已从该根入口完成一次 25 步文生图、50 步多视图、90,000 面 OBJ、修复 STL 和 Bambu Studio 自动切片；生成的 P1S 项目 3MF 通过切片元数据校验。生成网格仍非 watertight，必须保留切片器检查和实物质量评估。

## Bambu Lab 打印机配置

复制模板:

```powershell
copy config\printer.json.example config\printer.json
```

编辑 `config/printer.json`:

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

配置也可以通过命令写入:

```powershell
python scripts/auto_print.py config --host YOUR_PRINTER_IP --serial YOUR_PRINTER_SERIAL --developer-mode
python scripts/auto_print.py check-config
```

`config` 会隐藏输入 Access Code，避免把凭据留在 shell 历史和进程参数中；写入前也会运行同一套本地配置检查。请把示例 IP 和序列号替换为真实打印机信息。需要 AMS 时增加 `--use-ams --ams-slot 0`，其中槽位范围为 0 到 15。

直接局域网控制需要打印机启用 LAN Only 模式或 Developer Mode。客户端使用隐式 FTPS（TCP 990）上传文件，并通过 MQTT/TLS（TCP 8883）的 `device/{serial}/report` 和 `device/{serial}/request` 主题读取状态、发送命令和等待设备回执。Bambu Lab 将 Developer Mode 的 MQTT/FTP 接口标记为不受官方支持，因此固件升级后应重新执行真实设备验证。

常用命令:

```powershell
python scripts/auto_print.py discover
python scripts/auto_print.py add path\to\plate.gcode --name demo
python scripts/auto_print.py list
python scripts/auto_print.py start
python scripts/auto_print.py status
python scripts/auto_print.py watch
```

`start` 会在当前终端持续处理队列直至清空；运行期间可在另一个终端使用
`pause`、`resume` 或 `stop`。运行状态写入用户目录下的队列目录，进程中断后只会在
打印机仍打印同名文件时接管监控，不会重复上传或重复启动。

打印队列只接收 ready-to-print 文件，例如 Bambu/OrcaSlicer 项目 `.3mf`、`.gcode` 或 `.bgcode`。可以直接验证自动切片桥接:

```powershell
python scripts/bambu_slicer_bridge.py outputs/demo/demo.stl outputs/demo/demo.gcode.3mf `
  --slicer-exe "D:\path\to\bambu-studio.exe" `
  --template "D:\path\to\known-good-project.3mf"
```

模板提供打印机、喷嘴、层高、耗材和工艺参数；源模型几何仍来自输入文件。命令模板支持 `{input}`、`{output}`、`{output_dir}` 占位符，输出必须通过切片元数据校验后才能继续入队。

`BAMBU_SLICER_OUTPUT_EXT` 的 output extension 只允许 `.3mf`、`.gcode` 或 `.bgcode`；其他值会在执行切片器前被 reject。

注意: `add` 只入队，不会默认连接或启动打印机；需要显式运行 `start`。
`config`、`check-config`、`ai_to_print.py` 和 `continuous_print.py` 使用同一套本地配置 preflight。

## 模型转换和模型库

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
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
```

`model_converter.py` 对未知命令、缺少参数和不存在的输入文件会返回非 0，并输出普通错误信息。

添加到模型库:

```powershell
python scripts/model_collector.py add outputs/demo/demo.stl demo demo_model
python scripts/model_collector.py list
python scripts/model_collector.py export demo_model
```

`MODEL_COLLECTOR_MODELS_DIR` 可覆盖默认的 `models/` 目录；CLI 对未知命令、缺少参数和不存在的导出目标会返回非 0。

## 批量创意生成脚本

`scripts/generate_claude_crabs.py` 提供一组 Claude 主题小螃蟹提示词，调用 Hunyuan3D-1 批量生成模型。

查看提示词列表:

```powershell
python scripts/generate_claude_crabs.py --list
```

真实批量生成:

```powershell
python scripts/generate_claude_crabs.py --count 2 --output outputs/claude_crabs_demo
```

该脚本会调用 `Hunyuan3D-1/main.py`，因此同样需要 Hunyuan3D-1 依赖、权重和可用硬件。
`--list` 是本地成功路径；缺少 Hunyuan3D-1 入口或批量生成失败时 CLI 会返回非 0。

## ComfyUI

本地存在 `ComfyUI/` 和 `ComfyUI-Win-Blackwell/` 相关目录。`ComfyUI/` 是本地运行资产，已加入 `.gitignore`。

启动方式取决于你的本地 ComfyUI 安装，例如:

```powershell
cd ComfyUI
python main.py --disable-xformers --use-pytorch-cross-attention
```

准备并严格检查 Hunyuan3DWrapper 示例工作流引用的模型和输入图:

```powershell
python scripts/prepare_comfyui_workflow_assets.py --include-optional
python scripts/check_comfyui_workflow_assets.py
```

运行一个低成本的真实 API 图；脚本会按需启动并关闭临时 ComfyUI 服务，成功时输出生成 GLB 的网格统计:

```powershell
python scripts/comfyui_hunyuan_smoke.py --start-server --timeout 600
```

本机验证使用 5 步、128 octree、5000 面目标，输出 2356 个顶点、5000 个面且 watertight 的 GLB。完整质量工作流仍会使用更多显存和时间。

## 验证

本地静态/轻量验证:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python -m unittest tests.test_ai_to_print -v
python -m unittest tests.test_continuous_print -v
python scripts/system_preflight.py --allow-incomplete
python scripts/hunyuan_quick.py text "a small robot" --dry-run
python scripts/check_comfyui_workflow_assets.py
python scripts/comfyui_hunyuan_smoke.py --start-server --timeout 600
# Expected to report a missing local secret and exit nonzero until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
```

完整验证清单见 [docs/VERIFICATION.md](docs/VERIFICATION.md)。
交付摘要见 [docs/HANDOFF.md](docs/HANDOFF.md)。

## 不应提交的内容

以下内容应保持本地:

- `config/printer.json`
- `.env`
- `ComfyUI/`
- `Hunyuan3D-1/venv/`
- 模型权重，如 `*.safetensors`、`*.pt`、`*.ckpt`
- 临时输出目录，如 `outputs/text_*`、`outputs/img_*`、`outputs/continuous/`
- 本地模型工作区产物，如 `models/raw/`、`models/collection/`、`models/slicer-input/`、`models/converted/`
- 打印队列和日志

## 许可证

Hunyuan3D-1 和 Hunyuan3D-2 受腾讯混元相关许可约束。使用模型权重、上游源码和第三方依赖前，请阅读各自目录中的许可证和 README。
