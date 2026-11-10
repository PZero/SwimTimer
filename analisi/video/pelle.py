"""Bordo sinistro del corpo usando solo pixel 'pelle/costume' (diversi dallo sfondo E con rosso > blu) nella zona del muro:
esclude le bolle (bianche/grigie) e l'acqua (blu). Uso: python pelle.py V160.npy SEGNALI.npz USCITA.npz"""
import sys, numpy as np, cv2
src, seg, out = sys.argv[1:4]
V = np.load(src, mmap_mode='r'); z = np.load(seg); Q = z['Q']; N = len(V); X = 90
def radd(i):
    a, tx, ty = Q[i]; w = np.array([[np.cos(a), -np.sin(a), tx], [np.sin(a), np.cos(a), ty]], np.float32)
    return cv2.warpAffine(np.ascontiguousarray(V[i]), w, (160, 90), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE).astype(np.int16)
PASSO = 500; sfondi = []
for c in range(0, N, PASSO):
    ii = np.linspace(max(0, c - 1000), min(N - 1, c + 1000), 40).astype(int)
    sfondi.append(np.median(np.stack([radd(i) for i in ii]), axis=0))
k3 = np.ones((3, 3), np.uint8); prof = np.zeros((N, X), np.uint8)
for i in range(N):
    f = radd(i); bg = sfondi[min(len(sfondi) - 1, int(round(i / PASSO)))]
    m = (np.abs(f - bg).max(axis=2) > 30) & (f[..., 2] - f[..., 0] > 8)     # BGR: rosso - blu
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, k3)
    prof[i] = np.minimum(m[8:82, :X].sum(axis=0), 255)
np.savez(out, prof=prof); print('ok')
