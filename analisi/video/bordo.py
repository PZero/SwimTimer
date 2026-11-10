import sys, csv, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = sys.argv[1]; z = np.load(f'{S}/segnali.npz'); t, prof = z['t'], z['prof'].astype(int)
ev = [(float(r['t_video_s']), r['tipo']) for r in csv.DictReader(open(f'{S}/eventi_corretti.csv')) if r['tipo'] in 'APV']
def bordo(th):
    occ = prof[:, :100] >= th; e = np.where(occ.any(1), occ.argmax(1), 100).astype(float); return e
fig, ax = plt.subplots(3, 14, figsize=(30, 12)); ax = ax.ravel()
E = {th: bordo(th) for th in (2, 4, 8)}
for k, (te, ty) in enumerate(ev[:42]):
    s = (t > te - 3) & (t < te + 3); a = ax[k]
    for th, c in ((2, 'c'), (4, 'b'), (8, 'k')): a.plot(t[s] - te, E[th][s], '.', ms=1.5, color=c)
    a.axvline(0, color='r', lw=.8); a.set_ylim(0, 100); a.set_title(f'{ty} {te:.1f}', fontsize=9); a.grid(alpha=.3)
plt.tight_layout(); plt.savefig(f'{S}/bordo.png', dpi=45)
for ty in 'APV':
    v = [E[4][np.searchsorted(t, te)] for te, tt in ev if tt == ty]; print(ty, np.round(v).astype(int))
