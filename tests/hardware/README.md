# Test Hardware Buddy

Test degli adapter **REALI** con hardware fisico del Raspberry Pi 5.

## 🎯 Obiettivo

Verificare che tutti i componenti hardware funzionino correttamente usando gli **adapter di produzione** con configurazione dedicata (`adapter_config_hardware_test.yaml`).

Invece di test scollegati, questo approccio:
- ✅ Testa il **codice di produzione** (gli adapter reali)
- ✅ Verifica **l'integrazione completa** (routing, orchestrazione, brain)
- ✅ Usa **configurazione YAML** come in produzione
- ✅ Zero duplicazione di codice

## 🚀 Esecuzione

```bash
cd tests/hardware
python3 run_hardware_test.py
```

Il sistema si avvierà con:
- **Console Output** che mostra tutti gli eventi in tempo reale
- Tutti gli adapter input/output hardware attivi
- Brain che risponde alle domande

## ✅ Checklist Verifiche

### 🎤 Audio (Jabra 410)
- [ ] Dì "Ei Buddy" → LED BLU si accende
- [ ] Parla in italiano → STT riconosce correttamente
- [ ] Console mostra: `🎤 Utente: [tuo messaggio]`
- [ ] Buddy risponde con voce italiana chiara
- [ ] LED VERDE si accende durante la risposta vocale
- [ ] Console mostra: `🔊 Buddy: [risposta]`

### 📡 Sensori

**Radar LD2410C:**
- [ ] Console mostra `👤 Presenza: ASSENTE` quando nessuno c'è
- [ ] Avvicina la mano → `👤 Presenza: PRESENTE`
- [ ] Muovi la mano → verifica `mov_energy` in verbose mode

**DHT11 (Temperatura/Umidità):**
- [ ] Console mostra `🌡️ Temperatura: ~20-25°C`
- [ ] Console mostra `💧 Umidità: ~40-60%`
- [ ] Valori realistici per ambiente interno

### 💡 LED GPIO
- [ ] LED BLU (GPIO 26) lampeggia durante ascolto
- [ ] LED VERDE (GPIO 21) lampeggia durante risposta

### 🧠 Brain
- [ ] Risponde in modo sensato alle domande
- [ ] Memoria conversazione funziona
- [ ] Può usare Google Search se necessario

## 🔧 Troubleshooting

### LED non si accendono
```bash
# Verifica permessi GPIO
sudo usermod -a -G gpio $USER
# Logout e login

# Test manuale
python3 -c "from gpiozero import LED; led = LED(26); led.on()"
```

### Radar non rileva
```bash
# Verifica porta seriale
ls -la /dev/ttyAMA0
# Dovrebbe essere: crw-rw---- 1 root dialout

# Test baudrate
stty -F /dev/ttyAMA0 256000

# Verifica connessioni:
# - VCC → 5V
# - GND → GND
# - TX radar → RX Pi (GPIO 15)
# - RX radar → TX Pi (GPIO 14)
```

### DHT11 sempre fallisce
- Pin corretto? **GPIO 18** (non 4)
- Attendere **2-3 secondi** tra letture (limite hardware)
- Alimentazione: 3.3V (non 5V)
- Cavo non troppo lungo (max 20cm)

### Jabra non funziona
```bash
# Device riconosciuto?
arecord -l  # Cerca "Jabra"
aplay -l

# Solo UN processo alla volta!
# Chiudi altri programmi audio

# Test microfono
arecord -D plughw:CARD=SPEAK410,DEV=0 -f S16_LE -r 16000 test.wav
```

### Brain non risponde
- Verifica `GOOGLE_API_KEY` in `.env`
- Controlla quota API: https://aistudio.google.com/apikey
- Log in console mostrano errori API?

## 📊 Cosa osservare in Console

Output tipico durante test:
```
🌡️ Temperatura: 22.5°C | 💧 58%
👤 Presenza: ASSENTE
🎤 Utente: Ciao Buddy, come stai?
🔊 Buddy: Ciao! Sto bene, grazie. Come posso aiutarti?
👤 Presenza: PRESENTE | Dist: 85cm | Mov: 45
🌡️ Temperatura: 22.6°C | 💧 57%
```

## 🎓 Note Architettura

Questo test usa:
- **Hexagonal Architecture**: Adapter reali sostituibili
- **Event-Driven**: Brain → Events → Router → Adapters
- **YAML Configuration**: Facile modificare adapter attivi
- **ConsoleOutput**: Nuovo adapter per debug/test

## 📝 Prossimi Passi

Dopo test hardware:
1. Se tutto funziona → sistema pronto per deploy
2. Se qualcosa non va → debug specifico del componente
3. Per produzione → usa `adapter_config_prod.yaml`
