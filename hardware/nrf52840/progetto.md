# Tag su misura nRF52840 — progetto (proposta)

**Stato:** studio del 2026-10-25, nessun acquisto, nessuno schema. Componenti in `bom.md`. Prototipo attuale (ESP32-S3 SuperMini + BMI160) in `../bom.md` e `../schema.md`.

**Obiettivo:** tag da portare sotto la cuffia, ~18 × 26 × 9 mm resinato, con sensore di profondità e vibratore, LiPo ~20 mAh, ricarica a contatto in una custodia tipo AirPods, prodotto e montato da JLCPCB.

## Schema a blocchi

```
 custodia (5 V, molle pogo + magneti)
   │ VIN   GND
   ▼
 [TVS] → [Schottky] ──┬──► BQ25100 (15 mA, 4,2 V) ──► LiPo 20 mAh (con PCM)
                      │        │ /CHG → GPIO               │ BAT
                      └─ 1M/1M → GPIO "in custodia"         ▼
                                                    VDDH  nRF52840 (MDBT50Q)
                                                          REG0 LDO → VDD 3,0 V (UICR.REGOUT0)
                                                          REG1 DC/DC → core
                                                          SAADC: VDDHDIV5 = misura batteria
                         VDD 3,0 V ─┬─ LSM6DSV16X  (SPI, INT1/INT2: dati pronti, risveglio)
                                    ├─ W25Q256JV   (QSPI, 32 MB)
                                    ├─ MS5837-02BA (I2C, profondità)
                                    └─ LED RGB 1010 (GPIO in assorbimento)
                         VDDH ──[2×47 µF]── vibratore Ø 6 mm ── N-MOSFET ← GPIO (PWM)
                         SWD: piazzole interne per il primo avvio (sotto la resina)
```

Note di progetto:
- **VDDH direttamente dalla LiPo** (modo "alta tensione" dell'nRF52840): niente regolatore esterno. ⚠ In questo modo VDD esce a **1,8 V di serie**: il firmware (o il primo flash) deve scrivere `UICR.REGOUT0 = 3,0 V`, altrimenti la flash a 3 V non parte. VDD a 3,0 V permette di usare la batteria fino a ~3,3 V.
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

Anche Zephyr ha già i driver: `st,lsm6dsv16x`, `invensense,icm45686`, `meas,ms5837`, `nordic,qspi-nor`. La scheda **Seeed XIAO nRF52840 Sense** è già supportata (`xiao_ble/nrf52840/sense`) e ha un caricatore della stessa famiglia (BQ25101).

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

Con l'ICM-45686 il nuoto scende a ~1,1 mA (~14 h). Ricarica a 15 mA: **~1,5–2 h** da vuota. Questi numeri vanno **misurati** sulla XIAO (Nordic PPK2 o un multimetro con shunt) prima di fissare la cella.

## Ingombro stimato

| Parte | Misure |
|---|---|
| Scheda (4 strati, 0,8 mm, componenti su un lato) | ~14 × 22 mm; con componenti su due lati ~13 × 18 mm (montaggio JLC più caro) |
| Altezza componenti | 2,05 mm (modulo); 2,75 mm il sensore di pressione; vibratore Ø 6 × 2–2,7 mm accanto alla cella |
| Cella 20 mAh | ~4 × 10 × 12 mm o ~3 × 10 × 15 mm |
| **Tag finito** (scheda + cella e vibratore sovrapposti + ~1 mm di resina per lato) | **~18 × 26 × 9 mm, ~6 g** |

Confronto: il prototipo attuale (SuperMini 18 × 22 mm + modulo BMI160 + LiPo da 300–500 mAh) è parecchie volte più grande.

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
| **Carica a corrente bassa** (15 mA) | bassa/media | BQ25100 è fatto apposta (da 10 mA); attenzione al **timer di sicurezza fisso di 10 h** e alla soglia di terminazione (PRETERM); niente caricatori tipo TP4056 (minimo pratico ~50 mA) |
| **Picchi di corrente** su cella da 20 mAh (max 1–2 C = 20–40 mA), soprattutto il **vibratore** (50–80 mA) | alta | vibratore in PWM ~50 % a impulsi brevi, 2 × 47 µF su VDDH, niente radio/flash durante l'impulso, cella ≥ 2 C; soglia di spegnimento del vibratore sotto ~3,6 V; provarlo sulla XIAO prima del PCB |
| **Disponibilità componenti** (modulo e IMU *extended*, stock variabile) | media | verificare stock il giorno dell'ordine; riserva E73 per il modulo e ICM-45686 per l'IMU già nel progetto |
| **Primo flash e recupero**: dopo la resina l'SWD non è più raggiungibile | alta | programmare e collaudare (radio, IMU, flash, carica) **prima** della colata; da lì solo aggiornamenti via BLE con MCUboot: bootloader non aggiornabile, immagine nuova provata e confermata solo se il BLE funziona (altrimenti torna alla precedente), immagine di riserva nella flash esterna; programmatore J-Link EDU Mini o Raspberry Pi Pico come *debugprobe* con pinza pogo |
| **Porting del firmware** da Arduino/ESP32 a Zephyr | media | passo intermedio con la XIAO (sotto); algoritmi già indipendenti dall'hardware |
| **Sensore di pressione** con porta esposta | media | O-ring, prova di tenuta in vasca prima di resinare le altre schede |

## Piano a tappe

**(a) Passo intermedio — Seeed XIAO nRF52840 Sense (~15 $)**
nRF52840 + LSM6DS3TR-C + 2 MB QSPI + caricatore BQ25101, 21 × 17,5 mm, già supportata da Zephyr.
- Ambiente nRF Connect SDK (VS Code + estensione nRF Connect), progetto `firmware/tag-nrf/` con overlay per la XIAO.
- Portare: lettura IMU con FIFO, servizio GATT compatibile con la pagina `tools/`, annuncio BLE per il display, registrazione su flash, sonno con risveglio dall'IMU, misura della batteria.
- MCUboot + aggiornamento via BLE (SMP): da aggiungere alla pagina web (esistono librerie JavaScript per mcumgr su Web Bluetooth).
- **Misurare i consumi reali** e confermare frequenza e fondo scala dall'analisi delle registrazioni.
- Provare sulla XIAO anche un modulo MS5837 su I2C (profondità) e un vibratore con MOSFET alimentato da una cella da 20 mAh, misurando la caduta di tensione.

**(b) Schema e PCB (KiCad)** — solo dopo (a) e conferma dell'utente
- Schema e layout 4 strati, regole e librerie JLC; simbolo/impronta MDBT50Q dal foglio Raytac.
- Overlay Zephyr della scheda definitiva (stesso firmware della XIAO, solo i pin cambiano).
- Revisione dello schema prima dell'ordine (consumi a riposo, piazzole SWD, zona antenna).

**(c) Ordine prototipi** — 5 pezzi montati da JLC (~150–250 $ con spedizione e IVA)
- **Pannello**: più tag sulla stessa scheda (proposta 2 × 3 = 6 tag, ~70 × 80 mm con i bordi), staccati con **mouse bites** (fori di rottura su linguette da 2–3 mm, dove non c'è la zona dell'antenna); il V-cut no, perché taglia da bordo a bordo e su schede così piccole è poco preciso. Bordi di servizio da 5 mm con fiducial e fori di riferimento (servono comunque a JLC per montare schede sotto i 20 mm). Pannello generato con **KiKit** (plugin di KiCad). Prezzo: JLC fa pagare il pannello per le sue misure (fascia fino a 100 × 100 mm) e lo stesso progetto ripetuto è ammesso; più progetti *diversi* sullo stesso pannello pagano un supplemento.
- Il risparmio vale per PCB e spese fisse, **non per i componenti**, che restano a tag. Proposta: 5 pannelli prodotti, **2 montati** = 12 tag (~12 × 25 $ di componenti + spese fisse), i 3 pannelli nudi di scorta.
- Collaudo a banco: carica a 15 mA, consumi, portata BLE, scrittura flash.
- Resinare 1–2 pezzi, prova in vasca; gli altri restano aperti per le modifiche.

**(d) Custodia di ricarica**
- Stampa 3D, molle pogo dorate, magneti per allineamento e polarità, alimentazione USB-C (eventuale batteria nella custodia in una seconda fase).
- LED di carica sulla custodia (o lettura dello stato dal tag via BLE).

## Decisioni proposte (non ancora prese)

| Proposta | Motivo |
|---|---|
| Flash **32 MB W25Q256JV** (indicata dall'utente il 2026-10-25) | ~11 h a 50 Hz, pari all'autonomia della cella da 20 mAh |
| Modulo **Raytac MDBT50Q-1MV2**; E73 di riserva; ISP1807 per la v2 | certificato, 10,5 × 15,5 mm, montabile da JLC |
| IMU **LSM6DSV16X** a **±4 g**, ICM-45686 di riserva | rumore 3 volte inferiore al BMI160, fondo scala cambiabile via firmware |
| VDDH dalla LiPo, VDD a 3,0 V da UICR, batteria con VDDHDIV5 | meno componenti, zero perdite di partitori |
| Caricatore **BQ25100** a 15 mA | fatto per celle piccole, protetto fino a 28 V sull'ingresso |
| Sensore di pressione **MS5837-02BA** (**deciso dall'utente** il 2026-10-25) | fase subacquea, uscita dall'acqua, BLE spento sott'acqua |
| **Vibratore** Ø 6 mm in PWM (**deciso dall'utente** il 2026-10-25) | avviso tattile in acqua; picchi gestiti con PWM e condensatori |
| Firmware su **Zephyr / nRF Connect SDK** con MCUboot e DFU via BLE | driver pronti, stesso stack di SlimeVR, aggiornamento senza aprire il tag |
| Piazzole SWD interne, sotto la resina (**deciso dall'utente** il 2026-10-25) | si programmano una volta prima della colata; all'esterno solo i contatti di ricarica |
| Tag in **pannello 2 × 3 con mouse bites** (KiKit), 2 pannelli montati su 5 | PCB e spese fisse divise su 12 tag |
| Prima la **XIAO nRF52840 Sense** | porting del firmware e misure dei consumi prima di spendere per il PCB |
