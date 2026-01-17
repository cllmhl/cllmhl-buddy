# Error Handling Policy - Fail-Fast Architecture

## Principi Fondamentali

### ❌ **NO Silent Failures**
Non mascherare MAI gli errori. Preferire il crash all'inconsistenza.

### ✅ **Fail-Fast**
Fallire immediatamente e rumorosamente appena si rileva un problema.

### 📊 **Full Diagnostics**
Includere sempre `exc_info=True` per stack trace completi.

---

## Pattern da EVITARE

### ❌ Bare `except:` con `pass`
```python
# SBAGLIATO - maschera TUTTI gli errori, anche KeyboardInterrupt
try:
    do_something()
except:
    pass
```

### ❌ Ritornare `None` silenziosamente
```python
# SBAGLIATO - l'errore viene perso
try:
    return create_important_object()
except Exception:
    return None  # Chi ha causato l'errore?
```

### ❌ Fallback senza logging
```python
# SBAGLIATO - comportamento ambiguo
if OutputChannel:
    return OutputChannel.VOICE
return "voice"  # Perché fallback? C'è un problema?
```

### ❌ Generic exception senza context
```python
# SBAGLIATO - informazioni insufficienti
except Exception as e:
    logger.error(f"Error: {e}")  # Dove? Perché? Stack trace?
```

---

## Pattern da USARE

### ✅ Import Required (No Fallback)
```python
# CORRETTO - fail immediatamente se manca
from core.events import OutputChannel, EventType

# CORRETTO per dipendenze hardware opzionali
try:
    import pvporcupine
    PICOVOICE_AVAILABLE = True
except ImportError as e:
    PICOVOICE_AVAILABLE = False
    logger.warning(f"⚠️ Picovoice not available: {e}")
    logger.warning("Wake word detection disabled")
```

### ✅ Fail-Fast su Errori Critici
```python
# CORRETTO - propaga l'errore
try:
    adapter = create_adapter(config)
except Exception as e:
    logger.error(
        f"❌ Adapter creation failed: {e}",
        exc_info=True  # ← Stack trace completo
    )
    raise RuntimeError("Adapter creation failed") from e  # ← Propaga
```

### ✅ Worker Loops con Gestione Specifica
```python
# CORRETTO - gestisce errori ma continua il worker
while self.running:
    try:
        event = self.queue.get(timeout=0.5)
        process_event(event)
        
    except Empty:
        continue  # Timeout normale
        
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        break  # Exit pulito
        
    except ValueError as e:
        # Errore recuperabile - logga e continua
        logger.warning(f"Invalid event data: {e}")
        continue
        
    except Exception as e:
        # Errore inaspettato - logga con stack trace
        logger.error(
            f"Unexpected error in worker: {e}",
            exc_info=True  # ← Diagnostics complete
        )
        # Continue - un errore non deve fermare il worker
```

### ✅ Cleanup con Gestione Errori
```python
# CORRETTO - gestisce errori specifici nel cleanup
def stop(self):
    self.running = False
    
    if self.hardware_device:
        try:
            self.hardware_device.close()
        except (AttributeError, RuntimeError) as e:
            # Device già chiuso o non inizializzato - OK
            logger.debug(f"Device close: {e}")
        except Exception as e:
            # Errore inaspettato nel cleanup
            logger.error(f"Error closing device: {e}", exc_info=True)
```

### ✅ Init Hardware Critico
```python
# CORRETTO - fail se hardware critico non funziona
def __init__(self, name: str, config: dict):
    super().__init__(name, config)
    
    try:
        # Hardware NECESSARIO per questo adapter
        self.critical_device = initialize_device()
    except Exception as e:
        logger.error(
            f"❌ Critical device initialization failed: {e}",
            exc_info=True
        )
        raise RuntimeError(
            f"LEDOutputPort requires working LEDs"
        ) from e
```

### ✅ Init Hardware Opzionale
```python
# CORRETTO - continua se hardware opzionale fallisce
def __init__(self, name: str, config: dict):
    super().__init__(name, config)
    
    # LED è OPZIONALE (solo visual feedback)
    self.status_led = None
    try:
        self.status_led = LED(pin)
        logger.info("✅ Status LED initialized")
    except Exception as e:
        logger.warning(
            f"⚠️ Status LED initialization failed: {e}"
        )
        logger.warning(
            "Continuing without status LED (non-critical)"
        )
```

---

## Classificazione Errori

### Critici (MUST Fail-Fast)
- Import di moduli core (`core.events`, `adapters.ports`)
- Creazione adapter fallita
- Hardware necessario non funzionante (LEDOutputPort senza LED)
- Configurazione invalida

**Action**: `raise` per fermare sistema immediatamente

### Recuperabili (Log + Continue)
- Errore processando singolo evento nel worker
- Lettura sensore singola fallita (DHT11 timeout)
- Comunicazione seriale temporaneamente interrotta

**Action**: Log errore, continua loop

### Previsti (Debug Log)
- Timeout su queue vuota (`Empty`)
- Device già chiuso nel cleanup
- Letture DHT11 fallite (normale)

**Action**: Debug log, continua

### Non Critici (Warning + Continue)
- Hardware opzionale non disponibile
- Dipendenze opzionali mancanti

**Action**: Warning log, disabilita feature

---

## Logging Levels

### `logger.debug()`
- Eventi normali ad alta frequenza
- Timeout previsti
- Cleanup di risorse già chiuse

### `logger.info()`
- Operazioni successful
- Worker started/stopped
- Stato sistema

### `logger.warning()`
- Feature disabilitate (hardware opzionale mancante)
- Comportamento degradato ma funzionante
- Configurazione subottimale

### `logger.error()`
- Errori che impediscono operazione
- Sempre con `exc_info=True` per stack trace
- Usare prima di `raise`

### `logger.critical()`
- Sistema non può continuare
- Corruzione dati
- Violazioni sicurezza

---

## Stack Trace Policy

### ✅ SEMPRE includere `exc_info=True` quando:
- `logger.error()` per qualsiasi Exception
- Errore inaspettato in worker loop
- Fallimento inizializzazione critica

```python
logger.error(f"Error: {e}", exc_info=True)  # ← SEMPRE
```

### ❌ MAI includere `exc_info` per:
- `logger.debug()` - troppo verboso
- Errori previsti e normali
- Warning su feature opzionali

---

## Testing

Ogni pattern fail-fast deve avere test che verificano:

1. **Errore viene propagato** (non swallowed)
2. **Stack trace è completo** (diagnostics)
3. **Messaggio è chiaro** (debugging)
4. **Nessun fallback silenzioso** (consistency)

Vedi: [tests/test_failfast.py](../tests/test_failfast.py)

---

## Checklist Code Review

Prima di merge, verificare:

- [ ] Nessun `except:` bare (specificare eccezioni)
- [ ] Nessun `except Exception: pass` silenzioso
- [ ] Ogni `logger.error()` ha `exc_info=True`
- [ ] Import critici senza fallback
- [ ] Factory propaga errori (no return None)
- [ ] Hardware critico fail-fast
- [ ] Worker loops gestiscono `KeyboardInterrupt`
- [ ] Test verificano fail-fast

---

## Esempi dal Codebase

### ✅ Ports.py
- Import diretto `from core.events import OutputChannel` (no try/except)
- Nessun fallback nelle property

### ✅ Factory.py
- `raise RuntimeError` invece di `return None`
- `exc_info=True` su tutti gli errori

### ✅ LED Output
- Fail-fast se LEDs non disponibili (hardware critico)

### ✅ Voice Output
- Warning se status LED fallisce (hardware opzionale)

### ✅ Worker Loops
- Gestione specifica: `Empty`, `KeyboardInterrupt`, `Exception`
- Stack trace completi su errori inaspettati
