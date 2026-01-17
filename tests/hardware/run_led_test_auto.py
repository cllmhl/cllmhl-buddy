#!/usr/bin/env python3
"""
LED Hardware Test Runner - Automatic Sequence
Test automatico LED GPIO con sequenza predefinita
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Lancia main.py con config led test automatico
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/led_test_auto.yaml"

from main import main

if __name__ == "__main__":
    try:
        print("\n🔵 LED Hardware Test - Automatic Sequence")
        print("Eseguendo sequenza di test LED...\n")
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test LED terminato")
