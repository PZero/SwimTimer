# display-sync: display di sincronizzazione (LilyGO T-RGB)

Riceve dalle tag (fino a 3 insieme) i blocchi `.swr` da 4 KB, li salva sulla microSD, li **rilegge dalla SD** e solo allora manda la CONFERMA che permette alla tag di riscrivere il blocco. Specifica: `docs/SINCRONIZZAZIONE.md` (§3, §4, §6, §7). Schermata: `docs/img/mockup-stato-tag.png`.

## Compilare e caricare
```
pio run -d firmware/display-sync -e display                          # tag reali (BLE)
pio run -d firmware/display-sync -e demo                             # 3 tag simulate, senza BLE
pio run -d firmware/display-sync -e display -t upload --upload-port COMx
```
Ambiente identico a `display-prova` (espressif32@6.9.0, core Arduino 2.0.17, Adafruit GFX 1.11.11, SensorLib 0.2.3; niente LVGL, niente NimBLE). `demo` serve a provare schermata e SD: tre tag inventate producono blocchi validi che passano dalla stessa pipeline (verifica, coda SD, conferma, mappa); la tag 1 sbaglia un blocco ogni 4 (prova RIPETI) e ogni tanto sparisce, la tag 2 va in SPENTA dopo ~70 s. La SD e' vera: senza scheda si vede l'errore e le tag non scaricano.

## Struttura
| file | contenuto |
|---|---|
| `protocollo.h` | costanti, UUID, formati del §7, CRC32/CRC16, annuncio, comandi |
| `stato.h/.cpp` | stato condiviso (mutex), assegnazione degli spicchi |
| `ricezione.h/.cpp` | parser delle notifiche, buffer 2 x 4 KB per tag in PSRAM |
| `sd_scrittore.h/.cpp` | task unico (core 0): verifica, scrive, rilegge, indice, CONFERMA |
| `ble_sync.cpp` | scansione, collegamenti, bonding, PRONTO (solo `display`) |
| `demo.cpp` | tag simulate (solo `demo`) |
| `ui.h/.cpp` | schermata (core 1), `scheda.h` = oggetto `panel` |
| `display-sync.ino` | setup/loop |

## Struttura sulla SD
```
/swim/sessione.txt                 numero di avvio del display (+1 a ogni avvio), usato in avvii.txt
/swim/avvii.txt                    una riga per avvio con il motivo (accensione, watchdog, panic, calo di tensione...)
/swim/<id 8 hex>/tag.swr           TUTTI i blocchi della tag, da 4096 B, in coda (si legge da solo, anche dopo riavvii
                                   del display; fino al 2026-11-10 un file sNNNN.swr per avvio: aprirli insieme nella pagina)
/swim/<id 8 hex>/tag.idx           righe  seq,offset,crc32,scritto|confermato|anomalia
/swim/<id 8 hex>/tag.anomalia      stesso seq con CRC diverso (si salva e si segnala)
```
Nessuna conferma se la SD manca, ha meno di 50 MB liberi, o la scrittura/rilettura fallisce: STOP con motivo e errore a schermo. Doppioni (stesso seq e CRC) = solo CONFERMA; per riconoscerli, alla prima connessione di una tag si rileggono i suoi `.idx` (fino a 1024 voci).

## Da sapere
- Il CRC16 di ogni pagina e' verificato come nel formato 2 (`paginaValida()`): pagina tutta 0xFF = vuota = valida; pagina 0xB1 (intestazione di blocco) = CRC16 con il campo conferma considerato 0xFF (formato 2: byte 16; formato 3: parola 252..255); le altre come nel formato 1.
- Nome e colore della tag: la scansione e' ATTIVA (serve la scan response); il nome locale (max 12 caratteri ASCII) sostituisce `ST-xxxx` nello spicchio (carattere piu' piccolo se lungo) e il colore (byte 21 dell'annuncio, tavolozza del §7) tinge sfondo, arco e pallino; senza colore (0xFF) resta quello dello spicchio. La demo assegna nomi e colori inventati a 2 tag su 3.
- Il nome della funzione ESP-IDF e' `esp_ble_gap_set_prefered_phy` (con una sola "r" in piu' o in meno rispetto alla specifica).
- Senza MAPPA (tag mai collegata) i 512 blocchi sono mostrati tutti "liberi": la mappa arriva solo al primo collegamento.

## Cosa NON e' provato (nulla e' stato caricato sulla scheda)
- Solo compilato. Mai eseguito: schermata, SD, demo.
- BLE: 3 collegamenti insieme, MTU 247, PHY 2M, intervallo 7,5-15 ms, bonding/cifratura Just Works, `connect()` con scansione fermata e poi riavviata, riconnessione con `BLEClient` riusato, banda reale.
- SD: montaggio 1 bit con CS sull'espansore, `usedBytes()` (la prima scansione FAT puo' durare secondi), rilettura realmente dalla scheda e non dalla cache, tremolio dello schermo durante le scritture (contesa PSRAM).
- Tempi del ridisegno (~5 Hz previsti) e leggibilita' dei testi sul 2,1".
- Batteria della tag: stessa curva LiPo di `tools/index.html`. Segnale in % dall'RSSI mediato, scala provvisoria −95…−55 dBm (a 10 cm si misurano −57/−64 dBm), da tarare. Ogni avvio con il motivo in `/swim/avvii.txt`; il riepilogo sulla seriale ogni 5 s riporta RSSI, stato, blocchi salvati, errori e anomalie per tag.
