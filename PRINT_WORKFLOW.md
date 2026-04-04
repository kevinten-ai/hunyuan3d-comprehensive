# 拓竹3D打印机工作流

本文档描述如何使用本项目的AI生成功能为拓竹(Bambu Lab)3D打印机创建模型。

## 工作流程概览

```
文字/图片 -> Hunyuan3D AI生成 -> 模型修复/格式转换 -> 导出到Bambu Studio打印
```

## 快速开始

### 1. 环境准备

```bash
cd Hunyuan3D-2
pip install -r requirements.txt
pip install trimesh numpy
```

### 2. 生成模型

**方式一：使用快捷脚本**

```bash
# 文字生成
python scripts/hunyuan_quick.py text "a cute robot"

# 图片生成
python scripts/hunyuan_quick.py image ./photo.png

# 批量生成
python scripts/hunyuan_quick.py batch ./photos/
```

**方式二：直接使用Hunyuan3D**

```bash
# V2 图片转3D
cd Hunyuan3D-2
python minimal_demo.py

# V1 文字转3D
cd Hunyuan3D-1
python main.py --text_prompt "a dragon statue" --use_lite
```

### 3. 处理模型

```bash
# 修复模型（填补空洞、修复法线）
python scripts/model_converter.py repair ./output/model.stl

# 转换为STL
python scripts/model_converter.py convert ./output/model.obj stl

# 查看模型信息
python scripts/model_converter.py info ./output/model.stl
```

### 4. 收集管理模型

```bash
# 添加模型到库
python scripts/model_collector.py add ./model.stl toys my_robot

# 列出所有模型
python scripts/model_collector.py list

# 导出到打印目录
python scripts/model_collector.py export my_robot
```

### 5. 打印

1. 打开 **Bambu Studio**
2. 导入 `models/ready-to-print/` 目录下的STL文件
3. 选择拓竹打印机（X1C、P1S等）
4. 调整打印参数并切片
5. 发送打印

## 推荐打印设置

| 类型 | 层高 | 填充 | 壁厚 |
|------|------|------|------|
| 标准 | 0.2mm | 15-25% | 0.8mm |
| 高精度 | 0.12mm | 20% | 1.2mm |
| 机械零件 | 0.16mm | 40-60% | 1.6mm |

## 常见问题

**Q: 模型底部不平？**
A: 使用 `model_converter.py repair` 修复

**Q: 生成模型有裂缝？**
A: 尝试Hunyuan3D-2的PBR模式

**Q: 打印时拉丝？**
A: 在Bambu Studio中调整回抽设置
