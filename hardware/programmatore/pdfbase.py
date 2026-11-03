"""Utilita' per comporre il PDF: font, impaginazione a flusso, primitive di disegno in mm."""
import os
import fitz

MM = 72 / 25.4
A4 = (595.276, 841.89)
NERO, BIANCO = (0, 0, 0), (1, 1, 1)
GRIGIO, GRIGIO_CH = (0.45, 0.45, 0.45), (0.85, 0.85, 0.85)
ROSSO, VERDE, BLU, ARANCIO = (0.8, 0.05, 0.05), (0.05, 0.5, 0.15), (0.1, 0.25, 0.8), (0.9, 0.5, 0.0)
GIALLO = (1.0, 0.95, 0.6)


def _trova(nomi):
    for d in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/msttcorefonts", "/usr/share/fonts/truetype/dejavu",
              "/Library/Fonts", "/System/Library/Fonts/Supplemental"):
        for n in nomi:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


FILE_REG = _trova(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"])
FILE_BOLD = _trova(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"])
FILE_MONO = _trova(["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"])
FONT = {"r": fitz.Font(fontfile=FILE_REG) if FILE_REG else fitz.Font("helv"),
        "b": fitz.Font(fontfile=FILE_BOLD) if FILE_BOLD else fitz.Font("hebo"),
        "m": fitz.Font(fontfile=FILE_MONO) if FILE_MONO else fitz.Font("cour")}


def reg_font(page):
    for k, fn in (("r", FILE_REG), ("b", FILE_BOLD), ("m", FILE_MONO)):
        if fn:
            page.insert_font(fontname="F" + k, fontfile=fn)


def fname(k):
    ok = {"r": FILE_REG, "b": FILE_BOLD, "m": FILE_MONO}[k]
    return "F" + k if ok else {"r": "helv", "b": "hebo", "m": "cour"}[k]


def tl(s, size, k="r"):
    return FONT[k].text_length(s, fontsize=size)


def wrap(s, size, w, k="r"):
    righe = []
    for par in s.split("\n"):
        cur = ""
        for parola in par.split(" "):
            prova = (cur + " " + parola).strip()
            if tl(prova, size, k) <= w or not cur:
                cur = prova
            else:
                righe.append(cur)
                cur = parola
        righe.append(cur)
    return righe


def testo(page, x, y, s, size=9, k="r", col=NERO, ancora="s"):
    """Testo con base in (x,y) pt. ancora: 's' sinistra, 'c' centro, 'd' destra."""
    w = tl(s, size, k)
    if ancora == "c":
        x -= w / 2
    elif ancora == "d":
        x -= w
    page.insert_text((x, y), s, fontsize=size, fontname=fname(k), color=col)


def testo_speculare(page, x, y, s, size=9, k="b", col=NERO):
    """Testo specchiato orizzontalmente: parte da (x,y) e si estende verso sinistra."""
    page.insert_text((x, y), s, fontsize=size, fontname=fname(k), color=col, morph=(fitz.Point(x, y), fitz.Matrix(-1, 0, 0, 1, 0, 0)))


class Doc:
    def __init__(self, titolo_corrente=""):
        self.d = fitz.open()
        self.page = None
        self.y = 0
        self.titolo = titolo_corrente
        self.sez = []     # (titolo, pagina)
        self.marg = 42
        self.w = A4[0] - 2 * self.marg

    def nuova(self, titolo=None, voce=None):
        self.page = self.d.new_page(width=A4[0], height=A4[1])
        reg_font(self.page)
        if titolo is not None:
            self.titolo = titolo
        self.y = 52
        if voce:
            self.sez.append((voce, self.page.number + 1))
        return self.page

    def spazio_ok(self, h):
        if self.y + h > A4[1] - 50:
            self.nuova()
            return False
        return True

    def h1(self, t, voce=True):
        self.spazio_ok(40)
        if voce:
            self.sez.append((t, self.page.number + 1))
        testo(self.page, self.marg, self.y + 14, t, 17, "b", (0.05, 0.2, 0.45))
        self.page.draw_line((self.marg, self.y + 20), (A4[0] - self.marg, self.y + 20), color=(0.05, 0.2, 0.45), width=1)
        self.y += 34

    def h2(self, t):
        self.spazio_ok(30)
        testo(self.page, self.marg, self.y + 11, t, 11.5, "b", (0.1, 0.1, 0.1))
        self.y += 19

    def p(self, t, size=9.5, k="r", col=NERO, indent=0, gap=4, w=None):
        righe = wrap(t, size, (w or self.w) - indent, k)
        lh = size * 1.28
        for r in righe:
            self.spazio_ok(lh)
            testo(self.page, self.marg + indent, self.y + size, r, size, k, col)
            self.y += lh
        self.y += gap

    def li(self, t, size=9.5, liv=0, num=None):
        righe = wrap(t, size, self.w - 14 - 14 * liv)
        lh = size * 1.28
        for i, r in enumerate(righe):
            self.spazio_ok(lh)
            if i == 0:
                testo(self.page, self.marg + 3 + 14 * liv, self.y + size, num if num else "-", size, "b")
            testo(self.page, self.marg + 14 + 14 * liv, self.y + size, r, size)
            self.y += lh
        self.y += 2

    def codice(self, righe, size=8):
        lh = size * 1.3
        h = lh * len(righe) + 8
        self.spazio_ok(min(h, 300))
        # spezza in blocchi se non sta in pagina
        i = 0
        while i < len(righe):
            disp = int((A4[1] - 50 - self.y - 8) / lh)
            if disp < 2:
                self.nuova()
                continue
            blocco = righe[i:i + disp]
            hb = lh * len(blocco) + 8
            self.page.draw_rect(fitz.Rect(self.marg, self.y, self.marg + self.w, self.y + hb), color=(0.7, 0.7, 0.7),
                                fill=(0.95, 0.95, 0.95), width=0.5)
            for j, r in enumerate(blocco):
                testo(self.page, self.marg + 5, self.y + 4 + size + lh * j - 1, r, size, "m")
            self.y += hb + 4
            i += disp

    def riquadro(self, t, col=ROSSO, fill=(1, 0.9, 0.9), size=10.5, k="b"):
        righe = wrap(t, size, self.w - 20, k)
        lh = size * 1.3
        h = lh * len(righe) + 14
        self.spazio_ok(h)
        self.page.draw_rect(fitz.Rect(self.marg, self.y, self.marg + self.w, self.y + h), color=col, fill=fill, width=1.5)
        for j, r in enumerate(righe):
            testo(self.page, self.marg + 10, self.y + 8 + size + lh * j - 1, r, size, k, col)
        self.y += h + 6

    def tabella(self, intest, righe, larg, size=8.5):
        """larg: frazioni della larghezza utile."""
        tot = sum(larg)
        cw = [self.w * l / tot for l in larg]
        def altezza(r):
            return max(len(wrap(str(c), size, cw[i] - 6)) for i, c in enumerate(r)) * size * 1.25 + 5
        def riga(r, bold=False, fill=None):
            h = altezza(r)
            if self.y + h > A4[1] - 50:
                self.nuova()
            x = self.marg
            for i, c in enumerate(r):
                rc = fitz.Rect(x, self.y, x + cw[i], self.y + h)
                self.page.draw_rect(rc, color=(0.6, 0.6, 0.6), fill=fill, width=0.4)
                for j, ln in enumerate(wrap(str(c), size, cw[i] - 6, "b" if bold else "r")):
                    testo(self.page, x + 3, self.y + 3 + size + size * 1.25 * j - 1, ln, size, "b" if bold else "r")
                x += cw[i]
            self.y += h
        riga(intest, True, (0.85, 0.9, 0.97))
        for r in righe:
            riga(r)
        self.y += 8

    def figura(self, h, fn):
        """fn(page, x, y, w): disegna in un rettangolo alto h pt."""
        self.spazio_ok(h + 4)
        fn(self.page, self.marg, self.y, self.w)
        self.y += h + 6

    def piedi(self, nome):
        n = len(self.d)
        for i, pg in enumerate(self.d):
            testo(pg, self.marg, A4[1] - 24, nome, 7.5, "r", GRIGIO)
            testo(pg, A4[0] - self.marg, A4[1] - 24, f"pag. {i + 1} / {n}", 7.5, "r", GRIGIO, "d")


# ---- primitive di disegno in mm su una pagina ----
class Mappa:
    """Trasforma coordinate dell'adattatore (mm) in punti della pagina. s = punti per mm (MM = scala 1:1)."""

    def __init__(self, page, ox, oy, s=MM, x_min=0.0, y_min=0.0, mir_w=None):
        """mir_w: se dato (mm), l'asse x viene specchiato su una fascia larga mir_w (stampa speculare)."""
        self.pg, self.ox, self.oy, self.s, self.xm, self.ym, self.mw = page, ox, oy, s, x_min, y_min, mir_w

    def P(self, x, y):
        if self.mw is not None:
            return (self.ox + (self.mw - (x - self.xm)) * self.s, self.oy + (y - self.ym) * self.s)
        return (self.ox + (x - self.xm) * self.s, self.oy + (y - self.ym) * self.s)

    def L(self, a, b, col=NERO, w=0.3, dash=None, cap=0):
        self.pg.draw_line(self.P(*a), self.P(*b), color=col, width=w * self.s / MM if False else w * self.s, dashes=dash, lineCap=cap)

    def C(self, c, d, fill=NERO, col=None, w=0.2):
        self.pg.draw_circle(self.P(*c), d / 2 * self.s, color=col, fill=fill, width=w * self.s)

    def R(self, x0, y0, x1, y1, fill=None, col=NERO, w=0.2, dash=None):
        a, b = self.P(x0, y0), self.P(x1, y1)
        r = fitz.Rect(a, b)
        r.normalize()
        self.pg.draw_rect(r, color=col, fill=fill, width=w * self.s, dashes=dash)

    def OV(self, c, w, h, fill=NERO, col=None):
        """Piazzola ovale verticale: due cerchi e un rettangolo."""
        x, y = c
        r = w / 2
        self.R(x - r, y - h / 2 + r, x + r, y + h / 2 - r, fill=fill, col=None)
        self.C((x, y - h / 2 + r), w, fill=fill, col=col)
        self.C((x, y + h / 2 - r), w, fill=fill, col=col)

    def T(self, x, y, s, size=7, k="r", col=NERO, ancora="s"):
        px, py = self.P(x, y)
        if self.mw is not None:
            w = tl(s, size, k)
            px += {"s": 0, "c": w / 2, "d": w}[ancora]
            testo_speculare(self.pg, px, py, s, size, k, col)
            return
        testo(self.pg, px, py, s, size, k, col, ancora)
