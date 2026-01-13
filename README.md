# cllmhl-buddy
This ia Michele Alter Ego Assistant Project

## 📁 Struttura Progetto

```
cllmhl-buddy/
├── scripts/              # Script di setup e utility
│   ├── buddy_cmd.sh      # Helper per inviare comandi via pipe
│   ├── install_service.sh # Installazione servizio systemd
│   ├── setup_buddy.sh    # Setup iniziale ambiente
│   └── run_buddy.sh      # Avvio rapido
├── config/               # File di configurazione
│   └── buddy.service     # Definizione servizio systemd
├── docs/                 # Documentazione tecnica
│   ├── SETUP_SERVICE.md  # Guida servizio systemd
│   └── PIPE_USAGE.md     # Guida Named Pipe (FIFO)
├── main.py               # Ciclo principale e orchestrazione
├── brain.py              # Logica Gemini e personalità
├── io_buddy.py           # Gestione audio (Ears/Voice)
├── database_buddy.py     # Gestione SQLite e memoria
├── archivist.py          # Sistema RAG e archiviazione
├── .env                  # (NON caricare su GitHub) Chiavi API
├── config.env            # Configurazione opzioni Buddy
└── requirements.txt      # Librerie Python necessarie
```

## 🚀 Quick Start

### Installazione
```bash
bash scripts/setup_buddy.sh
```

### Esecuzione
```bash
# Modalità interattiva
python3 main.py

# Come servizio systemd (solo su Raspberry Pi)
sudo bash scripts/install_service.sh
sudo systemctl start buddy
```

### Invio Comandi
```bash
# Da tastiera (se interattivo)
# Scrivi direttamente nel terminale

# Da Named Pipe
echo "ciao Buddy" > /tmp/buddy_pipe
# O usa lo script helper
./scripts/buddy_cmd.sh "che ore sono?"
```

## 📚 Documentazione

- [Guida Servizio Systemd](docs/SETUP_SERVICE.md)
- [Guida Named Pipe](docs/PIPE_USAGE.md)
- [TODO e Roadmap](TODO.md)
