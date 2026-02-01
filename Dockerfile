# ==========================================
# Stage 1: Builder (Heavy, includes Compiler)
# ==========================================
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. Install Build Dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    ninja-build \
    cmake \
    git \
    build-essential \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Virtual Environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Upgrade pip and build tools
RUN pip3 install --upgrade pip setuptools wheel scikit-build-core

# =======================================================
# FIX FOR GITHUB ACTIONS (NO GPU)
# Link against CUDA stubs so the build succeeds without a Driver
# =======================================================
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64/stubs:${LD_LIBRARY_PATH}"

# 4. Build llama-cpp-python with CUDA optimizations
RUN CMAKE_ARGS="-DGGML_CUDA=on -DGGML_CUDA_F16=on -DGGML_FLASH_ATTN=on" \
    pip3 install --no-cache-dir llama-cpp-python[server]

# 5. Install other Python dependencies
RUN pip3 install --no-cache-dir runpod cryptography huggingface_hub hf_transfer

# ==========================================
# Stage 2: Runtime (Lightweight, no Compiler)
# ==========================================
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
# Set path to use the copied venv
ENV PATH="/opt/venv/bin:$PATH"
# Enable HF Transfer for fast downloads
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV MODEL_DIR=/models

# 1. Install Runtime Dependencies (No compilers needed)
RUN apt-get update && apt-get install -y \
    python3 \
    libgomp1 \
    curl \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# 3. Setup Application
WORKDIR /app
COPY . .
RUN chmod +x start.sh

# 4. Entrypoint
# Use an empty ENTRYPOINT to ensure CMD has full control -- allows override from runpod
ENTRYPOINT []
CMD ["/bin/bash", "/app/start.sh"]
