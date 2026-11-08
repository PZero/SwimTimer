# Design

Curato da `coordinatore-design`. Da sviluppare dopo le scelte di `docs/DOMANDE-APERTE.md`.

## Principi
- Si usa in acqua, con occhialini e senza mani libere: zero interazioni durante la nuotata.
- Display leggibile a colpo d'occhio da qualche metro: cifre grandi, alto contrasto, poche informazioni.
- Ogni evento riconosciuto (partenza, arrivo) dà una conferma visiva immediata.

## Prova in piscina: annotazione
Obiettivo: ottenere dati veri annotati a mano (video + registrazione della XIAO) per costruire dopo i filtri di rilevamento.

**Flusso**
1. In vasca: sveglia con 2 tocchi, LED blu, 2 tocchi (la tag registra); poi **5 tocchi di sync** (deboli e ben separati, ~0,4 s) mentre la telecamera inquadra la mano sul tag; poi si nuota.
2. A casa: USB in modalità normale, scheda **Registrazione** di `tools/index.html` (Collega USB, Scarica: salva `AAAAmmdd_HHMMSS.swr`), poi scheda **Annotazione** con il video MP4 (30 fps) e il `.swr`.

**Eventi** (tasto): B bracciata = entrata della mano in acqua; R respirazione = bocca fuori dall'acqua; V inizio virata; F fine virata; P partenza; A arrivo; X sync. Un anticipo regolabile compensa il tempo di reazione (default 0 ms, mai applicato a X).

**Sincronia con X**: nel video si preme X sul fotogramma del 5° tocco; nei grafici si clicca il 5° picco (aggancio al massimo di |acc| entro ±50 ms). `offset = t_dati − t_video`, modificabile (±1 campione, ±1 fotogramma, spostando X). Gli eventi si salvano nel **tempo del video**: cambiando l'offset si spostano tutti sui dati. Progetto `.swimproj.json` ed `eventi.csv` sono locali e ignorati da git (come video e `.swr`).

**Filtri**: si progetteranno dopo, quando tutti gli eventi saranno annotati (niente soglie decise prima di aver visto i dati veri); le misure in acqua restano da fare, il 2,4 GHz non attraversa l'acqua.

## App online: annotazione collaborativa (Firebase Spark)
Sito statico in `app/` (HTML/JS senza build, SDK Firebase modulare da CDN gstatic a versione fissa), regole in `firebase/firestore.rules`, progetto `swimtimer-pzero`, hosting `https://swimtimer-pzero.web.app`. Pagina pubblica `/` (landing con grafici dimostrativi a dati inventati), area riservata `/area/` (accesso Google, approvazione dell'amministratore, elenco sessioni, editor di annotazione = copia adattata di `tools/annotazione.js` con salvataggio su Firestore).

**Modello dati** (dettaglio campi in `docs/MODELLO-DATI.md`): `users/{uid}` (stato `in_attesa|approvato|rifiutato|revocato`), `sessioni/{id}` + `chunk/{n}` (il `.swr` in pezzi da 800 KiB), `video/{id}` (solo riferimento: link Drive/YouTube + sha256 + byte + fps + durata), `annotazioni/{id}` (eventi, offset, sync, autore).

**Regole**: l'amministratore e' riconosciuto dall'UID in `isAdmin()` (segnaposto `INSERISCI_UID_ADMIN` fino al primo accesso); un utente crea solo il proprio `users/{uid}` con stato `in_attesa` e non puo' mai cambiarlo; gli `approvato` leggono tutto, ognuno modifica/elimina solo cio' che ha creato (l'amministratore elimina tutto, non modifica le annotazioni altrui); autore = `request.auth.uid`, timestamp = `request.time`, tipi e dimensioni validati. Limite noto: gli elementi dentro `eventi` non sono validabili uno per uno nelle regole (solo lista e dimensione). Test con l'emulatore: `firebase/test` (`npm test`).

**Quote Spark** (1 GiB archiviati, 50.000 letture e 20.000 scritture al giorno, 10 GiB/mese di uscita): niente listener in tempo reale; l'elenco costa 3 query (sessioni, video, annotazioni), tenute in memoria fino a «Aggiorna»; i chunk, immutabili, si leggono prima dalla cache persistente del browser; un `.swr` pieno (2 MiB) sono 3 documenti. L'autosalvataggio online ha un debounce di 15 s (al massimo 4 scritture/minuto mentre si annota; una sessione di 1 ora ~ 240 scritture). Stima per 5 utenti, 20 aperture/giorno ciascuno: poche centinaia di letture e qualche centinaio di scritture al giorno, meno del 2% delle quote. Spazio: 10 sessioni da 2 MiB = 20 MiB, il 2% di 1 GiB.

**Perche' i video stanno su Drive/YouTube**: Cloud Storage richiede il piano Blaze per i bucket nuovi (dal 2024) e Firestore ha 1 MiB per documento e 1 GiB totali: un video di 5 minuti (centinaia di MB) non ci sta. Si registra solo il link e l'impronta sha256 (calcolata nel browser a blocchi): chi annota apre il file locale e la pagina avvisa se l'impronta non coincide con quella del video registrato.

## Sito pubblico: lingue, contatti, strumenti, display (novembre 2026)
- **IT/EN** su landing e area riservata: dizionario in `app/comune/i18n.js` (`data-i18n` per i testi statici, `t(chiave)` nel JS), scelta in localStorage, default dalla lingua del browser. La pagina Strumenti resta in italiano.
- **Contatti**: sezione nella landing con indirizzo del progetto e modulo (nome facoltativo, email di ricontatto obbligatoria, messaggio); salvataggio in Firestore `contatti` (vedi `docs/MODELLO-DATI.md`); nell'area, pagina admin «Messaggi» con badge dei non letti.
- **Strumenti della tag** su `/strumenti/` con firmware OTA e «Carica online» (account approvato); su GitHub Pages il pulsante non c'è e la pagina rimanda al sito Firebase. **Display** (mockup con dati inventati) su `/display/`, demo: `/display/?demo&vel=10`. Entrambe sono copie fatte dal predeploy in cartelle ignorate da git (`app/strumenti/`, `app/display/`).
