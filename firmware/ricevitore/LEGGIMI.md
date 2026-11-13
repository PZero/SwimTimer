# Ricevitore 0.1.0 (XIAO nRF52840 Sense, central BLE)

Scarica i blocchi da 2 tag (firmware 0.6.1-0.6.4). **0.1.7** (2026-11-12, compilata: sketch 139308 B, RAM 58692 B, NON caricata): con la tag 0.6.4 in registrazione il collegamento **resta aperto** e i blocchi arrivano in streaming (la MAPPA della tag fa da keepalive e azzera il timeout di 15 s di silenzio); scrittura su CONTROLLO con semaforo proprio e `Bluefruit.setEventCallback` (il vecchio `#define private public` in `ric.h` è stato **rimosso**; ora anche lo stato GATT del WRITE_RSP e' controllato: una scrittura rifiutata non vale come inviata); parametri di connect() propri (`connParam` 7,5 ms); nuovo messaggio DIAGNOSI2 inoltrato come EVENTO `DIAGNOSI2 tag: chiave=valore ...`; EVENTO fino a 200 byte (le righe DIAGNOSI e `diario tag:` non vengono piu' troncate). **0.1.6**: dichiara PRONTO versione 2 (frammenti da 238 B con ricaduta a 128 B per le tag vecchie, messaggio DIAGNOSI inoltrato come EVENTO) e li passa a un host (PC o Raspberry Pi) via USB seriale. Formato dei frame: `PROTOCOLLO-USB.md`. Protocollo tag: `docs/SINCRONIZZAZIONE.md`.

**Caricare insieme tag 0.6.4 e ricevitore 0.1.7.** Il ricevitore 0.1.6 non conosce la MAPPA come keepalive: con la tag 0.6.4 in registrazione (collegamento aperto, niente FINE) la ignora, resta 15 s senza messaggi utili e chiude il collegamento ogni 15 s. **Timeout**: se l'host non conferma (OK) un blocco entro 20 s (`ATTESA_OK_MS` in `blocchi.cpp`) il ricevitore chiude il collegamento senza confermare alla tag, che reinvia; se la tag non manda nulla (nemmeno la MAPPA) per 15 s (`TIMEOUT_ATTIVA_MS` in `ble_rx.cpp`) chiude comunque.

**Regola:** la conferma alla tag parte solo dopo l'OK dell'host (blocco salvato e riletto dal disco). Senza OK la tag tiene il blocco. Senza host (nessun PRESENZA da 3 s) il ricevitore non si collega a nessuna tag.

## Compilare e caricare
Il toolchain non accetta spazi nel percorso: si compila da una copia in `C:\Temp\xs` (come per la tag).
```
xcopy /E /I /Y firmware\ricevitore C:\Temp\xs\ricevitore
cd C:\Temp\xs
arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense ricevitore
arduino-cli upload  --fqbn Seeeduino:nrf52:xiaonRF52840Sense -p COM19 ricevitore   (doppio reset per il bootloader se serve)
```
Non e' ancora stato caricato su nessuna scheda (versione 0.1.0 solo compilata).

## Host
```
pip install pyserial
python stazione/ricevitore_host.py --porta COM19 --cartella dati/        (sul Pi: --porta /dev/ttyACM0)
```
Salva in `dati/<id tag 8 hex>/tag.swr` (blocchi da 4096 B in coda) e `tag.idx` (`seq,offset,crc32,stato`), come il display; `dati/ricevitore.log` ha log ed eventi. `dati/` e' escluso da git.

## Cosa si vede
Una riga al secondo per tutte le tag: id, collegamento (non vista / vista / connessione / sicurezza / attiva), stato annunciato, RSSI, KB/s, blocchi in memoria sulla tag (dall'annuncio), ricevuti, confermati, salvati, scartati, batteria, memoria, ms dall'avvistamento al PRONTO. Gli eventi (connessione fallita, timeout, STOP, FINE...) escono con riga `EVENTO`. LED blu acceso = host presente.

Prima volta con una tag: pairing Just Works automatico (la tag deve accettare un nuovo bonding).
