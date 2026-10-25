# Verifiche prima dell'ordine — tag nRF52840 v0.1

Controllo componente per componente di schema e PCB (`kicad/`) contro i documenti dei produttori.
Esito: ✅ conforme · 🔧 corretto in questa revisione · ⚠️ scelta consapevole (motivata) · ⏳ da fare.

## LSM6DSV16X (U2) — ST AN5763 rev 2, tabella 1 "Internal pin status"
Il datasheet su st.com non era raggiungibile (né da riga di comando né dal browser); la nota applicativa AN5763 riporta la stessa tabella dei pin.

| Pin | Indicazione ST (modo 1, senza hub ausiliario) | Scheda | Esito |
|---|---|---|---|
| 1 SDO/SA0 | uscita dati SPI 4 fili | IMU_MISO → P0.14 | ✅ |
| 2 SDx, 3 SCx | "connect to Vdd_IO or GND" se hub analogico/Qvar spenti | a GND | ✅ |
| 4 INT1, 9 INT2 | uscite, di default forzate a massa | P0.11, P0.12 | ✅ |
| 5 Vdd_IO, 8 Vdd | non lasciare flottanti; 100 nF per pin, il più vicino possibile | VDD 3,3 V, **C2 e C6 da 100 nF a ~1 mm dai pin** | 🔧 prima c'era un solo 100 nF a 5 mm: aggiunto C6, IMU ruotato di 180° |
| 6, 7 GND | massa | GND | ✅ |
| 10 OCS_Aux, 11 SDO_Aux | "connect to Vdd_IO or leave unconnected" (pull-up interno) | liberi | ✅ |
| 12 CS | 0 = SPI; pull-up interno di default (SPI a riposo) | IMU_CS → P0.16 | ✅ |
| 13 SCL/SPC, 14 SDA/SDI | ingressi senza pull-up | P0.15, P0.13 | ✅ — firmware: non lasciarli flottanti nel sonno (vedi sotto) |
| Impronta | LGA-14 2,5 × 3 mm, numerazione antioraria vista da sopra | impronta LCSC C5267406 | ✅ |

## MS5837-02BA (U5) — TE datasheet rev A8 (12/2019), pag. 14
| Voce | Indicazione TE | Scheda | Esito |
|---|---|---|---|
| Pin | 1 GND, 2 VDD, 3 SCL, 4 SDA | uguale | ✅ |
| Impronta | 3,3 × 3,3 mm, piazzole a passo 2 mm | impronta LCSC C2887129, stesso verso | ✅ |
| Condensatore | 100 nF tra VDD e GND | C4 accanto al sensore | ✅ |
| Pull-up I2C | 10 kΩ su SDA e SCL | **R5, R6 10 kΩ** | 🔧 prima si usavano i pull-up interni dell'nRF: aggiunti come da TE |
| Indirizzo | 0x76 (1110110x) | unico dispositivo I2C | ✅ |
| Alimentazione | 1,5–3,6 V, salita continua | VDD 3,3 V | ✅ |

## BQ25101 (U4) — TI SLUSBV8C
| Voce | Indicazione TI | Scheda | Esito |
|---|---|---|---|
| ISET | R = K_ISET / I, K_ISET 135 AΩ, 0,54–13,5 kΩ | 10 kΩ → **13,5 mA** (0,7 C per 20 mAh) | ✅ |
| TS | senza NTC: 10 kΩ verso VSS | R2 10 kΩ | ✅ |
| Terminazione | fissa al 10 % (BQ25101) = 1,35 mA (minimo 1 mA) | — | ✅ |
| Condensatore IN | 1–10 µF | C5 10 µF | ✅ |
| Condensatore OUT | 1–10 µF | **C7 10 µF** | 🔧 prima 2 × 22 µF sulla batteria (fuori intervallo): ora 10 µF |
| /CHG | open-drain, serve pull-up | pull-up interno di P0.04 (firmware) | ✅ |
| Timer | sicurezza fisso 10 h | ricarica ~2 h | ✅ |

## MDBT50Q-1MV2 (U1) — Raytac spec ver. K
| Voce | Indicazione Raytac | Scheda | Esito |
|---|---|---|---|
| Antenna | modulo sul bordo, nessun rame sotto l'antenna su ogni strato (3,8 mm) | zona vietata 3,8 mm su tutti gli strati | ✅ |
| Alimentazione (VDDH ≥ 3,6 V) | rif. 8.2: VDDH 10 µF, VDD 10 µF, DCCH libero in modo LDO | **C7 a 1,6 mm da VDDH, C1 sotto il pin VDD**, DCCH libero | 🔧 avvicinati (prima a 4–5 mm) |
| VBUS | rif. 8.2: 10 µF | collegato ai contatti di ricarica, condensatore C5 (10 µF) sulla stessa rete ma a ~7 mm | ⚠️ VBUS serve solo a rilevare la custodia, il regolatore USB resta spento |
| 32 kHz | facoltativo, si può usare l'oscillatore RC interno | nessun quarzo | ✅ firmware: `CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC` |
| SWD | SWDIO, SWDCLK, RESET (P0.18) | piazzole sotto, a passo 2 mm | ✅ |

## W25Q256JVEIQ (U3) — Winbond
| Voce | Scheda | Esito |
|---|---|---|
| Pin 1 /CS, 2 IO1, 3 IO2, 4 GND, 5 IO0, 6 CLK, 7 IO3, 8 VCC | collegati alla QSPI dell'nRF sui pin consigliati da Raytac | ✅ |
| Pad termico | a GND (consentito) | ✅ |
| 100 nF su VCC | C3 a ~4 mm dal pin (più vicino non c'è spazio: sopra la zona antenna, a destra il bordo) | ⚠️ |
| 32 MB | indirizzamento a 4 byte da abilitare nel firmware | ⏳ firmware |

## Vibratore, LED, regole JLC
| Voce | Esito |
|---|---|
| AO3400A (Vgs(th) ≤ 1,45 V, pilotato a 3,3 V), pull-down 100 kΩ sul gate, diodo 1N4148WS sul motore | ✅ |
| LED rosso con anodo sulla batteria: a LED spento il pin vede al massimo ~2,6 V (< VDD + 0,3 V) | ✅ |
| Piste ≥ 0,1 mm, distanze ≥ 0,1 mm, via 0,5/0,3 mm, foro-rame ≥ 0,2 mm, rame-bordo ≥ 0,2 mm, via coperti | ✅ DRC |
| Nessuna protezione ESD/inversione sui contatti di ricarica | ⚠️ tolta per spazio, polarità garantita dai magneti (domanda 23) |

## Note per il firmware (nate dalle verifiche)
- Scrivere `UICR.REGOUT0 = 3,3 V` al primo avvio (di serie VDD esce a 1,8 V e la flash non partirebbe).
- Abilitare il pin di reset su P0.18 (`PSELRESET`) per poter usare la piazzola RESET.
- Nel sonno: tenere pilotate (o con pull-down) le linee SPI verso l'IMU, che non hanno pull-up interni (ST: "the input pins that are not pulled-up/pulled-down must be polarized by the host").
- /CHG del caricatore con pull-up interno; VBUS (evento USB) per "nella custodia".
- Flash: modalità a 4 byte di indirizzo, QE già attivo nella versione IQ (da verificare in lettura del registro di stato).

## Ancora da fare prima di confermare l'ordine
- ⏳ Caricare Gerber, BOM e CPL nell'anteprima JLC: controllare rotazioni e stock dei 5 componenti *extended*.
- ⏳ Decisione dell'utente sulla protezione dei contatti (domanda 23).
