# Hunyuan3D + Bambu Lab 3D 打印整合项目

本仓库是一个本地 3D 生成与打印编排层，目标是把 Hunyuan3D-1、Hunyuan3D-2、ComfyUI 和 Bambu Lab 打印机工作流连接起来。

GitHub 仓库: https://github.com/kevinten-ai/hunyuan3d-comprehensive

## 当前状态

这个项目已经包含可用的基础模块，但完整端到端打印仍依赖外部条件。

| 模块 | 当前状态 | 说明 |
|---|---|---|
| Hunyuan3D-1 | 已包含源码 | 用于文字生成 3D；真实运行需要权重、CUDA/Python 环境 |
| Hunyuan3D-2 | 已包含源码 | 用于图片生成 3D；真实运行需要权重、CUDA/Python 环境 |
| ComfyUI | 本地运行资产 | `ComfyUI/` 是本地目录，不作为仓库代码提交 |
| 模型转换 | 已实现 | `scripts/model_converter.py` 使用 `trimesh` 转换/修复 STL、OBJ、GLB 等 |
| 模型收集 | 已实现 | `scripts/model_collector.py` 管理模型库和 ready-to-print 导出 |
| Bambu 打印队列 | 已实现基础层 | `bambu_print/` 管理队列、状态、MQTT 控制命令 |
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

Hunyuan3D-1 的完整安装请参考 `Hunyuan3D-1/README_zh_cn.md` 和 `Hunyuan3D-1/env_install.sh`。真实生成还需要下载对应模型权重。

可选环境变量模板:

```powershell
copy config\env.example .env
```

- `HUNYUAN3D1_PYTHON`: 指定 Hunyuan3D-1 使用的 Python，可覆盖默认的 `Hunyuan3D-1/venv/Scripts/python.exe`。
- `HUNYUAN3D2_MODEL_PATH`: 指定 Hunyuan3D-2 本地模型快照或 Hugging Face repo；未传 `--model-path` 时由 `scripts/hunyuan2_image.py` 使用。

`.env` 只用于本地运行，不能提交到 Git。

## 生成模型

### Dry run 验证命令

不会加载模型，只打印将执行的真实命令:

```powershell
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
```

### 真实文字生成

```powershell
python scripts/hunyuan_quick.py text "a small robot" --lite
```

这会调用 `Hunyuan3D-1/main.py`。需要 Hunyuan3D-1 依赖、权重和兼容 GPU/CPU 环境。

### 真实图片生成

```powershell
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --quality lite
```

这会调用 `scripts/hunyuan2_image.py`，由该包装器加载 Hunyuan3D-2 pipeline 并导出 GLB。需要 Hunyuan3D-2 依赖、权重和兼容 GPU/CPU 环境。

## AI 到打印工作流

`scripts/ai_to_print.py` 用于把生成、修复、入队串起来。为了避免假成功，它默认不会调用真实生成器，也不会返回不存在的模型。

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
`ai_to_print.py` 和 `continuous_print.py` 会复用同一套本地配置检查；如果 `config/printer.json` 仍是模板占位值，会跳过自动打印。

## Bambu Lab 打印机配置

复制模板:

```powershell
copy config\printer.json.example config\printer.json
```

编辑 `config/printer.json`:

```json
{
  "host": "192.168.1.100",
  "access_code": "YOUR_ACCESS_CODE",
  "serial": "SNXXX",
  "method": "mqtt"
}
```

配置也可以通过命令写入:

```powershell
python scripts/auto_print.py config --host 192.168.1.100 --access-code YOUR_CODE --serial SNXXX
python scripts/auto_print.py check-config
```

`config` 写入前也会运行同一套本地配置检查；请把示例 IP、访问码和序列号替换为真实打印机信息。

常用命令:

```powershell
python scripts/auto_print.py discover
python scripts/auto_print.py add outputs/demo/demo.stl --name demo
python scripts/auto_print.py list
python scripts/auto_print.py start
python scripts/auto_print.py status
python scripts/auto_print.py watch
```

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

添加到模型库:

```powershell
python scripts/model_collector.py add outputs/demo/demo.stl demo demo_model
python scripts/model_collector.py list
python scripts/model_collector.py export demo_model
```

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

## ComfyUI

本地存在 `ComfyUI/` 和 `ComfyUI-Win-Blackwell/` 相关目录。`ComfyUI/` 是本地运行资产，已加入 `.gitignore`。

启动方式取决于你的本地 ComfyUI 安装，例如:

```powershell
cd ComfyUI
python main.py --disable-xformers --use-pytorch-cross-attention
```

启动后访问 `http://localhost:8188`，加载 Hunyuan3D 工作流。该部分需要单独验证工作流 JSON、模型位置和显卡环境。

可先检查 Hunyuan3DWrapper 示例工作流引用的本地模型和输入图是否齐全:

```powershell
python scripts/check_comfyui_workflow_assets.py --allow-missing
```

若命令报告缺失 `models/diffusion_models/hy3dgen/...`、`models/upscale_models/...` 或 `input/...`，需要先把对应资产放到 ComfyUI 目录中，再执行工作流。

## 验证

本地静态/轻量验证:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/hunyuan_quick.py text "a small robot" --dry-run
python scripts/check_comfyui_workflow_assets.py --allow-missing
# Expected to report a missing local secret and exit nonzero until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
```

完整验证清单见 [docs/VERIFICATION.md](docs/VERIFICATION.md)。

## 不应提交的内容

以下内容应保持本地:

- `config/printer.json`
- `.env`
- `ComfyUI/`
- `Hunyuan3D-1/venv/`
- 模型权重，如 `*.safetensors`、`*.pt`、`*.ckpt`
- 临时输出目录，如 `outputs/text_*`、`outputs/img_*`、`outputs/continuous/`
- 打印队列和日志

## 许可证

Hunyuan3D-1 和 Hunyuan3D-2 受腾讯混元相关许可约束。使用模型权重、上游源码和第三方依赖前，请阅读各自目录中的许可证和 README。
