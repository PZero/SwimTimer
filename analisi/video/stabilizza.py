"""Stima per ogni fotogramma la trasformazione euclidea (rotazione + traslazione) rispetto a un riferimento mediano,
con ECC sulla zona del muro e della linea nera (x < 70 su 160). Uso: python stabilizza.py V160.npy USCITA.npy"""
import sys, time, numpy as np, cv2
src, out = sys.argv[1], sys.argv[2]
V = np.load(src, mmap_mode='r'); N = len(V)
ref = np.median(V[np.linspace(0, N - 1, 300).astype(int)], axis=0).astype(np.uint8)
g = lambda f: cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.float32)
R = g(ref); mask = np.zeros(R.shape, np.uint8); mask[:, :70] = 255
P = np.full((N, 4), np.nan)              # angolo (rad), tx, ty, correlazione
w = np.eye(2, 3, dtype=np.float32); t0 = time.time()
for i in range(N):
    w0 = w.copy()
    try:
        cc, w = cv2.findTransformECC(R, g(V[i]), w0, cv2.MOTION_EUCLIDEAN, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 1e-4), mask, 3)
        P[i] = (np.arctan2(w[1, 0], w[0, 0]), w[0, 2], w[1, 2], cc)
    except cv2.error:
        w = np.eye(2, 3, dtype=np.float32)
    if i % 5000 == 0: print(i, f'{time.time() - t0:.0f}s', flush=True)
np.save(out, P); cv2.imwrite(out.replace('.npy', '_ref.png'), ref); print('fatto', f'{time.time() - t0:.0f}s')
