"""Immagine: dove saldare i fili della cella sul tag v0.5 (J1)."""
import sys

from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
X0, Y0 = 183, 205          # angolo della scheda nel render (px), tarato sulle piazzole di J1
sx, sy = 46.6, 46.1


def px(x, y):
    return X0 + x * sx, Y0 + y * sy


PIN_P = (1.50, 26.88)    # piazzola 1 = BAT_IN (+ cella)
PIN_N = (4.60, 25.62)    # piazzola 2 = GND (- cella)
C = (3.05, 26.25)

F = "C:/Windows/Fonts/bahnschrift.ttf"
f_t, f_b, f_s = (ImageFont.truetype(F, s) for s in (54, 34, 27))
render = Image.open(src).convert("RGBA")
W, H = 3000, 1600
im = Image.new("RGB", (W, H), (14, 28, 54))
d = ImageDraw.Draw(im)
im.paste(render, (40, 10), render)
d = ImageDraw.Draw(im)
off = (40, 10)


def P(p):
    x, y = px(*p)
    return x + off[0], y + off[1]


# riquadro sulla scheda
cx, cy = P(C)
r = 3.4 * sx
d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), 18, outline=(255, 200, 40), width=8)

# ingrandimento 4x
k = 3
bx0, by0 = px(C[0] - 3.4, C[1] - 3.4)
bx1, by1 = px(C[0] + 3.4, C[1] + 3.4)
crop = render.crop((int(bx0), int(by0), int(bx1), int(by1)))
zw = int((bx1 - bx0) * k)
crop = crop.resize((zw, zw), Image.LANCZOS)
ZX, ZY = 1420, 230
bg = Image.new("RGBA", crop.size, (230, 230, 230, 255))
bg.alpha_composite(crop)
im.paste(bg.convert("RGB"), (ZX, ZY))
d.rectangle((ZX, ZY, ZX + zw, ZY + zw), outline=(255, 200, 40), width=8)
d.line((cx + r, cy - r, ZX, ZY), fill=(255, 200, 40), width=4)
d.line((cx + r, cy + r, ZX, ZY + zw), fill=(255, 200, 40), width=4)


def Z(p):
    x, y = px(*p)
    return ZX + (x - bx0) * k, ZY + (y - by0) * k


for p, col, lab, dy in ((PIN_P, (230, 40, 40), "+  filo ROSSO (positivo)", 70), (PIN_N, (30, 30, 30), "-  filo NERO (negativo)", -70)):
    x, y = Z(p)
    d.ellipse((x - 34, y - 34, x + 34, y + 34), outline=col, width=10)
    tx, ty = ZX + zw + 40, y + dy - 20
    d.line((x + 34, y, tx - 10, ty + 20), fill=(255, 255, 255), width=4)
    d.rounded_rectangle((tx - 14, ty - 16, tx + 520, ty + 60), 12, fill=col if col[0] > 100 else (60, 60, 60))
    d.text((tx, ty), lab, font=f_b, fill=(255, 255, 255))

d.text((1420, 60), "Tag v0.5: dove saldare la cella (J1)", font=f_t, fill=(255, 255, 255))
d.text((1420, 140), "Vista dall'alto, scheda 21,59 x 28 mm, J1 in basso a sinistra", font=f_s, fill=(170, 200, 235))
note = [
    "1. Prima di saldare: col tester individua il + della cella.",
    "2. + della cella  ->  piazzola sinistra di J1, accanto al segno \"+\".",
    "3. - della cella  ->  piazzola destra di J1, accanto al segno \"-\".",
    "4. Saldatura rapida sui pin dell'header, poi accorciali (7,2 mm).",
    "5. Fissa i fili con una goccia di adesivo elastico.",
    "Con la cella invertita Q1 (AO3401A) blocca la corrente,",
    "ma controlla sempre la polarita prima di saldare.",
]
for i, s in enumerate(note):
    d.text((1420, 1250 + i * 52), s, font=f_s, fill=(235, 240, 250) if i < 5 else (255, 200, 40))
im.save(out)
print(out)
