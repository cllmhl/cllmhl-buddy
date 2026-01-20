#!/usr/bin/env python3
"""
Hardware Test Runner
Lancia il sistema con configurazione per test hardware.
Tutti gli adapter sono REALI - verifica hardware sul Raspberry Pi.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
from dotenv import load_dotenv

# Setup
load_dotenv(".env")

# Lancia main.py con config hardware test
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/hardware_test.yaml"

print("=" * 70)
print("🔧 BUDDY HARDWARE TEST MODE")
print("=" * 70)
print("\n📡 Input Adapters:")
print("  • WakewordInput + EarInput (wake word + STT cloud)")
print("  • RadarInput (/dev/ttyAMA0, 256000 baud)")
print("  • TemperatureInput (GPIO 18, DHT11)")
print("\n📤 Output Adapters:")
print("  • ConsoleOutput (stampa eventi in tempo reale)")
print("  • GPIOLEDOutput (LED 26 blu + 21 verde)")
print("  • JabraVoiceOutput (TTS cloud, voce Paola)")
print("  • MockDatabaseOutput (no persistenza)")
print("\n💡 Cosa verificare:")
print("  ✓ Console mostra dati sensori (temp, umidità, presenza)")
print("  ✓ LED BLU lampeggia quando parli")
print("  ✓ LED VERDE lampeggia quando Buddy risponde")
print("  ✓ Jabra riconosce italiano e risponde con voce chiara")
print("  ✓ Radar rileva movimento (avvicina la mano)")
print("  ✓ Temperatura/umidità realistiche (~20-25°C, 40-60%)")
print("\n🛑 Ctrl+C per terminare")
print("=" * 70 + "\n")

from main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Test hardware terminato")
