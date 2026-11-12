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
