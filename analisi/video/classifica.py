"""Classifica automaticamente A (tocco), V (stacco dopo capriola) e P (stacco in partenza) su tutto il video, senza etichette.
Visite al muro = tratti con bordo del corpo < 40 (mediana 1 s). Visita in cui il corpo color pelle resta vicino al muro (bordo < 45) per >= 2 s -> A all'inizio + P allo stacco;
da 0,3 a 2 s -> V (capriola: la nuvola di bolle non conta); meno -> ignorata. Correzioni di scarto tarate sulle etichette manuali del 9/11/2026.
Uso: python classifica.py SEGNALI.npz PELLE.npz T_SYNC_VIDEO USCITA.json"""
import sys, json, numpy as np
from scipy.ndimage import median_filter
seg, pel, tsync, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
z = np.load(seg); t = z['t']
def bordo(p, th):
    o = p >= th; return median_filter(np.where(o.any(1), o.argmax(1), 90).astype(float), 5)
e = bordo(z['prof'][:, :90].astype(int), 4)          # bordo del corpo (differenza dallo sfondo)
ep = bordo(np.load(pel)['prof'].astype(int), 3)       # bordo dei soli pixel color pelle (senza bolle)
CORR_A, CORR_V = -0.39, -0.63                         # scarti medi misurati (automatico - manuale), da sottrarre
vic = median_filter((e < 40).astype(np.uint8), 51) > 0
d = np.diff(np.r_[0, vic.astype(int), 0]); ini, fin = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0] - 1
def stacco(a, b, xw=28):          # ultimo fotogramma <= xw dopo il quale il bordo resta > xw+12 per 1 s (lascia il muro)
    for i in range(b - 1, a, -1):
        if e[i] <= xw < e[i + 1] and e[i + 1:i + 51].min() > xw: 
            if e[i + 1:i + 51].max() > xw + 12: return i
    return None
def tocco(a, b, xw=32):
    for i in range(a, b):
        if e[i] <= xw: return i
def v_stacco(a, b):              # minimo del bordo pelle seguito da una risalita netta (>20 in 0,8 s)
    cand = [i for i in range(a, b) if ep[i] < 40 and np.max(np.where(ep[i:i + 40] < 90, ep[i:i + 40], 0)) > ep[i] + 20]
    return min(cand, key=lambda j: ep[j]) if cand else None
eventi = []
for a, b in zip(ini, fin):
    if t[b] - t[a] < 1.5 or t[b] < tsync + 1: continue
    a0, b1 = max(0, a - 50), min(len(e) - 60, b + 100)
    pelle = (ep[a0:b1] < 45).sum() / 50
    if pelle < 0.3: continue
    if t[b] > t[-1] - 0.5:     # visita tagliata dalla fine del video: solo l'arrivo
        i_a = tocco(a0, b)
        if i_a is not None: eventi.append(('A', t[i_a] - CORR_A, 'auto OpenCV: tocco, incerto +-0,3 s (fine video)'))
    elif pelle >= 2.0:
        i_p = stacco(a0, b1); i_a = tocco(a0, i_p if i_p else b)
        if i_a is not None: eventi.append(('A', t[i_a] - CORR_A, 'auto OpenCV: tocco, incerto +-0,3 s'))
        if i_p is not None: eventi.append(('P', t[i_p], 'auto OpenCV: stacco, +-0,15 s'))
    else:
        i_v = v_stacco(a0, b1)
        if i_v is not None: eventi.append(('V', t[i_v] - CORR_V, 'auto OpenCV: stacco in virata, incerto +-0,45 s'))
json.dump([{'tipo': k, 't_video_s': round(float(x), 3), 'nota': n} for k, x, n in eventi], open(out, 'w'), indent=1)
print(len(eventi), 'eventi:', {k: sum(1 for e_ in eventi if e_[0] == k) for k in 'AVP'})
