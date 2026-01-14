import serial
import time
import sys

# Configurazione Porta
SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 256000

def parse_radar_packet(packet):
    """
    Decodifica i byte grezzi del protocollo LD2410.
    Documentazione Offset:
    Byte 0-3: Header (F4 F3 F2 F1)
    Byte 4-5: Len
    Byte 8:   Target State (0=Nulla, 1=Moto, 2=Statico, 3=Entrambi)
    Byte 9-10: Moving Distance (cm)
    Byte 11:   Moving Energy (0-100)
    Byte 12-13: Static Distance (cm)
    Byte 14:    Static Energy (0-100)
    Byte 15-16: Detection Distance (cm)
    """
    try:
        # Interpretiamo i dati
        target_state = packet[8]
        
        # Distanze in Little Endian (Basso + Alto * 256)
        move_dist = packet[9] + (packet[10] << 8)
        move_energy = packet[11]
        
        static_dist = packet[12] + (packet[13] << 8)
        static_energy = packet[14]
        
        detection_dist = packet[15] + (packet[16] << 8)

        # Traduzione Stato in parole
        state_str = "❓"
        if target_state == 0: state_str = "❌ NESSUNO"
        elif target_state == 1: state_str = "🏃 IN MOVIMENTO"
        elif target_state == 2: state_str = "🧘 STATICO (Respiro)"
        elif target_state == 3: state_str = "🏃+🧘 MOVIMENTO E STATICO"

        # Creiamo una stringa formattata
        output = (
            f"STATO: {state_str:<25} | "
            f"DISTANZA: {detection_dist} cm\n"
            f"   └─ Dati Moto:    {move_dist} cm (Energy: {move_energy}%)\n"
            f"   └─ Dati Statici: {static_dist} cm (Energy: {static_energy}%)"
        )
        return output

    except IndexError:
        return "Errore: Pacchetto incompleto"

def main():
    print(f"--- RADAR DEEP DIVE ({SERIAL_PORT}) ---")
    print("Avvio scansione... (Premi Ctrl+C per uscire)\n")

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        buffer = b""
        
        while True:
            # Leggi tutto quello che c'è nel buffer
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                buffer += chunk

                # Cerchiamo l'header F4 F3 F2 F1
                while len(buffer) >= 23: # 23 byte è la lunghezza minima del pacchetto Base
                    # Trova l'inizio del pacchetto
                    idx = buffer.find(b'\xf4\xf3\xf2\xf1')
                    
                    if idx == -1:
                        # Nessun header trovato, teniamo solo gli ultimi byte per sicurezza
                        buffer = buffer[-4:]
                        break
                    
                    # Se l'header non è all'inizio, tagliamo la spazzatura prima
                    if idx > 0:
                        buffer = buffer[idx:]
                    
                    # Controlliamo se abbiamo abbastanza dati per un pacchetto intero (23 bytes)
                    if len(buffer) < 23:
                        break # Aspettiamo il prossimo giro del loop
                    
                    # Estraiamo il pacchetto
                    packet = buffer[:23]
                    
                    # --- VISUALIZZAZIONE ---
                    # Usiamo caratteri di escape per pulire lo schermo o stampare pulito
                    decoded_info = parse_radar_packet(packet)
                    
                    # Stampa e separatore
                    print("-" * 50)
                    print(decoded_info)
                    
                    # Rimuoviamo il pacchetto elaborato dal buffer
                    buffer = buffer[23:]
                    
                    # Rallentiamo leggermente per non illeggibilità (il radar manda 10Hz)
                    time.sleep(0.1) 
            else:
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStop.")
        if 'ser' in locals(): ser.close()
    except Exception as e:
        print(f"\nErrore Critico: {e}")

if __name__ == "__main__":
    main()