# Hunyuan3D Project Context

This workspace contains two major versions of Tencent's Hunyuan3D, a unified framework for high-fidelity Text-to-3D and Image-to-3D generation.

## Project Overview

### Hunyuan3D-1.0
A two-stage approach for 3D generation:
1.  **Multi-view Diffusion:** Generates multi-view RGB images in ~4 seconds.
2.  **Feed-forward Reconstruction:** Rapidly reconstructs 3D assets from multi-view images in ~7 seconds.
- **Versions:** Lite (faster, lower VRAM) and Standard (higher quality).
- **Key Components:** Hunyuan-DiT (Text-to-Image), Multi-view Diffusion (MVD), Sparse-view Reconstruction Model (SVRM), and a Texture Baking module.

### Hunyuan3D-2.0
An advanced large-scale 3D synthesis system featuring:
- **Hunyuan3D-DiT:** A scalable flow-based diffusion transformer for large-scale shape generation.
- **Hunyuan3D-Paint:** A large-scale texture synthesis model for high-resolution texture maps.
- **New Updates:** Includes Turbo models (distilled for speed) and support for PBR (Physically Based Rendering) materials (v2.1+).

---

## Technical Stack
- **Frameworks:** PyTorch, HuggingFace Diffusers, Transformers.
- **3D Libraries:** Trimesh, Xatlas, PyMeshLab, Open3D, PyMCubes.
- **Hardware Acceleration:** CUDA, Ninja (for compiling custom operators), Xformers/Flash-Attention.
- **Deployment:** Gradio (Web UI), FastAPI (API Server), Blender Addon.

---

## Building and Running

### Hunyuan3D-1.0
#### Installation
```bash
cd Hunyuan3D-1
conda create -n hunyuan3d-1 python=3.10
conda activate hunyuan3d-1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
bash env_install.sh
# Additional dependencies for baking/dust3r
cd third_party && git clone --recursive https://github.com/naver/dust3r.git
```

#### Inference
```bash
# Image to 3D (Standard)
python main.py --image_prompt "path/to/image.png" --save_folder ./outputs/test/ --do_texture_mapping --do_render

# Text to 3D (Lite)
python main.py --text_prompt "a lovely rabbit" --use_lite --save_folder ./outputs/test/
```

### Hunyuan3D-2.0
#### Installation
```bash
cd Hunyuan3D-2
pip install -r requirements.txt
pip install -e .

# Compile custom texture operators
cd hy3dgen/texgen/custom_rasterizer && python setup.py install
cd ../differentiable_renderer && python setup.py install
```

#### Inference
```bash
# Minimal Demo
python minimal_demo.py

# Gradio Web UI
python gradio_app.py --model_path tencent/Hunyuan3D-2 --subfolder hunyuan3d-dit-v2-0 --texgen_model_path tencent/Hunyuan3D-2 --low_vram_mode
```

---

## Development Conventions

- **Licensing:** Both versions are primarily under the **TENCENT HUNYUAN NON-COMMERCIAL LICENSE AGREEMENT**. Third-party components (like DUSt3R) have their own licenses.
- **Model Management:** Models are typically downloaded from HuggingFace (`tencent/Hunyuan3D-1`, `tencent/Hunyuan3D-2`).
- **Code Structure:**
    - `Hunyuan3D-1/infer/`: Core inference logic for V1.
    - `Hunyuan3D-2/hy3dgen/`: Main package for V2 (ShapeGen and TexGen).
- **VRAM Management:** Both versions support `--save_memory` or `--low_vram_mode` to accommodate GPUs with less memory (e.g., 16GB-24GB).
- **Testing:** New features or bug fixes should be verified using the `minimal_demo.py` (V2) or `main.py` (V1) scripts.
