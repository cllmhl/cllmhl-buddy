import os
import time
import logging
import threading
import queue
import subprocess
from dataclasses import dataclass
from ctypes import CFUNCTYPE, c_char_p, c_int, cdll
from dotenv import load_dotenv

# --- MOCK GPIO PER TESTING (solo se non su Raspberry Pi) ---
if not os.path.exists('/proc/device-tree/model'):
    # Non siamo su Raspberry Pi, usa mock pin factory
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

# --- LIBRERIE AUDIO STANDARD ---
import speech_recognition as sr
from gtts import gTTS
from gpiozero import LED

# --- LIBRERIE PICOVOICE (WAKE WORD) ---
import pvporcupine
from pvrecorder import PvRecorder

# Carichiamo le variabili d'ambiente
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
        # Configurazione: default 'cloud' (gTTS), opzionale 'local' (Piper)
        self.mode = os.getenv("TTS_MODE", "cloud").lower()
        self.voice_name = os.getenv("TTS_VOICE", "paola").lower()
        
        self.led_stato = LED(21) # Pin 21: Verde (Stato/Parlato)
        self.is_speaking_event = threading.Event()
        
        # --- PERCORSI E CONFIGURAZIONE PIPER ---
        home = os.path.expanduser("~")
        self.piper_base_path = os.path.join(home, "buddy_tools/piper")
        self.piper_binary = os.path.join(self.piper_base_path, "piper/piper")
        
        # Mappa delle voci disponibili
        self.voice_map = {
            "paola":    {"file": "it_IT-paola-medium.onnx", "speed": "1.0"},
            "riccardo": {"file": "it_IT-riccardo-x_low.onnx", "speed": "1.1"}
        }
        
        if self.voice_name not in self.voice_map:
            logger.warning(f"Voce '{self.voice_name}' non trovata. Fallback su Paola.")
            self.voice_name = "paola"
            
        selected_config = self.voice_map[self.voice_name]
        self.piper_model = os.path.join(self.piper_base_path, selected_config["file"])
        self.piper_speed = selected_config["speed"]
        
        logger.info(f"BuddyVoice inizializzato. Mode: {self.mode} | Voice: {self.voice_name.upper()}")

    def speak(self, text):
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
        try:
            piper_cmd = [
                self.piper_binary, "--model", self.piper_model,
                "--length_scale", self.piper_speed, "--output_file", "-"
            ]
            sox_cmd = ["sox", "-t", "wav", "-", "-r", "48000", "-t", "wav", "-"]
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

        except Exception as e:
            logger.error(f"Eccezione in _speak_local_piper: {e}")

    def _speak_gtts(self, text):
        tts = gTTS(text=text, lang='it')
        filename = "debug_audio.mp3"
        tts.save(filename)
        subprocess.run(["mpg123", "-q", filename], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if os.path.exists(filename): os.remove(filename)

# --- CLASSE PER L'INPUT UDITIVO (EARS) ---
class BuddyEars:
    def __init__(self, event_queue, speaking_event):
        self.mode = os.getenv("STT_MODE", "cloud").lower()
        self.event_queue = event_queue
        self.buddy_is_speaking = speaking_event
        self.led_ascolto = LED(26) 
        self.running = True
        self.enabled = True  # Flag per sapere se Ears è funzionante
        
        self.access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        self.keyword_path = os.getenv("WAKE_WORD_PATH")
        
        self.porcupine = None
        self.recorder = None
        self.device_index = -1
        
        # Verifica configurazione base
        if not self.access_key or not self.keyword_path:
            logger.warning("⚠️ PICOVOICE_ACCESS_KEY o WAKE_WORD_PATH mancanti. Wake Word DISABILITATO.")
            self.enabled = False
            return
        
        if not os.path.exists(self.keyword_path):
            logger.warning(f"⚠️ File Wake Word non trovato: {self.keyword_path}. Wake Word DISABILITATO.")
            self.enabled = False
            return
        
        # Tenta inizializzazione Porcupine
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.keyword_path]
            )
        except Exception as e:
            logger.warning(f"⚠️ Init Porcupine fallito: {e}. Wake Word DISABILITATO.")
            logger.info("💡 Questo è normale se non sei su Raspberry Pi o non hai l'hardware audio.")
            self.enabled = False
            return
            
        # Tenta inizializzazione Recorder
        try:
            target_index = -1
            available_devices = PvRecorder.get_available_devices()
            logger.info(f"Dispositivi Audio Rilevati: {available_devices}")
            
            for i, device in enumerate(available_devices):
                if "Jabra" in device:
                    target_index = i
                    logger.info(f"✅ Microfono Jabra trovato all'indice {i}: {device}")
                    break
            
            if target_index == -1:
                logger.warning("⚠️ Nessun Jabra trovato. Uso dispositivo di default (0).")
                target_index = 0
            
            self.device_index = target_index  # Salva per uso successivo
            self.recorder = PvRecorder(device_index=target_index, frame_length=self.porcupine.frame_length)
            
            # Test rapido Hardware
            self.recorder.start()
            self.recorder.stop()
            
            logger.info("👂 Porcupine attivato: 'Ehi Buddy' pronto.")
            
        except Exception as e:
            logger.warning(f"⚠️ Errore Hardware Microfono: {e}. Wake Word DISABILITATO.")
            logger.info("💡 Questo è normale se non sei su Raspberry Pi o non hai l'hardware audio.")
            self.enabled = False
            if self.porcupine:
                self.porcupine.delete()
                self.porcupine = None
            return

        logger.info(f"BuddyEars inizializzato. STT Mode: {self.mode}")

    def listen_loop(self):
        """Loop: Attesa Wake Word -> Sessione Continua -> Timeout."""
        
        if not self.enabled:
            logger.info("👂 BuddyEars disabilitato (nessun hardware wake word). Thread termina.")
            return
        
        if not self.porcupine or not self.recorder:
            logger.error("Impossibile avviare loop ascolto: Componenti non pronti.")
            return

        recognizer = sr.Recognizer()
        # Impostazioni ottimizzate
        recognizer.pause_threshold = 1.0 
        recognizer.non_speaking_duration = 0.5
        recognizer.dynamic_energy_threshold = False 
        recognizer.energy_threshold = 400

        logger.info("Thread Ears avviato (Attesa Wake Word)")
        
        try:
            self.recorder.start()
            
            while self.running:
                # Se Buddy parla, pausa per evitare trigger falsi
                if self.buddy_is_speaking.is_set():
                    time.sleep(0.1)
                    continue
                
                # 1. Ascolto Wake Word (PvRecorder)
                pcm = self.recorder.read()
                result = self.porcupine.process(pcm)

                if result >= 0:
                    logger.info("✨ WAKE WORD! Inizio Sessione Conversazione.")
                    self.led_ascolto.on()
                    self.recorder.stop() # Rilascio il mic per Google
                    
                    # 2. Avvio Sessione Continua
                    self._run_conversation_session(recognizer)
                    
                    # Fine Sessione
                    logger.info("💤 Fine Sessione. Torno in attesa di 'Ehi Buddy'...")
                    self.led_ascolto.off()
                    self.recorder.start() # Riprendo il mic per Porcupine

        except Exception as e:
            logger.error(f"Errore critico loop Ears: {e}")
        finally:
            if self.recorder: self.recorder.delete()
            if self.porcupine: self.porcupine.delete()
            self.led_ascolto.off()

    def _run_conversation_session(self, recognizer):
        """
        Gestisce il dialogo continuo con timeout reale.
        Il timeout di 15s si resetta SEMPRE se Buddy parla.
        """
        session_alive = True
        MAX_SILENCE_SECONDS = 15.0
        
        # Timestamp dell'ultima attività (parlato Buddy o input utente)
        last_interaction_time = time.time()
        
        # Inizializza il mic una sola volta
        with SuppressStream():
             mic_source = sr.Microphone()
             
        try:
            with mic_source as source:
                logger.info("🎤 Sessione Attiva. Parla pure...")
                
                while session_alive and self.running:
                    # 1. CONTROLLO PRIORITARIO: Buddy sta parlando?
                    if self.buddy_is_speaking.is_set():
                        # Se Buddy parla, il tempo è "congelato" o meglio resettato.
                        # Aggiorniamo il timestamp a "adesso" continuamente.
                        last_interaction_time = time.time()
                        time.sleep(0.1)
                        continue

                    # 2. CONTROLLO TIMEOUT REALE
                    # Quanto tempo è passato dall'ultima volta che Buddy ha finito o tu hai parlato?
                    elapsed = time.time() - last_interaction_time
                    if elapsed > MAX_SILENCE_SECONDS:
                        logger.info(f"⏳ Silenzio Reale > {MAX_SILENCE_SECONDS}s. Chiudo sessione.")
                        session_alive = False
                        continue

                    try:
                        # 3. ASCOLTO "A FETTE" (POLLING)
                        # Invece di ascoltare per 15s (che blocca tutto), ascoltiamo per 1.0s.
                        # Questo ci permette di tornare su al punto 1 e controllare se Buddy ha iniziato a parlare.
                        # timeout=1.0: Aspetta massimo 1s che l'utente INIZI a parlare.
                        audio = recognizer.listen(source, timeout=1.0, phrase_time_limit=15)
                        
                        # Se siamo qui, l'utente ha parlato!
                        # Resettiamo il timer
                        last_interaction_time = time.time()
                        
                        # Processiamo
                        threading.Thread(target=self._process_audio, args=(recognizer, audio)).start()
                        
                    except sr.WaitTimeoutError:
                        # Nessuno ha parlato nell'ultimo secondo.
                        # Non facciamo nulla, torniamo su.
                        # Il ciclo ricontrollerà se Buddy sta parlando e se il tempo totale è scaduto.
                        pass
                        
                    except Exception as e:
                        logger.warning(f"Errore lieve in sessione: {e}")
                        
        except Exception as e:
            logger.error(f"Errore apertura microfono sessione: {e}")

    def _process_audio(self, recognizer, audio):
        """Decide quale motore STT usare."""
        try:
            text = recognizer.recognize_google(audio, language="it-IT")

            if text:
                logger.info(f"🗣️  Comando capito: {text}")
                event = BuddyEvent(source="jabra", content=text, timestamp=time.time())
                self.event_queue.put(event)

        except sr.UnknownValueError:
            pass # Ignoriamo suoni non parole
        except Exception as e:
            logger.error(f"Errore riconoscimento: {e}")

    def start(self):
        t = threading.Thread(target=self.listen_loop, daemon=True, name="EarsThread")
        t.start()