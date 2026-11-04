# Distinta componenti — tag su misura nRF52840 (proposta)

**Stato:** proposta del 2026-10-25, **niente acquistato**. Da confermare con l'utente (vedi `docs/DOMANDE-APERTE.md`).
> **Aggiornamento 2026-10-25 — PCB v0.1 disegnato** (`kicad/`): la distinta effettiva per JLC è [`kicad/jlc/bom_jlc.csv`](kicad/jlc/bom_jlc.csv). Rispetto a questa proposta: caricatore **BQ25101YFPR** (C478468, carica a 13,5 mA con ISET 10 kΩ, TS a massa con 10 kΩ); niente TVS né Schottky su VIN; un solo LED rosso 0603 (C2286) invece dell'RGB; MOSFET AO3400A (C20917) con diodo 1N4148WS (C2128) per il vibratore; pull-up I2C 10 kΩ (R5/R6); 10 µF sulla batteria invece di 2 × 22 µF (limite del BQ25101); niente cicalino. Verifiche in [verifiche.md](verifiche.md). Componenti *extended*: modulo, IMU, flash, caricatore, pressione, TVS SD05 (C85201), Schottky B5819WS (C22624); gli altri sono *basic*. In v0.2 aggiunti protezione dei contatti e reset all'inserimento (AO3400A, 100 nF, 1 MΩ).

> **Aggiornamento 2026-11-01 — v0.3 collaudo** (`kicad/dati_scheda.py`; la distinta esportata sarà `kicad/jlc/v0.3_swimtag_collaudo/bom_jlc.csv` allo sbroglio). Stock e tipo (basic/extended) letti il 2026-11-01 dall'API JLCPCB; **riverificare prima dell'ordine**.
>
> | Rif. | Componente | LCSC | Tipo | Stock | $ / pezzo | Note |
> |---|---|---|---|---|---|---|
> | U6 | TI TPS22916CYFPR, interruttore di carico 2 A, QOD 150 Ω, smart pull-down su ON | C2680319 | extended | 1646 | 0,40 | DSBGA-4 0,78 mm, passo 0,4 |
> | U7 | MAX17048G+T10, misuratore di carica | C2682616 | extended | 24741 | 2,10 | TDFN-8 2 × 2 mm |
> | J1 | JST SM02B-SRSS-TB(LF)(SN), SH 1,0 mm, ingresso laterale | C160402 | extended | 74535 | 0,13 | scelto sul PicoBlade 1,25 (stesso prezzo, più piccolo); nessun connettore è *basic* |
> | ~~J2~~, ~~J3~~ | ~~header 2 × 12 (C7470112) e ponticello 1 × 2 (C22438188)~~ | | | | | **tolti nella variante 1c (2026-11-01)**: vedi sotto |
> | C10, C11 | 47 µF 6,3 V X5R 0805 (Samsung CL21A476MQYNNNE) | C16780 | **basic** | 1,0 M | 0,10 | a 4,2 V la capacità reale scende a circa 15–20 µF ciascuno |
> | C9 / C12 / R8–R10 | 100 nF / 10 µF / 1 MΩ / 10 kΩ | C1525 / C15525 / C26083 / C25744 | basic | milioni | < 0,03 | già in uso |
> | U5 | **MS583702BA01-50** (= MS5837-02BA01, stesso chip e stesso package del C2887129, che è a **stock 0**) | **C5785272** | extended | 1079 | 4,70 | cambiato il codice, nessun cambio di schema né di dati |
>
> **Modulo cambiato il 2026-11-01 (decisione dell'utente): Raytac MDBT50Q-1MV2 (C5118826) sostituito da Ebyte E73-2G4M08S1C.** Il Raytac era a stock 0 su JLC e LCSC (listino 19 $; alternative scartate: *Global Sourcing* JLC ~10 $ + ricarico e settimane in più, oppure attendere il riassortimento).
>
> | Rif. | Componente | LCSC | Tipo | Stock | $ / pezzo | Note |
> |---|---|---|---|---|---|---|
> | **U1** | **Ebyte E73-2G4M08S1C** (nRF52840-QIAA, antenna ceramica, 13,0 × 18,0 × 3,0 mm, 43 pad a 1,27 mm: perimetrali a mezzo foro + 15 interni LGA, rifusione) | **C356849** | extended | **572** (API JLC 2026-11-01) | **7,70** (1-9 pz; 7,54 da 10) | VDDH, VDD, VBUS, SWD e RESET esposti, DC/DC REG1 con induttori sul modulo, nessun quarzo a 32 kHz (verifiche in [verifiche.md](verifiche.md)). Costa meno del Raytac ma è 2,5 mm più largo, 2,5 mm più lungo e quasi 1 mm più alto (3,0 contro 2,05 mm): scheda e tag più grandi, vedi `progetto.md`. Certificazione dichiarata dal produttore (FCC ID 2ALPH-E73 in etichetta): non darla per scontata per un uso commerciale |
>
> **Variante 1c (2026-11-01, scheda 26 × 30 mm, approvata dall'utente): cambi alla distinta.** Distinta effettiva: `kicad/jlc/v0.3_swimtag_collaudo/bom_jlc.csv` (22 righe, 37 componenti montati da JLC, tutti sul lato sopra).
>
> | Rif. | Componente | LCSC | Tipo | $ / pezzo | Note |
> |---|---|---|---|---|---|
> | **R11** | resistenza **0 Ω 0402** (UNI-ROYAL 0402WGF0000TCE) tra BAT e VBAT | C17168 | **basic** | < 0,01 | si dissalda a banco per misurare la corrente (al posto di J3 + ponticello) |
> | **J4** | impronta **Tag-Connect TC2030-NL** (6 pad + 3 fori di centraggio) sul lato sotto | — (solo rame, non montata) | — | 0 | cavo TC2030-NL **da comprare a parte** (listino Tag-Connect ~40 $, prezzo da verificare, oppure un clone; serve un solo cavo per tutti i tag; con un J-Link serve anche l'adattatore ARM 10 pin: **non ordinato, da decidere**) |
> | TP1, TP2 | contatti di ricarica Ø 2,5 mm (VIN, GND) a 4,2 mm | — | — | 0 | solo rame (ENIG) |
> | TP3-TP6 / TP7-TP9 | piazzole di prova Ø 0,8 mm (CHG_N, SENS_ON, VDD_SENS, FG_ALRT) / Ø 1 mm (VBAT, VDD, GND) | — | — | 0 | solo rame |
> | TP10, TP11 | piazzole 1 × 1 mm MOT+, MOT− (prova del pilotaggio) | — | — | 0 | **vibratore non montato** sui tag di collaudo (2026-11-01), nessun filo |
>
> **Costi del tag di collaudo 1c (stima, da riverificare nel carrello JLC).** Per tag: modulo 7,70 + IMU ~3 + flash ~3 + caricatore ~1,5 + MS5837 4,70 + U6 0,40 + U7 2,10 + J1 0,13 + 2 × 47 µF 0,20 + resto ~1 = **~24 $ di componenti**; rispetto alla v0.3 con header risparmia ~0,2 $ per tag (J2 e J3) e ~6 $ di spese fisse (due componenti *extended* in meno). **Componenti *extended*: U1, U2, U3, U4, U5, U6, U7, J1, D3, D4 = 10 × ~3 $ = ~30 $ di caricamento.** Ordine di **2 tag** (JLC chiede minimo 5 schede, di cui 2 assemblate): componenti ~48 $ + caricamento *extended* ~30 $ + PCB 4 strati ENIG 26 × 30 mm ×5 ~30 $ + montaggio Economic/raggi X ~10-15 $ ≈ **120-130 $** (IVA e spedizione escluse; spedizione DHL da Shenzhen di solito 5-7 giorni lavorativi + ~3 giorni di produzione). Più cella 401012 (~3 $) e cavo Tag-Connect (~40 $ se non si ha già un programmatore con SWD a molle).

Prezzi indicativi in USD per pezzo a piccoli lotti (5–10 schede); codici LCSC/JLCPCB da riverificare al momento dell'ordine (stock e prezzi cambiano ogni settimana). Progetto e motivazioni in `progetto.md`.

## Componenti principali

| # | Funzione | Proposta | Codice LCSC / JLC | Package e ingombro | Consumo tipico | Costo indic. |
|---|---|---|---|---|---|---|
| U1 | MCU + BLE | ~~Raytac MDBT50Q-1MV2~~ (stock 0) → **Ebyte E73-2G4M08S1C** (nRF52840, antenna ceramica) dal 2026-11-01 | C356849 (JLC, *extended*, 572 pz) | 13,0 × 18,0 × 3,0 mm, 43 pad | 0,4 µA System OFF; ~5 mA in TX 0 dBm (stesso chip) | 7,70 $ |
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
| R1 | ISET del caricatore | 10 kΩ → **13,5 mA** (K_ISET 135 AΩ, BQ2510x) | ~0,7 C per la cella da 20 mAh |
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
| Raytac MDBT50Q-1MV2 | 10,5 × 15,5 × 2,05 mm | chip | FCC/CE/TELEC | C5118826, extended | 9–11 $ | era il proposto; **a stock 0 il 2026-11-01**, sostituito |
| **Ebyte E73-2G4M08S1C** | 13,0 × 18,0 × 3,0 mm | ceramica | CE/FCC (dichiarate dal produttore) | **C356849, extended, 572 pz** | 7,70 $ | **scelto il 2026-11-01** (decisione dell'utente): a magazzino JLC, meno caro; usato da SlimeVR r3 e nRFMicro; più grande (scheda +~11,5 mm in altezza, +1,5 in larghezza) |
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


---

# Distinta v0.4 "economica" (2026-11-02)

Distinta effettiva: `kicad/jlc/v0.4_swimtag_economica/bom_jlc.csv` (12 righe, 20 componenti per scheda, tutti sopra, per 2 schede montate). Stock, tipo e prezzo letti dall'API JLCPCB il 2026-11-02 (da riverificare prima dell'ordine). Servizio **Economic** (solo SMD, una faccia): 4 *extended* (E73, IMU, BQ25101, header) = 4 × 3,07 $ (dal 2026-11-03 il LED è un 0603 *basic*) di caricamento; gli altri sono *basic*.

| Rif. | Componente | LCSC | Tipo | Stock | $ / pezzo | Note |
|---|---|---|---|---|---|---|
| U1 | Ebyte E73-2G4M08S1C | C356849 | extended | 550 | 7,70 | come v0.3 |
| U2 | ST LSM6DSV16X (LGA-14 2,5 × 3) | C5267406 | extended | 15977 | 3,36 | come v0.3 |
| U3 | Winbond W25Q128JVSIQ, 128 Mbit, SOIC-8 208 mil | C97521 | **basic** | 78355 | 2,46 | **nuovo**, 16 MB, SPI semplice; vedi alternative sotto |
| U4 | TI BQ25101YFPR (DSBGA-6, passo 0,4) | C478468 | extended | 5054 | 0,82 | come v0.3 |
| D1 | LED rosso 0603 KT-0603R (Vf ~1,9 V), anodo su VDD, R3 1 k (~1,4 mA) | C2286 | **basic** | 6,98 M | 0,008 | **cambiato il 2026-11-03** (era 0402 NCD0402R1 C130719, extended: −3,07 $) |
| D2 | Schottky 1N5819WS SOD-323 40 V 1 A | C191023 | **basic** | 3,37 M | 0,012 | **nuovo**, al posto di TVS + B5819WS |
| J1 | Header SMD 1,27 mm 1 × 2 (PZ1.27-1x2PLT-L7.2-R) | C55213900 | extended | 3803 | 0,008 | **nuovo**, al posto del JST SH C160402 |
| C1 | 10 µF 0402 6,3 V (CL05A106MQ5NUNC), VDD | C15525 | basic | 9,87 M | 0,026 | |
| C5, C6 | **4,7 µF 0402 10 V X5R (CL05A475MP5NRNC)**: ingresso (5 V) e uscita del BQ25101 | C23733 | basic | 1,2 M | 0,015 | **v0.5**: C5 era 10 µF 6,3 V su 5 V; C7 tolto (VDDH ha 4,7 µF nel modulo) |
| U6 | TI TPS22916CYFPR, interruttore di carico dell'IMU (VDD → VDD_IMU) | C2680319 | extended | 1619 | 0,40 | **v0.5**, DSBGA-4 0,78 mm; "Standard only" come E73/IMU/BQ25101 |
| Q1 | AO3401A P-MOSFET SOT-23, protezione dall'inversione della cella | C15127 | **basic** | 1,64 M | 0,096 | **v0.5**; 85 mΩ a 2,5 V |
| D3 | TVS bidirezionale PTVSLC3D5VB SOD-323, 5 V, 200 nA, sul contatto VIN | C41408025 | extended | 3384 | 0,029 | **v0.5**; alternative: C918847 (1 µA), SD05 C85201 (v0.3) |
| C2-C4 | 100 nF 0402 | C1525 | basic | 35 M | 0,003 | |
| R1, R2, R4 | 10 kΩ 0402 | C25744 | basic | 16 M | 0,003 | ISET, TS, pull-up IO2/IO3 |
| R3 | 1 kΩ 0402 | C11702 | basic | 21 M | 0,001 | LED |
| R5, R6, R8, R9 | 100 kΩ 0402 | C25741 | basic | 8 M | 0,001 | R5 CS flash a VDD; R6 CS IMU a **VDD_IMU**; **R8 VIN-GND**; **R9 gate di Q1 a GND** |
| R7 | 1 MΩ 0402 | C26083 | basic | 2,7 M | 0,001 | pull-down su ON del TPS22916C (v0.5) |

**v0.5: 25 componenti montati per scheda, 6 tipi extended** (E73, IMU, BQ25101, header, TPS22916C, TVS). Distinta effettiva: `kicad/jlc/v0.5_swimtag_economica/bom_jlc.csv` (BOM senza intervalli; la cartella `v0.4_swimtag_economica/` è congelata).

Non montati da JLC (solo rame): TP8 VDD_IMU Ø 0,8 mm (v0.5), 5 piazzole pogo Ø 2,0 mm (VDD, SWDIO, SWDCLK, RESET, GND) e 2 contatti di ricarica Ø 2,5 mm (VIN, GND), tutti sul lato sotto.

**Alternative valutate (v0.4):**
- **Flash:** C97521 SOIC-8 *basic* 2,46 $ (scelto) · C190862 W25Q128JVPIQ WSON 5 × 6, extended, 3,38 $ · C3202839 XT25F128FWOIGT WSON 5 × 6, extended, 1,56 $ · GD25Q128ESIG SOP-8 C2758105, extended, 1,78 $. Il SOIC non paga il caricamento (3,07 $): costo per 2 schede 4,93 $ contro 9,83 $ (Winbond WSON) e 6,19 $ (XTX WSON); il WSON riduce l'ingombro di circa 3-4 mm in larghezza (non provato). Alcune varianti della stessa Winbond (C2456297 6 × 8, C401662) sono a stock 0 o più grandi.
- **Connettore batteria:** JST SH C160402 (26,6 mm², 0,133 $) · header SMD 1,27 mm C55213900 (10,4 mm², 0,008 $, scelto) · header SMD 2,54 mm C41417359 (22,1 mm², 0,028 $) · header THT 2,54 mm C225477: non adatto all'Economic (solo SMD); con montaggio Standard circa +20 $.
- **LED:** nessun 0402 *basic*; scelto il 0603 KT-0603R C2286 *basic* (−3,07 $ di caricamento).
- **Protezione contatti:** TVS SD05 C85201 (extended) tolto; Schottky B5819WS C22624 (extended) sostituito dal *basic* 1N5819WS C191023.

**Costo (2 schede, v0.5: ~125 € dal carrello JLC ricalcolato, vedi progetto.md); stima v0.4 originale:** vedi la tabella in [progetto.md](progetto.md#v04-economica-2026-11-02--registrazione-dei-dati-grezzi-dellimu-budget--100-): ~84,5 $ + IVA 22 % ≈ 103 $ ≈ **91-95 €** con PCB (5 pz, 2 strati, HASL senza piombo, 0,8 mm) e spedizione stimati (non verificati nel carrello JLC).
