---
description: Salva lo stato della sessione nei documenti del progetto e pubblica su GitHub
model: sonnet
---

Chiudiamo la sessione. Senza rileggere file che non servono:

1. Aggiorna `docs/STATO.md`: data di oggi, fase attuale, cosa è stato fatto in questa sessione, prossimi passi, problemi aperti e decisioni in attesa dell'utente. **Riscrivi** il file tenendolo sotto le 60 righe: è una fotografia dello stato, non un diario.
2. Aggiungi a `docs/DECISIONI.md` le decisioni prese oggi (una riga nella tabella: data, decisione, motivazione). Non riscrivere quelle vecchie. Aggiorna `docs/DOMANDE-APERTE.md` (togli le risolte, aggiungi le nuove).
3. Se sono cambiati componenti o collegamenti, verifica che `hardware/` e `firmware/` siano allineati; se sono cambiati i requisiti, aggiorna `docs/REQUISITI.md`. Se esiste l'app, verifica `docs/MODELLO-DATI.md` e `firebase/firestore.rules`.
4. Se ci sono test (`firmware/`: `pio test`; `app/`: `npm test`; `firebase/`: `npm run test:rules`), eseguili e riporta l'esito.
5. Affida all'agente `git-readme` (con una sintesi di cosa è cambiato oggi): aggiornare `README.md` (molto dettagliato e professionale) e `CHANGELOG.md`, controllare che non ci siano chiavi, token, password, `.env` o dati personali reali, poi commit in italiano e push su `origin main` (da sessione cloud: branch `cloud/<data>-<argomento>` + Pull Request).
6. Rispondimi con 5 righe al massimo: cosa è stato salvato e da dove ripartire la prossima volta.

Dopo questo comando posso chiudere la chat o usare `/clear`.
