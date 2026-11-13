# Stazione Raspberry Pi 3

Pi 3 Model B, Raspberry Pi OS Lite 64 bit (trixie 2026-10-06), nome `swimtimer-pi`, utente `swim` (accesso con chiave SSH, `sudo` senza password). Display di prova: Waveshare 4″ HDMI LCD (480×800, touch XPT2046); display finale: monitor 15,6″ HDMI.

## Preparare la SD (da Windows)
1. Scaricare `raspios_lite_arm64_latest`, verificare lo SHA256, decomprimere (`.img`).
2. Scrivere con `dd` di Git Bash da una PowerShell **amministratore** (`of=/dev/sdb` = PhysicalDrive1: controllare prima il disco!). `rpi-imager --cli` su Windows non funziona (eseguibile senza console).
3. Partizione di avvio: copiare `user-data.esempio` come `user-data` e sostituire i segnaposto; aggiungere in coda a `config.txt` il blocco sotto.

## `config.txt` (in fondo, sotto `[all]`)
```
#disable_fw_kms_setup=1      <- commentare la riga esistente
dtparam=spi=on
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 800 60 6 0 0 0
hdmi_drive=1
```
Con `video=HDMI-A-1:...` del KMS il pannello mostrava l'immagine triplicata o illeggibile. Per il monitor 15,6″ togliere le righe `hdmi_*`.

## Riconfigurare senza rete
cloud-init gira **solo al primo avvio**. Se il Wi-Fi è sbagliato: copiare `swim-firstrun.sh` nella partizione di avvio e aggiungere a `cmdline.txt` (stessa riga)
`systemd.run=/boot/firmware/swim-firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target`.
Lo script legge SSID e password da `user-data`, crea i profili NetworkManager, l'utente `swim` con la chiave, attiva SSH, installa `swim-diag.service`, poi si cancella e riavvia. Registro: `/boot/firmware/diag-firstrun.txt` (senza password).
A ogni avvio `/boot/firmware/diag.txt` riporta lo stato della rete (leggibile da Windows).
Dopo la configurazione sostituire le password in `user-data` (lo script non serve più).

## Stazione: host, pannello e kiosk
Tre servizi systemd (riavvio automatico se cadono, avvio al boot), configurati da `/etc/default/swimtimer` (modello: `swimtimer.default`):

| Servizio | Cosa fa |
|---|---|
| `swimtimer-host` | `ricevitore_host.py --porta /dev/ttyACM0 --cartella /home/swim/swimtimer-dati --stato /run/swimtimer/stato.json` |
| `swimtimer-pannello` | `pannello.py`: serve `pannello.html` e `stato.json` su `http://swimtimer-pi.local:8080/` (solo libreria standard) |
| `swimtimer-kiosk` | `kiosk.sh` sul tty7: **cog** (WPE WebKit su DRM/KMS, niente X) a schermo intero sul pannello |

- `--stato` (nuovo in `ricevitore_host.py`): ogni secondo scrive un JSON (file temporaneo + `os.replace`) con, per ogni tag, i campi STAT, i salvati, la DIAGNOSI2 e le ultime 30 righe del log. Senza l'opzione l'host funziona come prima.
- Il pannello mostra un avviso rosso se il JSON è vecchio di oltre 5 s (host fermo) o se il ricevitore USB non è collegato.
- **Nomi delle tag**: il ricevitore 0.1.x non legge il nome dall'annuncio BLE, quindi il pannello li prende da `/home/swim/swimtimer-dati/nomi.txt` (righe `<id> <nome>`, modello `nomi.esempio.txt`; riletto da solo quando cambia). Contiene nomi di persone: solo sul Pi.
- I dati di nuoto restano solo sul Pi in `/home/swim/swimtimer-dati/` (permessi 700), mai nel repository.
- Il pannello è visibile anche dal telefono in rete locale (`PANNELLO_INDIRIZZO=0.0.0.0`); per limitarlo al monitor mettere `127.0.0.1`.

### Installazione (deploy dal PC)
Con il Pi acceso e raggiungibile, dalla radice del repository in Git Bash:
```
bash stazione/rpi/deploy.sh                    # default swim@swimtimer-pi.local (.local a volte non risolve: usare l IP)
bash stazione/rpi/deploy.sh swim@192.168.1.50  # se .local non risolve
```
Copia i file in `~/swimtimer-install/` e lancia `sudo bash installa.sh`, che: installa `python3-serial` e `cog`, copia i programmi in `/opt/swimtimer/`, crea `/etc/default/swimtimer` (solo se manca), aggiunge `swim` ai gruppi `dialout video render input`, installa e avvia i servizi, aggiunge `consoleblank=0` a `cmdline.txt`. Rilanciabile per gli aggiornamenti (non tocca la configurazione).

**Monitor 15,6″:** prima togliere da `config.txt` le righe `hdmi_*` del display da 4″ (sezione sopra), poi riavviare.

### Problemi incontrati alla prima installazione (2026-11-12)
- **Sottotensione**: `vcgencmd get_throttled` = `0x50005` sia con il RPi PowerPack V1.2 sia con alimentatore diretto (4,9 V al misuratore, < 1 A). Sotto carico (`apt`) il Wi-Fi si blocca: SSH risponde al ping ma non si collega e le connessioni cadono. Per questo `installa.sh` va lanciato staccato da SSH (`sudo systemd-run --unit=swim-installa bash ~/swimtimer-install/installa.sh`, log con `journalctl -u swim-installa`). Serve un alimentatore da 5,1 V / 2,5 A con cavo corto. Su Pi OS Lite l'icona del fulmine non compare.
- **cog**: senza `libgles2` il renderer di WPE va in crash (`Couldn't open libGLESv2.so.2`). Ora installato da `installa.sh`.
- **cog nel servizio**: `bwrap: Unexpected capabilities but not setuid` → SIGTRAP. Risolto con `CapabilityBoundingSet=` vuoto nella unit (nessuna capability; la sandbox di WebKit resta attiva).
- Con il pannello acceso: ~330 MB per cog e WebKit, 638 MB liberi su 905.

### Riserva: Chromium
Se cog non parte o disegna male: in `/etc/default/swimtimer` mettere `BROWSER=chromium`, poi `sudo bash ~/swimtimer-install/installa.sh` (installa `cage` + `chromium`). Più pesante: 300–450 MB di RAM contro ~100 MB.

### Comandi utili sul Pi
```
systemctl status swimtimer-host swimtimer-pannello swimtimer-kiosk
journalctl -u swimtimer-kiosk -b            # errori del browser
tail -f /home/swim/swimtimer-dati/ricevitore.log
cat /run/swimtimer/stato.json
sudo systemctl stop swimtimer-host          # libera /dev/ttyACM0 (es. per aggiornare il ricevitore)
```

### Prova del pannello sul PC
`python stazione/rpi/pannello.py --indirizzo 127.0.0.1 --porta 8781 --stato stazione/rpi/stato-prova.json`, poi aprire `http://127.0.0.1:8781/?prova` (`?prova` rinfresca l'ora dei dati fissi). `stato-prova.json` contiene solo tag e valori inventati. In `.claude/launch.json` c'è la configurazione `pannello-prova`.

I file `*.sh`, `*.service` e gli altri in questa cartella sono forzati a fine riga LF (`.gitattributes`): con CRLF non girerebbero sul Pi.
