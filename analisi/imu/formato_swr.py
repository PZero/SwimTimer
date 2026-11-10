"""Decodifica del formato .swr del tag SwimTimer (firmware 0.5.x).

Formato (vedi docs di analisi, test.md §2): blocchi da 256 byte.
  0xA5 header di sessione, 0xD1 blocco dati, 0xE0 footer di sessione.
Blocco dati: [0]=0xD1, [1]=n campioni, [2:4]=seq u16, [4:8]=timestamp ms del primo
campione, [16:28]=primo campione assoluto (6 x int16: ax ay az gx gy gz), poi delta
int8 (6 byte per campione); il byte 0x80 introduce 6 x int16 assoluti (13 byte, "escape").

Problema noto: la FIFO dell'IMU a volte ruota ciclicamente l'ordine dei 6 canali.
Correzione: per ogni campione si provano le 6 rotazioni (costo = scarto di |a| da 1 g
+ |w| piccolo) e un Viterbi che permette il cambio rotazione solo ai campioni di escape
(penalita' 300). Qui e' implementato a livello di SEGMENTI (tra due escape), identico
come risultato ma vettorizzato.
"""
import struct
import numpy as np

BLOCCO = 256
ACC_LSB_G = 0.488e-3     # g/LSB (±16 g); letto anche dall'header se presente
GYR_LSB_DPS = 0.035      # dps/LSB (±1000 dps)
PENALITA_CAMBIO = 300.0


def sessioni(dati: bytes):
    """Elenca le sessioni: lista di (blocco_header, primo_blocco_dati, ultimo_blocco_dati)."""
    nb = len(dati) // BLOCCO
    out, cur = [], None
    for b in range(nb):
        tipo = dati[b * BLOCCO]
        if tipo == 0xA5:
            if cur:
                out.append(cur)
            cur = [b, None, None]
        elif tipo == 0xD1 and cur is not None:
            if cur[1] is None:
                cur[1] = b
            cur[2] = b
    if cur:
        out.append(cur)
    return [tuple(c) for c in out if c[1] is not None]


def intestazione(dati: bytes, blocco_header: int):
    """Risoluzioni dall'header: (acc_mg_per_lsb, gyro_mdps_per_lsb) se leggibili."""
    h = dati[blocco_header * BLOCCO:(blocco_header + 1) * BLOCCO]
    acc_mg = struct.unpack_from('<H', h, 18)[0] if len(h) > 20 else 488
    gyr_m = h[20] if len(h) > 20 else 35
    return acc_mg, gyr_m


def _decodifica_blocchi(dati, primo, ultimo):
    S, ESC, BLK = [], [], []
    for b in range(primo, ultimo + 1):
        blk = dati[b * BLOCCO:(b + 1) * BLOCCO]
        if blk[0] != 0xD1:
            continue
        n = blk[1]
        _, ts = struct.unpack_from('<HI', blk, 2)
        p = 16
        s = list(struct.unpack_from('<6h', blk, p)); p += 12
        BLK.append((len(S), n, ts))
        S.append(tuple(s)); ESC.append(True)
        cnt = 1
        while cnt < n:
            if blk[p] == 0x80:
                s = list(struct.unpack_from('<6h', blk, p + 1)); p += 13
                S.append(tuple(s)); ESC.append(True)
            else:
                d = struct.unpack_from('<6b', blk, p); p += 6
                s = [s[i] + d[i] for i in range(6)]
                S.append(tuple(s)); ESC.append(False)
            cnt += 1
    return np.array(S, float), np.array(ESC), np.array(BLK)


def _viterbi_rotazioni(S, ESC):
    N = len(S)
    cost = np.zeros((N, 6))
    for r in range(6):
        x = np.roll(S, -r, axis=1)
        an = np.linalg.norm(x[:, :3], axis=1)
        gn = np.linalg.norm(x[:, 3:], axis=1)
        cost[:, r] = np.minimum(np.abs(an - 2048) / 300, 5) + np.minimum(gn / 3000, 5)
    cs = np.vstack([np.zeros(6), np.cumsum(cost, 0)])
    starts = np.nonzero(ESC)[0]
    starts = starts if starts[0] == 0 else np.r_[0, starts]
    ends = np.r_[starts[1:], N]
    segc = cs[ends] - cs[starts]                      # M x 6
    M = len(starts)
    acc = segc[0].copy()
    back = np.zeros((M, 6), np.int8)
    ar = np.arange(6)
    for m in range(1, M):
        am = int(acc.argmin()); mn = acc[am]
        sw = mn + PENALITA_CAMBIO
        back[m] = np.where(acc <= sw, ar, am)
        acc = np.minimum(acc, sw) + segc[m]
    rot_seg = np.zeros(M, int)
    rot_seg[-1] = int(acc.argmin())
    for m in range(M - 1, 0, -1):
        rot_seg[m - 1] = back[m, rot_seg[m]]
    rot = np.repeat(rot_seg, ends - starts)
    return rot


def carica_swr(percorso, sessione=None):
    """Legge un .swr. Restituisce dict con:
      fs, dt, acc_g (N,3), gyro_dps (N,3), t (N,) [s dal primo campione], rotazioni, info.
    sessione: indice (0-based) fra quelle trovate; default = la piu' lunga."""
    dati = open(percorso, 'rb').read()
    ss = sessioni(dati)
    if not ss:
        raise ValueError('nessuna sessione dati nel file')
    if sessione is None:
        sessione = int(np.argmax([s[2] - s[1] for s in ss]))
    hb, b0, b1 = ss[sessione]
    S, ESC, BLK = _decodifica_blocchi(dati, b0, b1)
    rot = _viterbi_rotazioni(S, ESC)
    idx = (np.arange(6)[None, :] + rot[:, None]) % 6
    X = np.take_along_axis(S, idx, axis=1)
    # frequenza: fit lineare indice campione -> timestamp blocco (ms)
    ts = BLK[:, 2].astype(float)
    # (ms u32: nessun giro del contatore atteso in sessioni di pochi minuti)
    pend = np.polyfit(BLK[:, 0], ts, 1)
    dt = pend[0] / 1000.0
    acc_mg, gyr_m = intestazione(dati, hb)
    res = dict(
        fs=1.0 / dt, dt=dt,
        acc_g=X[:, :3] * (acc_mg / 1.0e6),
        gyro_dps=X[:, 3:] * (gyr_m / 1000.0),
        t=np.arange(len(X)) * dt,
        raw=X.astype(np.int16),
        cambi_rotazione=int(np.count_nonzero(np.diff(rot))),
        info=dict(blocchi=[int(b0), int(b1)], n_campioni=int(len(X)), n_sessioni=len(ss),
                  sessione=int(sessione), acc_mg_per_lsb=int(acc_mg), gyro_mdps_per_lsb=int(gyr_m)),
        blocchi=BLK,
    )
    return res
