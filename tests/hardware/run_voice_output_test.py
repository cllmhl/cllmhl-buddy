#!/usr/bin/env python3
"""
Voice Output Hardware Test Runner
Test TTS e speaker Jabra con menu interattivo
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Lancia main.py con config voice output test
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/voice_output_test.yaml"

from main import main

if __name__ == "__main__":
    try:
        print("\n🔊 Voice Output Hardware Test - Interactive Mode")
        print("Usa il menu per testare TTS e speaker\n")
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test Voice Output terminato")
