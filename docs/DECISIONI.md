# Registro delle decisioni

| Data | Decisione | Motivazione |
|---|---|---|
| 2026-10-24 | Repository `PZero/SwimTimer`, segreti solo in `.env` | Nessuna credenziale o dato personale su GitHub |
| 2026-10-24 | Eventuale app su Firebase Spark, senza Cloud Functions | Nessuna spesa |
| 2026-10-24 | Template adattato a progetto hardware: agenti `elettronica` e `app` al posto di `frontend`/`backend` | Il prodotto principale sono due dispositivi; l'app è facoltativa |
| 2026-10-24 | Repository GitHub pubblico | Scelta dell'utente; i dati reali restano fuori da git (`dati/` ignorata) |
| 2026-10-24 | Architettura di partenza: tag BLE indossato + display a bordo vasca | Idea dell'utente; dettagli e limiti in `docs/IDEA.md` |
| 2026-10-24 | Prototipo del tag con ESP32-S3 SuperMini + BMI160 + TP4056 | Componenti già disponibili; il magnetometro si aggiunge dopo se serve |
| 2026-10-24 | Batteria direttamente sui pad BAT+/BAT− dell'ESP32, senza TP4056 né interruttore di programmazione | La scheda ha il caricabatterie integrato; meno componenti |
| 2026-10-24 | START dalla spinta (accelerometro), STOP da tag vicino + calma ≥ ~3 s, con ora presa alla decelerazione | Evita falsi STOP in virata; distanze in multipli di 100 m, display sul lato di partenza |
| 2026-10-24 | Firmware con Arduino CLI (core esp32 3.3.12), non PlatformIO | Già installato sul PC; PlatformIO resta possibile in seguito |
| 2026-10-24 | Strumento di diagnosi come pagina HTML con Web Serial (`tools/assi.html`) | Nessuna installazione; funziona in Chrome o Edge |
| 2026-10-24 | Display a bordo vasca: LilyGO T-RGB (ESP32-S3, display rotondo 480×480, touch, microSD) | Già disponibile; BLE integrato e stesso microcontrollore del tag; si legge da fermi al muro |
| 2026-10-24 | Il display riceve i dati nell'annuncio BLE (dati produttore), senza collegarsi al tag | Un solo collegamento libero per la pagina; latenza bassa; il display resta in sola ricezione |
| 2026-10-24 | Libreria BLE del core esp32 (non NimBLE-Arduino) su tag e display | NimBLE-Arduino manda in crash il tag con core 3.3.12 |
| 2026-10-24 | Driver T-RGB copiato in `firmware/display-prova/src/trgb` e adattato | LilyGo-T-RGB richiede LVGL 8.4 e SensorLib 0.2; sul PC ci sono LVGL 9 e SensorLib 0.3 |
| 2026-10-24 | Doppio framebuffer con attesa del vsync sul display | Niente tremolio negli aggiornamenti |
| 2026-10-24 | Corona del display: 3 assi di accelerazione, un giro ogni 15 s in senso orario | Stessa lettura della pagina HTML, a colpo d'occhio |
| 2026-10-24 | Cronometro di prova: parte con colpo secco, si ferma con tag vicino e fermo 3 s (ora dell'ultimo movimento) | Provabile fuori dall'acqua, dove il BLE non cade |
| 2026-10-24 | Display compilato con PlatformIO, espressif32 6.9.0 (core Arduino 2.0.17), driver LilyGO originale | Con il core 3.x il display RGB scorre e balla (contesa sulla PSRAM); LilyGO supporta solo 2.0.x |
| 2026-10-24 | Il tag resta su arduino-cli con core 3.3.12 | Funziona bene; un solo ambiente per il display |
| 2026-10-24 | Interfaccia del display: pace clock con 4 lancette (sfondo, lancette, segni), al posto del grafico degli assi | Si legge a colpo d'occhio dall'acqua; meno aggiornamenti dello schermo |
| 2026-10-24 | Lancette continue (circa 15 immagini/s), costante per tornare agli scatti di un secondo | Provato: fluido |
| 2026-10-24 | Sonno profondo: tag dopo 2 min fermo (risveglio dal BMI160 su INT1), display dopo 5 min senza tag (risveglio al tocco) | Autonomia della batteria |
| 2026-10-24 | Seriale non bloccante sul tag (`setTxTimeoutMs(0)`) | Senza PC la seriale rallentava il programma e il BLE |
| 2026-10-24 | Quadrante sempre dritto con un accelerometro sul connettore I2C del display | Il display può essere appoggiato in qualsiasi orientamento |
| 2026-10-24 | Display: risveglio anche dal tasto BOOT, pull-up su GPIO1 nel sonno, motivo dell'avvio a schermo | Riserva se il touch non risveglia; diagnosi senza seriale |
| 2026-10-24 | Confronti dei tempi con segno quando un valore arriva da un altro task (`visto` dal BLE) | La sottrazione senza segno traboccava e mandava subito il display in sonno |
| 2026-10-25 | Tag su misura: modulo Raytac MDBT50Q-1MV2, IMU LSM6DSV16X a ±4 g, sensore di pressione MS5837, piazzole SWD sotto la resina | Certificato e montabile da JLC; meno rumore del BMI160 senza saturare; programmazione una volta prima della colata |
| 2026-10-25 | Autonomia del tag: 3 ore di nuoto | Requisito dell'utente: cella piccola, l'ingombro conta più della durata |
| 2026-10-25 | Tag su misura: disposizione B compatta (scheda 17,5 × 19,5 mm, componenti su un lato, cella sopra il modulo), tag finito ~19 × 21 × 7,2 mm | Più raccolta della versione lunga; montaggio su un solo lato più economico |
| 2026-10-25 | Tag su misura: cella LiPo 15–20 mAh con protezione | Bastano per le 3 ore richieste; l'ingombro conta più dell'autonomia |
| 2026-10-25 | Programmatore e custodia di ricarica costruiti da noi (elettronica + stampa 3D su Bambu Lab A1 mini) | Scelta dell'utente: tutto l'hardware è da progettare |
| 2026-10-25 | PCB del tag v0.1: 17,5 × 20,5 mm, 4 strati 0,8 mm, generato da script KiCad e sbrogliato con Freerouting; avviso solo con vibratore | Schema e PCB coerenti da un'unica tabella; 1 mm in più per le piazzole reali della flash |
| 2026-10-25 | Caricatore BQ25101 (disponibile su LCSC) al posto del BQ25100; niente TVS né diodo su VIN, un LED rosso | Spazio sulla scheda; polarità garantita dai magneti della custodia |
| 2026-10-25 | PCB v0.2: protezione dei contatti (TVS SD05 + Schottky B5819WS) e reset hardware all'inserimento nella custodia; scheda 17,5 × 22,5 mm | Richiesta dell'utente; un terzo contatto RESET esposto in acqua rischierebbe corrosione e reset spontanei |
| 2026-10-25 | Nessuna scheda nRF intermedia: il prototipo resta l'ESP32 SuperMini, poi direttamente il tag definitivo | Il prototipo è già montato; la scheda è da progettare comunque |
| 2026-10-25 | Primo ordine JLC: 2 tag senza pannello; pannello con mouse bites (KiKit) dal lotto successivo | Budget: il pannello conviene solo con molti tag |
| 2026-10-25 | Reset del tag all'inserimento nella custodia (nessun terzo contatto esposto); watchdog nel firmware per i blocchi in acqua | Un contatto RESET in acqua rischia corrosione e reset spontanei |
| 2026-10-25 | Sbroglio automatico con Freerouting 2.5.0 (Java 25, jar verificato col checksum di GitHub) | Scheda di 17,5 × 22,5 mm con BGA a passo 0,4 mm: a mano troppo lungo |
| 2026-10-25 | Verifiche sui datasheet: due 100 nF sull'IMU, pull-up I2C 10 kΩ, 10 µF sull'uscita del caricatore, condensatori del modulo vicini a VDD e VDDH | Indicazioni di ST (AN5763), TE, TI e Raytac; vedi `hardware/nrf52840/verifiche.md` |
| 2026-11-01 | Cella LiPo **401012 Ampul** (4 × 10 × 12 mm, 40 mAh dichiarati, 4,2 V, PCM integrato, 1 C) al posto della 301012 da 20 mAh; tag stimato ~19 × 24 × 8,2 mm | Nessuna cella da 3 mm regge 2 C e nessuna 401015 con PCM trovata: stesso ingombro in pianta, 40 mA per il vibratore; capacità reale da misurare |
| 2026-11-01 | Tag v0.3 di collaudo variante **1c**: 26 × 30 mm, una faccia, modulo Ebyte E73 (Raytac a stock 0), senza header, Tag-Connect TC2030-NL sotto, BAT/VBAT con 0 Ω | Indossato a lungo sotto la cuffia per le registrazioni: forma quasi quadrata, niente sporgenze |
| 2026-11-01 | Vibratore **non montato** sui 2 tag di collaudo; pilotaggio e piazzole MOT+/MOT− restano | L'utente non salda e nessun motore SMD adatto è montabile da JLC a rifusione; per le registrazioni non serve |
