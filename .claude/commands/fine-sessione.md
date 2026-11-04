---
description: Salva lo stato della sessione nei documenti del progetto e pubblica su GitHub
model: sonnet
---

Chiudiamo la sessione. Senza rileggere file che non servono:

1. Aggiorna `docs/STATO.md`: data di oggi, fase attuale, cosa è stato fatto in questa sessione, prossimi passi, problemi aperti e decisioni in attesa dell'utente. **Riscrivi** il file tenendolo sotto le 60 righe: è una fotografia dello stato, non un diario.
2. Aggiungi a `docs/DECISIONI.md` le decisioni prese oggi (una riga nella tabella: data, decisione, motivazione). Non riscrivere quelle vecchie. Aggiorna `docs/DOMANDE-APERTE.md` (togli le risolte, aggiungi le nuove).
3. Se sono cambiati componenti o collegamenti, verifica che `hardware/` e `firmware/` siano allineati; se sono cambiati i requisiti, aggiorna `docs/REQUISITI.md`. Se esiste l'app, verifica `docs/MODELLO-DATI.md` e `firebase/firestore.rules`.
4. Se ci sono test (`firmware/`: `pio test`; `app/`: `npm test`; `firebase/`: `npm run test:rules`), eseguili e riporta l'esito.
5. Rigenera i file prodotti da script che dipendono da quanto è cambiato (file JLC, PDF del programmatore, sfondi `hardware/wallpaper_v0.4/genera.py`, render): su GitHub devono finire le versioni aggiornate, non quelle vecchie.
6. Affida all'agente `git-readme` (con una sintesi di cosa è cambiato oggi): aggiornare `README.md` (molto dettagliato e professionale, con gli sfondi e le immagini attuali) e `CHANGELOG.md`, controllare che non ci siano chiavi, token, password, `.env` o dati personali reali.
7. **Tutto va su GitHub**, senza chiedere conferma: `git add -A` di tutti i file del progetto (immagini, PDF, file JLC compresi; restano fuori solo quelli in `.gitignore`), commit in italiano, poi `git status` deve risultare pulito.
   - Ramo della scheda (`claude/scheda-nrf52840-08642d`, contiene `hardware/nrf52840/`, `hardware/programmatore/`, `hardware/wallpaper_v0.4/`): push **solo sul remote `privato`** (`PZero/SwimTimer-nrf52840`), sia del ramo sia di `main` (`git push privato HEAD:main`, così la pagina principale del repository privato mostra l'ultima versione). **Mai** su `origin`.
   - Repository pubblico (`origin`, `PZero/SwimTimer`): solo le parti pubbliche (firmware del prototipo, pagina, documenti senza la scheda), da `main`; prima di ogni push su `origin` controlla che non contenga `hardware/nrf52840/`, `hardware/programmatore/` o `hardware/wallpaper_v0.4/`. Se `origin/main` ha commit nuovi, uniscili nel ramo della scheda (`git merge origin/main`) così il repository privato resta completo.
   - Verifica alla fine con `git ls-remote` che i remote puntino allo stesso commit locale. Da sessione cloud: branch `cloud/<data>-<argomento>` + Pull Request.
8. Rispondimi con 5 righe al massimo: cosa è stato salvato (commit e remote) e da dove ripartire la prossima volta.

Dopo questo comando posso chiudere la chat o usare `/clear`.
