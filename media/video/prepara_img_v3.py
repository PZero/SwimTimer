"""Immagini REALI per il video v3 (sessione del 9/11/2026 dell'autore): fotogrammi del video subacqueo, grafici IMU e
grafici OpenCV con lo stile del video. Le immagini sono dati personali: finiscono in una cartella FUORI dal repository.

Uso: python media/video/prepara_img_v3.py --video VIDEO.mp4 --swr SESSIONE.swr --viz viz.json --segnali video_segnali.npz
                                          --pelle pelle.npz --out CARTELLA
"""
import argparse
import json
import struct
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from scipy.ndimage import median_filter  # noqa: E402

BG, CARD, GRID = '#04102a', '#06122e', '#16346a'
CYAN, CYAN2, WHITE, MUTED = '#28d2ff', '#8ee9ff', '#f5faff', '#8ea6cc'
AMBER, GREEN, RED, VIOLET = '#ffbe3c', '#4cc38a', '#ff6b6f', '#a78bfa'
plt.rcParams.update({'font.family': 'Bahnschrift', 'font.size': 15, 'axes.facecolor': CARD, 'figure.facecolor': CARD,
                     'axes.edgecolor': GRID, 'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'grid.color': GRID, 'axes.grid': True, 'axes.unicode_minus': False, 'grid.linewidth': 0.8, 'savefig.facecolor': CARD})
TOCCO = 151.62            # arrivo verificato fotogramma per fotogramma (tempo video)
TOCCO_VECCHIO = 152.06    # la stessa etichetta nella prima annotazione


def leggi(cap, t, box=None, w=None):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000 + 1)
    ok, f = cap.read()
    if box:
        x0, y0, x1, y1 = box
        f = f[y0:y1, x0:x1]
    if w:
        f = cv2.resize(f, (w, int(f.shape[0] * w / f.shape[1])), interpolation=cv2.INTER_AREA)
    return f


def fotogrammi(a, out):
    cap = cv2.VideoCapture(a.video)
    box = (0, 110, 960, 650)                             # zona del muro (1280x720)
    d = out / 'tocco'
    d.mkdir(exist_ok=True)
    for i, t in enumerate(np.arange(TOCCO - 0.6, TOCCO + 0.42, 0.02)):   # 51 fotogrammi consecutivi a 50 fps
        cv2.imwrite(str(d / f'{i:03d}.jpg'), leggi(cap, t, box, 1440), [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(out / 'largo.jpg'), leggi(cap, 233.0), [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(out / 'sync.jpg'), leggi(cap, 0.82), [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(out / 'etichetta_nuova.jpg'), leggi(cap, TOCCO, box, 960), [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(out / 'etichetta_vecchia.jpg'), leggi(cap, TOCCO_VECCHIO, box, 960), [cv2.IMWRITE_JPEG_QUALITY, 92])
    for k, dt in enumerate((-0.2, 0.0, 0.2)):
        cv2.imwrite(str(out / f'arrivo_{k}.jpg'), leggi(cap, TOCCO + dt, box, 960), [cv2.IMWRITE_JPEG_QUALITY, 92])
    return cap


def picco_sync(a, out):
    """|acc| grezzo attorno al colpo di sync (decodifica dei blocchi 0xD1 del .swr, sessione 2)."""
    d = open(a.swr, 'rb').read()
    S = []
    for b in range(266, 8191):
        blk = d[b * 256:(b + 1) * 256]
        if blk[0] != 0xD1:
            continue
        n = blk[1]
        s = list(struct.unpack_from('<6h', blk, 16))
        p, got = 28, [tuple(s)]
        while len(got) < n:
            if blk[p] == 0x80:
                s = list(struct.unpack_from('<6h', blk, p + 1))
                p += 13
            else:
                s = [s[i] + struct.unpack_from('<b', blk, p + i)[0] for i in range(6)]
                p += 6
            got.append(tuple(s))
        S += got
        if len(S) > 40000:
            break
    S = np.array(S, float)
    dt = 0.004672358
    t = np.arange(len(S)) * dt
    an = np.linalg.norm(S[:, :3], axis=1) * 0.000488
    i0 = int(158 / dt)
    i1 = int(168 / dt)
    k = i0 + int(np.argmax(an[i0:i1]))
    s = slice(k - int(3 / dt), k + int(3 / dt))
    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=110)
    ax.plot(t[s] - t[k], an[s], color=CYAN, lw=1.4)
    ax.axvline(0, color=VIOLET, lw=2.5)
    ax.annotate(f'{an[k]:.1f} g', (0, an[k]), xytext=(0.25, an[k] * 0.92), color=VIOLET, fontsize=24, fontweight='bold')
    ax.set_xlabel('s dal colpo di sync')
    ax.set_ylabel('|a|  (g)')
    ax.set_xlim(-3, 3)
    fig.tight_layout()
    fig.savefig(out / 'sync_picco.png')
    plt.close(fig)
    return float(an[k])


def bordo(p, th):
    o = p >= th
    return median_filter(np.where(o.any(1), o.argmax(1), 90).astype(float), 5)


def opencv(a, cap, out):
    z = np.load(a.segnali)
    t = z['t']
    e = bordo(z['prof'][:, :90].astype(int), 4)
    ep = bordo(np.load(a.pelle)['prof'].astype(int), 3)
    # chimografo: tempo (verticale) x colonna (orizzontale) attorno al tocco
    i0, i1 = np.searchsorted(t, TOCCO - 3), np.searchsorted(t, TOCCO + 3)
    fig, ax = plt.subplots(figsize=(7, 9), dpi=110)
    ax.imshow(z['prof'][i0:i1, :90], aspect='auto', cmap='magma', vmin=0, vmax=22, extent=[0, 90, t[i1 - 1] - TOCCO, t[i0] - TOCCO])
    ax.axhline(0, color=CYAN, lw=2)
    ax.axvline(36, color=AMBER, lw=1.5, ls='--')
    ax.set_xlabel('distanza dal muro (pixel)')
    ax.set_ylabel('s dal tocco')
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(out / 'chimografo.png')
    plt.close(fig)
    # curva della distanza dal muro (bordo del corpo) attorno al tocco
    s = (t > TOCCO - 3) & (t < TOCCO + 3)
    fig, ax = plt.subplots(figsize=(12, 4.6), dpi=110)
    ax.plot(t[s] - TOCCO, e[s], '.', ms=4, color=MUTED, label='corpo')
    ax.plot(t[s] - TOCCO, np.where(ep[s] < 90, ep[s], np.nan), '.', ms=5, color=CYAN, label='solo pelle (senza bolle)')
    ax.axhline(36, color=AMBER, lw=1.5, ls='--')
    ax.text(-2.9, 39, 'bordo del muro', color=AMBER, fontsize=15)
    ax.axvline(0, color=RED, lw=2.5)
    ax.set_ylim(0, 90)
    ax.set_xlim(-3, 3)
    ax.set_xlabel('s dal tocco')
    ax.set_ylabel('distanza (px)')
    ax.legend(facecolor=CARD, edgecolor=GRID, labelcolor=WHITE, loc='upper right')
    fig.tight_layout()
    fig.savefig(out / 'distanza_muro.png')
    plt.close(fig)
    # maschera: fotogramma, maschera senza stabilizzazione, maschera stabilizzata + filtro pelle
    V = np.load(a.v160, mmap_mode='r')
    i = int(np.searchsorted(t, 233.0))              # partenza: corpo raccolto al muro, sopra l'acqua blu
    Q = z['Q']

    def radd(j):
        aa, tx, ty = Q[j]
        w = np.array([[np.cos(aa), -np.sin(aa), tx], [np.sin(aa), np.cos(aa), ty]], np.float32)
        return cv2.warpAffine(np.ascontiguousarray(V[j]), w, (160, 90), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE).astype(np.int16)
    ii = np.linspace(i - 1000, i + 1000, 40).astype(int)
    bg0 = np.median(V[ii].astype(np.int16), axis=0)
    bg1 = np.median(np.stack([radd(j) for j in ii]), axis=0)
    f0, f1 = V[i].astype(np.int16), radd(i)
    m0 = (np.abs(f0 - bg0).max(axis=2) > 35).astype(np.uint8) * 255          # grezza: senza stabilizzazione ne' pulizia
    m1 = cv2.morphologyEx((np.abs(f1 - bg1).max(axis=2) > 35).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) * 255
    big = lambda x: cv2.resize(x, (640, 360), interpolation=cv2.INTER_NEAREST)  # noqa: E731
    col = lambda m, c: (np.dstack([m, m, m]) / 255 * np.array(c)).astype(np.uint8)  # noqa: E731
    cv2.imwrite(str(out / 'maschera_0.png'), cv2.resize(leggi(cap, float(t[i])), (640, 360), interpolation=cv2.INTER_AREA))
    cv2.imwrite(str(out / 'maschera_1.png'), big(col(m0, (111, 107, 255))))
    cv2.imwrite(str(out / 'maschera_2.png'), big(col(m1, (255, 210, 40))))


def imu(a, out):
    """Grafico IMU (dati della pagina di analisi, 25 Hz) attorno allo stesso arrivo, con le etichette."""
    D = json.load(open(a.viz))
    fs, xv, xd, kv = D['fs'], D['xv'], D['xd'], D['kv']
    td = lambda tv: xd + (tv - xv) * kv  # noqa: E731
    tc = td(TOCCO)
    n = len(D['rms'])
    t = np.arange(n) / fs + D['t0']
    s = (t > tc - 6) & (t < tc + 6)
    fig, ax = plt.subplots(figsize=(12, 4.6), dpi=110)
    ax.plot(t[s] - tc, np.array(D['rms'])[s], color=AMBER, lw=2.5, label='rotazione della testa |ω| (°/s)')
    ax2 = ax.twinx()
    ax2.plot(t[s] - tc, np.array(D['gf'])[s], color=CYAN, lw=2.5, label='viso al cielo (-1…+1)')
    ax2.set_ylim(-1.1, 1.1)
    ax2.tick_params(colors=MUTED)
    ax2.grid(False)
    ax.axvline(0, color=RED, lw=2.5)
    ax.text(0.1, ax.get_ylim()[1] * 0.9, 'tocco (video)', color=RED, fontsize=16)
    for e in D['man']:
        if e['k'] in 'APV' and tc - 6 < e['t'] < tc + 6:
            ax.axvline(e['t'] - tc, color=MUTED, lw=1.5, ls=':')
    ax.set_xlim(-6, 6)
    ax.set_xlabel('s dal tocco')
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, facecolor=CARD, edgecolor=GRID, labelcolor=WHITE, loc='lower left', fontsize=13, ncol=2)
    fig.tight_layout()
    fig.savefig(out / 'imu_arrivo.png')
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    for k in ('video', 'swr', 'viz', 'segnali', 'pelle', 'v160', 'out'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cap = fotogrammi(a, out)
    print('picco sync', round(picco_sync(a, out), 2), 'g')
    opencv(a, cap, out)
    imu(a, out)
    print('ok', out)


if __name__ == '__main__':
    main()
