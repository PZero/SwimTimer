# Richiesta di revisione: scheda "SwimTag" v0.5 (nRF52840)

> Documento autonomo da dare a un revisore (persona o AI). Descrive la scheda, i requisiti e lo schema completo in testo.
> Si chiede di **trovare errori** prima di ordinare 2 prototipi montati da JLCPCB. Rispondere nel formato della sezione 11.

Versione descritta: **v0.5**, commit `01c6b8b` (2026-11-04). È la v0.4 già rivista da due AI (Gemini e Copilot), con le loro correzioni applicate (sezione 8). Questo è il giro di conferma prima dell'ordine.

---

## 1. Cos'è e a cosa serve

SwimTimer misura i tempi in piscina senza pulsanti. Il **tag** è una piccola scheda indossata **sotto la cuffia**, sulla nuca o sulla tempia. Registra i dati grezzi del sensore di movimento (IMU), così si possono studiare i filtri che riconoscono partenze, virate e arrivi.

Questa versione serve **solo alla raccolta dati**: registra l'IMU in memoria flash durante l'allenamento e, fuori dall'acqua, scarica i dati via Bluetooth Low Energy (BLE). Il BLE non funziona in acqua.

## 2. Requisiti funzionali

| ID | Requisito |
|---|---|
| R1 | Registrare accelerometro e giroscopio a 6 assi, 16 bit, a 100–240 Hz, per sessioni di circa 1–1,5 h |
| R2 | Memoria non volatile ≥ 16 MB (circa 97 min a 240 Hz, circa 3 h a 120 Hz) |
| R3 | BLE 5 per scaricare i dati e aggiornare il firmware (OTA con MCUboot), solo fuori dall'acqua |
| R4 | Batteria LiPo 3,7 V, 40 mAh (Ampul 401012, 12 × 10 × 4 mm, con protezione PCM integrata, scarica 1C) |
| R5 | Ricarica da **due contatti esterni** (VIN, GND) con molle pogo su una base. I contatti **non devono mai portare la tensione della batteria** fuori dalla custodia (elettrolisi e corrosione in acqua clorata) |
| R6 | Lettura della tensione della batteria dal processore e dello stato di carica (in carica / finito) |
| R7 | Un LED di stato (debug quando il BLE non funziona) |
| R8 | Programmazione SWD **una tantum** prima della colata in resina, tramite 5 piazzole sul lato sotto contattate da molle pogo (VDD solo come riferimento, SWDIO, SWCLK, RESET, GND). Dopo la resina solo aggiornamenti via BLE |
| R9 | Il tag viene **sigillato in resina**: niente pulsanti, niente connettori raggiungibili, nessuna rilavorazione. Un IMU bloccato (latch-up) deve poter essere sbloccato togliendogli l'alimentazione da firmware |
| R10 | Alimentazione dell'IMU commutabile da GPIO (vedi sezione 8) |

## 3. Vincoli

| Vincolo | Valore |
|---|---|
| Montaggio | Tutto da JLCPCB, componenti solo sul lato sopra. L'utente salda soltanto i 2 fili della cella su un header |
| Servizio JLC | Standard PCBA: E73, IMU (LGA) e caricatore (BGA) non sono montabili in Economic |
| Budget | Circa 100 € per 2 schede montate, spedizione e IVA comprese |
| Circuito stampato | **2 strati**, FR4 0,8 mm, HASL senza piombo (ENIG in valutazione) |
| Regole | JLC: piste/distanze 0,127 mm, via 0,6/0,3 mm |
| Dimensioni | **21,59 × 28,0 mm** (più piccola non chiude lo sbroglio a 2 strati) |
| Lato sotto | Solo rame: 5 piazzole SWD Ø 2,0 mm e 2 contatti di ricarica Ø 2,5 mm, su **griglia 2,54 mm** (adattatore a pogo fatto a mano) |
| Ambiente | Sotto la cuffia, acqua clorata, colata in resina; temperatura 20–35 °C |

## 4. Architettura dell'alimentazione

```
Contatto VIN (R8 100 kΩ e TVS D3 verso GND) ──► D2 Schottky (1N5819WS) ──► VIN_D ──► BQ25101 IN
                                                       BQ25101 OUT ──► VBAT ◄── Q1 AO3401A (contro l'inversione) ◄── cella (J1 +)
VBAT ──► VDDH del modulo E73 (nRF52840 in modo "alta tensione", REG0 interno)
E73 VDD (uscita REG0, 1,8 V di fabbrica, 3,3 V dopo UICR.REGOUT0) ──► memoria, LED, pull-up
                                       └──► U6 TPS22916C (ON = P0.04) ──► VDD_IMU ──► IMU
```

- Nessun regolatore esterno: VDD viene dal REG0 interno del nRF52840, con VDDH collegato alla cella.
- **Al primo avvio** l'UICR è vuoto e VDD vale **1,8 V**. La memoria (2,7–3,6 V) parte solo dopo aver scritto `UICR.REGOUT0 = 5` (3,3 V, registro 0x10001304) e riavviato.
- Lettura della batteria con l'ingresso interno **VDDHDIV5** del convertitore analogico (SAADC), senza partitore.
- Nessun quarzo a 32,768 kHz: LFCLK dall'oscillatore RC interno.

## 5. Distinta componenti (BOM per JLC)

| Rif. | Valore | Package | LCSC | Tipo JLC | Funzione |
|---|---|---|---|---|---|
| U1 | Ebyte **E73-2G4M08S1C** (nRF52840, antenna PCB integrata) | modulo 13 × 18 mm, 43 pad | C356849 | extended | MCU + BLE |
| U2 | ST **LSM6DSV16X** | LGA-14 2,5 × 3 mm, passo 0,5 | C5267406 | extended | IMU 6 assi, SPI 4 fili |
| U3 | Winbond **W25Q128JVSIQ** | SOIC-8 208 mil | C97521 | basic | Flash 16 MB, SPI semplice |
| U4 | TI **BQ25101YFPR** | DSBGA-6, passo 0,4 | C478468 | extended | Caricatore Li-ion lineare |
| U6 | TI **TPS22916C** | DSBGA-4, passo 0,4 | C2680319 | extended | Interruttore di carico dell'IMU (salita lenta, pull-down interno su ON) |
| Q1 | **AO3401A**, MOSFET P | SOT-23 | C15127 | basic | Contro l'inversione della cella: D verso la cella, S verso VBAT, G a GND tramite R9 |
| D1 | LED rosso KT-0603R | 0603 | C2286 | basic | Stato (anodo su VDD, acceso a livello basso) |
| D2 | 1N5819WS | SOD-323 | C191023 | basic | Schottky in serie sul contatto VIN |
| D3 | **PTVSLC3D5VB**, TVS bidirezionale 5 V, 200 nA | SOD-323 | C41408025 | extended | ESD sul contatto VIN, prima di D2 |
| J1 | Header SMD 1×2, passo 1,27 mm | SMD | C55213900 | extended | Fili della cella (+ / −) |
| C1 | 10 µF | 0402 | C15525 | basic | VDD |
| C2–C4 | 100 nF | 0402 | C1525 | basic | Disaccoppiamento (C2, C4 su VDD_IMU, C3 su VDD) |
| C5, C6 | 4,7 µF 10 V | 0402 | C23733 | basic | Ingresso del caricatore (VIN_D) e VBAT |
| R1, R2, R4 | 10 kΩ | 0402 | C25744 | basic | ISET (circa 13,5 mA), TS a massa, pull-up /WP e /HOLD |
| R3 | 1 kΩ | 0402 | C11702 | basic | LED |
| R5, R6, R8, R9 | 100 kΩ | 0402 | C25741 | basic | Pull-up /CS flash (su VDD), pull-up CS IMU (su **VDD_IMU**), VIN→GND, gate di Q1 |
| R7 | 1 MΩ | 0402 | C26083 | basic | Pull-down di ON del TPS22916C |
| TP1–TP8 | piazzole | rame, lato sotto | — | non montate | SWD, ricarica, VDD_IMU (TP8) |

## 6. Netlist completa (commit 8fd6cc0)

Formato: `rif.pin (funzione)`. Esportata dallo schema v0.5.

| Rete | Nodi |
|---|---|
| BAT_IN | J1.1 (+ cella), Q1.3 (D) |
| BAT_G | Q1.1 (G), R9.1 |
| VBAT | C6.1, Q1.2 (S), U1.23 (VDDH), U4.A1 (OUT) |
| VDD | C1.1, C3.1, D1.2 (anodo LED), R4.2, R5.2, TP1, U1.19 (VDD), U3.8 (VCC), U6.A2 (VIN) |
| VDD_IMU | C2.1, C4.1, R6.2, TP8, U2.5 (Vdd_IO), U2.8 (Vdd), U6.A1 (VOUT) |
| GND | C1–C6 pin 2, D3.2, J1.2 (− cella), R1.2, R2.2, R7.2, R8.2, R9.2, TP5, TP7, U1.5, U1.21, U1.24, U2.2 (SDx), U2.3 (SCx), U2.6, U2.7, U3.4, U4.C2 (VSS), U6.B1 (GND) |
| VIN | D2.2 (anodo), D3.1, R8.1, TP6 (contatto di ricarica) |
| VIN_D | C5.1, D2.1 (catodo), U4.A2 (IN) |
| ISET | R1.1, U4.B2 |
| TS | R2.1, U4.B1 |
| CHG_N | U1.32 (P0.20), U4.C1 (/CHG, open-drain) |
| SENS_ON | R7.1, U1.18 (P0.04), U6.B2 (ON) |
| LED | R3.2, U1.34 (P0.22) |
| LED_K | D1.1 (catodo), R3.1 |
| IMU_CS | R6.1, U1.20 (P0.12), U2.12 (CS) |
| IMU_MISO | U1.16 (P0.08), U2.1 (SDO/SA0) |
| IMU_MOSI | U1.15 (P0.05), U2.14 (SDA/SDI) |
| IMU_SCK | U1.17 (P1.09), U2.13 (SCL/SPC) |
| IMU_INT1 | U1.12 (P0.26), U2.4 (INT1) |
| IMU_INT2 | U1.14 (P0.06), U2.9 (INT2) |
| FL_CS | R5.1, U1.30 (P0.17), U3.1 (/CS) |
| FL_MISO | U1.28 (P0.15), U3.2 (DO/IO1) |
| FL_MOSI | U1.33 (P0.13), U3.5 (DI/IO0) |
| FL_SCK | U1.35 (P0.24), U3.6 (CLK) |
| FL_IO23 | R4.1, U3.3 (/WP/IO2), U3.7 (/HOLD/IO3) |
| SWDIO | TP2, U1.37 |
| SWDCLK | TP3, U1.39 |
| RESET | TP4, U1.26 (P0.18/nRESET) |

**Pin lasciati liberi:** E73 DCCH (25), VBUS (27), USB D+/D− (31/29), NFC1/NFC2 (41/43), P0.00/XL1, P0.01/XL2, P0.02, P0.03, P0.07, P0.28–P0.31, P1.00, P1.02, P1.04, P1.06, P1.10, P1.11, P1.13. IMU OCS_Aux (10) e SDO_Aux (11).

## 7. Circuito stampato

- 21,59 × 28,0 mm, 2 strati, 0,8 mm; 369 piste, 36 via.
- Controlli: DRC 0 errori e 0 non collegati; ERC 0 errori (41 avvisi pin_to_pin su pin "unspecified" dei simboli generati); verifica automatica della netlist contro una tabella attesa: 100/100 pin.
- **E73 con antenna sul bordo alto**, striscia di 3,7 mm senza rame su tutti gli strati. Il pad esterno sinistro del modulo è a **0,3 mm dal bordo**. Il foglio Ebyte non dà quote di zona libera laterale.
- Sotto il modulo: zona senza piste su F.Cu al centro (±2,2 mm, y 7,4–14,8); restano le uscite dei pad interni.
- Lato sotto (coordinate dall'angolo in alto a sinistra):
  - SWD a y = 12,70 (Ø 2,0): VDD x = 5,08, SWDIO 7,62, SWDCLK 10,16, RESET 12,70, GND 15,24;
  - TP8 VDD_IMU x = 17,78 (Ø 0,8);
  - ricarica a y = 17,78 (Ø 2,5): VIN x = 7,62, GND 12,70.
- Serigrafia ≥ 1,0 mm. Finitura prevista **ENIG**.

## 8. Modifiche già decise, in corso di disegno

Applicate nella v0.5 dopo le revisioni della v0.4:

1. **TPS22916C** per l'IMU (VDD_IMU), ON su P0.04 con 1 MΩ verso GND; R6 su VDD_IMU, quindi nessun pull-up dell'IMU verso la VDD sempre accesa.
2. **C5** 4,7 µF 10 V (prima 6,3 V); C7 tolto, C6 4,7 µF: su VBAT circa 9 µF con quelli del modulo.
3. **R8** 100 kΩ VIN→GND: con la base scollegata il contatto resta a circa 0 V nonostante la perdita inversa di D2.
4. **D3** TVS bidirezionale 5 V sul contatto VIN.
5. **Q1** AO3401A contro l'inversione dei fili della cella.
6. **IMU_CS e IMU_MISO** spostati da P0.00/P0.01 (XL1/XL2) a P0.12/P0.08.
7. **TP8** di prova su VDD_IMU; serigrafia ≥ 1 mm; meno piste sotto il modulo.

Falso positivo già chiarito: il TS del BQ25101 con 10 kΩ a massa è il collegamento indicato da TI quando non si usa l'NTC ("connect this pin to VSS through an external 10-kΩ resistor", SLUSBV8C p. 3).

## 9. Firmware (contesto)

- nRF Connect SDK / Zephyr, MCUboot con aggiornamento via BLE (SMP).
- Primo caricamento: scrivere `UICR.REGOUT0 = 5` (0x10001304) e `UICR.PSELRESET[0/1] = 18` (0x10001200/0x10001204), poi riavvio.
- Programmatore: Raspberry Pi 3/4 con OpenOCD in bit-bang. I GPIO del Pi sono a 3,3 V; al primo avvio il target è a 1,8 V. In serie su SWDIO, SWCLK e RESET ci sono resistenze da 1 kΩ, sull'adattatore e non sul tag.
- Scritture in flash (15–18 mA) mai durante la trasmissione BLE a potenza alta: il REG0 in modo alta tensione ha un limite di corrente esterna.

## 10. Rischi noti (già individuati)

- VDD scende sotto 3,3 V con la cella sotto circa 3,6 V (VDDH deve superare VDD di 0,3 V), e la flash smette di funzionare sotto 2,7 V.
- Margine VIN del BQ25101: 5 V meno lo Schottky danno circa 4,7 V; la soglia VIN-DPM è circa 4,3 V.
- Con un carico sopra circa 1,3 mA durante la carica, la terminazione (10 % di I_CHG) non scatta.
- Antenna: zona libera non quotata da Ebyte, modulo vicino al bordo e piste sotto, resina sopra. Prova di portata prevista.
- HASL con BGA a passo 0,4 mm e LGA a passo 0,5 mm (JLC consiglia ENIG).
- Nessuna protezione termica della carica (TS fisso).
- Q1 (AO3401A): caduta e comportamento in carica da verificare a banco con cella dritta e invertita.
- Due package a sfere passo 0,4 mm (BQ25101 e TPS22916C): Standard PCBA, ENIG, raggi X; ticket DFM a JLC.
- Verifiche precedenti: 65 test sui fogli tecnici sulla v0.4 (0 bloccanti), revisioni di Gemini e Copilot (correzioni applicate nella v0.5).

## 11. Cosa chiediamo al revisore

Controllare in particolare:

1. **Errori di schema**: pin sbagliati, pin che dovrebbero essere collegati e non lo sono (es. DEC del nRF52840 dentro o fuori dal modulo, condensatori richiesti da Ebyte o Nordic), configurazione SPI dell'IMU, flash.
2. **Alimentazione e caricatore**: correttezza del modo alta tensione con VDDH dalla cella, REG0 a 3,3 V, BQ25101 (ISET, TS a 10 kΩ, CHG, condensatori), percorso di ricarica dai contatti e requisito R5.
3. **Nuovi componenti della v0.5** (sez. 8): TPS22916C, Q1 AO3401A (orientamento, comportamento in carica), TVS D3 (posizione e valore), R8. Hanno introdotto nuovi problemi?
4. **Layout e antenna**: E73 a 0,3 mm dal bordo, piste sotto il modulo, piano di massa a 2 strati.
5. **Producibilità JLC**: 2 strati, HASL o ENIG, distanza rame-bordo, BGA 0,4 mm.
6. **Requisiti non coperti**, o scelte migliori a parità di costo.

**Formato della risposta** (tabella, un problema per riga):

| ID | Gravità (bloccante / importante / consiglio) | Area | Problema | Evidenza (foglio tecnico, pagina o sezione) | Correzione proposta |
|---|---|---|---|---|---|

Indicare anche cosa si è verificato e si considera corretto, e cosa non si è potuto verificare per mancanza di dati.

Nella versione PDF di questo documento seguono in appendice lo schema elettrico, i render del PCB, la BOM e il CPL per JLC. Gerber e disegno quotato sono disponibili su richiesta.
