# Stato del progetto

**Ultimo aggiornamento:** 2026-10-24 — Fase 1: prototipo del tag funzionante

## Fatto
- Repository pubblico `PZero/SwimTimer` con template, agenti e comandi.
- Idea analizzata in `docs/IDEA.md`: tag BLE con sensori + display a bordo vasca; logica START/STOP/virata e logiche aggiuntive.
- Tag di prova saldato (ESP32-S3 SuperMini + BMI160, batteria sui pad BAT) e verificato: accelerometro e giroscopio rispondono su tutti gli assi.
- `firmware/test-collegamenti`: test del bus I2C e invio dati a 50 Hz; `tools/assi.html`: pagina con valori e grafici dei 3 assi (Chrome/Edge, Web Serial).

## Prossimi passi
1. Firmware di registrazione: salva accelerazioni, rotazioni e segnale BLE in memoria per le prove in vasca (sacchetto stagno).
2. Prova in vasca e analisi dei dati: spinta dal muro, virata, arrivo, soglie di calma.
3. Display a bordo vasca: scelta componenti e firmware di ricezione BLE.

## Problemi aperti
- Il BLE non attraversa l'acqua: la logica si basa sull'accelerometro, il BLE serve per vicinanza e invio dati.
- Verificare con il tag fermo: un asse ≈ ±1 g, gli altri ≈ 0; giroscopio ≈ 0.
- Protezione della batteria sul tag e metodo di spegnimento da definire (vedi `hardware/schema.md`).
- Nessun test automatico ancora (`pio test` non impostato).
