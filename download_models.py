#!/usr/bin/env python3
import os
import sys

# 使用国内镜像加速下载
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

def download_model(repo_id, local_dir):
    print(f"Downloading {repo_id} -> {local_dir}")
    print("This may take a while. Progress will be shown below.")
    print("-" * 60)
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"\nDone: {repo_id}")

if __name__ == "__main__":
    os.makedirs(MODEL_DIR, exist_ok=True)

    # OmniVoice TTS model (~4GB)
    download_model("k2-fsa/OmniVoice", os.path.join(MODEL_DIR, "OmniVoice"))

    # Whisper ASR model
    download_model("openai/whisper-large-v3-turbo", os.path.join(MODEL_DIR, "whisper-large-v3-turbo"))

    print("\nAll models downloaded!")
