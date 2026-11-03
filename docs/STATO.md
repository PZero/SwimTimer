# Stato del progetto

**Ultimo aggiornamento:** 2026-11-02 — **v0.4 economica ricompattata il 2026-11-03 (21,59 × 26 mm, 2 strati, DRC 0, LED 0603 basic con anodo su VDD, ~87-91 € per 2 schede, file JLC rigenerati, anteprima JLC da fare)**;  2026-11-01 — Fase 1 (prototipo ESP32 sul tavolo) + scheda su misura nRF52840: **tag v0.3 di collaudo sbrogliato, pronto per l'anteprima JLC** (ramo `claude/scheda-nrf52840-08642d`, solo sul repository privato `PZero/SwimTimer-nrf52840`, mai su `origin`).

## Fatto
- **Prototipo** (invariato, dettagli in `hardware/bom.md`, `hardware/schema.md`): tag ESP32-S3 SuperMini + BMI160 con BLE e sonno profondo; display LilyGO T-RGB 2,8" con pace clock a 4 lancette; pagina `tools/assi.html`.
- **Scheda nRF52840 v0.3, variante di collaudo 1c** (`hardware/nrf52840/`, nessun acquisto):
  - 26 × 30 mm, 4 strati 0,8 mm, componenti su una faccia, tag finito ~29 × 33 × 9,2 mm (indossabile a lungo sotto la cuffia). Netlist 36/36, DRC 0 errori, 609 piste, 80 via.
  - Modulo **Ebyte E73** (Raytac a stock 0), IMU LSM6DSV16X, flash 32 MB, BQ25101 con TS da GPIO, MAX17048, sensori su interruttore di carico TPS22916C, cella **Ampul 401012** (40 mAh) su connettore JST SH, 2 × 47 µF, Tag-Connect TC2030-NL e piazzole di prova sotto, 2 contatti di ricarica a 4,2 mm.
  - **Vibratore non montato** (nessun motore SMD montabile da JLC a rifusione): restano pilotaggio e piazzole MOT+/MOT−.
  - Lezioni apprese del prototipo applicate alla v0.3 (tabella nel PDF e in `progetto.md`).
  - File per JLC in `kicad/jlc/v0.3_swimtag_collaudo/`; render, 8 wallpaper PNG (`wallpaper/png/`) e `SwimTag_v0.3_collaudo.pdf`, generati da script dal PCB reale.

- **Scheda v0.4 "economica"** (`hardware/nrf52840/`, solo registrazione IMU, budget ≤ 100 €): E73, LSM6DSV16X, flash 16 MB (W25Q128JVSIQ SOIC-8 *basic*, SPI), BQ25101 (TS 10 k a massa, CHG_N su GPIO), 1 LED 0603 *basic* (anodo su VDD), header SMD 1,27 mm per la cella, Schottky 1N5819WS sui contatti di ricarica, lettura batteria con VDDHDIV5. Tolti pressione, MAX17048, TPS22916C, vibratore, Tag-Connect, piazzole di prova. **21,59 × 26,0 mm (20,32 non chiude lo sbroglio, vedi progetto.md), 2 strati 0,8 mm HASL senza piombo, DRC 0; pinout cambiato: CHG_N P0.20, LED P0.22, INT1 P0.26, INT2 P0.06**; lato sotto 5 pogo SWD Ø 2 e 2 contatti di ricarica sulla griglia 2,54 mm (millefori). File in `kicad/jlc/v0.4_swimtag_economica/`, disegno `ingombro_v0.4.svg`; costi in `progetto.md` (sezione v0.4). Wallpaper e PDF della v0.4 **non fatti** (script legati alla v0.3).

## Prossimi passi
0. v0.4: anteprima JLC (rotazioni, header C55213900 nell'Economic, PCB/spedizione reali), poi ordine se il totale resta ≤ 100 €; frequenza di campionamento dell'IMU in base ai 16 MB (~24 min a 960 Hz).
1. Caricare i file JLC nell'anteprima (account dell'utente): rotazioni di E73, TPS22916C, MAX17048, JST, MOSFET e polarità di LED/diodi; stock e prezzo (stima 120–130 $ per 2 tag + cella e cavo).
2. Chiedere ad Ampul se vende la 401012 con spina JST SH; controllare la polarità col tester.
3. Scegliere come programmare (Tag-Connect + J-Link EDU Mini, oppure Pico con traslatore di livello); VREF solo riferimento.
4. Prova del vibratore sotto la cuffia sul prototipo ESP32; poi variante *definitiva* (Raytac o E73, vibratore, piano di massa pieno).
5. Firmware Zephyr/nRF Connect SDK (UICR.REGOUT0 3,3 V, TS open drain, GPIO a sensori spenti, MCUboot); custodia di ricarica **a più posti**.

## Problemi aperti
- Zona antenna dell'E73 non quotata da Ebyte: prova di portata prima della resina. QSPI su pin non consigliati da Nordic (clock 8–16 MHz).
- Piani interni non interi (Freerouting usa In1/In2 per i segnali); impronte di MAX17048 e TPS22916C da confrontare con LCSC.
- Risveglio dall'IMU impossibile a sensori spenti: decisione di firmware.
- Prototipo: display a batteria che non si accende (`docs/LEZIONI-APPRESE.md` sulla cartella principale); BLE non attraversa l'acqua.
- `STATO.md`, `DECISIONI.md`, `DOMANDE-APERTE.md` possono confliggere con la sessione principale: unire a mano.

## Decisioni in attesa dell'utente
- Programmatore (domanda 25), cella con spina JST (26), budget JLC (14), per cosa deve avvisare il vibratore (18).
