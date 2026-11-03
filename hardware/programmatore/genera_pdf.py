"""Genera i PDF dell'adattatore dal modello geometrico (modello.py, che legge il PCB del tag).

  Programmatore_SwimTag_v0.4.pdf     documento unico (spiegazione, schema, distinta, stampe 1:1, procedura)
  stampa/rame_speculare_1a1.pdf      solo le copie del rame, speculare, per il toner transfer
  stampa/componenti_1a1.pdf          solo la pagina non speculare (posizioni e serigrafia)

Uso:  python genera_pdf.py        (serve PyMuPDF: pip install pymupdf; per le immagini KiCad serve kicad-cli)
"""
import os
import subprocess
import sys
from pathlib import Path

import fitz

from modello import QUI, FORO_POGO, LARG_PISTA, ALT_BATTUTE, HAT_FORI, costruisci
from pdfbase import (A4, MM, NERO, BIANCO, GRIGIO, GRIGIO_CH, ROSSO, VERDE, BLU, ARANCIO, GIALLO, Doc, Mappa, testo,
                     testo_speculare, tl, reg_font, fname, wrap)

NOME_PDF = QUI / "Programmatore_SwimTag_v0.4.pdf"
KICAD_CLI = os.environ.get("KICAD_CLI", str(Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"))
PERNO = 4.0     # altezza della punta del pogo libero sopra la basetta (mm) = ALT_BATTUTE + compressione
COMPR = PERNO - ALT_BATTUTE
PI_PIN = {  # nome del segnale: (GPIO, pin fisico)
    "SWDIO": ("GPIO24", 18), "SWCLK": ("GPIO25", 22), "RESET": ("GPIO18", 12), "GND": ("-", 20), "5V": ("-", 2)}


# ---------------------------------------------------------------- disegni del PCB
def disegna_rame(M, m, col=NERO, punti=True, testi=True, w_extra=0.0):
    for rete, pts in m["piste"]:
        for a, b in zip(pts, pts[1:]):
            M.L(a, b, col=col, w=LARG_PISTA + w_extra, cap=1)
    for q in m["pads"]:
        if q["npth"]:
            M.C((q["x"], q["y"]), 1.6, fill=col)      # segno di centro: viene asportato dalla foratura da 2,75 mm
            continue
        if q.get("smd"):
            M.R(q["x"] - q["w"] / 2, q["y"] - q["h"] / 2, q["x"] + q["w"] / 2, q["y"] + q["h"] / 2, fill=col, col=None)
        elif q["forma"] == "oval":
            M.OV((q["x"], q["y"]), q["w"], q["h"], fill=col)
        else:
            M.C((q["x"], q["y"]), q["w"], fill=col)
    if punti:
        for q in m["pads"]:
            if not q.get("smd"):
                M.C((q["x"], q["y"]), 0.5, fill=BIANCO)
    if testi:
        for t in m["testi"]:
            M.T(t["cx"], t["cy"] + t["h"] / 2, t["s"], t["h"] * MM / 0.72, "b", col, "c")


def segni_taglio(M, m, col=NERO):
    xmin, ymin, xmax, ymax = m["bordo"]
    d, l = 1.0, 4.0
    for (cx, cy, sx, sy) in ((xmin, ymin, -1, -1), (xmax, ymin, 1, -1), (xmin, ymax, -1, 1), (xmax, ymax, 1, 1)):
        M.L((cx + sx * d, cy + sy * d), (cx + sx * (d + l), cy + sy * d), col=col, w=0.2)
        M.L((cx + sx * d, cy + sy * d), (cx + sx * d, cy + sy * (d + l)), col=col, w=0.2)


def barra_scala(pg, x, y, lungh_mm=50, speculare=False, verticale=False):
    L = lungh_mm * MM
    if not verticale:
        pg.draw_line((x, y), (x + L, y), color=NERO, width=1.2)
        for k in range(0, lungh_mm + 1, 5):
            h = 6 if k % 10 == 0 else 3.5
            pg.draw_line((x + k * MM, y - h), (x + k * MM, y + h), color=NERO, width=0.8)
        pg.draw_line((x, y - 9), (x, y + 9), color=NERO, width=1.2)
        pg.draw_line((x + L, y - 9), (x + L, y + 9), color=NERO, width=1.2)
        testo(pg, x + L / 2, y + 20, f"{lungh_mm} mm", 8, "b", NERO, "c")
    else:
        pg.draw_line((x, y), (x, y + L), color=NERO, width=1.2)
        for k in range(0, lungh_mm + 1, 5):
            h = 6 if k % 10 == 0 else 3.5
            pg.draw_line((x - h, y + k * MM), (x + h, y + k * MM), color=NERO, width=0.8)
        pg.draw_line((x - 9, y), (x + 9, y), color=NERO, width=1.2)
        pg.draw_line((x - 9, y + L), (x + 9, y + L), color=NERO, width=1.2)


def pagina_rame(d, m):
    """Pagina 1:1 del rame, SPECULARE (il rame e' sopra: la carta va girata sul rame), nero pieno su bianco."""
    pg = d.nuova("Stampa 1:1 rame speculare")
    xmin, ymin, xmax, ymax = m["bordo"]
    bw, bh = xmax - xmin, ymax - ymin
    marg, zona_alta, gap = 26, 66, 7.0 * MM
    cols = max(int((A4[0] - 2 * marg + gap) // (bw * MM + gap)), 1)
    righe = max(int((A4[1] - marg - zona_alta - 30 + gap) // (bh * MM + gap)), 1)
    testo(pg, marg, 22, "RAME SPECULARE - STAMPARE AL 100% (scala reale), NERO PIENO", 11, "b", ROSSO)
    testo(pg, marg, 35, "Disattivare 'adatta alla pagina' / 'riduci'. Misurare la barra: deve essere 50,0 mm (+-0,3). Laser, carta lucida, toner al massimo.", 7.5, "r")
    testo(pg, marg, 45, "Il rame e' SUL LATO COMPONENTI (sopra): la carta si gira sul rame. Dopo il trasferimento 'JIG 0.4' e 'USB->' si leggono dritte e il pin 1 e' a sinistra.", 7.5, "r")
    barra_scala(pg, marg + 12, 62, 50)
    testo(pg, marg + 12 + 50 * MM + 10, 65, "<- barra di controllo scala: 50 mm", 7.5, "r", GRIGIO)
    barra_scala(pg, A4[0] - 22, 40, 50, verticale=True)
    for (cx, cy) in ((14, 14), (A4[0] - 14, 14), (14, A4[1] - 14), (A4[0] - 14, A4[1] - 14)):
        pg.draw_line((cx - 9, cy), (cx + 9, cy), color=NERO, width=0.7)
        pg.draw_line((cx, cy - 9), (cx, cy + 9), color=NERO, width=0.7)
        pg.draw_circle((cx, cy), 5, color=NERO, width=0.7)
    tot_w = cols * bw * MM + (cols - 1) * gap
    x00, y00, n = (A4[0] - tot_w) / 2, marg + zona_alta, 0
    for r in range(righe):
        for c in range(cols):
            M = Mappa(pg, x00 + c * (bw * MM + gap), y00 + r * (bh * MM + gap), MM, xmin, ymin, mir_w=bw)
            disegna_rame(M, m)
            segni_taglio(M, m, GRIGIO)
            n += 1
    testo(pg, marg, A4[1] - 14, f"SwimTag programmatore v0.4 (HAT) - {n} copie 1:1 della stessa basetta ({bw:.1f} x {bh:.1f} mm) - generato da genera_pdf.py", 6.5, "r", GRIGIO)
    return n, (bw, bh)


def pagina_componenti(d, m, det=False):
    """Posizioni, viste da sopra (NON speculare). det=False: 1:1 con le sigle; det=True: 2:1 con tutte le etichette."""
    S = MM * (2.0 if det else 1.0)
    pg = d.nuova("Posizioni dei componenti " + ("2:1" if det else "1:1"))
    xmin, ymin, xmax, ymax = m["bordo"]
    ox, oy = 40, (92 if det else 70)
    M = Mappa(pg, ox, oy, S, xmin, ymin)
    titolo = "POSIZIONI - INGRANDIMENTO 2:1 (vista dall'alto)" if det else "POSIZIONI 1:1 (vista dall'alto, NON speculare)"
    testo(pg, 40, 26, titolo, 12, "b", (0.05, 0.2, 0.45))
    if det:
        testo(pg, 40, 40, "Pagina di consultazione (NON in scala 1:1) con tutte le etichette. Per costruire usare la pagina 1:1 precedente.", 8)
        barra_scala(pg, 48, 58, 50)
    else:
        testo(pg, 40, 40, "Stampare al 100%. Rame in grigio, tag tratteggiato blu. Etichette complete nella pagina 2:1 successiva. Barra: 50 mm.", 8)
        barra_scala(pg, 48, 56, 50)
    M.R(xmin, ymin, xmax, ymax, fill=None, col=NERO, w=0.25)
    disegna_rame(M, m, col=GRIGIO_CH, punti=False, testi=False)
    x0, y0, x1, y1 = m["x0"], m["y0"], m["x1"], m["y1"]
    M.R(x0, y0, x1, y1, fill=None, col=BLU, w=0.3, dash="[3 2] 0")
    fs = 6 if det else 4.5
    M.T((x0 + x1) / 2, y0 + 8.5, "TAG", 9 if det else 7, "b", BLU, "c")
    if det:
        M.T((x0 + x1) / 2, y0 + 10.2, "(a faccia in giu')", 6.5, "r", BLU, "c")
    # connettore: fila esterna con pad, fila interna con le code tagliate (croci)
    cn = m["conn"]
    M.R(cn["cx"] - 25.4 - 1.27, cn["ext"] - 1.27 - 0.5, cn["cx"] + 25.4 + 1.27, cn["int"] + 1.27 + 0.5, fill=None, col=ROSSO, w=0.2, dash="[2 2] 0")
    for q in m["pads"]:
        ref = q["ref"]
        if q["npth"]:
            M.C((q["x"], q["y"]), 2.75, fill=None, col=NERO, w=0.3)
            continue
        if q.get("smd"):
            M.R(q["x"] - 1.27, q["y"] - 1.27, q["x"] + 1.27, q["y"] + 1.27, fill=(0.9, 0.9, 0.9), col=NERO, w=0.2)
            M.T(q["x"] + 1.5, q["y"] + 0.5, ref, fs, "b", NERO)
        else:
            M.C((q["x"], q["y"]), 1.0, fill=BIANCO, col=NERO, w=0.15)
            if ref[0] == "S":
                M.T(q["x"] + 1.3, q["y"] + 0.5, ref, fs, "b", NERO)
            if ref[0] == "P":
                M.T(q["x"] + 1.3, q["y"] + 0.5 if ref in ("P6", "P7") else q["y"] - 1.9, ref, fs, "b", NERO)
    for c in range(1, 21):
        u = round(cn["cx"] + (c - 10.5) * 2.54, 4)
        M.L((u - 0.5, cn["int"] - 0.5), (u + 0.5, cn["int"] + 0.5), col=GRIGIO, w=0.12)
        M.L((u - 0.5, cn["int"] + 0.5), (u + 0.5, cn["int"] - 0.5), col=GRIGIO, w=0.12)
    M.R(cn["cx"] - 25.4 - 0.6, cn["int"] - 0.6, cn["cx"] - 25.4 + 0.6, cn["int"] + 0.6, fill=None, col=ROSSO, w=0.3)
    M.T(cn["cx"] - 25.4 - 0.6, cn["int"] + 2.4, "pin 1", fs, "b", ROSSO, "s")
    for k in (1, 2, 3, 4):
        a = [q for q in m["pads"] if q["ref"] == f"R{k}" and q["num"] == "1"][0]
        b2 = [q for q in m["pads"] if q["ref"] == f"R{k}" and q["num"] == "2"][0]
        M.L((a["x"], a["y"]), (b2["x"], b2["y"]), col=(1, 0.88, 0.4), w=2.2)
        M.T((a["x"] + b2["x"]) / 2 + 1.4, (a["y"] + b2["y"]) / 2 + 0.5, f"R{k}", fs, "b", NERO)
    def lab(ref, num, s, dx=2.0, dy=0.4, k="r", col=NERO, anc="s"):
        q = [q for q in m["pads"] if q["ref"] == ref and q["num"] == str(num)][0]
        M.T(q["x"] + dx, q["y"] + dy, s, fs, k, col, anc)
    if det:
        for pin, nome in ((2, "5V"), (12, "RESET"), (18, "SWDIO"), (20, "GND"), (22, "SWCLK")):
            q = [q for q in m["pads"] if q["ref"] == "J1" and q["num"] == str(pin)][0]
            M.T(q["x"], q["y"] - 1.5, f"{pin}", fs, "b", ROSSO, "c")
            M.T(q["x"], q["y"] + 3.2 + (1.4 if pin in (18, 22) else 0), nome, 4.2, "b", NERO, "c")
        lab("J4", 1, "J4 VDD: SOLO TESTER", -1.4, 0.4, "b", ROSSO, "d")
        lab("J3", 1, "J3 mA", 0, -1.8, "b", NERO, "c")
        lab("J3", 2, "J3 mA", 0, 3.2, "b", NERO, "c")
        lab("JP1", 1, "JP1 1 (Pi)", 1.5, 0.4, "b")
        lab("JP1", 2, "2", 1.5, 0.4, "b")
        lab("JP1", 3, "3 (EXT)", 1.5, 0.4, "b")
        lab("F1", 1, "F1 PTC", 1.8, 2.8, "b")
        lab("J2", 1, "J2 +5V EXT", 1.5, 0.4, "b")
        lab("J2", 2, "GND", -1.4, 0.4, "b", NERO, "d")
        lab("R4", 1, "R4", 1.5, 0.3, "b")
        lab("D1", 1, "D1 LED", 1.5, 0.3, "b")
        M.T(xmin + 12, ymin + 12, "JP1: 1-2 = carica dal Pi / 2-3 = 5V esterno / nessun ponticello = OFF", 5.5, "b", ROSSO)
        M.T(xmax - 4, ymax - 3, "LATO USB/ETHERNET ->", 7, "b", ROSSO, "d")
    else:
        M.T(xmax - 3, ymax - 2, "USB/ETH ->", 6, "b", ROSSO, "d")
    lx = ox + (xmax - xmin) * S + 14
    if lx > A4[0] - 190:
        lx, yy = 40, oy + (ymax - ymin) * S + 24
    else:
        yy = oy + 8
    righe_leg = ["LEGENDA", "P1..P7  pogo (ricettacolo + molla)", "S1,S2,S3  battute: pin 0,64 mm (lati sx e alto)", "S4,S5,S6  sedi degli appoggi (blocchetti 2,5 mm incollati)",
                 "R1..R3, R4  1 kohm (R2, R3 lunghe: ponti)", "J1  header FEMMINA 2x20, da sotto; solo pin pari saldati", "J4  pin VDD, SOLO TESTER",
                 "J3  header 1x2: tester in mA (o ponticello)", "JP1  header 1x3 + ponticello (carica)", "J2  header 1x2: +5V EXT / GND",
                 "F1  PTC radiale 0,1 A", "D1  LED verde 3 mm", "4 fori M2,5 (2,75 mm): specifica HAT", "",
                 "MAI IL 3,3 V DEL PI SUL VDD DEL TAG", "JP1 senza ponticello = CARICA OFF"]
    for i, riga in enumerate(righe_leg):
        rosso = riga.startswith("MAI") or riga.startswith("JP1 senza")
        testo(pg, lx, yy, riga, 8 if i == 0 else 7.2, "b" if i == 0 or rosso else "r", ROSSO if rosso else NERO)
        yy += 10.5
    return pg


def pagina_fori(d, m):
    pg = d.nuova("Mappa dei fori")
    xmin, ymin, xmax, ymax = m["bordo"]
    M = Mappa(pg, 40, 76, MM, xmin, ymin)
    testo(pg, 40, 26, "MAPPA DEI FORI 1:1 (vista dall'alto, lato rame)", 12, "b", (0.05, 0.2, 0.45))
    testo(pg, 40, 40, "Ogni foro porta la lettera del diametro. Forare dal lato rame verso il basso. Stampare al 100%.", 8)
    barra_scala(pg, 48, 58, 50)
    M.R(xmin, ymin, xmax, ymax, fill=None, col=NERO, w=0.25)
    disegna_rame(M, m, col=GRIGIO_CH, punti=False, testi=False)
    classi = {}
    for q in m["pads"]:
        if not q.get("smd"):
            classi.setdefault(round(q["foro"], 2), []).append(q)
    lettere = {dia: "ABCDEFGH"[i] for i, dia in enumerate(sorted(classi))}
    usi = {0.8: "R1-R4 (piedino 0,5-0,6 mm) e battute S1-S3 (pin 0,64 mm a pressione)",
           1.0: "connettore J1 (solo pin pari), header 1x1/1x2/1x3, PTC, LED", 1.5: "ricettacoli dei pogo P1-P7 (VERIFICARE sul pezzo!)",
           2.75: "viti M2,5 dell'HAT (angoli)"}
    for dia, qs in classi.items():
        for q in qs:
            M.C((q["x"], q["y"]), 1.1 if dia < 2 else 2.75, fill=(1, 1, 0.75) if dia < 2 else None, col=NERO, w=0.2)
            M.T(q["x"], q["y"] + 0.5, lettere[dia], 5.5 if dia < 2 else 8, "b", ROSSO, "c")
    lx = 40 + (xmax - xmin) * MM + 16
    yy = 130
    if lx > A4[0] - 170:
        lx, yy = 40, 76 + (ymax - ymin) * MM + 30
    testo(pg, lx, yy, "Foro   Diametro   N.   Uso", 8, "b")
    yy += 12
    for dia in sorted(classi):
        n = len(classi[dia])
        testo(pg, lx, yy, f"  {lettere[dia]}      {dia:.2f} mm    {n:>2}", 8, "b", ROSSO)
        righe = wrap(usi.get(dia, ""), 7.5, A4[0] - lx - 130 if lx > 100 else 400, "r")
        for j, ln in enumerate(righe):
            testo(pg, lx + 100, yy + j * 9, ln, 7.5)
        yy += 9 * max(1, len(righe)) + 7
    testo(pg, lx, yy + 8, "Punte: 0,8 / 1,0 / 1,5 / 2,75 (o 3,0) mm.", 7.5, "b")
    testo(pg, lx, yy + 18, "Foro da 1,5 mm: provare su uno scarto con il ricettacolo.", 7.5)
    testo(pg, lx, yy + 28, "Fori del connettore J1: SOLO sulla fila esterna (pin pari);", 7.5)
    testo(pg, lx, yy + 38, "la fila interna non ha fori (code tagliate).", 7.5)
    testo(pg, lx, yy + 52, "Totale fori: %d" % sum(len(v) for v in classi.values()), 7.5, "b")
    return pg, lettere


def fig_blocchi(pg, x, y, w):
    def box(bx, by, bw, bh, t, sub, fill):
        pg.draw_rect(fitz.Rect(bx, by, bx + bw, by + bh), color=NERO, fill=fill, width=1.2)
        testo(pg, bx + bw / 2, by + 16, t, 10, "b", NERO, "c")
        for i, s in enumerate(sub):
            testo(pg, bx + bw / 2, by + 30 + 10 * i, s, 7.5, "r", NERO, "c")
    box(x, y + 5, 138, 100, "TAG SwimTimer", ["nRF52840 (E73), cella 40 mAh", "5 piazzole SWD (O 2,0)", "2 contatti ricarica (O 2,5)", "lato sotto, a faccia in giu'"], (0.88, 0.95, 1))
    box(x + 168, y + 5, 150, 100, "ADATTATORE = HAT 65 x 56,5", ["7 pogo + battute di centraggio", "3 x 1 kohm in serie (SWD)", "ricarica: PTC, ponticello, LED", "header femmina 2x20 da sotto"], (1, 0.97, 0.85))
    box(x + w - 138, y + 5, 138, 100, "Raspberry Pi 3 / 4", ["OpenOCD, bit-bang su GPIO", "GPIO24 SWDIO  GPIO25 SWCLK", "GPIO18 reset  +  GND", "5 V (pin 2) per la carica"], (0.9, 1, 0.9))
    for (ax, bx2, t) in ((x + 138, x + 168, "pogo"), (x + 318, x + w - 138, "2x20")):
        pg.draw_line((ax, y + 55), (bx2, y + 55), color=NERO, width=2)
        testo(pg, (ax + bx2) / 2, y + 48, t, 7, "r", NERO, "c")
    testo(pg, x + w / 2, y + 125, "Il tag NON viene alimentato dall'adattatore: usa la sua cella. Il 3,3 V del Pi non va mai sul VDD del tag.", 8, "b", ROSSO, "c")


def fig_schema(pg, x, y, w):
    def R(rx, ry, t="1k"):
        pg.draw_rect(fitz.Rect(rx - 10, ry - 4, rx + 10, ry + 4), color=NERO, width=1)
        testo(pg, rx, ry - 7, t, 7, "r", NERO, "c")
    def ln(a, b, col=NERO, wd=1):
        pg.draw_line(a, b, color=col, width=wd)
    pg.draw_rect(fitz.Rect(x, y, x + 95, y + 330), color=(0.1, 0.25, 0.8), fill=(0.93, 0.96, 1), width=1.2)
    testo(pg, x + 47, y + 14, "TAG (piazzole)", 9, "b", BLU, "c")
    segn = ["VDD", "SWDIO", "SWCLK", "RESET", "GND"]
    ys = [60, 90, 120, 150, 180]
    for i, (n, yy) in enumerate(zip(segn, ys)):
        testo(pg, x + 88, y + yy + 3, n, 8, "b", NERO, "d")
        ln((x + 95, y + yy), (x + 125, y + yy))
        testo(pg, x + 108, y + yy - 4, "P" + str(i + 1), 6.5, "r", GRIGIO, "c")
    xr = x + 190
    for i in (1, 2, 3):
        yy = y + ys[i]
        ln((x + 125, yy), (xr - 12, yy))
        R(xr, yy, "R%d 1k" % i)
        ln((xr + 10, yy), (x + 300, yy))
    ln((x + 125, y + ys[0]), (x + 300, y + ys[0]))
    ln((x + 125, y + ys[4]), (x + 300, y + ys[4]))
    pg.draw_rect(fitz.Rect(x + 300, y + 38, x + w, y + 195), color=(0.1, 0.5, 0.2), fill=(0.92, 1, 0.92), width=1.2)
    testo(pg, x + 300 + (w - 300) / 2, y + 52, "J1 femmina 2x20 = Raspberry Pi", 8.5, "b", VERDE, "c")
    pi = [("J4: VDD solo tester (NON al Pi)", ys[0], ROSSO), ("pin 18  GPIO24  SWDIO", ys[1], NERO), ("pin 22  GPIO25  SWCLK", ys[2], NERO),
          ("pin 12  GPIO18  RESET", ys[3], NERO), ("pin 20  GND", ys[4], NERO)]
    for t, yy, c in pi:
        testo(pg, x + 308, y + yy + 3, t, 7.5, "b", c)
    yc = y + 235
    testo(pg, x + 100, yc - 18, "Ricarica (pogo P6 VIN e P7 GND, in parallelo a SWD, massa comune)", 8.5, "b", (0.05, 0.2, 0.45))
    ln((x + 95, yc + 10), (x + 125, yc + 10))
    testo(pg, x + 88, yc + 13, "VIN P6", 8, "b", NERO, "d")
    ln((x + 95, yc + 50), (x + 125, yc + 50))
    testo(pg, x + 88, yc + 53, "GND P7", 8, "b", NERO, "d")
    ln((x + 125, yc + 10), (x + 150, yc + 10))
    pg.draw_rect(fitz.Rect(x + 150, yc + 2, x + 190, yc + 18), color=NERO, width=1)
    testo(pg, x + 170, yc - 2, "J3 mA", 7, "b", NERO, "c")
    testo(pg, x + 170, yc + 13, "tester", 6.5, "r", NERO, "c")
    ln((x + 190, yc + 10), (x + 270, yc + 10))
    pg.draw_circle((x + 215, yc + 10), 2, color=NERO, fill=NERO)
    testo(pg, x + 222, yc + 27, "V5_SEL", 6.5, "r")
    ln((x + 215, yc + 10), (x + 215, yc + 30))
    R(x + 215, yc + 40, "R4 1k")
    pg.draw_rect(fitz.Rect(x + 211, yc + 30, x + 219, yc + 50), color=NERO, fill=(1, 1, 1), width=1)
    ln((x + 215, yc + 50), (x + 215, yc + 60))
    pg.draw_polyline([(x + 207, yc + 60), (x + 223, yc + 60), (x + 215, yc + 72), (x + 207, yc + 60)], color=NERO, fill=(0.6, 1, 0.6), width=1)
    testo(pg, x + 232, yc + 68, "D1 LED verde (parallelo)", 7, "r")
    ln((x + 215, yc + 72), (x + 215, yc + 80))
    ln((x + 125, yc + 50), (x + 125, yc + 80))
    ln((x + 125, yc + 80), (x + 215, yc + 80))
    pg.draw_rect(fitz.Rect(x + 270, yc - 12, x + 340, yc + 50), color=NERO, fill=(1, 0.97, 0.85), width=1.2)
    testo(pg, x + 305, yc + 2, "JP1 (1x3)", 7.5, "b", NERO, "c")
    testo(pg, x + 305, yc + 15, "2 = comune", 6.5, "r", NERO, "c")
    testo(pg, x + 305, yc + 26, "ponticello 1-2: Pi", 6.5, "r", NERO, "c")
    testo(pg, x + 305, yc + 36, "ponticello 2-3: EXT", 6.5, "r", NERO, "c")
    testo(pg, x + 305, yc + 46, "vuoto: OFF", 6.5, "b", ROSSO, "c")
    ln((x + 340, yc - 2), (x + 375, yc - 2))
    pg.draw_rect(fitz.Rect(x + 375, yc - 9, x + 410, yc + 5), color=NERO, width=1)
    testo(pg, x + 392, yc + 2, "F1 PTC", 6.5, "b", NERO, "c")
    ln((x + 410, yc - 2), (x + 440, yc - 2))
    testo(pg, x + 443, yc + 1, "J1 pin 2 = 5V del Pi", 7.5, "b")
    ln((x + 340, yc + 36), (x + 440, yc + 36))
    testo(pg, x + 443, yc + 39, "J2 +5V esterno", 7.5, "b")
    ln((x + 125, yc + 80), (x + 440, yc + 80))
    testo(pg, x + 443, yc + 83, "J1 pin 20 = GND (e J2 GND)", 7.5, "b")
    testo(pg, x, yc + 108, "GND unico sull'adattatore; nessun altro pin del connettore e' collegato.", 7.5, "r", GRIGIO)


def fig_sezione(pg, x, y, w):
    s = 17.0
    x0 = x + 30
    zb = y + 190
    def Z(z): return zb - z * s
    testo(pg, x, y + 12, "Sezione laterale (quote da verificare sui pezzi arrivati)", 8.5, "b")
    testo(pg, x, y + 24, "Rame e componenti sullo stesso lato (sopra). Punta libera = piano del tag + compressione. Il tag poggia sugli appoggi, non sui pogo.", 8)
    testo(pg, x, y + 35, "Testa del ricettacolo a H_r = %.1f mm - L sopra la basetta (L = quanto la punta sporge dal ricettacolo, molla a riposo)." % PERNO, 8)
    pg.draw_rect(fitz.Rect(x0, Z(0), x0 + 400, Z(-1.6)), color=NERO, fill=(0.75, 0.85, 0.7), width=1)
    pg.draw_rect(fitz.Rect(x0, Z(0) - 2, x0 + 400, Z(0)), color=NERO, fill=(0.85, 0.6, 0.3), width=0.3)
    testo(pg, x0, Z(-1.6) + 14, "basetta FR4 1,6 mm, rame (arancio) SOPRA", 7.5)
    xp, hr = x0 + 180, 1.0
    pg.draw_rect(fitz.Rect(xp - 12, Z(hr), xp + 12, Z(-3.0)), color=NERO, fill=(0.8, 0.8, 0.85), width=1)
    pg.draw_rect(fitz.Rect(xp - 4, Z(ALT_BATTUTE), xp + 4, Z(hr)), color=NERO, fill=(0.95, 0.85, 0.3), width=1)
    pg.draw_line((xp - 9, Z(PERNO)), (xp + 9, Z(PERNO)), color=ROSSO, width=1.2, dashes="[3 2] 0")
    pg.draw_polyline([(xp - 18, Z(0)), (xp - 12, Z(0.6)), (xp + 12, Z(0.6)), (xp + 18, Z(0))], color=NERO, fill=(0.7, 0.7, 0.7), width=0.5)
    testo(pg, xp + 22, Z(0.5), "saldatura SOPRA (lato rame)", 7.5)
    testo(pg, xp - 18, Z(-2.6), "coda del ricettacolo tagliata (<= 3 mm sotto)", 7.5, "r", NERO, "d")
    testo(pg, xp - 18, Z(1.8), "pogo P75-E2", 7.5, "r", NERO, "d")
    testo(pg, xp + 12, Z(PERNO) - 3, "punta libera", 7.5, "b", ROSSO)
    pg.draw_rect(fitz.Rect(x0 + 40, Z(ALT_BATTUTE + 0.8), x0 + 320, Z(ALT_BATTUTE)), color=BLU, fill=(0.8, 0.88, 1), width=1.2)
    testo(pg, x0 + 46, Z(ALT_BATTUTE) - 3.5, "TAG 0,8 mm, a faccia in giu' (piazzole sotto)", 7.5, "b", BLU)
    for xx in (x0 + 90, x0 + 270):
        yy = Z(ALT_BATTUTE + 0.8)
        pg.draw_line((xx, yy - 40), (xx, yy - 2), color=ROSSO, width=2)
        pg.draw_polyline([(xx - 4, yy - 8), (xx, yy - 1), (xx + 4, yy - 8)], color=ROSSO, width=2)
    testo(pg, x0 + 180, Z(ALT_BATTUTE + 0.8) - 46, "pressione dall'alto (dito, coperchio o elastico)", 8, "b", ROSSO, "c")
    for xx in (x0 + 70, x0 + 290):
        pg.draw_rect(fitz.Rect(xx - 1.27 * s * 0.8, Z(ALT_BATTUTE), xx + 1.27 * s * 0.8, Z(0) - 2), color=NERO, fill=(0.35, 0.35, 0.35), width=1)
        testo(pg, xx, Z(ALT_BATTUTE / 2) + 3, "appoggio", 6, "b", BIANCO, "c")
    xb = x0 + 330
    pg.draw_line((xb, Z(0)), (xb, Z(4.4)), color=NERO, width=3)
    testo(pg, xb + 6, Z(2.0), "battuta: pin 0,64 mm", 7, "r")
    def quota(xx, z0, z1, t):
        pg.draw_line((xx, Z(z0)), (xx, Z(z1)), color=ROSSO, width=0.8)
        for z in (z0, z1):
            pg.draw_line((xx - 4, Z(z)), (xx + 4, Z(z)), color=ROSSO, width=0.8)
        testo(pg, xx + 7, (Z(z0) + Z(z1)) / 2 + 3, t, 7.5, "b", ROSSO)
    quota(x0 + 345, 0, ALT_BATTUTE, f"{ALT_BATTUTE:.1f} mm piano tag")
    quota(x0 + 345, ALT_BATTUTE, PERNO, f"{COMPR:.1f} mm compress.")
    pg.draw_line((xp + 9, Z(PERNO)), (x0 + 345, Z(PERNO)), color=ROSSO, width=0.5, dashes="[2 2] 0")
    testo(pg, x, y + 262, "Condizione: la testa del ricettacolo non deve superare 2,0 mm sopra la basetta (altrimenti tocca il tag).", 8, "r", GRIGIO)


def fig_pianta(pg, x, y, w, m):
    s = 7.0
    x0, y0, x1, y1 = m["x0"], m["y0"], m["x1"], m["y1"]
    M = Mappa(pg, x + 30, y + 40, s, x0 - 9, y0 - 6.5)
    testo(pg, x, y + 12, "Pianta del centraggio (vista dall'alto, 7 pt per mm)", 8.5, "b")
    testo(pg, x, y + 24, "Il tag poggia sui blocchetti S4-S6 e si spinge contro i pin di battuta S1, S2 (bordo sinistro) e S3 (bordo alto).", 8)
    M.R(x0 - 9, y0 - 6.5, x1 + 9, y1 + 6, fill=(0.93, 0.97, 0.93), col=NERO, w=0.15)
    M.R(x0, y0, x1, y1, fill=(0.85, 0.9, 1.0), col=BLU, w=0.2)
    for ref, px, py, lato in m["battute"]:
        M.R(px - 0.32, py - 0.32, px + 0.32, py + 0.32, fill=(0.2, 0.2, 0.2), col=NERO, w=0.1)
        M.C((px, py), 2.0, fill=None, col=GRIGIO, w=0.15)
        M.T(px + 1.4, py + 0.5, ref, 6.5, "b", NERO)
    for ref, px, py in m["appoggi"]:
        M.R(px - 1.27, py - 1.27, px + 1.27, py + 1.27, fill=(0.75, 0.75, 0.75), col=NERO, w=0.15)
        M.T(px + 1.5, py + 0.5, ref, 6.5, "b", NERO)
    for q in m["pads"]:
        if q["ref"][0] == "P":
            if q["forma"] == "oval":
                M.OV((q["x"], q["y"]), q["w"], q["h"], fill=(0.95, 0.8, 0.3), col=NERO)
            else:
                M.C((q["x"], q["y"]), q["w"], fill=(0.95, 0.8, 0.3), col=NERO)
            M.C((q["x"], q["y"]), 1.0, fill=BIANCO, col=NERO, w=0.1)
    M.L((x0 + 14, y0 + 6.5), (x0 + 3, y0 + 2.5), col=ROSSO, w=0.25)
    M.T(x0 + 4, y0 + 8.7, "spingere verso l'angolo", 6.5, "b", ROSSO)
    for k in range(0, int(m["H"] // 2.54) + 1):
        M.L((x0, y0 + k * 2.54), (x0 + (0.9 if k % 5 else 1.8), y0 + k * 2.54), col=ARANCIO, w=0.15)
    for k in range(0, int(m["W"] // 2.54) + 1):
        M.L((x0 + k * 2.54, y0), (x0 + k * 2.54, y0 + (0.9 if k % 5 else 1.8)), col=ARANCIO, w=0.15)
    M.T(x0 - 8.6, y0 + 13, "gioco 0,1 mm", 6, "r", ROSSO)
    M.T(x0 - 8.6, y0 + 14.1, "battuta-bordo", 6, "r", ROSSO)
    M.T((x0 + x1) / 2, y1 - 1.0, "TAG", 8, "b", BLU, "c")
    tx = x + 330
    for i, r in enumerate(["Tolleranza richiesta: +-0,3 mm.", "Gioco battuta-bordo 0,1 mm,", "taglio del tag +-0,1 mm,", "foratura +-0,1 mm:", "totale ~ +-0,3 mm sulle piazzole.", "",
                           "Le piazzole del tag sono O 2,0 mm:", "la punta del pogo (~1 mm) cade", "comunque dentro la piazzola.", "",
                           "Tacche arancio = serigrafia del tag", "ogni 2,54 mm sui bordi sinistro e alto:", "controllo a vista del centraggio."]):
        testo(pg, tx, y + 60 + i * 11, r, 8, "b" if i == 0 else "r", ARANCIO if r.startswith("Tacche") else NERO)


def fig_innesto(pg, x, y, w, m):
    """Innesto sul Pi: pianta (Pi 85 x 56 con l'HAT sopra) e sezione laterale con i distanziali da 11 mm."""
    s = 4.6
    testo(pg, x, y + 12, "Innesto sul Raspberry Pi 3 / 4 (stessa posizione del connettore e dei fori)", 8.5, "b")
    ox, oy = x + 6, y + 30
    M = Mappa(pg, ox, oy, s, 0, 0)
    M.R(0, 0, 85, 56, fill=(0.85, 0.95, 0.85), col=NERO, w=0.3)
    M.R(0, 0, 65, 56.5, fill=(1, 0.97, 0.85), col=ROSSO, w=0.3, dash="[3 2] 0")
    M.R(66, 3, 85, 18, fill=(0.7, 0.7, 0.8), col=NERO, w=0.2)
    M.R(66, 20, 85, 37, fill=(0.7, 0.7, 0.8), col=NERO, w=0.2)
    M.T(75.5, 11, "USB", 7, "b", NERO, "c")
    M.T(75.5, 30, "Ethernet", 7, "b", NERO, "c")
    M.T(75.5, 45, "USB/ETH ->", 7, "b", ROSSO, "c")
    M.R(32.5 - 25.4 - 1.27, 3.5 - 2.54, 32.5 + 25.4 + 1.27, 3.5 + 2.54, fill=(0.2, 0.2, 0.2), col=NERO, w=0.2)
    for hx, hy in HAT_FORI:
        M.C((hx, hy), 2.75, fill=BIANCO, col=NERO, w=0.3)
    M.R(m["x0"], m["y0"], m["x1"], m["y1"], fill=(0.8, 0.88, 1), col=BLU, w=0.2)
    M.T((m["x0"] + m["x1"]) / 2, (m["y0"] + m["y1"]) / 2, "TAG", 8, "b", BLU, "c")
    M.T(1.5, 54.2, "SD", 7, "b", NERO)
    M.T(32.5, 1.6, "pin 2 ... pin 40 (pari, fila esterna)", 5, "r", WHITE if False else BIANCO, "c")
    M.R(8.37 - 0.9, 4.77 - 0.9, 8.37 + 0.9, 4.77 + 0.9, fill=ROSSO, col=None)
    M.T(11, 8.2, "pin 1", 6.5, "b", ROSSO)
    testo(pg, ox + 5 * s, oy + 60 * s + 2, "Pi (85 x 56 mm) con SD a sinistra; HAT tratteggiato (65 x 56,5 mm); connettore sul bordo alto.", 7.5)
    # sezione laterale
    sy = oy + 60 * s + 30
    sz = 7.0
    def Z(z): return sy + 14 * sz - z * sz
    def X(u): return ox + u * s
    pg.draw_rect(fitz.Rect(X(0), Z(0), X(85), Z(-1.4)), color=NERO, fill=(0.2, 0.55, 0.3), width=0.8)
    pg.draw_rect(fitz.Rect(X(66), Z(16), X(85), Z(0)), color=NERO, fill=(0.7, 0.7, 0.8), width=0.8)
    testo(pg, X(75.5), Z(8), "USB/ETH", 6.5, "b", NERO, "c")
    pg.draw_rect(fitz.Rect(X(7.1), Z(2.5), X(57.9), Z(0)), color=NERO, fill=(0.25, 0.25, 0.25), width=0.6)
    pg.draw_rect(fitz.Rect(X(7.1), Z(11.0), X(57.9), Z(2.5)), color=NERO, fill=(0.9, 0.9, 0.6), width=0.8)
    testo(pg, X(32.5), Z(6.2) + 2, "header femmina 8,5 mm sul maschio del Pi (2,5 mm di plastica)", 6, "b", NERO, "c")
    pg.draw_rect(fitz.Rect(X(0), Z(12.6), X(65), Z(11.0)), color=NERO, fill=(0.75, 0.85, 0.7), width=1)
    pg.draw_rect(fitz.Rect(X(0), Z(12.6), X(65), Z(12.6) + 2), color=NERO, fill=(0.85, 0.6, 0.3), width=0.3)
    for hx in (3.5, 61.5):
        pg.draw_rect(fitz.Rect(X(hx) - 4, Z(11.0), X(hx) + 4, Z(0)), color=NERO, fill=(0.8, 0.8, 0.85), width=0.8)
    pg.draw_rect(fitz.Rect(X(m["x0"]), Z(12.6) - 18, X(m["x1"]), Z(12.6) - 12), color=BLU, fill=(0.8, 0.88, 1), width=0.8)
    testo(pg, X(m["x1"]) + 6, Z(12.6) - 8, "tag + pogo (sopra l'HAT)", 6.5, "r", BLU)
    pg.draw_line((X(66), Z(11.0)), (X(70), Z(11.0)), color=ROSSO, width=0.8)
    pg.draw_line((X(66), Z(0)), (X(70), Z(0)), color=ROSSO, width=0.8)
    pg.draw_line((X(68), Z(0)), (X(68), Z(11.0)), color=ROSSO, width=0.8)
    testo(pg, X(66.6), Z(3.0) + 3, "11 mm = distanziali", 6.5, "b", ROSSO)
    testo(pg, X(66.6), Z(3.0) + 11, "M2,5 F-F", 6.5, "b", ROSSO)
    testo(pg, X(0), Z(-1.4) + 14, "Sezione: i distanziali (4, ai fori M2,5) si avvitano all'HAT e poggiano sul Pi; non serve fissarli al Pi.", 7.5)
    testo(pg, X(0), Z(-1.4) + 24, "Sotto l'HAT restano solo: il connettore (8,5 mm), i corpi dei 4 header (2,5 mm) e le code dei componenti tagliate.", 7.5)


def immagini_kicad():
    img = QUI / "img"
    img.mkdir(exist_ok=True)
    pcb = QUI / "swimtag_programmatore.kicad_pcb"
    out = {}
    for lato, nome in (("top", "render_top.png"), ("bottom", "render_rame.png")):
        try:
            subprocess.run([KICAD_CLI, "pcb", "render", "--side", lato, "--width", "1000", "--height", "880", "--quality", "basic",
                            "-o", str(img / nome), str(pcb)], check=True, capture_output=True, cwd=QUI)
            out[lato] = img / nome
        except Exception as e:
            print("render KiCad non riuscito:", e, file=sys.stderr)
    return out


def costruisci_documento(m):
    d = Doc()
    pg = d.nuova("Copertina", voce=None)
    testo(pg, 42, 70, "SwimTimer", 12, "r", GRIGIO)
    testo(pg, 42, 108, "Adattatore di programmazione", 24, "b", (0.05, 0.2, 0.45))
    testo(pg, 42, 136, "e collaudo del tag v0.4", 24, "b", (0.05, 0.2, 0.45))
    testo(pg, 42, 160, "pogo jig nRF52840 (E73) a forma di HAT - si innesta sul Raspberry Pi 3 / 4 e si programma con OpenOCD", 10, "r")
    d.y = 180
    d.h1("1. Cos'e' e come funziona")
    d.p("Il tag SwimTimer ha, sul lato sotto, 5 piazzole per il debug SWD (VDD, SWDIO, SWCLK, RESET, GND) e 2 contatti di ricarica "
        "(VIN, GND), tutti su griglia 2,54 mm. L'adattatore e' una basetta delle dimensioni e con i fori di un HAT del Raspberry Pi (65 x 56,5 mm, 4 fori M2,5): "
        "si innesta direttamente sul connettore a 40 pin del Pi (header femmina 2x20 completo, niente cavetti) e porta sulla faccia superiore 7 molle (pogo pin) che cadono sulle piazzole del tag. "
        "Il tag si appoggia a faccia in giu' sulle molle, lo si spinge contro tre battute e lo si preme.")
    d.p("Serve a tre cose: (1) scrivere bootloader, firmware e impostazione UICR.REGOUT0 (VDD a 3,3 V) con OpenOCD in bit-bang sui GPIO del Pi; (2) ricaricare la cella "
        "senza staccarla, anche mentre il tag e' collegato via SWD (massa comune); (3) misurare tensioni e corrente di carica con il tester.")
    d.figura(140, fig_blocchi)
    d.riquadro("ATTENZIONE - MAI il 3,3 V del Raspberry Pi sul VDD del tag. La piazzola VDD e' solo un punto di misura per il tester "
               "(pin J4 isolato, non collegato al connettore). Il tag si alimenta dalla sua cella. Sul connettore sono collegati SOLO i pin 2 (5 V), 12, 18, 20 (GND) e 22: tutti gli altri restano scollegati.")
    d.p("Al primo avvio il VDD del tag e' 1,8 V (UICR vuoto); dopo UICR.REGOUT0 e un reset diventa 3,3 V. Il Pi pilota SWDIO, SWCLK e RESET a 3,3 V: "
        "le tre resistenze da 1 kOhm in serie limitano la corrente che passa nei diodi di protezione dell'nRF52840 mentre il tag e' ancora a 1,8 V "
        "(circa 1 mA per linea). E' una protezione, non una traduzione di livello: vedi la sezione 9.8.", 9.5)
    ind = d.nuova("Indice")
    d.h1("Indice", voce=False)
    indice_page = ind.number
    d.nuova("Schema")
    d.h1("2. Schema elettrico e collegamenti")
    d.figura(340, fig_schema)
    d.h2("Pin del connettore a 40 pin usati (gli altri 35 sono scollegati)")
    d.tabella(["Pin fisico", "GPIO (BCM)", "Segnale", "Sull'adattatore", "Note"],
              [["18", "GPIO24", "SWDIO", "R1 1 kohm -> P2", "bit-bang OpenOCD"],
               ["22", "GPIO25", "SWCLK", "R2 1 kohm -> P3", "bit-bang OpenOCD"],
               ["12", "GPIO18", "RESET (P0.18)", "R3 1 kohm -> P4", "open drain in OpenOCD"],
               ["20", "-", "GND", "dorsale di massa: P5, P7, J2, LED", "massa comune SWD + carica"],
               ["2", "-", "5 V", "PTC F1 -> JP1 -> J3 -> P6 (VIN)", "solo con ponticello JP1 1-2"],
               ["(nessuno)", "-", "VDD del tag", "J4 (pin isolato)", "solo tester: mai al Pi"]],
              [1.0, 1.1, 1.3, 3.2, 2.4])
    d.p("R1 sta su SWDIO (J1 pin 18), R2 su SWCLK (pin 22), R3 su RESET (pin 12). R2 e R3 sono resistenze 'lunghe' che scavalcano altre piste: in una basetta a una faccia solo le piste "
        "tra pogo e connettore si incrociano (ordine SWDIO-SWCLK-RESET-GND sul tag, RESET-SWDIO-GND-SWCLK sul connettore), quindi le due resistenze fanno anche da ponticello. "
        "I GPIO sono quelli delle configurazioni OpenOCD storiche per il Pi (raspberrypi2-native.cfg: SWCLK GPIO25, SWDIO GPIO24, SRST GPIO18; massa pin 20). "
        "Le configurazioni piu' recenti hanno spostato i default (SWCLK GPIO11, SWDIO GPIO8): il file di configurazione della sezione 9 assegna comunque i pin in modo esplicito.", 9)
    d.nuova("Ricarica")
    d.h1("3. Ricarica del tag dall'adattatore")
    d.p("I pogo P6 (VIN) e P7 (GND) toccano i contatti di ricarica del tag. Sul tag, VIN passa da un diodo Schottky 1N5819WS (protezione) e arriva al caricatore "
        "BQ25101, impostato a 13,5 mA (R_ISET = 10 kOhm) con terminazione fissa al 10 % (circa 1,35 mA) e timer di sicurezza di 10 ore.")
    d.li("JP1 e' la selezione ON/OFF e della sorgente. Nessun ponticello = ricarica OFF (predefinito): si programma senza caricare. "
         "Ponticello 1-2 = 5 V dal Raspberry Pi (pin 2 del connettore, attraverso il PTC). Ponticello 2-3 = 5 V da alimentatore esterno su J2 (limitato a 50-100 mA).")
    d.li("Il LED verde D1 con R4 (1 kOhm) e' in parallelo, subito dopo JP1 e prima del tester: indica 5 V presente e la sua corrente (circa 3 mA) non entra nella misura.")
    d.li("J3 e' il punto per il tester: con il tester in serie (portata mA) si legge la corrente di carica; senza tester va messo un ponticello su J3, altrimenti non carica.")
    d.li("F1 e' un PTC radiale (0,1 A di mantenimento) sul 5 V del Pi: se un pogo va in corto il Pi non e' esposto; dopo l'intervento si lascia raffreddare qualche minuto.")
    d.li("La massa e' unica: si puo' programmare via SWD mentre si carica e il firmware puo' leggere CHG_N (P0.03) e VDDH (canale VDDHDIV5 del SAADC).")
    d.h2("Verifica della tensione minima del caricatore")
    d.tabella(["Voce", "Valore", "Nota"],
              [["5 V del Pi (pin 2)", "4,9-5,1 V", "con il carico di 14 mA non cala"],
               ["PTC F1 (0,1 A hold)", "-0,03...-0,1 V", "ordine di 2-7 ohm x 14 mA"],
               ["Tester in portata mA", "-0,05...-0,3 V", "dipende dallo strumento: usare la portata 200 mA (shunt piccolo)"],
               ["Schottky 1N5819WS sul tag", "circa -0,2 V", "a 13,5 mA; Vf piu' alta a corrente maggiore"],
               ["VIN al BQ25101", "circa 4,4-4,8 V", "TI: tensione consigliata 4,45-6,45 V; sotto 4,25-4,37 V interviene la VIN-DPM e la corrente cala"]],
              [2.2, 1.4, 4])
    d.p("Conclusione: con 5 V pieni, PTC e un tester a basso carico il margine e' di 0,2-0,4 V. Se la corrente misurata e' molto minore di 13,5 mA mentre la tensione "
        "sul pin 2 di J3 e' sotto circa 4,7 V, la VIN-DPM sta riducendo la corrente: togliere il tester (ponticello su J3) o usare l'alimentatore esterno a 5,0-5,2 V. "
        "I valori del BQ25101 vanno ricontrollati sul datasheet TI prima di fare affidamento sui margini.", 9.5)
    d.h2("Tempi e cosa misurare (cella Ampul 401012 da 40 mAh)")
    d.tabella(["Situazione", "Atteso"],
              [["Corrente in carica a corrente costante (CC)", "13,5 mA (misura al tester su J3, firmware in sleep)"],
               ["Cella molto scarica (sotto circa 3 V)", "prima una fase a corrente ridotta (precarica, circa il 10 %: ~1,4 mA) finche' VBAT sale"],
               ["Fine carica", "corrente a circa 1,35 mA (10 % di I_CHG); CHG_N (P0.03) torna alto"],
               ["Durata dalla cella vuota", "circa 3-3,5 ore (CC ~3 h + coda a tensione costante)"],
               ["Durata dal 50 %", "circa 1,5-2 ore"],
               ["Timer di sicurezza", "10 ore, poi il caricatore si ferma da solo"],
               ["VIN sul pogo P6 (tester su J3.2 e GND)", "4,6-5,1 V"],
               ["Tensione sulla cella a fine carica", "4,2 V (misurare sui fili cella o leggere VDDH)"]],
              [3, 5])
    d.p("Nota: il carico del tag (CPU in debug, qualche mA) e' alimentato dalla stessa cella/caricatore: durante la misura della corrente di carica "
        "il firmware deve essere fermo o in sleep (o RESET tenuto basso), altrimenti si legge carica + carico e la terminazione al 10 % "
        "non scatta finche' il carico supera 1,35 mA.", 9.5)
    d.nuova("Distinta")
    d.h1("4. Distinta componenti (prezzi indicativi, novembre 2026)")
    d.p("I link sono ricerche sui cataloghi: i codici esatti e le giacenze vanno controllati al momento dell'acquisto. Spedizioni dalla Cina (AliExpress, LCSC): 1-3 settimane; da distributori europei (Mouser, Farnell, RS) 2-4 giorni.", 9)
    d.tabella(["Q.", "Componente", "Codice / tipo", "Prezzo", "Dove"],
              [["7+3", "Pogo pin P75-E2 (testa a corona, O corpo ~1,0-1,3 mm, corsa ~2 mm)", "P75-E2 (3 di scorta)", "~2-3 EUR per 10 pz", "lcsc.com/search?q=P75-E2 - AliExpress 'P75-E2 pogo pin'"],
               ["7+3", "Ricettacolo per P75 (a saldare / wire-wrap)", "R75-2W (o R75-3S)", "~2 EUR per 10 pz", "lcsc.com/search?q=R75-2W"],
               ["1", "Header FEMMINA 2x20 (40 pin), passo 2,54, altezza 8,5 mm, per HAT", "es. 'Raspberry Pi 40 pin female header 2x20'", "~1-2 EUR", "lcsc.com/search?q=female+header+2x20 - Pimoroni/Adafruit/Kiwi"],
               ["4", "Distanziale M2,5 femmina-femmina, 11 mm (nylon o ottone)", "kit distanziali M2,5", "~3 EUR (kit)", "AliExpress / Amazon"],
               ["4+4", "Vite M2,5 x 6 (testa tonda)", "kit viti M2,5", "~1 EUR", "ferramenta / kit"],
               ["1", "Basetta FR4 1,6 mm, rame su una faccia (100 x 160 mm; ne ricavi 2)", "normale (non fotosensibile)", "~4-6 EUR", "AliExpress / Amazon 'single side copper clad 100x160'"],
               ["1 striscia", "Header maschio 1x40, passo 2,54 (JP1 3, J2 2, J3 2, J4 1, battute 3 pin)", "generico", "~0,5 EUR", "lcsc.com/search?q=pin+header+1x40"],
               ["2 (+1)", "Ponticello (jumper cap) 2,54 mm", "generico", "~0,3 EUR", "come sopra"],
               ["4", "Resistenza 1 kohm 1/4 W 5 %, foro passante (corpo 6,3 mm)", "generica", "~0,1 EUR", "qualsiasi"],
               ["1", "LED verde 3 mm, foro passante", "generico", "~0,1 EUR", "qualsiasi"],
               ["1", "PTC radiale, hold 0,1 A, passo 5,08 mm", "es. Bourns MF-R010 / Littelfuse RXEF010", "~0,4 EUR", "mouser.it / farnell.com ('PTC 100 mA radial')"],
               ["3", "Blocchetto 2,54 x 2,54 x 2,5 mm: corpo di plastica di un header (appoggi del tag)", "ricavato da 1 header maschio", "-", "cianoacrilico o biadesivo"],
               ["-", "Carta lucida (rivista patinata o carta fotografica glossy), persolfato di sodio o cloruro ferrico, punte 0,8 / 1,0 / 1,5 / 2,75 mm", "consumabili", "~10-15 EUR", "negozi di elettronica / AliExpress"]],
              [0.6, 3.6, 2.2, 1.4, 3])
    d.p("Totale: circa 25-30 EUR di componenti piu' circa 10-15 EUR di consumabili se non li hai gia'. Il connettore femmina 2x20 e' un normale header per HAT (non il 'GPIO stacking' con code lunghe): "
        "va montato da sotto e saldato sopra (sezione 6.6).", 9.5)
    d.h2("Scelta dei pogo: due alternative a confronto")
    d.tabella(["", "P75-E2 + R75 (scelto)", "P50 + R50 (alternativa)"],
              [["Corpo del ricettacolo", "foro ~1,5 mm: anello di rame 0,25 mm intorno (piazzola ovale 2,0 x 3,2)", "foro ~1,0 mm: anello 0,5 mm, piu' comodo da forare a mano"],
               ["Corrente / robustezza", "~3 A, molla piu' robusta", "~1-2 A, molla piu' debole, stesso uso"],
               ["Reperibilita'", "molto comune (e' la serie 'standard' a passo 2,54)", "comune"],
               ["Contro", "foro grande: allineare bene la punta del trapano", "punta del pogo piu' sottile: piu' fragile"]],
              [2, 4, 4])
    d.p("Motivo della scelta: richiesta e disponibilita' della serie P75; se il foro da 1,5 mm strappa il rame in foratura, passare a P50/R50 (stessa piazzola, basta cambiare FORO_POGO in modello.py e rigenerare).", 9)
    n_copie, dim = pagina_rame(d, m)
    pag_rame = len(d.d)
    d.sez.append(("5a. STAMPA 1:1 - rame speculare (toner transfer)", pag_rame))
    pagina_componenti(d, m)
    pag_comp = len(d.d)
    d.sez.append(("5b. STAMPA 1:1 - posizioni dei componenti (non speculare)", pag_comp))
    pagina_componenti(d, m, det=True)
    d.sez.append(("5b'. Posizioni dei componenti ingrandite 2:1 (consultazione)", len(d.d)))
    pagina_fori(d, m)
    d.sez.append(("5c. Mappa dei fori 1:1", len(d.d)))
    d.nuova("Procedura")
    d.h1("6. Costruzione, passo passo")
    d.riquadro("Particolarita' di questa basetta: il rame e' SUL LATO COMPONENTI (sopra), come in un HAT vero, perche' il connettore femmina a 40 pin si monta da sotto e si salda sopra. "
               "Quindi la stampa e' speculare (carta girata sul rame) e tutti i componenti si saldano dal lato in cui si vedono le piste.", BLU, (0.9, 0.95, 1), 9.5)
    d.h2("6.1 Preparare la stampa")
    d.li("Aprire la pagina 5a (o stampa/rame_speculare_1a1.pdf); stampare al 100 % ('dimensione reale'), mai 'adatta alla pagina'. Stampante LASER, qualita' massima, toner scuro, nessun risparmio toner.", num="1.")
    d.li("Carta: carta lucida da rivista patinata (la piu' economica) o carta fotografica 'glossy' a getto d'inchiostro; il toner deve restare sopra, senza assorbirsi.", num="2.")
    d.li("Controllo della scala: misurare con un righello la barra da 50 mm in alto e la barra verticale a destra: devono dare 50,0 +- 0,3 mm.", num="3.")
    d.li("Controllo del verso: sul foglio le scritte 'USB->' e 'JIG 0.4' sono scritte al rovescio e il pin 1 e' a destra: e' giusto. Dopo il trasferimento sul rame (guardandolo da sopra) si leggono dritte e il pin 1 e' a sinistra.", num="4.")
    d.li("Ritagliare UNA copia lungo i segni di taglio (angoli), lasciando 3-5 mm di carta intorno. Le altre copie servono come scorta.", num="5.")
    d.h2("6.2 Preparare il rame")
    d.li("Tagliare la basetta a misura (%.1f x %.1f mm, angoli arrotondati r = 3 mm come da specifica HAT) con seghetto o cutter da PCB incidendo piu' volte e spezzando; limare i bordi e gli angoli." % dim, num="1.")
    d.li("Pulire il rame con paglietta fine / carta vetro 1000 e acetone o alcol isopropilico: rame lucido, senza ditate. Non toccarlo piu' con le dita.", num="2.")
    d.h2("6.3 Trasferimento con il ferro")
    d.li("Appoggiare la carta con il toner rivolto verso il rame, centrata, fissarla con nastro di carta su due lati.", num="1.")
    d.li("Ferro da stiro al massimo, senza vapore. Premere forte e uniformemente 2-3 minuti sul primo punto, poi muovere lentamente su tutta la superficie per altri 3-5 minuti, insistendo sui bordi.", num="2.")
    d.li("Lasciare raffreddare, poi mettere in acqua tiepida con una goccia di detersivo per 10 minuti e togliere la carta sfregando con il dito.", num="3.")
    d.li("Controllare con una lente: piste continue, piazzole piene. Ritoccare i difetti con un pennarello indelebile a punta fine; i punti bianchi dei fori (O 0,5 mm) non vanno coperti.", num="4.")
    d.h2("6.4 Incisione (con avvertenze)")
    d.riquadro("Sicurezza: cloruro ferrico e persolfato macchiano e sono corrosivi. Occhiali, guanti, abiti vecchi, ambiente ventilato, vaschetta di plastica o vetro (mai metallo). "
               "Non versare la soluzione esausta nello scarico: conferirla al centro di raccolta rifiuti speciali del comune. Tenere lontano da bambini e animali.",
               ARANCIO, (1, 0.95, 0.85), 9.5)
    d.li("Soluzione tiepida (40-50 C) di persolfato di sodio (circa 100-200 g/litro) o cloruro ferrico, in vaschetta. Agitare dolcemente.", num="1.")
    d.li("Tempo: persolfato circa 10-20 minuti, cloruro ferrico 15-30 minuti. Fermarsi appena il rame scoperto e' sparito del tutto (controllare in controluce).", num="2.")
    d.li("Sciacquare in abbondanza. Togliere il toner con acetone o paglietta fine: il rame delle piste deve tornare lucido. Passare un velo di flussante o stagno liquido.", num="3.")
    d.li("Controllare con il tester (continuita') l'assenza di corti tra piste e piazzole vicine: specialmente tra le piazzole del connettore (0,54 mm) e dei pogo.", num="4.")
    d.h2("6.5 Foratura")
    d.p("Usare la mappa dei fori (pagina 5c). Punteggiare con un punto di bulino sui segni bianchi, forare con un mini-trapano (punte in metallo duro: 0,8 / 1,0 / 1,5 / 2,75 mm). "
        "Il connettore ha fori SOLO sulla fila esterna (20 fori, pin pari). Per il foro da 1,5 mm: partire con 1,0 mm e allargare, basetta ben ferma su un legno di scarto, senza premere. Sbavare a mano.", 9.5)
    d.h2("6.6 Montaggio (tutto si salda dal lato rame, sopra)")
    d.li("Connettore femmina 2x20: con un tronchesino a filo, TAGLIARE le code dei pin dispari (fila interna, quella che sulla basetta non ha fori; sono i pin 1, 3, ... 39). "
         "Inserirlo DA SOTTO, con le prese rivolte verso il basso (verso il Pi) e le code della fila esterna che sporgono sopra; il lato con il pin 1 a sinistra, la fila esterna verso il bordo. "
         "Saldare le 20 code sopra (sono la ritenzione meccanica) e tagliarle a ~1 mm.", num="1.")
    d.li("Resistenze: R1 e R4 'in piedi' (un piedino piegato sul corpo, 2,54 mm). R2 (SWCLK) e R3 (RESET) sdraiate, con i piedini a 10,16 mm: il corpo scavalca le piste. "
         "Inserire dall'alto, tenere il corpo sollevato ~1-2 mm dalla basetta (uno spessore) e saldare sopra il piedino dove entra nel foro; tagliare sotto.", num="2.")
    d.li("Header maschio (JP1 3 pin, J2 2 pin, J3 2 pin, J4 1 pin): inserire DA SOTTO con il lato lungo dei pin verso l'alto, corpo di plastica sotto la basetta; saldare sopra, e tagliare a filo la parte corta sotto il corpo.", num="3.")
    d.li("LED e PTC: inserire dall'alto, lasciare 2-3 mm di piedino libero sopra la basetta, saldare sopra (polarita' LED: anodo in alto nella pagina 5b', verso R4).", num="4.")
    d.li("Battute S1, S2 (bordo sinistro) e S3 (bordo alto): pezzi di pin di header (0,64 mm) infilati nel foro da 0,8 mm da sotto, sporgenti 4-5 mm sopra, saldati sopra; devono restare dritti e con una faccia piana verso il tag.", num="5.")
    d.li("Appoggi S4, S5, S6: blocchetti di plastica da 2,54 x 2,54 x 2,5 mm (il corpo di un header privato dei pin) incollati con una goccia di cianoacrilico sui quadrati di rame da 3 x 3 mm.", num="6.")
    d.li("Pogo: v. sezione successiva. Distanziali: avvitare i 4 distanziali da 11 mm sotto l'HAT con le viti M2,5 dall'alto.", num="7.")
    d.nuova("Pogo")
    d.h1("7. Montaggio dei pogo all'altezza giusta")
    d.figura(275, fig_sezione)
    d.li("Inserire un ricettacolo nel suo foro dall'alto; infilarci il pogo e misurare con il calibro quanto la punta sporge dalla testa del ricettacolo con la molla a riposo (L).", num="1.")
    d.li("Calcolare l'altezza della testa del ricettacolo sopra la basetta: H_r = %.1f mm - L. Esempio: se L = 3,0 mm, la testa va a 1,0 mm sopra la basetta. Se H_r > 2,0 mm il ricettacolo sarebbe troppo alto: usare un ricettacolo piu' corto." % PERNO, num="2.")
    d.li("Togliere il pogo (per non scaldare la molla). Con uno spessore di H_r mm sotto la testa del ricettacolo, saldare SOPRA, intorno al corpo, con stagno e poca fiamma; il piano delle punte resta cosi' a %.1f mm." % PERNO, num="3.")
    d.li("Reinserire i pogo. Tagliare la coda del ricettacolo che sporge sotto (resta al massimo 3 mm: sotto c'e' il Pi).", num="4.")
    d.li("Verifica del piano: appoggiare un righello rigido sui blocchetti S4-S6: le punte dei 7 pogo devono sporgere di %.1f mm dalla faccia del righello (+-0,3), tutte uguali." % COMPR, num="5.")
    d.li("Prova del contatto: appoggiare il tag, premere, e controllare con il tester (continuita') tra una piazzola del tag e il corrispondente pin (J4, J3, ...).", num="6.")
    d.nuova()
    d.h2("Posizionamento e centraggio del tag")
    d.figura(325, lambda pg, x, y, w: fig_pianta(pg, x, y, w, m))
    d.p("Forza dei pogo: ogni molla da circa 0,5-1 N a meta' corsa, quindi circa 4-7 N sui sette: basta premere con un dito sul tag, oppure un coperchio di plexiglas "
        "o un elastico largo intorno all'HAT e al Pi. L'HAT poggia sui distanziali: la pressione verso il basso e' sostenuta dal Pi. "
        "Prima di programmare, tenere il tag premuto: un contatto intermittente da' errori misteriosi di OpenOCD.", 9.5)
    d.nuova("Innesto sul Pi")
    d.h1("8. Innesto sul Raspberry Pi")
    d.p("Con il Pi spento, appoggiare l'HAT sul connettore con il bordo del connettore verso il bordo del Pi, la scritta 'USB->' verso le porte USB/Ethernet, il pin 1 (fila interna, a sinistra) dal lato della scheda SD. "
        "I 4 fori M2,5 (58 x 49 mm) e la posizione del connettore sono quelli della specifica HAT ufficiale (identici su Pi 3 e Pi 4): con i distanziali ai fori l'HAT entra in un solo verso. "
        "Il connettore e' completo (2x20), quindi non puo' scorrere di un pin. Distanziali da 11 mm (header femmina 8,5 mm + 2,5 mm di plastica del maschio): il tag e i pogo restano sopra, "
        "le porte USB/Ethernet restano scoperte.", 9.5)
    d.figura(510, lambda pg, x, y, w: fig_innesto(pg, x, y, w, m))
    d.riquadro("Verificare la posizione del connettore sulla specifica HAT (centro del connettore a 3,5 mm dal bordo e a meta' tra i fori) sul proprio Pi prima della foratura: "
               "un errore di 1 mm si vede subito perche' i fori M2,5 non coincidono.", ROSSO, (1, 0.9, 0.9), 9)
    d.h2("E se l'HAT fosse innestato ruotato di 180 gradi?")
    d.p("La specifica HAT lo rende fisicamente evidente: ruotato di 180 gradi intorno al connettore, l'HAT sporgerebbe di 49 mm oltre il bordo del Pi e due soli distanziali cadrebbero sui fori del Pi. "
        "Se lo si forzasse comunque, la presa 'pin 2k' dell'HAT finisce sul pin 41-2k del Pi; i pin pari del Pi (5 V, GND, GPIO) incontrano la fila interna dell'HAT, le cui code sono tagliate: "
        "quindi non si collega nulla di cio' che e' sulla fila esterna del Pi (5 V compresi).", 9.5)
    d.tabella(["Presa dell'HAT (segnale)", "Pin del Pi con innesto ruotato", "Effetto"],
              [["pin 2 (5 V, verso PTC F1)", "pin 39 = GND", "la linea 5 V dell'adattatore va a massa: nessun danno (con JP1 1-2 il tag vede 0 V). MAI fare JP1 2-3 con il 5 V esterno: l'ingresso esterno non tocca questa linea."],
               ["pin 12 (RESET)", "pin 29 = GPIO5", "ingresso/uscita GPIO libera: nessun effetto finche' non la si usa"],
               ["pin 18 (SWDIO)", "pin 23 = GPIO11 (SPI SCLK)", "come sopra"],
               ["pin 20 (GND dell'adattatore)", "pin 21 = GPIO9 (SPI MISO)", "la massa del tag e dell'eventuale alimentatore esterno e' su un GPIO in ingresso: nessun cortocircuito"],
               ["pin 22 (SWCLK)", "pin 19 = GPIO10 (SPI MOSI)", "come sopra"],
               ["altre prese a pin pari (40 pad flottanti)", "pin dispari: 1 e 17 = 3,3 V, 2/4 non raggiunti", "pad flottanti: i 3,3 V del Pi cadono su rame isolato"]],
              [2.5, 2.5, 5.5])
    d.p("Conclusione: nessun caso pericoloso. I 3,3 V (pin 1 e 17) e i 5 V (pin 2, 4) del Pi non finiscono mai su una linea collegata del tag, ne' innestato giusto ne' ruotato: il 5 V arriva "
        "soltanto dal pin 2 attraverso il PTC e JP1 (spento per default). Ne' occorre aggiungere protezioni; restano le 1 kohm in serie e il PTC.", 9.5)
    d.nuova("Programmazione")
    d.h1("9. Primo collegamento e programmazione")
    d.h2("9.1 Controlli con il tester (tag NON ancora sull'adattatore, adattatore NON sul Pi)")
    d.li("Continuita' tra ogni pogo e il suo punto: P1-J4, P2-pin 18 del connettore (circa 1 kohm, via R1), P3-pin 22 (1 kohm), P4-pin 12 (1 kohm), P5-pin 20 (0 ohm), P6-J3, P7-pin 20.", num="1.")
    d.li("Nessun corto tra pin vicini e nessuna continuita' tra il pin 20 (GND) e il pin 2 (5 V), ne' tra J4 (VDD) e qualunque pin del connettore.", num="2.")
    d.li("JP1 senza ponticello (carica OFF), J3 con ponticello.", num="3.")
    d.h2("9.2 Il tag sull'adattatore")
    d.li("Innestare l'HAT sul Pi (spento). Collegare la cella al connettore batteria del tag. Appoggiare il tag a faccia in giu', spingerlo contro S1-S3 e premerlo.", num="1.")
    d.li("Con il tester in portata 20 V: nero su pin GND (J2 GND), rosso su J4 (VDD). Primo avvio, UICR vuoto: atteso 1,8 V (da 1,7 a 1,9 V). Se e' 0 V: cella scollegata, scarica, contatto mancante. Se legge 3,3 V il REGOUT0 e' gia' impostato.", num="2.")
    d.li("Solo ora accendere il Pi e lanciare OpenOCD.", num="3.")
    d.h2("9.3 Installare OpenOCD sul Raspberry Pi (Raspberry Pi OS)")
    d.codice(["sudo apt update", "sudo apt install -y openocd", "openocd --version            # 0.12.0 su Raspberry Pi OS Bookworm", "openocd -c 'adapter list' -c shutdown   # deve elencare bcm2835gpio (e linuxgpiod)",
              "# controlla i default ufficiali installati sul tuo Pi (possono cambiare tra versioni):", "grep -n 'swd_nums\\|swclk\\|srst' /usr/share/openocd/scripts/interface/raspberrypi*native.cfg"])
    d.p("OpenOCD va lanciato con sudo (accede alla memoria dei GPIO). Pi 5: non supportato da bcm2835gpio (GPIO dietro il chip RP1), non usarlo.", 9)
    d.h2("9.4 File di configurazione completo: swimtag_pi.cfg")
    d.codice(["# swimtag_pi.cfg - nRF52840 con bit-bang su GPIO del Raspberry Pi",
              "# --- scegliere UNA sola riga peripheral_base ---",
              "# Pi 3 / Pi 2 / Zero 2:   0x3F000000          Pi 4:   0xFE000000",
              "adapter driver bcm2835gpio",
              "bcm2835gpio peripheral_base 0x3F000000",
              "# calibrazione velocita' (valore di partenza del Pi 3; sul Pi 4 vedi 9.5)",
              "bcm2835gpio speed_coeffs 146203 36",
              "# SWCLK = GPIO25 (pin 22), SWDIO = GPIO24 (pin 18)",
              "bcm2835gpio swd_nums 25 24",
              "# RESET = GPIO18 (pin 12), a drenaggio aperto (il tag ha il pull-up interno)",
              "bcm2835gpio srst_num 18",
              "reset_config srst_only srst_open_drain",
              "transport select swd",
              "adapter speed 1000",
              "set WORKAREASIZE 0",
              "source [find target/nrf52.cfg]"])
    d.p("Con OpenOCD piu' recente (dalla 0.12 con 'adapter gpio') la sintassi equivalente e': 'adapter gpio swclk 25', 'adapter gpio swdio 24', 'adapter gpio srst 18'. "
        "Su Pi 4 l'indirizzo delle periferiche e' 0xFE000000. 'adapter speed' e' in kHz: partire da 1000, scendere a 200-400 se compaiono errori di parita' o timeout.", 9)
    d.h2("9.5 Differenze tra Pi 3 e Pi 4")
    d.tabella(["", "Raspberry Pi 3", "Raspberry Pi 4"],
              [["peripheral_base", "0x3F000000", "0xFE000000"],
               ["speed_coeffs", "146203 36 (valore dei file ufficiali)", "il driver e' tarato sul Pi 3: partire da 'adapter speed 400' e alzare; misurare il clock con un oscilloscopio o un analizzatore se serve"],
               ["Alternativa", "-", "driver linuxgpiod (richiede openocd compilato con --enable-linuxgpiod): 'adapter driver linuxgpiod', 'linuxgpiod gpiochip 0', 'linuxgpiod swd_nums 25 24', 'linuxgpiod srst_num 18'; piu' lento ma indipendente dall'indirizzo delle periferiche"],
               ["Velocita' tipica", "1-2 MHz di bit-bang", "1-3 MHz, usare comunque meno di 2 MHz"]],
              [1.6, 3, 5])
    d.h2("9.6 Comandi")
    d.p("Tutti dalla cartella con swimtag_pi.cfg; la sigla -c esegue il comando e poi esce.", 9)
    d.codice(["# a) Leggere l'ID: IDCODE SWD, riconoscimento nRF52840 e protezione APPROTECT",
              "sudo openocd -f swimtag_pi.cfg -c 'init; dap info; exit'",
              "sudo openocd -f swimtag_pi.cfg -c 'init; mdw 0x10000100 1; mdw 0x10000060 2; mdw 0x10001208 1; exit'",
              "#   0x10000100 FICR.INFO.PART  deve valere 0x00052840",
              "#   0x10000060 FICR.DEVICEID[0..1] identifica il singolo chip",
              "#   0x10001208 UICR.APPROTECT  0xFFFFFFFF = vuoto / non protetto",
              "# L'IDCODE SWD atteso e' 0x2ba01477 (messaggio all'avvio di OpenOCD).",
              "",
              "# b) Impostare UICR.REGOUT0 = 3,3 V (VDD del tag da 1,8 a 3,3 V)",
              "#    UICR.REGOUT0 = 0x10001304, VOUT = bit 2:0, valore 5 = 3,3 V (0xFFFFFFFD); NVMC.CONFIG = 0x4001E504 (1 = scrittura)",
              "sudo openocd -f swimtag_pi.cfg -c 'init; halt' \\",
              "   -c 'mww 0x4001E504 1' -c 'mww 0x10001304 0xFFFFFFFD' -c 'sleep 100' -c 'mww 0x4001E504 0' \\",
              "   -c 'mdw 0x10001304 1' -c 'reset run' -c exit",
              "#   atteso nel mdw: 0x10001304: fffffffd. Il nuovo VDD parte dopo il reset: scollegare e ricollegare",
              "#   la cella se il tester su J4 vede ancora 1,8 V.",
              "",
              "# c) Reset",
              "sudo openocd -f swimtag_pi.cfg -c 'init; reset run; exit'      # reset e riparte",
              "sudo openocd -f swimtag_pi.cfg -c 'init; reset halt; exit'     # reset e si ferma",
              "",
              "# d) Cancellare e caricare bootloader e firmware (esempi con i file generati da PlatformIO / nrfutil)",
              "sudo openocd -f swimtag_pi.cfg -c 'init; halt; nrf5 mass_erase; exit'",
              "sudo openocd -f swimtag_pi.cfg -c 'init; halt; program bootloader.hex verify' -c 'program firmware.hex verify reset exit'",
              "# NB: mass_erase cancella anche UICR: dopo, rifare il passo b) (a meno che il .hex contenga l'UICR).",
              "",
              "# e) Verifica del contenuto",
              "sudo openocd -f swimtag_pi.cfg -c 'init; halt; verify_image firmware.hex; exit'",
              "sudo openocd -f swimtag_pi.cfg -c 'init; halt; mdw 0x10001304 1; flash info 0; exit'"])
    d.p("Alternativa breve: con J-Link o Pico/debugprobe servirebbero cavetti sulle prese dell'HAT, ma l'adattatore e' pensato solo per il Pi. Il VDD (J4) non va mai collegato a VTref di un programmatore che lo alimenti.", 9)
    d.h2("9.7 Tensioni attese in ogni fase")
    d.tabella(["Fase", "VDD sul tester (J4 - GND)", "Se non e' cosi'"],
              [["Cella collegata, chip vuoto (UICR vuoto)", "1,8 V (1,7-1,9)", "0 V: cella assente/scarica; 3,3 V: REGOUT0 gia' scritto"],
               ["Dopo la scrittura REGOUT0 e il reset/power cycle", "3,3 V (3,2-3,4)", "ancora 1,8 V: non e' scattato il reset, rifare 'reset run' o scollegare la cella"],
               ["VIN sul pogo P6 con carica attiva (J3.2-GND)", "4,6-5,1 V", "sotto 4,45 V la carica rallenta o non parte"],
               ["Corrente di carica (J3)", "13,5 mA in CC, ~1,35 mA a fine carica", "vedi sezione 3"]],
              [3.5, 2.6, 4])
    d.h2("9.8 Limiti dei livelli a 3,3 V e alternative")
    d.p("Finche' il VDD del tag e' 1,8 V il Pi porta SWDIO, SWCLK e RESET a 3,3 V, oltre il limite VDD + 0,3 V dell'nRF52840. Le tre resistenze da 1 kohm limitano la corrente nei diodi di protezione a circa (3,3 - 1,8 - 0,5) / 1000 = 1 mA per linea "
        "(circa 3 mA in tutto, che finiscono nel VDD del tag). E' tollerabile solo per i pochi minuti del primo collegamento e solo se il tag, con la CPU ferma, assorbe piu' di quei 3 mA "
        "(altrimenti il VDD potrebbe salire di qualche decimo di volt). Mitigazioni: (1) scrivere REGOUT0 subito, poi il rischio sparisce; "
        "(2) non collegare RESET nel primo passaggio (togliere R3 o sollevare un suo piedino); (3) alzare R1-R3 a 2,2 kohm con 400-500 kHz; (4) adattatore di livello 3,3/1,8 V "
        "bidirezionale open-drain (tipo BSS138) su SWCLK e SWDIO; (5) un programmatore con VTref (J-Link), che si adatta ai 1,8 V.", 9.5)
    d.h2("9.9 Risoluzione dei problemi")
    d.tabella(["Sintomo", "Causa probabile e rimedio"],
              [["'Error: couldn't open /dev/mem' / 'Permission denied'", "lanciare con sudo"],
               ["'SWD DPIDR 0x00000000' o 'Failed to read'", "tag non alimentato (cella), pogo che non toccano: premere, controllare altezza e centraggio; HAT non innestato a fondo"],
               ["'DPIDR 0xffffffff'", "SWDIO a livello alto fisso: pista interrotta, resistenza R1 interrotta, tag in System OFF: dare RESET (pin 12) e riprovare"],
               ["Errori di parita' / timeout casuali", "contatto intermittente: 'adapter speed 200', premere meglio il tag, controllare l'innesto"],
               ["OpenOCD parte ma chip non riconosciuto", "target/nrf52.cfg troppo vecchio (<0.11): aggiornare OpenOCD"],
               ["'Failed to examine' / accesso negato con APPROTECT attivo", "lanciare 'nrf52_recover' (cancella tutto, e' normale)"],
               ["mdw 0x10001304 dice fffffffd ma VDD resta a 1,8 V", "serve un reset di sistema o un power cycle (togliere un istante la cella)"],
               ["La carica non parte (LED D1 spento)", "JP1 senza ponticello; PTC F1 intervenuto (aspettare); il 5 V non arriva dal pin 2 del Pi; HAT non a fondo"],
               ["LED acceso ma corrente 0 mA", "J3 senza ponticello e senza tester; VIN troppo bassa (v. sezione 3); contatti VIN/GND non toccano"],
               ["Corrente molto minore di 13,5 mA", "VIN-DPM: tester con shunt troppo alto, usare 5,1 V esterno o ponticello; oppure carico del tag acceso"]],
              [3.8, 6])
    imgs = immagini_kicad()
    d.nuova("Immagini KiCad")
    d.h1("10. Immagini dal progetto KiCad e rigenerazione")
    d.p("Render del file swimtag_programmatore.kicad_pcb (kicad-cli): a sinistra la faccia superiore con il rame (le piste sono sul lato dei componenti), a destra la faccia inferiore (solo "
        "foratura e connettore).", 9)
    if imgs:
        d.spazio_ok(300)
        ytop = d.y
        for k, key in enumerate(("top", "bottom")):
            if key in imgs:
                r = fitz.Rect(d.marg + k * (d.w / 2) + 4, ytop, d.marg + (k + 1) * (d.w / 2) - 4, ytop + 270)
                d.page.insert_image(r, filename=str(imgs[key]), keep_proportion=True)
        d.y = ytop + 280
    d.h2("Rigenerazione dopo la ricompattazione della scheda")
    d.codice(["cd hardware/programmatore", "python genera_kicad.py --drc    # rilegge TP1-TP7 e il contorno dal PCB del tag, riscrive KiCad, esegue DRC ed ERC",
              "python genera_pdf.py            # rigenera questo PDF e le stampe 1:1",
              "# PCB del tag diverso: SWIMTAG_PCB=percorso/al/file.kicad_pcb python genera_kicad.py"])
    d.p("Lo script avvisa se il passo delle piazzole non e' piu' 2,54 mm o se TP6/TP7 non stanno piu' sotto SWDIO/RESET (lo sbroglio dei ponti e della ricarica dipende da questo). "
        "Con la scheda ricompattata le coordinate dei pogo seguono le piazzole, le battute i bordi del tag.", 9)
    d.p(f"Dati letti dal PCB del tag per questa copia: scheda tag {m['W']:.2f} x {m['H']:.2f} mm; "
        + "; ".join(f"{k} ({v[0]:.2f}, {v[1]:.2f}) O {v[2]:.1f}" for k, v in sorted(m['tag']['tp'].items())) + ".", 8.5, "r", GRIGIO)
    pg = d.d[indice_page]
    y = 90
    for t, n in d.sez:
        testo(pg, 42, y, t, 10, "r")
        testo(pg, A4[0] - 42, y, str(n), 10, "b", NERO, "d")
        pg.draw_line((42 + tl(t, 10) + 6, y - 2), (A4[0] - 42 - 18, y - 2), color=GRIGIO_CH, width=0.5, dashes="[1 2] 0")
        y += 16
    y += 10
    testo(pg, 42, y, f"Le stampe 1:1 sono a pagina {pag_rame} (rame speculare, {n_copie} copie), {pag_comp} (posizioni componenti) e {pag_comp + 2} (mappa fori).", 10, "b", ROSSO)
    d.piedi("SwimTag - adattatore di programmazione e collaudo v0.4 (HAT)")
    return d, dict(rame=pag_rame, comp=pag_comp, fori=pag_comp + 2, copie=n_copie, dim=dim)


def main():
    m = costruisci()
    for a in m["avvisi"]:
        print("AVVISO:", a)
    d, info = costruisci_documento(m)
    d.d.set_metadata({"title": "SwimTag - adattatore di programmazione e collaudo v0.4", "author": "SwimTimer", "subject": "pogo jig nRF52840"})
    d.d.save(str(NOME_PDF), garbage=3, deflate=True)
    print("scritto", NOME_PDF.name, len(d.d), "pagine;", info)
    # PDF di stampa separati
    (QUI / "stampa").mkdir(exist_ok=True)
    d1 = Doc()
    pagina_rame(d1, m)
    d1.d.save(str(QUI / "stampa" / "rame_speculare_1a1.pdf"), deflate=True)
    d2 = Doc()
    pagina_componenti(d2, m)
    d2.d.save(str(QUI / "stampa" / "componenti_1a1.pdf"), deflate=True)
    print("scritti stampa/rame_speculare_1a1.pdf e stampa/componenti_1a1.pdf")


if __name__ == "__main__":
    main()
