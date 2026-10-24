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
