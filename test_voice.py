import os
import subprocess
import sys
import time

def check_paths():
    """Verifica che i file esistano dove ci aspettiamo."""
    home = os.path.expanduser("~")
    base_path = os.path.join(home, "buddy_tools/piper")
    
    piper_bin = os.path.join(base_path, "piper/piper")
    # NOTA: Qui usiamo il nome corretto x_low scaricato dallo script
    model_file = os.path.join(base_path, "it_IT-riccardo-x_low.onnx")
    
    print(f"--- VERIFICA PERCORSI ---")
    print(f"1. Binary Piper: {piper_bin}")
    if os.path.exists(piper_bin):
        print("   ✅ Trovato")
    else:
        print("   ❌ NON TROVATO - Verifica installazione")
        return None, None

    print(f"2. Modello ONNX: {model_file}")
    if os.path.exists(model_file):
        print("   ✅ Trovato")
    else:
        print("   ❌ NON TROVATO - Verifica download")
        return None, None
        
    return piper_bin, model_file

def speak(text, piper_bin, model_file):
    """Esegue la sintesi vocale."""
    print(f"\n--- TEST AUDIO ---")
    print(f"Generazione audio per: '{text}'")
    
    try:
        # Comando Piper
        piper_cmd = [
            piper_bin,
            "--model", model_file,
            "--output_raw"
        ]
        
        # Comando Aplay
        # Le voci x_low spesso sono a 16000Hz o 22050Hz.
        # Se la voce sembra uno scoiattolo o un demone, cambia il rate qui sotto.
        aplay_cmd = [
            "aplay",
            "-r", "16000", # Prova 22050, se suona male prova 16000
            "-f", "S16_LE",
            "-t", "raw",
            "-"
        ]

        # Creazione Pipe
        process_piper = subprocess.Popen(
            piper_cmd, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        process_aplay = subprocess.Popen(
            aplay_cmd, 
            stdin=process_piper.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Invio testo ed esecuzione
        stdout_data, stderr_data = process_piper.communicate(input=text.encode('utf-8'))
        process_aplay.wait()

        if process_piper.returncode != 0:
            print(f"❌ Errore Piper: {stderr_data.decode()}")
        else:
            print("✅ Riproduzione completata (se hai sentito l'audio).")

    except Exception as e:
        print(f"❌ Errore Python: {e}")

if __name__ == "__main__":
    bin_path, model_path = check_paths()
    
    if bin_path and model_path:
        speak("Ciao! Io sono Buddy. Se senti questa voce, il sistema locale funziona.", bin_path, model_path)
    else:
        print("\nImpossibile procedere al test audio a causa di file mancanti.")