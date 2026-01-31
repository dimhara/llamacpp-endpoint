# vLLM Secure Worker

A lightweight, security-focused serverless handler for [vLLM](https://github.com/vllm-project/vllm) on RunPod.

This project provides a simplified, encrypted interface for deploying Large Language Models (LLMs) like Llama 3, Mistral, and Qwen. It strips away the complexity of the official RunPod worker in favor of a direct, encrypted-input pipeline with streaming support.

## Features

*   **🔒 End-to-End Input Encryption**: Prompts are encrypted on the client using Fernet (symmetric encryption). The server decrypts them strictly in memory. The prompt text never traverses the network in plain text.
*   **⚡ High-Performance Inference**: Powered by vLLM (paged attention) for state-of-the-art throughput.
*   **🌊 Token Streaming**: Supports real-time token streaming back to the client via RunPod's generator interface.
*   **📦 Smart Caching**: Automatically handles model downloads from HuggingFace, supporting caching on RunPod Network Volumes for instant cold starts.
*   **🛠️ Argument Agnostic**: Pass standard sampling parameters (`temperature`, `top_p`, `max_tokens`) dynamically.

---

## 1. Setup & Deployment

### A. Docker Build
Build the image locally or via GitHub Actions.

```bash
docker build -t dimhara/vllm-secure-worker:latest .
docker push dimhara/vllm-secure-worker:latest
```

### B. RunPod Configuration
Create a Serverless Endpoint on RunPod using your Docker image. Set the following **Environment Variables**:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `MODELS` | **Required.** Comma-separated list of HuggingFace Repo IDs. The first one is loaded by default. | `meta-llama/Meta-Llama-3-8B-Instruct` |
| `ENCRYPTION_KEY` | **Required.** A 32-byte URL-safe base64 key. | Generate one using the snippet below. |
| `HF_TOKEN` | Optional. Required for gated models (like Llama 3). | `hf_...` |
| `GPU_MEMORY_UTILIZATION` | vLLM VRAM reservation (0.0 to 1.0). | `0.95` (Default) |
| `MAX_MODEL_LEN` | Maximum context length. | `4096` (Default) |

#### Generating an Encryption Key
Run this Python one-liner to generate a valid key for your environment variables and client:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 2. Client Usage

Use the provided `client.py` to interact with your endpoint. This script handles the encryption of your prompt before sending it.

### Configuration
Edit the top of `client.py`:
```python
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_RUNPOD_API_KEY"
ENCRYPTION_KEY = "YOUR_GENERATED_KEY_HERE" # Must match Server
```

### Running Inference
```bash
# Basic Usage
python client.py -p "Explain quantum computing in one sentence."

# With Sampling Parameters
python client.py \
  -p "Write a poem about rust." \
  --temp 0.8 \
  --max-tokens 200
```

**How it works:**
1. Client encrypts the prompt json payload.
2. Encrypted blob is sent to RunPod.
3. Server decrypts blob in memory.
4. vLLM generates text.
5. Tokens are streamed back to the client in real-time.

---

## 3. Local Testing

You can test the handler logic inside the Docker container (or a RunPod Interactive pod) without triggering an API call. This is useful for debugging model loading and memory issues.

1. SSH into the Pod.
2. Run the test script:

```bash
# Ensure env vars are set if testing manually
export ENCRYPTION_KEY="your_key..."
export MODELS="facebook/opt-125m"

# Run test
python3 test_local.py --prompt "To be or not to be,"
```

---

## 4. Directory Structure

*   **`Dockerfile`**: Based on `vllm/vllm-openai`, adds security/handler logic.
*   **`rp_handler.py`**: The entry point. Initializes the AsyncLLMEngine, handles decryption, and yields streaming responses.
*   **`utils.py`**: Handles downloading full model snapshots from HuggingFace to `/models`.
*   **`client.py`**: Reference client implementation.
*   **`start.sh`**: Startup script for interactive debugging (keeps container alive).

## 5. Security Notes

*   **Input**: Heavily secured. The prompt is opaque to the RunPod proxy and network intermediaries.
*   **Output**: Streamed back via standard HTTPS. While HTTPS is secure, the response body is not double-encrypted by Fernet in this version to maintain streaming performance.
*   **Storage**: Models are cached to disk, but prompts and generation contexts are held strictly in VRAM/RAM during the request lifecycle.

