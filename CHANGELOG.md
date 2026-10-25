# Changelog

## 2026-10-25
- Tag, firmware 0.4.2 (`firmware/test-collegamenti`): accelerometro a ±16 g e 100 Hz; registrazione di sessioni su LittleFS con doppio tap (avvio) e triplo tap (fine); tap riconosciuti dai campioni (salto oltre 0,8 g, escluso con giroscopio oltre 300 °/s); scaricamento via Bluetooth o USB.
- Aggiornamento del firmware via Bluetooth (due copie del programma, `partitions.csv`), ritorno automatico alla versione precedente, marcatore `SWIMTAG_VER=x.y.z;` nel .bin; stessa versione rifiutata, precedente con conferma.
- Stato esteso del tag (batteria da partitore su GPIO 1, pin 5V su GPIO 2, motivo dell'ultimo riavvio), sblocco automatico del bus I2C, LED RGB come riscontro. Caratteristiche BLE: dati `7a1e0002`, stato `7a1e0003`, comandi `7a1e0004`, risposte `7a1e0005`, OTA `7a1e0006`, versione `7a1e0007`.
- `tools/index.html` (nuova pagina di analisi): schede "Dal vivo" e "Registrazioni", batteria, orientamento 3D, radar con scia di 15 s, interpretazione, eventi, traccia con zoom, finestre Firmware e LED, Demo; Bluetooth (Chrome, Edge, Bluefy su iPhone) o USB. `tools/assi.html` resta la vecchia pagina.
- `tools/index.html`: corretto `versioneDaBin`, che si fermava alla prima occorrenza di `SWIMTAG_VER=%s;` (formato) e non trovava il marcatore vero; ora riconosce il marcatore anche dopo il formato.
- `.github/workflows/pages.yml`: compila il firmware (arduino-cli, core esp32 3.3.12) e pubblica pagina, `firmware/tag.bin` e `firmware/tag.json` su GitHub Pages. Da attivare in Settings, Pages, Source: GitHub Actions.
- `docs/RICERCA-ALGORITMI.md`: ricerca sugli algoritmi IMU per il nuoto; base utile il brevetto FORM US 11833392; nessun dataset pubblico con IMU sulla testa.
- Hardware: partitori 2×100 kΩ su GPIO 1 e GPIO 2; BMI160 a ±16 g (`hardware/bom.md`, `hardware/schema.md`).
- `.gitignore`: escluso `versione.h`, scritto dalla CI.
- Stato: 0.4.0, 0.4.1 e 0.4.2 compilano; la 0.4.2 non è provata sul tag; frequenza reale in registrazione circa 44 Hz (FIFO del BMI160 da fare). Display invariato.
- README aggiornato: funzionalità, canali BLE, stato e comandi, pagina di analisi, aggiornamento del firmware, CI, privacy, brevetti, roadmap.
- `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati.

## 2026-10-24
- Impostazione del progetto: struttura, agenti, comandi `/stato` e `/fine-sessione`, documenti iniziali.
- Analisi dell'idea iniziale (tag BLE + display a bordo vasca) in `docs/IDEA.md`.
- Logica di partenza e arrivo (spinta, calma, virata parziale) e logiche aggiuntive da valutare in `docs/IDEA.md`.
- Distinta componenti (`hardware/bom.md`) e schema del tag prototipo (`hardware/schema.md`).
- Tag di prova: ESP32-S3 SuperMini + BMI160, batteria LiPo sui pad BAT+/BAT-. Sensore verificato su tutti gli assi.
- `firmware/test-collegamenti`: test del bus I2C del BMI160 e invio delle righe dati a circa 50 Hz.
- `tools/assi.html`: pagina Web Serial (Chrome/Edge) con valori e grafici dei 3 assi.
- README completato con architettura, hardware, firmware, uso e roadmap.
- Display scelto: LilyGO T-RGB. Schema del tag riscritto con la batteria sui pad BAT (TP4056 come alternativa scartata).
- `firmware/test-collegamenti`: servizio GATT BLE (25 Hz) e annuncio `SwimTag` con i dati (20 Hz) per il display. Libreria BLE del core esp32 3.3.12, NimBLE-Arduino scartata perché va in crash.
- `tools/assi.html`: pulsante "Collega via Bluetooth" (Web Bluetooth, Chrome/Edge su desktop e Android) accanto a quello USB.
- `firmware/display-prova` (nuovo): firmware di prova per il display LilyGO T-RGB 2,8" (GT911). Riceve gli annunci del tag senza collegarsi, doppio framebuffer, corona dei 3 assi, cronometro di prova. Driver `src/trgb` adattato da LilyGo-T-RGB 1.0.5 (MIT).
- Distinta e stato: display 2,8" con touch GT911 verificato; `docs/STATO.md`, `docs/DECISIONI.md` e `docs/DOMANDE-APERTE.md` aggiornati.
- README aggiornato: canali BLE e flusso dei dati, firmware del display, compilazione con le librerie, struttura delle cartelle, roadmap.
- `firmware/display-prova`: corretta la ricaduta immediata in sonno profondo (sottrazione senza segno in overflow, ora confronti con segno); risveglio anche dal pulsante BOOT (GPIO 0); pull-up RTC su GPIO 1 durante il sonno; motivo dell'avvio mostrato per 2 s.
- `hardware/bom.md`: aggiunte LiPo 1000 mAh del display (caricatore TP4065) e accelerometro I2C da collegare (SDA 8, SCL 48).
- Problema aperto: il display a batteria, senza USB, non si accende.
