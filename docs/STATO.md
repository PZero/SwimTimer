# Stato del progetto

**Ultimo aggiornamento:** 2026-11-07. Tutto il progetto è nel repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: prototipo. La XIAO nRF52840 Sense è arrivata e funziona con il firmware nostro; ordine dei primi 20 tag su NextPCB in attesa di Viviane.

## Fotografia
- **Scheda v0.6 "Rev0"** (`hardware/nrf52840/kicad/swimtag_v06.*`): 4 strati 0,8 mm, 21,59 × 28,5 mm, senza BGA, MCP73831 (15 mA), TPS22917, DRC/ERC 0. Uscite in `nextpcb/v0.6/` (con `NOTE_ORDINE.md`) e `jlc/v0.6_swimtag_v06/`. Preventivo NextPCB Rev0: 20 pz, **216,39 $** con coupon (~10,8 $/tag) più spedizione e IVA; consegna stimata 2026-11-12. La v0.5 resta come riferimento.
- **XIAO nRF52840 Sense** (`hardware/xiao/`, cella LP-401230 100 mAh, carica 50 mA): ora ha il firmware **`firmware/xiao-stream/` 0.4.2** (Arduino, core Seeeduino:nrf52 + Bluefruit). Protocollo BLE 'SwimTag' come l'ESP32 (dati 16 byte a 25 Hz mediati a 208 Hz, stato a 12 byte, comandi, log, versione). Funzionano: tab XIAO della pagina (busto orientato dall'IMU), **log via BLE**, **bias del giroscopio tarato** (testa meno «storta»), sospensione con comando o **automatica dopo 60 s «abbastanza fermo»** (non con seriale aperta né durante un OTA), risveglio con tap o USB (**provato il doppio tap; i 4 tap e la batteria bassa no**), **aggiornamento firmware via BLE dalla pagina** (OTA nostro sulla 0006, provato 0.4.0→0.4.1→0.4.2, `xiao.bin`/`xiao.json` pubblicati su GitHub Pages). Il DFU Nordic legacy non è raggiungibile dal browser (blocklist).
- **Scheda di prova guasta in parte:** il regolatore 3,3 V è morto (0 V sul 3V3, forse durante la saldatura della cella); va con la cella tramite un diodo al silicio. Cella 100 mAh letta ~4,0 V (tester 4,05 V).
- **Riquadro Batteria** rifatto per la XIAO (stato carica, % LiPo, tempo, grafico, taratura `VCAL`): provato con stati simulati.
- **Display a bordo vasca** (architettura proposta, da confermare): Raspberry Pi 4 + dongle USB nRF52840 + monitor portatile 15,6" + power bank PD, Wi-Fi spento, ~13 W per 2 h, fino a 10 tag. Mockup `tools/display.html` (UI in inglese): segmenti generici, Effort 1–10 dell'ultimo segmento con storico a 10, cronometro che riparte al primo nuotatore, demo con 7 nuotatori e fase mostrata sotto la data.
- Associazione nuotatore–tag con base di ricarica a slot + gettone NFC; versione finale senza flash esterna (buffer RAM ~10 s, solo eventi).
- Prototipo ESP32-S3 + BMI160 (`tools/index.html`, LilyGO T-RGB): abbandonato per ora, codice mantenuto. Firmware nRF52840 definitivo: da scrivere (Zephyr o proseguire in Arduino).
- README solo in inglese; `docs/` in italiano; commit in inglese. Video: https://youtu.be/EVrdSybpnE4 (en), https://youtu.be/_2UzpOqblVI (it).

## Prossimi passi
1. Aspettare Viviane (NextPCB), scadenza consigliata mercoledì 2026-11-11, poi ordinare o meno. Prima: incollare `NOTE_ORDINE.md`, scrivere a Shelly (V-cut, U1), leggere i termini "No Touch", annotare gli MPN per C2–C6 e R3.
2. **XIAO:** comprare un multimetro e una scheda di scorta; tarare la batteria (`VCAL`); provare i 4 tap, la sospensione a batteria bassa e il riquadro Batteria con la scheda vera; tarare le soglie della sospensione sotto la cuffia; «Verifica assi» (segno di Z, `XIAO_ASSE_USB`); celle LP-401230.
3. **Display:** confermare l'architettura Pi + dongle e far preparare la distinta; scegliere il test per l'Effort; decidere il ricevitore al muro opposto (vasca da 50 m); collegare `ricevi()` a una sorgente BLE reale; incorporare i font per l'uso offline.
4. A schede arrivate: prova a banco (Q1, ~50 mA), REGOUT0 a 3,0 V, programmatore, portata antenna.
5. Firmware del tag: eventi con orario e conferma, base a slot/NFC, registrazione; decidere tra Zephyr (MCUboot + SMP) e Arduino. Cancellare a mano `C:\swt_chk`.

## Problemi aperti
- Rischio V-cut con componenti a 0,3–0,6 mm dal bordo (note a NextPCB forse ignorate nel Rev0).
- Livello CHG_N con D4 borderline a VDD 1,8 V; fix: REGOUT0 3,0 V o Schottky.
- Guasto del regolatore della XIAO in saldatura: per le prossime, verificare la polarità col tester, USB staccata, un filo alla volta.
- Il diodo sul 3V3 va bene solo al banco: con cella carica la sospensione è al limite (consigliata una resistenza da 10 kΩ verso massa).
- Brevetti (FORM US 11833392): verifica di libertà di operare prima di vendere.
- Il BLE non attraversa l'acqua e in vasca da 50 m non arriva al muro opposto al display; custodia stagna da definire. Nessun test automatico.
- Effort provvisorio (scala tarata a occhio, test di riferimento da concordare). Monitor ~300 nit: non leggibile al sole. L'OTA ha un'unica prova sulla scheda.

## Decisioni in attesa dell'utente
- Ordine NextPCB dopo Viviane; scheda di scorta, multimetro e celle; architettura del display; test per l'Effort; ricevitore al muro opposto; Zephyr o Arduino. Vedi `docs/DOMANDE-APERTE.md` (33–39).

## Riferimenti
- Scheda: `hardware/nrf52840/progetto.md`; XIAO: `hardware/xiao/README.md`, `firmware/xiao-stream/LEGGIMI.md`; programmatore: `hardware/programmatore/README.md`.
- Prototipo: `hardware/bom.md`, `docs/LEZIONI-APPRESE.md`, `docs/RICERCA-ALGORITMI.md`. Display: `tools/display.html`.
