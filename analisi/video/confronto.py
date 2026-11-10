import sys, csv, numpy as np, cv2
sys.argv = [sys.argv[0], sys.argv[1]]; S = sys.argv[1]
exec(open(f'{S}/taratura.py').read().split("for ty, f in")[0])          # e, t, ev, tocco, stacco
exec(open(f'{S}/taratura2.py').read().split("for xmax in")[0].split("F = 50")[1].join(["F = 50", ""]) if False else "")
from scipy.ndimage import median_filter
def lascia(te, salto=8):
    i0, i1 = np.searchsorted(t, te - 2.5), np.searchsorted(t, te + 3.5); w = e[i0:i1]; k = int(np.argmin(w)); m = w[k]
    for j in range(k, len(w)):
        if w[j] > m + salto:
            jj = j
            while jj > k and w[jj] > m + 3: jj -= 1
            return t[i0 + jj]
    return np.nan
cap = cv2.VideoCapture(r'C:\Users\fnico\Downloads\815912470.855863_14121794219690.mp4')
def foto(tt, txt, col):
    cap.set(cv2.CAP_PROP_POS_MSEC, tt * 1000); ok, f = cap.read()
    c = cv2.resize(f[140:580, 0:560], (224, 176)); cv2.putText(c, txt, (4, 16), 0, 0.45, col, 2); return c
righe_csv = []
for ty, fn in (('A', lambda te: tocco(te, 32)), ('P', lambda te: stacco(te, 28)), ('V', lascia)):
    fogli = []
    for te, tt in ev:
        if tt != ty: continue
        ta = fn(te); righe_csv.append((ty, te, ta, ta - te))
        if ty == 'P': continue
        r = [foto(ta + d, f'auto{d:+.1f}' if d else f'AUTO {ta:.2f}', (0, 200, 0)) for d in (-0.2, 0, 0.2)] if not np.isnan(ta) else [np.zeros((176, 224, 3), np.uint8)] * 3
        r.append(foto(te, f'MANUALE {te:.2f}', (0, 0, 255)))
        fogli.append(np.hstack(r))
    if fogli: cv2.imwrite(f'{S}/confronto_{ty}.jpg', np.vstack(fogli), [cv2.IMWRITE_JPEG_QUALITY, 80])
with open(f'{S}/eventi_video_auto.csv', 'w', newline='') as fo:
    w = csv.writer(fo); w.writerow(['tipo', 't_video_manuale_s', 't_video_auto_s', 'differenza_s'])
    for r in righe_csv: w.writerow([r[0], f'{r[1]:.3f}', '' if np.isnan(r[2]) else f'{r[2]:.3f}', '' if np.isnan(r[3]) else f'{r[3]:+.3f}'])
print('ok')
