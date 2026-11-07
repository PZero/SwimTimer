# xiao-stream - XIAO nRF52840 Sense, streaming IMU via BLE (0.2.0)

Firmware di prova: annuncia "SwimTag", invia l'IMU alla tab XIAO di `tools/index.html`, manda un log, si sospende con doppio tap e si aggiorna via Bluetooth.

## Compilazione e caricamento via USB
Core `Seeeduino:nrf52` 1.1.13 (non mbed, con Bluefruit), FQBN `Seeeduino:nrf52:xiaonRF52840Sense`.
Indice schede: `https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json`.

Il toolchain ARM **non accetta percorsi con spazi**: compilare una copia in un percorso senza spazi.

    mkdir C:\Temp\xs\xiao-stream ; copy xiao-stream.ino C:\Temp\xs\xiao-stream\
    arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense --build-path C:\Temp\xs\build C:\Temp\xs\xiao-stream
    arduino-cli upload -p COMxx --fqbn Seeeduino:nrf52:xiaonRF52840Sense --input-dir C:\Temp\xs\build

L'upload entra da solo nel bootloader (touch a 1200 baud); la porta cambia (COM13 -> COM15). Se non entra: doppio tap su reset.
Seriale 115200: stampa le righe di log e una riga acc/gyro al secondo.

## Aggiornamento firmware via Bluetooth
La compilazione crea gia' il pacchetto DFU: `C:\Temp\xs\build\xiao-stream.ino.zip` (lo fa il core Seeed con `adafruit-nrfutil dfu genpkg`, e' lo stesso file che usa l'upload USB). In alternativa, a mano:

    adafruit-nrfutil dfu genpkg --dev-type 0x0052 --sd-req 0xB6 --application xiao-stream.ino.hex pacchetto.zip

(il valore di `--sd-req` e' quello di `build.sd_fwid` in `boards.txt` del core).

**Dal browser NON funziona (verificato 2026-11-07):** Chrome/Edge mettono nella blocklist di Web Bluetooth il servizio DFU Nordic legacy `00001530-1212-efde-1523-785feabcd123` (niente verifica di firma), quindi la pagina non lo vede. Il pulsante «Aggiorna firmware» della tab XIAO e' nascosto; il codice JS del DFU legacy resta nella pagina (provato solo contro un bootloader simulato in node).

Come aggiornare via Bluetooth oggi: app **nRF Connect for Mobile** (Nordic, Android/iOS) → collegati a "SwimTag" → pulsante **DFU** → scegli il .zip. Il bootloader resta sempre recuperabile via USB con doppio tap su reset.
Per il tag definitivo: Zephyr + MCUboot + aggiornamento SMP, compatibile con Web Bluetooth, con firma e ritorno automatico alla versione precedente.

## Protocollo (little endian)
- Servizio `7a1e0001-5b1d-4c8e-9f3a-1d2c3b4a5e60`.
- DATI `7a1e0002-...` notify, 16 byte a 25 Hz: `uint32 millis`, `int16 ax,ay,az` (2048 LSB/g, +-16 g), `int16 gx,gy,gz` (16,4 LSB/dps). Ogni valore e' la **media** dei campioni a 208 Hz nei 40 ms dall'ultimo pacchetto (niente aliasing); il giroscopio e' gia' privo di bias.
- STATO `7a1e0003-...` read+notify, 1 Hz, 8 byte: `uint16 mV`, `uint8 flag` (bit0 USB presente o in carica, bit1 IMU ok, bit2 registrazione=0, bit4 g16=1), `uint8 causa` (0 accensione, 1 doppio tap, 3 watchdog, 5 software, 6 lockup, 7 USB, 8 pin reset), `uint32 millis`. mV = 0 se la cella non c'e'.
- COMANDI `7a1e0004-...` write (testo): `SLEEP` sospende; `LIST` risponde `Z` (nessuna registrazione); altro -> risposta `X`.
- RISPOSTE `7a1e0005-...` notify: primo byte = tipo. **`G` + testo = riga di log** (`secondi.decimi messaggio`, es. `12.3 bat 3987 mV usb 1 carica 1`); `Z` fine elenco; `X` errore.
- VERSIONE `7a1e0007-...` read, stringa (`xiao-0.2.0`). Servizio DFU Nordic `00001530-1212-efde-1523-785feabcd123` (BLEDfu).

## Log
Buffer circolare in RAM di 50 righe (44 caratteri): boot e causa di reset (con RESETREAS grezzo), IMU ok/errore, bias del giroscopio, batteria/USB/carica (a ogni cambio e ogni 60 s), connessioni, sospensione, comandi non supportati. Alla connessione (quando la pagina abilita le notifiche su 0005) viene rimandato tutto il buffer; la pagina mostra le righe nel pannello «Log tag» con l'orario del PC. Le stesse righe escono sulla seriale.

## Sospensione e risveglio
Comando `SLEEP` (pulsante «Sospendi») o nessun altro modo per ora. Il firmware: spegne il giroscopio, accelerometro a 416 Hz +-2 g in basso consumo, tap hardware (`TAP_CFG=0x8E`, `TAP_THS_6D`=soglia, `INT_DUR2=0x7F`, `WAKE_UP_THS=0x80` doppio tap, `MD1_CFG=0x08` doppio tap su INT1 = P0.11), poi System OFF dell'nRF52840 con sense alto su P0.11. Risveglio = riavvio completo: doppio tap, inserimento USB (RESETREAS.VBUS) o reset; la causa e' nel log e nel byte `causa`.
- **Soglia del doppio tap**: `TAP_SOGLIA` in cima allo sketch (12 = 0,75 g, 1 LSB = 62,5 mg). Piu' basso = piu' sensibile. La durata massima fra i due tap e' in `INT_DUR2` (DUR=7, ~0,5 s a 416 Hz).
- **Consumo in sospensione: stima, non misura.** nRF52840 in System OFF senza RAM ritenuta circa 1 uA; LSM6DS3TR-C con solo accelerometro a 416 Hz in basso consumo circa 100-200 uA (e' il termine dominante: il tap hardware richiede almeno 416 Hz); flash QSPI e BQ25101 pochi uA. Totale atteso ~0,1-0,2 mA, cioe' circa 8-16 giorni con la cella da 40 mAh. Va misurato con un multimetro in serie alla batteria.

## Orientamento: perche' la testa si storceva e cosa e' cambiato
1. **Aliasing (causa principale)**: prima ogni pacchetto era un campione istantaneo a 25 Hz del giroscopio; una rotazione veloce (decine di gradi in poche decine di ms) cade fra due campioni e l'integrale e' sbagliato. Ora il firmware campiona a 208 Hz e manda la media: la somma dei pacchetti conserva l'integrale della velocita' angolare.
2. **Bias del giroscopio**: ~1-2 dps da fermo si integrano in 10-20 gradi al minuto. Il firmware lo misura nel primo secondo dopo il boot (se il tag e' fermo) e lo ri-stima di continuo quando e' fermo (finestre da 0,5 s, variazione sotto 2,5 dps, |a| fra 0,9 e 1,1 g, media entro 4 dps dal bias noto). La pagina ha comunque la sua stima del residuo.
3. **Assi/segni**: da verificare con «Verifica assi» (Z a +1 g a faccia in su, Y a +1 g con l'USB-C in alto). Un segno sbagliato fa tirare la correzione della gravita' dalla parte opposta e lascia un'inclinazione. Non e' controllabile da firmware: si corregge `XIAO_ASSE_USB` o il segno di Z nella pagina.
4. **Imbardata (yaw)**: senza magnetometro non e' osservabile, la gravita' non la corregge. La deriva e' inevitabile; si azzera con «Ricentra» (o «Calibra»/«Annuisci»).

## Prove da fare
- Misura da seriale (scheda ferma): `acc` ~2048 LSB di modulo, `gyro` vicino a 0 dopo la calibrazione.
- Batteria: il partitore (2,96) va confermato con la cella reale e un multimetro.

## Sospensione automatica (0.3.0)
Se il tag resta fermo per `INATTIVITA_MS` (60 s) va in sospensione da solo, come col comando `SLEEP`, e nel log scrive `fermo da 60 s: sospensione`. "Fermo" significa: giroscopio sotto `MOTO_GYRO_DPS` (8 °/s) su tutti gli assi e accelerometro che non cambia più di `MOTO_ACC_G` (0,08 g) tra due pacchetti. Si riattiva col doppio tap o inserendo la USB. Al banco: se la scheda dorme non compare sulla USB, quindi per caricare un firmware via cavo prima svegliala con un doppio tap. `INATTIVITA_MS 0` disattiva la funzione.
