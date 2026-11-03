# Adattatore di programmazione e collaudo (pogo jig, forma di HAT) per il tag SwimTimer v0.4

Basetta a una faccia, a foro passante, da realizzare a mano con il **toner transfer**, con **forma e fori di un HAT del Raspberry Pi** (65 x 56,5 mm, angoli r = 3 mm, 4 fori M2,5 a 58 x 49 mm). Si **innesta direttamente sul connettore a 40 pin** del Pi 3 o 4 (header femmina 2x20 completo, niente cavetti); sulla faccia superiore 7 molle (pogo pin) cadono sulle piazzole sotto il tag: 5 di debug SWD (VDD, SWDIO, SWCLK, RESET, GND) e 2 di ricarica (VIN, GND). Il Pi programma con OpenOCD in bit-bang sui GPIO e puo' anche **ricaricare la cella** del tag mentre e' collegato.

> **MAI il 3,3 V del Raspberry Pi sul VDD del tag.** Il tag si alimenta dalla sua cella; la piazzola VDD (pin J4 dell'adattatore) serve solo al tester e non e' collegata al connettore. Sul connettore sono collegati **solo** i pin 2 (5 V, attraverso PTC e ponticello), 12, 18, 20 (GND) e 22; gli altri 35 restano scollegati. Al primo avvio il VDD del tag e' 1,8 V (UICR vuoto), dopo `UICR.REGOUT0` e un reset 3,3 V.

Documento completo (schema, distinta, stampe 1:1, procedura illustrata, innesto, OpenOCD, problemi): **[`Programmatore_SwimTag_v0.4.pdf`](Programmatore_SwimTag_v0.4.pdf)**. Le **stampe 1:1 sono alle pagine 6 (rame speculare, 8 copie), 7 (posizioni componenti), 8 (ingrandimento 2:1 con tutte le etichette) e 9 (mappa fori)**; gli stessi fogli sono anche in [`stampa/`](stampa/).

## File

| File | Contenuto |
|---|---|
| `modello.py` | geometria: legge `TP1-TP7` e il contorno dal PCB del tag e ricava HAT, pogo, battute, appoggi, piste |
| `genera_kicad.py` | scrive `swimtag_programmatore.kicad_pcb/.kicad_sch/.kicad_pro`; con `--drc` esegue DRC ed ERC con `kicad-cli` |
| `genera_pdf.py`, `pdfbase.py` | PDF unico e fogli di stampa (PyMuPDF) |
| `swimtag_programmatore.*` | progetto KiCad (schema + PCB): piste 0,8 mm, distanze >= 0,5 mm, piazzole >= 2,0 mm, una sola faccia di rame (F.Cu) |
| `stampa/rame_speculare_1a1.pdf`, `stampa/componenti_1a1.pdf` | fogli 1:1 |
| `bom.md` | distinta con prezzi e link |
| `img/` | render KiCad usati nel PDF |

**Risultato di `python genera_kicad.py --drc`: DRC 0 violazioni, 0 pad non collegati, ERC 0** (kicad-cli 10.0.6; il controllo e' sensibile: con distanza 0,6 mm il DRC segnala errori).

## Rigenerare dopo la ricompattazione della scheda

```
cd hardware/programmatore
python genera_kicad.py --drc     # rilegge TP1-TP7 e Edge.Cuts da ../nrf52840/kicad/swimtag_economica.kicad_pcb
python genera_pdf.py             # PDF e fogli di stampa (pip install pymupdf; per i render serve kicad-cli)
# altro file del tag:  SWIMTAG_PCB=percorso/file.kicad_pcb python genera_kicad.py
```

Il tag viene solo traslato nell'HAT (angolo in alto a sinistra a u = 22,5, v = 24,0 mm, costanti `OU`, `OV`): pogo e battute seguono le sue piazzole e i suoi bordi. Fisso nello script: la fila SWD a 2,54 mm e i contatti di ricarica sotto SWDIO e RESET (lo sbroglio dei ponti dipende da questo; lo script avvisa se cambia). Costanti in `modello.py`: `FORO_POGO` (1,5 mm), `LARG_PISTA`, `ALT_BATTUTE` (2,5 mm), `GIOCO_BATTUTA` (0,1 mm). Il PCB del tag e' **solo letto**; dopo la ricompattazione rigenerare e ristampare.

## Forma di HAT e innesto

- Connettore al centro tra i fori, a 3,5 mm dal bordo lungo (specifica HAT ufficiale: **verificare sul proprio Pi** prima di forare: un errore si vede subito perche' i fori M2,5 non coincidono). Pin 1 sul lato della scheda SD, evidenziato da un "1" inciso nel rame; "USB->" inciso verso le porte USB/Ethernet (che l'HAT da 65 mm lascia scoperte).
- **Header femmina 2x20 completo**: montato **da sotto**, saldato **sopra**. Le **code dei pin dispari (fila interna) si tagliano** prima di montarlo (cosi' la fila interna non ha fori e le piste dei 5 pin usati, tutti sulla fila esterna, escono liberamente); le 20 code della fila esterna si saldano (ritenzione) e solo 5 sono collegate.
- Distanziali M2,5 femmina-femmina da **11 mm** (header femmina 8,5 mm + 2,5 mm di plastica del maschio del Pi) ai 4 fori; poggiano sul Pi e non serve fissarli: sostengono anche la pressione quando si preme il tag.
- Sotto l'HAT: solo il connettore (8,5 mm), i corpi degli header maschio (2,5 mm) e le code tagliate.
- **Rame sopra** (come un HAT vero), quindi stampa **speculare** e tutto si salda dal lato in cui si vedono le piste (resistenze, LED e PTC con il corpo sollevato 1-2 mm; header maschio inseriti da sotto con il pin lungo in alto).

### E se fosse innestato ruotato di 180 gradi?
L'HAT sporgerebbe di 49 mm oltre il bordo del Pi e solo due distanziali cadrebbero sui fori. Se lo si forzasse: la presa "pin 2k" finisce sul pin 41-2k del Pi, e i pin pari del Pi (5 V, GND, GPIO) incontrano la fila interna con le code tagliate (nessun contatto). Risultato:

| Presa dell'HAT | Pin del Pi | Effetto |
|---|---|---|
| pin 2 (5 V, verso PTC) | 39 = GND | la linea 5 V va a massa: nessun danno (il tag vede 0 V con JP1 1-2) |
| pin 12 (RESET) | 29 = GPIO5 | GPIO libero |
| pin 18 (SWDIO) | 23 = GPIO11 | GPIO libero |
| pin 20 (GND adattatore) | 21 = GPIO9 | massa del tag/alimentatore esterno su un GPIO in ingresso: nessun corto |
| pin 22 (SWCLK) | 19 = GPIO10 | GPIO libero |
| prese flottanti | 1 e 17 (3,3 V) | cadono su rame isolato |

**Nessun caso pericoloso**: i 3,3 V e i 5 V del Pi non toccano mai una linea collegata del tag, ne' innestato giusto ne' ruotato (il 5 V passa solo dal pin 2 e da JP1, spento di default). Nessuna protezione aggiuntiva necessaria oltre a PTC e alle 1 kohm.

## Pogo e centraggio

- **Pogo P75-E2** (testa a corona) con **ricettacolo R75-2W** a saldare; alternativa P50/R50 (foro 1,0 mm). Foro del ricettacolo **1,5 mm da verificare con il pezzo** (dati dei venditori discordi), piazzola ovale 2,0 x 3,2 mm (0,54 mm tra piazzole vicine). Corsa ~2-2,5 mm.
- Tag a **faccia in giu'** su 3 blocchetti di plastica da 2,5 mm incollati (S4-S6); punta libera dei pogo a **4,0 mm** (compressione 1,5 mm). Altezza della testa del ricettacolo = 4,0 mm - L (L = quanto la punta sporge a riposo; procedura nel PDF, sezione 7, con sezione quotata).
- **Centraggio:** tre pin di battuta (S1, S2 sul bordo sinistro, S3 sul bordo alto), cioe' i bordi dove ci sono le tacche serigrafiche del tag; gioco 0,1 mm; errore totale stimato ~ +-0,3 mm. Pogo e battute sono sulla parte lontana dal connettore.

## Piedinatura sul connettore

| Pin fisico | GPIO (BCM) | Segnale | Collegamento |
|---|---|---|---|
| 18 | GPIO24 | SWDIO | R1 1 kohm in serie -> P2 |
| 22 | GPIO25 | SWCLK | R2 1 kohm -> P3 |
| 12 | GPIO18 | RESET (P0.18) | R3 1 kohm -> P4 |
| 20 | - | GND | massa comune (anche carica) |
| 2 | - | 5 V solo carica | PTC F1 -> JP1 -> J3 -> P6 |

R2 e R3 sono resistenze "lunghe" (piedini a 10,16 mm) che scavalcano altre piste: sul tag l'ordine e' SWDIO-SWCLK-RESET-GND, sul connettore RESET-SWDIO-GND-SWCLK, quindi su una faccia sola le piste si incrocerebbero. I GPIO sono quelli delle configurazioni OpenOCD storiche (`raspberrypi2-native.cfg`: SWCLK GPIO25, SWDIO GPIO24, SRST GPIO18); le versioni piu' recenti hanno spostato i default (SWCLK GPIO11, SWDIO GPIO8), per questo `swimtag_pi.cfg` assegna i pin esplicitamente.

## Ricarica (in parallelo a SWD)

I pogo P6 (VIN) e P7 (GND) caricano la cella 401012 da 40 mAh tramite il BQ25101 del tag (13,5 mA, terminazione al 10 % = ~1,35 mA, timer 10 h; ~3-3,5 h da vuota).

- **JP1** (header 1x3 + ponticello): **nessun ponticello = ricarica OFF (predefinito)**; 1-2 = 5 V dal Pi (pin 2, via PTC F1); 2-3 = 5 V esterno su J2 (alimentatore limitato a 50-100 mA).
- **LED verde D1 + R4 1 kohm in parallelo** dopo JP1 e prima di J3 (~3 mA, non entra nella misura).
- **J3** (header 1x2): tester in serie in portata mA; senza tester **serve un ponticello**. **F1**: PTC radiale 0,1 A sul 5 V del Pi.
- **Tensione minima:** 5 V - PTC (~0,05 V) - tester (0,05-0,3 V) - Schottky 1N5819WS del tag (~0,2 V) = ~4,4-4,8 V sul BQ25101, contro 4,45-6,45 V consigliati (scheda prodotto TI: da ricontrollare sul datasheet) e soglia VIN-DPM 4,25-4,37 V. Margine **stretto**: tester a basso carico (200 mA), o ponticello su J3, o 5,1 V esterni.
- Massa unica: SWD e carica insieme; il firmware puo' leggere CHG_N (P0.03) e VDDH. Durante la misura il firmware deve stare in sleep (o RESET basso).

## Procedura sintetica (dettagli nel PDF)

1. **Stampa** `stampa/rame_speculare_1a1.pdf` al 100 % (mai "adatta alla pagina"), laser, carta lucida; barra da 50 mm = 50,0 +- 0,3 mm. Sul foglio "USB->" e "JIG 0.4" sono a specchio e il pin 1 e' a destra: dopo il trasferimento (rame guardato da sopra) si leggono dritte, pin 1 a sinistra.
2. **Rame:** taglio a misura (angoli r = 3 mm), pulizia. **Trasferimento** col ferro 5-8 min, bagno, ritocchi. **Incisione** in persolfato o cloruro ferrico (occhiali, guanti, rifiuti al centro di raccolta).
3. **Foratura** (pagina 9): 0,8 / 1,0 / 1,5 / 2,75 mm; connettore con fori solo sulla fila esterna.
4. **Montaggio:** connettore femmina (code dispari tagliate, da sotto, saldato sopra); resistenze, header maschio da sotto, LED, PTC; battute (pin 0,64 mm); blocchetti d'appoggio incollati; pogo per ultimi all'altezza giusta.
5. **Controlli col tester** prima di innestare: continuita' pogo -> punti, nessun corto, nessuna continuita' tra pin 2 e pin 20 ne' tra J4 e il connettore.
6. **Innesto** sul Pi spento con distanziali da 11 mm; cella collegata al tag, tag premuto contro le battute; tester tra J4 e GND: **1,8 V attesi**; poi OpenOCD.

## OpenOCD sul Raspberry Pi (Raspberry Pi OS)

```bash
sudo apt update && sudo apt install -y openocd        # 0.12.0 su Bookworm
openocd -c 'adapter list' -c shutdown                 # deve elencare bcm2835gpio
```

`swimtag_pi.cfg`:

```tcl
adapter driver bcm2835gpio
# Pi 3 / Pi 2 / Zero 2: 0x3F000000     Pi 4: 0xFE000000
bcm2835gpio peripheral_base 0x3F000000
bcm2835gpio speed_coeffs 146203 36
bcm2835gpio swd_nums 25 24        # SWCLK GPIO25 (pin 22), SWDIO GPIO24 (pin 18)
bcm2835gpio srst_num 18           # RESET GPIO18 (pin 12)
reset_config srst_only srst_open_drain
transport select swd
adapter speed 1000                # kHz; sul Pi 4 partire da 400
set WORKAREASIZE 0
source [find target/nrf52.cfg]
```

Sintassi recente: `adapter gpio swclk 25`, `adapter gpio swdio 24`, `adapter gpio srst 18`. **Pi 3 / Pi 4:** cambia `peripheral_base`; `speed_coeffs` e' tarato sul Pi 3 (sul Pi 4 verificare la velocita' reale; alternativa: driver `linuxgpiod` se compilato). **Pi 5 non supportato.**

```bash
# ID e protezione: IDCODE SWD 0x2ba01477; FICR.INFO.PART = 0x00052840; UICR.APPROTECT = 0xffffffff se libero
sudo openocd -f swimtag_pi.cfg -c 'init; dap info; mdw 0x10000100 1; mdw 0x10000060 2; mdw 0x10001208 1; exit'

# UICR.REGOUT0 (0x10001304): VOUT = bit 2:0, 5 = 3,3 V -> 0xFFFFFFFD; NVMC.CONFIG = 0x4001E504
sudo openocd -f swimtag_pi.cfg -c 'init; halt' \
   -c 'mww 0x4001E504 1' -c 'mww 0x10001304 0xFFFFFFFD' -c 'sleep 100' -c 'mww 0x4001E504 0' \
   -c 'mdw 0x10001304 1' -c 'reset run' -c exit
# se il tester su J4 vede ancora 1,8 V, scollegare un istante la cella (il nuovo VDD parte dopo il reset)

sudo openocd -f swimtag_pi.cfg -c 'init; reset run; exit'                  # reset
sudo openocd -f swimtag_pi.cfg -c 'init; halt; nrf5 mass_erase; exit'      # cancella tutto, UICR compreso
sudo openocd -f swimtag_pi.cfg -c 'init; halt; program bootloader.hex verify' -c 'program firmware.hex verify reset exit'
sudo openocd -f swimtag_pi.cfg -c 'init; halt; verify_image firmware.hex; mdw 0x10001304 1; exit'
```

Tensioni attese: **1,8 V** (cella collegata, chip vuoto) -> **3,3 V** dopo REGOUT0 e reset; VIN sul pogo con carica attiva 4,6-5,1 V. Alternativa breve: J-Link o Pico/debugprobe richiederebbero cavetti sulle prese dell'HAT (non previsti).

## Limiti e rischi

- **Livelli.** Con il tag a 1,8 V il Pi porta SWDIO, SWCLK e RESET a 3,3 V, oltre VDD + 0,3 V. Le **1 kohm** limitano la corrente nei diodi di protezione a circa 1 mA per linea (~3 mA in tutto nel VDD del tag): accettabile solo per il primo collegamento breve e solo se il tag con la CPU ferma assorbe piu' di quella corrente. **Non e' una traduzione di livello.** Mitigazioni: scrivere subito REGOUT0; non collegare RESET nel primo passaggio; R1-R3 a 2,2 kohm con 400-500 kHz; adattatore di livello 3,3/1,8 V (BSS138) su SWDIO/SWCLK; programmatore con VTref.
- **Bit-bang** del Pi: con errori di parita' scendere a 200-400 kHz.
- **Foro del pogo** (1,5 mm) e quote del ricettacolo da misurare sul pezzo; anello di rame di 0,25 mm intorno al foro: fragile con foratura a mano.
- **Posizione del connettore e dei fori** presa dalla specifica HAT: da verificare con un Pi reale (e con lo spazio sotto l'HAT di Pi 3/4: nessun componente sotto supera 5 mm, il connettore PoE a 4 pin del Pi 3B+/4 e' piu' basso dei 11 mm).
- **Saldatura sul lato dei componenti** (resistenze, LED, PTC, ricettacoli): meno robusta di una saldatura passante; le saldature del connettore sono quelle che sopportano l'estrazione.
- **Margine VIN** del caricatore (vedi sopra).
- **Non provato fisicamente:** la geometria e' verificata da DRC e render, la scala dei PDF e' stata misurata nel file (barra 50,0 mm), ma la basetta non e' stata costruita.
