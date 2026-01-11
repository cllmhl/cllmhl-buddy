import subprocess
import os

# Percorsi
home = os.path.expanduser("~")
piper = os.path.join(home, "buddy_tools/piper/piper/piper")
model = os.path.join(home, "buddy_tools/piper/it_IT-riccardo-x_low.onnx")

# Messaggio
testo = "Ciao. Questa è una prova a 16000 hertz."

print(f"--- TEST VOCALE ---")
print(f"Piper: {piper}")
print(f"Model: {model}")

# Comando Piper (Base, senza opzioni extra)
cmd_piper = [piper, "--model", model, "--output_raw"]

# Comando Aplay (Rate fisso a 16000 per x_low)
cmd_aplay = ["aplay", "-r", "16000", "-f", "S16_LE", "-t", "raw", "-"]

try:
    # 1. Avvia Piper
    p1 = subprocess.Popen(
        cmd_piper, 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )

    # 2. Avvia Aplay (prende l'output di Piper)
    p2 = subprocess.Popen(
        cmd_aplay, 
        stdin=p1.stdout
    )

    # 3. Invia testo e aspetta
    print("Riproduzione in corso...")
    out, err = p1.communicate(input=testo.encode('utf-8'))
    p2.wait()

    # 4. Diagnostica errori se muto
    if p1.returncode != 0:
        print(f"❌ ERRORE PIPER:\n{err.decode()}")
    else:
        print("✅ Finito.")

except Exception as e:
    print(f"❌ ERRORE PYTHON: {e}")