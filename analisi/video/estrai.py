"""Decodifica tutto il video in un memmap uint8 (N, H, W, 3) a bassa risoluzione + tempi dei fotogrammi.
Uso: python estrai.py VIDEO USCITA.npy [W H]"""
import sys, time, cv2, numpy as np
video, out = sys.argv[1], sys.argv[2]
W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (160, 90)
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
mm = np.lib.format.open_memmap(out, mode='w+', dtype=np.uint8, shape=(n, H, W, 3))
ts = np.zeros(n); t0 = time.time(); i = 0
while i < n:
    ok, f = cap.read()
    if not ok: break
    ts[i] = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
    mm[i] = cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA); i += 1
    if i % 5000 == 0: print(i, f'{time.time() - t0:.0f}s', flush=True)
mm.flush(); np.save(out.replace('.npy', '_t.npy'), ts[:i])
print('fatto', i, 'fotogrammi', f'{time.time() - t0:.0f}s')
