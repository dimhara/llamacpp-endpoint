import os
import asyncio
import json
import argparse
from cryptography.fernet import Fernet

# MOCK ENV
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
# Ensure MODELS is set or models exist in /models
os.environ["MODELS"] = "facebook/opt-125m" 
os.environ["GPU_MEMORY_UTILIZATION"] = "0.90"

try:
    from rp_handler import handler, init_engine
except ImportError:
    print("Error: Could not find rp_handler.py")
    exit(1)

async def run_test(prompt):
    # 1. Initialize (Cold Start)
    await init_engine()

    # 2. Encrypt
    f = Fernet(os.environ["ENCRYPTION_KEY"].encode())
    payload = {"prompt": prompt, "sampling_params": {"max_tokens": 50}}
    encrypted = f.encrypt(json.dumps(payload).encode()).decode()

    # 3. Create Job
    job = {"input": {"encrypted_input": encrypted}}

    print(f"\n--- Streaming Response for: '{prompt}' ---\n")
    
    # 4. Consume Generator
    async for chunk in handler(job):
        if isinstance(chunk, dict) and "error" in chunk:
            print(f"\nERROR: {chunk['error']}")
        else:
            print(chunk, end="", flush=True)
    
    print("\n\n--- Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="To be or not to be,")
    args = parser.parse_args()
    
    asyncio.run(run_test(args.prompt))
