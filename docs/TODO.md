# WBS - Work Breakdown Structure

## 1.0 CASA

### 1.1 Logica proattiva
- [ ] **Bentornato a casa:** capisce che entro in casa: Saluto ed inizio dialogo (dipendiamo dal sensore porta).

### 1.2 Integrazione Hardware
- [ ] **Sensore Luminosita:** Integrazione LDR (Luce): questo su GPIO non va perchè analogico. DObbiamo fare una catena. Mettiamo il sensore su arduino, colleghiamo arduino alla porta USB del Raspberry. Leggiamo dalla porta USB i dati di luminosità. In pratica la porta USB alimenta Arduino ed allo stesso tempo è un input di segnale di luce.
- [ ] **Sensore Porta:** Qui il giro e' un pochino lungo e si spendono 40 euro: 20 euro per il capo dei sensori ZigBee: "SONOFF ZigBee 3.0 USB Dongle Plus, TI CC2652P" e 20 euro per "Aqara Détecteur d'Ouverture Porte/Fenêtre"
- [ ] **Display 7-Segment (TM1637):** Visualizzazione codici stato (es. "Err", "On")
- [ ] **LED a piacere:** ci possiamo mettere tutti i led che vogliamo
- [ ] **Migliorare meccanismo di Feedback:** Sviluppo di un sistema per notificare l'utente sullo stato del sistema (es. tramite LED, display o notifiche vocali).
- [ ] **Active Buzzer:** Feedback acustici (Beep conferma, Alarm error) 

## 2.0 Ufficio

### 2.1 Long term Memory. Vedi context.png

#### 2.1.1 Raffinamento dell'Archivista (Ingestione Intelligente)
- [ ] **Prompt Engineering "Filtro Rumore"**: Modificare il System Prompt dell'Archivista. Istruirlo esplicitamente a ignorare: Dati effimeri (Meteo attuale, ora esatta, news del giorno). Chiacchiere di cortesia ("Ciao", "Come stai"). Output di sistema grezzi (log di errori, conferme di esecuzione comandi domotici standard).
- [ ] **Classificazione Tassonomica**: Definire categorie rigide per l'estrazione per aiutare il filtro (es. Preferenze Utente, Fatti Biografici, Configurazione Casa, Relazioni). Se non rientra in queste, viene scartato.

#### 2.1.2 Logica di Consolidamento (Deduplica e Rinforzo)
- [ ] **Query Pre-Inserimento (Check di Esistenza)**: Prima di salvare un nuovo fatto in ChromaDB, l'Archivista deve eseguire una ricerca vettoriale (similarity search) su ChromaDB con il fatto appena estratto.
- [ ] **Logica di Merge (Upsert)**: Se esiste un fatto simile (distanza < threshold): NON creare un nuovo record. Aggiornare il record esistente incrementando un campo reinforcement_count e aggiornando il timestamp last_accessed. Se il nuovo fatto aggiunge un dettaglio, arricchire il testo esistente. Se NON esiste: Creare il nuovo record in ChromaDB con reinforcement_count = 1

#### 2.1.3 Attivazione della Memoria (Retrieval & RAG)
- [ ] **Implementazione "Recall" (Smart Trigger)**: Prima di inviare il prompt dell'utente all'LLM principale (Chat): Vettorializzare l'ultima frase dell'utente. Query su ChromaDB per estrarre i "Fatti" più rilevanti (Top-K).
- [ ] **Context Injection**: Iniettare i fatti recuperati nel System Prompt della chat corrente (es. in una sezione [Context from Long Term Memory]).
- [ ] **Personalizzazione Dinamica**: Assicurarsi che le preferenze recuperate sovrascrivano i default generici.

#### 2.1.4 Il "Giardiniere" (Dimenticatoio Selettivo (Decay))
- [ ] **Job di Manutenzione Notturna**: Creare un processo che gira una volta al giorno (es. alle 04:00).
- [ ] **Algoritmo di Decay**:
Applicare una formula di decadimento all'importanza di ogni ricordo non rinforzato recentemente. Formula ipotetica: Nuova_Importanza = Importanza_Attuale * Fattore_Tempo. 
- [ ] **Pruning (Eliminazione)**: Se Importanza scende sotto una soglia minima (es. 0.2) AND reinforcement_count è basso -> Eliminare il record da ChromaDB. Eccezione: I "Core Memories" (fatti marcati come vitali o inseriti manualmente) non decadono mai.

#### 2.1.5 Final tuning
- [ ] **Questionario? Cheklist?:** Esiste un set di domande standard per arricchirlo? 
- [ ] **Sentiment Analysis:** Tracciamento umore dell'utente nel DB
- [ ] **Inside Jokes:** Evoluzione personalità basata sullo storico a lungo termine
