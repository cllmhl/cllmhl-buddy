# 🧠 Buddy Senses - Documentazione Sensori

## Panoramica

Il modulo `senses.py` gestisce tutti i sensori fisici di Buddy, implementando un'architettura **event-driven** dove i sensori inviano eventi in una coda condivisa.

## Architettura

```
┌─────────────────────────────────────────────┐
│            BuddySenses Manager              │
│                                             │
│  ┌──────────────┐      ┌──────────────┐   │
│  │ RadarLD2410C │      │   DHT11      │   │
│  │   (UART)     │      │  (GPIO 4)    │   │
│  └──────┬───────┘      └──────┬───────┘   │
│         │                     │            │
│         └─────────┬───────────┘            │
│                   ▼                        │
│            event_queue ───────────────────▶  main.py
└─────────────────────────────────────────────┘
```

## Sensori Implementati

### 1. Radar mmWave LD2410C 📡

**Connessione:** UART/Serial (`/dev/ttyAMA0`)  
**Baudrate:** 256000  
**Funzionalità:**
- Rilevamento presenza umana
- Distinzione movimento/statico
- Misurazione distanza (cm)

**Eventi generati:**
- `radar_presence`: Booleano (presenza rilevata)
- Metadata: `movement`, `static`, `distance`

**Configurazione:**
```python
config = {
    'radar_enabled': True,
    'radar_port': '/dev/ttyAMA0',
    'radar_baudrate': 256000,
    'radar_interval': 0.5  # secondi tra letture
}
```

**Variabili d'ambiente:**
```bash
RADAR_ENABLED=true
RADAR_PORT=/dev/ttyAMA0
RADAR_BAUDRATE=256000
RADAR_INTERVAL=0.5
```

### 2. DHT11 - Temperatura e Umidità 🌡️💧

**Connessione:** GPIO 4 (BCM numbering)  
**Protocollo:** 1-Wire  
**Funzionalità:**
- Temperatura: 0-50°C (±2°C)
- Umidità: 20-90% (±5%)
- Lettura ogni 2 secondi (limitazione hardware)

**Eventi generati:**
- `temperature`: Float (gradi Celsius)
- `humidity`: Float (percentuale)

**Configurazione:**
```python
config = {
    'dht11_enabled': True,
    'dht11_pin': 4,  # GPIO BCM
    'dht11_interval': 30.0  # secondi tra report
}
```

**Variabili d'ambiente:**
```bash
DHT11_ENABLED=true
DHT11_PIN=4
DHT11_INTERVAL=30.0
```

## Utilizzo

### In main.py

```python
from senses import BuddySenses, SensorEvent

# Configurazione
sensor_config = {
    'radar_enabled': True,
    'dht11_enabled': True,
    # ... altre opzioni
}

# Inizializzazione
senses = BuddySenses(event_queue, sensor_config)
senses.start()

# Nel main loop
while True:
    if not event_queue.empty():
        event = event_queue.get()
        
        if isinstance(event, SensorEvent):
            # Gestisci evento sensore
            if event.sensor_type == "radar_presence":
                if event.value:
                    print("Presenza rilevata!")
            
            elif event.sensor_type == "temperature":
                print(f"Temperatura: {event.value}°C")
```

### Test Standalone

```bash
# Test interattivo
python3 test_senses.py

# Test specifico
python3 test_senses.py 1  # Test inizializzazione
python3 test_senses.py 2  # Test lettura dati
python3 test_senses.py 3  # Monitoraggio continuo

# Con script bash
./test_senses.sh
```

## Installazione Dipendenze

```bash
pip install pyserial adafruit-circuitpython-dht
```

### Raspberry Pi - Setup Hardware

#### Radar LD2410C
```bash
# Abilita UART
sudo raspi-config
# Interface Options > Serial Port
# - Login shell: NO
# - Serial port hardware: YES

# Verifica
ls -l /dev/ttyAMA0
```

**Connessioni Hardware:**
- **VCC** → Striscia Rossa (5V)
- **GND** → Striscia Blu (GND)
- **TX** → Pin 10 del T-Cobbler (GPIO 15 / RXD)
- **RX** → Pin 8 del T-Cobbler (GPIO 14 / TXD)

#### DHT11
```python
# Connessioni:
# VCC  -> Pin 1 (3.3V)
# DATA -> Pin 7 (GPIO 4)
# GND  -> Pin 9 (Ground)
```

## Eventi Sensori

### SensorEvent

```python
@dataclass
class SensorEvent:
    sensor_type: str    # "radar_presence", "temperature", "humidity"
    value: any          # Il valore misurato
    timestamp: float    # Unix timestamp
    metadata: dict      # Dati aggiuntivi (opzionale)
```

### Esempi Eventi

```python
# Presenza rilevata
SensorEvent(
    sensor_type="radar_presence",
    value=True,
    timestamp=1234567890.0,
    metadata={
        'movement': True,
        'static': False,
        'distance': 120  # cm
    }
)

# Temperatura
SensorEvent(
    sensor_type="temperature",
    value=23.5,
    timestamp=1234567890.0,
    metadata={'unit': 'celsius'}
)

# Umidità
SensorEvent(
    sensor_type="humidity",
    value=65.0,
    timestamp=1234567890.0,
    metadata={'unit': 'percent'}
)
```

## Ottimizzazioni

### Riduzione Eventi

I sensori inviano eventi solo quando c'è un **cambiamento significativo**:

- **Temperatura:** ±0.5°C
- **Umidità:** ±2%
- **Radar:** Cambio stato presenza

Questo evita flooding della event_queue.

### Intervalli Lettura

- **Radar:** 0.5s (real-time)
- **DHT11:** 30s (sensore lento, dati stabili)

Configurabili tramite `config` o variabili d'ambiente.

## Troubleshooting

### Radar non funziona
```bash
# Verifica connessione UART
ls -l /dev/ttyAMA0

# Test lettura diretta
cat /dev/ttyAMA0 | hexdump -C

# Log Buddy
grep "RadarLD2410C" buddy_system.log
```

### DHT11 errori di lettura
```python
# È NORMALE: il DHT11 è instabile
# Il modulo gestisce automaticamente retry
# e mantiene l'ultimo valore valido

# Se persiste:
# 1. Verifica collegamenti
# 2. Aggiungi resistore pull-up 10kΩ su DATA
# 3. Controlla alimentazione (3.3V stabile)
```

### Performance
```bash
# Monitora CPU usage thread sensori
top -H -p $(pgrep -f main.py)

# Se troppo alto, aumenta intervalli:
RADAR_INTERVAL=1.0
DHT11_INTERVAL=60.0
```

## Prossimi Sensori

- [ ] **LDR** - Sensore luminosità (ADC)
- [ ] **PIR** - Motion detector passivo
- [ ] **Microfono Ambientale** - Livello rumore
- [ ] **BME280** - Temperatura/Umidità/Pressione (I2C)

## Note Sviluppo

### Thread Safety
- `event_queue` è thread-safe (Queue)
- Ogni sensore ha il proprio thread di lettura
- Nessuna modifica di stato condiviso

### Mock per Testing
```python
# Su PC (non Raspberry Pi):
# - GPIO usa mock pin factory
# - Sensori si disabilitano automaticamente
# - Test possono simulare eventi

# Esempio test mock:
test_queue = queue.Queue()
test_queue.put(SensorEvent("temperature", 25.0, time.time()))
```

## Riferimenti

- [LD2410C Datasheet](https://drive.google.com/file/d/1CYgZTAV3pV5xGXuy3RAoCKDXQS3NaFRu/view)
- [DHT11 Datasheet](https://www.mouser.com/datasheet/2/758/DHT11-Technical-Data-Sheet-Translated-Version-1143054.pdf)
- [Adafruit DHT Library](https://github.com/adafruit/Adafruit_CircuitPython_DHT)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
