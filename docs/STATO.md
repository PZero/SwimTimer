# Stato del progetto

**Ultimo aggiornamento:** 2026-11-07. Tutto è nel repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: prototipo; si prepara la **prima prova in piscina con video** per annotare gli eventi a mano e sviluppare poi i filtri.

## Fotografia
- **Scheda v0.6 "Rev0"** (`hardware/nrf52840/kicad/swimtag_v06.*`): 4 strati, 21,59 × 28,5 mm, DRC/ERC 0; uscite in `nextpcb/v0.6/` e `jlc/v0.6_swimtag_v06/`. Preventivo NextPCB 20 pz 216,39 $ con coupon, in attesa di Viviane.
- **XIAO nRF52840 Sense** (tag di prova, cella 100 mAh): ha il firmware `firmware/xiao-stream/` **0.5.0 caricata sulla tag; la 0.5.1 compila ma non è ancora caricata** (blu che si spegne a ogni tocco contato). Provati: risveglio, avvio della registrazione e lampo verde ogni 8 s.
  - **Risveglio:** 2 tocchi, LED blu, 2 tocchi. Il bug dei 2 tocchi era il bootloader che azzera `RESETREAS`: ora marca in `GPREGRET2` prima di ogni System OFF.
  - **Registra:** QSPI 2 MB, pagine da 256 B con CRC, delta int8, 208 Hz, acc ±16 g, gyro ±1000 dps, ~25 min con dati regolari; BLE spento; nuovi risvegli accodano un segmento. **Azzera:** 2 tocchi, blu, 6 tocchi, poi 2 di conferma. Nessuno stop a tocchi; quiete 180 s, memoria piena, batteria < 3,3 V.
  - **Scarico:** solo USB (`DUMP`), dalla pagina (Web Serial) o con `scarica.py`; formato `.swr` (decodificatori `swr.py` e `tools/swr.js`, 11 test Python verdi).
- **Pagina `tools/index.html`:** nuove schede **Registrazione** (USB, scarica, azzera, apri `.swr`) e **Annotazione** (grafici con zoom in alto, video sotto a 30 fps, sync con X sul 5° tocco, eventi B/R/V/F/P/A nel tempo del video, progetto JSON e CSV). La vecchia «Registrazioni» ora è «Reg. ESP32». Provata solo con dati simulati.
- **Display a bordo vasca** (da confermare): Raspberry Pi 4 + dongle nRF52840 + monitor 15,6" + power bank; mockup `tools/display.html`.
- Riquadro Batteria, tab XIAO, OTA via BLE (0.4.x) funzionano; il DFU Nordic legacy non è raggiungibile dal browser.
- **Scheda XIAO di prova guasta in parte:** regolatore 3,3 V morto, va con un diodo al silicio.

## Prossimi passi
1. Collegare la tag all'USB e caricare la 0.5.1 via BLE (modalità normale); provare il lampo blu.
2. **Prova a secco della 0.5.0:** registrare a casa (5 colpi, movimento, 3 min fermo), scaricare via USB, `node tools/parita_swr.mjs <file>` e controllare il CSV (az ≈ 1 g, 5 picchi, nessuna CRC errata).
3. Provare a mano le schede: Web Serial con la tag, un MP4 vero a 30 fps (passo di un fotogramma, X, eventi), salvataggio e riapertura del progetto.
4. Prima registrazione in piscina (5–10 min, tag sotto la cuffia, video H.264 a 30 fps), poi annotazione a mano di tutti gli eventi; **solo dopo** sviluppo e confronto dei filtri.
5. Aspettare Viviane (NextPCB) fino a mercoledì 2026-11-11; poi decidere l'ordine. Display: confermare l'architettura Pi + dongle.

## Problemi aperti
- 0.5.0/0.5.1: non verificati su hardware l'ordine FIFO gyro/acc, la cancellazione chip della flash (5–15 s), il QSPI senza SoftDevice, i consumi, la parità C++/Python del formato.
- Durata reale della registrazione con dati veri (compressione); 180 s di quiete contano anche prima di entrare in acqua.
- Nessun BLE/OTA durante la registrazione: aggiornare richiede l'USB. LED poco visibile sotto la cuffia.
- Rischio V-cut sulla v0.6; livello CHG_N con D4 borderline; brevetti (verifica di libertà di operare).
- Il BLE non attraversa l'acqua; custodia stagna da definire. Nessun test automatico oltre ai 11 del formato `.swr`.

## Decisioni in attesa dell'utente
- Data della prova a secco e della piscina; telefono e video H.264 30 fps; ordine NextPCB; scheda di scorta e multimetro; architettura display; test per l'Effort; Zephyr o Arduino. Vedi `docs/DOMANDE-APERTE.md` (33–44).

## Riferimenti
- Firmware tag: `firmware/xiao-stream/LEGGIMI.md` (grammatica dei tocchi, LED, formato `.swr`). Scheda: `hardware/nrf52840/progetto.md`. Pagina: `tools/index.html`, definizioni degli eventi in `docs/DESIGN.md`.
- Video: https://youtu.be/EVrdSybpnE4 (en), https://youtu.be/_2UzpOqblVI (it).
