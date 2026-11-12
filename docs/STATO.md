# Stato del progetto

**Ultimo aggiornamento:** 2026-11-12. Repository unico e pubblico `PZero/SwimTimer` (`main`).

## ⚠ PRIMA DI TUTTO: TOKEN
**Obiettivo dell'utente: dimezzare il costo in token.** Regole (dettaglio in `docs/LEZIONI-APPRESE.md`, voci 27–31):
- un obiettivo per sessione; `/clear` fra un obiettivo e l'altro; all'inizio leggere solo questo file; risposte essenziali;
- agenti sempre **nuovi**, incarico breve, rapporto ≤ 20 righe; **mai riprendere un agente lungo**; `haiku` per compilare, caricare, test;
- niente letture intere di file grandi (Grep + righe); `xiao-stream.ino` va diviso in moduli;
- prove hardware: max 3 tentativi; revisore solo sul `git diff`; un solo caricamento per gruppo di modifiche (BOT+RST).

## Fase
Passaggio dal prototipo alla **struttura definitiva**: tag XIAO nRF52840 → **XIAO ricevente** (USB) → **Raspberry Pi 3** → monitor (finale 15,6″ HDMI; ora Waveshare 4″). In test: **2 tag in raw**; a regime si registreranno solo gli eventi (pochi dati).

## Fatto il 2026-11-12
- **Pi 3 configurato:** Raspberry Pi OS Lite 64 bit (trixie 2026-10-06), `swimtimer-pi` a `192.168.1.40` (Wi-Fi di casa), utente `swim` solo con chiave SSH del PC (password non impostata), `sudo` senza password. Script e note in `stazione/rpi/`.
- **Display Waveshare 4″ HDMI** (480×800, touch XPT2046) funzionante: `hdmi_cvt 480 800 60 6 0 0 0` + `hdmi_drive=1`, `disable_fw_kms_setup` commentato (con `video=` del KMS l'immagine era triplicata).
- cloud-init gira **solo al primo avvio**: per riconfigurare senza rete si usa uno script con `systemd.run=` sulla partizione di avvio. A ogni avvio `/boot/firmware/diag.txt` riporta lo stato della rete.
- **Analisi del crash dell'11/11** (tag `4A510689`, fw 0.6.0): reset certo (blocco 2519 chiuso dopo il riavvio), causa **non registrata** (0.6.0 non salvava RESETREAS). Batteria 3,99 V, nessun segno prima. Ipotesi: (A) contatto batteria/3V3 momentaneo; (B) stack overflow/HardFault nei callback BLE della sincronizzazione (stack 3 KB, buffer grandi, `snprintf`; reset silenzioso con CFG_DEBUG=0). 25 % dei campioni con acc/giro scambiati (FIFO 0.6.0, corretto in 0.6.1).
- Stima di banda: produzione ~1,25 KB/s per tag; scarico atteso 30–80 KB/s (mai misurato). 100 m con 2 tag ≈ 250 KB ≈ 4–12 s al muro; ciò che non si scarica resta in flash (~27 min per tag).

## Prossimi passi (un obiettivo per sessione)
1. **XIAO ricevente + stazione sul Pi**: firmware `firmware/ricevitore/` (2 tag, sincronizzazione cifrata, USB seriale a pacchetti), conferma dei blocchi alla tag **solo dopo l'ok del Pi**; servizio Python + pagina HTML di dettaglio (RSSI, blocchi in memoria/ricevuti/confermati, KB/s, collegamenti, tempo fermo→collegato, log), salvataggio `.swr` e log sul Pi.
2. **Tag 0.6.2 contro il crash**: stack dei callback più grande, niente buffer grandi/`snprintf` nei callback, hook di overflow che salva il contesto, motivo del reset e diario inviati al ricevitore dopo ogni collegamento; prova a banco 60 min con 2 tag prima della vasca.
3. **Misura della banda** a 1/3/5 m e sotto la cuffia; poi sessione in vasca (anche per verificare standby, quiete, FIFO).
4. Chromium a schermo intero all'avvio del Pi; password dell'utente `swim`.

## Problemi aperti
1. **Causa del crash** non provata (vedi sopra): servono le risposte dell'utente e i dati della 0.6.1/0.6.2.
2. **USB caricatore ≠ PC**: sul caricatore la tag deve andare in idle da sola; dalla pagina del PC la tag su USB non si spegne (si riavvia, regola «mai sonno con VBUS»). Da riprogettare.
3. Standby dalla scheda (M_SONNO) e arresto per quiete su `447B0247`: caricati, **non verificati**.
4. Riallineamenti del FIFO ~40/min con la scheda collegata; mappa dei blocchi ferma con collegamento aperto.
5. Diario: con BLE collegato si perdono eventi (`PERSI`); diario in memoria esterna da decidere.
6. `connect()` della libreria BLE della scheda senza timeout.
7. T-RGB con schermo rotto (resta scheda di sviluppo «cieca»); restano scheda v0.6 (NextPCB), privacy, V-cut, brevetti.

## Decisioni in attesa dell'utente
Risposte sul crash (riavvio a mano? custodia? urto?); conferma della regola «conferma blocchi dopo l'ok del Pi». Dettagli in `docs/DOMANDE-APERTE.md`.

## Riferimenti
Tag: `firmware/xiao-stream/LEGGIMI.md`, `PROVA-0.6.1.md`. Scheda T-RGB: `firmware/display-sync/LEGGIMI.md`. Pi: `stazione/rpi/LEGGIMI.md`. Protocollo: `docs/SINCRONIZZAZIONE.md`. Lezioni: `docs/LEZIONI-APPRESE.md`. Dati dell'incidente: `C:\Temp\swimtimer-backup\2026-11-11\` (fuori dal repo).
