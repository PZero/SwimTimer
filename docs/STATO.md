# Stato del progetto

**Ultimo aggiornamento:** 2026-10-24 — Fase 1: tag e display funzionanti sul tavolo, pace clock a 4 lancette, sonno e risveglio del display verificati

## Fatto
- Repository pubblico `PZero/SwimTimer`; template, agenti, comandi; analisi in `docs/IDEA.md`.
- **Tag** (ESP32-S3 SuperMini + BMI160, arduino-cli, core esp32 3.3.12): dati via USB, servizio GATT BLE per la pagina e annuncio BLE con l'ultimo campione per il display; seriale non bloccante; sonno profondo dopo 2 min fermo (solo senza PC e senza pagina collegata), risveglio dal BMI160 su INT1.
- **Pagina** `tools/assi.html`: 3 assi con grafici, collegamento USB o Bluetooth (verificata anche via BLE).
- **Display** LilyGO T-RGB 2,8" (GT911), PlatformIO + core Arduino 2.0.17 + driver LilyGO originale (`firmware/display-prova`): pace clock con 4 lancette continue (circa 15 immagini/s), partenza = colpo secco, arrivo = tag vicino e fermo 3 s, pallini verde/rosso e tempo per 3 s, tocco = azzera, tensione e % batteria.
- **Sonno del display** dopo 5 min senza tag né tocchi; risveglio al tocco o col tasto BOOT (verificato). Corretto il bug per cui ricadeva subito in sonno: il task BLE aggiornava `visto` dopo `ora`, la sottrazione senza segno traboccava; ora i confronti sono con segno. All'avvio il display mostra per 2 s il motivo (accensione, tocco, BOOT, errore, tensione bassa).

## Prossimi passi
1. Far funzionare il display a batteria (vedi problemi aperti).
2. Provare il pace clock con partenza/arrivo veri; provare sonno e risveglio del tag senza PC.
3. Quadrante sempre dritto: accelerometro sul connettore I2C del display (SDA 8, SCL 48, 0x68), ruotando il disegno.
4. Partitore 2×100 kΩ sul tag (BAT+ → GPIO 1 → GND) per la batteria; poi registrazione e prova in vasca; tarare soglia RSSI e calma.

## Problemi aperti
- **Display a batteria non si accende** (nemmeno il LED) staccando l'USB: verificare polarità del connettore, tensione col tester, ricarica di un'ora con USB (protezione della LiPo forse scattata). Il firmware non richiede altro.
- Il BLE non attraversa l'acqua: la logica usa l'accelerometro, il BLE serve per vicinanza e invio.
- Custodia stagna e metodo di spegnimento del tag da definire.
- Nessun test automatico.
