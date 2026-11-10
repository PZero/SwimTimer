# Banco di prova IMU (fase 2)

Misura i rilevatori di eventi di nuoto (A = arrivo, P = partenza, V = virata) sui dati grezzi dell'IMU del tag
(LSM6DS3, ±16 g, ±1000 dps), confrontandoli con un riferimento video. Python 3 + numpy + scipy.

**Niente dati personali nel repository**: le sessioni di nuoto sono dati di salute. Dataset, cache e risultati
vanno in una cartella FUORI dal repository (`valuta.py` rifiuta un output dentro il repo senza `--forza`).

## Un comando

```
python analisi\imu\valuta.py --sessioni <cartella_dataset> [--uscite <cartella_uscite>]
```

Produce in `<uscite>`: `rapporto_fase2.md`, `risultati_<sessione>.json`, `cache/` (decodifica .swr in cache).
Opzioni utili: `--k auto|1.0`, `--frequenze 104,52,26`, `--tol 1.5`, `--salta-causalita`.
Tempo: circa 1 minuto per sessione. Test (solo dati sintetici): `python analisi\imu\test_banco.py`.

## Formato del dataset (una cartella per sessione)

```
<dataset>/<nome_sessione>/
    sessione.json      metadati
    <file>.swr         registrazione del tag
    eventi.json        riferimento: {"eventi":[{"t_video_s":..,"tipo":"A|P|V|X"}]}   (o eventi.csv)
```

`sessione.json` (campi: vedi `dataset.py`): `swr`, `indice_sessione` (null = la piu' lunga nel file), `riferimento`,
`montaggio`, `sync.video_s`, `sync.dati_s` (null = lo cerca nella finestra `ricerca_dati_s`), `k` (scala video->dati,
`t_dati = t_sync + (t_video - sync_video) * k`), `k_metodo`, `durata_video_s`, `etichettato_fino_s` (oltre non ci sono
etichette: non sono negativi), `acqua_dati_s` (intervallo in acqua per la calibrazione degli assi), `tipi`.
Una sessione con `"solo_confronto": true` serve solo alla verifica del porting (vecchie etichette).
Per aggiungere una sessione: nuova cartella con questi file; il codice non cambia.

## Moduli

| File | Ruolo |
|---|---|
| `formato_swr.py` | decodifica `.swr` (delta int8, escape 0x80), correzione della rotazione ciclica dei canali FIFO (Viterbi per segmenti), fs dai timestamp |
| `dataset.py` | caricatore unico (dati a fs costante, riferimento, mappatura video->dati), cache |
| `streaming.py` | `Rilevatore` (interfaccia a campione singolo), `simula` (con consegna a blocchi), `verifica_causalita` (rilancio su dati troncati) |
| `valutazione.py` | abbinamento uno-a-uno con tolleranza, precisione/richiamo/FP, errore di tempo (media, dev.std, mediana, % entro 0,1/0,2/0,3 s), ritardo di notifica di A |
| `validazione.py` | struttura "una sessione esclusa" (`loso`) e divisione temporale (`meta_temporale`) |
| `rilevatori_orig.py` | porting in streaming dei rilevatori di `detect.py` (non ritarati), assi anatomici fissi o online |
| `stima_k.py` | stima di k (urti, inizio/fine gruppi di bracciate), verifica della fine del video |
| `frequenza.py` | ricampionamento con anti-aliasing e misura della compressione del firmware |
| `rapporto.py` | scrive il rapporto Markdown |

## Aggiungere un rilevatore

Sottoclasse di `streaming.Rilevatore` con `inizia(fs)`, `push(t, a, g) -> [Evento]`, `fine()`; poi si valuta con
`simula(...)` e `valutazione.valuta(...)`. Per A il simulatore fissa `t_notifica` (istante dell'ultimo campione
consegnato) e `verifica_causalita` rilancia su dati troncati.
