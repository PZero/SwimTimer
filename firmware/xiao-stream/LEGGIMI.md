# xiao-stream - XIAO nRF52840 Sense, streaming IMU via BLE

Firmware di prova: annuncia "SwimTag", invia l'IMU alla tab XIAO di `tools/index.html`, manda un log, si sospende (comando, fermo prolungato) e si risveglia con 4 tocchi o con l'USB, e si aggiorna via Bluetooth dalla finestra «Firmware del tag».

## Compilazione e caricamento via USB
Core `Seeeduino:nrf52` 1.1.13 (non mbed, con Bluefruit), FQBN `Seeeduino:nrf52:xiaonRF52840Sense`.
Indice schede: `https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json`.

Il toolchain ARM **non accetta percorsi con spazi**: compilare una copia in un percorso senza spazi.

    mkdir C:\Temp\xs\xiao-stream ; copy xiao-stream.ino C:\Temp\xs\xiao-stream\
    arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense --build-path C:\Temp\xs\build C:\Temp\xs\xiao-stream
    arduino-cli upload -p COMxx --fqbn Seeeduino:nrf52:xiaonRF52840Sense --input-dir C:\Temp\xs\build

L'upload entra da solo nel bootloader (touch a 1200 baud); la porta cambia (COM13 -> COM15). Se non entra: doppio tap su reset (la scheda in sospensione va svegliata prima).

## Aggiornamento via Bluetooth (OTA 0006, stesso protocollo dell'ESP32)
Il servizio DFU Nordic legacy e' sulla blocklist di Web Bluetooth (Chrome/Edge), quindi l'aggiornamento usa un OTA nostro sulla caratteristica `7a1e0006`, identico a quello dell'ESP32: comando `OTA,<byte>,<crc32 hex>,<versione>[,forza]` su 0004, poi scritture su 0006 = `uint32 offset LE + dati`, poi `OTAEND`. Risposte su 0005: `K ota pronto,<blocco>`, `X ota offset,N` (ripartire da N), `K ota ok`, errori `X ota ...`.

**Cosa si carica**: il `.bin` dell'applicazione, cioe' l'ELF convertito con objcopy (parte da 0x27000, `SP` iniziale in RAM 0x2000xxxx). Il core non lo produce da solo (genera .hex e .zip): si ottiene con

    arm-none-eabi-objcopy -O binary xiao-stream.ino.elf xiao-0.4.x.bin

(l'objcopy e' in `%LOCALAPPDATA%\Arduino15\packages\Seeeduino\tools\arm-none-eabi-gcc\9-2019q4\bin`). Il binario contiene `SWIMTAG_VER=<versione>;` e `SWIMTAG_BOARD=xiao-nrf52840;`: il tag rifiuta (`X`) qualsiasi immagine senza la firma della scheda o con vettori non validi (es. il .bin dell'ESP32), con dimensione fuori da 1 KB..356 KB, della stessa versione o precedente (senza `forza`).

### Mappa della flash (nRF52840, 1 MB)
| Indirizzi | Contenuto | Fonte |
|---|---|---|
| 0x00000-0x26FFF | MBR + SoftDevice S140 7.3.0 | `nrf52840_s140_v7.ld` del core: `FLASH ORIGIN = 0x27000` |
| **0x27000** (`APP_BASE`) - fine app | applicazione (~140 KB, fine ~0x4A000) | idem |
| **0x80000** (`STAGING_BASE`) - 0xEC FFF | **staging** dell'immagine ricevuta (max 356 KB = `APP_MAX_BYTE`, anche limite per l'app) | scelto: dopo l'app, prima di InternalFS |
| 0xED000-0xF3FFF | InternalFS di Bluefruit (bonding, 7 pagine) | `InternalFileSystem.cpp`: `LFS_FLASH_ADDR 0xED000` |
| 0xF4000-0xFDFFF | bootloader Adafruit | `dfu_types.h`: `BOOTLOADER_REGION_START 0xF4000` |
| 0xFE000 / **0xFF000** | MBR params / **impostazioni del bootloader** (`BL_SETTINGS`) | `dfu_types.h` |

### Come funziona
1. I dati arrivano in un anello da 8 KB (la callback BLE non tocca la flash) e il `loop` li scrive nello staging con `flash_nrf5x_write` (API del core sopra `sd_flash_write/erase`, compatibile col SoftDevice). Il CRC32 si calcola mentre arrivano.
2. A `OTAEND`: controllo di lunghezza, CRC32, vettori (SP in RAM, reset dispari dentro l'immagine), firma scheda e marcatore di versione. Se qualcosa non torna: scartato, `X ...` e riga di log.
3. Se tutto torna: `K ota ok`, dopo 0,8 s disconnessione, `sd_softdevice_disable`, interrupt spenti e routine `ramInstalla` **tutta in RAM** (sezione `.data.ramfunc`, verificato col disassemblato: nessuna chiamata a funzioni in flash): cancella le pagine dell'app, copia lo staging con NVMC, rilegge e confronta, riscrive le impostazioni del bootloader e fa il reset di sistema.
4. **Bootloader (fonte: `bootloader.c` e `dfu_types.h` di Adafruit_nRF52_Bootloader, letti da GitHub)**: all'avvio `bootloader_app_is_valid()` guarda `bank_0 == BANK_VALID_APP (1)` e, **se `bank_0_crc != 0`, calcola il CRC16 su `bank_0_size` byte** e lo confronta; con `crc == 0` il controllo e' disattivato. Su questa scheda la pagina impostazioni dopo un upload USB contiene `bank_0 = 1, crc = 0, size = dimensione dell'app` (il firmware lo legge e lo scrive nel log all'avvio: `bl bank0 ok crc 0000 = dim N`). L'OTA scrive esattamente lo stesso formato (`bank_0=1`, `bank_0_crc=0`, `bank_1=0xFF`, `bank_0_size` = byte arrotondati a 4), quindi il bootloader accetta la nuova app. Se la copia non verifica, le impostazioni non vengono toccate e il bootloader (versione di riferimento) resta in modalita' DFU.
5. **Recupero**: il bootloader non viene mai modificato; se la nuova app non parte, doppio tap su reset (LED che pulsa, unita' XIAO-SENSE o porta DFU) e caricamento via USB.

Ogni fase finisce nel log del tag (`ota: 143008 byte, v0.4.1`, `ricevuto 25/50/75/100%`, `crc ok`, `installazione`, errori) e quindi nel pannello «Log tag». Durante l'OTA il flusso IMU e la sospensione automatica sono fermi. Velocita' misurata con Windows/Realtek: ~1 KB/s (scritture con risposta), cioe' circa 2,5 minuti.

Prova da PC senza browser: `python ota_prova.py ota xiao-0.4.1.bin 0.4.1` (script `bleak`, stesso protocollo della pagina; vedi sotto in «Prove»).

## Protocollo (little endian)
- Servizio `7a1e0001-5b1d-4c8e-9f3a-1d2c3b4a5e60`.
- DATI `7a1e0002-...` notify, 16 byte a 25 Hz: `uint32 millis`, `int16 ax,ay,az` (2048 LSB/g, +-16 g), `int16 gx,gy,gz` (16,4 LSB/dps). Ogni valore e' la **media** dei campioni a 208 Hz nei 40 ms dall'ultimo pacchetto (niente aliasing); il giroscopio e' gia' privo di bias.
- STATO `7a1e0003-...` read+notify, 1 Hz, 8 byte: `uint16 mV`, `uint8 flag` (bit0 USB presente o in carica, bit1 IMU ok, bit2 registrazione=0, bit4 g16=1), `uint8 causa` (0 accensione, 1 doppio tap, 3 watchdog, 5 software, 6 lockup, 7 USB, 8 pin reset), `uint32 millis`. mV = 0 se la cella non c'e'.
- COMANDI `7a1e0004-...` write (testo, max 64): `SLEEP`, `LIST` (risponde `Z`), `OTA,...`, `OTAEND`, `OTAABORT`; altro -> `X non supportato`.
- RISPOSTE `7a1e0005-...` notify: primo byte = tipo. **`G` + testo = riga di log**; `Z` fine elenco; `K`/`X` risposte ai comandi.
- OTA `7a1e0006-...`, VERSIONE `7a1e0007-...` (`xiao-0.4.x`). Servizio DFU Nordic (BLEDfu) ancora presente per l'app nRF Connect.

## Batteria (0.4.2)
- **STATO a 12 byte** (compatibile: i primi 8 sono invariati; la pagina riconosce la XIAO dalla lunghezza 12): `[8] flag2` (bit0 VBUS presente, bit1 carica completata, bit2 in carica, bit3 batteria bassa < 3,4 V), `[9] int8` temperatura del die in gradi (`sd_temp_get`), `[10-11] uint16` fattore del partitore x1000. Stati: in carica = VBUS e ~CHG basso; carica completata = VBUS e ~CHG alto con cella presente; a batteria = niente VBUS.
- **Lettura ADC**: 24 letture a 1 ms, media delle 16 centrali (scarta i picchi causati dalle trasmissioni radio).
- **Taratura**: comando `VCAL,<mV letti col tester>` calcola il fattore del partitore e lo salva in flash (file `/vcal.bin` nell'InternalFS di Bluefruit, 0xED000-0xF3FFF: non tocca ne' lo staging OTA 0x80000 ne' le impostazioni del bootloader). `VCAL` senza argomento mostra il fattore, `VCAL,0` ripristina 2,96. Risposta `K vcal 2.xxx`, errori `X vcal ...`.
- **Batteria bassa**: log `batteria bassa` sotto 3,4 V a batteria; sotto 3,3 V per 5 letture di fila sospensione "solo USB" (IMU spento). Mai con la USB collegata.

## Log
Buffer circolare in RAM di 50 righe (44 caratteri): boot e causa di reset (con RESETREAS grezzo), IMU ok/errore, bias del giroscopio, stato del bootloader, batteria/USB/carica (a ogni cambio e ogni 60 s), connessioni, sospensione, OTA. Alla connessione (quando la pagina abilita le notifiche su 0005) viene rimandato tutto il buffer; la pagina mostra le righe nel pannello «Log tag». Le stesse righe escono sulla seriale.

## Sospensione e risveglio con 4 tocchi
`SLEEP` (pulsante «Sospendi») oppure 60 s "abbastanza fermo" (vedi costanti `QUIETE_*`). Il firmware spegne il giroscopio, accelerometro a 416 Hz +-2 g in basso consumo, doppio tap hardware (`TAP_CFG=0x8F` con **LIR**, `TAP_THS_6D`=soglia, `INT_DUR2=0x7F`, `WAKE_UP_THS=0x80`, `MD1_CFG=0x08` -> INT1 = P0.11), poi System OFF con sense alto su P0.11.
- **Risveglio**: il primo doppio tap fa partire il chip. Prima di USB e BLE, `risveglioQuattroTap()` riaccende l'IMU (all'uscita da System OFF i pin tornano al default e l'IMU perde alimentazione e configurazione), la riconfigura, ignora `RISVEGLIO_PAUSA_MS` (150 ms) di residui, azzera il latch e attende fino a `RISVEGLIO_FINESTRA_MS` (2000 ms) un **secondo doppio tap** (INT1 + `TAP_SRC` bit DOUBLE_TAP). Se arriva: avvio normale e log `risveglio 4 tap`. Altrimenti torna subito in System OFF con la stessa configurazione, senza BLE, USB ne' log. Il risveglio da USB (RESETREAS.VBUS) resta immediato.
- **Niente sospensione automatica con la seriale aperta**: se un programma sul PC tiene aperta la porta USB (CDC con DTR attivo, `Serial` vero) la sospensione per quiete non scatta e nel log compare una volta `seriale aperta: niente sospensione`. Restano attivi il comando `SLEEP` esplicito e la protezione batteria bassa (esclusa comunque con la USB). Idem se la pagina e' collegata via BLE con comandi negli ultimi 120 s e durante un OTA.
- **Falso risveglio**: da sveglio per circa 40 ms (avvio) + 40 ms (IMU) + 150 ms + 2000 ms + qualche ms = **~2,3 s**, a regime CPU ferma in attesa (da misurare con un amperometro).
- **Soglia del doppio tap**: `TAP_SOGLIA` in cima allo sketch (12 = 0,75 g, 1 LSB = 62,5 mg). Piu' basso = piu' sensibile. La durata massima fra i due tap di un doppio tap e' in `INT_DUR2` (DUR=7, ~0,5 s a 416 Hz).
- **Consumo in sospensione: stima, non misura.** nRF52840 in System OFF ~1 uA; LSM6DS3TR-C con solo accelerometro a 416 Hz in basso consumo ~100-200 uA (termine dominante: il tap hardware richiede almeno 416 Hz); flash QSPI e BQ25101 pochi uA. Totale atteso ~0,1-0,2 mA, cioe' 8-16 giorni con la cella da 40 mAh. Da misurare con un multimetro in serie alla batteria.

## Orientamento: perche' la testa si storceva e cosa e' cambiato
1. **Aliasing (causa principale)**: prima ogni pacchetto era un campione istantaneo a 25 Hz del giroscopio; una rotazione veloce cade fra due campioni e l'integrale e' sbagliato. Ora il firmware campiona a 208 Hz e manda la media.
2. **Bias del giroscopio**: ~1-2 dps da fermo si integrano in 10-20 gradi al minuto. Misurato al boot e ri-stimato quando il tag e' fermo (finestre da 0,5 s, variazione sotto 2,5 dps, |a| fra 0,9 e 1,1 g, media entro 4 dps dal bias noto).
3. **Assi/segni**: da verificare con «Verifica assi» (Z a +1 g a faccia in su, Y a +1 g con l'USB-C in alto).
4. **Imbardata (yaw)**: senza magnetometro non e' osservabile; la deriva si azzera con «Ricentra».

## Prove
- `C:\Temp\xs\ota_prova.py` (venv con `bleak`): `python ota_prova.py log` legge versione e log; `python ota_prova.py ota file.bin 0.4.1` esegue l'OTA come la pagina.
- Il partitore batteria (2,96) va confermato con un multimetro: letti ~4,0 V con la cella collegata e USB.
