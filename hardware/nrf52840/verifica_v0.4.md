# Verifica indipendente della scheda tag v0.4 "economica" (2026-11-03)

Revisore: agente `elettronica` in ruolo di revisore indipendente (non ha progettato la scheda). Obiettivo: trovare errori **prima dell'ordine a JLC**.

## 0. Cosa è stato verificato e con quali fonti

- **Versione esaminata:** commit `8fd6cc0` (estratto con `git archive` in una cartella temporanea; la scheda è stata modificata da un altro agente mentre la verifica era in corso). File: `swimtag_economica.kicad_sch/.kicad_pcb`, libreria `lib/`, `jlc/v0.4_swimtag_economica/` (BOM, CPL, gerber), `progetto.md` (sezione v0.4).
- **Strumenti:** `kicad-cli` 10.0.6 (netlist, ERC, DRC) e lo script `kicad/verifica_v04.py` (tabella ATTESA scritta a mano dai fogli tecnici, **non** copiata dallo script di generazione, confrontata con la netlist esportata e con i pad del PCB). Uso: `python verifica_v04.py <pcb> <net.xml> [cpl.csv bom.csv]`.
- **Fogli tecnici effettivamente letti** (scaricati dal web):

| Sigla | Documento | Note |
|---|---|---|
| EBY | Ebyte E73-2G4M08S1C User Manual v1.9 (2020-03-30) | pagine 4-7: dati, disegno quotato, tabella pin. Nessuna quota di zona libera antenna |
| NRF | Nordic nRF52840 Product Specification **v1.1** (4413_417 v1.1) | l'unica copia scaricabile; la v1.11 attuale non è raggiungibile (reindirizza a un sito dinamico). Pagine citate = numeri stampati nel documento. Possibili differenze nelle versioni successive |
| TI | TI bq25100/bq25101 SLUSBV8C (nov. 2014) | pp. 3-5, 9-22, YFP0006 |
| WB | Winbond W25Q128JV rev. F (2018-03-27) | par. 3.3 p.5, par. 7.1.4 p.16 |
| ST | ST **AN5763 rev. 2** (LSM6DSV16X) | pp. 2-4: figura dei pin (vista dal basso) e tabella 1. **Il foglio dati DS13510 non è stato raggiunto** (timeout/403): i test che ne dipendono sono "non verificabile" |
| XIA | Seeed XIAO nRF52840 v1.1, schema PDF | letto rendendo la pagina del PDF |
| LCSC/JLC | pagine prodotto LCSC (C478468, C2286, C191023, C97521, C356849, C55213900, C15525, C25744, C25741, C11702, C1525) e JLC (C2286, C191023, C5267406); pagina "PCB capabilities" JLC | LCSC blocca il download diretto dei PDF: i fogli di D1, D2, J1 non sono stati letti |

- **Non fatto:** nessuna misura fisica, nessuna anteprima JLC (richiede l'account), nessun modello 3D. Le rotazioni del CPL restano da confermare nell'anteprima.

## 1. Tabella dei test

Legenda: ✅ superato, ❌ non superato, ⚠️ da attenzione, ❓ non verificabile.

| ID | Test | Esito | Evidenza | Azione richiesta |
|---|---|---|---|---|
| A1 | Simbolo U1 (E73) ↔ tabella pin Ebyte: i 43 pad e i 20 usati (GND 5/21/24, VDD 19, VDDH 23, RST 26, SWDIO 37, SWDCLK 39, GPIO 11-17 dispari, 12, 14, 28, 30, 32-35) | ✅ | EBY p.5-7 (la tabella estratta dal PDF è confusa, riletta con il disegno di p.5); nomi GPIO coerenti con la tabella pin Nordic (P0.00=XL1, P0.01=XL2, P0.18=nRESET) | nessuna |
| A2 | Simbolo U2 (LSM6DSV16X): 1 SDO/SA0, 2 SDx, 3 SCx, 4 INT1, 5 Vdd_IO, 6-7 GND, 8 Vdd, 9 INT2, 10 OCS_Aux, 11 SDO_Aux, 12 CS, 13 SCL, 14 SDA | ✅ | ST AN5763 fig. 1 p.2 e tab. 1 p.3-4 | nessuna |
| A3 | Simbolo U3 (W25Q128JVS, SOIC-8): 1 /CS, 2 DO, 3 /WP(IO2), 4 GND, 5 DI, 6 CLK, 7 /HOLD(IO3), 8 VCC | ✅ | WB par. 3.3 p.5 | nessuna |
| A4 | Simbolo U4 (BQ25101): A1 OUT, A2 IN, B1 TS, B2 ISET, C1 CHG, C2 VSS (spin bq25101: C1 = /CHG, nel bq25100 è PRE-TERM) | ✅ | TI p.3 (disegno e tabella "Pin Functions", nota "Spins have different pin definitions"); confronto tabella dispositivi p.3: bq25101 = CHG | nessuna |
| A5 | Simbolo D1 (LED): pin 1 = K, pin 2 = A (`Device:LED`) | ⚠️ | Convenzione KiCad; foglio dati KT-0603R (C2286) non scaricabile, polarità fisica del contenitore non letta dal documento | confermare nell'anteprima JLC (D1: catodo verso R3) |
| A6 | Simbolo D2 (1N5819WS): 1 = K, 2 = A | ⚠️ | Convenzione SOD-323; foglio dati C191023 non scaricabile (la pagina LCSC mostra un'immagine del pinout senza testo) | confermare catodo/lato fascia nell'anteprima JLC |
| A7 | Simbolo J1 (header 2 pin): 1 = VBAT (+), 2 = GND | ⚠️ | Pezzo `PZ1.27-1x2PLT-L7.2-R`: fisicamente simmetrico, la polarità è solo una scelta del progetto e della serigrafia ("+" sul pad 1) | nessuna sul pezzo; saldare i fili rispettando la serigrafia. Considerare una protezione contro l'inversione (vedi consiglio 9) |
| B1 | Impronta U1: 43 pad, pad 1 a destra in basso (vista dall'alto), 1-10 destra, 11-25 alto, 26-43 sinistra; passo 1,27; pad interni a 2,1 mm dal bordo; corpo 13 × 18, antenna in basso | ✅ | Confronto con EBY p.5 (vista dall'alto = immagine speculare della "Bottom pad"): quote 2,6 / 4,505 / 3,97 / 2,1 / 1,27 coincidono entro 0,03 mm. Unica differenza: pad 3 a y = 4,50 invece di 4,47 (0,03 mm, irrilevante). Pad 0,9 × 2,0 contro 0,8 di Ebyte | nessuna |
| B2 | Impronta U2 (LGA-14 2,5 × 3,0, passo 0,5): numerazione e chiralità | ⚠️ | Numerazione verificata contro ST AN5763 fig. 1 (vista dal basso): l'impronta è l'immagine dall'alto ruotata di 180°, **non** speculare (chiralità corretta: pad 1 in basso a destra, 1-4 a destra, 5-7 sopra, 8-11 a sinistra, 12-14 sotto). Quote dei pad (0,6 × 0,27, centri a ±1,17 / ±0,92) **non verificabili** senza DS13510 | confrontare con il disegno meccanico del DS13510 (par. "Package information") prima dell'ordine |
| B3 | Impronta U3: SOIC-8 208 mil (KiCad `SOIC-8_5.3x5.3mm_P1.27mm`), pad 1 in alto a sinistra a rot 0 | ✅ | Impronta standard KiCad, pad a ±3,6 mm; pad 5-8 risalgono a destra; 4 a GND | nessuna |
| B4 | Impronta U4: DSBGA 0,4 mm, matrice A-C × 1-2 | ✅ | TI YFP0006 (p.30-31): sfere ∅ 0,25, passo 0,4 × 0,4; A1 angolo in alto a sinistra in vista dall'alto. Impronta e posizione sul PCB sono rotazioni pure (non speculari) della vista dall'alto. Pad ∅ 0,20 contro 0,23 consigliato da TI (leggermente piccoli, accettabile) | nessuna (vedi M5 per la finitura) |
| B5 | Impronta D1: `LED_0603_1608Metric`, pad 1 = catodo, serigrafia aperta lato catodo | ✅ | Impronta standard KiCad; sul PCB pad 1 = LED_K (catodo), pad 2 = VDD (anodo) | nessuna |
| B6 | Impronta D2: SOD-323, pad 1 sinistra con barra serigrafica sul lato del pad 1 = catodo | ⚠️ | Impronta da EasyEDA; pad 1 = VIN_D (lato caricatore) = catodo: corretto per un serie al contatto. Foglio dati non letto | anteprima JLC |
| B7 | Impronta J1: pad 0,74 × 2,1 sfalsati (±0,63 × ±1,55) | ❓ | Foglio dati C55213900 non scaricabile (LCSC blocca); disegno dell'impronta da easyeda2kicad | confrontare con il PDF LCSC aperto nel browser: pad sfalsati, passo 1,27 |
| C1 | Netlist esportata ↔ tabella attesa (85 pin) | ✅ | `verifica_v04.py`: 85 pin attesi, 0 differenze, 0 pin collegati non attesi | nessuna |
| C2 | PCB ↔ schema (rete di ogni pad) | ✅ | 0 differenze; i 25 pad senza rete hanno solo il nome automatico `unconnected-…` | nessuna |
| C3 | Pin lasciati liberi: giusti? | ✅ | U1: 23 pad liberi (P1.11 ecc., DCCH 25, VBUS 27, D± 29/31, NFC 41/43) tutti ammessi (vedi D5, D7); U2: OCS_Aux e SDO_Aux liberi ("Connect to Vdd_IO or leave unconnected", ST AN5763 tab.1); SDx/SCx a GND ("Connect to Vdd_IO or GND if the analog hub and/or Qvar are disabled"). Nessun pin da collegare è libero: flash /WP e /HOLD alti tramite R4, DEC/GND/VDD del modulo collegati | nessuna |
| D1 | VDDH dalla cella, modo alta tensione | ✅ | NRF par. 5.3.1 p.61: si entra in alta tensione quando l'alimentazione è solo su VDDH e VDD non è collegato a una sorgente. Schema: rete VBAT sul pad 23, rete VDD sul pad 19 usata solo come uscita; le due reti non si toccano | nessuna |
| D2 | REGOUT0: indirizzo e valore per 3,3 V | ✅ | NRF par. 4.5.1.8 p.46: UICR base 0x10001000 + 0x304 = **0x10001304**; VOUT: 0=1,8; 1=2,1; 2=2,4; 3=2,7; 4=3,0; **5=3,3 V**; 7=predefinito 1,8 V. Scrivere ad es. `0xFFFFFFFD` (bit 2:0 = 5; si possono solo azzerare bit senza cancellare la pagina UICR) | nessuna; sequenza di programmazione nei consigli (2.3, punto 1) |
| D3 | Margine VDDH − VDD | ⚠️ | NRF par. 5.3.8.2 p.80-81: VREG0,DROP ≥ 0,3 V (VDDH deve superare VDD di 0,3 V). Con 3,3 V servono VDDH ≥ 3,6 V; sotto, VDD segue VDDH − 0,3 V. Flash: VCC minimo 2,7 V (WB par. 9) → il tag funziona completo solo con cella ≥ 3,0 V circa | usare la soglia di taglio batteria ≥ 3,2 V nel firmware (spegnere la scrittura flash e il BLE sotto 3,3 V); la cella ha il PCM |
| D4 | Corrente esterna da VDD (modo alta tensione) | ⚠️ | NRF p.80-81: IEXT,HIGH = 25 mA con potenza radio ≤ 4 dBm; **IEXT,LOW = 5 mA con radio > 4 dBm**. Carichi su VDD: flash fino a 15-18 mA in scrittura (WB, ICC3/ICC4), IMU ~1 mA, LED 1,4 mA | firmware: non scrivere in flash mentre il BLE trasmette a +8 dBm (potenza radio ≤ 4 dBm oppure tempi separati) |
| D5 | DCCH libero ammesso? | ✅ | NRF fig. 15 p.63 (alta tensione, solo LDO) e fig. 211 p.587 (config. 2, batteria su VDDH): DCCH senza induttore. Nota NRF p.62: **mai abilitare il DC/DC senza il filtro LC** (dispositivo e debug inibiti) | firmware: lasciare `DCDCEN0` = 0 (DCCH non ha induttore sul modulo). Il DC/DC REG1 (`DCDCEN`) dipende dall'LC interno al modulo, non documentato nel manuale Ebyte: non abilitarlo nel primo prototipo |
| D6 | Condensatori su VDD e VDDH | ⚠️ | NRF fig. 211: VDD 4,7 µF, VDDH 4,7 µF, VBUS 4,7 µF (config. 2). CVDD capacità effettiva ammessa 1,7-5,5 µF (NRF p.80). La scheda ha 10 µF su VDD (C1) e su VDDH (C7, più C6 del caricatore): C15525 è X5R 6,3 V (LCSC): a 3,3 V la capacità effettiva scende (stima non misurata: circa 3-5 µF, quindi dentro l'intervallo). Ebyte non indica condensatori (DEC sono nel modulo) | accettabile; se in prova c'è instabilità provare 4,7 µF su C1 |
| D7 | VBUS (pad 27) libero | ⚠️ | I riferimenti Nordic (fig. 211-214) mostrano sempre VBUS con 4,7 µF verso massa, ma nessun testo prescrive il comportamento senza USB. Il pad flottante entra nel rilevatore USB (eventi USBDETECTED) solo se si abilita la periferica | firmware: non abilitare USB né i relativi eventi del SoftDevice; se compaiono eventi spurii aggiungere 100 kΩ a massa in una revisione successiva |
| E1 | ISET: corrente risultante | ✅ | TI p.3: 13,5 kΩ = 10 mA … 0,54 kΩ = 250 mA; KISET = 135 A·Ω (tipico): **10 kΩ → 13,5 mA** (0,34 C per una cella da 40 mAh); dentro l'intervallo consigliato 10-250 mA | nessuna |
| E2 | TS con 10 kΩ a massa | ✅ | TI p.3 (Pin Functions, TS): "If NTC sensing is not needed, connect this pin to VSS through an external 10-kΩ resistor". 50 µA × 10 kΩ = 0,5 V (zona normale: né TTDM né disabilitazione) | nessuna |
| E3 | CHG open drain | ✅ | TI p.3: basso = in carica, open drain = non in carica o ciclo concluso; max 7 V, sink 15 mA (p.4). P0.20 con pull-up interno a VDD (3,3 V): compatibile | firmware: pull-up interno acceso; "alto" = non in carica **oppure** fine ciclo **oppure** guasto timer (par. 8.3.9, timer) |
| E4 | VIN minima e VIN-DPM rispetto a 5 V − Schottky | ⚠️ | TI p.4-5: tensione di funzionamento consigliata **4,45-6,45 V**, UVLO 3,15-3,45 V, VIN-DPM 4,25-4,37 V, OVP 6,52-6,82 V. 1N5819WS (LCSC): 0,6 V a 1 A, a 13,5 mA tipico ~0,2-0,3 V → VIN_D ≈ 4,7 V con 5,0 V: margine > 0,3 V rispetto a VIN-DPM. Con 4,75 V (USB minimo) si scende a ~4,5 V: al limite | alimentare dal dock con ≥ 5,0 V (il programmatore usa il 5 V del Pi con un PTC da 0,1 A: va bene) |
| E5 | Condensatori IN/OUT | ⚠️ | TI p.3: 1-10 µF su IN e su OUT; p.4 (ESD): servono almeno 1 µF su IN e 2 µF su OUT (ok). Qui IN = 10 µF (C5), OUT = 10 µF (C6) **più** 10 µF di C7 sulla stessa rete (20 µF nominali, sopra l'intervallo 1-10 µF; la capacità effettiva con la polarizzazione non è stata misurata). C15525 è da 6,3 V: su un ingresso da 5 V con extra-tensioni da inserzione TI (par. 9.2.2.1.4) consiglia componenti con tensione nominale adeguata | consigliato: C5 con tensione ≥ 10 V (es. 4,7 µF X5R 10 V 0402) e valutare di togliere C6 o C7 |
| E6 | Confronto con lo schema pubblico del Seeed XIAO nRF52840 | ✅ | XIA (pagina 2): chip BQ25100 (C1 chiamato PRETERM ma collegato a P0.17 "CHG"), IN 2,2 µF, OUT 2,2 µF, **TS = 10 kΩ a massa** (con nota "Disable Temp sense function, use fixed 10k resistor"), ISET 2,7 kΩ ∥ 2,7 kΩ commutabile (50/100 mA), nessun diodo in ingresso, partitore batteria su P0.31/P0.14. Differenze del tag: diodo Schottky in serie (−0,25 V), condensatori da 10 µF, ISET fisso, CHG su P0.20, nessun partitore (si usa VDDHDIV5) | nessuna |
| E7 | Terminazione con carico sull'uscita | ⚠️ | TI p.3-4 e par. 8.3.10 (Termination): terminazione al 10 % di IOUT (1,35 mA, minimo 1 mA di precisione). Il sistema (nRF + IMU) è alimentato dalla rete OUT: se durante la carica il carico supera ~1,3 mA la terminazione non scatta e il ciclo termina al timer di 10 h | nel dock tenere il tag a riposo (IMU spento, BLE fermo) durante la carica |
| F1 | IMU in SPI a 4 fili | ✅ | ST AN5763 tab. 1: SDO/SA0 (pin 1) = MISO, SDA (14) = MOSI, SCL (13) = SCK, CS (12) con pull-up R6 100 kΩ a VDD; SDx/SCx a GND; OCS_Aux/SDO_Aux liberi | firmware: dopo il primo accesso disabilitare I²C/I3C (`IF_CFG.I2C_I3C_disable = 1`) per evitare passaggi accidentali di modo |
| F2 | Livelli e alimentazioni | ✅ | Vdd 1,71-3,6 V e Vdd_IO 1,08-3,6 V (riassunto del DS13510 trovato su un sito secondario, non sul documento ST); VDD = 3,3 V dopo la programmazione dell'UICR | nessuna |
| F3 | Condensatori consigliati | ❓ | DS13510 non letto: la scheda ha 100 nF su Vdd (C4) e su Vdd_IO (C2) più 10 µF sulla rete VDD (C1) | controllare "Electrical connections" nel DS13510 |
| F4 | INT1/INT2 | ✅ | Pin 4 e 9 collegati a P0.26 e P0.06. ST tab.1: all'avvio le uscite sono "forced to ground" (non in alta impedenza): nessun conflitto con ingressi GPIO | nessuna |
| G1 | Flash in SPI semplice: CS con pull-up, /WP e /HOLD alti | ✅ | WB par. 3.3 p.5; R5 100 kΩ su CS, R4 10 kΩ su pin 3 e 7 | nessuna |
| G2 | Stato QE di fabbrica | ✅ | WB par. 7.1.4 p.16: per i codici **"IQ"/"JQ" (W25Q128JVSIQ) QE = 1 fisso**: IO2/IO3 abilitati e /HOLD disabilitato; per "IM"/"JM" QE = 0. Con IO2/IO3 alti tramite R4 il comportamento è corretto in entrambi i casi | nessuna |
| G3 | VCC con VDD 1,8 V al primo avvio | ✅ | WB par. 9 (Operating Ranges, tab. Recommended Operating): VCC 2,7-3,6 V (50 MHz). A 1,8 V il flash non risponde ma non si danneggia (max assoluto −0,6/+4,6 V) | firmware: non accedere alla flash prima che REGOUT0 sia 3,3 V (dopo il reset successivo alla scrittura UICR) |
| H1 | GPIO esistenti e non riservati; nessuno è pin "bassa frequenza" | ✅ | NRF tab. pin (aQFN73) e EBY p.5-7: i "low frequency" (10 kHz) sono P0.02, P0.03, P0.09, P0.10, P0.28-31, P1.01-P1.07, P1.10-P1.15. Usati per SPI (P0.00, P0.01, P0.05, P1.09, P0.13, P0.15, P0.17, P0.24) e per i segnali lenti (P0.06, P0.20, P0.22, P0.26): nessuno dell'elenco | nessuna |
| H2 | P0.18 come RESET | ✅ | NRF par. 4.5.1.4: `UICR.PSELRESET[0]` (0x10001200) e `[1]` (0x10001204) devono contenere lo stesso valore: PIN = 18, PORT = 0, CONNECT = 0 → **0x00000012**. Senza questa scrittura P0.18 è un normale GPIO (il pogo RESET non fa nulla) | scrivere i due registri nella stessa sessione di REGOUT0 |
| H3 | XL1/XL2 (P0.00, P0.01) usati come GPIO | ⚠️ | EBY p.4: "Crystal oscillator 32 MHz" (nessun 32,768 kHz citato); p.6: XL1/XL2 "Connect to 32.768 kHz crystal" → il modulo non ha il quarzo lento, ma il manuale non lo scrive esplicitamente. NRF fig. 211 e par. 5.4: se LFCLK = XTAL i pin sono di oscillatore | verificare sulla prima scheda (nessun quarzo tra pad 11 e 13); firmware: **LFCLK da RC o sintetizzato (mai XTAL)**, altrimenti il clock non parte e il codice resta bloccato |
| H4 | Nota Nordic sui pin vicino alla radio / SPI ad alta frequenza | ❓ | Nella PS v1.1 non esiste una nota di questo tipo: la tabella dei pin segna solo "Standard drive, low frequency I/O only". Non verificabile se le versioni successive della PS (1.11) aggiungano note su SPIM3 a 32 MHz | usare SPIM a ≤ 8 MHz (IMU e flash lo reggono); non scendere sotto con SPIM3 senza leggere la PS corrente |
| I1 | LED: anodo su VDD, corrente | ✅ | D1: pad 2 (anodo) su VDD, pad 1 (catodo) su R3 1 kΩ → P0.22 in assorbimento. (3,3 − ~1,8) / 1 kΩ ≈ 1,4-1,6 mA. A VDD = 1,8 V (primo avvio) non si accende, nessuna corrente nei diodi di protezione | firmware: acceso con livello **basso** |
| I2 | Polarità D1, D2, J1 su impronta e serigrafia | ✅ | D1: serigrafia aperta lato catodo (pad 1 = LED_K); D2: barra sul lato del pad 1 (catodo, rete VIN_D), anodo su VIN (TP6); J1: "+" a 1,2 mm dal pad 1 (VBAT) e "−" dal pad 2 (GND) sulla F.SilkS | nessuna |
| J1 | Ogni designatore in BOM e CPL | ✅ | 20 componenti montati = 20 righe CPL = 20 designatori BOM (elencati uno per uno); nessuno in più né in meno; TP1-TP7 non montati | nessuna |
| J2 | Codici LCSC = parti volute | ✅ | C478468 = BQ25101YFPR (DSBGA-6); C2286 = KT-0603R rosso 0603; C191023 = 1N5819WS (Hottech, SOD-323, 40 V, 1 A); C97521 = W25Q128JVSIQ (SOIC-8 208 mil); C356849 = E73-2G4M08S1C; C55213900 = header 1x2 1,27 mm SMD sfalsato (SHOU HAN PZ1.27-1x2PLT-L7.2-R); C15525 = CL05A106MQ5NUNC 10 µF 6,3 V X5R; C1525 = CL05B104KO5NNNC 100 nF 16 V X7R; C25744 = 10 kΩ 1 %; C25741 = 100 kΩ 1 %; C11702 = 1 kΩ 1 %; C5267406 = LSM6DSV16XTR | nessuna |
| J3 | Tipo Basic/Extended | ⚠️ | Verificato su JLC: C2286 e C191023 **Basic**; C5267406 **Extended**; E73 Extended (fonte secondaria). Non confermati: C97521 (la pagina JLC non riporta il tipo; progetto.md dice Basic), passivi 0402, BQ25101, header | controllare il totale nel carrello JLC (4 Extended attesi: E73, IMU, BQ25101, header) |
| J4 | Rotazioni CPL | ⚠️ | CPL = rotazione KiCad (U3 270 = 0 + correzione 270 per i SOIC, già verificata dal progettista nell'anteprima JLC, commit 2455e71; coordinate Y negative come KiCad e origine gerber 0,0 coerenti: Edge.Cuts da X0 Y0 a 21,59 × −26). Per i pezzi con impronta easyeda2kicad (U1, U2, U4, D2, J1) l'orientamento coincide con quello EasyEDA/JLC per costruzione; per D1 (impronta standard KiCad) la polarità JLC non è garantita | **anteprima JLC obbligatoria** prima di pagare, controllando: pin 1 di U1 (angolo in basso a destra del modulo a rot 0; con rot 180 l'antenna deve finire in alto), U2 (pin 1), U4 (A1), D1 (catodo), D2 (fascia), J1 |
| J5 | Quantità e coordinate | ✅ | CPL = coordinate del PCB (differenze 0, Y con segno invertito); quantità BOM: 4 × 10 µF, 3 × 100 nF, 3 × 10 kΩ, 1 × 1 kΩ, 2 × 100 kΩ, 1 LED, 1 diodo, 1 header, 4 integrati/moduli = 20 | nessuna |
| K1 | DRC rieseguito | ✅ | `kicad-cli pcb drc --severity-all --all-track-errors` (copia in percorso corto): **0 violazioni, 0 non collegati**. In un percorso molto lungo KiCad non trova la libreria `swimtag` e dà 10 avvisi `lib_footprint_issues`: sono un artefatto della lunghezza del percorso (Windows 260 caratteri), non del progetto | nessuna |
| K2 | ERC rieseguito: i 34 `pin_to_pin` sono innocui? | ✅ | **0 errori, 34 avvisi `pin_to_pin`** (20 "Unspecified–Passive", 14 "Unspecified–Unspecified"): derivano dai simboli generati con pin di tipo "unspecified", che impedisce a KiCad di controllare conflitti elettrici (due uscite, ingressi flottanti). Non indicano collegamenti sbagliati: i collegamenti sono stati verificati a parte con C1-C3 | nessuna (in futuro assegnare i tipi pin per riattivare il controllo) |
| L1 | Zona antenna | ⚠️ | EBY non fornisce alcuna quota di zona libera (solo "antenna lontana da metallo", "esposta", p.8-9). Sul PCB: keep-out 3,7 mm sul bordo alto, larga quanto la scheda, su F.Cu e B.Cu (nessuna pista, via o riempimento); 0 piste e 0 via con y < 3,7 mm; l'antenna del modulo (fine corpo a 0,2 mm dal bordo) cade tutta dentro la zona. Lato sinistro: bordo a 1,3 mm dal corpo del modulo | misura di portata obbligatoria (RSSI in aria e col tag in mano); in acqua il 2,4 GHz non passa: la portata si misura fuori dall'acqua |
| L2 | Rame e piste sotto il modulo | ⚠️ | EBY p.8: sotto il modulo evitare piste digitali ad alta frequenza, analogiche e di alimentazione; se inevitabile, farle passare sul lato opposto al modulo. Sul PCB 62 segmenti hanno un estremo sotto il modulo, **in gran parte su F.Cu** (stesso lato del modulo): SPI della flash (FL_MOSI 8, FL_CS 6, FL_MISO 6), VDD, GND, LED, CHG_N; su B.Cu solo SWDIO, VDD, RESET, ecc. | non bloccante (prototipo di registrazione, BLE usato a riposo); la misura di portata dirà se serve spostare le piste |
| L3 | Distanza rame-bordo | ✅ | Pad del modulo a **0,30 mm** dal bordo sinistro (calcolo: 7,8 − 6,5 − 1,0 = 0,3 mm), piste ≥ 0,32 mm. JLC: minimo rame-bordo **0,2 mm** (pagina "PCB capabilities") | nessuna |
| M1 | Piste e distanze minime | ✅ | Tutte le 313 piste a 0,127 mm; distanze 0,127 mm (regola progetto); JLC 2 strati 1 oz: 0,10/0,10 mm. Distanza minima via-pista di altra rete 0,148 mm; distanza pad-pad SMD ≥ 0,15 mm (JLC) rispettata nei pacchetti passo fine (BGA 0,2 mm tra pad, LGA 0,23 mm) | nessuna |
| M2 | Via | ✅ | 29 via ∅ 0,6 / foro 0,3 mm (anello 0,15 mm). JLC: foro minimo 0,15 mm (consigliato 0,2), via minimo 0,25 mm; anello ≥ 0,18 mm vale per le piazzole con foro (PTH), non per i via; il progetto non ha PTH | nessuna |
| M3 | Contorno e spessore | ✅ | 21,59 × 26,0 mm, 0,8 mm, 2 strati, HASL: tutti opzioni standard JLC (dimensione minima 3 × 3 mm) | nessuna |
| M4 | Serigrafia | ⚠️ | JLC: altezza testo minima 1,0 mm, larghezza tratto 0,15 mm. Sul PCB i testi misurano 0,8 mm (lato B) e 0,9 mm ("+" e "−"); le tacche sono a 0,15 mm | non bloccante; i testi usciranno poco leggibili. Portarli a 1,0 mm se c'è spazio |
| M5 | Finitura HASL e componenti a passo fine | ⚠️ | JLC (articolo "Comparing HASL and ENIG"): HASL **non adatta a componenti a passo fine e BGA** (planarità). Qui: BQ25101 DSBGA a **0,4 mm** (pad ∅ 0,2) e LGA a 0,5 mm. Se U4 non salda bene la carica non funziona (e con lei il test di ricarica del prototipo) | **decisione prima dell'ordine:** scegliere ENIG (costo extra da quotare in JLC) oppure accettare il rischio su 2 schede di prova. Raccomandato ENIG |
| M6 | Compatibilità con il servizio Economic | ✅ | Componenti solo sopra; 0 PTH; 20 componenti; nessuna richiesta fuori standard | nessuna |
| N1 | Piazzole TP1-TP7 ↔ pogo dell'adattatore | ✅ | Coordinate dal bordo in alto a sinistra: TP1-TP5 (5,08; 7,62; 10,16; 12,70; 15,24 mm; y = 12,70), TP6 (7,62; 17,78), TP7 (12,70; 17,78) = pogo P1-P7 di `swimtag_programmatore.kicad_pcb` (differenza 0,00 mm); stesse reti (VDD, SWDIO, SWDCLK, RESET, GND, VIN, GND). Ø 2,0 e 2,5 mm sulla griglia 2,54 mm | nessuna |
| N2 | Faccia e specchiatura | ✅ | L'adattatore usa le coordinate del PCB senza specchiatura: corretto perché il tag poggia con il lato **componenti verso l'alto** e le piazzole (B.Cu) verso il basso sui pogo, per cui la pianta coincide con quella vista dall'alto del PCB. L'etichetta "TAG (faccia in giù)" nel PCB dell'adattatore si riferisce alle piazzole e può confondere | rendere l'etichetta più chiara ("piazzole verso i pogo, componenti in alto") |
| N3 | Battute di centraggio (S1-S3) | ❓ | Calcolate dallo script sul contorno 21,59 × 26 mm (gioco 0,1 mm); non misurabili senza il pezzo fisico | provare con un PCB nudo (JLC li spedisce 5) prima di saldare i pogo |
| N4 | VDD del tester isolata dal Pi | ✅ | Il pogo VDD (P1) non è collegato al connettore del Pi (netto `VDD_T`); sul connettore solo 5 V (via PTC e ponticello JP1 spento), GND, SWDIO, SWDCLK, RESET con 1 kΩ in serie. Il tag si programma con la cella collegata | nessuna |
| O1 | Tabella pad → GPIO → funzione per il firmware | ✅ | Capitolo 3, ricavata dalla netlist verificata (C1) | nessuna |

### Conteggio per esito

| ✅ | ❌ | ⚠️ | ❓ | Totale |
|---|---|---|---|---|
| 42 | 0 | 19 | 4 | 65 |

## 2. Difetti

### 2.1 Difetti bloccanti (da correggere prima dell'ordine)

**Nessuno.** Netlist, piedinature, impronte (con l'eccezione di U2 non verificabile fino al DS13510), DRC, ERC, regole di fabbricazione e coincidenza con l'adattatore sono corretti.

### 2.2 Decisioni e controlli da fare **prima di pagare** (non sono errori, ma possono rovinare le 2 schede)

1. **Finitura ENIG o HASL (M5).** HASL con BGA a 0,4 mm è sconsigliata da JLC. Raccomandato ENIG sul costo, oppure ordinare sapendo che U4 può non saldare.
2. **Anteprima JLC (J4):** rotazioni e pin 1 di U1, U2, U4, D1, D2, J1. Il rischio maggiore è U2 (LGA, orientamento non verificato con JLC), poi D1 (LED invertito: non si danneggia, ma non si accende).
3. **Confronto di U2 col disegno meccanico del DS13510 (B2):** quote dei pad, non solo la numerazione.
4. **Stock dell'E73 (J2/J3):** la pagina LCSC riporta da 99 a circa 1000 pezzi a seconda della fonte; ne servono 2.

### 2.3 Consigli (in ordine di importanza)

1. **Sequenza di programmazione UICR (D2, H2):** con la cella collegata e il tag a 1,8 V di VDD scrivere in una sola sessione `UICR.REGOUT0 (0x10001304) = 0xFFFFFFFD` (3,3 V), `PSELRESET[0] (0x10001200) = PSELRESET[1] (0x10001204) = 0x00000012` (P0.18 = RESET), poi un reset. Solo dopo il reset VDD = 3,3 V e flash/IMU funzionano. Verificare con un tester VDD = 3,3 V prima di montare altro.
2. **LFCLK dall'RC (H3):** i pad 11 e 13 (P0.00, P0.01) sono usati come IMU_CS e IMU_MISO: un firmware con LFCLK = XTAL (default di molti SDK/Arduino) li pilota come oscillatore e si blocca.
3. **Potenza radio e scritture flash (D4):** limite di 5 mA di corrente esterna con radio > 4 dBm.
4. **Soglia di taglio batteria (D3):** VDD = VDDH − 0,3 V sotto 3,6 V; flash ≥ 2,7 V.
5. **Condensatori del caricatore (E5):** C5 ≥ 10 V; valutare di togliere C6 o C7.
6. **Carica a riposo (E7):** il carico sulla rete OUT impedisce la terminazione (timer 10 h).
7. **Documentazione incoerente:** in `progetto.md` (sezione v0.4, voce "Stato di carica") compare ancora "`CHG_N` su P0.03", mentre la tabella dei pin e `verifiche.md` riportano P0.20 (pad 32). Correggere. Nella stessa sezione "Nessun dato inviato all'app cambia" compare due volte.
8. **Etichetta dell'adattatore (N2):** chiarire "TAG (faccia in giù)".
9. **Inversione della cella (A7):** J1 non ha protezione; un errore di saldatura dei fili brucia il modulo. Marcare i fili (rosso su "+").
10. **VBUS (D7):** se il SoftDevice segnala eventi USB spurii, 100 kΩ a massa.
11. **ERC (K2):** assegnare i tipi ai pin dei simboli generati, per riattivare il controllo sui conflitti.

## 3. Tabella pinout per il firmware

Nomi GPIO = `Pp.nn` (porta.numero). Pad = numero del pad dell'E73 (EBY p.5-7). Tutti i segnali a 3,3 V (VDD dopo REGOUT0).

| Pad E73 | GPIO | Rete | Direzione | Funzione e note per il firmware |
|---|---|---|---|---|
| 11 | P0.00 | IMU_CS | uscita | CS dell'IMU, attivo basso; R6 100 kΩ a VDD. **Pin XL1: LFCLK non da XTAL** |
| 13 | P0.01 | IMU_MISO | ingresso | SDO/SA0 dell'IMU (pin 1). **Pin XL2** |
| 15 | P0.05 | IMU_MOSI | uscita | SDA/SDI dell'IMU (pin 14) |
| 17 | P1.09 | IMU_SCK | uscita | SCL/SPC dell'IMU (pin 13). SPI modo 3 (CPOL=1, CPHA=1) o modo 0, ≤ 8 MHz con SPIM0-2 |
| 12 | P0.26 | IMU_INT1 | ingresso | INT1 dell'IMU (pin 4); all'avvio forzato a massa dall'IMU finché non lo si configura |
| 14 | P0.06 | IMU_INT2 | ingresso | INT2 dell'IMU (pin 9) |
| 30 | P0.17 | FL_CS | uscita | /CS della flash, attivo basso; R5 100 kΩ a VDD |
| 28 | P0.15 | FL_MISO | ingresso | DO (IO1) della flash |
| 33 | P0.13 | FL_MOSI | uscita | DI (IO0) della flash |
| 35 | P0.24 | FL_SCK | uscita | CLK della flash. /WP e /HOLD (IO2/IO3) alti con R4: solo SPI semplice, QE = 1 di fabbrica (W25Q128JVSIQ) |
| 32 | P0.20 | CHG_N | ingresso con pull-up | /CHG del BQ25101: basso = in carica; alto = non in carica / ciclo finito / guasto timer |
| 34 | P0.22 | LED | uscita (assorbe) | LED rosso, **acceso a livello basso** (anodo su VDD, 1 kΩ, ~1,5 mA) |
| 26 | P0.18 | RESET | ingresso | nRESET dopo la scrittura di `UICR.PSELRESET`; collegato solo al pogo RESET |
| 37 / 39 | SWDIO / SWDCLK | SWDIO / SWDCLK | | Pogo TP2 / TP3 |
| 23 | VDDH | VBAT | | Cella; lettura batteria: canale SAADC `VDDHDIV5` (nessun partitore, nessun GPIO) |
| 19 | VDD | VDD | | Uscita REG0 = 3,3 V (da UICR); alimenta IMU, flash, pull-up, LED |
| 5, 21, 24 | GND | GND | | |
| 25 | DCCH | - | | Libero: **non abilitare DCDCEN0** |
| 27 | VBUS | - | | Libero |
| altri | - | - | | Non collegati (P1.11, P1.10, P0.03, P0.28, P1.13, P0.02, P0.29, P0.31, P0.30, P0.08, P0.04, P0.12, P0.07, D-, D+, P1.00, P1.02, P1.04, NFC, P1.06) |

Registri UICR da scrivere (una volta, con SWD): `REGOUT0` (0x10001304) = 5 (3,3 V); `PSELRESET[0]` e `[1]` (0x10001200 / 0x10001204) = 18.

## 4. Da riverificare dopo l'aggiunta del TPS22916C (interruttore di alimentazione dell'IMU)

| Test | Cosa cambia e cosa controllare |
|---|---|
| C (netlist) | Nuova rete IMU_VDD (commutata): pin 5 e 8 dell'IMU e C2/C4 passano dalla rete VDD alla rete commutata; pin del TPS22916C (VIN, VOUT, ON, GND, e il pin CT se presente) e il GPIO di abilitazione. Rieseguire `verifica_v04.py` aggiornando la tabella ATTESA (non copiarla dal generatore). Decidere dove va il pull-up di IMU_CS (R6): se resta su VDD, con l'IMU spento passa corrente (~33 µA) nei diodi di protezione dell'IMU |
| D (alimentazione) | Carico aggiuntivo su VDD e caduta del TPS22916C (RON); nuovo GPIO usato; la corrente dell'IMU acceso è nei limiti IEXT (D4) |
| F (IMU) | Ordine di accensione: Vdd e Vdd_IO insieme dalla rete commutata; le linee SPI e INT1/INT2 non devono essere pilotate a livello alto con l'IMU spento (alimentazione parassita attraverso i diodi): GPIO a basso o in alta impedenza prima di togliere l'alimentazione. Tempo di salita del TPS22916C rispetto ai tempi di avvio dell'IMU. Condensatori: il TPS22916C vuole un condensatore su VOUT limitato (verificare sul foglio TI) |
| H (GPIO) | Nuovo pin di abilitazione: deve essere un GPIO non "bassa frequenza" non riservato (controllare che non sia tra quelli già usati) |
| J (CPL/BOM) | Nuova riga BOM/CPL, impronta DSBGA-4 (0,4 mm, in libreria: `DSBGA-4_L0.78-W0.78-P0.40`), tipo Basic/Extended (+3,07 $ se Extended), rotazione e pin 1 nell'anteprima JLC; 21 componenti montati |
| K (DRC/ERC) | Rifare DRC (con `--all-track-errors`) ed ERC in un percorso corto; sbroglio nuovo → riverificare anche distanze e via |
| M (regole JLC) | Il nuovo componente a passo 0,4 mm rafforza il punto M5 (HASL/ENIG); controllare distanze e via del nuovo sbroglio |
| N (adattatore) | Controllare che le piazzole TP1-TP7 non si siano spostate rigenerando il PCB (il programmatore le rilegge da `swimtag_economica.kicad_pcb`: `python genera_kicad.py --drc`) |
| A, B (opzionali) | Piedinatura e impronta del TPS22916C (foglio TI: pin e matrice A1-B2, polarità) |

## 5. File prodotti dalla verifica

- `hardware/nrf52840/verifica_v0.4.md` (questo documento)
- `hardware/nrf52840/kicad/verifica_v04.py` (script ripetibile)
