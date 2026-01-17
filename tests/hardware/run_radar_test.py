#!/usr/bin/env python3
"""
Radar Test Runner
Test hardware per sensore di presenza (radar).
Stampa in console tutte le rilevazioni.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Lancia main.py con config radar test
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/radar_test.yaml"

from main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test radar terminato")
