#!/bin/bash

# Enable fast download transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
MODEL_DIR="/models"

mkdir -p $MODEL_DIR

echo "---------------------------------------------------"
echo "Initializing Models from Environment Variable..."
echo "MODELS: $MODELS"
echo "---------------------------------------------------"

# Use the shared utils script to download
python3 /utils.py "$MODEL_DIR"

echo "---------------------------------------------------"
echo "Models ready in $MODEL_DIR"
echo "---------------------------------------------------"
echo "You can now start the handler manually for testing:"
echo "python3 rp_handler.py"
echo "---------------------------------------------------"

# Keep container running
sleep infinity

