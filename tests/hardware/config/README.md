# Hardware Test Configurations

Questa directory contiene le configurazioni YAML per i test hardware.

## 📁 Struttura

```
tests/hardware/config/
├── hardware_test.yaml          # Test integrazione completa (tutti i componenti)
├── led_test.yaml               # Test LED interattivo
├── led_test_auto.yaml          # Test LED automatico (sequenza)
├── led_test_mock.yaml          # Test LED mock (senza GPIO)
├── radar_test.yaml             # Test sensore presenza (LD2410C)
├── temperature_test.yaml       # Test temperatura/umidità (DHT11)
├── voice_test.yaml             # Test input vocale (Jabra + Porcupine)
└── voice_output_test.yaml      # Test output vocale (TTS + Jabra)
```

## 🎯 Utilizzo

Ogni configurazione è usata dal corrispondente script in `tests/hardware/`:

```bash
# Test LED interattivo
python3 tests/hardware/run_led_test.py
# Usa: tests/hardware/config/led_test.yaml

# Test radar
python3 tests/hardware/run_radar_test.py
# Usa: tests/hardware/config/radar_test.yaml
```

## 📝 Formato

Tutte le configurazioni seguono lo stesso formato:

```yaml
buddy_home: ${BUDDY_HOME:-.}

brain:
  model_id: "gemini-2.0-flash-exp"
  # ...

adapters:
  input:
    - class: "AdapterClass"
      config:
        # adapter-specific config
  
  output:
    - class: "OutputClass"
      config:
        # adapter-specific config
```

## 🔍 Differenze con config/ principale

- **`config/`** → Configurazioni di produzione/deployment (dev.yaml, prod.yaml)
- **`tests/hardware/config/`** → Configurazioni per test hardware isolati

Questa separazione mantiene pulita la directory di configurazione principale e raggruppa i test con le loro configurazioni.
