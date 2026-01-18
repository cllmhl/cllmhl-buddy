#!/bin/bash

# ============================================================================
# Common utilities for Buddy scripts
# Source this file in other scripts: source "$(dirname "$0")/common.sh"
# ============================================================================

validate_buddy_home() {
    if [ -z "$BUDDY_HOME" ]; then
        echo "❌ ERROR: BUDDY_HOME non settato"
        echo "   Esegui: export BUDDY_HOME=/path/to/cllmhl-buddy"
        exit 1
    fi

    if [ ! -d "$BUDDY_HOME" ]; then
        echo "❌ ERROR: BUDDY_HOME non esiste: $BUDDY_HOME"
        exit 1
    fi
}

validate_buddy_config() {
    if [ -z "$BUDDY_CONFIG" ]; then
        echo "❌ ERROR: BUDDY_CONFIG non settato"
        echo "   Esegui: export BUDDY_CONFIG=config/dev.yaml"
        exit 1
    fi
}

validate_all() {
    validate_buddy_home
    validate_buddy_config
}
