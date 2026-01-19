"""
Test di integrazione per ArchivistAdapter
Verifica che il brain triggheri correttamente la distillazione ogni N secondi
"""

import os
import sys
import time
from pathlib import Path

# Aggiungi parent directory al path per imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Setup
load_dotenv(".env")
os.environ.setdefault("GOOGLE_API_KEY", "dummy_key_for_testing")

from core.brain import BuddyBrain
from core.events import Event, InputEventType, OutputEventType, EventPriority, create_output_event


def test_archivist_trigger():
    """Test che il brain emetta eventi DISTILL_MEMORY periodicamente"""
    
    print("=" * 60)
    print("TEST: Archivist Trigger Periodico")
    print("=" * 60)
    
    # Configurazione brain con intervallo breve (5s)
    config = {
        'model_id': 'gemini-2.5-flash-lite',
        'temperature': 0.7,
        'archivist_interval': 5.0,  # 5 secondi per test veloce
        'system_instruction': 'Sei Buddy per test'
    }
    
    brain = BuddyBrain(os.getenv("GOOGLE_API_KEY"), config)
    
    print(f"\n✅ Brain inizializzato")
    print(f"   Archivist interval: {brain.archivist_interval}s")
    print(f"   Last trigger time: {brain.last_archivist_time}")
    
    # Simula eventi sensoriali (non dovrebbero triggerare archivist immediatamente)
    print("\n📡 Invio evento SENSOR_PRESENCE (t=0s)...")
    sensor_event = Event(
        type=InputEventType.SENSOR_PRESENCE,
        content=True,
        source="radar",
        timestamp=time.time(),
        priority=EventPriority.NORMAL
    )
    
    output_events, commands = brain.process_event(sensor_event)
    distill_events = [e for e in output_events if e.type == OutputEventType.DISTILL_MEMORY]
    
    print(f"   Output events: {len(output_events)}")
    print(f"   DISTILL_MEMORY events: {len(distill_events)}")
    assert len(distill_events) == 0, "❌ Non dovrebbe triggerare archivist subito"
    print("   ✅ OK: nessun trigger immediato")
    
    # Attendi 2 secondi (meno dell'intervallo)
    print("\n⏳ Attendo 2 secondi (< 5s interval)...")
    time.sleep(2)
    
    print("📡 Invio altro evento SENSOR_TEMPERATURE...")
    temp_event = Event(
        type=InputEventType.SENSOR_TEMPERATURE,
        content=25.5,
        source="dht11",
        timestamp=time.time(),
        priority=EventPriority.NORMAL
    )
    
    output_events, commands = brain.process_event(temp_event)
    distill_events = [e for e in output_events if e.type == OutputEventType.DISTILL_MEMORY]
    
    print(f"   Output events: {len(output_events)}")
    print(f"   DISTILL_MEMORY events: {len(distill_events)}")
    assert len(distill_events) == 0, "❌ Ancora troppo presto per trigger"
    print("   ✅ OK: nessun trigger (2s < 5s)")
    
    # Attendi altri 4 secondi (totale 6s, oltre l'intervallo)
    print("\n⏳ Attendo altri 4 secondi (totale 6s > 5s interval)...")
    time.sleep(4)
    
    print("📡 Invio evento SENSOR_PRESENCE...")
    sensor_event2 = Event(
        type=InputEventType.SENSOR_PRESENCE,
        content=False,
        source="radar",
        timestamp=time.time(),
        priority=EventPriority.NORMAL
    )
    
    output_events, commands = brain.process_event(sensor_event2)
    distill_events = [e for e in output_events if e.type == OutputEventType.DISTILL_MEMORY]
    
    print(f"   Output events: {len(output_events)}")
    print(f"   DISTILL_MEMORY events: {len(distill_events)}")
    
    if len(distill_events) > 0:
        print(f"   ✅ SUCCESSO: Trigger archivist dopo {distill_events[0].metadata.get('elapsed_seconds', 0):.1f}s")
        print(f"   Event details: {distill_events[0]}")
    else:
        print(f"   ❌ FALLITO: Doveva triggerare dopo 6s (intervallo 5s)")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TEST PASSED: Archivist trigger periodico funziona")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_archivist_trigger()
        exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
