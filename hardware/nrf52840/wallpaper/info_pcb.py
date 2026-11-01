"""Estrae dal PCB i dati per i wallpaper (da eseguire con il Python di KiCad).

Uso: python.exe info_pcb.py scheda.kicad_pcb uscita.json
Coordinate in mm, origine nell'angolo in alto a sinistra del contorno della scheda.
"""
import json
import sys

import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
bb = b.GetBoardEdgesBoundingBox()
ox, oy = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())


def mm(p):
    return [round(pcbnew.ToMM(p.x) - ox, 3), round(pcbnew.ToMM(p.y) - oy, 3)]


fps = {}
for f in b.GetFootprints():
    r = f.GetBoundingBox(False)
    fps[f.GetReference()] = dict(
        pos=mm(f.GetPosition()), x0=round(pcbnew.ToMM(r.GetX()) - ox, 3), y0=round(pcbnew.ToMM(r.GetY()) - oy, 3),
        w=round(pcbnew.ToMM(r.GetWidth()), 3), h=round(pcbnew.ToMM(r.GetHeight()), 3),
        val=f.GetValue(), side="B" if f.IsFlipped() else "F")

vias, fori = [], []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append(mm(t.GetPosition()) + [round(pcbnew.ToMM(t.GetDrillValue()), 3)])
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetDrillSize().x > 0:
            fori.append(mm(p.GetPosition()) + [round(pcbnew.ToMM(p.GetDrillSize().x), 3),
                        "NPTH" if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else "PTH"])

piste = sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_TRACK")
lunghezza = sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetClass() == "PCB_TRACK")
json.dump(dict(w=round(pcbnew.ToMM(bb.GetWidth()), 3), h=round(pcbnew.ToMM(bb.GetHeight()), 3),
               piste=piste, lunghezza_mm=round(lunghezza), vias=vias, fori=fori, fps=fps,
               strati=b.GetCopperLayerCount()), open(sys.argv[2], "w"), indent=1)

# copia senza zone di rame (per disegnare solo piste e piazzole)
if len(sys.argv) > 3:
    for z in list(b.Zones()):
        b.Remove(z)
    b.Save(sys.argv[3])
