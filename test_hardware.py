import serial
import time
import board
import adafruit_dht

print("--- DIAGNOSTICA HARDWARE BUDDY ---")

# 1. TEST RADAR (LD2410C)
print("\n📡 Test Radar (UART su /dev/ttyAMA0)...")
try:
    # Usiamo ttyAMA0 che è quella sui pin 8 e 10
    ser = serial.Serial('/dev/ttyAMA0', 256000, timeout=1)
    print("   ✅ Porta seriale aperta correttamenta.")
    
    print("   In ascolto per 3 secondi...")
    start_time = time.time()
    data_found = False
    
    while time.time() - start_time < 3:
        if ser.in_waiting > 0:
            raw_data = ser.read(ser.in_waiting)
            # Cerchiamo l'header f4 f3 f2 f1
            if b'\xf4\xf3\xf2\xf1' in raw_data:
                print(f"   🔥 DATI RICEVUTI! Header trovato. (Letto {len(raw_data)} bytes)")
                data_found = True
                break
        time.sleep(0.1)
        
    if not data_found:
        print("   ⚠️ Porta aperta ma nessun dato dal Radar. Controlla TX/RX incrociati!")
        
    ser.close()
    
except Exception as e:
    print(f"   ❌ ERRORE RADAR: {e}")
    print("      Suggerimento: Hai riavviato dopo raspi-config?")


# 2. TEST DHT11 (Aggiornato a GPIO 18)
print("\n🌡️ Test Ambiente (DHT11 su GPIO 18)...")
try:
    # Nota: board.D18 corrisponde al GPIO 18 (Pin 12)
    dht = adafruit_dht.DHT11(board.D18)
    
    # Facciamo fino a 3 tentativi (il DHT è lento)
    for i in range(3):
        try:
            t = dht.temperature
            h = dht.humidity
            if t is not None and h is not None:
                print(f"   ✅ SUCCESSO: Temp={t}°C  Umidità={h}%")
                break
        except RuntimeError:
            # Ignora errori di checksum temporanei
            time.sleep(1.0)
            continue
    else:
        print("   ⚠️ Nessuna lettura valida dopo 3 tentativi.")

    dht.exit()
    
except Exception as e:
    print(f"   ❌ ERRORE DHT: {e}")

print("\n--- FINE TEST ---")