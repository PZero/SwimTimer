# xiao-stream - XIAO nRF52840 Sense, streaming IMU via BLE, registrazione in vasca e sincronizzazione con il display

Firmware di prova: annuncia "SwimTag", invia l'IMU alla tab XIAO di `tools/index.html`, manda un log, si sospende (comando, fermo prolungato) e si risveglia con 4 tocchi o con l'USB, e si aggiorna via Bluetooth dalla finestra «Firmware del tag».

**0.6.0** (2026-11-10, provata a secco su 2 tag: 666 blocchi in 15 min, 0 errori): sincronizzazione con il display (`docs/SINCRONIZZAZIONE.md`), BLE sempre acceso anche in registrazione, memoria ad anello (**formato 3**), nome e colore della tag, **LED spenti a batteria** (accesi solo con l'USB alimentata, anche il lampeggio del BLE), seq mai riusato (`/seq.bin`). Vedi la sezione «Sincronizzazione con il display (0.6.0)» in fondo.

**0.5.4** (2026-11-08): corrente di carica 100 mA (P0.13 basso, resta in System OFF). Per le prove si usa una cella da 1000 mAh: da vuota servono ~10-12 h.

## Compilazione e caricamento via USB
Core `Seeeduino:nrf52` 1.1.13 (non mbed, con Bluefruit), FQBN `Seeeduino:nrf52:xiaonRF52840Sense`.
Indice schede: `https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json`.

Il toolchain ARM **non accetta percorsi con spazi**: compilare una copia in un percorso senza spazi. Dalla 0.6.0 lo sketch ha piu' file (`swr_formato.h`, `swr_anello.h`, `swr_sync.h`, `flash_qspi.h`): vanno copiati tutti.

    mkdir C:\Temp\xs\xiao-stream ; copy xiao-stream.ino,*.h C:\Temp\xs\xiao-stream\
    arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense --build-path C:\Temp\xs\build C:\Temp\xs\xiao-stream
    arduino-cli upload -p COMxx --fqbn Seeeduino:nrf52:xiaonRF52840Sense --input-dir C:\Temp\xs\build

Dalla 0.6.0 la compilazione dice: sketch ~172 KB (21 %), RAM globale ~34,8 KB (14 %); il limite dell'app per l'OTA e' 356 KB.

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
- **Risveglio (0.4.5/0.5.0)**: il primo doppio tap hardware (2 tocchi) fa partire il chip. **All'uscita da System OFF l'IMU perde l'alimentazione e resta cieco per circa 0,5 s** (bootloader, avvio, riaccensione e riconfigurazione): il 3o e il 4o tocco dati a ritmo normale cadono in questo buco, misurato sulla tag. Per questo, dopo `RISVEGLIO_PAUSA_MS` (150 ms), `risveglioQuattroTap()` accende il **LED blu come invito** a dare i tocchi di conferma e li conta in software (tocco singolo, `TAP_SRC` bit SINGLE_TAP, antirimbalzo 100 ms) entro `RISVEGLIO_FINESTRA_MS` (3000 ms); il blu si spegne a fine sequenza. Sequenza **2 tocchi, blu, 2 tocchi** = risveglio (log `risveglio 4 tap`). Falso risveglio (solo 2 tocchi): torna in System OFF senza BLE, USB ne' log, scrivendo in `GPREGRET2` `MARCA_FALSO` (0xC0 | tocchi visti), che al boot vale come marca di sleep ed e' visibile nel log `marca %02X` (provato: `marca C0`). WHO_AM_I e' ritentato 4 volte da 40 ms. Il risveglio da USB (VBUS) resta immediato.
- **Bug del risveglio con 2 tocchi: causa vera (0.5.0)**: il bootloader Adafruit azzera `RESETREAS` prima di lanciare l'app, quindi `causaReset` risultava sempre "accensione" (RESETREAS 0, anche dopo un OTA) e `risveglioQuattroTap()` non veniva mai chiamata: la tag partiva al primo doppio tap. La correzione di 0.4.3 (conferma in software) era giusta ma non veniva eseguita. Ora, prima di **ogni** System OFF, si scrive la marca `MARCA_SLEEP` (0xB7) in `GPREGRET2` (`sd_power_gpregret_*` con il SoftDevice, il registro diretto senza; il bootloader non lo tocca); in `setup()` la si legge e la si azzera, e se c'e' la marca, non c'e' VBUS e la causa non e' USB, `causaReset = 1` (doppio tap). Nel log compare `marca B7 vbus 0`. (Fonte: prove sulla tag del coordinatore, versione 0.4.4 provvisoria.)
- **Niente sospensione automatica con la seriale aperta**: se un programma sul PC tiene aperta la porta USB (CDC con DTR attivo, `Serial` vero) la sospensione per quiete non scatta e nel log compare una volta `seriale aperta: niente sospensione`. Restano attivi il comando `SLEEP` esplicito e la protezione batteria bassa (esclusa comunque con la USB). Idem se la pagina e' collegata via BLE con comandi negli ultimi 120 s e durante un OTA.
- **Falso risveglio**: da sveglio per circa 40 ms (avvio) + 40 ms (IMU) + 250 ms + 2500 ms + qualche ms = **~2,9 s**, a regime CPU ferma in attesa (da misurare con un amperometro).
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

## Modalita' vasca (0.5.0): registrazione su flash (dalla 0.6.0 il BLE resta acceso solo per annunciarsi e sincronizzare)
Per la prova in piscina: il BLE non attraversa l'acqua, quindi la tag registra l'IMU grezzo sulla flash QSPI; i dati si scaricano a bordo vasca dal display (0.6.0) oppure a casa via USB.

### Uso (tocchi, tag senza USB)
| Gesto | Effetto |
|---|---|
| **REGISTRA**: 2 tocchi, **LED blu** (si spegne un attimo a ogni tocco contato, dalla 0.5.1), 2 tocchi | sveglia e **registra subito**. Se in memoria c'e' gia' una registrazione, si **accoda** come nuovo segmento (una sola sessione, piu' risvegli). |
| **AZZERA**: 2 tocchi, **LED blu**, 6 tocchi, poi rosso lampeggiante e 2 di conferma entro 4 s | **azzera** la memoria (LED rosso lampeggiante durante i 4 s; senza conferma non succede nulla). Cancellazione 5-15 s. |
| tag ferma | **stop** per quiete: 180 s consecutivi "abbastanza fermi" (soglie `QUIETE_GYRO_DPS`/`QUIETE_ANGOLO_GRADI`), poi chiusura e sospensione. |
Nessuno stop a tocchi. Altri stop: memoria piena, batteria sotto 3,3 V (3 letture ogni 5 s). Il blu si accende 150 ms dopo il risveglio e resta acceso finche' la sequenza non e' finita: finisce quando passano 900 ms senza un nuovo tocco (la registrazione parte ~1 s dopo l'ultimo), e il conteggio decide: 6 tocchi dopo il blu = azzera, da 2 a 5 = registra (2 non si scambia con 6). Finestra totale per il 1o tocco dopo il blu: 3 s. Con la **USB collegata** i tocchi danno la modalita' normale (BLE, OTA, log) e non si registra. **0.6.0**: se la flash contiene dati del **formato 1** (0.5.x) la registrazione **non parte** e i dati non si cancellano da soli: 4 lampi viola (rosso+blu); si scaricano con `DUMP` e poi si azzera con la sequenza AZZERA (6 tocchi + conferma). Un contenuto non riconosciuto (ne' formato 1 ne' 2) si cancella da solo, come in 0.5.x. Nota: i 180 s di quiete contano anche prima di entrare in acqua.

### LED (RGB a tre canali discreti attivi bassi: LED_RED P0.26, LED_GREEN P0.30, LED_BLUE P0.06; non e' un NeoPixel)
| Stato | Segnale |
|---|---|
| registrazione avviata | 3 lampi verdi da 150 ms |
| in registrazione | 1 lampo verde da 30 ms ogni 8 s |
| memoria > 80% non confermata (0.6.0) | 2 lampi gialli (rosso+verde) ogni 8 s |
| batteria < 3,5 V | 1 lampo rosso ogni 8 s |
| memoria piena di blocchi non confermati (stop) / azzera rifiutato | 5 lampi rossi |
| flash in formato 1 (non si registra) | 4 lampi viola (rosso+blu) |
| batteria < 3,4 V al risveglio (non registra) | 3 lampi rossi da 200 ms |
| batteria < 3,3 V (stop e chiusura) | 3 lampi rossi da 200 ms, poi IMU spento: si riparte solo con l'USB |
| errore (IMU, flash, I2C) | 10 lampi rossi rapidi |
| conferma azzeramento | rosso lampeggiante a 5 Hz per 4 s; poi azzerata = 3 lampi blu; gia' vuota = 1 lampo blu |
| flash formattata (altro contenuto) | blu fisso durante la cancellazione |
**Dalla 0.6.0 i LED sono spenti a batteria** (decisione 2026-11-10: sotto la cuffia non si vedono e consumano): la tabella vale solo con l'USB alimentata. I tempi delle sequenze (tocchi, finestre) restano uguali; lo stato si vede sul display e sulla pagina.

### Cosa si registra
208 Hz, accelerometro +-16 g (488 ug/LSB), giroscopio +-1000 dps (35 mdps/LSB), FIFO dell'LSM6 in modo continuo (a 208 Hz tiene ~1,6 s: copre le scritture in flash). Il giroscopio **non e' corretto del bias** (si stima a casa dai tratti fermi). Ordine nel FIFO secondo il datasheet: G poi XL; nel file: ax ay az gx gy gz. Controllo a secco: a faccia in su az ~ +1 g.
Se mai il FIFO va in overrun, riparte e la pagina successiva ha il flag di interruzione.

### Formato .swr 1 (0.5.x; specifica completa in `swr_formato.h`; il formato 2 della 0.6.0 e' descritto piu' sotto)
Flash = sequenza di **pagine da 256 byte** scritte una sola volta, in ordine (nessuna cancellazione in registrazione, nessun filesystem). Intestazione da 16 byte: tipo (segmento 0xA5 / dati 0xD1 / chiusura 0xE0), numero di pagina, `millis` del primo campione, mV, temperatura, flag, segmento, **CRC16** dell'intera pagina. Pagina dati: primo campione **assoluto** (12 B) poi per campione 6 differenze int8, oppure un **escape** (0x80 + 12 B assoluti) se una differenza esce da -127..127: ogni pagina si decodifica da sola. Capacita': 8192 pagine; con dati regolari ~6 B/campione (~2 x rispetto ai 12 B grezzi: ~25 min), con molti escape meno (13 B al campione). Una pagina di segmento a ogni risveglio, una di chiusura (motivo, campioni).
La fine si ricostruisce dall'ultima pagina valida (ricerca binaria della prima pagina libera): se la batteria muore senza chiusura i dati scritti restano e il segmento risulta "senza chiusura". Al risveglio, con pagina 0 non valida e non vuota, la flash viene azzerata (prima installazione).
Il driver `flash_qspi.h` usa direttamente `nrfx_qspi` (la libreria utente `Adafruit_SPIFlash` 5.x rompe la compilazione di Bluefruit).

### Scarico (USB, modalita' normale) e analisi
Comandi sulla seriale (115200): `MEM`, `DUMP`, `ERASE`. `DUMP` risponde `SWR1 <pagine>`, le pagine binarie, `END <pagine>` (flash in formato 1) oppure, dalla 0.6.0 con la flash in formato 2, `SWR2 <blocchi>`, i blocchi non vuoti da 4096 byte in ordine fisico (confermati compresi: lo scarico USB legge anche cio' che e' gia' sul display), `END <blocchi>`; durante il dump niente log sulla seriale. `swr.py` e `scarica.py` riconoscono i due formati (primo byte 0xA5 o 0xB1), riordinano i blocchi per seq, saltano le intestazioni, trattano le pagine 0xFF come vuote e segnalano i buchi di seq. `MEM` in formato 3: `K mem formato3 da_validare N confermati N liberi N anomali N seq N`. `ERASE` cancella tutto (anche non confermato: e' un comando esplicito da USB).

    pip install pyserial
    python scarica.py scarica COM5        # salva registrazioni/AAAAmmdd_HHMMSS.swr e il CSV
    python scarica.py converti file.swr   # solo conversione
    python scarica.py mem COM5 ; python scarica.py azzera COM5
    python test_swr.py                    # test su dati inventati (23 test; anche `python -m unittest test_swr` dalla cartella)

CSV: `seg,pagina,n,t_s,ax_g..gz_dps,mV` (`--grezzo` per gli LSB). `t_s` e' in secondi dall'inizio del segmento (dai `millis` di pagina, regolarizzati con una regressione sulle pagine contigue); tra segmenti diversi il tempo non e' collegabile. Il programma segnala pagine corrotte, interruzioni, segmenti senza chiusura. I `.swr` e i CSV sono dati di salute: ignorati da git.

### Limiti noti (0.5.0, non provata su hardware)
- Non collaudata sulla tag: ordine G/XL del FIFO, lettura a burst da `FIFO_DATA_OUT`, cancellazione chip, QSPI senza SoftDevice e consumi vanno verificati a secco.
- Il codificatore C++ (`swr_formato.h`) e' specchiato in Python (`swr.py`) ma non e' stato eseguito su PC (nessun compilatore host): i test provano il formato in Python; la parita' C++/Python e' per costruzione e va confermata scaricando una registrazione vera.
- Il tempo dei campioni nel firmware e' stimato (±1 campione); il bias del giroscopio non e' misurato.
- Nessun BLE/OTA in vasca: aggiornare il firmware richiede l'USB. Il sensore `LED` puo' non essere visibile sotto la cuffia.
- Consumo stimato (da misurare): ~1,5-2 mA registrando, ~0,1-0,2 mA in sospensione.

## Sincronizzazione con il display (0.6.0)
Specifica: `docs/SINCRONIZZAZIONE.md` (§1-§3, §7, §8). Riferimento binario lato display: `firmware/display-sync/protocollo.h` (i messaggi di `swr_sync.h` devono combaciare byte per byte).

### Cosa fa
- **BLE sempre acceso**, anche in registrazione (prima in vasca era spento): annuncio connectable ogni **200 ms** con i dati produttore del §7 (22 byte: id, stato, batteria, % memoria non confermata, blocchi in attesa, ultimo seq, secondi di registrazione, errori, colore) e, nella scan response, il nome. **2 collegamenti periferici** contemporanei (display + pagina web). La tag **non interpreta il movimento**: l'annuncio e' sempre lo stesso, con i dati che cambiano.
- **Nome** nella scan response: il nome scelto dall'utente (max 12 caratteri ASCII) oppure `ST-xxxx` (ultime 4 cifre dell'id). **Cambia rispetto alla 0.5.x** (prima `SwimTag`): la pagina `tools/index.html` non deve piu' filtrare per nome `SwimTag`. Nella scan response c'e' anche il servizio `7a1e0001` se il nome e' di al massimo 11 caratteri.
- **Stati annunciati**: 0 vado in sonno (~2 s prima di dormire; se la memoria e' piena prima 2 s di stato 4; se un display sta scaricando si aspetta la sua FINE/STOP, al massimo 60 s), 1 pronta (modalita' normale), 2 registra, 4 memoria piena, 5 errore (IMU o flash, anche flash in formato 1), 6 sincronizza.
- **Servizio `7a1e0101`**: CONTROLLO `0102` (scrittura, **solo collegamento cifrato**: `SECMODE_ENC_NO_MITM`, bonding Just Works con le impostazioni predefinite di Bluefruit: bond, LESC se il chip lo permette), DATI `0103` (notifiche inviate direttamente al SoftDevice con `sd_ble_gatts_hvx`: se la coda radio e' piena non si blocca, riprova al giro dopo), STATO SYNC `0104` (lettura + notifica ogni 2 s, 151 byte, senza cifratura, la pagina non puo' confermare). MTU 247, coda di 4 notifiche, evento da 7,5 ms; PHY 2M e DLE li negozia il display (la libreria Bluefruit accetta le richieste del centrale).
- **Scarico**: dopo PRONTO la tag manda MAPPA, poi il blocco non confermato piu' vecchio (BLOCCO + 32 FRAMMENTI), al massimo 2 blocchi trasmessi e non confermati; **attende la CONFERMA senza timer**; non rinvia mai da sola; RIPETI rimette in coda il blocco; STOP chiude; quando non resta niente da confermare manda FINE (e riparte da sola se si chiude un nuovo blocco mentre il display e' ancora collegato). **Il blocco aperto non si invia** (niente anteprima): il display riceve solo blocchi chiusi (~3 s di ritardo al massimo).
- **Conferma**: CONFERMA(seq, crc32) -> la tag **ricalcola il CRC32 dalla flash** e solo se coincide scrive la parola 252..255 a 0x00, **rilegge l'intera intestazione** (deve risultare confermata e ancora valida) e risponde CONFERMATO. Altrimenti ERRORE (1 CRC diverso, 2 seq sconosciuto, 3 flash).
- **La registrazione non si ferma durante lo scarico**: tutto gira nel `loop` a pezzi (al massimo ~10 messaggi per giro, ogni frammento e' una lettura da 128 byte dalla flash; il CRC32 di un blocco = 16 letture da 256 byte). Il FIFO dell'IMU (1,6 s) viene servito almeno ogni 20 ms mentre si scarica (40 ms altrimenti). Le operazioni piu' lunghe sono la **cancellazione di un settore** (45 ms tipici, fino a 300 ms; una per blocco, solo quando la memoria ha fatto il giro) e la scrittura. **Misure per verificarlo**: la pagina di chiusura di ogni segmento ora contiene (byte 24..30) il massimo intervallo fra due letture del FIFO in ms, gli overrun, il massimo tempo di apertura di un blocco (cancellazione compresa) e i blocchi confermati nella sessione; `swr.py` le mostra nel riassunto (`tempi: ...`). Se il massimo intervallo si avvicina a 1600 ms il FIFO va in overrun.

### Memoria ad anello (formato 3)
- Flash da 2 MB = **512 blocchi da 4 KB** (= settore). Pagina 0 del blocco = intestazione `0xB1` (seq u32 globale, id tag, **parola 252..255 = conferma** fuori dal CRC16; il formato 2 la teneva nel byte 16, vedi sotto), pagine 1-15 = pagine del formato 1 (segmento 0xA5, dati 0xD1, chiusura 0xE0, numero di pagina fisica). Capacita' utile 15/16 della flash (~7680 pagine). CRC32 del blocco = IEEE sui 4096 byte con la conferma a 0xFF (anche nei frammenti inviati). Il seq non si riusa mai: prima di ogni cancellazione totale si salva il massimo in `/seq.bin` (InternalFS), senza file si parte da 1000.
- All'avvio si leggono le 512 intestazioni (~100 ms): seq massimo, blocchi da validare, confermati, liberi, anomali (contenuto non riconosciuto: non si toccano mai). Un blocco e' "aperto" solo in RAM mentre si registra; dopo un riavvio i blocchi scritti a meta' sono semplicemente "da validare" (le pagine non scritte restano 0xFF = vuote e valide). Ogni segmento (ogni risveglio) comincia un blocco nuovo; il blocco si chiude quando e' pieno o a fine segmento.
- Nuovo blocco: il **libero successivo** (in ordine ad anello); se non c'e', il **confermato piu' vecchio** (cancellato solo ora); se sono tutti non confermati: **stop `SWR_STOP_PIENA`** (5 lampi rossi, stato 4). **Mai si scrive su un blocco non confermato.** Il blocco libero si verifica tutto 0xFF prima dell'uso (cancellazione interrotta da un'interruzione di corrente), altrimenti si cancella.
- Con memoria piena la pagina di chiusura del segmento non si scrive (il segmento risulta senza chiusura per `swr.py`; il motivo e' nell'annuncio, stato 4) e l'ultima pagina dati parziale (< 0,2 s) puo' andare persa.
- Il seq riparte da 1 dopo un azzeramento totale (`ERASE` o AZZERA a tocchi): il display riconosce un seq gia' visto con CRC diverso come anomalia e lo segnala.
- **Flash in formato 1 trovata all'avvio**: non si cancella, non si registra (vedi sopra); `DUMP` la legge ancora come prima. In 0.5.x un contenuto estraneo veniva azzerato da solo; **dalla 0.6.0 mai**: 4 lampi viola (solo con USB), niente registrazione, si azzera con `ERASE` o con i tocchi.

### Nome e colore (comandi sulla caratteristica `7a1e0004`, solo in modalita' normale)
`NOME,<testo>` (max 12 caratteri ASCII stampabili, vuoto = cancella; risposte `K nome <testo>`, `X nome troppo lungo (max 12)`, `X nome carattere non valido`), `COLORE,<0-9>` / `COLORE,-1` (`K colore <n>`, `X colore fuori campo (0-9 o -1)`); `COLORE` senza argomento mostra il valore. Salvati in InternalFS `/nome.bin` (come `/vcal.bin`: restano dopo riavvio e OTA); il nome cambia subito la scan response, il colore e' il byte 21 dell'annuncio. In registrazione (vasca) tutti i comandi rispondono `X registrazione in corso`.

### Consumi stimati del BLE in registrazione (stime, NON misure)
Annuncio a 200 ms, +4 dBm (3 canali per evento, con le finestre di ascolto per scan request e connessione): ~50-100 uA medi; con 0 dBm circa un quarto in meno. In piu': 2 stop/start dell'annuncio ogni 4 s (trascurabile) e il loop sveglio ogni 40 ms come prima. Rispetto ai ~1,5-2 mA della registrazione e' un +3-5 %: da **misurare con un amperometro in serie alla batteria**, prima e dopo. Collegata al display (7,5-15 ms) la tag assorbe ~0,5 mA in piu', con picchi di qualche mA durante lo scarico (pochi secondi a ogni sosta).

### Cosa NON e' provato (0.6.0: solo compilata, mai eseguita su hardware)
- Memoria SRAM del SoftDevice con 2 collegamenti, MTU 247, 4 notifiche e tabella attributi da 3 KB: se `Bluefruit.begin` fallisce il BLE resta spento ma la registrazione parte comunque (log `BLE begin KO`; in modalita' normale si vede nel pannello log). Da verificare al primo avvio.
- **Lezione 2026-11-10 (formato 2 → 3):** la Puya della XIAO, riprogrammando una parola da 4 byte gia' scritta, la **sostituisce** (non fa l'AND dei bit): scrivere `00 FF FF FF` nei byte 16..19 cancellava i byte 17..19 del seq. Intestazioni non valide, seq riusati, 185 anomalie al display (nessun dato perso: erano blocchi gia' confermati). Dal formato 3 la conferma ha una parola tutta sua (252..255) e dopo la scrittura si rilegge l'intestazione intera.
- Ordine e tempi reali: massimo intervallo fra letture FIFO con scarico in corso e con cancellazioni, throughput (atteso 30-80 KB/s con PHY 2M, mai misurato), tempo da «fermo» a «collegato».
- Bonding Just Works con il display ESP32 (CONTROLLO richiede la cifratura; se il display non fa il pairing la scrittura viene rifiutata), PHY 2M e DLE, stop/start dell'annuncio con 1 collegamento attivo (il secondo collegamento si riannuncia dal loop), nome lungo nella scan response, collegamento contemporaneo di display e pagina.
- Il codificatore C++ del formato 2 (`swr_formato.h`, `swr_anello.h`) e' specchiato in `swr.py` e provato lato Python (25 test, compresi la parola di conferma isolata e la lettura del formato 2); non c'e' un compilatore host: la parita' C++/Python va confermata con uno scarico USB reale. Nessun test automatico sulla logica dell'anello e della macchina a stati (solo compilazione).
- La batteria non e' stata considerata per lo scarico: la tag non si spegne da sola finche' un display sta scaricando (max 60 s dopo lo stop).
