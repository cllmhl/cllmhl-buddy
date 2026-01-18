#!/usr/bin/env python3
"""
Test DIRECT_OUTPUT - Verifica il pattern di bypass del Brain
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.events import Event, EventType, EventPriority, create_input_event, create_output_event
from core.brain import BuddyBrain

def test_direct_output():
    """Test del pattern DIRECT_OUTPUT"""
    
    print("\n" + "="*60)
    print("TEST: DIRECT_OUTPUT Pattern")
    print("="*60 + "\n")
    
    # Simula un brain minimale (senza API key reale per test)
    config = {
        "model_id": "gemini-2.0-flash-exp",
        "temperature": 0.7,
        "archivist_interval": 300.0
    }
    
    # Crea eventi output reali (quelli che andrebbero agli adapter)
    led_control_event = create_output_event(
        event_type=EventType.LED_CONTROL,
        content=None,
        priority=EventPriority.HIGH,
        metadata={'led': 'ascolto', 'command': 'on'}
    )
    
    speak_event = create_output_event(
        event_type=EventType.SPEAK,
        content="Ciao, questo è un test",
        priority=EventPriority.HIGH
    )
    
    # Wrappa in DIRECT_OUTPUT (questo viene dall'input)
    direct_led = create_input_event(
        event_type=EventType.DIRECT_OUTPUT,
        content=led_control_event,  # <- Evento output wrappato
        source="test",
        priority=EventPriority.HIGH
    )
    
    direct_speak = create_input_event(
        event_type=EventType.DIRECT_OUTPUT,
        content=speak_event,
        source="test",
        priority=EventPriority.HIGH
    )
    
    print("✅ Eventi creati:")
    print(f"   1. LED_CONTROL wrappato in DIRECT_OUTPUT")
    print(f"   2. SPEAK wrappato in DIRECT_OUTPUT\n")
    
    # Simula processing (senza inizializzare il client LLM)
    try:
        # Mock brain senza API
        brain = object.__new__(BuddyBrain)
        brain.config = config
        brain.archivist_interval = 300.0
        brain.last_archivist_time = 0
        
        print("🧠 Processando DIRECT_OUTPUT (LED_CONTROL)...")
        result_led = brain._handle_direct_output(direct_led)
        
        print(f"   → Risultato: {len(result_led)} evento/i")
        if result_led:
            print(f"   → Tipo: {result_led[0].type.value}")
            print(f"   → Metadata: {result_led[0].metadata}\n")
        
        print("🧠 Processando DIRECT_OUTPUT (SPEAK)...")
        result_speak = brain._handle_direct_output(direct_speak)
        
        print(f"   → Risultato: {len(result_speak)} evento/i")
        if result_speak:
            print(f"   → Tipo: {result_speak[0].type.value}")
            print(f"   → Content: {result_speak[0].content[:50]}...\n")
        
        print("="*60)
        print("✅ TEST PASSED: DIRECT_OUTPUT unwrapping funziona!")
        print("="*60 + "\n")
        
        print("📝 Note:")
        print("   - L'evento wrapper (DIRECT_OUTPUT) è di tipo INPUT")
        print("   - L'evento interno (LED_CONTROL, SPEAK) è di tipo OUTPUT")
        print("   - Il Brain li unwrappa e inoltra direttamente")
        print("   - Nessuna chiamata LLM = perfetto per test hardware\n")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_direct_output()
    sys.exit(0 if success else 1)
