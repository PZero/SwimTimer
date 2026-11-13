#!/bin/bash
# Dal PC (Git Bash), nella radice del repository:  bash stazione/rpi/deploy.sh [swim@swimtimer-pi.local]
# Copia i file della stazione sul Pi e lancia installa.sh. Non copia dati, log ne' credenziali.
set -euo pipefail
PI="${1:-swim@swimtimer-pi.local}"
QUI="$(cd "$(dirname "$0")" && pwd)"
DEST="swimtimer-install"
ssh -o ConnectTimeout=10 "$PI" "mkdir -p $DEST"
scp "$QUI/../ricevitore_host.py" "$QUI/pannello.py" "$QUI/pannello.html" "$QUI/kiosk.sh" "$QUI/installa.sh" \
    "$QUI/swimtimer.default" "$QUI"/swimtimer-*.service "$PI:$DEST/"
# staccato da SSH (systemd-run): se il Wi-Fi del Pi cade a meta' di apt, l'installazione prosegue
ssh "$PI" "sudo systemd-run --unit=swim-installa --collect --wait bash /home/swim/$DEST/installa.sh" || \
  echo "connessione persa: l'installazione continua sul Pi; log con  ssh $PI journalctl -u swim-installa"
ssh "$PI" "journalctl -u swim-installa --no-pager -n 15 -o cat" || true
