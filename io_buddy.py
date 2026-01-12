import os
import time
import logging
import threading
import queue
import subprocess
from dataclasses import dataclass
from ctypes import CFUNCTYPE, c_char_p, c_int, cdll
from dotenv import load_dotenv  # Aggiunto per caricare config.env

# --- LIBRERIE AUDIO STANDARD ---
import speech_recognition as sr
from gtts import gTTS
from gpiozero import LED

# --- LIBRERIE PICOVOICE (WAKE WORD) ---
import pvporcupine
from pvrecorder import PvRecorder

# Carichiamo le variabili d'ambiente (chiavi e path)
load_dotenv()
load_dotenv("config.env")

# --- CONFIGURAZIONE LOGGER ---
logger = logging.getLogger()

@dataclass
class BuddyEvent:
    source: str      # "terminal", "jabra", "sensor"
    content: str     # Il testo o il dato
    timestamp: float = 0.0

# --- GESTIONE BASSO LIVELLO AUDIO (ALSA/JACK SILENCE) ---
# MANTENUTO ESATTAMENTE COME NEL TUO FILE
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
# MANTENUTA ESATTAMENTE COME NEL TUO FILE (Piper + SoX chain)
class BuddyVoice:
    def __init__(self):
        # Configurazione: default 'cloud' (gTTS), opzionale 'local' (Piper)
        self.mode = os.getenv("TTS_MODE", "cloud").lower()
        # Voce scelta: default 'paola' (o 'riccardo')
        self.voice_name = os.getenv("TTS_VOICE", "paola").lower()
        
        self.led_stato = LED(21) # Pin 21: Verde (Stato/Parlato)
        self.is_speaking_event = threading.Event()
        
        # --- PERCORSI E CONFIGURAZIONE PIPER ---
        home = os.path.expanduser("~")
        self.piper_base_path = os.path.join(home, "buddy_tools/piper")
        self.piper_binary = os.path.join(self.piper_base_path, "piper/piper")
        
        # Mappa delle voci disponibili (File e Velocità ottimale)
        self.voice_map = {
            "paola":    {"file": "it_IT-paola-medium.onnx", "speed": "1.0"},
            "riccardo": {"file": "it_IT-riccardo-x_low.onnx", "speed": "1.1"}
        }
        
        # Selezione configurazione
        if self.voice_name not in self.voice_map:
            logger.warning(f"Voce '{self.voice_name}' non trovata. Fallback su Paola.")
            self.voice_name = "paola"
            
        selected_config = self.voice_map[self.voice_name]
        self.piper_model = os.path.join(self.piper_base_path, selected_config["file"])
        self.piper_speed = selected_config["speed"]
        
        logger.info(f"BuddyVoice inizializzato. Mode: {self.mode} | Voice: {self.voice_name.upper()}")

    def speak(self, text):
        """Gestisce la sintesi vocale in base alla configurazione."""
        try:
            text = text.replace('"', '').replace("'", "")
            self.led_stato.on()
            self.is_speaking_event.set()

            if self.mode == "local":
                self._speak_local_piper(text)
            else:
                self._speak_gtts(text)

        except Exception as e:
            logger.error(f"Errore TTS: {e}")
        finally:
            self.is_speaking_event.clear()
            self.led_stato.off()

    def _speak_local_piper(self, text):
        """Usa Piper TTS -> SoX -> Aplay (Catena per fix 48kHz)."""
        try:
            piper_cmd = [
                self.piper_binary,
                "--model", self.piper_model,
                "--length_scale", self.piper_speed, 
                "--output_file", "-" 
            ]

            sox_cmd = [
                "sox",
                "-t", "wav", "-",   # Input Pipe
                "-r", "48000",      # Output Rate
                "-t", "wav", "-"    # Output Pipe
            ]

            aplay_cmd = ["aplay", "-D", "plughw:0,0"]

            p_piper = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_sox = subprocess.Popen(sox_cmd, stdin=p_piper.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_aplay = subprocess.Popen(aplay_cmd, stdin=p_sox.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            p_piper.stdout.close()
            p_sox.stdout.close()
            
            _, stderr_piper = p_piper.communicate(input=text.encode('utf-8'))
            p_aplay.wait()

            if p_piper.returncode != 0:
                logger.error(f"Errore Piper: {stderr_piper.decode()}")

        except FileNotFoundError:
            logger.error("Componenti audio mancanti (Piper/SoX/Aplay).")
        except Exception as e:
            logger.error(f"Eccezione in _speak_local_piper: {e}")

    def _speak_gtts(self, text):
        tts = gTTS(text=text, lang='it')
        filename = "debug_audio.mp3"
        tts.save(filename)
        subprocess.run(["mpg123", "-q", filename], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

# --- CLASSE PER L'INPUT UDITIVO (EARS) ---
# MODIFICATA PER INTEGRARE PORCUPINE MA MANTENENDO LA LOGICA GOOGLE ESISTENTE
class BuddyEars:
    def __init__(self, event_queue, speaking_event):
        self.mode = os.getenv("STT_MODE", "cloud").lower()
        self.event_queue = event_queue
        self.buddy_is_speaking = speaking_event
        self.led_ascolto = LED(26) # Pin 26: Blu (Ascolto)
        self.running = True
        
        # --- CONFIGURAZIONE PICOVOICE (NUOVA) ---
        self.access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        self.keyword_path = os.getenv("WAKE_WORD_PATH")
        
        self.porcupine = None
        self.recorder = None
        
        # Verifica Wake Word
        if not self.access_key or not self.keyword_path or not os.path.exists(self.keyword_path):
            logger.error("❌ ERRORE WAKE WORD: Controlla PICOVOICE_ACCESS_KEY e WAKE_WORD_PATH nel config.env")
            # Fallback o stop? Per ora logghiamo errore ma lasciamo init
        else:
            try:
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=[self.keyword_path]
                )
                self.recorder = PvRecorder(device_index=-1, frame_length=self.porcupine.frame_length)
                logger.info("👂 Porcupine attivato: 'Ehi Buddy' pronto.")
            except Exception as e:
                logger.error(f"Errore init Porcupine: {e}")

        logger.info(f"BuddyEars inizializzato. STT Mode: {self.mode}")

    def listen_loop(self):
        """Loop ibrido: Wake Word Locale -> Google STT Cloud."""
        
        # Se Porcupine non è configurato, usciamo (o si potrebbe fare fallback su loop continuo)
        if not self.porcupine or not self.recorder:
            logger.error("Impossibile avviare loop ascolto: Porcupine non inizializzato.")
            return

        recognizer = sr.Recognizer()
        # Le tue impostazioni ottimizzate
        recognizer.pause_threshold = 1.0 
        recognizer.non_speaking_duration = 0.5
        recognizer.dynamic_energy_threshold = False 
        recognizer.energy_threshold = 400

        logger.info("Thread Ears avviato (Modalità Wake Word)")
        
        try:
            self.recorder.start() # Avvia ascolto locale leggero
            
            while self.running:
                # 1. Se Buddy parla, pausa tutto per evitare feedback
                if self.buddy_is_speaking.is_set():
                    time.sleep(0.1)
                    continue
                
                # 2. Ascolto Wake Word (Locale, veloce)
                pcm = self.recorder.read()
                result = self.porcupine.process(pcm)

                if result >= 0:
                    logger.info("✨ WAKE WORD RILEVATA! ('Ehi Buddy')")
                    self.led_ascolto.on()

                    # 3. STOP Porcupine per liberare il microfono
                    self.recorder.stop()
                    
                    # 4. START Google Speech Recognition
                    try:
                        with sr.Microphone() as source:
                            logger.info("🎤 In ascolto del comando (Google)...")
                            # Timeout breve (5s) per aspettare che inizi a parlare
                            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                            
                            self.led_ascolto.off()
                            # Processiamo l'audio
                            self._process_audio(recognizer, audio)
                            
                    except sr.WaitTimeoutError:
                        logger.info("⏳ Nessun comando dopo la wake word.")
                        self.led_ascolto.off()
                    except Exception as e:
                        logger.error(f"Errore durante ascolto comando: {e}")
                        self.led_ascolto.off()
                    
                    # 5. RESTART Porcupine
                    logger.info("👂 Torno in attesa di 'Ehi Buddy'...")
                    self.recorder.start()

        except Exception as e:
            logger.error(f"Errore critico loop Ears: {e}")
        finally:
            if self.recorder: self.recorder.delete()
            if self.porcupine: self.porcupine.delete()
            self.led_ascolto.off()

    def _process_audio(self, recognizer, audio):
        """Decide quale motore STT usare (Codice tuo originale mantenuto)."""
        text = ""
        try:
            # Usiamo sempre Google come da tua configurazione stabile
            text = recognizer.recognize_google(audio, language="it-IT")

            if text:
                logger.info(f"🗣️  Comando capito: {text}")
                event = BuddyEvent(source="jabra", content=text, timestamp=time.time())
                self.event_queue.put(event)

        except sr.UnknownValueError:
            logger.info("🤷 Google non ha capito le parole.")
        except Exception as e:
            logger.error(f"Errore riconoscimento: {e}")

    def start(self):
        t = threading.Thread(target=self.listen_loop, daemon=True, name="EarsThread")
        t.start()