#!/bin/bash

# ============================================================================
# Buddy Launcher
# RICHIEDE: BUDDY_HOME e usa configurazione di sviluppo
# ============================================================================

source "$(dirname "$0")/common.sh"
export BUDDY_CONFIG=config/dev.yaml
validate_all

echo "--- Buddy OS Startup ---"
echo "🏠 BUDDY_HOME: $BUDDY_HOME"
echo "📋 BUDDY_CONFIG: $BUDDY_CONFIG"
echo ""
echo "🚀 Avvio Buddy..."
python3 -u "$BUDDY_HOME/main.py"

echo ""
echo "--- Buddy OS Offline ---"
