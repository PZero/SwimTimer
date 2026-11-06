"""Disegno di montaggio della v0.6 (lato sopra) con pin 1 / polarita' leggibili: nextpcb/v0.6/assembly_pin1.png
Uso (Python di KiCad, ha PIL):  python.exe disegno_montaggio_v06.py
Legge swimtag_v06.kicad_pcb; segna con un cerchio rosso il pin 1 dei circuiti integrati e dei transistor e con una barra il catodo
(pad 1) dei diodi e del LED; scrive il designatore accanto a ogni componente montato (J1 DNP in grigio tratteggiato).
"""
from pathlib import Path

import pcbnew
from PIL import Image, ImageDraw, ImageFont

QUI = Path(__file__).parent
PCB = QUI / "swimtag_v06.kicad_pcb"
OUT = QUI / "nextpcb" / "v0.6" / "assembly_pin1.png"
S = 64          # pixel per mm
MARG = 2.0      # mm di margine


def main():
    b = pcbnew.LoadBoard(str(PCB))
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0 = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())
    w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    img = Image.new("RGB", (int((w + 2 * MARG) * S), int((h + 2 * MARG) * S)), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arial.ttf", 20)
        fb = ImageFont.truetype("arialbd.ttf", 24)
    except OSError:
        f = fb = ImageFont.load_default()

    def px(x, y):
        return ((x - x0 + MARG) * S, (y - y0 + MARG) * S)

    d.rectangle([px(x0, y0), px(x0 + w, y0 + h)], outline="black", width=3, fill=(214, 232, 214))
    for fp in b.GetFootprints():
        if fp.GetLayer() != pcbnew.F_Cu:
            continue
        rif = fp.GetReference()
        dnp = bool(fp.GetAttributes() & pcbnew.FP_DNP)
        if rif.startswith("TP"):
            continue
        for p in fp.Pads():
            r = p.GetBoundingBox()
            d.rectangle([px(pcbnew.ToMM(r.GetX()), pcbnew.ToMM(r.GetY())), px(pcbnew.ToMM(r.GetRight()), pcbnew.ToMM(r.GetBottom()))],
                        fill=(150, 150, 150) if dnp else (200, 160, 40), outline="black")
        cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if cy.GetWidth() > 0:
            d.rectangle([px(pcbnew.ToMM(cy.GetX()), pcbnew.ToMM(cy.GetY())), px(pcbnew.ToMM(cy.GetRight()), pcbnew.ToMM(cy.GetBottom()))],
                        outline=(120, 120, 255) if not dnp else (150, 150, 150), width=1)
        c = fp.GetPosition()
        cx, cyy = px(pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))
        pad1 = next((p for p in fp.Pads() if p.GetNumber() == "1"), None)
        if pad1 is not None and rif[0] in "UQ":
            q = pad1.GetPosition()
            qx, qy = px(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
            d.ellipse([qx - 12, qy - 12, qx + 12, qy + 12], outline="red", width=4)
            d.text((qx + 14, qy - 30), "1", fill="red", font=fb)
        elif pad1 is not None and rif[0] == "D" and rif != "D3":   # catodo = pad 1 (impronte KiCad D_SOD-323 e LED)
            r = pad1.GetBoundingBox()
            d.rectangle([px(pcbnew.ToMM(r.GetX()), pcbnew.ToMM(r.GetY())), px(pcbnew.ToMM(r.GetRight()), pcbnew.ToMM(r.GetBottom()))],
                        outline="red", width=4)
            q = pad1.GetPosition()
            qx, qy = px(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
            d.text((qx - 6, qy - 30), "K", fill="red", font=fb)
        if rif[0] in "UQJ" or rif in ("D1", "D2", "D3", "D4"):
            d.text((cx - 20, cyy - 10), rif + ("(DNP)" if dnp else ""), fill="blue", font=fb)
        elif rif[0] in "CR":
            d.text((cx - 12, cyy - 10), rif, fill=(60, 60, 60), font=f)
    d.text((10, 10), "SwimTag v0.6 - lato sopra (vista dall'alto). Cerchio rosso = pin 1; K = catodo (D1 LED, D2, D4); D3 TVS bidirezionale: nessuna polarita'",
           fill="black", font=f)
    img.save(OUT)
    print("scritto", OUT)


if __name__ == "__main__":
    main()
