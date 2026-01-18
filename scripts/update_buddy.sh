#!/bin/bash

# ============================================================================
# Buddy Updater - Git Pull
# RICHIEDE: BUDDY_HOME deve essere settato esternamente
# ============================================================================

source "$(dirname "$0")/common.sh"
validate_buddy_home

echo "--- 🔄 Aggiornamento Buddy ---"
echo "🏠 BUDDY_HOME: $BUDDY_HOME"
echo ""

cd "$BUDDY_HOME" || exit 1

echo "Recupero aggiornamenti da Git..."
git fetch --all
git reset --hard origin/main

echo ""
echo "✅ Aggiornamento completato"
