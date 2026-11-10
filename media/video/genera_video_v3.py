"""Video v3 «Il primo test in vasca»: 150 s, 1920x1080, 30 fps, IT ed EN, musica originale (musica_v3.py).

Riusa la grafica di genera_video.py / genera_video_v2.py (testo cinetico, pannelli, transizioni, sfondo) con immagini REALI
della sessione del 9/11/2026 dell'autore (scelta dell'autore): fotogrammi del video subacqueo, grafici IMU e OpenCV.
Le immagini si generano con prepara_img_v3.py in una cartella FUORI dal repository (dati personali).

Uso:  python media/video/genera_video_v3.py --img CARTELLA_IMG                       (italiano: musica + miniatura + video)
      python media/video/genera_video_v3.py --img CARTELLA_IMG --lingua en --no-musica
      python media/video/genera_video_v3.py --img CARTELLA_IMG --anteprima 3 40 80 --dir CARTELLA
"""
import argparse
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
LANG = os.environ.get('SWIMTIMER_LANG', 'it')
import genera_video_v2 as v2  # noqa: E402
import genera_video as gv  # noqa: E402

if LANG == 'en':
    from testi_v3_en import EN as _TR3
    gv._TR = _TR3
else:
    gv._TR = {}
tr = gv.tr
T, block, kicker, wipe_text, G, panel, tlayer = gv.T, gv.block, gv.kicker, gv.wipe_text, gv.G, gv.panel, gv.tlayer
ease, smooth, clamp, lerp = gv.ease, gv.smooth, gv.clamp, gv.lerp
TM, chip, check, num = v2.TM, v2.chip, v2.check, v2.num
W, H, FPS, DUR = gv.W, gv.H, gv.FPS, 150.0
NFRAMES = int(DUR * FPS)
CYAN, CYAN2, WHITE, MUTED, AMBER, GREEN = gv.CYAN, gv.CYAN2, gv.WHITE, gv.MUTED, gv.AMBER, gv.GREEN
RED, VIOLET, ORANGE, CARD = v2.RED, v2.VIOLET, v2.ORANGE, v2.CARD
IMG3 = Path(os.environ.get('SWIMTIMER_IMG3', '.'))
TOCCO = 151.62

_src_v2 = v2.src


@lru_cache(maxsize=None)
def src(key):
    if key[0] == 'r3':                              # ('r3', file nella cartella delle immagini reali, riquadro o None)
        im = Image.open(IMG3 / key[1]).convert('RGB')
        return im.crop(key[2]) if len(key) > 2 and key[2] else im
    return _src_v2(key)


gv.src = src
R = lambda name, box=None: ('r3', name, box)  # noqa: E731
FULL = (0.5, 0.5, 1.0)


def stat_card(cv, t, t0, x, y, w, big, small, col=CYAN, bsz=72):
    """Scheda con un numero grande e una didascalia."""
    if t < t0:
        return
    p = ease((t - t0) / 0.4)
    g = G(w, 170)
    g.rrect((0, 0, w * p, 170), 20, fill=CARD + (235,), outline=col + (255,), width=3)
    g.paste_to(cv, int(x), int(y))
    if p >= 1:
        T(cv, big, x + 28, y + 18, bsz, t, t0 + 0.15, 700, col, maxw=w - 50)
        T(cv, small, x + 30, y + 112, 30, t, t0 + 0.3, 500, MUTED, maxw=w - 50)


# ---------------------------------------------------------------- scene
def s_hook(cv, t):
    """Il tocco fotogramma per fotogramma: 30 fotogrammi (0,6 s reali) in 4 s, poi fermo immagine."""
    box = (110, 150, 1240, 700)
    k = int(clamp((t - 0.4) / 4.0) * 30)
    panel(cv, R(f'tocco/{k:03d}.jpg'), box, FULL, FULL, t, t0=0.1, dur=1, reveal=0.5)
    if t >= 0.6:
        x, y, w, h = box
        d = ImageDraw.Draw(cv)
        xs = x + int(w * 438 / 1440)                 # bordo del muro nell'inquadratura
        for yy in range(y + 10, y + h - 10, 26):
            d.line((xs, yy, xs, yy + 14), fill=AMBER, width=4)
        chip(cv, 'bordo del muro', xs - 120, y + h - 80, t, 0.9, AMBER, 26, (4, 12, 30))
        tv = TOCCO + (k - 30) * 0.02
        TM(cv, f'{num(tv, 2)} s  ·  ' + tr('fotogramma') + f' {round(tv * 50)}', x + 24, y + 24, 36, t, 0.6, WHITE)
    kicker(cv, 'TEST IN VASCA', t, 0.3, 1410, 170)
    T(cv, 'Quando tocca', 1410, 280, 78, t, 0.6, 700, WHITE, maxw=440)
    T(cv, 'davvero', 1410, 370, 78, t, 0.8, 700, WHITE, maxw=440)
    T(cv, 'il muro?', 1410, 460, 78, t, 1.0, 700, CYAN, maxw=440)
    T(cv, '1 fotogramma = 0,02 s', 1410, 610, 40, t, 2.0, 500, MUTED, maxw=440)
    if t > 4.6:
        p = ease((t - 4.6) / 0.5)
        x, y, w, h = box
        r = int(40 + 30 * (1 - p))
        cx, cy = x + int(w * 400 / 1440), y + int(h * 505 / 810)   # punta delle dita nel fotogramma del tocco (1440x810)
        ImageDraw.Draw(cv).ellipse((cx - r, cy - r, cx + r, cy + r), outline=RED, width=5)
        T(cv, 'ADESSO?', 1410, 720, 92, t, 4.8, 700, RED, maxw=440)


def s_prova(cv, t):
    block(cv, t, 'LA PROVA · 9 NOVEMBRE', [('Una camera,', WHITE), ('un tag in testa.', CYAN)], [], tsz=88, maxw=820, cy=230)
    panel(cv, R('largo.jpg'), (110, 400, 960, 540), FULL, (0.45, 0.5, 0.85), t, t0=0.3, dur=9)
    chip(cv, 'Insta360 X4 sul fondo, vicino al muro', 130, 860, t, 1.2, CYAN, 28, (4, 12, 30))
    cards = [('8:50', 'di video a 50 fps', CYAN), ('17 min', 'di dati IMU a 214 Hz', GREEN), ('2 MiB', 'memoria piena: fine registrazione', AMBER),
             ('±16 g', '±1000 °/s · 6 assi', VIOLET)]
    for i, (a, b, col) in enumerate(cards):
        stat_card(cv, t, 1.0 + 0.5 * i, 1130 + (i % 2) * 350, 400 + (i // 2) * 200, 330, a, b, col)
    T(cv, 'Nuotate brevi: partenza, virata, arrivo, pausa.', 1130, 830, 34, t, 3.4, 500, WHITE, maxw=680)


def s_sync(cv, t):
    block(cv, t, 'SINCRONIA', [('Un colpo sul tag', WHITE), ('= istante zero.', CYAN)], [], tsz=88, maxw=900, cy=220)
    panel(cv, R('sync.jpg'), (110, 400, 760, 428), FULL, (0.62, 0.45, 0.8), t, t0=0.3, dur=7)
    panel(cv, R('sync_picco.png'), (920, 400, 900, 390), FULL, FULL, t, t0=0.7, dur=1)
    chip(cv, '11,4 g', 1450, 820, t, 1.6, VIOLET, 40)
    TM(cv, 'video 0,82 s  ↔  dati: picco di |a|', 920, 900, 38, t, 2.2, CYAN2)
    TM(cv, 't_dati = t_picco + (t_video − 0,82) · k', 110, 900, 34, t, 3.0, WHITE)


def s_mano(cv, t):
    block(cv, t, 'ETICHETTE A MANO', [('Ogni evento,', WHITE), ('fotogramma per fotogramma.', CYAN)], [], tsz=80, maxw=1700, cy=200)
    panel(cv, R('editor_1.png', (0, 270, 2853, 1030)), (110, 330, 1700, 452), FULL, (0.45, 0.5, 0.75), t, t0=0.3, dur=9.5)
    evs = [('78', 'eventi'), ('15', 'arrivi A'), ('14', 'partenze P'), ('12', 'virate V'), ('36', 'bracciate B')]
    cols = [WHITE, RED, GREEN, AMBER, CYAN]
    x = 110
    for i, ((n_, s), col) in enumerate(zip(evs, cols)):
        x += chip(cv, f'{n_}  ' + tr(s), x, 830, t, 1.2 + 0.3 * i, col, 36) + 22
    T(cv, 'Il riferimento su cui tarare i filtri.', 110, 940, 40, t, 3.0, 500, MUTED, maxw=1700)


def s_filtri(cv, t):
    block(cv, t, 'FILTRI SUI DATI IMU', [('La testa racconta', WHITE), ('cosa succede.', CYAN)], [], tsz=80, maxw=780, cy=200)
    panel(cv, R('pagina_analisi.png', (560, 260, 1100, 760)), (110, 330, 680, 568), FULL, (0.5, 0.5, 0.85), t, t0=0.3, dur=15)
    chip(cv, 'testa nello spazio (dati reali)', 130, 830, t, 1.0, CYAN, 26, (4, 12, 30))
    panel(cv, R('pagina_analisi.png', (1120, 60, 2880, 990)), (830, 110, 990, 523), FULL, (0.6, 0.45, 0.8), t, t0=0.6, dur=15)
    rules = [('Orientamento della testa', 'filtro di Mahony: giroscopio + gravità', CYAN),
             ('Arrivo', 'viso al cielo > 0,8 per 0,3 s, dopo almeno 3 s di nuotata', RED),
             ('Virata', 'sommità della testa verso il fondo (capriola)', AMBER),
             ('Partenza', 'prima scivolata 2–12 s dopo l\'arrivo', GREEN)]
    y = 670
    for i, (a, b, col) in enumerate(rules):
        t0 = 2.0 + 1.8 * i
        if t >= t0:
            ImageDraw.Draw(cv).rectangle((830, y + 6, 836, y + 76), fill=col)
        T(cv, a, 860, y, 40, t, t0, 700, WHITE, maxw=950)
        T(cv, b, 860, y + 46, 30, t, t0 + 0.15, 400, MUTED, maxw=950)
        y += 96


def s_risultati(cv, t):
    block(cv, t, 'RISULTATI DEI FILTRI', [('Vicini.', WHITE), ('Non abbastanza.', RED)], [], tsz=96, maxw=820, cy=230)
    rows = [('Arrivi trovati', '10 / 15', AMBER), ('Errore sull\'arrivo', '± 0,88 s', RED), ('Partenze trovate', '11 / 14', AMBER),
            ('Virate trovate', '11 / 12', GREEN), ('Tempo partenza - arrivo', '± 1,47 s', RED)]
    y = 420
    for i, (a, b, col) in enumerate(rows):
        t0 = 0.8 + 0.6 * i
        if t >= t0:
            p = ease((t - t0) / 0.4)
            ImageDraw.Draw(cv).rounded_rectangle((110, y, 110 + int(1000 * p), y + 92), 16, fill=CARD, outline=(40, 110, 190), width=2)
        T(cv, a, 140, y + 20, 44, t, t0 + 0.1, 500, WHITE, maxw=620)
        TM(cv, b, 1080, y + 18, 50, t, t0 + 0.25, col, 'r')
        y += 110
    if t > 4.2:
        p = ease((t - 4.2) / 0.5)
        g = G(620, 360)
        g.rrect((0, 0, 620, 360 * p), 26, fill=(40, 10, 20, 230), outline=RED + (255,), width=4)
        g.paste_to(cv, 1200, 420)
        T(cv, 'OBIETTIVO', 1240, 460, 40, t, 4.5, 600, MUTED, track=4)
        TM(cv, '± 0,3 s', 1240, 520, 110, t, 4.6, WHITE)
        T(cv, 'non raggiunto', 1240, 680, 62, t, 5.0, 700, RED, maxw=540)


def s_twist(cv, t):
    block(cv, t, 'COLPO DI SCENA', [('Lo stesso arrivo,', WHITE), ('etichettato due volte.', CYAN)], [], tsz=80, maxw=1700, cy=190)
    panel(cv, R('etichetta_vecchia.jpg'), (110, 320, 830, 467), FULL, (0.4, 0.5, 0.8), t, t0=0.3, dur=6)
    panel(cv, R('etichetta_nuova.jpg'), (990, 320, 830, 467), FULL, (0.4, 0.5, 0.8), t, t0=0.9, dur=6)
    chip(cv, 'prima: 152,06 s', 130, 720, t, 1.0, MUTED, 30, (4, 12, 30))
    chip(cv, 'verificato: 151,62 s', 1010, 720, t, 1.6, GREEN, 30, (4, 12, 30))
    TM(cv, '−0,44 s', 1010, 336, 56, t, 2.2, RED)
    items = [('Stessi arrivi, due passate: fino a ±0,45 s', RED), ('Editor a 30 fps su un video a 50 fps', AMBER),
             ('Orologi di camera e tag: deriva dello 0,24%', AMBER)]
    y = 830
    for i, (s, col) in enumerate(items):
        t0 = 3.0 + 0.9 * i
        if t >= t0:
            check(cv, 110 + (i % 3) * 0, y, 40, col)
        T(cv, s, 165, y + 2, 36, t, t0, 600, WHITE, maxw=1100)
        y += 62
    if t > 8.0:
        p = ease((t - 8.0) / 0.6)
        g = G(640, 220)
        g.rrect((0, 0, 640, 220 * p), 24, fill=CARD + (245,), outline=CYAN + (255,), width=4)
        g.paste_to(cv, 1180, 830)
        T(cv, 'Il problema era', 1220, 860, 50, t, 8.3, 600, WHITE, maxw=560)
        T(cv, 'il riferimento.', 1220, 930, 66, t, 8.6, 700, CYAN, maxw=560)
    pp = clamp((t - 9.6) / 4.4)                       # tensione verso il drop
    ImageDraw.Draw(cv).rectangle((0, 0, int(W * pp), 6), fill=CYAN)


def s_cv1(cv, t):
    block(cv, t, 'OPENCV · 1', [('Il video', WHITE), ('si analizza da solo.', CYAN)], [], tsz=84, maxw=1700, cy=190)
    boxes = [(110, 330), (720, 330), (1330, 330)]
    names = ['maschera_0.png', 'maschera_1.png', 'maschera_2.png']
    labs = [('fotogramma', CYAN), ('differenza dallo sfondo', RED), ('stabilizzata e pulita', AMBER)]
    for i, ((x, y), n_, (lab, col)) in enumerate(zip(boxes, names, labs)):
        panel(cv, R(n_), (x, y, 580, 326), FULL, (0.5, 0.5, 0.95), t, t0=0.4 + 0.5 * i, dur=10)
        chip(cv, lab, x + 20, y + 346, t, 0.9 + 0.5 * i, col, 30)
    steps = ['Stabilizzazione: l\'inquadratura oscilla di qualche pixel (ECC)', 'Sfondo mediano ogni 10 s: resta solo il corpo',
             'Filtro colore pelle contro le bolle della capriola']
    y = 780
    for i, s in enumerate(steps):
        t0 = 3.0 + 1.6 * i
        if t >= t0:
            check(cv, 110, y, 44, [CYAN, GREEN, AMBER][i])
        T(cv, s, 175, y + 2, 40, t, t0, 600, WHITE, maxw=1600)
        y += 78


def s_cv2(cv, t):
    block(cv, t, 'OPENCV · 2', [('Distanza dal muro,', WHITE), ('50 volte al secondo.', CYAN)], [], tsz=80, maxw=900, cy=200)
    panel(cv, R('chimografo.png'), (1180, 90, 640, 823), FULL, (0.5, 0.55, 0.85), t, t0=0.3, dur=11)
    panel(cv, R('distanza_muro.png'), (110, 380, 1020, 391), FULL, FULL, t, t0=0.8, dur=1)
    chip(cv, 'chimografo: tempo × distanza dal muro', 1200, 940, t, 1.4, CYAN, 26)
    T(cv, 'Tocco = la mano raggiunge il bordo del muro.', 110, 820, 40, t, 2.4, 600, WHITE, maxw=1020)
    T(cv, 'Stacco = l\'ultimo fotogramma attaccato al muro.', 110, 885, 40, t, 3.4, 600, CYAN, maxw=1020)


def s_arrivo(cv, t):
    kicker(cv, 'UN ARRIVO, TRE VISTE', t, 0.2, 110, 70)
    for i in range(3):
        panel(cv, R(f'arrivo_{i}.jpg'), (110 + i * 580, 140, 550, 309), FULL, (0.45, 0.5, 0.9), t, t0=0.3 + 0.3 * i, dur=9)
        chip(cv, ['-0,2 s', 'TOCCO', '+0,2 s'][i], 130 + i * 580, 380, t, 0.8 + 0.3 * i, RED if i == 1 else CYAN, 28, (4, 12, 30))
    panel(cv, R('distanza_muro.png'), (110, 490, 850, 326), FULL, FULL, t, t0=1.6, dur=1)
    panel(cv, R('imu_arrivo.png'), (990, 490, 830, 318), FULL, FULL, t, t0=2.2, dur=1)
    chip(cv, 'video: distanza dal muro', 130, 830, t, 2.4, CYAN, 28)
    chip(cv, 'IMU: rotazione e viso al cielo', 1010, 830, t, 2.8, AMBER, 28)
    T(cv, 'Ora il riferimento viene dal video, non dall\'occhio.', 960, 940, 44, t, 4.0, 600, WHITE, anchor='c', maxw=1700)


def s_ris_cv(cv, t):
    block(cv, t, 'RISULTATI OPENCV', [('Partenze:', WHITE), ('al fotogramma.', GREEN)], [], tsz=84, maxw=760, cy=200)
    rows = [('Partenze', '14 / 14', '± 0,14 s', GREEN), ('Arrivi', '13 / 15', '± 0,4 s', AMBER), ('Virate', '10 / 12', '± 0,45 s', AMBER),
            ('Tipo di evento', '0 errori', '', GREEN)]
    y = 380
    for i, (a, b, c, col) in enumerate(rows):
        t0 = 0.7 + 0.5 * i
        T(cv, a, 110, y, 46, t, t0, 600, WHITE, maxw=360)
        TM(cv, b, 500, y, 46, t, t0 + 0.15, col)
        TM(cv, c, 720, y, 46, t, t0 + 0.3, col)
        y += 92
    panel(cv, R('confronto_A.jpg', (0, 400, 896, 1730)), (1000, 110, 820, 870), FULL, (0.5, 0.35, 0.8), t, t0=0.4, dur=7.5)
    T(cv, 'Dal fondo il muro è una fascia:', 110, 800, 38, t, 3.2, 500, MUTED, maxw=860)
    T(cv, 'la prossima volta, camera sul muro.', 110, 852, 38, t, 3.6, 600, CYAN, maxw=860)


def s_decisione(cv, t):
    block(cv, t, 'LA DECISIONE', [('Metodo,', WHITE), ('non tentativi.', CYAN)], [], tsz=88, maxw=760, cy=200)
    items = [('Dataset con etichette verificate', CYAN), ('Banco di prova in streaming', CYAN), ('Validazione su sessioni nuove', CYAN)]
    y = 360
    for i, (s, col) in enumerate(items):
        t0 = 0.7 + 0.5 * i
        if t >= t0:
            check(cv, 110, y, 44, col)
        T(cv, s, 175, y + 2, 40, t, t0, 600, WHITE, maxw=700)
        y += 76
    kicker(cv, 'RETE NEURALE · SOLO PER L\'ARRIVO', t, 2.4, 110, 620)
    nodes = [('Regola-porta', 'bracciate finite, vicino al muro', AMBER), ('Rete 1D', 'int8 sul nRF52840', VIOLET), ('Tempo del tocco', 'datato all\'indietro', RED)]
    x = 110
    for i, (a, b, col) in enumerate(nodes):
        t0 = 3.0 + 0.8 * i
        if t >= t0:
            p = ease((t - t0) / 0.4)
            g = G(330, 170)
            g.rrect((0, 0, 330 * p, 170), 22, fill=CARD + (240,), outline=col + (255,), width=4)
            g.paste_to(cv, x, 700)
            if i < 2:
                d = ImageDraw.Draw(cv)
                d.line((x + 335, 785, x + 385, 785), fill=col, width=5)
                d.polygon([(x + 385, 772), (x + 405, 785), (x + 385, 798)], fill=col)
        T(cv, a, x + 24, 724, 40, t, t0 + 0.2, 700, col, maxw=290)
        T(cv, b, x + 24, 790, 28, t, t0 + 0.3, 400, MUTED, maxw=290)
        x += 410
    # linea del tempo: tocco -> notifica
    if t >= 6.0:
        bx, by, bw = 1000 + 360, 180, 460
        p = ease((t - 6.0) / 0.6)
        g = G(500, 440)
        g.rrect((0, 0, 500, 440 * p), 24, fill=CARD + (240,), outline=(40, 110, 190, 255), width=3)
        g.paste_to(cv, 1320, 140)
        if p >= 1:
            d = ImageDraw.Draw(cv)
            d.line((1370, 360, 1770, 360), fill=(60, 100, 170), width=6)
            u = clamp((t - 6.6) / 2.0)
            d.line((1420, 360, 1420 + int(260 * u), 360), fill=CYAN, width=6)
            d.ellipse((1406, 346, 1434, 374), fill=RED)
            T(cv, 'tocco', 1420, 390, 32, t, 6.7, 700, RED, anchor='c')
            if u >= 1:
                d.ellipse((1666, 346, 1694, 374), fill=GREEN)
                T(cv, 'notifica', 1680, 390, 32, t, 8.7, 700, GREEN, anchor='c')
            TM(cv, '≤ 1,5 s', 1550, 290, 40, t, 7.2, CYAN2, 'c')
            T(cv, 'Il tempo resta quello del tocco.', 1570, 470, 30, t, 9.2, 500, WHITE, anchor='c', maxw=440)
    T(cv, 'Prima la rete batte un metodo classico, poi va sul tag.', 110, 940, 36, t, 10.0, 500, MUTED, maxw=1700)


def s_prossimi(cv, t):
    kicker(cv, 'PROSSIMI PASSI', t, 0.2, 110, 130)
    T(cv, 'Il secondo test, già strutturato.', 110, 210, 84, t, 0.35, 700, WHITE, maxw=1700)
    items = [('Ripetute da 100 m', 'partenza e arrivo davanti alla camera', CYAN), ('Camera attaccata al muro', 'il muro diventa una linea netta', GREEN),
             ('Sync a inizio e fine', 'la deriva si misura, non si stima', AMBER), ('Frequenza più bassa', 'sedute più lunghe nella stessa memoria', VIOLET),
             ('Editor a fotogrammi veri', 'frecce per spostare ogni etichetta', CYAN)]
    y = 380
    for i, (a, b, col) in enumerate(items):
        t0 = 0.9 + 0.7 * i
        if t >= t0:
            pp = ease((t - t0) / 0.4)
            ImageDraw.Draw(cv).rectangle((110, y + 6, 116, y + 6 + int(96 * pp)), fill=col)
        T(cv, a, 140, y, 48, t, t0, 700, WHITE, maxw=820)
        T(cv, b, 140, y + 58, 32, t, t0 + 0.15, 400, MUTED, maxw=820)
        y += 120
    panel(cv, R('tocco/030.jpg'), (1000, 380, 820, 610), FULL, (0.35, 0.5, 0.7), t, t0=1.0, dur=9)


def s_close(cv, t):
    gv.waves(cv, t, 960, (30, 100, 180), 12, 3, 26)
    kicker(cv, 'PROGETTO APERTO', t, 0.3, 700, 130)
    wipe_text(cv, (('SWIM', WHITE), ('TIMER', CYAN)), 960, 220, 230, t, 0.5, 1.0, 700)
    d = ImageDraw.Draw(cv)
    lp = ease((t - 1.4) / 0.8)
    d.rectangle((960 - int(480 * lp), 500, 960 + int(480 * lp), 505), fill=CYAN)
    T(cv, 'Dati reali, metodo aperto · prossimo test in arrivo', 960, 535, 50, t, 1.8, 600, MUTED, anchor='c', maxw=1500)
    rows = [('WEB', 'swimtimer-pzero.web.app'), ('EMAIL', 'SmartSwimTimer@gmail.com'), ('GITHUB', 'PZero/SwimTimer')]
    for i, (k, v) in enumerate(rows):
        t0 = 2.6 + 0.4 * i
        y = 650 + i * 82
        T(cv, k, 900, y + 8, 34, t, t0, 600, CYAN, anchor='r', track=3)
        T(cv, v, 940, y, 54, t, t0 + 0.1, 600, WHITE)


# (inizio, durata, funzione, sfondo)
SCENES = [
    (0, 8, s_hook, None),
    (8, 10, s_prova, (R('largo.jpg'), 0.5, 0.3)),
    (18, 8, s_sync, None),
    (26, 10, s_mano, None),
    (36, 16, s_filtri, None),
    (52, 10, s_risultati, None),
    (62, 14, s_twist, None),
    (76, 12, s_cv1, None),
    (88, 12, s_cv2, None),
    (100, 10, s_arrivo, (R('arrivo_1.jpg'), 0.5, 0.25)),
    (110, 8, s_ris_cv, None),
    (118, 14, s_decisione, None),
    (132, 10, s_prossimi, None),
    (142, 8, s_close, None),
]
TRANS = ['push', 'wipe', 'dissolve', 'pushup', 'zoom', 'wipe', 'push', 'zoom', 'pushup', 'push', 'wipe', 'dissolve', 'pushup']
CHAP = dict(zip([s[2].__name__ for s in SCENES], [None, '01', '01', '01', '02', '02', '03', '04', '04', '04', '04', '05', '06', None]))


def scene_frame(k, ts):
    st, du, fn, bgs = SCENES[k]
    bg = gv.make_bg(*bgs).copy() if bgs else gv.make_bg().copy()
    gv.bubbles(bg, ts + st)
    fn(bg, ts)
    c = CHAP[fn.__name__]
    if c:
        lay, pad, dy, tw = tlayer(((c, CYAN), (' / 06', (70, 110, 170))), 30, 600)
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
    if 76 <= t < 76.3:                                   # lampo sul drop
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.5 * (1 - (t - 76) / 0.3))
    if 148.0 <= t < 148.2:                               # stacco finale
        img = Image.blend(img, Image.new('RGB', (W, H), (190, 235, 255)), 0.3 * (1 - (t - 148) / 0.2))
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 6, int(W * t / DUR), H), fill=CYAN)
    if t > 148.6:
        img = Image.blend(img, Image.new('RGB', (W, H), (0, 0, 0)), clamp((t - 148.6) / 1.3))
    return img


def frame_bytes(i):
    return frame_image(i).tobytes()


def miniatura(path):
    bg = gv.make_bg(R('arrivo_1.jpg'), 0.5, 0.35).copy()
    panel(bg, R('tocco/030.jpg'), (900, 90, 920, 518), FULL, FULL, 9, t0=0, dur=1)
    panel(bg, R('imu_arrivo.png'), (900, 640, 920, 352), FULL, FULL, 9, t0=0, dur=1)
    T(bg, 'SWIM', 100, 110, 200, 9, 0, 700, WHITE)
    T(bg, 'TIMER', 100, 280, 200, 9, 0, 700, CYAN)
    ImageDraw.Draw(bg).rectangle((110, 540, 640, 546), fill=CYAN)
    T(bg, 'Primo test in vasca', 110, 580, 80, 9, 0, 700, WHITE, maxw=760)
    T(bg, 'IMU, OpenCV e rete neurale', 110, 690, 52, 9, 0, 600, CYAN, maxw=760)
    T(bg, '± 0,02 s?', 110, 790, 110, 9, 0, 700, RED, maxw=760)
    bg.resize((1280, 720), Image.LANCZOS).save(path)


def main():
    global IMG3
    ap = argparse.ArgumentParser()
    ap.add_argument('--img', required=True, help='cartella delle immagini reali (prepara_img_v3.py), fuori dal repository')
    ap.add_argument('--anteprima', nargs='*', type=float)
    ap.add_argument('--dir', default=str(HERE))
    ap.add_argument('--solo-miniatura', action='store_true')
    ap.add_argument('--no-musica', action='store_true')
    ap.add_argument('--lingua', choices=['it', 'en'], default='it')
    a = ap.parse_args()
    if a.lingua != LANG or os.environ.get('SWIMTIMER_IMG3') != a.img:
        env = dict(os.environ, SWIMTIMER_LANG=a.lingua, SWIMTIMER_IMG3=a.img)
        sys.exit(subprocess.call([sys.executable, __file__] + sys.argv[1:], env=env))
    if a.anteprima:
        Path(a.dir).mkdir(parents=True, exist_ok=True)
        for tsec in a.anteprima:
            frame_image(int(round(tsec * FPS))).save(Path(a.dir) / f'v3_{LANG}_{tsec:06.2f}.png')
        return
    if a.solo_miniatura:
        miniatura(HERE / f'miniatura_test1_{LANG}.png')
        return
    wav = HERE / 'musica_v3.wav'
    if not a.no_musica or not wav.exists():
        import musica_v3
        y, lufs, peak = musica_v3.compose(wav)
        print(f'Musica: {lufs} LUFS, picco {peak} dBFS')
    miniatura(HERE / f'miniatura_test1_{LANG}.png')
    out = HERE / f'SwimTimer_test1_{LANG}.mp4'
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
