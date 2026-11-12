"""Video v4 «Houston, abbiamo un problema»: 180 s, 1920x1080, 30 fps, IT ed EN, musica originale (musica_v4.py).

Stesso metodo di genera_video_v3.py (grafica di genera_video.py / genera_video_v2.py: testo cinetico, transizioni, sfondo),
ma TUTTE le animazioni sono disegnate in codice con PIL su dati INVENTATI (nessun dato reale delle sessioni).
Dai 6 s ai 33 s va la clip Marte/Houston dell'autore (con il suo audio): intera, in una cornice centrata.
I fotogrammi della clip si estraggono con ffmpeg in una cache FUORI dal repository (%TEMP%/swimtimer_v4_cache).

Uso:  python media/video/genera_video_v4.py                                       (italiano: musica + miniatura + video)
      python media/video/genera_video_v4.py --lingua en [--no-musica]
      python media/video/genera_video_v4.py --clip PERCORSO.mp4                    (clip diversa da quella predefinita)
      python media/video/genera_video_v4.py --anteprima 3 20 70 --dir CARTELLA     (solo fotogrammi PNG)
      python media/video/genera_video_v4.py --prova-audio 40 --dir CARTELLA        (solo il mix audio dei primi 40 s)
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
LANG = os.environ.get('SWIMTIMER_LANG', 'it')
import genera_video_v2 as v2  # noqa: E402
import genera_video as gv  # noqa: E402

if LANG == 'en':
    from testi_v4_en import EN as _TR4
    gv._TR = _TR4
else:
    gv._TR = {}
tr = gv.tr
T, kicker, wipe_text, G, tlayer = gv.T, gv.kicker, gv.wipe_text, gv.G, gv.tlayer
ease, smooth, clamp, lerp = gv.ease, gv.smooth, gv.clamp, gv.lerp
TM, chip, check, num = v2.TM, v2.chip, v2.check, v2.num
W, H, FPS, DUR = gv.W, gv.H, gv.FPS, 180.0
NFRAMES = int(DUR * FPS)
CYAN, CYAN2, WHITE, MUTED, AMBER, GREEN = gv.CYAN, gv.CYAN2, gv.WHITE, gv.MUTED, gv.AMBER, gv.GREEN
RED, VIOLET, ORANGE, CARD = v2.RED, v2.VIOLET, v2.ORANGE, v2.CARD
YELLOW = (255, 214, 64)
NAVY = (6, 24, 60)
CLIP_T0 = 6.0
CLIP_BOX = (288, 100, 1344, 756)
CLIP_DEFAULT = {'it': '~/Downloads/My_first_board_Marte_-_Houston_chiavi_montaggio_finalemp4_0y5GZMft.mp4',
                'en': '~/Downloads/My_first_board_Mars_-_Houston_keys_English_finalmp4_mjfu3RR4.mp4'}
CACHE_ROOT = Path(tempfile.gettempdir()) / 'swimtimer_v4_cache'
DUCK_DB = -18.0


# ================================================================ utilita'
def mix(c1, c2, u):
    return tuple(int(lerp(a, b, u)) for a, b in zip(c1, c2))


def lay(w, h):
    return G(int(w), int(h))


def wrap_text(cv, t, s, x, y, size, t0, maxw, wght=700, color=WHITE, anchor='l', gap=0.12, lh=1.22):
    """Testo che va a capo da solo (il dizionario EN traduce la frase intera). Restituisce la y sotto l'ultima riga."""
    words = tr(s).split(' ')
    lines, cur = [], ''
    for w in words:
        trial = (cur + ' ' + w).strip()
        if cur and gv.text_len(trial, size, wght) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    for i, ln in enumerate(lines):
        T(cv, ln, x, int(y + i * size * lh), size, t, t0 + gap * i, wght, color, anchor=anchor)
    return y + len(lines) * size * lh


def words_text(cv, t, sentence, t0, cy, size, maxw, col=WHITE, hicol=CYAN, span=3.8, xc=960):
    """Frase che compare parola per parola, centrata."""
    hi = {'pianti', 'dettaglio', 'crash', 'detail'}
    ws = tr(sentence).split(' ')
    sp = gv.font(size, 700).getlength(' ')
    wl = [gv.text_len(w, size, 700) for w in ws]
    lines, cur, cw = [], [], 0.0
    for i, l in enumerate(wl):
        if cur and cw + sp + l > maxw:
            lines.append(cur)
            cur, cw = [], 0.0
        cw += (sp if cur else 0) + l
        cur.append(i)
    lines.append(cur)
    per = span / len(ws)
    lh = int(size * 1.32)
    y = cy - len(lines) * lh / 2
    for ln in lines:
        x = xc - (sum(wl[i] for i in ln) + sp * (len(ln) - 1)) / 2
        for i in ln:
            c = hicol if ws[i].strip('.,') in hi else col
            T(cv, ws[i], x, int(y), size, t, t0 + i * per, 700, c, dur=0.35)
            x += wl[i] + sp
        y += lh


def badge(cv, n, x, y, t, t0, col=CYAN):
    """Numero cerchiato disegnato in codice (il font non ha ①②③)."""
    if t < t0:
        return
    p = ease((t - t0) / 0.35)
    g = lay(72, 72)
    g.ellipse((4, 4, 68, 68), fill=CARD + (240,), outline=col + (255,), width=4)
    im = g.im.resize((72, 72), Image.LANCZOS)
    im.putalpha(im.getchannel('A').point(lambda v, k=p: int(v * k)))
    cv.paste(im, (int(x), int(y)), im)
    T(cv, str(n), x + 36, y + 11, 42, t, t0 + 0.1, 700, col, anchor='c')


@lru_cache(maxsize=1)
def make_light_bg():
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(0, 1, W)[None, :, None]
    v = np.clip(0.7 * yy + 0.3 * xx, 0, 1)
    g = np.array((14, 100, 172))[None, None, :] * (1 - v) + np.array((40, 172, 224))[None, None, :] * v
    im = Image.fromarray(g.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for k in range(14):
        d.line([(x, 70 + k * 75 + 18 * math.sin(x / 130 + k * 1.3)) for x in range(0, W + 40, 40)], fill=(84, 196, 238), width=2)
    return im


# ================================================================ disegni
def draw_tag(g, cx, cy, s=1.0, led=None, glow=0.0):
    w, h = 200 * s, 92 * s
    lw = max(2, 3 * s)
    g.rrect((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 14 * s, fill=(14, 40, 86, 255), outline=(80, 160, 235, 255), width=lw)
    g.rrect((cx - w * .40, cy - h * .26, cx - w * .10, cy + h * .26), 4 * s, fill=(30, 72, 134, 255), outline=(100, 180, 245, 255), width=max(1, 2 * s))
    g.rrect((cx + w * .02, cy - h * .30, cx + w * .20, cy + h * .02), 3 * s, fill=(44, 96, 168, 255))
    g.line([(cx + w * .22, cy + h * .16), (cx + w * .40, cy + h * .16), (cx + w * .40, cy - h * .28)], (100, 180, 245, 255), max(1, 2.5 * s))
    lx, ly, r = cx - w * .25, cy + h * .36, 6.5 * s
    if led and glow > 0:
        g.ellipse((lx - r * 2.2, ly - r * 2.2, lx + r * 2.2, ly + r * 2.2), fill=led + (int(80 * glow),))
    g.ellipse((lx - r, ly - r, lx + r, ly + r), fill=(led + (255,)) if led else (50, 66, 100, 255))


def tag_at(cv, cx, cy, s=1.0, led=None, glow=0.0):
    g = lay(240 * s, 130 * s)
    draw_tag(g, 120 * s, 65 * s, s, led, glow)
    g.paste_to(cv, int(cx - 120 * s), int(cy - 65 * s))


def draw_balloon(cv, cx, cy, t, level):
    """Palloncino che galleggia con una tag dentro; level = quota dell'acqua entrata (0..1)."""
    g = lay(620, 800)
    ox, oy = 310, 380
    rx, ry = 175, 215
    bob = 9 * math.sin(t * 1.4)
    oy += bob
    g.ellipse((ox - rx, oy - ry, ox + rx, oy + ry), fill=(140, 205, 255, 58), outline=(185, 230, 255, 235), width=5)
    g.arc((ox - rx + 28, oy - ry + 28, ox + rx - 28, oy + ry - 28), 200, 262, (235, 248, 255, 200), 7)
    g.poly([(ox - 17, oy + ry + 14), (ox + 17, oy + ry + 14), (ox, oy + ry - 6)], (185, 230, 255, 235))
    g.line([(ox, oy + ry + 12)] + [(ox + 22 * math.sin(i * 0.9 + t * 2.2), oy + ry + 12 + i * 28) for i in range(1, 6)], (200, 235, 255, 180), 4)
    if level > 0:                                                   # acqua entrata
        yw = oy + ry - 2 * ry * level * 0.55
        pts_l, pts_r = [], []
        for yy in np.linspace(yw, oy + ry, 18):
            hw = rx * math.sqrt(max(0.0, 1 - ((yy - oy) / ry) ** 2))
            pts_l.append((ox - hw, yy))
            pts_r.append((ox + hw, yy))
        g.water(pts_l + pts_r[::-1], (40, 140, 225, 150))
        g.line([(ox + pts_l[0][0] - ox, yw), (ox + pts_r[0][0] - ox, yw)], (190, 235, 255, 220), 3)
    draw_tag(g, ox, oy + 25, 0.95, led=(255, 120, 80), glow=0.5 + 0.5 * math.sin(t * 6))
    hx, hy = ox - rx * 0.76, oy - ry * 0.66                         # foro e gocce
    g.ellipse((hx - 6, hy - 6, hx + 6, hy + 6), fill=(10, 30, 70, 255), outline=(255, 120, 80, 255), width=2)
    yw_s = oy + ry - 2 * ry * level * 0.55 if level > 0 else oy + ry - 10
    for i in range(4):
        u = ((t * 0.85 + i / 4) % 1.0)
        if u < 0.35:                                                # arriva da fuori
            k = u / 0.35
            px, py = hx - 70 * (1 - k), hy - 80 * (1 - k)
        else:                                                       # cade dentro
            k = (u - 0.35) / 0.65
            px, py = hx + 4 * k, lerp(hy, yw_s, k * k)
            if py >= yw_s:
                continue
        g.ellipse((px - 6, py - 6, px + 6, py + 7), fill=(150, 215, 255, 240))
        g.poly([(px - 5, py - 3), (px + 5, py - 3), (px, py - 15)], (150, 215, 255, 240))
    g.paste_to(cv, int(cx - 310), int(cy - 380))


ITEM_COL = [CYAN, GREEN, AMBER, VIOLET, ORANGE, CYAN2, GREEN, AMBER, VIOLET]


def slot(i):
    return 70 + (i % 3) * 85, 310 - (i // 3) * 85


def draw_pack(cv, x0, y0, wf, items, shake=0.0, flap=0.0):
    """Zaino: x0,y0 = angolo alto-sinistra del corpo (300*wf x 380). items: (lx, ly, lato, colore) nel sistema del corpo."""
    bw = int(300 * wf)
    g = lay(bw + 200, 560)
    bx, by = 100, 120
    col, edge = (16, 46, 100, 235), (70, 150, 235, 255)
    strap = (40, 100, 190, 255)
    g.line([(bx + 8, by + 90), (bx - 40, by + 200), (bx - 24, by + 340)], strap, 14)
    g.line([(bx + bw - 8, by + 90), (bx + bw + 40, by + 200), (bx + bw + 24, by + 340)], strap, 14)
    g.arc((bx + bw / 2 - 55, by - 50 - flap * 50, bx + bw / 2 + 55, by + 30 - flap * 50), 180, 360, edge, 10)
    g.rrect((bx, by, bx + bw, by + 380), 60, fill=col, outline=edge, width=5)
    for lx, ly, sz, c in items:
        g.rrect((bx + lx - sz / 2, by + ly - sz / 2, bx + lx + sz / 2, by + ly + sz / 2), 14, fill=c + (255,))
    fy = by - flap * 55
    g.rrect((bx, fy, bx + bw, fy + 96), 40, fill=(24, 66, 140, 255), outline=edge, width=5)
    g.rrect((bx + bw / 2 - 22, fy + 60, bx + bw / 2 + 22, fy + 108), 8, fill=AMBER + (255,))
    g.line([(bx + 20, fy + 80), (bx + bw / 2 - 30, fy + 80)], (110, 180, 245, 255), 4)
    g.line([(bx + bw / 2 + 30, fy + 80), (bx + bw - 20, fy + 80)], (110, 180, 245, 255), 4)
    g.paste_to(cv, int(x0 - bx + shake), int(y0 - by))


def free_item(cv, x, y, sz, col):
    g = lay(sz + 16, sz + 16)
    g.rrect((8, 8, 8 + sz, 8 + sz), 14, fill=col + (255,))
    g.paste_to(cv, int(x - sz / 2 - 8), int(y - sz / 2 - 8))


def gauge(cv, x, y, h, f, t, blink=False):
    g = lay(70, h + 20)
    g.rrect((6, 6, 64, h + 14), 16, fill=CARD + (240,), outline=(90, 150, 230, 255), width=4)
    ff = clamp(f)
    c = GREEN if ff < 0.6 else (AMBER if ff < 0.88 else RED)
    if blink and int(t * 6) % 2 == 0:
        c = (255, 200, 200)
    if ff > 0.01:
        top = 14 + (h - 8) * (1 - ff)
        g.rrect((14, top, 56, h + 6), 10, fill=c + (255,))
    g.paste_to(cv, int(x), int(y))


def draw_box(cv, cx, cy, t, door=0.0, rec=True):
    """Scatola nera arancione; door 0..1 apre il portello e mostra il chip di memoria."""
    g = lay(440, 380)
    o = (190, 92, 18, 255)
    g.rrect((170, 96, 270, 150), 18, outline=(251, 146, 60, 255), width=10)
    g.rrect((50, 130, 390, 340), 28, fill=ORANGE + (255,), outline=o, width=6)
    g.rrect((50, 160, 390, 178), 4, fill=(255, 238, 205, 255))
    g.rrect((50, 188, 390, 196), 3, fill=(255, 238, 205, 255))
    g.rrect((112, 214, 328, 324), 12, fill=(6, 18, 46, 255), outline=o, width=4)      # alloggio del chip
    g.rrect((150, 236, 290, 302), 6, fill=(18, 50, 110, 255), outline=CYAN + (255,), width=3)
    for i in range(5):
        g.line([(166 + i * 28, 236), (166 + i * 28, 224)], CYAN + (255,), 3)
        g.line([(166 + i * 28, 302), (166 + i * 28, 314)], CYAN + (255,), 3)
    if door > 0.6:
        g.rrect((140, 246, 300, 292), 4, fill=CYAN + (int(70 * (0.5 + 0.5 * math.sin(t * 7))),))
    dh = 110 * (1 - clamp(door))
    if dh > 2:
        g.rrect((112, 214, 328, 214 + dh), 12, fill=(222, 112, 30, 255), outline=o, width=4)
        if dh > 40:
            g.rrect((206, 214 + dh - 34, 234, 214 + dh - 12), 5, fill=(255, 238, 205, 255))
    if rec:
        c = RED if int(t * 2) % 2 == 0 else (120, 40, 50)
        g.ellipse((340, 140, 372, 172), fill=c + (255,))
    g.paste_to(cv, int(cx - 220), int(cy - 190))


def draw_ring(cv, cx, cy, r, t, tagcx, tagcy, s=1.0):
    """Lente d'ingrandimento sopra la tag (spenta)."""
    mag = lay(2 * r, 2 * r)
    mag.ellipse((0, 0, 2 * r, 2 * r), fill=(10, 24, 56, 255))
    draw_tag(mag, r + (tagcx - cx) * 1.9, r + (tagcy - cy) * 1.9, s * 1.9)
    m = Image.new('L', mag.im.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, mag.im.size[0] - 1, mag.im.size[1] - 1), fill=255)
    mag.im.putalpha(m)
    mag.paste_to(cv, int(cx - r), int(cy - r))
    g = lay(2 * r + 200, 2 * r + 200)
    c = r + 20
    g.ellipse((c - r, c - r, c + r, c + r), outline=(220, 235, 250, 255), width=12)
    g.ellipse((c - r + 16, c - r + 16, c + r - 16, c + r - 16), fill=(255, 255, 255, 22))
    g.arc((c - r + 24, c - r + 24, c + r - 24, c + r - 24), 200, 260, (255, 255, 255, 190), 8)
    a = math.radians(45)
    g.line([(c + r * math.cos(a), c + r * math.sin(a)), (c + r * math.cos(a) + 130, c + r * math.sin(a) + 130)], (220, 235, 250, 255), 22)
    g.paste_to(cv, int(cx - c), int(cy - c))


@lru_cache(maxsize=1)
def water_patch():
    return Image.new('RGB', (W, 290), (30, 130, 210))


def pool(cv, t, wy=470, wall=False):
    d = ImageDraw.Draw(cv)
    d.rectangle((0, wy, W, wy + 290), fill=(10, 66, 128))
    d.rectangle((0, wy + 290, W, wy + 300), fill=(30, 110, 180))
    for i in range(0, W + 200, 160):
        x = (i - t * 60) % (W + 160) - 80
        d.line((x, wy + 250, x + 70, wy + 250), fill=(26, 92, 160), width=6)
    if wall:
        d.rectangle((1700, wy - 110, 1800, wy + 300), fill=(188, 214, 238))
        d.rectangle((1700, wy + 20, 1712, wy + 190), fill=CYAN)


def pool_top(cv, t, wy=470):
    reg = cv.crop((0, wy, W, wy + 290))
    cv.paste(Image.blend(reg, water_patch(), 0.33), (0, wy))
    gv.waves(cv, t, wy, (100, 200, 255), 5, 2, 12)


SWS = 1.25                                                          # scala del nuotatore


def swimmer(cv, x, y, ph, glide=False, t=0.0):
    """Nuotatore stilizzato di lato verso destra. (x, y) = centro del corpo; ph = fase della bracciata 0..1
    (0 = mano avanti, all'ingresso in acqua). A ph = 0 il centro della mano sta a x + 176."""
    g = lay(560, 320)
    cx, cy = 280, 160
    skin, skin2 = (242, 200, 165, 255), (206, 160, 130, 255)
    suit, suit2 = (226, 236, 250, 255), (160, 178, 208, 255)
    kk = 15 * math.sin(2 * math.pi * 3 * ph) if not glide else 4 * math.sin(t * 5)
    hip = (cx - 98, cy + 3)

    def leg(sg, c, w):
        kf = sg * kk
        knee = (hip[0] - 56, hip[1] + kf * 0.45)
        foot = (hip[0] - 116, hip[1] + kf)
        g.line([hip, knee, foot], c, w)
        g.line([(foot[0] + 2, foot[1] - 2), (foot[0] - 30, foot[1] + 5 * (1 if kf > 0 else -1))], c, w * 0.7)
    leg(-1, suit2, 14)
    leg(1, suit, 16)
    shoulder = (cx + 38, cy - 4)
    L = 138

    def arm(p, c, w):
        a = 2 * math.pi * p
        ex, ey = shoulder[0] + L * math.cos(a), shoulder[1] + L * math.sin(a)
        rec = 0.5 <= p < 1.0                                        # recupero fuori dall'acqua: gomito alto
        bend = 0 if glide else 40 * abs(math.sin(2 * math.pi * p)) * (1.0 if rec else 0.55)
        nx, ny = math.sin(a), -math.cos(a)
        mid = ((shoulder[0] + ex) / 2 + nx * bend, (shoulder[1] + ey) / 2 + ny * bend)
        g.line([shoulder, mid, (ex, ey)], c, w)
        g.ellipse((mid[0] - w / 2, mid[1] - w / 2, mid[0] + w / 2, mid[1] + w / 2), fill=c)
        g.ellipse((ex - 14, ey - 11, ex + 14, ey + 11), fill=c)
    if glide:
        arm(0.0, skin2, 19)
    else:
        arm(ph + 0.5, skin2, 19)
    g.line([(cx - 104, cy), (cx + 56, cy)], skin, 42)                # busto
    g.ellipse((cx - 125, cy - 21, cx - 83, cy + 21), fill=suit)
    g.line([(cx - 104, cy), (cx - 40, cy)], suit, 42)                # costume
    g.ellipse((cx + 17, cy - 25, cx + 59, cy + 17), fill=skin)       # spalla
    g.line([(cx + 56, cy - 4), (cx + 76, cy - 8)], skin, 20)         # collo
    g.ellipse((cx + 66, cy - 30, cx + 116, cy + 20), fill=skin)      # testa
    g.ellipse((cx + 63, cy - 33, cx + 113, cy + 4), fill=AMBER + (255,))   # cuffia
    g.line([(cx + 66, cy - 6), (cx + 114, cy - 6)], (150, 100, 20, 255), 3)
    g.line([(cx + 66, cy - 8), (cx + 114, cy - 8)], (40, 70, 110, 255), 3)   # fascia occhialini
    g.ellipse((cx + 94, cy - 14, cx + 114, cy + 2), fill=(20, 40, 70, 255), outline=(190, 230, 255, 255), width=2)
    g.ellipse((cx + 100, cy - 11, cx + 106, cy - 6), fill=(255, 255, 255, 230))
    g.line([(cx + 108, cy + 10), (cx + 113, cy + 12)], (176, 120, 100, 255), 3)   # bocca
    if glide:
        arm(0.015, skin, 21)
    else:
        arm(ph, skin, 21)
    S = SWS
    im = g.im.resize((int(560 * S), int(320 * S)), Image.LANCZOS)
    cv.paste(im, (int(x - cx * S), int(y - cy * S)), im)


def tick(cv, x, ty, col, t=None, t0=0.0, h=64, w=8, dashed=False):
    p = 1.0 if t is None else ease((t - t0) / 0.3)
    if p <= 0:
        return
    d = ImageDraw.Draw(cv)
    if dashed:
        for yy in range(int(ty - h / 2), int(ty + h / 2), 16):
            d.line((x, yy, x, yy + 9), fill=col, width=w - 2)
    else:
        hh = int(h * p)
        d.rounded_rectangle((x - w // 2, ty - hh // 2, x + w // 2, ty + hh // 2), 3, fill=col)


# ================================================================ clip Marte/Houston
def clip_meta():
    f = CACHE_ROOT / LANG / 'meta.json'
    return json.loads(f.read_text()) if f.exists() else {'frames': 800, 'dur': 26.7}


@lru_cache(maxsize=6)
def clip_frame_img(i):
    return Image.open(CACHE_ROOT / LANG / f'{i + 1:04d}.jpg').convert('RGB')


def prepara_clip(clip):
    """Estrae i fotogrammi (30 fps, 1344x756) nella cache fuori dal repository e restituisce la durata dell'audio/clip."""
    clip = Path(clip).expanduser()
    out = CACHE_ROOT / LANG
    meta = out / 'meta.json'
    key = f'{clip}|{clip.stat().st_mtime_ns}'
    if meta.exists() and json.loads(meta.read_text()).get('key') == key:
        return json.loads(meta.read_text())['dur']
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob('*.jpg'):
        f.unlink()
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(clip)]).decode().strip())
    subprocess.check_call(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(clip), '-an',
                           '-vf', f'fps={FPS},scale={CLIP_BOX[2]}:{CLIP_BOX[3]}:flags=lanczos', '-q:v', '3', str(out / '%04d.jpg')])
    n = len(list(out.glob('*.jpg')))
    meta.write_text(json.dumps({'key': key, 'frames': n, 'dur': dur}))
    return dur


# ================================================================ scene
SENT = 'Se nei test ti pianti, è perché sei arrivato a un livello di dettaglio nuovo.'


def s_apertura(cv, t):
    words_text(cv, t, SENT, 0.3, 520, 84, 1500)
    p = ease((t - 4.4) / 0.8)
    ImageDraw.Draw(cv).rectangle((960 - int(260 * p), 800, 960 + int(260 * p), 805), fill=CYAN)


def s_clip(cv, t):
    x, y, w, h = CLIP_BOX
    p = ease(t / 0.6)
    gl = gv.glow(w, h)
    cv.paste(Image.new('RGB', gl.size, (20, 120, 200)), (x - 100, y - 100), gl.point(lambda v, k=p: int(v * k)))
    meta = clip_meta()
    cv.paste(clip_frame_img(min(int(t * FPS), meta['frames'] - 1)), (x, y), gv.rmask(w, h, 28))
    ImageDraw.Draw(cv).rounded_rectangle((x, y, x + w, y + h), 28, outline=CYAN, width=4)
    chip(cv, 'Dove eravamo rimasti', 960, 904, t, 0.4, CYAN, 36, anchor='c')


def s_houston(cv, t):
    y = wrap_text(cv, t, 'Houston, abbiamo un problema.', 110, 150, 88, 0.3, 1000)
    wrap_text(cv, t, '11 novembre: la tag nuota in un palloncino non stagno.', 110, y + 30, 50, 2.0, 1000, 500, MUTED)
    gv.waves(cv, t, 760, (50, 140, 220), 12, 3, 26)
    draw_balloon(cv, 1450, 470, t, clamp((t - 1.0) / 8.0) * 0.8)


@lru_cache(maxsize=1)
def _sig():
    r = np.random.default_rng(11)
    m = np.linspace(0, 10, 500)
    v = 0.42 + 0.22 * np.abs(np.sin(m * 5.3)) + 0.14 * np.sin(m * 13.1) + 0.05 * r.standard_normal(m.size)
    return m, np.clip(v, 0.04, 1.0)


def s_grafico(cv, t):
    T(cv, 'Minuto 10: il grafico si ferma.', 110, 120, 84, t, 0.3, 700, WHITE, maxw=1700)
    px0, px1, py0, py1 = 170, 1790, 340, 760
    g = lay(1700, 480)
    g.rrect((1, 1, 1698, 478), 22, fill=CARD + (235,), outline=(40, 110, 190, 255), width=3)
    g.paste_to(cv, 110, 300)
    d = ImageDraw.Draw(cv)
    for i in range(0, 13, 2):                                       # griglia e asse dei tempi
        xx = px0 + (px1 - px0) * i / 12
        d.line((xx, py0, xx, py1), fill=(22, 52, 104), width=2)
        TM(cv, str(i), xx, py1 + 6, 26, t, 0.8, MUTED, 'c')
    for j in range(5):
        d.line((px0, py1 - (py1 - py0) * j / 4, px1, py1 - (py1 - py0) * j / 4), fill=(22, 52, 104), width=2)
    chip(cv, 'movimento della tag', 190, 312, t, 0.8, CYAN, 26)
    T(cv, 'minuti', 960, 800, 30, t, 0.8, 500, MUTED, anchor='c')
    cm = 10 * clamp((t - 1.0) / 4.0) + 2 * clamp((t - 5.2) / 0.8)
    m, v = _sig()
    pts = []
    for mm, vv in zip(m, v):
        if mm <= min(cm, 10):
            pts.append((px0 + (px1 - px0) * mm / 12, py1 - (py1 - py0) * vv * 0.92))
    if cm > 10:
        pts += [(px0 + (px1 - px0) * 10 / 12, py1), (px0 + (px1 - px0) * cm / 12, py1)]
    if len(pts) > 1:
        gg = lay(1700, 480)
        gg.line([(x - 110, y - 300) for x, y in pts], CYAN + (255,), 4)
        gg.paste_to(cv, 110, 300)
        hx, hy = pts[-1]
        d.ellipse((hx - 8, hy - 8, hx + 8, hy + 8), fill=WHITE)
    if t >= 5.0:
        xs = px0 + (px1 - px0) * 10 / 12
        for yy in range(py0, py1, 20):
            d.line((xs, yy, xs, yy + 10), fill=RED, width=4)
        chip(cv, 'minuto 10', xs - 90, py0 - 8, t, 5.0, RED, 26)
        d.line((xs, py1, px1, py1), fill=RED, width=6)
    T(cv, 'Perché?', 960, 870, 120, t, 7.0, 700, RED, anchor='c', maxw=800)


def s_lente(cv, t):
    T(cv, 'Le abbiamo dato una scatola nera.', 110, 140, 82, t, 0.3, 700, WHITE, maxw=1700)
    p = ease((t - 0.4) / 0.5)
    tx = 640 if t < 3.6 else lerp(640, 520, ease((t - 3.6) / 0.8))
    ty = 640
    tag_at(cv, tx, ty, 1.8, None)
    if t < 4.2:
        lx = 560 + 120 * math.sin(t * 1.3)
        draw_ring(cv, lx, 600, 140, t, tx, ty, 1.8)
    if t >= 3.6:
        q = ease((t - 3.6) / 0.7)
        d = ImageDraw.Draw(cv)
        for i in range(0, int(220 * q), 24):
            d.line((780 + i, 640, 780 + min(i + 12, 220 * q), 640), fill=CYAN, width=5)
        bx = 1330
        draw_box(cv, bx, 640 + 40 * (1 - q), t, door=ease((t - 4.8) / 1.0))
        if t > 6.2:
            for i in range(3):
                u = ((t - 6.2) * 0.9 + i / 3) % 1.0
                d.ellipse((bx - 8, 470 - 140 * u - 8, bx + 8, 470 - 140 * u + 8), fill=CYAN2)


def s_zaino(cv, t):
    T(cv, 'Ha confessato:', 110, 150, 64, t, 0.4, 600, MUTED)
    wrap_text(cv, t, 'lo zaino della memoria per il Bluetooth era troppo piccolo.', 110, 250, 60, 1.2, 960, 700, WHITE)
    wrap_text(cv, t, 'Un passo di troppo… e trabocca.', 110, 700, 64, 9.2, 1040, 700, RED)
    x0, y0 = 1330, 300
    TB = 10.1                                                       # istante del trabocco
    items, flying = [], []
    for i in range(9):
        ts = 2.0 + 0.7 * i
        if t < ts:
            continue
        sx, sy = slot(i)
        u = clamp((t - ts) / 0.5)
        yy = lerp(-60, sy, u * u)
        if t >= TB and i >= 6:                                      # ultima fila: schizza fuori
            tau = t - TB
            vx, vy = [(-250, -560), (40, -700), (290, -520)][i - 6]
            flying.append((x0 + sx + vx * tau, y0 + sy + vy * tau + 700 * tau * tau, 70, ITEM_COL[i]))
        else:
            items.append((sx, yy, 70, ITEM_COL[i]))
    if t >= 9.6:
        u = clamp((t - 9.6) / 0.5)
        if t < TB:
            items.append((150, lerp(-120, 52, u * u), 100, RED))
        else:
            tau = t - TB
            flying.append((x0 + 150 + 30 * tau, y0 + 52 - 380 * tau + 700 * tau * tau, 100, RED))
    shake = 9 * math.sin(55 * (t - TB)) * math.exp(-3 * (t - TB)) if t >= TB else 0.0
    flap = ease((t - TB) / 0.25) if t >= TB else 0.0
    draw_pack(cv, x0, y0, 1.0, items, shake, flap)
    for fx, fy, sz, c in flying:
        if fy < H + 80:
            free_item(cv, fx, fy, sz, c)
    n = sum(clamp((t - (2.3 + 0.7 * i)) / 0.4) for i in range(9))
    f = n / 9.0 if t < TB else 1.0
    gauge(cv, 1160, 290, 400, f, t, blink=(t > TB or f > 0.9))
    if t >= TB:                                                     # avviso
        d = ImageDraw.Draw(cv)
        c = RED if int(t * 5) % 2 == 0 else (255, 200, 200)
        d.polygon([(1195, 215), (1160, 270), (1230, 270)], fill=c)
        d.rectangle((1192, 232, 1198, 252), fill=CARD)
        d.rectangle((1192, 257, 1198, 263), fill=CARD)


def s_cambi(cv, t):
    badge(cv, 1, 110, 130, t, 0.3)
    T(cv, 'La scatola nera resta.', 205, 142, 58, t, 0.4, 700, WHITE, maxw=700)
    badge(cv, 2, 1010, 130, t, 0.9)
    T(cv, 'Zaino doppio.', 1105, 142, 58, t, 1.0, 700, WHITE, maxw=700)
    draw_box(cv, 480, 600, t, door=0.0)
    if t >= 1.4:
        p = ease((t - 1.4) / 0.4)
        check(cv, 620 - 4 * (1 - p), 330, max(int(110 * p), 12), GREEN)
    wf = 1 + smooth((t - 2.4) / 1.8)
    items = [(slot(i)[0], slot(i)[1], 70, ITEM_COL[i]) for i in range(9)]
    draw_pack(cv, 1100, 340, wf, items)
    gauge(cv, 990, 330, 400, 1 / wf if t > 1.0 else 1.0, t)
    if t > 4.6:
        check(cv, 1500 + int(160 * (wf - 1)), 240, 76, GREEN)


def s_stazione(cv, t):
    badge(cv, 3, 110, 130, t, 0.3)
    T(cv, 'Una stazione a bordo vasca.', 205, 142, 62, t, 0.4, 700, WHITE, maxw=1500)
    T(cv, 'Ogni pezzo salvato riceve una ricevuta.', 110, 260, 46, t, 1.0, 500, MUTED, maxw=1700)
    ys = 560
    xs = [260, 640, 1060, 1520]
    e = ease((t - 0.6) / 0.6)
    tag_at(cv, xs[0], ys, 1.1, (80, 230, 170), 0.6 + 0.4 * math.sin(t * 6))
    g = lay(160, 240)                                               # ricevitore: chiavetta con antenna
    g.rrect((40, 50, 120, 190), 14, fill=(14, 40, 86, 255), outline=(80, 160, 235, 255), width=4)
    g.rrect((54, 190, 106, 232), 4, fill=(150, 170, 200, 255))
    g.line([(80, 50), (80, 8)], (100, 180, 245, 255), 6)
    g.ellipse((72, 70, 88, 86), fill=GREEN + (255,))
    g.paste_to(cv, xs[1] - 80, ys - 120)
    g = lay(300, 200)                                               # piccolo computer
    g.rrect((20, 30, 280, 170), 12, fill=(14, 90, 70, 255), outline=(60, 200, 150, 255), width=4)
    g.rrect((50, 60, 110, 110), 4, fill=(20, 24, 30, 255))
    g.rrect((130, 60, 180, 100), 4, fill=(150, 160, 175, 255))
    g.rrect((230, 50, 266, 150), 4, fill=(190, 200, 215, 255))
    g.rrect((60, 128, 150, 150), 3, fill=(30, 40, 50, 255))
    g.paste_to(cv, xs[2] - 150, ys - 100)
    g = lay(300, 240)                                               # monitor
    g.rrect((20, 20, 280, 180), 14, fill=(20, 28, 44, 255), outline=(190, 205, 225, 255), width=5)
    g.rrect((34, 34, 266, 166), 6, fill=CARD + (255,))
    g.rrect((130, 180, 170, 214), 4, fill=(150, 165, 190, 255))
    g.rrect((90, 212, 210, 226), 6, fill=(150, 165, 190, 255))
    n = max(0, int((t - 2.3) / 1.1))
    for i in range(min(n, 4)):
        g.ellipse((50, 50 + i * 28, 66, 66 + i * 28), fill=GREEN + (255,))
        g.rrect((82, 54 + i * 28, 230, 62 + i * 28), 3, fill=(90, 130, 200, 255))
    g.paste_to(cv, xs[3] - 150, ys - 110)
    d = ImageDraw.Draw(cv)
    for a, b in ((xs[0] + 120, xs[1] - 90), (xs[1] + 90, xs[2] - 160), (xs[2] + 160, xs[3] - 160)):
        d.line((a, ys, b, ys), fill=(60, 120, 200), width=4)
        d.polygon([(b, ys - 10), (b + 16, ys), (b, ys + 10)], fill=(60, 120, 200))
    for x in range(xs[0], xs[2], 28):                               # percorso di ritorno delle ricevute
        d.line((x, 720, x + 14, 720), fill=(40, 150, 110), width=4)
    d.polygon([(xs[0], 710), (xs[0] - 16, 720), (xs[0], 730)], fill=(40, 150, 110))
    T(cv, 'tag', xs[0], 790, 34, t, 0.9, 600, CYAN, anchor='c')
    T(cv, 'ricevitore', xs[1], 790, 34, t, 1.0, 600, CYAN, anchor='c')
    T(cv, 'stazione', (xs[2] + xs[3]) / 2, 790, 34, t, 1.1, 600, CYAN, anchor='c')
    if t > 1.6:
        per = 1.1
        for k in range(int((t - 1.6) / per) - 1, int((t - 1.6) / per) + 1):
            if k < 0:
                continue
            u = (t - 1.6 - k * per) / per
            if not 0 <= u <= 1:
                continue
            if u < 0.6:                                             # blocco: tag -> ricevitore -> stazione
                q = u / 0.6
                px = lerp(xs[0] + 120, xs[2] - 160, q)
                d.rounded_rectangle((px - 14, ys - 14, px + 14, ys + 14), 5, fill=CYAN)
            else:                                                   # ricevuta che torna
                q = (u - 0.6) / 0.4
                px = lerp(xs[2] - 150, xs[0] + 20, q)
                d.rounded_rectangle((px - 20, 692, px + 20, 752), 5, fill=WHITE)
                d.line((px - 11, 706, px + 11, 706), fill=(120, 150, 200), width=3)
                d.line((px - 11, 716, px + 5, 716), fill=(120, 150, 200), width=3)
                d.line((px - 9, 734, px - 3, 740, px + 10, 724), fill=GREEN, width=4)


def s_contatore(cv, t):
    T(cv, 'Quasi 1000 blocchi, zero persi.', 960, 130, 84, t, 0.3, 700, WHITE, anchor='c', maxw=1700)
    u = ease((t - 0.8) / 3.0)
    n = int(round(985 * u))
    T(cv, str(n), 960, 290, 330, t, 0.8, 700, CYAN if u < 1 else WHITE, anchor='c', dur=0.1)
    T(cv, 'blocchi ricevuti', 960, 650, 46, t, 1.0, 500, MUTED, anchor='c')
    if t >= 4.0:
        p = ease((t - 4.0) / 0.5)
        g = lay(560, 190)
        g.rrect((0, 0, 560, 190 * p), 28, fill=(8, 40, 38, 240), outline=GREEN + (255,), width=5)
        g.paste_to(cv, 680, 740)
        if p >= 1:
            check(cv, 715, 790, 90, GREEN)
            T(cv, '0 persi', 830, 780, 86, t, 4.3, 700, GREEN, maxw=390)


# ---- ritmo nello spazio della corsia: passo corto (SH) / lungo (LG), la mano entra in acqua sulla tacca
SH, LG, HAND, TYN, WALLX = 170, 255, int(176 * SWS), 718, 1686
SWY = 508
RX = [-184, -14, 241, 411, 666, 836, 1091, 1261, 1516, 1686, 1941]   # tacche reali e previste (+ virtuali ai bordi)
SOL = [241, 411, 666, 836, 1091]                                     # bracciate reali
GHO = [1261, 1516, 1686]                                             # tacche previste dal ritmo
TSOL = [2.0 + (x - 241) / 113.0 for x in SOL]                        # istante in cui la mano arriva sulla tacca


def phase_at(hx):
    for a, b in zip(RX, RX[1:]):
        if a <= hx < b:
            return (hx - a) / (b - a)
    return 0.0


def lane_line(cv):
    ImageDraw.Draw(cv).line((110, TYN, 1700, TYN), fill=(52, 108, 186), width=3)


def ilab(cv, xa, xb, t, t0):
    T(cv, 'corto' if abs(xb - xa - SH) < 2 else 'lungo', (xa + xb) / 2, TYN + 14, 26, t, t0, 500, MUTED, anchor='c', dur=0.3)


def prev_lab(cv, x, t, t0):
    T(cv, 'previsto', x - 46 if x >= WALLX else x, TYN - 62, 24, t, t0, 600, CYAN2, anchor='c', dur=0.3)


def ghost(cv, x, t, t0, col=None, h=72):
    if t < t0:
        return
    pulse = 0.5 + 0.5 * math.sin((t - t0) * 6)
    tick(cv, x, TYN, col or mix((70, 120, 190), CYAN2, pulse), h=h, w=10, dashed=True)


def band(cv, cb, wb, a, y0=420, y1=780):
    if a <= 0 or wb < 1:
        return
    im = Image.new('RGBA', (int(wb), y1 - y0), RED + (int(70 * a),))
    cv.paste(im, (int(cb - wb / 2), y0), im)
    d = ImageDraw.Draw(cv)
    d.line((cb - wb / 2, y0, cb - wb / 2, y1), fill=RED, width=3)
    d.line((cb + wb / 2, y0, cb + wb / 2, y1), fill=RED, width=3)


def hand_tacche(t):
    return 113 * t + 15


def hand_proiez(t):                                                  # rallenta da 113 a 40 px/s in 1 s
    return hand_tacche(10.0) + 40 * t + 24.3 * (1 - (1 - min(t, 1.0)) ** 3)


def hand_tocco(t):
    h0 = hand_proiez(6.0)
    return h0 + (WALLX - h0) * min(t / 6.0, 1.0)


def hand_scivolata(t):
    if t < 1.8:
        return 1516 - 60 * (1.8 - t)
    tau = min(t - 1.8, 4.2)
    return 1516 + 81 * tau - (81 / 8.4) * tau * tau


def s_metronomo(cv, t):
    T(cv, 'Non solo hardware.', 110, 330, 96, t, 0.3, 700, WHITE, maxw=1000)
    T(cv, 'Anche il ritmo.', 110, 460, 112, t, 0.7, 700, CYAN, maxw=1000)
    g = lay(420, 600)
    g.poly([(90, 560), (330, 560), (260, 40), (160, 40)], (16, 46, 100, 255))
    g.line([(90, 560), (330, 560), (260, 40), (160, 40), (90, 560)], (80, 160, 235, 255), 6)
    th = math.radians(30) * math.sin(2 * math.pi * t * 1.0)       # una battuta ogni 0,5 s (120 BPM)
    px, py = 210, 500
    ex, ey = px + 430 * math.sin(th), py - 430 * math.cos(th)
    g.line([(px, py), (ex, ey)], WHITE + (255,), 7)
    wx, wy = px + 270 * math.sin(th), py - 270 * math.cos(th)
    g.ellipse((wx - 26, wy - 26, wx + 26, wy + 26), fill=AMBER + (255,))
    g.ellipse((px - 18, py - 18, px + 18, py + 18), fill=CYAN + (255,))
    for s_ in (-1, 1):
        near = abs(math.sin(th) * s_ - 0.5) < 0.12
        c = CYAN if near else (50, 100, 170)
        g.ellipse((210 + s_ * 175 - 11, 120 - 11, 210 + s_ * 175 + 11, 120 + 11), fill=c + (255,))
    g.paste_to(cv, 1250, 190)
    ty = 900                                                         # il ritmo: tacche corto/lungo che continuano
    ImageDraw.Draw(cv).line((110, ty, 1810, ty), fill=(52, 108, 186), width=3)
    xs = [150, 235, 363, 448, 576, 661, 789, 874, 1002, 1087]
    for i, xk in enumerate(xs):
        t0 = 1.2 + 0.3 * i
        if i < 5:
            tick(cv, xk, ty, CYAN, t, t0, h=56, w=7)
        elif t >= t0:
            ghost(cv, xk, t, t0, h=56)


def s_tacche(cv, t):
    T(cv, 'Ogni bracciata lascia una tacca:', 110, 110, 66, t, 0.3, 700, WHITE, maxw=1700)
    T(cv, 'corto, lungo, corto, lungo.', 110, 200, 66, t, 1.2, 700, CYAN, maxw=1700)
    h = hand_tacche(t)
    pool(cv, t, wall=True)
    pool_top(cv, t)
    swimmer(cv, h - HAND, SWY, phase_at(h), False, t)
    lane_line(cv)
    for k, xk in enumerate(SOL):
        tick(cv, xk, TYN, CYAN, t, TSOL[k])
        if 0 <= t - TSOL[k] < 0.35:                                  # la tacca cade dove la mano e' entrata
            yy = SWY + 14 + (TYN - 40 - SWY) * ((t - TSOL[k]) / 0.35) ** 2
            ImageDraw.Draw(cv).ellipse((xk - 8, yy - 8, xk + 8, yy + 8), fill=CYAN2)
        if k:
            ilab(cv, SOL[k - 1], xk, t, TSOL[k])


def s_fantasma(cv, t):
    T(cv, 'Il ritmo si proietta in avanti.', 110, 140, 80, t, 0.3, 700, WHITE, maxw=1700)
    h = hand_proiez(t)
    pool(cv, t, wall=True)
    pool_top(cv, t)
    swimmer(cv, h - HAND, SWY, phase_at(h), False, t)
    lane_line(cv)
    for k, xk in enumerate(SOL):
        tick(cv, xk, TYN, CYAN)
        if k:
            ilab(cv, SOL[k - 1], xk, t, -9)
    WT, WS = 0.9, 900.0                                              # lancio dell'onda dall'ultima tacca
    wx = SOL[-1] + WS * (t - WT)
    prev = SOL[-1]
    for i, xk in enumerate(GHO):
        t0 = WT + (xk - SOL[-1]) / WS
        if h > xk:
            tick(cv, xk, TYN, CYAN)
        else:
            ghost(cv, xk, t, t0, col=WHITE if t - t0 < 0.25 else None)
            prev_lab(cv, xk, t, t0 + 0.3)
        ilab(cv, prev, xk, t, t0 + 0.2)
        prev = xk
    if t >= WT:
        im = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        e = min(wx, WALLX + 40)
        if wx < WALLX + 300:
            for j in range(26):                                      # scia luminosa dietro la testa dell'onda
                xa = e - j * 10
                if xa < SOL[-1]:
                    break
                al = int(230 * (1 - j / 26) ** 1.6)
                d.line((xa - 10, 130, xa, 130), fill=CYAN2 + (al,), width=max(3, 14 - j // 2))
            d.ellipse((e - 16, 114, e + 16, 146), fill=WHITE + (255,))
            d.polygon([(e + 30, 130), (e + 6, 112), (e + 6, 148)], fill=CYAN2 + (255,))
        r = (t - WT) * 190                                           # anelli all'origine
        for rr, al in ((r, 1.0), (r * 0.6, 0.8)):
            a_ = int(200 * max(0.0, 1 - (t - WT) / 0.9) * al)
            if a_ > 0 and rr > 2:
                d.ellipse((SOL[-1] - rr, 130 - rr, SOL[-1] + rr, 130 + rr), outline=CYAN2 + (a_,), width=4)
        cv.paste(im, (0, TYN - 130), im)


def s_tocco(cv, t):
    T(cv, 'Il sensore: il tocco è qui… più o meno.', 110, 100, 60, t, 0.5, 700, WHITE, maxw=1700)
    T(cv, 'Il tocco cade su un battito del ritmo.', 110, 185, 60, t, 5.2, 700, GREEN, maxw=1700)
    TT_ = 6.0                                                        # istante del tocco
    h = hand_tocco(t)
    pool(cv, t, wall=True)
    pool_top(cv, t)
    swimmer(cv, h - HAND, SWY, phase_at(h), False, t)
    lane_line(cv)
    for k, xk in enumerate(SOL + GHO[:1]):
        tick(cv, xk, TYN, CYAN)
        if k:
            ilab(cv, (SOL + GHO)[k - 1], xk, t, -9)
    ilab(cv, GHO[0], GHO[1], t, -9)
    ilab(cv, GHO[1], GHO[2], t, -9)
    if h > GHO[1]:
        tick(cv, GHO[1], TYN, CYAN)
    else:
        ghost(cv, GHO[1], t, 0)
        prev_lab(cv, GHO[1], t, 0.2)
    u = ease((t - 3.4) / 2.2)                                       # fascia di incertezza del sensore
    wb, cb = 440 * (1 - u) + 26 * u, 1560 * (1 - u) + WALLX * u
    if t >= 0.5:
        band(cv, cb, wb, ease((t - 0.5) / 0.5))
    if t < TT_:
        ghost(cv, GHO[2], t, 0, col=mix((70, 120, 190), WHITE, u) if u > 0 else None, h=72 + int(12 * u))
        prev_lab(cv, GHO[2], t, 0.2)
    else:
        tick(cv, GHO[2], TYN, GREEN, t, TT_, h=84, w=12)
    TM(cv, num(32.47, 2) + ' s', 1560, 805, 76, t, 6.4, GREEN, 'c')
    if TT_ < t < TT_ + 0.5:
        f = clamp(1 - (t - TT_) / 0.5)
        im = Image.new('RGBA', (100, 410), (255, 255, 255, int(110 * f)))
        cv.paste(im, (1700, 360), im)


def s_scivolata(cv, t):
    T(cv, 'Tacca vuota: scivolata finale.', 110, 110, 66, t, 0.5, 700, WHITE, maxw=1700)
    glide = t >= 1.8
    h = hand_scivolata(t)
    pool(cv, t, wall=True)
    pool_top(cv, t)
    swimmer(cv, h - HAND, SWY, phase_at(h) if not glide else 0.0, glide, t)
    lane_line(cv)
    allx = SOL + GHO[:2]
    for k, xk in enumerate(allx):
        if xk == GHO[1]:
            tick(cv, xk, TYN, CYAN, t, 1.8)
        else:
            tick(cv, xk, TYN, CYAN)
        if k:
            ilab(cv, allx[k - 1], xk, t, -9)
    ilab(cv, GHO[1], GHO[2], t, -9)
    d = ImageDraw.Draw(cv)
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    for yy in range(TYN - 36, TYN + 36, 16):                        # tacca prevista, rimasta vuota
        d.line((WALLX, yy, WALLX, yy + 9), fill=mix((70, 100, 160), MUTED, pulse), width=7)
    d.ellipse((WALLX - 14, TYN - 58, WALLX + 14, TYN - 30), outline=mix((70, 100, 160), MUTED, pulse), width=4)
    if glide:                                                       # linee di velocita'
        for i in range(4):
            xx = h - HAND - 150 - i * 50 - 30 * ((t * 2) % 1)
            d.line((xx, 520 + i * 22, xx - 60, 520 + i * 22), fill=(120, 200, 255), width=3)
    if t >= 6.0:
        T(cv, 'Arriva bene al muro!', 110, 195, 66, t, 6.0, 700, GREEN, maxw=1400)
        check(cv, 1560, 150, 72, GREEN)
        f = clamp(1 - (t - 6.0) / 0.5)
        if f > 0:
            im = Image.new('RGBA', (100, 410), (255, 255, 255, int(110 * f)))
            cv.paste(im, (1700, 360), im)


def s_verifica(cv, t):
    y = wrap_text(cv, t, 'Pista promettente, in verifica:', 110, 110, 70, 0.3, 1700, 700, WHITE)
    wrap_text(cv, t, "su 12 arrivi l'errore scende", 110, y + 10, 48, 1.2, 1700, 500, MUTED)
    wrap_text(cv, t, 'da circa 0,8 a 0,5 s, ma dipende dalla taratura.', 110, y + 70, 48, 1.5, 1700, 500, MUTED)
    p = ease((t - 2.4) / 0.6)
    g = lay(1100, 400)
    g.rrect((0, 0, 1100, 400 * p), 30, fill=(30, 26, 8, 245), outline=YELLOW + (255,), width=6)
    g.paste_to(cv, 410, 470)
    if p >= 1:
        d = ImageDraw.Draw(cv)
        for i in range(0, 18):                                      # fascia a strisce
            x = 430 + i * 60
            d.polygon([(x, 490), (x + 30, 490), (x + 10, 540), (x - 20 if i else x, 540)], fill=YELLOW)
        T(cv, 'IN VERIFICA', 960, 555, 76, t, 3.0, 700, YELLOW, anchor='c', track=6)
        TM(cv, num(0.8, 1) + ' s', 640, 700, 110, t, 3.6, YELLOW, 'c')
        TM(cv, '→', 960, 705, 110, t, 4.0, YELLOW, 'c')
        TM(cv, num(0.5, 1) + ' s', 1280, 700, 110, t, 4.4, YELLOW, 'c')
        chip(cv, '12 arrivi', 560, 860, t, 5.0, YELLOW, 30)
        chip(cv, 'dipende dalla taratura', 800, 860, t, 5.5, YELLOW, 30)


def s_prossimo(cv, t):
    T(cv, 'Prossimo livello: 1 ora a banco con 2 tag.', 110, 130, 70, t, 0.3, 700, WHITE, maxw=1700)
    tag_at(cv, 480, 560, 1.7, GREEN, 0.5 + 0.5 * math.sin(t * 5))
    tag_at(cv, 900, 560, 1.7, GREEN, 0.5 + 0.5 * math.sin(t * 5 + 1.5))
    cx, cy, r = 1450, 560, 190
    g = lay(2 * r + 40, 2 * r + 40)
    c = r + 20
    g.ellipse((c - r, c - r, c + r, c + r), fill=CARD + (255,), outline=CYAN + (255,), width=8)
    for i in range(12):
        a = math.radians(i * 30)
        g.line([(c + (r - 22) * math.sin(a), c - (r - 22) * math.cos(a)), (c + (r - 6) * math.sin(a), c - (r - 6) * math.cos(a))], WHITE + (255,), 5)
    mn = 360 * clamp((t - 1.0) / 5.0)
    for ang, ln, wd, col in ((mn / 12, 0.5 * r, 12, WHITE), (mn, 0.82 * r, 8, CYAN)):
        a = math.radians(ang)
        g.line([(c, c), (c + ln * math.sin(a), c - ln * math.cos(a))], col + (255,), wd)
    g.ellipse((c - 12, c - 12, c + 12, c + 12), fill=CYAN + (255,))
    g.paste_to(cv, cx - c, cy - c)
    if t >= 6.3:                                                    # l'acqua sale: di nuovo in vasca
        lv = lerp(H + 60, 400, ease((t - 6.3) / 2.6))
        d = ImageDraw.Draw(cv)
        pts = [(x, lv + 14 * math.sin(x / 140 + t * 2.2)) for x in range(0, W + 30, 30)]
        d.polygon(pts + [(W, H), (0, H)], fill=(14, 100, 172))
        d.line(pts, fill=(120, 215, 250), width=4)
        gv.bubbles(cv, t)
    T(cv, 'Poi di nuovo in vasca.', 960, 770, 88, t, 7.2, 700, WHITE, anchor='c', maxw=1700)


def s_frase(cv, t):
    gv.waves(cv, t, 880, (170, 232, 252), 10, 3, 24)
    words_text(cv, t, SENT, 0.3, 480, 84, 1500, col=WHITE, hicol=NAVY)
    p = ease((t - 4.4) / 0.8)
    ImageDraw.Draw(cv).rectangle((960 - int(260 * p), 760, 960 + int(260 * p), 765), fill=WHITE)


def s_chiusura(cv, t):
    gv.waves(cv, t, 960, (30, 100, 180), 12, 3, 26)
    wipe_text(cv, (('SWIM', WHITE), ('TIMER', CYAN)), 960, 200, 230, t, 0.5, 1.0, 700)
    d = ImageDraw.Draw(cv)
    lp = ease((t - 1.4) / 0.8)
    d.rectangle((960 - int(480 * lp), 500, 960 + int(480 * lp), 505), fill=CYAN)
    rows = [('WEB', 'swimtimer-pzero.web.app'), ('GITHUB', 'PZero/SwimTimer')]
    for i, (k, v) in enumerate(rows):
        t0 = 2.2 + 0.5 * i
        y = 620 + i * 110
        T(cv, k, 700, y + 12, 38, t, t0, 600, CYAN, anchor='r', track=3)
        T(cv, v, 740, y, 66, t, t0 + 0.1, 600, WHITE)


# (inizio, durata, funzione, sfondo)
SCENES = [
    (0, 6, s_apertura, 'dark'), (6, 27, s_clip, 'dark'), (33, 10, s_houston, 'dark'), (43, 12, s_grafico, 'dark'),
    (55, 8, s_lente, 'dark'), (63, 15, s_zaino, 'dark'), (78, 8, s_cambi, 'dark'), (86, 10, s_stazione, 'dark'),
    (96, 6, s_contatore, 'dark'), (102, 4, s_metronomo, 'dark'), (106, 10, s_tacche, 'dark'), (116, 6, s_fantasma, 'dark'),
    (122, 12, s_tocco, 'dark'), (134, 8, s_scivolata, 'dark'), (142, 10, s_verifica, 'dark'), (152, 10, s_prossimo, 'dark'),
    (162, 10, s_frase, 'light'), (172, 8, s_chiusura, 'dark'),
]
TRANS = ['dissolve', 'dissolve', 'push', 'wipe', 'zoom', 'pushup', 'push', 'wipe', 'zoom', 'push', 'pushup', 'push', 'wipe', 'zoom',
         'pushup', 'dissolve', 'wipe']


def scene_frame(k, ts):
    st, du, fn, kind = SCENES[k]
    bg = (make_light_bg() if kind == 'light' else gv.make_bg()).copy()
    gv.bubbles(bg, ts + st)
    fn(bg, ts)
    return bg


def frame_image(i):
    t = i / FPS
    k = max(j for j, s in enumerate(SCENES) if s[0] <= t + 1e-9)
    ts = t - SCENES[k][0]
    img = scene_frame(k, ts)
    if k > 0 and ts < 0.4:
        a = scene_frame(k - 1, t - SCENES[k - 1][0])
        img = gv.transition(a, img, TRANS[(k - 1) % len(TRANS)], ts / 0.4)
    if 102 <= t < 102.3:                                    # lampo sul groove
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.5 * (1 - (t - 102) / 0.3))
    if 178.0 <= t < 178.2:                                  # stacco finale
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.3 * (1 - (t - 178) / 0.2))
    ImageDraw.Draw(img).rectangle((0, H - 6, int(W * t / DUR), H), fill=CYAN)
    if t > 178.6:
        img = Image.blend(img, Image.new('RGB', (W, H), (0, 0, 0)), clamp((t - 178.6) / 1.3))
    return img


def frame_bytes(i):
    return frame_image(i).tobytes()


def miniatura(path):
    bg = gv.make_bg().copy()
    gv.waves(bg, 1.0, 780, (50, 140, 220), 12, 3, 26)
    draw_balloon(bg, 1400, 470, 1.0, 0.45)
    T(bg, 'SWIM', 100, 90, 130, 9, 0, 700, WHITE)
    T(bg, 'TIMER', 440, 90, 130, 9, 0, 700, CYAN)
    ImageDraw.Draw(bg).rectangle((110, 260, 640, 266), fill=CYAN)
    wrap_text(bg, 9, 'Houston, abbiamo un problema.', 100, 320, 130, 0, 1000, 700, WHITE, gap=0.0, lh=1.12)
    bg.resize((1280, 720), Image.LANCZOS).save(path)


# ================================================================ audio
def audio_args(wav, clip, dur_clip, nsec=None):
    """Filtro: musica a -18 dB (rampe di 1 s) mentre parla la clip, audio della clip dai 6,0 s."""
    e = CLIP_T0 + dur_clip
    g = 10 ** (DUCK_DB / 20)
    vol = f"volume='1-{1 - g:.4f}*(clip((t-{CLIP_T0 - 1})/1,0,1)-clip((t-{e})/1,0,1))':eval=frame"
    fc = (f"[1:a]{vol}[m];[2:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(CLIP_T0 * 1000)}:all=1[c];"
          f"[m][c]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    return fc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', help='clip Marte/Houston (predefinita in ~/Downloads, diversa per lingua)')
    ap.add_argument('--anteprima', nargs='*', type=float)
    ap.add_argument('--dir', default=str(HERE))
    ap.add_argument('--solo-miniatura', action='store_true')
    ap.add_argument('--prova-audio', type=float, help='scrive solo il mix audio dei primi N secondi (WAV) in --dir')
    ap.add_argument('--no-musica', action='store_true')
    ap.add_argument('--lingua', choices=['it', 'en'], default='it')
    a = ap.parse_args()
    if a.lingua != LANG:
        env = dict(os.environ, SWIMTIMER_LANG=a.lingua)
        sys.exit(subprocess.call([sys.executable, __file__] + sys.argv[1:], env=env))
    if a.solo_miniatura:
        miniatura(HERE / f'miniatura_houston_{LANG}.png')
        return
    clip = Path(a.clip or CLIP_DEFAULT[LANG]).expanduser()
    dclip = prepara_clip(clip)
    if a.anteprima:
        Path(a.dir).mkdir(parents=True, exist_ok=True)
        for tsec in a.anteprima:
            frame_image(int(round(tsec * FPS))).save(Path(a.dir) / f'v4_{LANG}_{tsec:06.2f}.png')
        return
    wav = HERE / 'musica_v4.wav'
    if not a.no_musica or not wav.exists():
        import musica_v4
        y, lufs, peak = musica_v4.compose(wav)
        print(f'Musica: {lufs} LUFS, picco {peak} dBFS')
    fc = audio_args(wav, clip, dclip)
    if a.prova_audio:
        Path(a.dir).mkdir(parents=True, exist_ok=True)
        out = Path(a.dir) / f'prova_audio_{LANG}.wav'
        subprocess.check_call(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(wav), '-i', str(wav), '-i', str(clip),
                               '-filter_complex', fc, '-map', '[a]', '-t', str(a.prova_audio), '-ar', '48000', '-ac', '2', str(out)])
        print('Prova audio:', out)
        return
    miniatura(HERE / f'miniatura_houston_{LANG}.png')
    out = HERE / f'SwimTimer_houston_{LANG}.mp4'
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-i', str(wav), '-i', str(clip), '-filter_complex', fc.replace('[a]', '[aout]'), '-map', '0:v', '-map', '[aout]',
           '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-maxrate', '8M', '-bufsize', '16M', '-g', '60',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-t', str(DUR), '-movflags', '+faststart', str(out)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(max(2, (os.cpu_count() or 4) - 1)) as pool_:
        for n, fb in enumerate(pool_.imap(frame_bytes, range(NFRAMES), chunksize=8)):
            pr.stdin.write(fb)
            if n % 300 == 0:
                print(f'fotogramma {n}/{NFRAMES}', flush=True)
    pr.stdin.close()
    pr.wait()
    print('Fatto:', out)


if __name__ == '__main__':
    main()
