"""Sfondi tecnici per il telefono: tag v0.5 (nRF52840 + E73) e programmatore a pogo pin.

Tavole da disegno: blueprint blu, bianco su nero (OLED), nero su carta tecnica, rame su verde scuro.
Griglia 2,54 mm, quote con frecce, sezioni, esplosi con linee d'asse, ingrandimenti di dettaglio,
nomi delle reti sulle piazzole, piedinatura, schema a blocchi, mappa fori e cartiglio (foglio n/20).

Uso:
    python hardware/wallpaper_v0.5/genera.py                  # tutti i 20 sfondi
    python hardware/wallpaper_v0.5/genera.py --solo 1 3 12    # solo alcuni
    python hardware/wallpaper_v0.5/genera.py --bozza          # le 3 bozze
    python hardware/wallpaper_v0.5/genera.py --tag X.kicad_pcb --prog Y.kicad_pcb
    (oppure variabili d'ambiente SWIMTAG_PCB e SWIMTAG_PROG_PCB)
    --forza    rifa' anche i render 3D (altrimenti riusa render/ se la scheda non e' cambiata)

Tutto viene dai PCB reali: strati e contorno con `kicad-cli pcb export svg` (rasterizzati con PyMuPDF),
posizioni, reti e fori con il Python di KiCad (estrai_dati.py), viste 3D con `kicad-cli pcb render`.
Esce in png/NN_nome_1170x2532.png e png/NN_nome_1080x2400.png, piu' anteprima.png.
Niente loghi di terzi e niente dati personali.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

QUI = Path(__file__).resolve().parent
REPO = QUI.parent.parent
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
CLI = KICAD / "bin" / "kicad-cli.exe"
KIPY = KICAD / "bin" / "python.exe"
RENDER = QUI / "render"
OUT = QUI / "png"
FORMATI = [(1170, 2532, "1170x2532"), (1080, 2400, "1080x2400")]
SS = 2
FONT = "C:/Windows/Fonts/bahnschrift.ttf"
VIETATI = "→≈↔▲▼"            # glifi che Bahnschrift non ha
N_FOGLI = 20

PAL = {
    "blu": dict(bg1=(11, 61, 140), bg2=(5, 28, 76), line=(224, 237, 255), faint=(118, 164, 236), grid=(150, 192, 255),
                acc=(255, 214, 120), acc2=(122, 226, 255), txt=(236, 244, 255), tipo="blu"),
    "oled": dict(bg1=(0, 0, 0), bg2=(0, 0, 0), line=(238, 242, 246), faint=(98, 110, 122), grid=(70, 78, 88),
                 acc=(64, 206, 222), acc2=(255, 150, 104), txt=(238, 242, 246), tipo="oled"),
    "carta": dict(bg1=(242, 240, 230), bg2=(226, 224, 212), line=(22, 28, 40), faint=(118, 126, 138), grid=(160, 164, 166),
                  acc=(196, 48, 38), acc2=(18, 88, 160), txt=(22, 28, 40), tipo="carta"),
    "verde": dict(bg1=(10, 48, 40), bg2=(4, 24, 22), line=(234, 184, 122), faint=(76, 138, 110), grid=(64, 116, 96),
                  acc=(255, 232, 172), acc2=(150, 232, 200), txt=(238, 234, 216), tipo="verde"),
}

# ---------------------------------------------------------------- elenco dei 20 fogli
SOGGETTI = [
    (1, "tag_pianta", "blu", "Pianta del tag: strato superiore e inferiore, quote d'ingombro e sigle dei componenti"),
    (2, "tag_esploso", "blu", "Esploso isometrico: cella, rame inferiore, scheda, rame superiore + serigrafia, modulo E73, con linee d'asse"),
    (3, "tag_sezione", "blu", "Sezione A-A: spessore PCB, modulo, componenti, cella e resina tratteggiata, con quote"),
    (4, "tag_dettagli", "blu", "Pianta con 4 ingrandimenti tondi: antenna E73, LGA IMU, sfere BQ25101, SOIC flash (nomi delle reti)"),
    (5, "e73_antenna", "blu", "Ingrandimento del modulo E73: antenna, zona libera dal rame, passo 1,27 mm, quote"),
    (6, "e73_piedinatura", "blu", "Piedinatura del modulo E73: numero del pad e nome della rete"),
    (7, "rame_superiore", "verde", "Rame superiore F.Cu (rame su verde scuro) con griglia 2,54 mm e piazzole della batteria"),
    (8, "rame_inferiore", "oled", "Rame inferiore B.Cu in bianco su nero, vista da sotto, con le 7 piazzole di servizio nominate"),
    (9, "maschera_serigrafia", "carta", "Apertura maschera e serigrafia, nero su carta tecnica"),
    (10, "quattro_strati", "verde", "I quattro strati affiancati: F.Cu, B.Cu, maschera, serigrafia"),
    (11, "mappa_fori", "carta", "Mappa fori: via e fori con diametri e tabella di foratura"),
    (12, "zona_carica", "blu", "Ingrandimento rettangolare della zona carica: BQ25101, connettore della cella e diodo, con nomi delle reti"),
    (13, "quote_posizione", "oled", "Quote di posizionamento dei componenti principali rispetto all'angolo della scheda"),
    (14, "piazzole_servizio", "blu", "Le 7 piazzole sotto il tag (SWD e carica) con nomi, passi e quote, vista da sotto"),
    (15, "tre_viste", "blu", "Tre viste ortogonali (alto, fronte, lato) a linee, ricavate dal render 3D"),
    (16, "isometrica_distinta", "blu", "Isometrica a linee del tag con la distinta dei componenti"),
    (17, "programmatore_pianta", "blu", "Programmatore: pianta con quote, foratura e nomi delle reti sulle piazzole"),
    (18, "programmatore_pogo", "verde", "Programmatore: ingrandimento della zona dei 7 pogo pin con nomi e passo"),
    (19, "programmatore_hat", "blu", "Programmatore innestato sul Raspberry Pi (HAT): esploso a linee con asse e header 2x40, senza loghi"),
    (20, "programmatore_toner", "carta", "Foglio per il toner transfer: rame del programmatore in nero, segni di taglio, scala e fori"),
]
BOZZA = [4, 12, 20]


# ---------------------------------------------------------------- font e testo
def font(px, peso="Light"):
    try:
        f = ImageFont.truetype(FONT, int(px))
        f.set_variation_by_name(peso)
        return f
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", int(px))


def virgola(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def nome_rete(p):
    """Nome leggibile della rete di una piazzola (per i non collegati: nome del pin)."""
    n = p.get("net", "") or ""
    if n.startswith("unconnected-("):
        m = re.search(r"\(\w+-(.+?)-Pad", n)
        return (m.group(1) if m else "NC").replace("{slash}", "/")
    n = n.lstrip("/")
    m = re.match(r"Net-\((.+?)\)$", n)
    if m:
        n = m.group(1)
    return n.replace("{slash}", "/")


def pulisci(s):
    for c in VIETATI:
        if c in s:
            raise ValueError(f"glifo non disponibile nel font: {c!r} in {s!r}")
    return s


# ---------------------------------------------------------------- tavola
class Tavola:
    """Immagine RGBA di lavoro a SS volte la risoluzione finale; u = unita' di progetto (1170 px)."""

    def __init__(self, W, H, stile, numero, tag, prog):
        self.W, self.H = W * SS, H * SS
        self.u = self.W / 1170
        self.pal = PAL[stile]
        self.numero = numero
        self.tag, self.prog = tag, prog
        p = self.pal
        a = np.linspace(0, 1, self.H)[:, None, None]
        arr = (np.array(p["bg1"])[None, None, :] * (1 - a) + np.array(p["bg2"])[None, None, :] * a)
        arr = np.repeat(arr, self.W, axis=1).astype(np.uint8)
        self.im = Image.fromarray(arr, "RGB").convert("RGBA")
        self.cart_top = self.H - int((36 + 214) * self.u)
        self.y_min = int(self.H * 0.27)          # il 25 % alto resta libero per l'orologio
        self.y_max = self.cart_top - int(24 * self.u)

    # --- primitive
    def draw(self):
        return ImageDraw.Draw(self.im)

    def c(self, nome):
        return self.pal[nome]

    def w(self, x):
        return max(1, int(round(x * self.u)))

    def linea(self, a, b, col=None, w=1.6, dash=None, alfa=255):
        col = col or self.pal["line"]
        d = ImageDraw.Draw(self.im, "RGBA")
        if not dash:
            d.line([a, b], fill=tuple(col) + (alfa,), width=self.w(w))
            return
        (x1, y1), (x2, y2) = a, b
        L = math.hypot(x2 - x1, y2 - y1)
        if L == 0:
            return
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        pat = [dash[0] * self.u, dash[1] * self.u] if len(dash) == 2 else [v * self.u for v in dash]
        pos, i = 0.0, 0
        while pos < L:
            seg = pat[i % len(pat)]
            if i % 2 == 0:
                e = min(L, pos + seg)
                d.line([(x1 + ux * pos, y1 + uy * pos), (x1 + ux * e, y1 + uy * e)], fill=tuple(col) + (alfa,), width=self.w(w))
            pos += seg
            i += 1

    def poli(self, pts, col=None, riempi=None, w=1.6, alfa=255, alfa_r=255):
        d = ImageDraw.Draw(self.im, "RGBA")
        if riempi is not None:
            d.polygon(pts, fill=tuple(riempi) + (alfa_r,))
        if col is not None:
            d.line(list(pts) + [pts[0]], fill=tuple(col) + (alfa,), width=self.w(w), joint="curve")

    def cerchio(self, c, r, col=None, riempi=None, w=1.6, dash=None, alfa=255):
        d = ImageDraw.Draw(self.im, "RGBA")
        box = [c[0] - r, c[1] - r, c[0] + r, c[1] + r]
        if riempi is not None:
            d.ellipse(box, fill=tuple(riempi) + (255,))
        if col is not None and not dash:
            d.ellipse(box, outline=tuple(col) + (alfa,), width=self.w(w))
        elif col is not None:
            n = max(12, int(2 * math.pi * r / (self.u * (dash[0] + dash[1]))))
            for i in range(n):
                a0 = 360 * i / n
                d.arc(box, a0, a0 + 360 / n * dash[0] / (dash[0] + dash[1]), fill=tuple(col) + (alfa,), width=self.w(w))

    def rett(self, box, col=None, riempi=None, w=1.6, r=0, alfa=255, dash=None):
        x0, y0, x1, y1 = box
        if dash and col is not None:
            for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                self.linea(a, b, col, w, dash, alfa)
            return
        d = ImageDraw.Draw(self.im, "RGBA")
        kw = dict(fill=tuple(riempi) + (255,) if riempi is not None else None,
                  outline=tuple(col) + (alfa,) if col is not None else None, width=self.w(w))
        if r:
            d.rounded_rectangle(box, int(r), **kw)
        else:
            d.rectangle(box, **kw)

    def freccia(self, p, ang, size=15, col=None):
        """Punta di freccia piena che punta verso ang (radianti) con la punta in p."""
        col = col or self.pal["line"]
        s = size * self.u
        a1, a2 = ang + math.pi - 0.28, ang + math.pi + 0.28
        pts = [p, (p[0] + s * math.cos(a1), p[1] + s * math.sin(a1)), (p[0] + s * math.cos(a2), p[1] + s * math.sin(a2))]
        ImageDraw.Draw(self.im, "RGBA").polygon(pts, fill=tuple(col) + (255,))

    def txt(self, xy, s, px, col=None, peso="Light", ancora="l", base="s", ang=0, spazio=0.0, alone=None):
        """Testo. ancora l/m/r (orizzontale), base s (linea base) o m (centro). ang in gradi antiorari.
        alone = colore del contorno (alone) per leggere sopra i disegni."""
        s = pulisci(s)
        col = col or self.pal["txt"]
        f = font(px * self.u, peso)
        sw = self.w(3.2) if alone else 0
        if not ang:
            d = ImageDraw.Draw(self.im, "RGBA")
            if spazio:
                larg = sum(f.getlength(ch) for ch in s) + spazio * px * self.u * (len(s) - 1)
                x = xy[0] - (larg if ancora == "r" else larg / 2 if ancora == "m" else 0)
                for ch in s:
                    d.text((x, xy[1]), ch, font=f, fill=tuple(col) + (255,), anchor="l" + base,
                           stroke_width=sw, stroke_fill=tuple(alone) + (255,) if alone else None)
                    x += f.getlength(ch) + spazio * px * self.u
            else:
                d.text(xy, s, font=f, fill=tuple(col) + (255,), anchor=ancora + base,
                       stroke_width=sw, stroke_fill=tuple(alone) + (255,) if alone else None)
            return
        S_ = max(int(f.getlength(s)) + 40, int(px * self.u * 3) + 40)
        tmp = Image.new("RGBA", (2 * S_, 2 * S_), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((S_, S_), s, font=f, fill=tuple(col) + (255,), anchor=ancora + base,
                                 stroke_width=sw, stroke_fill=tuple(alone) + (255,) if alone else None)
        tmp = tmp.rotate(ang, resample=Image.BICUBIC)
        layer = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        layer.paste(tmp, (int(xy[0] - S_), int(xy[1] - S_)))
        self.im.alpha_composite(layer)

    def incolla(self, img, x, y):
        """Incolla img (RGBA) con l'angolo in alto a sinistra in (x, y); tollera i bordi."""
        layer = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        layer.paste(img, (int(x), int(y)))
        self.im.alpha_composite(layer)

    def incolla_centro(self, img, cx, cy):
        self.incolla(img, cx - img.width / 2, cy - img.height / 2)

    # --- elementi di disegno
    def griglia(self, passo, ox, oy, forte=5, alfa=44):
        lay = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        g = self.pal["grid"]
        x = ox % passo
        while x < self.W:
            i = round((x - ox) / passo)
            d.line([x, 0, x, self.cart_top], fill=g + ((alfa + 30) if i % forte == 0 else alfa,), width=self.w(1.4 if i % forte == 0 else 0.8))
            x += passo
        y = oy % passo
        while y < self.cart_top:
            i = round((y - oy) / passo)
            d.line([0, y, self.W, y], fill=g + ((alfa + 30) if i % forte == 0 else alfa,), width=self.w(1.4 if i % forte == 0 else 0.8))
            y += passo
        self.im.alpha_composite(lay)

    def quota_h(self, x1, x2, y, testo, y_ob1=None, y_ob2=None, col=None, px=34, sopra=True):
        col = col or self.pal["line"]
        for x, yo in ((x1, y_ob1), (x2, y_ob2)):
            if yo is not None:
                s = 1 if y > yo else -1
                self.linea((x, yo + s * 10 * self.u), (x, y + s * 16 * self.u), col, 1.2)
        self.linea((x1, y), (x2, y), col, 1.6)
        self.freccia((x1, y), math.pi, 18, col)
        self.freccia((x2, y), 0, 18, col)
        self.txt(((x1 + x2) / 2, y - (12 if sopra else -42) * self.u), testo, px, col, "Regular", "m")

    def quota_v(self, y1, y2, x, testo, x_ob1=None, x_ob2=None, col=None, px=34, lato=1, off=14):
        col = col or self.pal["line"]
        for y, xo in ((y1, x_ob1), (y2, x_ob2)):
            if xo is not None:
                s = 1 if x > xo else -1
                self.linea((xo + s * 10 * self.u, y), (x + s * 16 * self.u, y), col, 1.2)
        self.linea((x, y1), (x, y2), col, 1.6)
        self.freccia((x, y1), -math.pi / 2, 18, col)
        self.freccia((x, y2), math.pi / 2, 18, col)
        self.txt((x + lato * off * self.u, (y1 + y2) / 2), testo, px, col, "Regular", "m", "m", ang=90 if lato > 0 else 90)

    def richiamo(self, p_da, p_a, testo, px=30, col=None, ancora="l", alone=True, sotto=None):
        """Linea di richiamo da p_da (sul disegno) a p_a, con testo accanto a p_a."""
        col = col or self.pal["acc2"]
        self.cerchio(p_da, 5 * self.u, riempi=col, col=None)
        self.linea(p_da, p_a, col, 1.6)
        dx = 10 * self.u if ancora == "l" else -10 * self.u
        self.txt((p_a[0] + dx, p_a[1]), testo, px, col, "SemiLight", ancora, "m", alone=self.pal["bg2"] if alone else None)

    def cornice(self, titolo, sottotitolo, scala):
        p = self.pal
        m = int(36 * self.u)
        # riquadro e cartiglio
        d = self.draw()
        x0, x1 = m, self.W - m
        y1 = self.H - m
        yc = self.cart_top
        d.rectangle([x0, yc, x1, y1], fill=p["bg2"] + (255,))
        self.rett((x0, int(self.y_min * 0.0 + 36 * self.u), x1, y1), p["line"], None, 2.4)
        self.linea((x0, yc), (x1, yc), p["line"], 2.4)
        xs = x0 + int((x1 - x0) * 0.56)
        self.linea((xs, yc), (xs, y1), p["line"], 1.6)
        ym = (yc + y1) // 2
        self.linea((xs, ym), (x1, ym), p["line"], 1.6)
        xm = (xs + x1) // 2
        self.linea((xm, yc), (xm, y1), p["line"], 1.6)
        # titolo
        self.txt((x0 + 22 * self.u, yc + 38 * self.u), "TITOLO", 22, p["faint"], "Regular")
        pxt = 54
        while font(pxt * self.u, "SemiBold").getlength(titolo) > (xs - x0 - 44 * self.u) and pxt > 30:
            pxt -= 2
        self.txt((x0 + 22 * self.u, yc + 112 * self.u), titolo, pxt, p["line"], "SemiBold")
        self.txt((x0 + 22 * self.u, yc + 160 * self.u), sottotitolo, 30, p["txt"], "Light")
        self.txt((x0 + 22 * self.u, y1 - 14 * self.u), "SWIMTIMER", 24, p["acc2"] if p["tipo"] != "carta" else p["acc2"], "SemiBold",
                 spazio=0.3)
        # celle
        celle = [((xs, yc), (xm, ym), "SCALA", scala), ((xm, yc), (x1, ym), "REV.", "v0.5"),
                 ((xs, ym), (xm, y1), "DATA", datetime.date.today().strftime("%d/%m/%Y")),
                 ((xm, ym), (x1, y1), "FOGLIO", f"{self.numero}/{N_FOGLI}")]
        for (a, b, et, val) in celle:
            self.txt((a[0] + 14 * self.u, a[1] + 32 * self.u), et, 20, p["faint"], "Regular")
            self.txt((a[0] + 14 * self.u, b[1] - 20 * self.u), val, 36, p["line"], "SemiBold")

    def finale(self, W, H):
        return self.im.convert("RGB").resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- dati dai PCB
def togli_zone(t):
    out, i = [], 0
    while True:
        m = re.search(r"^\s*\(zone\b", t[i:], re.M)
        if not m:
            out.append(t[i:])
            break
        a = i + m.start()
        out.append(t[i:a])
        prof, j = 0, a + t[a:].index("(")
        while True:
            c = t[j]
            if c == "(":
                prof += 1
            elif c == ")":
                prof -= 1
                if prof == 0:
                    break
            j += 1
        i = j + 1
    return "".join(out)


class Scheda:
    """Una scheda: render 3D, maschere degli strati, dati (reti, posizioni) e dimensioni in mm."""

    VISTE = {   # nome: (rotazione, zoom, lato)
        "iso": ("-55,0,-35", 0.75, "top"),
        "alto": ("0,0,0", 0.8, "top"),
        "fronte": ("0,0,0", 1.1, "front"),
        "lato": ("0,0,0", 1.1, "left"),
    }

    def __init__(self, nome, pcb, forza=False):
        self.nome, self.pcb = nome, Path(pcb).resolve()
        if not self.pcb.exists():
            sys.exit(f"PCB non trovato: {self.pcb}")
        self.testo_pcb = self.pcb.read_text(encoding="utf-8")
        self.chiave = hashlib.sha1(self.testo_pcb.encode("utf-8")).hexdigest()[:12]
        self.forza = forza
        self._m = None
        self._d = None
        self.pxmm = 140 if nome == "tag" else 70

    @property
    def mm(self):
        self.strati()
        return self._mm

    # -- dati dal PCB
    def dati(self):
        if self._d is None:
            tmp = Path(tempfile.mkdtemp(prefix="wp_dati_")) / "dati.json"
            subprocess.run([str(KIPY), str(QUI / "estrai_dati.py"), str(self.pcb), str(tmp)], check=True,
                           capture_output=True, cwd=self.pcb.parent)
            self._d = json.loads(tmp.read_text(encoding="utf-8"))
        return self._d

    # -- render 3D
    def render_file(self, v):
        return RENDER / f"{self.nome}_{v}.png"

    def prepara_render(self, viste):
        RENDER.mkdir(exist_ok=True)
        procs = []
        for v in viste:
            f = self.render_file(v)
            k = f.with_suffix(".chiave")
            if not self.forza and f.exists() and k.exists() and k.read_text() == self.chiave + str(self.VISTE[v]):
                continue
            rot, zoom, lato = self.VISTE[v]
            cmd = [str(CLI), "pcb", "render", "--quality", "high", "--background", "transparent", "--width", "1800",
                   "--height", "1800", "--zoom", str(zoom), "--side", lato, "--rotate", rot, "-o", str(f), str(self.pcb)]
            procs.append((v, f, k, subprocess.Popen(cmd, cwd=self.pcb.parent, stdout=subprocess.DEVNULL,
                                                    stderr=subprocess.DEVNULL)))
            if len(procs) >= 3:
                self._attendi(procs)
                procs = []
        self._attendi(procs)

    def _attendi(self, procs):
        for v, f, k, p in procs:
            p.wait(timeout=900)
            if p.returncode != 0 or not f.exists():
                print(f"  ! render {self.nome}/{v} fallito")
            else:
                k.write_text(self.chiave + str(self.VISTE[v]))

    def render(self, vista):
        self.prepara_render([vista])
        img = Image.open(self.render_file(vista)).convert("RGBA")
        bb = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        return img.crop(bb) if bb else img

    # -- strati
    def strati(self):
        """dict nome -> maschera L (255 = presente), tutte della stessa misura (riquadro della scheda)."""
        if self._m is not None:
            return self._m
        tmp = Path(tempfile.mkdtemp(prefix="wp_"))
        senza = tmp / "senza_zone.kicad_pcb"
        senza.write_text(togli_zone(self.testo_pcb), encoding="utf-8")
        elenco = "F.Cu,B.Cu,Edge.Cuts,F.SilkS,B.SilkS,F.Mask,B.Mask"
        for sub, scheda in (("pieno", self.pcb), ("piste", senza)):
            subprocess.run([str(CLI), "pcb", "export", "svg", "--mode-multi", "--black-and-white", "--page-size-mode", "2",
                            "--exclude-drawing-sheet", "-l", elenco, "-o", str(tmp / sub), str(scheda)],
                           check=True, capture_output=True, cwd=self.pcb.parent)
        m = {}
        for sub in ("pieno", "piste"):
            for nome, alias in (("F_Cu", "F_Cu"), ("B_Cu", "B_Cu"), ("Edge_Cuts", "Edge_Cuts"), ("F_Silkscreen", "F_SilkS"),
                                ("B_Silkscreen", "B_SilkS"), ("F_SilkS", "F_SilkS"), ("B_SilkS", "B_SilkS"), ("F_Mask", "F_Mask"), ("B_Mask", "B_Mask")):
                tr = list((tmp / sub).glob(f"*-{nome}.svg"))
                if tr:
                    m[f"{sub}:{alias}"] = self._raster(tr[0])
        size = m["pieno:Edge_Cuts"].size
        for k in list(m):
            if m[k].size != size:
                m[k] = m[k].resize(size)
        for sub in ("pieno", "piste"):
            for nome in ("F_Cu", "B_Cu", "F_SilkS", "B_SilkS", "F_Mask", "B_Mask"):
                m.setdefault(f"{sub}:{nome}", Image.new("L", size, 0))
        m["contorno"] = self._riempi(m["pieno:Edge_Cuts"])
        self._mm = (size[0] / self.pxmm, size[1] / self.pxmm)
        self._m = m
        return m

    def _raster(self, svg):
        doc = pymupdf.open(svg)
        k = self.pxmm / 2.83465
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(k, k), colorspace=pymupdf.csGRAY)
        return ImageChops.invert(Image.frombytes("L", (pix.width, pix.height), pix.samples))

    @staticmethod
    def _riempi(edge):
        p = Image.new("L", (edge.width + 20, edge.height + 20), 0)
        p.paste(edge.point(lambda v: 255 if v > 80 else 0), (10, 10))
        ImageDraw.floodfill(p, (0, 0), 128)
        interno = p.point(lambda v: 255 if v != 128 else 0)
        return interno.crop((10, 10, 10 + edge.width, 10 + edge.height))

    def arte(self, box, spx, strati, specchio=False):
        """Regione box=(x0,y0,w,h) in mm disegnata a spx px/mm; strati = [(maschera, colore, alfa)]."""
        m = self.strati()
        x0, y0, w, h = box
        k = self.pxmm
        Wp, Hp = max(1, int(round(w * spx))), max(1, int(round(h * spx)))
        out = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0))
        for nome, col, alfa in strati:
            cr = m[nome].crop((int(round(x0 * k)), int(round(y0 * k)), int(round((x0 + w) * k)), int(round((y0 + h) * k))))
            cr = cr.resize((Wp, Hp), Image.LANCZOS)
            if specchio:
                cr = cr.transpose(Image.FLIP_LEFT_RIGHT)
            lay = Image.new("RGBA", (Wp, Hp), tuple(col) + (255,))
            lay.putalpha(cr.point(lambda v: int(v * alfa)))
            out = Image.alpha_composite(out, lay)
        return out


class Vista:
    """Mappa millimetri della scheda -> pixel della tavola."""

    def __init__(self, cx, cy, wmm, hmm, s, specchio=False):
        self.s, self.w, self.h, self.sp = s, wmm, hmm, specchio
        self.x0, self.y0 = cx - wmm * s / 2, cy - hmm * s / 2

    def p(self, x, y):
        return (self.x0 + ((self.w - x) if self.sp else x) * self.s, self.y0 + y * self.s)


def stili_strati(pal, piste=True, tinta=0.22):
    """Strati colorati nello stile della tavola: contorno, rame inferiore tenue, rame superiore, serigrafia."""
    t = pal["tipo"]
    cu = "piste:" if piste else "pieno:"
    if t == "carta":
        return [("contorno", pal["faint"], 0.10), (cu + "B_Cu", pal["faint"], 0.55), (cu + "F_Cu", pal["line"], 1.0),
                ("pieno:F_SilkS", pal["acc2"], 0.9), ("pieno:Edge_Cuts", pal["line"], 1.0)]
    if t == "verde":
        return [("contorno", (10, 70, 56), 0.9), (cu + "B_Cu", pal["faint"], 0.5), (cu + "F_Cu", pal["line"], 1.0),
                ("pieno:F_SilkS", pal["txt"], 0.9), ("pieno:Edge_Cuts", pal["acc"], 1.0)]
    return [("contorno", pal["faint"], tinta), (cu + "B_Cu", pal["faint"], 0.55), (cu + "F_Cu", pal["line"], 1.0),
            ("pieno:F_SilkS", pal["acc"], 0.9), ("pieno:Edge_Cuts", pal["line"], 1.0)]


def metti_arte(t, v, img):
    t.incolla(img, v.x0, v.y0)


def funzione(val):
    v = val.upper()
    if v.startswith("E73"):
        return "MODULO"
    if v.startswith("LSM6"):
        return "IMU"
    if v.startswith("W25Q"):
        return "FLASH"
    if v.startswith("BQ25"):
        return "CARICA"
    if v.startswith("BATT"):
        return "CELLA"
    if "ROSSO" in v or v.startswith("LED"):
        return "LED"
    if v.startswith("1N"):
        return "DIODO"
    return val


def orient_pad(fp, p):
    """'col' se la piazzola sta in una colonna di piazzole, 'riga' se in una riga."""
    col = sum(1 for q in fp["pads"] if q is not p and abs(q["pos"][0] - p["pos"][0]) < 0.06)
    riga = sum(1 for q in fp["pads"] if q is not p and abs(q["pos"][1] - p["pos"][1]) < 0.06)
    return "col" if col >= riga else "riga"


def etichette_pad(t, v, fp, spx_px, px=22, solo_nominate=True, col=None, alone=True, pads=None, filtro=None):
    for p in (pads or fp["pads"]):
        nm = nome_rete(p)
        if not nm or (filtro and not filtro(p)):
            continue
        X, Y = v.p(*p["pos"])
        ang = 90 if orient_pad(fp, p) == "riga" and len(fp["pads"]) > 3 else 0
        t.txt((X, Y), nm, px, col or t.pal["acc"], "SemiBold", "m", "m", ang=ang, alone=t.pal["bg2"] if alone else None)


def etichette_colonna(t, elenco, x_col, a_destra=True, sep=58, col=None, px=28):
    """Sigle con richiamo a gomito, distribuite in una colonna senza sovrapposizioni.
    elenco = [(X, Y, testo)] in px della tavola."""
    col = col or t.pal["acc2"]
    elenco = sorted(elenco, key=lambda a: a[1])
    ys = [a[1] for a in elenco]
    for _ in range(80):
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] < sep * t.u:
                m = (ys[i] + ys[i - 1]) / 2
                ys[i - 1], ys[i] = m - sep * t.u / 2, m + sep * t.u / 2
    for (X, Y, testo), yl in zip(elenco, ys):
        d = 36 * t.u if a_destra else -36 * t.u
        t.cerchio((X, Y), 5 * t.u, riempi=col)
        t.linea((X, Y), (x_col - d, yl), col, 1.5)
        t.linea((x_col - d, yl), (x_col, yl), col, 1.5)
        t.txt((x_col + (8 * t.u if a_destra else -8 * t.u), yl), testo, px, col, "SemiLight", "l" if a_destra else "r", "m")


def etichette_righe(t, items, px=26, col=None, tol=6):
    """items = [(X, Y, testo)]. La riga piu' in alto ha il testo verticale sopra, le altre sotto."""
    col = col or t.pal["acc"]
    righe = sorted({round(y / (tol * t.u)) for _, y, _ in items})
    top = righe[0]
    for X, Y, s_ in items:
        if round(Y / (tol * t.u)) == top:
            t.linea((X, Y - 16 * t.u), (X, Y - 44 * t.u), col, 1.2)
            t.txt((X, Y - 52 * t.u), s_, px, col, "SemiBold", "l", "m", ang=90, alone=t.pal["bg2"])
        else:
            t.linea((X, Y + 16 * t.u), (X, Y + 44 * t.u), col, 1.2)
            t.txt((X, Y + 52 * t.u), s_, px, col, "SemiBold", "l", "m", ang=-90, alone=t.pal["bg2"])


def tondo(t, tagobj, vm, centro_mm, L_mm, centro, r, lettera, titolo, strati, r_src_mm, ref_fp=None, px=22, filtro=None, specchio=False):
    """Ingrandimento tondo con linea di richiamo dalla pianta."""
    p = t.pal
    X, Y = vm.p(*centro_mm)
    rs = r_src_mm * vm.s
    t.cerchio((X, Y), rs, p["acc2"], None, 2.2)
    dx, dy = centro[0] - X, centro[1] - Y
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    t.linea((X + ux * rs, Y + uy * rs), (centro[0] - ux * r, centro[1] - uy * r), p["acc2"], 1.8)
    sp = 2 * r / L_mm
    img = tagobj.arte((centro_mm[0] - L_mm / 2, centro_mm[1] - L_mm / 2, L_mm, L_mm), sp, strati, specchio)
    # sfondo scuro/chiaro del tondo
    base = Image.new("RGBA", img.size, tuple(p["bg2"]) + (255,))
    base = Image.alpha_composite(base, img)
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, base.width - 1, base.height - 1], fill=255)
    base.putalpha(mask)
    t.incolla_centro(base, *centro)
    t.cerchio(centro, r, p["line"], None, 3.0)
    t.cerchio(centro, r + 9 * t.u, p["line"], None, 1.0)
    ox_, oy_ = centro_mm[0] - L_mm / 2, centro_mm[1] - L_mm / 2
    vd = Vista(centro[0], centro[1], L_mm, L_mm, sp)
    _pp = vd.p
    vd.p = lambda x, y: _pp(x - ox_, y - oy_)
    d = tagobj.dati()
    for ref, fp in d["fps"].items():
        if fp["side"] != "F" or fp["val"] in ("",):
            continue
        for q in fp["pads"]:
            x, y = q["pos"]
            if abs(x - centro_mm[0]) < L_mm / 2 - 0.2 and abs(y - centro_mm[1]) < L_mm / 2 - 0.2:
                if filtro and not filtro(fp, q):
                    continue
                nm = nome_rete(q)
                if not nm:
                    continue
                X2, Y2 = vd.p(x, y)
                ang = 90 if (orient_pad(fp, q) == "riga" and len(fp["pads"]) > 3) else 0
                t.txt((X2, Y2), nm, px, p["acc"], "SemiBold", "m", "m", ang=ang, alone=p["bg2"])
    # lettera e titolo
    bx, by = centro[0] - r * 0.72, centro[1] - r * 0.72
    t.cerchio((bx, by), 24 * t.u, p["line"], p["bg2"], 2.2)
    t.txt((bx, by), lettera, 30, p["line"], "SemiBold", "m", "m")
    t.txt((centro[0], centro[1] + r + 46 * t.u), titolo, 28, p["line"], "SemiLight", "m")


# ---------------------------------------------------------------- utilita' immagine
def iso(img, scala=1.0):
    if scala != 1:
        img = img.resize((int(img.width * scala), int(img.height * scala)), Image.LANCZOS)
    w, h = img.size
    c, s = math.cos(math.radians(30)), 0.5
    ow, oh = int(math.ceil((w + h) * c)), int(math.ceil((w + h) * s))
    coeff = (1 / (2 * c), 1 / (2 * s), -h / 2, -1 / (2 * c), 1 / (2 * s), h / 2)
    return img.transform((ow, oh), Image.AFFINE, coeff, Image.BICUBIC)


C30, S30 = math.cos(math.radians(30)), 0.5


def pt_iso(org, hh, x, y, z=0.0):
    """Punto (x, y, z) di un'immagine piana alta hh, proiettata e incollata con l'angolo in org."""
    return (org[0] + (x - y) * C30 + hh * C30, org[1] + (x + y) * S30 - z)


def linee_render(img, col, soglia=22, spessore=3):
    """Disegno a linee ricavato da un render: bordi di luminosita' e silhouette."""
    bg = Image.new("RGB", img.size, (128, 128, 128))
    bg.paste(img.convert("RGB"), mask=img.getchannel("A"))
    L = bg.convert("L")
    L = ImageChops.invert(Image.eval(L, lambda v: v))        # nessun effetto sui bordi, serve solo il tipo
    L = bg.convert("L").filter(ImageFilter.GaussianBlur(1.2))
    e = L.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > soglia else 0)
    a = img.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    sil = ImageChops.subtract(a.filter(ImageFilter.MaxFilter(5)), a.filter(ImageFilter.MinFilter(5)))
    m = ImageChops.lighter(e, sil)
    m = ImageChops.multiply(m, a.filter(ImageFilter.MaxFilter(7)))
    m = m.filter(ImageFilter.MaxFilter(spessore))
    lay = Image.new("RGBA", img.size, tuple(col) + (255,))
    lay.putalpha(m)
    return lay


def ritaglia(img, margine=0):
    bb = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return img.crop(bb) if bb else img


def adatta(img, w, h):
    k = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)


def tabella(t, x, y, righe, larghezze, px=30, altezza=48, intestazione=True, col=None):
    p = t.pal
    col = col or p["line"]
    xs = [x]
    for wcol in larghezze:
        xs.append(xs[-1] + wcol * t.u)
    for i, riga in enumerate(righe):
        yy = y + i * altezza * t.u
        if i == 0 and intestazione:
            t.rett((xs[0], yy, xs[-1], yy + altezza * t.u), col, p["bg2"], 2.0)
        else:
            t.linea((xs[0], yy + altezza * t.u), (xs[-1], yy + altezza * t.u), p["faint"], 1.0)
        for j, cella in enumerate(riga):
            t.txt((xs[j] + 12 * t.u, yy + altezza * 0.72 * t.u), cella, px, col, "SemiBold" if (i == 0 and intestazione) else "Light")
    t.rett((xs[0], y, xs[-1], y + len(righe) * altezza * t.u), col, None, 2.0)
    for xx in xs[1:-1]:
        t.linea((xx, y), (xx, y + len(righe) * altezza * t.u), p["faint"], 1.0)


def modello_e73(scheda):
    m = re.search(r"WIRELM-SMD_L([\d.]+)-W([\d.]+)-H([\d.]+)", scheda.testo_pcb)
    return tuple(float(v) for v in m.groups()) if m else (18.0, 13.0, 3.0)


def fp_per_valore(d, inizio):
    for r, f in d["fps"].items():
        if f["val"].upper().startswith(inizio.upper()):
            return r, f
    return None, None


def vista_scheda(t, sch, cx, cy, larg_px, specchio=False):
    sch.strati()
    wmm, hmm = sch.mm
    return Vista(cx, cy, wmm, hmm, larg_px / wmm, specchio)


# ================================================================ i 20 fogli
def s01(t, tag, prog):
    d = tag.dati()
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.585, 680 * t.u)
    t.griglia(2.54 * v.s, v.x0, v.y0)
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, stili_strati(t.pal)))
    wmm, hmm = tag.mm
    x0, y0, x1, y1 = v.x0, v.y0, v.x0 + wmm * v.s, v.y0 + hmm * v.s
    t.quota_h(x0, x1, y1 + 90 * t.u, f"{virgola(d['w'] - 0.1)} mm", y1, y1)
    t.quota_v(y0, y1, x0 - 90 * t.u, f"{virgola(d['h'] - 0.1)} mm", x0, x0, lato=-1)
    el = []
    for ref, f in d["fps"].items():
        if f["side"] == "F" and ref[0] in "UJD" and not ref.startswith("TP"):
            X, Y = v.p(*f["pos"])
            el.append((X, Y, f"{ref}  {funzione(f['val'])}"))
    etichette_colonna(t, el, x1 + 70 * t.u, True)
    t.txt((x0, y0 - 28 * t.u), "FRONTE (F.Cu + serigrafia)  ·  rame inferiore tenue", 26, t.pal["faint"], "Light", "l")
    t.cornice("TAG  v0.5", "Pianta  ·  nRF52840 + E73", "ca. 1:1")


def s02(t, tag, prog):
    p = t.pal
    m = tag.strati()
    wmm, hmm = tag.mm
    k = 19.5 * t.u                                        # px per mm
    w, h = int(wmm * k), int(hmm * k)
    L, W_, H_ = modello_e73(tag)
    d = tag.dati()
    cell = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cell)
    cd.rounded_rectangle([int(0.06 * w), int(0.08 * h), int(0.94 * w), int(0.92 * h)], int(0.07 * w), fill=p["faint"] + (60,),
                         outline=p["line"] + (255,), width=t.w(2.4))
    cd.line([int(0.06 * w), int(0.22 * h), int(0.94 * w), int(0.22 * h)], fill=p["line"] + (170,), width=t.w(1.4))
    spx = k
    sc = lambda nome, col, a: tag.arte((0, 0, *tag.mm), spx, [(nome, col, a)])
    lastra = lambda a: Image.alpha_composite(tag.arte((0, 0, *tag.mm), spx, [("contorno", p["faint"], a)]),
                                              tag.arte((0, 0, *tag.mm), spx, [("pieno:Edge_Cuts", p["line"], 1.0)]))
    inf = Image.alpha_composite(lastra(0.30), tag.arte((0, 0, *tag.mm), spx, [("piste:B_Cu", p["acc2"], 0.95)]))
    fr4 = lastra(0.45)
    sup = Image.alpha_composite(lastra(0.22), tag.arte((0, 0, *tag.mm), spx, [("piste:F_Cu", p["line"], 1.0), ("pieno:F_SilkS", p["acc"], 0.95)]))
    strati = [("1", "CELLA", cell), ("2", "RAME INF. B.Cu", inf), ("3", "SCHEDA FR4", fr4), ("4", "RAME SUP. F.Cu", sup)]
    gap = 175 * t.u
    cx = t.W / 2
    n = 5
    base_y = t.y_min + 120 * t.u + (n - 1) * gap + 270 * t.u
    isos = []
    for i, (num, nome, img) in enumerate(strati):
        im = iso(img)
        cy = base_y - i * gap
        isos.append((im, cy))
    # asse verticale (linea d'asse) dietro agli strati
    top_y = base_y - (n - 1) * gap - 330 * t.u
    t.linea((cx, base_y + 330 * t.u), (cx, top_y), p["acc2"], 1.6, (30, 8, 4, 8))
    for i, (im, cy) in enumerate(isos):
        t.incolla_centro(im, cx, cy)
        org = (cx - im.width / 2, cy - im.height / 2)
        hh = h
        # spigoli verticali tratteggiati verso lo strato sopra
        if i < len(isos) - 1:
            for (x, y) in ((0, 0), (w, 0), (0, h), (w, h)):
                a = pt_iso(org, hh, x, y)
                t.linea(a, (a[0], a[1] - gap), p["faint"], 1.2, (8, 8))
    # modulo E73 come parallelepipedo sopra lo strato 4
    im4, cy4 = isos[3]
    org = (cx - im4.width / 2, cy4 - im4.height / 2 - gap)
    r1, f1 = fp_per_valore(d, "E73")
    bx, by = f1["pos"]
    bw, bh = W_, L                                            # larghezza x, lunghezza y (scheda in verticale)
    zk = H_ * k
    P = lambda x, y, z=0: pt_iso(org, h, x * k, y * k, z)
    xa, xb, ya, yb = bx - bw / 2, bx + bw / 2, by - bh / 2, by + bh / 2
    top = [P(xa, ya, zk), P(xb, ya, zk), P(xb, yb, zk), P(xa, yb, zk)]
    lat1 = [P(xa, yb, 0), P(xb, yb, 0), P(xb, yb, zk), P(xa, yb, zk)]
    lat2 = [P(xb, ya, 0), P(xb, yb, 0), P(xb, yb, zk), P(xb, ya, zk)]
    t.poli(lat1, p["line"], p["bg2"], 2.0)
    t.poli(lat2, p["line"], p["bg2"], 2.0)
    t.poli(top, p["line"], p["bg2"], 2.0, alfa_r=255)
    # antenna: striscia sul lato alto del modulo
    ant = [P(xa + 1.2, ya + 0.6, zk), P(xb - 1.2, ya + 0.6, zk), P(xb - 1.2, ya + 3.4, zk), P(xa + 1.2, ya + 3.4, zk)]
    t.poli(ant, p["acc"], None, 1.8)
    a_c = ((ant[0][0] + ant[2][0]) / 2, (ant[0][1] + ant[2][1]) / 2)
    # palloncini numerati e legenda
    def pallino(punto, xt, num):
        yt = punto[1]
        t.linea(punto, (xt - 26 * t.u, yt), p["acc2"], 1.6)
        t.cerchio(punto, 5 * t.u, riempi=p["acc2"])
        t.cerchio((xt, yt), 26 * t.u, p["line"], p["bg2"], 2.0)
        t.txt((xt, yt), num, 30, p["line"], "SemiBold", "m", "m")
    for i, (im, cy) in enumerate(isos):
        org_i = (cx - im.width / 2, cy - im.height / 2)
        tip = pt_iso(org_i, h, w, 0)                      # punta destra del rombo
        pallino(tip, t.W - 80 * t.u, strati[i][0])
    pallino(((top[1][0] + top[2][0]) / 2, (top[1][1] + top[2][1]) / 2), t.W - 80 * t.u, "5")
    # legenda
    leg = [("1", "CELLA"), ("2", "RAME INFERIORE B.Cu"), ("3", "SCHEDA FR4"), ("4", "RAME SUPERIORE F.Cu + SERIGRAFIA"), ("5", f"MODULO E73  {virgola(L, 0)} x {virgola(W_, 0)} x {virgola(H_, 1)} mm")]
    y0 = t.cart_top - 24 * t.u - 5 * 44 * t.u - 8 * t.u
    for i, (n_, s_) in enumerate(leg):
        yy = y0 + (i + 1) * 44 * t.u
        t.cerchio((70 * t.u, yy - 10 * t.u), 17 * t.u, p["line"], None, 1.6)
        t.txt((70 * t.u, yy - 10 * t.u), n_, 22, p["line"], "SemiBold", "m", "m")
        t.txt((104 * t.u, yy), s_, 27, p["txt"], "Light")
    t.cornice("TAG  v0.5", "Vista esplosa", "n.s.")


def s03(t, tag, prog):
    p = t.pal
    d = tag.dati()
    L, W_, H_ = modello_e73(tag)
    wmm, hmm = tag.mm
    k = 30 * t.u                                          # px per mm
    cx = t.W / 2
    spess = d["spessore"]
    h_sec = (H_ + 1.6) * k + spess * k + 28 * t.u + 3.6 * k + 1.6 * k
    ypcb = t.H * 0.54 - h_sec / 2 + (H_ + 1.6) * k
    ytop = ypcb - (H_ + 1.6) * k - 250 * t.u
    # inset pianta con linea di sezione
    ix, iy, iw = 90 * t.u, ytop - 40 * t.u, 130 * t.u
    iv = Vista(ix + iw / 2, iy + iw * hmm / wmm / 2, wmm, hmm, iw / wmm)
    metti_arte(t, iv, tag.arte((0, 0, *tag.mm), iv.s, [("contorno", p["faint"], 0.3), ("pieno:Edge_Cuts", p["line"], 1.0), ("piste:F_Cu", p["line"], 0.7)]))
    r1, f1 = fp_per_valore(d, "E73")
    yc_mm = f1["pos"][1]
    ya = iv.p(0, yc_mm)[1]
    t.linea((ix - 30 * t.u, ya), (ix + iw + 30 * t.u, ya), p["acc"], 2.0, (22, 6, 4, 6))
    t.txt((ix - 18 * t.u, ya), "A", 28, p["acc"], "SemiBold", "r", "m")
    t.txt((ix + iw + 18 * t.u, ya), "A", 28, p["acc"], "SemiBold", "l", "m")
    # sezione: PCB al centro, cella sotto, resina intorno
    x0 = cx - wmm * k / 2
    ycell0 = ypcb + spess * k + 28 * t.u
    ncell = 3.6 * k
    yres_top = ypcb - H_ * k - 1.6 * k
    yres_bot = ycell0 + ncell + 1.6 * k
    xr0, xr1 = x0 - 1.6 * k, x0 + wmm * k + 1.6 * k
    # resina: maschera esterna meno interno
    outer = Image.new("L", t.im.size, 0)
    ImageDraw.Draw(outer).rounded_rectangle([xr0, yres_top, xr1, yres_bot], int(1.2 * k), fill=255)
    inner = Image.new("L", t.im.size, 0)
    di = ImageDraw.Draw(inner)
    di.rectangle([x0, ypcb, x0 + wmm * k, ypcb + spess * k], fill=255)
    di.rectangle([x0 + 2.0 * k, ycell0, x0 + wmm * k - 2.0 * k, ycell0 + ncell], fill=255)
    # componenti (sagome nella vista laterale)
    alt = {"E73": H_, "SOIC": 1.75, "LGA": 0.86, "DSBGA": 0.45, "HDR": 2.6, "SOD": 1.0, "LED": 0.5, "0402": 0.5}
    elem = []
    for ref, f in d["fps"].items():
        if f["side"] != "F" or ref.startswith("TP"):
            continue
        hz = 0.5
        for kk, vv in alt.items():
            if kk in f["fpid"].upper() or kk in f["val"].upper():
                hz = vv
                break
        elem.append((ref, f, hz))
    for ref, f, hz in sorted(elem, key=lambda e: -e[2]):
        xa = x0 + f["x0"] * k
        xb = xa + f["w"] * k
        di.rectangle([xa, ypcb - hz * k, xb, ypcb], fill=255)
    hatch = Image.new("L", t.im.size, 0)
    dh = ImageDraw.Draw(hatch)
    passo = int(26 * t.u)
    for off in range(-int(t.H), int(t.W), passo):
        dh.line([off, yres_bot + 40, off + (yres_bot - yres_top) + 80, yres_top - 40], fill=255, width=t.w(1.6))
    region = ImageChops.subtract(outer, inner)
    hatch = ImageChops.multiply(hatch, region)
    lay = Image.new("RGBA", t.im.size, tuple(p["faint"]) + (255,))
    lay.putalpha(hatch)
    t.im.alpha_composite(lay)
    t.rett((xr0, yres_top, xr1, yres_bot), p["line"], None, 2.4, r=1.2 * k)
    # PCB (sezione tagliata, tratteggio fitto)
    t.rett((x0, ypcb, x0 + wmm * k, ypcb + spess * k), p["line"], p["bg2"], 2.2)
    t.rett((x0, ypcb, x0 + wmm * k, ypcb + 1.6 * t.u), p["acc"], p["acc"], 1.0)
    t.rett((x0, ypcb + spess * k - 1.6 * t.u, x0 + wmm * k, ypcb + spess * k), p["acc"], p["acc"], 1.0)
    # componenti
    for ref, f, hz in sorted(elem, key=lambda e: -e[2]):
        xa = x0 + f["x0"] * k
        xb = xa + f["w"] * k
        tagliato = abs(f["pos"][1] - yc_mm) < f["h"] / 2
        col = p["acc"] if tagliato else p["line"]
        t.rett((xa, ypcb - hz * k, xb, ypcb), col, p["bg2"], 2.0 if tagliato else 1.4)
        if f["val"].upper().startswith("E73"):
            t.txt(((xa + xb) / 2, ypcb - hz * k / 2), "E73", 34, p["line"], "SemiBold", "m", "m")
            e73 = (xa, xb, ypcb - hz * k)
        if f["val"].upper().startswith("W25"):
            t.txt(((xa + xb) / 2, ypcb - hz * k / 2), "U3", 22, p["line"], "Regular", "m", "m")
    # cella
    t.rett((x0 + 2.0 * k, ycell0, x0 + wmm * k - 2.0 * k, ycell0 + ncell), p["line"], p["bg2"], 2.2, r=0.5 * k)
    t.txt((cx, ycell0 + ncell / 2), "CELLA", 34, p["line"], "SemiBold", "m", "m")
    # simbolo di interruzione (spessore secondo la cella scelta)
    # palloncini numerati e quote
    def pall(num, bersaglio, y_pal=None):
        yb = bersaglio[1] if y_pal is None else y_pal
        xp = xr0 - 50 * t.u
        t.linea(bersaglio, (xp + 22 * t.u, yb), p["acc2"], 1.5)
        t.cerchio(bersaglio, 5 * t.u, riempi=p["acc2"])
        t.cerchio((xp, yb), 22 * t.u, p["line"], p["bg2"], 2.0)
        t.txt((xp, yb), num, 26, p["line"], "SemiBold", "m", "m")
    pall("1", (xr0 + 0.6 * k, yres_bot - 1.0 * k))
    pall("2", (x0 + 1.0 * k, ypcb + spess * k / 2), ypcb + spess * k / 2 + 36 * t.u)
    pall("3", (x0 + 2.0 * k, ycell0 + ncell / 2))
    pall("4", (e73[0], e73[2] + 0.3 * k), e73[2] - 20 * t.u)
    t.quota_v(ypcb, ypcb + spess * k, xr1 + 56 * t.u, f"{virgola(spess, 1)}", xr1, xr1, px=28, off=34)
    t.quota_v(e73[2], ypcb, xr1 + 120 * t.u, f"{virgola(H_, 1)}", e73[1] + 4 * t.u, xr1, px=28)
    t.quota_h(x0, x0 + wmm * k, yres_bot + 70 * t.u, f"{virgola(wmm)} mm", yres_bot, yres_bot)
    leg = ["RESINA (involucro)", "PCB FR4", "CELLA (spessore secondo la cella scelta)", "MODULO E73"]
    yl0 = yres_bot + 180 * t.u
    for i_, tx in enumerate(leg):
        yy = yl0 + i_ * 48 * t.u
        t.cerchio((cx - 250 * t.u, yy - 10 * t.u), 18 * t.u, p["line"], None, 1.6)
        t.txt((cx - 250 * t.u, yy - 10 * t.u), str(i_ + 1), 22, p["line"], "SemiBold", "m", "m")
        t.txt((cx - 214 * t.u, yy), tx, 28, p["txt"], "Light")
    t.txt((cx, ytop - 18 * t.u), "SEZIONE  A-A", 38, p["line"], "SemiBold", "m", spazio=0.1)
    t.cornice("TAG  v0.5", "Sezione trasversale", "ca. 3:1")


def s04(t, tag, prog):
    p = t.pal
    d = tag.dati()
    wmm, hmm = tag.mm
    v = vista_scheda(t, tag, t.W / 2, t.y_min + 320 * t.u, 400 * t.u)
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=36)
    st = stili_strati(p)
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, st))
    r = 185 * t.u
    cx1, cx2 = t.W * 0.285, t.W * 0.715
    ry1 = v.y0 + tag.mm[1] * v.s + 60 * t.u + r
    ry2 = ry1 + 2 * r + 110 * t.u
    r1, f1 = fp_per_valore(d, "E73")
    r2, f2 = fp_per_valore(d, "LSM6")
    r3, f3 = fp_per_valore(d, "BQ25")
    r4, f4 = fp_per_valore(d, "W25Q")
    L, W_, H_ = modello_e73(tag)
    xl = min(q["pos"][0] for q in f1["pads"])
    pl = [q for q in f1["pads"] if abs(q["pos"][0] - xl) < 0.06]
    ant_pos = (xl + 1.0, sum(q["pos"][1] for q in pl) / len(pl))
    def solo_f(fp, q):
        return True
    lst = [
        (ant_pos, 9.0, (cx1, ry1), "A", "MODULO E73  PAD SX", 5.0, None),
        (f2["pos"], 4.0, (cx2, ry1), "B", "LGA-14  IMU", 2.1, lambda fp, q: fp["val"].startswith("LSM6")),
        (f3["pos"], 2.3, (cx1, ry2), "C", "BGA  CARICATORE", 1.2, lambda fp, q: fp["val"].startswith("BQ25")),
        (f4["pos"], 8.2, (cx2, ry2), "D", "SOIC-8  FLASH", 4.2, lambda fp, q: fp["val"].startswith("W25Q")),
    ]
    for (pos, Lmm, ctr, lett, tit, rs, filt) in lst:
        tondo(t, tag, v, pos, Lmm, ctr, r, lett, tit, st, rs, px=21, filtro=filt)
    t.cornice("TAG  v0.5", "Ingrandimenti di dettaglio", "vari")


def s05(t, tag, prog):
    p = t.pal
    d = tag.dati()
    r1, f1 = fp_per_valore(d, "E73")
    L, W_, H_ = modello_e73(tag)
    bx, by = f1["pos"]
    reg = (bx - 8.6, by - L / 2 - 2.2, 17.2, L + 4.4)
    sp = (t.W - 300 * t.u) / reg[2]
    cx, cy = t.W / 2, t.y_min + (reg[3] * sp) / 2 + 50 * t.u
    vv = Vista(cx, cy, reg[2], reg[3], sp)
    vv.x0, vv.y0 = cx - reg[2] * sp / 2, cy - reg[3] * sp / 2
    # vista locale con offset di regione
    class V2(Vista):
        def p(s, x, y):
            return (vv.x0 + (x - reg[0]) * sp, vv.y0 + (y - reg[1]) * sp)
    v = V2(cx, cy, reg[2], reg[3], sp)
    t.griglia(2.54 * sp, v.p(0, 0)[0], v.p(0, 0)[1], alfa=34)
    img = tag.arte(reg, sp, stili_strati(p))
    t.incolla(img, vv.x0, vv.y0)
    xa, xb, ya, yb = bx - W_ / 2, bx + W_ / 2, by - L / 2, by + L / 2
    t.rett((*v.p(xa, ya), *v.p(xb, yb)), p["acc2"], None, 2.4, dash=(18, 8))
    # antenna e zona libera
    ant_y1 = f1["pads"][0]["pos"][1] - 1.2
    t.rett((*v.p(xa + 0.6, ya + 0.2), *v.p(xb - 0.6, ant_y1)), p["acc"], None, 2.0, dash=(10, 6))
    pa = v.p(bx, (ya + ant_y1) / 2)
    t.txt(pa, "ANTENNA", 34, p["acc"], "SemiBold", "m", "m", alone=p["bg2"])
    t.txt((pa[0], pa[1] + 40 * t.u), "nessun rame sotto", 24, p["acc"], "Light", "m", "m", alone=p["bg2"])
    # quote del corpo
    t.quota_h(v.p(xa, 0)[0], v.p(xb, 0)[0], v.p(0, ya)[1] - 120 * t.u, f"{virgola(W_, 1)} mm", v.p(0, ya)[1], v.p(0, ya)[1], p["acc2"])
    t.quota_v(v.p(0, ya)[1], v.p(0, yb)[1], v.p(xb, 0)[0] + 110 * t.u, f"{virgola(L, 1)} mm", v.p(xb, 0)[0], v.p(xb, 0)[0], p["acc2"])
    # passo dei pad (colonna sinistra)
    col = sorted([q for q in f1["pads"] if abs(q["pos"][0] - f1["pads"][0]["pos"][0]) < 0.06], key=lambda q: q["pos"][1])
    if len(col) >= 3:
        q1, q2 = col[2], col[3]
        xq = v.p(q1["pos"][0], 0)[0] - 60 * t.u
        t.quota_v(v.p(0, q1["pos"][1])[1], v.p(0, q2["pos"][1])[1], xq, "1,27", xq + 50 * t.u, xq + 50 * t.u, p["acc"], px=26, lato=-1)
    pad1 = f1["pads"][0]
    X, Y = v.p(*pad1["pos"])
    t.cerchio((X, Y), 28 * t.u, p["acc"], None, 2.4)
    t.txt((X - 44 * t.u, Y), "1", 30, p["acc"], "SemiBold", "r", "m", alone=p["bg2"])
    t.txt((t.W / 2, vv.y0 + reg[3] * sp + 64 * t.u), "PASSO PAD 1,27 mm  ·  PAD 1 IN ALTO A SINISTRA", 26, p["txt"], "Light", "m")
    t.cornice("MODULO  E73", "Antenna e ingombro", "ca. 3:1")


def s06(t, tag, prog):
    p = t.pal
    d = tag.dati()
    r1, f1 = fp_per_valore(d, "E73")
    L, W_, H_ = modello_e73(tag)
    pads = f1["pads"]
    xmin, xmax = min(q["pos"][0] for q in pads), max(q["pos"][0] for q in pads)
    ymin, ymax = min(q["pos"][1] for q in pads), max(q["pos"][1] for q in pads)
    sp = 500 * t.u / (xmax - xmin)
    cx = t.W / 2
    cy = t.y_min + 120 * t.u + (ymax - ymin) * sp / 2 + 40 * t.u
    mx, my = (xmin + xmax) / 2, (ymin + ymax) / 2
    P = lambda q: (cx + (q[0] - mx) * sp, cy + (q[1] - my) * sp)
    bx, by = f1["pos"]
    xa, xb, ya, yb = bx - W_ / 2, bx + W_ / 2, by - L / 2, by + L / 2
    A, B = P((xa, ya)), P((xb, yb))
    t.rett((A[0], A[1], B[0], B[1]), p["line"], p["bg1"] if p["tipo"] != "carta" else None, 2.4)
    t.rett((A[0] + 8 * t.u, A[1] + 8 * t.u, B[0] - 8 * t.u, A[1] + (ymin - ya) * sp - 30 * t.u), p["acc"], None, 1.4, dash=(10, 6))
    t.txt((cx, A[1] + 56 * t.u), "ANTENNA", 28, p["acc"], "SemiBold", "m", "m")
    for q in pads:
        X, Y = P(q["pos"])
        orient = orient_pad(f1, q)
        nm = nome_rete(q) or "-"
        etichetta = f"{q['n']}  {nm}" if nm else q["n"]
        gnd = nm.upper() == "GND"
        col = p["faint"] if gnd else p["acc"]
        # quadratino piazzola
        t.rett((X - 6 * t.u, Y - 6 * t.u, X + 6 * t.u, Y + 6 * t.u), p["line"], p["line"], 1.0)
        if orient == "col":
            if q["pos"][0] < mx:
                t.linea((X - 8 * t.u, Y), (X - 40 * t.u, Y), p["faint"], 1.0)
                t.txt((X - 46 * t.u, Y), etichetta, 24, col, "SemiBold" if not gnd else "Light", "r", "m")
            else:
                t.linea((X + 8 * t.u, Y), (X + 40 * t.u, Y), p["faint"], 1.0)
                t.txt((X + 46 * t.u, Y), etichetta, 24, col, "SemiBold" if not gnd else "Light", "l", "m")
        else:
            ymax_riga = max(a["pos"][1] for a in pads)
            if q["pos"][1] >= ymax_riga - 0.3:
                t.linea((X, Y + 8 * t.u), (X, Y + 36 * t.u), p["faint"], 1.0)
                t.txt((X, Y + 44 * t.u), etichetta, 24, col, "SemiBold" if not gnd else "Light", "r", "m", ang=90)
            elif q["pos"][1] > my - 1:
                t.linea((X, Y - 8 * t.u), (X, Y - 36 * t.u), p["faint"], 1.0)
                t.txt((X, Y - 44 * t.u), etichetta, 24, col, "SemiBold" if not gnd else "Light", "l", "m", ang=90)
    t.txt((cx, B[1] + 330 * t.u), "I pad centrali interni non sono etichettati", 24, p["faint"], "Light", "m")
    t.cornice("MODULO  E73", "Piedinatura (pad - rete)", "n.s.")


def s07(t, tag, prog):
    p = t.pal
    d = tag.dati()
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.575, 860 * t.u)
    t.griglia(2.54 * v.s, v.x0, v.y0)
    st = [("contorno", (12, 78, 62), 0.95), ("pieno:F_Cu", p["line"], 1.0), ("pieno:Edge_Cuts", p["acc"], 1.0)]
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, st))
    wmm, hmm = tag.mm
    t.quota_h(v.x0, v.x0 + wmm * v.s, v.y0 + hmm * v.s + 80 * t.u, f"{virgola(d['w'] - 0.1)} mm", v.y0 + hmm * v.s, v.y0 + hmm * v.s, p["acc"])
    t.quota_v(v.y0, v.y0 + hmm * v.s, v.x0 + wmm * v.s + 80 * t.u, f"{virgola(d['h'] - 0.1)} mm", v.x0 + wmm * v.s, v.x0 + wmm * v.s, p["acc"])
    # nomi sulle piazzole della batteria
    j = d["fps"]["J1"]
    for i_, q in enumerate(j["pads"]):
        X, Y = v.p(*q["pos"])
        yb_ = v.y0 + hmm * v.s + 160 * t.u + i_ * 52 * t.u
        t.cerchio((X, Y), 14 * t.u, p["acc2"], None, 2.0)
        t.linea((X, Y + 14 * t.u), (X, yb_), p["acc2"], 1.4)
        t.linea((X, yb_), (X + 24 * t.u, yb_), p["acc2"], 1.4)
        t.txt((X + 32 * t.u, yb_), f"J1-{q['n']}  {nome_rete(q)}", 28, p["acc2"], "SemiBold", "l", "m")
    t.txt((v.x0, v.y0 - 28 * t.u), "STRATO F.Cu  ·  VISTA DALL'ALTO", 28, p["acc"], "SemiBold")
    t.cornice("RAME  SUPERIORE", "F.Cu", "ca. 1:1")


def s08(t, tag, prog):
    p = t.pal
    d = tag.dati()
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.58, 720 * t.u, specchio=True)
    wmm, hmm = tag.mm
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=40)
    st = [("contorno", p["faint"], 0.16), ("piste:B_Cu", p["line"], 1.0), ("pieno:Edge_Cuts", p["line"], 1.0)]
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, st, specchio=True))
    tps = [(r, f) for r, f in d["fps"].items() if r.startswith("TP")]
    voci = []
    for ref, f in tps:
        X, Y = v.p(*f["pos"])
        t.cerchio((X, Y), 12 * t.u, p["acc"], None, 2.2)
        voci.append((X, Y, f"{ref}  {nome_rete(f['pads'][0])}"))
    etichette_righe(t, voci, 28, p["acc"])
    t.quota_h(v.x0, v.x0 + wmm * v.s, v.y0 + hmm * v.s + 80 * t.u, f"{virgola(d['w'] - 0.1)} mm", v.y0 + hmm * v.s, v.y0 + hmm * v.s)
    t.txt((v.x0, v.y0 - 28 * t.u), "STRATO B.Cu  ·  VISTA DA SOTTO (SPECCHIO)", 26, p["acc"], "SemiBold")
    t.cornice("RAME  INFERIORE", "B.Cu  ·  piazzole di servizio", "ca. 1:1")


def s09(t, tag, prog):
    p = t.pal
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.58, 860 * t.u)
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=60)
    st = [("contorno", p["faint"], 0.08), ("pieno:F_Mask", p["acc2"], 0.55), ("pieno:F_SilkS", p["line"], 1.0), ("pieno:Edge_Cuts", p["line"], 1.0)]
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, st))
    wmm, hmm = tag.mm
    d = tag.dati()
    t.quota_h(v.x0, v.x0 + wmm * v.s, v.y0 + hmm * v.s + 80 * t.u, f"{virgola(d['w'] - 0.1)} mm", v.y0 + hmm * v.s, v.y0 + hmm * v.s)
    # legenda
    y = v.y0 - 70 * t.u
    t.rett((v.x0, y - 22 * t.u, v.x0 + 34 * t.u, y + 6 * t.u), p["acc2"], p["acc2"], 1.0)
    t.txt((v.x0 + 48 * t.u, y), "APERTURE DELLA MASCHERA", 26, p["txt"], "Light")
    t.linea((v.x0 + 520 * t.u, y - 8 * t.u), (v.x0 + 556 * t.u, y - 8 * t.u), p["line"], 3.0)
    t.txt((v.x0 + 568 * t.u, y), "SERIGRAFIA", 26, p["txt"], "Light")
    t.cornice("MASCHERA  E  SERIGRAFIA", "F.Mask  ·  F.SilkS", "ca. 1:1")


def s10(t, tag, prog):
    p = t.pal
    wmm, hmm = tag.mm
    w = 470 * t.u
    s = w / wmm
    celle = [("F.Cu", "pieno:F_Cu", p["line"]), ("B.Cu", "pieno:B_Cu", p["acc2"]), ("F.Mask", "pieno:F_Mask", p["faint"]), ("F.SilkS", "pieno:F_SilkS", p["acc"])]
    y1_ = t.y_min + hmm * s / 2 + 30 * t.u
    y2_ = y1_ + hmm * s + 120 * t.u
    pos = [(t.W * 0.285, y1_), (t.W * 0.715, y1_), (t.W * 0.285, y2_), (t.W * 0.715, y2_)]
    for (nome, chiave, col), (cx, cy) in zip(celle, pos):
        v = Vista(cx, cy, wmm, hmm, s)
        t.rett((v.x0 - 6 * t.u, v.y0 - 6 * t.u, v.x0 + w + 6 * t.u, v.y0 + hmm * s + 6 * t.u), p["faint"], None, 1.0, dash=(10, 6))
        metti_arte(t, v, tag.arte((0, 0, *tag.mm), s, [("contorno", (12, 78, 62), 0.9), (chiave, col, 1.0), ("pieno:Edge_Cuts", p["acc"], 1.0)]))
        t.txt((cx, v.y0 + hmm * s + 40 * t.u), nome, 30, p["txt"], "SemiBold", "m")
    t.cornice("I  QUATTRO  STRATI", "F.Cu · B.Cu · maschera · serigrafia", "ca. 1:2")


def s11(t, tag, prog):
    p = t.pal
    d = tag.dati()
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.575, 780 * t.u)
    wmm, hmm = tag.mm
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=60)
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, [("contorno", p["faint"], 0.07), ("piste:F_Cu", p["faint"], 0.55), ("piste:B_Cu", p["faint"], 0.35), ("pieno:Edge_Cuts", p["line"], 1.0)]))
    conta = {}
    for via in d["vias"]:
        key = ("VIA", via["drill"])
        conta[key] = conta.get(key, 0) + 1
        X, Y = v.p(*via["pos"])
        t.cerchio((X, Y), 7 * t.u, p["acc"], None, 2.0)
        t.linea((X - 12 * t.u, Y), (X + 12 * t.u, Y), p["acc"], 1.0)
        t.linea((X, Y - 12 * t.u), (X, Y + 12 * t.u), p["acc"], 1.0)
    for ref, f in d["fps"].items():
        for q in f["pads"]:
            if q["drill"] > 0:
                key = ("FORO", q["drill"])
                conta[key] = conta.get(key, 0) + 1
                X, Y = v.p(*q["pos"])
                t.cerchio((X, Y), 9 * t.u, p["acc2"], None, 2.0)
    righe = [["SIMBOLO", "TIPO", "Ø mm", "Q.TA"]]
    for (tipo, dr), n in sorted(conta.items()):
        righe.append(["+" if tipo == "VIA" else "o", "via" if tipo == "VIA" else "foro", virgola(dr, 2), str(n)])
    if len(righe) == 1:
        righe.append(["-", "nessun foro", "-", "0"])
    ty = v.y0 + hmm * v.s + 80 * t.u
    tabella(t, (t.W - 560 * t.u) / 2, ty, righe, [150, 140, 150, 120], 28, 46)
    t.txt((v.x0, v.y0 - 28 * t.u), "MAPPA FORI  ·  via e fori passanti", 28, p["line"], "SemiBold")
    t.cornice("MAPPA  FORI", "Foratura e via", "ca. 1:1")


def s12(t, tag, prog):
    """Due ingrandimenti rettangolari: caricatore BQ25101 con il LED e connettore della cella con il diodo."""
    p = t.pal
    d = tag.dati()
    fps = d["fps"]
    wmm, hmm = tag.mm
    v = vista_scheda(t, tag, t.W / 2, t.y_min + 210 * t.u, 300 * t.u)
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=34)
    st = stili_strati(p)
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, st))
    gruppi = [("A", "CARICATORE  U4 BQ25101", ["U4", "D1", "R1"]), ("B", "CELLA  J1  E  DIODO  D2", ["J1", "D2"])]
    gruppi = [g for g in gruppi if all(r in fps for r in g[2])]
    fx0, fx1 = 80 * t.u, t.W - 80 * t.u
    top1 = v.y0 + hmm * v.s + 170 * t.u
    h = (t.y_max - top1 - 150 * t.u) / 2
    for gi, (lett, titolo, refs) in enumerate(gruppi):
        fy0 = top1 + 50 * t.u + gi * (h + 100 * t.u)
        fy1 = fy0 + h
        x0 = min(fps[r]["x0"] for r in refs) - 1.2
        y0 = min(fps[r]["y0"] for r in refs) - 1.2
        x1 = max(fps[r]["x0"] + fps[r]["w"] for r in refs) + 1.2
        y1 = max(fps[r]["y0"] + fps[r]["h"] for r in refs) + 1.2
        fw, fh = fx1 - fx0, fy1 - fy0
        sp = min(min(fw / (x1 - x0), fh / (y1 - y0)), 120 * t.u)
        rw, rh = fw / sp, fh / sp
        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
        rx0 = max(-0.2, min(cxm - rw / 2, wmm + 0.2 - rw))
        ry0 = max(-0.2, min(cym - rh / 2, hmm + 0.2 - rh))
        reg = (rx0, ry0, rw, rh)
        A, B = v.p(x0, y0), v.p(x1, y1)
        t.rett((A[0], A[1], B[0], B[1]), p["acc2"], None, 2.4)
        t.cerchio((A[0] - 4 * t.u, A[1] - 4 * t.u), 20 * t.u, p["line"], p["bg2"], 2.0)
        t.txt((A[0] - 4 * t.u, A[1] - 4 * t.u), lett, 24, p["line"], "SemiBold", "m", "m")
        img = tag.arte(reg, sp, st)
        base = Image.new("RGBA", img.size, tuple(p["bg2"]) + (255,))
        t.incolla(Image.alpha_composite(base, img), fx0, fy0)
        t.rett((fx0, fy0, fx1, fy1), p["line"], None, 3.0)
        t.rett((fx0 - 8 * t.u, fy0 - 8 * t.u, fx1 + 8 * t.u, fy1 + 8 * t.u), p["line"], None, 1.0)
        P = lambda x, y, fx0=fx0, fy0=fy0, reg=reg, sp=sp: (fx0 + (x - reg[0]) * sp, fy0 + (y - reg[1]) * sp)
        for r in refs:
            fp = fps[r]
            if fp["val"].upper().startswith("BQ25"):
                continue                      # le sfere a 0,4 mm sono nel foglio 4 (dettaglio C)
            for q in fp["pads"]:
                X, Y = P(*q["pos"])
                nm = nome_rete(q)
                if nm:
                    t.txt((X, Y), nm, 24, p["acc"], "SemiBold", "m", "m", alone=p["bg2"])
        for r in refs:
            fp = fps[r]
            a, b = P(fp["x0"], fp["y0"]), P(fp["x0"] + fp["w"], fp["y0"] + fp["h"])
            t.rett((a[0] - 6 * t.u, a[1] - 6 * t.u, b[0] + 6 * t.u, b[1] + 6 * t.u), p["acc2"], None, 2.0, dash=(12, 7))
            t.txt((a[0], a[1] - 16 * t.u), f"{r}  {funzione(fp['val'])}", 28, p["acc2"], "SemiBold", "l", alone=p["bg2"])
        t.txt((fx0, fy0 - 20 * t.u), f"{lett}   {titolo}", 28, p["line"], "SemiBold", "l")
        t.txt((fx1, fy0 - 20 * t.u), f"{virgola(rw, 1)} x {virgola(rh, 1)} mm", 24, p["faint"], "Regular", "r")
    t.cornice("ZONA  CARICA", "Caricatore, cella, diodo e LED", "vari")


def s13(t, tag, prog):
    p = t.pal
    d = tag.dati()
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.585, 600 * t.u)
    wmm, hmm = tag.mm
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=46)
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, stili_strati(p)))
    t.cerchio((v.x0, v.y0), 14 * t.u, p["acc"], None, 2.2)
    t.linea((v.x0 - 24 * t.u, v.y0), (v.x0 + 24 * t.u, v.y0), p["acc"], 1.4)
    t.linea((v.x0, v.y0 - 24 * t.u), (v.x0, v.y0 + 24 * t.u), p["acc"], 1.4)
    t.txt((v.x0 - 20 * t.u, v.y0 - 22 * t.u), "0 , 0", 24, p["acc"], "SemiBold", "r")
    sel = [(r, f) for r, f in d["fps"].items() if f["side"] == "F" and r[0] in "UJD" and not r.startswith("TP")]
    # catena X in alto: una linea di quota, testi verticali distribuiti
    sel.sort(key=lambda a: a[1]["pos"][0])
    yd = v.y0 - 70 * t.u
    t.linea((v.x0, yd), (v.x0 + wmm * v.s, yd), p["acc2"], 1.2)
    xs = [v.p(*f["pos"])[0] for _, f in sel]
    sep = 38 * t.u
    xt = list(xs)
    for _ in range(80):
        for i in range(1, len(xt)):
            if xt[i] - xt[i - 1] < sep:
                m = (xt[i] + xt[i - 1]) / 2
                xt[i - 1], xt[i] = m - sep / 2, m + sep / 2
    for (ref, f), X, xx in zip(sel, xs, xt):
        Y = v.p(*f["pos"])[1]
        t.linea((X, Y), (X, yd), p["faint"], 1.0, (6, 5))
        t.cerchio((X, Y), 6 * t.u, riempi=p["acc2"])
        t.linea((X, yd), (xx, yd - 22 * t.u), p["acc2"], 1.2)
        t.txt((xx, yd - 30 * t.u), f"{ref}  {virgola(f['pos'][0])}", 24, p["txt"], "Regular", "l", "m", ang=90)
    # catena Y a destra
    sel.sort(key=lambda a: a[1]["pos"][1])
    xd = v.x0 + wmm * v.s + 60 * t.u
    t.linea((xd, v.y0), (xd, v.y0 + hmm * v.s), p["acc"], 1.2)
    ys = [v.p(*f["pos"])[1] for _, f in sel]
    yt = list(ys)
    for _ in range(80):
        for i in range(1, len(yt)):
            if yt[i] - yt[i - 1] < 40 * t.u:
                m = (yt[i] + yt[i - 1]) / 2
                yt[i - 1], yt[i] = m - 20 * t.u, m + 20 * t.u
    for (ref, f), Y, yy in zip(sel, ys, yt):
        X = v.p(*f["pos"])[0]
        t.linea((X, Y), (xd, Y), p["faint"], 1.0, (6, 5))
        t.linea((xd, Y), (xd + 26 * t.u, yy), p["acc"], 1.2)
        t.txt((xd + 34 * t.u, yy), f"{ref}  {virgola(f['pos'][1])}", 24, p["txt"], "Regular", "l", "m")
    t.quota_h(v.x0, v.x0 + wmm * v.s, v.y0 + hmm * v.s + 70 * t.u, f"{virgola(d['w'] - 0.1)} mm", v.y0 + hmm * v.s, v.y0 + hmm * v.s)
    t.cornice("QUOTE  DI  POSIZIONE", "Centri dei componenti dall'angolo 0,0", "ca. 1:1")


def s14(t, tag, prog):
    p = t.pal
    d = tag.dati()
    wmm, hmm = tag.mm
    v = vista_scheda(t, tag, t.W / 2, t.H * 0.575, 620 * t.u, specchio=True)
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=40)
    st = [("contorno", p["faint"], 0.15), ("pieno:Edge_Cuts", p["line"], 1.0)]
    metti_arte(t, v, tag.arte((0, 0, *tag.mm), v.s, st, specchio=True))
    tps = [(r, f) for r, f in d["fps"].items() if r.startswith("TP")]
    voci = []
    for ref, f in tps:
        q = f["pads"][0]
        X, Y = v.p(*q["pos"])
        rad = q["w"] / 2 * v.s
        t.cerchio((X, Y), rad, p["acc"], p["acc"] if p["tipo"] == "carta" else None, 2.4)
        voci.append((X, Y + (rad if True else 0) * 0, f"{ref}  {nome_rete(q)}"))
    etichette_righe(t, [(X, Y, tx) for X, Y, tx in voci], 28, p["acc"])
    # quote tra due piazzole con la stessa x e tra due con la stessa y
    tps.sort(key=lambda a: (round(a[1]["pos"][0], 1), a[1]["pos"][1]))
    fatte = 0
    for i in range(len(tps) - 1):
        a, b = tps[i][1]["pads"][0]["pos"], tps[i + 1][1]["pads"][0]["pos"]
        if abs(a[0] - b[0]) < 0.05 and fatte < 1:
            A, B = v.p(*a), v.p(*b)
            xq = A[0] + (-1 if A[0] < t.W / 2 else 1) * 110 * t.u
            t.quota_v(A[1], B[1], xq, virgola(abs(b[1] - a[1])), xq, xq, p["line"], px=26, lato=1)
            fatte += 1
    t.quota_h(v.x0, v.x0 + wmm * v.s, v.y0 + hmm * v.s + 80 * t.u, f"{virgola(d['w'] - 0.1)} mm", v.y0 + hmm * v.s, v.y0 + hmm * v.s)
    t.txt((v.x0, v.y0 - 28 * t.u), "VISTA DA SOTTO  ·  piazzole del tag", 26, p["acc"], "SemiBold")
    t.cornice("PIAZZOLE  DI  SERVIZIO", "SWD e carica (TP1-TP7)", "ca. 1:1")


def s15(t, tag, prog):
    p = t.pal
    ia = linee_render(tag.render("alto"), p["line"], 20, 3)
    fr = linee_render(tag.render("fronte"), p["line"], 18, 3)
    la = linee_render(tag.render("lato"), p["line"], 18, 3)
    ia, fr, la = ritaglia(ia), ritaglia(fr), ritaglia(la)
    # stessa scala: il lato e il fronte sono ortografici con stesso zoom del piano. Scalo con il rapporto tra le dimensioni reali
    wmm, hmm = tag.mm
    d = tag.dati()
    k = 600 * t.u / wmm
    def rid(img, wm=None, hm=None):
        return img.resize((max(1, int(wm * k)), max(1, int(hm * k))), Image.LANCZOS)
    L, W_, H_ = modello_e73(tag)
    hz = d["spessore"] + H_
    A = rid(ia, wmm, hmm)
    F = rid(fr, wmm, hz)
    S = rid(la, hmm, hz).rotate(90, expand=True)         # lato sinistro: lunghezza in verticale
    tot = A.width + 90 * t.u + S.width
    xa = (t.W - tot) / 2 + 40 * t.u
    ya = t.y_min + 110 * t.u
    xs_ = xa + A.width + 90 * t.u
    t.incolla(A, xa, ya)
    t.incolla(S, xs_, ya)
    yf = ya + A.height + 110 * t.u
    t.incolla(F, xa, yf)
    # quote
    t.quota_v(ya, ya + A.height, xa - 56 * t.u, f"{virgola(hmm)}", xa, xa, px=26, lato=-1)
    t.quota_h(xa, xa + A.width, yf + F.height + 56 * t.u, f"{virgola(wmm)}", yf + F.height, yf + F.height, px=26, sopra=False)
    t.quota_v(yf, yf + F.height, xa - 56 * t.u, f"{virgola(hz, 1)}", xa, xa, px=26, lato=-1)
    t.quota_h(xs_, xs_ + S.width, ya + A.height + 56 * t.u, f"{virgola(hz, 1)}", ya + A.height, ya + A.height, px=26, sopra=False)
    t.txt((xa, ya - 18 * t.u), "PIANTA", 26, p["acc2"], "SemiBold")
    t.txt((xa, yf - 18 * t.u), "FRONTE", 26, p["acc2"], "SemiBold")
    t.txt((xs_, ya - 18 * t.u), "LATO SX", 26, p["acc2"], "SemiBold")
    # linee di proiezione tratteggiate
    t.linea((xa, ya + A.height), (xa, yf), p["faint"], 1.0, (8, 6))
    t.linea((xa + A.width, ya + A.height), (xa + A.width, yf), p["faint"], 1.0, (8, 6))
    t.linea((xa + A.width, ya), (xs_, ya), p["faint"], 1.0, (8, 6))
    t.linea((xa + A.width, ya + A.height), (xs_, ya + A.height), p["faint"], 1.0, (8, 6))
    t.cornice("TAG  v0.5", "Tre viste ortogonali (a linee)", "n.s.")


def s16(t, tag, prog):
    p = t.pal
    d = tag.dati()
    im = ritaglia(linee_render(tag.render("iso"), p["line"], 20, 3))
    im = adatta(im, 880 * t.u, 700 * t.u)
    t.incolla_centro(im, t.W / 2, t.y_min + 340 * t.u)
    # distinta raggruppata per valore
    gruppi = {}
    for r, f in d["fps"].items():
        if r.startswith("TP"):
            continue
        gruppi.setdefault((f["val"], f["fpid"].split(":")[-1]), []).append(r)
    righe = [["SIGLE", "VALORE", "Q.TA"]]
    def ordina(x):
        return (0 if x[1][0][0] in "UJ" else 1, x[1][0])
    for (val, fpid), refs in sorted(gruppi.items(), key=ordina):
        sig = ",".join(sorted(refs, key=lambda s: (s[0], int(re.sub(r"\D", "", s) or 0))))
        if len(sig) > 15:
            sig = sig[:13] + "..."
        righe.append([sig, val.replace(".", ","), str(len(refs))])
    righe = righe[:14]
    tabella(t, (t.W - 880 * t.u) / 2, t.y_min + 740 * t.u, righe, [250, 520, 110], 28, 48)
    t.cornice("TAG  v0.5", "Isometrica e distinta", "n.s.")


def s17(t, tag, prog):
    p = t.pal
    d = prog.dati()
    wmm, hmm = prog.mm if hasattr(prog, "mm") else (prog.strati() and prog.mm)
    hmax = (t.y_max - t.y_min) - 200 * t.u
    larg = min(880 * t.u, hmax * wmm / hmm)
    v = vista_scheda(t, prog, t.W / 2, (t.y_min + t.y_max) / 2 + 20 * t.u, larg)
    t.griglia(2.54 * v.s, v.x0, v.y0, alfa=40)
    st = [("contorno", p["faint"], 0.22), ("piste:B_Cu", p["line"], 1.0), ("piste:F_Cu", p["line"], 1.0), ("pieno:F_SilkS", p["acc"], 0.9), ("pieno:Edge_Cuts", p["line"], 1.0)]
    metti_arte(t, v, prog.arte((0, 0, *prog.mm), v.s, st))
    voci = []
    for r in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
        f = d["fps"].get(r)
        if not f:
            continue
        q = f["pads"][0]
        X, Y = v.p(*q["pos"])
        nm = nome_rete(q).replace("_T", "").replace("_C", "")
        t.cerchio((X, Y), 15 * t.u, p["acc"], None, 2.0)
        voci.append((X, Y, f"{r}  {nm}"))
    etichette_righe(t, voci, 26, p["acc"])
    t.quota_h(v.x0, v.x0 + wmm * v.s, v.y0 + hmm * v.s + 70 * t.u, f"{virgola(wmm)} mm", v.y0 + hmm * v.s, v.y0 + hmm * v.s)
    t.quota_v(v.y0, v.y0 + hmm * v.s, v.x0 - 80 * t.u, f"{virgola(hmm)} mm", v.x0, v.x0, lato=-1)
    t.cornice("PROGRAMMATORE", "Pianta  ·  pogo pin e foratura", "n.s.")


def s18(t, tag, prog):
    p = t.pal
    d = prog.dati()
    prog.strati()
    pog = [d["fps"][r] for r in ("P1", "P2", "P3", "P4", "P5", "P6", "P7") if r in d["fps"]]
    if not pog:
        return
    xs = [f["pos"][0] for f in pog]
    ys = [f["pos"][1] for f in pog]
    cx_mm, cy_mm = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    Wm = max(xs) - min(xs) + 9.0
    Hm = max(ys) - min(ys) + 9.0
    sp = min((t.W - 220 * t.u) / Wm, (t.y_max - t.y_min - 240 * t.u) / Hm)
    cx, cy = t.W / 2, (t.y_min + t.y_max) / 2
    reg = (cx_mm - Wm / 2, cy_mm - Hm / 2, Wm, Hm)
    img = prog.arte(reg, sp, [("contorno", (12, 78, 62), 0.9), ("pieno:B_Cu", p["line"], 1.0), ("pieno:F_Cu", p["line"], 1.0), ("pieno:F_SilkS", p["txt"], 0.9), ("pieno:Edge_Cuts", p["acc"], 1.0)])
    x0, y0 = cx - img.width / 2, cy - img.height / 2
    t.griglia(2.54 * sp, x0 - reg[0] * sp, y0 - reg[1] * sp, alfa=44)
    t.incolla(img, x0, y0)
    P = lambda x, y: (x0 + (x - reg[0]) * sp, y0 + (y - reg[1]) * sp)
    for f in pog:
        q = f["pads"][0]
        X, Y = P(*q["pos"])
        nm = nome_rete(q).replace("_T", "").replace("_C", "")
        t.cerchio((X, Y), 1.9 * sp, p["acc"], None, 2.4, dash=(10, 5))
        t.txt((X, Y - 2.6 * sp), nm, 30, p["acc"], "SemiBold", "m", "m", alone=(4, 24, 22))
        t.txt((X, Y + 2.6 * sp), f["val"].split("(")[0].strip()[:0] or "", 20, p["txt"], "Light", "m", "m")
    fila = sorted([f for f in pog if abs(f["pos"][1] - pog[0]["pos"][1]) < 0.1], key=lambda f: f["pos"][0])
    if len(fila) >= 2:
        a, b = P(*fila[0]["pads"][0]["pos"]), P(*fila[1]["pads"][0]["pos"])
        yq = a[1] - 5.2 * sp
        t.quota_h(a[0], b[0], yq, virgola(abs(fila[1]["pos"][0] - fila[0]["pos"][0])) + " mm", a[1] - 3.0 * sp, a[1] - 3.0 * sp, p["acc2"], px=28)
    t.txt((x0 + img.width, y0 - 24 * t.u), "7 POGO PIN  ·  vista dall'alto", 28, p["acc"], "SemiBold", "r")
    t.cornice("PROGRAMMATORE", "Zona dei 7 pogo pin", "ca. 4:1")


def s19(t, tag, prog):
    p = t.pal
    d = prog.dati()
    k = 7.8 * t.u
    pw, ph = 85.0, 56.0
    pi = Image.new("RGBA", (int(pw * k), int(ph * k)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(pi)
    lw = t.w(2.4)
    dd.rounded_rectangle([0, 0, pi.width - 1, pi.height - 1], int(3 * k), fill=tuple(p["faint"]) + (50,), outline=tuple(p["line"]) + (255,), width=lw)
    holes = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
    for (hx, hy) in holes:
        r = 1.35 * k
        dd.ellipse([hx * k - r, hy * k - r, hx * k + r, hy * k + r], outline=tuple(p["line"]) + (255,), width=lw)
    j1 = d["fps"]["J1"]
    pins = [q["pos"] for q in j1["pads"]]
    ys = sorted({round(q[1], 2) for q in pins})
    xmin, xmax = min(q[0] for q in pins), max(q[0] for q in pins)
    pos_header = [(xmin + i * 2.54, y) for i in range(20) for y in (ys[0], ys[0] + 2.54)]
    dd.rectangle([(xmin - 1.3) * k, (ys[0] - 1.3) * k, (xmin + 19 * 2.54 + 1.3) * k, (ys[0] + 2.54 + 1.3) * k], outline=tuple(p["acc"]) + (255,), width=lw)
    for (x, y) in pos_header:
        r = 0.45 * k
        dd.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=tuple(p["acc"]) + (255,))
    for (x1, y1, x2, y2) in ((66, 5, 85, 17), (66, 21, 85, 33), (66, 37, 85, 49)):
        dd.rectangle([x1 * k, y1 * k, x2 * k, y2 * k], outline=tuple(p["line"]) + (255,), width=lw)
    dd.rectangle([22 * k, 22 * k, 36 * k, 36 * k], outline=tuple(p["line"]) + (255,), width=lw)
    wmm, hmm = prog.mm
    hat = Image.alpha_composite(prog.arte((0, 0, wmm, hmm), k, [("contorno", p["acc2"], 0.16)]),
                                prog.arte((0, 0, wmm, hmm), k, [("pieno:B_Cu", p["acc2"], 1.0), ("pieno:F_Cu", p["acc2"], 1.0), ("pieno:Edge_Cuts", p["acc2"], 1.0)]))
    hd = ImageDraw.Draw(hat)
    for r_ in ("H1", "H2", "H3", "H4"):
        f_ = d["fps"].get(r_)
        if f_:
            X, Y = f_["pos"][0] * k, f_["pos"][1] * k
            hd.ellipse([X - 1.5 * k, Y - 1.5 * k, X + 1.5 * k, Y + 1.5 * k], outline=tuple(p["acc"]) + (255,), width=lw)
    ip, ih = iso(pi), iso(hat)
    cx = t.W / 2
    gap = 340 * t.u
    cy_pi = t.y_min + 520 * t.u + gap
    cy_h = cy_pi - gap
    org_pi = (cx - ip.width / 2, cy_pi - ip.height / 2)
    org_h = (org_pi[0] + (pi.height - hat.height) * C30, org_pi[1] - gap)
    t.incolla(ip, *org_pi)
    for (hx, hy) in holes:
        a = pt_iso(org_pi, pi.height, hx * k, hy * k)
        t.linea((a[0], a[1] + 120 * t.u), (a[0], a[1] - gap - 40 * t.u), p["acc"], 1.4, (22, 6, 4, 6))
    for (x, y) in (pos_header[0], pos_header[-1]):
        a = pt_iso(org_pi, pi.height, x * k, y * k)
        t.linea(a, (a[0], a[1] - gap), p["acc2"], 1.2, (8, 8))
    t.incolla(ih, *org_h)
    a1 = pt_iso(org_pi, pi.height, pos_header[0][0] * k, pos_header[0][1] * k)
    t.richiamo(a1, (60 * t.u, a1[1] + 60 * t.u), "HEADER 2x20 · passo 2,54 mm", 26, p["acc"], "l")
    a2 = pt_iso(org_pi, pi.height, 70 * k, 49 * k)
    t.richiamo(a2, (t.W - 60 * t.u, a2[1] + 90 * t.u), "RASPBERRY Pi 3 / 4 (generico)", 26, p["line"], "r")
    a3 = pt_iso(org_h, ih.height, wmm * k * 0.55, hmm * k * 0.45)
    t.richiamo(a3, (t.W - 60 * t.u, cy_h - 210 * t.u), "PROGRAMMATORE (HAT)", 26, p["acc2"], "r")
    t.txt((t.W / 2, t.y_max - 90 * t.u), f"{virgola(d['w'] - 0.1, 1)} x {virgola(d['h'] - 0.1, 1)} mm  ·  fori M2,5 a 58 x 49 mm", 26, p["txt"], "Light", "m")
    t.cornice("PROGRAMMATORE  HAT", "Esploso con linee d'asse", "n.s.")


def s20(t, tag, prog):
    p = t.pal
    d = prog.dati()
    prog.strati()
    wmm, hmm = prog.mm
    larg = min(800 * t.u, (t.y_max - t.y_min - 400 * t.u) * wmm / hmm)
    s = larg / wmm
    pw, ph = int(940 * t.u), int(hmm * s + 400 * t.u)
    foglio = Image.new("RGBA", (pw, ph), (247, 246, 240, 255))
    rng = np.random.default_rng(1)
    g = rng.normal(0, 3.2, (ph, pw)).astype(np.int16)
    arr = np.array(foglio.convert("RGB")).astype(np.int16) + g[:, :, None]
    foglio = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    rame = ImageChops.lighter(prog.arte((0, 0, wmm, hmm), s, [("pieno:F_Cu", (14, 14, 18), 1.0)]), prog.arte((0, 0, wmm, hmm), s, [("pieno:B_Cu", (14, 14, 18), 1.0)]))
    rame = rame.transpose(Image.FLIP_LEFT_RIGHT)
    layer = Image.new("RGBA", foglio.size, (0, 0, 0, 0))
    ox, oy = int((pw - rame.width) / 2), int(70 * t.u)
    layer.paste(rame, (ox, oy))
    foglio = Image.alpha_composite(foglio, layer)
    dd = ImageDraw.Draw(foglio)
    ink = (24, 28, 36, 255)
    x1, y1, x2, y2 = ox - 28 * t.u, oy - 28 * t.u, ox + rame.width + 28 * t.u, oy + rame.height + 28 * t.u
    for (x, y, sx, sy) in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        dd.line([x, y, x + sx * 34 * t.u, y], fill=ink, width=t.w(1.8))
        dd.line([x, y, x, y + sy * 34 * t.u], fill=ink, width=t.w(1.8))
    # barra di scala 20 mm
    yb = y2 + 60 * t.u
    dd.rectangle([ox, yb, ox + 20 * s, yb + 8 * t.u], fill=ink)
    for i in range(0, 21, 5):
        dd.line([ox + i * s, yb - 8 * t.u, ox + i * s, yb], fill=ink, width=t.w(1.4))
    f = font(26 * t.u, "Regular")
    dd.text((ox + 20 * s + 18 * t.u, yb + 8 * t.u), "20 mm", font=f, fill=ink, anchor="lm")
    dd.text((ox, yb + 50 * t.u), "STAMPA 1:1  ·  SPECCHIO  ·  TONER TRANSFER", font=font(24 * t.u, "Light"), fill=ink, anchor="ls")
    # tabella fori sul foglio
    fori = {}
    for r, fpd in d["fps"].items():
        for q in fpd["pads"]:
            if q["drill"] > 0:
                fori[q["drill"]] = fori.get(q["drill"], 0) + 1
    dd.text((ox, yb + 100 * t.u), "FORI:  " + "   ".join(f"{virgola(k_, 1)} mm x {n}" for k_, n in sorted(fori.items())), font=font(24 * t.u, "Light"), fill=ink, anchor="ls")
    foglio = foglio.rotate(2.2, expand=True, resample=Image.BICUBIC)
    # ombra e incollo
    a = Image.new("L", (foglio.width + 160, foglio.height + 160), 0)
    a.paste(foglio.getchannel("A").point(lambda v: int(v * 0.5)), (80, 80))
    sh = Image.new("RGBA", a.size, (0, 0, 0, 255))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(26 * t.u)))
    cx, cy = t.W / 2, (t.y_min + t.y_max) / 2
    # sul fondo carta l'ombra e' appena accennata
    t.incolla_centro(sh, cx + 12 * t.u, cy + 20 * t.u)
    t.incolla_centro(foglio, cx, cy)
    t.cornice("PROGRAMMATORE", "Foglio per il toner transfer", "1:1")


FUNZIONI = {1: s01, 2: s02, 3: s03, 4: s04, 5: s05, 6: s06, 7: s07, 8: s08, 9: s09, 10: s10, 11: s11, 12: s12, 13: s13,
            14: s14, 15: s15, 16: s16, 17: s17, 18: s18, 19: s19, 20: s20}
VISTE_TAG = {15: ["alto", "fronte", "lato"], 16: ["iso"]}


# ---------------------------------------------------------------- anteprima e principale
def anteprima(files, dest):
    n = len(files)
    cols = 5
    rows = math.ceil(n / cols)
    tw, th = 234, 506
    g = 14
    sheet = Image.new("RGB", (cols * (tw + g) + g, rows * (th + g) + g), (18, 20, 24))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS)
        x, y = g + (i % cols) * (tw + g), g + (i // cols) * (th + g)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 34, y + 26], fill=(0, 0, 0))
        d.text((x + 6, y + 4), f.name[:2], fill=(255, 255, 255), font=font(18, "Regular"))
    sheet.save(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=os.environ.get("SWIMTAG_PCB", REPO / "hardware/nrf52840/kicad/swimtag_economica.kicad_pcb"))
    ap.add_argument("--prog", default=os.environ.get("SWIMTAG_PROG_PCB", REPO / "hardware/programmatore/swimtag_programmatore.kicad_pcb"))
    ap.add_argument("--solo", type=int, nargs="*")
    ap.add_argument("--bozza", action="store_true")
    ap.add_argument("--forza", action="store_true", help="rifa i render 3D")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    numeri = a.solo or (BOZZA if a.bozza else [n for n, *_ in SOGGETTI])
    tag, prog = Scheda("tag", a.tag, a.forza), Scheda("programmatore", a.prog, a.forza)
    tag.prepara_render(sorted({v for n in numeri for v in VISTE_TAG.get(n, [])}))
    info = {n: (nome, stile) for n, nome, stile, _ in SOGGETTI}
    fatti = []
    for n in numeri:
        for W, H, tf in FORMATI:
            try:
                nome, stile = info[n]
                t = Tavola(W, H, stile, n, tag, prog)
                FUNZIONI[n](t, tag, prog)
                f = out / f"{n:02d}_{nome}_{tf}.png"
                t.finale(W, H).save(f, optimize=True)
                print("ok", f.name)
            except Exception as e:           # un foglio rotto non ferma gli altri
                import traceback
                traceback.print_exc()
                print(f"!! {n:02d} {info[n][0]} {tf}: {e}")
    dest = QUI / "anteprima.png" if a.out == str(OUT) else out / "anteprima.png"
    anteprima(sorted(out.glob("*_1170x2532.png")), dest)


if __name__ == "__main__":
    main()
