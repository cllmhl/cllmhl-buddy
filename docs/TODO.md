# WBS - Work Breakdown Structure

## 1.0 CASA

### 1.1 Logica proattiva
- [ ] **Bentornato a casa:** capisce che entro in casa: Saluto ed inizio dialogo.
- [ ] **Accediamo le luci:** capisce che entro in casa oltre le 18: "Alexa: accendi la luce".
- [ ] **Spengo le luci:** sono tra le 18 e le 8: spengo le luci se non mi muovo per un po'
- [ ] **Accendo le luci:** sono tra le 18 e le 8: accendo le luci se mi muovo dopo essere stato fermo

### 1.2 Miglioramento Voce (Google Cloud API)
- [ ] **Google Cloud TTS (Professionale):** Sostituzione gTTS con API Neural2/WaveNet (richiede account Billing Google Cloud)
- [ ] **Google Cloud STT (Streaming):** Valutazione passaggio a STT in streaming reale per latenza zero (vs speech_recognition attuale)

### 1.3 Integrazione Hardware
- [ ] **Sensore Luminosita:** Integrazione LDR (Luce): questo su GPIO non va perchè analogico. DObbiamo fare una catena. Mettiamo il sensore su arduino, colleghiamo arduino alla porta USB del Raspberry. Leggiamo dalla porta USB i dati di luminosità. In pratica la porta USB alimenta Arduino ed allo stesso tempo è un input di segnale di luce.
- [ ] **Display 7-Segment (TM1637):** Visualizzazione codici stato (es. "Err", "On")
- [ ] **LED a piacere:** ci possiamo mettere tutti i led che vogliamo
- [ ] **Migliorare meccanismo di Feedback:** Sviluppo di un sistema per notificare l'utente sullo stato del sistema (es. tramite LED, display o notifiche vocali).
- [ ] **Active Buzzer:** Feedback acustici (Beep conferma, Alarm error)
- [ ] **Domotica Tapo:** Integrazione luci e prese smart tramite API

## 2.0 Ufficio

### 2.1 Memoria e Intelligence
- [ ] **Contesto e stato di base:** Il sistema deve sempre avere chiaro chi è, che ora è, dove è, come mi chiamo, se qualcuno è in casa, la temperatura, ... Verificare che sia così. Con una serie di test di interazione di base.
- [ ] **Come funziona Buddy:** Come funziona il gioco? quanto dura una chat? Quale è la dimensione ragionevole di un contesto per una AI? Posso recuperare intere chat del giorno prima a comando? Posso lierare spazio/contesto a comando?
- [ ] **Database SQLite e memoria:** Ottimizzazione storage per log conversazioni e metadati persistenti. Cosa salvo? Solo quello che dico io o anche quello che dice lui? Come impara cosa mi piace e cosa no delle sue risposte?
- [ ] **Questionario? Cheklist?:** Esiste un set di domande standard per arricchirlo? 
- [ ] **RAG (Il Diario):** Ricerca semantica nel DB per recupero contesto storico prima di rispondere (tifo Juvenus, mi piace il tennis, sono un fisico, sono sposato con due figli, ....). 
- [ ] **Dimenticatoio Selettivo (Decay):** Implementazione algoritmo di pulizia ricordi vecchi/inutili
- [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB
- [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine
