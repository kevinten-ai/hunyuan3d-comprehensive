# syntax=docker/dockerfile:1.7
FROM nvidia/cuda:13.0.2-devel-ubuntu24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    PATH=/opt/venv/bin:$PATH \
    TORCH_CUDA_ARCH_LIST=12.0 \
    FORCE_CUDA=1 \
    MAX_JOBS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    freeglut3-dev \
    git \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libosmesa6-dev \
    ninja-build \
    python3-dev \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel

# CUDA 13 wheels include Blackwell (sm_120) support. Keep them separate from
# the upstream Windows/cu121 lock so Docker does not downgrade the runtime.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
      torch==2.10.0 torchvision==0.25.0 \
      --index-url https://download.pytorch.org/whl/cu130

WORKDIR /app
COPY requirements-core.txt ./requirements-core.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r requirements-core.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
      "git+https://github.com/NVlabs/nvdiffrast.git@253ac4fcea7de5f396371124af597e6cc957bfae" \
      --no-build-isolation
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-deps \
      xformers==0.0.35 \
      --index-url https://download.pytorch.org/whl/cu130

RUN python -c "import torch; assert torch.version.cuda == '13.0'; print('PyTorch CUDA 13 wheel ready')" \
    && python -c "import nvdiffrast.torch, xformers; print('Hunyuan3D-1 native extensions ready')"

FROM nvidia/cuda:13.0.2-runtime-ubuntu24.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libglut3.12 \
    libosmesa6 \
    python3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
EXPOSE 8080
CMD ["python", "app.py"]
