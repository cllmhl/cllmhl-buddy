# BUDDY_HOME - Gestione Path Assoluti

## Problema

Quando Buddy viene lanciato da:
- Un servizio systemd
- Uno script esterno
- Una directory diversa da quella del progetto

I **path relativi** (come `config/adapter_config_dev.yaml`, `buddy_system.log`) causano errori perché vengono risolti rispetto alla directory di lavoro corrente, non alla directory del progetto.

## Soluzione: BUDDY_HOME

Buddy ora usa la variabile `BUDDY_HOME` per risolvere tutti i path in modo assoluto, indipendentemente da dove viene lanciato.

### Come Funziona

1. **Auto-detection**: Se `BUDDY_HOME` NON è impostato, viene automaticamente rilevato come la directory parent del file `config_loader.py`

2. **Manual override**: Puoi impostare esplicitamente `BUDDY_HOME` per sovrascrivere l'auto-detection

3. **Path resolution**: Tutti i path relativi vengono risolti rispetto a `BUDDY_HOME`

### Configurazione

#### 1. File .env (sviluppo locale)

```bash
# Opzionale - se non impostato viene auto-rilevato
BUDDY_HOME=/workspaces/cllmhl-buddy

# Obbligatorio
BUDDY_CONFIG=config/adapter_config_dev.yaml
GOOGLE_API_KEY=your_api_key_here
```

#### 2. Servizio systemd (produzione)

```ini
[Service]
Environment="BUDDY_HOME=/home/cllmhl/cllmhl-buddy"
Environment="BUDDY_CONFIG=config/adapter_config_prod.yaml"
WorkingDirectory=/home/cllmhl/cllmhl-buddy
ExecStart=/home/cllmhl/cllmhl-buddy/venv/bin/python3 /home/cllmhl/cllmhl-buddy/main_new.py
```

#### 3. Script bash

```bash
#!/bin/bash
# Imposta BUDDY_HOME
export BUDDY_HOME="/home/cllmhl/cllmhl-buddy"
export BUDDY_CONFIG="config/adapter_config_prod.yaml"

# Lancia Buddy (NON serve cd nella directory)
$BUDDY_HOME/venv/bin/python3 $BUDDY_HOME/main_new.py
```

### Esempi d'Uso

#### Sviluppo in DevContainer/Codespaces

```bash
# Auto-detection - funziona ovunque tu sia
cd /tmp
python3 /workspaces/cllmhl-buddy/main_new.py
```

#### Produzione su Raspberry Pi

```bash
# Script helper che imposta BUDDY_HOME
bash /home/cllmhl/cllmhl-buddy/scripts/run_buddy.sh

# Oppure manualmente
export BUDDY_HOME=/home/cllmhl/cllmhl-buddy
export BUDDY_CONFIG=config/adapter_config_prod.yaml
python3 $BUDDY_HOME/main_new.py
```

#### Servizio systemd

```bash
sudo systemctl start buddy
# Il servizio ha BUDDY_HOME impostato in buddy.service
```

### File che Usano BUDDY_HOME

- **config/config_loader.py**: 
  - `get_buddy_home()` - Ottiene BUDDY_HOME
  - `resolve_path()` - Risolve path relativi
  
- **main_new.py**: 
  - Usa `get_buddy_home()` per logging
  - Risolve tutti i path di configurazione
  
- **scripts/run_buddy.sh**: 
  - Imposta automaticamente `BUDDY_HOME`
  - Carica `.env` con path corretto

### Path Risolti Automaticamente

✅ Questi path sono ora **sempre assoluti**:

- `BUDDY_CONFIG` (es. `config/adapter_config_dev.yaml`)
- Log file (`buddy_system.log`)
- Memory store (`buddy_memory/`)
- Models (`models/Ei-Buddy_*.ppn`)
- Tutti i file di configurazione

### Vantaggi

✅ **Portabilità**: Lancia Buddy da qualsiasi directory  
✅ **Servizi**: Funziona con systemd senza problemi  
✅ **Scripts**: Nessun `cd` obbligatorio  
✅ **Auto-detection**: Funziona out-of-the-box senza configurazione  
✅ **Override**: Puoi forzare una directory specifica se necessario

### Debugging

Se hai problemi con i path:

```bash
# Verifica BUDDY_HOME rilevato
python3 -c "from config.config_loader import get_buddy_home; print(get_buddy_home())"

# Verifica risoluzione path
python3 -c "from config.config_loader import resolve_path; print(resolve_path('config/adapter_config_dev.yaml'))"

# Log mostra sempre BUDDY_HOME all'avvio
python3 main_new.py
# Output: 🏠 BUDDY_HOME: /workspaces/cllmhl-buddy
```

### Migration Checklist

Per aggiornare codice esistente:

- [ ] Usa `resolve_path()` per path relativi
- [ ] Testa lancio da directory diverse
- [ ] Aggiorna script con `BUDDY_HOME`
- [ ] Aggiorna servizi systemd
- [ ] Documenta path richiesti
