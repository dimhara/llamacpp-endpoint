# llama.cpp Secure Worker

A high-performance, security-focused serverless worker for [llama.cpp](https://github.com/ggerganov/llama.cpp) (via `llama-cpp-python`) optimized for RunPod.

This worker provides **low-latency cold starts** and **strict privacy**. It is designed for "the odd query" where vLLM's heavy initialization and massive VRAM pre-allocation are overkill.

## 🚀 Features
*   **Flash Attention**: Enabled by default for massive speed boosts on Ampere+ GPUs (A10, A100, RTX 30/40).
*   **Native Jinja2 Templates**: Automatically uses the official chat template embedded in the GGUF file (supports Llama 3.x, Qwen 2.5, DeepSeek R1, etc.).
*   **OpenAI Schema**: Fully supports the `messages` array (System/User/Assistant) natively.
*   **Dual Mode**: Switch between a Secure Serverless Worker and a standard OpenAI-compatible API server.

---

## 🔒 Security & Privacy Model

*   **End-to-End Prompt Encryption**: Payloads (prompts, history, and images) are encrypted via **Fernet (AES-128)** on the client. The worker decrypts them strictly in RAM.
*   **Zero-Disk Footprint**: 
    - Prompts and multimodal data are never written to `/tmp` or persistent storage.
    - Model contexts are wiped upon Serverless instance termination.
*   **Encrypted Transport**: Layered protection using HTTPS + symmetric payload encryption.

---

## 🛠️ Operating Modes

| Mode | Environment Variable | Use Case |
| :--- | :--- | :--- |
| **Secure Worker** | `RUN_MODE=SECURE_WORKER` (Default) | **Serverless.** Cold starts in < 3s. Requires Fernet decryption by the client. |
| **OpenAI Server** | `RUN_MODE=OPENAI_SERVER` | **Full Pod.** Connect directly to third-party tools (SillyTavern, etc.) on port 8000. |

---

## 1. Setup & Configuration

### Environment Variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `MODELS` | **Required.** Format: `repo_id:filename` | `unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf` |
| `ENCRYPTION_KEY` | **Required for Secure Worker.** | Generate using the snippet below. |
| `MAX_MODEL_LEN` | Context window size (tokens). | `4096` (Default: 4096) |
| `RUN_MODE` | Switch between `SECURE_WORKER` and `OPENAI_SERVER`. | `SECURE_WORKER` |
| `CHAT_FORMAT` | Chat template logic for server. | `qwen` (for DeepSeek R1), `llama-3` (for Llama 3), `chatml` (default) |





### Generate your Encryption Key
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 2. Deployment

### Building the Image
The Dockerfile uses **CUDA 12.4** and compiles `llama-cpp-python` with **Flash Attention** support.

```bash
docker build -t your-username/llama-cpp-secure-worker:latest .
docker push your-username/llama-cpp-secure-worker:latest
```

### RunPod Settings
*   **Container Image**: `your-username/llama-cpp-secure-worker:latest`
*   **Container Disk**: 20GB+ (depending on model size).
*   **GPU**: Requires NVIDIA GPU. Ampere or newer recommended for Flash Attention.

---

## 3. Usage

### Local Testing (Within a Pod)
To verify the engine, encryption, and Jinja templates are working:
```bash
export MODELS="Qwen/Qwen2.5-0.5B-Instruct-GGUF:qwen2.5-0.5b-instruct-q4_k_m.gguf"
export ENCRYPTION_KEY="your-key-here"

python3 test_local.py --prompt "Why is llama.cpp faster for cold starts than vLLM?"
```

### Secure Remote Client
Update `client.py` with your `ENDPOINT_ID`, `API_KEY`, and `ENCRYPTION_KEY`.
```bash
python client.py -p "Compare GGUF vs Safetensors."
```

---

## ⚡ Performance Tips

1.  **GGUF Quantization**: Use `Q4_K_M` or `IQ4_XS` for the best balance of speed and intelligence.
2.  **RunPod Volume**: In RunPod Endpoint settings, set the **Model** field to the Hugging Face repo ID. This mounts the model cache to `/runpod-volume/`, skipping the download step for future cold starts.
3.  **VRAM Offloading**: The worker is pre-configured with `n_gpu_layers=-1` to offload the entire model to the GPU for maximum speed.

---

## 🛠️ Project Structure
*   `rp_handler.py`: RunPod entry point. Decrypts input in RAM and uses `create_chat_completion`.
*   `utils.py`: Fast model downloader using `hf_transfer`.
*   `client.py`: Reference client implementing Fernet encryption and OpenAI schema.
*   `start.sh`: Mode-switcher (Secure Worker vs OpenAI Server).
*   `Dockerfile`: Optimized for NVIDIA CUDA 12.4 + Flash Attention.
