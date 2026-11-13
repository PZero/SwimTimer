#!/bin/bash
# Installa la stazione SwimTimer sul Pi. Da lanciare SUL PI con sudo, dalla cartella che contiene i file:
#   sudo bash installa.sh            (con BROWSER=chromium in /etc/default/swimtimer installa anche cage+chromium)
set -euo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo "serve sudo"; exit 1; }

[ -f /etc/default/swimtimer ] || install -m 644 swimtimer.default /etc/default/swimtimer
. /etc/default/swimtimer

PACCHETTI="python3 python3-serial"
if [ "${BROWSER:-cog}" = chromium ]; then PACCHETTI="$PACCHETTI cage chromium"; else PACCHETTI="$PACCHETTI cog libgles2 libegl1 libgl1-mesa-dri"; fi   # senza libgles2 il renderer di WPE va in crash
apt-get update
apt-get install -y --no-install-recommends $PACCHETTI

install -d -m 755 /opt/swimtimer
install -m 644 ricevitore_host.py pannello.py pannello.html /opt/swimtimer/
install -m 755 kiosk.sh /opt/swimtimer/
install -d -o swim -g "$(id -gn swim)" -m 700 "$CARTELLA"
usermod -aG dialout,video,render,input swim

install -m 644 swimtimer-host.service swimtimer-pannello.service swimtimer-kiosk.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable swimtimer-host swimtimer-pannello swimtimer-kiosk
systemctl restart swimtimer-host swimtimer-pannello swimtimer-kiosk

# schermo sempre acceso (niente spegnimento della console)
if ! grep -q consoleblank=0 /boot/firmware/cmdline.txt; then
  sed -i '1 s/$/ consoleblank=0/' /boot/firmware/cmdline.txt
  echo "aggiunto consoleblank=0 a cmdline.txt (vale dal prossimo riavvio)"
fi

sleep 3
systemctl --no-pager --lines=3 status swimtimer-host swimtimer-pannello swimtimer-kiosk || true
echo "pannello: http://$(hostname).local:${PANNELLO_PORTA}/"
