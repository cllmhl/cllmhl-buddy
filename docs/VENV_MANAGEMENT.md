# Gestione Ambienti Python

## 🎯 Problema

Buddy gira su due ambienti diversi:
- **GitHub Devspaces/Codespaces**: Python di sistema (nessun venv)
- **Raspberry Pi**: Virtual environment (venv) per isolamento dipendenze

## ✅ Soluzione Implementata

### Rilevamento Automatico

Gli script bash rilevano automaticamente l'ambiente usando variabili d'ambiente:

```bash
if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
    # Raspberry Pi → attiva venv
    source "$BUDDY_HOME/venv/bin/activate"
else
    # Devspaces → usa Python di sistema
fi
```

### Script Principali

| Script | Descrizione | Gestione venv |
|--------|-------------|---------------|
| [setup_buddy.sh](../scripts/setup_buddy.sh) | Setup iniziale ambiente | ✅ Crea venv su Raspberry |
| [run_buddy.sh](../scripts/run_buddy.sh) | Avvia Buddy principale | ✅ Attiva venv automaticamente |
| [run_hw_test.sh](../scripts/run_hw_test.sh) | Test hardware | ✅ Attiva venv automaticamente |
| [hwtest](../scripts/hwtest) | Alias veloce per hw test | ✅ Usa run_hw_test.sh |

## 🚀 Utilizzo

### Su Raspberry Pi (con venv)

```bash
# Setup iniziale (una volta sola)
bash scripts/setup_buddy.sh

# Esecuzione normale
bash scripts/run_buddy.sh

# Test hardware
bash scripts/run_hw_test.sh
bash scripts/hwtest led          # shortcut
bash scripts/hwtest radar
```

### In Devspaces (senza venv)

```bash
# Installazione dipendenze (già in devcontainer.json)
pip install -r requirements.txt

# Esecuzione diretta
python3 main.py

# Test hardware (N/A - manca hardware fisico)
```

## 🔍 Verifica Ambiente

Per vedere quale ambiente stai usando:

```bash
# Controlla variabili d'ambiente
echo "REMOTE_CONTAINERS: $REMOTE_CONTAINERS"
echo "CODESPACES: $CODESPACES"

# Controlla se venv è attivo
echo "VIRTUAL_ENV: $VIRTUAL_ENV"

# Path del Python in uso
which python3
```

Esempi di output:

**Raspberry Pi (venv attivo):**
```bash
REMOTE_CONTAINERS: 
CODESPACES: 
VIRTUAL_ENV: /home/cllmhl/cllmhl-buddy/venv
/home/cllmhl/cllmhl-buddy/venv/bin/python3
```

**Devspaces:**
```bash
REMOTE_CONTAINERS: true
CODESPACES: 
VIRTUAL_ENV: 
/usr/local/bin/python3
```

## ⚠️ Troubleshooting

### "ModuleNotFoundError" su Raspberry Pi

**Causa**: venv non attivo

**Soluzione**: Usa sempre gli script bash wrapper:
```bash
# ❌ NON fare
cd tests/hardware
python3 run_hardware_test.py

# ✅ Fare
bash scripts/run_hw_test.sh
```

### Conflitti di dipendenze

**Raspberry Pi**:
```bash
# Ricrea venv da zero
rm -rf venv/
bash scripts/setup_buddy.sh
```

**Devspaces**:
```bash
# Reinstalla dipendenze
pip install --force-reinstall -r requirements.txt
```

### Script non eseguibili

```bash
chmod +x scripts/*.sh
chmod +x scripts/hwtest
```

## 📝 Best Practices

1. **Non eseguire mai Python direttamente su Raspberry Pi** - usa sempre i wrapper bash
2. **Gli script Python non gestiscono venv** - è responsabilità dei wrapper bash
3. **Setup una tantum**: `setup_buddy.sh` crea il venv, poi tutti gli script lo riusano
4. **In Devspaces puoi eseguire Python direttamente** - nessun venv necessario

## 🏗️ Architettura

```
┌─────────────────────────────────────────┐
│     Utente esegue script bash           │
│     (run_buddy.sh / run_hw_test.sh)     │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│   Rileva ambiente                       │
│   $REMOTE_CONTAINERS / $CODESPACES      │
└─────────────────────────────────────────┘
          │                    │
          ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│ Raspberry Pi     │  │ Devspaces        │
│                  │  │                  │
│ source venv/bin/ │  │ (skip venv)      │
│   activate       │  │                  │
└──────────────────┘  └──────────────────┘
          │                    │
          └──────────┬─────────┘
                     ▼
          ┌──────────────────────┐
          │  python3 main.py     │
          │  o test specifico    │
          └──────────────────────┘
```

## 🔗 File Correlati

- [BUDDY_HOME.md](BUDDY_HOME.md) - Gestione path assoluti
- [../scripts/setup_buddy.sh](../scripts/setup_buddy.sh) - Setup ambiente
- [../scripts/run_buddy.sh](../scripts/run_buddy.sh) - Runner principale
- [../scripts/run_hw_test.sh](../scripts/run_hw_test.sh) - Test hardware
