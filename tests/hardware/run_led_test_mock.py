#!/usr/bin/env python3
"""
LED Mock Test - Verifica logica senza hardware
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

# Usa config mock (no GPIO)
os.environ["BUDDY_CONFIG"] = "tests/hardware/config/led_test_mock.yaml"

from main import main

if __name__ == "__main__":
    try:
        print("\n🧪 LED Mock Test - Testing logic without GPIO hardware")
        print("Watching for MockLEDOutput messages...\n")
        main()
        print("\n✅ Test completato con successo!")
    except KeyboardInterrupt:
        print("\n\n✅ Test interrotto")
    except Exception as e:
        print(f"\n❌ Test fallito: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
