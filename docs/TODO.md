# 🚀 Buddy Project - Roadmap

## Testing & Stabilità
1. [ ] **Testing Stabilità Wake Word:** Verifica timeout sessione (15s) e gestione concorrenza audio (Jabra lock)
2. [ ] **Test Completo Sistema:** Verificare funzionamento completo su Raspberry Pi in produzione

## Sensi Fisici e Architettura Modulare

### Refactoring Architettura (Event-Driven)
3. [x] **Creazione `senses.py` (INPUT):** Modulo isolato per la lettura dei sensori. Scrive solo nella `event_queue`
4. [ ] **Creazione `feedback.py` (OUTPUT):** Modulo per feedback non verbali (LED, Suoni, Display)
5. [ ] **Refactoring `io_buddy.py` -> `audio_core.py`:** Pulizia del modulo audio (rimozione gestione LED/Sensori), focus solo su Mic/Cange Speaker
6. [ ] **Orchestrazione `main.py`:** Aggiornamento del loop principale per smistare eventi da `senses` a `brain` a `feedback`/`audio`

### Integrazione Hardware
7. [x] **Radar mmWave (LD2410C):** Lettura via UART (Serial) in `senses.py`. Rilevamento presenza statica/movimento
8. [x] **Sensore Ambiente:** Integrazione DHT11 (Temp/Umidità) su GPIO
9. [ ] **Sensore Luminosita:** Integrazione LDR (Luce) su GPIO
10. [ ] **Display 7-Segment (TM1637):** Visualizzazione codici stato (es. "Err", "On") o orologio in `feedback.py`
11. [ ] **Active Buzzer:** Feedback acustici (Beep conferma, Alarm error) in `feedback.py`
12. [ ] **Logica Proattiva:** Implementazione trigger "Presenza + Silenzio > 2 ore" (Buddy saluta se entri dopo tanto tempo)

## Miglioramento Voce (Google Cloud API)
13. [ ] **Google Cloud TTS (Professionale):** Sostituzione gTTS con API Neural2/WaveNet (richiede account Billing Google Cloud)
14. [ ] **Google Cloud STT (Streaming):** Valutazione passaggio a STT in streaming reale per latenza zero (vs speech_recognition attuale)

## Memoria e Intelligence
15. [ ] **Database SQLite su SSD:** Ottimizzazione storage per log conversazioni e metadati persistenti
16. [ ] **RAG (Il Diario):** Ricerca semantica nel DB per recupero contesto storico prima di rispondere
17. [ ] **Dimenticatoio Selettivo (Decay):** Implementazione algoritmo di pulizia ricordi vecchi/inutili
18. [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB

## Integrazioni Smart Home
19. [ ] **Domotica Tapo:** Integrazione luci e prese smart tramite API
20. [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine

---

## ✅ Completato

### Wake Word & Background System
- [x] **Wake Word Integration:** Implementazione Picovoice Porcupine ("Ehi Buddy") con loop di ascolto ibrido
- [x] **Esecuzione in background (Service):** Creazione file `buddy.service` per avvio automatico con `systemd`
- [x] **Input da Terminale (Named Pipe):** Implementazione FIFO pipe per inviare comandi testuali anche se Buddy gira in background
- [x] **Organizzazione Progetto:** Struttura cartelle `scripts/`, `config/`, `docs/` per codice pulito e manutenibile
