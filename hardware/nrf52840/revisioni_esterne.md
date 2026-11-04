# Revisioni esterne della v0.4: esito e azioni

Le modifiche decise sono state applicate nella v0.5 (commit 01c6b8b): TPS22916C, TVS, AO3401A contro l'inversione della cella, 100 kΩ VIN-GND, TP8, IMU_MISO/CS su P0.08/P0.12; ENIG e procedure restano scelte d'ordine e di montaggio.

Documento dato ai revisori: `revisione_esterna_v0.4.md` (anche in PDF). Qui si raccolgono le risposte, la nostra valutazione e cosa si è deciso.

## Gemini, 2026-11-04 (3 giri)

### Modifiche al PCB decise (in corso di disegno)
| Origine | Modifica | Motivo |
|---|---|---|
| Giro 2, nostra analisi | 100 kΩ tra VIN e GND (C25741) | La perdita inversa di D2 porterebbe VIN verso VBAT: elettrolisi lenta e continua tra VIN e GND in acqua |
| Giro 2 | IMU_CS e IMU_MISO via da P0.00/P0.01 (XL1/XL2), se lo sbroglio lo permette | MISO commuta in MHz vicino al clock e alla radio; non bloccante |
| Giro 1 e 3 | Finitura **ENIG** (opzione d'ordine, non cambia i Gerber) | Coplanarità per BGA 0,4 mm e LGA 0,5 mm; contatti di ricarica e piazzole pogo più resistenti |

### Confermato corretto
E73 con disaccoppiamento interno (DEC non esposti); modo alta tensione con DCCH libero; IMU in SPI 4 fili (pin 1, 2, 3, 10, 11); flash SPI con /WP e /HOLD alti; sfere del BQ25101 (A1 OUT, A2 IN, B1 TS, B2 ISET, C1 /CHG, C2 VSS); condensatori del caricatore (≥ 1 µF richiesti); TPS22916C con 1 MΩ su ON; diagnostica con SWD + LED + VDDHDIV5.

### Requisiti per il firmware (nessuna modifica al PCB)
1. **Sottotensione**: comparatore POF su VDDH a circa 2,8–3,0 V. Sotto soglia: chiudere il file, niente scritture in flash, System OFF. La flash non va scritta sotto 2,7 V. Con la cella sotto circa 3,6 V, VDD scende sotto 3,3 V.
2. **Carica**: con il tag in carica (CHG_N basso, P0.20) andare in **System OFF** con risveglio su CHG_N, così il carico scende sotto l'1,35 mA della terminazione. Altrimenti la carica finisce solo per il timer di sicurezza.
3. **IMU**: prima di spegnere il TPS22916C portare SPI, CS e INT a livello basso (o alta impedenza senza pull-up); alla riaccensione attendere il tempo di salita di VDD_IMU e il boot dell'IMU.
4. **Radio**: potenza fino a +8 dBm per compensare resina e testa, ma oltre +4 dBm la corrente esterna del REG0 va limitata (niente scritture in flash durante la trasmissione).
5. **Primo avvio**: script OpenOCD unico: REGOUT0 = 5 (0x10001304), PSELRESET[0/1] = 18, reset. **Mai APPROTECT** sui prototipi. MCUboot con immagine di riserva.
6. RESET: pull-up interno attivo (P0.18 come nRESET tramite UICR).

### Procedure (montaggio e collaudo)
- **Polarità della cella**: prima di saldare, verificare col tester il + della cella e la serigrafia "+" di J1. Un'inversione distrugge nRF52840 e flash, e non c'è protezione in hardware.
- Prima accensione da alimentatore limitato a circa 50 mA, poi la cella.
- Prima della colata: pulizia del flussante, **essiccazione a 60 °C per 1 h**, resina per elettronica a basso ritiro; fili della cella sigillati.
- Prova di portata BLE prima e dopo la resina, fuori dall'acqua.
- Centraggio dei pogo: verificare l'adattatore con una scheda nuda (ne arrivano 3 non montate).

## Copilot, 2026-11-04 (sign-off, 1 giro)

Verdetto di Copilot: "non firmerei ancora" (S1, S5, S6 aperti). Nostra valutazione:

| ID | Copilot dice | Valutazione | Azione |
|---|---|---|---|
| S1 | TS con 10 kΩ a massa = probabile errore bloccante (hot fault) | **Falso positivo.** Il foglio TI dice testualmente: "If NTC sensing is not needed, connect this pin to VSS through an external 10-kΩ resistor" (SLUSBV8C p. 3); 50 µA × 10 kΩ = 0,5 V, zona normale. La XIAO nRF52840 fa lo stesso | Nessuna |
| S2 | Terminazione a 1,35 mA | Già noto | Firmware: sotto 0,8–1 mA in carica (System OFF) |
| S3 | Flash sotto 2,7 V | Già noto. Copilot aggiunge: soglia di non scrittura a 3,15–3,2 V, chiusura a 3,0–3,1 V, record con CRC e commit marker, niente cancellazioni in sessione | Firmware (per i prototipi basta, secondo Copilot stesso) |
| S4 | SWD 3,3 V contro 1,8 V | Già noto, le 1 kΩ sono un compromesso | Valutare un traslatore di livello sull'adattatore |
| S5 | Mancano punti di misura VBAT e VDD_IMU | Fondato per VDD_IMU (VBAT è già sui pin di J1 prima della colata) | Piazzola di prova VDD_IMU (solo rame), facoltativa CHG_N |
| S6 | Due package a 0,4 mm (BQ25101 e TPS22916C): Standard PCBA, ENIG, raggi X, rail di pannello | Fondato, già nel piano | Aprire un ticket DFM a JLC prima di pagare |
| S7 | Antenna | Già noto. Copilot aggiunge il piano di misura: RSSI a 0,5–10 m, cuffia asciutta e bagnata, 0/+4/+8 dBm, PHY 1M e coded | Test |
| S8 | Contatti senza TVS | Rimandato o anticipato (decisione dell'utente) | Base di ricarica con corrente limitata (20–30 mA) e polarità meccanica |
| S9 | TPS22916C | Corretto: ha già un pull-down interno da circa 750 kΩ su ON; salita lenta (circa 3 ms) | Firmware: sequenze di accensione e spegnimento con attesa di 5–10 ms |
| S10 | Resina | **Correzione importante a Gemini**: essiccare la scheda **senza la cella collegata**, mai la LiPo in forno; colata in due fasi sottili; supporto meccanico dei fili della cella; offset dell'IMU confrontato prima e dopo la colata | Procedura |

### Rimandato alla v0.5 (poi applicato)
- TVS bidirezionale tra VIN e GND contro l'ESD alla manipolazione. Applicato nella v0.5 (D3 PTVSLC3D5VB): BQ25101 IN regge 30 V e D2 è in serie.
- Protezione contro l'inversione della cella (MOSFET P). Costa un caricamento extended e spazio; applicata nella v0.5 (Q1 AO3401A, gate a GND con R9 100 kΩ), da provare a banco.
