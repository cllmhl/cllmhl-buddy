import serial
import time

# --- CONFIGURAZIONE ---
# Inserisci qui la porta che hai trovato al punto 2
PORTA_USB = '/dev/ttyACM0' 
BAUD_RATE = 9600 # Deve essere identico a quello scritto su Arduino (Serial.begin)

def leggi_luminosita():
    try:
        # Apriamo il canale di comunicazione
        print(f"🔌 Tentativo di connessione a {PORTA_USB}...")
        ser = serial.Serial(PORTA_USB, BAUD_RATE, timeout=1)
        
        # IMPORTANTE: Quando Python apre la seriale, l'Arduino si riavvia.
        # Dobbiamo dargli un paio di secondi per "svegliarsi" prima di leggere.
        time.sleep(2) 
        print("✅ Connesso! In ascolto del sensore...")

        while True:
            # Se c'è un messaggio in coda dalla USB...
            if ser.in_waiting > 0:
                # Leggiamo la riga, la decodifichiamo e togliamo spazi vuoti/a capo
                linea_dati = ser.readline().decode('utf-8').rstrip()
                
                # Assicuriamoci che l'Arduino abbia mandato un numero valido
                if linea_dati.isdigit():
                    luminosita = int(linea_dati)
                    
                    print(f"Luce percepita: {luminosita} / 1023")
                    
                    # --- QUI METTI LA LOGICA DI BUDDY ---
                    # Esempio:
                    # if luminosita < 300:
                    #     print("È buio! Dico a Buddy di accendere le luci.")

    except serial.SerialException as e:
        print(f"❌ Errore USB: {e}")
        print("L'Arduino è collegato? La porta è quella giusta?")
    except KeyboardInterrupt:
        print("\nChiusura script...")
    finally:
        # Chiudiamo sempre la porta pulitamente quando fermiamo lo script
        if 'ser' in locals() and ser.is_open:
            ser.close()

# Avviamo il test
if __name__ == "__main__":
    leggi_luminosita()