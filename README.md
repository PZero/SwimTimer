# SwimTimer

Tempi automatici in piscina: un tag sotto la cuffia e un display a bordo vasca riconoscono partenza e arrivo, senza pulsanti.

![Stato](https://img.shields.io/badge/stato-prototipo%20ESP32%20funzionante-yellow) ![Scheda](https://img.shields.io/badge/tag%20nRF52840-v0.5%20pronta%20da%20ordinare-green) ![Repository](https://img.shields.io/badge/repository-pubblico-blue) ![Licenza](https://img.shields.io/badge/licenza-da%20definire-lightgrey)

Aggiornato al **2026-11-04**. Repository unico e pubblico `PZero/SwimTimer`: prototipo ESP32, firmware, pagina di analisi (GitHub Pages: https://pzero.github.io/SwimTimer/), tag nRF52840 (KiCad, Gerber, file JLC), programmatore HAT, sfondi tecnici e video.

### Video di presentazione (2 minuti)

[![SwimTimer: video di presentazione su YouTube](media/video/miniatura_youtube.png)](https://youtu.be/_2UzpOqblVI)

Guarda il video su YouTube: **https://youtu.be/_2UzpOqblVI** (musica originale generata per il video; sorgenti in [`media/video/`](media/video/)).

![Render del tag v0.5, vista dall'alto](hardware/nrf52840/kicad/jlc/v0.5_swimtag_economica/render_sopra.png)

## Indice
- [Cos'è SwimTimer](#cosè-swimtimer)
- [Stato attuale](#stato-attuale)
- [Architettura del sistema](#architettura-del-sistema)
- [Prototipo ESP32, firmware 0.4.3 e pagina di analisi](#prototipo-esp32-firmware-043-e-pagina-di-analisi)
- [Tag nRF52840](#tag-nrf52840)
- [Revisioni esterne](#revisioni-esterne-v04)
- [Programmatore HAT per Raspberry Pi](#programmatore-hat-per-raspberry-pi-34)
- [Galleria degli sfondi tecnici](#galleria-degli-sfondi-tecnici)
- [Struttura delle cartelle](#struttura-delle-cartelle)
- [Come rigenerare i file](#come-rigenerare-i-file)
- [Flusso d'ordine JLCPCB](#flusso-dordine-jlcpcb)
- [Roadmap e problemi aperti](#roadmap-e-problemi-aperti)
- [Privacy e sicurezza](#privacy-e-sicurezza)
- [Licenza e autore](#licenza-e-autore)

## Cos'è SwimTimer

**Problema.** In piscina i tempi per vasca e i riposi si perdono. Guardare l'orologio o premere un pulsante interrompe l'allenamento.

**Soluzione.** Un piccolo tag con sensore inerziale (accelerometro e giroscopio) si indossa sotto la cuffia. Riconosce da solo la spinta dal muro (partenza), le virate e la calma all'arrivo. Un display a bordo vasca mostra i tempi.

**Vincolo fisico.** Il BLE a 2,4 GHz non attraversa l'acqua. Il tempo non si misura col segnale radio: lo decide il sensore sul tag. Il BLE serve solo fuori dall'acqua, per riconoscere la vicinanza al display e inviare i dati. Analisi completa: [`docs/IDEA.md`](docs/IDEA.md).

## Stato attuale

| Area | Stato |
|---|---|
| Prototipo ESP32-S3 + BMI160, firmware **0.4.3**, pagina di analisi | Funzionante sul tavolo; prove in vasca non ancora fatte |
| Display LilyGO T-RGB (pace clock a 4 lancette) | Funzionante sul tavolo |
| Tag nRF52840 **v0.5 "economica"** | **Pronta**: 21,59 × 28,0 mm, 2 strati, DRC 0, ERC 0 errori, `verifica_v05.py` 100/100 pin. File JLC in `hardware/nrf52840/kicad/jlc/v0.5_swimtag_economica/` |
| Costo dell'ordine | Circa **125 €** con Standard PCBA, raggi X e coupon: **sopra il tetto di 100 €**, da decidere (tagli in [Costi v0.5](#costi-v05)) |
| Ordine a JLCPCB | **Non ancora fatto**: servono anteprima JLC, scelta HASL/ENIG, ticket DFM e decisione sul costo |
| Firmware del tag nRF52840 | Da scrivere (Zephyr / nRF Connect SDK) |
| Programmatore HAT per Raspberry Pi 3/4 | Progettato, rigenerato sulla v0.5 (TP1–TP7 invariati), DRC 0; **non ancora costruito** |

## Architettura del sistema

```mermaid
flowchart LR
  subgraph TAG[Tag sotto la cuffia]
    IMU[IMU 6 assi] -- SPI --> MCU[nRF52840 / ESP32-S3<br/>BLE]
    FL[Flash] -- SPI --> MCU
    CEL[Cella LiPo] --> MCU
  end
  MCU -- "annuncio BLE (fuori dall'acqua)" --> DSP[Display a bordo vasca<br/>LilyGO T-RGB 2,8 pollici]
  MCU -- "GATT / OTA (fuori dall'acqua)" --> WEB[Pagina di analisi<br/>Web Bluetooth]
  MCU -. "registrazione in flash,<br/>scaricata dopo" .-> WEB
  DSP -- "pace clock, tempi" --> NUO[Nuotatore]
  CUS[Base di ricarica / programmatore] -- "contatti sotto il tag" --> TAG
```

- **Tag.** Sotto la cuffia, premuto sul cranio. Decide da solo START, virate e STOP con l'IMU e registra i dati grezzi in flash.
- **Display a bordo vasca.** Riceve gli annunci BLE del tag senza collegarsi. Mostra un pace clock a 4 lancette. Va in sonno dopo 5 minuti senza tag.
- **Pagina web.** `tools/index.html`: dati dal vivo, registrazioni, calibrazione, aggiornamento firmware via Bluetooth.
- **BLE fuori dall'acqua.** Sott'acqua il segnale sparisce in pochi centimetri: durante la nuotata il tag lavora da solo e consegna i dati quando emerge o a fine sessione.

## Prototipo ESP32, firmware 0.4.3 e pagina di analisi

Il prototipo serve a mettere a punto gli algoritmi prima della scheda su misura.

**Tag (prototipo).** ESP32-S3 SuperMini + BMI160 (GY-BMI160), LiPo con interruttore generale. Distinta: [`hardware/bom.md`](hardware/bom.md). Collegamenti: [`hardware/schema.md`](hardware/schema.md).

**Firmware 0.4.3** (`firmware/test-collegamenti`, arduino-cli, core `esp32:esp32` 3.3.12):
- ±16 g e 100 Hz, impostati a sensori accesi e riletti (fino a 5 tentativi);
- flash con due copie del programma e circa 1,9 MB di LittleFS (circa 40 minuti a 50 Hz);
- doppio tap = inizio registrazione, triplo tap = fine (rilevamento software, poco affidabile: circa 1 volta su 10);
- BLE con dati, stato, comandi, OTA e versione; stessi comandi via USB; aggiornamento via Bluetooth con ritorno automatico alla versione precedente;
- sblocco automatico del bus I2C, LED RGB come riscontro, motivo dell'ultimo riavvio, partitori su GPIO 1 (batteria) e GPIO 2 (pin 5V).

**Pagina di analisi** [`tools/index.html`](tools/index.html), online su <https://pzero.github.io/SwimTimer/> (GitHub Pages del repository **pubblico**, firmware 0.4.3 pubblicato):
- schede "Dal vivo" (batteria, orientamento 3D, radar con scia di 15 s, interpretazione, eventi, grafici) e "Registrazioni";
- calibrazione automatica, finestre Firmware e LED, modalità Demo;
- Bluetooth (Chrome, Edge, Bluefy su iPhone) o USB;
- card batteria con grafico di GPIO 1, GPIO 2 e tensione stimata a riposo.

`tools/assi.html` è la vecchia pagina dei 3 assi, conservata.

**Display** (`firmware/display-prova`): LilyGO T-RGB 2,8 pollici, PlatformIO con espressif32 6.9.0, driver copiato e adattato in `src/trgb/` (licenza MIT, Xinyuan-LilyGO).

**Compilare e caricare il tag:**
```
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc --upload -p <COM> firmware/test-collegamenti
```

Documenti collegati: [`docs/RICERCA-ALGORITMI.md`](docs/RICERCA-ALGORITMI.md), [`docs/LEZIONI-APPRESE.md`](docs/LEZIONI-APPRESE.md) (13 lezioni del prototipo per la scheda miniaturizzata), [`docs/REQUISITI.md`](docs/REQUISITI.md), [`docs/DESIGN.md`](docs/DESIGN.md).

## Tag nRF52840

**Obiettivo.** Sostituire il prototipo con un tag miniaturizzato per la cuffia, montato da JLCPCB, con ricarica a contatto e programmazione dalle piazzole sul lato sotto. Documento di progetto: [`hardware/nrf52840/progetto.md`](hardware/nrf52840/progetto.md).

### Storia delle versioni

| Versione | Data | Scheda | Contenuto | Esito |
|---|---|---|---|---|
| v0.1 | 2026-10-25 | 17,5 × 20,5 mm, 4 strati | Raytac MDBT50Q, LSM6DSV16X, MS5837, flash 32 MB, BQ25101, vibratore | Sostituita |
| v0.2 | 2026-10-25 | 17,5 × 22,5 mm, 4 strati | Aggiunti TVS, Schottky e reset all'inserimento nella custodia; DRC 0 | Storico |
| v0.3 collaudo (1c) | 2026-11-01 | 26 × 30 mm, 4 strati 0,8 mm | Ebyte E73 (Raytac a stock 0), TPS22916C, MAX17048, cella Ampul 401012 su JST SH, Tag-Connect, piazzole di prova; vibratore non montato; DRC 0, 609 piste, 80 via | Pronta, mai ordinata (~120–130 $) |
| v0.4 economica | 2026-11-02 | 22,86 × 26 mm, 2 strati | Solo registrazione IMU, budget ≤ 100 €: tolti pressione, MAX17048, TPS22916C, vibratore, Tag-Connect, TVS; flash 16 MB | Ricompattata |
| v0.4 ricompattata | 2026-11-03 | **21,59 × 26 mm**, 2 strati | LED 0603 *basic* con anodo su VDD, pinout cambiato, DRC 0, file JLC rigenerati | Verificata (65 test, 0 bloccanti) |
| v0.5 economica | 2026-11-04 | **21,59 × 28,0 mm**, 2 strati | TPS22916C su VDD_IMU, TVS, AO3401A contro l'inversione della cella, 100 kΩ VIN-GND, TP8, IMU_MISO/CS su P0.08/P0.12; DRC 0, ERC 0 | **Pronta** (commit 01c6b8b), non ordinata |

### v0.5 in dettaglio

La v0.5 nasce dalla v0.4 con le modifiche decise dopo le [revisioni esterne](#revisioni-esterne-v04). Si legge prima il blocco "Revisione v0.5" di [`hardware/nrf52840/progetto.md`](hardware/nrf52840/progetto.md). La v0.4 resta **storica**: file congelati in `kicad/jlc/v0.4_swimtag_economica/`, rigenerabile dal commit `8fd6cc0`.

**Misure.** **21,59 × 28,0 mm**, 2 strati, 0,8 mm, 25 componenti montati per scheda, 369 piste, 36 via. A 26–27,5 mm lo sbroglio a 2 strati non chiude (BGA 0,4 mm del BQ25101 e MISO dell'IMU). Tag finito circa 25 × 31 mm con la resina.

**Novità rispetto alla v0.4:**

| Rif. | Modifica | LCSC | Tipo JLC |
|---|---|---|---|
| U6 | TPS22916C: VDD → VDD_IMU per l'IMU, ON su P0.04 (`SENS_ON`) con R7 1 MΩ; R6 (pull-up CS) su VDD_IMU | C2680319 | extended |
| C5 | 4,7 µF 10 V all'ingresso del BQ25101 (era 10 µF 6,3 V) | C23733 | basic |
| C6, C7 | C6 4,7 µF 10 V su VBAT, C7 tolto | C23733 | basic |
| R8 | 100 kΩ tra VIN e GND: niente elettrolisi tra i contatti in acqua | C25741 | basic |
| D3 | TVS bidirezionale PTVSLC3D5VB sul contatto VIN, prima di D2 | C41408025 | extended |
| Q1, R9 | AO3401A contro l'inversione della cella, gate a GND con 100 kΩ | C15127 | basic |
| TP8 | Piazzola `VDD_IMU`, Ø 0,8 mm, sotto, a (17,78; 12,70) mm | solo rame | |

Altre modifiche: IMU_MISO su P0.08 (pad 16) e IMU_CS su P0.12 (pad 20), così XL1/XL2 restano liberi; serigrafia da 1,0 mm; zona senza piste su F.Cu al centro sotto il modulo. Le piazzole TP1–TP7 hanno le stesse coordinate della v0.4: il programmatore HAT resta valido. Da provare a banco: Q1 con cella dritta e invertita.

**Verifiche.** DRC 0 errori e 0 avvisi, 0 non collegati, parità schema/PCB 0, ERC 0 errori (41 avvisi `pin_to_pin` innocui dei simboli generati), 28 reti, `kicad/verifica_v05.py`: 100 pin attesi su 100, 0 differenze.

**Pinout v0.5 che cambia** (il resto è come nella tabella della v0.4 sotto):

| Pad E73 | GPIO | Rete |
|---|---|---|
| 16 | P0.08 | IMU_MISO |
| 20 | P0.12 | IMU_CS (R6 100 kΩ su VDD_IMU) |
| 18 | P0.04 | SENS_ON (R7 1 MΩ a GND) |

P0.00/P0.01 (XL1/XL2) sono liberi; LFCLK resta dall'RC.

#### Costi v0.5
Stima dal carrello JLC reale del 2026-11-03 (v0.4, 128,46 €), ricalcolata e non rifatta nel carrello. Montaggio Standard PCBA obbligatorio (E73, IMU, BQ25101). **Circa 125 € con raggi X e coupon, sopra il tetto di 100 €** (ENIG: +5–10 €).

| Taglio (cumulativo) | Totale stimato |
|---|---|
| Nessuno (v0.5 completa, raggi X, coupon) | ~125 € |
| Senza raggi X (rischio sui BGA/LGA non verificati) | ~109 € |
| + senza TVS D3 | ~105 € |
| + senza header J1 (fili sulle piazzole) | ~100,5 € |

Sono tutte rinunce a protezioni o controlli: decide l'utente. Cella, programmatore e pogo sono esclusi.

**Da controllare nell'anteprima JLC:** rotazioni di U6, Q1, D1, D3, J1 (e U2, U4, D2); il TPS22916C è probabilmente "Standard only".

### v0.4 in dettaglio (storica)

**Scopo.** Due prototipi per registrare i dati grezzi dell'IMU e mettere a punto i filtri, spesi il meno possibile. Dati in `kicad/dati_economica.py`, posizioni in `kicad/posizioni_economica.py`, disegno quotato in [`hardware/nrf52840/ingombro_v0.4.svg`](hardware/nrf52840/ingombro_v0.4.svg).

**Misure.** Scheda **21,59 × 26,0 mm** (8,5 passi da 2,54 mm), **2 strati**, 0,8 mm, componenti solo sopra, 313 piste, 29 via. Tag finito circa 25 × 29 mm con 1,5 mm di resina. A 20,32 mm lo sbroglio a 2 strati non chiude (circa 100 prove con Freerouting, mai DRC 0).

**Componenti (codici LCSC):**

| Funzione | Componente | LCSC | Tipo JLC |
|---|---|---|---|
| Microcontrollore e BLE | Ebyte E73-2G4M08S1C (nRF52840), VDDH dalla cella, REGOUT0 a 3,3 V da UICR | C356849 | extended |
| IMU 6 assi | ST LSM6DSV16X, SPI con INT1/INT2 | C5267406 | extended |
| Flash 16 MB | Winbond W25Q128JVSIQ, SOIC-8, SPI semplice | C97521 | basic |
| Caricatore | TI BQ25101 (TS 10 kΩ a massa, ISET 10 kΩ = 13,5 mA) | C478468 | extended |
| LED | KT-0603R rosso, anodo su VDD | C2286 | basic |
| Protezione ricarica | Schottky 1N5819WS in serie ai contatti | C191023 | basic |
| Cella | Header SMD 1,27 mm 1 × 2 (fili saldati alla cella) | C55213900 | extended |
| Passivi | 6 resistenze, 7 condensatori | vedi `bom_jlc.csv` | basic |

Distinta completa e rotazioni: `hardware/nrf52840/kicad/jlc/v0.4_swimtag_economica/` (`bom_jlc.csv`, `cpl_jlc.csv`). Altre alternative valutate (flash WSON, JST SH, NTC): [`hardware/nrf52840/progetto.md`](hardware/nrf52840/progetto.md).

**Lato sotto, griglia 2,54 mm** (millefori e pogo):

| Piazzola | Rete | x (mm) | y (mm) | Ø |
|---|---|---|---|---|
| TP1 | VDD (solo riferimento) | 5,08 | 12,70 | 2,0 |
| TP2 | SWDIO | 7,62 | 12,70 | 2,0 |
| TP3 | SWDCLK | 10,16 | 12,70 | 2,0 |
| TP4 | RESET | 12,70 | 12,70 | 2,0 |
| TP5 | GND | 15,24 | 12,70 | 2,0 |
| TP6 | VIN (ricarica) | 7,62 | 17,78 | 2,5 |
| TP7 | GND (ricarica) | 12,70 | 17,78 | 2,5 |

Coordinate dall'angolo in alto a sinistra (lato antenna), scheda vista da sopra. Tacche di serigrafia ogni 2,54 mm sui bordi sinistro e alto.

**Pinout per il firmware** (tutti i segnali a 3,3 V dopo REGOUT0). Tabella completa in [`hardware/nrf52840/verifica_v0.4.md`](hardware/nrf52840/verifica_v0.4.md), sezione 3.

| Pad E73 | GPIO | Rete | Note |
|---|---|---|---|
| 11 | P0.00 | IMU_CS | R6 100 kΩ a VDD; pin XL1: **LFCLK non da XTAL** |
| 13 | P0.01 | IMU_MISO | pin XL2 |
| 15 | P0.05 | IMU_MOSI | |
| 17 | P1.09 | IMU_SCK | SPI fino a 8 MHz |
| 12 | P0.26 | IMU_INT1 | |
| 14 | P0.06 | IMU_INT2 | |
| 30 | P0.17 | FL_CS | R5 100 kΩ a VDD |
| 28 | P0.15 | FL_MISO | |
| 33 | P0.13 | FL_MOSI | |
| 35 | P0.24 | FL_SCK | /WP e /HOLD alti: solo SPI semplice |
| 32 | P0.20 | CHG_N | pull-up interno; basso = in carica |
| 34 | P0.22 | LED | acceso a livello basso, circa 1,4 mA |
| 26 | P0.18 | RESET | dopo la scrittura di `UICR.PSELRESET` |
| 37 / 39 | SWDIO / SWDCLK | SWD | pogo TP2 / TP3 |
| 23 | VDDH | VBAT | batteria con canale SAADC `VDDHDIV5`, nessun partitore |

Pinout della v0.4: nella v0.5 cambiano IMU_CS e IMU_MISO e si aggiunge SENS_ON (vedi sopra). Registri UICR da scrivere una volta via SWD: `REGOUT0` (0x10001304) = `0xFFFFFFFD` (3,3 V), `PSELRESET[0]` e `[1]` (0x10001200 / 0x10001204) = `0x12`.

**Scelte principali.**
- **Flash 16 MB** SOIC-8 *basic*: 4,93 $ per 2 schede contro 9,83 $ del WSON. Durata: circa 24 minuti a 960 Hz (sei assi, 16 bit), circa 97 minuti a 240 Hz, circa 3 ore a 120 Hz.
- **LED 0603 *basic*** con anodo su VDD: toglie 3,07 $ di caricamento extended e non inietta corrente nel pin al primo avvio (VDD a 1,8 V con UICR vuoto).
- **Header SMD 1,27 mm** al posto del JST SH: 10,4 contro 26,6 mm², costa meno.
- **2 strati, HASL senza piombo**: lo sbroglio chiude senza toccare la zona antenna (3,7 mm senza rame).
- **Tolti:** pressione (manca la profondità; avvisare l'agente app se serve), MAX17048, vibratore, Tag-Connect, TVS, reset all'inserimento.

**Costi reali dal carrello JLC della v0.4** (2026-11-03, scheda 22,86 × 26 mm, prima del LED *basic* e del TPS22916C). E73, IMU (LGA) e BQ25101 (BGA) sono montabili **solo in Standard PCBA**, non nell'Economic:

| Voce | € |
|---|---|
| 5 PCB 2 strati HASL (offerta) | 1,79 |
| Setup Standard | 23,02 |
| Stencil | 7,39 |
| Componenti per 2 schede | 26,95 |
| Caricamento extended (5 tipi) | 16,63 |
| Montaggio SMT | 0,66 |
| Raggi X | 8,85 |
| Imballo | 0,45 |
| Spedizione | 9,62 |
| IVA, dazio temporaneo e diritti di gestione Ue | 31,32 |
| **Totale** | **128,46** |

Riduzioni: coupon *PCBA Special Offer* (−8,05 €, scade il 2026-11-29) e *JLCONE PCB* (fino a −1,79 €), LED *basic* già fatto (circa −4 € con IVA). Il TPS22916C aggiunge un caricamento extended (circa +4,5 € con IVA). Per la v0.5 vedi [Costi v0.5](#costi-v05).

### Verifica indipendente (v0.4)

Documento: [`hardware/nrf52840/verifica_v0.4.md`](hardware/nrf52840/verifica_v0.4.md). Eseguita il 2026-11-03 da un agente revisore sul commit `8fd6cc0`, con `kicad-cli` 10.0.6 e lo script `kicad/verifica_v04.py` (tabella attesa scritta a mano dai fogli tecnici).

**Esito: 65 test, 0 difetti bloccanti.** Netlist 85 pin attesi, 0 differenze; PCB e schema coincidono; piedinature e impronte coerenti con i fogli tecnici.

Punti ⚠️ principali:
- **Finitura HASL o ENIG.** HASL con il BGA del BQ25101 a 0,4 mm è sconsigliata da JLC; la verifica raccomanda ENIG (costa di più). È una scelta dell'utente da fare all'ordine.
- **LGA dell'IMU (U2):** orientamento da confermare nell'anteprima JLC e quote dei pad da confrontare col disegno meccanico del DS13510 (non raggiunto).
- **Polarità di LED (D1), Schottky (D2) e header (J1)** e rotazioni di E73, IMU, BQ25101: da confermare nell'anteprima JLC. L'header è simmetrico: nessuna protezione contro l'inversione della cella (marcare i fili).
- **Margine di tensione:** VDD segue VDDH − 0,3 V sotto 3,6 V e la flash vuole almeno 2,7 V: taglio batteria nel firmware a 3,2–3,3 V.
- **Corrente esterna da VDD:** 5 mA con radio sopra +4 dBm: non scrivere in flash mentre il BLE trasmette a potenza alta.
- **Caricatore:** C5 con tensione ≥ 10 V, valutare di togliere C6 o C7; con ingresso 5,0 V e Schottky il margine su VIN-DPM è stretto; il carico durante la carica impedisce la terminazione (timer 10 h).
- **Antenna:** il foglio Ebyte non quota la zona libera; la prova di portata prima della resina è obbligatoria.
- **Firmware:** niente DC/DC, LFCLK dall'RC (P0.00/P0.01 sono usati come GPIO), niente eventi USB.
- **TPS22916C:** applicato nella v0.5. Firmware: SPI, CS e INT a livello basso prima di togliere l'alimentazione e attesa di 5–10 ms alla riaccensione. La verifica della v0.5 è `kicad/verifica_v05.py` (100/100 pin).

### Documenti collegati
- [`hardware/nrf52840/bom.md`](hardware/nrf52840/bom.md): distinta con codici LCSC e alternative.
- [`hardware/nrf52840/verifiche.md`](hardware/nrf52840/verifiche.md): controlli sui fogli tecnici (v0.2/v0.3).
- [`hardware/nrf52840/SwimTag_v0.3_collaudo.pdf`](hardware/nrf52840/SwimTag_v0.3_collaudo.pdf): PDF storico della v0.3.
- Render v0.5: `hardware/nrf52840/kicad/jlc/v0.5_swimtag_economica/render_sopra.png`, `render_sotto.png`, `render_3d.png` (v0.4 in `v0.4_swimtag_economica/`).
- [`hardware/nrf52840/revisioni_esterne.md`](hardware/nrf52840/revisioni_esterne.md): esito delle revisioni di Gemini e Copilot.

## Revisioni esterne (v0.4)

Il documento di progetto della v0.4 è stato dato a due revisori esterni il 2026-11-04. Esiti e azioni: [`hardware/nrf52840/revisioni_esterne.md`](hardware/nrf52840/revisioni_esterne.md). Il testo inviato: [`hardware/nrf52840/revisione_esterna_v0.4.md`](hardware/nrf52840/revisione_esterna_v0.4.md). Le modifiche decise sono nella v0.5.

- **Gemini (3 giri):** modifiche al PCB: 100 kΩ VIN-GND, IMU_CS e IMU_MISO fuori da XL1/XL2, finitura ENIG (opzione d'ordine). Confermati corretti E73, IMU in SPI, flash, BGA del BQ25101, TPS22916C. Requisiti per il firmware: soglia di sottotensione, System OFF in carica, IMU con segnali bassi prima dello spegnimento, radio entro +4 dBm con flash, UICR al primo avvio.
- **Copilot (sign-off, "non firmerei ancora"):** S1 (TS con 10 kΩ a massa come errore bloccante) è un **falso positivo**: il foglio TI (SLUSBV8C p. 3) prescrive proprio 10 kΩ verso VSS se l'NTC non serve; 50 µA × 10 kΩ = 0,5 V. Fondati: punto di misura VDD_IMU (TP8), ticket DFM a JLC per i due package a 0,4 mm, essiccazione della scheda **senza la cella** prima della resina.
- **Applicato nella v0.5:** TPS22916C, TVS D3, Q1 contro l'inversione della cella, R8, TP8, nuovi GPIO. **Resta da fare:** ENIG, ticket DFM, firmware (sottotensione, carica, sequenze dell'IMU), prova di portata, traslatore di livello sullo SWD.

## Programmatore HAT per Raspberry Pi 3/4

Basetta a una faccia, da costruire a mano con il **toner transfer**, con forma e fori di un HAT del Raspberry Pi (65 × 56,5 mm). Si innesta sul connettore a 40 pin del Pi 3 o 4. Sette molle **pogo** cadono sulle piazzole sotto il tag: 5 di debug SWD e 2 di ricarica. Il Pi programma con **OpenOCD** in bit-bang sui GPIO e può ricaricare la cella mentre il tag è collegato.

![Programmatore, render](hardware/programmatore/img/render_top.png)

- **Collegamenti sul connettore:** pin 2 (5 V, solo ricarica, via PTC e ponticello), 12 (RESET, GPIO18), 18 (SWDIO, GPIO24), 20 (GND), 22 (SWCLK, GPIO25). Resistenze in serie da 1 kΩ su SWD e RESET.
- **Regola fondamentale:** mai il 3,3 V del Pi sul VDD del tag. Il tag si alimenta dalla cella; al primo avvio il suo VDD è 1,8 V finché non si scrive `UICR.REGOUT0`.
- **Ricarica:** pogo VIN e GND caricano la cella 401012 tramite il BQ25101 (13,5 mA, circa 3–3,5 ore da vuota). Ponticello JP1: nessuno = ricarica spenta (predefinito), 1-2 = 5 V del Pi, 2-3 = 5 V esterno.
- **Centraggio:** tre pin di battuta sui bordi con le tacche del tag, errore stimato circa ±0,3 mm.
- **OpenOCD:** file `swimtag_pi.cfg` (driver `bcm2835gpio`, base periferiche 0x3F000000 per Pi 3 e 0xFE000000 per Pi 4). Pi 5 non supportato.
- **DRC 0, ERC 0** con `kicad-cli` 10.0.6.
- **Non provato fisicamente:** la basetta non è stata costruita. Rischi noti: livelli a 1,8 V sul tag (le 1 kΩ non sono una traduzione di livello), foro dei pogo da verificare sul pezzo, posizione del connettore da verificare su un Pi reale.

**Documentazione:**
- [`hardware/programmatore/Programmatore_SwimTag_v0.5.pdf`](hardware/programmatore/Programmatore_SwimTag_v0.5.pdf): schema, distinta, procedura, OpenOCD. Le stampe 1:1 sono alle pagine 6 (rame speculare), 7 (componenti), 8 (ingrandimento 2:1) e 9 (mappa fori).
- [`hardware/programmatore/README.md`](hardware/programmatore/README.md): dettagli, piedinatura, procedura e limiti.
- [`hardware/programmatore/bom.md`](hardware/programmatore/bom.md): distinta con prezzi.
- [`hardware/programmatore/stampa/`](hardware/programmatore/stampa/): fogli di stampa 1:1.

## Galleria degli sfondi tecnici

Venti tavole da disegno 1170 × 2532 px, generate dai PCB reali (blueprint, OLED, carta tecnica, rame su verde). Generati sulla **v0.5**. Fotografie intere in [`hardware/wallpaper_v0.5/png/`](hardware/wallpaper_v0.5/png/) (file `NN_nome_1170x2532.png`, stessi nomi della v0.4).

| &nbsp; | &nbsp; | &nbsp; | &nbsp; |
|---|---|---|---|
| <img src="hardware/wallpaper_v0.5/png/01_tag_pianta_1170x2532.png" width="180"><br>**01** Pianta del tag | <img src="hardware/wallpaper_v0.5/png/02_tag_esploso_1170x2532.png" width="180"><br>**02** Esploso | <img src="hardware/wallpaper_v0.5/png/03_tag_sezione_1170x2532.png" width="180"><br>**03** Sezione | <img src="hardware/wallpaper_v0.5/png/04_tag_dettagli_1170x2532.png" width="180"><br>**04** Dettagli |
| <img src="hardware/wallpaper_v0.5/png/05_e73_antenna_1170x2532.png" width="180"><br>**05** E73 e antenna | <img src="hardware/wallpaper_v0.5/png/06_e73_piedinatura_1170x2532.png" width="180"><br>**06** E73, piedinatura | <img src="hardware/wallpaper_v0.5/png/07_rame_superiore_1170x2532.png" width="180"><br>**07** Rame superiore | <img src="hardware/wallpaper_v0.5/png/08_rame_inferiore_1170x2532.png" width="180"><br>**08** Rame inferiore |
| <img src="hardware/wallpaper_v0.5/png/09_maschera_serigrafia_1170x2532.png" width="180"><br>**09** Maschera e serigrafia | <img src="hardware/wallpaper_v0.5/png/10_quattro_strati_1170x2532.png" width="180"><br>**10** Strati (vista a pila) | <img src="hardware/wallpaper_v0.5/png/11_mappa_fori_1170x2532.png" width="180"><br>**11** Mappa dei fori | <img src="hardware/wallpaper_v0.5/png/12_zona_carica_1170x2532.png" width="180"><br>**12** Zona di carica |
| <img src="hardware/wallpaper_v0.5/png/13_quote_posizione_1170x2532.png" width="180"><br>**13** Quote e posizioni | <img src="hardware/wallpaper_v0.5/png/14_piazzole_servizio_1170x2532.png" width="180"><br>**14** Piazzole di servizio | <img src="hardware/wallpaper_v0.5/png/15_tre_viste_1170x2532.png" width="180"><br>**15** Tre viste | <img src="hardware/wallpaper_v0.5/png/16_isometrica_distinta_1170x2532.png" width="180"><br>**16** Isometrica con distinta |
| <img src="hardware/wallpaper_v0.5/png/17_programmatore_pianta_1170x2532.png" width="180"><br>**17** Programmatore, pianta | <img src="hardware/wallpaper_v0.5/png/18_programmatore_pogo_1170x2532.png" width="180"><br>**18** Programmatore, pogo | <img src="hardware/wallpaper_v0.5/png/19_programmatore_hat_1170x2532.png" width="180"><br>**19** Programmatore, HAT | <img src="hardware/wallpaper_v0.5/png/20_programmatore_toner_1170x2532.png" width="180"><br>**20** Programmatore, toner transfer |

**Come rigenerarli.** `python hardware/wallpaper_v0.5/genera.py` (richiede `kicad-cli` e PyMuPDF). Opzioni: `--solo 1 3 12`, `--bozza`, `--forza` per rifare anche i render 3D. Gli sfondi della v0.4 restano in [`hardware/wallpaper_v0.4/png/`](hardware/wallpaper_v0.4/png/) (storici). Gli sfondi della v0.3, vecchi e solo storici, sono in [`hardware/nrf52840/wallpaper/png/`](hardware/nrf52840/wallpaper/png/).

## Struttura delle cartelle

```
SwimTimer/
├── docs/                         idea, stato, decisioni, domande aperte, requisiti, design, lezioni, algoritmi
├── firmware/
│   ├── test-collegamenti/        tag ESP32-S3: firmware 0.4.3
│   └── display-prova/            display T-RGB
├── tools/                        index.html (pagina di analisi), assi.html (vecchia)
├── hardware/
│   ├── bom.md, schema.md         prototipo ESP32
│   ├── nrf52840/                 scheda su misura: progetto.md, bom.md, verifiche.md, verifica_v0.4.md,
│   │   │                         revisioni_esterne.md, revisione_esterna_v0.4.md, ingombro*.svg, PDF e wallpaper della v0.3
│   │   └── kicad/                script, progetti KiCad (swimtag, _collaudo, _economica), jlc/ (v0.3, v0.4, v0.5; verifica_v04.py, verifica_v05.py)
│   ├── programmatore/            HAT per Raspberry Pi: KiCad, PDF, stampe 1:1, script
│   ├── wallpaper_v0.5/           genera.py, estrai_dati.py, render/, png/ (20 sfondi, v0.5)
│   └── wallpaper_v0.4/           sfondi della v0.4 (storici)
├── CHANGELOG.md                  modifiche per data
├── CLAUDE.md                     regole di lavoro del progetto
└── README.md                     questo file
```

## Come rigenerare i file

| Cosa | Comando | Note |
|---|---|---|
| Schema e PCB (v0.5) | `SWIMTAG_VARIANTE=economica python hardware/nrf52840/kicad/genera_schema.py` e `genera_pcb.py` | dati in `dati_economica.py`, posizioni in `posizioni_economica.py` |
| Sbroglio | `sbroglia.py` | Freerouting 2.5.0, Java 25; non deterministico: ripetere finché il DRC è 0 |
| Controllo netlist | `verifica_netlist.py` | confronta la netlist con i dati |
| Verifica indipendente | `python hardware/nrf52840/kicad/verifica_v05.py <pcb> <net.xml> [cpl.csv bom.csv]` | tabella ATTESA scritta a mano dai fogli tecnici (`verifica_v04.py` per la v0.4) |
| File JLC | `SWIMTAG_VARIANTE=economica python hardware/nrf52840/kicad/esporta_jlc.py` | scrive in `jlc/v0.5_swimtag_economica/` |
| Programmatore | `cd hardware/programmatore; python genera_kicad.py --drc` poi `python genera_pdf.py` | rilegge TP1–TP7 dal PCB del tag; PDF richiede PyMuPDF e `kicad-cli` |
| Sfondi | `python hardware/wallpaper_v0.5/genera.py` | vedi galleria |

La v0.4 si rigenera dal commit `8fd6cc0`; la v0.3 si rigenera con `SWIMTAG_VARIANTE=collaudo` (predefinita).

## Flusso d'ordine JLCPCB

La scheda v0.5 è verificata (DRC/ERC, `verifica_v05.py`). **Non ordinare** prima di: decisione sul costo (~125 € contro il tetto di 100 €), anteprima JLC, scelta HASL/ENIG, ticket DFM.

1. Rigenerare i file JLC e controllare `bom_jlc.csv` e `cpl_jlc.csv`.
2. Caricare lo zip dei Gerber (`swimtag_gerber.zip`) nell'ordine PCB: 2 strati, 0,8 mm, **HASL senza piombo oppure ENIG** (scelta dell'utente, vedi verifica).
3. Servizio di montaggio **Standard PCBA** (obbligatorio: E73, IMU e BQ25101 sono "Standard only"), lato sopra, **PCBA Qty = 2**; se chiesto, bordi di lavorazione "Added by JLCPCB".
4. Caricare BOM e CPL e controllare nell'anteprima rotazioni e pin 1 di E73, IMU (LGA), BQ25101 (BGA), TPS22916C (U6, probabilmente "Standard only"), Q1 (SOT-23), flash (U3 a 270°), LED (D1), Schottky (D2), TVS (D3) e header (J1); stock dell'E73.
5. Applicare i **coupon** dal Coupon Center: *PCBA Special Offer* (8,05 €) e *JLCONE PCB* (ordine dall'app JLCONE).
6. Attivare **Confirm Parts Placement** (0,45 €) per approvare il posizionamento prima della produzione.
7. Aggiungere i raggi **X-ray** per E73, IMU, BQ25101 e gli altri componenti con pad nascosti (circa +10 $).
8. Aprire un ticket DFM a JLC per i due package a 0,4 mm (BQ25101 e TPS22916C).
9. Verificare il totale (obiettivo ≤ 100 € con IVA, vedi tagli in [Costi v0.5](#costi-v05)), poi pagare. Cella, pogo e programmatore sono esclusi.

## Roadmap e problemi aperti

**Scheda nRF52840**
1. Decidere il costo: ~125 € contro il tetto di 100 € (tagli: raggi X, TVS, header).
2. Anteprima JLC (rotazioni di U6, Q1, D1, D3, J1), scelta HASL/ENIG, ticket DFM, ordine di 2 schede.
3. Prova a banco di Q1 con cella dritta e invertita; prima accensione da alimentatore limitato a circa 50 mA.
4. Costruire il programmatore, scrivere UICR, prova di portata dell'antenna prima della resina (antenna a 0,3 mm dal bordo, scheda da 28 mm).
5. Firmware su Zephyr / nRF Connect SDK (SPI, flash, registrazione, MCUboot, sonno con INT dell'IMU), poi prova in vasca.
6. Variante definitiva: vibratore, pressione, custodia di ricarica a più posti.

**Prototipo ESP32**
- A sola batteria il tag non fa il lampo blu e non si vede in Bluetooth (LED rosso acceso, 3,87 V ai pad).
- Latch-up del BMI160 dopo spegnimenti bruschi: si usa l'interruttore generale.
- Display a batteria che non si accende senza USB.
- Tap software poco affidabile; lettura dalla FIFO del BMI160 (circa 44 Hz reali).
- Sessioni registrate con video, messa a punto degli algoritmi, prova in vasca.

**Rischi generali**
- Brevetti nel settore (FORM US 11833392): verifica di libertà di operare prima di un uso commerciale.
- Il BLE non attraversa l'acqua; custodia stagna e resina da definire.
- Nessun test automatico.
- `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` possono confliggere con il repository pubblico: unire a mano.

Dettagli: [`docs/STATO.md`](docs/STATO.md). Decisioni: [`docs/DECISIONI.md`](docs/DECISIONI.md). Modifiche: [`CHANGELOG.md`](CHANGELOG.md).

## Privacy e sicurezza

- Nessuna credenziale nel repository: se servono, solo in `.env` (escluso da git) e come secrets in CI.
- Nessun dato personale reale: le sessioni di nuoto sono dati di salute e restano in locale (`dati/`, esclusa da git). Nei test solo dati inventati.
- Dal 2026-11-04 tutto il progetto, hardware compreso, è in questo unico repository pubblico; il vecchio repository privato `PZero/SwimTimer-nrf52840` è dismesso.
- Eventuale app: Firebase piano gratuito Spark, senza Cloud Functions.

## Licenza e autore

Licenza del progetto: da definire (nessun file `LICENSE`). Il driver in `firmware/display-prova/src/trgb/` è sotto licenza MIT (Copyright 2024 Xinyuan-LilyGO), con il proprio file `LICENSE`.

Autore: PZero (GitHub `PZero`).
