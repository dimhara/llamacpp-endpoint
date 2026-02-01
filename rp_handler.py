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
    
    # DeepSeek R1 Distill-Qwen models use the Qwen/ChatML logic.
    # If CHAT_FORMAT is not provided, we default to 'qwen'.
    requested_format = os.environ.get("CHAT_FORMAT", "qwen") 

    try:
        model_path = utils.prepare_models(model_dir)
        max_ctx = int(os.environ.get("MAX_MODEL_LEN", 4096))

        llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1, 
            n_ctx=max_ctx,
            flash_attn=ENABLE_FLASH_ATTN,
            chat_format=requested_format,
            verbose=False
        )

        ctx_val = llm.n_ctx() if callable(llm.n_ctx) else llm.n_ctx
        print(f"--- 🛠️  Model Metadata & Config ---")
        print(f"   - Model File:     {os.path.basename(model_path)}")
        print(f"   - Context Window:  {ctx_val} tokens")
        print(f"   - Chat Format:     {requested_format}")
        print(f"   - Flash Attn:      {'ENABLED' if ENABLE_FLASH_ATTN else 'DISABLED'}")
        print(f"--- ✅ Engine Ready ---")

    except Exception as e:
        print(f"--- ❌ Engine Initialization Failed ---")
        traceback.print_exc()
        raise e

def handler(job):
    # 1. DECRYPT
    try:
        if not ENCRYPTION_KEY:
            yield {"error": "Server ENCRYPTION_KEY missing."}
            return
            
        f = Fernet(ENCRYPTION_KEY.encode())
        input_payload = job.get('input', {})
        encrypted_input = input_payload.get('encrypted_input')
        
        decrypted_json = f.decrypt(encrypted_input.encode()).decode()
        request_data = json.loads(decrypted_json)
    except Exception as e:
        yield {"error": f"Decryption/Parsing failed: {str(e)}"}
        return

    # 2. PREPARE
    messages = request_data.get("messages", [])
    if not messages and "prompt" in request_data:
        messages = [{"role": "user", "content": request_data["prompt"]}]

    params = request_data.get("sampling_params", {})

    # 3. GENERATE & STREAM
    try:
        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=params.get("max_tokens", 1024),
            temperature=params.get("temperature", 0.6),
            stream=True
        )

        print("--- ⚡ Generation Started ---")
        token_count = 0
        
        for chunk in stream:
            if 'choices' in chunk and len(chunk['choices']) > 0:
                delta = chunk['choices'][0]['delta']
                
                # FIX: Check both 'content' (final answer) and 'reasoning_content' (thinking)
                # DeepSeek-R1 Distills generate reasoning first.
                token = delta.get('content') or delta.get('reasoning_content')
                
                if token:
                    token_count += 1
                    # Optional: Print heartbeat every 50 tokens to keep logs clean
                    if token_count % 50 == 0:
                        print(f"--- 💓 Generated {token_count} tokens ---")
                    yield token
        
        print(f"--- ✨ Generation Finished (Total tokens: {token_count}) ---")
        
        if token_count == 0:
            yield " " # Prevent empty return if model yielded nothing

    except Exception as e:
        print(f"Inference error: {str(e)}")
        yield {"error": f"Inference failed: {str(e)}"}

# Trigger eager load
init_engine()

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
