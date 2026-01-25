# WBS - Work Breakdown Structure

## 1.0 CASA

### 1.2 Logica proattiva
- [ ] **Bentornato a casa:** capisce che entro in casa: Saluto ed inizio dialogo.

### 1.3 Integrazione Hardware
- [ ] **Domotica Tapo:** Integrazione luci e prese smart tramite API
- [ ] **Sensore Luminosita:** Integrazione LDR (Luce): questo su GPIO non va perchè analogico. DObbiamo fare una catena. Mettiamo il sensore su arduino, colleghiamo arduino alla porta USB del Raspberry. Leggiamo dalla porta USB i dati di luminosità. In pratica la porta USB alimenta Arduino ed allo stesso tempo è un input di segnale di luce.
- [ ] **Display 7-Segment (TM1637):** Visualizzazione codici stato (es. "Err", "On")
- [ ] **LED a piacere:** ci possiamo mettere tutti i led che vogliamo
- [ ] **Migliorare meccanismo di Feedback:** Sviluppo di un sistema per notificare l'utente sullo stato del sistema (es. tramite LED, display o notifiche vocali).
- [ ] **Active Buzzer:** Feedback acustici (Beep conferma, Alarm error) 

## 2.0 Ufficio

### 2.1 Action tools. Vedi context.png
- [ ] **web_search:** Buddy cerca in rete con Tavily
- [ ] **get_current_time:** Buddy deve sempre avere chiaro che ora è.
- [ ] **get_current_temp:** Buddy deve sempre avere chiaro temperatura ed umidità.
- [ ] **get_current_position:** Buddy deve sempre avere chiaro dove è.
- [ ] **get_presence_events:** Buddy deve sapere gli ultimi eventi di presenza/assenza per decidere se parlare, spegnere le luci, ... 
- [ ] **set_lights_off:** Buddy spegne le luci
- [ ] **set_lights_on:** Buddy accende le luci
- [ ] **weather_forecast:** Buddy mi dice le previsioni usando Open-Meteo
- [ ] **local_newst:** Buddy mi dice notizie (Glebali, Locali, ..) usando degli RSS feeds
- [ ] **sport_newst:** Verificare come fare...
- [ ] **wikipedia:** Buddy cerca definizioni, storia e biografie su Wikipedia.
- [ ] **mail:** Buddy accede alle mie mail e se sono in casa me la legge.
- [ ] **calendar:** Buddy accede al mio calendar e mi ricorda delle cose.

### 2.1 Log term Memory. Vedi context.png
- [ ] **Come funziona Buddy:** Come funziona il gioco? quanto dura una chat? Quale è la dimensione ragionevole di un contesto per una AI? Posso recuperare intere chat del giorno prima a comando? Posso lierare spazio/contesto a comando?
- [ ] **Database SQLite e memoria:** Ottimizzazione storage per log conversazioni e metadati persistenti. Cosa salvo? Solo quello che dico io o anche quello che dice lui? Come impara cosa mi piace e cosa no delle sue risposte?
- [ ] **Questionario? Cheklist?:** Esiste un set di domande standard per arricchirlo? 
- [ ] **RAG (Il Diario):** Ricerca semantica nel DB per recupero contesto storico prima di rispondere (tifo Juvenus, mi piace il tennis, sono un fisico, sono sposato con due figli, ....). 
- [ ] **Dimenticatoio Selettivo (Decay):** Implementazione algoritmo di pulizia ricordi vecchi/inutili
- [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB
- [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine
