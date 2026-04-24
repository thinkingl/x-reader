#!/usr/bin/env python3
import os
import torch
from omnivoice import OmniVoice

def main():
    print("Downloading OmniVoice model...")
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cpu",
        dtype=torch.float32
    )
    print("OmniVoice model downloaded successfully!")

if __name__ == "__main__":
    main()
