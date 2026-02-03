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

# 1. Download Model
python3 utils.py "$MODEL_DIR"

# 2. Select Mode
if [ "$RUN_MODE" = "OPENAI_SERVER" ]; then
    echo "--- Launching Direct Native API (Localhost for SSH Tunneling) ---"
    llama-server \
        --model "$MODEL_DIR"/*.gguf \
        --host 127.0.0.1 \
        --port 8000 \
        --n-gpu-layers -1 \
        --jinja \
        --chat-template auto \
        --reasoning-format deepseek
else
    echo "--- Launching Secure Serverless Proxy ---"
    python3 -u rp_handler_fork.py
fi
