import sys, csv, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, cv2
S = sys.argv[1]; z = np.load(f'{S}/segnali.npz'); t, prof = z['t'], z['prof']
cv2.imwrite(f'{S}/sfondo_stab.png', cv2.resize(z['sfondo'], (640, 360), interpolation=cv2.INTER_NEAREST))
ev = [(float(r['t_video_s']), r['tipo']) for r in csv.DictReader(open(f'{S}/eventi_corretti.csv')) if r['tipo'] in 'APV']
fig, ax = plt.subplots(3, 14, figsize=(30, 14)); ax = ax.ravel()
for k, (te, ty) in enumerate(ev[:42]):
    i0, i1 = np.searchsorted(t, te - 3), np.searchsorted(t, te + 3)
    a = ax[k]; a.imshow(prof[i0:i1, :90], aspect='auto', cmap='gray_r', vmin=0, vmax=20, extent=[0, 90, t[i1-1]-te, t[i0]-te])
    a.axhline(0, color='r', lw=.8); a.set_title(f'{ty} {te:.1f}', fontsize=9); a.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig(f'{S}/kimo.png', dpi=45)
