# llama.cpp Secure Worker (v2025)

A high-performance, privacy-first serverless worker for [llama.cpp](https://github.com/ggerganov/llama.cpp) optimized for RunPod. This worker is designed for **low-latency cold starts** and **zero-disk data handling**.

## 🚀 2025 Features
*   **Encrypted Logic**: Payloads are encrypted locally via **AES-128 (Fernet)**. Decryption happens strictly in the Pod's RAM.
*   **DeepSeek-R1 Native**: Supports the new `reasoning_content` field to capture and stream "Chain of Thought" tokens.
*   **Flash Attention**: Pre-compiled with FA support for massive speed boosts on Ampere+ GPUs (A10, A100, RTX 30/40 series).
*   **Auto-Jinja Templates**: Automatically resolves official chat templates (Llama 3, Qwen 2.5, DeepSeek) from model metadata.

---

## 🛠️ Configuration (Environment Variables)

| Variable | Description | Default | Example |
| :--- | :--- | :--- | :--- |
| `MODELS` | **Required.** Format: `repo_id:filename` | - | `unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf` |
| `ENCRYPTION_KEY` | **Required.** 32-byte URL-safe base64 key. | - | `Generate using the command below.` |
| `RUN_MODE` | `SECURE_WORKER` or `OPENAI_SERVER`. | `SECURE_WORKER` | `SECURE_WORKER` |
| `CHAT_FORMAT` | Chat handler logic. | `jinja` | `jinja`, `qwen`, `llama-3`, `chatml` |
| `MAX_MODEL_LEN` | Context window size (tokens). | `4096` | `8192` |
| `ENABLE_FLASH_ATTN` | Enable Flash Attention (Requires Ampere+). | `false` | `true` |
| `LISTEN_ADDR` | IP for `OPENAI_SERVER` mode. | `127.0.0.1` | `0.0.0.0` (for public access) |
| `API_KEY` | Optional auth key for `OPENAI_SERVER`. | - | `your-secret-api-key` |

---

## 🔒 Security Modes

### 1. Secure Worker (Serverless Mode)
This mode is designed for maximum privacy. It uses RunPod's Serverless infrastructure to scale to zero when not in use.
*   **How it works**: You encrypt your prompt + history locally. The worker decrypts it in RAM, generates a response, and sends it back. 
*   **Benefit**: Cleartext data never exists on RunPod's persistent storage.
*   **Usage**: Set `RUN_MODE=SECURE_WORKER`. Use `client.py` to talk to it.

### 2. OpenAI Server (Full Pod Mode)
This mode transforms the pod into a standard OpenAI-compatible API.
*   **How it works**: Launches the `llama_cpp.server` module.
*   **Security (Local-Only)**: By default, it binds to `127.0.0.1`. You must use an **SSH Tunnel** to access it.
*   **Usage**: 
    1. Set `RUN_MODE=OPENAI_SERVER` and `LISTEN_ADDR=127.0.0.1`.
    2. From your local terminal, run: `ssh -L 8000:127.0.0.1:8000 -p [POD_SSH_PORT] root@[POD_IP]`
    3. Access your API locally at `http://localhost:8000/v1`.

---

## 📦 Setup Instructions

### 1. Generate Encryption Key
Before deploying, generate your AES-128 key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Deployment
*   **Fat Image Option**: To eliminate download time during cold starts, use a `Dockerfile` that starts `FROM` this image and runs `python3 utils.py /models` to "bake" the model into the container.
*   **RunPod Volume**: Alternatively, mount a RunPod Network Volume to `/models` to cache the GGUF file across pod restarts.

### 3. Client Usage
Update your environment variables and run the interactive chat:
```bash
export RUNPOD_API_KEY="your_key"
export RUNPOD_ENDPOINT_ID="your_id"
export ENCRYPTION_KEY="your_aes_key"

python3 client.py --system "You are a private assistant. Reason in English."
```

---

## ⚡ Performance Tips
1.  **Quantization**: Use `Q4_K_M` or `IQ4_XS` GGUF files for the best performance/quality ratio.
2.  **GPU Layers**: This worker is configured to offload **all layers** (`-1`) to the GPU by default.
3.  **DeepSeek-R1**: Small distilled models (1.5B/7B) generate "Reasoning" tokens before the final answer. **Always set `max_tokens` to at least 1024** in your client to ensure the model doesn't cut off during its thinking phase.

---

## 🛠️ Project Structure
*   `rp_handler.py`: RunPod entry point. Decrypts in RAM and handles `reasoning_content`.
*   `utils.py`: Fast model downloader using `hf_transfer`.
*   `client.py`: Reference client implementing Fernet encryption and RunPod stream parsing.
*   `start.sh`: Mode-switcher logic.
*   `Dockerfile`: Multi-stage build optimized for CUDA 12.4.
