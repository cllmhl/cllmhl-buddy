#!/usr/bin/env python3
"""
LED Hardware Test Runner - Interactive Mode
Test manuale LED GPIO con menu interattivo
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Lancia main.py con config led test
os.environ["BUDDY_CONFIG"] = "config/led_test.yaml"

from main import main

if __name__ == "__main__":
    try:
        print("\n🔵 LED Hardware Test - Interactive Mode")
        print("Usa il menu per testare i LED GPIO\n")
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test LED terminato")
