"""Esperimento sulla frequenza di campionamento.

1. `ricampiona`: porta la sessione a una frequenza piu' bassa con filtro anti-aliasing
   (FIR passa-basso a fase zero, taglio 0,4*fs_nuova, 0,1*fs_nuova di transizione) e interpolazione cubica
   su griglia uniforme. E' un'APPROSSIMAZIONE di un IMU impostato a ODR inferiore (il filtro
   digitale interno dell'LSM6DS3 e' diverso e il rumore reale cambia): da confermare con
   una registrazione vera a quell'ODR.
2. `comprimi`: stesso schema del firmware 0.5.x (test.md §2): blocco da 256 byte, intestazione
   16 byte + primo campione assoluto 12 byte, poi per ogni campione 6 byte di delta int8
   oppure, se un delta non sta in int8 (o il primo delta e' -128, valore riservato come
   escape 0x80), 13 byte (0x80 + 6 x int16). Si chiude il blocco quando il campione
   successivo non ci sta. Ritorna campioni/blocco e minuti nei 2 MiB.
"""
import dataclasses

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import firwin, oaconvolve

BLOCCO_BYTE = 256
INTEST = 16 + 12
BLOCCHI_FLASH = 2 * 1024 * 1024 // BLOCCO_BYTE      # 8192
BLOCCHI_UTILI = BLOCCHI_FLASH - 2                   # un header e un footer di sessione
ACC_G_LSB = 0.488e-3
GYR_DPS_LSB = 0.035


def ricampiona(sess, fn):
    """Sessione ricampionata a fn Hz (stessa base tempi, stessi eventi)."""
    fs0 = sess.fs
    ntap = int(4 * fs0 / (0.1 * fn)) | 1
    h = firwin(ntap, 0.4 * fn, fs=fs0, window='hamming')
    X = np.hstack([sess.acc, sess.gyro])
    Xf = oaconvolve(X, h[:, None], mode='same', axes=0)
    tn = np.arange(0, sess.t[-1], 1.0 / fn)
    Y = CubicSpline(sess.t, Xf, axis=0)(tn)
    return dataclasses.replace(sess, t=tn, acc=Y[:, :3], gyro=Y[:, 3:], fs=float(fn))


def quantizza(acc_g, gyro_dps):
    a = np.clip(np.round(acc_g / ACC_G_LSB), -32768, 32767)
    g = np.clip(np.round(gyro_dps / GYR_DPS_LSB), -32768, 32767)
    return np.hstack([a, g]).astype(np.int32)


def comprimi(X):
    """X: (N,6) interi (LSB). Ritorna dict(blocchi, campioni_per_blocco, escape_frac, byte_per_campione)."""
    d = np.diff(X, axis=0)
    ok = (d >= -128).all(1) & (d <= 127).all(1) & (d[:, 0] != -128)
    ok = np.concatenate([[False], ok])
    n = len(X)
    blocchi = 1
    used = INTEST
    esc = 0
    for j in range(1, n):
        need = 6 if ok[j] else 13
        if used + need > BLOCCO_BYTE:
            blocchi += 1
            used = INTEST
        else:
            used += need
            if not ok[j]:
                esc += 1
    return dict(blocchi=blocchi, campioni_per_blocco=n / blocchi, escape_frac=esc / n,
                byte_per_campione=blocchi * BLOCCO_BYTE / n)


def minuti_in_flash(campioni_per_blocco, fs, blocchi=BLOCCHI_UTILI):
    return blocchi * campioni_per_blocco / fs / 60.0


def esperimento_compressione(sess, frequenze=(None, 104, 52, 26), finestra=None):
    """Per ogni frequenza (None = originale) misura la compressione sull'intera sessione e
    nella finestra 'in acqua' (se data). Ritorna lista di dict."""
    out = []
    for f in frequenze:
        s = sess if f is None else ricampiona(sess, f)
        X = quantizza(s.acc, s.gyro)
        r = comprimi(X)
        r['fs'] = s.fs
        r['minuti_2MiB'] = minuti_in_flash(r['campioni_per_blocco'], s.fs)
        if finestra:
            m = (s.t >= finestra[0]) & (s.t <= finestra[1])
            r2 = comprimi(X[m])
            r['campioni_per_blocco_acqua'] = r2['campioni_per_blocco']
            r['minuti_2MiB_acqua'] = minuti_in_flash(r2['campioni_per_blocco'], s.fs)
        out.append(r)
    return out
