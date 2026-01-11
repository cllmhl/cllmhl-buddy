import subprocess
import os

# --- CONFIGURAZIONE ---
home = os.path.expanduser("~")
piper_bin = os.path.join(home, "buddy_tools/piper/piper/piper")
model_onnx = os.path.join(home, "buddy_tools/piper/it_IT-riccardo-x_low.onnx")

def test_speak_wav():
    print(f"--- TEST AUDIO (WAV MODE) ---")
    
    # Verifica esistenza file
    if not os.path.exists(piper_bin) or not os.path.exists(model_onnx):
        print("❌ ERRORE: File di Piper mancanti. Controlla il percorso.")
        print(f"Binario: {piper_bin}")
        print(f"Modello: {model_onnx}")
        return

    text = "Questa è una prova con formato Wave. Dovrebbe sentirsi bene."
    
    # 1. Comando Piper
    # --output_file -  : Il trattino '-' dice a Piper di buttare il WAV nello stdout invece che su disco
    cmd_piper = [
        piper_bin,
        "--model", model_onnx,
        "--output_file", "-" 
    ]

    # 2. Comando Aplay
    # Non mettiamo nessun flag (-r, -c, -f). 
    # Aplay leggerà l'header del WAV e si configurerà da solo.
    cmd_aplay = ["aplay"]

    try:
        print("Generazione e riproduzione in corso...")
        
        # Creiamo la catena
        p1 = subprocess.Popen(
            cmd_piper, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        p2 = subprocess.Popen(
            cmd_aplay, 
            stdin=p1.stdout
        )
        
        # Inviamo il testo
        _, err = p1.communicate(input=text.encode('utf-8'))
        p2.wait() # Aspettiamo che aplay finisca

        if p1.returncode != 0:
            print(f"❌ Errore Piper: {err.decode()}")
        else:
            print("✅ Riproduzione terminata.")

    except Exception as e:
        print(f"❌ Errore critico: {e}")

if __name__ == "__main__":
    test_speak_wav()