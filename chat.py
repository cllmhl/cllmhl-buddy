#!/usr/bin/env python3
"""
Buddy Chat - CLI interattivo per comunicare con Buddy via named pipes

Permette di:
- Inviare eventi a Buddy (DIRECT_OUTPUT, USER_SPEECH, etc.)
- Monitorare eventi di output da Buddy in real-time
- Testare LED, voce e altri output rapidamente
"""

import os
import sys
import json
import select
import threading
from pathlib import Path
from datetime import datetime


# ===== CONFIG =====
PIPE_IN = Path("data/buddy.in")   # Scriviamo qui → Buddy
PIPE_OUT = Path("data/buddy.out") # Leggiamo da qui ← Buddy


# ===== COLORS =====
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Text colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'


def color(text, color_code):
    """Applica colore al testo"""
    return f"{color_code}{text}{Colors.RESET}"


# ===== OUTPUT MONITOR =====
class OutputMonitor:
    """Thread che monitora la pipe di output e stampa eventi"""
    
    def __init__(self, pipe_path: Path):
        self.pipe_path = pipe_path
        self.running = False
        self.thread = None
        
    def start(self):
        """Avvia il monitor"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Ferma il monitor"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            
    def _monitor_loop(self):
        """Loop di lettura dalla pipe output"""
        while self.running:
            try:
                # Apri in lettura (blocca finché Buddy scrive)
                with open(self.pipe_path, 'r') as pipe:
                    while self.running:
                        line = pipe.readline()
                        if not line:  # EOF
                            break
                            
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            self._display_event(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(color(f"\n⚠️  JSON invalido: {e}", Colors.RED))
                            
            except Exception as e:
                if self.running:
                    print(color(f"\n⚠️  Errore monitor: {e}", Colors.RED))
                    
    def _display_event(self, event_data: dict):
        """Mostra un evento ricevuto"""
        event_type = event_data.get('type', 'unknown')
        content = event_data.get('content', '')
        timestamp = event_data.get('timestamp', 0)
        priority = event_data.get('priority', 'NORMAL')
        
        time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        
        # Colore per tipo evento
        if event_type == 'speak':
            icon = '🔊'
            color_code = Colors.GREEN
        elif event_type.startswith('led_'):
            icon = '💡'
            color_code = Colors.YELLOW
        elif event_type.startswith('save_'):
            icon = '💾'
            color_code = Colors.BLUE
        else:
            icon = '📤'
            color_code = Colors.CYAN
            
        # Priorità badge
        if priority == 'CRITICAL':
            priority_badge = color('[CRITICAL]', Colors.BG_RED + Colors.WHITE)
        elif priority == 'HIGH':
            priority_badge = color('[HIGH]', Colors.YELLOW)
        else:
            priority_badge = ''
            
        msg = f"\n{icon} {color(time_str, Colors.MAGENTA)} "
        msg += f"{color(event_type.upper(), color_code + Colors.BOLD)} "
        if priority_badge:
            msg += f"{priority_badge} "
        msg += f"→ {content}"
        
        print(msg)
        print(color("\n> ", Colors.CYAN), end='', flush=True)


# ===== SENDER =====
def send_event(event_data: dict):
    """Invia un evento a Buddy via pipe"""
    json_line = json.dumps(event_data) + '\n'
    
    try:
        with open(PIPE_IN, 'w') as pipe:
            pipe.write(json_line)
            pipe.flush()
        return True
    except Exception as e:
        print(color(f"❌ Errore invio: {e}", Colors.RED))
        return False


# ===== EVENT BUILDERS =====
def build_direct_output(event_type: str, content, priority: str = "normal", metadata: dict | None = None):
    """Costruisce un DIRECT_OUTPUT event"""
    return {
        "type": "direct_output",
        "priority": priority,
        "content": {
            "event_type": event_type,
            "content": content,
            "priority": priority
        },
        "metadata": metadata or {}
    }


def build_led_control(led: str, command: str, **kwargs):
    """
    Costruisce un evento LED_CONTROL.
    
    Args:
        led: 'ascolto' | 'parlo'
        command: 'on' | 'off' | 'blink'
        **kwargs: continuous, on_time, off_time, times
    """
    metadata = {
        'led': led,
        'command': command,
        **kwargs
    }
    return build_direct_output("led_control", None, "normal", metadata)


def build_user_speech(text: str):
    """Costruisce un USER_SPEECH event"""
    return {
        "type": "user_speech",
        "priority": "high",
        "content": text
    }


# ===== MENU =====
def print_menu():
    """Stampa il menu principale"""
    print("\n" + "="*60)
    print(color("🤖  BUDDY CHAT - Menu Interattivo", Colors.CYAN + Colors.BOLD))
    print("="*60)
    
    print(f"\n{color('COMANDI RAPIDI:', Colors.YELLOW + Colors.BOLD)}")
    print(f"  {color('s', Colors.GREEN)} <testo>    → Speak (emetti voce)")
    print(f"  {color('t', Colors.GREEN)} <testo>    → Talk (invia speech utente)")
    
    print(f"\n{color('LED ASCOLTO (Blu):', Colors.BLUE + Colors.BOLD)}")
    print(f"  {color('lona', Colors.BLUE)}         → LED Ascolto ON")
    print(f"  {color('loffa', Colors.BLUE)}        → LED Ascolto OFF")
    print(f"  {color('lba', Colors.BLUE)} <n>      → LED Ascolto BLINK (n volte)")
    print(f"  {color('lidlea', Colors.BLUE)}       → LED Ascolto IDLE (lampeggia continuo)")
    
    print(f"\n{color('LED PARLO (Verde):', Colors.GREEN + Colors.BOLD)}")
    print(f"  {color('lonp', Colors.GREEN)}         → LED Parlo ON")
    print(f"  {color('loffp', Colors.GREEN)}        → LED Parlo OFF")
    print(f"  {color('lbp', Colors.GREEN)} <n>      → LED Parlo BLINK (n volte)")
    
    print(f"\n{color('MENU AVANZATO:', Colors.YELLOW + Colors.BOLD)}")
    print(f"  {color('menu', Colors.BLUE)}         → Mostra questo menu")
    print(f"  {color('json', Colors.BLUE)}         → Invia JSON custom")
    print(f"  {color('test', Colors.BLUE)}         → Test sequenza LED+Voce")
    print(f"  {color('help', Colors.BLUE)}         → Guida completa")
    print(f"  {color('quit', Colors.RED)}         → Esci")
    
    print("\n" + "="*60)


def print_help():
    """Stampa l'help dettagliato"""
    print("\n" + color("📖  GUIDA COMPLETA", Colors.CYAN + Colors.BOLD))
    print("\n" + color("Eventi DIRECT_OUTPUT supportati:", Colors.YELLOW))
    print("  • speak          - Emetti audio vocale")
    print("  • led_control    - Controllo unificato LED (con metadata)")
    
    print("\n" + color("Formato JSON custom:", Colors.YELLOW))
    print("""
  {
    "type": "direct_output",
    "priority": "high",
    "content": {
      "event_type": "speak",
      "content": "Ciao!"
    }
  }
    """)
    
    print(color("Esempi:", Colors.YELLOW))
    print("  s Ciao come stai?")
    print("  t Hey Buddy, accendi la luce")
    print("  lb 5")
    print("  json")


def interactive_loop():
    """Loop interattivo principale"""
    print(color("\n🚀 Buddy Chat avviato!", Colors.GREEN + Colors.BOLD))
    print(color(f"   Input pipe:  {PIPE_IN}", Colors.CYAN))
    print(color(f"   Output pipe: {PIPE_OUT}", Colors.CYAN))
    print("\nDigita 'menu' per vedere i comandi disponibili")
    
    # Avvia monitor output
    monitor = OutputMonitor(PIPE_OUT)
    monitor.start()
    
    try:
        while True:
            try:
                cmd = input(color("\n> ", Colors.CYAN)).strip()
                
                if not cmd:
                    continue
                    
                # Parse comando
                parts = cmd.split(maxsplit=1)
                action = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # ===== COMANDI =====
                if action in ['quit', 'exit', 'q']:
                    print(color("\n👋 Ciao!", Colors.GREEN))
                    break
                    
                elif action == 'menu':
                    print_menu()
                    
                elif action == 'help':
                    print_help()
                    
                elif action == 's':  # Speak
                    if not args:
                        print(color("⚠️  Uso: s <testo da dire>", Colors.RED))
                        continue
                    event = build_direct_output("speak", args, "high")
                    if send_event(event):
                        print(color(f"✅ Inviato: SPEAK '{args}'", Colors.GREEN))
                        
                elif action == 't':  # Talk (user speech)
                    if not args:
                        print(color("⚠️  Uso: t <testo>", Colors.RED))
                        continue
                    event = build_user_speech(args)
                    if send_event(event):
                        print(color(f"✅ Inviato: USER_SPEECH '{args}'", Colors.GREEN))
                
                # ===== LED ASCOLTO (Blu) =====
                elif action == 'lona':  # LED Ascolto ON
                    event = build_led_control('ascolto', 'on')
                    if send_event(event):
                        print(color("✅ Inviato: LED ASCOLTO ON", Colors.BLUE))
                        
                elif action == 'loffa':  # LED Ascolto OFF
                    event = build_led_control('ascolto', 'off')
                    if send_event(event):
                        print(color("✅ Inviato: LED ASCOLTO OFF", Colors.BLUE))
                        
                elif action == 'lba':  # LED Ascolto BLINK
                    times = int(args) if args else 3
                    event = build_led_control('ascolto', 'blink', times=times)
                    if send_event(event):
                        print(color(f"✅ Inviato: LED ASCOLTO BLINK x{times}", Colors.BLUE))
                        
                elif action == 'lidlea':  # LED Ascolto IDLE (continuous blink)
                    event = build_led_control('ascolto', 'blink', continuous=True, on_time=1.0, off_time=1.0)
                    if send_event(event):
                        print(color("✅ Inviato: LED ASCOLTO IDLE (lampeggia continuo)", Colors.BLUE))
                
                # ===== LED PARLO (Verde) =====
                elif action == 'lonp':  # LED Parlo ON
                    event = build_led_control('parlo', 'on')
                    if send_event(event):
                        print(color("✅ Inviato: LED PARLO ON", Colors.GREEN))
                        
                elif action == 'loffp':  # LED Parlo OFF
                    event = build_led_control('parlo', 'off')
                    if send_event(event):
                        print(color("✅ Inviato: LED PARLO OFF", Colors.GREEN))
                        
                elif action == 'lbp':  # LED Parlo BLINK
                    times = int(args) if args else 3
                    event = build_led_control('parlo', 'blink', times=times)
                    if send_event(event):
                        print(color(f"✅ Inviato: LED PARLO BLINK x{times}", Colors.GREEN))
                
                # ===== LEGACY LED COMANDI (backward compat) =====
                elif action == 'lon':  # LED ON (default parlo)
                    event = build_led_control('parlo', 'on')
                    if send_event(event):
                        print(color("✅ Inviato: LED ON (parlo)", Colors.YELLOW))
                        
                elif action == 'loff':  # LED OFF (default parlo)
                    event = build_led_control('parlo', 'off')
                    if send_event(event):
                        print(color("✅ Inviato: LED OFF (parlo)", Colors.YELLOW))
                        
                elif action == 'lb':  # LED BLINK (default parlo)
                    times = int(args) if args else 3
                    event = build_led_control('parlo', 'blink', times=times)
                    if send_event(event):
                        print(color(f"✅ Inviato: LED BLINK x{times} (parlo)", Colors.YELLOW))
                        
                elif action == 'json':  # JSON custom
                    print(color("\nInserisci JSON (linea singola):", Colors.CYAN))
                    json_input = input(color("> ", Colors.CYAN))
                    try:
                        event = json.loads(json_input)
                        if send_event(event):
                            print(color("✅ JSON inviato", Colors.GREEN))
                    except json.JSONDecodeError as e:
                        print(color(f"❌ JSON invalido: {e}", Colors.RED))
                        
                elif action == 'test':  # Test sequence
                    print(color("\n🧪 Avvio test sequence LED...", Colors.MAGENTA))
                    tests = [
                        (build_led_control('ascolto', 'blink', continuous=True), "LED ASCOLTO → IDLE (lampeggia)"),
                        (build_direct_output("speak", "Test LED in corso"), "SPEAK"),
                        (build_led_control('ascolto', 'on'), "LED ASCOLTO → ON (fisso)"),
                        (build_led_control('parlo', 'on'), "LED PARLO → ON"),
                        (build_direct_output("speak", "Sto parlando"), "SPEAK"),
                        (build_led_control('parlo', 'off'), "LED PARLO → OFF"),
                        (build_led_control('ascolto', 'off'), "LED ASCOLTO → OFF"),
                        (build_direct_output("speak", "Test completato"), "SPEAK"),
                    ]
                    for event, desc in tests:
                        print(color(f"  → {desc}...", Colors.CYAN))
                        send_event(event)
                        import time
                        time.sleep(1.5)
                    print(color("✅ Test completato!", Colors.GREEN))
                    
                else:
                    print(color(f"❌ Comando sconosciuto: {action}", Colors.RED))
                    print(color("   Digita 'menu' per vedere i comandi", Colors.YELLOW))
                    
            except KeyboardInterrupt:
                print(color("\n\n👋 Interrotto, usa 'quit' per uscire", Colors.YELLOW))
                
            except Exception as e:
                print(color(f"\n❌ Errore: {e}", Colors.RED))
                
    finally:
        monitor.stop()


# ===== MAIN =====
def main():
    """Entry point"""
    
    # Verifica che le pipe esistano
    if not PIPE_IN.exists():
        print(color(f"⚠️  Pipe input non trovata: {PIPE_IN}", Colors.RED))
        print(color("   Buddy deve essere avviato prima!", Colors.YELLOW))
        print(color("   Le named pipe vengono create automaticamente da Buddy", Colors.YELLOW))
        sys.exit(1)
        
    if not PIPE_OUT.exists():
        print(color(f"⚠️  Pipe output non trovata: {PIPE_OUT}", Colors.RED))
        print(color("   Buddy deve essere avviato prima!", Colors.YELLOW))
        sys.exit(1)
        
    # Avvia loop interattivo
    try:
        interactive_loop()
    except Exception as e:
        print(color(f"\n❌ Errore fatale: {e}", Colors.RED))
        sys.exit(1)


if __name__ == "__main__":
    main()
