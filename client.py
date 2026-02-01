import os
import sys
import json
import requests
from cryptography.fernet import Fernet

# CONFIG
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
API_KEY = os.environ.get("RUNPOD_API_KEY")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

def chat():
    history = [{"role": "system", "content": "You are a helpful assistant. If you use a thinking process, wrap it in <think> tags."}]
    f = Fernet(ENCRYPTION_KEY.encode())

    print(f"--- 🔒 Secure Session: {ENDPOINT_ID} ---")

    while True:
        user_input = input("\n👤 User: ")
        if user_input.lower() in ['exit', 'quit']: break
        
        history.append({"role": "user", "content": user_input})

        payload = {
            "messages": history,
            "sampling_params": {"max_tokens": 1536, "temperature": 0.6}
        }
        encrypted_blob = f.encrypt(json.dumps(payload).encode()).decode()

        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        response = requests.post(URL, json={"input": {"encrypted_input": encrypted_blob}}, headers=headers, stream=True)

        print("🤖 AI: ", end="", flush=True)
        assistant_response = ""

        for line in response.iter_lines():
            if not line: continue
            try:
                chunk = json.loads(line.decode('utf-8'))
                if "output" in chunk:
                    token = chunk["output"]
                    
                    # FIX: Handle if the token arrived as a list or string
                    if isinstance(token, list):
                        token = "".join(token)
                    
                    # Stop if it's an error
                    if isinstance(token, dict) and "error" in token:
                        print(f"\n❌ Error: {token['error']}")
                        break
                    
                    print(token, end="", flush=True)
                    assistant_response += token
            except:
                continue

        history.append({"role": "assistant", "content": assistant_response})
        print("")

if __name__ == "__main__":
    chat()
