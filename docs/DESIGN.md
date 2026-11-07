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
