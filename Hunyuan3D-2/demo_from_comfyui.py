"""
Hunyuan3D-2 Demo 生成脚本
使用本地ComfyUI模型
"""

import os
import sys
from pathlib import Path

# 设置模型路径
COMFYUI_MODELS = Path("d:/projects/3d/ComfyUI/models/checkpoints")
os.environ['HF_HOME'] = str(COMFYUI_MODELS.parent.parent)
os.environ['TRANSFORMERS_CACHE'] = str(COMFYUI_MODELS.parent.parent / "huggingface")

from PIL import Image
import torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# 使用示例图片
demo_image = Path("d:/projects/3d/Hunyuan3D-2/assets/demo.png")
if not demo_image.exists():
    print(f"示例图片不存在: {demo_image}")
    sys.exit(1)

print(f"\n使用图片: {demo_image}")

# 检查模型
model_path = COMFYUI_MODELS / "hunyuan3d-dit-v2.safetensors"
print(f"模型路径: {model_path}")
print(f"模型存在: {model_path.exists()}")

# 由于模型格式不同，我们直接复制到Hunyuan3D-2期望的位置
import shutil
target_dir = Path("d:/projects/3d/Hunyuan3D-2/tencent/Hunyuan3D-2")
target_dir.mkdir(parents=True, exist_ok=True)

# 创建模型链接/复制
hf_model = target_dir / "models" / "safetensors"
hf_model.parent.mkdir(parents=True, exist_ok=True)

# 使用符号链接
try:
    link_path = target_dir / "model.fp16.safetensors"
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    shutil.copy(str(model_path), str(link_path))
    print(f"模型已复制到: {link_path}")
except Exception as e:
    print(f"复制失败: {e}")

print("\n开始生成3D模型...")
print("这可能需要几分钟时间...")

from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen import Hunyuan3DPaintPipeline

try:
    # 加载模型
    print("\n[1/3] 加载ShapeGen模型...")
    pipeline_shapegen = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("d:/projects/3d/Hunyuan3D-2/tencent/Hunyuan3D-2")

    print("[2/3] 处理图片...")
    image = Image.open(demo_image).convert("RGBA")
    if image.mode == 'RGB':
        rembg = BackgroundRemover()
        image = rembg(image)

    print("[3/3] 生成3D模型...")
    mesh = pipeline_shapegen(image=image)[0]

    # 导出
    output_path = Path("d:/projects/3d/output/demo_from_comfyui.glb")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(output_path))

    print(f"\n✅ 生成完成!")
    print(f"模型文件: {output_path}")
    print(f"文件大小: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

except Exception as e:
    print(f"生成失败: {e}")
    import traceback
    traceback.print_exc()
