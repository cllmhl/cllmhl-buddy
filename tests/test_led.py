#!/usr/bin/env python3
import time
import sys
import argparse
try:
    from gpiozero import LED
except ImportError:
    print("Errore: la libreria 'gpiozero' non è installata.")
    print("Puoi installarla con: pip install gpiozero")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Testa un LED collegato a un pin GPIO in isolamento.")
    parser.add_argument("--pin", type=int, default=20, help="Il numero del pin GPIO da testare (default: 20)")
    args = parser.parse_args()

    pin = args.pin
    print(f"Inizializzazione del test per il LED sul pin GPIO {pin}...")

    try:
        led = LED(pin)
    except Exception as e:
        print(f"Errore durante l'inizializzazione del pin {pin}: {e}")
        sys.exit(1)

    try:
        print(f"\n[Test 1/3] Accensione del LED sul pin {pin}...")
        led.on()
        time.sleep(3)

        print(f"[Test 2/3] Spegnimento del LED sul pin {pin}...")
        led.off()
        time.sleep(2)

        print(f"[Test 3/3] Lampeggio (Blink) del LED sul pin {pin} per 5 secondi...")
        led.blink(on_time=0.5, off_time=0.5)
        time.sleep(5)
        led.off()

        print("\nTest completato con successo (lato software).")
        print("Se non hai visto il LED accendersi o lampeggiare, verifica:")
        print("1. Che il LED sia collegato al pin corretto (GPIO " + str(pin) + ", non il numero fisico del pin).")
        print("2. Che la polarità del LED sia corretta (gamba lunga al pin GPIO, gamba corta a GND, con una resistenza in mezzo).")
        print("3. Che i cavi e i collegamenti siano saldi.")

    except KeyboardInterrupt:
        print("\nTest interrotto dall'utente.")
    finally:
        led.close()
        print("Risorse GPIO rilasciate.")

if __name__ == "__main__":
    main()
