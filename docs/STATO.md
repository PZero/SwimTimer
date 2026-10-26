# Stato del progetto

**Ultimo aggiornamento:** 2026-10-26 (sera) — Fase 1: il tag registra sessioni da solo (tap), si aggiorna via Bluetooth e ha una pagina di analisi pubblicata su GitHub Pages. Diagnosi in corso: a sola batteria il tag non parte. Lezioni del prototipo raccolte per la scheda nRF52840.

## Fatto
- Repository pubblico `PZero/SwimTimer`; template, agenti, comandi; analisi in `docs/IDEA.md`.
- **Tag** (ESP32-S3 SuperMini + BMI160, arduino-cli, core esp32 3.3.12), firmware **0.4.3** in `firmware/test-collegamenti`:
  - ±16 g e 100 Hz (impostati a sensori accesi e riletti); flash con due copie del programma e ~1,9 MB di LittleFS (~40 min a 50 Hz).
  - Doppio tap = inizio registrazione, triplo tap = fine (rilevamento software, poco affidabile: ~1 volta su 10).
  - BLE con dati, stato, comandi, OTA e versione; stessi comandi via USB. Aggiornamento via Bluetooth con ritorno automatico.
  - Sblocco del bus I2C, LED RGB (GPIO 48), motivo dell'ultimo riavvio, partitori su GPIO 1 (batteria) e GPIO 2 (pin 5V).
  - Batteria sostituita e **interruttore generale** montato; partitore verificato col tester (3,91 V letti = 3,91 V misurati).
- **Pagina** `tools/index.html`, online su https://pzero.github.io/SwimTimer/ (Pages attivo, firmware 0.4.3 pubblicato):
  - "Dal vivo" (batteria, 3D, radar, interpretazione, eventi, grafici) e "Registrazioni"; calibrazione automatica, finestre Firmware e LED, Demo.
  - Card batteria nuova: grafico 1–10 min di GPIO 1, GPIO 2 e tensione stimata a riposo, livello target in % con quanto manca; correzione in carica 0,05 V (misurata).
- **Display** LilyGO T-RGB (pace clock a 4 lancette, sonno e risveglio): invariato.
- `docs/RICERCA-ALGORITMI.md` (algoritmi) e `docs/LEZIONI-APPRESE.md` (13 lezioni del prototipo per la scheda miniaturizzata).
- Scheda nRF52840 v0.2, nel repository **privato** `PZero/SwimTimer-nrf52840` (ramo `claude/scheda-nrf52840-08642d`; mai su questo repository pubblico): 17,5 × 22,5 mm, piste complete, DRC 0 errori. Confrontata con le lezioni: mancano alimentazione commutata del sensore, misuratore di carica, spegnimento vero, etichette +/− della batteria; 3 voci coperte in parte.

## Prossimi passi
1. Capire perché a sola batteria il tag non parte: misurare il 3V3 dopo l'accensione con l'interruttore; prova "senza riavvio" (collegato via Bluetooth con USB, poi staccare l'USB).
2. Scheda nRF52840: decidere le modifiche dalle lezioni apprese (sessione `scheda-nrf`), poi anteprima JLC (rotazioni, stock, prezzo) e ordine.
3. Tap riconosciuto in hardware dal sensore (INT mappato) al posto di quello simulato.
4. Lettura dalla FIFO del BMI160: oggi ~44 Hz reali, campioni persi durante le scritture in flash.
5. Sessioni registrate con video, messa a punto degli algoritmi, poi prova in vasca.

## Problemi aperti
- **A sola batteria il tag non fa il lampo blu e non si vede in Bluetooth** (LED rosso acceso, 3,87 V ai pad). Sospetti: latch-up del sensore all'accensione con l'interruttore, o tensione al limite.
- **Latch-up del BMI160** dopo spegnimenti bruschi (3V3 a 0 V, ripartiva solo staccando GND): sul prototipo si spegne tutto con l'interruttore; firmware 0.4.4 (sensore su GPIO 5) scartato, patch tenuta fuori dal repository.
- **Display a batteria non si accende** staccando l'USB: forse lo stesso sintomo del tag.
- Riavvii spontanei osservati; crash a fine registrazione corretto nella 0.4.0, da riverificare.
- Vibrazione sospesa finché non si trova un modulo con transistor (GPIO 5 libero).
- Brevetti (FORM US 11833392): per l'uso commerciale serve una verifica di libertà di operare.
- Il BLE non attraversa l'acqua; custodia stagna da definire. Nessun test automatico.

## Decisioni in attesa dell'utente
- Modifiche alla scheda nRF52840 v0.2 dalle lezioni apprese (comportano di rifare parte delle piste).
- Ordine dei prototipi della scheda nRF52840.
