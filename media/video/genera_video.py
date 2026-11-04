"""Genera il video di presentazione di SwimTimer (1920x1080, 30 fps, 120 s).

Uso:  python media/video/genera_video.py            (musica + video + miniatura)
      python media/video/genera_video.py --anteprima 12 47.5 63 --dir CARTELLA   (solo fotogrammi PNG)
      python media/video/genera_video.py --solo-musica | --solo-miniatura
Tutti i fotogrammi sono disegnati con Pillow; la codifica e' fatta da ffmpeg.
"""
import argparse
import glob
import math
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WALL = ROOT / 'hardware' / 'wallpaper_v0.5' / 'png'
RJLC = ROOT / 'hardware' / 'nrf52840' / 'kicad' / 'jlc' / 'v0.5_swimtag_economica'
RPROG = ROOT / 'hardware' / 'programmatore' / 'img'
FONT = 'C:/Windows/Fonts/bahnschrift.ttf'
W, H, FPS, DUR = 1920, 1080, 30, 120.0
NFRAMES = int(DUR * FPS)

BG0, BG1 = (4, 9, 28), (9, 30, 74)
CYAN = (40, 210, 255)
CYAN2 = (130, 232, 255)
WHITE = (245, 250, 255)
MUTED = (178, 205, 240)
AMBER = (255, 190, 60)
GREEN = (80, 230, 170)


# ---------------------------------------------------------------- utilita'
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def smooth(p):
    p = clamp(p)
    return p * p * (3 - 2 * p)


def lerp(a, b, u):
    return a + (b - a) * u


@lru_cache(maxsize=None)
def font(size, wght=700, width=100):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([wght, width])
    return f


def text_len(s, size, wght, track=0, width=100):
    f = font(size, wght, width)
    if not track:
        return f.getlength(s)
    return sum(f.getlength(c) + track for c in s) - track


def fit_size(s, maxw, size, wght, track=0, width=100):
    while size > 20 and text_len(s, size, wght, track, width) > maxw:
        size -= 2
    return size


@lru_cache(maxsize=1024)
def tlayer(parts, size, wght, track=0, width=100):
    """parts: tuple di (testo, colore). Restituisce (immagine RGBA, pad, dy, larghezza)."""
    f = font(size, wght, width)
    tw = int(sum(text_len(p[0], size, wght, track, width) + (track if track else 0) for p in parts)) + 2
    pad = int(size * 0.3) + 4
    dy = int(size * 0.18)
    im = Image.new('RGBA', (tw + 2 * pad, int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for txt, col in parts:
        if track:
            for c in txt:
                d.text((x, dy), c, font=f, fill=col + (255,))
                x += f.getlength(c) + track
        else:
            d.text((x, dy), txt, font=f, fill=col + (255,))
            x += f.getlength(txt)
    return im, pad, dy, tw


def T(cv, s, x, y, size, t, t0, wght=700, color=WHITE, track=0, anchor='l', dur=0.5, maxw=None, width=100):
    """Testo con ingresso a scorrimento+maschera. y = alto della riga."""
    if t < t0:
        return
    parts = s if isinstance(s, tuple) else ((s, color),)
    full = ''.join(p[0] for p in parts)
    if maxw:
        size = fit_size(full, maxw, size, wght, track, width)
    lay, pad, dy, tw = tlayer(parts, size, wght, track, width)
    if anchor == 'c':
        x = x - tw / 2
    elif anchor == 'r':
        x = x - tw
    p = ease((t - t0) / dur)
    pos = (int(x - pad), int(y - dy))
    if p >= 1:
        cv.paste(lay, pos, lay)
        return
    tmp = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    tmp.paste(lay, (0, int((1 - p) * lay.height * 0.75)))
    a = tmp.getchannel('A').point(lambda v, k=min(1.0, p * 1.8): int(v * k))
    tmp.putalpha(a)
    cv.paste(tmp, pos, tmp)


def wipe_text(cv, parts, x, y, size, t, t0, dur=1.0, wght=700, anchor='c', track=0):
    """Titolo con rivelazione a maschera da sinistra e barra ciano sul bordo."""
    if t < t0:
        return
    lay, pad, dy, tw = tlayer(parts, size, wght, track)
    if anchor == 'c':
        x = x - tw / 2
    p = smooth((t - t0) / dur)
    cw = int(lay.width * p)
    if cw > 0:
        crop = lay.crop((0, 0, cw, lay.height))
        cv.paste(crop, (int(x - pad), int(y - dy)), crop)
    if p < 1:
        ex = int(x - pad + cw)
        ImageDraw.Draw(cv).rectangle((ex, int(y), ex + 10, int(y + size * 1.1)), fill=CYAN)


# ---------------------------------------------------------------- immagini
@lru_cache(maxsize=None)
def src(key):
    kind, name = key
    if kind == 'w':
        f = glob.glob(str(WALL / f'{name:02d}_*_1170x2532.png'))[0]
        return Image.open(f).convert('RGB')
    if kind == 'r':
        return Image.open(RJLC / f'render_{name}.png').convert('RGB')
    im = Image.open(RPROG / f'render_{name}.png').convert('RGBA')
    bgc = Image.new('RGBA', im.size, (10, 26, 62, 255))
    bgc.alpha_composite(im)
    return bgc.convert('RGB')


def kb(im, bw, bh, r0, r1, u):
    cx, cy, w = (lerp(r0[i], r1[i], u) for i in range(3))
    cw = w * im.width
    ch = cw * bh / bw
    if ch > im.height:
        cw *= im.height / ch
        ch = im.height
    if cw > im.width:
        ch *= im.width / cw
        cw = im.width
    x0 = clamp(cx * im.width - cw / 2, 0, im.width - cw)
    y0 = clamp(cy * im.height - ch / 2, 0, im.height - ch)
    return im.resize((bw, bh), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


@lru_cache(maxsize=None)
def rmask(w, h, rad):
    m = Image.new('L', (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 3 - 1, h * 3 - 1), rad * 3, fill=255)
    return m.resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=64)
def glow(w, h):
    g = Image.new('L', (w + 200, h + 200), 0)
    ImageDraw.Draw(g).rounded_rectangle((100, 100, 100 + w, 100 + h), 24, fill=110)
    return g.filter(ImageFilter.GaussianBlur(34))


def panel(cv, key, box, r0, r1, t, t0=0.2, dur=5.0, alpha=1.0, reveal=0.6, rev='x', frame=True, rad=18, shadow=True):
    if t < t0:
        return
    x, y, w, h = box
    u = smooth((t - t0) / max(dur, 0.01))
    tile = kb(src(key), w, h, r0, r1, u)
    p = ease((t - t0) / reveal)
    mask = rmask(w, h, rad)
    if p < 1:
        m = Image.new('L', (w, h), 0)
        if rev == 'x':
            m.paste(255, (0, 0, max(1, int(w * p)), h))
        else:
            m.paste(255, (0, 0, w, max(1, int(h * p))))
        mask = ImageChops.multiply(mask, m)
    if shadow and alpha >= 1:
        g = glow(w, h)
        cv.paste(Image.new('RGB', g.size, (20, 120, 200)), (x - 100, y - 100), g.point(lambda v, k=p: int(v * k)))
    if alpha < 1:
        mask = mask.point(lambda v, a=alpha: int(v * a))
    cv.paste(tile, (x, y), mask)
    d = ImageDraw.Draw(cv)
    if frame and alpha >= 1:
        if p >= 1:
            d.rounded_rectangle((x, y, x + w, y + h), rad, outline=CYAN, width=3)
        else:
            if rev == 'x':
                ex = x + int(w * p)
                d.rectangle((ex - 2, y, ex + 3, y + h), fill=CYAN)
            else:
                ey = y + int(h * p)
                d.rectangle((x, ey - 2, x + w, ey + 3), fill=CYAN)


class G:
    """Disegno anti-aliasing (supercampionato x2) su livello RGBA."""

    def __init__(s, w, h, k=2):
        s.w, s.h, s.k = w, h, k
        s.im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
        s.d = ImageDraw.Draw(s.im)

    def _pt(s, pts):
        return [(x * s.k, y * s.k) for x, y in pts]

    def line(s, pts, fill, width=3):
        s.d.line(s._pt(pts), fill=fill, width=max(1, int(width * s.k)), joint='curve')

    def ellipse(s, b, fill=None, outline=None, width=1):
        s.d.ellipse([v * s.k for v in b], fill=fill, outline=outline, width=int(width * s.k))

    def arc(s, b, a0, a1, fill, width=3):
        s.d.arc([v * s.k for v in b], a0, a1, fill=fill, width=int(width * s.k))

    def rrect(s, b, r, fill=None, outline=None, width=1):
        s.d.rounded_rectangle([v * s.k for v in b], r * s.k, fill=fill, outline=outline, width=int(width * s.k))

    def poly(s, pts, fill):
        s.d.polygon(s._pt(pts), fill=fill)

    def water(s, pts, fill):
        tmp = Image.new('RGBA', s.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(tmp).polygon(s._pt(pts), fill=fill)
        s.im.alpha_composite(tmp)

    def paste_to(s, cv, x, y):
        im = s.im.resize((s.w, s.h), Image.LANCZOS)
        cv.paste(im, (x, y), im)


# ---------------------------------------------------------------- sfondo
@lru_cache(maxsize=1)
def base_grad():
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(0, 1, W)[None, :, None]
    v = np.clip(0.55 * yy + 0.45 * (1 - xx) * 0.6 + 0.2 * xx, 0, 1)
    c0 = np.array(BG0)[None, None, :]
    c1 = np.array(BG1)[None, None, :]
    return (c0 * (1 - v) + c1 * v).astype(np.float32)


@lru_cache(maxsize=1)
def vignette():
    yy = (np.linspace(-1, 1, H)[:, None]) ** 2
    xx = (np.linspace(-1, 1, W)[None, :]) ** 2
    v = 1 - 0.38 * np.clip((xx * 0.55 + yy * 0.75) - 0.15, 0, 1)
    return v[:, :, None].astype(np.float32)


@lru_cache(maxsize=4)
def make_bg(key=None, cy=0.5, strength=0.45):
    g = base_grad().copy()
    if key:
        im = src(key)
        cw = im.width * (0.95 if key[0] == 'w' else 1.0)
        ch = cw * H / W
        if ch > im.height:
            cw, ch = im.height * W / H, im.height
        y0 = clamp(cy * im.height - ch / 2, 0, im.height - ch)
        x0 = (im.width - cw) / 2
        bl = im.resize((W // 2, H // 2), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).filter(ImageFilter.GaussianBlur(14))
        a = np.asarray(bl.resize((W, H), Image.BILINEAR), dtype=np.float32)
        lum = a.mean() / 255.0
        a = a * (0.38 / max(lum, 0.08)) * 0.55
        g = g * (1 - strength) + a * strength
    g = g * vignette()
    out = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    for gx in range(0, W, 80):
        d.line((gx, 0, gx, H), fill=(14, 38, 88) if gx % 400 else (20, 52, 112), width=1)
    for gy in range(0, H, 80):
        d.line((0, gy, W, gy), fill=(14, 38, 88) if gy % 400 else (20, 52, 112), width=1)
    return out


_rb = np.random.default_rng(7)
BUB = [(_rb.uniform(0, W), _rb.uniform(5, 15), _rb.uniform(24, 70), _rb.uniform(0, 1500), _rb.uniform(0, 6.3)) for _ in range(26)]


def bubbles(cv, t):
    d = ImageDraw.Draw(cv)
    for x0, r, sp, off, ph in BUB:
        y = H + 40 - ((t * sp + off) % (H + 80))
        x = x0 + 14 * math.sin(t * 0.8 + ph)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(36, 100, 170), width=2)
        d.ellipse((x - r * 0.45, y - r * 0.55, x - r * 0.1, y - r * 0.2), fill=(50, 120, 190))


def waves(cv, t, y0, col=(40, 120, 200), amp=14, n=4, spacing=26):
    d = ImageDraw.Draw(cv)
    for k in range(n):
        pts = []
        for x in range(0, W + 30, 30):
            pts.append((x, y0 + k * spacing + amp * math.sin(x / 150 + t * 1.6 + k * 0.9)))
        c = tuple(int(col[i] * (1 - 0.18 * k)) for i in range(3))
        d.line(pts, fill=c, width=3)


# ---------------------------------------------------------------- blocchi di testo
def kicker(cv, s, t, t0, x=110, y=0):
    p = ease((t - t0) / 0.5)
    ImageDraw.Draw(cv).rectangle((x, y + 24, x + int(60 * p), y + 28), fill=CYAN)
    T(cv, s, x + 80, y, 40, t, t0 + 0.05, wght=600, color=CYAN, track=5)


def block(cv, t, kick, title, subs=(), x=110, cy=540, tsz=116, maxw=860, t0=0.2, sub_size=54, sub_gap=0.0):
    nl = len(title)
    lh = int(tsz * 1.1)
    total = 56 + 34 + nl * lh + (28 + len(subs) * 70 if subs else 0)
    y = cy - total / 2
    kicker(cv, kick, t, t0, x, int(y))
    y += 90
    for i, ln in enumerate(title):
        s, col = ln if isinstance(ln, tuple) else (ln, WHITE)
        T(cv, s, x, int(y), tsz, t, t0 + 0.15 + 0.2 * i, wght=700, color=col, maxw=maxw)
        y += lh
    y += 28
    for j, s in enumerate(subs):
        col = MUTED if j == 0 else CYAN2
        T(cv, s, x, int(y), sub_size, t, t0 + 0.25 + 0.2 * nl + 0.25 * j + sub_gap, wght=400, color=col, maxw=maxw)
        y += 70


# ---------------------------------------------------------------- scene
def s_open(cv, t):
    tiles = [(1, (0.5, .59, .6), (0.5, .55, .5)), (4, (0.5, .62, .55), (0.5, .66, .5)), (5, (0.5, .5, .6), (0.5, .42, .45)),
             (12, (0.5, .62, .55), (0.5, .58, .5)), (16, (0.5, .42, .6), (0.5, .46, .5))]
    for i, (n, r0, r1) in enumerate(tiles):
        panel(cv, ('w', n), (i * 384, 0, 384, H), r0, r1, t, t0=0.1 + 0.18 * i, dur=10, alpha=0.24, reveal=0.8, rev='y', frame=False, rad=0, shadow=False)
    wipe_text(cv, (('SWIM', WHITE), ('TIMER', CYAN)), 960, 250, 250, t, 0.3, 1.0, 700)
    d = ImageDraw.Draw(cv)
    lp = ease((t - 1.5) / 0.8)
    d.rectangle((960 - int(520 * lp), 560, 960 + int(520 * lp), 565), fill=CYAN)
    T(cv, 'I tuoi tempi in vasca.', 960, 610, 76, t, 2.0, 400, (215, 230, 255), anchor='c')
    T(cv, 'Senza fermarti. Senza pulsanti.', 960, 710, 76, t, 3.4, 600, CYAN, anchor='c', maxw=1700)
    if t > 5.6:
        k = ease((t - 5.6) / 0.8)
        pts = []
        for x in range(160, 1761, 8):
            env = math.exp(-((x - 960) / 520) ** 2)
            pts.append((x, 930 + k * env * 70 * math.sin(x / 22 - t * 7)))
        d.line(pts, fill=CYAN, width=4)


def s_problem(cv, t):
    block(cv, t, 'IL PROBLEMA', [('Ti fermi.', WHITE), ('Premi un pulsante.', WHITE), ('Perdi il ritmo.', CYAN)], tsz=112, maxw=880)
    # cronometro
    if t < 0.3:
        return
    g = G(760, 760)
    cx = cy = 380
    R = 290
    ang = (min(t, 1.45) * 150 - 90) % 360
    g.ellipse((cx - R - 20, cy - R - 20, cx + R + 20, cy + R + 20), fill=(8, 24, 60, 255), outline=CYAN + (255,), width=10)
    g.ellipse((cx - R + 22, cy - R + 22, cx + R - 22, cy + R - 22), outline=(40, 90, 170, 255), width=3)
    for i in range(60):
        a = math.radians(i * 6)
        r1 = R - (44 if i % 5 == 0 else 28)
        g.line([(cx + math.cos(a) * r1, cy + math.sin(a) * r1), (cx + math.cos(a) * (R - 8), cy + math.sin(a) * (R - 8))],
               WHITE + (255,) if i % 5 == 0 else (110, 150, 210, 255), 4 if i % 5 == 0 else 2)
    press = 1 if 1.35 <= t < 1.7 else 0
    g.rrect((cx - 34, cy - R - 80 + press * 18, cx + 34, cy - R - 20), 10, fill=CYAN + (255,))
    g.rrect((cx - 12, cy - R - 28, cx + 12, cy - R - 10), 4, fill=(20, 80, 140, 255))
    a = math.radians(ang)
    g.line([(cx - math.cos(a) * 40, cy - math.sin(a) * 40), (cx + math.cos(a) * (R - 50), cy + math.sin(a) * (R - 50))], WHITE + (255,), 10)
    g.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=CYAN + (255,))
    if t >= 1.35:
        k = clamp((t - 1.35) / 0.6)
        g.ellipse((cx - 34 - 90 * k, cy - R - 50 - 90 * k, cx + 34 + 90 * k, cy - R - 50 + 90 * k), outline=AMBER + (int(255 * (1 - k)),), width=6)
    g.paste_to(cv, 1060, 160)


def s_idea(cv, t):
    block(cv, t, "L'IDEA", ['Un tag', 'sotto la cuffia.'], ['Riconosce partenze,', 'virate e arrivi.'], tsz=112, maxw=800, sub_size=52)
    panel(cv, ('r', '3d'), (1000, 250, 800, 670), (0.5, 0.5, 1.0), (0.46, 0.55, 0.72), t, t0=0.3, dur=5)


def s_display(cv, t):
    block(cv, t, 'A BORDO VASCA', ['Un display.'], ['I tempi, chiari', 'a colpo d\'occhio.'], tsz=124, maxw=800, sub_size=54)
    if t < 0.4:
        return
    p = ease((t - 0.4) / 0.6)
    g = G(820, 600)
    g.rrect((0, 0, 820 * p, 600), 34, fill=(5, 14, 36, 255), outline=CYAN + (255,), width=6)
    g.paste_to(cv, 1030, 240)
    if p < 1:
        return
    v = 40.0 + t * 3.6
    s = f'{int(v // 60):02d}:{int(v % 60):02d}.{int((v % 1) * 100):02d}'
    x = 1080
    for ch in s:
        cw = 102 if ch.isdigit() else 50
        lay, pad, dy, tw = tlayer(((ch, WHITE),), 150, 700)
        cv.paste(lay, (int(x + (cw - tw) / 2 - pad), 330 - dy), lay)
        x += cw
    T(cv, 'L1   29.4', 1090, 560, 56, t, 1.6, 400, CYAN2)
    T(cv, 'L2   29.0', 1090, 640, 56, t, 2.4, 400, CYAN2)
    ImageDraw.Draw(cv).rectangle((1070, 530, 1790, 534), fill=(30, 80, 150))


def s_cap(cv, t):
    block(cv, t, 'COME FUNZIONA', ['Tag BLE', 'sotto la cuffia.'], [], tsz=116, maxw=800)
    if t < 0.4:
        return
    g = G(840, 720)
    wl = 440
    cx, hy, r = 420, 330, 190
    # testa + cuffia
    g.ellipse((cx - r, hy - r, cx + r, hy + r), fill=(18, 52, 112, 255), outline=CYAN + (255,), width=5)
    g.arc((cx - r - 12, hy - r - 12, cx + r + 12, hy + r + 12), 195, 345, CYAN + (255,), 14)
    # tag
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    g.rrect((cx - 46, hy - r + 40, cx + 46, hy - r + 84), 8, fill=(255, 255, 255, 255), outline=CYAN + (255,), width=4)
    g.rrect((cx - 30, hy - r + 52, cx + 30, hy - r + 72), 4, fill=CYAN + (255,))
    for i in range(3):
        k = ((t * 0.7 + i / 3) % 1)
        rr = 60 + k * 190
        g.arc((cx - rr, hy - r + 62 - rr, cx + rr, hy - r + 62 + rr), 230, 310, CYAN + (int(255 * (1 - k)),), 6)
    # acqua
    pts = [(x, wl + 10 * math.sin(x / 55 + t * 2.2)) for x in range(0, 841, 12)]
    g.water(pts + [(840, 720), (0, 720)], (20, 90, 180, 150))
    g.line(pts, CYAN2 + (255,), 4)
    g.paste_to(cv, 1030, 190)


def s_sensor(cv, t):
    block(cv, t, 'SENSORE', ['6 assi', 'di movimento.'], [], tsz=116, maxw=800, cy=460)
    if t < 0.3:
        return
    bx, by, bw, bh = 960, 200, 860, 640
    p = ease((t - 0.3) / 0.6)
    g = G(bw, bh)
    g.rrect((0, 0, bw * p, bh), 22, fill=(5, 14, 38, 255), outline=CYAN + (255,), width=4)
    if p >= 1:
        for k in range(1, 8):
            g.line([(k * bw / 8, 14), (k * bw / 8, bh - 14)], (20, 50, 100, 255), 1)
        for k in range(1, 5):
            g.line([(14, k * bh / 5), (bw - 14, k * bh / 5)], (20, 50, 100, 255), 1)
        xs = np.linspace(30, bw - 30, 300)
        tau = (xs - 30) / (bw - 60) * 6 + t
        ev = [2.3, 4.5, 6.3]
        cols = [CYAN, CYAN2, (70, 150, 255), WHITE, (190, 205, 255), (120, 170, 235)]
        for i in range(6):
            ph = i * 1.3
            sig = 0.16 * np.sin(2 * np.pi * (0.9 + 0.07 * i) * tau + ph) + 0.05 * np.sin(2 * np.pi * 3.1 * tau + i)
            sig += 0.7 * np.exp(-((tau - ev[0]) / 0.18) ** 2) * (1 if i % 2 == 0 else -0.8) * (1 - i * 0.08)
            sig += 0.5 * np.exp(-((tau - ev[1]) / 0.25) ** 2) * np.sin(7 * (tau - ev[1]) + i)
            sig += -0.65 * np.exp(-((tau - ev[2]) / 0.12) ** 2) * (1 if i % 2 else -1)
            y = 60 + (i + 0.5) * (bh - 120) / 6 - sig * 62
            g.line(list(zip(xs, y)), cols[i] + (255,), 3)
        for e in ev:
            x = 30 + (e - t) / 6 * (bw - 60)
            if 40 < x < bw - 40:
                g.line([(x, 20), (x, bh - 20)], AMBER + (200,), 3)
    g.paste_to(cv, bx, by)
    if p >= 1:
        for e, name in zip([2.3, 4.5, 6.3], ['PARTENZA', 'VIRATA', 'ARRIVO']):
            x = bx + 30 + (e - t) / 6 * (bw - 60)
            if bx + 110 < x < bx + bw - 110:
                lay, pad, dy, tw = tlayer(((name, AMBER),), 40, 700, 2)
                cv.paste(lay, (int(x - tw / 2 - pad), by + bh + 18 - dy), lay)


def s_link(cv, t):
    block(cv, t, 'DOPO LA NUOTATA', ['Dati via', 'Bluetooth.'], ['Il Bluetooth non', 'attraversa l\'acqua.'], tsz=112, maxw=800, sub_size=50)
    if t < 0.3:
        return
    bw, bh = 860, 700
    g = G(bw, bh)
    wl = 380
    up = smooth((t - 2.5) / 0.9)
    tx = lerp(150, 210, up)
    ty = lerp(wl + 190, wl - 150, up)
    # display
    dx, dy_, dw, dh = 560, wl - 330, 270, 190
    lit = clamp((t - 3.5) / 0.4)
    g.rrect((dx, dy_, dx + dw, dy_ + dh), 20, fill=(5, 14, 38, 255), outline=(CYAN if lit else (60, 100, 160)) + (255,), width=5)
    if lit:
        prog = clamp((t - 3.7) / 1.1)
        g.rrect((dx + 28, dy_ + dh - 56, dx + 28 + (dw - 56) * prog, dy_ + dh - 30), 8, fill=GREEN + (255,))
        for k in range(4):
            hh = 30 + 24 * ((k * 5) % 3)
            g.rrect((dx + 34 + k * 56, dy_ + 100 - hh, dx + 62 + k * 56, dy_ + 100), 4, fill=CYAN + (255,))
    # segnale
    if t < 2.5:
        for i in range(3):
            k = ((t * 0.8 + i / 3) % 1)
            rr = 30 + k * 100
            g.arc((tx - rr, ty - rr, tx + rr, ty + rr), 300, 360 + 60, CYAN + (int(220 * (1 - k)),), 6)
        if t > 1.0:
            a = clamp((t - 1.0) / 0.3)
            x0, y0 = tx + 150, wl + 70
            g.line([(x0, y0), (x0 + 70, y0 + 70)], AMBER + (int(255 * a),), 12)
            g.line([(x0 + 70, y0), (x0, y0 + 70)], AMBER + (int(255 * a),), 12)
    elif t > 3.4:
        for i in range(3):
            k = ((t * 0.9 + i / 3) % 1)
            rr = 60 + k * 330
            g.arc((tx - rr, ty - rr, tx + rr, ty + rr), -28, 28, CYAN + (int(230 * (1 - k)),), 7)
    # acqua
    pts = [(x, wl + 10 * math.sin(x / 60 + t * 2.0)) for x in range(0, bw + 1, 12)]
    g.water(pts + [(bw, bh), (0, bh)], (20, 90, 180, 150))
    g.line(pts, CYAN2 + (255,), 4)
    # tag
    g.rrect((tx - 38, ty - 20, tx + 38, ty + 20), 8, fill=(255, 255, 255, 255), outline=CYAN + (255,), width=4)
    g.rrect((tx - 22, ty - 9, tx + 22, ty + 9), 4, fill=CYAN + (255,))
    g.paste_to(cv, 1010, 190)


def s_tag(cv, t):
    block(cv, t, 'LA PROTAGONISTA', [('TAG', WHITE), ('v0.5', CYAN)], ['Progettata per nuotare.'], tsz=190, maxw=800, sub_size=54, cy=520)
    panel(cv, ('r', '3d'), (960, 160, 880, 736), (0.5, 0.5, 1.0), (0.42, 0.52, 0.62), t, t0=0.1, dur=5)


def feat(cv, t, kick, title, subs, panels, **kw):
    block(cv, t, kick, title, subs, **kw)
    for p in panels:
        panel(cv, *p[:4], t, **(p[4] if len(p) > 4 else {}))


def s_nrf(cv, t):
    feat(cv, t, 'PROCESSORE', [('nRF52840', CYAN)], ['Bluetooth 5', 'modulo E73'],
         [(('w', 5), (1000, 190, 820, 700), (0.5, 0.52, 0.9), (0.5, 0.36, 0.55), {'t0': 0.15, 'dur': 5})], tsz=116, maxw=800)


def s_imu(cv, t):
    feat(cv, t, 'MOVIMENTO', [('IMU', CYAN), ('6 assi', WHITE)], ['LSM6DSV16X'],
         [(('w', 4), (1000, 190, 820, 700), (0.71, 0.60, 0.66), (0.71, 0.60, 0.46), {'t0': 0.15, 'dur': 5})], tsz=124, maxw=800)


def s_flash(cv, t):
    feat(cv, t, 'MEMORIA', [('16 MB', CYAN)], ['Flash: circa 1,5 ore', 'di dati grezzi a 240 Hz'],
         [(('w', 4), (1000, 190, 820, 700), (0.71, 0.78, 0.66), (0.71, 0.78, 0.46), {'t0': 0.15, 'dur': 5})], tsz=150, maxw=800, sub_size=50)


def s_size(cv, t):
    block(cv, t, 'COMPATTA', [('21,59 × 28 mm', CYAN)], ['2 strati', 'cella LiPo 40 mAh'], tsz=100, maxw=840, sub_size=52)
    panel(cv, ('w', 7), (1000, 90, 390, 900), (0.5, 0.52, 0.88), (0.5, 0.48, 0.7), t, t0=0.15, dur=5, rev='y')
    panel(cv, ('w', 8), (1430, 90, 390, 900), (0.5, 0.52, 0.88), (0.5, 0.48, 0.7), t, t0=0.45, dur=5, rev='y')


def s_charge(cv, t):
    feat(cv, t, 'RICARICA', ['2 contatti', 'a molla'], ['Fuori dalla base:', 'contatti a 0 V'],
         [(('r', 'sotto'), (1000, 190, 820, 700), (0.47, 0.5, 0.8), (0.5, 0.52, 0.62), {'t0': 0.15, 'dur': 5})], tsz=116, maxw=800, sub_size=52)


def s_protect(cv, t):
    block(cv, t, 'PROTEZIONI', ['Più sicura.'], [], tsz=116, maxw=800, cy=330)
    items = ['Cella montata al contrario', 'ESD sui contatti', 'Sensore sbloccabile']
    items = ['Inversione della cella', 'ESD sui contatti', 'Sensore commutabile']
    y = 560
    d = ImageDraw.Draw(cv)
    for i, s in enumerate(items):
        t0 = 0.9 + 0.7 * i
        if t >= t0:
            p = ease((t - t0) / 0.4)
            g = G(56, 56)
            g.ellipse((4, 4, 52, 52), outline=GREEN + (255,), width=4)
            g.line([(15, 29), (24, 38), (41, 19)], GREEN + (255,), 6)
            g.paste_to(cv, 110, y - 2)
        T(cv, s, 190, y, 56, t, t0, 600, WHITE, maxw=780)
        y += 100
    panel(cv, ('w', 16), (1000, 190, 820, 700), (0.45, 0.41, 0.95), (0.45, 0.41, 0.85), t, t0=0.15, dur=5)


def s_swd(cv, t):
    block(cv, t, 'AGGIORNAMENTI', ['SWD · 5 piazzole'], ['Passo 2,54 mm', 'Sigillata in resina', 'Aggiornata via Bluetooth'], tsz=84, maxw=860, sub_size=48, cy=540)
    panel(cv, ('w', 14), (1000, 100, 820, 540), (0.5, 0.58, 0.82), (0.5, 0.58, 0.6), t, t0=0.15, dur=5)
    panel(cv, ('w', 3), (1000, 680, 820, 300), (0.5, 0.54, 0.85), (0.5, 0.54, 0.75), t, t0=2.4, dur=2.6)


def card(cv, t, t0, x, y, w, h, big, small, count=None, sub=None, color=CYAN):
    if t < t0:
        return
    p = ease((t - t0) / 0.5)
    g = G(w, h)
    g.rrect((0, 0, w, h), 26, fill=(6, 18, 46, 255), outline=color + (255,), width=4)
    ox = int((1 - p) * 60)
    im = g.im.resize((w, h), Image.LANCZOS)
    im.putalpha(im.getchannel('A').point(lambda v, k=p: int(v * k)))
    cv.paste(im, (x + ox, y), im)
    if p < 0.6:
        return
    txt = big
    if count:
        v = ease((t - t0 - 0.3) / 1.2)
        txt = count(v)
    T(cv, txt, x + 50, y + 36, 190, t, t0 + 0.2, 700, color, maxw=w - 100)
    T(cv, small, x + 50, y + h - 120, 50, t, t0 + 0.4, 400, MUTED, maxw=w - 100)
    if sub:
        T(cv, sub, x + 50, y + h - 66, 40, t, t0 + 0.55, 400, CYAN2, maxw=w - 100)


def s_verify1(cv, t):
    kicker(cv, 'VERIFICHE', t, 0.2, 110, 110)
    T(cv, 'Progettata per non sbagliare.', 110, 190, 96, t, 0.35, 700, WHITE, maxw=1700)
    card(cv, t, 0.9, 110, 400, 800, 480, '0', 'errori DRC', lambda v: str(int(0 * v)), 'regole di progetto')
    card(cv, t, 1.3, 960, 400, 850, 480, '', 'pin della netlist verificati', lambda v: f'{int(100 * v)}/100', 'schema e scheda coincidono', GREEN)


def s_verify2(cv, t):
    kicker(cv, 'VERIFICHE', t, 0.2, 110, 110)
    T(cv, 'Controllata e ricontrollata.', 110, 190, 96, t, 0.35, 700, WHITE, maxw=1700)
    card(cv, t, 0.9, 110, 400, 800, 480, '', 'controlli sui fogli tecnici', lambda v: str(int(65 * v)), 'quote, sigle, piedinature')
    # revisioni incrociate
    if t >= 1.3:
        p = ease((t - 1.3) / 0.5)
        g = G(850, 480)
        g.rrect((0, 0, 850, 480), 26, fill=(6, 18, 46, 255), outline=GREEN + (255,), width=4)
        for i, (cx, col) in enumerate([(285, CYAN), (400, GREEN), (515, WHITE)]):
            k = ease((t - 1.6 - 0.25 * i) / 0.5)
            g.ellipse((cx - 90 * k, 150 - 90 * k, cx + 90 * k, 150 + 90 * k), outline=col + (255,), width=8)
        g.paste_to(cv, 960, 400)
        T(cv, 'Revisioni incrociate', 1010, 700, 52, t, 2.2, 600, WHITE, maxw=760)
        T(cv, 'indipendenti', 1010, 770, 52, t, 2.4, 400, CYAN2, maxw=760)


def s_prog(cv, t):
    feat(cv, t, 'IL PROGRAMMATORE', ['HAT per', 'Raspberry Pi'], ['Pogo pin: programma', 'e ricarica il tag'],
         [(('w', 19), (1000, 190, 820, 700), (0.5, 0.54, 1.0), (0.5, 0.53, 0.9), {'t0': 0.15, 'dur': 5})], tsz=108, maxw=840, sub_size=50)


def s_hand(cv, t):
    block(cv, t, 'FATTO A MANO', ['Toner', 'transfer.'], ['Pronto per il tag.'], tsz=116, maxw=800)
    panel(cv, ('w', 20), (960, 90, 400, 900), (0.5, 0.5, 1.0), (0.5, 0.5, 0.92), t, t0=0.15, dur=5, rev='y')
    panel(cv, ('p', 'top'), (1400, 90, 440, 430), (0.5, 0.5, 0.95), (0.5, 0.5, 0.75), t, t0=0.5, dur=4.5, rev='y')
    panel(cv, ('w', 18), (1400, 560, 440, 430), (0.5, 0.6, 0.8), (0.5, 0.6, 0.62), t, t0=0.85, dur=4.2, rev='y')


def s_state(cv, t):
    block(cv, t, 'STATO', ['Fase di', 'prototipo.'], ['Schede progettate,', 'in arrivo.'], tsz=116, maxw=800, sub_size=52)
    panel(cv, ('r', 'sopra'), (1000, 190, 820, 686), (0.5, 0.5, 1.0), (0.5, 0.48, 0.78), t, t0=0.2, dur=5)
    if t >= 1.5:
        p = ease((t - 1.5) / 0.4)
        g = G(300, 78)
        g.rrect((0, 0, 300, 78), 14, fill=(6, 18, 46, 255), outline=AMBER + (255,), width=4)
        g.paste_to(cv, 1500, 150 + int((1 - p) * -30))
        T(cv, 'IN ARRIVO', 1650, 168, 44, t, 1.7, 700, AMBER, track=3, anchor='c')


def s_next(cv, t):
    kicker(cv, 'PROSSIMI PASSI', t, 0.2, 110, 130)
    T(cv, 'Dal prototipo alla vasca.', 110, 210, 92, t, 0.35, 700, WHITE, maxw=1700)
    labels = ['Primi 2 tag', 'Registrare i dati', 'Filtri a punto', 'Prove in vasca']
    xs = [260, 780, 1300, 1700]
    xs = [250, 710, 1170, 1630]
    d = ImageDraw.Draw(cv)
    ly = 640
    prog = clamp((t - 0.9) / 3.6)
    d.line((xs[0], ly, xs[-1], ly), fill=(30, 70, 140), width=8)
    d.line((xs[0], ly, int(lerp(xs[0], xs[-1], prog)), ly), fill=CYAN, width=8)
    for i, (x, lab) in enumerate(zip(xs, labels)):
        t0 = 0.9 + 1.2 * i
        if t >= t0:
            k = ease((t - t0) / 0.4)
            r = int(30 * k)
            pulse = 6 * math.sin(t * 5) * k if i == 0 else 0
            rr = max(1, r + pulse); d.ellipse((x - rr, ly - rr, x + rr, ly + rr), fill=CYAN if i == 0 else (6, 18, 46), outline=CYAN, width=6)
            T(cv, lab, x, ly + 70 + (30 if i % 2 else 0), 48, t, t0 + 0.1, 600, WHITE if i == 0 else MUTED, anchor='c', maxw=420)


def s_close(cv, t):
    waves(cv, t, 930, (30, 100, 180), 12, 3, 28)
    wipe_text(cv, (('SWIM', WHITE), ('TIMER', CYAN)), 960, 260, 230, t, 0.5, 1.0, 700)
    d = ImageDraw.Draw(cv)
    lp = ease((t - 1.5) / 0.8)
    d.rectangle((960 - int(480 * lp), 530, 960 + int(480 * lp), 535), fill=CYAN)
    T(cv, 'Prototipo v0.5 · 2026', 960, 575, 72, t, 2.3, 600, MUTED, anchor='c')
    T(cv, 'Nuota.', 960, 690, 110, t, 4.6, 700, WHITE, anchor='c')
    T(cv, 'Al resto pensa il tag.', 960, 810, 80, t, 6.0, 600, CYAN, anchor='c', maxw=1600)


# (inizio, durata, funzione, sfondo(key, cy, strength))
SCENES = [
    (0, 10, s_open, None),
    (10, 5, s_problem, None),
    (15, 5, s_idea, (('w', 1), 0.55, 0.40)),
    (20, 5, s_display, (('w', 16), 0.4, 0.30)),
    (25, 5, s_cap, None),
    (30, 5, s_sensor, (('w', 5), 0.5, 0.35)),
    (35, 5, s_link, None),
    (40, 5, s_tag, (('r', '3d'), 0.5, 0.45)),
    (45, 5, s_nrf, (('w', 6), 0.5, 0.40)),
    (50, 5, s_imu, (('w', 4), 0.62, 0.40)),
    (55, 5, s_flash, (('w', 4), 0.78, 0.40)),
    (60, 5, s_size, (('w', 10), 0.5, 0.40)),
    (65, 5, s_charge, (('r', 'sotto'), 0.5, 0.40)),
    (70, 5, s_protect, (('w', 16), 0.4, 0.35)),
    (75, 5, s_swd, (('w', 15), 0.5, 0.35)),
    (80, 5, s_verify1, (('w', 11), 0.5, 0.30)),
    (85, 5, s_verify2, (('w', 13), 0.5, 0.30)),
    (90, 5, s_prog, (('w', 17), 0.55, 0.40)),
    (95, 5, s_hand, (('w', 20), 0.6, 0.30)),
    (100, 5, s_state, (('r', 'sopra'), 0.5, 0.40)),
    (105, 5, s_next, (('w', 2), 0.5, 0.35)),
    (110, 10, s_close, None),
]
TRANS = ['push', 'wipe', 'dissolve', 'pushup', 'zoom', 'wipe', 'push', 'dissolve', 'zoom', 'pushup']


def scene_frame(k, ts):
    st, du, fn, bgs = SCENES[k]
    bg = make_bg(*bgs).copy() if bgs else make_bg().copy()
    bubbles(bg, ts)
    fn(bg, ts)
    return bg


@lru_cache(maxsize=1)
def diag():
    yy, xx = np.mgrid[0:H, 0:W]
    return (xx + 0.45 * yy).astype(np.float32)


def transition(a, b, kind, p):
    p = smooth(p)
    if kind == 'push':
        o = Image.new('RGB', (W, H))
        s = int(W * p)
        o.paste(a, (-s, 0))
        o.paste(b, (W - s, 0))
        return o
    if kind == 'pushup':
        o = Image.new('RGB', (W, H))
        s = int(H * p)
        o.paste(a, (0, -s))
        o.paste(b, (0, H - s))
        return o
    if kind == 'wipe':
        thr = p * (W + 0.45 * H + 120) - 60
        dg = diag()
        m = (dg < thr).astype(np.uint8) * 255
        edge = (np.abs(dg - thr) < 5).astype(np.uint8) * 255
        o = Image.composite(b, a, Image.fromarray(m))
        o.paste(Image.new('RGB', (W, H), CYAN), (0, 0), Image.fromarray(edge))
        return o
    if kind == 'zoom':
        s = 1.12 - 0.12 * p
        cw, ch = W / s, H / s
        bz = b.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        return Image.blend(a, bz, p)
    return Image.blend(a, b, p)


def frame_image(i):
    t = i / FPS
    k = max(j for j, s in enumerate(SCENES) if s[0] <= t + 1e-9)
    ts = t - SCENES[k][0]
    img = scene_frame(k, ts)
    if k > 0 and ts < 0.4:
        a = scene_frame(k - 1, t - SCENES[k - 1][0])
        img = transition(a, img, TRANS[(k - 1) % len(TRANS)], ts / 0.4)
    if 40 <= t < 40.28:  # lampo sul drop
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.45 * (1 - (t - 40) / 0.28))
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 6, int(W * t / DUR), H), fill=CYAN)
    if t > 118.0:
        img = Image.blend(img, Image.new('RGB', (W, H), (0, 0, 0)), clamp((t - 118.0) / 2.0))
    return img


def frame_bytes(i):
    return frame_image(i).tobytes()


# ---------------------------------------------------------------- miniatura
def miniatura(path):
    bg = make_bg(('w', 1), 0.55, 0.45).copy()
    d = ImageDraw.Draw(bg)
    for k in range(5):
        pts = [(x, 905 + k * 26 + 14 * math.sin(x / 150 + k)) for x in range(0, W + 30, 30)]
        d.line(pts, fill=tuple(int(c * (1 - 0.18 * k)) for c in (40, 120, 200)), width=3)
    panel(bg, ('r', '3d'), (1010, 150, 800, 670), (0.5, 0.5, 1.0), (0.5, 0.5, 1.0), 9, t0=0, dur=1)
    panel(bg, ('w', 1), (1560, 590, 260, 400), (0.5, 0.6, 0.7), (0.5, 0.6, 0.7), 9, t0=0, dur=1)
    T(bg, 'SWIM', 100, 190, 250, 9, 0, 700, WHITE)
    T(bg, 'TIMER', 100, 400, 250, 9, 0, 700, CYAN)
    d.rectangle((110, 700, 600, 706), fill=CYAN)
    T(bg, 'Tempi in vasca.', 110, 740, 78, 9, 0, 600, WHITE)
    T(bg, 'Senza pulsanti.', 110, 840, 78, 9, 0, 600, CYAN)
    bg.resize((1280, 720), Image.LANCZOS).save(path)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anteprima', nargs='*', type=float)
    ap.add_argument('--dir', default=str(HERE))
    ap.add_argument('--solo-musica', action='store_true')
    ap.add_argument('--solo-miniatura', action='store_true')
    ap.add_argument('--no-musica', action='store_true')
    a = ap.parse_args()
    if a.anteprima:
        Path(a.dir).mkdir(parents=True, exist_ok=True)
        for tsec in a.anteprima:
            frame_image(int(tsec * FPS)).save(Path(a.dir) / f'prev_{tsec:06.2f}.png')
        return
    if a.solo_miniatura:
        miniatura(HERE / 'miniatura_youtube.png')
        return
    wav = HERE / 'musica_originale.wav'
    if not a.no_musica:
        sys.path.insert(0, str(HERE))
        import musica
        y, lufs, peak = musica.compose(wav)
        print(f'Musica: {lufs} LUFS, picco {peak} dBFS')
        print('\n'.join(musica.stats(y)))
    if a.solo_musica:
        return
    miniatura(HERE / 'miniatura_youtube.png')
    out = HERE / 'SwimTimer_presentazione.mp4'
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-i', str(wav), '-map', '0:v', '-map', '1:a',
           '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-maxrate', '5M', '-bufsize', '10M',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-t', str(DUR), '-movflags', '+faststart', str(out)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(max(2, (__import__('os').cpu_count() or 4) - 1)) as pool:
        for n, fb in enumerate(pool.imap(frame_bytes, range(NFRAMES), chunksize=10)):
            pr.stdin.write(fb)
            if n % 300 == 0:
                print(f'fotogramma {n}/{NFRAMES}', flush=True)
    pr.stdin.close()
    pr.wait()
    print('Fatto:', out)


if __name__ == '__main__':
    main()
