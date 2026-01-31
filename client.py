import argparse
import requests
import json
import sys
from cryptography.fernet import Fernet

# CONFIGURATION
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_API_KEY"
URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# SECURITY - Must match Server
ENCRYPTION_KEY = "YOUR_GENERATED_KEY_HERE"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--prompt", required=True, help="Text prompt to send")
    parser.add_argument("--temp", type=float, default=0.7, help="Temperature")
    parser.add_argument("--max-tokens", type=int, default=500, help="Max tokens")
    args = parser.parse_args()

    # 1. PREPARE PAYLOAD
    payload = {
        "prompt": args.prompt,
        "sampling_params": {
            "temperature": args.temp,
            "max_tokens": args.max_tokens
        }
    }

    # 2. ENCRYPT PAYLOAD
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        json_bytes = json.dumps(payload).encode()
        encrypted_token = f.encrypt(json_bytes).decode()
    except Exception as e:
        print(f"Client Encryption Failed: {e}")
        return

    # 3. SEND REQUEST
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"Sending encrypted request for prompt: '{args.prompt}'...")
    print("-" * 40)
    
    try:
        # Note: 'runsync' usually waits for completion. For streaming, 
        # RunPod usually requires connecting to the /stream endpoint 
        # or handling the generator response carefully.
        # Below is a simplified handling for a Generator response in RunPod.
        
        response = requests.post(
            URL, 
            json={"input": {"encrypted_input": encrypted_token}}, 
            headers=headers, 
            stream=True # Enable streaming
        )

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    
                    # RunPod Stream format: usually "data: <json>"
                    # But depending on 'return_aggregate_stream', it might be raw chunks
                    # or RunPod JSON wrappers.
                    
                    # Simple heuristic cleanup for demo:
                    # In return_aggregate_stream=True mode, RunPod sends specific JSON structures.
                    # We print raw output for debugging or text if it looks like text.
                    
                    try:
                        # Try to parse RunPod stream wrapper
                        data = json.loads(decoded_line)
                        if 'output' in data:
                            # Print the actual token
                            sys.stdout.write(data['output'])
                            sys.stdout.flush()
                        elif 'status' in data:
                             pass # Status update
                    except:
                        # Fallback: just print the line
                        print(decoded_line)
            print("\n" + "-" * 40)
            print("Done.")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
