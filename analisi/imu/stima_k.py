"""Stima della scala k video->dati e verifica della fine del video.

Mappatura: t_dati = t_sync_dati + (t_video - t_sync_video) * k.

Metodo (dichiarato). Non si usano i rilevatori da valutare ne' le loro soglie: si usano due
caratteristiche IMU nette e semplici, definite qui:
  - "primo picco di bracciata dopo la P": primo picco del modulo del giroscopio (|w| con media
    mobile 0,3 s, altezza > 200 dps, distanza minima 0,5 s) entro [-0,5, +8] s dal riferimento P.
    Quando la nuotata parte subito cade a ~+0,2 s dallo stacco;
  - "ultimo picco di bracciata prima della A": ultimo picco analogo in [-6, +1,5] s dal tocco.
Ogni gruppo (P, A) ha una propria intercetta (scarto costante: non usata altrove). Si risolve ai
minimi quadrati   t_feat - t_rif(k=1) = c_gruppo + (k-1)*x,   x = t_video - t_sync_video,
con taglio iterativo dei residui oltre 0,5 s: dopo alcune P la nuotata parte con 4-6 s di
scivolata/pausa (la caratteristica non vale) e dopo alcune A l'ultima bracciata e' lontana dal
tocco. Incertezza: bootstrap sulle coppie (2000 ricampionamenti, 95%). Controllo incrociato:
scansione di k che minimizza lo scarto quadratico troncato (0,5 s) dopo aver tolto la mediana
di ogni gruppo. Il fit usa solo eventi con t_video < `fine_video_fit` (500 s): oltre c'e'
l'anomalia descritta in `controlla_fine_video`.
"""
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks

from dataset import video_a_dati


def picchi_bracciata(sess, soglia=200.0, liscia_s=0.3, dist_s=0.5):
    gn = np.linalg.norm(sess.gyro, axis=1)
    w = uniform_filter1d(gn, max(1, int(sess.fs * liscia_s)))
    pk, _ = find_peaks(w, height=soglia, distance=int(dist_s * sess.fs))
    return sess.t[pk]


def _costo_scan(x, y, gid, ng, ks, tau=0.4, cgrid=None):
    """Per ogni k: somma sui gruppi del minimo su c di sum(min((e-c)^2, tau^2)), e = y - (k-1)x.
    Stimatore robusto (M-stima troncata) a intercetta libera per gruppo. Ritorna (costi, c_opt)."""
    cgrid = np.arange(-3.0, 3.0001, 0.02) if cgrid is None else cgrid
    costi = np.zeros(len(ks))
    copt = np.zeros((len(ks), ng))
    for a, k in enumerate(ks):
        e = y - (k - 1.0) * x
        for g in range(ng):
            m = gid == g
            if not m.any():
                continue
            d = e[m][:, None] - cgrid[None, :]
            cc = np.minimum(d * d, tau * tau).sum(0)
            j = int(np.argmin(cc))
            costi[a] += cc[j]
            copt[a, g] = cgrid[j]
    return costi, copt


def _stima(x, y, gid, ng, tau=0.4):
    ks = np.arange(0.990, 1.0141, 0.0001)
    costi, copt = _costo_scan(x, y, gid, ng, ks, tau)
    kb = float(ks[np.nonzero(costi <= costi.min() + 1e-9)[0]].mean())
    j = int(np.argmin(np.abs(ks - kb)))
    inl = np.ones(len(x), bool)
    for g in range(ng):
        m = gid == g
        inl[m] = np.abs(y[m] - (kb - 1.0) * x[m] - copt[j, g]) < tau
    # rifinitura ai minimi quadrati sugli inlier (intercette di gruppo, pendenza comune)
    num = den = 0.0
    for g in range(ng):
        m = inl & (gid == g)
        if m.sum() >= 2:
            xg, yg = x[m].mean(), y[m].mean()
            num += ((x[m] - xg) * (y[m] - yg)).sum()
            den += ((x[m] - xg) ** 2).sum()
    k_ls = 1.0 + num / den if den > 1e-9 else kb
    return kb, k_ls, inl, copt[j]


def bouts_bracciata(sess, gap_s=2.0, min_picchi=3, **kw):
    """Gruppi di picchi di bracciata separati da meno di gap_s: lista di (t_primo_picco, t_ultimo_picco)."""
    pk = picchi_bracciata(sess, **kw)
    out, cur = [], [pk[0]] if len(pk) else []
    for p in pk[1:]:
        if p - cur[-1] > gap_s:
            if len(cur) >= min_picchi:
                out.append((float(cur[0]), float(cur[-1])))
            cur = [p]
        else:
            cur.append(p)
    if len(cur) >= min_picchi:
        out.append((float(cur[0]), float(cur[-1])))
    return out


def picchi_impatto(sess, soglia_g=8.0):
    """Picchi del modulo dell'accelerazione > soglia (urti: spinta dei piedi sul muro)."""
    an = np.linalg.norm(sess.acc, axis=1)
    p, _ = find_peaks(an, height=soglia_g, distance=int(0.3 * sess.fs))
    return sess.t[p], an[p]


def stima_k(sess, k_start=1.0, fine_video_fit=500.0, n_boot=300, seed=1, tipi=('P', 'A', 'I'), tau=0.4, tol_ass=3.0,
            finestra_impatto=(-1.5, 2.0)):
    """Stima k. Le caratteristiche sono intrinseche ai dati (inizio e fine dei gruppi di bracciate);
    ogni riferimento P (A) e' associato al piu' vicino inizio (fine) gruppo entro tol_ass s del
    tempo predetto; l'associazione e' ripetuta con il k stimato finche' converge."""
    sy = sess.meta['sync']
    sv, sd = sy['video_s'], sess.sync_dati_s
    bo = bouts_bracciata(sess)
    starts = np.array([b[0] for b in bo])
    ends = np.array([b[1] for b in bo])
    rif = [(tp, (t - sd) / sess.k + sv) for t, tp in sess.eventi]
    nomi = [t for t in ('P', 'A', 'I') if t in tipi]
    tp_imp, g_imp = picchi_impatto(sess)

    def coppie(k):
        X, Y, G, TV = [], [], [], []
        for tp, tv in rif:
            if tv > fine_video_fit:
                continue
            tr = float(video_a_dati(tv, sv, sd, k))
            voci = []
            if tp in nomi:
                cand = starts if tp == 'P' else ends
                j = int(np.argmin(np.abs(cand - tr)))
                if abs(cand[j] - tr) <= tol_ass:
                    voci.append((tp, cand[j]))
            if tp in ('P', 'V') and 'I' in nomi:
                m = (tp_imp > tr + finestra_impatto[0]) & (tp_imp < tr + finestra_impatto[1])
                if m.any():
                    voci.append(('I', tp_imp[m][int(np.argmax(g_imp[m]))]))
            for g, f in voci:
                X.append(tv - sv)
                Y.append(f - float(video_a_dati(tv, sv, sd, 1.0)))
                G.append(nomi.index(g))
                TV.append(tv)
        return tuple(map(np.array, (X, Y, G, TV)))

    k = k_start
    for _ in range(6):
        X, Y, G, TV = coppie(k)
        kb, k_ls, inl, c = _stima(X, Y, G, len(nomi), tau)
        if abs(k_ls - k) < 1e-5:
            break
        k = k_ls
    rng = np.random.default_rng(seed)
    bs = []
    idx = np.arange(len(X))
    for _ in range(n_boot):
        s = rng.choice(idx, len(idx))
        bs.append(_stima(X[s], Y[s], G[s], len(nomi), tau)[1])
    ci = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    res = Y - c[G] - (k_ls - 1.0) * X
    return dict(k=float(k_ls), k_scan=kb, ci95=ci, k_start=float(k_start), n_coppie=int(len(X)),
                n_usate=int(inl.sum()), std_residuo_s=float(res[inl].std()),
                intercette={nomi[g]: float(c[g]) for g in range(len(nomi)) if (G == g).any()},
                sync_dati_s=float(sd), tempi_video=TV.tolist(), residui=res.tolist(),
                gruppo=[nomi[g] for g in G], inlier=inl.tolist())

def tratti_nuotata(sess, soglia=130.0, unisci_s=4.0, min_s=4.0):
    """Tratti di nuotata: RMS di |w| su 1 s > soglia, uniti se separati < unisci_s, durata >= min_s."""
    gn = np.linalg.norm(sess.gyro, axis=1)
    k1 = int(sess.fs)
    cg = np.concatenate([[0], np.cumsum(gn ** 2)])
    i = np.arange(len(gn))
    rms = np.sqrt((cg[i + 1] - cg[np.maximum(0, i + 1 - k1)]) / k1)
    idx = np.nonzero(rms > soglia)[0]
    tratti = []
    if len(idx):
        s0 = p = idx[0]
        for j in idx[1:]:
            if sess.t[j] - sess.t[p] > unisci_s:
                if sess.t[p] - sess.t[s0] >= min_s:
                    tratti.append((float(sess.t[s0]), float(sess.t[p])))
                s0 = j
            p = j
        if sess.t[p] - sess.t[s0] >= min_s:
            tratti.append((float(sess.t[s0]), float(sess.t[p])))
    return tratti, rms


def controlla_fine_video(sess, k, da_video=470.0):
    """Verifica della fine del video. Per ogni riferimento dopo `da_video` s di video: RMS di |w| nei
    3 s prima e dopo il tempo dati predetto. Poi: tratti di nuotata nei dati (in tempo dati e
    in tempo video equivalente) e il piu' lungo tratto di quiete dopo l'ultimo evento etichettato."""
    sy = sess.meta['sync']
    sv, sd = sy['video_s'], sess.sync_dati_s
    gn = np.linalg.norm(sess.gyro, axis=1)

    def rms_fin(a, b):
        m = (sess.t >= a) & (sess.t < b)
        return float(np.sqrt(np.mean(gn[m] ** 2))) if m.any() else float('nan')

    righe = []
    for t, tp in sess.eventi:
        tv = (t - sd) / sess.k + sv
        if tv < da_video:
            continue
        tp_ = float(video_a_dati(tv, sv, sd, k))
        righe.append(dict(tipo=tp, t_video=float(tv), t_dati_pred=tp_,
                          rms_prima=rms_fin(tp_ - 3, tp_), rms_dopo=rms_fin(tp_, tp_ + 3)))
    tr, rms = tratti_nuotata(sess)
    a_v = lambda t: float((t - sd) / k + sv)
    tratti = [dict(t_dati=(a, b), t_video=(a_v(a), a_v(b))) for a, b in tr]
    ult = max((t for t, _ in sess.eventi), default=0.0)
    after = [x for x in tratti if x['t_dati'][1] > ult - 20]
    # quiete (RMS 1 s < 60) piu' lunga dopo l'ultimo evento
    q = rms < 60
    best = (0.0, 0.0, 0.0)
    i0 = int(np.searchsorted(sess.t, ult))
    j = i0
    n = len(q)
    while j < n:
        if q[j]:
            e = j
            while e < n and q[e]:
                e += 1
            d = sess.t[e - 1] - sess.t[j]
            if d > best[0]:
                best = (float(d), float(sess.t[j]), float(sess.t[e - 1]))
            j = e
        else:
            j += 1
    acc_q = sess.acc[(sess.t >= best[1]) & (sess.t <= best[2])].mean(0) if best[0] > 0 else np.zeros(3)
    nu = [x for x in tratti if x['t_dati'][1] < ult + 5]
    acc_n = np.zeros(3)
    if nu:
        a0, a1 = nu[-1]['t_dati']
        acc_n = sess.acc[(sess.t >= a0) & (sess.t <= a1)].mean(0)
    return dict(righe=righe, tratti_nuotata=tratti, tratti_dopo_ultimo_evento=after,
                acc_media_quiete=acc_q.tolist(), acc_media_ultimo_tratto=acc_n.tolist(),
                quiete_piu_lunga=dict(durata_s=best[0], da_dati_s=best[1], a_dati_s=best[2],
                                      da_video_s=a_v(best[1]), a_video_s=a_v(best[2])),
                ultimo_evento_dati_s=float(ult))


