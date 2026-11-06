# Tag di prova con Seeed XIAO nRF52840 Sense (2 esemplari)

Prototipo "subito" in attesa delle schede su misura v0.5 (`hardware/nrf52840/`): stesso SoC (nRF52840), firmware Zephyr / nRF Connect SDK. Il tag sta sotto la cuffia (nuca/tempia), **registra l'IMU in flash mentre è in acqua** (il BLE a 2,4 GHz non attraversa l'acqua) e **scarica i dati via BLE fuori dall'acqua**.

Data della ricerca: 2026-11-05. Prezzi indicativi, da riverificare il giorno dell'ordine. Simbolo ⚠️ = non verificato su una fonte (o fonte ambigua/in contrasto). Fonti numerate in fondo, es. [3].

---

## 1. Distinta materiali (2 tag + prove)

| # | Voce | Modello / scelta | Q.tà | Prezzo indicativo | Dove | Note |
|---|------|------------------|------|-------------------|------|------|
| 1 | Scheda | **Seeed XIAO nRF52840 Sense** (versione Sense, con IMU; non la non-Sense; codice articolo da controllare nel carrello ⚠️) | 2 | 13,1 € + IVA (~16 €) DigiKey IT [6]; 15,90 $ Seeed [2]; 21,6 € RS IT [7] | DigiKey IT / Seeed / RS | Su Amazon IT non l'ho trovata ⚠️. Evitare cloni "Seeeduino Sense" a 40 € e AliExpress senza marchio. Spedizione Seeed dalla Cina ⚠️ ~1-2 settimane; DigiKey/RS in genere pochi giorni ⚠️ |
| 2 | Cella LiPo | **LP-401230, 3,7 V 100 mAh, con protezione (PCM), 30,5 × 12,0 × 4,05 mm, cavo JST-PH 10 cm** | 2 (+1 scorta) | 3,40 € cad. IVA incl. + spedizione [8] | BerryBase (DE), disponibile 35 pz, consegna 1-3 gg | Carica max 1C = 100 mA, standard 0,5C = 50 mA: coincide con la corrente di carica della XIAO. Tagliare il JST e saldare i 2 fili ai pad BAT |
| 2b | Alternativa cella | 150-250 mAh (es. 502030 ≈ 5 × 20 × 30 mm) | - | ⚠️ non verificata | Amazon IT / Soldered | Più autonomia ma più spessa; 250 mAh a 50 mA = 0,2C va bene, a 100 mA = 0,4C |
| 3 | Tappo USB-C | Tappo/antipolvere in silicone per USB-C (set, es. 10 pz) | 1 set | ~5-8 € ⚠️ | Amazon IT | Serve per la mascheratura durante la colata e per tenere chiusa la porta in vasca |
| 4 | Resina (scelta) | **MG Chemicals 832C**, epossidica bicomponente per incapsulare elettronica, traslucida ambra, 375 ml [4][5] | 1 | ⚠️ prezzo non letto (stimo 40-60 €) | DigiKey / Farnell / Mouser IT | Dati: miscela 2:1 volume (2,3:1 peso), vita utile 60 min (100 g), indurimento 24 h a 22 °C, Shore 84D, viscosità ~2,7 Pa·s, assorbimento acqua <1% in 45 gg, uso -30..140 °C [4]. Rigida, **tinta ambra** (non limpida come acqua) |
| 4b | Resina (limpida) | MG 832WC "water clear" [9] | opz. | ⚠️ | idem | Se si vuole vedere il LED; stesso produttore |
| 4c | Resina economica | Epossidica trasparente da colata "deep pour / bassa esotermia" bicomponente 1:1 o 2:1, 250-500 g | 1 | ~20-30 € ⚠️ | Amazon IT / ferramenta | ⚠️ nessuna scheda tecnica verificata: controllare spessore massimo per colata (tipico 2-5 mm per strato) e assorbimento acqua |
| 4d | Resina flessibile (opz.) | Poliuretano bicomponente morbido (Shore A/D bassa) | opz. | ⚠️ | - | Più adatto alla cella che si gonfia (v. §5), ma ⚠️ nessun prodotto verificato |
| 5 | Stampo | (a) stampo in silicone rettangolare ~35 × 25 × 12 mm interno, oppure (b) stampo stampato 3D PLA + distaccante (cera/PVA spray), oppure (c) guaina termorestringente con adesivo (solo prove) | 1-2 | silicone ~8-12 €; PLA ~1 €; distaccante ~8 € ⚠️ | Amazon IT | Il silicone non richiede distaccante e dà una finitura liscia. Stampo con un'asola per far uscire la USB-C |
| 6 | Consumo | Alcool isopropilico ≥99%, guanti nitrile, bicchierini graduati o siringhe da 10 ml (rapporto 2:1 in volume), stecche di miscelazione, nastro **kapton** 5-10 mm | - | ~25 € in tutto ⚠️ | Amazon IT / ferramenta | Una bilancia da 0,01 g (~10 €) permette di usare il rapporto in peso 2,3:1, più preciso delle siringhe |
| 7 | Saldatura | Stagno, filo siliconico fine 26-28 AWG (se si cambiano i fili della cella) | - | già in possesso? | - | L'unica saldatura: i 2 fili ai pad BAT sul retro |

**Totale stimato per 2 tag:** schede ~32-35 € + celle ~7 € (+ spedizione ~5 €) + tappi 6 € + resina 832C ~50 € (o ~25 € economica) + stampo 10 € + consumi 25 € = **circa 130 € con 832C, circa 105 € con la resina economica** ⚠️ (la resina e la spedizione sono stime).

### Dati verificati della scheda (wiki Seeed [1] e Zephyr [3])

| Caratteristica | Valore |
|---|---|
| IMU | **LSM6DS3TR-C** 6 assi (accelerometro + giroscopio), I2C 0x6A [1][10]; alimentato da un pin (IMU_PWR = P1.08), INT1 su P0.11 [1][10] |
| Flash | **2 MB** P25Q16H, QSPI (`nordic,qspi-nor`) [1][3] (la wiki cita anche "1MB Flash" in una tabella: è la flash interna del SoC) |
| Caricatore | **TI BQ25101** [1][11]; **50 mA di default**, **100 mA se P0.13 è portato a LOW** (uscita); in ingresso/alta impedenza = 50 mA [1][12] |
| Tensione di carica | BQ25101 = 4,20 V (le varianti "H" sono 4,35 V) [11]; ⚠️ alcune schede prodotto parlano di 4,35 V: controllare lo schema Seeed e misurare la tensione a cella piena prima di collegare la LiPo da 4,2 V |
| Pad batteria | Pad **BAT +/-** sul retro della scheda: la gestione batteria (carica, misura) funziona **solo** con i pad sul retro, non col pin 5V [13] |
| Dimensioni | 21 × 17,8 mm [1] (spessore ⚠️ ~3,5 mm col connettore, non riportato) |
| Consumo in sleep | Scheda tecnica dice "< 5 µA" [1]; utenti riportano ~0,5 µA con flash QSPI in deep power-down (comando 0xB9) [14] o 140-570 µA se la flash/periferiche restano accese [14] ⚠️ da misurare |
| Bootloader | Adafruit nRF52 Bootloader (UF2): doppio tap su reset, appare l'unità `XIAO BLE`, si copia `zephyr.uf2` [3]. Non è un DFU via BLE; per l'aggiornamento senza pulsante serve una funzione firmware ⚠️ |
| LED | RGB attivo basso: rosso P0.26, verde P0.30, blu P0.06; LED di carica rosso P0.17 (LOW in carica) [1] |
| Lettura batteria | ADC P0.31 (AIN7), abilitazione con P0.14 a LOW; **non** tenere P0.14 HIGH durante la carica (rischio di bruciare P0.31) [1][13]; rapporto del partitore non riportato ⚠️ |
| Zephyr | Board `xiao_ble`, target `xiao_ble/nrf52840/sense` [3]; il devicetree usa il driver `st,lsm6dsl` per l'IMU (compatibile con l'LSM6DS3TR-C) [10] |

---

## 2. Procedura di sigillatura (XIAO + cella, USB-C fuori)

**Principio:** la scheda è già sigillata nella colata tranne la USB-C (ricarica e programmazione), chiusa con tappo in silicone in acqua. **Prima della colata** si programma e si collauda tutto: dopo la resina l'SWD/le pastiglie non servono più, ma il pulsante di reset e la USB devono restare utilizzabili.

### 2.0 Prova a vuoto su un campione (OBBLIGATORIA, prima dei tag veri)

1. Costruire un "tag finto": un ritaglio di FR4/cartoncino delle stesse misure della XIAO + una cella finta (un blocchetto di plastica 30 × 12 × 4 mm, mai una LiPo vera o danneggiata) + un pezzetto di carta assorbente avvolto in kapton come **indicatore di infiltrazioni** + un tappo USB-C inserito in un connettore finto.
2. Fare l'intera procedura §2.1-2.6 su questo campione: fissaggio, mascheratura, strati, tempi, sformatura.
3. Pesare prima e dopo l'immersione (bilancia 0,01 g). Poi tagliare il campione a metà: cercare bolle, vuoti sotto la scheda, adesione alla USB-C, spessore dei singoli strati.
4. Ripetere se emergono bolle > 1 mm o sbavature nella porta.

### 2.1 Preparazione (pulizia ed essiccazione)

1. Programmare e collaudare la XIAO a banco (vedi §4): BLE, IMU, flash, carica, lettura batteria.
2. Pulire la scheda con alcool isopropilico e spazzolino morbido (residui di flussante impediscono l'adesione e causano corrosione); asciugare.
3. **Essiccare 2-4 h a ~40 °C max** (non oltre: la LiPo ⚠️ sopporta max ~45 °C in carica e 60 °C in scarica per le celle tipiche) e lasciare in un contenitore con gel di silice fino alla colata. L'umidità intrappolata dà bolle e distacco.
4. Indossare guanti; non toccare più la scheda sul lato dei componenti.

### 2.2 Fissaggio cella e fili

1. Cella: tagliare il connettore JST, lasciare ~2 cm di filo, saldare **+ e -** ai pad BAT sul retro (rispettare la polarità: invertire distrugge la scheda).
2. Isolare le saldature con kapton; fare un'ansa di scarico (i fili non devono fare leva sui pad).
3. Fissare la cella al retro della scheda con biadesivo sottile (~0,2 mm) **oppure** lasciarla appoggiata in un nido in schiuma/silicone morbido (§5, gonfiore). La cella sta dietro alla scheda, non sopra l'antenna ceramica.
4. Spessore finale atteso: scheda ~3,5 ⚠️ + cella 4,05 + resina 1 mm per lato ≈ 10 mm; ingombro ~25 × 22 mm.

### 2.3 Orientamento noto dell'IMU

1. Fissare **una sola orientazione** scheda/stampo (la XIAO ha l'IMU sul retro, accanto al microfono ⚠️: confermare il verso sul disegno Seeed).
2. Con un pennarello indelebile (o un'incisione nello stampo) segnare sull'involucro finito gli assi **X, Y, Z** e una freccia "nuca/alto": sempre lo stesso verso sotto la cuffia.
3. Annotare in `hardware/xiao/` (o nella pagina web di prove) la convenzione: asse X verso destra, Y verso l'alto, Z verso l'esterno, come da datasheet LSM6DS3TR-C ⚠️ (da verificare con una prova di gravità: tag fermo con il lato segnato verso l'alto, deve dare +1 g sull'asse atteso).
4. Il firmware deve registrare nell'intestazione il modello IMU e la scala (v. §4).

### 2.4 Mascheratura USB-C e pulsanti

1. Inserire il tappo in silicone nella USB-C: deve sporgere dal bordo dello stampo (asola nello stampo), così la resina non entra nella porta.
2. Coprire con kapton la zona del connettore vicino alla porta e le **pastiglie sotto la scheda** non necessarie.
3. **Pulsante di reset:** lasciarlo accessibile (foro Ø ~3 mm riempito con un tappino di silicone/gomma) oppure sacrificarlo e prevedere l'entrata nel bootloader da firmware. Resina sul pulsante = niente doppio tap.
4. LED: lasciare una finestrella libera se si usa resina ambra (il LED in colata ambra si vede poco). ⚠️

### 2.5 Colata in più strati

Dati 832C [4]: miscela 2:1 in volume (2,3:1 in peso), vita utile 60 min a 100 g (molto di più per 10 g: mescolare solo 10-15 ml per volta), forte dipendenza dalla temperatura.

1. Preriscaldare le due parti a ~30 °C in bagnomaria per abbassare la viscosità (aiuta a far uscire le bolle). ⚠️ Non oltre 40 °C.
2. Pesare/dosare con precisione; mescolare lentamente per 2 min raschiando fondo e pareti (non frullare: introduce aria). Lasciare riposare 2-3 min.
3. **Strato 1 (fondo):** 1-2 mm nello stampo, adagiare la scheda con la cella, spingere leggermente per cacciare l'aria sotto. Aspettare **gelificazione** (circa 4-6 h a 22 °C ⚠️).
4. **Strato 2:** fino a coprire metà cella (~3-4 mm di spessore per strato), eliminare bolle superficiali con uno stecchino o con un colpo di phon a 20 cm (rapido, non scaldare).
5. **Strato 3:** copertura finale di 1-2 mm sopra tutto, USB-C esclusa.
6. Più strati sottili = meno calore e meno bolle. L'esotermia dell'832C non è riportata nelle parti che ho letto ⚠️: partire con strati ≤ 4 mm e controllare con le dita il calore.
7. Proteggere dalla polvere con una scatola capovolta.

### 2.6 Indurimento

| Fase | Condizione |
|---|---|
| Tra uno strato e l'altro | 4-6 h a 20-25 °C ⚠️ (devono essere ancora leggermente appiccicosi per far aderire il successivo) |
| Indurimento completo | **24 h a 22 °C** [4] |
| Indurimento a caldo | 60 min a 65 °C o 45 min a 80 °C [4] **non usare con la LiPo** ⚠️ (limiti di temperatura della cella) |
| Sformatura | dopo 24 h; attesa totale 3 giorni prima della prova in acqua |

### 2.7 Prove di tenuta

1. **A secco (peso + carta):** pesare, immergere 24 h in acqua del rubinetto con tag SPENTO, riasciugare, ripesare (variazione < 0,05 g).
2. **In acqua col tag acceso:** registrazione dell'IMU per 2-4 h in una bacinella con acqua + cloro (tipo piscina 1-3 mg/l ⚠️), poi 24 h, poi 1 settimana.
3. Controllare: ricarica ancora ok, USB-C non corrosa, firmware funzionante, cella non gonfia.
4. **Portata BLE prima e dopo (in aria):** con un telefono e l'app nRF Connect, misurare RSSI a 0,5/1/2/3 m in linea retta, tag allineato, ambiente ripetibile. Fare lo stesso dopo la colata. Differenza accettabile ≤ 3 dB ⚠️ (soglia mia). **In acqua il BLE non va**: l'RSSI sott'acqua non serve a nulla, se non per confermare l'assenza di segnale.

---

## 3. Alternativa senza resina: capsula stagna richiudibile (prime prove)

| | |
|---|---|
| Cos'è | Scatola/capsula in plastica con O-ring (IP67/68), ~40 × 25 × 15 mm interno, in cui infilare scheda + cella; chiusura a vite o a scatto. ⚠️ Nessun modello verificato; costo ~5-10 € |
| Pro | Niente colata, niente attesa di 24 h; si riapre per ricaricare e riprogrammare (USB-C accessibile); recupero della scheda; si possono provare più orientamenti dell'IMU; ottima per le **primissime sessioni di registrazione** e per verificare il firmware |
| Contro | Più ingombrante (> 10 mm di spessore sotto la cuffia); tenuta nel tempo non garantita (O-ring, cloro, pressione in immersione); la scheda ballonzola: vibrazioni = dati rumorosi (fissarla con schiuma/silicone); aria intrappolata = tag galleggiante e non assorbe urti; infiltrazione = cella LiPo in acqua |
| Quando usarla | Test di 15-60 min a testa, controllo dei dati IMU a banco; poi si passa alla resina per prove prolungate |

---

## 4. Differenze rispetto al tag v0.5 (rilevanti per il firmware)

| Aspetto | XIAO nRF52840 Sense (prova) | Tag v0.5 (`hardware/nrf52840/progetto.md`) |
|---|---|---|
| SoC | nRF52840 | nRF52840 (modulo E73-2G4M08S1C) |
| IMU | LSM6DS3TR-C, **I2C 0x6A**, INT1 P0.11, alimentazione da pin P1.08 [1][10] | **LSM6DSV16X**, **SPI**, INT1 P0.26, INT2 P0.06 |
| Flash dati | **2 MB** QSPI (`nordic,qspi-nor`) [3] | **16 MB** in SPI semplice |
| Interruttore sensori | nessun TPS22916C; solo il pin IMU_PWR (P1.08) per l'IMU | **TPS22916C (U6)**, SENS_ON su P0.04: spegne l'IMU per toglierlo dal latch-up |
| Caricatore | BQ25101, 50/100 mA via P0.13 | BQ25101 (13,5 mA sulla cella da 40 mAh) |
| Lettura batteria | ADC P0.31 con abilitazione P0.14 LOW [1] | VDDHDIV5 del SAADC (nessun partitore esterno) |
| LED | RGB attivo basso (P0.26/30/06) + LED di carica P0.17 [1] | 1 LED su P0.22 |
| Alimentazione SoC | VDD/DC-DC dalla scheda (3,3 V ⚠️) | VDDH dalla cella, REGOUT0 = 3,3 V da UICR |
| Boot / aggiornamenti | Adafruit UF2 bootloader (doppio tap reset) [3] | MCUboot + SWD su pastiglie |
| Cella | 100 mAh (consigliata) | 40 mAh |

**Nota per l'app (tocca l'agente `app`):** l'intestazione del file scaricato via BLE deve riportare modello IMU, scala (fondo scala accel/giro), frequenza, versione del formato, perché il tag di prova e il v0.5 producono dati con sensibilità e rumore diversi. Se si aggiunge un campo, il formato dei dati inviati all'app cambia e va concordato.

### Durata di registrazione sulla flash da 2 MB (6 assi, 16 bit = 12 byte/campione, senza compressione)

Flash utile assunta 2.097.152 byte, senza intestazioni ⚠️ (con partizioni di servizio, intestazione e timestamp ogni N campioni, ~5% in meno).

| Frequenza | Byte/s | XIAO 2 MB | Tag v0.5 16 MB (confronto) |
|---|---|---|---|
| 50 Hz | 600 | **~58 min** | ~7,8 h |
| 100 Hz | 1.200 | **~29 min** | ~3,9 h |
| 240 Hz | 2.880 | **~12 min** | ~1,6 h |

Una sessione di nuoto di 45-60 min a 50 Hz entra appena; a 100 Hz serve la compressione (differenze tra campioni consecutivi + codifica) o una finestra più corta. In alternativa, usare la flash interna (~1 MB, parte occupata dall'app) per estendere, ma la cancellazione blocca la CPU e logora il chip ⚠️ non consigliato per ora.

Autonomia: 100 mAh con IMU in alta prestazione ~0,9 mA + CPU in sleep tra i blocchi FIFO ⚠️ stima, da misurare con Nordic PPK2: supera le ore di registrazione sulla flash; il vincolo è la memoria.

### Proposta di struttura del firmware (una base, due schede)

```
firmware/tag/
  prj.conf                    Kconfig comune
  boards/
    xiao_ble_nrf52840_sense.overlay   alias imu0, storage, vbat, led0
    swimtag_v05.overlay               stessa API, nodi diversi (spi/lsm6dsv16x, spi-nor)
  src/
    main.c                    macchina a stati: sleep, registrazione, scarico BLE
    imu_fifo.[ch]             interfaccia astratta: init, start(odr), leggi_blocco
    imu_lsm6ds3.c             backend I2C (XIAO)
    imu_lsm6dsv.c             backend SPI (v0.5)
    storage_log.[ch]          scrittura sequenziale su flash_area "storage_partition"
    power.[ch]                batteria, interruttore sensori (opzionale), sleep
    detect/                   logica di rilevamento, pura C, nessuna dipendenza hardware
  test/                       pio test con dati inventati
```

- **Alias devicetree:** `imu0` (nodo `st,lsm6dsl` I2C su XIAO, `st,lsm6dsv16x` SPI su v0.5), `storage_partition` (stessa etichetta, flash esterna diversa), `vbat` (ADC), `led0`, `sens-on` opzionale (solo v0.5).
- **Kconfig:** `CONFIG_SWIM_BOARD_XIAO` / `CONFIG_SWIM_BOARD_V05` seleziona il backend IMU e la lettura batteria; il resto del codice non cambia.
- **FIFO:** il driver Zephyr `lsm6dsl` non gestisce la FIFO dell'IMU (8 KB): scrivere un backend minimo con `i2c_burst_read` sui registri FIFO ⚠️ da verificare nel sorgente del driver.
- **Sleep:** a fine registrazione mettere la flash QSPI in deep power-down (0xB9) e spegnere IMU_PWR (P1.08), altrimenti il consumo sale a centinaia di µA [14].
- **Formato file:** intestazione con versione, modello IMU, ODR, fondo scala, ora di partenza; payload a blocchi con CRC.
- Il modulo di rilevamento (`detect/`) funziona su array di campioni: si prova con `pio test` e dati inventati, identico sulle due schede.

---

## 5. Rischi e punti da verificare

| Rischio | Gravità | Mitigazione / verifica |
|---|---|---|
| **LiPo in resina rigida**: la cella si gonfia e non ha spazio per espandersi; calore di esotermia e di indurimento | alta | Cella con PCM; nido di schiuma/silicone intorno; cure a ≤ 25 °C; strati sottili; ricarica a 50 mA (≤ 0,5C); mai ricaricare incustodito; sospendere se la cella scalda o si gonfia. La resina 832C ha Tg 35 °C [4] ⚠️: vicino alla pelle potrebbe ammorbidirsi: verificare in uso |
| **Tensione di carica 4,35 V** del caricatore (se la scheda monta davvero una variante H) con cella 4,2 V | alta ⚠️ | Misurare a cella piena con tester prima di sigillare; se > 4,25 V, usare una cella HV (4,35 V) |
| **Corrosione della USB-C esposta al cloro** | alta | Tappo in silicone; sciacquare con acqua dolce e asciugare prima di ricaricare; verificare i contatti dopo 1 settimana; ⚠️ nessun dato sulla tenuta del tappo |
| **Ricarica con porta bagnata**: cortocircuito, corrosione, elettrolisi | alta | Mai ricaricare bagnata: asciugare 30 min, aria compressa; verificare con un tester che VBUS/CC siano a 0 V a tag fuori dal caricatore |
| **Ingresso di acqua dalle fessure fili/stampo** | media | Prova a vuoto con carta assorbente (§2.0); doppia colata attorno ai fili |
| **Colata che copre il pulsante di reset** | media | Foro con tappino o accesso al bootloader da firmware |
| **Resina sopra l'antenna ceramica** (detuning) | media | Misura RSSI prima/dopo (§2.7) |
| **Bolle d'aria** (vuoti = punti di infiltrazione e perdita di robustezza) | media | Dosaggio preciso, pre-riscaldo, strati sottili, mescolamento lento |
| **Orientamento dell'IMU diverso da quello atteso** | media | Segnare gli assi, test di gravità (§2.3) |
| **Memoria 2 MB** (12-58 min) | media | Frequenza 50 Hz o compressione; limite noto, il v0.5 ha 16 MB |
| **Consumo in sleep** non verificato (dichiarato < 5 µA [1], utenti riportano 0,5 µA..570 µA [14]) | media ⚠️ | Misurare con PPK2 prima di fidarsi dell'autonomia |
| **Resina a bordo pelle**: allergie, irritazione | bassa | Completare l'indurimento (72 h), verniciare/rivestire se la pelle è sensibile ⚠️ nessuna scheda sulla biocompatibilità; la scheda dice che il polimerizzato "non presenta pericoli noti" [4] |
| **Temperatura di indurimento / limiti LiPo** | media | Max ~40 °C nelle fasi di essiccazione/cura ⚠️ |
| **Disponibilità e spedizione** | bassa | Seeed dalla Cina ⚠️ lenta; DigiKey/RS IT più rapidi |

---

## Fonti

1. Wiki Seeed XIAO nRF52840 (Sense): <https://wiki.seeedstudio.com/XIAO_BLE/>
2. Negozio Seeed, XIAO nRF52840 Sense (15,90 $): <https://www.seeedstudio.com/Seeed-XIAO-BLE-Sense-nRF52840-p-5253.html>
3. Documentazione Zephyr, board `xiao_ble`: <https://docs.zephyrproject.org/latest/boards/seeed/xiao_ble/doc/index.html>
4. Scheda tecnica MG Chemicals 832C (rev. 2.00): <https://media.onlinecomponents.com/productfiles/mf-mgc/1946295481758717tds-832c-2parts.pdf> (copia letta da <https://www.mgchemicals.com/downloads/tds/tds-832c-2parts.pdf>)
5. Listing 832C-375ML: <https://nl.farnell.com/mg-chemicals/832c-375ml/chemical-potting-compound-375ml/dp/2889782> (prezzo non letto)
6. DigiKey IT, XIAO nRF52840 Sense: <https://www.digikey.it/it/products/detail/seeed-technology-co-ltd/102010694/26553872> (e varianti in <https://www.digikey.it/it/products/detail/seeed-technology-co-ltd/102010632/26553897>)
7. RS Online IT: <https://it.rs-online.com/web/p/arduino-kit-e-schede-compatibili/2500968>
8. BerryBase LP-401230: <https://www.berrybase.de/en/lp-401230-lithium-polymer-lipo-battery-3.7v-100mah-with-2-pin-jst-connector>
9. MG Chemicals 832WC (elenco prodotti): <https://azcus.digikey.com/en/products/detail/mg-chemicals/832WC-375ML/9451527>
10. Zephyr, devicetree `xiao_ble_nrf52840_sense.dts`: <https://github.com/zephyrproject-rtos/zephyr/blob/main/boards/seeed/xiao_ble/xiao_ble_nrf52840_sense.dts>
11. TI BQ25100/BQ25101 (varianti di tensione): <https://www.ti.com/product/ja-jp/BQ25101>
12. Forum Seeed, corrente di carica 50/100 mA (P0.13): <https://forum.seeedstudio.com/t/xiao-sense-nrf52840-a-guide-on-how-to-set-battery-charging-current-0ma-vs-50ma-vs-100ma-non-mbed/276351>
13. Forum Seeed, guida batteria e wiki sulle precauzioni di carica: <https://forum.seeedstudio.com/t/battery-guidance-for-the-nrf52840-sense/273224> e <https://wiki.seeedstudio.com/battery_charging_considerations/>
14. Nordic DevZone, consumi in sleep della XIAO BLE con Zephyr: <https://devzone.nordicsemi.com/f/nordic-q-a/117629/high-power-consumption-in-system-off-mode-using-xiao-nrf52840-ble/530660> e <https://devzone.nordicsemi.com/f/nordic-q-a/97377/xiao-ble-drawing-570ua-with-zephyr/415003>
