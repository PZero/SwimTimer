# Stato del progetto

**Ultimo aggiornamento:** 2026-10-26 — Fase 1 (prototipo ESP32 sul tavolo) + progetto della scheda su misura nRF52840: PCB v0.2 sbrogliato, pronto per l'anteprima JLC (ramo `claude/scheda-nrf52840-08642d`, da unire al ramo principale).

## Fatto
- **Prototipo** (invariato, dettagli in `hardware/bom.md`, `hardware/schema.md`): tag ESP32-S3 SuperMini + BMI160 con BLE e sonno profondo; display LilyGO T-RGB 2,8" con pace clock a 4 lancette, sonno e risveglio verificati; pagina `tools/assi.html`.
- **Scheda su misura nRF52840** (`hardware/nrf52840/`, solo documenti e KiCad, nessun acquisto):
  - progetto, consumi, rischi, piano a tappe: `progetto.md`; distinta con codici LCSC: `bom.md`; verifiche sui datasheet: `verifiche.md`; ingombro in scala: `ingombro.svg`.
  - **PCB v0.2** in `kicad/`: 17,5 × 22,5 mm, 4 strati 0,8 mm, tag finito ~19 × 24 × 7,2 mm; modulo Raytac MDBT50Q-1MV2, IMU LSM6DSV16X (±4 g), flash 32 MB, caricatore BQ25101 (13,5 mA), sensore di profondità MS5837, vibratore con MOSFET, TVS + Schottky sui contatti di ricarica, reset all'inserimento nella custodia, piazzole SWD sotto la resina.
  - Schema e PCB generati da script (`dati_scheda.py` è l'unica fonte), sbrogliati con Freerouting 2.5.0 (Java 25 installato a fianco del 21): **DRC 0 errori**, netlist 30/30.
  - File per JLC in `kicad/jlc/`: Gerber (zip), `bom_jlc.csv`, `cpl_jlc.csv`, render, PDF dello schema.
  - Confronto con `docs/LEZIONI-APPRESE.md` (documento nella cartella principale, non su questo ramo): lacune riportate alla sessione principale, **nessuna modifica fatta**.

## Prossimi passi
1. **v0.3** (piano approvato il 2026-11-01): cella Ampul 401012 (4 × 10 × 12 mm, 40 mAh) decisa, 2–3 celle da comprare per misurarla; poi decisioni sulle lezioni apprese: sensori alimentati da GPIO (reset senza dissaldare, pull-up sul lato commutato), misuratore di carica MAX17048, + e − serigrafati sulla batteria, eventuale spegnimento vero (interruttore di carico/reed).
2. Caricare `kicad/jlc/` nell'anteprima JLC (account dell'utente): rotazioni, stock dei 7 componenti extended, prezzo (stima 80–100 €, non 50).
3. Ordinare 2 tag (senza pannello); poi firmware Zephyr/nRF Connect SDK con MCUboot e aggiornamento via BLE.
4. Progettare custodia di ricarica (con fusibile ripristinabile) e attrezzo di programmazione (Raspberry Pi Pico + pogo), stampati con la Bambu Lab A1 mini; stampo per la resina più avanti.
5. Prototipo ESP32: prova di vibratore e cicalino sotto la cuffia (sessione principale).

## Problemi aperti
- Budget: l'utente vuole 50 € per JLC, servono ~80 € (senza sensore di pressione) o ~100 €.
- Datasheet ST su st.com non raggiungibile: pin dell'IMU verificati sulla nota AN5763 (da ricontrollare se serve).
- Modulo Raytac, TVS e Schottky senza modello 3D nei render.
- Prototipo: display a batteria che non si accende (vedi `docs/LEZIONI-APPRESE.md`); BLE non attraversa l'acqua; custodia stagna da definire.
- Nessun test automatico di firmware; per l'hardware: `kicad/verifica_netlist.py` e DRC con `kicad-cli`.
- `docs/STATO.md`, `DECISIONI.md`, `DOMANDE-APERTE.md` possono entrare in conflitto con le versioni della sessione principale: unire a mano.

## Decisioni in attesa dell'utente
- Modifiche v0.3 (sopra), budget JLC, per cosa deve avvisare il vibratore, protezione/fusibile della custodia di ricarica.
