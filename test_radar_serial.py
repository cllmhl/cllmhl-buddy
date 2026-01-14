#!/usr/bin/env python3
"""
Test diretto della comunicazione seriale con il radar LD2410C.
Legge i dati raw e mostra i frame ricevuti.
"""

import os
import sys
import time
import serial

def parse_frame(data):
    """Cerca e parsifica frame LD2410C."""
    header = b'\xFD\xFC\xFB\xFA'
    tail = b'\x04\x03\x02\x01'
    
    frames = []
    idx = 0
    
    while idx < len(data):
        # Cerca header
        header_idx = data.find(header, idx)
        if header_idx == -1:
            break
        
        # Cerca tail dopo l'header
        tail_idx = data.find(tail, header_idx + 4)
        if tail_idx == -1:
            break
        
        # Estrai frame completo
        frame = data[header_idx:tail_idx + 4]
        frames.append(frame)
        idx = tail_idx + 4
    
    return frames

def decode_target_report(frame):
    """Decodifica un frame di report target."""
    if len(frame) < 23:
        return None
    
    # Byte 5-6: Target state
    target_state = frame[5]
    
    presence = target_state > 0
    movement = target_state in [1, 3]
    static = target_state in [2, 3]
    
    # Byte 7-8: Movement distance (little endian)
    mov_distance = frame[7] + (frame[8] << 8) if len(frame) > 8 else 0
    
    # Byte 9: Movement energy
    mov_energy = frame[9] if len(frame) > 9 else 0
    
    # Byte 10-11: Static distance
    static_distance = frame[10] + (frame[11] << 8) if len(frame) > 11 else 0
    
    # Byte 12: Static energy
    static_energy = frame[12] if len(frame) > 12 else 0
    
    return {
        'target_state': target_state,
        'presence': presence,
        'movement': movement,
        'static': static,
        'mov_distance': mov_distance,
        'mov_energy': mov_energy,
        'static_distance': static_distance,
        'static_energy': static_energy
    }

def test_radar_serial():
    """Test diretto della seriale."""
    print("\n" + "="*60)
    print("📡 Test Seriale Radar LD2410C")
    print("="*60)
    print()
    
    # Configurazione da env
    port = os.getenv('RADAR_PORT', '/dev/ttyAMA10')
    baudrate = int(os.getenv('RADAR_BAUDRATE', '256000'))
    
    print(f"🔧 Configurazione:")
    print(f"   Porta: {port}")
    print(f"   Baudrate: {baudrate}")
    print()
    
    # Apri connessione seriale
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        print(f"✅ Connesso a {port}")
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        return False
    
    print()
    print("🔬 Lettura dati (30 secondi)...")
    print("   Premi Ctrl+C per terminare")
    print()
    print("-" * 60)
    
    frame_count = 0
    valid_reports = 0
    start_time = time.time()
    buffer = b''
    
    try:
        while time.time() - start_time < 30:
            # Leggi dati disponibili
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer += data
                
                # Cerca frame completi
                frames = parse_frame(buffer)
                
                if frames:
                    # Pulisci buffer dai frame già processati
                    last_frame_end = buffer.rfind(b'\x04\x03\x02\x01')
                    if last_frame_end != -1:
                        buffer = buffer[last_frame_end + 4:]
                    
                    for frame in frames:
                        frame_count += 1
                        print(f"\n📦 Frame #{frame_count} ({len(frame)} bytes):")
                        print(f"   Raw: {frame.hex(' ')}")
                        
                        # Decodifica
                        report = decode_target_report(frame)
                        if report:
                            valid_reports += 1
                            print(f"   🎯 Target State: {report['target_state']}")
                            print(f"   👤 Presenza: {'✅ SI' if report['presence'] else '❌ NO'}")
                            print(f"   🏃 Movimento: {'✅ SI' if report['movement'] else '❌ NO'} (dist: {report['mov_distance']}cm, energy: {report['mov_energy']})")
                            print(f"   🧍 Statico: {'✅ SI' if report['static'] else '❌ NO'} (dist: {report['static_distance']}cm, energy: {report['static_energy']})")
            else:
                time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n⏸️  Lettura interrotta")
    
    ser.close()
    
    print("\n" + "="*60)
    print(f"📊 Statistiche:")
    print(f"   Frame totali: {frame_count}")
    print(f"   Report validi: {valid_reports}")
    print(f"   Tempo: {time.time() - start_time:.1f}s")
    
    if frame_count == 0:
        print("\n⚠️  DIAGNOSI:")
        print("   Nessun frame ricevuto!")
        print("   Possibili cause:")
        print("   1. Radar non alimentato (controlla VCC/GND)")
        print("   2. Cavi TX/RX invertiti")
        print("   3. Porta seriale errata")
        print("   4. Baudrate errato")
        print("   5. Radar difettoso")
    elif valid_reports == 0:
        print("\n⚠️  DIAGNOSI:")
        print("   Frame ricevuti ma non decodificabili.")
        print("   Il radar potrebbe essere in modalità configurazione.")
    else:
        print("\n✅ Radar funziona correttamente!")
        if valid_reports < frame_count * 0.8:
            print("   ⚠️  Alcuni frame non sono decodificabili (normale)")
    
    print("="*60)
    return frame_count > 0

if __name__ == "__main__":
    try:
        success = test_radar_serial()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrotto")
        sys.exit(130)
