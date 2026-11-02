# Verifiche prima dell'ordine — tag nRF52840 v0.2

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
| Contatti di ricarica: TVS Semtech SD05 (5 V, 350 W, C85201) subito dopo il contatto VIN, Schottky B5819WS (C22624) in serie contro l'inversione; caduta ~0,3 V → caricatore e VBUS vedono ~4,7 V (VBUS minimo 4,35 V) | 🔧 aggiunti (v0.2); con polarità invertita il TVS conduce: la custodia deve avere un fusibile ripristinabile |
| Reset all'inserimento nella custodia: fronte di VIN → 100 nF → gate di AO3400A (1 MΩ a massa) → RESET basso per ~0,16 s (τ = 0,1 s, soglia ~1 V); all'estrazione il gate va a −5 V (limite ±12 V) | 🔧 aggiunto (v0.2); serve `PSELRESET` = P0.18 nel firmware |

## Misura della batteria
- La tensione della cella è misurata dall'nRF52840 con il canale interno **VDDHDIV5** (VDDH = batteria, nessun partitore esterno): funziona **sempre, sia durante l'uso sia in carica**.
- **In uso**: tensione → percentuale con la curva della LiPo (precisione ~±10 %, migliore a riposo che durante i picchi del vibratore o della radio: misurare a radio ferma).
- **In carica**: la tensione letta è più alta della reale (corrente di carica × resistenza interna, poi 4,2 V fissi nella fase finale) → si mostra "in carica" dal pin /CHG (P0.04) e la tensione solo come indicazione; carica finita quando /CHG torna alto (terminazione a 1,35 mA).
- Nel sonno profondo (System OFF) non si misura: la lettura si fa al risveglio.
- v0.3: aggiunto il *fuel gauge* MAX17048 (vedi sotto); il canale VDDHDIV5 resta come controllo incrociato.

## Note per il firmware (nate dalle verifiche)
- Scrivere `UICR.REGOUT0 = 3,3 V` al primo avvio (di serie VDD esce a 1,8 V e la flash non partirebbe).
- Abilitare il pin di reset su P0.18 (`PSELRESET`) per poter usare la piazzola RESET.
- Nel sonno: tenere pilotate (o con pull-down) le linee SPI verso l'IMU, che non hanno pull-up interni (ST: "the input pins that are not pulled-up/pulled-down must be polarized by the host").
- /CHG del caricatore con pull-up interno; VBUS (evento USB) per "nella custodia".
- Flash: modalità a 4 byte di indirizzo, QE già attivo nella versione IQ (da verificare in lettura del registro di stato).

## Ancora da fare prima di confermare l'ordine
- ⏳ Caricare Gerber, BOM e CPL nell'anteprima JLC: controllare rotazioni e stock dei 5 componenti *extended*.
- ✅ Protezione dei contatti e reset all'inserimento aggiunti (v0.2).


---

# Verifiche v0.3 (2026-11-01) — variante collaudo

Datasheet letti in locale: TI TPS22916 SLVSDO5F (dic. 2021), TI BQ25101 SLUSBV8C, Maxim MAX17048 rev 7 (11/2016), Raytac MDBT50Q spec (cap. 2.4 e 2.5; modulo poi sostituito dall'Ebyte E73, vedi in fondo), TE MS5837-02BA (tabella d'ordine), JST SH. Stock e tipo basic/extended: API JLCPCB del 2026-11-01.

## TPS22916C (U6, interruttore dei sensori) — TI SLVSDO5F
| Voce | Datasheet | Scheda | Esito |
|---|---|---|---|
| Pin YFP (DSBGA-4) | A1 VOUT, A2 VIN, B1 GND, B2 ON; vista dall'alto: ON/GND sopra, VIN/VOUT sotto | impronta `DSBGA-4_L0.78-W0.78-P0.40` costruita così, passo 0,4 | ✅ (impronta da controllare in anteprima JLC) |
| Variante C | attivo alto, **QOD 150 Ω** a spento, salita lenta (tON 1,7 ms a 3,6 V) | scarica rapida di VDD_SENS richiesta | ✅ |
| Soglie ON | VIH ≥ 1 V, VIL ≤ 0,35 V; perdita su ON ±10 nA | GPIO a 3,3 V | ✅ |
| Pull-down su ON | **"smart pull-down" 750 kΩ** interno, attivo finché ON è basso | R8 1 MΩ esterno richiesto: ridondante, costa 3,3 µA a sensori accesi | ⚠️ tenuto per richiesta; si può non montare |
| Corrente a spento | 10 nA tip., 100 nA max; da acceso Iq 0,5 µA | — | ✅ |
| Rds(on) | 70 mΩ a 3,6 V | IMU + MS5837 ≈ 1,5 mA → 0,1 mV | ✅ |
| VIN | 1–5,5 V, blocco della corrente inversa | VDD 3,3 V | ✅ |

**Nessun pin dei sensori va a VDD sempre acceso** (controllo sulla netlist): IMU pin 5 (Vdd_IO) e 8 (Vdd), MS5837 pin 2, R5/R6 e i tre 100 nF sono su `VDD_SENS`; su `VDD` restano solo modulo, flash, ingresso di U6 e pull-up del secondo I2C. Pin 10/11 dell'IMU liberi (ST: "leave unconnected" ammesso), SDx/SCx a GND.

⚠️ **Conseguenze per il firmware (sensori spenti):**
- I GPIO verso IMU e MS5837 non devono restare alti: con VDD_SENS a 0 un pin a 3,3 V alimenterebbe il sensore dal diodo ESD. Prima di spegnere: SCK, MOSI, CS, SDA, SCL a **uscita bassa** (o ingresso scollegato); MISO, INT1, INT2 come **ingressi senza pull-up**.
- Spento, l'IMU perde la configurazione (FIFO, ODR, FSM): va riprogrammato a ogni accensione; MS5837: reset e lettura PROM ogni volta, almeno 3 ms dopo l'accensione (tON 1,7 ms + avvio).
- **Il risveglio dall'IMU (INT) non funziona a sensori spenti.** Per la sveglia al movimento in System OFF bisogna lasciare VDD_SENS acceso con l'IMU a basso consumo (pochi µA), oppure risvegliare da timer / VBUS. Scelta di firmware, non cambia l'hardware.

## MAX17048 (U7) — Maxim rev 7
| Voce | Datasheet | Scheda | Esito |
|---|---|---|---|
| Pin TDFN-8 | 1 CTG a massa, 2 CELL (sul MAX17048 "non collegato internamente"), 3 VDD (batteria +, 100 nF), 4 GND, 5 ALRT (open-drain), 6 QSTRT (a massa se non usato), 7 SCL, 8 SDA, EP a GND | CTG, QSTRT, GND, EP a massa; **VDD e CELL a VBAT**, C9 100 nF | ✅ |
| Alimentazione | VDD 2,5–4,5 V, misura direttamente la cella | VBAT 3,0–4,2 V | ✅ |
| I2C | indirizzo 0x36, SDA/SCL tolleranti a 5,5 V, VIH ≥ 1,4 V, open-drain: servono pull-up | R9, R10 10 kΩ su **VDD** (sempre acceso), bus separato da quello dell'MS5837 | ✅ |
| ALRT | open-drain, attivo basso, si cancella via I2C | P0.07, pull-up interno nRF | ✅ |
| Consumi | hibernate 3 µA (automatico), attivo 23 µA, **sleep < 1 µA (0,5 tip.)** | — | ✅ |
| **Sleep con linee basse** | sleep se MODE.EnSleep = 1 e SDA e SCL **bassi per più di 2,5 s**; sveglia al primo fronte in salita; in alternativa CONFIG.SLEEP = 1 via I2C (si esce solo scrivendo SLEEP = 0) | con i pull-up da 10 kΩ, tenere le linee basse costa **330 µA per linea** (3,3 V / 10 kΩ): molto peggio del risparmio di 2–3 µA | ⚠️ **non usare le linee basse**; per dormire usare CONFIG.SLEEP via I2C, oppure restare in hibernate (3 µA, preciso). In sleep il MAX non vede carica e scarica: svegliarlo prima di caricare |
| Inserimento batteria | debounce delle prime misure ("può stare lato sistema") | lato sistema (VBAT, dopo J3) | ✅; senza ponticello il MAX non è alimentato |

La percentuale è solo indicativa con una cella da 40 mAh e i picchi del vibratore (1,25 C): leggerla a riposo.

## BQ25101 (U4) — pin TS comandato da GPIO e corrente di carica — TI SLUSBV8C
| Voce | Datasheet | Scheda | Esito |
|---|---|---|---|
| TS basso | "Pulling pin low disables the IC": carica disabilitata sotto 0,125 V (riabilitata sopra 0,175 V), corrente di polarizzazione ridotta a 30 µA, timer azzerato; al rilascio parte un nuovo ciclo con rilevamento batteria e /CHG si riarma | **GPIO P0.25 sul nodo TS**, R2 10 kΩ resta | ✅ **fattibile in modo pulito** |
| TS normale | 50 µA nel 10 kΩ → 0,5 V: zona normale 10–45 °C | GPIO come ingresso scollegato (nessun carico): misura invariata | ✅ |
| TS alto o flottante | **TTDM**: timer e terminazione disattivati | un GPIO a livello alto, anche per errore, disattiverebbe terminazione e timer | ⚠️ **firmware: P0.25 solo come open-drain a massa (S0D1)**, mai uscita alta |
| Fermarsi verso l'80 % | il BQ25101 non ha una soglia propria: carica fino a 4,2 V fissi | l'MCU legge il SOC dal MAX17048 e porta TS a massa; sospeso, il caricatore assorbe solo 75 nA dalla cella | ✅ |
| Verifica batteria collegata | rilevamento batteria all'uscita da TS basso, ripetuto finché la batteria manca | VCELL dal MAX17048 + rilascio di TS e osservazione di /CHG | ✅ (prova da fare a banco) |
| ISET | I = 135 AΩ / R: 10 kΩ → 13,5 mA = **0,34 C** su 40 mAh; 6,8 kΩ → ~19,9 mA = 0,5 C | R1 = 10 kΩ invariato | ✅ consigliati 13,5 mA (carica completa in ~3 h, terminazione a 1,35 mA, più dolce per una cella da 4 mm) |
| Condensatore OUT | "expected range 1–10 µF" | C12 10 µF su BAT; i 2 × 47 µF stanno su **VBAT, a valle di J3**: con il ponticello inserito il caricatore li vede in parallelo alla cella | ⚠️ fuori dall'intervallo TI: il rischio riguarda solo la batteria assente (rilevamento batteria più lento o falsato); con la cella collegata domina la sua impedenza. Da provare a banco |

## Condensatori, connettore batteria, ponticello
| Voce | Esito |
|---|---|
| 2 × 47 µF X5R 6,3 V a 4,2 V: capacità reale ~15–20 µF ciascuno (perdita da polarizzazione in c.c.) | ⚠️ ~35 µF effettivi: bastano per il vibratore in PWM; se serve di più, 1206 o 10 V |
| J3 tra BAT e VBAT: la carica **non** passa dal ponticello (BQ25101, C12 e J1 su BAT) → si misura solo l'assorbimento del circuito, MAX17048 compreso | ✅ |
| Polarità di J1 non protetta (scelta dell'utente): le celle con spina JST sono vendute spesso con i fili **invertiti** rispetto alla serigrafia | ⚠️ controllare con il tester il piedino + prima di collegare |
| J1 SM02B-SRSS-TB: 1,0 mm, ingresso laterale, altezza 2,9 mm, impronta 5,9 × 6,6 mm | ✅ la cella deve avere una spina SH 1,0 mm a 2 poli |

## Pin del modulo (foglio Raytac cap. 2.4/2.5)
- Pin "GPIO vicini alla radio, standard drive, solo bassa frequenza": 3–14, 50, 52, 54, 56–61 → **non usati**.
- Scelti: SENS_ON P0.05 (21), FG_ALRT P0.07 (23), FG_SCL P1.08 (25), FG_SDA P1.09 (26), TS P0.25 (49): tutti "General-purpose I/O". Il secondo I2C a 400 kHz sta quindi su pin normali. Liberi: 47 (P1.00) e 48 (P0.24); P0.00/P0.01 tenuti per un eventuale quarzo a 32 kHz.

## Connettori e pin di collaudo
| Voce | Esito |
|---|---|
| JLC monta componenti a foro passante anche nel montaggio *Economic* (lato singolo; SMD a rifusione, THT a onda; fori non usati protetti), pagina JLC "PCBA Capabilities" | ✅ da confermare nell'anteprima d'ordine |
| Saldatura a onda sul lato sotto, dove stanno i contatti di ricarica dorati e le piazzole SWD | ⏳ rischio da chiarire con JLC prima dell'ordine (protezione o controllo manuale) |
| J2 ad angolo retto C7470112: isolante 2 mm, pin 3 mm: sporgono ~5 mm dal bordo, 2–3 mm fuori dalla resina. La versione verticale (C7470094: isolante 1 mm + pin 4 mm = 5 mm sopra la scheda) **non uscirebbe** dalla resina (~8 mm) | ✅ angolo retto |
| J3 C22438188 (1×2, angolo retto) + ponticello C150949, da comprare a parte | ✅ |
| Stock a 0 per il modulo Raytac (C5118826) e per l'MS5837-02BA (C2887129). MS5837 sostituito con C5785272 (TE MS583702BA01-50 = MS5837-02BA01, tabella d'ordine del datasheet, stesso package) | 🔧 MS5837 / ⚠️ modulo: decisione dell'utente |

---

# Verifiche v0.3, modulo Ebyte E73-2G4M08S1C (2026-11-01)

Il Raytac MDBT50Q-1MV2 è a stock 0 (JLC e LCSC): su decisione dell'utente U1 passa all'**Ebyte E73-2G4M08S1C** (LCSC C356849). Fonti: *E73-2G4M08S1C User Manual v1.9* (Ebyte; copia inglese e specifica cinese del distributore con lo schema del modulo, cap. 3 e 5.1), pagine online Nordic nRF52840 Product Specification (*Pin assignments*, *QSPI*), simbolo/impronta/modello 3D da LCSC con easyeda2kicad. Le sezioni "MDBT50Q" più sopra valgono solo come storia.

| Voce | Foglio Ebyte / Nordic | Scheda | Esito |
|---|---|---|---|
| VDDH esposto | pad 23 "VDH" = VDDH; schema del modulo: VDDH separato da VDD, 4,7 µF a bordo | pad 23 = `VBAT` (cella direttamente) + C7 10 µF | ✅ |
| VDD esposto | pad 19; il foglio dà 1,7-5,5 V e "3,3 V per la massima potenza". Con VDDH alimentato, VDD è l'uscita di REG0 (REGOUT0 = 3,3 V da UICR, già in progetto) | pad 19 = `VDD` + C1 10 µF; i due pad sono distinti e sul modulo non sono uniti | ✅ misurare VDD = 3,3 V sul primo tag |
| VBUS esposto | pad 27 "VBS" = VBUS, ingresso USB 5 V | pad 27 = `VIN_D` (dal caricatore), solo evento "in custodia" | ✅ |
| Pin QSPI | nessun pin fisso nel foglio Ebyte; nel Nordic PS la QSPI ha registri PSEL.SCK/CSN/IO0-3 su **qualsiasi GPIO**. I pin consigliati (P0.17, 19, 20, 21, 22, 23) sul modulo sono esposti solo P0.17, P0.20, P0.22 | QSPI su 6 pad della fila bassa (P0.26, P0.06, P0.05, P0.08, P1.09, P0.04), GPIO in *high drive* (consiglio Nordic) | ✅ ⚠️ SCK a 8-16 MHz, non 32 MHz (fuori dai pin consigliati, nessuna garanzia Nordic) |
| SWDIO, SWDCLK, RESET | pad 37 SWDIO, 39 SWDCLK, 26 P0.18/RESET | stesse piazzole di collaudo; RESET richiede `UICR.PSELRESET` = P0.18 (come col Raytac) | ✅ |
| DC/DC REG1 | schema del modulo: **L1 15 nH e L2 10 µH sul modulo**, quindi DC/DC REG1 utilizzabile; DCCH (pad 25) senza induttore = REG0 in LDO | DCCH non collegato | ✅ |
| Quarzo 32,768 kHz | **assente** (nello schema c'è solo il 32 MHz); XL1/XL2 = P0.00/P0.01 sui pad 11 e 13 | pad 11 e 13 liberi; RC interno come prima | ✅ |
| Condensatori esterni | lo schema del modulo ha già 4,7 µF su VDD, VDDH, DECUSB e i condensatori DEC; il foglio non chiede altro | restano C1 10 µF (VDD), C7 10 µF (VDDH), C5 10 µF (VBUS) | ✅ |
| Zona libera dell'antenna | **nessuna quota nel foglio**: solo "antenna esposta, lontana da metallo". Dal disegno l'antenna ceramica sta nei 3,97 mm tra il bordo corto e la fila di pad 1/43 | zona vietata su tutti gli strati di 3,7 mm dal bordo (`ANTENNA_H`), larga quanto la scheda; modulo a 0,22 mm dal bordo | ⚠️ valore dedotto dal disegno, da confermare con la prova di portata prima della resina |
| Dimensioni e pad | 13,0 × 18,0 ± 0,1 mm, altezza 3,0 ± 0,1; pad perimetrali 0,8 × 1,0 mm a passo 1,27 (mezzo foro); pad interni LGA 0,8 × 0,8 a 2,1 mm dal bordo; 43 pad | impronta LCSC: 0,9 × 2,0 (1 mm di fillet fuori dal modulo) e 0,9 × 0,9, stesse posizioni (confrontata con il disegno) | ✅ |
| Pin "bassa frequenza" | Nordic PS (≤ 10 kHz): P0.02, P0.03, P0.09, P0.10, P0.28-P0.31, P1.01-P1.07, P1.10-P1.15 | SPI, I2C e QSPI solo su pin normali; sui pin lenti solo segnali statici (colonna sinistra) | ✅ |
| Piste sotto il modulo | il foglio sconsiglia piste ad alta frequenza o di potenza sul lato opposto, sotto il modulo | piani di massa In1/In2 pieni; sotto il modulo solo le uscite dei pad interni | ⚠️ da rivedere allo sbroglio (QSPI corta, via vicino al pad) |
| Programmazione | solo J-Link (SWD) | piazzole SWD su due file, come prima | ✅ |

**Assegnazione dei pin (v0.3, E73).** Stesse reti di prima, pin cambiati:

| Rete | Pad | GPIO | | Rete | Pad | GPIO |
|---|---|---|---|---|---|---|
| TS | 2 | P1.10 | | QSPI_CS | 12 | P0.26 |
| CHG_N | 3 | P0.03 | | QSPI_IO1 | 14 | P0.06 |
| FG_ALRT | 4 | P0.28 | | QSPI_IO2 | 15 | P0.05 |
| SENS_ON | 6 | P1.13 | | QSPI_IO3 | 16 | P0.08 |
| IMU_INT2 | 7 | P0.02 | | QSPI_SCK | 17 | P1.09 |
| IMU_INT1 | 8 | P0.29 | | QSPI_IO0 | 18 | P0.04 |
| LED | 9 | P0.31 | | IMU_SCK | 20 | P0.12 |
| MOT_PWM | 10 | P0.30 | | IMU_MOSI | 22 | P0.07 |
| I2C_SDA | 32 | P0.20 | | IMU_MISO | 28 | P0.15 |
| I2C_SCL | 33 | P0.13 | | IMU_CS | 30 | P0.17 |
| FG_SDA | 34 | P0.22 | | RESET | 26 | P0.18 |
| FG_SCL | 35 | P0.24 | | SWDIO / SWDCLK | 37 / 39 | SWD |
| VDD / VBAT (VDDH) / VIN_D (VBUS) | 19 / 23 / 27 | | | GND | 5, 21, 24 | |

Non usati: P1.11 (1), XL1/XL2 (11, 13: per un eventuale quarzo), DCCH (25), USB D-/D+ (29, 31), P1.00 (36), P1.02 (38), P1.04 (40), P1.06 (42), NFC (41, 43; GPIO solo con `UICR.NFCPINS`). **Per il firmware:** MOT_PWM è su un pin a bassa frequenza, quindi PWM del vibratore **≤ 10 kHz** (1-2 kHz va bene); CHG_N usa il pull-up interno di P0.03; i GPIO della QSPI in *high drive*; i pin della QSPI non sono quelli di default (da dichiarare nell'overlay). I dati inviati all'app non cambiano.

## Intestazioni SMD da 1,27 mm (solo informazione, schema invariato)
Cercate su JLCPCB (API del 2026-11-01) per evitare la saldatura a onda sul lato dei contatti dorati.
- **Ad angolo retto, SMD:** Amphenol **20021221-00010C4LF, C180221** (2 × 5 poli; la pagina LCSC dice "Right Angle" e la descrizione JLC "卧贴", cioè montaggio orizzontale; stock 6341, ~1,11 $, extended; profondità 5,5-5,6 mm, altezza da verificare sul disegno Amphenol) e **214012, C780571** (1 × 4 ad angolo retto, stock 245, ~2,68 $). Un 2 × 12 ad angolo retto a magazzino **non c'è**: la serie Amphenol a 12, 20 e 24 poli è a stock 0 (C236048, C240306, C17288418).
- **Verticali SMD:** XUNPU PH1.27-02-xxPWS, da 2 × 2 a 2 × 20 (C41360874-C41360891, 130-1800 pz, 0,08-0,54 $): perno 4 mm + 1 mm di plastica = ~5 mm. Il 2 × 12 non c'è ma si può usare un 2 × 13 (C41360884, 280 pz, 0,35 $) o due 2 × 6 (C41360878, 788 pz, 0,16 $). Altezza ~5 mm: **non esce da ~8 mm di resina**. Le femmine verticali (C22436132, 2 × 12, H 4,3 mm, 1528 pz, 0,26 $) sono ancora più basse.
- **Opzioni:** (a) due header ad angolo retto 2 × 5 (C180221) e J2 ridotto a 2 × 10; (b) J2 come file di piazzole per pogo (come l'SWD): nessuna saldatura a onda; (c) tenere il THT C7470112 e chiedere a JLC la protezione dei contatti dorati.



## Tag-Connect TC2030-NL e piazzole di prova (variante 1c, 2026-11-01)

Impronta presa dalla libreria KiCad 10 (`Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical`, dal disegno Tag-Connect TC2030-IDC-NL); simbolo `Connector:Conn_ARM_SWD_TagConnect_TC2030-NL`.

| Voce | Dato (impronta / disegno) | Nel progetto | Esito |
|---|---|---|---|
| Pad | 6 pad Ø 0,787 mm (0,031"), due file a passo 1,27 mm | stessi pad, lato sotto (B.Cu), nessuna via sotto i pad (zona di divieto dell'impronta) | ✅ |
| Fori di allineamento | 3 NPTH Ø 0,991 mm a (−2,54; 0), (+2,54; ±1,016) mm dal centro | stessi fori; **passano sotto il corpo dell'E73** (x = 13, y = 9,5: nessun pad del modulo vicino, pad laterali a ≥ 2,5 mm); DRC `npth_inside_courtyard` su *ignore* | ✅ ⚠️ controllare nell'anteprima JLC che i fori non tocchino pad del modulo |
| Pinout ARM SWD | 1 VCC (VREF), 2 SWDIO/TMS, 3 nRESET, 4 SWCLK/TCK, 5 GND, 6 SWO/TDO | 1 `VDD`, 2 `SWDIO`, 3 `RESET`, 4 `SWDCLK`, 5 `GND`, 6 non collegato | ✅ come da simbolo KiCad; da riconfermare con il foglio del cavo prima del primo collegamento (non misurato) |
| Alimentazione di prova | VREF serve solo come riferimento di livello (il programmatore non alimenta il tag) | `VDD` = uscita di REG0 (3,3 V da UICR); col tag spento (batteria scollegata) SWD non risponde | ⚠️ programmare con la batteria collegata; il primo avvio (UICR vuoto, VDD a 1,8 V) è da provare |
| Spessore scheda | il cavo senza gambe (NL) si appoggia ai fori: nessun requisito sullo spessore | 0,8 mm | ✅ |
| Resina | il connettore resta annegato come le vecchie piazzole SWD | da fresare/aprire o programmare prima | ⚠️ da decidere con l'involucro |
| Controllo DRC | | 0 errori, 0 non connessi, parità schema/PCB 0 | ✅ |
| Piazzole di prova | Ø 0,8 (4) e Ø 1 mm (3), nomi in serigrafia sotto | CHG_N, SENS_ON, VDD_SENS, FG_ALRT, VBAT, VDD, GND | ✅ |
| Contatti di ricarica | Ø 2,5 mm a 4,2 mm tra i centri (1,7 mm tra i bordi) | TP1 VIN (x = 15,2), TP2 GND (x = 19,4), y = 28,0 | ✅ servirà base a più posti |


## Vibratore SMD per il montaggio JLC (2026-11-01)

| Codice | Componente | Montaggio JLC | Esito |
|---|---|---|---|
| C2942345 | LEADER LBM0625A3217F, moneta Ø 6 mm, 3 V 80 mA | Wave Soldering, solo Standard | scartato |
| C2992359 | LEADER LCM04084521-B1 | Wave Soldering | scartato |
| C41348533 | LEADER LD-SM-430, 4 × 3 × 11 mm | SMT | troppo alto |
| C2836756 | KOTL Z4TH3B0791626, cilindrico 3 V 90 mA | SMT | stock e misure non verificati (LCSC: "Part not found") |

Fonte: pagine jlcpcb.com/partdetail. I motori SMD non sono sigillati: niente lavaggio dopo la rifusione. Decisione: vibratore non montato sui tag di collaudo.


---

# Verifiche v0.4 "economica" (2026-11-02)

Fonti: API JLCPCB (stock, tipo, descrizione parametri) del 2026-11-02; impronte KiCad e easyeda2kicad; per BQ25101, E73 e pin lenti/veloci le verifiche v0.3 sopra (datasheet TI SLUSBV8C, manuale Ebyte v1.9, Nordic PS). **Il datasheet Winbond W25Q128JV non è stato riletto in questa sessione:** i punti sulla flash marcati ⚠️ vanno confermati sul foglio prima dell'ordine.

## Flash W25Q128JVSIQ (U3, C97521) in SPI semplice

| Voce | Dato | Scheda | Esito |
|---|---|---|---|
| Pin SOIC-8 | 1 /CS, 2 DO (IO1), 3 /WP (IO2), 4 GND, 5 DI (IO0), 6 CLK, 7 /HOLD (IO3), 8 VCC | netlist: 1 FL_CS, 2 FL_MISO, 5 FL_MOSI, 6 FL_SCK, 4 GND, 8 VDD, 3 e 7 su `FL_IO23` | ✅ come simbolo KiCad `Memory_Flash:W25Q128JVS` |
| /WP e /HOLD in SPI standard | in SPI semplice con QE = 0 sono funzioni attive (HOLD basso ferma il dispositivo): vanno tenuti alti | R4 10 k da `FL_IO23` a VDD (un resistore per i due pin; con QE = 1 diventano IO2/IO3 e la resistenza resta innocua) | ⚠️ confermare sul foglio Winbond il valore di QE alla consegna |
| Alimentazione | 2,7-3,6 V (descrizione JLC) | VDD = 3,3 V da REGOUT0, C3 100 nF | ✅ |
| /CS durante il reset | GPIO flottanti all'avvio | R5 100 k a VDD | ✅ |
| Capacità | 128 Mbit = 16 MB, 133 MHz | SPI a 8 MHz bastano; ~11,5 kB/s per IMU a 960 Hz sei assi | ⚠️ **~24 min a 960 Hz, ~97 min a 240 Hz, ~3 h a 120 Hz** |
| Impronta | SOIC-8 5,3 × 5,3 mm (EIAJ 208 mil), `Package_SO:SOIC-8_5.3x5.3mm_P1.27mm`; courtyard 9,4 × 5,9 mm | pin 1 con il punto; la JLC (C97521) è "SOIC-8-208mil" | ✅ rotazione da controllare nell'anteprima |

## BQ25101 (U4) senza GPIO su TS

| Voce | Dato (verifiche v0.3, TI SLUSBV8C) | Scheda | Esito |
|---|---|---|---|
| TS | senza NTC: 10 kΩ verso VSS; 50 µA × 10 k = 0,5 V in zona normale (carica abilitata) | R2 10 k a massa, nessun GPIO | ✅ (niente TTDM: il pin non è mai flottante o alto) |
| ISET | 135 AΩ / R: 10 k → 13,5 mA (0,34 C su 40 mAh); terminazione fissa al 10 % | R1 10 k | ✅ |
| /CHG | open drain, basso durante la carica | `CHG_N` su P0.03, pull-up interno | ✅ firmware: abilitare il pull-up |
| Condensatori | ingresso e uscita 1-10 µF | C5 10 µF su VIN_D, C6 10 µF su VBAT | ✅ |
| Rinuncia | niente sospensione della carica a SOC 80 % (serviva il MAX17048) | il caricatore carica sempre a 4,2 V | ✅ accettato per la registrazione |
| Tensione sui contatti | IN max 28 V assoluti, OVP; nessuna via cella → IN | Schottky 1N5819WS in serie, VIN → D2 → `VIN_D` | ✅ |

## Lettura batteria, LED, regole 2 strati

| Voce | Dato | Scheda | Esito |
|---|---|---|---|
| VDDHDIV5 | ingresso interno del SAADC = VDDH/5 (Nordic PS): 4,2 V → 0,84 V | nessun partitore, nessun GPIO; VDDH è `VBAT` (pad 23) | ✅ da provare a banco col tester |
| LED NCD0402R1 | Vf 1,6-2,6 V, 25 mA max (descrizione JLC), rosso 630 nm | anodo su VBAT, 1 k, catodo sul GPIO P0.31: ~2,2 mA a 4,2 V, ~0,5 mA a 3,0 V; con GPIO alto (3,3 V) a 4,2 V la tensione ai capi (0,9 V) è sotto la Vf: spento | ✅ polarità da controllare nell'anteprima |
| Regole JLC 2 strati | piste/distanze 0,127 mm, via 0,6/0,3 mm, foro-rame 0,2 mm | DRC 0 con questi valori; margine di 20 µm nello sbroglio | ✅ |
| Zona antenna | 3,7 mm senza rame su F.Cu e B.Cu (zona vietata) | invariata, modulo a 2,2 mm dal bordo | ⚠️ valore dedotto dal disegno Ebyte (v0.3), prova di portata |
| Sbroglio sotto il modulo | il foglio Ebyte sconsiglia piste veloci sotto il modulo | B.Cu: massa piena, 59 piste di segnale (circa 77 mm in tutto sotto il modulo) | ⚠️ sotto il modulo passano 4,8 mm di FL_CS e 4,7 mm di FL_MISO (SPI a 8 MHz), più INT1/INT2, CHG_N, VIN_D, SWD e RESET: da rivedere se la portata risultasse scarsa |

## Header batteria SMD 1,27 mm (J1, C55213900) e JST SH (confronto)

| Voce | JST SH C160402 | Header 1,27 C55213900 | Header 2,54 SMD C41417359 | Header 2,54 THT C225477 |
|---|---|---|---|---|
| Impronta (pad, mm) | 4,8 × 5,55 = 26,6 mm² | 2,0 × 5,2 = 10,4 mm² | 3,81 × 5,8 = 22,1 mm² | THT (foro Ø ~1) |
| Prezzo | 0,133 $ | 0,008 $ | 0,028 $ | 0,041 $ |
| Tipo / stock | extended / 73858 | extended / 3803 | extended / 48116 | extended / 30477 |
| Economic JLC | sì | sì (da confermare in anteprima) | sì | **no, solo Standard (+~20 $)** |
| Altezza | ~2,6 mm | pin 7,2 mm totali, da accorciare | ~8,5 mm | ~8,5 mm |

Impronte ricavate con easyeda2kicad (pad e quote dal disegno LCSC); il file `lib/swimtag.pretty/HDR-SMD_2P-P1.27-V-M-LS4.2-R1.kicad_mod` contiene solo i pad (2 × 0,74 × 2,1 mm sfalsati di 1,26 mm e 3,1 mm) e il courtyard, senza modello 3D. ⚠️ Non letto il foglio del produttore: portata e tenuta dei pad all'estrazione dei fili da verificare in prova (resina o fermacavo).
