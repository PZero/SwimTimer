# Stato del progetto

**Ultimo aggiornamento:** 2026-11-13. Repository unico e pubblico `PZero/SwimTimer` (`main`).

## ⚠ PRIMA DI TUTTO: TOKEN
**Obiettivo dell'utente: dimezzare il costo in token.** Regole (dettaglio in `docs/LEZIONI-APPRESE.md`, voci 27–31):
- un obiettivo per sessione; `/clear` fra un obiettivo e l'altro; all'inizio leggere solo questo file; risposte essenziali;
- agenti sempre **nuovi**, incarico breve, rapporto ≤ 20 righe; **mai riprendere un agente lungo**; `haiku` per compilare, caricare, test;
- niente letture intere di file grandi (Grep + righe); prove hardware: max 3 tentativi; revisore solo sul `git diff`.

## Fase
Catena: tag XIAO nRF52840 → **XIAO ricevente** (USB) → **Raspberry Pi 3** (host + pannello) → monitor. Dal 2026-11-12 la stazione gira **sul Pi** e scarica 2 tag (447b0247 e 4a510689) con 0 scarti.

## Versioni
- **Tag 0.6.4** (`firmware/xiao-stream/`): in registrazione resta collegata al ricevitore; DIAGNOSI2; stack BLE 10 KB. **Ricevitore 0.1.7** (`firmware/ricevitore/`). Scritti il 12/11; prova a banco di 60 min ancora da fare.
- **Host** `stazione/ricevitore_host.py` (`--porta --cartella --log --stato`): `--stato` scrive ogni secondo un JSON per il pannello; errori di porta nel log solo al cambio.
- **Stazione Pi** (`stazione/rpi/`, istruzioni in `LEGGIMI.md`): servizi systemd `swimtimer-host`, `-pannello` (porta 8080, solo libreria standard), `-kiosk` (**cog**, WPE su DRM, senza X; riserva Chromium+cage). `deploy.sh` dal PC, `installa.sh` sul Pi (gira staccato da SSH). Pi: `swim@192.168.1.40` (`swimtimer-pi.local` spesso non risolve), dati in `/home/swim/swimtimer-dati/` (fuori dal repo).
- **Pannello** (`pannello.html`): scheda per tag con nome, RSSI, KB/s, batteria, memoria, blocchi ric/conf/salvati/scart, DIAGNOSI2 (int, MTU, PHY, VBUS, HCI 0x3E, stack libero), indicatore «● REGISTRA» dedotto dalla crescita dell'ultimo blocco annunciato, log filtrato. Nomi tag da `swimtimer-dati/nomi.txt` (solo sul Pi; modello `nomi.esempio.txt`). Display Waveshare 4″ in verticale.

## Prossimi passi (un obiettivo per sessione)
1. **Pulsante «Metti a riposo» sul touch**: il comando SONNO (0x14) esiste già nella tag; serve ricevitore 0.1.8 con frame USB host→ricevitore `0x23 SONNO <id>`, l'host che legge i comandi dal pannello (file in `/run/swimtimer/`), pulsante con doppio tocco di conferma. Poi prova e calibrazione del touch (ADS7846 visto dal Pi).
2. **Firmware**: la tag annuncia «registra» anche da collegata; il ricevitore legge il nome dall'annuncio e lo passa all'host (poi `nomi.txt` non serve più). Raggruppare con le altre modifiche al ricevitore (un solo caricamento).
3. **Alimentazione del Pi**: alimentatore da 5,1 V / 2,5 A, cavo corto. Poi prova 60 min a banco con 2 tag.
4. Pagina orizzontale con le card affiancate (utente d'accordo; rotazione nel browser + touch) e monitor 15,6″: togliere le righe `hdmi_*` da `config.txt`. Poi misura a 1/3/5 m, sotto la cuffia, sessione in vasca.

## Problemi aperti
1. **Pi in sottotensione** (`get_throttled` = `0x50005`) con il PowerPack V1.2 e con alimentatore diretto (4,9 V al misuratore, < 1 A): sotto carico il Wi-Fi si blocca. Validazione blocco 26 ms sul Pi contro 6–13 sul PC.
2. Banda totale ~17 KB/s per il ricevitore; RSSI −76/−85 dBm con tag lontane; HCI 0x3E da 2 in su.
3. Stack BLE della tag: margine sottile (606 B liberi su 8 KB dopo ore, ora 10 KB). DIAGNOSI troncata; «WDT già attivo al boot» su 4a510689.
4. Ricevitore: `#define private public` in `ric.h`. USB caricatore ≠ PC (la tag deve andare in idle da sola). Standby M_SONNO e arresto per quiete non verificati.
5. NOTE 14–18 del diario da decodificare; `ricevitore/LEGGIMI.md` da allineare alla 0.1.7.
6. T-RGB con schermo rotto; restano scheda v0.6 (NextPCB), privacy, V-cut, brevetti.

## Decisioni in attesa dell'utente
Crash dell'11/11 (domanda 65), finestra di 3 blocchi (68), password utente `swim` (67), ricevitore 0.1.8 con comando SONNO e pulsante touch (via libera). Dettagli in `docs/DOMANDE-APERTE.md`.

## Riferimenti
Tag: `firmware/xiao-stream/LEGGIMI.md`. Ricevitore: `firmware/ricevitore/LEGGIMI.md`, `PROTOCOLLO-USB.md`. Stazione: `stazione/rpi/LEGGIMI.md`. Protocollo: `docs/SINCRONIZZAZIONE.md`. Compilazione: copiare lo sketch in `C:\Temp\xs\` (il percorso con spazi non va); la porta COM cambia dopo il caricamento.
