#!/usr/bin/env python3
"""
Temperature Test Runner
Test hardware per sensore temperatura/umidità (DHT11).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Lancia main.py con config temperature test
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/temperature_test.yaml"

from main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test temperatura terminato")
