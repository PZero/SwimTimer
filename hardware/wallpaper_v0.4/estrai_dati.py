"""Estrae dal PCB i dati per gli sfondi (da eseguire con il Python di KiCad).

Uso: python.exe estrai_dati.py scheda.kicad_pcb uscita.json
Coordinate in mm, origine nell'angolo in alto a sinistra del riquadro dei contorni (Edge.Cuts).
"""
import json
import sys

import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
bb = b.GetBoardEdgesBoundingBox()
ox, oy = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())


def mm(p):
    return [round(pcbnew.ToMM(p.x) - ox, 3), round(pcbnew.ToMM(p.y) - oy, 3)]


def f2(v):
    return round(pcbnew.ToMM(v), 3)


fps = {}
for f in b.GetFootprints():
    r = f.GetBoundingBox(False)
    pads = []
    for p in f.Pads():
        pads.append(dict(n=p.GetNumber(), name=p.GetPadName() if hasattr(p, "GetPadName") else p.GetNumber(),
                         net=p.GetNetname(), pos=mm(p.GetPosition()), w=f2(p.GetSize().x), h=f2(p.GetSize().y),
                         drill=f2(p.GetDrillSize().x), shape=int(p.GetShape()), rot=p.GetOrientationDegrees(),
                         tipo="NPTH" if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else ("PTH" if p.GetDrillSize().x > 0 else "SMD")))
    fps[f.GetReference()] = dict(
        val=f.GetValue(), fpid=f.GetFPIDAsString(), side="B" if f.IsFlipped() else "F", pos=mm(f.GetPosition()),
        rot=f.GetOrientationDegrees(), x0=round(pcbnew.ToMM(r.GetX()) - ox, 3), y0=round(pcbnew.ToMM(r.GetY()) - oy, 3),
        w=f2(r.GetWidth()), h=f2(r.GetHeight()), pads=pads)

vias = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append(dict(pos=mm(t.GetPosition()), drill=f2(t.GetDrillValue()), dia=f2(t.GetWidth(0)), net=t.GetNetname()))

json.dump(dict(w=f2(bb.GetWidth()), h=f2(bb.GetHeight()), spessore=pcbnew.ToMM(b.GetDesignSettings().GetBoardThickness()),
               strati=b.GetCopperLayerCount(), vias=vias, fps=fps), open(sys.argv[2], "w", encoding="utf-8"), indent=1,
          ensure_ascii=False)
