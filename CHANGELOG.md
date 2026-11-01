# Changelog

## 2026-11-01
- Tag v0.3 di collaudo, variante 1c: scheda 26 x 30 mm, 4 strati 0,8 mm, una faccia, tag finito circa 29 x 33 x 9,2 mm. Netlist 36/36, DRC 0 errori, 609 piste, 80 via. File JLC in `hardware/nrf52840/kicad/jlc/v0.3_swimtag_collaudo/`.
- Modulo Ebyte E73 al posto del Raytac (stock 0); cella Ampul 401012 (40 mAh, PCM, 1 C) su JST SH; sensori su interruttore di carico TPS22916C; MAX17048 su secondo bus I2C; TS del BQ25101 da GPIO; 2 x 47 uF; 0 ohm tra cella e circuito; Tag-Connect TC2030-NL per SWD (VDD solo come riferimento); piazzole di prova; contatti di ricarica a 4,2 mm per una futura base a più posti.
- Vibratore non montato sui 2 tag di collaudo (nessun motore SMD montabile da JLC a rifusione); restano pilotaggio e piazzole MOT+/MOT-.
- Nuovi: 8 wallpaper tecnici PNG 1170 x 2532 in `hardware/nrf52840/wallpaper/png/`, script `genera_wallpaper.py` e `genera_pdf.py`, PDF di progetto `hardware/nrf52840/SwimTag_v0.3_collaudo.pdf` (14 pagine); `ingombro.svg` generato dal PCB reale.
- Costo stimato 2 tag JLC circa 120-130 $ più cella e cavo Tag-Connect (non ancora ordinato, anteprima JLC da fare).
- README: sezione nRF52840 aggiornata alla v0.3; `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati.

## 2026-10-25 / 2026-10-26
- Scheda su misura nRF52840 (`hardware/nrf52840/`): studio dei progetti SlimeVR, distinta (`bom.md`), progetto (`progetto.md`) e ingombro in scala (`ingombro.svg`).
- Progetto KiCad generato da script (`kicad/`, `dati_scheda.py` come unica fonte): v0.1, poi v0.2 con scheda 17,5 × 22,5 mm a 4 strati.
- Sbroglio automatico con Freerouting 2.5.0 (Java 25): DRC 0 errori.
- Verifiche sui datasheet (ST AN5763, TE MS5837, TI BQ25101, Raytac) con 4 correzioni, registrate in `verifiche.md`.
- Protezione dei contatti di ricarica (TVS SD05 e Schottky B5819WS) e reset all'inserimento nella custodia.
- File per JLC in `kicad/jlc/`: Gerber (zip), BOM, CPL, render, PDF dello schema.
- Documenti aggiornati: `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md`.
- README: nuova sezione sulla scheda nRF52840, mappa delle cartelle e roadmap.

## 2026-10-24
- Impostazione del progetto: struttura, agenti, comandi `/stato` e `/fine-sessione`, documenti iniziali.
- Analisi dell'idea iniziale (tag BLE + display a bordo vasca) in `docs/IDEA.md`.
- Logica di partenza e arrivo (spinta, calma, virata parziale) e logiche aggiuntive da valutare in `docs/IDEA.md`.
- Distinta componenti (`hardware/bom.md`) e schema del tag prototipo (`hardware/schema.md`).
- Tag di prova: ESP32-S3 SuperMini + BMI160, batteria LiPo sui pad BAT+/BAT-. Sensore verificato su tutti gli assi.
- `firmware/test-collegamenti`: test del bus I2C del BMI160 e invio delle righe dati a circa 50 Hz.
- `tools/assi.html`: pagina Web Serial (Chrome/Edge) con valori e grafici dei 3 assi.
- README completato con architettura, hardware, firmware, uso e roadmap.
- Display scelto: LilyGO T-RGB. Schema del tag riscritto con la batteria sui pad BAT (TP4056 come alternativa scartata).
- `firmware/test-collegamenti`: servizio GATT BLE (25 Hz) e annuncio `SwimTag` con i dati (20 Hz) per il display. Libreria BLE del core esp32 3.3.12, NimBLE-Arduino scartata perché va in crash.
- `tools/assi.html`: pulsante "Collega via Bluetooth" (Web Bluetooth, Chrome/Edge su desktop e Android) accanto a quello USB.
- `firmware/display-prova` (nuovo): firmware di prova per il display LilyGO T-RGB 2,8" (GT911). Riceve gli annunci del tag senza collegarsi, doppio framebuffer, corona dei 3 assi, cronometro di prova. Driver `src/trgb` adattato da LilyGo-T-RGB 1.0.5 (MIT).
- Distinta e stato: display 2,8" con touch GT911 verificato; `docs/STATO.md`, `docs/DECISIONI.md` e `docs/DOMANDE-APERTE.md` aggiornati.
- README aggiornato: canali BLE e flusso dei dati, firmware del display, compilazione con le librerie, struttura delle cartelle, roadmap.
- `firmware/display-prova`: corretta la ricaduta immediata in sonno profondo (sottrazione senza segno in overflow, ora confronti con segno); risveglio anche dal pulsante BOOT (GPIO 0); pull-up RTC su GPIO 1 durante il sonno; motivo dell'avvio mostrato per 2 s.
- `hardware/bom.md`: aggiunte LiPo 1000 mAh del display (caricatore TP4065) e accelerometro I2C da collegare (SDA 8, SCL 48).
- Problema aperto: il display a batteria, senza USB, non si accende.
