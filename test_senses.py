"""
Test script per verificare il funzionamento dei sensori.
"""

import os
import sys
import time
import queue
import logging

from senses import BuddySenses, SensorEvent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_basic():
    """Test base: verifica inizializzazione sensori."""
    print("\n" + "="*60)
    print("TEST 1: Inizializzazione Base")
    print("="*60)
    
    test_queue = queue.Queue()
    
    config = {
        'radar_enabled': os.getenv('RADAR_ENABLED', 'true').lower() == 'true',
        'radar_port': os.getenv('RADAR_PORT', '/dev/ttyAMA10'),
        'radar_baudrate': int(os.getenv('RADAR_BAUDRATE', '256000')),
        'radar_interval': float(os.getenv('RADAR_INTERVAL', '0.5')),
        'dht11_enabled': os.getenv('DHT11_ENABLED', 'true').lower() == 'true',
        'dht11_pin': int(os.getenv('DHT11_PIN', '18')),
        'dht11_interval': float(os.getenv('DHT11_INTERVAL', '30.0')),
    }
    
    senses = BuddySenses(test_queue, config)
    
    print(f"✓ BuddySenses creato")
    print(f"  - Radar: {'✅ Abilitato' if senses.radar.enabled else '⚠️  Disabilitato'}")
    print(f"  - DHT11: {'✅ Abilitato' if senses.dht11.enabled else '⚠️  Disabilitato'}")
    
    senses.stop()
    return True

def test_sensor_data():
    """Test lettura dati dai sensori."""
    print("\n" + "="*60)
    print("TEST 2: Lettura Dati Sensori (10 secondi)")
    print("="*60)
    
    test_queue = queue.Queue()
    
    config = {
        'radar_enabled': os.getenv('RADAR_ENABLED', 'true').lower() == 'true',
        'radar_port': os.getenv('RADAR_PORT', '/dev/ttyAMA10'),
        'radar_baudrate': int(os.getenv('RADAR_BAUDRATE', '256000')),
        'radar_interval': float(os.getenv('RADAR_INTERVAL', '0.5')),
        'dht11_enabled': os.getenv('DHT11_ENABLED', 'true').lower() == 'true',
        'dht11_pin': int(os.getenv('DHT11_PIN', '18')),
        'dht11_interval': float(os.getenv('DHT11_INTERVAL', '1')),
    }
    
    senses = BuddySenses(test_queue, config)
    senses.start()
    
    print("📡 In ascolto eventi sensori...\n")
    
    start_time = time.time()
    event_count = 0
    
    try:
        while time.time() - start_time < 10:
            if not test_queue.empty():
                event = test_queue.get()
                event_count += 1
                
                if isinstance(event, SensorEvent):
                    print(f"  [{event_count}] {event.sensor_type}: {event.value}")
                    if event.metadata:
                        print(f"      Metadata: {event.metadata}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n⏸️  Test interrotto")
    
    senses.stop()
    
    print(f"\n✓ Test completato: {event_count} eventi ricevuti in 10 secondi")
    return True

def test_continuous():
    """Test continuo: monitora i sensori finché non viene interrotto."""
    print("\n" + "="*60)
    print("TEST 3: Monitoraggio Continuo")
    print("="*60)
    print("Premi Ctrl+C per terminare\n")
    
    test_queue = queue.Queue()
    
    config = {
        'radar_enabled': os.getenv('RADAR_ENABLED', 'true').lower() == 'true',
        'radar_port': os.getenv('RADAR_PORT', '/dev/ttyAMA10'),
        'radar_baudrate': int(os.getenv('RADAR_BAUDRATE', '256000')),
        'radar_interval': float(os.getenv('RADAR_INTERVAL', '0.5')),
        'dht11_enabled': os.getenv('DHT11_ENABLED', 'true').lower() == 'true',
        'dht11_pin': int(os.getenv('DHT11_PIN', '18')),
        'dht11_interval': float(os.getenv('DHT11_INTERVAL', '1')),
    }
    
    senses = BuddySenses(test_queue, config)
    senses.start()
    
    print("📊 Dashboard Sensori:")
    print("-" * 60)
    
    last_temp = None
    last_humidity = None
    last_presence = None
    event_count = 0
    
    try:
        while True:
            if not test_queue.empty():
                event = test_queue.get()
                event_count += 1
                
                if isinstance(event, SensorEvent):
                    if event.sensor_type == "temperature":
                        last_temp = event.value
                    elif event.sensor_type == "humidity":
                        last_humidity = event.value
                    elif event.sensor_type == "radar_presence":
                        last_presence = event.value
                    
                    # Stampa dashboard
                    print(f"\r🌡️  Temp: {last_temp:.1f}°C  " if last_temp else "\r🌡️  Temp: ---  ", end="")
                    print(f"💧 Hum: {last_humidity:.1f}%  " if last_humidity else "💧 Hum: ---  ", end="")
                    print(f"📡 Presenza: {'✅' if last_presence else '❌'}  ", end="")
                    print(f"📨 Eventi: {event_count}  ", end="", flush=True)
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoraggio terminato")
    
    senses.stop()
    print(f"✓ Test completato: {event_count} eventi totali")
    return True

def main():
    print("\n🧪 BUDDY SENSES - Suite di Test")
    print("="*60)
    
    tests = [
        ("Inizializzazione", test_basic),
        ("Lettura Dati", test_sensor_data),
        ("Monitoraggio Continuo", test_continuous)
    ]
    
    if len(sys.argv) > 1:
        # Esegui test specifico
        test_num = int(sys.argv[1])
        if 1 <= test_num <= len(tests):
            name, test_func = tests[test_num - 1]
            print(f"\nEsecuzione test {test_num}: {name}")
            test_func()
        else:
            print(f"❌ Test {test_num} non valido. Scegli tra 1-{len(tests)}")
    else:
        # Menu interattivo
        while True:
            print("\nSeleziona test:")
            for i, (name, _) in enumerate(tests, 1):
                print(f"  {i}. {name}")
            print("  0. Esci")
            
            try:
                choice = input("\nScelta: ").strip()
                
                if choice == "0":
                    print("👋 Arrivederci!")
                    break
                
                test_num = int(choice)
                if 1 <= test_num <= len(tests):
                    name, test_func = tests[test_num - 1]
                    print(f"\n▶️  Esecuzione: {name}")
                    test_func()
                else:
                    print("❌ Scelta non valida")
                    
            except ValueError:
                print("❌ Inserisci un numero")
            except KeyboardInterrupt:
                print("\n\n👋 Arrivederci!")
                break

if __name__ == "__main__":
    main()
