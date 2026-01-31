import os
from huggingface_hub import snapshot_download

# Defined in RunPod docs
RUNPOD_CACHE_DIR = "/runpod-volume/huggingface-cache/hub"

def get_model_map():
    """
    Parses the MODELS environment variable.
    Format: repo_id,repo_id
    Example: facebook/opt-125m,mistralai/Mistral-7B-Instruct-v0.2
    """
    models_env = os.environ.get("MODELS", "")
    if not models_env:
        return []
    
    # Split by comma
    return [entry.strip() for entry in models_env.split(",") if entry.strip()]

def resolve_model(repo_id, download_dir):
    """
    Downloads the full model snapshot.
    """
    print(f"[Download] Checking/Downloading {repo_id} to {download_dir}...")
    
    try:
        # snapshot_download handles caching automatically if HF_HOME is set via Docker/Env
        # It returns the local path to the folder
        path = snapshot_download(
            repo_id=repo_id,
            cache_dir=download_dir,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"] # Ignore non-vLLM formats
        )
        print(f"[Ready] Model available at: {path}")
        return path
    except Exception as e:
        print(f"Error downloading {repo_id}: {e}")
        raise e

def prepare_models(target_dir):
    """
    Iterates through env vars and ensures all models are ready.
    Returns the path of the *first* model defined (primary model).
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    model_list = get_model_map()
    first_model_path = None

    print(f"--- Resolving {len(model_list)} models from env var ---")

    for i, repo_id in enumerate(model_list):
        path = resolve_model(repo_id, target_dir)
        if i == 0:
            first_model_path = path
        
    return first_model_path

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "/models"
    prepare_models(target)
