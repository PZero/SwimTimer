# Stato del progetto

**Ultimo aggiornamento:** 2026-10-24 — Fase 1: tag e display funzionanti sul tavolo

## Fatto
- Repository pubblico `PZero/SwimTimer`; template, agenti, comandi; analisi in `docs/IDEA.md`.
- **Tag** (ESP32-S3 SuperMini + BMI160, batteria sui pad BAT): `firmware/test-collegamenti` invia i dati via USB (50 Hz), via servizio GATT (25 Hz) e dentro l'annuncio BLE (20 Hz, per il display).
- **Pagina** `tools/assi.html`: 3 assi con grafici, collegamento USB o Bluetooth (Chrome/Edge).
- **Display** LilyGO T-RGB 2,8" (GT911): `firmware/display-prova` con doppio buffer senza tremolio, corona con le 3 linee in senso orario, cronometro (colpo secco = parte; tag vicino e fermo 3 s = stop all'ultimo movimento), tocco per azzerare. Driver in `src/trgb` (adattato a SensorLib 0.3 e doppio buffer).
- Core esp32 3.3.12: NimBLE-Arduino va in crash, si usa il BLE del core; LVGL 9 e Arduino_GFX 1.6.4 non compilano con la T-RGB.

## Prossimi passi
1. Caricare sul tag l'ultimo firmware (annuncio con i dati) e provare corona e cronometro sul tavolo.
2. Montare il partitore 2×100 kΩ (BAT+ → GPIO 1 → GND), poi percentuale batteria e stato di carica su tag, display e pagina.
3. Tarare la soglia RSSI "vicino" e la calma; firmware di registrazione in memoria per la prova in vasca.

## Problemi aperti
- Il BLE non attraversa l'acqua: la logica usa l'accelerometro, il BLE serve per vicinanza e invio.
- Batteria 1000 mAh sulla T-RGB: controllare la polarità prima di collegarla; capacità e protezione dell'altra LiPo da definire.
- Compilazione lenta (librerie in OneDrive): valutare di spostarle fuori.
- Nessun test automatico; custodia stagna e metodo di spegnimento da definire.
