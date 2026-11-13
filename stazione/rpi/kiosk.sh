#!/bin/bash
# Apre il pannello a schermo intero. BROWSER in /etc/default/swimtimer: cog (leggero, default) oppure chromium (riserva).
URL="http://127.0.0.1:${PANNELLO_PORTA:-8080}/"
# aspetta il pannello (max ~30 s), poi parte comunque: la pagina riprova da sola
for i in $(seq 30); do
  (exec 3<>/dev/tcp/127.0.0.1/"${PANNELLO_PORTA:-8080}") 2>/dev/null && break
  sleep 1
done
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
case "${BROWSER:-cog}" in
  chromium)
    exec cage -d -- chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --ozone-platform=wayland \
      --disable-features=Translate --check-for-update-interval=31536000 --password-store=basic "$URL" ;;
  *)
    # WPE WebKit direttamente su DRM/KMS: niente X, niente compositore
    exec cog --platform=drm "$URL" ;;
esac
