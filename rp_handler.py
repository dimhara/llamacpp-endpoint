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
    
    # Passing None allows the library to use the embedded GGUF Jinja template.
    # This is the most accurate for DeepSeek-R1 Distills.
    requested_format = os.environ.get("CHAT_FORMAT") 

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
        print(f"--- ✅ Engine Ready (Format: {llm.chat_format}) ---")
    except Exception as e:
        print(f"--- ❌ Engine Initialization Failed: {e}")
        raise e

def handler(job):
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
        yield {"error": f"Decryption failed: {str(e)}"}
        return

    messages = request_data.get("messages", [])
    params = request_data.get("sampling_params", {})

    try:
        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=params.get("max_tokens", 1024),
            temperature=params.get("temperature", 0.6),
            stream=True
        )

        for chunk in stream:
            if 'choices' in chunk and len(chunk['choices']) > 0:
                delta = chunk['choices'][0]['delta']
                
                # Check for content or reasoning
                token = delta.get('content') or delta.get('reasoning_content')
                
                if token:
                    # Ensure we only yield strings, never lists
                    if isinstance(token, list):
                        yield "".join(token)
                    else:
                        yield str(token)

    except Exception as e:
        yield {"error": f"Inference failed: {str(e)}"}

init_engine()

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
