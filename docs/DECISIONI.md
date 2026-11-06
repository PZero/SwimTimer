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
| 2026-10-25 | Pagina di analisi unica `tools/index.html` (3D, radar, interpretazione, registrazioni), al posto di `assi.html` | Un solo posto per vedere i dati, calibrare e rielaborare le registrazioni |
| 2026-10-25 | Calibrazione automatica: fermo in piedi 2 s per l'asse "su", cenno in avanti per l'asse "avanti" | Il tag sotto la cuffia non è mai montato nello stesso modo; senza magnetometro |
| 2026-10-25 | Registrazione sul tag con doppio tap (inizio) e triplo tap (fine), file su LittleFS; la pagina scarica e rielabora | Il BLE non passa l'acqua; la logica sta nella pagina finché gli algoritmi si mettono a punto |
| 2026-10-25 | Tap riconosciuti dai campioni (salto oltre 0,8 g), non dal motore tap del BMI160 | Il bit del motore tap non si attivava mai senza pin mappato |
| 2026-10-25 | Accelerometro a ±16 g e 100 Hz | Il ±2 g satura su tuffi e urti; la letteratura usa 100 Hz o più |
| 2026-10-25 | Flash con due copie del programma e aggiornamento via Bluetooth con ritorno automatico; ~40 min di registrazione | Non servono più cavo e tasto BOOT (con la batteria sempre collegata non si entrava in modalità BOOT) |
| 2026-10-25 | Versione numerica con marcatore nel .bin; stessa versione rifiutata, precedente con conferma; controllo sia nella pagina sia nel tag | Il firmware lo rilasciamo noi; evita caricamenti inutili o file sbagliati |
| 2026-10-25 | Firmware compilato da GitHub e pubblicato con la pagina (`firmware/tag.bin`, `tag.json`) | La pagina può aggiornare "all'ultima" anche dall'iPhone |
| 2026-10-25 | Partitore su GPIO 2 dal pin 5V; percentuale in carica stimata con correzione di 0,15 V | Sapere se è in carica; il misuratore MAX17048 resta l'alternativa precisa |
| 2026-10-25 | LED RGB del tag come riscontro (legenda nella pagina) | Prima il tag era muto: non si capiva se registrasse o dormisse |
| 2026-10-25 | Sblocco automatico del bus I2C all'avvio e dopo 20 letture fallite | Il BMI160 si era incantato tenendo SDA a 0 V |
| 2026-10-25 | Algoritmi propri, ispirati alla letteratura; origine annotata | Brevetti sul campo (es. FORM): verifica di libertà di operare prima di vendere |
| 2026-10-25 | Scheda su misura nRF52840 affidata a una sessione dedicata; prototipo resta l'ESP32 finché gli algoritmi non funzionano | Gli algoritmi sono indipendenti dall'hardware; si evita di cambiare due cose insieme |
| 2026-10-25 | Fondo scala ±16 g impostato a sensori accesi e riletto (fino a 5 tentativi) | Con il BMI160 sospeso le scritture si perdevano: ±2 g sul sensore, ±16 g nella pagina, 8 g da fermo |
| 2026-10-25 | La pagina avvisa se da fermo il modulo non vale circa 1 g | Scale incoerenti tra tag e pagina falsano calibrazione, tap ed eventi |
| 2026-10-25 | Vibrazione sospesa (serve un modulo con transistor; GPIO 5 libero) | Nessun modulo trovato da saldare; riscontro per ora dal LED |
| 2026-10-25 | Latch-up del BMI160: sul prototipo interruttore generale per spegnere tutto; firmware 0.4.4 (sensore alimentato da GPIO 5) scartato. Sulla nRF52840 load switch o P-MOSFET sul sensore | Dopo uno spegnimento brusco il sensore si sblocca solo togliendogli tensione; sul prototipo basta l'interruttore in fase di test |
| 2026-10-25 | Lezioni apprese dal prototipo in `docs/LEZIONI-APPRESE.md`, da applicare alla scheda nRF52840 | Confronto con la v0.2: mancano alimentazione commutata del sensore, misuratore di carica, spegnimento vero, etichette +/− |
| 2026-10-25 | Correzione in carica della percentuale da 0,15 a 0,05 V | Misurato col tester: 3,84 V a riposo, 3,87 V in carica; con 0,15 V la pagina segnava 29% invece di ~65% |
| 2026-10-26 | Card batteria della pagina con grafico di GPIO 1, GPIO 2, tensione stimata a riposo e livello target in % | Distinguere a colpo d'occhio partitori, batteria vera e carica mancante; il valore in carica falsava la percentuale |
| 2026-10-26 | GitHub Pages attivo (Source: GitHub Actions) | Pagina e firmware raggiungibili da iPhone (Bluefy) e aggiornamento "all'ultima" dalla pagina |
| 2026-10-26 | Il progetto della scheda nRF52840 vive nel repository privato `PZero/SwimTimer-nrf52840`; `SwimTimer` resta pubblico | Hardware della miniaturizzazione riservato; rendere privato tutto spegnerebbe GitHub Pages (piano gratuito), che serve pagina e firmware |
| 2026-11-01 | Cella LiPo **401012 Ampul** (4 × 10 × 12 mm, 40 mAh dichiarati, 4,2 V, PCM integrato, 1 C) al posto della 301012 da 20 mAh; tag stimato ~19 × 24 × 8,2 mm | Nessuna cella da 3 mm regge 2 C e nessuna 401015 con PCM trovata: stesso ingombro in pianta, 40 mA per il vibratore; capacità reale da misurare |
| 2026-11-01 | Tag v0.3 di collaudo variante **1c**: 26 × 30 mm, una faccia, modulo Ebyte E73 (Raytac a stock 0), senza header, Tag-Connect TC2030-NL sotto, BAT/VBAT con 0 Ω | Indossato a lungo sotto la cuffia per le registrazioni: forma quasi quadrata, niente sporgenze |
| 2026-11-01 | Vibratore **non montato** sui 2 tag di collaudo; pilotaggio e piazzole MOT+/MOT− restano | L'utente non salda e nessun motore SMD adatto è montabile da JLC a rifusione; per le registrazioni non serve |
| 2026-11-01 | v0.3: sensori su interruttore di carico (TPS22916C), MAX17048 su bus I2C separato, TS del caricatore da GPIO, 2 × 47 µF, 0 Ω tra cella e circuito, niente reed né protezione d'inversione (connettore polarizzato) | Risponde alle lezioni apprese del prototipo senza componenti inutili |
| 2026-11-01 | Programmazione via Tag-Connect TC2030-NL; il pin VDD è solo riferimento (VREF), programmatore a tensione adattabile | Con la cella collegata VDD è già alimentato; a 1,8 V di fabbrica un Pico a 3,3 V danneggerebbe la scheda |
| 2026-11-01 | Wallpaper tecnici e PDF di progetto generati dal PCB reale con script (`hardware/nrf52840/wallpaper/`) | Riproducibili a ogni revisione della scheda |
| 2026-11-02 | **v0.4 "economica"** su JLC con E73: solo IMU, flash, caricatore, 1 LED, header batteria; scheda 22,86 × 26 mm | Prototipi di sola registrazione dei dati grezzi dell'IMU con tetto di 100 € tutto compreso |
| 2026-11-02 | v0.4: via MS5837, MAX17048, TPS22916C, vibratore, Tag-Connect, piazzole di prova, TVS e MOSFET di reset; lettura batteria con VDDHDIV5 | Risparmio di componenti *extended* (3,07 $ l'uno) e di spazio; non servono alla registrazione (manca la profondità) |
| 2026-11-02 | v0.4: 2 strati, 0,8 mm, HASL senza piombo, DRC 0 con regole JLC 0,127 mm | Lo sbroglio a 2 strati chiude senza toccare l'antenna: nessun motivo per i 4 strati |
| 2026-11-02 | v0.4: flash W25Q128JVSIQ SOIC-8 *basic* (C97521) in SPI semplice, 16 MB | 4,93 $ per 2 schede contro 9,83 $ del WSON (caricamento extended); costa 3 mm di larghezza |
| 2026-11-02 | v0.4: TS del BQ25101 con 10 k a massa (niente NTC né GPIO), CHG_N su GPIO, Schottky *basic* in serie ai contatti | Soluzione più economica; carica sempre; polarità e ritorno verso i contatti bloccati |
| 2026-11-02 | v0.4: batteria su header SMD 1,27 mm (C55213900) invece del JST SH | 10,4 contro 26,6 mm² e costa meno; il THT 2,54 mm non è montabile nell'Economic (+~20 $) |
| 2026-11-02 | v0.4: sotto 5 pogo SWD Ø 2 e 2 contatti di ricarica sulla griglia 2,54 mm, tacche di serigrafia | Primo caricamento su millefori con pin/molle pogo saldati |
| 2026-11-03 | v0.4: LED 0603 KT-0603R (C2286, *basic*) con anodo su VDD; scheda ricompattata a 21,59 × 26 mm (E73 a 0,3 mm dal bordo sinistro, pinout dei segnali lenti spostato sui pad interni) | −3,07 $ di caricamento extended; anodo su VDD per non iniettare corrente nel pin al primo avvio (VDD 1,8 V); 20,32 mm non chiude lo sbroglio a 2 strati |
| 2026-11-03 | Programmatore: HAT 65 × 56,5 mm innestato sul 40 pin del Raspberry Pi 3/4 (OpenOCD bit-bang), pogo sulle 7 piazzole, 1 kΩ in serie su SWD, ricarica 5 V con ponticello e PTC; toner transfer | L'utente ha un Pi 3/4 e non vuole comprare altre schede; l'innesto 2×20 completo evita errori di cablaggio |
| 2026-11-03 | Regola "niente saldature" solo per il tag (tutto montato da JLC); il programmatore lo salda l'utente | Chiarimento dell'utente |
| 2026-11-04 | v0.5: TPS22916C su VDD_IMU (R6 su VDD_IMU), TVS C41408025 su VIN, AO3401A contro l'inversione della cella, 100 kΩ VIN-GND, TP8 VDD_IMU, C5/C6 4,7 µF 10 V (C7 tolto), IMU_MISO/CS su P0.08/P0.12; scheda 21,59 × 28 mm | un IMU in latch-up nella resina si sblocca solo senza alimentazione; protezioni dalle revisioni esterne; a 26 mm lo sbroglio a 2 strati non chiude; costo ~125 € (Standard), tetto 100 € non raggiunto |
| 2026-11-04 | Repository unico e **pubblico** `PZero/SwimTimer` con tutto il progetto (scheda, programmatore, sfondi, video); il privato `SwimTimer-nrf52840` dismesso | Scelta dell'utente: un solo progetto; GitHub Pages resta gratuito per la pagina di analisi e i test a secco del tag |
| 2026-11-05 | Associazione nuotatore–tag con la **base di ricarica a slot** ("pulsantiera"): gettone NFC passivo personale lasciato nello slot del tag preso; la base attiva il tag, a fine allenamento ne scarica i dati e li manda al display; tag non attivato = non registra | Il display non è touch e può essere lontano dagli atleti; niente telefono a bordo vasca; deterrente al furto |
| 2026-11-06 | v0.6 "Rev0" (`swimtag_v06`): MCP73831T-2ACI/OT (SOT-23-5, PROG 66,5 kΩ = 15 mA, STAT su CHG_N tramite 1N4148WS + pull-up 100 kΩ) al posto del BQ25101, TPS22917DBVR (SOT-23-6) al posto del TPS22916C, J1 DNP (fili a mano), 4 strati 0,8 mm (In1 massa), 21,59 × 28,5 mm | NextPCB Rev0 rifiuta i BGA con passo < 0,45 mm (DSBGA 0,4); v0.5 resta invariata |
| 2026-11-06 | README.md solo in inglese (nessuna copia italiana), senza sezione ringraziamenti per ora; documenti di lavoro in `docs/` in italiano; nuove voci del CHANGELOG in inglese | Repository pubblico con pubblico internazionale; i documenti interni restano nella lingua di lavoro |
| 2026-11-06 | Resta la v0.6 a 4 strati (non a 2): ordine NextPCB Rev0 da 20 pz in 5 pannelli 2×2, D3 sostituito con LC05CI; si attende il contatto di Viviane prima di ordinare | A 2 strati il risparmio è solo ~25–40 $ (~1,5–2 $/tag) ma la scheda crescerebbe e servirebbe nuovo sbroglio e nuova anteprima; la massa piena aiuta l'antenna |
| 2026-11-06 | Versione finale del tag senza flash esterna (solo eventi, buffer RAM ~10 s); i prototipi la tengono. XIAO nRF52840 Sense con cella LP-401230 100 mAh (minimo 50 mA di carica) valutato come tag di prova | Semplifica l'elettronica; il BQ25101 del XIAO non carica sotto 50 mA |
| 2026-11-06 | Messaggi di commit e descrizione del repository GitHub in inglese (i vecchi commit restano in italiano) | Repository pubblico con pubblico internazionale, coerente con il README |
| 2026-11-06 | Pagina web: tab XIAO con testa wireframe dalla scansione Lee Perry-Smith (CC BY 3.0, caricata da CDN, crediti in pagina), collo e spalle procedurali; calibrazione del montaggio dalla gravità + cenni | Più realistica di una testa procedurale; licenza libera con attribuzione, nessun file del modello nel repo |
| 2026-11-06 | Tag XIAO sempre sul lato destro della testa con il lato componenti verso l'esterno: tolte dalla pagina le scelte «Lato componenti» e «USB-C verso» | Con lato e verso fissi la gravità basta a ricavare anche la rotazione della scheda nel suo piano (verificato: errore 0° con qualunque direzione dell'USB-C); resta solo lo spostamento avanti/indietro, corretto da «Annuisci» |
