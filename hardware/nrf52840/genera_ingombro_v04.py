"""Genera ingombro_v0.4.svg: pianta in scala (1 unita' = 1 mm) del tag nRF52840 v0.4 "economica".

Legge il PCB reale (kicad/swimtag_economica.kicad_pcb), come genera_ingombro.py (v0.3, che resta com'e'). Disegna lato sopra,
lato sotto con la griglia 2,54 mm della millefori sovrapposta (origine = angolo in alto a sinistra, lato antenna) e la sezione.
Da eseguire con il Python di KiCad (serve pcbnew):  python.exe genera_ingombro_v04.py
"""
import pcbnew

import genera_ingombro as g
from genera_ingombro import QUI, RESINA, mm, rect, circ, text, pad_box, ST, out

PCB = QUI / "kicad" / "swimtag_economica.kicad_pcb"
ANTENNA_H = 3.7
G = 2.54
ST["grid"] = 'fill="none" stroke="#1f6fb5" stroke-width="0.06" stroke-dasharray="0.3 0.25"'
ST["hole"] = 'fill="#1f6fb5" fill-opacity="0.55"'


def vista(board, ox, oy, titolo, lato, W, H):
    def X(x):
        return ox + (x if lato == "F" else W - x)
    out.append("<g>")
    text(ox - RESINA, oy - 3.4, titolo, 1.4, cls="h")
    rect(ox - RESINA, oy - RESINA, W + 2 * RESINA, H + 2 * RESINA, "resina")
    rect(ox, oy, W, H, "pcb")
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if not p.IsOnLayer(pcbnew.F_Cu if lato == "F" else pcbnew.B_Cu):
                continue
            x, y, w, h = pad_box(p)
            if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                circ(X(x + w / 2), oy + y + h / 2, w / 2, "pad" if lato == "F" else "padb")
            else:
                rect(X(x + w) if lato == "B" else X(x), oy + y, w, h, "pad" if lato == "F" else "padb")
        if lato == "F" and fp.GetReference() == "U1":
            cx, cy = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
            out.append(f'<rect x="{ox + cx - 6.5:.2f}" y="{oy + cy - 9.0:.2f}" width="13" height="18" fill="none" '
                       f'stroke="#555555" stroke-width="0.15"/>')
            text(ox + cx, oy + cy + 2.2, "E73-2G4M08S1C", 0.9, "middle")
            text(ox + cx, oy + cy + 3.4, "13 × 18 mm", 0.8, "middle")
        if lato == "F" and fp.GetReference() in ("U2", "U3", "U4", "D1", "J1"):
            x, y = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
            nome = {"U2": "IMU", "U3": "flash 16 MB", "U4": "BQ25101", "D1": "LED", "J1": "batteria"}[fp.GetReference()]
            text(ox + x, oy + y + 0.3, nome, 0.7, "middle")
    rect(ox, oy, W, ANTENNA_H, "keep")
    text(ox + W / 2, oy + 1.5, "antenna: niente rame", 0.75, "middle")
    text(ox + W / 2, oy + 2.6, "(3,7 mm, tutti gli strati)", 0.75, "middle")
    if lato == "F":
        cx0 = ox + (W - 10) / 2
        rect(cx0, oy + 5.0, 10, 12, "cella")
        text(cx0 + 5, oy + 10.5, "cella 401012", 0.85, "middle")
        text(cx0 + 5, oy + 11.6, "4 × 10 × 12 mm", 0.8, "middle")
        text(cx0 + 5, oy + 12.7, "(sopra il modulo)", 0.8, "middle")
    else:
        # griglia 2,54 mm della millefori: linee e fori a partire dal bordo sinistro (in alto a sinistra visto da sopra) e dal bordo alto
        for i in range(0, int(W // G) + 1):
            x = X(i * G)
            out.append(f'<line x1="{x:.2f}" y1="{oy:.2f}" x2="{x:.2f}" y2="{oy + H:.2f}" {ST["grid"]}/>')
        for j in range(0, int(H // G) + 1):
            out.append(f'<line x1="{ox:.2f}" y1="{oy + j * G:.2f}" x2="{ox + W:.2f}" y2="{oy + j * G:.2f}" {ST["grid"]}/>')
        for i in range(0, int(W // G) + 1):
            for j in range(0, int(H // G) + 1):
                circ(X(i * G), oy + j * G, 0.45, "hole")
        for fp in board.GetFootprints():
            if fp.GetLayer() == pcbnew.B_Cu:
                x, y = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
                nome = fp.GetValue()
                text(X(x), oy + y - (1.5 if y < 15 else -2.7), nome, 0.6, "middle")
        text(ox + W / 2, oy + H + RESINA + 0.5, "griglia 2,54 mm: foro (0,0) = angolo antenna (sinistro visto da sopra)", 0.7, "middle")
    text(ox + W / 2, oy + H + RESINA + 2.0, f"scheda {W:g} × {H:g} mm".replace(".", ","), 1.0, "middle")
    text(ox + W / 2, oy + H + RESINA + 3.5, f"con resina ≈ {W + 2 * RESINA:g} × {H + 2 * RESINA:g} mm".replace(".", ","),
         1.0, "middle", cls="h")
    out.append("</g>")


def main():
    board = pcbnew.LoadBoard(str(PCB))
    bb = board.GetBoardEdgesBoundingBox()
    W, H = round(mm(bb.GetWidth()) * 2) / 2, round(mm(bb.GetHeight()) * 2) / 2
    vista(board, 4, 6, "Sopra (componenti)", "F", W, H)
    vista(board, W + 12, 6, "Sotto (visto girando la scheda), griglia 2,54", "B", W, H)
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
    text(sx, sy + tot + 3.0, "(header batteria e flash entro lo spessore del modulo)", 0.85)
    lx, ly = sx, sy + tot + 7
    leg = [("pad", "piazzole sopra"), ("padb", "piazzole sotto"), ("keep", "zona antenna senza rame"),
           ("cella", "cella 401012 (sopra il modulo)"), ("grid", "griglia millefori 2,54 mm"),
           ("resina", f"ingombro con {RESINA:g} mm di resina per lato")]
    text(lx, ly - 1.5, "Legenda (scala 1:1 in mm)", 1.2, cls="h")
    for i, (cls, s) in enumerate(leg):
        rect(lx, ly + i * 1.9, 2.4, 1.3, cls)
        text(lx + 3.2, ly + i * 1.9 + 1.0, s, 0.95)
    vw, vh = 2 * W + 46, H + 16
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:g} {vh:g}" width="{vw * 15:g}" height="{vh * 15:g}">'
           f'<rect width="{vw:g}" height="{vh:g}" fill="#ffffff"/>' + "\n".join(out) + "</svg>")
    (QUI / "ingombro_v0.4.svg").write_text(svg, encoding="utf-8")
    print("scritto ingombro_v0.4.svg", W, H)


if __name__ == "__main__":
    main()
