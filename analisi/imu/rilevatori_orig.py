"""Porting in STREAMING dei rilevatori originali (analisi_nuoto_codice/detect.py, test.md §4.4).

NON ritarati: soglie e offset sono quelli della vecchia analisi (A: +0,23 s; P: -0,66 s;
V: +1,4 s e -3,0 s; faceUp>0,8 per 0,3 s; headUp<-0,6; ecc.). Cambia solo la struttura:
un campione alla volta, nessun campione futuro. Le regole che nel codice originale usavano
filtri centrati / non causali o liste di eventi globali sono ora decisioni DIFFERITE:
si decide quando sono disponibili i campioni (e gli altri eventi) necessari, e il ritardo
di notifica e' misurato dal simulatore.

Ritardi di decisione (parametri RIT_*): sono la finestra "futura" strettamente necessaria
alla regola originale (+ margine):
    P regola 1  : 1,0 s di quiete + 0,3 s (filtro centrato)
    P regola 2  : 7,5 s  (serve sapere se c'e' una P di regola 1 entro 6 s dopo)
    V regola 1  : 11 s   (nessuna P entro 3 s, compresa regola 2)
    V regola 2  : 22 s   (nessuna capriola entro 10 s dopo)
    finalizzazione (post-elaborazione V->A e dedup P/V entro 2 s): evento + 50 s

Assi anatomici (viso F, sommita' U): servono a faceUp/headUp. Due modalita':
  - 'fisso'  : (F, U) dati dall'esterno, come farebbe la calibrazione a 3 pose all'inizio
               della sessione. ATTENZIONE: nella valutazione sono stimati sull'INTERA sessione
               (e il verso di U con le etichette A, come nella vecchia analisi): e' un
               limite superiore OTTIMISTICO, non un risultato causale.
  - 'online' : stima causale con statistiche cumulative (media della gravita' durante la
               bracciata -> F; PCA nel piano ortogonale -> U; verso di U dalle ultime
               rotazioni dopo gli arrivi RILEVATI). A parte il tempo di "riscaldamento"
               e' realizzabile in firmware.
"""
import heapq
import math

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

from streaming import Evento, Rilevatore

PAR = dict(
    soglia_nuotata=130.0,      # dps, RMS di |w| su 1 s
    soglia_quiete=60.0,        # dps, media di |w| su 0,6 s (centrata)
    faceup_arrivo=0.8, durata_faceup=0.3, nuotata_min_10s=3.0, pausa_arrivi=15.0, off_arrivo=0.23,
    p1_min_dopo_A=2.0, p1_max_dopo_A=12.0, p1_quiete_min=1.0, off_p1=0.66,
    p2_fermo=20.0, p2_impulso=0.7,
    headdown=-0.6, v1_durata_min=0.2, v1_faceup_max=0.5, v1_off=1.4,
    v2_quiete_min=1.5, v2_rot=150.0, v2_off=3.0,
    rit_p2=7.5, rit_v1=11.0, rit_v2=22.0, rit_fin=50.0,
)


class Mahony:
    """Filtro di Mahony (come quat.py): up = 'alto' del mondo visto dal sensore."""

    def __init__(self, fs, kp_ok=1.0, kp_dyn=0.1, ki=0.01, n_init=50):
        self.dt = 1.0 / fs
        self.kp_ok, self.kp_dyn, self.ki, self.n_init = kp_ok, kp_dyn, ki, n_init
        self.buf = []
        self.q = None
        self.ei = [0.0, 0.0, 0.0]

    def _step(self, a, g):
        w, x, y, z = self.q
        vx = 2 * (x * z - w * y)
        vy = 2 * (w * x + y * z)
        vz = w * w - x * x - y * y + z * z
        an = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
        d = an if an > 1e-6 else 1e-6
        ax, ay, az = a[0] / d, a[1] / d, a[2] / d
        ex = ay * vz - az * vy
        ey = az * vx - ax * vz
        ez = ax * vy - ay * vx
        kp = self.kp_ok if abs(an - 1.0) < 0.1 else self.kp_dyn
        dt = self.dt
        ei = self.ei
        ei[0] += self.ki * ex * dt
        ei[1] += self.ki * ey * dt
        ei[2] += self.ki * ez * dt
        r = math.pi / 180.0
        ox = g[0] * r + kp * ex + ei[0]
        oy = g[1] * r + kp * ey + ei[1]
        oz = g[2] * r + kp * ez + ei[2]
        h = 0.5 * dt
        nw = w + h * (-(x * ox + y * oy + z * oz))
        nx = x + h * (w * ox + y * oz - z * oy)
        ny = y + h * (w * oy - x * oz + z * ox)
        nz = z + h * (w * oz + x * oy - y * ox)
        n = math.sqrt(nw * nw + nx * nx + ny * ny + nz * nz)
        self.q = (nw / n, nx / n, ny / n, nz / n)

    def update(self, a, g):
        """Restituisce up (3 float) oppure None durante l'inizializzazione (primi n_init campioni)."""
        if self.q is None:
            self.buf.append((a, g))
            if len(self.buf) < self.n_init:
                return None
            m = [sum(b[0][k] for b in self.buf) / len(self.buf) for k in range(3)]
            nm = math.sqrt(sum(v * v for v in m)) or 1.0
            a0 = [v / nm for v in m]
            ax = (a0[1] * 1.0 - a0[2] * 0.0, a0[2] * 0.0 - a0[0] * 1.0, 0.0)   # a0 x z
            s = math.sqrt(ax[0] ** 2 + ax[1] ** 2 + ax[2] ** 2)
            c = a0[2]
            if s > 1e-6:
                ang = math.atan2(s, c)
                sn = math.sin(ang / 2) / s
                self.q = (math.cos(ang / 2), ax[0] * sn, ax[1] * sn, ax[2] * sn)
            else:
                self.q = (1.0, 0.0, 0.0, 0.0)
            for b in self.buf:
                self._step(b[0], b[1])
            self.buf = []
        else:
            self._step(a, g)
        w, x, y, z = self.q
        return (2 * (x * z - w * y), 2 * (w * x + y * z), w * w - x * x - y * y + z * z)


def mahony_up(acc, gyro, fs):
    """Batch: serie di 'up' (N,3) con lo stesso filtro (primi 50 campioni = (0,0,1))."""
    m = Mahony(fs)
    out = np.zeros((len(acc), 3))
    out[:, 2] = 1.0
    al, gl = acc.tolist(), gyro.tolist()
    for i in range(len(al)):
        u = m.update(al[i], gl[i])
        if u is not None:
            out[i] = u
    return out


def stima_assi_sessione(sess, etichette_A=None, finestra_acqua=None):
    """Assi anatomici come in frame2.py, stimati sull'INTERA sessione (ottimistico).
    Ritorna (F, U) come tuple. Il verso di U usa gli arrivi di riferimento (taratura sulle etichette)."""
    t, acc, gyr, fs = sess.t, sess.acc, sess.gyro, sess.fs
    up = mahony_up(acc, gyr, fs)
    gn = np.linalg.norm(gyr, axis=1)
    k = int(fs * 1.0)
    cg = np.concatenate([[0], np.cumsum(gn ** 2)])
    i = np.arange(len(gn))
    rms = np.sqrt((cg[i + 1] - cg[np.maximum(0, i + 1 - k)]) / k)
    a0, a1 = finestra_acqua or sess.meta.get('acqua_dati_s', [0, t[-1]])
    sw = (rms > PAR['soglia_nuotata']) & (t > a0) & (t < a1)
    f = up[sw].mean(0)
    f /= np.linalg.norm(f)
    P = up[sw] - np.outer(up[sw] @ f, f)
    C = P.T @ P
    _, V = np.linalg.eigh(C)
    cand = [V[:, j] for j in range(3) if abs(V[:, j] @ f) < 0.5]
    var = [np.var(up[sw] @ c) for c in cand]
    U = cand[int(np.argmin(var))]
    if etichette_A is None:
        etichette_A = [te for te, tp in sess.eventi if tp == 'A']
    sc = np.mean([(up[(t > a) & (t < a + 2.5)] @ U).mean() for a in etichette_A
                  if np.any((t > a) & (t < a + 2.5))])
    if sc < 0:
        U = -U
    return tuple((-f).tolist()), tuple(U.tolist())


class AssiOnline:
    """Stima causale di (F, U) con statistiche cumulative sui campioni di nuotata."""

    def __init__(self, fs, min_nuotata_s=20.0, aggiorna_s=1.0):
        self.n = 0
        self.s = np.zeros(3)
        self.c = np.zeros((3, 3))
        self.minN = min_nuotata_s * fs
        self.per = max(1, int(fs * aggiorna_s))
        self.cont = 0
        self.F = None
        self.U = None
        self.arr = []          # medie di 'up' dopo arrivi rilevati
        self._f = None
        self._Ucand = None

    def campione(self, up, nuotata):
        if nuotata:
            self.n += 1
            u = np.array(up)
            self.s += u
            self.c += np.outer(u, u)
        self.cont += 1
        if self.cont % self.per == 0 and self.n >= self.minN:
            self._ricalcola()

    def _ricalcola(self):
        m = self.s / self.n
        f = m / np.linalg.norm(m)
        Pm = np.eye(3) - np.outer(f, f)
        C = Pm @ self.c @ Pm
        _, V = np.linalg.eigh(C)
        cov = self.c / self.n - np.outer(m, m)
        cand = [V[:, j] for j in range(3) if abs(V[:, j] @ f) < 0.5]
        if not cand:
            return
        var = [c @ cov @ c for c in cand]
        U = cand[int(np.argmin(var))]
        self.F = tuple((-f).tolist())
        if self.arr:
            sa = np.mean(self.arr, axis=0)
            if sa @ U < 0:
                U = -U
            self.U = tuple(U.tolist())
        else:
            self.U = None
        self._Ucand = U

    def aggiungi_arrivo(self, media_up):
        self.arr.append(np.array(media_up))


class RilevatoreOriginale(Rilevatore):
    """Rileva A (causale), P e V (differiti) con le regole di detect.py."""

    def __init__(self, assi=None, par=None, nome='orig_fisso'):
        """assi = (F, U) per la modalita' 'fisso'; None = stima 'online'."""
        self.nome = nome
        self.par = dict(PAR)
        if par:
            self.par.update(par)
        self.assi_fissi = assi

    # ------------------------------------------------------------------ stato
    def inizia(self, fs):
        p = self.par
        self.fs = fs
        self.dt = 1.0 / fs
        self.n = 0
        self.mah = Mahony(fs)
        self.k1 = int(fs * 1.0)
        self.L10 = int(fs * 10)
        self.W12 = int(fs * 1.2)
        self.Sq = int(fs * 0.6)          # finestra quiete (centrata)
        self.S1 = int(fs * 1.0)          # finestra 1 s (centrata)
        self.need = int(fs * p['durata_faceup'])
        self.fsi = int(fs)
        self.tl = []
        self.gn = []
        self.cg2 = [0.0]
        self.cgn = [0.0]
        self.csw = [0]
        self.cgx = [0.0]
        self.cgy = [0.0]
        self.cgz = [0.0]
        self.fu = []
        self.hu = []
        self.rotn = []
        self.lin = []
        self.up = []
        self.F = self.assi_fissi[0] if self.assi_fissi else None
        self.U = self.assi_fissi[1] if self.assi_fissi else None
        self.online = None if self.assi_fissi else AssiOnline(fs)
        self.cnt = 0
        self.last_A = -1e9
        self.Alist = []
        self.pendA = []          # arrivi in attesa di una P di regola 1
        self.Ptimes = []
        self.flips = []
        self.cands = []          # candidati P/V non ancora finalizzati
        self.kept = []           # P/V finali (tempo) per il dedup
        self.big = []            # (t, tipo) di tutti A/P/V candidati (pre-relabel)
        self.q_prev = False
        self.seg_s = None
        self.seg_flag1 = False
        self.seg_flag15 = False
        self.dn_prev = False
        self.dn_s = None
        self.heap = []
        self.seq = 0
        self.arr_pend = []       # per la stima online del verso di U
        self.nuotata_s = 0.0
        lp = butter(2, 4 / (fs / 2))
        self.lp_b, self.lp_a = lp

    # ---------------------------------------------------------------- utilita'
    def _sched(self, due, tipo, payload):
        self.seq += 1
        heapq.heappush(self.heap, (due, self.seq, tipo, payload))

    def _idx_t(self, a, b):
        """Indici i con a < t[i] < b (estremi esclusi), con i dati disponibili."""
        tl = self.tl
        lo = max(0, int(math.floor((a - tl[0]) * self.fs)) - 1)
        hi = min(len(tl), int(math.ceil((b - tl[0]) * self.fs)) + 2)
        r = [i for i in range(lo, hi) if a < tl[i] < b]
        return r

    # --------------------------------------------------------------- campione
    def push(self, t, a, g):
        p = self.par
        i = self.n
        self.n += 1
        out = []
        self.tl.append(t)
        gx, gy, gz = g
        gn = math.sqrt(gx * gx + gy * gy + gz * gz)
        self.gn.append(gn)
        self.cg2.append(self.cg2[-1] + gn * gn)
        self.cgn.append(self.cgn[-1] + gn)
        self.cgx.append(self.cgx[-1] + gx)
        self.cgy.append(self.cgy[-1] + gy)
        self.cgz.append(self.cgz[-1] + gz)
        k = self.k1
        rms = math.sqrt((self.cg2[i + 1] - self.cg2[max(0, i + 1 - k)]) / k)
        sw = rms > p['soglia_nuotata']
        self.csw.append(self.csw[-1] + (1 if sw else 0))
        swhist = self.csw[i + 1] - self.csw[max(0, i + 1 - self.L10)]
        up = self.mah.update(a, g)
        if up is None:
            up = (0.0, 0.0, 1.0)
        if self.online is not None:
            self.online.campione(up, sw)
            if self.online.F is not None:
                self.F = self.online.F
            self.U = self.online.U
        self.up.append(up)
        F, U = self.F, self.U
        fu = up[0] * F[0] + up[1] * F[1] + up[2] * F[2] if F is not None else -1.0
        hu = up[0] * U[0] + up[1] * U[1] + up[2] * U[2] if U is not None else 0.0
        self.fu.append(fu)
        self.hu.append(hu)
        self.lin.append((a[0] - up[0], a[1] - up[1], a[2] - up[2]))
        W = self.W12
        if i >= W:
            d = math.sqrt(((self.cgx[i + 1] - self.cgx[i + 1 - W]) / self.fs) ** 2 +
                          ((self.cgy[i + 1] - self.cgy[i + 1 - W]) / self.fs) ** 2 +
                          ((self.cgz[i + 1] - self.cgz[i + 1 - W]) / self.fs) ** 2)
        else:
            d = 0.0
        self.rotn.append(d)

        # ---- A (causale)
        if F is not None and self.n > 100:
            self.cnt = self.cnt + 1 if fu > p['faceup_arrivo'] else 0
            if (self.cnt == self.need and t - self.last_A > p['pausa_arrivi']
                    and swhist > self.fs * p['nuotata_min_10s']):
                t_on = self.tl[max(0, i - self.need)] + p['off_arrivo']
                self.last_A = t
                self.Alist.append(t_on)
                self.pendA.append(t_on)
                self.big.append((t_on, 'A'))
                self.arr_pend.append(t_on)
                out.append(Evento('A', t_on, info=dict(faceUp=fu, causale=True)))
        # media 'up' dopo l'arrivo (per il verso di U online): 2,5 s dopo l'evento
        if self.online is not None and self.arr_pend and t >= self.arr_pend[0] + 2.5:
            ta = self.arr_pend.pop(0)
            ii = self._idx_t(ta, ta + 2.5)
            if ii:
                m = np.mean([self.up[j] for j in ii], axis=0)
                self.online.aggiungi_arrivo(m)

        # ---- quiete centrata (0,6 s): q[j] con j = i - (Sq-1)//2
        S = self.Sq
        hq = (S - 1) // 2
        j = i - hq
        if j - S // 2 >= 0:
            qj = (self.cgn[i + 1] - self.cgn[i + 1 - S]) / S < p['soglia_quiete']
            if qj and not self.q_prev:
                self.seg_s = j - 1
                self.seg_flag1 = False
                self.seg_flag15 = False
            if qj and self.seg_s is not None:
                dur = (j - self.seg_s) * self.dt
                if dur >= p['p1_quiete_min'] and not self.seg_flag1:
                    self.seg_flag1 = True
                    self._p1(self.seg_s, t, out)
                if dur >= p['v2_quiete_min'] and not self.seg_flag15:
                    self.seg_flag15 = True
                    self._sched(self.tl[self.seg_s] + p['rit_v2'], 'V2', self.seg_s)
            if not qj:
                self.seg_s = None
            self.q_prev = qj

        # ---- testa in giu' (headUp < -0.6): transizioni
        if U is not None:
            dn = hu < p['headdown']
            if dn and not self.dn_prev:
                self.dn_s = i - 1
                self._sched(self.tl[max(0, i - 1)] + p['rit_p2'], 'P2', self.dn_s)
            if not dn and self.dn_prev and self.dn_s is not None:
                s, e = self.dn_s, i - 1
                if (e - s) * self.dt >= p['v1_durata_min']:
                    due = max(self.tl[max(0, s)] + p['rit_v1'], t + 1.2)
                    self._sched(due, 'V1', (s, e))
                self.dn_s = None
            self.dn_prev = dn

        # ---- scadenze
        h = self.heap
        while h and h[0][0] <= t:
            _, _, tipo, pl = heapq.heappop(h)
            self._esegui(tipo, pl, out)
        return out

    def fine(self):
        out = []
        while self.heap:
            _, _, tipo, pl = heapq.heappop(self.heap)
            self._esegui(tipo, pl, out)
        return out

    # ------------------------------------------------------------------ regole
    def _p1(self, s, t_now, out):
        """Segmento di quiete qualificato (>= 1 s) che inizia in s: P di regola 1."""
        p = self.par
        ts = self.tl[s]
        rest = []
        for at in self.pendA:
            if t_now - at > p['p1_max_dopo_A'] + 2.0:
                continue
            if at + p['p1_min_dopo_A'] < ts < at + p['p1_max_dopo_A']:
                self.Ptimes.append(ts)
                self._cand('P', ts - p['off_p1'], ts, ts, 'prima scivolata dopo arrivo', t_now)
            else:
                rest.append(at)
        self.pendA = rest

    def _cand(self, k, t_ev, det, anchor, why, tdec):
        c = dict(k=k, t=t_ev, t0=t_ev, det=det, anchor=anchor, why=why, tdec=tdec)
        self.cands.append(c)
        self.big.append((t_ev, k))
        self._sched(max(tdec, t_ev + self.par['rit_fin']), 'FIN', c)

    def _esegui(self, tipo, pl, out):
        p = self.par
        tl = self.tl
        if tipo == 'P2':
            s = pl
            ts = tl[s]
            fi = self.fsi
            if max(self.fu[max(0, s - fi):s + fi]) > p['v1_faceup_max']:
                return
            if any(abs(ts - pt) < 6 for pt in self.Ptimes):
                return
            ii = self._idx_t(ts - 3, ts - 0.2)
            if not ii:
                return
            S1 = self.S1
            lo, hi = S1 // 2, (S1 - 1) // 2
            wmin = min((self.cgn[min(j + hi + 1, len(self.cgn) - 1)] - self.cgn[max(0, j - lo)]) / S1 for j in ii)
            if wmin >= p['p2_fermo']:
                return
            a0 = max(0, s - int(1.5 * self.fs))
            a1 = min(len(tl), s + int(4.0 * self.fs))
            L = np.array(self.lin[a0:a1])
            Lf = filtfilt(self.lp_b, self.lp_a, L, axis=0)
            al = np.linalg.norm(Lf, axis=1)
            tt = np.array(tl[a0:a1])
            m2 = np.nonzero((tt > ts) & (tt < ts + 1.2))[0]
            if len(m2) < 3:
                return
            pk, _ = find_peaks(al[m2], height=p['p2_impulso'])
            if not len(pk):
                return
            ti = float(tt[m2[pk[0]]])
            self.Ptimes.append(ti)
            self._cand('P', ti, ti, ti, 'partenza da fermo: immersione + spinta', ts + p['rit_p2'])
        elif tipo == 'V1':
            s, e = pl
            ts, te = tl[s], tl[e]
            fi = self.fsi
            if max(self.fu[max(0, s - fi):e + fi]) > p['v1_faceup_max']:
                return
            if any(abs(ts - at) < 4 for at in self.Alist):
                return
            if any(abs(ts - pt) < 3 for pt in self.Ptimes):
                return
            self.flips.append(ts)
            self._cand('V', ts + p['v1_off'], te, ts, 'capriola: testa verso il fondo', max(ts + p['rit_v1'], te + 1.2))
        elif tipo == 'V2':
            s = pl
            ts = tl[s]
            if any(abs(ts - pt) < 2.5 for pt in self.Ptimes):
                return
            if any(0 < ts - at < 12 for at in self.Alist):
                return
            if any(-10 < ts - ft < 8 for ft in self.flips):
                return
            ii = self._idx_t(ts - 3.5, ts + 0.5)
            if not ii:
                return
            r = np.array([self.rotn[j] for j in ii])
            if r.max() < p['v2_rot']:
                return
            tr = tl[ii[int(np.argmax(r))]]
            self._cand('V', tr - p['v2_off'], ts, tr, 'rotazione + scivolata (capriola non visibile)', ts + p['rit_v2'])
        elif tipo == 'FIN':
            c = pl
            if c['k'] == 'V':
                succ = [(tt, kk) for tt, kk in self.big if tt > c['t0']]
                if succ:
                    tt, kk = min(succ)
                    if kk == 'P' and tt - c['t0'] < 20:
                        out.append(Evento('A', c['anchor'], info=dict(causale=False, origine='virata seguita da partenza',
                                                                       why=c['why'])))
                        return
            if any(abs(y - c['t0']) < 2 for y in self.kept):
                return
            self.kept.append(c['t0'])
            out.append(Evento(c['k'], c['t0'], info=dict(t_decisione=c['tdec'], why=c['why'], det=c['det'])))
