# 🚀 Buddy Project - TODO List

## 🟡 FASE 2: Indipendenza e Wake Word (Priorità Alta)
- [ ] **STT Locale (Whisper):** Sostituire Google Cloud con Whisper locale (versione Tiny/Base ottimizzata per Pi 5).
- [ ] **Wake Word Integration:** Configurazione motore locale (Porcupine/Snowboy) per attivazione su "Ehi Buddy".

## 🟡 FASE 3: Sensi Fisici e Refactoring (Hardware Pronto)
- [ ] **Radar mmWave (LD2410C):** Collegamento fisico tramite T-Cobbler e cavetti DuPont.
- [ ] **Monitoraggio Presenza:** Sviluppo script in background per lettura dati radar.
- [ ] **Logica Proattiva:** Implementazione trigger "Presenza + Silenzio > 2 ore".
- [ ] **Resume Work:** Logica per riprendere il filo del discorso/lavoro al ritorno dell'utente.
- [ ] **Refactoring Architetturale:** Separazione moduli `io_buddy.py` in `stt.py`, `tts.py`, `hardware.py`.

## 🔴 FASE 4: Memoria Totale e Decay
- [ ] **Database SQLite:** Setup su SSD per log conversazioni e metadati.
- [ ] **RAG (Il Diario):** Ricerca semantica nel DB per recupero ricordi pre-risposta.
- [ ] **Dimenticatoio Selettivo (Decay):** Implementazione degradazione ricordi (Istr. 08/01).
- [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB.

## 🔵 FASE 5: Integrazioni Finali
- [ ] **Domotica Tapo:** Integrazione luci e prese smart tramite API.
- [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine.