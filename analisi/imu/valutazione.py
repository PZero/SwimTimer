"""Valutazione dei rilevatori contro il riferimento.

Per ogni tipo (A, P, V): abbinamento uno-a-uno evento-riferimento entro una tolleranza
(algoritmo ungherese sul valore assoluto dell'errore di tempo), poi
  - TP, FP, FN, precisione, richiamo, F1;
  - errore di tempo e = t_rilevato - t_riferimento sui TP: media, dev. std, mediana,
    MAE, percentuale di TP entro 0,1 / 0,2 / 0,3 s (e sul totale dei riferimenti);
  - per A anche il ritardo di notifica rispetto al tocco di riferimento
    (t_notifica - t_rif) e la quota notificata entro 2 s.
Solo la finestra in cui il riferimento e' completo conta (fuori: ne' FP ne' FN).
"""
import numpy as np
from scipy.optimize import linear_sum_assignment

TOLLERANZE_DEFAULT = {'A': 1.5, 'P': 1.5, 'V': 1.5}


def abbina(t_rif, t_det, tol):
    """Ritorna lista di coppie (i_rif, i_det) con |dt| <= tol, uno-a-uno, minimizzando la somma di |dt|."""
    if len(t_rif) == 0 or len(t_det) == 0:
        return []
    d = np.abs(np.subtract.outer(np.asarray(t_rif), np.asarray(t_det)))
    big = 1e6
    c = np.where(d <= tol, d, big)
    r, k = linear_sum_assignment(c)
    return [(int(i), int(j)) for i, j in zip(r, k) if c[i, j] < big]


def _stat(e):
    e = np.asarray(e, float)
    if len(e) == 0:
        return dict(media=np.nan, std=np.nan, mediana=np.nan, mae=np.nan, p90=np.nan)
    return dict(media=float(e.mean()), std=float(e.std()), mediana=float(np.median(e)),
                mae=float(np.abs(e).mean()), p90=float(np.percentile(np.abs(e), 90)))


def metriche_tipo(rif, eventi, tipo, tol, finestra, solo_causali=False):
    """rif: [(t,tipo)] di riferimento; eventi: lista di Evento; finestra=(a,b) s dati."""
    a, b = finestra
    tr = np.array([t for t, k in rif if k == tipo and a <= t <= b])
    ev = [e for e in eventi if e.tipo == tipo and a <= e.t_evento <= b]
    if solo_causali:
        ev = [e for e in ev if e.info.get('causale', True)]
    td = np.array([e.t_evento for e in ev])
    pairs = abbina(tr, td, tol)
    err = np.array([td[j] - tr[i] for i, j in pairs])
    tp = len(pairs)
    fp = len(td) - tp
    fn = len(tr) - tp
    prec = tp / len(td) if len(td) else float('nan')
    ric = tp / len(tr) if len(tr) else float('nan')
    f1 = 2 * prec * ric / (prec + ric) if (tp and prec + ric) else 0.0
    out = dict(tipo=tipo, n_rif=len(tr), n_det=len(td), tp=tp, fp=fp, fn=fn, precisione=prec,
               richiamo=ric, f1=f1, tol=tol, **_stat(err), errori=err.tolist())
    for s in (0.1, 0.2, 0.3):
        out[f'entro_{s}'] = float(np.mean(np.abs(err) <= s)) if tp else float('nan')
        out[f'entro_{s}_su_rif'] = float(np.sum(np.abs(err) <= s) / len(tr)) if len(tr) else float('nan')
    # stessa statistica dopo aver tolto lo scarto mediano (cosa si otterrebbe ritarando l'offset costante)
    ec = err - np.median(err) if tp else err
    for s in (0.1, 0.2, 0.3):
        out[f'entro_c_{s}'] = float(np.mean(np.abs(ec) <= s)) if tp else float('nan')
    if tipo == 'A':
        rit = np.array([ev[j].t_notifica - tr[i] for i, j in pairs])
        out['ritardo_notifica'] = _stat(rit) | dict(max=float(rit.max()) if tp else float('nan'),
                                                    entro_2s=float(np.mean(rit <= 2.0)) if tp else float('nan'))
        out['ritardo_proprio'] = _stat([ev[j].t_notifica - ev[j].t_evento for i, j in pairs])
    else:
        lat = np.array([ev[j].t_notifica - ev[j].t_evento for i, j in pairs])
        out['latenza'] = _stat(lat)
    out['coppie'] = [(float(tr[i]), float(td[j])) for i, j in pairs]
    out['mancati'] = [float(t) for k, t in enumerate(tr) if k not in {i for i, _ in pairs}]
    out['falsi'] = [float(t) for k, t in enumerate(td) if k not in {j for _, j in pairs}]
    return out


def valuta(sess, eventi, tol=None, finestra=None, tipi=('A', 'P', 'V'), solo_causali_A=True):
    tol = {**TOLLERANZE_DEFAULT, **(tol or {})}
    fin = finestra or sess.finestra_valida
    return {k: metriche_tipo(sess.eventi, eventi, k, tol[k], fin, solo_causali=(solo_causali_A and k == 'A'))
            for k in tipi}


def riga(m):
    """Riga di tabella markdown per un tipo."""
    f = lambda x: '-' if (x is None or (isinstance(x, float) and np.isnan(x))) else f'{x:.2f}'
    pc = lambda x: '-' if (isinstance(x, float) and np.isnan(x)) else f'{100 * x:.0f}%'
    return (f"| {m['tipo']} | {m['n_rif']} | {m['n_det']} | {m['tp']}/{m['fp']}/{m['fn']} | {pc(m['precisione'])} | "
            f"{pc(m['richiamo'])} | {f(m['media'])} | {f(m['std'])} | {f(m['mediana'])} | "
            f"{pc(m['entro_0.1'])}/{pc(m['entro_0.2'])}/{pc(m['entro_0.3'])} |")


INTESTAZIONE = ("| Tipo | Rif | Rilev. | TP/FP/FN | Prec. | Richiamo | Err. medio (s) | Dev.std (s) | Mediana (s) | "
                "TP entro 0,1/0,2/0,3 s |\n|---|---|---|---|---|---|---|---|---|---|")


def sotto_finestra(sess, a, b):
    """Finestra di valutazione ristretta (per la divisione temporale)."""
    fa, fb = sess.finestra_valida
    return (max(a, fa), min(b, fb))
