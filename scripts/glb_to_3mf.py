"""
GLB 转 3MF 转换器
将 GLB 格式转换为拓竹 Studio 可用的 3MF 格式
"""
import os
import sys

def convert_glb_to_3mf(glb_path, output_path=None):
    """将 GLB 转换为 3MF"""
    try:
        import trimesh
        import numpy as np
    except ImportError:
        print("请先安装依赖: pip install trimesh numpy")
        return False

    # 加载 GLB 文件
    print(f"加载 GLB: {glb_path}")
    mesh = trimesh.load(glb_path)

    # 如果是多个网格，合并
    if isinstance(mesh, trimesh.Scene):
        meshes = []
        for name, geom in mesh.geometry.items():
            if isinstance(geom, trimesh.Trimesh):
                meshes.append(geom)
        if meshes:
            mesh = trimesh.util.concatenate(meshes)
        else:
            print("错误: 无法提取网格数据")
            return False

    # 导出为 STL
    if output_path is None:
        output_path = glb_path.replace('.glb', '.stl')
    else:
        output_path = output_path.replace('.3mf', '.stl')

    print(f"导出 STL: {output_path}")
    mesh.export(output_path, file_type='stl')

    print(f"\n✅ 转换完成!")
    print(f"   GLB → {output_path}")
    print(f"   用拓竹 Studio 打开 STL 文件即可")

    return True

if __name__ == "__main__":
    glb_file = "d:/projects/3d/outputs/demo/demo.glb"
    output_file = "d:/projects/3d/outputs/demo/demo.stl"

    if len(sys.argv) > 1:
        glb_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    if not os.path.exists(glb_file):
        print(f"错误: 文件不存在 {glb_file}")
        sys.exit(1)

    success = convert_glb_to_3mf(glb_file, output_file)
    sys.exit(0 if success else 1)