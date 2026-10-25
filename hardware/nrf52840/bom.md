# Distinta componenti — tag su misura nRF52840 (proposta)

**Stato:** proposta del 2026-10-25, **niente acquistato**. Da confermare con l'utente (vedi `docs/DOMANDE-APERTE.md`).
> **Aggiornamento 2026-10-25 — PCB v0.1 disegnato** (`kicad/`): la distinta effettiva per JLC è [`kicad/jlc/bom_jlc.csv`](kicad/jlc/bom_jlc.csv). Rispetto a questa proposta: caricatore **BQ25101YFPR** (C478468, carica a 13,5 mA con ISET 10 kΩ, TS a massa con 10 kΩ); niente TVS né Schottky su VIN; un solo LED rosso 0603 (C2286) invece dell'RGB; MOSFET AO3400A (C20917) con diodo 1N4148WS (C2128) per il vibratore; pull-up I2C 10 kΩ (R5/R6); 10 µF sulla batteria invece di 2 × 22 µF (limite del BQ25101); niente cicalino. Verifiche in [verifiche.md](verifiche.md). Solo 5 componenti *extended* (modulo, IMU, flash, caricatore, pressione), tutti gli altri sono *basic*.

Prezzi indicativi in USD per pezzo a piccoli lotti (5–10 schede); codici LCSC/JLCPCB da riverificare al momento dell'ordine (stock e prezzi cambiano ogni settimana). Progetto e motivazioni in `progetto.md`.

## Componenti principali

| # | Funzione | Proposta | Codice LCSC / JLC | Package e ingombro | Consumo tipico | Costo indic. |
|---|---|---|---|---|---|---|
| U1 | MCU + BLE | **Raytac MDBT50Q-1MV2** (nRF52840, antenna chip, FCC/CE/TELEC) | C5118826 (JLC, *extended*, richiede raggi X) | SMD-61, 10,5 × 15,5 × 2,05 mm | 0,4 µA System OFF; ~5 mA in TX 0 dBm | 9–11 $ |
| U2 | IMU 6 assi | **ST LSM6DSV16X** (FIFO 4,5 KB, FSM + MLC + SFLP sul sensore) | C5267406 (LSM6DSV16XTR, a stock) | LGA-14, 2,5 × 3 × 0,83 mm | 0,65 mA acc+giro alte prestazioni; 2,6 µA standby | 2,5–3,5 $ |
| U3 | Memoria dati | **Winbond W25Q256JVEIQ**, NOR QSPI **32 MB** (scelta dell'utente) | C97522 (a stock) | WSON-8 8 × 6 mm | ~15 mA in scrittura; 1 µA in power-down | 2,5–3,5 $ |
| U4 | Caricatore | **TI BQ25100YFPR** (lineare, 10–250 mA, ingresso fino a 28 V, OVP 6,5 V, perdita sulla batteria 75 nA) — riserva BQ25101YFPR | BQ25101YFPR = C478468; BQ25100YFPR da cercare (⚠ **non** il BQ25100**A**, C206119, che carica a 4,3 V) | DSBGA-6, 1,6 × 0,9 mm, passo 0,4 mm | Iq < 1 µA a ingresso assente | 1–2,5 $ |
| U5 | Pressione/profondità (**deciso** 2026-10-25) | **TE MS5837-02BA** (0–2 bar, risoluzione ~0,2 mm d'acqua) | C2887129 (JLC) | 3,3 × 3,3 × 2,75 mm, cappuccio metallico con gel | 1,25 mA solo durante la conversione; 0,1 µA a riposo | 5–8 $ |
| M1 | Vibratore (**deciso** 2026-10-25) | motore a moneta Ø 6 mm × 2–2,7 mm, 3 V, il più basso consumo disponibile (codice da scegliere su LCSC) | — | Ø 6 mm | 50–80 mA mentre vibra; limitato a ~30–40 mA in PWM | 0,5–1 $ |
| Q1/D4 | Pilotaggio vibratore | N-MOSFET logico (SOT-723/SOT-523, Vgs(th) < 1,5 V) + diodo di ricircolo + 10 Ω in serie al gate | — | — | — | 0,1 $ |
| D1 | LED di stato | LED RGB 1010 a anodo comune (codice da scegliere tra i *basic* JLC) | — | 1,0 × 1,0 mm | 1–2 mA per colore, a impulsi | 0,1 $ |
| BT1 | Batteria | LiPo 3,7 V **~20 mAh con PCM** (es. 401012 ≈ 4 × 10 × 12 mm o 301015 ≈ 3 × 10 × 15 mm; misure da verificare col fornitore) | fuori JLC (AliExpress/fornitori celle) | saldata a filo o linguette | autoscarica ~2–3 %/mese | 2–4 $ |
| J1–J3 | Ricarica a contatto | 2 piazzole dorate (VIN, GND) + 1 facoltativa; nella custodia molle pogo e magneti | piazzole sulla scheda; pogo nella custodia | Ø 2–2,5 mm ciascuna | — | — |
| J4 | Programmazione del primo avvio | 5 piazzole SWD (VDD, SWDIO, SWCLK, RESET, GND) a passo 1,27 mm (o impronta Tag-Connect TC2030-NL), lette con una pinza a molle pogo: nessun connettore saldato. **Interne: si usano prima della resina e restano annegate** (decisione dell'utente 2026-10-25) | — | ~6 × 3 mm | — | — |

## Passivi e protezioni

| Rif. | Funzione | Valore / tipo | Note |
|---|---|---|---|
| D2 | ESD/TVS su VIN | TVS unidirezionale 5 V (SOD-523/0201, tra i *basic* JLC) | i contatti sono esposti |
| D3 | Inversione di polarità su VIN | Schottky in serie (SOD-523) **o** P-MOSFET | la custodia con magneti è già polarizzata: Schottky basta (caduta 0,3 V su 5 V) |
| R1 | ISET del caricatore | per **15 mA** (formula nel datasheet BQ2510x) | 0,75 C per la cella da 20 mAh |
| R2 | PRETERM | precarica/terminazione ~2–3 mA | |
| R3/R4 | Rilevamento custodia | partitore 1 MΩ / 1 MΩ da VIN a GPIO | sveglia da System OFF quando VIN sparisce/compare; nessuna tensione di batteria sulle piazzole |
| C | Disaccoppiamenti | 100 nF ogni integrato, 4,7 µF su VDDH, **22–47 µF** di riserva su VDD, **2 × 47 µF** su VDDH vicino al vibratore | la cella da 20 mAh regge 1–2 C: i picchi (radio, flash, vibratore) vanno coperti dai condensatori |
| L | DC/DC dell'nRF | già nel modulo MDBT50Q (REG1) | verificare sul foglio Raytac se serve anche l'induttanza di REG0 |
| NTC | Temperatura cella (facolt.) | 10 kΩ sul pin TS, oppure resistenza fissa | in acqua la temperatura non è un problema; in custodia al sole sì |

## Facoltativi (da decidere)

| Componente | Proposta | Pro | Contro |
|---|---|---|---|
| Protezione sulla scheda | TI BQ2970 + doppio MOSFET | se la cella non avesse il PCM | altri 2 componenti; meglio comprare la cella col PCM |
| 32 kHz esterno | quarzo 32,768 kHz (se non già nel modulo) | ~1 µA in meno rispetto all'oscillatore RC | ingombro; il RC interno basta per il prototipo |

**Vibratore con la cella da 20 mAh:** la cella regge 20–40 mA continui, il motore ne chiede 50–80. Accorgimenti: alimentato da VDDH tramite MOSFET in **PWM (~50 %)**, impulsi brevi (100–300 ms), condensatori di riserva su VDDH, nessuna scrittura in flash né trasmissione durante l'impulso, cella scelta con **scarica ≥ 2 C** (meglio ancora 30–40 mA h se lo spessore lo consente). Il consumo medio è trascurabile: 100 impulsi da 200 ms ≈ 0,3 mAh per allenamento.

## Alternative valutate per il modulo

| Modulo | Ingombro | Antenna | Certificazione | LCSC/JLC | Costo | Giudizio |
|---|---|---|---|---|---|---|
| **Raytac MDBT50Q-1MV2** | 10,5 × 15,5 × 2,05 mm | chip | FCC/CE/TELEC | C5118826, extended | 9–11 $ | **proposto**: compatto, certificato, montabile da JLC |
| Ebyte E73-2G4M08S1C | 13 × 18 × 2 mm | PCB | CE/FCC (dichiarate dal produttore) | C356849, stock variabile | 5,5–7,5 $ | usato da SlimeVR r3 e nRFMicro; più grande, più economico; buona riserva |
| Holyiot YJ-18010 | 18 × 13,5 × 1,6 mm | ceramica | — | non su LCSC | ~6 $ | scartato: non montabile da JLC senza fornitura a parte |
| Insight SiP ISP1807-LR | **8 × 8 × 1 mm** (quarzi e DC/DC dentro) | integrata | FCC/CE | non su LCSC (DigiKey ~12,5 $) | 10–13 $ | candidato per la **seconda versione** ultra piccola; LGA a passo fine, fornitura a parte (*consigned parts*) |
| nRF52840-QIAA nudo | aQFN-73 7 × 7 mm + antenna chip + quarzi | da progettare | nessuna | C1851953 | ~4 $ + RF | scartato per ora: progetto RF, via-in-pad, taratura dell'antenna |

## Alternative valutate per l'IMU

Tutti i sensori moderni hanno il **fondo scala selezionabile** (±2/4/8/16 g): a ±2 g la risoluzione è la stessa per tutti (0,061 mg per bit). Quello che migliora davvero la "sensibilità" è il **rumore**:

| Sensore | Rumore acc. | Rumore giro | Corrente 6 assi | Fondo scala acc. | LCSC | Nota |
|---|---|---|---|---|---|---|
| BMI160 (prototipo) | ~180 µg/√Hz | ~7 mdps/√Hz | ~0,9 mA | ±2…16 g | — | a ±2 g **satura** nelle registrazioni attuali |
| **LSM6DSV16X** | **~60 µg/√Hz** | **2,8 mdps/√Hz** | 0,65 mA | ±2…16 g | C5267406 | **proposto**: 3 volte meno rumore del BMI160, FSM/MLC per i gesti, driver Zephyr e SlimeVR |
| ICM-45686 | 70 µg/√Hz | 3,8 mdps/√Hz | 0,42 mA | ±2…32 g | C22459454 (~8 $) | alternativa a consumo minore; driver Zephyr e SlimeVR; più caro |
| ICM-42688-P | ~70 µg/√Hz | 2,8 mdps/√Hz | ~0,9 mA | ±2…16 g | C1850418 | economico, ma generazione precedente |
| ADXL355 | 22 µg/√Hz | — (niente giroscopio) | 0,2 mA | ±2…8 g | — | scartato: senza giroscopio non si vedono bracciate e virate; 6 × 6 mm |

Proposta di impostazione: **±4 g** (rumore invariato, nessuna saturazione a spinta e capovolta); se le registrazioni con la nuova scheda mostreranno picchi sempre sotto 2 g si passa a ±2 g via firmware, senza toccare l'hardware.

## Riepilogo costo per pezzo (stima, 5–10 pezzi)

| Voce | Stima |
|---|---|
| Componenti (modulo, IMU, flash, caricatore, passivi, LED) | 16–22 $ |
| Sensore di pressione + vibratore e pilotaggio | 6–9 $ |
| Cella LiPo 20 mAh con PCM | 2–4 $ |
| PCB 4 strati 0,8 mm + montaggio JLC (spese fisse ~25–40 $ divise sul lotto, componenti *extended* ~3 $ l'uno, raggi X) | 6–12 $ |
| **Totale tag** | **~30–45 $ al pezzo** (spedizione e IVA escluse; ordine di 5 pezzi ~150–250 $ tutto compreso) |
