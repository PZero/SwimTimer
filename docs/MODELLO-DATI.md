# Modello dati

Contratto tra firmware, strumenti e app online. Aggiornare a ogni modifica.

## File `.swr` (registrazione grezza della tag XIAO)
Formato a pagine da 256 byte (intestazione 16 byte con CRC16, dati a delta), decodificato da `tools/swr.js` e `firmware/xiao-stream/swr.py` (gemelli). Dettaglio: `firmware/xiao-stream/`. Il `.swr` non e' mai nel repository (dato di salute).

## Progetto di annotazione locale (`*.swimproj.json`, versione 1)
`{ versione, video{nome,durata_s,dimensione}, dati{nome,sha256_primi_mb,segmento,fs}, offset_s, sync{video_s,dati_s}, eventi[{id,t_video_s,tipo,nota}] }`. Tempi nel tempo del video; `t_dati = t_video + offset_s`. Tipi evento: B bracciata, R respirazione, V inizio virata, F fine virata, P partenza, A arrivo, X sync (5° tocco).

## Firestore (app online, progetto `swimtimer-pzero`, regole in `firebase/firestore.rules`)
Tutti i timestamp sono `request.time` lato server. Gli autori sono `{ uid, nome }` con `uid == request.auth.uid`.

| Percorso | Campi |
|---|---|
| `users/{uid}` | `nome`, `email`, `foto?`, `stato` (`in_attesa`/`approvato`/`rifiutato`/`revocato`), `creato`, `deciso?`, `decisoDa?` (solo l'amministratore cambia `stato`) |
| `sessioni/{id}` | `titolo`, `data` (AAAA-MM-GG), `nota?`, `caricatoDa{uid,nome}`, `caricatoIl`, `sha256` (64 hex del `.swr` intero), `byte` (<= 4 MiB), `nChunk` (1..6), `completa` (false durante l'upload, poi true) |
| `sessioni/{id}/chunk/{n}` | `n` (0..nChunk-1), `data` (Bytes <= 900000; il client usa 800 KiB). Concatenando i chunk in ordine si ottiene il `.swr`; immutabili |
| `video/{id}` | `sessioneId`, `link` (https Drive/YouTube non in elenco), `nome`, `sha256` (file intero), `byte`, `fps`, `durata_s`, `caricatoDa{uid,nome}`, `caricatoIl`. Il video non e' su Firebase |
| `annotazioni/{id}` | `sessioneId`, `videoId`, `autore{uid,nome}`, `eventi[{tipo,t_video_s,nota}]` (<= 6000), `offset_s` (numero o null), `sync{video_s,dati_s}` (o null), `anticipo_ms` (0..2000), `segmento?` (intero), `nota?`, `creato`, `aggiornato` |

Permessi: leggono solo gli `approvato` (e l'amministratore); modifica/eliminazione solo di chi ha creato (annotazioni: solo l'autore modifica; l'amministratore puo' eliminare tutto). Eliminando una sessione il client elimina prima chunk, annotazioni e video collegati (le regole non fanno cascata).
