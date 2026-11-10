import sys, csv, numpy as np
from scipy.ndimage import median_filter
S = sys.argv[1]; z = np.load(f'{S}/segnali.npz'); t, prof = z['t'], z['prof'].astype(int)
occ = prof[:, :100] >= 4; e = median_filter(np.where(occ.any(1), occ.argmax(1), 100).astype(float), 5)
ev = [(float(r['t_video_s']), r['tipo']) for r in csv.DictReader(open(f'{S}/eventi_corretti.csv')) if r['tipo'] in 'APV']
def tocco(te, xw):      # primo fotogramma con bordo <= xw dopo essere stato > xw+15, cercando in [te-2.5, te+2.5]
    i0, i1 = np.searchsorted(t, te - 2.5), np.searchsorted(t, te + 2.5)
    lontano = False
    for i in range(i0, i1):
        if e[i] > xw + 15: lontano = True
        elif lontano and e[i] <= xw: return t[i]
    return np.nan
def stacco(te, xw):     # ultimo fotogramma con bordo <= xw prima che superi xw+12 (per sempre nella finestra corta)
    i0, i1 = np.searchsorted(t, te - 2.5), np.searchsorted(t, te + 2.5)
    for i in range(i0, i1):
        if i > i0 and e[i] > xw + 12 and e[i0:i].min() <= xw:
            j = i
            while j > i0 and e[j] > xw: j -= 1
            return t[j]
    return np.nan
def minimo(te):         # virata: ultimo minimo del bordo prima della risalita
    i0, i1 = np.searchsorted(t, te - 2.5), np.searchsorted(t, te + 2.5)
    return np.nan
for ty, f in (('A', tocco), ('P', stacco), ('V', stacco)):
    for xw in (20, 25, 28, 30, 32, 35, 38, 40):
        d = np.array([f(te, xw) - te for te, tt in ev if tt == ty]); ok = ~np.isnan(d)
        print(ty, xw, f'trovati {ok.sum()}/{len(d)}  medio {np.nanmean(d):+.3f}  dev {np.nanstd(d):.3f}  mediana-ass {np.nanmedian(np.abs(d - np.nanmedian(d))):.3f}')
print('--- singoli (A xw=32, P/V xw=28)')
for ty, f, xw in (('A', tocco, 32), ('P', stacco, 28), ('V', stacco, 28)):
    print(ty, ' '.join(f'{te:.1f}:{f(te, xw) - te:+.2f}' for te, tt in ev if tt == ty))
