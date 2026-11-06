# Changelog

## 2026-11-06
- **Board v0.6 "Rev0"** (nRF52840 tag, 4 layers, no BGA): MCP73831 charger, TPS22917 load switch, J1 left DNP, D4 + R2 added, D3 replaced by LC05CI. Design kept at 4 layers on purpose.
- **NextPCB order files** in `hardware/nrf52840/kicad/nextpcb/v0.6/` (Gerber, BOM, CPL, `NOTE_ORDINE.md`). Quote for 20 boards: 216.39 USD after coupon.
- **Panel generators** `crea_pannelli.py`, `cuci_massa.py`, `esporta_nextpcb.py`, `verifica_v06.py` in `hardware/nrf52840/kicad/`. Panels v0.5 3x1 and 2x1 were rejected by the Rev0 review.
- **XIAO documentation** in `hardware/xiao/`.
- **Charging base** redesigned as a slot-based base with NFC tokens (planned, see `docs/DECISIONI.md`).
- **README** now in English only (decision of 2026-11-06); no Italian copy. Working documents in `docs/` remain in Italian.
- Security check on the public repository (tracked and untracked files): no keys, tokens, passwords, `.env` or personal data. Absolute paths with the Windows user name were not found.

## 2026-11-04
- Allineamento del ramo della scheda con `main` del repository pubblico (firmware 0.4.3, pagina di analisi `tools/index.html`, documenti).
- **Scheda v0.5** (commit 01c6b8b), 21,59 x 28,0 mm (a 26-27,5 lo sbroglio a 2 strati non chiude), 2 strati: TPS22916C (U6) su VDD_IMU con ON su P0.04 e R7 1 MOhm, R6 su VDD_IMU, C5 4,7 uF 10 V, C7 tolto e C6 4,7 uF, R8 100 kOhm VIN-GND, TVS D3 PTVSLC3D5VB prima di D2, AO3401A (Q1) con R9 contro l'inversione della cella, TP8 VDD_IMU, IMU_MISO/CS su P0.08/P0.12 (XL1/XL2 liberi), serigrafia 1,0 mm. DRC 0, ERC 0 errori, `verifica_v05.py` 100/100 pin, 28 reti, 369 piste, 36 via. File JLC in `jlc/v0.5_swimtag_economica/` (v0.4 congelata). Costo stimato circa 125 EUR (sopra il tetto di 100): tagli possibili senza raggi X ~109, senza TVS ~105, senza header ~100,5.
- Revisioni esterne (Gemini, Copilot) raccolte in `hardware/nrf52840/revisioni_esterne.md` (ex `revisioni_esterne_v0.4.md`): modifiche applicate nella v0.5; S1 di Copilot (TS con 10 kOhm a massa) e' un falso positivo, confermato dal foglio TI; testo inviato in `revisione_esterna_v0.4.md`.
- Nuovi sfondi tecnici sulla v0.5 in `hardware/wallpaper_v0.5/` (20 PNG 1170 x 2532, stessi nomi della v0.4).
- README riscritto da zero (storia v0.1-v0.4, v0.4 in dettaglio, programmatore, galleria dei 20 sfondi, rigenerazione, flusso d'ordine JLC, roadmap, privacy).

## 2026-11-03
- v0.4 ricompattata a 21,59 x 26,0 mm (era 22,86): E73 a 0,3 mm dal bordo sinistro, pinout cambiato (CHG_N P0.20, LED P0.22, INT1 P0.26, INT2 P0.06). 2 strati, DRC 0, 313 piste, 29 via. 20,32 mm non chiude lo sbroglio.
- LED 0603 KT-0603R (C2286, basic) con anodo su VDD: -3,07 $ di caricamento extended. File JLC rigenerati; costo stimato circa 87-91 EUR per 2 schede.
- Verifica indipendente `hardware/nrf52840/verifica_v0.4.md` (65 test, 0 bloccanti, sul commit 8fd6cc0) e script `kicad/verifica_v04.py`; consiglia ENIG per BQ25101 (0,4 mm) e IMU (0,5 mm).
- Programmatore HAT per Raspberry Pi 3/4 in `hardware/programmatore/` (pogo sulle 7 piazzole, toner transfer, OpenOCD, ricarica con PTC e ponticello, PDF con stampe 1:1); DRC 0, ERC 0; non costruito.
- Generatore dei 20 sfondi tecnici in `hardware/wallpaper_v0.4/` (PNG 1170 x 2532 e 1080 x 2400).
- Decisione: regola "niente saldature" solo per il tag; il programmatore lo salda l'utente.

## 2026-11-02
- Nuova scheda v0.4 "economica" (budget <= 100 EUR): E73, LSM6DSV16X, flash 16 MB W25Q128JVSIQ (basic), BQ25101 con TS 10 k a massa, 1 LED, header batteria SMD 1,27 mm (C55213900), Schottky 1N5819WS sui contatti di ricarica, lettura batteria con VDDHDIV5. Tolti pressione, MAX17048, TPS22916C, vibratore, Tag-Connect, TVS, reset all'inserimento.
- 2 strati 0,8 mm HASL senza piombo, scheda 22,86 x 26 mm, DRC 0. Sotto: 5 pogo SWD e 2 contatti di ricarica su griglia 2,54 mm. File in `kicad/jlc/v0.4_swimtag_economica/`, disegno `ingombro_v0.4.svg`.

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
## 2026-10-26
- `tools/index.html`: card Batteria rifatta con grafico (finestra 1-10 min) di GPIO 1, GPIO 2 e tensione stimata a riposo; livello target in % impostabile con quanto manca (% e V); etichette "misurata" e "A riposo (stima)"; correzione in carica da 0,15 a 0,05 V (misura col tester: 3,84 V a riposo, 3,87 V in carica); la Demo simula anche il partitore 5V.
- Il progetto della scheda nRF52840 (KiCad, Gerber, BOM, v0.2) è ora nel repository privato `PZero/SwimTimer-nrf52840`; questo repository resta pubblico per GitHub Pages.
- GitHub Pages attivato: pagina online su https://pzero.github.io/SwimTimer/ con il firmware 0.4.3 pubblicato.
- Prototipo: batteria sostituita, interruttore generale montato, partitore verificato col tester. Il BMI160 è andato in latch-up dopo uno spegnimento brusco; si usa l'interruttore.
- Problema aperto: a sola batteria il tag non parte (LED rosso acceso, niente lampo blu né Bluetooth), diagnosi in corso.
- Firmware invariato (0.4.3); una 0.4.4 è stata provata e scartata.
- Nuovo `docs/LEZIONI-APPRESE.md`: 13 lezioni per la scheda nRF52840 e confronto con la v0.2.
- `hardware/schema.md`, `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati; README aggiornato.

## 2026-10-25 (sera)
- Tag, firmware 0.4.3 (`firmware/test-collegamenti`): corretto un difetto reale; il BMI160 restava a ±2 g (le scritture del fondo scala, fatte a sensore sospeso, andavano perse) mentre la pagina leggeva ±16 g, quindi da fermo si vedevano 8 g invece di 1 g. Ora fondo scala e frequenze si impostano a sensori accesi e vengono riletti (fino a 5 tentativi); in seriale "BMI160: fondo scala ±16 g verificato".
- `tools/index.html`: avviso negli eventi se da fermo il modulo dell'accelerazione non vale circa 1 g (scala incoerente tra tag e pagina).
- Problemi aperti: batteria del tag letta a 3,5 V (quasi scarica, circa 2%), da verificare col tester; vibrazione sospesa in attesa di un modulo con transistor (GPIO 5 libero). La 0.4.3 non è ancora provata sul tag.
- README aggiornato alla versione 0.4.3; `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md`, `hardware/bom.md` aggiornati.

## 2026-10-25
- Tag, firmware 0.4.2 (`firmware/test-collegamenti`): accelerometro a ±16 g e 100 Hz; registrazione di sessioni su LittleFS con doppio tap (avvio) e triplo tap (fine); tap riconosciuti dai campioni (salto oltre 0,8 g, escluso con giroscopio oltre 300 °/s); scaricamento via Bluetooth o USB.
- Aggiornamento del firmware via Bluetooth (due copie del programma, `partitions.csv`), ritorno automatico alla versione precedente, marcatore `SWIMTAG_VER=x.y.z;` nel .bin; stessa versione rifiutata, precedente con conferma.
- Stato esteso del tag (batteria da partitore su GPIO 1, pin 5V su GPIO 2, motivo dell'ultimo riavvio), sblocco automatico del bus I2C, LED RGB come riscontro. Caratteristiche BLE: dati `7a1e0002`, stato `7a1e0003`, comandi `7a1e0004`, risposte `7a1e0005`, OTA `7a1e0006`, versione `7a1e0007`.
- `tools/index.html` (nuova pagina di analisi): schede "Dal vivo" e "Registrazioni", batteria, orientamento 3D, radar con scia di 15 s, interpretazione, eventi, traccia con zoom, finestre Firmware e LED, Demo; Bluetooth (Chrome, Edge, Bluefy su iPhone) o USB. `tools/assi.html` resta la vecchia pagina.
- `tools/index.html`: corretto `versioneDaBin`, che si fermava alla prima occorrenza di `SWIMTAG_VER=%s;` (formato) e non trovava il marcatore vero; ora riconosce il marcatore anche dopo il formato.
- `.github/workflows/pages.yml`: compila il firmware (arduino-cli, core esp32 3.3.12) e pubblica pagina, `firmware/tag.bin` e `firmware/tag.json` su GitHub Pages. Da attivare in Settings, Pages, Source: GitHub Actions.
- `docs/RICERCA-ALGORITMI.md`: ricerca sugli algoritmi IMU per il nuoto; base utile il brevetto FORM US 11833392; nessun dataset pubblico con IMU sulla testa.
- Hardware: partitori 2×100 kΩ su GPIO 1 e GPIO 2; BMI160 a ±16 g (`hardware/bom.md`, `hardware/schema.md`).
- `.gitignore`: escluso `versione.h`, scritto dalla CI.
- Stato: 0.4.0, 0.4.1 e 0.4.2 compilano; la 0.4.2 non è provata sul tag; frequenza reale in registrazione circa 44 Hz (FIFO del BMI160 da fare). Display invariato.
- README aggiornato: funzionalità, canali BLE, stato e comandi, pagina di analisi, aggiornamento del firmware, CI, privacy, brevetti, roadmap.
- `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati.

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
