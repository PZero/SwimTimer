"""Genera ingombro.svg: pianta in scala (1 unita' = 1 mm) del tag nRF52840 v0.3, variante 1c (collaudo).

Legge il PCB reale (kicad/swimtag_collaudo.kicad_pcb: pad e posizioni dei componenti) e disegna lato sopra, lato sotto
e sezione, con la cella 401012 (4 x 10 x 12 mm) sopra il modulo E73 e il vibratore Ø 6 mm sopra la flash.
Da eseguire con il Python di KiCad (serve pcbnew):  python.exe genera_ingombro.py
"""
from pathlib import Path

import pcbnew

QUI = Path(__file__).parent
PCB = QUI / "kicad" / "swimtag_collaudo.kicad_pcb"
RESINA = 1.5          # parete di resina per lato (mm)
ANTENNA_H = 3.7
mm = pcbnew.ToMM

ST = {
    "pcb": 'fill="#2e7d4f" stroke="#1b4d30" stroke-width="0.1"',
    "mod": 'fill="#b8bec6" stroke="#555555" stroke-width="0.1"',
    "pad": 'fill="#c9a66b" stroke="#7a5a2a" stroke-width="0.05"',
    "padb": 'fill="#e8c46a" stroke="#7a5a2a" stroke-width="0.05"',
    "keep": 'fill="#e74c3c" fill-opacity="0.3" stroke="#c0392b" stroke-width="0.12"',
    "cella": 'fill="#3478dc" fill-opacity="0.25" stroke="#2a62c9" stroke-width="0.15" stroke-dasharray="0.6 0.4"',
    "motore": 'fill="#e67e22" fill-opacity="0.25" stroke="#d35400" stroke-width="0.15" stroke-dasharray="0.6 0.4"',
    "resina": 'fill="#c8dcf0" fill-opacity="0.35" stroke="#7fa7c9" stroke-width="0.12" stroke-dasharray="0.3 0.3"',
    "resina2": 'fill="#dde9f3" stroke="#7fa7c9" stroke-width="0.08"',
    "t": 'fill="#222222" font-family="Arial, sans-serif"',
    "h": 'fill="#111111" font-family="Arial, sans-serif" font-weight="bold"',
}
out = []


def rect(x, y, w, h, cls):
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" {ST[cls]}/>')


def circ(cx, cy, r, cls):
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" {ST[cls]}/>')


def text(x, y, s, fs=1.0, anchor="start", cls="t"):
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{fs}" text-anchor="{anchor}" {ST[cls]}>{s}</text>')


def pad_box(p):
    bb = p.GetBoundingBox()
    return mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetWidth()), mm(bb.GetHeight())


def vista(board, ox, oy, titolo, lato, W, H):
    """lato: 'F' o 'B'. Per il lato sotto la vista e' specchiata (come girando la scheda sul lato lungo)."""
    def X(x):
        return ox + (x if lato == "F" else W - x)
    out.append(f'<g>')
    text(ox - RESINA, oy - 3.4, titolo, 1.4, cls="h")
    rect(ox - RESINA, oy - RESINA, W + 2 * RESINA, H + 2 * RESINA, "resina")
    rect(ox, oy, W, H, "pcb")
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for p in fp.Pads():
            if not p.IsOnLayer(pcbnew.F_Cu if lato == "F" else pcbnew.B_Cu):
                continue
            x, y, w, h = pad_box(p)
            if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                circ(X(x + w / 2), oy + y + h / 2, w / 2, "pad" if lato == "F" else "padb")
            else:
                rect(X(x + w) if lato == "B" else X(x), oy + y, w, h, "pad" if lato == "F" else "padb")
        if lato == "F" and ref == "U1":
            cx, cy = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
            out.append(f'<rect x="{ox + cx - 6.5:.2f}" y="{oy + cy - 9.0:.2f}" width="13" height="18" fill="none" '
                       f'stroke="#555555" stroke-width="0.15"/>')
            text(ox + cx, oy + cy + 2.2, "E73-2G4M08S1C", 0.9, "middle")
            text(ox + cx, oy + cy + 3.4, "13 × 18 mm", 0.8, "middle")
    # antenna: striscia senza rame
    rect(ox, oy, W, ANTENNA_H, "keep")
    text(ox + W / 2, oy + 1.5, "antenna: niente rame", 0.75, "middle")
    text(ox + W / 2, oy + 2.6, "(3,7 mm, tutti gli strati)", 0.75, "middle")
    if lato == "F":
        # cella 401012 (10 x 12 mm in pianta) sopra il modulo, fuori dalla striscia dell'antenna
        cx0 = ox + (W - 10) / 2
        rect(cx0, oy + 5.0, 10, 12, "cella")
        text(cx0 + 5, oy + 10.5, "cella 401012", 0.85, "middle")
        text(cx0 + 5, oy + 11.6, "4 × 10 × 12 mm", 0.8, "middle")
        text(cx0 + 5, oy + 12.7, "(sopra il modulo)", 0.8, "middle")
        # vibratore Ø 6 sopra la flash (U3)
        u3 = board.FindFootprintByReference("U3")
        circ(ox + mm(u3.GetPosition().x), oy + mm(u3.GetPosition().y), 3.0, "motore")
        text(ox + mm(u3.GetPosition().x), oy + mm(u3.GetPosition().y) + 0.3, "vibratore Ø 6", 0.75, "middle")
    else:
        for fp in board.GetFootprints():
            if fp.GetLayer() == pcbnew.B_Cu and fp.GetReference() in ("TP1", "TP2", "J4", "TP10", "TP11", "TP7"):
                x, y = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
                text(X(x), oy + y - 2.0, {"TP1": "VIN", "TP2": "GND", "J4": "TC2030", "TP10": "MOT+", "TP11": "MOT-",
                                          "TP7": "prova"}[fp.GetReference()], 0.8, "middle")
    text(ox + W / 2, oy + H + RESINA + 2.0, f"scheda {W:g} × {H:g} mm".replace(".", ","), 1.0, "middle")
    text(ox + W / 2, oy + H + RESINA + 3.5, f"con resina ≈ {W + 2 * RESINA:g} × {H + 2 * RESINA:g} mm".replace(".", ","),
         1.0, "middle", cls="h")
    out.append("</g>")


def main():
    board = pcbnew.LoadBoard(str(PCB))
    bb = board.GetBoardEdgesBoundingBox()
    W, H = round(mm(bb.GetWidth()) * 2) / 2, round(mm(bb.GetHeight()) * 2) / 2   # la bbox include lo spessore della linea del contorno
    vista(board, 4, 6, "Sopra (componenti)", "F", W, H)
    vista(board, W + 12, 6, "Sotto (visto girando la scheda)", "B", W, H)
    # sezione
    sx, sy = 2 * W + 20, 9
    text(sx, sy - 3.4, "Sezione (spessori)", 1.4, cls="h")
    strati = [("resina sotto 0,5", 0.5, "resina2"), ("PCB 0,8", 0.8, "pcb"), ("modulo E73 3,0", 3.0, "mod"),
              ("cella 4,0", 4.0, "cella"), ("resina sopra 0,9", 0.9, "resina2")]
    tot = sum(s[1] for s in strati)
    y = sy + tot
    for nome, h, cls in strati:
        y -= h
        rect(sx, y, 14, h, cls)
        text(sx + 15, y + h / 2 + 0.35, nome, 0.9)
    text(sx, sy + tot + 1.6, f"totale ≈ {tot:.1f} mm".replace(".", ","), 1.0, cls="h")
    text(sx, sy + tot + 3.0, "(vibratore e flash sotto lo spessore del modulo)", 0.85)
    # legenda
    lx, ly = sx, sy + tot + 7
    leg = [("pad", "piazzole sopra"), ("padb", "piazzole sotto"), ("keep", "zona antenna senza rame"),
           ("cella", "cella 401012 (sopra il modulo)"), ("motore", "vibratore Ø 6 (sopra la flash)"),
           ("resina", f"ingombro con {RESINA:g} mm di resina per lato")]
    text(lx, ly - 1.5, "Legenda (scala 1:1 in mm)", 1.2, cls="h")
    for i, (cls, s) in enumerate(leg):
        rect(lx, ly + i * 1.9, 2.4, 1.3, cls)
        text(lx + 3.2, ly + i * 1.9 + 1.0, s, 0.95)
    vw = 2 * W + 46
    vh = H + 16
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:g} {vh:g}" width="{vw * 15:g}" height="{vh * 15:g}">'
           f'<rect width="{vw:g}" height="{vh:g}" fill="#ffffff"/>' + "\n".join(out) + "</svg>")
    (QUI / "ingombro.svg").write_text(svg, encoding="utf-8")
    print("scritto ingombro.svg", W, H)


if __name__ == "__main__":
    main()
