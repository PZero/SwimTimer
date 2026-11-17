# Stato del progetto

**Ultimo aggiornamento:** 2026-11-17. Repository unico e pubblico `PZero/SwimTimer` (`main`).

## ⚠ PRIMA DI TUTTO: TOKEN
**Obiettivo dell'utente: dimezzare il costo in token.** Regole (dettaglio in `docs/LEZIONI-APPRESE.md`, voci 27–31):
- un obiettivo per sessione; `/clear` fra un obiettivo e l'altro; all'inizio leggere solo questo file; risposte essenziali;
- agenti sempre **nuovi**, incarico breve, rapporto ≤ 20 righe; **mai riprendere un agente lungo**; `haiku` per compilare, caricare, test;
- niente letture intere di file grandi (Grep + righe); prove hardware: max 3 tentativi; revisore solo sul `git diff`.

## Fase
Catena: tag XIAO nRF52840 → **XIAO ricevente** (USB) → **Raspberry Pi 3** (host + pannello, ruotato di 180°) → monitor. Banco: tag 0.6.4 / ricevitore 0.1.7 scaricano 2 tag con 0 scarti; la registrazione però perde campioni quando il collegamento cade (vedi sotto).

## Versioni
- **Tag 0.6.4 provata, 0.6.5 caricata** (`firmware/xiao-stream/`): 0.6.5 = PC sempre accesa; con il solo caricatore sospensione, risveglio coi 4 tap, sonno dopo 3 min fermi. Caricata su entrambe le tag, **non ancora verificata sul campo**. In registrazione resta collegata al ricevitore; stack BLE 10 KB (`-DCFG_BLE_TASK_STACKSIZE=(256*10)`, altrimenti `#error`). `-DQUIETE_REG_S=3900` = build da banco (65 min).
- **Ricevitore 0.1.7**, host `stazione/ricevitore_host.py` (`--stato` per il pannello), stazione Pi in `stazione/rpi/` (servizi systemd, kiosk cog).
- **Scatola di prova della stazione** (`hardware/stazione-involucro/`, OpenSCAD + STL): 164×106×54 mm, cavi 3,6 cm, Waveshare 4″ sul Pi, PowerPack V1.2 sotto, XIAO in vano separato in alto, 2 anelli per il cordino (mensola 45°), prolunga stampata per l'interruttore ON/OFF. **Stampa avviata, misure ancora stimate** (elenco nel LEGGIMI).

## Prova a banco del 12–13/11 (2,5 h, 2 tag ferme, tag sempre collegata)
- ~7100 blocchi, **0 scarti**; stack BLE ≥ 8112 B liberi; nessun evento VBUS.
- **Campioni persi alle cadute del collegamento: 41 s (4a510689) e 54 s (447b0247), ~0,6 %** («FIFO riall»). Cadute molto più frequenti con RSSI −75 dBm (spostate sul mobile).
- **La chiusura per quiete non è scattata** (tag ferme per ore): da indagare via seriale.
- Una tag produce un blocco ogni ~2,5 s: i **512 blocchi bastano per ~21 min**, non 60. Servono scarichi nelle pause; consumo non prioritario (1 h, 1000 mAh).
- Una cella LiPo è scesa a **1,3 V** (registrazione mai chiusa): scartata; ricarica e riuso sconsigliati. Sull'altra tag c'è una **18350 senza protezione, solo banco**.

## Prossimi passi (un obiettivo per sessione)
1. **Tag 0.6.6:** nessun campione perso alla caduta del collegamento; chiusura per quiete verificata; **stop sicuro a batteria bassa** (~3,5 V, sonno profondo); poi prova ripetuta con soste realistiche (5–10 s, 1 min, scarico finale).
2. **Ricevitore 0.1.8** + pulsante «Metti a riposo» sul touch (SONNO 0x14); firmware: «registra» anche da collegata, nome tag dall'annuncio.
3. **Stazione:** alimentazione 5,1 V / 2,5 A; verifica scatola con le misure reali (spina USB, levetta, distanziali); misure a 1/3/5 m, sotto la cuffia, sessione in vasca.

## Problemi aperti
1. **Pi in sottotensione** (`0x50005`) anche con alimentatore diretto: sotto carico il Wi-Fi si blocca.
2. Banda ~17 KB/s per il ricevitore; RSSI −76/−85 dBm con tag lontane; HCI 0x3E da 2 in su; intervallo di connessione sale 7,5 → 15 ms.
3. «WDT già attivo al boot» su 4a510689 (reset software precedente, non un guasto); XIAO con regolatore 3,3 V guasto fragile: scheda di scorta.
4. Batteria sul pannello arrotondata a passi di 20 mV (troncata), non è un errore.
5. Standby M_SONNO da verificare; NOTE 14–22 del diario da decodificare.
6. Idea arrivo dalle bracciate: **indicativa, non conclusiva** (12 arrivi, dipende da k); rifare col riferimento OpenCV.
7. T-RGB con schermo rotto; restano scheda v0.6 (NextPCB), privacy, V-cut, brevetti.

## Decisioni in attesa dell'utente
Distanziali PowerPack–Pi: 11 mm previsti, hai quelli da 22 mm (domanda 73); finestra di 3 blocchi (68); password `swim` (67); ricevitore 0.1.8 con SONNO (72). Dettagli in `docs/DOMANDE-APERTE.md`.

## Riferimenti
Tag: `firmware/xiao-stream/LEGGIMI.md`. Ricevitore: `firmware/ricevitore/LEGGIMI.md`, `PROTOCOLLO-USB.md`. Stazione: `stazione/rpi/LEGGIMI.md`. Scatola: `hardware/stazione-involucro/LEGGIMI.md`. Protocollo: `docs/SINCRONIZZAZIONE.md`. Compilazione: copiare lo sketch in `C:\Temp\xs\` (il percorso con spazi non va); la porta COM cambia dopo il caricamento.
