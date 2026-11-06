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
6. Affida all'agente `git-readme` (con una sintesi di cosa è cambiato oggi): aggiornare `README.md` (**solo in inglese**, molto dettagliato e professionale, con gli sfondi e le immagini attuali; `docs/` resta in italiano) e `CHANGELOG.md` (nuove voci in inglese), controllare che non ci siano chiavi, token, password, `.env` o dati personali reali.
7. **Tutto va su GitHub**, senza chiedere conferma: `git add -A` di tutti i file del progetto (immagini, PDF, file JLC compresi; restano fuori solo quelli in `.gitignore`), commit in inglese, poi `git status` deve risultare pulito.
   - Repository **unico e pubblico** `PZero/SwimTimer` (remote `origin`), ramo `main`: lì va tutto (prototipo, firmware, pagina, tag nRF52840, programmatore, sfondi). Se lavori su un altro ramo, prima `git merge origin/main`, poi `git push origin HEAD:main`.
   - Il repository pubblico è visibile a tutti: prima del push controlla con `git grep` che non ci siano email, percorsi con il nome utente, segreti o dati personali.
   - Il vecchio repository privato `SwimTimer-nrf52840` è dismesso: non fare più push lì.
   - Verifica alla fine con `git ls-remote origin` che `main` remoto punti al commit locale. Da sessione cloud: branch `cloud/<data>-<argomento>` + Pull Request.
8. Rispondimi con 5 righe al massimo: cosa è stato salvato (commit e remote) e da dove ripartire la prossima volta.

Dopo questo comando posso chiudere la chat o usare `/clear`.
