#!/usr/bin/env python3
"""Banco di prova (fase 2): rilevatori di eventi di nuoto dai dati IMU grezzi del tag.

Uso:
    python analisi\\imu\\valuta.py --sessioni <cartella con sottocartelle-sessione> [--uscite <cartella>]

Esegue per ogni sessione: caricamento (.swr -> dati a fs costante), stima di k (video->dati), verifica
della fine del video, rilevatori originali in streaming (assi fissi e assi online) a 214/104/52/26 Hz,
valutazione per tipo, test di causalita' di A, validazione a meta' temporale, esperimento di
compressione. Scrive SOLO in <uscite>: rapporto_fase2.md, risultati_<sessione>.json, cache/.
Dati e risultati contengono dati personali: <uscite> deve stare FUORI dal repository.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from dataset import carica_sessione, elenca_sessioni, video_a_dati  # noqa: E402
from frequenza import esperimento_compressione, ricampiona       # noqa: E402
from rilevatori_orig import RilevatoreOriginale, stima_assi_sessione  # noqa: E402
from stima_k import (stima_k, controlla_fine_video, bouts_bracciata)  # noqa: E402
from streaming import simula, verifica_causalita                 # noqa: E402
from validazione import meta_temporale                           # noqa: E402
from valutazione import valuta                                   # noqa: E402
import rapporto                                                  # noqa: E402


def _dentro_repo(percorso):
    radice = os.path.abspath(os.path.join(AQUI, '..', '..'))
    p = os.path.abspath(percorso)
    return os.path.commonpath([p, radice]) == radice


def _snello(m):
    """Toglie dalle metriche le liste lunghe non necessarie al JSON di riepilogo."""
    return {k: v for k, v in m.items() if k not in ('coppie',)}


def esegui_confronto(cartella, uscite, cache):
    """Sessione 'solo confronto' (vecchie etichette): verifica del porting a 214 Hz con le vecchie tolleranze."""
    s = carica_sessione(cartella, cache)
    F, U = stima_assi_sessione(s)
    ev, viol = simula(RilevatoreOriginale(assi=(F, U)), s.t, s.acc, s.gyro, s.fs)
    tol = s.meta.get('tolleranze', {'A': 2.5, 'P': 2.5, 'V': 3.0})
    return dict(nome=s.nome, tolleranze=tol, metriche=valuta(s, ev, tol=tol), n_eventi=len(ev))


def esegui_sessione(cartella, uscite, cache, opz):
    t_ini = time.time()
    s0 = carica_sessione(cartella, cache)
    R = dict(nome=s0.nome, fs=s0.fs, n_campioni=len(s0.t), durata_s=float(s0.t[-1]),
             sync_dati_s=s0.sync_dati_s, finestra_valida=s0.finestra_valida,
             n_rif={k: sum(1 for _, x in s0.eventi if x == k) for k in 'APV'},
             cambi_rotazione=s0.extra['cambi_rotazione'], blocchi=int(len(s0.extra['blocchi'])), meta=s0.meta)
    B = np.asarray(s0.extra['blocchi'], float)       # (indice_primo_campione, n_campioni, timestamp_ms)
    dev = np.diff(B[:, 2]) - B[:-1, 1] * 1000.0 / s0.fs
    R['continuita'] = dict(max_dev_ms=float(np.abs(dev).max()), n_blocchi_20ms=int((np.abs(dev) > 20).sum()),
                           n_blocchi=int(len(B)))
    # ---- k
    kres = None
    if str(opz.k).lower() == 'auto':
        kres = stima_k(s0)
        k = kres['k'] if kres['n_usate'] >= 5 else s0.k
    else:
        k = float(opz.k)
    R['k_meta'] = s0.k
    R['k'] = k
    R['k_stima'] = kres
    s = carica_sessione(cartella, cache, k=k)
    R['fine_video'] = controlla_fine_video(s, k)
    R['bouts'] = bouts_bracciata(s)
    # ---- assi anatomici (assi fissi = taratura "ottimistica" sull'intera sessione)
    F, U = stima_assi_sessione(s)
    R['assi_fissi'] = dict(F=F, U=U)
    freqs = [None] + [f for f in opz.frequenze if f < s.fs]
    R['freq'] = {}
    for f in freqs:
        sf = s if f is None else ricampiona(s, f)
        nome = f'{sf.fs:.0f}'
        r = dict(fs=sf.fs)
        for modo, assi in (('fisso', (F, U)), ('online', None)):
            fab = (lambda a=assi, m=modo: RilevatoreOriginale(assi=a, nome=f'orig_{m}'))
            ev, viol = simula(fab(), sf.t, sf.acc, sf.gyro, sf.fs)
            m = valuta(sf, ev, tol=opz.tol_dict)
            r[modo] = dict(metriche={k2: _snello(v) for k2, v in m.items()}, violazioni=len(viol), n_eventi=len(ev),
                           a_tardivi=sum(1 for e in ev if e.tipo == 'A' and not e.info.get('causale', True)),
                           latenza_decisione={tp: _lat(ev, tp) for tp in 'PV'})
            if modo == 'fisso' and not opz.salta_causalita:
                r[modo]['causalita_A'] = verifica_causalita(fab, sf.t, sf.acc, sf.gyro, sf.fs, tipi=('A',),
                                                            n_test=opz.n_causalita, eventi=ev)
            if modo == 'fisso' and f is None:
                r['eventi_fisso'] = [(e.tipo, e.t_evento, e.t_notifica) for e in ev]
        R['freq'][nome] = r
        print(f'  [{s.nome}] {nome} Hz fatto ({time.time() - t_ini:.0f} s)', flush=True)
    R['fine_video']['ipotesi_salto'] = _ipotesi_salto(s, k, R)
    # ---- sensibilita' a k (214 Hz, assi fissi)
    ev, _ = simula(RilevatoreOriginale(assi=(F, U)), s.t, s.acc, s.gyro, s.fs)
    sens = {}
    for kk in sorted({1.0, round(k, 4), 1.0024}):
        sk = carica_sessione(cartella, cache, k=kk)
        m = valuta(sk, ev, tol=opz.tol_dict)
        sens[f'{kk:.4f}'] = {t: dict(tp=m[t]['tp'], media=m[t]['media'], std=m[t]['std'],
                                    entro_0_3=m[t]['entro_0.3'], mediana=m[t]['mediana']) for t in 'APV'}
    R['sensibilita_k'] = sens
    # ---- validazione temporale
    R['meta_temporale'] = meta_temporale(s, tol=opz.tol_dict)
    # ---- compressione
    R['compressione'] = esperimento_compressione(s, finestra=tuple(s.meta.get('acqua_dati_s', [0, s.t[-1]])))
    R['tempo_calcolo_s'] = time.time() - t_ini
    return R


def _ipotesi_salto(s, k, R):
    """Ipotesi: dopo l'ultima P etichettata il video NON contiene la pausa che i dati mostrano.
    Stima lo scarto Delta tra l'ultima P (video) e la prima nuotata successiva nei dati
    (la prima bracciata cade ~0,2 s dopo lo stacco, come nelle altre P) e dove cadrebbe l'arrivo
    successivo rilevato nei dati."""
    sy = s.meta['sync']
    sv, sd = sy['video_s'], s.sync_dati_s
    P = [t for t, tp in s.eventi if tp == 'P']
    if not P:
        return None
    tpv = (P[-1] - sd) / s.k + sv
    pred = float(video_a_dati(tpv, sv, sd, k))
    nxt = [b for b in R['bouts'] if b[0] > pred + 2]
    if not nxt:
        return None
    S = nxt[0][0]
    evf = next((v['eventi_fisso'] for v in R['freq'].values() if 'eventi_fisso' in v), [])
    A = [e[1] for e in evf if e[0] == 'A' and e[1] > S]
    a = A[0] if A else None
    return dict(p_video_s=float(tpv), p_dati_predetto_s=pred, inizio_nuotata_dati_s=float(S),
                delta_s=float(S - 0.2 - pred), a_dati_s=a,
                a_video_ipotetico_s=float(tpv + (a - (S - 0.2))) if a else None,
                durata_video_s=s.meta.get('durata_video_s'))


def _lat(ev, tp):
    v = [e.t_notifica - e.t_evento for e in ev if e.tipo == tp]
    d = [e.info['t_decisione'] - e.t_evento for e in ev if e.tipo == tp and 't_decisione' in e.info]
    return dict(n=len(v), mediana=float(np.median(v)) if v else float('nan'), max=float(max(v)) if v else float('nan'),
                regola_mediana=float(np.median(d)) if d else float('nan'), regola_max=float(max(d)) if d else float('nan'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sessioni', required=True, help='cartella con sottocartelle-sessione (o una sessione)')
    ap.add_argument('--uscite', default=None, help='cartella di output (default: cartella madre di --sessioni)')
    ap.add_argument('--k', default='auto', help="scala video->dati: 'auto' (stima) oppure un numero")
    ap.add_argument('--frequenze', default='104,52,26', help='frequenze ricampionate (Hz), oltre alla nativa')
    ap.add_argument('--tol', type=float, default=1.5, help='tolleranza di abbinamento (s) per A, P, V')
    ap.add_argument('--salta-causalita', action='store_true', help='salta il test di causalita (lento)')
    ap.add_argument('--n-causalita', type=int, default=4, help='eventi A su cui rilanciare il test di causalita')
    ap.add_argument('--forza', action='store_true', help='consente un output dentro il repository (sconsigliato)')
    a = ap.parse_args(argv)
    sess_dir = os.path.abspath(a.sessioni)
    uscite = os.path.abspath(a.uscite) if a.uscite else os.path.dirname(sess_dir.rstrip('\\/'))
    if _dentro_repo(uscite) and not a.forza:
        sys.exit(f'RIFIUTO: {uscite} e\' dentro il repository (i risultati contengono dati personali). Usa --uscite altrove.')
    os.makedirs(uscite, exist_ok=True)
    cache = os.path.join(uscite, 'cache')
    a.frequenze = [float(x) for x in a.frequenze.split(',') if x]
    a.tol_dict = {'A': a.tol, 'P': a.tol, 'V': a.tol}
    cart = elenca_sessioni(sess_dir)
    if not cart:
        sys.exit('nessuna sessione (sessione.json) trovata')
    principali, confronti = [], []
    for c in cart:
        with open(os.path.join(c, 'sessione.json'), encoding='utf-8-sig') as f:
            (confronti if json.load(f).get('solo_confronto') else principali).append(c)
    print(f'Sessioni: {len(principali)} principali, {len(confronti)} di confronto. Uscite: {uscite}')
    risultati = []
    for c in principali:
        print('Sessione', c, flush=True)
        R = esegui_sessione(c, uscite, cache, a)
        with open(os.path.join(uscite, f"risultati_{R['nome']}.json"), 'w', encoding='utf-8') as f:
            json.dump(R, f, ensure_ascii=False, indent=1, default=float)
        risultati.append(R)
    conf = [esegui_confronto(c, uscite, cache) for c in confronti]
    rapporto.scrivi(os.path.join(uscite, 'rapporto_fase2.md'), risultati, conf, a)
    print('Rapporto:', os.path.join(uscite, 'rapporto_fase2.md'))


if __name__ == '__main__':
    main()
