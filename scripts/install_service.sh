#!/bin/bash
# Script di installazione del servizio systemd per Buddy

set -e  # Exit on error

# Ottieni la directory del progetto (parent della cartella scripts)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🤖 Installazione Buddy Service..."

# Verifica che lo script sia eseguito da root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Esegui questo script con sudo:"
    echo "   sudo bash scripts/install_service.sh"
    exit 1
fi

# Copia il file service nella directory systemd
echo "📦 Copiando buddy.service in /etc/systemd/system/..."
cp "$PROJECT_DIR/config/buddy.service" /etc/systemd/system/buddy.service

# Ricarica i daemon di systemd
echo "🔄 Ricaricando systemd daemon..."
systemctl daemon-reload

# Abilita il servizio per l'avvio automatico
echo "✅ Abilitando Buddy all'avvio..."
systemctl enable buddy.service

# Verifica lo stato
echo ""
echo "✨ Installazione completata!"
echo ""
echo "📋 Comandi utili:"
echo "   sudo systemctl start buddy      # Avvia Buddy"
echo "   sudo systemctl stop buddy       # Ferma Buddy"
echo "   sudo systemctl restart buddy    # Riavvia Buddy"
echo "   sudo systemctl status buddy     # Stato del servizio"
echo "   journalctl -u buddy -f          # Visualizza log in tempo reale"
echo "   journalctl -u buddy -n 100      # Ultimi 100 log"
echo ""
echo "🚀 Per avviare Buddy ora:"
echo "   sudo systemctl start buddy"
