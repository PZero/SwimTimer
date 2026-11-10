"""Test del banco di prova con SOLI dati sintetici (nessun dato personale).
Esecuzione:  python analisi\\imu\\test_banco.py   oppure   pytest analisi\\imu
"""
import os
import struct
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formato_swr import carica_swr                                        # noqa: E402
from frequenza import comprimi, ricampiona, quantizza                      # noqa: E402
from rilevatori_orig import RilevatoreOriginale                            # noqa: E402
from streaming import Evento, Rilevatore, simula, verifica_causalita       # noqa: E402
from valutazione import abbina, metriche_tipo                              # noqa: E402
import dataclasses                                                         # noqa: E402


def _scrivi_swr(percorso, S, dt_ms=4.672358517):
    """Codifica i campioni S (N,6 int) come il firmware (delta int8 / escape 0x80), 256 byte per blocco."""
    out = bytearray()
    hdr = bytearray(b'\xff' * 256)
    hdr[0:4] = bytes([0xA5, 1, 0, 0])
    struct.pack_into('<H', hdr, 18, 488)
    hdr[20] = 35
    out += hdr
    i, N, seq = 0, len(S), 0
    while i < N:
        blk = bytearray(b'\xff' * 256)
        blk[0] = 0xD1
        struct.pack_into('<HI', blk, 2, seq, int(round(i * dt_ms)))
        struct.pack_into('<6h', blk, 16, *[int(v) for v in S[i]])
        p, n, prev = 28, 1, S[i]
        i += 1
        while i < N:
            d = S[i] - prev
            if (d >= -128).all() and (d <= 127).all() and d[0] != -128:
                if p + 6 > 256:
                    break
                struct.pack_into('<6b', blk, p, *[int(v) for v in d]); p += 6
            else:
                if p + 13 > 256:
                    break
                blk[p] = 0x80
                struct.pack_into('<6h', blk, p + 1, *[int(v) for v in S[i]]); p += 13
            prev = S[i]
            i += 1
            n += 1
        blk[1] = n
        out += blk
        seq += 1
    foot = bytearray(b'\xff' * 256)
    foot[0] = 0xE0
    out += foot
    open(percorso, 'wb').write(bytes(out))


def _sintetico(N=6000, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(N) / 214.0
    acc = np.tile([0.1, 0.2, 0.97], (N, 1)) / 1.0
    acc = acc / np.linalg.norm(acc, axis=1, keepdims=True)
    acc += rng.normal(0, 0.01, acc.shape)
    gyro = rng.normal(0, 3, (N, 3)) + 40 * np.sin(2 * np.pi * 1.5 * t)[:, None]
    S = np.hstack([np.round(acc / 0.488e-3), np.round(gyro / 0.035)]).astype(int)
    return S


def test_decodifica_con_rotazione_canali():
    S = _sintetico()
    S2 = S.copy()
    S2[3000:] = np.roll(S[3000:], 2, axis=1)       # disallineamento ciclico FIFO dal campione 3000
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'x.swr')
        _scrivi_swr(p, S2)
        r = carica_swr(p)
    assert len(r['raw']) == len(S)
    assert r['cambi_rotazione'] >= 1
    err = np.abs(r['raw'].astype(int) - S).max()
    assert err == 0, f'decodifica/rotazione non esatta (max err {err} LSB)'
    assert abs(r['fs'] - 1000 / 4.672358517) < 0.5


def test_abbina_e_metriche():
    assert abbina([1.0, 5.0], [1.2, 9.0], 0.5) == [(0, 0)]
    ev = [Evento('P', 10.1, 12.0), Evento('P', 20.5, 21.0), Evento('P', 60.0, 61.0)]
    rif = [(10.0, 'P'), (20.0, 'P'), (30.0, 'P')]
    m = metriche_tipo(rif, ev, 'P', 1.0, (0, 50))
    assert (m['tp'], m['fp'], m['fn']) == (2, 0, 1)        # il 60 s e' fuori finestra: ne' FP ne' FN
    assert abs(m['media'] - 0.3) < 1e-9 and abs(m['entro_0.1'] - 0.5) < 1e-9


def _scenario_arrivo(fs=100.0):
    """Nuotata con bracciate (gyro x), poi capovolgimento di 180 gradi (viso al cielo), poi di nuovo nuotata."""
    rng = np.random.default_rng(1)
    segs = [(0, 25, 'nuoto'), (25, 26.2, 'su'), (26.2, 34, 'fermo'), (34, 35.2, 'giu'), (35.2, 60, 'nuoto'),
            (60, 61.2, 'su'), (61.2, 70, 'fermo')]
    N = int(70 * fs)
    t = np.arange(N) / fs
    th = np.zeros(N)
    gx = np.zeros(N)
    cur = 0.0
    for a, b, s in segs:
        m = (t >= a) & (t < b)
        if s == 'su':
            th[m] = np.pi * (t[m] - a) / (b - a)
            cur = np.pi
        elif s == 'giu':
            th[m] = np.pi - np.pi * (t[m] - a) / (b - a)
            cur = 0.0
        else:
            th[m] = cur
        if s == 'nuoto':
            gx[m] = 250 * np.sin(2 * np.pi * 0.6 * t[m])
        elif s in ('su', 'giu'):
            gx[m] = np.degrees(np.gradient(th, 1 / fs))[m]
    acc = np.stack([np.zeros(N), np.cos(th), np.sin(th)], 1) + rng.normal(0, 0.01, (N, 3))
    gyro = np.stack([gx, np.zeros(N), np.zeros(N)], 1) + rng.normal(0, 2, (N, 3))
    return t, acc, gyro, fs


def test_arrivo_causale_e_verifica_causalita():
    t, acc, gyro, fs = _scenario_arrivo()
    F, U = (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)
    fab = lambda: RilevatoreOriginale(assi=(F, U))
    ev, viol = simula(fab(), t, acc, gyro, fs)
    A = [e for e in ev if e.tipo == 'A' and e.info.get('causale', True)]
    assert len(A) >= 1, 'arrivo sintetico non rilevato'
    assert not viol
    assert all(0 <= e.t_notifica - e.t_evento < 1.5 for e in A)
    c = verifica_causalita(fab, t, acc, gyro, fs, tipi=('A',), eventi=ev)
    assert c['ok'] and c['provati'] >= 1, c
    # notifica a blocchi (come la FIFO): stesso istante evento, notifica al piu' dopo il blocco
    ev2, _ = simula(fab(), t, acc, gyro, fs, blocco=10)
    A2 = [e for e in ev2 if e.tipo == 'A' and e.info.get('causale', True)]
    assert [round(e.t_evento, 6) for e in A2] == [round(e.t_evento, 6) for e in A]


class _FuturoDatato(Rilevatore):
    """Controesempio: data l'evento 0,5 s DOPO il campione corrente (decisione 'dal futuro')."""

    def inizia(self, fs):
        self.i = 0
        self.fs = fs

    def push(self, t, a, g):
        self.i += 1
        return [Evento('A', t + 0.5)] if self.i == 300 else []


class _DipendeDaiDatiConsegnati(Rilevatore):
    """Controesempio rilevabile dal test per troncamento: l'evento dipende dal NUMERO di campioni
    consegnati in totale (solo se il flusso e' stato troncato cambia): usa fine() per decidere 'con tutto il file'."""

    def inizia(self, fs):
        self.n = 0
        self.tl = []

    def push(self, t, a, g):
        self.n += 1
        self.tl.append(t)
        # decide a campione 200 usando la durata del flusso 'a posteriori': non realizzabile se si tronca
        return []

    def fine(self):
        return [Evento('A', self.tl[199])]       # evento emesso solo a fine flusso (flag da_fine)


def test_simulatore_segnala_eventi_datati_nel_futuro_e_da_fine():
    t, acc, gyro, fs = _scenario_arrivo()
    ev, viol = simula(_FuturoDatato(), t, acc, gyro, fs)
    assert len(viol) == 1 and viol[0].t_evento > viol[0].t_notifica
    ev2, viol2 = simula(_DipendeDaiDatiConsegnati(), t, acc, gyro, fs)
    assert not viol2 and ev2[0].info.get('da_fine')
    # un evento decisibile solo a fine flusso non e' "causale": la verifica lo esclude e lo segnala nei dati
    assert ev2[0].t_notifica == t[-1]


def test_compressione_e_ricampionamento():
    rng = np.random.default_rng(0)
    X = np.cumsum(rng.integers(-3, 4, (3000, 6)), axis=0)
    r = comprimi(X)
    assert abs(r['campioni_per_blocco'] - 228 / 6 - 1) < 1.5       # tutto delta: 1 + 38 per blocco
    X2 = X.copy()
    X2[::3] += 1000
    assert comprimi(X2)['campioni_per_blocco'] < r['campioni_per_blocco']
    # ricampionamento: 5 Hz resta, 40 Hz viene eliminato a 52 Hz di uscita
    fs = 214.0
    t = np.arange(0, 60, 1 / fs)
    x = np.sin(2 * np.pi * 5 * t) + np.sin(2 * np.pi * 40 * t)
    from dataset import Sessione
    s = Sessione('s', t, np.stack([x, x, x], 1), np.stack([x, x, x], 1) * 100, fs, [], {}, (0, 60))
    s2 = ricampiona(s, 52)
    y = s2.acc[:, 0]
    tt = s2.t
    ideale = np.sin(2 * np.pi * 5 * tt)
    m = (tt > 2) & (tt < 58)
    assert np.sqrt(np.mean((y[m] - ideale[m]) ** 2)) < 0.05


if __name__ == '__main__':
    n = 0
    for nome, f in sorted(globals().items()):
        if nome.startswith('test_') and callable(f):
            f()
            print('OK', nome)
            n += 1
    print(n, 'test passati')
