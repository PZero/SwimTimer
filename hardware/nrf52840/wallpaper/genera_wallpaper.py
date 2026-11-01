"""Wallpaper tecnici per il telefono dal PCB reale del tag (1170 x 2532 px).

Uso: python genera_wallpaper.py
Legge kicad/swimtag_collaudo.kicad_pcb, esporta gli strati in SVG con kicad-cli,
li rasterizza con PyMuPDF e compone le tavole con Pillow. Scrive i PNG in png/.
I render 3D (render/*.png) si fanno a parte con `kicad-cli pcb render`.
"""
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

QUI = Path(__file__).resolve().parent
PCB = QUI.parent / "kicad" / "swimtag_collaudo.kicad_pcb"
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
CLI = KICAD / "bin" / "kicad-cli.exe"
KIPY = KICAD / "bin" / "python.exe"
OUT = QUI / "png"

W, H = 1170, 2532          # schermo del telefono
SS = 2                     # sovracampionamento per linee morbide
FONT = "C:/Windows/Fonts/bahnschrift.ttf"

# palette: grafite, champagne, avorio
FONDO_A, FONDO_B = (12, 16, 21), (6, 8, 11)
GRIGLIA, GRIGLIA_F = (22, 30, 39), (30, 41, 53)
ORO = (201, 170, 108)
AVORIO = (233, 228, 216)
TENUE = (122, 132, 145)
ACQUA = (96, 158, 160)
ACCIAIO = (112, 131, 168)
RAME = (176, 122, 110)

TITOLO = "SWIMTIMER"
SOTTOTITOLO = "TAG v0.3  ·  nRF52840  ·  26 × 30 mm"


def font(px, peso="Light"):
    f = ImageFont.truetype(FONT, int(px * SS))
    f.set_variation_by_name(peso)
    return f


# ---------- dati dalla scheda ----------

def prepara(tmp):
    info = Path(tmp) / "info.json"
    senza = Path(tmp) / "senza_zone.kicad_pcb"
    subprocess.run([str(KIPY), str(QUI / "info_pcb.py"), str(PCB), str(info), str(senza)], check=True)
    strati = "F.Cu,In1.Cu,In2.Cu,B.Cu,Edge.Cuts,F.SilkS,B.SilkS,F.Fab,F.Mask,B.Mask"
    for nome, scheda in (("svg", PCB), ("piste", senza)):
        subprocess.run([str(CLI), "pcb", "export", "svg", "--mode-multi", "--black-and-white", "--page-size-mode", "2",
                        "--exclude-drawing-sheet", "-l", strati, "-o", str(Path(tmp) / nome), str(scheda)],
                       check=True, capture_output=True)
    return Path(tmp) / "svg", Path(tmp) / "piste", json.load(open(info))


def maschera(svg, nome, pxmm, specchio=False):
    """Strato come maschera L (255 = rame) a pxmm pixel per millimetro."""
    doc = pymupdf.open(next(svg.glob(f"*-{nome}.svg")))
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(pxmm / 2.83465, pxmm / 2.83465), colorspace=pymupdf.csGRAY)
    m = ImageChops.invert(Image.frombytes("L", (pix.width, pix.height), pix.samples))
    return m.transpose(Image.FLIP_LEFT_RIGHT) if specchio else m


def colora(m, colore, alfa=1.0):
    img = Image.new("RGBA", m.size, colore + (255,))
    img.putalpha(m.point(lambda v: int(v * alfa)))
    return img


# ---------- elementi grafici ----------

def tela():
    t = Image.new("RGB", (W * SS, H * SS))
    d = ImageDraw.Draw(t)
    for y in range(0, H * SS, 4):
        k = y / (H * SS)
        c = tuple(int(a + (b - a) * k) for a, b in zip(FONDO_A, FONDO_B))
        d.rectangle([0, y, W * SS, y + 4], fill=c)
    return t.convert("RGBA")


def griglia(t, passo, ox=0, oy=0, forte=5):
    d = ImageDraw.Draw(t)
    i = 0
    x = ox % passo
    while x < t.width:
        n = round((x - ox) / passo)
        d.line([x, 0, x, t.height], fill=GRIGLIA_F if n % forte == 0 else GRIGLIA, width=SS)
        x += passo
    y = oy % passo
    while y < t.height:
        n = round((y - oy) / passo)
        d.line([0, y, t.width, y], fill=GRIGLIA_F if n % forte == 0 else GRIGLIA, width=SS)
        y += passo


def vignetta(t):
    v = Image.new("L", t.size, 0)
    d = ImageDraw.Draw(v)
    d.ellipse([-t.width * 0.35, -t.height * 0.12, t.width * 1.35, t.height * 1.12], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(t.width * 0.18))
    nero = Image.new("RGBA", t.size, FONDO_B + (255,))
    return Image.composite(t, nero, v)


def testo(d, xy, s, px, colore=AVORIO, peso="Light", spazio=0.0, ancora="la"):
    f = font(px, peso)
    if not spazio:
        d.text((xy[0] * SS, xy[1] * SS), s, font=f, fill=colore, anchor=ancora)
        return
    # spaziatura tra lettere (maiuscole tecniche)
    larg = sum(f.getlength(c) for c in s) + spazio * SS * px * (len(s) - 1)
    x = xy[0] * SS - (larg if ancora[0] == "r" else larg / 2 if ancora[0] == "m" else 0)
    for c in s:
        d.text((x, xy[1] * SS), c, font=f, fill=colore, anchor="l" + ancora[1])
        x += f.getlength(c) + spazio * SS * px


def linea(d, a, b, colore=TENUE, w=1.0):
    d.line([a[0] * SS, a[1] * SS, b[0] * SS, b[1] * SS], fill=colore, width=max(1, int(w * SS)))


def crocino(d, x, y, r=10, colore=TENUE):
    linea(d, (x - r, y), (x + r, y), colore)
    linea(d, (x, y - r), (x, y + r), colore)


def quota(d, a, b, etichetta, scosta, colore=AVORIO):
    """Quota con linee di richiamo e frecce sottili; a, b in px finali."""
    (x1, y1), (x2, y2) = a, b
    ang = math.atan2(y2 - y1, x2 - x1)
    nx, ny = -math.sin(ang) * scosta, math.cos(ang) * scosta
    p1, p2 = (x1 + nx, y1 + ny), (x2 + nx, y2 + ny)
    k = 1 if scosta > 0 else -1
    linea(d, (x1 + nx * 0.15, y1 + ny * 0.15), (p1[0] + k * -math.sin(ang) * 8, p1[1] + k * math.cos(ang) * 8), TENUE, 0.8)
    linea(d, (x2 + nx * 0.15, y2 + ny * 0.15), (p2[0] + k * -math.sin(ang) * 8, p2[1] + k * math.cos(ang) * 8), TENUE, 0.8)
    linea(d, p1, p2, colore, 1)
    for p, s in ((p1, 1), (p2, -1)):
        for da in (0.35, -0.35):
            q = (p[0] + s * 14 * math.cos(ang + da), p[1] + s * 14 * math.sin(ang + da))
            linea(d, p, q, colore, 1)
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    off = 22 if scosta > 0 else -22
    testo(d, (mx - math.sin(ang) * off, my + math.cos(ang) * off), etichetta, 24, colore, "SemiLight", ancora="mm")


def cartiglio(t, numero, titolo_tavola, nota=""):
    sfuma = Image.new("L", (1, H * SS), 0)
    for y in range(H * SS):
        k = (y / SS - (H - 560)) / 260
        sfuma.putpixel((0, y), int(240 * min(1, max(0, k))))
    nero = Image.new("RGBA", t.size, FONDO_B + (255,))
    t.paste(Image.composite(nero, t, sfuma.resize(t.size)), (0, 0))
    d = ImageDraw.Draw(t)
    y = H - 250
    linea(d, (90, y), (W - 90, y), TENUE, 0.8)
    testo(d, (90, y + 48), TITOLO, 34, AVORIO, "SemiBold", 0.42)
    testo(d, (90, y + 98), SOTTOTITOLO, 24, TENUE, "Light", 0.04)
    testo(d, (W - 90, y + 48), f"{numero:02d} / 08", 26, ORO, "SemiLight", 0.2, "rm")
    testo(d, (W - 90, y + 98), titolo_tavola.upper(), 22, AVORIO, "Light", 0.3, "rm")
    if nota:
        testo(d, (90, y + 146), nota, 20, TENUE, "Light", 0.02)
    # segni di registro agli angoli
    for (x, yy) in ((60, 60), (W - 60, 60), (60, H - 60), (W - 60, H - 60)):
        crocino(d, x, yy, 12, GRIGLIA_F)


def fine(t, nome):
    OUT.mkdir(exist_ok=True)
    t.convert("RGB").resize((W, H), Image.LANCZOS).save(OUT / f"{nome}.png", optimize=True)
    print("scritto", nome)


def incolla(t, img, x, y):
    """Incolla un'immagine RGBA (gia in px sovracampionati) con angolo in (x, y) px finali."""
    t.alpha_composite(img, (int(x * SS), int(y * SS)))


# ---------- tavole ----------

def mm_it(v):
    return f"{v:.1f}".replace(".", ",")


def etichetta(d, punto, lato, ty, righe, colore=AVORIO):
    """Richiamo: pallino sul componente, linea verticale e orizzontale, testo nella colonna di sinistra o destra."""
    x, y = punto
    r = 5
    d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], outline=colore, width=SS)
    f = font(25, "SemiBold")
    larg = max(sum(f.getlength(c) for c in righe[0]) / SS * 1.12, font(21).getlength(max(righe[1:], key=len)) / SS)
    if lato == "s":
        tx, ancora, fine_linea = 90, "la", 90 + larg + 16
    else:
        tx, ancora, fine_linea = W - 90, "ra", W - 90 - larg - 16
    linea(d, (x, y + (r if ty > y else -r)), (x, ty), TENUE, 0.8)
    linea(d, (x, ty), (fine_linea, ty), TENUE, 0.8)
    testo(d, (tx, ty - 30), righe[0], 25, colore, "SemiBold", 0.12, ancora)
    for i, r2 in enumerate(righe[1:]):
        testo(d, (tx, ty + 8 + i * 28), r2, 21, TENUE, "Light", ancora=ancora)


def centro(info, ref, bx, by, pxmm, specchio=False):
    p = info["fps"][ref]
    x = p["x0"] + p["w"] / 2
    if specchio:
        x = info["w"] - x
    return bx + x * pxmm, by + (p["y0"] + p["h"] / 2) * pxmm


def tavola_pianta(svg, piste, info):
    """01 · pianta del rame superiore con quote e richiami."""
    pxmm = 25.0
    bw, bh = info["w"] * pxmm, info["h"] * pxmm
    bx, by = (W - bw) / 2, 930
    t = tela()
    griglia(t, pxmm * SS, bx * SS, by * SS)
    t = vignetta(t)
    incolla(t, colora(maschera(svg, "In1_Cu", pxmm * SS), ACQUA, 0.10), bx, by)
    incolla(t, colora(maschera(piste, "F_Fab", pxmm * SS), TENUE, 0.45), bx, by)
    incolla(t, colora(maschera(piste, "F_Cu", pxmm * SS), ORO, 0.95), bx, by)
    incolla(t, colora(maschera(piste, "Edge_Cuts", pxmm * SS), AVORIO), bx, by)
    d = ImageDraw.Draw(t)
    quota(d, (bx, by), (bx + bw, by), mm_it(info["w"] - 0.1), -60)
    quota(d, (bx, by), (bx, by + bh), mm_it(info["h"] - 0.1), 60)
    etichetta(d, centro(info, "U1", bx, by, pxmm), "s", 760, ["E73 · nRF52840", "Bluetooth LE · 13 × 18 mm"])
    etichetta(d, (bx + bw * 0.78, by + 1.8 * pxmm), "d", 760, ["ANTENNA", "3,7 mm senza rame"])
    etichetta(d, centro(info, "J1", bx, by, pxmm), "s", by + bh + 110, ["BATTERIA", "JST SH · LiPo 40 mAh"])
    etichetta(d, centro(info, "U3", bx, by, pxmm), "s", by + bh + 220, ["FLASH 32 MB", "W25Q256 · QSPI"])
    etichetta(d, centro(info, "U5", bx, by, pxmm), "d", by + bh + 110, ["MS5837", "profondità · 2 bar"])
    etichetta(d, centro(info, "U2", bx, by, pxmm), "d", by + bh + 220, ["LSM6DSV16X", "IMU 6 assi · ±4 g"])
    cartiglio(t, 1, "Pianta · rame superiore", f"{info['piste']} piste · {len(info['vias'])} via · 4 strati · 0,8 mm")
    fine(t, "01_pianta")


def tavola_strati(svg, piste, info):
    """02 · vista esplosa dei quattro strati di rame."""
    pxmm = 15.5
    t = tela()
    griglia(t, 36 * SS)
    t = vignetta(t)
    strati = [("B_Cu", RAME, "B.Cu", "contatti · SWD"), ("In2_Cu", ACCIAIO, "In2.Cu", "segnali"),
              ("In1_Cu", ACQUA, "In1.Cu", "massa"), ("F_Cu", ORO, "F.Cu", "componenti")]
    passo, y0 = 250, 1620
    d = ImageDraw.Draw(t)
    angoli = []
    for i, (nome, col, etich, nota) in enumerate(strati):
        m = maschera(piste, nome, pxmm * SS)
        z = maschera(svg, nome, pxmm * SS).point(lambda v: v // 5)
        b = maschera(piste, "Edge_Cuts", pxmm * SS)
        m = ImageChops.lighter(ImageChops.lighter(m, z), b)
        m = m.rotate(45, expand=True, resample=Image.BICUBIC)
        m = m.resize((m.width, int(m.height * 0.5)), Image.LANCZOS)
        x = (W * SS - m.width) / 2 / SS - 60
        y = y0 - i * passo - m.height / SS / 2
        incolla(t, colora(m, col, 0.95), x, y)
        cy = y + m.height / SS / 2
        xr = x + m.width / SS
        angoli.append((x, xr, cy))
        linea(d, (xr + 10, cy), (W - 230, cy), TENUE, 0.8)
        testo(d, (W - 90, cy - 16), etich, 26, col, "SemiBold", 0.1, "rm")
        testo(d, (W - 90, cy + 18), nota, 20, TENUE, "Light", ancora="rm")
    for xa, xb, _ in angoli[:1]:
        for xx in (xa, xb):
            linea(d, (xx, angoli[0][2]), (xx, angoli[-1][2]), GRIGLIA_F, 1)
    cartiglio(t, 2, "Stack · vista esplosa", "4 strati · FR-4 0,8 mm · finitura ENIG")
    fine(t, "02_strati")


def tavola_macro(svg, piste, info):
    """03 · ingrandimento del modulo e della zona antenna."""
    pxmm = 95.0
    f = info["fps"]["U1"]
    cx, cy = f["x0"] + f["w"] * 0.62, f["y0"] + f["h"] * 0.42
    ox = W / 2 - cx * pxmm
    oy = (H - 600) / 2 - cy * pxmm + 120
    t = tela()
    griglia(t, pxmm * SS, ox * SS, oy * SS, forte=5)
    incolla(t, colora(maschera(svg, "In1_Cu", pxmm * SS), ACQUA, 0.08), ox, oy)
    incolla(t, colora(maschera(piste, "F_Cu", pxmm * SS), ORO, 0.9), ox, oy)
    incolla(t, colora(maschera(piste, "F_Fab", pxmm * SS), AVORIO, 0.5), ox, oy)
    incolla(t, colora(maschera(piste, "Edge_Cuts", pxmm * SS), AVORIO), ox, oy)
    t = vignetta(t)
    d = ImageDraw.Draw(t)
    ya = oy + 3.7 * pxmm
    if 0 < ya < H:
        for x in range(0, W, 26):
            linea(d, (x, ya), (x + 13, ya), ACQUA, 1.2)
        testo(d, (90, ya - 34), "ZONA ANTENNA · NESSUN RAME · 3,7 mm", 22, ACQUA, "SemiLight", 0.18)
    sx, sy = W - 90 - pxmm - 90, ya - 120
    linea(d, (sx, sy), (sx + pxmm, sy), AVORIO, 2)
    linea(d, (sx, sy - 8), (sx, sy + 8), AVORIO, 1.5)
    linea(d, (sx + pxmm, sy - 8), (sx + pxmm, sy + 8), AVORIO, 1.5)
    testo(d, (sx + pxmm + 18, sy), "1 mm", 22, AVORIO, "SemiLight", ancora="lm")
    cartiglio(t, 3, "Dettaglio · modulo E73", "piazzole a mezzo foro e LGA · passo 1,27 mm")
    fine(t, "03_macro_modulo")


def tavola_sotto(svg, piste, info):
    """04 · lato sotto, con lente sul Tag-Connect."""
    pxmm = 25.0
    bw, bh = info["w"] * pxmm, info["h"] * pxmm
    bx, by = (W - bw) / 2, 1060
    t = tela()
    griglia(t, pxmm * SS, bx * SS, by * SS)
    t = vignetta(t)
    livelli = (("piste", "B_Cu", RAME, 0.75), ("piste", "B_Mask", ORO, 0.95), ("piste", "B_Silkscreen", AVORIO, 0.85))
    sorg = {"piste": piste, "svg": svg}
    for s, nome, col, a in livelli:
        incolla(t, colora(maschera(sorg[s], nome, pxmm * SS, specchio=True), col, a), bx, by)
    incolla(t, colora(maschera(piste, "Edge_Cuts", pxmm * SS, specchio=True), AVORIO), bx, by)
    j = info["fps"]["J4"]
    jx, jy = info["w"] - (j["x0"] + j["w"] / 2), j["y0"] + j["h"] / 2
    px_, py_ = bx + jx * pxmm, by + jy * pxmm
    zoom, R = 105.0, 215
    lx, ly = W / 2 - 120, 640
    lente = Image.new("RGBA", (2 * R * SS, 2 * R * SS), FONDO_A + (255,))
    for s, nome, col, a in livelli:
        m = maschera(sorg[s], nome, zoom * SS, specchio=True)
        cx, cy = jx * zoom * SS, jy * zoom * SS
        lente.alpha_composite(colora(m.crop((int(cx - R * SS), int(cy - R * SS), int(cx + R * SS), int(cy + R * SS))), col, a))
    cerchio = Image.new("L", lente.size, 0)
    ImageDraw.Draw(cerchio).ellipse([0, 0, lente.width - 1, lente.height - 1], fill=255)
    lente.putalpha(cerchio)
    incolla(t, lente, lx - R, ly - R)
    d = ImageDraw.Draw(t)
    d.ellipse([(lx - R) * SS, (ly - R) * SS, (lx + R) * SS, (ly + R) * SS], outline=AVORIO + (255,), width=SS)
    r0 = pxmm * R / zoom
    d.ellipse([(px_ - r0) * SS, (py_ - r0) * SS, (px_ + r0) * SS, (py_ + r0) * SS], outline=AVORIO + (255,), width=SS)
    a = math.atan2(py_ - ly, px_ - lx)
    linea(d, (lx + R * math.cos(a), ly + R * math.sin(a)), (px_ - r0 * math.cos(a), py_ - r0 * math.sin(a)), TENUE, 0.8)
    testo(d, (lx + R + 30, ly - 20), "TC2030-NL", 25, AVORIO, "SemiBold", 0.12, "lm")
    testo(d, (lx + R + 30, ly + 14), "SWD · 6 pad · senza piedini", 20, TENUE, ancora="lm")
    testo(d, (lx + R + 30, ly + 44), f"× {zoom / pxmm:.1f}".replace(".", ","), 20, ORO, "SemiLight", ancora="lm")
    cartiglio(t, 4, "Lato sotto", "contatti di ricarica Ø 2,5 mm · passo 4,2 mm · piazzole di prova")
    fine(t, "04_lato_sotto")


def tavola_sezione(info):
    """05 · sezione trasversale del tag finito (scala verticale esagerata)."""
    t = tela()
    griglia(t, 36 * SS)
    t = vignetta(t)
    d = ImageDraw.Draw(t)
    kx, ky = 20.0, 60.0                        # px per mm in orizzontale e in verticale
    resina = 1.5
    larg = info["w"] - 0.1
    x0 = 150 + resina * kx
    ybase = 1560
    pezzi = [  # nome, x da, x a, spessore, colore
        ("PCB 4 strati", 0, larg, 0.8, ORO),
        ("modulo E73", larg / 2 - 6.5, larg / 2 + 6.5, 3.0, ACCIAIO),
        ("cella LiPo 401012", larg / 2 - 5, larg / 2 + 5, 4.0, RAME)]
    y = ybase - 0.6 * ky
    quote = [("resina", 0.6, ybase - 0.6 * ky, ybase, TENUE)]
    for nome, xa, xb, s, col in pezzi:
        h = s * ky
        ax, bx_ = x0 + xa * kx, x0 + xb * kx
        d.rectangle([ax * SS, (y - h) * SS, bx_ * SS, y * SS], outline=col + (255,), width=int(1.5 * SS))
        for xx in range(int(ax - h), int(bx_), 16):
            p1x = max(xx, ax)
            p2x = min(xx + h, bx_)
            if p2x > p1x:
                linea(d, (p1x, y - (p1x - xx)), (p2x, y - (p2x - xx)), col + (70,), 0.6)
        if nome.startswith("PCB"):
            for i in range(1, 4):
                linea(d, (ax, y - h * i / 4), (bx_, y - h * i / 4), ORO + (150,), 0.6)
        quote.append((nome, s, y - h, y, col))
        y -= h
    ytop = y - 0.8 * ky
    quote.append(("resina", 0.8, ytop, y, TENUE))
    d.rounded_rectangle([150 * SS, ytop * SS, (x0 + larg * kx + resina * kx) * SS, ybase * SS],
                        radius=int(1.0 * kx * SS), outline=AVORIO + (255,), width=SS)
    xq = x0 + larg * kx + resina * kx + 90
    for nome, s, ya, yb, col in quote:
        linea(d, (xq, ya), (xq, yb), col, 1)
        for yy in (ya, yb):
            linea(d, (xq - 8, yy), (xq + 8, yy), col, 1)
    # etichette distanziate per non sovrapporsi
    yl = [(ya + yb) / 2 for _, _, ya, yb, _ in quote]
    for i in range(1, len(yl)):
        if yl[i - 1] - yl[i] < 70:
            yl[i] = yl[i - 1] - 70
    for (nome, s, ya, yb, col), yy in zip(quote, yl):
        testo(d, (xq + 30, yy - 12), mm_it(s), 24, col if col != TENUE else AVORIO, "SemiBold", ancora="lm")
        testo(d, (xq + 30, yy + 15), nome, 19, TENUE, ancora="lm")
    tot = sum(q[1] for q in quote)
    quota(d, (150, ybase), (150, ytop), mm_it(tot) + " mm", 60, ORO)
    quota(d, (150, ybase), (x0 + larg * kx + resina * kx, ybase), mm_it(larg + 2 * resina) + " mm", 70, AVORIO)
    testo(d, (W / 2, ybase + 190), "SEZIONE A–A  ·  scala verticale × 3", 21, TENUE, "Light", 0.22, "mm")
    cartiglio(t, 5, "Sezione · spessori", "tag finito stimato · cella sopra il modulo · resina 1,5 mm sui lati")
    fine(t, "05_sezione")


def tavola_render(nome_render, numero, titolo, nota, larghezza=0.9, sfuma_bordi=False):
    """06-07 · render 3D di KiCad su fondo grafite."""
    src = QUI / "render" / f"{nome_render}.png"
    if not src.exists():
        print("manca", src)
        return
    t = tela()
    griglia(t, 36 * SS)
    t = vignetta(t)
    r = Image.open(src).convert("RGBA")
    if sfuma_bordi:
        # il render tocca i bordi del riquadro: sfuma i tagli netti
        m = Image.new("L", r.size, 0)
        ImageDraw.Draw(m).rectangle([r.width * 0.1, r.height * 0.1, r.width * 0.9, r.height * 0.9], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(r.width * 0.06))
        r.putalpha(ImageChops.multiply(r.getchannel("A"), m))
    r = r.crop(r.getbbox())
    scala = (W * SS * larghezza) / r.width
    r = r.resize((int(r.width * scala), int(r.height * scala)), Image.LANCZOS)
    ombra = Image.new("RGBA", r.size, (0, 0, 0, 0))
    ombra.putalpha(r.getchannel("A").point(lambda v: int(v * 0.6)))
    ombra = ombra.filter(ImageFilter.GaussianBlur(40 * SS))
    x = (W * SS - r.width) // 2
    y = int(H * SS * 0.5 - r.height / 2)
    t.alpha_composite(ombra, (x + 30 * SS, y + 60 * SS))
    t.alpha_composite(r, (x, y))
    cartiglio(t, numero, titolo, nota)
    fine(t, f"{numero:02d}_{nome_render}")


def tavola_fori(info):
    """08 · mappa di via e fori."""
    pxmm = 30.0
    bw, bh = info["w"] * pxmm, info["h"] * pxmm
    bx, by = (W - bw) / 2, 900
    t = tela()
    t = vignetta(t)
    d = ImageDraw.Draw(t)
    d.rectangle([bx * SS, by * SS, (bx + bw) * SS, (by + bh) * SS], outline=AVORIO + (255,), width=SS)
    for x in range(int(bx), int(bx + bw), 22):
        linea(d, (x, by + 3.7 * pxmm), (min(x + 11, bx + bw), by + 3.7 * pxmm), ACQUA, 0.8)
    for x, y, dr in info["vias"]:
        r = max(dr * pxmm / 2, 3)
        cx, cy = bx + x * pxmm, by + y * pxmm
        d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], outline=ORO + (255,), width=SS)
    for x, y, dr, tipo in info["fori"]:
        r = dr * pxmm / 2
        cx, cy = bx + x * pxmm, by + y * pxmm
        col = AVORIO if tipo == "NPTH" else ACQUA
        d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], outline=col + (255,), width=int(1.5 * SS))
        if tipo == "NPTH":
            crocino(d, cx, cy, r + 10, AVORIO + (200,))
    quota(d, (bx, by), (bx + bw, by), mm_it(info["w"] - 0.1), -60)
    yt = by + bh + 110
    testo(d, (bx, yt), "TABELLA FORI", 22, AVORIO, "SemiBold", 0.3)
    righe = {}
    for *_, dr in info["vias"]:
        righe[("via", dr)] = righe.get(("via", dr), 0) + 1
    for *_, dr, tipo in info["fori"]:
        nome = "centraggio Tag-Connect" if tipo == "NPTH" else "via termico flash"
        righe[(nome, dr)] = righe.get((nome, dr), 0) + 1
    for i, ((nome, dr), n) in enumerate(sorted(righe.items(), key=lambda v: -v[1])):
        yy = yt + 56 + i * 38
        col = ORO if nome == "via" else (AVORIO if nome.startswith("centr") else ACQUA)
        testo(d, (bx, yy), f"Ø {dr:.2f}".replace(".", ","), 22, col, "SemiLight")
        testo(d, (bx + 150, yy), nome, 22, TENUE)
        testo(d, (bx + bw, yy), f"× {n}", 22, AVORIO, "SemiLight", ancora="ra")
    cartiglio(t, 8, "Foratura", f"{len(info['vias'])} via passanti · fori di centraggio Tag-Connect")
    fine(t, "08_foratura")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        svg, piste, info = prepara(tmp)
        tavola_pianta(svg, piste, info)
        tavola_strati(svg, piste, info)
        tavola_macro(svg, piste, info)
        tavola_sotto(svg, piste, info)
        tavola_sezione(info)
        tavola_render("iso_sopra", 6, "Render · lato sopra", "modello 3D KiCad · componenti montati da JLC")
        tavola_render("iso_sotto", 7, "Render · lato sotto", "contatti di ricarica dorati · Tag-Connect · piazzole di prova")
        tavola_fori(info)
        json.dump(info, open(OUT / "info.json", "w"), indent=1)


if __name__ == "__main__":
    main()
