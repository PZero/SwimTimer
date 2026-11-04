"""Modello geometrico dell'adattatore di programmazione e collaudo (pogo jig) SwimTag.

Legge dal PCB del tag (default ../nrf52840/kicad/swimtag_economica.kicad_pcb) il contorno (Edge.Cuts)
e le coordinate delle piazzole TP1..TP7, e ne ricava tutta la geometria dell'adattatore.
Sistema di coordinate dell'adattatore = quello del PCB del tag, visto da SOPRA con il tag appoggiato
a faccia in giu' sui pogo (x verso destra, y verso il basso; origine = angolo in alto a sinistra del tag).
Tutte le misure in mm. Nessun valore del tag e' scritto qui: cambiano con il file .kicad_pcb.

Uso:  from modello import costruisci;  m = costruisci()
"""
import math
import os
import re
import uuid
from pathlib import Path

QUI = Path(__file__).parent
PCB_TAG = Path(os.environ.get("SWIMTAG_PCB", QUI.parent / "nrf52840" / "kicad" / "swimtag_economica.kicad_pcb"))
NS = uuid.UUID("a3b1c9d2-5e47-4f6a-8d10-77c2e9b04a11")

# ---- parametri di progetto (modificabili) ----
LARG_PISTA = 0.8          # piste (minimo toner transfer 0,6)
DIST_MIN = 0.5            # distanza minima rame-rame
PAD_MIN = 2.0             # piazzola minima
FORO_POGO = 1.5           # foro del ricettacolo pogo (DA VERIFICARE sul pezzo arrivato, vedi README)
FORO_M3 = 3.2
GIOCO_BATTUTA = 0.1       # gioco tra bordo del tag e battuta
ALT_BATTUTE = 2.5         # altezza del corpo di un header 2,54 mm (battute e appoggi)
PASSO = 2.54


def uid(*p):
    return str(uuid.uuid5(NS, "/".join(map(str, p))))


# ---------------- lettura del PCB del tag ----------------
def _alberi(testo):
    """Parser minimale di S-expression: restituisce liste annidate di stringhe."""
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', testo)
    pila, cur = [], []
    for t in tok:
        if t == "(":
            pila.append(cur)
            cur = []
        elif t == ")":
            nuovo = cur
            cur = pila.pop()
            cur.append(nuovo)
        else:
            cur.append(t.strip('"') if t.startswith('"') else t)
    return cur[0]


def _fig(nodo, nome):
    return [x for x in nodo if isinstance(x, list) and x and x[0] == nome]


def leggi_tag(percorso=PCB_TAG):
    pcb = _alberi(Path(percorso).read_text(encoding="utf-8"))
    tp = {}
    for fp in _fig(pcb, "footprint"):
        rif = None
        for pr in _fig(fp, "property"):
            if pr[1] == "Reference":
                rif = pr[2]
        if rif and re.fullmatch(r"TP[1-7]", rif):
            at = _fig(fp, "at")[0]
            fx, fy = float(at[1]), float(at[2])
            pad = _fig(fp, "pad")[0]
            pat = _fig(pad, "at")[0]
            sz = _fig(pad, "size")[0]
            # rotazione del footprint: le piazzole sono tonde e il pad e' in (0,0); si somma l'offset ruotato
            rot = float(at[3]) if len(at) > 3 else 0.0
            ox, oy = float(pat[1]), float(pat[2])
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            tp[rif] = (round(fx + ox * c + oy * s, 4), round(fy - ox * s + oy * c, 4), float(sz[1]))
    xs, ys = [], []
    for gr in pcb:
        if not isinstance(gr, list) or not gr or gr[0] not in ("gr_rect", "gr_line", "gr_arc", "gr_poly", "gr_circle"):
            continue
        if not any(len(l) > 1 and l[0] == "layer" and l[1] == "Edge.Cuts" for l in gr if isinstance(l, list)):
            continue
        for sotto in gr:
            if isinstance(sotto, list) and sotto and sotto[0] in ("start", "end", "mid", "center"):
                xs.append(float(sotto[1])); ys.append(float(sotto[2]))
            if isinstance(sotto, list) and sotto and sotto[0] == "pts":
                for p in sotto[1:]:
                    xs.append(float(p[1])); ys.append(float(p[2]))
    if len(tp) != 7 or not xs:
        raise SystemExit("TP1..TP7 o Edge.Cuts non trovati in %s" % percorso)
    return {"tp": tp, "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys), "file": str(percorso)}


# ---------------- costruzione dell'adattatore (forma di HAT) ----------------
# Sistema di coordinate dell'adattatore = quello dell'HAT visto da SOPRA: u verso destra (asse lungo del Pi,
# SD a sinistra, USB/Ethernet a destra), v verso il basso, origine nell'angolo in alto a sinistra; il connettore a
# 40 pin sta lungo il bordo v = 0 (specifica HAT ufficiale). Il rame e' SOPRA (stesso lato dei pogo e dei componenti
# alti); il connettore femmina 2x20 si monta da sotto e si salda sopra, come in un HAT vero.
HAT_W, HAT_H, HAT_R = 65.0, 56.5, 3.0
HAT_FORI = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
FORO_HAT = 2.75
CONN_CX, CONN_V = 32.5, 3.5            # centro del connettore: meta' tra i fori, a 3,5 mm dal bordo
CONN_EXT = CONN_V - PASSO / 2         # fila esterna (pin pari 2, 4, ..., 40), vicina al bordo
CONN_INT = CONN_V + PASSO / 2         # fila interna (pin dispari): code TAGLIATE, niente fori
OU, OV = 22.5, 24.0                    # posizione dell'angolo in alto a sinistra del tag sull'HAT
PIN_QUADRO = 0.32                      # semi-lato di un pin 0,64 mm (battute)
DISTANZIALI = 11.0


def col_conn(c):
    """Ascissa della colonna c (1..20) del connettore; il pin pari e' 2c, il dispari 2c-1."""
    return round(CONN_CX + (c - 10.5) * PASSO, 4)


def costruisci(percorso=PCB_TAG):
    t = leggi_tag(percorso)
    W, H = t["x1"] - t["x0"], t["y1"] - t["y0"]
    # coordinate del tag nel sistema dell'HAT (il tag viene solo traslato)
    tp = {n: (round(v[0] - t["x0"] + OU, 4), round(v[1] - t["y0"] + OV, 4), v[2]) for n, v in t["tp"].items()}
    x0, y0, x1, y1 = OU, OV, OU + W, OV + H
    avvisi = []
    col = {n: tp[n][0] for n in tp}
    rowy = tp["TP1"][1]
    for n in ("TP2", "TP3", "TP4", "TP5"):
        if abs(tp[n][1] - rowy) > 0.01:
            avvisi.append(f"{n} non e' sulla stessa fila di TP1")
    for a, b in (("TP1", "TP2"), ("TP2", "TP3"), ("TP3", "TP4"), ("TP4", "TP5")):
        if abs(col[b] - col[a] - PASSO) > 0.02:
            avvisi.append(f"passo {a}-{b} = {col[b]-col[a]:.3f} mm (atteso 2,54): lo sbroglio dei ponti va rivisto")
    if abs(col["TP7"] - col["TP6"] - PASSO * 2) > 0.02 or abs(tp["TP6"][1] - tp["TP7"][1]) > 0.01:
        avvisi.append("TP6-TP7 non a 5,08 mm sulla stessa riga: lo sbroglio della ricarica va rivisto")
    if abs(tp["TP6"][0] - col["TP2"]) > 0.02 or abs(tp["TP7"][0] - col["TP4"]) > 0.02:
        avvisi.append("TP6/TP7 non sotto SWDIO/RESET come nella v0.5 attuale: controllare lo sbroglio")
    if y1 + 3 > HAT_H - 1:
        avvisi.append(f"il tag ({H:.1f} mm) non sta nell'HAT con questa posizione OV={OV}")
    for n in tp:
        if tp[n][2] < 1.5:
            avvisi.append(f"{n}: piazzola del tag molto piccola ({tp[n][2]} mm)")

    p, fp = [], {}

    def pad(ref, num, x, y, forma="circle", w=2.0, h=None, foro=1.0, rete=None, npth=False, smd=False):
        p.append(dict(ref=ref, num=str(num), x=round(x, 4), y=round(y, 4), forma=forma, w=w, h=h or w, foro=foro,
                      rete=rete, npth=npth, smd=smd))

    def XY(ref, num):
        q = [a for a in p if a["ref"] == ref and a["num"] == str(num)][0]
        return (q["x"], q["y"])

    nomi = {"TP1": "VDD", "TP2": "SWDIO", "TP3": "SWCLK", "TP4": "RESET", "TP5": "GND", "TP6": "VIN", "TP7": "GND_C"}
    rete_pogo = {"TP1": "/VDD_T", "TP2": "/SWDIO_T", "TP3": "/SWCLK_T", "TP4": "/RESET_T", "TP5": "/GND", "TP6": "/VIN_T", "TP7": "/GND"}
    for i in range(1, 8):
        n = f"TP{i}"
        x, y, d = tp[n]
        if i <= 5:
            pad(f"P{i}", 1, x, y, "oval", PAD_MIN, 3.2, FORO_POGO, rete_pogo[n])
        else:
            pad(f"P{i}", 1, x, y, "circle", 2.8, 2.8, FORO_POGO, rete_pogo[n])
        fp[f"P{i}"] = dict(valore=f"Pogo P75-E2 / R75-2W ({nomi[n]})", lib="SwimJig:Pogo_P75_ricettacolo")

    # connettore femmina 2x20: solo la fila esterna (pin pari) ha le piazzole; i pin sono 2, 4, ..., 40
    usati = {2: "/V5_PI", 12: "/RESET_H", 18: "/SWDIO_H", 20: "/GND", 22: "/SWCLK_H"}
    for c in range(1, 21):
        pad("J1", 2 * c, col_conn(c), CONN_EXT, rete=usati.get(2 * c), foro=1.0)
    fp["J1"] = dict(valore="Header femmina 2x20 (HAT), da sotto; code dei pin dispari tagliate", lib="SwimJig:Header_F_2x20_HAT")

    xe, xa, xb, xc, xd = col["TP1"], col["TP2"], col["TP3"], col["TP4"], col["TP5"]
    vp = tp["TP1"][1]                    # fila dei pogo
    v_alto = vp - 1.6                    # estremo alto della piazzola ovale
    uA, uD, uB, uC, u5 = col_conn(9), col_conn(10), col_conn(11), col_conn(6), col_conn(1)
    vR3 = y0 - 5.0                       # R3 (RESET): ponte orizzontale sopra SWDIO e SWCLK
    pad("R3", 1, xc, vR3, rete="/RESET_T", foro=0.8)
    pad("R3", 2, xc - 10.16, vR3, rete="/RESET_H", foro=0.8)
    pad("R1", 1, uA, 9.0, rete="/SWDIO_T", foro=0.8)                  # R1 (SWDIO): in piedi
    pad("R1", 2, uA, 9.0 - PASSO, rete="/SWDIO_H", foro=0.8)
    pad("R2", 1, uB, 15.0, rete="/SWCLK_T", foro=0.8)                 # R2 (SWCLK): ponte verticale sulla massa
    pad("R2", 2, uB, 15.0 - 10.16, rete="/SWCLK_H", foro=0.8)
    for k in (1, 2, 3):
        fp[f"R{k}"] = dict(valore="1 kohm 1/4 W", lib="SwimJig:R_1k")
    vD = 9.9
    pad("J4", 1, 18.5, vp, rete="/VDD_T")
    fp["J4"] = dict(valore="Pin VDD (solo tester)", lib="SwimJig:Header_1x1")

    g = [u5 - PASSO, u5, u5 + PASSO, u5 + 2 * PASSO, u5 + 3 * PASSO, u5 + 4 * PASSO]
    pad("F1", 1, u5, 9.0, w=2.2, rete="/V5_PI")
    pad("F1", 2, u5, 9.0 + 5.08, w=2.2, rete="/V5_F")
    fp["F1"] = dict(valore="PTC 0,1 A (hold) radiale passo 5,08", lib="SwimJig:PTC_Radial_P5.08")
    for k, rete in enumerate(("/V5_F", "/V5_SEL", "/V5_EXT")):
        pad("JP1", k + 1, u5, 19.0 + k * PASSO, rete=rete)
    fp["JP1"] = dict(valore="CARICA: 1-2 Pi, 2-3 esterno, nessun ponticello = OFF", lib="SwimJig:Header_1x3_P2.54")
    pad("J2", 1, u5, 28.62, rete="/V5_EXT")
    pad("J2", 2, g[0], 28.62, rete="/GND")
    fp["J2"] = dict(valore="EXT: +5V esterno / GND (header 1x2)", lib="SwimJig:Header_1x2_P2.54")
    xs = g[3]                               # colonna del ramo SEL
    v_tp6 = tp["TP6"][1]
    pad("J3", 1, g[4], v_tp6, rete="/VIN_T")
    pad("J3", 2, xs, v_tp6, rete="/V5_SEL")
    fp["J3"] = dict(valore="mA: tester in serie (o ponticello)", lib="SwimJig:Header_1x2_P2.54")
    pad("R4", 1, g[2], 33.0, rete="/V5_SEL", foro=0.8)
    pad("R4", 2, g[2], 33.0 + PASSO, rete="/LED_A", foro=0.8)
    fp["R4"] = dict(valore="1 kohm 1/4 W", lib="SwimJig:R_1k")
    pad("D1", 1, g[2], 38.08, rete="/LED_A", foro=1.0)
    pad("D1", 2, g[2], 38.08 + PASSO, rete="/GND", foro=1.0)
    fp["D1"] = dict(valore="LED verde 3 mm (5 V presente)", lib="SwimJig:LED_P2.54")

    def a_griglia(v, base):
        return base + round((v - base) / PASSO) * PASSO
    gx = x0 - PIN_QUADRO - GIOCO_BATTUTA
    gy = y0 - PIN_QUADRO - GIOCO_BATTUTA
    battute = [("S1", gx, y0 + PASSO, "sx"), ("S2", gx, a_griglia(y1 - PASSO, y0), "sx"), ("S3", a_griglia(x1 - PASSO, x0), gy, "alto")]
    for ref, x, y, lato in battute:
        pad(ref, 1, x, y, foro=0.8)
        fp[ref] = dict(valore=f"Battuta lato {'sinistro' if lato == 'sx' else 'alto'} (pin 0,64 mm)", lib="SwimJig:Header_1x1")
    appoggi = [("S4", x0 + PASSO, y0 + 3 * PASSO), ("S5", a_griglia(x1 - PASSO, x0), y0 + 3 * PASSO),
               ("S6", a_griglia(x0 + W / 2, x0), y1 - 1.9)]
    for ref, x, y in appoggi:
        pad(ref, 1, x, y, "rect", 3.0, 3.0, 0, None, smd=True)
        fp[ref] = dict(valore="Sede dell'appoggio (blocchetto 2,5 mm incollato)", lib="SwimJig:Glue_3x3")
    for k, (x, y) in enumerate(HAT_FORI):
        pad(f"H{k+1}", 1, x, y, "circle", FORO_HAT, FORO_HAT, FORO_HAT, None, npth=True)
        fp[f"H{k+1}"] = dict(valore="Foro M2,5 (HAT)", lib="SwimJig:MountingHole_M2.5")

    piste = []

    def pista(rete, *punti):
        piste.append((rete, [tuple(round(c, 4) for c in q) for q in punti]))
    # --- SWD ---
    pista("/VDD_T", (xe, vp), XY("J4", 1))
    pista("/SWDIO_T", (xa, v_alto), (xa, 13.0), (uA, 11.57), XY("R1", 1))
    pista("/SWDIO_H", XY("R1", 2), (uA, CONN_EXT))
    pista("/SWCLK_T", (xb, v_alto), (xb, vR3 - 1.4), (uB, 16.49), XY("R2", 1))
    pista("/SWCLK_H", XY("R2", 2), (uB, CONN_EXT))
    pista("/RESET_T", (xc, v_alto), XY("R3", 1))
    pista("/RESET_H", XY("R3", 2), (xc - 10.16, 9.0), (uC, 9.0 - (xc - 10.16 - uC)), (uC, CONN_EXT))
    pista("/GND", (xd, v_alto), (xd, vD), (uD, vD), (uD, CONN_EXT))
    # --- ricarica ---
    pista("/V5_PI", (u5, CONN_EXT), XY("F1", 1))
    pista("/V5_F", XY("F1", 2), XY("JP1", 1))
    pista("/V5_EXT", XY("JP1", 3), XY("J2", 1))
    pista("/V5_SEL", XY("JP1", 2), (xs, XY("JP1", 2)[1]), XY("J3", 2))
    pista("/V5_SEL", (xs, 33.0), XY("R4", 1))
    pista("/LED_A", XY("R4", 2), XY("D1", 1))
    pista("/VIN_T", (tp["TP6"][0], v_tp6), XY("J3", 1))
    vg = tp["TP7"][1] + 2.9              # linea di massa sotto TP6
    pista("/GND", (tp["TP7"][0], tp["TP7"][1]), (tp["TP7"][0], vg), (g[0], vg), XY("J2", 2))
    pista("/GND", (tp["TP7"][0], tp["TP7"][1]), (xd, tp["TP7"][1]), (xd, vp))
    pista("/GND", XY("D1", 2), (g[0], XY("D1", 2)[1]))
    # testi in rame (in KiCad su F.Cu): sono riferimenti, non serigrafia
    testi = [dict(s="1", cx=5.6, cy=6.4, h=2.6, nota="pin 1 del connettore"),
             dict(s="USB->", cx=52.0, cy=16.0, h=2.6, nota="lato USB/Ethernet del Pi"),
             dict(s="JIG 0.5", cx=50.0, cy=44.0, h=3.2, nota="controllo del verso")]

    return dict(tag=t, W=W, H=H, x0=x0, y0=y0, x1=x1, y1=y1, tp=tp, pads=p, fp=fp, piste=piste, avvisi=avvisi,
                bordo=(0.0, 0.0, HAT_W, HAT_H), battute=battute, appoggi=appoggi, testi=testi, col=col, vp=vp,
                param=dict(FORO_POGO=FORO_POGO, LARG_PISTA=LARG_PISTA, ALT_BATTUTE=ALT_BATTUTE),
                conn=dict(cx=CONN_CX, ext=CONN_EXT, int=CONN_INT, usati=usati), g=g, vD=vD, vR3=vR3,
                uA=uA, uB=uB, uC=uC, uD=uD, u5=u5)


if __name__ == "__main__":
    m = costruisci()
    print("tag", round(m["W"], 3), "x", round(m["H"], 3), "HAT", m["bordo"])
    for a in m["avvisi"]:
        print("AVVISO", a)
