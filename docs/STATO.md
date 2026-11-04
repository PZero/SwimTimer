# Stato del progetto

**Ultimo aggiornamento:** 2026-11-04. Ramo `claude/scheda-nrf52840-08642d`, solo sul repository privato `PZero/SwimTimer-nrf52840` (mai su `origin` pubblico).

## Fotografia
- **Scheda nRF52840 v0.5 pronta** (commit 01c6b8b): 21,59 × 28,0 mm, 2 strati 0,8 mm, DRC 0, ERC 0 errori, parità schema/PCB 0, `kicad/verifica_v05.py` 100/100 pin, 369 piste, 36 via. File JLC in `hardware/nrf52840/kicad/jlc/v0.5_swimtag_economica/`; la v0.4 è congelata in `jlc/v0.4_swimtag_economica/` (rigenerabile dal commit 8fd6cc0).
- Novità v0.5: TPS22916C (U6) su VDD_IMU con ON su P0.04, TVS D3, AO3401A (Q1) contro l'inversione della cella, 100 kΩ VIN-GND, TP8 VDD_IMU, IMU_MISO/CS su P0.08/P0.12. Dettagli: blocco "Revisione v0.5" in `hardware/nrf52840/progetto.md`.
- **Costo ~125 €** (Standard PCBA, raggi X, coupon; ENIG +5–10 €): **sopra il tetto di 100 €**. Tagli: senza raggi X ~109 €, + senza TVS ~105 €, + senza header ~100,5 €. Decide l'utente.
- Revisioni esterne (Gemini, Copilot) in `hardware/nrf52840/revisioni_esterne.md`: modifiche applicate nella v0.5; S1 di Copilot (TS a massa) è un falso positivo.
- Sfondi della v0.5 in `hardware/wallpaper_v0.5/png/` (20 file); programmatore HAT rigenerato (TP1–TP7 invariate), non costruito.
- Prototipo ESP32-S3 + BMI160, firmware 0.4.3, pagina `tools/index.html` (online su https://pzero.github.io/SwimTimer/), display LilyGO T-RGB: funzionanti sul tavolo, nessuna prova in vasca.
- **Firmware del tag nRF52840: da scrivere** (Zephyr / nRF Connect SDK).

## Prossimi passi
1. Decidere il costo (tetto 100 € contro ~125 €) e la finitura HASL o ENIG (consigliata per BQ25101 a 0,4 mm e IMU LGA).
2. Anteprima JLC: rotazioni di U2, U4, U6, Q1, D1, D2, D3, J1; il TPS22916C è probabilmente "Standard only"; stock dell'E73.
3. Aprire un ticket DFM a JLC (BQ25101 e TPS22916C a 0,4 mm) prima di pagare; poi ordine di 2 schede.
4. A scheda arrivata: prova a banco di Q1 (cella dritta e invertita), prima accensione da alimentatore limitato a ~50 mA, costruire il programmatore, scrivere UICR (`REGOUT0`, `PSELRESET`), prova di portata dell'antenna prima della resina (antenna a 0,3 mm dal bordo, scheda 28 mm).
5. Firmware: SPI, flash, registrazione, MCUboot, sonno con INT dell'IMU, sottotensione, System OFF in carica, sequenze del TPS22916C (5–10 ms).
6. Prototipo ESP32: sessioni registrate con video, messa a punto degli algoritmi, prova in vasca; tap hardware al posto di quello simulato; FIFO del BMI160 (~44 Hz reali).
7. Variante definitiva: vibratore, pressione, custodia di ricarica a più posti.
8. Cancellare a mano la cartella temporanea `C:\swt_chk`.

## Problemi aperti
- A sola batteria il tag ESP32 non fa il lampo blu e non si vede in Bluetooth (LED rosso, 3,87 V ai pad); latch-up del BMI160 dopo spegnimenti bruschi; display a batteria che non si accende senza USB.
- Riavvii spontanei osservati; tap software poco affidabile (~1 volta su 10).
- Brevetti (FORM US 11833392): serve una verifica di libertà di operare per l'uso commerciale.
- Il BLE non attraversa l'acqua; custodia stagna e resina da definire (essiccare senza la cella). Nessun test automatico.
- Zona antenna dell'E73 non quotata da Ebyte; zona senza piste F.Cu sotto il modulo non eliminabile del tutto: prova di portata obbligatoria.
- Livelli SWD: 1 kΩ in serie non sono un traslatore (VDD 1,8 V al primo avvio): valutare un traslatore sul programmatore.
- Q1 (AO3401A) non provato a banco; polarità di D1, D2, D3, J1 e rotazioni da confermare nell'anteprima JLC.
- `STATO.md`, `DECISIONI.md`, `DOMANDE-APERTE.md` possono confliggere con il repository pubblico: unire a mano.

## Decisioni in attesa dell'utente
- Costo dell'ordine e tagli (raggi X, TVS, header); HASL o ENIG.
- Ordine dei prototipi della scheda nRF52840.
- Domande 14 (budget JLC), 18 (per cosa deve avvisare il vibratore), 25 (programmatore), 26 (cella con spina JST): vedi `docs/DOMANDE-APERTE.md`.

## Riferimenti
- Prototipo: `hardware/bom.md`, `hardware/schema.md`, `docs/LEZIONI-APPRESE.md`, `docs/RICERCA-ALGORITMI.md`.
- Scheda: `hardware/nrf52840/progetto.md`, `verifica_v0.4.md`, `revisioni_esterne.md`, `bom.md`.
- Storico v0.3 (collaudo, 26 × 30 mm, 4 strati) e v0.4: `hardware/nrf52840/progetto.md` e `CHANGELOG.md`.
