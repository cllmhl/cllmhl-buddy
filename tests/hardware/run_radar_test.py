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
from dotenv import load_dotenv

# Setup
load_dotenv(".env")

# Lancia main.py con config radar test
os.environ["BUDDY_CONFIG"] = "config/radar_test.yaml"

print("=" * 70)
print("📡 BUDDY RADAR TEST MODE")
print("=" * 70)
print("\n🎯 Test sensore di presenza")
print("  • Input: RadarInput (/dev/ttyAMA0, 256000 baud)")
print("  • Output: ConsoleOutput (stampa eventi in tempo reale)")
print("\n💡 Cosa verificare:")
print("  ✓ Console mostra eventi di presenza quando rileva movimento")
print("  ✓ Avvicina la mano al radar per testare")
print("  ✓ Verifica che i dati siano corretti (distanza, target, ecc)")
print("\n🛑 Ctrl+C per terminare")
print("=" * 70 + "\n")

from main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test radar terminato")
