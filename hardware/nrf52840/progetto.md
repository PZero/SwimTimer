# Tag su misura nRF52840 — progetto (proposta)

**Stato:** studio del 2026-10-25 (schema e PCB v0.2 fatti; v0.3 in corso, vedi sotto), nessun acquisto. Componenti in `bom.md`. Prototipo attuale (ESP32-S3 SuperMini + BMI160) in `../bom.md` e `../schema.md`.

**Obiettivo:** tag da portare sotto la cuffia, ~19 × 21 × 7,2 mm resinato (disposizione B), con sensore di profondità e vibratore, LiPo ~20 mAh, ricarica a contatto in una custodia tipo AirPods, prodotto e montato da JLCPCB.

## Schema a blocchi

```
 custodia (5 V, molle pogo + magneti)
   │ VIN   GND
   ▼
 [TVS] → [Schottky] ──┬──► BQ25101 (13,5 mA, 4,2 V) ──► LiPo 20 mAh (con PCM)
                      │        │ /CHG → GPIO               │ BAT
                      └─ 1M/1M → GPIO "in custodia"         ▼
                                                    VDDH  nRF52840 (MDBT50Q)
                                                          REG0 LDO → VDD 3,3 V (UICR.REGOUT0)
                                                          REG1 DC/DC → core
                                                          SAADC: VDDHDIV5 = misura batteria
                         VDD 3,3 V ─┬─ LSM6DSV16X  (SPI, INT1/INT2: dati pronti, risveglio)
                                    ├─ W25Q256JV   (QSPI, 32 MB)
                                    ├─ MS5837-02BA (I2C, profondità)
                                    └─ LED rosso 0603 (anodo sulla batteria, GPIO in assorbimento)
                         VDDH ──[2×47 µF]── vibratore Ø 6 mm ── N-MOSFET ← GPIO (PWM)
                         SWD: piazzole interne per il primo avvio (sotto la resina)
```

Note di progetto:
- **VDDH direttamente dalla LiPo** (modo "alta tensione" dell'nRF52840): niente regolatore esterno. ⚠ In questo modo VDD esce a **1,8 V di serie**: il firmware (o il primo flash) deve scrivere `UICR.REGOUT0 = 3,3 V`, altrimenti la flash a 3 V non parte. VDD a 3,3 V (deciso in v0.1 per il LED e la flash) permette di usare la batteria fino a ~3,5 V.
- **Batteria con VDDHDIV5** sul SAADC: nessun partitore esterno, nessuna perdita a riposo (SlimeVR usa un partitore con interruttore; qui non serve).
- **IMU su SPI** (8 MHz, meno tempo di CPU sveglia rispetto all'I2C) con FIFO: l'nRF si sveglia ~3 volte al secondo, legge un blocco e torna a dormire.
- **Le piazzole non portano mai la tensione della batteria**: senza custodia VIN è tirato a massa dal partitore → niente elettrolisi in acqua tra i contatti.
- **Risveglio**: dall'IMU (movimento o doppio tocco, come sul prototipo) e dal pin "in custodia" (estrazione = accensione, inserimento = sonno e ricarica).

## Cosa riusare dai progetti SlimeVR nRF

Fonti: [SlimeVR-Tracker-nRF](https://github.com/SlimeVR/SlimeVR-Tracker-nRF) (firmware, Zephyr/nRF Connect SDK, licenza MIT/Apache 2.0), [SlimeVR-Tracker-nRF-PCB](https://github.com/SlimeVR/SlimeVR-Tracker-nRF-PCB), [slimenrf3 su OSHWLab](https://oshwlab.com/sctanf/slimenrf3), [documentazione Smol Slimes](https://docs.slimevr.dev/smol-slimes).

| Area | Cosa fanno | Cosa riusiamo |
|---|---|---|
| Moduli | slimenrf r3 = Ebyte E73 (nRF52840); versioni precedenti con Insight SiP ISP1807 e ISP1507 (8 × 8 mm); molti cloni "SuperMini nRF52840" | conferma che E73 e ISP1807 sono montabili e funzionano; ISP1807 per la v2 ultra piccola |
| IMU | driver con FIFO per LSM6DSV, LSM6DSO/DSM, ISM330BX, ICM-45686, ICM-42688, BMI270; la loro classifica mette LSM6DSV e ICM-45686 ai primi posti | scelta dell'IMU, configurazione FIFO, calibrazione del giroscopio, uso del clock esterno dell'IMU (`clk-gpios`) |
| Magnetometri | MMC5983MA, BMM350, LIS2MDL… | non servono a noi (direzione assoluta inutile in vasca) |
| Carica | caricatore con pin `chg`/`stby` letti dal firmware; pin `dock` per la base; base di ricarica con 3 contatti per 8 tracker a 300 mA | lettura stato di carica, rilevamento custodia, idea della base a 2–3 contatti |
| Batteria | partitore con interruttore (`power-gpios`) sul SAADC | noi usiamo VDDHDIV5 (più semplice) |
| Alimentazione | DC/DC (`reg1` in modo DCDC), opzionalmente LDO separato | DC/DC attivo su REG1 |
| Sonno | System OFF con risveglio dall'IMU (`int0-gpios`) o pulsante | stesso schema |
| Bootloader | UF2 (Adafruit) su USB | **diverso**: niente USB nel tag sigillato → MCUboot + aggiornamento via BLE (SMP/mcumgr) |
| Radio | ESB proprietario verso un dongle | **diverso**: BLE verso display e pagina web |

Anche Zephyr ha già i driver: `st,lsm6dsv16x`, `invensense,icm45686`, `meas,ms5837`, `nordic,qspi-nor`.

## Memoria: 32 MB

| Frequenza | Dati per ora (6 assi × 16 bit + tempo + intestazioni) | Ore in 32 MB (~31 MB liberi, 1 MB per la copia del firmware di MCUboot) |
|---|---|---|
| 50 Hz | ~2,8 MB | **~11 h** |
| 100 Hz | ~5,5 MB | ~5,5 h |
| 50 Hz + pressione a 5 Hz | ~2,9 MB | ~10,5 h |

32 MB coincidono con l'autonomia della batteria (~12 h di registrazione): 64 MB (W25Q512JV, stesso package 8 × 6) non servirebbero finché la cella è da 20 mAh. Scaricamento via BLE: una sessione di 1 h (~3 MB) in 30–60 s; la memoria piena in 5–10 min.
Trucco per i consumi: **cancellare la flash mentre è in custodia** (la cancellazione è la parte più costosa delle scritture), così in acqua si scrive soltanto.

## Bilancio dei consumi (stima, cella 20 mAh, ~16 mAh utilizzabili)

| Voce | Nuoto (registra a 50 Hz, BLE attivo) | Fermo fuori dalla custodia | In custodia, custodia scarica |
|---|---|---|---|
| IMU LSM6DSV16X | 0,65 mA (alte prestazioni) | ~5 µA (solo acc., risveglio al movimento) | 2,6 µA (spenta) |
| nRF52840 (CPU + RAM) | ~0,2 mA (letture FIFO, algoritmi) | ~3 µA (System ON in attesa) | ~1,5 µA (System OFF + risveglio sui GPIO) |
| BLE (annunci 10 Hz, 0 dBm; zero sott'acqua se si usa la pressione) | ~0,15 mA | — (o ~20 µA con annunci a 1 Hz) | — |
| Flash (solo scrittura, pre-cancellata) | ~0,04 mA | 1 µA | 1 µA |
| Pressione 5 Hz | ~0,06 mA | — | 0,1 µA |
| LED a impulsi | ~0,05 mA | — | — |
| Vibratore (~100 impulsi da 200 ms per ora, PWM 50 %) | ~0,2 mA medi | — | — |
| PCM della cella + caricatore | ~3 µA | ~3 µA | ~3 µA |
| **Totale** | **~1,35 mA** | **~12 µA** | **~8 µA** |
| **Autonomia** | **~12 h** (circa 8–10 allenamenti da 1–1,5 h) | ~55 giorni | ~80 giorni (poi interviene il PCM) |

Con l'ICM-45686 il nuoto scende a ~1,1 mA (~14 h). Ricarica a 13,5 mA: **~1,5–2 h** da vuota. Questi numeri vanno **misurati** sui primi tag montati (Nordic PPK2 o un multimetro con shunt) prima di fissare la cella.

## Ingombro stimato

Pianta in scala 1:1 in [`ingombro.svg`](ingombro.svg) (rigenerabile con `python genera_ingombro.py`). Vincolo principale dal foglio Raytac: **antenna sul bordo della scheda** e striscia di **3,8 mm senza rame su tutti gli strati**, larga quanto la scheda. Sopra al modulo, fuori da quella striscia, ci sta esattamente una cella da ~3 × 10 × 12 mm.

| Disposizione | Scheda | Tag finito (0,8 mm di resina sui lati) | Note |
|---|---|---|---|
| **A · lunga** (un solo lato) | 11,5 × 26,5 mm | **~13 × 28 × 7,2 mm** | modulo in alto, sotto la flash con il vibratore sopra, in fondo IMU, pressione, caricatore, LED |
| **B · compatta** (un solo lato) — **scelta dall'utente** | 17,5 × 19,5 mm | **~19 × 21 × 7,2 mm** | flash e vibratore a fianco del modulo, pressione e passivi in basso |
| C · due lati (non disegnata) | ~11,5 × 19 mm | ~13 × 21 × 10 mm | componenti anche sotto il modulo: più corta ma più spessa (il sensore di pressione da 2,75 mm finisce sotto), montaggio JLC più caro, poco posto per il vibratore |

Spessore di A e B: resina sotto 0,5 (copre le piazzole SWD) + PCB 0,8 + modulo 2,05 + biadesivo 0,2 + cella 3,0 + resina sopra 0,6 ≈ **7,2 mm**; il vibratore (2,7 mm) sta sopra la flash (0,75 mm) senza aumentare lo spessore. Peso stimato ~4–5 g.
Contatti di ricarica: due piazzole tonde Ø 2,5 mm sul lato sotto, a filo della resina; piazzole SWD sul lato sotto, annegate. Il sensore di pressione resta scoperto verso l'alto (O-ring).

Confronto: una moneta da 2 € è Ø 25,75 mm; il prototipo attuale (SuperMini 18 × 22 mm + modulo BMI160 + LiPo da 300–500 mAh) è parecchie volte più grande.

## Avviso in acqua: vibratore o cicalino

| | Vibratore (motore a moneta Ø 6 × 2,7 mm) | Cicalino magnetico passivo (es. Huaneng MLT-5020, LCSC C94598, 5 × 5 mm, 4 kHz, ~75 dB, ~0,4 $) |
|---|---|---|
| Chi lo percepisce | tutti, anche i non udenti | solo chi sente; sotto la cuffia arriva per via ossea (come il metronomo FINIS Tempo Trainer) |
| Dubbio | sotto la cuffia e in movimento potrebbe sentirsi poco | potrebbe sentirsi troppo o disturbare chi nuota vicino |
| Intensità regolabile | sì, PWM sulla tensione del motore (soglia minima per partire) | **sì**: duty cycle del PWM (volume) e frequenza (tono; più forte vicino a 4 kHz). Livello impostabile dalla pagina web o dal display |
| Consumo | 50–80 mA mentre vibra | decine di mA, molto meno a volume basso |
| Ingombro sulla scheda B | sopra la flash, nessun mm in più | 5 × 5 mm sulla scheda: con entrambi la scheda passa da 19,5 a ~21 mm (tag ~19 × 22,5 mm) |

**Consiglio:** puntare sul **vibratore** come avviso principale (vale per tutti, discreto, non disturba la corsia) e decidere con una **prova sul prototipo ESP32**, prima dello schema:
- 2 motori a moneta (Ø 6 e Ø 8 mm, per confronto), 1 cicalino MLT-5020, 2 MOSFET AO3400 (SOT-23, facili da saldare a mano), 2 diodi 1N4148, resistenze; ~5 € in tutto.
- Firmware di prova: impulsi singoli, doppi, lunghi; intensità in PWM a 3–4 livelli; da provare sotto la cuffia, prima a secco poi nuotando.
- Se il vibratore si sente bene: solo vibratore. Se è al limite: entrambi sulla scheda (+1,5 mm) e scelta dall'utente nelle impostazioni.

## Sigillatura in resina

- Guscio stampato in 3D (o stampo in silicone) riempito di **resina epossidica o poliuretanica a basso ritiro**; colata sotto vuoto o con degasaggio per evitare bolle sui componenti BGA.
- **Restano fuori dalla resina**: le piazzole di ricarica (a filo della superficie) e la porta del sensore di pressione (il gel del MS5837 deve toccare l'acqua: guarnizione o O-ring intorno al cappuccio, mai resina sopra).
- LED visibile attraverso una resina trasparente o una finestrella.
- Vibratore incollato rigido al guscio prima della colata (la resina rigida trasmette bene la vibrazione; una morbida la smorza).
- **Contatti esterni: solo i 2 poli di ricarica** (più l'eventuale terzo). Le piazzole SWD servono una volta sola, prima della colata (MCUboot + firmware + prova), e poi restano annegate nella resina.
- Niente pulsanti: accensione/spegnimento dalla custodia e dai gesti (doppio/triplo tocco già usati nella pagina).
- La resina sopra l'antenna sposta un po' la frequenza: provare la portata **dopo** la colata.

## Rischi

| Rischio | Gravità | Mitigazione |
|---|---|---|
| **Corrosione dei contatti nel cloro** | alta | nessuna tensione sulle piazzole fuori dalla custodia; oro spesso (ENIG ha solo 0,05–0,1 µm: si consuma) → meglio inserti dorati o in acciaio inox sulla resina, saldati alla scheda; molle pogo e magneti nella custodia; risciacquo con acqua dolce |
| **Antenna** sotto la cuffia, vicino alla testa e all'acqua | media | il BLE in acqua non va comunque (già noto): trasmettere solo fuori dall'acqua/al muro; antenna sul bordo della scheda, zona libera da rame e componenti come da foglio Raytac; prova di portata dopo la resina |
| **Montaggio** (DSBGA 0,4 mm, LGA, modulo con piazzole sotto) | media | JLC li monta con raggi X; nessun componente 0201 fuori dai *basic*; ordinare 5 pezzi e provarne 2 prima di resinare |
| **Carica a corrente bassa** (13,5 mA) | bassa/media | il BQ2510x è fatto apposta (da 10 mA); attenzione al **timer di sicurezza fisso di 10 h** e alla soglia di terminazione (PRETERM); niente caricatori tipo TP4056 (minimo pratico ~50 mA) |
| **Picchi di corrente** su cella da 20 mAh (max 1–2 C = 20–40 mA), soprattutto il **vibratore** (50–80 mA) | alta | vibratore in PWM ~50 % a impulsi brevi, 2 × 47 µF su VDDH, niente radio/flash durante l'impulso, cella ≥ 2 C; soglia di spegnimento del vibratore sotto ~3,6 V; provarlo sul prototipo ESP32 prima del PCB |
| **Disponibilità componenti** (modulo e IMU *extended*, stock variabile) | media | verificare stock il giorno dell'ordine; riserva E73 per il modulo e ICM-45686 per l'IMU già nel progetto |
| **Primo flash e recupero**: dopo la resina l'SWD non è più raggiungibile | alta | programmare e collaudare (radio, IMU, flash, carica) **prima** della colata; da lì solo aggiornamenti via BLE con MCUboot: bootloader non aggiornabile, immagine nuova provata e confermata solo se il BLE funziona (altrimenti torna alla precedente), immagine di riserva nella flash esterna; programmatore J-Link EDU Mini o Raspberry Pi Pico come *debugprobe* con pinza pogo |
| **Porting del firmware** da Arduino/ESP32 a Zephyr | media | algoritmi già indipendenti dall'hardware e messi a punto sul prototipo ESP32; il porting si fa su un tag montato e **non resinato**, collegato all'attrezzo di programmazione |
| **Sensore di pressione** con porta esposta | media | O-ring, prova di tenuta in vasca prima di resinare le altre schede |

## Progetto KiCad v0.2 (2026-10-25)

File in [`kicad/`](kicad/), generati da script a partire da un'unica tabella di dati, così schema e PCB restano coerenti:

| File | Cosa fa |
|---|---|
| `dati_scheda.py` | componenti, codici LCSC, collegamenti, posizioni sulla scheda (**si modifica solo questo**) |
| `genera_schema.py` | scrive `swimtag.kicad_sch` (schema a etichette di rete) |
| `verifica_netlist.py` | confronta la netlist esportata da KiCad con i dati (oggi: 28 reti su 28) |
| `genera_pcb.py` | scrive `swimtag.kicad_pcb`: contorno, componenti, piani di massa, zona antenna, regole JLC |
| `sbroglia.py` | sbroglio automatico con **Freerouting 2.5.0** (Java 25), poi riempimenti di massa |
| `esporta_jlc.py` | Gerber + fori (zip), BOM e CPL nel formato JLC, render, PDF dello schema in `jlc/` |
| `lib/` | simboli, impronte e modelli 3D scaricati da LCSC con `easyeda2kicad` |

**Scheda:** 17,5 × **22,5 mm** (v0.1 era 20,5: +1 mm per le piazzole reali della flash, +2 mm per protezione dei contatti e reset), 4 strati, 0,8 mm. Tag finito ~**19 × 24 × 7,2 mm**.
- Sopra tutti i componenti (montaggio JLC su un lato); sotto solo piazzole: 2 contatti di ricarica Ø 2,5 mm sul bordo basso (VIN a sinistra, GND a 4,2 mm), 5 piazzole SWD Ø 1 mm su due file sfalsate (VDD, SWDIO, SWDCLK, RESET, GND, per molle pogo), BAT+/BAT− sul bordo sinistro, MOT+/MOT− sul bordo destro (fili saldati a mano).
- Antenna sul bordo alto, striscia di 3,8 mm senza rame su tutti gli strati; massa su In1 (piano) e riempimenti di massa sugli altri strati.
- Regole: piste 0,127 mm (minimo 0,1), distanze 0,1 mm, via 0,5/0,3 mm (nessun sovrapprezzo), foro-rame 0,2 mm; via coperti dal solder mask (anche quelli sotto il modulo).
- **DRC: 0 errori**, 401 piste, 55 via (dopo le correzioni delle verifiche, vedi [verifiche.md](verifiche.md)). Restano avvisi di sola serigrafia (contorni delle impronte LCSC) e i pin liberi del modulo, che nello schema hanno la crocetta.

**Pin dell'nRF52840:** QSPI flash P0.17 CS, P0.19 SCK, P0.20/21/22/23 IO0–3 (pin consigliati da Raytac); IMU in SPI P0.15 SCK, P0.13 MOSI, P0.14 MISO, P0.16 CS, INT1 P0.11, INT2 P0.12; pressione I2C P0.26 SDA, P0.27 SCL (pull-up 10 kΩ R5/R6, come da TE); vibratore P0.08 (MOSFET, pull-down 100 kΩ); LED P0.06; stato di carica P0.04; contatti di ricarica → TVS SD05 → Schottky B5819WS → caricatore e VBUS del modulo (evento USB = "nella custodia"); reset hardware all'inserimento nella custodia (AO3400A + 100 nF + 1 MΩ su RESET); VDDH alla batteria, VDD 3,3 V da impostare in `UICR.REGOUT0`.

**Per l'ordine JLC** (non ancora fatto): `jlc/swimtag_gerber.zip`, `jlc/bom_jlc.csv`, `jlc/cpl_jlc.csv`. Opzioni: 4 strati, 0,8 mm, **ENIG** (contatti dorati), montaggio *Economic* lato sopra, raggi X per modulo e BGA. Controllare nell'anteprima JLC la rotazione dei componenti (alcune impronte risultano ruotate di 90/180° rispetto alla libreria JLC).

**Verifiche sui datasheet:** fatte il 2026-10-25, registro in [verifiche.md](verifiche.md) (4 correzioni: due 100 nF sull'IMU, pull-up I2C, 10 µF sull'uscita del caricatore, condensatori del modulo avvicinati). Restano: anteprima JLC (rotazioni e stock) e la protezione dei contatti. Il modulo Raytac non ha modello 3D (nei render si vedono solo le piazzole).

## v0.3 (in corso, 2026-11-01) — solo variante "collaudo"

> **Modulo sostituito il 2026-11-01: Raytac MDBT50Q-1MV2 → Ebyte E73-2G4M08S1C (LCSC C356849).** Il Raytac è a **stock 0** su JLC e LCSC (decisione dell'utente). Il resto della v0.3 è invariato; cambiano pin del modulo, impronta, zona antenna, misure della scheda (ora **19,0 × 46,0 mm**) e spessore. Verifiche sul foglio Ebyte in [verifiche.md](verifiche.md) (ultima sezione). Il testo sotto sul "foglio Raytac" vale solo come storia; il disegno `ingombro.svg` e `genera_ingombro.py` sono ancora quelli del Raytac (v0.2).

Schema generato e verificato anche dopo il cambio di modulo (`kicad/swimtag_collaudo.kicad_sch`, 36 reti, `verifica_netlist.py` 0 differenze, ERC 0 errori); **PCB non sbrogliato**: `kicad/swimtag_collaudo.kicad_pcb` è solo un posizionamento di prova per stimare l'ingombro (render in `kicad/prova/`). I file v0.2 (`swimtag.kicad_sch/pcb`, `jlc/`) restano come storico. La variante *definitiva* è prevista in `dati_scheda.py` (`SWIMTAG_VARIANTE`) ma non ancora implementata.

| Cambio | Come | Pin / rete |
|---|---|---|
| Batteria Ampul 401012 (40 mAh, PCM) | connettore **JST SH 1,0 mm laterale SM02B-SRSS-TB (J1)**, montato da JLC; serigrafia + (BAT) e − (GND) | rete `BAT` |
| Sensori commutati | **TPS22916C (U6)**: VDD → `VDD_SENS`; alimenta IMU (Vdd e Vdd_IO), MS5837, pull-up I2C R5/R6 e i loro 100 nF. La flash resta su VDD | ON = `SENS_ON` pad 6 (P1.13); pull-down 1 MΩ (R8) |
| Misuratore di carica | **MAX17048 (U7)** sul VBAT lato sistema, 100 nF, secondo bus I2C con pull-up 10 kΩ (R9/R10) su VDD sempre acceso | SDA2 pad 34 (P0.22), SCL2 pad 35 (P0.24), ALRT pad 4 (P0.28) |
| Sospensione carica | pin TS del BQ25101 a un GPIO, R2 10 kΩ resta | `TS` pad 2 (P1.10) |
| Condensatori | 2 × 47 µF 0805 (C10, C11) su VBAT; 10 µF su VDDH (C7) e 10 µF sull'uscita del caricatore lato batteria (C12) | |
| Corrente | **J3** (1×2, 1,27 mm) tra `BAT` (cella e caricatore) e `VBAT` (circuito) + ponticello da 1,27 mm; tolto il ponticello il tester va in serie | la carica non passa dal ponticello |
| Collaudo | **J2** 2×12, 1,27 mm, ad angolo retto sul bordo basso: i pin escono dalla resina verso il basso | tabella sotto |
| Misure | scheda **19,0 × 46,0 mm** con l'E73 (con il Raytac 17,5 × 34,5; v0.2: 17,5 × 22,5), vedi sotto | |

**Pin del modulo scelti (E73, rete → pad → GPIO).** Fonte: foglio Ebyte cap. 3 e Nordic PS. SPI, I2C e QSPI solo su pin non "bassa frequenza"; sui pin lenti (colonna sinistra, pad 2-10) solo segnali statici.
- Alimentazione e sistema: VDD 19, VDDH (`VBAT`) 23, VBUS (`VIN_D`) 27, GND 5/21/24, RESET P0.18 26, SWDIO 37, SWDCLK 39.
- Lenti: TS 2 (P1.10), CHG_N 3 (P0.03), FG_ALRT 4 (P0.28), SENS_ON 6 (P1.13), IMU_INT2 7 (P0.02), IMU_INT1 8 (P0.29), LED 9 (P0.31), MOT_PWM 10 (P0.30, **PWM ≤ 10 kHz**).
- QSPI (qualsiasi GPIO, registri PSEL): CS 12 (P0.26), IO1 14 (P0.06), IO2 15 (P0.05), IO3 16 (P0.08), SCK 17 (P1.09), IO0 18 (P0.04); i pin consigliati da Nordic non sono esposti tutti (P0.19, 21, 23 mancano).
- IMU in SPI: SCK 20 (P0.12), MOSI 22 (P0.07), MISO 28 (P0.15), CS 30 (P0.17). I2C sensori: SDA 32 (P0.20), SCL 33 (P0.13). I2C misuratore: SDA 34 (P0.22), SCL 35 (P0.24).
- Liberi: P1.11, XL1/XL2 (11, 13, per un eventuale quarzo), DCCH, USB D±, P1.00, P1.02, P1.04, P1.06, NFC.

**Header J2 (pin 1 a destra, file dispari/pari):** 1 VDD (=VREF per il programmatore) · 2 SWDIO · 3 GND · 4 SWDCLK · 5 RESET · 6 GND · 7 VBAT · 8 VDD_SENS · 9 CHG_N · 10 TS · 11 SENS_ON · 12 FG_ALRT · 13 I2C_SDA · 14 I2C_SCL · 15 FG_SDA · 16 FG_SCL · 17 GND · 18 IMU_SCK · 19 IMU_MOSI · 20 IMU_MISO · 21 IMU_CS · 22 GND · 23 IMU_INT1 · 24 IMU_INT2. BAT e VBAT sono anche su J3.

**Ingombro (collaudo, E73, da posizionamento di prova senza sbroglio; render in `kicad/prova/`):**
- **Scheda 19,0 × 46,0 mm** (Raytac: 17,5 × 34,5). Il modulo E73 (13 × 18 mm, antenna sul bordo alto) occupa i primi 18 mm; flash (9,5 × 6,1 mm), IMU, caricatore, sensori, JST, 2 × 47 µF e J2 stanno tutti sotto, sul solo lato sopra (montaggio JLC su un lato). Larghezza 19 mm per avere 2 mm di margine ai lati dei pad e far passare le piste dei pin laterali. Nessuna sovrapposizione di ingombri (controllo DRC delle zone dei componenti), ma lo spazio per lo sbroglio è stato stimato con 0,2 mm tra le zone dei componenti: potrebbe servire ancora 1-2 mm.
- Zona antenna: striscia di **3,7 mm** senza rame su tutti gli strati (dal bordo al pad 1/43 del modulo); la cella 401012 (4 × 10 × 12 mm) sta sopra il modulo tra y = 5 e 17 mm, cioè ≥ 1,3 mm oltre la striscia; il modulo è alto 3,0 mm, la cella ci poggia sopra.
- **Tag finito:** resina +~1,5 mm per lato → **~22 × 49 mm**; con la spina della cella a sinistra (+~5 mm), i pin di J3 a destra (+~3 mm) e quelli di J2 sotto (+~3 mm): **~30 × 52 mm** nel punto più largo e più lungo. **Spessore ~9,2 mm** (scheda 0,8 + modulo 3,0 + cella 4,0 + resina ~1,4), cioè ~1 mm più della versione Raytac (8,2 mm).
- Cambio rispetto al Raytac: la scheda cresce di +1,5 mm in larghezza e +11,5 mm in altezza, il tag finito di ~+4 × +13 mm. La variante *definitiva*, senza striscia di J2/J3, dovrebbe scendere a circa 19 × 38 mm.
- Possibili riduzioni (decisioni dell'utente): flash 16 MB (WSON 6 × 5 mm) al posto di quella da 32 MB (WSON 8 × 6 mm) = −1 mm; componenti anche sul lato sotto (JLC montaggio doppia faccia più caro) = −8 mm circa.
- Non risolto: il 47 µF vicino al modulo/vibratore e C12 vicino al BQ25101 sono lontani dove servono (da avvicinare allo sbroglio). I contatti di ricarica (TP1/TP2) sono sul lato sotto, sotto la flash; le piazzole SWD e quelle del vibratore sul lato sotto.

**Pendenze dello sbroglio:** impronta MAX17048 (KiCad TDFN-8 2×2, EP 0,8 × 1,2) da confrontare con quella LCSC; il PCB v0.2 sbrogliato non va riusato; `esporta_jlc.py` ora scrive in `jlc/v0.3_<variante>/` e include anche i componenti a foro passante nel CPL.

## Piano a tappe

**(a) Prototipo: resta l'ESP32-S3 SuperMini + BMI160** (decisione dell'utente 2026-10-25)
- Su di esso si mettono a punto gli algoritmi (registrazioni e video) e si prova l'avviso in acqua: vibratore Ø 6 mm e cicalino con un MOSFET su un GPIO, sotto la cuffia.
- Niente scheda di sviluppo nRF intermedia: il firmware Zephyr nasce direttamente sui primi tag definitivi.

**(b) Schema e PCB (KiCad)** — v0.1 fatta il 2026-10-25 (vedi sopra)
- Schema e layout 4 strati, regole e librerie JLC; simbolo/impronta MDBT50Q dal foglio Raytac.
- Firmware `firmware/tag-nrf/` su nRF Connect SDK (VS Code + estensione nRF Connect) con overlay della scheda: lettura IMU con FIFO, servizio GATT compatibile con la pagina `tools/`, annuncio BLE per il display, registrazione su flash, sonno con risveglio dall'IMU, misura della batteria, MCUboot + aggiornamento via BLE (SMP, da aggiungere alla pagina web).
- Revisione dello schema prima dell'ordine (consumi a riposo, piazzole SWD, zona antenna).

**(c) Ordine prototipi** — 5 pezzi montati da JLC (~150–250 $ con spedizione e IVA)
- **Pannello**: più tag sulla stessa scheda (proposta 2 × 3 = 6 tag, ~70 × 80 mm con i bordi), staccati con **mouse bites** (fori di rottura su linguette da 2–3 mm, dove non c'è la zona dell'antenna); il V-cut no, perché taglia da bordo a bordo e su schede così piccole è poco preciso. Bordi di servizio da 5 mm con fiducial e fori di riferimento (servono comunque a JLC per montare schede sotto i 20 mm). Pannello generato con **KiKit** (plugin di KiCad). Prezzo: JLC fa pagare il pannello per le sue misure (fascia fino a 100 × 100 mm) e lo stesso progetto ripetuto è ammesso; più progetti *diversi* sullo stesso pannello pagano un supplemento.
- Il risparmio vale per PCB e spese fisse, **non per i componenti**, che restano a tag. Proposta: 5 pannelli prodotti, **2 montati** = 12 tag (~12 × 25 $ di componenti + spese fisse), i 3 pannelli nudi di scorta.
- Collaudo a banco: carica a 13,5 mA, consumi, portata BLE, scrittura flash.
- Resinare 1–2 pezzi, prova in vasca; gli altri restano aperti per le modifiche.

**(d) Custodia di ricarica e attrezzo di programmazione** — da progettare noi (elettronica + parti 3D stampate con la Bambu Lab A1 mini, piano 180 × 180 mm)
- Stampa 3D, molle pogo dorate, magneti per allineamento e polarità, alimentazione USB-C (eventuale batteria nella custodia in una seconda fase).
- LED di carica sulla custodia (o lettura dello stato dal tag via BLE).

## Risposte dell'utente (2026-10-25) e conseguenze

- **Modulo Raytac MDBT50Q-1MV2** e **IMU a ±4 g**: confermati.
- **Autonomia richiesta: 3 ore.** Al nuoto servono ~4–5 mAh (3 h × ~1,4 mA) più qualche giorno di attesa (~2 mAh a settimana). Basta una cella da **15–20 mAh**: la 40 mAh non serve e aumenta l'ingombro, che è il vincolo principale. Si tiene la 20 mAh solo se il vibratore la richiede (picchi: 20 mAh × 2 C = 40 mA).
- **Memoria:** 3 h a 50 Hz sono ~8,4 MB. 32 MB = 3–4 allenamenti senza scaricare; **16 MB (W25Q128JV, WSON 6 × 5 mm invece di 8 × 6)** = un allenamento e mezzo, con meno ingombro. Da decidere.
- **Ingombro:** scelta la disposizione **B compatta** (~19 × 21 × 7,2 mm), vedi *Ingombro stimato*. ISP1807 scartato dall'utente.
- **Feedback in acqua:** il vibratore è l'unico avviso mentre si nuota, ma va provato: sotto la cuffia il tag è premuto sul cranio, che trasmette bene le vibrazioni. Alternativa da provare insieme: un **cicalino** piezo o magnetico (come il FINIS Tempo Trainer, un metronomo che si mette sotto la cuffia e si sente bene in acqua). Prova sul prototipo ESP32 con entrambi prima di fissare lo schema; sulla scheda si può lasciare l'impronta e montarlo o no.
- **Budget: 50 € per la sola parte JLC** (PCB + montaggio + componenti + spedizione). JLC monta **almeno 2 schede** (minimo del montaggio economico, da riverificare):

| Voce JLC (2 tag con MDBT50Q, stima) | Con sensore di pressione | Senza |
|---|---|---|
| PCB 4 strati, 5 pezzi | ~8 $ | ~8 $ |
| Spese fisse (impianto ~8 $, stencil ~1,5 $, ~5 componenti *extended* a ~3 $) | ~25 $ | ~22 $ |
| Componenti per 2 tag | ~50 $ | ~38 $ |
| Spedizione economica | ~8 $ | ~8 $ |
| IVA 22 % | ~20 $ | ~17 $ |
| **Totale** | **~110 $ ≈ 95–100 €** | **~93 $ ≈ 80 €** |

  **50 € non bastano** per 2 tag con questi componenti: il modulo da solo costa ~10 $ a tag e il minimo è 2 tag. Leve per ridurre: sensore di pressione non montato al primo giro (impronta pronta; ~−15 €), solo componenti *basic* per i passivi, vibratore saldato a mano (i fili non servono a JLC), eventuali buoni sconto per nuovi clienti del montaggio. Realisticamente **~80 € il minimo**, ~100 € completo.
- **ISP1807 (8 × 8 mm) come opzione:** sì. Non è su LCSC, ma JLC lo può comprare per noi con il servizio **Global Sourcing** (lo prende da DigiKey/Mouser, lo mette nella nostra libreria e lo monta), oppure glielo si spedisce noi (*consigned parts*). Contro: prezzo più alto (DigiKey ~12,5 $; tramite JLC alcuni utenti riportano ricarichi fino al +50 %), 1–3 settimane in più di attesa, piazzole LGA fini (montaggio con raggi X). Costo in più sull'ordine di 2 tag: **~+15–20 €**. Da verificare sul datasheet Insight SiP prima di sceglierlo: piedini VDDH e QSPI disponibili (servono per alimentazione dalla LiPo e flash da 32 MB).
- **Memoria: 32 MB confermati** (W25Q256JV).
- **Stampo per la resina:** rinviato.
- **Da progettare (elettronica + oggetto 3D):** custodia di ricarica, attrezzo di programmazione, stampo per la resina:

| Oggetto | Elettronica | Parte 3D |
|---|---|---|
| Custodia di ricarica | USB-C con resistenze CC da 5,1 kΩ, fusibile ripristinabile, LED; 2 molle pogo e 2 magneti. Basta una schedina da USB-C già pronta: il caricatore sta nel tag | guscio con sede del tag, coperchio, magneti a polarità fissa (il tag non entra al contrario) |
| Attrezzo di programmazione | 5 molle pogo sulle piazzole SWD + Raspberry Pi Pico con firmware *debugprobe*; contatti di ricarica per il collaudo | culla che allinea la scheda (o il pannello) sopra le molle |
| Stampo per la resina | — | guscio stampato che resta come involucro, oppure stampo in silicone ricavato da un modello stampato; sedi per contatti, porta del sensore di pressione con O-ring, finestrella del LED |

## Decisioni proposte (non ancora prese)

| Proposta | Motivo |
|---|---|
| Flash **32 MB W25Q256JV** (**confermato dall'utente**) | 3–4 allenamenti da 3 h senza scaricare |
| Modulo **Raytac MDBT50Q-1MV2** (**confermato dall'utente**); ISP1807 scartato dall'utente | certificato, montabile da JLC |
| IMU **LSM6DSV16X** a **±4 g** (**confermato dall'utente**), ICM-45686 di riserva | rumore 3 volte inferiore al BMI160, fondo scala cambiabile via firmware |
| VDDH dalla LiPo, VDD a 3,3 V da UICR, batteria con VDDHDIV5 | meno componenti, zero perdite di partitori |
| Caricatore **BQ25101** a 13,5 mA (deciso in v0.1) | fatto per celle piccole, protetto fino a 28 V sull'ingresso |
| Sensore di pressione **MS5837-02BA** (**deciso dall'utente** il 2026-10-25) | fase subacquea, uscita dall'acqua, BLE spento sott'acqua |
| **Vibratore** Ø 6 mm in PWM come avviso principale; cicalino MLT-5020 solo se la prova sul prototipo ESP32 lo richiede | vale anche per i non udenti, discreto; volume/intensità regolabili in PWM |
| Cella **15–20 mAh** (non 40) | 3 h di autonomia richieste; l'ingombro è il vincolo principale |
| Firmware su **Zephyr / nRF Connect SDK** con MCUboot e DFU via BLE | driver pronti, stesso stack di SlimeVR, aggiornamento senza aprire il tag |
| Piazzole SWD interne, sotto la resina (**deciso dall'utente** il 2026-10-25) | si programmano una volta prima della colata; all'esterno solo i contatti di ricarica |
| Primo ordine: 2 tag senza pannello; **pannello con mouse bites** (KiKit) dal lotto successivo | budget; il pannello conviene solo con molti tag |
| Disposizione **B compatta**, componenti su un solo lato (**decisa dall'utente**) | ~19 × 21 × 7,2 mm; montaggio JLC su un lato, più economico |
| Nessuna scheda nRF intermedia (**deciso dall'utente**): prototipo ESP32 per gli algoritmi, poi direttamente il tag definitivo | il prototipo è già montato e funzionante |
| Budget JLC: ~80 € senza sensore di pressione, ~100 € completo (obiettivo dell'utente 50 €) | il minimo di 2 tag e il costo del modulo non permettono di scendere a 50 € |
