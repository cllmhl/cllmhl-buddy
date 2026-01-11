import os
import subprocess
import sys

def check_paths():
    home = os.path.expanduser("~")
    base_path = os.path.join(home, "buddy_tools/piper")
    
    piper_bin = os.path.join(base_path, "piper/piper")
    # Usiamo il modello x_low che abbiamo scaricato
    model_file = os.path.join(base_path, "it_IT-riccardo-x_low.onnx")
    
    if os.path.exists(piper_bin) and os.path.exists(model_file):
        return piper_bin, model_file
    else:
        print("❌ File mancanti. Verifica setup.")
        return None, None

def speak(text, piper_bin, model_file):
    print(f"\n--- TEST AUDIO (Fix 16kHz) ---")
    try:
        # Comando Piper
        piper_cmd = [
            piper_bin,
            "--model", model_file,
            "--length_scale", "1.05", # Rallenta leggermente (1.0 è standard)
            "--output_raw"
        ]
        
        # Comando Aplay CORRETTO
        # Riccardo x_low lavora a 16000Hz, non 22050Hz!
        aplay_cmd = [
            "aplay",
            "-r", "16000", # <--- QUESTA È LA CHIAVE DEL PROBLEMA
            "-f", "S16_LE",
            "-t", "raw",
            "-"
        ]

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
        
        # Aggiungiamo un punto alla fine per aiutare la cadenza
        if not text.endswith("."):
            text += "."
            
        stdout_data, stderr_data = process_piper.communicate(input=text.encode('utf-8'))
        process_aplay.wait()

        if process_piper.returncode != 0:
            print(f"❌ Errore Piper: {stderr_data.decode()}")
        else:
            print("✅ Riproduzione terminata.")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    bin_path, model_path = check_paths()
    if bin_path:
        speak("Ciao, adesso la mia voce dovrebbe essere corretta e non robotica.", bin_path, model_path)