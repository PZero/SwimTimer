# Stato del progetto

**Ultimo aggiornamento:** 2026-11-12 (notte). Repository unico e pubblico `PZero/SwimTimer` (`main`).

## ⚠ PRIMA DI TUTTO: TOKEN
**Obiettivo dell'utente: dimezzare il costo in token di ogni avanzamento.** Il 2026-11-11 si è consumato troppo. Regole (dettaglio in `docs/LEZIONI-APPRESE.md`, voci 27–31):
- un obiettivo per sessione; `/clear` fra un obiettivo e l'altro; all'inizio leggere solo questo file;
- agenti sempre **nuovi** con incarico breve e rapporto ≤ 20 righe; **mai riprendere un agente lungo**; `haiku` per compilare, caricare e lanciare i test;
- niente letture intere di file grandi (Grep + righe); `xiao-stream.ino` va diviso in moduli;
- prove hardware: al massimo 3 tentativi, poi rapporto; revisore solo sul `git diff`, un giro per modifica;
- raggruppare le modifiche al display e caricare una volta sola (ogni caricamento chiede BOT+RST all'utente).

## Fotografia
- **Incidente in vasca 2026-11-11:** il nuoto non è stato registrato. La tag si è riavviata durante la registrazione ed è ripartita in modalità normale (PRONTA, tocchi ignorati); in borsa poi ha registrato 23 min da ferma fino a memoria piena. Dati e analisi: copie in `C:\Temp\swimtimer-backup\2026-11-11\` (fuori dal repo).
- **Tag 0.6.1 (versione di prova `-prove`) su entrambe le tag** (`4A510689` e `447B0247`): ripresa automatica dopo crash e watchdog (marca + seconda rete, max 3), watchdog 8 s, contesto del guasto, diario persistente (`DIARIO`), FIFO riallineato (controllo sul contenuto provato con urti), tempo di sessione continuo (T_AVVIO 500 ± 30 ms, misurato via USB e a batteria), regole USB (2 s, attesa VBUS, mai sonno con VBUS), LED visibili nella gestione dei tocchi, comando SONNO sul canale di sincronizzazione. Dettagli: `firmware/xiao-stream/LEGGIMI.md`, prove: `PROVA-0.6.1.md`.
- **Display:** schermo del T-RGB **rotto** (piattina strappata). La scheda funziona «cieca»: scarica le tag sulla SD e crea la rete Wi-Fi **SwimTimer** (password in `segreti.h`, fuori da git) con la pagina di stato su `http://192.168.4.1` (avvisi con l'azione da fare, REGISTRA anche durante lo scarico, «Ultimo blocco salvato su SD», pulsante standby). Pannello impostato a 2,8″ fisso.
- **Involucro del display** disegnato: `hardware/display-involucro/` (vaso PLA, tappo in silicone, forcella con snodo a scatti di 15°, STL e rendering).

## Problemi aperti (in ordine di importanza)
1. **USB caricatore ≠ PC (richiesta dell'utente, non fatto):** sul caricatore la tag deve andare **da sola in idle** (sonno), svegliabile; oggi con qualsiasi USB resta sveglia in modalità normale. Inoltre **dalla pagina del PC la tag su USB non si spegne**: si riavvia (effetto della regola «mai sonno con VBUS», `NOTA 11`). Da riprogettare insieme.
2. **Standby dalla pagina della scheda non funziona ancora:** prima versione (secondo collegamento) fallita; seconda (comando M_SONNO sul canale di sincronizzazione, inviato subito dopo PRONTO) caricata ma **non verificata**.
3. **Arresto per quiete (3 min fermo) non scatta** sulla tag `447B0247`; correzione del bias caricata ma non verificata.
4. **Riallineamenti del FIFO ~40/min con la scheda collegata** (4–7 a riposo): dati corretti ma molti piccoli buchi.
5. **Mappa dei blocchi ferma** quando il collegamento resta aperto (tag vicina).
6. **Diario:** con il BLE collegato non si scrive in flash e si perdono eventi (`PERSI`); in futuro diario nella memoria esterna (tocca la mappa a 512 blocchi del display).
7. `connect()` della libreria BLE della scheda senza timeout.
8. Schermo da ricomprare (T-RGB 2,8″ completo) e antenna U.FL/IPEX-1 da verificare (schema del T-RGB).
9. Restano: scheda v0.6 (NextPCB), privacy dei dati, rischio V-cut, brevetti.

## Risolti il 2026-11-11
Analisi dell'incidente; ripresa automatica e protezione dai cicli (provate a batteria: 3 crash e 3 blocchi, rifiuto alla 4ª); USB instabile (caso 40 superato); LED per i tocchi; tempo di avvio misurato a batteria (494–496 ms); urti e taglio forzato del FIFO superati; memoria piena diagnosticata (azzerata dopo copia verificata); pagina Wi-Fi funzionante da iPhone; agente `revisore` creato.

## Prossimi passi
1. **Sessione in vasca** con la tag e la scheda cieca (lista nel messaggio di fine sessione: dati cellulari spenti, 2 tocchi → verde → 2 tocchi → 3 lampi verdi, REGISTRA sulla pagina, a fine allenamento «Da scaricare 0 %» poi USB).
2. **Riprogettare gli stati della tag** (caricatore/PC/batteria, idle, standby) con un piano scritto prima del codice.
3. Verificare standby, quiete, FIFO in movimento sui dati della vasca.
4. Ordinare il T-RGB nuovo; decidere l'antenna.

## Riferimenti
Tag: `firmware/xiao-stream/LEGGIMI.md`, `PROVA-0.6.1.md`. Scheda: `firmware/display-sync/LEGGIMI.md`, `web.cpp`, `pagina.h`. Protocollo: `docs/SINCRONIZZAZIONE.md`. Lezioni: `docs/LEZIONI-APPRESE.md`. Involucro: `hardware/display-involucro/LEGGIMI.md`.
