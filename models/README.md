# Models Workspace

本目录是本地模型工作区，不是发布用模型包。这里的运行时产物默认应保持未跟踪，避免把生成模型、切片中间件或个人模型库提交到 Git。

## 当前目录语义

```text
models/
├── raw/             # 原始生成或临时导入的源模型草稿
├── collection/      # model_collector.py 管理的本地模型库副本，按类别归档
├── slicer-input/    # 导出给 Bambu Studio / OrcaSlicer 打开的源模型
├── converted/       # GLB/STL/OBJ 转换后的中间文件，例如普通几何 3MF
└── README.md        # 本说明文件
```

`models/raw/`、`models/collection/`、`models/slicer-input/`、`models/converted/` 都是本地工作目录，已经在 `.gitignore` 中忽略。旧的 `models/ready-to-print/` 路径也保持忽略，仅用于兼容历史本地文件，不再作为推荐目录。

## 文件格式边界

- STL、OBJ、GLB、GLTF、PLY、普通几何 3MF 都是源模型或切片器输入，不应直接加入 Bambu 打印队列。
- `scripts/model_converter.py` 和 `scripts/glb_to_3mf.py` 可以生成切片器可打开的 STL/3MF 中间文件，但这些文件仍不是 printer-ready 输出。
- 只有经过 Bambu Studio 或 OrcaSlicer 切片导出的 Bambu/OrcaSlicer 项目 `.3mf`、`.gcode` 或 `.bgcode` 才属于 ready-to-print 文件。
- `scripts/auto_print.py add` 和底层 `bambu_print.PrintQueue` 会拒绝源模型和缺少切片元数据的普通 3MF。

## 常用命令

```powershell
# 查看模型信息
python scripts/model_converter.py info outputs/demo/demo.stl

# 将 GLB 转换为切片器可打开的 3MF
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf

# 将本地模型加入模型库，并导出到 slicer-input
python scripts/model_collector.py add path\to\robot.stl toys robot
python scripts/model_collector.py export toys_robot_20260607_120000

# 添加已经切片导出的 ready-to-print 文件
python scripts/auto_print.py add path\to\plate.gcode --name demo
```

## 命名建议

模型库条目建议使用可读类别和名称，`model_collector.py` 会在复制时追加时间戳:

```text
{category}_{name}_{YYYYMMDD_HHMMSS}.{ext}
```

示例:

```text
toys_robot_20260607_120000.stl
mechanical_bracket_20260607_121500.3mf
```
