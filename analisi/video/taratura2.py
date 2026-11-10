import sys, csv, numpy as np
from scipy.ndimage import median_filter
S = sys.argv[1]; z = np.load(f'{S}/segnali.npz'); t, prof = z['t'], z['prof'].astype(int)
occ = prof[:, :100] >= 4; e = median_filter(np.where(occ.any(1), occ.argmax(1), 100).astype(float), 5)
ev = [(float(r['t_video_s']), r['tipo']) for r in csv.DictReader(open(f'{S}/eventi_corretti.csv')) if r['tipo'] in 'APV']
F = 50
def ferma(te, xmax, tol, dur):   # primo fotogramma, dopo l'avvicinamento, in cui il bordo (< xmax) resta entro tol per dur s
    i0, i1 = np.searchsorted(t, te - 2.5), np.searchsorted(t, te + 2.5); n = int(dur * F); lont = False
    for i in range(i0, i1):
        if e[i] > xmax + 15: lont = True
        elif lont and e[i] < xmax and np.ptp(e[i:i + n]) <= tol: return t[i]
    return np.nan
def lascia(te, salto):           # virata: ultimo fotogramma vicino al minimo del bordo prima che salga di 'salto'
    i0, i1 = np.searchsorted(t, te - 2.5), np.searchsorted(t, te + 3.5); w = e[i0:i1]
    k = int(np.argmin(w)); m = w[k]
    for j in range(k, len(w)):
        if w[j] > m + salto:
            jj = j
            while jj > k and w[jj] > m + 3: jj -= 1
            return t[i0 + jj]
    return np.nan
for xmax in (40, 45, 50):
    for tol in (2, 3, 4):
        for dur in (0.1, 0.16, 0.24):
            d = np.array([ferma(te, xmax, tol, dur) - te for te, tt in ev if tt == 'A']); ok = ~np.isnan(d)
            print('A', xmax, tol, dur, f'{ok.sum()}/15 medio {np.nanmean(d):+.3f} dev {np.nanstd(d):.3f}')
for salto in (8, 12, 20):
    d = np.array([lascia(te, salto) - te for te, tt in ev if tt == 'V']); ok = ~np.isnan(d)
    print('V', salto, f'{ok.sum()}/12 medio {np.nanmean(d):+.3f} dev {np.nanstd(d):.3f}', ' '.join(f'{x:+.2f}' for x in d))
