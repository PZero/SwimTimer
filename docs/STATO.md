# Stato del progetto

**Ultimo aggiornamento:** 2026-11-08. Tutto è nel repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: prototipo; pronta la **campagna di test 1** (video + raw, annotazione a mano) e la parte online collaborativa; i filtri verranno dopo.

## Fotografia
- **Scheda v0.6 "Rev0"** (`hardware/nrf52840/kicad/`): 4 strati, DRC/ERC 0; uscite in `nextpcb/v0.6/` e `jlc/`. Preventivo NextPCB 216,39 $ per 20 pz, in attesa di Viviane (fino a mer 2026-11-11).
- **Tag di prova XIAO nRF52840 Sense** (cella ora da 1000 mAh, regolatore 3,3 V guasto: va con un diodo): firmware `firmware/xiao-stream/` **0.5.4** sulla tag (caricata via BLE dal PC con uno script che usa il protocollo OTA della pagina; carica a 100 mA). Cella ora da **1000 mAh**: a 100 mA servono ~10-12 h da vuota; 3,58 → 3,61 V in ~2 h, quindi la carica funziona. Registra raw su QSPI 2 MB (208 Hz, ~25 min, `.swr`). **Per registrare:** staccare l'USB, addormentarla (Sospendi o 60 s ferma), poi 2 tocchi → blu fisso → 2 tocchi → 3 lampi verdi, poi un lampo verde ogni 8 s. Blu lampeggiante = modalità normale (BLE, sempre con USB o dopo un reset). Con USB alimentata non va in sospensione; USB durante la registrazione la chiude (motivo 4). `release/xiao.bin` pubblicato è ancora 0.4.2.
- **Memoria della tag:** al momento 2204/8192 pagine usate (registrazione di prova a casa), già scaricata e annotata dall'utente (dati personali: restano fuori dal repo).
- **Pagina locale `tools/index.html`** (solo XIAO, riordinata oggi): pannello unico USB/Bluetooth/Demo; schede Dal vivo, Registrazione, Annotazione, Firmware. Rimossi ESP32 e `assi.html`. Provata in browser con Demo e porte simulate, poi dall'utente con la tag vera (USB, scarico, annotazione con video).
- **App online** (nuova, Firebase Spark, nessun Storage/Functions): https://swimtimer-pzero.web.app (landing pubblica) e `/area/` (login Google, approvazione utenti solo admin, sessioni raw su Firestore a chunk, video come link Drive con sha256, annotazioni con autore). Admin = UID in `firebase/firestore.rules`. Aggiornamento automatico della cache (`versione.json` a ogni deploy). Regole: 14 test emulatore verdi. Login e accesso admin provati dall'utente; **non provati dal vivo**: upload sessione, collegamento video, salvataggio annotazione online, duplica come mia, controllo sha256.
- **Display a bordo vasca** (da confermare): Pi 4 + dongle nRF52840 + monitor 15,6" + power bank; mockup `tools/display.html`.

## Prossimi passi
1. **Prova a secco a casa** con la cella carica: registrare (5 colpi, movimento, 5 colpi, 3 min fermo), scaricare via USB, annotare con il video e controllare l'allineamento dei 5 colpi finali.
2. Provare l'app online con dati veri: caricare una sessione `.swr`, collegare il video da Drive, annotare e salvare; correggere ciò che non va.
3. **Campagna di test 1** (50 m, solo l'utente, ~800 m/giorno, 4 giorni, iPhone o Insta360 fermo al muro): esercizi per virate, partenze, arrivi (giorni 1–3), allenamento vero per verifica (giorno 4). Giorno 1 annotato a mano → bozza del filtro (solo web) → giorni successivi pre-classificati con confidenza.
4. Adattare l'Annotazione al frame rate reale (60 fps se iPhone/camera lo permettono).
5. Decidere NextPCB dopo mer 2026-11-11; confermare architettura display.

## Problemi aperti
- Annotazione assume 30 fps (in `tools/` e in `app/area/`, due copie da tenere allineate).
- Dopo il reset con USB la tag una volta non rispondeva finché non è stata riprogrammata; il 2026-11-08 era finita nel bootloader UF2 (cause ignote).
- 0.5.x: da verificare su hardware FIFO gyro/acc, consumi, durata reale con dati veri; LED poco visibile sotto la cuffia; nessun BLE/OTA durante la registrazione.
- Privacy: video e raw dei nuotatori sono dati di salute (consenso scritto, permesso della piscina, mai nel repo).
- Rischio V-cut v0.6; livello CHG_N con D4 borderline; brevetti; BLE non attraversa l'acqua, custodia stagna da definire.

## Decisioni in attesa dell'utente
- Frame rate del video e programma dei 4 giorni (domande 46–47); ordine NextPCB; scheda di scorta e multimetro; architettura display; test per l'Effort; Zephyr o Arduino. Vedi `docs/DOMANDE-APERTE.md`.

## Riferimenti
- Firmware: `firmware/xiao-stream/LEGGIMI.md`. Scheda: `hardware/nrf52840/progetto.md`. Pagina locale: `tools/index.html`. App online: `app/`, `firebase/`, `docs/MODELLO-DATI.md`, `docs/DESIGN.md` (sezione App online).
- Video: https://youtu.be/EVrdSybpnE4 (en), https://youtu.be/_2UzpOqblVI (it).
