"""Maschera del corpo su fotogrammi stabilizzati e profilo per colonna (quanti pixel del corpo in ogni colonna x).
Uso: python segnali.py V160.npy STAB.npy USCITA.npz"""
import sys, numpy as np, cv2
src, stab, out = sys.argv[1:4]
V = np.load(src, mmap_mode='r'); t = np.load(src.replace('.npy', '_t.npy')); P = np.load(stab)
N, H, W, _ = V.shape; fps = 50.0
# parametri affidabili: buona correlazione e rotazione piccola; gli altri interpolati, poi mediana mobile 0,5 s
ok = (P[:, 3] > 0.88) & (np.abs(np.degrees(P[:, 0])) < 12) & (np.abs(P[:, 1]) < 15) & (np.abs(P[:, 2]) < 15)
idx = np.arange(N); Q = np.zeros((N, 3))
for k in range(3): Q[:, k] = np.interp(idx, idx[ok], P[ok, k])
from scipy.ndimage import median_filter
Q = median_filter(Q, size=(25, 1), mode='nearest')
def raddrizza(i):
    a, tx, ty = Q[i]; w = np.array([[np.cos(a), -np.sin(a), tx], [np.sin(a), np.cos(a), ty]], np.float32)
    return cv2.warpAffine(np.ascontiguousarray(V[i]), w, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
PASSO = int(10 * fps); centri = np.arange(0, N, PASSO); sfondi = []
for c in centri:
    ii = np.linspace(max(0, c - 20 * fps), min(N - 1, c + 20 * fps), 40).astype(int)
    sfondi.append(np.median(np.stack([raddrizza(i) for i in ii]), axis=0).astype(np.int16))
k3 = np.ones((3, 3), np.uint8); prof = np.zeros((N, W), np.uint8); area = np.zeros(N)
for i in range(N):
    f = raddrizza(i).astype(np.int16); bg = sfondi[min(len(sfondi) - 1, int(round(i / PASSO)))]
    m = cv2.morphologyEx((np.abs(f - bg).max(axis=2) > 35).astype(np.uint8), cv2.MORPH_OPEN, k3)
    prof[i] = np.minimum(m[8:82].sum(axis=0), 255); area[i] = m.sum()
np.savez(out, t=t, prof=prof, area=area, ok=ok, Q=Q, sfondo=sfondi[len(sfondi) // 2].astype(np.uint8))
print('ok', N, 'affidabili', ok.mean().round(3))
