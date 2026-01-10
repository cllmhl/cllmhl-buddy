import sys
from gpiozero import LED
from time import sleep

def test_led(pin_number):
    try:
        # Inizializziamo il LED con il numero passato
        led = LED(pin_number)
        print(f"--- Test LED sul pin GPIO {pin_number} avviato ---")
        print("Premi Ctrl+C per fermare il test.")
        
        while True:
            led.on()
            print(f"GPIO {pin_number}: ACCESO")
            sleep(0.5)
            led.off()
            print(f"GPIO {pin_number}: SPENTO")
            sleep(0.5)
            
    except ValueError:
        print(f"❌ Errore: '{pin_number}' non è un numero di pin GPIO valido.")
    except KeyboardInterrupt:
        print("\nTest interrotto dall'utente.")
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")

if __name__ == "__main__":
    # Controlliamo se l'utente ha passato l'argomento
    if len(sys.argv) > 1:
        pin = sys.argv[1]
        test_led(pin)
    else:
        print("Uso: python3 test_led_arg.py <numero_gpio>")
        print("Esempio: python3 test_led_arg.py 17")