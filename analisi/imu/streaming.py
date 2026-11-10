"""Simulatore di streaming per rilevatori di eventi dal tag.

Un rilevatore e' un oggetto con l'interfaccia di `Rilevatore`:
    inizia(fs)          prepara lo stato per una nuova sessione
    push(t, a, g)       riceve UN campione (t in s, a in g, g in dps) e restituisce
                        la lista (anche vuota) di `Evento` decisi con i soli dati <= t
    fine()              fine registrazione: eventuali decisioni rimaste in sospeso

Il simulatore passa solo valori (non array) e quindi il rilevatore non puo' "sbirciare"
il futuro; `t_notifica` e' fissato DAL SIMULATORE come istante dell'ultimo campione
consegnato quando l'evento esce (o dell'ultimo campione del blocco, se si consegna a
blocchi, come farebbe il firmware leggendo la FIFO). `t_evento` e' l'istante stimato
dell'evento e puo' essere datato all'indietro.

`verifica_causalita` fa il controllo meccanico: rilancia il rilevatore sui dati TRONCATI
a t_notifica e verifica che l'evento sia identico (se usasse campioni futuri consegnati
nel flusso, sparirebbe o cambierebbe). Limite: un rilevatore che leggesse il futuro da
una fonte esterna al flusso (array globali, file) non sarebbe visibile al test; per questo il
simulatore consegna solo valori. Si controllano anche gli eventi datati nel futuro
(t_evento > t_notifica) e quelli emessi solo a fine flusso (`info['da_fine']`).
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Evento:
    tipo: str                 # 'A' | 'P' | 'V'
    t_evento: float           # s (base tempi dei dati)
    t_notifica: float = None  # s, fissato dal simulatore
    info: dict = field(default_factory=dict)

    @property
    def ritardo(self):
        return self.t_notifica - self.t_evento


class Rilevatore:
    nome = 'base'

    def inizia(self, fs):
        raise NotImplementedError

    def push(self, t, a, g):
        raise NotImplementedError

    def fine(self):
        return []


def simula(rilevatore, t, acc, gyro, fs, blocco=1, fino_a=None):
    """Esegue il rilevatore in streaming. blocco = campioni per consegna (1 = campione a campione).
    fino_a = indice (escluso) oltre il quale non si consegnano campioni (test di causalita').
    Ritorna (eventi, violazioni): violazioni = eventi con t_evento > t_notifica."""
    n = len(t) if fino_a is None else fino_a
    rilevatore.inizia(fs)
    out = []
    tl = t.tolist()
    al = acc.tolist()
    gl = gyro.tolist()
    push = rilevatore.push
    i = 0
    while i < n:
        j = min(i + blocco, n)
        evs = []
        for k in range(i, j):
            r = push(tl[k], al[k], gl[k])
            if r:
                evs.extend(r)
        tn = tl[j - 1]
        for e in evs:
            e.t_notifica = tn
        out.extend(evs)
        i = j
    if n > 0:
        fin = rilevatore.fine() or []
        for e in fin:
            e.t_notifica = tl[n - 1]
            e.info['da_fine'] = True
        out.extend(fin)
    viol = [e for e in out if e.t_evento > e.t_notifica + 1e-9]
    return out, viol


def verifica_causalita(fabbrica, t, acc, gyro, fs, tipi=('A',), n_test=6, eventi=None):
    """Test meccanico di causalita' per gli eventi dei `tipi` indicati.
    fabbrica: funzione senza argomenti che crea un rilevatore nuovo.
    Per n_test eventi (equidistribuiti) rilancia su dati troncati a t_notifica e verifica
    che gli eventi dei `tipi` notificati fino a quel punto siano identici a quelli del run completo.
    Ritorna dict(ok, provati, falliti=[...])."""
    if eventi is None:
        eventi, _ = simula(fabbrica(), t, acc, gyro, fs)
    cand = [e for e in eventi if e.tipo in tipi and not e.info.get('da_fine')]
    if not cand:
        return dict(ok=True, provati=0, falliti=[])
    sel = np.linspace(0, len(cand) - 1, min(n_test, len(cand))).round().astype(int)
    falliti = []
    for s in sorted(set(sel.tolist())):
        e0 = cand[s]
        # indice dell'ultimo campione consegnato = primo con t >= t_notifica
        idx = int(np.searchsorted(t, e0.t_notifica - 1e-9)) + 1
        parz, _ = simula(fabbrica(), t, acc, gyro, fs, fino_a=idx)
        tn = t[idx - 1]
        ref = sorted((e.tipo, round(e.t_evento, 6)) for e in eventi
                     if e.tipo in tipi and e.t_notifica <= tn + 1e-9 and not e.info.get('da_fine'))
        got = sorted((e.tipo, round(e.t_evento, 6)) for e in parz
                     if e.tipo in tipi and not e.info.get('da_fine'))
        if ref != got:
            falliti.append(dict(t_notifica=float(e0.t_notifica), atteso=ref[-3:], ottenuto=got[-3:]))
    return dict(ok=not falliti, provati=len(set(sel.tolist())), falliti=falliti)
