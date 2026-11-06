"""Cerca le posizioni dei componenti della variante 1c (scheda quasi quadrata) con raffreddamento simulato
e scrive posizioni_collaudo.py. Il modulo E73 e' fisso; le piazzole del lato sotto hanno posizioni scelte a mano (sotto()).
Costo = lunghezza stimata delle reti (HPWL, GND escluso) + penalita' per sovrapposizioni e uscite dal bordo.
Uso (Python di KiCad):  python.exe cerca_posizioni.py LARGHEZZA ALTEZZA [seme] [passi] [file_uscita]
"""
import math
import random
import sys

import pcbnew

import genera_pcb as g
from dati_scheda import COMPONENTI, VARIANTE

ECO = VARIANTE in ("economica", "v06")
import importlib
de = importlib.import_module("dati_v06" if VARIANTE == "v06" else "dati_economica") if ECO else None

mm = pcbnew.ToMM
GAP = float(__import__("os").environ.get("GAP", "0.2"))      # spazio minimo tra ingombri (mm): piste a 0,127 e via da 0,5
MARGINE = 0.35  # distanza minima dal bordo scheda
ROT = (0, 90, 180, 270)


def info(impronta):
    """{rot: (pads [(num, dx, dy)], (x0, y0, x1, y1) ingombro di pad e courtyard)} relativo al centro dell'impronta."""
    res = {}
    for rot in ROT:
        fp = g.carica_impronta(impronta)
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        fp.SetOrientationDegrees(rot)
        pads = [(p.GetNumber(), mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in fp.Pads()]
        xs0, ys0, xs1, ys1 = [], [], [], []
        for p in fp.Pads():
            r = p.GetBoundingBox()
            xs0.append(mm(r.GetX())); ys0.append(mm(r.GetY())); xs1.append(mm(r.GetRight())); ys1.append(mm(r.GetBottom()))
        cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if cy.GetWidth() > 0:   # courtyard dell'impronta (il DRC KiCad controlla che non si sovrappongano)
            xs0.append(mm(cy.GetX())); ys0.append(mm(cy.GetY())); xs1.append(mm(cy.GetRight())); ys1.append(mm(cy.GetBottom()))
        b = [min(xs0), min(ys0), max(xs1), max(ys1)]
        if impronta.startswith("swimtag:WSON-8"):   # flash: il corpo (8 x 6,1 mm) e' piu' alto della fila di pad
            cx, cy2 = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            w, h = (b[2] - b[0], 6.2) if (b[2] - b[0]) > (b[3] - b[1]) else (6.2, b[3] - b[1])
            b = [cx - w / 2, cy2 - h / 2, cx + w / 2, cy2 + h / 2]
        res[rot] = (pads, tuple(b))
    return res


def sotto(W, H):
    """Posizioni (x, y, rot) delle piazzole e del Tag-Connect sul lato sotto (a mano)."""
    yc = H - 2.0
    return {
        # contatti di ricarica Ø 2,5 a 4,2 mm, a destra sul bordo basso (la base a piu' posti li tocca da sotto)
        "TP1": (W - 10.8, yc, 0), "TP2": (W - 6.6, yc, 0),
        # vibratore: piazzole 1 mm vicino al bordo basso, sotto la flash (il vibratore sta sopra la flash)
        "TP10": (8.6, H - 1.3, 0), "TP11": (10.6, H - 1.3, 0),
        # piazzole di prova in colonna sul bordo destro (nomi in serigrafia a sinistra): Ø 0,8 segnali, Ø 1 per il tester
        "TP3": (W - 2.4, 13.6, 0), "TP4": (W - 2.4, 15.4, 0), "TP5": (W - 2.4, 17.2, 0), "TP6": (W - 2.4, 18.8, 0),
        "TP7": (W - 2.4, 20.6, 0), "TP8": (W - 2.4, 22.6, 0), "TP9": (W - 2.4, 24.6, 0),
        "J4": (W / 2, 9.5, 0),   # Tag-Connect sotto il corpo del modulo (sul lato opposto non ci sono pad); fori NPTH sotto il modulo
        # lato sopra, nella fascia sotto il modulo (non stanno nelle strisce laterali larghe ~4 mm): connettore batteria
        # a filo del bordo sinistro (apertura verso l'esterno) e flash accanto, con il corpo di 8 x 6,1 mm
        "J1": (3.35, H - 0.35 - 2.95, 270), "U3": (3.35 + 3.33 + 0.5 + 4.73, H - 0.35 - 3.1, 90),
    }


def main():
    W, H = float(sys.argv[1]), float(sys.argv[2])
    seme = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    passi = int(sys.argv[4]) if len(sys.argv) > 4 else 150000
    rnd = random.Random(seme)
    if ECO:   # v0.4: piazzole pogo e ricarica su griglia 2,54 mm (dati_economica.fissi), nessun componente sopra fissato
        fisso = de.fissi(W, H)
    else:
        fisso = sotto(W, H)
    comp = {c[0]: c for c in COMPONENTI}
    inf = {r: info(c[3]) for r, c in comp.items()}
    mod_xy = (de.MOD_X if ECO else W / 2, 11.2)
    reti = {}
    for r, c in comp.items():
        for pin, net in c[5].items():
            if net != "GND":
                reti.setdefault(net, []).append((r, str(pin)))
    mobili = [r for r in comp if r != "U1" and r not in fisso]
    # ostacoli fissi lato sopra oltre al modulo (J1, U3): usati nei controlli di sovrapposizione
    sopra_fissi = de.SOPRA_FISSI if ECO else ("J1", "U3")
    rot_ok = {} if ECO else {"J1": (90, 270)}   # connettore batteria: apertura verso l'esterno (90 = bordo destro, 270 = bordo sinistro)
    pos = {r: [rnd.uniform(3, W - 3), rnd.uniform(5, H - 3), rnd.choice(rot_ok.get(r, ROT))] for r in mobili}
    FAN = float(__import__("os").environ.get("FAN", "0.9"))
    mx0, mx1, my0, my1 = mod_xy[0] - 7.5 - FAN, mod_xy[0] + 7.5 + FAN, 0, 19.3 + FAN

    padd = {r: {rot: {n: (dx, dy) for n, dx, dy in inf[r][rot][0]} for rot in ROT} for r in inf}
    reti_di = {}
    for net, nodi in reti.items():
        for r, _ in nodi:
            reti_di.setdefault(r, set()).add(net)

    def pad_xy(r, pad):
        if r == "U1":
            x, y, rot = mod_xy[0], mod_xy[1], 180
        elif r in fisso:
            x, y, rot = fisso[r]
        else:
            x, y, rot = pos[r]
        d = padd[r][rot].get(pad)
        return (x + d[0], y + d[1]) if d else (x, y)

    EXTRA = ({"U2": 0.3} if VARIANTE == "v06" else {"U4": 0.5, "U6": 0.3, "U2": 0.3}) if ECO else {}   # piu' aria attorno ai pacchetti a passo fine (lo sbroglio li esce male)

    def box(r, x, y, rot):
        x0, y0, x1, y1 = inf[r][rot][1]
        e = GAP / 2 + EXTRA.get(r, 0.0)
        return x + x0 - e, y + y0 - e, x + x1 + e, y + y1 + e

    ostacoli = [box(r, *fisso[r]) for r in sopra_fissi]
    peso = {"VDD": 0.4, "VBAT": 0.4, "VDD_SENS": 0.4, "BAT": 0.6, "VIN_D": 0.6}

    def costo_reti(solo=None):
        t = 0.0
        for net in (reti if solo is None else solo):
            nodi = reti[net]
            pts = [pad_xy(r, p) for r, p in nodi]
            if len(pts) < 2:
                continue
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            t += peso.get(net, 1.0) * ((max(xs) - min(xs)) + (max(ys) - min(ys)))
        return t

    attr = getattr(de, "ATTRAZIONI", {}) if ECO else {}

    def costo_attr(r):
        """Condensatori di disaccoppiamento e resistenze di configurazione: vicini al loro pin (peso 4 sulla distanza)."""
        if r not in attr:
            return 0.0
        (u, pin), w = attr[r]
        x1, y1 = pad_xy(r, "1")
        x2, y2 = pad_xy(u, pin)
        return w * (abs(x1 - x2) + abs(y1 - y2))

    def pen_comp(r, f=1.0):
        x, y, rot = pos[r]
        b = box(r, x, y, rot)
        p = 0.0
        if b[0] < MARGINE - GAP / 2 or b[1] < MARGINE - GAP / 2 or b[2] > W - MARGINE + GAP / 2 or b[3] > H - MARGINE + GAP / 2:
            p += 100 + 40 * (max(0, MARGINE - b[0]) + max(0, MARGINE - b[1]) + max(0, b[2] - W + MARGINE) + max(0, b[3] - H + MARGINE))
        ox = min(b[2], mx1) - max(b[0], mx0)
        oy = min(b[3], my1) - max(b[1], my0)
        if ox > 0 and oy > 0:
            p += 100 + 60 * min(ox, oy)
        if b[1] < 3.7 + 0.2:   # striscia dell'antenna: niente rame, quindi niente componenti
            p += 100 + 60 * (3.9 - b[1])
        for c in ostacoli:
            ox = min(b[2], c[2]) - max(b[0], c[0])
            oy = min(b[3], c[3]) - max(b[1], c[1])
            if ox > 0 and oy > 0:
                p += 100 + 60 * min(ox, oy)
        for s in mobili:
            if s == r:
                continue
            c = box(s, *pos[s])
            ox = min(b[2], c[2]) - max(b[0], c[0])
            oy = min(b[3], c[3]) - max(b[1], c[1])
            if ox > 0 and oy > 0:
                p += f * (100 + 60 * min(ox, oy))
        return p

    def pen_j1():
        return 0

    def pen_j1_vecchio():  # (non piu' usato: J1 e' fisso)
        b = box("J1", *pos["J1"])
        if pos["J1"][2] == 270:
            return 0 if b[0] <= 0.2 else 5 + 5 * b[0]
        return 0 if b[2] >= W - 0.2 else 5 + 5 * (W - b[2])

    def totale():
        return costo_reti() + sum(pen_comp(r, 0.5) + costo_attr(r) for r in mobili) + pen_j1()

    legati = {}   # v0.6: spostando un circuito integrato cambia anche il costo dei suoi condensatori/resistenze legati (nella v0.5 non contava: il costo si "sporcava")
    if VARIANTE == "v06":
        for rr, ((uu, _), _) in attr.items():
            legati.setdefault(uu, []).append(rr)

    def locale(r):
        return costo_reti(reti_di[r]) + pen_comp(r) + costo_attr(r) + sum(costo_attr(x) for x in legati.get(r, ())) + (pen_j1() if r == "J1" else 0)

    T0, T1 = 3.0, 0.02
    cur = totale()
    migliore = (cur, {r: tuple(v) for r, v in pos.items()})
    for i in range(passi):
        T = T0 * (T1 / T0) ** (i / passi)
        r = rnd.choice(mobili)
        vecchio = list(pos[r])
        l0 = locale(r)
        sc = 0.4 + 6 * (1 - i / passi)
        u = rnd.random()
        if u < 0.1:
            pos[r][2] = rnd.choice(rot_ok.get(r, ROT))
        elif u < 0.2:
            pos[r][0] = rnd.uniform(1, W - 1)
            pos[r][1] = rnd.uniform(1, H - 1)
        else:
            pos[r][0] += rnd.gauss(0, sc)
            pos[r][1] += rnd.gauss(0, sc)
        nuovo = cur + locale(r) - l0
        if nuovo <= cur or rnd.random() < math.exp((cur - nuovo) / T):
            cur = nuovo
            if cur < migliore[0]:
                migliore = (cur, {k: tuple(v) for k, v in pos.items()})
        else:
            pos[r] = vecchio
    cur, best = migliore
    for k, v in best.items():
        pos[k] = list(v)
    cur = totale()   # ricalcolato: il costo accumulato a passi puo' essere sfalsato
    pen = sum(pen_comp(r, 0.5) for r in mobili) + pen_j1()
    for r in mobili:
        if pen_comp(r) > 0:
            print("  viola", r, [round(v, 1) for v in pos[r]], round(pen_comp(r), 1))
    print("  J1", round(pen_j1(), 1))
    print(f"W={W} H={H} seme={seme} costo={cur:.1f} penalita={pen:.1f} reti={costo_reti():.1f}")
    if len(sys.argv) > 5:
        with open(sys.argv[5], "w", encoding="utf-8") as f:
            f.write(f"SCHEDA_L = {W}\nSCHEDA_H_TOT = {H}\nPOS = {{\n")
            f.write(f'    "U1": ({mod_xy[0]}, {mod_xy[1]}, 180, "F"),\n')
            for r in comp:
                if r in fisso:
                    x, y, rot = fisso[r]
                    f.write(f'    "{r}": ({x:.2f}, {y:.2f}, {rot}, "{"F" if r in sopra_fissi else "B"}"),\n')
                elif r != "U1":
                    x, y, rot = pos[r]
                    f.write(f'    "{r}": ({round(x, 2)}, {round(y, 2)}, {rot}, "F"),\n')
            f.write("}\n")
    return pen


if __name__ == "__main__":
    main()
