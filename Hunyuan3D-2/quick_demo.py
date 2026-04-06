"""
快速3D生成demo - 仅形状生成，速度更快
"""
from PIL import Image
import torch
import time

print("=" * 50)
print("Hunyuan3D-2 快速生成Demo")
print("=" * 50)

# 1. 加载模块
print("\n[1/4] 加载模块...")
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

# 2. 加载模型
print("[2/4] 加载模型...")
start = time.time()
pipeline_shapegen = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2')
print(f"模型加载完成: {time.time() - start:.1f}秒")

# 3. 加载图片
print("[3/4] 加载图片...")
image_path = 'assets/demo.png'
image = Image.open(image_path).convert("RGBA")
print(f"图片尺寸: {image.size}")

# 4. 生成模型
print("[4/4] 生成3D模型...")
start = time.time()

# 只生成形状（不生成纹理，速度更快）
mesh = pipeline_shapegen(image=image)[0]

elapsed = time.time() - start
print(f"生成完成: {elapsed:.1f}秒")

# 5. 保存
output_path = 'demo_output.glb'
mesh.export(output_path)
print(f"\n✅ 模型已保存: {output_path}")
print(f"   文件位置: d:/projects/3d/Hunyuan3D-2/{output_path}")