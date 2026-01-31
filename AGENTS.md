# Agent Documentation (AGENTS.md)

## 🎯 Primary Objective (Definition of Done)
**Agent (Jules/others):** Your goal is to configure and deploy this worker such that the **Verification Protocol** below returns `SUCCESS`. You should iterate on the configuration (Dockerfile, Env Vars) until this test passes 100% of the time.

### 🏆 Verification Protocol
To verify success, you must be able to run this command inside the container and receive a streaming, decrypted response:

```bash
python3 test_local.py --prompt "Sanity check."
```

**Success Criteria:**
1.  **No Crash:** The script must not exit with an error code.
2.  **Streaming:** Output must be printed incrementally (not a single block after a long pause).
3.  **Correctness:** The output must be coherent English text (verifying encryption/decryption worked).
4.  **Performance:** Time-To-First-Token (TTFT) should be < 5 seconds on a warm container.

---

## 🏗️ Architecture Context

### Core Components
*   **`rp_handler.py`**: The serverless entry point. It initializes `vllm.AsyncLLMEngine`, handles Fernet decryption, and streams text deltas.
*   **`utils.py`**: The Model Downloader. **Crucial:** It uses `hf_transfer` (Rust) for 10Gbps+ downloads.
*   **`client.py`**: Reference client. It encrypts the prompt locally before sending.

### Data Flow
1.  **Client**: Encrypts JSON payload `{"prompt": "..."}` using Fernet Key -> Sends to RunPod.
2.  **Worker**: Decrypts payload -> Feeds to vLLM -> Streams tokens back.
3.  **RunPod**: Aggregates stream (or passes raw stream) -> Returns to Client.

---

## ⚙️ Configuration Variables (The "Knobs")

You must set these correctly for the Verification Protocol to pass.

| Variable | Description | Value to set |
| :--- | :--- | :--- |
| `MODELS` | The Model ID to load. | Example: `facebook/opt-125m` (for fast testing) or `meta-llama/Meta-Llama-3-8B-Instruct`. |
| `ENCRYPTION_KEY` | Symmetric Key. | Generate via: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `HF_HUB_ENABLE_HF_TRANSFER` | Enable Rust downloader. | **MUST BE `1`**. |
| `HF_TOKEN` | Hugging Face Token. | Required only if `MODELS` is a gated repo (e.g., Llama 3). |
| `GPU_MEMORY_UTILIZATION` | VRAM reservation. | Default `0.95`. Decrease to `0.90` if OOM errors occur during testing. |

---

## 🚀 Optimization & Performance Strategy

To achieve the "Performance" success criteria, you must leverage **RunPod Cached Models**.

### How to use RunPod Pre-Caching (Serverless)
*   **Do NOT** use `utils.py` to download large models if you can avoid it.
*   **DO** set the Model ID in the RunPod Endpoint Configuration (UI or API).
*   **Mechanism:** RunPod mounts cached models at `/runpod-volume/huggingface-cache/hub`.
*   **Agent Action:** Your code in `utils.py` is already compatible with this. It checks the cache directory before attempting a download.

**Reference URLs:**
*   **Cached Models**: [https://docs.runpod.io/serverless/workers/cached-models](https://docs.runpod.io/serverless/workers/cached-models)
*   **Fast Downloads**: [https://huggingface.co/docs/huggingface_hub/guides/download#faster-downloads](https://huggingface.co/docs/huggingface_hub/guides/download#faster-downloads)

---

## 🐛 Iterative Debugging Guide (The Loop)

If the **Verification Protocol** fails, use this decision tree to iterate:

1.  **Error: `Decryption failed`**
    *   *Cause:* The `ENCRYPTION_KEY` in `client.py` (or test script) does not match the env var in the container.
    *   *Fix:* Regenerate the key and ensure both sides use the exact same string.

2.  **Error: `Model not found` / Slow Cold Start**
    *   *Cause:* `hf_transfer` is not working or the model name is typoed.
    *   *Fix:* Verify `HF_HUB_ENABLE_HF_TRANSFER=1` is in Dockerfile. Verify `MODELS` matches a valid HF Repo ID.

3.  **Error: `OOM` / CUDA Error**
    *   *Cause:* vLLM is trying to reserve too much VRAM.
    *   *Fix:* Set env var `GPU_MEMORY_UTILIZATION=0.90`.

4.  **Error: `AttributeError: 'AsyncLLMEngine' object has no attribute 'generate'`**
    *   *Cause:* vLLM API mismatch.
    *   *Fix:* Ensure `Dockerfile` pulls `vllm/vllm-openai:v0.6.3` or newer.

---

## 🛠️ Tooling for Agents

### 1. Key Generator
Use this to generate the required secret for deployment:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 2. Local Docker Test
Simulate the RunPod environment locally before deploying:
```bash
docker build -t test-worker .
docker run --gpus all \
  -e MODELS="facebook/opt-125m" \
  -e ENCRYPTION_KEY="[YOUR_KEY]" \
  -e HF_HUB_ENABLE_HF_TRANSFER=1 \
  test-worker \
  python3 test_local.py --prompt "Testing 123"
```
