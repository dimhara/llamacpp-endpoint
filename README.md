# llama.cpp Secure Worker

A high-performance, architecture-agnostic, and privacy-first serverless worker for [llama.cpp](https://github.com/ggerganov/llama.cpp) optimized for RunPod. 

## 🚀 Key Features
*   **Autoselect Templating**: Automatically extracts Jinja templates and special tokens (BOS/EOS) directly from GGUF metadata.
*   **Encrypted Logic**: Payloads are encrypted locally via **AES-128 (Fernet)**.
*   **Flash Attention**: Support for massive speed boosts on Ampere+ GPUs (A10, A100, RTX 30/40/50 series).
*   **Unix Pipeline Ready**: Use `client.py` as an interactive chat or a standard Unix tool in a command pipeline.

---

## 🛠️ Configuration (Environment Variables)

| Variable | Description | Required | Example |
| :--- | :--- | :--- | :--- |
| `MODELS` | GGUF model to load. | **Yes** | `unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF:DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf` |
| `ENCRYPTION_KEY` | 32-byte URL-safe base64 key. | **Yes** | Use command in Setup section to generate. |
| `RUN_MODE` | `SECURE_WORKER` or `OPENAI_SERVER`. | No | Defaults to `SECURE_WORKER`. |
| `MAX_MODEL_LEN` | Context window size (tokens). | No | Default `4096`. |
| `ENABLE_FLASH_ATTN` | Enable Flash Attention. | No | `true` (Requires Ampere+ GPU). |

---

## 🔒 Security Modes

### 1. Secure Worker (Serverless Mode)
Scales to zero when not in use. Prompts are decrypted only in the ephemeral RAM of the GPU worker.
*   **Usage**: Set `RUN_MODE=SECURE_WORKER`. Use `client.py` for communication.

### 2. OpenAI Server (Full Pod Mode)
Transforms the pod into a standard OpenAI-compatible API listening on localhost.
*   **Usage**: Set `RUN_MODE=OPENAI_SERVER` and use an SSH Tunnel to access `http://localhost:8000/v1`.

---

## 📦 Setup & Deployment

### 1. Generate Encryption Key
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. RunPod Environment
Ensure the following variables are set in your RunPod template:
*   `MODELS`: `repo:filename`
*   `ENCRYPTION_KEY`: (The key generated above)
*   `HF_TOKEN`: (Optional, for gated models like Llama 3)

---

## 🛠️ Client Usage (`client.py`)

The client requires `requests` and `cryptography`. 
Set `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`, and `ENCRYPTION_KEY` in your local environment.

### Mode A: Interactive Chat
Simply run the script to enter a conversational loop with full history support.
```bash
python3 client.py
```

### Mode B: Unix Pipeline
Pipe data from any command into `client.py`. It will combine the piped data with your prompt as context.
```bash
# Summarize a manual page
man ffmpeg | python3 client.py "Summarize the 5 most important flags"

# Analyze logs for errors
cat system.log | python3 client.py "Identify any security warnings" --temperature 0

# Use a custom system prompt and settings
python3 client.py "Write a poem about GPUs" --system "You are Shakespeare" --temperature 0.9
```

---

## ⚡ Performance & Compatibility Tips
1.  **Thinking Models**: For DeepSeek-R1, the worker automatically yields the pre-filled `<think>` tag if the template requires it.
2.  **Duplicate BOS**: The worker dynamically detects if a model adds its own Beginning-of-Sentence token to prevent the "Duplicate BOS" warning and maintain quality.
3.  **Large Context**: If using models with >32k context, adjust `MAX_MODEL_LEN` to fit your available VRAM.

## 🛠️ Project Structure
*   `rp_handler.py`: Python-native worker using `llama-cpp-python`.
*   `rp_handler_fork.py`: C++ binary-based proxy for maximum performance.
*   `client.py`: The multi-mode secure client and pipeline tool.
*   `utils.py`: Fast model downloader using `hf_transfer`.
