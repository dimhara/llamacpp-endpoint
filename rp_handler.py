import os
import runpod
import json
import traceback
from cryptography.fernet import Fernet
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Jinja2ChatFormatter, ChatFormatterResponse
import utils

# CONFIG
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
ENABLE_FLASH_ATTN = os.environ.get("ENABLE_FLASH_ATTN", "false").lower() == "true"

# Globals
llm = None
chat_formatter = None
eos_token_str = None

def init_engine():
    global llm, chat_formatter, eos_token_str
    if llm is not None: return

    print("--- 🚀 Initializing llama.cpp Secure Worker ---")
    model_dir = os.environ.get("MODEL_DIR", "/models")
    
    try:
        model_path = utils.prepare_models(model_dir)
        max_ctx = int(os.environ.get("MAX_MODEL_LEN", 4096))
        
        # 1. Initialize Engine
        # We leave chat_format=None to avoid KeyError and handle templating in Python
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1, 
            n_ctx=max_ctx,
            flash_attn=ENABLE_FLASH_ATTN,
            verbose=False 
        )

        # 2. Dynamic Metadata Extraction
        # Extract BOS/EOS IDs and convert to literal strings via the tokenizer
        # special=True is the generic way to tell llama.cpp to emit control strings
        eos_id = llm.token_eos()
        bos_id = llm.token_bos()
        
        eos_token_str = llm.detokenize([eos_id], special=True).decode("utf-8", errors="ignore")
        bos_token_str = llm.detokenize([bos_id], special=True).decode("utf-8", errors="ignore")
        
        raw_template = llm.metadata.get("tokenizer.chat_template")
        if isinstance(raw_template, bytes):
            raw_template = raw_template.decode("utf-8")

        if raw_template:
            print(f"--- ✅ GGUF Metadata Template Detected ---")
            # ARCHITECTURAL NOTE: We pass an empty string for bos_token to the Formatter.
            # llama-cpp-python adds the BOS ID automatically at the batch level.
            # Including it in the prompt string triggers "Duplicate BOS" warnings.
            chat_formatter = Jinja2ChatFormatter(
                template=raw_template,
                eos_token=eos_token_str,
                bos_token="" 
            )
        else:
            print("--- ⚠️ No metadata template found. Falling back to basic content. ---")

    except Exception as e:
        print(f"--- ❌ Engine Initialization Failed ---")
        traceback.print_exc()
        raise e

def handler(job):
    # --- Secure Decryption ---
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        input_payload = job.get('input', {})
        encrypted_input = input_payload.get('encrypted_input')
        
        if not encrypted_input:
            yield {"error": "Missing encrypted_input"}
            return

        decrypted_json = f.decrypt(encrypted_input.encode()).decode()
        request_data = json.loads(decrypted_json)
    except Exception as e:
        yield {"error": f"Security layer error: {str(e)}"}
        return

    messages = request_data.get("messages", [])
    params = request_data.get("sampling_params", {})

    try:
        # --- Generic Prompt Rendering ---
        if chat_formatter:
            # result.prompt will contain the formatted turn-based string
            # add_generation_prompt=True ensures the final Assistant header is added
            result: ChatFormatterResponse = chat_formatter(
                messages=messages, 
                add_generation_prompt=True
            )
            prompt = result.prompt
        else:
            # Fallback for models without GGUF chat_template metadata
            prompt = messages[-1]['content'] if messages else ""

        # --- Generation ---
        # Using raw create_completion ensures the library doesn't try to 
        # re-apply any secondary internal templates.
        stream = llm.create_completion(
            prompt=prompt,
            max_tokens=params.get("max_tokens", 1024),
            temperature=params.get("temperature", 0.6),
            stream=True,
            stop=[eos_token_str] if eos_token_str else []
        )

        token_count = 0
        for chunk in stream:
            # Raw completion returns delta in the 'text' field
            token = chunk['choices'][0]['text']
            if token:
                token_count += 1
                yield token
        
        if token_count == 0:
             yield {"error": "Model produced no output. Possible template mismatch."}

    except Exception as e:
        yield {"error": f"Inference failed: {str(e)}"}

# Pre-initialize engine so cold starts are handled before RunPod accepts jobs
init_engine()

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler, "return_aggregate_stream": True})
