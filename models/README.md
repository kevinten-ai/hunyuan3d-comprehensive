# 3D Model Repository for Bambu Lab Printers
# 拓竹3D打印机模型库

本目录用于存储和管理可打印的3D模型文件。

## 目录结构
```
models/
├── raw/                    # 原始生成的模型（未处理）
│   ├── text-to-3d/        # 文字生成模型
│   └── image-to-3d/        # 图片生成模型
├── processed/             # 已处理模型（优化、切片参数）
├── ready-to-print/         # 可直接打印的模型
├── collection/             # 收集的模型库
│   ├── characters/         # 角色/人物
│   ├── animals/             # 动物
│   ├── tools/               # 工具
│   ├── toys/                # 玩具
│   ├── home-decor/          # 家居装饰
│   └── mechanical/           # 机械零件
└── archive/                # 归档模型
```

## 支持的文件格式
- **STL**: 拓竹打印机原生支持
- **3MF**: 带颜色和材料的完整模型包
- **OBJ**: 通用3D格式
- **PLY**: 点云格式

## 模型命名规范
```
{类别}_{名称}_{版本}_{日期}.{格式}
例: toys_dragon_statue_v1_20260404.stl
```
