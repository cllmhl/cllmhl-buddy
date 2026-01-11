import subprocess
import os
import json

def get_config():
    home = os.path.expanduser("~")
    base_dir = os.path.join(home, "buddy_tools/piper")
    piper_bin = os.path.join(base_dir, "piper/piper")
    model_onnx = os.path.join(base_dir, "it_IT-riccardo-x_low.onnx")
    model_json = model_onnx + ".json"

    # Verifiche esistenza
    if not os.path.exists(model_json):
        print(f"❌ File config non trovato: {model_json}")
        return None, None, None
        
    # Leggiamo la frequenza corretta dal file JSON
    try:
        with open(model_json, 'r') as f:
            conf = json.load(f)
            # Solitamente è in audio -> sample_rate, o espeak -> sample_rate
            # Cerchiamo in modo sicuro
            if 'audio' in conf and 'sample_rate' in conf['audio']:
                rate = conf['audio']['sample_rate']
            elif 'espeak' in conf and 'sample_rate' in conf['espeak']:
                rate = conf['espeak']['sample_rate']
            else:
                rate = 16000 # Fallback
                print("⚠️ Sample rate non trovato nel JSON, uso default 16000")
    except Exception as e:
        print(f"⚠️ Errore lettura JSON: {e}")
        rate = 16000

    return piper_bin, model_onnx, str(rate)

def test_speak():
    piper, model, rate = get_config()
    
    if not piper:
        return

    print(f"--- DIAGNOSTICA AUDIO ---")
    print(f"Modello: {os.path.basename(model)}")
    print(f"Frequenza Rilevata: {rate} Hz")
    print(f"Forzatura Mono: ATTIVA (-c 1)")
    
    text = "Prova tecnica di trasmissione. Uno, due, tre. Se mi senti normale, il problema era lo stereo."

    # Comando Piper
    cmd_piper = [piper, "--model", model, "--output_raw"]

    # Comando Aplay
    # -c 1 = Mono (CRUCIALE per evitare l'effetto velocità doppia)
    # -r {rate} = Usa la frequenza scritta nel file di configurazione
    cmd_aplay = ["aplay", "-r", rate, "-c", "1", "-f", "S16_LE", "-t", "raw", "-"]

    print("\nRiproduzione...")
    try:
        p1 = subprocess.Popen(cmd_piper, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(cmd_aplay, stdin=p1.stdout)
        
        _, err = p1.communicate(input=text.encode('utf-8'))
        p2.wait()
        
        if p1.returncode != 0:
            print(f"❌ Errore Piper: {err.decode()}")
        else:
            print("✅ Test completato.")
            
    except Exception as e:
        print(f"❌ Errore esecuzione: {e}")

if __name__ == "__main__":
    test_speak()