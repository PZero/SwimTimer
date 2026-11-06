"""Via di cucitura della massa (v0.6, 4 strati): collegano i riempimenti di massa di F.Cu, In2.Cu e B.Cu al piano In1.Cu.

Aggiunge via GND (stessa misura dei via di segnale: 0,6 / 0,3, coperti) su una griglia e accanto a ogni pad di massa, solo dove c'e'
spazio (distanza dalle altre reti >= DISTANZA + margine su tutti gli strati), fuori dalla zona antenna e dal bordo.
Uso: stitch(board, passo=2.54) prima del riempimento finale delle zone (chiamato da sbroglia.py per la variante v06).
"""
import math

import pcbnew

from dati_scheda import ANTENNA_H, DISTANZA, SCHEDA_H_TOT, SCHEDA_L, VIA_D, VIA_FORO

mm = pcbnew.FromMM
um = pcbnew.ToMM
MARGINE = 0.06       # mm oltre DISTANZA (arrotondamenti di Freerouting)
BORDO = 0.2 + 0.3 + 0.1   # distanza minima del centro del via dal bordo scheda


def _dist_rett(px, py, x0, y0, x1, y1):
    dx = max(x0 - px, 0, px - x1)
    dy = max(y0 - py, 0, py - y1)
    return math.hypot(dx, dy)


def _dist_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    l2 = vx * vx + vy * vy
    t = 0 if l2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / l2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def stitch(board, passo=2.54):
    gnd = next(n for n in board.GetNetsByName().values() if n.GetNetname() == "/GND")
    ostacoli = []   # (tipo, dati, rete) su qualsiasi strato di rame
    for t in board.GetTracks():
        if t.GetNetname() == "/GND" and t.GetClass() == "PCB_TRACK":
            continue   # le piste di massa non sono un ostacolo per i via di massa (stessa rete)
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            ostacoli.append(("v", (um(p.x), um(p.y), um(t.GetFrontWidth()) / 2), t.GetNetname()))
        else:
            a, b = t.GetStart(), t.GetEnd()
            ostacoli.append(("t", (um(a.x), um(a.y), um(b.x), um(b.y), um(t.GetWidth()) / 2), t.GetNetname()))
    for fp in board.GetFootprints():
        for p in fp.Pads():
            r = p.GetBoundingBox()
            if p.GetNetname() == "/GND":   # pad di massa: il via non ci va sopra (piazzole di contatto sotto: niente fori), ma puo' stargli accanto
                ostacoli.append(("pg", (um(r.GetX()), um(r.GetY()), um(r.GetRight()), um(r.GetBottom())), "/GND"))
                continue
            ostacoli.append(("p", (um(r.GetX()), um(r.GetY()), um(r.GetRight()), um(r.GetBottom())), p.GetNetname()))
    vias_gnd = [(um(t.GetPosition().x), um(t.GetPosition().y)) for t in board.GetTracks()
                if t.GetClass() == "PCB_VIA" and t.GetNetname() == "/GND"]
    rv = VIA_D / 2
    lim = DISTANZA + MARGINE

    def libero(x, y):
        if x < BORDO or y < ANTENNA_H + BORDO or x > SCHEDA_L - BORDO or y > SCHEDA_H_TOT - BORDO:
            return False
        for tipo, d, _ in ostacoli:
            if tipo == "v":
                if math.hypot(x - d[0], y - d[1]) < rv + d[2] + lim:
                    return False
            elif tipo == "t":
                if _dist_seg(x, y, *d[:4]) < rv + d[4] + lim:
                    return False
            elif tipo == "pg":
                if _dist_rett(x, y, *d) < rv + 0.1:
                    return False
            else:
                if _dist_rett(x, y, *d) < rv + lim:
                    return False
        # via di massa esistenti: almeno 1,0 mm tra i centri (foro-foro)
        return all(math.hypot(x - a, y - b) >= 1.0 for a, b in vias_gnd)

    def aggiungi(x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetFrontWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_FORO))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(gnd)
        board.Add(v)
        vias_gnd.append((x, y))

    n = 0
    # accanto a ogni pad di massa SMD: via entro 2 mm (collega il pad al piano anche se il riempimento lo isola)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != "/GND" or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            c = p.GetPosition()
            cx, cy = um(c.x), um(c.y)
            if any(math.hypot(cx - a, cy - b) < 2.0 for a, b in vias_gnd):
                continue
            trovato = False
            for raggio in (0.9, 1.2, 1.5, 1.8, 2.1):
                for k in range(24):
                    ang = 2 * math.pi * k / 24
                    x, y = cx + raggio * math.cos(ang), cy + raggio * math.sin(ang)
                    if libero(x, y):
                        aggiungi(round(x, 3), round(y, 3))
                        n += 1
                        trovato = True
                        break
                if trovato:
                    break
    # griglia regolare
    y = ANTENNA_H + 1.0
    while y < SCHEDA_H_TOT - 0.7:
        x = 0.9
        while x < SCHEDA_L - 0.7:
            if libero(x, y):
                aggiungi(round(x, 3), round(y, 3))
                n += 1
            x += passo
        y += passo
    return n
