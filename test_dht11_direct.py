#!/usr/bin/env python3
"""
Test diretto del DHT11 senza il framework BuddySenses.
Utile per diagnosticare problemi di connessione hardware.
"""

import os
import time
import logging

# Mock GPIO per testing su non-Raspberry
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'
    print("⚠️  Mock mode: non sei su Raspberry Pi")

try:
    import adafruit_dht
    import board
    DHT_AVAILABLE = True
except ImportError:
    print("❌ Libreria adafruit-dht non disponibile!")
    print("   Installa con: pip3 install adafruit-circuitpython-dht")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_dht11_direct():
    """Test diretto del DHT11."""
    print("\n" + "="*60)
    print("🌡️  Test Diagnostico DHT11")
    print("="*60)
    print()
    
    # Configurazione
    GPIO_PIN = int(os.getenv('DHT11_PIN', '18'))
    
    print(f"📍 GPIO Pin: {GPIO_PIN}")
    print(f"🔌 Connessioni previste:")
    print(f"   - VCC  → Pin 1 (3.3V)")
    print(f"   - DATA → Pin 12 (GPIO 18)")
    print(f"   - GND  → Pin 9 (Ground)")
    print()
    
    # Mappa GPIO a board pin
    pin_map = {
        4: board.D4,
        17: board.D17,
        18: board.D18,
        27: board.D27,
        22: board.D22,
        23: board.D23,
        24: board.D24,
    }
    
    if GPIO_PIN not in pin_map:
        print(f"❌ GPIO{GPIO_PIN} non supportato!")
        print(f"   Pin supportati: {list(pin_map.keys())}")
        return False
    
    board_pin = pin_map[GPIO_PIN]
    
    print(f"🔧 Inizializzazione sensore...")
    try:
        dht_device = adafruit_dht.DHT11(board_pin)
        print(f"✅ Sensore inizializzato\n")
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        return False
    
    print("📊 Tentativo lettura (10 tentativi)...")
    print("-" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i in range(10):
        print(f"\nTentativo {i+1}/10:")
        
        try:
            temp = dht_device.temperature
            humidity = dht_device.humidity
            
            if temp is not None and humidity is not None:
                print(f"  ✅ Temperatura: {temp:.1f}°C")
                print(f"  ✅ Umidità: {humidity:.1f}%")
                success_count += 1
            else:
                print(f"  ⚠️  Valori NULL (temp={temp}, humidity={humidity})")
                fail_count += 1
                
        except RuntimeError as e:
            print(f"  ⚠️  RuntimeError (normale per DHT11): {e}")
            fail_count += 1
        except Exception as e:
            print(f"  ❌ Errore: {e}")
            fail_count += 1
        
        # DHT11 richiede almeno 2 secondi tra letture
        time.sleep(2.5)
    
    print("\n" + "="*60)
    print(f"📈 Risultati:")
    print(f"   ✅ Letture riuscite: {success_count}/10")
    print(f"   ❌ Letture fallite: {fail_count}/10")
    
    if success_count == 0:
        print("\n⚠️  DIAGNOSI:")
        print("   Il sensore non restituisce dati validi.")
        print("   Possibili cause:")
        print("   1. Sensore non collegato o collegato male")
        print("   2. GPIO pin errato (verifica i cavi)")
        print("   3. Sensore difettoso")
        print("   4. Alimentazione insufficiente (prova con 5V invece di 3.3V)")
        print("   5. Necessita resistore pull-up 10kΩ sul pin DATA")
    elif success_count < 5:
        print("\n⚠️  DIAGNOSI:")
        print("   Il sensore funziona ma con molti errori.")
        print("   Questo è parzialmente normale per DHT11, ma può migliorare:")
        print("   1. Aggiungi resistore pull-up 10kΩ sul pin DATA")
        print("   2. Usa cavi più corti")
        print("   3. Verifica alimentazione stabile")
    else:
        print("\n✅ Il sensore funziona correttamente!")
    
    print("="*60)
    
    # Cleanup
    try:
        dht_device.exit()
    except:
        pass
    
    return success_count > 0

if __name__ == "__main__":
    try:
        success = test_dht11_direct()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrotto")
        exit(130)
