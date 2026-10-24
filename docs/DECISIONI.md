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
