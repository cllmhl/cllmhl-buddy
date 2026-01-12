# 🚀 Buddy Project - TODO List

## 🟡 FASE 2: Wake Word (Priorità Alta)
- [ ] **Wake Word Integration:** Configurazione motore locale (Porcupine/Snowboy) per attivazione su "Ehi Buddy".

## 🟡 FASE 3: Sensi Fisici e Refactoring (Hardware Pronto)
- [ ] **Radar mmWave (LD2410C):** Collegamento fisico tramite T-Cobbler e cavetti DuPont.
- [ ] **Monitoraggio Presenza:** Sviluppo script in background per lettura dati radar.
- [ ] **Logica Proattiva:** Implementazione trigger "Presenza + Silenzio > 2 ore".
- [ ] **Resume Work:** Logica per riprendere il filo del discorso/lavoro al ritorno dell'utente.
- [ ] **Refactoring Architetturale:** Separazione moduli `io_buddy.py` in `stt.py`, `tts.py`, `hardware.py`.

## 🟡 FASE 4: Google Cloud API: Le API di google sembrano imbattibili. Proviamole seriamente!
- [ ] **Valutazione Google Cloud TTS API:** Implementazione Google Cloud TTS API (Voci Neural2/WaveNet) per sostituire gTTS e Piper con qualità umana.
- [ ] **Valutazione Google Cloud STT API:** Implementazione Google Cloud STT API per confrontarla con speech_recognition attuale.

## 🔴 FASE 5: Memoria Totale e Decay
- [ ] **Database SQLite:** Setup su SSD per log conversazioni e metadati.
- [ ] **RAG (Il Diario):** Ricerca semantica nel DB per recupero ricordi pre-risposta.
- [ ] **Dimenticatoio Selettivo (Decay):** Implementazione degradazione ricordi (Istr. 08/01).
- [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB.

## 🔵 FASE 6: Integrazioni Finali
- [ ] **Domotica Tapo:** Integrazione luci e prese smart tramite API.
- [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine.
