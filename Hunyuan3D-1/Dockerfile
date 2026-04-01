# 使用支持 CUDA 12.1 的官方 PyTorch 镜像
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel

# 设置环境变量，避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# 安装系统级依赖
RUN apt-get update && apt-get install -y \
    git \
    ninja-build \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libosmesa6-dev \
    freeglut3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 安装 pytorch3d (从预编译源安装，避免漫长的编译)
RUN pip install --no-cache-dir iopath fvcore
RUN pip install --no-cache-dir "git+https://github.com/facebookresearch/pytorch3d.git"

# 安装 nvdiffrast
RUN pip install --no-cache-dir git+https://github.com/NVlabs/nvdiffrast.git

# 复制项目依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 修复 Pydantic 兼容性
RUN pip install --no-cache-dir pydantic==1.10.12

# 暴露 Gradio 默认端口
EXPOSE 8080

# 默认运行 app.py (启动 Web UI)
CMD ["python", "app.py"]
