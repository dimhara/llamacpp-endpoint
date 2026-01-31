# ==========================================
# RUNTIME
# ==========================================
FROM vllm/vllm-openai:v0.6.3

# We use the official vLLM image as base because compiling vLLM 
# from scratch takes a long time and is error-prone.
# This base image already has CUDA, Python, and vLLM installed.

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. Install Runtime Deps (SSH for debugging, git, etc)
RUN apt-get update && apt-get install -y \
    wget curl git libgomp1 openssh-server \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies for RunPod/Security
RUN pip3 install --no-cache-dir runpod cryptography huggingface_hub

# 3. Setup Directories
RUN mkdir -p /models && mkdir -p /workspace

# 4. Environment Variables
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV MODEL_DIR=/models

# 5. Copy Scripts
WORKDIR /
COPY utils.py /utils.py
COPY test_local.py /test_local.py
COPY rp_handler.py /rp_handler.py
COPY start.sh /start.sh
RUN chmod +x /start.sh

# DEFAULT CMD
CMD ["python3", "-u", "/rp_handler.py"]
