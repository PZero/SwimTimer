# Ricevitore 0.1.0 (XIAO nRF52840 Sense, central BLE)

Scarica i blocchi da 2 tag (firmware 0.6.1 e 0.6.2). **0.1.6**: dichiara PRONTO versione 2 (frammenti da 238 B con ricaduta a 128 B per le tag vecchie, messaggio DIAGNOSI inoltrato come EVENTO) e li passa a un host (PC o Raspberry Pi) via USB seriale. Formato dei frame: `PROTOCOLLO-USB.md`. Protocollo tag: `docs/SINCRONIZZAZIONE.md`.

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
