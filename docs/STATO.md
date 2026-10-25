# Stato del progetto

**Ultimo aggiornamento:** 2026-10-25 — Fase 1: il tag registra sessioni da solo (tap), si aggiorna via Bluetooth e ha una pagina di analisi completa. Si sta preparando la scheda su misura nRF52840.

## Fatto
- Repository pubblico `PZero/SwimTimer`; template, agenti, comandi; analisi in `docs/IDEA.md`.
- **Tag** (ESP32-S3 SuperMini + BMI160, arduino-cli, core esp32 3.3.12), firmware **0.4.2** in `firmware/test-collegamenti`:
  - ±16 g (2048 LSB/g) e 100 Hz; flash 4 MB con due copie del programma (`partitions.csv`) e circa 1,9 MB di LittleFS (~40 min a 50 Hz).
  - Doppio tap = inizio registrazione, triplo tap = fine (rilevamento software: salto oltre 0,8 g tra due letture, escluso con giroscopio oltre 300 °/s). File `/rNNN.bin`, record da 16 byte.
  - BLE: dati 7a1e0002, stato 7a1e0003 (18 byte), comandi 7a1e0004, risposte 7a1e0005, OTA 7a1e0006, versione 7a1e0007. Stesso protocollo di comandi (LIST, GET, DEL, REC, STOP) via USB.
  - Aggiornamento via Bluetooth con ritorno automatico alla versione precedente; versione numerica con marcatore `SWIMTAG_VER=x.y.z;` nel .bin e controlli (stessa versione rifiutata, precedente con conferma).
  - Sblocco automatico del bus I2C (sensore incantato con SDA a 0 V), LED RGB (GPIO 48) come riscontro, motivo dell'ultimo riavvio, partitori su GPIO 1 (batteria) e GPIO 2 (pin 5V).
- **Pagina** `tools/index.html`: schede "Dal vivo" (batteria, 3D reale e corretto, radar con scia di 15 s, interpretazione, eventi, grafici) e "Registrazioni" (scarico, traccia con zoom, eventi del tag e riconosciuti), calibrazione automatica, finestre Firmware e LED, Demo. Una schermata senza scorrimento su schermi larghi.
- **Display** LilyGO T-RGB (pace clock a 4 lancette, sonno e risveglio): invariato, riceve ancora i dati a 16384 LSB/g.
- Ricerca sugli algoritmi: `docs/RICERCA-ALGORITMI.md`. Workflow `.github/workflows/pages.yml` (compila il firmware e pubblica pagina + `firmware/tag.bin`), non ancora eseguito.
- Sessione separata sulla scheda nRF52840 (ramo `claude/scheda-nrf52840-08642d`, non unito): progetto KiCad, BOM, pannello da 6 tag; mancano le piste.

## Prossimi passi
1. Caricare 0.4.1 e 0.4.2 via Bluetooth (file in Download) e verificare partitori, LED, tap e triplo tap con scaricamento.
2. Commit/push riusciti: attivare Pages (Settings → Pages → Source: GitHub Actions) per la pagina su iPhone (Bluefy).
3. Passare dal BMI160 alla lettura dalla FIFO: oggi la frequenza reale è ~44 Hz, si perdono campioni durante le scritture in flash.
4. Registrare sessioni con video (battito di mani per sincronizzare) e mettere a punto gli algoritmi seguendo la ricerca; poi tradurli in C.
5. Prova in vasca; tarare soglia tap, RSSI e calma; quadrante sempre dritto sul display.

## Problemi aperti
- **Display a batteria non si accende** staccando l'USB (polarità, tensione col tester, ricarica di un'ora).
- Riavvii spontanei del tag osservati (motivo ora riportato nello stato); un crash a fine registrazione via Bluetooth corretto nella 0.4.0, da riverificare.
- Il BMI160 si è bloccato una volta con SDA a 0 V (risolto togliendo l'alimentazione; sblocco automatico nella 0.4.2, non provato).
- Brevetti: la ricerca cita il brevetto FORM US 11833392; per un uso commerciale serve una verifica di libertà di operare. Algoritmi nostri, con l'origine annotata.
- Il BLE non attraversa l'acqua: la logica usa l'accelerometro. Custodia stagna del tag e spegnimento da definire. Nessun test automatico.

## Decisioni in attesa dell'utente
- Piste della scheda nRF52840 (sessione `scheda-nrf`), poi ordine dei prototipi.
- Commit/push su GitHub e attivazione di Pages.
