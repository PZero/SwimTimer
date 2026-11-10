"""Strutture di validazione: "una sessione esclusa" e divisione temporale.

`loso`: per ogni sessione di test, si calibra su TUTTE le altre e si valuta sulla sessione
esclusa. Con una sola sessione non e' applicabile (si usa `meta_temporale`).
`meta_temporale`: prima meta' / seconda meta' della finestra con riferimento. La
calibrazione (assi anatomici (F,U) dei rilevatori "fissi": e' l'unica parte "appresa" dei
rilevatori originali, che non hanno soglie ritarate qui) e' fatta su una meta' e il rilevatore
gira sull'intero flusso (niente effetti di avvio) ma e' valutato solo sull'altra meta'.
E' una validazione DEBOLE: le due meta' sono la stessa seduta, stesso nuotatore e montaggio.
"""
import numpy as np

from rilevatori_orig import RilevatoreOriginale, stima_assi_sessione
from streaming import simula
from valutazione import metriche_tipo, TOLLERANZE_DEFAULT


def _pool(lista):
    """Unisce le metriche di piu' valutazioni (stesso tipo) sommando conteggi e riunendo gli errori."""
    tp = sum(m['tp'] for m in lista)
    fp = sum(m['fp'] for m in lista)
    fn = sum(m['fn'] for m in lista)
    e = np.array([x for m in lista for x in m['errori']])
    prec = tp / (tp + fp) if tp + fp else float('nan')
    ric = tp / (tp + fn) if tp + fn else float('nan')
    out = dict(tipo=lista[0]['tipo'], n_rif=tp + fn, n_det=tp + fp, tp=tp, fp=fp, fn=fn, precisione=prec,
               richiamo=ric, f1=(2 * prec * ric / (prec + ric)) if tp else 0.0,
               media=float(e.mean()) if len(e) else float('nan'), std=float(e.std()) if len(e) else float('nan'),
               mediana=float(np.median(e)) if len(e) else float('nan'))
    for s in (0.1, 0.2, 0.3):
        out[f'entro_{s}'] = float(np.mean(np.abs(e) <= s)) if len(e) else float('nan')
    out['errori'] = e.tolist()
    return out


def meta_temporale(sess, tol=None, tipi=('A', 'P', 'V')):
    """Calibra gli assi su una meta' e valuta sull'altra (due direzioni). Ritorna dict per tipo (pool)
    e i dettagli per direzione."""
    tol = {**TOLLERANZE_DEFAULT, **(tol or {})}
    a, b = sess.finestra_valida
    mid = 0.5 * (a + b)
    dett = {}
    per_tipo = {k: [] for k in tipi}
    for nome, (tr0, tr1), (te0, te1) in [('1a->2a meta', (a, mid), (mid, b)), ('2a->1a meta', (mid, b), (a, mid))]:
        etA = [t for t, k in sess.eventi if k == 'A' and tr0 <= t <= tr1]
        F, U = stima_assi_sessione(sess, etichette_A=etA, finestra_acqua=(max(tr0, sess.meta.get('acqua_dati_s', [0, 1e9])[0]),
                                                                          min(tr1, sess.meta.get('acqua_dati_s', [0, 1e9])[1])))
        ev, _ = simula(RilevatoreOriginale(assi=(F, U)), sess.t, sess.acc, sess.gyro, sess.fs)
        dett[nome] = {}
        for k in tipi:
            m = metriche_tipo(sess.eventi, ev, k, tol[k], (te0, te1), solo_causali=(k == 'A'))
            dett[nome][k] = m
            per_tipo[k].append(m)
    return dict(pool={k: _pool(v) for k, v in per_tipo.items()}, dettaglio=dett, meta=mid)


def loso(sessioni, fabbrica_da_calibrazione, calibra, tol=None, tipi=('A', 'P', 'V')):
    """Una sessione esclusa. `calibra(lista_sessioni_train)` -> parametri;
    `fabbrica_da_calibrazione(parametri)` -> rilevatore nuovo. Ritorna {nome_sessione: {tipo: metriche}}.
    Richiede >= 2 sessioni (altrimenti solleva ValueError)."""
    if len(sessioni) < 2:
        raise ValueError('loso richiede almeno 2 sessioni')
    tol = {**TOLLERANZE_DEFAULT, **(tol or {})}
    out = {}
    for i, test in enumerate(sessioni):
        train = [s for j, s in enumerate(sessioni) if j != i]
        par = calibra(train)
        ev, _ = simula(fabbrica_da_calibrazione(par), test.t, test.acc, test.gyro, test.fs)
        out[test.nome] = {k: metriche_tipo(test.eventi, ev, k, tol[k], test.finestra_valida, solo_causali=(k == 'A'))
                          for k in tipi}
    return out
