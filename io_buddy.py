import os
import time
import logging
import threading
import queue
import subprocess
from dataclasses import dataclass
from ctypes import CFUNCTYPE, c_char_p, c_int, cdll
import speech_recognition as sr
from gtts import gTTS
from gpiozero import LED

# --- CONFIGURAZIONE LOGGER ---
logger = logging.getLogger()

@dataclass
class BuddyEvent:
    source: str      # "terminal", "jabra", "sensor"
    content: str     # Il testo o il dato
    timestamp: float = 0.0

# --- GESTIONE BASSO LIVELLO AUDIO (ALSA/JACK SILENCE) ---
# Manteniamo questa logica qui per non inquinare il main
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
    """Zittisce forzatamente stderr a basso livello."""
    def __enter__(self):
        self.err_null = os.open(os.devnull, os.O_WRONLY)
        self.old_err = os.dup(2)
        os.dup2(self.err_null, 2)
    def __exit__(self, *args):
        os.dup2(self.old_err, 2)
        os.close(self.err_null)
        os.close(self.old_err)

# --- CLASSE PER L'OUTPUT VOCALE (VOICE) ---
class BuddyVoice:
    def __init__(self):
        # Configurazione: default 'cloud' (gTTS), opzionale 'local' (es. pyttsx3/piper)
        self.mode = os.getenv("TTS_MODE", "cloud").lower()
        self.led_stato = LED(21) # Pin 21: Verde (Stato/Parlato)
        self.is_speaking_event = threading.Event()
        logger.info(f"BuddyVoice inizializzato in modalità: {self.mode}")

    def speak(self, text):
        """Gestisce la sintesi vocale in base alla configurazione."""
        try:
            logger.debug(f"Inizio sintesi vocale ({self.mode}): {text[:20]}...")
            self.led_stato.on()
            self.is_speaking_event.set()

            if self.mode == "local":
                # TODO: Implementare TTS locale (es. Piper o pyttsx3)
                logger.warning("Modalità TTS locale non ancora implementata, fallback su print.")
                print(f"[TTS LOCALE]: {text}")
                # Simuliamo il tempo di parlato
                time.sleep(len(text) * 0.05) 
            else:
                # Default: Cloud (gTTS)
                self._speak_gtts(text)

            logger.debug("Riproduzione audio completata")

        except Exception as e:
            logger.error(f"Errore TTS: {e}")
        finally:
            self.is_speaking_event.clear()
            self.led_stato.off()

    def _speak_gtts(self, text):
        tts = gTTS(text=text, lang='it')
        filename = "debug_audio.mp3"
        tts.save(filename)
        
        # Riproduzione con mpg123
        result = subprocess.run(
            ["mpg123", "-q", filename], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Errore mpg123: {result.stderr}")

# --- CLASSE PER L'INPUT UDITIVO (EARS) ---
class BuddyEars:
    def __init__(self, event_queue, speaking_event):
        # Configurazione: default 'cloud' (Google), opzionale 'local' (es. Whisper)
        self.mode = os.getenv("STT_MODE", "cloud").lower()
        self.event_queue = event_queue
        self.buddy_is_speaking = speaking_event
        self.led_ascolto = LED(26) # Pin 26: Blu (Ascolto)
        self.running = True
        logger.info(f"BuddyEars inizializzato in modalità: {self.mode}")

    def listen_loop(self):
        """Loop principale di ascolto."""
        if not self._check_hardware():
            return

        r = sr.Recognizer()
        r.pause_threshold = 1.5
        r.non_speaking_duration = 0.5
        r.dynamic_energy_threshold = True

        logger.info("Thread Jabra (Ears) avviato")

        while self.running:
            # Se Buddy sta parlando, le orecchie riposano per evitare eco
            if self.buddy_is_speaking.is_set():
                time.sleep(0.1)
                continue

            try:
                with SuppressStream():
                    with sr.Microphone() as source:
                        r.adjust_for_ambient_noise(source, duration=0.1)
                        
                        try:
                            self.led_ascolto.on()
                            # Timeout 5s per iniziare a parlare
                            audio = r.listen(source, timeout=5, phrase_time_limit=None)
                            self.led_ascolto.off()
                            
                            self._process_audio(r, audio)

                        except sr.WaitTimeoutError:
                            self.led_ascolto.off()
                            pass
                        except sr.UnknownValueError:
                            self.led_ascolto.off()
                            pass
            except Exception as e:
                self.led_ascolto.off()
                logger.error(f"Errore critico Ears: {e}")
                time.sleep(0.1)

    def _check_hardware(self):
        try:
            with SuppressStream():
                mics = sr.Microphone.list_microphone_names()
            if mics:
                logger.info(f"Microfoni trovati: {mics}")
                return True
            else:
                logger.warning("Nessun microfono rilevato.")
                return False
        except Exception as e:
            logger.error(f"Errore controllo mic: {e}")
            return False

    def _process_audio(self, recognizer, audio):
        """Decide quale motore STT usare."""
        text = ""
        try:
            if self.mode == "local":
                # TODO: Implementare STT locale (es. Whisper o Vosk)
                # Per ora usiamo Google come placeholder finché non installiamo le lib locali
                logger.warning("STT Locale non ancora attivo, uso Google temporaneamente.")
                text = recognizer.recognize_google(audio, language="it-IT")
            else:
                # Default: Google Cloud Speech API (tramite speech_recognition)
                text = recognizer.recognize_google(audio, language="it-IT")

            if text:
                logger.info(f"Jabra Input Rilevato: {text}")
                event = BuddyEvent(source="jabra", content=text, timestamp=time.time())
                self.event_queue.put(event)

        except Exception as e:
            logger.error(f"Errore riconoscimento ({self.mode}): {e}")

    def start(self):
        t = threading.Thread(target=self.listen_loop, daemon=True, name="EarsThread")
        t.start()