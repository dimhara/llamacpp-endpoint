#!/bin/bash
############ SSH ##########
# Setup ssh
setup_ssh() {
    if [[ $PUBLIC_KEY ]]; then
        echo "Setting up SSH..."
        mkdir -p ~/.ssh
        echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
        chmod 700 -R ~/.ssh

        if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
            ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -q -N ''
            echo "ED25519 key fingerprint:"
            ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
        fi

        service ssh start

        echo "SSH host keys:"
        for key in /etc/ssh/*.pub; do
            echo "Key: $key"
            ssh-keygen -lf $key
        done
    fi
}

setup_ssh

##########################

# Enable fast download
export HF_HUB_ENABLE_HF_TRANSFER=1
MODEL_DIR="/models"
mkdir -p $MODEL_DIR

echo "--- Preparing Model ---"
python3 utils.py "$MODEL_DIR"

# Use CHAT_FORMAT env var if provided, otherwise default to "chatml" 
# (ChatML works for Qwen and most modern distills)
FORMAT=${CHAT_FORMAT:-chatml}

if [ "$RUN_MODE" = "OPENAI_SERVER" ]; then
    echo "--- Launching Standard OpenAI API Server (Unencrypted) ---"
    # Changed --chat_format auto to $FORMAT
    python3 -m llama_cpp.server --model "$MODEL_DIR"/*.gguf --host 127.0.0.1 --port 8000 --n_gpu_layers -1 --chat_format "$FORMAT"
else
    echo "--- Launching Secure RunPod Worker, that works autodetects formats ---"
    python3 -u rp_handler.py
fi
