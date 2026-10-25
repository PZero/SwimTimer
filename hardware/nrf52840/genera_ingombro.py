"""Genera ingombro.svg: pianta in scala (1 unità = 1 mm) delle disposizioni del tag nRF52840.

Misure dai datasheet: MDBT50Q-1MV2 10,5 x 15,5 x 2,05 mm con zona senza rame di 3,8 mm sotto
l'antenna su ogni strato; W25Q256JV WSON-8 8 x 6; LSM6DSV16X 2,5 x 3; MS5837 3,3 x 3,3 x 2,75;
BQ25100 1,6 x 0,9; cella 20 mAh ~3 x 10 x 12 (taglia tipica, da verificare); vibratore 6 x 2,7.
Uso: python genera_ingombro.py  (scrive ingombro.svg accanto allo script)
"""
from pathlib import Path

RESINA = 0.8  # parete di resina intorno alla scheda (mm)
out = []

# Stili scritti come attributi (non CSS) così l'SVG si vede uguale ovunque
ST = {
    "pcb": 'fill="#2e7d4f" stroke="#1b4d30" stroke-width="0.1"',
    "mod": 'fill="#b8bec6" stroke="#555555" stroke-width="0.1"',
    "ic": 'fill="#3a3a3a" stroke="#000000" stroke-width="0.05"',
    "pas": 'fill="#c9a66b" stroke="#7a5a2a" stroke-width="0.05"',
    "led": 'fill="#f5f5f5" stroke="#999999" stroke-width="0.05"',
    "keep": 'fill="#e74c3c" fill-opacity="0.3" stroke="#c0392b" stroke-width="0.12"',
    "cella": 'fill="#3478dc" fill-opacity="0.2" stroke="#2a62c9" stroke-width="0.15" stroke-dasharray="0.6 0.4"',
    "motore": 'fill="#e67e22" fill-opacity="0.2" stroke="#d35400" stroke-width="0.15" stroke-dasharray="0.6 0.4"',
    "sotto": 'fill="none" stroke="#d4a017" stroke-width="0.15" stroke-dasharray="0.4 0.3"',
    "resina": 'fill="#c8dcf0" fill-opacity="0.35" stroke="#7fa7c9" stroke-width="0.12" stroke-dasharray="0.3 0.3"',
    "resina2": 'fill="#dde9f3" stroke="#7fa7c9" stroke-width="0.08"',
    "t": 'fill="#222222" font-family="Arial, sans-serif"',
    "tw": 'fill="#ffffff" font-family="Arial, sans-serif"',
    "h": 'fill="#111111" font-family="Arial, sans-serif" font-weight="bold"',
}


def rect(x, y, w, h, cls, label="", fs=0.9):
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" {ST[cls]}/>')
    if label:
        out.append(f'<text x="{x + w / 2:.2f}" y="{y + h / 2 + fs * 0.35:.2f}" font-size="{fs}" '
                   f'text-anchor="middle" {ST["tw" if cls == "ic" else "t"]}>{label}</text>')


def circ(cx, cy, r, cls, label="", fs=0.9):
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" {ST[cls]}/>')
    if label:
        out.append(f'<text x="{cx:.2f}" y="{cy + fs * 0.35:.2f}" font-size="{fs}" text-anchor="middle" {ST["t"]}>{label}</text>')


def text(x, y, s, fs=1.1, anchor="start", cls="t"):
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{fs}" text-anchor="{anchor}" {ST[cls]}>{s}</text>')


def opzione(ox, oy, titolo, W, L, comp, sotto, pila, finito):
    out.append(f'<g transform="translate({ox},{oy})">')
    text(-RESINA, -3.2, titolo, 1.4, cls="h")
    rect(-RESINA, -RESINA, W + 2 * RESINA, L + 2 * RESINA, "resina")
    rect(0, 0, W, L, "pcb")
    for c in comp:
        rect(*c)
    rect(0, 0, W, 3.8, "keep")  # sopra al modulo: è la zona dell'antenna
    text(W / 2, 1.6, "antenna: niente rame", 0.75, "middle")
    text(W / 2, 2.7, "(3,8 mm, tutti gli strati)", 0.75, "middle")
    for c in sotto:
        (circ if c[0] == "o" else rect)(*c[1:])
    for c in pila:
        (circ if c[0] == "o" else rect)(*c[1:])
    # quote
    text(W / 2, L + RESINA + 2.0, f"scheda {W} × {L} mm".replace(".", ","), 1.0, "middle")
    text(W / 2, L + RESINA + 3.5, f"finito ≈ {finito}", 1.1, "middle", cls="h")
    out.append("</g>")


# Opzione A: lunga e stretta, componenti su un solo lato
A_W, A_L = 11.5, 26.5
A_comp = [
    (0.5, 0, 10.5, 15.5, "mod", "MDBT50Q", 1.1),
    (0.5, 15.9, 8, 6, "ic"),
    (9.1, 16.1, 1.6, 0.8, "pas"), (9.1, 17.2, 1.6, 0.8, "pas"),
    (9.4, 18.4, 1.0, 0.5, "pas"), (9.4, 19.2, 1.0, 0.5, "pas"), (9.4, 20.0, 1.0, 0.5, "pas"), (9.4, 20.8, 1.0, 0.5, "pas"),
    (0.5, 22.3, 2.5, 3.0, "ic", "IMU", 0.7),
    (3.4, 22.3, 3.3, 3.3, "ic", "press.", 0.7),
    (7.1, 22.4, 1.6, 0.9, "ic"), (9.2, 22.4, 1.0, 1.0, "led"),
    (7.1, 23.7, 1.2, 1.2, "ic"), (8.6, 23.9, 1.0, 0.5, "pas"), (9.8, 23.7, 1.2, 0.8, "pas"),
    (7.1, 25.2, 1.0, 0.5, "pas"), (8.4, 25.2, 1.0, 0.5, "pas"), (9.7, 25.2, 1.0, 0.5, "pas"),
]
A_sotto = [("o", 3.0, 19.0, 1.25, "sotto"), ("o", 8.0, 19.0, 1.25, "sotto")] + \
          [("r", 1.2 + i * 1.27, 23.9, 0.9, 0.9, "sotto") for i in range(5)]
A_pila = [("r", 0.75, 4.0, 10, 12, "cella", "cella 20 mAh (sopra)", 0.9), ("o", 4.5, 18.9, 3.0, "motore", "flash + vibr.", 0.8)]
opzione(4, 6, "A · lunga, un solo lato", A_W, A_L, A_comp, A_sotto, A_pila, "13 × 28 × 7,2 mm")

# Opzione B: più quadrata, componenti su un solo lato
B_W, B_L = 17.5, 19.5
B_comp = [
    (0.3, 0, 10.5, 15.5, "mod", "MDBT50Q", 1.1),
    (11.2, 4.1, 6, 8, "ic"),
    (11.4, 12.6, 2.5, 3.0, "ic", "IMU", 0.7), (14.4, 12.7, 1.6, 0.9, "ic"),
    (14.4, 14.0, 1.0, 0.5, "pas"), (14.4, 14.8, 1.0, 0.5, "pas"),
    (16.1, 12.7, 1.0, 0.5, "pas"), (16.1, 13.5, 1.0, 0.5, "pas"), (16.1, 14.3, 1.0, 0.5, "pas"), (16.1, 15.1, 1.0, 0.5, "pas"),
    (0.3, 15.9, 3.3, 3.3, "ic", "press.", 0.7),
    (4.0, 16.1, 1.6, 0.8, "pas"), (4.0, 17.3, 1.6, 0.8, "pas"),
    (6.0, 16.1, 1.2, 1.2, "ic"), (7.6, 16.1, 1.2, 0.8, "pas"), (9.2, 16.1, 1.0, 0.5, "pas"), (10.6, 16.0, 1.0, 1.0, "led"),
    (6.0, 17.8, 1.0, 0.5, "pas"), (7.4, 17.8, 1.0, 0.5, "pas"), (8.8, 17.8, 1.0, 0.5, "pas"), (10.2, 17.8, 1.0, 0.5, "pas"),
]
B_sotto = [("o", 4.0, 10.0, 1.25, "sotto"), ("o", 9.0, 10.0, 1.25, "sotto")] + \
          [("r", 11.3 + i * 1.27, 17.3, 0.9, 0.9, "sotto") for i in range(5)]
B_pila = [("r", 0.55, 4.0, 10, 12, "cella", "cella 20 mAh (sopra)", 0.9), ("o", 14.2, 8.1, 3.0, "motore", "flash + vibr.", 0.8)]
opzione(26, 6, "B · compatta, un solo lato", B_W, B_L, B_comp, B_sotto, B_pila, "19 × 21 × 7,2 mm")

# Sezione (vale per A e B): spessori in mm
sx, sy = 52, 9
text(sx, sy - 3.2, "Sezione (A e B)", 1.4, cls="h")
strati = [("resina sotto (copre l'SWD)", 0.5, "resina2"), ("PCB 0,8", 0.8, "pcb"), ("modulo 2,05", 2.05, "mod"),
          ("biadesivo 0,2", 0.2, "pas"), ("cella 3,0", 3.0, "cella"), ("resina sopra 0,6", 0.6, "resina2")]
y = sy + 9
ty = sy + 9.3
for nome, h, cls in strati:
    y -= h
    rect(sx, y, 16, h, cls)
    ty = min(ty - 1.1, y + h / 2 + 0.35)
    text(sx + 17, ty, nome, 0.9)
text(sx, sy + 11, "totale ≈ 7,2 mm; contatti di ricarica a filo sotto", 0.9)
text(sx, sy + 12.4, "sensore di pressione: porta verso l'alto con O-ring", 0.9)

# Legenda
lx, ly = 52, 26
leg = [("mod", "modulo nRF52840"), ("ic", "integrati"), ("pas", "passivi 0402/0603"), ("led", "LED RGB"),
       ("keep", "zona antenna senza rame"), ("cella", "cella (impilata sopra)"), ("motore", "vibratore Ø 6 (sopra)"),
       ("sotto", "lato sotto: contatti ricarica (tondi) e SWD (quadrati)"), ("resina", "ingombro finito con 0,8 mm di resina")]
text(lx, ly - 1.5, "Legenda (scala 1:1 in mm)", 1.2, cls="h")
for i, (cls, s) in enumerate(leg):
    rect(lx, ly + i * 1.9, 2.4, 1.3, cls)
    text(lx + 3.2, ly + i * 1.9 + 1.0, s, 0.95)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 92 46" width="1380" height="690">'
       f'<rect width="92" height="46" fill="#ffffff"/>' + "\n".join(out) + "</svg>")
Path(__file__).with_name("ingombro.svg").write_text(svg, encoding="utf-8")
print("scritto ingombro.svg")
