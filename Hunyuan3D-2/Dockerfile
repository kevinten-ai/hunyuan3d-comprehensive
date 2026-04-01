# 使用支持 CUDA 12.1 的官方 PyTorch 镜像
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    ninja-build \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libosmesa6-dev \
    freeglut3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e .

# 编译纹理插件
RUN cd hy3dgen/texgen/custom_rasterizer && python setup.py install && cd ../../..
RUN cd hy3dgen/texgen/differentiable_renderer && python setup.py install && cd ../../..

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "gradio_app.py", "--model_path", "tencent/Hunyuan3D-2", "--subfolder", "hunyuan3d-dit-v2-0", "--texgen_model_path", "tencent/Hunyuan3D-2", "--host", "0.0.0.0", "--port", "8080", "--low_vram_mode"]
