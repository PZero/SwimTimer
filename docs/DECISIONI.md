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
