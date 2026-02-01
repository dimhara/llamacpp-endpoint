import os
import runpod
import json
import traceback
from cryptography.fernet import Fernet
from llama_cpp import Llama
import utils

# CONFIG
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
ENABLE_FLASH_ATTN = os.environ.get("ENABLE_FLASH_ATTN", "false").lower() == "true"

llm = None

def init_engine():
    global llm
    if llm is not None: return

    print("--- 🚀 Initializing llama.cpp Secure Worker ---")
    
    model_dir = os.environ.get("MODEL_DIR", "/models")
    requested_format = os.environ.get("CHAT_FORMAT") # Can be None for auto-detect

    try:
        # 1. Download/Verify Model
        model_path = utils.prepare_models(model_dir)

        # 2. Set Context Size
        max_ctx = int(os.environ.get("MAX_MODEL_LEN", 4096))

        # 3. Load Engine
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1, 
            n_ctx=max_ctx,
            flash_attn=ENABLE_FLASH_ATTN,
            chat_format=requested_format,
            verbose=False
        )

        # 4. Extract and Log Metadata (Non-Sensitive)
        # We query the resolved chat_format to see what the engine actually picked
        resolved_format = llm.chat_format
        
        print(f"--- 🛠️  Model Metadata & Config ---")
        print(f"   - Model File:    {os.path.basename(model_path)}")
        print(f"   - Context Window: {llm.n_ctx} tokens")
        print(f"   - Chat Format:    {resolved_format}")
        print(f"   - Flash Attn:     {'ENABLED' if ENABLE_FLASH_ATTN else 'DISABLED'}")
        print(f"   - GPU Offload:    ALL LAYERS (-1)")
        print(f"--- ✅ Engine Ready ---")

    except Exception as e:
        print(f"--- ❌ Engine Initialization Failed ---")
        traceback.print_exc()
        raise e

def handler(job):
    # 1. DECRYPT & PARSE
    try:
        if not ENCRYPTION_KEY:
            yield {"error": "Server ENCRYPTION_KEY missing."}
            return
            
        f = Fernet(ENCRYPTION_KEY.encode())
        input_payload = job.get('input', {})
        encrypted_input = input_payload.get('encrypted_input')
        
        if not encrypted_input:
             yield {"error": "Missing encrypted_input payload."}
             return

        decrypted_json = f.decrypt(encrypted_input.encode()).decode()
        request_data = json.loads(decrypted_json)
    except Exception as e:
        yield {"error": f"Decryption/Parsing failed: {str(e)}"}
        return

    # 2. PREPARE REQUEST
    messages = request_data.get("messages", [])
    if not messages and "prompt" in request_data:
        messages = [{"role": "user", "content": request_data["prompt"]}]

    params = request_data.get("sampling_params", {})

    # 3. GENERATE & STREAM
    try:
        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature", 0.7),
            top_p=params.get("top_p", 0.95),
            stream=True
        )

        for chunk in stream:
            if 'choices' in chunk and len(chunk['choices']) > 0:
                delta = chunk['choices'][0]['delta']
                if 'content' in delta:
                    yield delta['content']

    except Exception as e:
        yield {"error": f"Inference failed: {str(e)}"}

# Trigger eager load
try:
    init_engine()
except:
    print("--- 💀 FATAL: Initialization failed. Exiting. ---")
    exit(1)

if __name__ == "__main__":
    print("--- 🟢 Starting RunPod Serverless Loop ---")
    runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
    
