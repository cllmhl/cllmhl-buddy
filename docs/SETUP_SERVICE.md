# 🚀 Buddy Service - Guida Setup Systemd

Questa guida spiega come configurare Buddy per l'esecuzione in background come servizio systemd sul Raspberry Pi.

## 📋 Prerequisiti

- Buddy funzionante (testato con `python3 main.py`)
- Accesso SSH al Raspberry Pi
- Permessi sudo

## ⚙️ Installazione

### 1. Verifica i percorsi nel file `buddy.service`

Apri `buddy.service` e controlla che i percorsi siano corretti:

```bash
nano buddy.service
```

Verifica:
- `User=cllmhl` → il tuo username sul Raspberry Pi
- `Group=cllmhl` → il tuo gruppo (di solito uguale allo username)
- `WorkingDirectory=/home/cllmhl/cllmhl-buddy` → percorso del progetto
- `ExecStart=/home/cllmhl/cllmhl-buddy/venv/bin/python3 ...` → percorso del venv

### 2. Installa il servizio

Esegui lo script di installazione:

```bash
sudo bash install_service.sh
```

Lo script:
- Copia `buddy.service` in `/etc/systemd/system/`
- Ricarica i daemon systemd
- Abilita Buddy per l'avvio automatico

### 3. Avvia Buddy

```bash
sudo systemctl start buddy
```

### 4. Verifica che funzioni

```bash
sudo systemctl status buddy
```

Dovresti vedere:
```
● buddy.service - Buddy - AI Voice Assistant
   Loaded: loaded (/etc/systemd/system/buddy.service; enabled)
   Active: active (running) since ...
```

## 📊 Comandi Utili

### Gestione Servizio

```bash
# Avvia Buddy
sudo systemctl start buddy

# Ferma Buddy
sudo systemctl stop buddy

# Riavvia Buddy
sudo systemctl restart buddy

# Stato del servizio
sudo systemctl status buddy

# Disabilita avvio automatico
sudo systemctl disable buddy

# Riabilita avvio automatico
sudo systemctl enable buddy
```

### Visualizzazione Log

```bash
# Log in tempo reale (come 'tail -f')
journalctl -u buddy -f

# Ultimi 50 log
journalctl -u buddy -n 50

# Log di oggi
journalctl -u buddy --since today

# Log con timestamp specifico
journalctl -u buddy --since "2026-01-13 20:00:00"

# Esporta log in file
journalctl -u buddy > buddy_logs.txt
```

## 🔧 Risoluzione Problemi

### Il servizio non parte

1. **Controlla lo status dettagliato:**
   ```bash
   sudo systemctl status buddy -l
   ```

2. **Verifica i permessi:**
   ```bash
   ls -la /home/cllmhl/cllmhl-buddy/main.py
   ls -la /home/cllmhl/cllmhl-buddy/venv/bin/python3
   ```

3. **Testa l'esecuzione manuale:**
   ```bash
   cd /home/cllmhl/cllmhl-buddy
   ./venv/bin/python3 main.py
   ```

### Errori di audio/GPIO

Il servizio include i gruppi supplementari `audio`, `gpio`, e `dialout`. Verifica che l'utente `cllmhl` appartenga a questi gruppi:

```bash
groups cllmhl
```

Se mancano, aggiungili:

```bash
sudo usermod -aG audio,gpio,dialout cllmhl
```

### Modifiche al servizio

Dopo aver modificato `config/buddy.service`:

```bash
sudo cp config/buddy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart buddy
```

## 🧪 Testing Dopo l'Installazione

1. **Riavvia il Raspberry Pi:**
   ```bash
   sudo reboot
   ```

2. **Dopo il riavvio, verifica che Buddy sia partito automaticamente:**
   ```bash
   sudo systemctl status buddy
   ```

3. **Prova a dire "Ehi Buddy"** e verifica che risponda.

4. **Controlla i log:**
   ```bash
   journalctl -u buddy -n 100
   ```

## 📝 Note Importanti

- **File log:** Il servizio scrive su `journalctl` (systemd logs) E sul file `buddy_system.log` nella directory del progetto
- **Auto-restart:** Se Buddy crasha, systemd lo riavvierà automaticamente dopo 10 secondi
- **Input tastiera:** Con Buddy in background, l'input da terminale NON funzionerà. Questo sarà risolto nella prossima fase con le Named Pipes (FIFO)

## 🎯 Prossimi Passi

Dopo aver verificato che il servizio funzioni, il prossimo step è:

- **Named Pipe (FIFO):** Per inviare comandi testuali a Buddy anche quando gira in background

---

🤖 **Buddy è ora un vero servizio di sistema!**
