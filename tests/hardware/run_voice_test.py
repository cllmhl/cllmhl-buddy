#!/usr/bin/env python3
"""
Voice Test Runner
Test hardware per input vocale (Jabra + Porcupine wake word).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Lancia main.py con config voice test
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/voice_test.yaml"

from main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test voice terminato")
