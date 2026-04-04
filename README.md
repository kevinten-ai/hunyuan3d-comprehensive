# 🎯 拓竹3D打印机 AI模型生成方案

> 用AI从文字/图片生成3D模型，直接打印！

**一句话说明**：这是一个本地部署的3D生成AI，可以为你的拓竹(Bambu Lab)打印机创建独特的3D模型。

---

## ⚡ 快速开始

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

---

## 📁 目录结构

```
d:/projects/3d/
├── Hunyuan3D-1/              # 文字→3D (快速)
├── Hunyuan3D-2/              # 图片→3D (高质量)
├── scripts/                  # 工具脚本
│   ├── hunyuan_quick.py     # 一键生成
│   ├── model_collector.py   # 模型管理
│   └── model_converter.py   # 格式转换/修复
├── models/
│   ├── collection/          # 收藏的模型
│   └── ready-to-print/      # 可直接打印的STL
└── outputs/                  # 临时输出
```

---

## 🖨️ 拓竹打印设置建议

| 类型 | 层高 | 填充 | 适用场景 |
|------|------|------|----------|
| 标准 | 0.2mm | 15-20% | 日常打印 |
| 高精度 | 0.12mm | 15-20% | 精细模型 |
| 机械零件 | 0.16mm | 40-60% | 功能件 |

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

## 🔗 相关文档

- [拓竹打印工作流](./PRINT_WORKFLOW.md) - 完整流程详解
- [Hunyuan3D-1 中文文档](./Hunyuan3D-1/README_zh_cn.md)
- [Hunyuan3D-2 中文文档](./Hunyuan3D-2/README_zh_cn.md)

---

<div align="center">

**🎉 开始为你的拓竹打印机创造独特的3D模型吧！**

</div>
