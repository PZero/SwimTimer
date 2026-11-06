"""Crea i pannelli NextPCB (3x1 e 2x1) della scheda swimtag_economica, senza V-cut.

Le schede hanno componenti a 0,3-0,6 mm dal bordo, quindi: intercapedine di 2 mm tra le schede e verso le
guide, schede agganciate con linguette (tab) con fori "mouse bite" nelle zone libere del bordo.
Il J1 (connettore batteria) NON viene montato: resta nel PCB (i fili si saldano a mano) ma e' escluso da BOM e CPL.

Uso (Python di KiCad):  <KiCad>/bin/python.exe crea_pannelli.py
Poi, con il Python di sistema (serve openpyxl):  python csv_a_xlsx.py nextpcb/v0.5_pannello_3x1  (e _2x1)
Non modifica ne' la scheda singola ne' jlc/ ne' nextpcb/v0.5/.
Schema designatori: ogni scheda del pannello e' numerata da sinistra (1..N); U1 diventa U1_1, U1_2, ...
"""
import csv
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pcbnew
from pcbnew import FromMM as mm_, VECTOR2I

QUI = Path(__file__).parent
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
CLI = KICAD / "bin" / "kicad-cli.exe"
FP_LIB = KICAD / "share" / "kicad" / "footprints"
NOME = "swimtag_economica"
PCB = QUI / f"{NOME}.kicad_pcb"
BOM_SINGOLA = QUI / "nextpcb" / "v0.5" / "bom_nextpcb.csv"
ESCLUSI = {"J1"}  # non montati da NextPCB (saldatura a mano dei fili)

W_S, H_S = 21.59, 28.0          # scheda singola
GAP = 2.0                       # intercapedine (fresatura)
H_PAN = 50.0                    # altezza pannello
RAIL = (H_PAN - H_S - 2 * GAP) / 2   # guida sopra e sotto = 9 mm
TAB_W = 3.2
# linguette: centro x (nel sistema della scheda) libero da componenti: in alto a destra del modulo E73 (x 16.85..20.05),
# in basso tra R9 e U3 (x 8.3..11.5). Agganciano la scheda alle guide sopra e sotto.
TAB_TOP_X, TAB_BOT_X = 18.45, 9.9
BITE_D, BITE_PITCH, BITE_OFF = 0.5, 0.8, 0.3   # foro, passo, spostamento verso l'esterno rispetto al bordo scheda
CONFIGURAZIONI = {
    "pannello_3x1": dict(n=3, rail_lat=0.0),
    "pannello_2x1": dict(n=2, rail_lat=3.0),
}
EDGE = pcbnew.Edge_Cuts


def cli(*argomenti):
    r = subprocess.run([str(CLI), *map(str, argomenti)], capture_output=True, text=True)
    if r.returncode not in (0,):
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout


def vec(x, y):
    return VECTOR2I(mm_(x), mm_(y))


def linea(b, x1, y1, x2, y2, layer=EDGE, w=0.1):
    if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
        return
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(layer)
    s.SetStart(vec(x1, y1))
    s.SetEnd(vec(x2, y2))
    s.SetWidth(mm_(w))
    b.Add(s)


def segmenti_orizz(b, y, x0, x1, tagli):
    """Linea orizzontale da x0 a x1 interrotta negli intervalli `tagli` (linguette)."""
    x = x0
    for a, c in sorted(tagli):
        linea(b, x, y, a, y)
        x = c
    linea(b, x, y, x1, y)


def aggiungi_netinfo(panel, nome):
    n = panel.FindNet(nome)
    if n is None:
        n = pcbnew.NETINFO_ITEM(panel, nome)
        panel.Add(n)
    return n


def sposta_in(panel, sorgente, dx, dy, idx, primo):
    """Sposta tutto il contenuto di `sorgente` (tranne Edge.Cuts) nel pannello, rinominando i designatori."""
    off = vec(dx, dy)
    for f in list(sorgente.GetFootprints()):
        sorgente.RemoveNative(f)
        f.Move(off)
        f.SetReference(f"{f.GetReference()}_{idx}")
        for p in f.Pads():
            if p.GetNetname():
                p.SetNet(aggiungi_netinfo(panel, f"B{idx}_{p.GetNetname()}"))
        panel.Add(f)
    for t in list(sorgente.GetTracks()):
        sorgente.RemoveNative(t)
        t.Move(off)
        t.SetNet(aggiungi_netinfo(panel, f"B{idx}_{t.GetNetname()}"))
        panel.Add(t)
    for z in list(sorgente.Zones()):
        sorgente.RemoveNative(z)
        z.Move(off)
        z.SetNet(aggiungi_netinfo(panel, f"B{idx}_{z.GetNetname()}"))
        panel.Add(z)
    for d in list(sorgente.GetDrawings()):
        sorgente.RemoveNative(d)
        if d.GetLayer() == EDGE:
            continue
        d.Move(off)
        panel.Add(d)


def foro_npth(panel, x, y, d, rif):
    f = pcbnew.FOOTPRINT(panel)
    f.SetReference(rif)
    f.SetValue("NPTH")
    f.Reference().SetVisible(False)
    f.Value().SetVisible(False)
    f.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    p = pcbnew.PAD(f)
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(mm_(d), mm_(d)))
    p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
    p.SetDrillSize(pcbnew.VECTOR2I(mm_(d), mm_(d)))
    p.SetLayerSet(pcbnew.LSET.AllCuMask())
    p.SetNumber("")
    f.Add(p)
    f.SetPosition(vec(x, y))
    panel.Add(f)


def fiducial(panel, x, y, rif):
    f = pcbnew.FootprintLoad(str(FP_LIB / "Fiducial.pretty"), "Fiducial_1mm_Mask2mm")
    f.SetReference(rif)
    f.Reference().SetVisible(False)
    f.Value().SetVisible(False)
    f.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    f.SetPosition(vec(x, y))
    panel.Add(f)


def costruisci(nome, n, rail_lat, out):
    panel = pcbnew.LoadBoard(str(PCB))
    # reti per scheda (B1_/GND, B2_/GND, ...): senza prefisso il DRC vedrebbe le schede come collegate tra loro
    for nm, net in list(panel.GetNetInfo().NetsByName().items()):
        if nm:
            net.SetNetname(f"B1_{nm}")
    xs = []
    x0 = rail_lat + (GAP if rail_lat else 0.0)       # x del bordo sinistro della prima scheda
    wtot = 2 * x0 + n * W_S + (n - 1) * GAP
    y0 = RAIL + GAP                                   # y del bordo alto delle schede
    for i in range(n):
        xs.append(x0 + i * (W_S + GAP))
    # prima copia = la scheda caricata; le altre da file nuovi
    sorg = [panel] + [pcbnew.LoadBoard(str(PCB)) for _ in range(n - 1)]
    for i, (b, x) in enumerate(zip(sorg, xs), start=1):
        if i == 1:
            # il contenuto sta gia' nel pannello: sposta in loco
            off = vec(x, y0)
            for f in panel.GetFootprints():
                f.Move(off)
                f.SetReference(f"{f.GetReference()}_1")
            for t in panel.GetTracks():
                t.Move(off)
            for z in panel.Zones():
                z.Move(off)
            for d in list(panel.GetDrawings()):
                if d.GetLayer() == EDGE:
                    panel.RemoveNative(d)
                else:
                    d.Move(off)
        else:
            sposta_in(panel, b, x, y0, i, False)

    # --- contorno (Edge.Cuts) ---
    tabs_x = [(x + TAB_TOP_X, x + TAB_BOT_X) for x in xs]  # (alto, basso)
    tagli_alto = [(tx - TAB_W / 2, tx + TAB_W / 2) for tx, _ in tabs_x]
    tagli_basso = [(bx - TAB_W / 2, bx + TAB_W / 2) for _, bx in tabs_x]
    ytop, ybot = y0, y0 + H_S
    for x in xs:   # bordi sinistro/destro delle schede
        linea(panel, x, ytop, x, ybot)
        linea(panel, x + W_S, ytop, x + W_S, ybot)
    for x in xs:   # bordi alto e basso delle schede, interrotti dalle linguette
        ta = [t for t in tagli_alto if x <= t[0] and t[1] <= x + W_S]
        tb = [t for t in tagli_basso if x <= t[0] and t[1] <= x + W_S]
        segmenti_orizz(panel, ytop, x, x + W_S, ta)
        segmenti_orizz(panel, ybot, x, x + W_S, tb)
    # lati della linguetta (attraversano l'intercapedine)
    for a, c in tagli_alto:
        linea(panel, a, ytop - GAP, a, ytop)
        linea(panel, c, ytop - GAP, c, ytop)
    for a, c in tagli_basso:
        linea(panel, a, ybot, a, ybot + GAP)
        linea(panel, c, ybot, c, ybot + GAP)
    # contorno esterno del pannello e bordo interno delle guide
    yr1, yr2 = RAIL, H_PAN - RAIL                     # bordo interno guida alta / bassa
    if rail_lat == 0:
        # guide separate: senza guide laterali, le schede estreme formano il bordo del pannello
        linea(panel, 0, 0, wtot, 0)
        linea(panel, 0, 0, 0, yr1)
        linea(panel, wtot, 0, wtot, yr1)
        segmenti_orizz(panel, yr1, 0, wtot, tagli_alto)
        linea(panel, 0, H_PAN, wtot, H_PAN)
        linea(panel, 0, yr2, 0, H_PAN)
        linea(panel, wtot, yr2, wtot, H_PAN)
        segmenti_orizz(panel, yr2, 0, wtot, tagli_basso)
    else:
        xi0, xi1 = rail_lat, wtot - rail_lat
        for (a, b_, c, d) in ((0, 0, wtot, 0), (0, H_PAN, wtot, H_PAN), (0, 0, 0, H_PAN), (wtot, 0, wtot, H_PAN)):
            linea(panel, a, b_, c, d)
        segmenti_orizz(panel, yr1, xi0, xi1, tagli_alto)
        segmenti_orizz(panel, yr2, xi0, xi1, tagli_basso)
        linea(panel, xi0, yr1, xi0, yr2)
        linea(panel, xi1, yr1, xi1, yr2)

    # --- mouse bite: fila di fori a BITE_OFF fuori dal bordo scheda, centrata sulla linguetta ---
    k = 0
    for (tx, bx), x in zip(tabs_x, xs):
        for cx, yb in ((tx, ytop - BITE_OFF), (bx, ybot + BITE_OFF)):
            for j in (-1.5, -0.5, 0.5, 1.5):
                k += 1
                foro_npth(panel, cx + j * BITE_PITCH, yb, BITE_D, f"MB{k}")

    # --- fori di tooling (4 agli angoli) e fiducial (3, asimmetrici) sulle guide ---
    for k, (tx, ty) in enumerate([(3, 3), (wtot - 3, 3), (3, H_PAN - 3), (wtot - 3, H_PAN - 3)], 1):
        foro_npth(panel, tx, ty, 1.152, f"TH{k}")
    for k, (fx, fy) in enumerate([(9.0, 4.5), (9.0, H_PAN - 4.5), (wtot - 14.0, H_PAN - 4.5)], 1):
        fiducial(panel, fx, fy, f"FID{k}")

    # scritta sulla guida alta
    t = pcbnew.PCB_TEXT(panel)
    t.SetText(f"SwimTag v0.5 {n}x1")
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm_(1.2), mm_(1.2)))
    t.SetPosition(vec(wtot / 2, 4.5))
    panel.Add(t)

    # ricalcolo delle zone di rame (spostate)
    pcbnew.ZONE_FILLER(panel).Fill(panel.Zones())
    out.mkdir(parents=True, exist_ok=True)
    pcb_out = out / f"{nome}.kicad_pcb"
    panel.Save(str(pcb_out))
    shutil.copy(QUI / f"{NOME}.kicad_pro", out / f"{nome}.kicad_pro")
    # tabella librerie impronte: libreria swimtag relativa alla cartella del pannello (nextpcb/<cartella>/ -> ../../lib)
    tab = (QUI / "fp-lib-table").read_text(encoding="utf-8")
    (out / "fp-lib-table").write_text(tab.replace("${KIPRJMOD}/lib/", "${KIPRJMOD}/../../lib/"), encoding="utf-8")
    return pcb_out, wtot


def esporta(nome, n, pcb_out, out):
    gerber = out / "gerber"
    shutil.rmtree(gerber, ignore_errors=True)
    gerber.mkdir()
    strati = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    cli("pcb", "export", "gerbers", "--layers", strati, "--subtract-soldermask", "-o", gerber, pcb_out)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", gerber, pcb_out)
    with zipfile.ZipFile(out / "swimtag_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gerber.iterdir()):
            z.write(f, f.name)
    # CPL: stesso comando del pannello singolo (pos nativo KiCad, Y = -Y della scheda), poi formato Designator/Mid X...
    pos = out / "pos_kicad_nativo.csv"
    cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "-o", pos, pcb_out)
    righe = []
    with pos.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            base = r["Ref"].rsplit("_", 1)[0]
            if base in ESCLUSI or r["Ref"].startswith(("FID", "TH", "MB")):
                continue
            righe.append(r)
    with (out / "cpl_nextpcb.csv").open("w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in righe:
            w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                        "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]) % 360:.0f}'])
    # centroid nel layout del pannello singolo (Ref,Val,Package,PosX,PosY,Rot,Side): csv intermedio -> xlsx
    with (out / "centroid_nextpcb.csv").open("w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["Ref", "Val", "Package", "PosX", "PosY", "Rot", "Side"])
        for r in righe:
            w.writerow([r["Ref"], r["Val"], r["Package"], r["PosX"], r["PosY"], r["Rot"], r["Side"]])
    pos.unlink()

    # BOM: dalla BOM singola, J1 escluso, designatori per scheda, quantita' x n
    with BOM_SINGOLA.open(encoding="utf-8") as f:
        rd = csv.reader(f)
        intest = next(rd)
        bom = []
        for riga in rd:
            des = [d.strip() for d in riga[0].split(",")]
            des = [d for d in des if d not in ESCLUSI]
            if not des:
                continue
            nuovi = [f"{d}_{i}" for i in range(1, n + 1) for d in des]
            bom.append([",".join(nuovi), len(nuovi)] + riga[2:])
    with (out / "bom_nextpcb.csv").open("w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(intest)
        w.writerows(bom)
    cli("pcb", "render", "-o", out / "assembly_top_render.png", "-w", "1600", "-h", "1100", "--quality", "high",
        "--background", "opaque", "--side", "top", pcb_out)
    cli("pcb", "drc", "--format", "report", "--severity-all", "--units", "mm", "-o", out / "drc_pannello.rpt", pcb_out)


def main():
    for nome, c in CONFIGURAZIONI.items():
        out = QUI / "nextpcb" / ("v0.5_" + nome)
        pcb_out, wtot = costruisci(nome, c["n"], c["rail_lat"], out)
        esporta(nome, c["n"], pcb_out, out)
        print(nome, f"{wtot:.2f} x {H_PAN:.2f} mm ->", out)


if __name__ == "__main__":
    main()
