"""
3D模型格式转换工具

支持拓竹3D打印机常用格式:
- STL: 拓竹原生支持
- 3MF: 带颜色材料的完整包
- OBJ: 通用格式

依赖:
    pip install trimesh numpy-stl
"""

import os
import sys
from pathlib import Path
from typing import Optional
import numpy as np

# 可选依赖，优雅处理
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("警告: trimesh未安装，格式转换功能受限")

try:
    from stl import mesh as numpy_stl
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "models" / "converted"


class ModelConverter:
    """3D模型格式转换器"""

    SUPPORTED_READ = ['.stl', '.obj', '.ply', '.glb', '.gltf', '.3mf']
    SUPPORTED_WRITE = ['.stl', '.obj', '.ply']

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert(self, input_path: str, output_format: str,
                output_name: Optional[str] = None) -> Path:
        """
        转换模型格式

        Args:
            input_path: 输入文件路径
            output_format: 输出格式 (.stl, .obj, .ply)
            output_name: 输出文件名（不含扩展名）

        Returns:
            输出文件路径
        """
        if not TRIMESH_AVAILABLE:
            raise RuntimeError("trimesg未安装，无法进行格式转换")

        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        ext = input_path.suffix.lower()
        if ext not in self.SUPPORTED_READ:
            raise ValueError(f"不支持读取格式: {ext}")

        if not output_format.startswith('.'):
            output_format = '.' + output_format
        if output_format.lower() not in self.SUPPORTED_WRITE:
            raise ValueError(f"不支持输出格式: {output_format}")

        # 加载模型
        print(f"加载模型: {input_path}")
        mesh = trimesh.load(str(input_path))

        # 确定输出路径
        if output_name is None:
            output_name = input_path.stem
        output_path = self.output_dir / f"{output_name}{output_format}"

        # 导出
        print(f"转换中: {output_path}")
        mesh.export(str(output_path), file_type=output_format[1:])

        print(f"✓ 转换完成: {output_path}")
        return output_path

    def to_stl(self, input_path: str, output_name: Optional[str] = None) -> Path:
        """转换为STL（拓竹原生格式）"""
        return self.convert(input_path, '.stl', output_name)

    def to_3mf(self, input_path: str, output_name: Optional[str] = None) -> Path:
        """转换为3MF（含颜色信息）"""
        return self.convert(input_path, '.3mf', output_name)

    def repair_mesh(self, input_path: str, output_name: Optional[str] = None) -> Path:
        """
        修复模型问题（填补空洞、修复法线等）
        拓竹打印前建议修复
        """
        if not TRIMESH_AVAILABLE:
            raise RuntimeError("trimesg未安装，无法修复模型")

        input_path = Path(input_path)
        mesh = trimesh.load(str(input_path))

        # 修复操作
        print("修复中...")

        # 1. 填补小空洞
        mesh.fill_holes()

        # 2. 修复法线
        mesh.fix_normals()

        # 3. 移除重复顶点
        mesh.merge_vertices()

        # 4. 确保watertight（可打印）
        if not mesh.is_watertight:
            print("  警告: 模型可能不是完全封闭的")
            # 尝试修复
            trimesh.repair.fill_holes(mesh)

        output_name = output_name or (input_path.stem + "_repaired")
        output_path = self.output_dir / f"{output_name}.stl"

        mesh.export(str(output_path), file_type='stl')
        print(f"✓ 模型已修复: {output_path}")
        return output_path

    def get_info(self, input_path: str) -> dict:
        """获取模型信息"""
        if not TRIMESH_AVAILABLE:
            raise RuntimeError("trimesg未安装，无法读取模型信息")

        input_path = Path(input_path)
        mesh = trimesh.load(str(input_path))

        info = {
            'file': input_path.name,
            'vertices': len(mesh.vertices),
            'faces': len(mesh.faces),
            'is_watertight': mesh.is_watertight,
            'is_empty': mesh.is_empty,
            'volume': mesh.volume if hasattr(mesh, 'volume') else None,
            'bounds': mesh.bounds.tolist() if hasattr(mesh, 'bounds') else None,
        }

        return info


def main():
    """命令行入口"""
    if not TRIMESH_AVAILABLE:
        print("错误: 请先安装 trimesh")
        print("  pip install trimesh")
        return

    converter = ModelConverter()

    if len(sys.argv) < 2:
        print("""
3D模型格式转换工具
==================
用法:
  python model_converter.py convert <输入文件> <输出格式> [输出名]
  python model_converter.py repair <输入文件> [输出名]
  python model_converter.py info <文件>

示例:
  python model_converter.py convert model.obj stl my_model
  python model_converter.py repair ./output/model.stl
  python model_converter.py info model.stl
        """)
        return

    cmd = sys.argv[1].lower()

    if cmd == 'convert':
        if len(sys.argv) < 4:
            print("错误: 请提供输入文件和输出格式")
            return
        converter.convert(sys.argv[2], sys.argv[3],
                          sys.argv[4] if len(sys.argv) > 4 else None)

    elif cmd == 'repair':
        if len(sys.argv) < 3:
            print("错误: 请提供输入文件")
            return
        converter.repair_mesh(sys.argv[2],
                              sys.argv[3] if len(sys.argv) > 3 else None)

    elif cmd == 'info':
        if len(sys.argv) < 3:
            print("错误: 请提供文件路径")
            return
        info = converter.get_info(sys.argv[2])
        print(f"""
模型信息:
--------
文件: {info['file']}
顶点数: {info['vertices']:,}
面数: {info['faces']:,}
体积: {info['volume']:.2f} cm³" if info['volume'] else "N/A"
边界: {info['bounds']}
封闭性: {'✓ 是' if info['is_watertight'] else '✗ 否 (可能需要修复)'}
        """)

    else:
        print(f"未知命令: {cmd}")


if __name__ == '__main__':
    main()
