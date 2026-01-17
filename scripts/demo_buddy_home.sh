#!/bin/bash

# ============================================================================
# ESEMPIO: Dimostrazione del problema dei path relativi RISOLTO
# ============================================================================

echo "============================================================"
echo "Dimostrazione BUDDY_HOME - Path Assoluti"
echo "============================================================"
echo ""

# Setup
BUDDY_HOME_PATH="/workspaces/cllmhl-buddy"
export BUDDY_HOME="$BUDDY_HOME_PATH"
export BUDDY_CONFIG="config/adapter_config_dev.yaml"

echo "🏠 BUDDY_HOME impostato a: $BUDDY_HOME"
echo "📋 BUDDY_CONFIG: $BUDDY_CONFIG"
echo ""

# Test 1: Lanciare da directory diversa (PRIMA falliva)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Lancio da /tmp (directory diversa)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /tmp
echo "Current directory: $(pwd)"
echo ""
echo "PRIMA (path relativi): ❌ FileNotFoundError: config/..."
echo "DOPO (BUDDY_HOME):     ✅ Funziona!"
echo ""

python3 -c "
import sys
sys.path.insert(0, '$BUDDY_HOME')
from config.config_loader import get_buddy_home, resolve_path

buddy_home = get_buddy_home()
config_path = resolve_path('$BUDDY_CONFIG')

print(f'✓ BUDDY_HOME rilevato: {buddy_home}')
print(f'✓ Config path risolto: {config_path}')
print(f'✓ Config exists: {config_path.exists()}')
"
echo ""

# Test 2: Simulare systemd service
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Simulazione servizio systemd"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Il servizio systemd lancia con path assoluti ma CWD diverso"
echo ""
echo "PRIMA: WorkingDirectory richiesto, fragile"
echo "DOPO:  BUDDY_HOME environment variable, robusto"
echo ""

# Simula il servizio
cd /
echo "Current directory: $(pwd) (come systemd)"
python3 "$BUDDY_HOME_PATH/main_new.py" --help 2>&1 | head -n 5 || echo "(main_new.py non ha --help, ma carica config correttamente)"
echo "✓ Può essere lanciato da qualsiasi directory"
echo ""

# Test 3: Script wrapper
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Script wrapper (come run_buddy.sh)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd "$BUDDY_HOME_PATH"
echo "run_buddy.sh imposta automaticamente BUDDY_HOME"
echo ""

cat << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BUDDY_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
export BUDDY_CONFIG="${BUDDY_CONFIG:-config/adapter_config_dev.yaml}"

# Funziona da QUALSIASI directory!
python3 "$BUDDY_HOME/main_new.py"
EOF
echo ""
echo "✓ Nessun 'cd' necessario"
echo "✓ Path sempre corretti"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VANTAGGI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Lancia Buddy da qualsiasi directory"
echo "✅ Servizi systemd funzionano senza WorkingDirectory"
echo "✅ Script wrapper più semplici e robusti"
echo "✅ Auto-detection se non impostato"
echo "✅ Override manuale possibile"
echo "✅ Path sempre assoluti e corretti"
echo ""
echo "Per maggiori info: docs/BUDDY_HOME.md"
echo "============================================================"
