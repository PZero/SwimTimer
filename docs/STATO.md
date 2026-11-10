# Stato del progetto

**Ultimo aggiornamento:** 2026-11-10 (notte). Repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: **sincronizzazione tag → display funzionante a secco** con 2 tag; ora si punta a una versione «super stabile» di tag e display prima di nuove funzioni.

## Fotografia
- **Protocollo di sincronizzazione** (`docs/SINCRONIZZAZIONE.md`): blocchi da 4 KB; la tag spinge il più vecchio non confermato; il display lo scrive su SD, lo rilegge, e solo allora conferma; nessun rinvio a tempo; finestra 2; seq mai riusato (anche dopo azzeramento, base in `/seq.bin`).
- **Tag XIAO 0.6.0** (`firmware/xiao-stream`): flash ad anello di 512 blocchi, **formato `.swr` 3** (conferma nella parola 252..255: la flash Puya *sostituisce* la parola da 4 byte invece di fare l'AND); BLE sempre acceso (annuncio 200 ms, 2 collegamenti, CONTROLLO cifrato); nome (≤ 11 car.) e colore impostabili; **LED spenti a batteria**; memoria non riconosciuta mai cancellata da sola. Due tag in prova (id `4A510689` e `447B0247`, la seconda nuova).
- **Display T-RGB** (`firmware/display-sync`, Adafruit GFX, no LVGL): 3 spicchi da 120°, mappa dei 512 blocchi per tag, nome e colore, batteria con la stessa curva LiPo della pagina, segnale in % (scala provvisoria), mai in standby; scrittore SD unico; log degli avvii in `/swim/avvii.txt`. Modalità DEMO con 3 tag simulate.
- **Prova a secco 2026-11-10:** 2 tag × 15 min: 666 blocchi salvati e confermati, 0 errori CRC, 0 anomalie, memoria di entrambe ad anello, nessun riavvio del display. Velocità vista fino a 8 KB/s (i dati nascono a ~1,25 KB/s).
- **Pagina `tools/index.html`**: riquadro Sincronizzazione (stato, mappa, nome e colore), lettura `.swr` formati 1/2/3. **Usare Edge**: Chrome su Windows tiene un collegamento BLE appeso.
- Guasto trovato e corretto oggi: con il formato 2 la conferma rovinava il seq → intestazioni non valide, seq riusati (185 anomalie al display). Dati non persi (copie in `C:\Temp\swimtimer-backup`, fuori dal repo).
- **SD del display verificata dal PC** (2408 blocchi delle due tag vere, 0 buchi di seq, 0 overrun, 1,27 M campioni decodificati). Il display ora scrive **un file per tag** (`/swim/<id>/tag.swr`); la pagina apre più `.swr` insieme e li unisce per seq (i file `sNNNN.swr` di oggi tornano interi). Cartelle DEMO nella SD (`1000a3f2`, `20007c10`, `3000e95b`) = dati inventati, da cancellare.
- Correzioni dopo la prova: **Sospendi** funziona anche in registrazione (motivo di fine 6 «comando SLEEP»); la pagina chiede nome e colore alla tag; `MEM`/`DUMP` via USB nel formato 3. Firmware aggiornato su entrambe le tag.
- Invariati: scheda v0.6 (preventivo NextPCB 216,39 $, attesa Viviane fino a mer 11/11), analisi video/IMU del test 1, app online, video v3.

## Prossimi passi
1. **Stabilità** (priorità dell'utente): annuncio ERRORE prima del sonno (memoria da azzerare, batteria, IMU) visibile sul display; timeout sul `connect()` e watchdog del display; la pagina chiude il collegamento BLE alla chiusura.
2. Provare dalla pagina (Edge, Ctrl+F5): scarico USB formato 3, apertura di più file, Sospendi in registrazione.
3. Tarare il segnale: RSSI a 10 cm, 1 m, 3 m e tag ruotata; 0% = dove lo scarico smette.
4. Prova di durata 30–60 min e casi limite (display spento a metà blocco, SD tolta, memoria piena, display + pagina insieme); misure FIFO/overrun nella pagina di chiusura.
5. Poi: release 0.6.0 (`release/xiao.bin`), metodo filtri (fase 3), seconda seduta in vasca, decisione NextPCB.

## Problemi aperti
- Antenna del T-RGB: a 10 cm solo −57/−64 dBm; il margine a bordo vasca è da misurare.
- Display: `connect()` della libreria BLE senza timeout (può bloccare la scansione).
- Con i LED spenti una tag che rifiuta di partire non lo segnala a nessuno (finché non c'è l'annuncio ERRORE).
- Riavvii del display visti in giornata: probabilmente caricamenti e USB staccata; ora registrati con il motivo.
- Consumi del BLE in registrazione: solo stimati (+50–100 µA).
- Restano: «Prova Inventata» da cancellare in Messaggi; fine video del 9/11; una sola sessione in vasca; privacy dei dati; rischio V-cut v0.6; brevetti.

## Decisioni in attesa dell'utente
- Scala del segnale dopo le misure; ordine NextPCB; programma delle sedute e piscina; architettura display definitiva (T-RGB per 1–3 nuotatori, Pi per 10?); Zephyr o Arduino. Vedi `docs/DOMANDE-APERTE.md`.

## Riferimenti
- Sincronizzazione: `docs/SINCRONIZZAZIONE.md`, mockup `docs/img/mockup-stato-tag.png`. Tag: `firmware/xiao-stream/LEGGIMI.md`. Display: `firmware/display-sync/LEGGIMI.md`. Pagina: `tools/index.html`. Scheda: `hardware/nrf52840/progetto.md`. Analisi: `analisi/`.
