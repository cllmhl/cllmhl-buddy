# 🔧 Named Pipe (FIFO) - Guida all'uso

Buddy ora utilizza una **Named Pipe** (FIFO) per ricevere comandi testuali, permettendo l'interazione anche quando gira come servizio in background.

## 📍 Percorso Pipe

```
/tmp/buddy_pipe
```

## 🚀 Modi per Inviare Comandi

### 1. Script Helper (Modo Più Semplice)

```bash
# Invia un singolo comando
./scripts/buddy_cmd.sh "che ore sono?"

# Modalità interattiva (multipli comandi)
./scripts/buddy_cmd.sh
```

### 2. Echo diretto

```bash
echo "dimmi una barzelletta" > /tmp/buddy_pipe
```

### 3. Printf (per messaggi multilinea)

```bash
printf "racconta una storia\nlunga e interessante\n" > /tmp/buddy_pipe
```

### 4. Da Script o Programmi

```python
# Python
with open("/tmp/buddy_pipe", "w") as pipe:
    pipe.write("temperatura della stanza\n")
```

```bash
# Bash script
#!/bin/bash
TEMP=$(sensors | grep "temp1" | awk '{print $2}')
echo "la temperatura è $TEMP" > /tmp/buddy_pipe
```

## 🎯 Esempi Pratici

### Comando da SSH

```bash
ssh raspberry "echo 'accendi le luci del soggiorno' > /tmp/buddy_pipe"
```

### Integrazione con Cron

```bash
# Ogni mattina alle 7:00
0 7 * * * echo "buongiorno, che tempo fa oggi?" > /tmp/buddy_pipe

# Ogni sera alle 22:00
0 22 * * * echo "spegni tutte le luci" > /tmp/buddy_pipe
```

### Trigger da Sensori

```bash
#!/bin/bash
# Script che gira continuamente e monitora un sensore

while true; do
    MOTION=$(read_pir_sensor)
    if [ "$MOTION" == "1" ]; then
        echo "ho rilevato movimento" > /tmp/buddy_pipe
        sleep 300  # Aspetta 5 minuti prima di ricontrollare
    fi
    sleep 1
done
```

### Comando Rapido da Alias

Aggiungi al tuo `~/.bashrc`:

```bash
alias buddy='bash /home/cllmhl/cllmhl-buddy/scripts/buddy_cmd.sh'
```

Poi:

```bash
buddy "che ore sono?"
```

## 🔍 Verifica che la Pipe Funzioni

### 1. Controlla che la pipe esista

```bash
ls -l /tmp/buddy_pipe
```

Output atteso:
```
prw-rw-rw- 1 cllmhl cllmhl 0 Jan 13 21:00 /tmp/buddy_pipe
```

La `p` iniziale indica che è una pipe.

### 2. Testa l'invio di un comando

```bash
echo "ciao Buddy" > /tmp/buddy_pipe
```

### 3. Verifica nei log

```bash
# Se Buddy gira in foreground
tail -f buddy_system.log

# Se gira come servizio
journalctl -u buddy -f
```

Dovresti vedere:
```
INFO - PipeThread - Comando ricevuto da pipe: ciao Buddy
```

## ⚠️ Risoluzione Problemi

### "No such file or directory"

La pipe non esiste. Verifica che Buddy sia in esecuzione:

```bash
# Se gira come servizio
sudo systemctl status buddy

# Se gira in foreground
ps aux | grep main.py
```

### "Broken pipe"

Buddy ha smesso di leggere dalla pipe. Riavvia Buddy.

### Permessi negati

```bash
# Verifica i permessi
ls -l /tmp/buddy_pipe

# Se necessario, ricreali (da eseguire come user che fa girare Buddy)
rm /tmp/buddy_pipe
# Buddy ricreerà la pipe al prossimo avvio
```

## 🎓 Come Funziona Tecnicamente

1. **Buddy crea la pipe** all'avvio con `os.mkfifo()`
2. **Thread dedicato** legge continuamente dalla pipe (bloccante)
3. **Quando scrivi sulla pipe**, il thread si sblocca e legge il contenuto
4. **Il messaggio diventa un evento** che viene processato come un input vocale

### Differenze con input standard

| Feature | Input Standard | Named Pipe |
|---------|---------------|------------|
| Funziona come servizio | ❌ No | ✅ Sì |
| Accessibile da SSH | ❌ No | ✅ Sì |
| Chiamabile da script | ❌ Difficile | ✅ Facile |
| Multipli processi | ❌ No | ✅ Sì |

## 🔮 Prossimi Miglioramenti

- [ ] **Pipe bidirezionale:** Buddy risponde sulla pipe `/tmp/buddy_reply`
- [ ] **Formato JSON:** Supporto per comandi strutturati con metadata
- [ ] **Autenticazione:** Token per comandi da fonti esterne
- [ ] **Rate limiting:** Prevenzione spam

---

🤖 **Buddy è ora controllabile da qualsiasi parte del sistema!**
