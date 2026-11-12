# Stato del progetto

**Ultimo aggiornamento:** 2026-11-12 (sera). Repository unico e pubblico `PZero/SwimTimer` (`main`).

## ⚠ PRIMA DI TUTTO: TOKEN
**Obiettivo dell'utente: dimezzare il costo in token.** Regole (dettaglio in `docs/LEZIONI-APPRESE.md`, voci 27–31):
- un obiettivo per sessione; `/clear` fra un obiettivo e l'altro; all'inizio leggere solo questo file; risposte essenziali;
- agenti sempre **nuovi**, incarico breve, rapporto ≤ 20 righe; **mai riprendere un agente lungo**; `haiku` per compilare, caricare, test;
- niente letture intere di file grandi (Grep + righe); prove hardware: max 3 tentativi; revisore solo sul `git diff`.

## Fase
Struttura definitiva: tag XIAO nRF52840 → **XIAO ricevente** (USB) → host (ora PC, poi **Raspberry Pi 3**) → monitor 15,6″. Lo scarico tag → ricevitore → host funziona a banco con 1 e 2 tag, 0 scarti.

## Versioni in uso
- **Tag 0.6.3** (`firmware/xiao-stream/`): frammenti 238 B (PRONTO v2), DIAGNOSI dopo ogni collegamento, stack BLE 8 KB (`-DCFG_BLE_TASK_STACKSIZE=(256*8)`, obbligatorio anche in OTA).
- **Ricevitore 0.1.6** (`firmware/ricevitore/`, XIAO Sense): central per 2 tag, frame USB con CRC (`PROTOCOLLO-USB.md`), conferma alla tag solo dopo l'OK dell'host.
- **Host** `stazione/ricevitore_host.py` (`--porta COMx --cartella --log`): salva `dati/<tag>/tag.swr` + `.idx` (scritto, fsync, riletto).
- Pi 3 configurato (`swimtimer-pi`, solo chiave SSH, display Waveshare 4″): note in `stazione/rpi/`.
- **Video v4** «Houston, abbiamo un problema» (3 min, solo scritte) pubblicato: IT `85RNvPnFV1E`, EN `mj6OTWkjgwk`; sul portale e nel README. Sorgenti `media/video/genera_video_v4.py`.

## Prove a banco del 2026-11-12 (sera)
Porte sul PC: ricevitore COM21; tag 4a510689 e 447b0247 (COM cambiano). Con l'USB la tag **non registra**: per avere dati servono i 4 tocchi a batteria; l'host chiuso impedisce al ricevitore di collegarsi.

| Prova | Blocchi / scarti | KB/s | ms per blocco | OK→CONFERMATO |
|---|---|---|---|---|
| 1 tag (447b0247, arretrato) | 141 / 0 | 16–16,7 | 287 (radio 283) | 171 (78–203) |
| 2 tag, arretrato poi registrazione | 397 / 0 | ~8,8 per tag (~17,6 tot) | ~490 | 218–248 arretrato, 75–80 in registrazione |
| 2 tag in registrazione | 447 / 0 | ~8 per tag | 547–927 | 183–467 |

- **Il limite è la radio del ricevitore condivisa (~17 KB/s totali)**, non la conferma della tag (il periodo non cambia con la conferma; host 6–13 ms).
- Con 1 tag 287 ms per blocco contro i 150 ms misurati con tag 0.6.1 / ricevitore 0.1.5: da capire.
- **Stack BLE:** 7852 B liberi dopo l'avvio, **606–612 B** dopo ore d'uso → servono ~7,4 KB: con i vecchi 5 KB l'overflow era certo (causa molto probabile del crash dell'11/11). Margine sottile anche con 8 KB.
- HCI 0x3E in fase sicurezza: 2–14 per prova; tag in registrazione si ricollega a ogni blocco (fino a 247 ricollegamenti in 6 min).
- La DIAGNOSI a volte arriva troncata a ~119 caratteri. 4a510689 segna «WDT già attivo al boot» a ogni avvio (causa 5).
- Log e dati delle prove solo nello scratchpad della sessione (dati di salute: mai nel repo).

## Prossimi passi (un obiettivo per sessione)
1. **Tag 0.6.4:** stack BLE a 10 KB; in registrazione **resta collegata** al ricevitore e invia ogni blocco appena completo (decisione dell'utente; verificare consumo e ripresa dopo la perdita del collegamento); capire i 287 ms vs 150 ms con 1 tag (intervallo di connessione 7,5→15 ms? eventi radio del ricevitore); DIAGNOSI non troncata; HCI 0x3E. Poi prova 60 min a banco con 2 tag.
2. **Stazione sul Pi:** `ricevitore_host.py` come servizio + pagina HTML (RSSI, blocchi, KB/s, collegamenti, log); Chromium a schermo intero.
3. Misura a 1/3/5 m e sotto la cuffia; poi sessione in vasca.

## Problemi aperti
1. Banda totale limitata a ~17 KB/s dal ricevitore; con 1 tag 287 ms/blocco (prima 150).
2. Tag in registrazione vicino al ricevitore: un ricollegamento per blocco; HCI 0x3E frequente.
3. Stack BLE: 606 B liberi su 8 KB.
4. DIAGNOSI troncata a ~119 caratteri; «WDT già attivo al boot» su 4a510689.
5. Ricevitore: `#define private public` in `ric.h` per il semaforo delle scritture: da sostituire.
6. **USB caricatore ≠ PC**: sul caricatore la tag deve andare in idle da sola. Da riprogettare.
7. Standby dalla scheda (M_SONNO) e arresto per quiete: non verificati. Diario: eventi persi con BLE collegato (visto «PERSI 177 eventi (RAM piena)»).
8. NOTE 14–18 del diario da aggiungere alla decodifica; `ricevitore/LEGGIMI.md` da aggiornare alla 0.1.6.
9. T-RGB con schermo rotto; restano scheda v0.6 (NextPCB), privacy, V-cut, brevetti.

## Decisioni in attesa dell'utente
Crash dell'11/11 (domanda 65, ora quasi spiegato dallo stack); finestra di 3 blocchi (68, probabilmente inutile); password utente `swim` (67). Dettagli in `docs/DOMANDE-APERTE.md`.

## Riferimenti
Tag: `firmware/xiao-stream/LEGGIMI.md`. Ricevitore: `firmware/ricevitore/LEGGIMI.md`, `PROTOCOLLO-USB.md`. Host: `stazione/ricevitore_host.py`. Pi: `stazione/rpi/LEGGIMI.md`. Protocollo: `docs/SINCRONIZZAZIONE.md`. Compilazione: copiare lo sketch in `C:\Temp\xs\` (il percorso con spazi non va); la porta COM cambia dopo il caricamento.
