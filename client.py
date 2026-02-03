import os
import sys
import json
import requests
import argparse
from cryptography.fernet import Fernet

# CONFIG - From Environment
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
API_KEY = os.environ.get("RUNPOD_API_KEY")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

def get_piped_input():
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None

def flatten_token(token):
    """Helper to convert RunPod list output or dict errors into clean strings."""
    if isinstance(token, list):
        return "".join(token)
    if isinstance(token, dict) and "error" in token:
        return f"\n❌ Error: {token['error']}"
    return str(token)

def send_request(history, args, fernet):
    payload = {
        "messages": history,
        "sampling_params": {
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "top_p": args.top_p
        }
    }
    encrypted_blob = fernet.encrypt(json.dumps(payload).encode()).decode()
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    return requests.post(URL, json={"input": {"encrypted_input": encrypted_blob}}, headers=headers, stream=True)

def run_tool_mode(args, piped_data, fernet):
    user_content = args.prompt if args.prompt else ""
    if piped_data:
        user_content += f"\n\n[CONTEXT]:\n{piped_data}"
    
    history = [
        {"role": "system", "content": args.system},
        {"role": "user", "content": user_content}
    ]
    
    response = send_request(history, args, fernet)
    for line in response.iter_lines():
        if not line: continue
        try:
            chunk = json.loads(line.decode('utf-8'))
            if "output" in chunk:
                # Use the flatten helper to fix the list issue
                print(flatten_token(chunk["output"]), end="", flush=True)
        except: continue
    print("")

def run_interactive_mode(args, fernet):
    history = [{"role": "system", "content": args.system}]
    print(f"--- 🔒 Secure Session: {ENDPOINT_ID} ---")

    while True:
        try:
            user_input = input("\n👤 User: ")
            if user_input.lower() in ['exit', 'quit']: break
            
            history.append({"role": "user", "content": user_input})
            response = send_request(history, args, fernet)

            print("🤖 AI: ", end="", flush=True)
            assistant_response = ""

            for line in response.iter_lines():
                if not line: continue
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if "output" in chunk:
                        # Use the flatten helper to fix the list issue
                        token = flatten_token(chunk["output"])
                        print(token, end="", flush=True)
                        assistant_response += token
                except: continue

            history.append({"role": "assistant", "content": assistant_response})
            print("")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="llama.cpp RunPod Secure Client")
    parser.add_argument("prompt", nargs="?", help="Prompt for tool mode")
    parser.add_argument("--system", default="You are a helpful assistant. If you use a thinking process, wrap it in <think> tags.", help="System prompt")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max_tokens", type=int, default=1536)
    parser.add_argument("--top_p", type=float, default=0.95)
    
    args = parser.parse_args()
    
    if not ENCRYPTION_KEY:
        print("❌ Error: ENCRYPTION_KEY env var not set.")
        sys.exit(1)
        
    f = Fernet(ENCRYPTION_KEY.encode())
    piped_data = get_piped_input()

    if args.prompt or piped_data:
        run_tool_mode(args, piped_data, f)
    else:
        run_interactive_mode(args, f)
