"""Video «SwimTimer: a che punto siamo» (v2): 120 s, 1920x1080, 30 fps, IT ed EN, musica originale (musica_v2.py).

Riusa la pipeline di genera_video.py (testo cinetico, pannelli Ken Burns, transizioni, sfondo) e aggiunge:
spezzoni video dell'autore (senza audio), schermate delle pagine del progetto (media/video/img_v2/, solo dati inventati)
e grafici animati dei filtri calcolati con numpy su segnali inventati.

Uso:  python media/video/genera_video_v2.py --clip-dir CARTELLA_VIDEO            (italiano: musica + miniatura + video)
      python media/video/genera_video_v2.py --lingua en --no-musica --clip-dir CARTELLA_VIDEO
      python media/video/genera_video_v2.py --anteprima 3 15 50 --dir CARTELLA --clip-dir CARTELLA_VIDEO
La CARTELLA_VIDEO contiene i video originali (WhatsApp) elencati in CLIP; i fotogrammi estratti (senza audio,
con color grading) finiscono in una cache temporanea fuori dal repository.
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import genera_video as gv  # noqa: E402

LANG = os.environ.get('SWIMTIMER_LANG', 'it')
if LANG == 'en':
    from testi_v2_en import EN as _TR
else:
    _TR = {}
gv._TR = _TR                     # T, block, wipe_text di genera_video traducono con questo dizionario
tr = gv.tr
T, block, kicker, wipe_text, G, panel, tlayer = gv.T, gv.block, gv.kicker, gv.wipe_text, gv.G, gv.panel, gv.tlayer
ease, smooth, clamp, lerp = gv.ease, gv.smooth, gv.clamp, gv.lerp
W, H, FPS, DUR = gv.W, gv.H, gv.FPS, 120.0
NFRAMES = int(DUR * FPS)
CYAN, CYAN2, WHITE, MUTED, AMBER, GREEN = gv.CYAN, gv.CYAN2, gv.WHITE, gv.MUTED, gv.AMBER, gv.GREEN
CARD = (6, 18, 46)
GRIDC = (22, 52, 104)
RED = (255, 107, 111)
VIOLET = (167, 139, 250)
ORANGE = (251, 146, 60)
IMG = HERE / 'img_v2'
MONO = 'C:/Windows/Fonts/consola.ttf'

# spezzoni: nome -> (file originale, inizio s, filtro di scala); 6,2 s ciascuno, audio sempre tolto (-an)
CLIP = {
    'tag': ('WhatsApp Video 2026-11-05 at 17.14.26.mp4', 1.0, 'deshake,scale=540:968:flags=lanczos'),
    'tondo': ('WhatsApp Video 2026-11-05 at 17.14.33.mp4', 3.0, 'deshake,scale=540:960:flags=lanczos'),
    'testa3d': ('WhatsApp Video 2026-11-06 at 21.48.24.mp4', 4.0, 'scale=1280:714:flags=lanczos'),
    'display': ('WhatsApp Video 2026-11-06 at 22.55.08.mp4', 2.0, 'scale=1280:714:flags=lanczos'),
    'cuffia': ('WhatsApp Video 2026-11-07 at 18.23.39.mp4', 2.0, 'scale=1280:720:flags=lanczos'),
}
CACHE = Path(os.environ.get('SWIMTIMER_CLIP_CACHE', Path(tempfile.gettempdir()) / 'swimtimer_video_v2_clip'))


def prepara_clip(cartella):
    for nome, (f, ss, vf) in CLIP.items():
        out = CACHE / nome
        if out.exists() and len(list(out.glob('*.jpg'))) >= 180:
            continue
        out.mkdir(parents=True, exist_ok=True)
        src_ = Path(cartella) / f
        if not src_.exists():
            sys.exit(f'Manca il video {src_}: indica la cartella con --clip-dir')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(ss), '-t', '6.2', '-i', str(src_), '-an',
                        '-vf', vf + ',fps=30,eq=contrast=1.07:saturation=1.1:gamma=1.02,unsharp=5:5:0.6',
                        '-q:v', '3', str(out / '%04d.jpg')], check=True)


# ---------------------------------------------------------------- sorgenti immagine (estende genera_video.src)
_src_orig = gv.src


@lru_cache(maxsize=None)
def src(key):
    if key[0] == 'f':                               # ('f', file in img_v2 o percorso dal ROOT, riquadro o None)
        p = IMG / key[1] if (IMG / key[1]).exists() else ROOT / key[1]
        im = Image.open(p)
        if im.mode == 'RGBA':
            bgc = Image.new('RGBA', im.size, (10, 26, 62, 255))
            bgc.alpha_composite(im)
            im = bgc
        im = im.convert('RGB')
        return im.crop(key[2]) if key[2] else im
    return _src_orig(key)


gv.src = src                                       # panel() e make_bg() di genera_video usano questa


def L(name):
    """Immagine nella lingua del video (landing e area riservata)."""
    return name.replace('{l}', LANG)


@lru_cache(maxsize=None)
def mfont(size):
    return ImageFont.truetype(MONO, size)


def TM(cv, s, x, y, size, t, t0, color=CYAN2, anchor='l', dur=0.4):
    """Testo monospaziato (formule, valori) con dissolvenza."""
    if t < t0:
        return
    s = tr(s)
    f = mfont(size)
    w = f.getlength(s)
    if anchor == 'c':
        x -= w / 2
    elif anchor == 'r':
        x -= w
    a = ease((t - t0) / dur)
    lay = Image.new('RGBA', (int(w) + 8, int(size * 1.4)), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((4, 0), s, font=f, fill=color + (int(255 * a),))
    cv.paste(lay, (int(x) - 4, int(y + (1 - a) * 12)), lay)


def num(v, dec):
    """Numero con la virgola decimale in italiano, il punto in inglese."""
    s = f'{v:.{dec}f}'
    return s.replace('.', ',') if LANG == 'it' else s


def chip(cv, s, x, y, t, t0, color=CYAN, size=34, fill=CARD, anchor='l'):
    """Etichetta arrotondata con bordo colorato. Restituisce la larghezza."""
    if t < t0:
        return 0
    lay, pad, dy, tw = tlayer(((s, color),), size, 600)
    w, h = int(tw + size * 1.1), int(size * 1.7)
    if anchor == 'c':
        x -= w / 2
    p = ease((t - t0) / 0.35)
    g = G(w, h)
    g.rrect((1, 1, w - 2, h - 2), h / 2, fill=fill + (235,), outline=color + (255,), width=3)
    im = g.im.resize((w, h), Image.LANCZOS)
    im.putalpha(im.getchannel('A').point(lambda v, k=p: int(v * k)))
    cv.paste(im, (int(x), int(y + (1 - p) * 20)), im)
    if p > 0.3:
        cv.paste(lay, (int(x + (w - tw) / 2 - pad), int(y + (1 - p) * 20 + (h - size * 1.18) / 2 - dy)), lay)
    return w


def check(cv, x, y, s=44, col=GREEN):
    g = G(s, s)
    g.ellipse((3, 3, s - 3, s - 3), outline=col + (255,), width=4)
    g.line([(s * 0.27, s * 0.52), (s * 0.43, s * 0.68), (s * 0.73, s * 0.34)], col + (255,), 5)
    g.paste_to(cv, int(x), int(y))


# ---------------------------------------------------------------- spezzoni video
@lru_cache(maxsize=8)
def _clip_frame(name, i):
    return Image.open(CACHE / name / f'{i + 1:04d}.jpg').convert('RGB')


def clip_img(name, ts):
    return _clip_frame(name, int(clamp(ts * FPS, 0, 179)))


def card_reveal_mask(w, h, p, rad, rev='x'):
    m = gv.rmask(w, h, rad)
    if p >= 1:
        return m
    k = Image.new('L', (w, h), 0)
    if rev == 'x':
        k.paste(255, (0, 0, max(1, int(w * p)), h))
    else:
        k.paste(255, (0, 0, w, max(1, int(h * p))))
    return ImageChops.multiply(m, k)


def clip_panel(cv, name, box, t, t0=0.2, z0=1.0, z1=1.08, cx=0.5, cy=0.5, rev='x', rad=22, label=None, ts0=0.0):
    """Spezzone orizzontale in un riquadro con bordo, ombra luminosa e leggero zoom."""
    if t < t0:
        return
    x, y, w, h = box
    fr = clip_img(name, t - t0 + ts0)
    z = lerp(z0, z1, smooth((t - t0) / 6.0))
    sw = fr.width / z
    sh = sw * h / w
    if sh > fr.height / z:
        sh = fr.height / z
        sw = sh * w / h
    x0 = clamp(cx * fr.width - sw / 2, 0, fr.width - sw)
    y0 = clamp(cy * fr.height - sh / 2, 0, fr.height - sh)
    tile = fr.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + sw, y0 + sh))
    p = ease((t - t0) / 0.6)
    g = gv.glow(w, h)
    cv.paste(Image.new('RGB', g.size, (20, 120, 200)), (x - 100, y - 100), g.point(lambda v, k=p: int(v * k)))
    cv.paste(tile, (x, y), card_reveal_mask(w, h, p, rad, rev))
    d = ImageDraw.Draw(cv)
    if p >= 1:
        d.rounded_rectangle((x, y, x + w, y + h), rad, outline=CYAN, width=3)
    if label and p >= 1:
        chip(cv, label, x + 22, y + h - 70, t, t0 + 0.7, CYAN, 28, (4, 12, 30))


def vclip_panel(cv, name, box, t, t0=0.2, label=None, ts0=0.0):
    """Spezzone verticale: riquadro con lo stesso video sfocato e scurito come sfondo, video nitido al centro."""
    if t < t0:
        return
    x, y, w, h = box
    fr = clip_img(name, t - t0 + ts0)
    p = ease((t - t0) / 0.6)
    # sfondo sfocato
    bw = w
    bh = int(bw * fr.height / fr.width)
    bgi = fr.resize((max(1, w // 8), max(1, bh // 8)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((w, bh), Image.BILINEAR)
    oy = (bh - h) // 2
    bgi = bgi.crop((0, oy, w, oy + h))
    bgi = Image.blend(bgi, Image.new('RGB', (w, h), (4, 14, 38)), 0.55)
    # video nitido
    z = lerp(1.0, 1.06, smooth((t - t0) / 6.0))
    vh = h - 40
    vw = int(vh * fr.width / fr.height)
    sw, sh = fr.width / z, fr.height / z
    vid = fr.resize((vw, vh), Image.BICUBIC, box=((fr.width - sw) / 2, (fr.height - sh) / 2, (fr.width + sw) / 2, (fr.height + sh) / 2))
    sh_ = Image.new('L', (vw + 60, vh + 60), 0)
    ImageDraw.Draw(sh_).rounded_rectangle((30, 30, 30 + vw, 30 + vh), 18, fill=170)
    sh_ = sh_.filter(ImageFilter.GaussianBlur(14))
    bgi.paste((0, 0, 0), ((w - vw) // 2 - 30, 20 - 22), sh_)
    bgi.paste(vid, ((w - vw) // 2, 20), gv.rmask(vw, vh, 16))
    gl = gv.glow(w, h)
    cv.paste(Image.new('RGB', gl.size, (20, 120, 200)), (x - 100, y - 100), gl.point(lambda v, k=p: int(v * k)))
    cv.paste(bgi, (x, y), card_reveal_mask(w, h, p, 22, 'y'))
    if p >= 1:
        ImageDraw.Draw(cv).rounded_rectangle((x, y, x + w, y + h), 22, outline=CYAN, width=3)
    if label and p >= 1:
        chip(cv, label, x + w // 2, y + h - 74, t, t0 + 0.7, CYAN, 28, (4, 12, 30), anchor='c')


# ---------------------------------------------------------------- grafici (segnali INVENTATI, calcolati una volta)
def _signals():
    r = np.random.default_rng(11)
    fs = 100
    t = np.arange(0, 12, 1 / fs)
    # fusione: angolo vero, giroscopio integrato con deriva, accelerometro rumoroso, complementare
    th = 22 * np.sin(2 * np.pi * 0.35 * t) + 9 * np.sin(2 * np.pi * 1.1 * t + 0.6)
    om = np.gradient(th, 1 / fs) + 4.5 + r.normal(0, 2.0, t.size)
    gyro = np.cumsum(om) / fs
    accp = th + r.normal(0, 7, t.size)
    fus = np.zeros_like(t)
    a = 0.98
    for i in range(1, t.size):
        fus[i] = a * (fus[i - 1] + om[i] / fs - 3.0 / fs * 0) + (1 - a) * accp[i]
    # pulizia: |omega| grezzo con bias e rumore, filtrato (passa-basso del 2 ordine), stima del bias da fermo
    swim = ((t > 3) & (t < 9)).astype(float)
    sm = np.convolve(swim, np.ones(40) / 40, 'same')
    w_true = sm * (60 * np.sin(2 * np.pi * 0.77 * t) + 25 * np.sin(2 * np.pi * 1.54 * t + 1))
    raw = w_true + 6.0 + r.normal(0, 9, t.size) + 7 * np.sin(2 * np.pi * 9 * t)
    lp = np.zeros_like(raw)
    k = 0.12
    s1 = s2 = raw[0]
    for i, v in enumerate(raw):
        s1 += k * (v - s1)
        s2 += k * (s1 - s2)
        lp[i] = s2
    bias = raw[(t < 2.6) | (t > 9.4)].mean()
    # segmentazione: |acc| su 20 s con fermo, nuoto, virata, nuoto, fermo
    t2 = np.arange(0, 20, 1 / fs)
    sw = (((t2 > 3) & (t2 < 9.2)) | ((t2 > 10.2) & (t2 < 16.5))).astype(float)
    sw = np.convolve(sw, np.ones(30) / 30, 'same')
    acc = 1 + sw * (0.35 * np.sin(2 * np.pi * 0.77 * t2) + 0.15 * np.sin(2 * np.pi * 1.54 * t2)) + r.normal(0, 0.03, t2.size)
    acc += -0.9 * np.exp(-((t2 - 9.3) / 0.25) ** 2) + 1.8 * np.exp(-((t2 - 10.1) / 0.18) ** 2) + 1.4 * np.exp(-((t2 - 3.05) / 0.15) ** 2)
    rot = 320 * np.exp(-((t2 - 9.6) / 0.35) ** 2)
    var = np.array([acc[max(0, i - 50):i + 50].var() for i in range(t2.size)])
    thr = np.array([np.median(var[max(0, i - 300):i + 1]) * 0.6 + 0.004 for i in range(t2.size)])
    # cadenza: autocorrelazione di un segnale di bracciata con periodo 1,3 s
    t3 = np.arange(0, 20, 1 / fs)
    st = np.sin(2 * np.pi * t3 / 1.3) + 0.4 * np.sin(4 * np.pi * t3 / 1.3 + 0.8) + r.normal(0, 0.35, t3.size)
    st -= st.mean()
    ac = np.correlate(st, st, 'full')[st.size - 1:]
    ac = ac / ac[0]
    lags = np.arange(ac.size) / fs
    m = lags <= 4
    return dict(t=t, th=th, gyro=gyro, accp=accp, fus=fus, raw=raw, lp=lp, bias=bias, t2=t2, acc=acc, rot=rot, var=var,
                thr=thr, sw=sw, lags=lags[m], ac=ac[m])


SIG = _signals()


def plot_card(cv, box, t, t0, series, x, yr, xr=None, reveal=2.5, grid=(8, 4), bands=(), marks=(), cursor=True, title=None):
    """Grafico su scheda: series = [(y, colore, spessore)], rivelato da sinistra a destra con un cursore."""
    if t < t0:
        return None
    bx, by, bw, bh = box
    p = ease((t - t0) / 0.5)
    g = G(bw, bh)
    g.rrect((0, 0, bw * p, bh), 22, fill=CARD + (240,), outline=(40, 110, 190, 255), width=3)
    if p < 1:
        g.paste_to(cv, bx, by)
        return None
    l, rgt, top, bot = 70, 30, 30 + (40 if title else 0), 50
    pw, ph = bw - l - rgt, bh - top - bot
    for k_ in range(grid[0] + 1):
        xx = l + pw * k_ / grid[0]
        g.line([(xx, top), (xx, top + ph)], GRIDC + (255,), 1)
    for k_ in range(grid[1] + 1):
        yy = top + ph * k_ / grid[1]
        g.line([(l, yy), (l + pw, yy)], GRIDC + (255,), 1)
    xr = xr or (x[0], x[-1])
    X = lambda v: l + (v - xr[0]) / (xr[1] - xr[0]) * pw          # noqa: E731
    Y = lambda v: top + ph - (np.clip(v, yr[0], yr[1]) - yr[0]) / (yr[1] - yr[0]) * ph  # noqa: E731
    u = clamp((t - t0 - 0.4) / reveal)
    xc = xr[0] + u * (xr[1] - xr[0])
    for (a0, a1, col) in bands:
        if a0 < xc:
            g.rrect((X(a0), top, X(min(a1, xc)), top + ph), 4, fill=col)
    n = max(2, int(len(x) * u))
    for (y, col, wd) in series:
        xs = X(x[:n])
        ys = Y(y[:n])
        step = max(1, n // 700)
        g.line(list(zip(xs[::step], ys[::step])), col + (255,), wd)
    for (xm, col) in marks:
        if xm <= xc:
            g.line([(X(xm), top), (X(xm), top + ph)], col + (230,), 3)
    if cursor and u < 1:
        g.line([(X(xc), top - 6), (X(xc), top + ph + 6)], WHITE + (200,), 2)
    g.paste_to(cv, bx, by)
    if title:
        T(cv, title, bx + l, by + 18, 30, t, t0 + 0.3, 600, MUTED)
    return dict(X=lambda v: bx + X(v), Y=lambda v: by + Y(v), xc=xc, u=u)


# ---------------------------------------------------------------- scene
def s_open(cv, t):
    for i, (k, r0, r1) in enumerate([(('f', 'display_serie.png', None), (0.3, .5, .5), (0.35, .5, .42)),
                                     (('f', 'strumenti_annotazione.png', (0, 280, 2880, 1000)), (0.4, .5, .5), (0.45, .5, .4)),
                                     (('f', 'hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/render_3d.png', None), (0.5, .5, .7), (0.5, .5, .55)),
                                     (('f', 'strumenti_dal_vivo.png', (0, 120, 1120, 820)), (0.5, .5, .7), (0.5, .45, .6)),
                                     (('f', 'strumenti_annotazione_virata.png', (0, 395, 2880, 990)), (0.6, .5, .5), (0.65, .5, .4))]):
        panel(cv, k, (i * 384, 0, 384, H), r0, r1, t, t0=0.05 + 0.15 * i, dur=8, alpha=0.11, reveal=0.8, rev='y', frame=False, rad=0, shadow=False)
    kicker(cv, 'AGGIORNAMENTO · NOVEMBRE 2026', t, 0.3, 610, 170)
    wipe_text(cv, (('SWIM', WHITE), ('TIMER', CYAN)), 960, 260, 250, t, 0.5, 1.0, 700)
    d = ImageDraw.Draw(cv)
    lp = ease((t - 1.6) / 0.8)
    d.rectangle((960 - int(520 * lp), 570, 960 + int(520 * lp), 575), fill=CYAN)
    T(cv, 'Tempi in vasca.', 960, 620, 76, t, 2.0, 400, (215, 230, 255), anchor='c')
    T(cv, 'Senza fermarti. Senza pulsanti.', 960, 720, 76, t, 2.8, 600, CYAN, anchor='c', maxw=1700)
    if t > 3.6:
        k = ease((t - 3.6) / 0.8)
        pts = [(x, 920 + k * math.exp(-((x - 960) / 520) ** 2) * 60 * math.sin(x / 22 - t * 7)) for x in range(160, 1761, 8)]
        d.line(pts, fill=CYAN, width=4)


def s_problem(cv, t):
    block(cv, t, 'LA SFIDA', [('Contare le vasche.', WHITE), ('Prendere i tempi.', WHITE), ('Mentre nuoti.', CYAN)],
          ['Senza fermarti, senza premere nulla.'], tsz=100, maxw=860, sub_size=46)
    # vasca vista dall'alto con il nuotatore che va e torna e il contatore delle vasche
    if t < 0.3:
        return
    bx, by, bw, bh = 1010, 250, 800, 560
    p = ease((t - 0.3) / 0.6)
    g = G(bw, bh)
    g.rrect((0, 0, bw * p, bh), 26, fill=(10, 60, 120, 255), outline=CYAN + (255,), width=4)
    if p >= 1:
        for ly in (bh * 0.25, bh * 0.75):
            for xx in range(30, bw - 20, 26):
                g.ellipse((xx, ly - 6, xx + 12, ly + 6), fill=(AMBER if (xx // 26) % 2 else RED) + (255,))
        g.line([(80, bh / 2), (bw - 80, bh / 2)], (6, 30, 70, 255), 10)
        ph = (t - 0.6) / 2.4
        lap = int(max(0, ph))
        f = max(0, ph) % 1
        xs = lerp(70, bw - 70, f if lap % 2 == 0 else 1 - f)
        ys = bh / 2 - 60 + 8 * math.sin(t * 9)
        for k_ in range(6):
            xx = xs - (k_ + 1) * 16 * (1 if lap % 2 == 0 else -1)
            g.ellipse((xx - 6 + k_, ys - 6 + k_, xx + 6 - k_, ys + 6 - k_), fill=(180, 230, 255, 140 - k_ * 20))
        g.ellipse((xs - 20, ys - 16, xs + 20, ys + 16), fill=(255, 130, 40, 255))
    g.paste_to(cv, bx, by)
    if p >= 1:
        lap = int(max(0, (t - 0.6) / 2.4)) + 1
        chip(cv, f'LAP {lap}', bx + 30, by + bh + 26, t, 0.9, CYAN, 36)
        v = max(0.0, t - 0.6) * 12.3
        TM(cv, f'{int(v // 60):02d}:{v % 60:05.2f}', bx + bw, by + bh + 22, 54, t, 0.9, WHITE, 'r')


def s_tag(cv, t):
    block(cv, t, 'IL TAG', [('Sotto la cuffia.', WHITE)], [], tsz=104, maxw=820, cy=200)
    T(cv, 'XIAO nRF52840 Sense', 110, 330, 56, t, 0.5, 600, CYAN, maxw=820)
    items = [('IMU 6 assi', 'accelerometro + giroscopio · 208 Hz', CYAN),
             ('Flash 2 MB', 'dati grezzi · compressione delta · CRC per pagina', GREEN),
             ('Bluetooth spento in acqua', 'il 2,4 GHz non attraversa l\'acqua', AMBER)]
    y = 450
    for i, (a, b, col) in enumerate(items):
        t0 = 1.0 + 0.8 * i
        if t >= t0:
            pp = ease((t - t0) / 0.4)
            ImageDraw.Draw(cv).rectangle((110, y + 6, 116, y + 6 + int(118 * pp)), fill=col)
        T(cv, a, 140, y, 54, t, t0, 700, WHITE, maxw=800)
        T(cv, b, 140, y + 70, 38, t, t0 + 0.15, 400, MUTED, maxw=800)
        y += 160
    # testa con cuffia, tag e onde del sensore; in basso un segnale a 208 Hz che scorre
    if t < 0.3:
        return
    g = G(820, 820)
    cx, hy, r = 410, 360, 230
    g.ellipse((cx - r, hy - r, cx + r, hy + r), fill=(18, 52, 112, 255), outline=CYAN + (255,), width=5)
    g.arc((cx - r - 14, hy - r - 14, cx + r + 14, hy + r + 14), 190, 350, (255, 130, 40, 255), 22)
    g.rrect((cx - 56, hy - r + 46, cx + 56, hy - r + 98), 10, fill=(250, 250, 255, 255), outline=CYAN + (255,), width=4)
    g.rrect((cx - 36, hy - r + 60, cx + 36, hy - r + 84), 4, fill=CYAN + (255,))
    for i in range(3):
        k = ((t * 0.7 + i / 3) % 1)
        rr = 70 + k * 210
        g.arc((cx - rr, hy - r + 72 - rr, cx + rr, hy - r + 72 + rr), 225, 315, CYAN + (int(255 * (1 - k)),), 6)
    wl = hy + 120
    pts = [(x, wl + 9 * math.sin(x / 50 + t * 2.2)) for x in range(0, 821, 12)]
    g.water(pts + [(820, 640), (0, 640)], (20, 90, 180, 150))
    g.line(pts, CYAN2 + (255,), 4)
    xs = np.linspace(40, 780, 260)
    ph = xs / 60 - t * 6
    sig = 40 * np.sin(ph) + 16 * np.sin(2.3 * ph + 1)
    g.line(list(zip(xs, 720 + sig)), CYAN2 + (255,), 4)
    g.line(list(zip(xs, 720 + 0.6 * np.roll(sig, 30) + 10 * np.sin(5 * ph))), (90, 160, 255, 200), 3)
    g.paste_to(cv, 1010, 150)
    TM(cv, '208 Hz · ±16 g · ±1000 dps', 1420, 950, 34, t, 1.2, CYAN2, 'c')


def s_ota(cv, t):
    block(cv, t, 'AGGIORNAMENTI', [('Firmware', WHITE), ('via Bluetooth.', CYAN)], ['OTA dal browser, senza cavi.'], tsz=100, maxw=820, cy=330, sub_size=46)
    # barra di aggiornamento OTA
    if t >= 1.0:
        p = clamp((t - 1.2) / 3.0)
        d = ImageDraw.Draw(cv)
        d.rounded_rectangle((110, 600, 830, 640), 20, fill=(10, 30, 70), outline=(40, 100, 180), width=2)
        if p > 0:
            d.rounded_rectangle((114, 604, 114 + int(712 * p), 636), 16, fill=CYAN if p < 1 else GREEN)
        TM(cv, f'DFU · Bluetooth LE   {int(p * 100):3d}%', 110, 660, 34, t, 1.0, WHITE if p < 1 else GREEN)
    kicker(cv, 'SCHEDA SU MISURA', t, 2.0, 110, 780)
    T(cv, 'v0.6 in arrivo', 190, 840, 72, t, 2.2, 700, AMBER, maxw=700)
    panel(cv, ('f', 'hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/render_3d.png', None), (960, 150, 860, 720),
          (0.5, 0.5, 1.0), (0.45, 0.5, 0.8), t, t0=0.2, dur=6)
    chip(cv, 'nRF52840 · v0.6', 960, 910, t, 1.6, AMBER, 30)


def s_live(cv, t):
    block(cv, t, 'DAL VIVO', [('La testa 3D', WHITE), ('segue la tua.', CYAN)], [], tsz=92, maxw=1700, cy=230)
    clip_panel(cv, 'cuffia', (110, 420, 840, 473), t, 0.2, 1.0, 1.08, 0.5, 0.45)
    clip_panel(cv, 'testa3d', (990, 420, 840, 473), t, 0.45, 1.25, 1.35, 0.33, 0.5)
    T(cv, 'Calibrazione in 3 fasi: scheda, posizionamento, test.', 960, 940, 46, t, 1.2, 400, MUTED, anchor='c', maxw=1700)


def s_live2(cv, t):
    block(cv, t, 'ANALISI DAL VIVO', [('Orientamento', WHITE), ('e grafici in diretta.', CYAN)], ['Pagina web: Bluetooth, USB, demo.'],
          tsz=84, maxw=700, cy=300, sub_size=42)
    vclip_panel(cv, 'tag', (1350, 110, 470, 920), t, 0.3)
    panel(cv, ('f', 'strumenti_dal_vivo.png', (0, 60, 1920, 1080)), (110, 560, 1200, 460), (0.5, 0.45, 1.0), (0.32, 0.4, 0.6), t, t0=0.6, dur=5.4)


def s_sync(cv, t):
    block(cv, t, 'METODO DEI TEST', [('Video + dati grezzi,', WHITE), ('allineati.', CYAN)], [], tsz=88, maxw=1100, cy=220)
    T(cv, '5 tocchi sul tag = picchi di sincronia', 110, 400, 44, t, 0.6, 400, MUTED, maxw=1100)
    panel(cv, ('f', 'strumenti_annotazione.png', (0, 395, 2880, 990)), (110, 500, 1710, 353), (0.5, 0.5, 1.0), (0.22, 0.45, 0.45), t, t0=0.3, dur=5.6)
    # 5 picchi animati sopra il pannello
    if t > 1.2:
        for i in range(5):
            t0 = 1.4 + 0.25 * i
            if t >= t0:
                k = ease((t - t0) / 0.3)
                x = 1320 + i * 92
                d = ImageDraw.Draw(cv)
                d.line((x, 440, x, 440 - int(70 * k)), fill=VIOLET if i == 4 else CYAN, width=6)
        chip(cv, 'X · SYNC', 1660, 900, t, 2.8, VIOLET, 34)
    TM(cv, 't_dati = t_video + offset', 110, 905, 40, t, 3.0, CYAN2)


def s_truth(cv, t):
    block(cv, t, 'ANNOTAZIONE', [('Ogni evento,', WHITE), ('a mano.', CYAN)], [], tsz=96, maxw=820, cy=170)
    panel(cv, ('f', 'strumenti_annotazione_virata.png', (0, 395, 2880, 990)), (110, 340, 1100, 280), (0.5, 0.5, 1.0), (0.6, 0.5, 0.8), t, t0=0.2, dur=3.8)
    panel(cv, ('f', 'strumenti_annotazione.png', (1900, 1830, 2860, 2260)), (1260, 340, 560, 250), (0.5, 0.5, 1.0), (0.48, 0.45, 0.92), t, t0=0.4, dur=3.6)
    evs = [('P', 'Partenza', GREEN), ('V', 'Inizio virata', AMBER), ('F', 'Fine virata', ORANGE), ('A', 'Arrivo', RED)]
    x = 110
    for i, (k, s, col) in enumerate(evs):
        w = chip(cv, f'{k}  ' + tr(s), x, 690, t, 0.8 + 0.3 * i, col, 38)
        x += w + 24
    # flusso degli eventi verso il dataset
    if t > 2.0:
        d = ImageDraw.Draw(cv)
        k = ease((t - 2.0) / 0.8)
        d.rounded_rectangle((110, 830, 110 + int(1710 * k), 960), 24, fill=(8, 26, 60), outline=CYAN, width=3)
        for j in range(26):
            xx = 150 + j * 64
            if xx < min(110 + 1710 * k - 40, 1150):
                col = [GREEN, CYAN, AMBER, ORANGE, CYAN, RED][j % 6]
                hgt = 20 + 40 * ((j * 7) % 5) / 4
                d.rounded_rectangle((xx, 935 - hgt, xx + 30, 935), 6, fill=col)
        T(cv, 'DATASET DI VERITÀ', 1790, 852, 52, t, 2.6, 700, WHITE, anchor='r', track=3)
    # tensione del build-up: barra che si riempie
    pp = clamp((t - 0.2) / 3.8)
    ImageDraw.Draw(cv).rectangle((0, 0, int(W * pp), 6), fill=CYAN)


def filt_head(cv, t, k, title, subs):
    block(cv, t, k, title, subs, tsz=92, maxw=720, cy=330, sub_size=40, t0=0.1)


def s_fusion(cv, t):
    filt_head(cv, t, 'FILTRI · 1', [('Fusione', WHITE), ('sensoriale.', CYAN)], ['Accelerometro + giroscopio', 'filtro complementare / Madgwick'])
    S = SIG
    r = plot_card(cv, (900, 110, 920, 640), t, 0.2, [(S['accp'], (110, 130, 170), 2), (S['gyro'], AMBER, 3), (S['fus'], CYAN, 5)],
                  S['t'], (-60, 80), reveal=3.0)
    if r:
        TM(cv, 'θ = α·(θ + ω·Δt) + (1−α)·θ_acc', 1360, 790, 38, t, 1.0, WHITE, 'c')
        x = 900
        for i, (s, col) in enumerate([('fusione: stabile', CYAN), ('giroscopio integrato: deriva', AMBER), ('accelerometro: rumore', (150, 170, 210))]):
            w = chip(cv, s, x, 870, t, 1.6 + 0.3 * i, col, 28)
            x += w + 16
    TM(cv, 'Madgwick: q, 208 Hz', 110, 700, 40, t, 2.4, CYAN2)


def s_clean(cv, t):
    filt_head(cv, t, 'FILTRI · 2', [('Segnale', WHITE), ('pulito.', CYAN)], ['Passa-basso e passa-banda', 'bias del giroscopio stimato da fermo'])
    S = SIG
    r = plot_card(cv, (900, 110, 920, 640), t, 0.2, [(S['raw'], (100, 120, 165), 2), (S['lp'], CYAN, 5)], S['t'], (-110, 130), reveal=3.0,
                  bands=[(0, 2.6, (255, 190, 60, 40)), (9.4, 12, (255, 190, 60, 40))])
    if r:
        y = r['Y'](S['bias'])
        if r['xc'] > 2.6:
            ImageDraw.Draw(cv).line((r['X'](0), y, r['X'](2.6), y), fill=AMBER, width=4)
            TM(cv, 'bias ≈ ' + num(S['bias'], 1) + ' °/s', r['X'](0.1), r['Y'](125), 28, t, 1.4, AMBER)
        x = 900 + chip(cv, 'FERMO · stima del bias', 900, 870, t, 1.6, AMBER, 28) + 16
        x += chip(cv, 'grezzo', x, 870, t, 1.9, (150, 170, 210), 28) + 16
        chip(cv, 'filtrato', x, 870, t, 2.2, CYAN, 28)
    TM(cv, 'y[n] = y[n−1] + k·(x[n] − y[n−1])', 110, 700, 34, t, 2.4, CYAN2)


def s_segment(cv, t):
    filt_head(cv, t, 'FILTRI · 3', [('Fermo', WHITE), ('o nuoto?', CYAN)], ['Varianza su finestra mobile', 'soglie adattive · rilevamento dei picchi'])
    S = SIG
    sw = S['sw']
    bands = []
    cur, st = sw[0] > 0.5, 0
    for i in range(1, len(sw)):
        c = sw[i] > 0.5
        if c != cur or i == len(sw) - 1:
            bands.append((S['t2'][st], S['t2'][i], (40, 210, 255, 34) if cur else (120, 140, 180, 26)))
            cur, st = c, i
    bands.append((9.2, 10.2, (255, 190, 60, 60)))
    r = plot_card(cv, (900, 90, 920, 380), t, 0.2, [(S['acc'], CYAN, 3)], S['t2'], (0, 3.2), reveal=3.0, bands=bands, grid=(10, 3))
    r2 = plot_card(cv, (900, 490, 920, 300), t, 0.5, [(S['var'], GREEN, 4), (S['thr'], AMBER, 3)], S['t2'], (0, 0.12), reveal=3.0, grid=(10, 3))
    if r:
        for x0, lab, col in ((1.2, 'FERMO', (170, 185, 215)), (5.5, 'NUOTO', CYAN), (9.25, 'VIRATA', AMBER), (13, 'NUOTO', CYAN)):
            if r['xc'] > x0 + 0.8:
                T(cv, lab, r['X'](x0), 120, 28, t, 0, 700, col, track=2)
    if r2:
        T(cv, 'varianza (finestra 1 s)', 990, 505, 26, t, 1.0, 600, GREEN)
        T(cv, 'soglia adattiva', 1500, 505, 26, t, 1.3, 600, AMBER)
    T(cv, 'firma della virata: rotazione > 250 °/s + frenata + spinta', 900, 830, 34, t, 2.4, 600, WHITE, maxw=920)
    TM(cv, 'σ²(t) = var(|a|, t ± ' + num(0.5, 1) + ' s)', 110, 700, 34, t, 2.6, CYAN2)


def s_cadence(cv, t):
    filt_head(cv, t, 'FILTRI · 4', [('Cadenza', WHITE), ('e fiducia.', CYAN)], ['Autocorrelazione della bracciata', 'punteggio di confidenza per evento'])
    S = SIG
    pk = 1.3
    r = plot_card(cv, (900, 90, 560, 470), t, 0.2, [(S['ac'], CYAN, 4)], S['lags'], (-0.8, 1.05), reveal=2.2, grid=(4, 4), marks=[(pk, AMBER)])
    if r and r['xc'] > pk:
        d = ImageDraw.Draw(cv)
        x, y = r['X'](pk), r['Y'](float(np.interp(pk, S['lags'], S['ac'])))
        d.ellipse((x - 10, y - 10, x + 10, y + 10), outline=AMBER, width=4)
        TM(cv, 'T = ' + num(1.30, 2) + ' s → 46 /min', x + 20, r['Y'](-0.62), 28, t, 1.6, AMBER)
    T(cv, 'ritardo (s)', 1180, 520, 24, t, 0.8, 400, MUTED, anchor='c')
    # punteggi di confidenza
    if t >= 0.5:
        p = ease((t - 0.5) / 0.4)
        g = G(340, 470)
        g.rrect((0, 0, 340, 470 * p), 22, fill=CARD + (240,), outline=(40, 110, 190, 255), width=3)
        g.paste_to(cv, 1480, 90)
        evs = [('P', 0.97, GREEN), ('V', 0.91, AMBER), ('F', 0.86, ORANGE), ('V', 0.62, AMBER), ('A', 0.95, RED)]
        for i, (k, c, col) in enumerate(evs):
            t0 = 1.0 + 0.25 * i
            if t < t0:
                continue
            y = 130 + i * 84
            u = ease((t - t0) / 0.6)
            d = ImageDraw.Draw(cv)
            T(cv, k, 1510, y, 40, t, t0, 700, col)
            d.rounded_rectangle((1560, y + 14, 1560 + 170, y + 34), 10, fill=(20, 45, 90))
            d.rounded_rectangle((1560, y + 14, 1560 + int(170 * c * u), y + 34), 10, fill=col if c > 0.7 else (150, 150, 170))
            TM(cv, f'{c * u:.2f}', 1745, y + 6, 30, t, t0, WHITE if c > 0.7 else (200, 160, 160))
    for i, s in enumerate(['Validazione per sessione, non per evento', 'Obiettivo: elaborazione quasi in tempo reale sul tag']):
        t0 = 2.2 + 0.5 * i
        if t >= t0:
            check(cv, 900, 610 + i * 90, 46, GREEN if i == 0 else CYAN)
        T(cv, s, 965, 612 + i * 90, 38, t, t0, 600, WHITE, maxw=860)
    TM(cv, 'R(τ) = Σ x(t)·x(t+τ)', 110, 700, 34, t, 2.6, CYAN2)


def s_platform(cv, t):
    block(cv, t, 'PIATTAFORMA', [('Online.', WHITE), ('Aperta.', CYAN)], ['Sito pubblico in italiano e inglese.'], tsz=110, maxw=700, cy=400, sub_size=42)
    TM(cv, 'swimtimer-pzero.web.app', 110, 660, 40, t, 1.4, CYAN)
    off = 28 if LANG == 'en' else 0
    panel(cv, ('f', L('landing_{l}.png'), (300, 0, 1620, 900)), (900, 90, 920, 627), (0.5, 0.3, 1.0), (0.5, 0.35, 0.9), t, t0=0.2, dur=6)
    panel(cv, ('f', L('landing_{l}.png'), (360, 1300 + off, 1560, 2110 + off)), (900, 760, 450, 300), (0.5, 0.5, 1.0), (0.5, 0.5, 0.85), t, t0=0.8, dur=5)
    panel(cv, ('f', L('landing_{l}.png'), (360, 3170 + off, 1560, 3720 + off)), (1370, 760, 450, 300), (0.5, 0.5, 1.0), (0.5, 0.5, 0.85), t, t0=1.1, dur=5)


def s_access(cv, t):
    block(cv, t, 'ACCESSO', [('Solo membri', WHITE), ('approvati.', CYAN)], [], tsz=92, maxw=740, cy=230)
    steps = [(L('area_{l}_login.png'), 'Accedi con Google', CYAN), (L('area_{l}_attesa.png'), 'In attesa', AMBER),
             (None, 'L\'admin approva', GREEN)]
    for i, (f, lab, col) in enumerate(steps):
        t0 = 0.5 + 0.8 * i
        y = 430 + i * 190
        if t >= t0:
            k = ease((t - t0) / 0.35)
            d = ImageDraw.Draw(cv)
            r = int(32 * k)
            d.ellipse((142 - r, y + 32 - r, 142 + r, y + 32 + r), fill=col)
            if i < 2:
                d.line((142, y + 74, 142, y + 74 + int(110 * ease((t - t0 - 0.4) / 0.5))), fill=(40, 90, 160), width=4)
        T(cv, str(i + 1), 142, y + 4, 42, t, t0 + 0.15, 700, (4, 14, 38), anchor='c')
        T(cv, lab, 200, y + 6, 46, t, t0 + 0.2, 600, WHITE, maxw=360)
        if f:
            panel(cv, ('f', f, (600, 170, 1320, 470)), (560, y - 30, 300, 125), (0.5, 0.5, 1.0), (0.5, 0.5, 1.0), t, t0=t0 + 0.2, dur=1, rad=12)
    panel(cv, ('f', L('area_{l}_admin_admin.png'), (180, 130, 1490, 860)), (900, 140, 920, 513), (0.5, 0.5, 1.0), (0.5, 0.5, 1.0), t, t0=0.3, dur=1)
    if t >= 2.9:
        k = clamp((t - 2.9) / 0.7)
        bx, by = APPROVA
        d = ImageDraw.Draw(cv)
        rr = 18 + 50 * k
        d.ellipse((bx - rr, by - rr, bx + rr, by + rr), outline=GREEN, width=max(1, int(6 * (1 - k)) + 1))
        g = G(40, 52)
        g.poly([(4, 2), (4, 40), (14, 31), (21, 48), (28, 45), (21, 29), (34, 29)], (255, 255, 255, 255))
        g.line([(4, 2), (4, 40), (14, 31), (21, 48), (28, 45), (21, 29), (34, 29), (4, 2)], (4, 14, 38, 255), 2)
        g.paste_to(cv, bx + 4, by + 2)


APPROVA = (int(900 + 920 * (1350 - 180) / 1310), int(140 + 513 * (265 - 130) / 730))


def s_shared(cv, t):
    block(cv, t, 'COLLABORAZIONE', [('Dati condivisi,', WHITE), ('verificabili.', CYAN)], [], tsz=92, maxw=780, cy=200)
    items = [('Sessioni .swr grezze condivise', CYAN), ('Video verificati con impronta SHA-256', GREEN), ('Annotazioni con autore', AMBER),
             ('Firebase, piano gratuito', VIOLET)]
    y = 420
    for i, (s, col) in enumerate(items):
        t0 = 0.8 + 0.5 * i
        if t >= t0:
            check(cv, 110, y, 48, col)
        T(cv, s, 180, y + 2, 42, t, t0, 600, WHITE, maxw=660)
        y += 105
    TM(cv, 'sha256: 7c41e9a2b0…', 110, 860, 32, t, 2.8, GREEN)
    panel(cv, ('f', L('area_{l}_admin_sessioni.png'), (150, 60, 1100, 900)), (900, 140, 920, 813), (0.5, 0.5, 1.0), (0.42, 0.42, 0.82), t, t0=0.2, dur=6)


def s_display(cv, t):
    block(cv, t, 'A BORDO VASCA', [('Il display.', WHITE)], ['7 nuotatori, tempi, ritmo', 'e livello di sforzo.'], tsz=100, maxw=560, cy=330, sub_size=40, x=110)
    panel(cv, ('f', 'display_serie.png', None), (720, 110, 1100, 619), (0.5, 0.5, 1.0), (0.42, 0.45, 0.8), t, t0=0.2, dur=6)
    chip(cv, 'Mockup con dati inventati', 720, 770, t, 1.6, AMBER, 30)
    panel(cv, ('f', 'display_serie.png', (0, 0, 980, 260)), (110, 830, 560, 149), (0.5, 0.5, 1.0), (0.4, 0.5, 0.8), t, t0=1.2, dur=4.8)


def s_display2(cv, t):
    block(cv, t, 'PROTOTIPI', [('Dal mockup', WHITE), ('al banco.', CYAN)], ['Display rotondo a lancette, cella 1000 mAh.'], tsz=88, maxw=1000, cy=250, sub_size=40)
    clip_panel(cv, 'display', (110, 500, 1000, 540), t, 0.2, 1.0, 1.1, 0.5, 0.5)
    vclip_panel(cv, 'tondo', (1250, 110, 570, 930), t, 0.5)


def s_roadmap(cv, t):
    kicker(cv, 'ROADMAP', t, 0.2, 110, 130)
    T(cv, 'Prossima tappa: la vasca.', 110, 210, 92, t, 0.35, 700, WHITE, maxw=1700)
    nodes = [('Tag e registrazione', 'fatto'), ('Piattaforma online', 'fatto'), ('Test 1 · vasca da 50 m', 'ora'),
             ('Filtri automatici', 'poi'), ('Più nuotatori', 'poi')]
    xs = [230, 595, 960, 1325, 1690]
    ly = 600
    d = ImageDraw.Draw(cv)
    prog = clamp((t - 0.9) / 3.2)
    d.line((xs[0], ly, xs[-1], ly), fill=(30, 70, 140), width=8)
    d.line((xs[0], ly, int(lerp(xs[0], xs[2], min(1, prog * 1.6))), ly), fill=CYAN, width=8)
    for i, (x, (lab, st)) in enumerate(zip(xs, nodes)):
        t0 = 0.9 + 0.55 * i
        if t < t0:
            continue
        k = ease((t - t0) / 0.4)
        col = GREEN if st == 'fatto' else (AMBER if st == 'ora' else (90, 130, 190))
        r = int(34 * k)
        if st == 'ora':
            rr = r + 10 + 8 * math.sin(t * 6)
            d.ellipse((x - rr, ly - rr, x + rr, ly + rr), outline=AMBER, width=3)
        d.ellipse((x - r, ly - r, x + r, ly + r), fill=col if st != 'poi' else CARD, outline=col, width=6)
        if st == 'fatto' and k >= 1:
            g = G(40, 40)
            g.line([(9, 21), (17, 29), (31, 12)], (4, 14, 38, 255), 6)
            g.paste_to(cv, x - 20, ly - 20)
        up = i % 2 == 0
        T(cv, lab, x, ly + 70 if up else ly - 150, 44, t, t0 + 0.1, 600, WHITE if st != 'poi' else MUTED, anchor='c', maxw=420)
        chip(cv, st.upper() if LANG == 'it' else tr(st).upper(), x, ly + 135 if up else ly - 85, t, t0 + 0.2, col, 26, anchor='c')


def s_close(cv, t):
    gv.waves(cv, t, 960, (30, 100, 180), 12, 3, 26)
    kicker(cv, 'PROGETTO APERTO', t, 0.3, 700, 130)
    wipe_text(cv, (('SWIM', WHITE), ('TIMER', CYAN)), 960, 220, 230, t, 0.5, 1.0, 700)
    d = ImageDraw.Draw(cv)
    lp = ease((t - 1.4) / 0.8)
    d.rectangle((960 - int(480 * lp), 500, 960 + int(480 * lp), 505), fill=CYAN)
    T(cv, 'Progetto aperto · prototipo in sviluppo', 960, 535, 52, t, 1.8, 600, MUTED, anchor='c', maxw=1500)
    rows = [('WEB', 'swimtimer-pzero.web.app'), ('EMAIL', 'SmartSwimTimer@gmail.com'), ('GITHUB', 'PZero/SwimTimer')]
    for i, (k, v) in enumerate(rows):
        t0 = 2.6 + 0.4 * i
        y = 650 + i * 82
        T(cv, k, 900, y + 8, 34, t, t0, 600, CYAN, anchor='r', track=3)
        T(cv, v, 940, y, 54, t, t0 + 0.1, 600, WHITE)


# (inizio, durata, funzione, sfondo(key, cy, strength))
SCENES = [
    (0, 6, s_open, None),
    (6, 6, s_problem, None),
    (12, 8, s_tag, None),
    (20, 6, s_ota, (('f', 'hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/render_sopra.png', None), 0.5, 0.25)),
    (26, 6, s_live, None),
    (32, 6, s_live2, (('f', 'strumenti_dal_vivo.png', None), 0.5, 0.25)),
    (38, 6, s_sync, None),
    (44, 4, s_truth, None),
    (48, 6, s_fusion, None),
    (54, 6, s_clean, None),
    (60, 6, s_segment, None),
    (66, 6, s_cadence, None),
    (72, 6, s_platform, None),
    (78, 6, s_access, None),
    (84, 6, s_shared, None),
    (90, 6, s_display, (('f', 'display_serie.png', None), 0.5, 0.3)),
    (96, 6, s_display2, None),
    (102, 8, s_roadmap, None),
    (110, 10, s_close, None),
]
TRANS = ['push', 'wipe', 'dissolve', 'pushup', 'zoom', 'wipe', 'push', 'zoom', 'pushup', 'push', 'wipe',
         'dissolve', 'pushup', 'push', 'wipe', 'zoom', 'pushup', 'dissolve']
CHAP = {s[2].__name__: c for s, c in zip(SCENES, [None, None, '01', '01', '02', '02', '03', '03', '04', '04', '04', '04', '05', '05', '05',
                                                   '06', '06', '07', None])}


def scene_frame(k, ts):
    st, du, fn, bgs = SCENES[k]
    bg = gv.make_bg(*bgs).copy() if bgs else gv.make_bg().copy()
    gv.bubbles(bg, ts + st)
    fn(bg, ts)
    c = CHAP[fn.__name__]
    if c:
        lay, pad, dy, tw = tlayer(((c, CYAN), (' / 07', (70, 110, 170))), 30, 600)
        bg.paste(lay, (int(1810 - tw - pad), int(36 - dy)), lay)
    return bg


def frame_image(i):
    t = i / FPS
    k = max(j for j, s in enumerate(SCENES) if s[0] <= t + 1e-9)
    ts = t - SCENES[k][0]
    img = scene_frame(k, ts)
    if k > 0 and ts < 0.4:
        a = scene_frame(k - 1, t - SCENES[k - 1][0])
        img = gv.transition(a, img, TRANS[(k - 1) % len(TRANS)], ts / 0.4)
    if 48 <= t < 48.3:                                   # lampo sul drop
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.5 * (1 - (t - 48) / 0.3))
    if 118.0 <= t < 118.2:                               # stacco finale
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.3 * (1 - (t - 118) / 0.2))
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 6, int(W * t / DUR), H), fill=CYAN)
    if t > 118.6:
        img = Image.blend(img, Image.new('RGB', (W, H), (0, 0, 0)), clamp((t - 118.6) / 1.3))
    return img


def frame_bytes(i):
    return frame_image(i).tobytes()


def miniatura(path):
    bg = gv.make_bg(('f', 'display_serie.png', None), 0.5, 0.35).copy()
    gv.waves(bg, 1.0, 930, (40, 120, 200), 14, 4, 26)
    panel(bg, ('f', 'display_serie.png', None), (1000, 110, 820, 461), (0.5, 0.5, 1.0), (0.5, 0.5, 1.0), 9, t0=0, dur=1)
    panel(bg, ('f', 'strumenti_annotazione_virata.png', (0, 330, 2880, 1000)), (1000, 620, 820, 190), (0.5, 0.5, 1.0), (0.5, 0.5, 1.0), 9, t0=0, dur=1)
    panel(bg, ('f', 'hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/render_3d.png', None), (1560, 760, 260, 220), (0.5, 0.5, 0.9), (0.5, 0.5, 0.9), 9, t0=0, dur=1)
    T(bg, 'SWIM', 100, 150, 240, 9, 0, 700, WHITE)
    T(bg, 'TIMER', 100, 350, 240, 9, 0, 700, CYAN)
    ImageDraw.Draw(bg).rectangle((110, 640, 640, 646), fill=CYAN)
    T(bg, 'A che punto siamo', 110, 680, 84, 9, 0, 700, WHITE, maxw=860)
    T(bg, 'Tag, dati, filtri, piattaforma', 110, 790, 54, 9, 0, 600, CYAN, maxw=860)
    bg.resize((1280, 720), Image.LANCZOS).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anteprima', nargs='*', type=float)
    ap.add_argument('--dir', default=str(HERE))
    ap.add_argument('--clip-dir', default=str(Path.home() / 'Downloads' / 'VideoTMP'))
    ap.add_argument('--solo-musica', action='store_true')
    ap.add_argument('--solo-miniatura', action='store_true')
    ap.add_argument('--no-musica', action='store_true')
    ap.add_argument('--lingua', choices=['it', 'en'], default='it')
    a = ap.parse_args()
    if a.lingua != LANG:
        env = dict(os.environ, SWIMTIMER_LANG=a.lingua)
        sys.exit(subprocess.call([sys.executable, __file__] + sys.argv[1:], env=env))
    if not a.solo_musica and not a.solo_miniatura:
        prepara_clip(a.clip_dir)
    if a.anteprima:
        Path(a.dir).mkdir(parents=True, exist_ok=True)
        for tsec in a.anteprima:
            frame_image(int(round(tsec * FPS))).save(Path(a.dir) / f'v2_{LANG}_{tsec:06.2f}.png')
        return
    if a.solo_miniatura:
        miniatura(HERE / f'miniatura_avanzamento_{LANG}.png')
        return
    wav = HERE / 'musica_v2.wav'
    if not a.no_musica or not wav.exists():
        import musica_v2
        y, lufs, peak = musica_v2.compose(wav)
        print(f'Musica: {lufs} LUFS, picco {peak} dBFS')
    if a.solo_musica:
        return
    miniatura(HERE / f'miniatura_avanzamento_{LANG}.png')
    out = HERE / f'SwimTimer_avanzamento_{LANG}.mp4'
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-i', str(wav), '-map', '0:v', '-map', '1:a',
           '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-maxrate', '8M', '-bufsize', '16M', '-g', '60',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-t', str(DUR), '-movflags', '+faststart', str(out)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(max(2, (os.cpu_count() or 4) - 1)) as pool:
        for n, fb in enumerate(pool.imap(frame_bytes, range(NFRAMES), chunksize=8)):
            pr.stdin.write(fb)
            if n % 300 == 0:
                print(f'fotogramma {n}/{NFRAMES}', flush=True)
    pr.stdin.close()
    pr.wait()
    print('Fatto:', out)


if __name__ == '__main__':
    main()
