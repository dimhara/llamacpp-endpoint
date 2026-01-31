import os
import runpod
import json
import asyncio
from cryptography.fernet import Fernet
from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams, RequestOutput
from vllm.utils import random_uuid
import utils

# SECURITY KEY
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

# GLOBAL ENGINE INSTANCE
llm_engine = None

def init_engine():
    global llm_engine
    if llm_engine is not None:
        return

    print("--- 🚀 Initializing vLLM Engine ---")
    
    # 1. Download/Check Models
    model_dir = os.environ.get("MODEL_DIR", "/models")
    # This ensures the model is downloaded and gets the local path
    model_path = utils.prepare_models(model_dir)
    
    if not model_path:
        # Fallback if MODELS env is empty, try to find a folder in /models
        subdirs = [f.path for f in os.scandir(model_dir) if f.is_dir()]
        if subdirs:
            model_path = subdirs[0]
        else:
            raise RuntimeError("No model found in MODELS env var or /models directory")

    print(f"Loading model from: {model_path}")

    # 2. Configure vLLM
    engine_args = AsyncEngineArgs(
        model=model_path,
        gpu_memory_utilization=float(os.environ.get("GPU_MEMORY_UTILIZATION", "0.95")),
        max_model_len=int(os.environ.get("MAX_MODEL_LEN", "4096")),
        dtype="auto",
        enforce_eager=False,
        disable_log_stats=False
    )

    llm_engine = AsyncLLMEngine.from_engine_args(engine_args)
    print("--- ✅ vLLM Engine Ready ---")

async def handler(job):
    global llm_engine
    
    # 1. DECRYPT PAYLOAD
    try:
        if not ENCRYPTION_KEY:
            yield {"error": "Server ENCRYPTION_KEY not set."}
            return
        
        input_payload = job.get('input', {})
        encrypted_input = input_payload.get('encrypted_input')
        
        if not encrypted_input:
            yield {"error": "No encrypted_input found."}
            return

        f = Fernet(ENCRYPTION_KEY.encode())
        decrypted_json_str = f.decrypt(encrypted_input.encode()).decode()
        request_data = json.loads(decrypted_json_str)
        
    except Exception as e:
        print(f"Decryption failed: {e}")
        yield {"error": "Decryption failed or invalid key."}
        return

    # 2. PARSE REQUEST
    prompt = request_data.get("prompt")
    if not prompt:
        yield {"error": "No prompt provided in encrypted payload."}
        return

    # Sampling Parameters (with defaults)
    params_dict = request_data.get("sampling_params", {})
    try:
        sampling_params = SamplingParams(
            temperature=params_dict.get("temperature", 0.7),
            max_tokens=params_dict.get("max_tokens", 512),
            top_p=params_dict.get("top_p", 1.0),
            presence_penalty=params_dict.get("presence_penalty", 0.0),
            frequency_penalty=params_dict.get("frequency_penalty", 0.0),
            stop=params_dict.get("stop", [])
        )
    except Exception as e:
        yield {"error": f"Invalid sampling parameters: {str(e)}"}
        return

    request_id = random_uuid()
    
    # 3. GENERATE & STREAM
    try:
        # Initiate generation
        results_generator = llm_engine.generate(prompt, sampling_params, request_id)

        # Track previous text to send only deltas (streaming)
        previous_text = ""
        
        async for request_output in results_generator:
            # vLLM returns the full generated text every time
            full_text = request_output.outputs[0].text
            
            # Calculate delta
            delta = full_text[len(previous_text):]
            previous_text = full_text
            
            # Yield token/chunk
            # Note: We are streaming CLEAR TEXT back. 
            # Encrypting individual tokens is inefficient and usually unnecessary 
            # if the transport (HTTPS) is secure, but the prompt (input) remains protected.
            yield delta

    except Exception as e:
        print(f"Generation Error: {e}")
        yield {"error": str(e)}

# Initialize Engine immediately on import/start
loop = asyncio.get_event_loop()
loop.run_until_complete(init_engine())

# Start RunPod
runpod.serverless.start({
    "handler": handler,
    "return_aggregate_stream": True # This is crucial for streaming
})
