import os
import subprocess
from dotenv import load_dotenv

# Carichiamo la configurazione
load_dotenv("config.env")

# --- CONFIGURAZIONE DINAMICA ---
# Leggiamo quale voce vuole l'utente. Default: paola
# Valori attesi nel config.env: 'paola' oppure 'riccardo'
SELECTED_VOICE = os.getenv("TTS_VOICE", "paola").lower()

# Definiamo i percorsi e le impostazioni specifiche per ogni modello
# Struttura: "nome_chiave": ("nome_file_onnx", "velocità_ottimale")
VOICE_MAP = {
    "paola": {
        "file": "it_IT-paola-medium.onnx",
        "speed": "1.1", # Paola è naturale, non serve rallentarla
        "desc": "Paola (Medium Quality - 22kHz)"
    },
    "riccardo": {
        "file": "it_IT-riccardo-x_low.onnx",
        "speed": "1.1", # Riccardo corre, lo rallentiamo del 10%
        "desc": "Riccardo (Low Quality - 16kHz)"
    }
}

def get_paths():
    home = os.path.expanduser("~")
    base_path = os.path.join(home, "buddy_tools/piper")
    piper_bin = os.path.join(base_path, "piper/piper")
    
    # Recuperiamo i dati della voce scelta
    if SELECTED_VOICE not in VOICE_MAP:
        print(f"⚠️ Voce '{SELECTED_VOICE}' non riconosciuta. Uso fallback su 'paola'.")
        voice_data = VOICE_MAP["paola"]
    else:
        voice_data = VOICE_MAP[SELECTED_VOICE]
        
    model_path = os.path.join(base_path, voice_data["file"])
    
    return piper_bin, model_path, voice_data["speed"], voice_data["desc"]

def test_speak_dynamic():
    piper_bin, model_path, speed, desc = get_paths()
    
    print(f"--- TEST VOCE DINAMICO ---")
    print(f"Configurazione scelta: {SELECTED_VOICE.upper()}")
    print(f"Modello: {desc}")
    print(f"Speed Scale: {speed}")
    
    # Verifica esistenza file
    if not os.path.exists(piper_bin) or not os.path.exists(model_path):
        print("❌ ERRORE: File mancanti.")
        print(f"Binario: {piper_bin}")
        print(f"Modello: {model_path}")
        return

    text = f"Ciao, questa è una prova con la voce di {SELECTED_VOICE}. Sto usando la catena di conversione Sox."
    
    # 1. PIPER (Genera WAV)
    piper_cmd = [
        piper_bin,
        "--model", model_path,
        "--length_scale", speed, 
        "--output_file", "-" 
    ]

    # 2. SOX (Resampling a 48000Hz per Jabra)
    # Fondamentale per far funzionare sia Paola (22k) che Riccardo (16k)
    sox_cmd = [
        "sox",
        "-t", "wav", "-",   # Input pipe
        "-r", "48000",      # Output rate forzato
        "-t", "wav", "-"    # Output pipe
    ]

    # 3. APLAY (Hardware Output)
    aplay_cmd = [
        "aplay",
        "-D", "plughw:0,0"
    ]

    try:
        print("Generazione audio in corso...")
        
        # Catena: Piper -> SoX -> Aplay
        p_piper = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        p_sox = subprocess.Popen(sox_cmd, stdin=p_piper.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        p_aplay = subprocess.Popen(aplay_cmd, stdin=p_sox.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Chiudiamo le uscite intermedie per evitare deadlock
        p_piper.stdout.close()
        p_sox.stdout.close()
        
        # Esecuzione
        _, err_piper = p_piper.communicate(input=text.encode('utf-8'))
        p_aplay.wait()

        if p_piper.returncode != 0:
            print(f"❌ Errore Piper: {err_piper.decode()}")
        else:
            print("✅ Riproduzione terminata.")

    except Exception as e:
        print(f"❌ Errore critico: {e}")

if __name__ == "__main__":
    test_speak_dynamic()