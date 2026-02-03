import os
import runpod
import json
import time
import requests
import subprocess
from cryptography.fernet import Fernet
import utils

# CONFIG
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
MAX_MODEL_LEN = os.environ.get("MAX_MODEL_LEN", "4096")

# Global process variable for the C++ binary
llama_process = None

def start_llama_server():
    """Launches the C++ llama-server in the background."""
    global llama_process
    print("--- 🚀 Starting Native llama-server ---")
    
    model_path = utils.prepare_models(os.environ.get("MODEL_DIR", "/models"))
    
    # Standard C++ binary flags - Architecture Agnostic
    cmd = [
        "llama-server",
        "--model", model_path,
        "--ctx-size", MAX_MODEL_LEN,
        "--n-gpu-layers", "-1",
        "--host", "127.0.0.1",
        "--port", "8080",
        "--jinja",                        # Use the modern internal Jinja engine
        "--chat-template", "auto",        # Rely on GGUF metadata
        "--reasoning-format", "deepseek"  # Handle CoT fields natively
    ]
    
    llama_process = subprocess.Popen(cmd)
    
    # Wait for the server to be ready
    for i in range(30):
        try:
            res = requests.get("http://127.0.0.1:8080/health")
            if res.status_code == 200:
                print("--- ✅ Native Engine Ready ---")
                return
        except:
            pass
        time.sleep(1)
    raise Exception("llama-server failed to start")

def handler(job):
    # 1. Decrypt in RAM
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        encrypted_input = job.get('input', {}).get('encrypted_input')
        decrypted_json = f.decrypt(encrypted_input.encode()).decode()
        request_data = json.loads(decrypted_json)
    except Exception as e:
        yield {"error": f"Security layer error: {str(e)}"}
        return

    # 2. Forward to Local C++ Binary
    # We strip your custom encryption and pass the standard OAI payload to localhost
    try:
        url = "http://127.0.0.1:8080/v1/chat/completions"
        payload = {
            "messages": request_data.get("messages", []),
            "stream": True,
            "max_tokens": request_data.get("sampling_params", {}).get("max_tokens", 512),
            "temperature": request_data.get("sampling_params", {}).get("temperature", 0.7),
        }

        with requests.post(url, json=payload, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8').replace('data: ', '')
                    if decoded == '[DONE]': break
                    try:
                        chunk = json.loads(decoded)
                        # The C++ binary handles DeepSeek reasoning natively in the content
                        # or reasoning_content field depending on the version
                        delta = chunk['choices'][0]['delta']
                        token = delta.get('content') or delta.get('reasoning_content')
                        if token:
                            yield token
                    except:
                        continue
    except Exception as e:
        yield {"error": f"Engine communication error: {str(e)}"}

# Initial launch
if not llama_process:
    start_llama_server()

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
