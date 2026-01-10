from logging.handlers import RotatingFileHandler
import os
import logging
from dotenv import load_dotenv
import threading
import queue
import time
import subprocess
from dataclasses import dataclass
from ctypes import CFUNCTYPE, c_char_p, c_int, cdll # Aggiunto per silence_alsa
import speech_recognition as sr
from gtts import gTTS
# --- AGGIUNTA LIBRERIA GPIO ---
from gpiozero import LED

# Le tue classi esistenti
from database_buddy import BuddyDatabase
from brain import BuddyBrain
from archivist import BuddyArchivist

# --- CONFIGURAZIONE HARDWARE LED ---
# Inizializzazione LED sui pin scelti (26 Blu, 21 Verde)
led_ascolto = LED(26) 
led_stato = LED(21)

# --- CONFIGURAZIONE LOGGING ---
# I log vanno SOLO su file, niente output su console
handler = RotatingFileHandler('buddy_system.log', maxBytes=10*1024*1024, backupCount=1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
handler.setFormatter(formatter)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.INFO)
logging.getLogger("posthog").setLevel(logging.ERROR)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# --- SILENZIAMENTO LOG ESTERNI (ALSA/JACK) ---
def py_error_handler(filename, line, function, err, fmt):
    pass

ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

def silence_alsa():
    """Impedisce alle librerie audio di scrivere errori non critici nel terminale."""
    try:
        asound = cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(c_error_handler)
    except Exception:
        pass

class SuppressStream:
    """Zittisce forzatamente stderr a basso livello per bloccare JACK/ALSA in console."""
    def __enter__(self):
        self.err_null = os.open(os.devnull, os.O_WRONLY)
        self.old_err = os.dup(2)
        os.dup2(self.err_null, 2)
    def __exit__(self, *_):
        os.dup2(self.old_err, 2)
        os.close(self.err_null)
        os.close(self.old_err)

# --- DEFINIZIONE EVENTI ---
@dataclass
class BuddyEvent:
    source: str      # "terminal", "jabra", "sensor"
    content: str     # Il testo o il dato
    timestamp: float = 0.0

# Semaforo per evitare l'auto-ascolto
buddy_is_speaking = threading.Event()
# Coda centrale
event_queue = queue.Queue()

# --- ATTUATORI (OUTPUT) ---

def speak_text(text):
    """Genera audio TTS."""
    try:
        logger.debug(f"Inizio sintesi vocale: {text[:20]}...")
        led_stato.on() # Accensione LED verde (parlato)
        buddy_is_speaking.set()
        
        tts = gTTS(text=text, lang='it')
        filename = "debug_audio.mp3"  # Nome fisso per trovarlo facilmente
        tts.save(filename)
        
        logger.debug(f"File {filename} creato. Avvio riproduzione...")
        
        # Usiamo stderr=subprocess.PIPE per leggere l'errore se mpg123 fallisce
        # Proviamo a non forzare il device, lasciando che il sistema usi il default
        result = subprocess.run(
            ["mpg123", "-q", filename], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Errore mpg123 (Exit Code {result.returncode}): {result.stderr}")
        
        # COMMENTA temporaneamente la riga sotto per verificare se il file viene creato
        # if os.path.exists(filename): os.remove(filename) 
        
        logger.debug("Riproduzione audio completata")
            
    except Exception as e:
        logger.error(f"Errore TTS: {e}")
    finally:
        buddy_is_speaking.clear()
        led_stato.off() # Spegnimento LED verde

# --- SENSORI (INPUT THREADS) ---

def keyboard_thread():
    """Ascolta il terminale."""
    logger.info("Thread tastiera avviato")
    while True:
        try:
            text = input() 
            if text:
                event = BuddyEvent(source="terminal", content=text, timestamp=time.time())
                event_queue.put(event)
        except EOFError:
            break

def jabra_thread():
    """Ascolta il microfono Jabra."""
    r = sr.Recognizer()
    
    # --- MODIFICA STRETTAMENTE NECESSARIA ---
    # Riducendo pause_threshold, termina l'ascolto appena smetti di parlare (Problema 2)
    r.pause_threshold = 0.8  
    # Dynamic energy aiuta a regolare la sensibilità automaticamente (Problema 3)
    r.dynamic_energy_threshold = True 
    
    logger.info("Thread Jabra avviato con calibrazione dinamica")
    
    while True:
        if buddy_is_speaking.is_set():
            time.sleep(0.1)
            continue

        try:
            # Wrap per silenziare i log JACK/ALSA durante l'apertura del microfono
            with SuppressStream():
                with sr.Microphone() as source:
                    # --- MODIFICA STRETTAMENTE NECESSARIA ---
                    # Calibra il rumore ambientale per non dover urlare (Problema 3)
                    # Ascolta il rumore di fondo per 0.5 secondi prima di ogni ascolto
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    
                    # Timeout breve per non bloccare il thread per sempre se c'è silenzio
                    try:
                        # logger.debug("Jabra in ascolto...") # Troppo verboso anche per il log?
                        led_ascolto.on() # Accensione LED blu (ascolto)
                        
                        # timeout=5: aspetta 5 secondi che tu inizi a parlare
                        # phrase_time_limit=None: non interrompe finché non finisci la frase
                        audio = r.listen(source, timeout=5, phrase_time_limit=None)
                        
                        led_ascolto.off() # Spegnimento LED blu dopo cattura audio
                        
                        text = r.recognize_google(audio, language="it-IT")
                        
                        if text:
                            logger.info(f"Jabra Input Rilevato: {text}")
                            event = BuddyEvent(source="jabra", content=text, timestamp=time.time())
                            event_queue.put(event)
                            
                    except sr.WaitTimeoutError:
                        led_ascolto.off() # Spegnimento LED se timeout
                        pass 
                    except sr.UnknownValueError:
                        led_ascolto.off() # Spegnimento LED se non compreso
                        pass 
                    
        except Exception as e:
            led_ascolto.off()
            logger.error(f"Errore critico Jabra: {e}")
            time.sleep(1)

# --- MAIN LOOP ---

def main():
    # Silenzia ALSA prima di ogni altra operazione audio
    silence_alsa()

    # Carica prima la configurazione pubblica (che può essere sovrascritta da quella privata)
    load_dotenv("config.env")
    # Carica la chiave API dal file privato
    load_dotenv(".env")
    
    # Reset LED all'avvio
    led_ascolto.off()
    led_stato.off()

    # Inizializzazione
    try:
        db = BuddyDatabase()
        api_key = os.getenv("GOOGLE_API_KEY")
        buddy = BuddyBrain(api_key)
        archivist = BuddyArchivist(api_key=api_key)
        logger.info("Sottosistemi inizializzati correttamente")
    except Exception as e:
        print(f"Errore critico in avvio: {e}")
        return

    # Avvio Threads
    t_key = threading.Thread(target=keyboard_thread, daemon=True, name="KbdThread")
    t_key.start()

    # --- CONTROLLO HARDWARE AUDIO ---
    audio_enabled = False
    try:
        # Verifica se ci sono microfoni collegati (Silenziato con SuppressStream)
        with SuppressStream():
            mics = sr.Microphone.list_microphone_names()
        
        if mics:
            logger.info(f"Microfoni trovati: {mics}")
            t_jabra = threading.Thread(target=jabra_thread, daemon=True, name="JabraThread")
            t_jabra.start()
            audio_enabled = True
        else:
            logger.warning("Nessun microfono rilevato. JabraThread non avviato.")
    except Exception as e:
        logger.error(f"Impossibile verificare l'hardware audio: {e}")

    # Output visibile all'avvio
    msg_audio = "Attivo" if audio_enabled else "Non disponibile"
    print("\n--- Buddy OS Online ---")
    print(f"Audio: {msg_audio} | Log: buddy_system.log")
    print("\nTu > ", end="", flush=True)

    last_archive_time = time.time()

    try:
        while True:
            # 1. GESTIONE EVENTI
            if not event_queue.empty():
                event = event_queue.get()
                
                # Gestione uscita
                if event.content.lower() in ["esci", "quit", "spegniti"]:
                    logger.info("Ricevuto comando di spegnimento")
                    print("\nBuddy: Shutdown...")
                    if event.source == "jabra" and audio_enabled:
                        speak_text("Mi sto spegnendo.")
                    break

                # UI: Se l'input è vocale, lo stampiamo per confermare la comprensione
                # Usiamo \r per sovrascrivere il prompt "Tu > " che era in attesa
                if event.source == "jabra":
                    print(f"\rTu (🗣️) > {event.content}")
                
                # Se era tastiera, il "Tu >" è già stato riempito dall'input dell'utente, 
                # quindi non serve ristamparlo, ma logghiamo.
                logger.info(f"Input processato ({event.source}): {event.content}")

                # Processo Cognitivo
                led_stato.on() # Accensione LED verde (elaborazione brain)
                db.add_history("user", event.content)
                risposta = buddy.respond(event.content)
                db.add_history("model", risposta)

                # Output
                print(f"Buddy > {risposta}")
                
                # Ripristina il prompt per il prossimo input
                print("\nTu > ", end="", flush=True)

                # Parla solo se l'audio è abilitato e l'input era vocale
                if event.source == "jabra" and audio_enabled:
                    speak_text(risposta)
                
                led_stato.off() # Fine elaborazione/parlato
                event_queue.task_done()

            # 2. GESTIONE ARCHIVISTA (Silenziosa)
            current_time = time.time()
            if current_time - last_archive_time > 30:
                unprocessed = db.get_unprocessed_history()
                if len(unprocessed) > 0:
                    logger.debug(f"Avvio archiviazione per {len(unprocessed)} messaggi")
                    archivist.distill_and_save(db)
                    logger.debug("Fine archiviazione")
                
                last_archive_time = current_time

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nBuddy: Arresto forzato.")
        logger.warning("Arresto forzato da tastiera")
    finally:
        # Cleanup finale LED
        led_ascolto.off()
        led_stato.off()

if __name__ == "__main__":
    main()