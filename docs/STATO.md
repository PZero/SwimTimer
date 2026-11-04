# Stato del progetto

**Ultimo aggiornamento:** 2026-11-04 — **scheda v0.5 (TPS22916C, TVS, protezione inversione cella, 100 kΩ VIN-GND, TP8 VDD_IMU; 21,59 × 28 mm, DRC 0, ERC 0 errori, file JLC rigenerati in `jlc/v0.5_swimtag_economica/`; costo ~125 € con montaggio Standard, tetto 100 € non raggiunto)**; 2026-11-01 — Fase 1 (prototipo ESP32 sul tavolo) + scheda su misura nRF52840: **tag v0.3 di collaudo sbrogliato** (ramo `claude/scheda-nrf52840-08642d`, solo sul repository privato `PZero/SwimTimer-nrf52840`, mai su `origin`).


## Ripresa (aggiornata il 2026-11-04)
- **Fatto (v0.5):** TPS22916C per l'IMU (R6 su VDD_IMU, ON su P0.04 con 1 MΩ), C5 4,7 µF 10 V, C7 tolto e C6 4,7 µF, 100 kΩ VIN-GND, TVS C41408025 sul contatto VIN, AO3401A contro l'inversione della cella, TP8 VDD_IMU, IMU_MISO/CS su P0.08/P0.12 (XL1/XL2 liberi), serigrafia ≥ 1 mm, zona senza piste F.Cu sotto il modulo. DRC 0, parità 0, ERC 0 errori, `kicad/verifica_v05.py` 100/100. Dettagli in `hardware/nrf52840/progetto.md` (blocco "Revisione v0.5").
- **Da fare prima dell'ordine:** decisione sul costo (~125 € con i coupon, vedi tagli in `progetto.md`), anteprima JLC (rotazioni di U2, U4, U6, Q1 SOT-23, D1, D2, D3, J1; JLC accetta l'header e le parti "Standard only"), scelta HASL/ENIG, prova a banco di Q1 con cella dritta e invertita, prova di portata (antenna a 0,3 mm dal bordo, scheda 28 mm).
- Non rigenerati: `hardware/wallpaper_v0.4/genera.py` (20 sfondi) e PDF del programmatore (le piazzole TP1–TP7 non sono cambiate, quindi l'adattatore vale ancora; TP8 non serve al programmatore).
- Da cancellare a mano: cartella temporanea `C:\swt_chk`.

## Fatto
- Repository pubblico `PZero/SwimTimer`; template, agenti, comandi; analisi in `docs/IDEA.md`.
- **Tag** (ESP32-S3 SuperMini + BMI160, arduino-cli, core esp32 3.3.12), firmware **0.4.3** in `firmware/test-collegamenti`:
  - ±16 g e 100 Hz (impostati a sensori accesi e riletti); flash con due copie del programma e ~1,9 MB di LittleFS (~40 min a 50 Hz).
  - Doppio tap = inizio registrazione, triplo tap = fine (rilevamento software, poco affidabile: ~1 volta su 10).
  - BLE con dati, stato, comandi, OTA e versione; stessi comandi via USB. Aggiornamento via Bluetooth con ritorno automatico.
  - Sblocco del bus I2C, LED RGB (GPIO 48), motivo dell'ultimo riavvio, partitori su GPIO 1 (batteria) e GPIO 2 (pin 5V).
  - Batteria sostituita e **interruttore generale** montato; partitore verificato col tester (3,91 V letti = 3,91 V misurati).
- **Pagina** `tools/index.html`, online su https://pzero.github.io/SwimTimer/ (Pages attivo, firmware 0.4.3 pubblicato):
  - "Dal vivo" (batteria, 3D, radar, interpretazione, eventi, grafici) e "Registrazioni"; calibrazione automatica, finestre Firmware e LED, Demo.
  - Card batteria nuova: grafico 1–10 min di GPIO 1, GPIO 2 e tensione stimata a riposo, livello target in % con quanto manca; correzione in carica 0,05 V (misurata).
- **Display** LilyGO T-RGB (pace clock a 4 lancette, sonno e risveglio): invariato.
- `docs/RICERCA-ALGORITMI.md` (algoritmi) e `docs/LEZIONI-APPRESE.md` (13 lezioni del prototipo per la scheda miniaturizzata).
- **Prototipo** (invariato, dettagli in `hardware/bom.md`, `hardware/schema.md`): tag ESP32-S3 SuperMini + BMI160 con BLE e sonno profondo; display LilyGO T-RGB 2,8" con pace clock a 4 lancette; pagina `tools/assi.html`.
- **Scheda nRF52840 v0.3, variante di collaudo 1c** (`hardware/nrf52840/`, nessun acquisto):
  - 26 × 30 mm, 4 strati 0,8 mm, componenti su una faccia, tag finito ~29 × 33 × 9,2 mm (indossabile a lungo sotto la cuffia). Netlist 36/36, DRC 0 errori, 609 piste, 80 via.
  - Modulo **Ebyte E73** (Raytac a stock 0), IMU LSM6DSV16X, flash 32 MB, BQ25101 con TS da GPIO, MAX17048, sensori su interruttore di carico TPS22916C, cella **Ampul 401012** (40 mAh) su connettore JST SH, 2 × 47 µF, Tag-Connect TC2030-NL e piazzole di prova sotto, 2 contatti di ricarica a 4,2 mm.
  - **Vibratore non montato** (nessun motore SMD montabile da JLC a rifusione): restano pilotaggio e piazzole MOT+/MOT−.
  - Lezioni apprese del prototipo applicate alla v0.3 (tabella nel PDF e in `progetto.md`).
  - File per JLC in `kicad/jlc/v0.3_swimtag_collaudo/`; render, 8 wallpaper PNG (`wallpaper/png/`) e `SwimTag_v0.3_collaudo.pdf`, generati da script dal PCB reale.

- **Scheda v0.4 "economica"** (`hardware/nrf52840/`, solo registrazione IMU, budget ≤ 100 €): E73, LSM6DSV16X, flash 16 MB (W25Q128JVSIQ SOIC-8 *basic*, SPI), BQ25101 (TS 10 k a massa, CHG_N su GPIO), 1 LED 0603 *basic* (anodo su VDD), header SMD 1,27 mm per la cella, Schottky 1N5819WS sui contatti di ricarica, lettura batteria con VDDHDIV5. Tolti pressione, MAX17048, TPS22916C, vibratore, Tag-Connect, piazzole di prova. **21,59 × 26,0 mm (20,32 non chiude lo sbroglio, vedi progetto.md), 2 strati 0,8 mm HASL senza piombo, DRC 0; pinout cambiato: CHG_N P0.20, LED P0.22, INT1 P0.26, INT2 P0.06**; lato sotto 5 pogo SWD Ø 2 e 2 contatti di ricarica sulla griglia 2,54 mm (millefori). File in `kicad/jlc/v0.4_swimtag_economica/`, disegno `ingombro_v0.4.svg`; costi in `progetto.md` (sezione v0.4). Wallpaper e PDF della v0.4 **non fatti** (script legati alla v0.3).

## Prossimi passi
### Prototipo ESP32
1. Capire perché a sola batteria il tag non parte: misurare il 3V3 dopo l'accensione con l'interruttore; prova "senza riavvio" (collegato via Bluetooth con USB, poi staccare l'USB).
2. Scheda nRF52840: decidere le modifiche dalle lezioni apprese (sessione `scheda-nrf`), poi anteprima JLC (rotazioni, stock, prezzo) e ordine.
3. Tap riconosciuto in hardware dal sensore (INT mappato) al posto di quello simulato.
4. Lettura dalla FIFO del BMI160: oggi ~44 Hz reali, campioni persi durante le scritture in flash.
5. Sessioni registrate con video, messa a punto degli algoritmi, poi prova in vasca.
### Scheda nRF52840
0. v0.4: anteprima JLC (rotazioni, header C55213900 nell'Economic, PCB/spedizione reali), poi ordine se il totale resta ≤ 100 €; frequenza di campionamento dell'IMU in base ai 16 MB (~24 min a 960 Hz).
1. Caricare i file JLC nell'anteprima (account dell'utente): rotazioni di E73, TPS22916C, MAX17048, JST, MOSFET e polarità di LED/diodi; stock e prezzo (stima 120–130 $ per 2 tag + cella e cavo).
2. Chiedere ad Ampul se vende la 401012 con spina JST SH; controllare la polarità col tester.
3. Scegliere come programmare (Tag-Connect + J-Link EDU Mini, oppure Pico con traslatore di livello); VREF solo riferimento.
4. Prova del vibratore sotto la cuffia sul prototipo ESP32; poi variante *definitiva* (Raytac o E73, vibratore, piano di massa pieno).
5. Firmware Zephyr/nRF Connect SDK (UICR.REGOUT0 3,3 V, TS open drain, GPIO a sensori spenti, MCUboot); custodia di ricarica **a più posti**.

## Problemi aperti
- **A sola batteria il tag non fa il lampo blu e non si vede in Bluetooth** (LED rosso acceso, 3,87 V ai pad). Sospetti: latch-up del sensore all'accensione con l'interruttore, o tensione al limite.
- **Latch-up del BMI160** dopo spegnimenti bruschi (3V3 a 0 V, ripartiva solo staccando GND): sul prototipo si spegne tutto con l'interruttore; firmware 0.4.4 (sensore su GPIO 5) scartato, patch tenuta fuori dal repository.
- **Display a batteria non si accende** staccando l'USB: forse lo stesso sintomo del tag.
- Riavvii spontanei osservati; crash a fine registrazione corretto nella 0.4.0, da riverificare.
- Vibrazione sospesa finché non si trova un modulo con transistor (GPIO 5 libero).
- Brevetti (FORM US 11833392): per l'uso commerciale serve una verifica di libertà di operare.
- Il BLE non attraversa l'acqua; custodia stagna da definire. Nessun test automatico.
- Zona antenna dell'E73 non quotata da Ebyte: prova di portata prima della resina. QSPI su pin non consigliati da Nordic (clock 8–16 MHz).
- Piani interni non interi (Freerouting usa In1/In2 per i segnali); impronte di MAX17048 e TPS22916C da confrontare con LCSC.
- Risveglio dall'IMU impossibile a sensori spenti: decisione di firmware.
- Prototipo: display a batteria che non si accende (`docs/LEZIONI-APPRESE.md` sulla cartella principale); BLE non attraversa l'acqua.
- `STATO.md`, `DECISIONI.md`, `DOMANDE-APERTE.md` possono confliggere con la sessione principale: unire a mano.

## Decisioni in attesa dell'utente
- Modifiche alla scheda nRF52840 v0.2 dalle lezioni apprese (comportano di rifare parte delle piste).
- Ordine dei prototipi della scheda nRF52840.
- Programmatore (domanda 25), cella con spina JST (26), budget JLC (14), per cosa deve avvisare il vibratore (18).
