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

### 1. Setup Ambiente

**Prima esecuzione** - Imposta le variabili d'ambiente obbligatorie:

```bash
# Aggiungi al tuo ~/.bashrc o ~/.profile
export BUDDY_HOME=/home/cllmhl/cllmhl-buddy  # Path assoluto al progetto
export BUDDY_CONFIG=config/dev.yaml          # Config da usare

# Ricarica
source ~/.bashrc
```

> **IMPORTANTE**: `BUDDY_HOME` e `BUDDY_CONFIG` sono **OBBLIGATORI**. Gli script falliscono se non sono settati. Vedi [docs/ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md) per dettagli.

### 2. Installazione Dipendenze

```bash
bash scripts/setup_buddy.sh
```

> **Nota**: Lo script rileva automaticamente l'ambiente:
> - **Raspberry Pi**: Crea e usa `venv` (ambiente virtuale Python)
> - **Devspaces/Container**: Usa Python di sistema

### 3. Esecuzione

**Buddy principale:**
```bash
bash scripts/run_buddy.sh
```

**Test hardware (solo Raspberry Pi):**
```bash
bash scripts/run_hw_test.sh              # Test completo
bash scripts/run_hw_test.sh led          # Test LED
bash scripts/run_hw_test.sh radar        # Test radar
bash scripts/run_hw_test.sh temperature  # Test temperatura
```

**Come servizio systemd (solo Raspberry Pi):**
```bash
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

- **[Setup Ambiente](docs/ENVIRONMENT_SETUP.md)** - Come settare BUDDY_HOME e BUDDY_CONFIG
- [Gestione Ambienti Python (venv)](docs/VENV_MANAGEMENT.md) - Raspberry Pi vs Devspaces
- [Guida Servizio Systemd](docs/SETUP_SERVICE.md)
- [Guida Named Pipe](docs/PIPE_USAGE.md)
- [TODO e Roadmap](TODO.md)
