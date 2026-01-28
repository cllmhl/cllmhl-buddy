#!/bin/bash

# ============================================================================
# Buddy Launcher
# RICHIEDE: BUDDY_HOME e usa configurazione di sviluppo
# ============================================================================


# Allow config selection: if parameter is present, use as config file name; else default to dev.yaml
source "$(dirname "$0")/common.sh"
if [[ -n "$1" ]]; then
    export BUDDY_CONFIG="config/$1.yaml"
else
    export BUDDY_CONFIG="config/dev.yaml"
fi
validate_all

echo "--- Buddy OS Startup ---"
echo "🏠 BUDDY_HOME: $BUDDY_HOME"
echo "📋 BUDDY_CONFIG: $BUDDY_CONFIG"
echo ""
echo "🚀 Avvio Buddy..."
python3 -u "$BUDDY_HOME/main.py"

echo ""
echo "--- Buddy OS Offline ---"
