# 🚀 Buddy Project - TODO List

## � FASE 2: Wake Word & Background (COMPLETATA!)
- [x] **Wake Word Integration:** Implementazione Picovoice Porcupine ("Ehi Buddy") con loop di ascolto ibrido.
- [ ] **Testing Stabilità:** Verifica timeout sessione (15s) e gestione concorrenza audio (Jabra lock).
- [x] **Esecuzione in background (Service):** Creazione file `buddy.service` per avvio automatico con `systemd`.
- [x] **Input da Terminale (Named Pipe):** Implementazione FIFO pipe per inviare comandi testuali anche se Buddy gira in background.

## 🟡 FASE 3: Sensi Fisici e Nuova Architettura (The Body)
### Architettura Modulare (Event-Driven)
- [ ] **Creazione `senses.py` (INPUT):** Modulo isolato per la lettura dei sensori. Scrive solo nella `event_queue`.
- [ ] **Creazione `feedback.py` (OUTPUT):** Modulo per feedback non verbali (LED, Suoni, Display).
- [ ] **Refactoring `io_buddy.py` -> `audio_core.py`:** Pulizia del modulo audio (rimozione gestione LED/Sensori), focus solo su Mic/Speaker.
- [ ] **Orchestrazione `main.py`:** Aggiornamento del loop principale per smistare eventi da `senses` a `brain` a `feedback`/`audio`.

### Integrazione Hardware (`senses.py` & `feedback.py`)
- [ ] **Radar mmWave (LD2410C):** Lettura via UART (Serial) in `senses.py`. Rilevamento presenza statica/movimento.
- [ ] **Sensori Ambientali:** Integrazione DHT11 (Temp/Umidità) e LDR (Luce) su GPIO.
- [ ] **Display 7-Segment (TM1637):** Visualizzazione codici stato (es. "Err", "On") o orologio in `feedback.py`.
- [ ] **Active Buzzer:** Feedback acustici (Beep conferma, Alarm error) in `feedback.py`.
- [ ] **Logica Proattiva:** Implementazione trigger "Presenza + Silenzio > 2 ore" (Buddy saluta se entri dopo tanto tempo).

## 🟡 FASE 4: Super Voice (Google Cloud API)
- [ ] **Google Cloud TTS (Professionale):** Sostituzione gTTS con API Neural2/WaveNet (richiede account Billing Google Cloud).
- [ ] **Google Cloud STT (Streaming):** Valutazione passaggio a STT in streaming reale per latenza zero (vs speech_recognition attuale).

## 🔴 FASE 5: Memoria Totale e Decay (Il Cervello)
- [ ] **Database SQLite:** Setup su SSD per log conversazioni e metadati persistenti.
- [ ] **RAG (Il Diario):** Ricerca semantica nel DB per recupero contesto storico prima di rispondere.
- [ ] **Dimenticatoio Selettivo (Decay):** Implementazione algoritmo di pulizia ricordi vecchi/inutili.
- [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB.

## 🔵 FASE 6: Integrazioni Finali (Estensioni)
- [ ] **Domotica Tapo:** Integrazione luci e prese smart tramite API.
- [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine.
