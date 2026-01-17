# Test Hardware Output - Guida Completa

## 🎯 Filosofia

I test output mantengono **la stessa filosofia dei test input**:
- ✅ Configurazione YAML dedicata
- ✅ Esecuzione tramite `main.py`
- ✅ Brain che processa eventi (unwrap DIRECT_OUTPUT)
- ✅ Output adapter reali testati

## 📦 Architettura

### Test Input (esistenti)
```
Hardware Sensore → Input Adapter → Events → Brain → ConsoleOutput
     (radar)        (RadarInput)              ↓         (visualizza)
                                         (elabora)
```

### Test Output (nuovi)
```
DirectOutputInput → DIRECT_OUTPUT → Brain → GPIOLEDOutput → Hardware LED
     ↓                               ↓            ↑
(genera eventi)                (unwrap)    (testa reale)
```

## 🔧 DirectOutputInput Adapter

Adapter configurabile che genera eventi `DIRECT_OUTPUT` da YAML.

### Modalità Supportate

#### 1. Interactive Mode
Menu interattivo per test manuali:
```yaml
adapters:
  input:
    - class: "DirectOutputInput"
      config:
        mode: "interactive"
```

#### 2. Sequence Mode
Sequenza automatica (esegue e termina):
```yaml
adapters:
  input:
    - class: "DirectOutputInput"
      config:
        mode: "sequence"
        sequence:
          - type: "LED_ON"
            metadata: {led: "ascolto"}
            delay: 2.0
          
          - type: "LED_OFF"
            metadata: {led: "ascolto"}
            delay: 1.0
```

#### 3. Loop Mode
Ripete sequenza continuamente:
```yaml
adapters:
  input:
    - class: "DirectOutputInput"
      config:
        mode: "loop"
        loop_delay: 5.0      # Pausa tra iterazioni
        loop_count: 10       # Numero iterazioni (null = infinito)
        sequence:
          - type: "LED_BLINK"
            metadata: {led: "stato", times: 3}
```

## 📋 Test Disponibili

### 1. Test LED Interactive

**File:** `run_led_test.py`  
**Config:** `config/led_test.yaml`

```bash
cd tests/hardware
python3 run_led_test.py
```

**Menu interattivo:**
```
1) LED ascolto ON
2) LED ascolto OFF
3) LED stato ON
4) LED stato OFF
5) LED blink ascolto (3x)
6) LED blink stato (5x)
q) Quit
```

**Verifica:**
- [ ] LED blu (GPIO 26) risponde ai comandi
- [ ] LED verde (GPIO 21) risponde ai comandi
- [ ] Blink conta corretta
- [ ] Console mostra eventi

---

### 2. Test LED Automatico

**File:** `run_led_test_auto.py`  
**Config:** `config/led_test_auto.yaml`

```bash
cd tests/hardware
python3 run_led_test_auto.py
```

**Sequenza automatica:**
1. LED ascolto ON (2s)
2. LED ascolto OFF (1s)
3. LED stato ON (2s)
4. LED stato OFF (1s)
5. Blink ascolto 3x
6. Blink stato 5x

**Verifica:**
- [ ] Sequenza eseguita completamente
- [ ] Timing corretto
- [ ] Nessun errore GPIO

---

### 3. Test Voice Output Interactive

**File:** `run_voice_output_test.py`  
**Config:** `config/voice_output_test.yaml`

```bash
cd tests/hardware
python3 run_voice_output_test.py
```

**Menu interattivo:**
```
1) LED ascolto ON
2) LED ascolto OFF
...
7) TTS test
8) TTS custom
q) Quit
```

**Verifica:**
- [ ] Audio chiaro e comprensibile
- [ ] Pronuncia italiana corretta
- [ ] LED verde lampeggia durante TTS
- [ ] Volume appropriato

## 🔄 Flusso Completo

### Esempio: Test LED ON

1. **DirectOutputInput** (da config):
   ```yaml
   sequence:
     - type: "LED_ON"
       metadata: {led: "ascolto"}
   ```

2. **Genera evento wrapper**:
   ```python
   inner = Event(type=LED_ON, metadata={'led': 'ascolto'})
   wrapper = Event(type=DIRECT_OUTPUT, content=inner)
   ```

3. **Input Queue** riceve wrapper

4. **Brain** processa:
   ```python
   if event.type == DIRECT_OUTPUT:
       return [event.content]  # Unwrap
   ```

5. **Output Queue** riceve `LED_ON`

6. **Router** smista a `GPIOLEDOutput`

7. **GPIOLEDOutput** accende LED fisico

8. **ConsoleOutput** mostra evento

## 🆚 Confronto Test Input vs Output

| Aspetto | Test Input | Test Output |
|---------|------------|-------------|
| **Config** | `radar_test.yaml` | `led_test.yaml` |
| **Input Adapter** | RadarInput (hardware) | DirectOutputInput (config) |
| **Eventi Generati** | SENSOR_* | DIRECT_OUTPUT(LED_*) |
| **Brain** | Elabora sensori | Unwrap DIRECT_OUTPUT |
| **Output Adapter** | ConsoleOutput (visualizza) | GPIOLEDOutput (hardware) |
| **Verifica** | Leggi console | Osserva hardware |
| **Modalità** | Passiva (ascolto) | Attiva (comando) |

## ✅ Vantaggi Architettura

### Coerenza
- Stessa struttura test input/output
- Stessa filosofia: config + script + main.py
- Pattern ripetibile

### Flessibilità
- **Interactive**: test manuali esplorativi
- **Sequence**: test automatici CI/CD
- **Loop**: stress test, demo

### Manutenibilità
- Sequenze in YAML (no codice hardcoded)
- Facile aggiungere nuovi test
- Configurazione dichiarativa

### Realismo
- Usa Brain reale (unwrap DIRECT_OUTPUT)
- Usa Router reale
- Usa Output adapter di produzione
- Confidence alta che il sistema funziona

## 🛠️ Configurazione Sequenza

### Formato Evento
```yaml
- type: "LED_ON"              # EventType name (required)
  content: null               # Event content (optional)
  metadata: {led: "ascolto"}  # Event metadata (optional)
  priority: "HIGH"            # EventPriority name (optional, default: HIGH)
  delay: 2.0                  # Delay dopo evento in secondi (optional)
```

### Esempi

**LED:**
```yaml
sequence:
  - type: "LED_ON"
    metadata: {led: "ascolto"}
    delay: 2.0
  
  - type: "LED_BLINK"
    metadata: {led: "stato", times: 5}
    delay: 3.0
```

**TTS:**
```yaml
sequence:
  - type: "SPEAK"
    content: "Ciao, questo è un test"
    delay: 5.0
  
  - type: "SPEAK"
    content: "Test completato"
    delay: 0
```

**Mix:**
```yaml
sequence:
  - type: "LED_ON"
    metadata: {led: "ascolto"}
  
  - type: "SPEAK"
    content: "LED acceso"
    delay: 3.0
  
  - type: "LED_OFF"
    metadata: {led: "ascolto"}
```

## 📊 Esempi d'Uso

### Test Manuale Esplorativo
```bash
# Interactive mode
python3 run_led_test.py
# Scegli comandi dal menu
```

### Test Automatico CI/CD
```bash
# Sequence mode
python3 run_led_test_auto.py
# Esegue sequenza e esce
echo $?  # 0 = success
```

### Demo Loop
```yaml
# config/led_demo.yaml
input:
  - class: "DirectOutputInput"
    config:
      mode: "loop"
      loop_delay: 3.0
      sequence:
        - type: "LED_BLINK"
          metadata: {led: "ascolto", times: 2}
        - type: "LED_BLINK"
          metadata: {led: "stato", times: 2}
```

### Stress Test
```yaml
# config/led_stress.yaml
input:
  - class: "DirectOutputInput"
    config:
      mode: "loop"
      loop_count: 100
      loop_delay: 0.5
      sequence:
        - type: "LED_ON"
          metadata: {led: "ascolto"}
          delay: 0.1
        - type: "LED_OFF"
          metadata: {led: "ascolto"}
          delay: 0.1
```

## 🔍 Troubleshooting

### LED non si accendono
```bash
# Verifica GPIO
python3 -c "from gpiozero import LED; LED(26).on()"

# Verifica adapter registrato
python3 -c "from adapters.factory import AdapterFactory; print(AdapterFactory.get_registered_classes())"

# Controlla log
tail -f logs/led_test.log
```

### DirectOutputInput non trovato
```bash
# Verifica import
python3 -c "from adapters.input import DirectOutputInput; print('OK')"

# Verifica registrazione
python3 -c "from adapters.factory import AdapterFactory; print('DirectOutputInput' in AdapterFactory.get_registered_classes()['input'])"
```

### Sequenza non eseguita
```bash
# Verifica config YAML
python3 -c "import yaml; print(yaml.safe_load(open('config/led_test_auto.yaml')))"

# Verifica mode
grep "mode:" config/led_test_auto.yaml
```

## 🎓 Best Practices

### ✅ Fare
- Usare **interactive** per test manuali
- Usare **sequence** per test automatici
- Usare **loop** per demo/stress
- Specificare `delay` tra eventi
- Verificare log dopo test

### ❌ Non fare
- Non mettere delay troppo brevi (< 0.1s)
- Non fare loop infiniti senza modo di uscire
- Non ignorare errori nei log
- Non testare LED e Voice insieme (conflitti risorse)

## 🚀 Workflow Tipico

1. **Setup:**
   ```bash
   cd tests/hardware
   ```

2. **Test Interactive (esplorazione):**
   ```bash
   python3 run_led_test.py
   # Prova vari comandi manualmente
   ```

3. **Crea sequenza automatica:**
   ```yaml
   # Aggiungi ai config/led_test_auto.yaml
   ```

4. **Test automatico (CI):**
   ```bash
   python3 run_led_test_auto.py
   # Valida che passa
   ```

5. **Verifica log:**
   ```bash
   tail -f logs/led_test.log
   grep "ERROR" logs/led_test.log
   ```

## 📚 Riferimenti

- [DIRECT_OUTPUT Pattern](../../docs/DIRECT_OUTPUT_PATTERN.md) - Pattern tecnico
- [Event System](../../docs/EVENT_SYSTEM.md) - Sistema eventi
- [Hardware Test README](./README.md) - Overview test hardware
