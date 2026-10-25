"""Genera swimtag.kicad_pcb dai dati di dati_scheda.py (componenti piazzati, reti, zone, regole JLC).

Da eseguire con il Python di KiCad:
  "C:\\Users\\<utente>\\AppData\\Local\\Programs\\KiCad\\10.0\\bin\\python.exe" genera_pcb.py
Le piste non vengono tracciate qui: lo sbroglio si fa dopo (KiCad o Freerouting).
"""
import os
from pathlib import Path

import pcbnew

from dati_scheda import ANTENNA_H, COMPONENTI, SCHEDA_H, SCHEDA_L
from genera_schema import uid

QUI = Path(__file__).parent
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
FP_KICAD = KICAD / "share" / "kicad" / "footprints"
mm = pcbnew.FromMM


def punto(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def carica_impronta(nome):
    lib, fp = nome.split(":")
    cartella = QUI / "lib" / "swimtag.pretty" if lib == "swimtag" else FP_KICAD / f"{lib}.pretty"
    return pcbnew.FootprintLoad(str(cartella), fp)


def rettangolo(board, layer, x0, y0, x1, y1, larghezza=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(punto(x0, y0))
    s.SetEnd(punto(x1, y1))
    s.SetLayer(layer)
    s.SetWidth(mm(larghezza))
    board.Add(s)


def zona(board, nome_rete, layer, x0, y0, x1, y1, reti):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(reti[nome_rete])
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        z.AppendCorner(punto(x, y), -1)
    z.SetMinThickness(mm(0.15))
    z.SetLocalClearance(mm(0.15))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)  # massa piena: niente raggi termici "affamati" sui pad piccoli
    board.Add(z)


def main(solo_piano_interno=False):
    """solo_piano_interno=True: solo il piano di massa In1 (per lo sbroglio con Freerouting)."""
    board = pcbnew.NewBoard(str(QUI / "swimtag.kicad_pcb"))
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    # regole JLCPCB 4 strati (capacità standard, senza sovrapprezzo)
    ds.m_TrackMinWidth = mm(0.1)
    ds.m_MinClearance = mm(0.1)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.2)
    ds.m_HoleClearance = mm(0.2)  # JLC: foro-rame 0,2 mm
    ds.SetBoardThickness(mm(0.8))
    ds.m_TentViasFront = True   # via coperti dal solder mask: sotto il modulo non devono toccare nulla
    ds.m_TentViasBack = True
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(mm(0.127))  # 5 mil: serve per uscire dal BGA del caricatore (passo 0,4)
    nc.SetClearance(mm(0.1))
    nc.SetViaDiameter(mm(0.5))   # foro 0,3 mm: nessun sovrapprezzo JLC
    nc.SetViaDrill(mm(0.3))

    # contorno con angoli arrotondati (r = 1 mm) tranne il bordo dell'antenna, che resta dritto
    rettangolo(board, pcbnew.Edge_Cuts, 0, 0, SCHEDA_L, SCHEDA_H)

    reti = {}
    for comp in COMPONENTI:
        for net in comp[5].values():
            if net not in reti:
                reti[net] = pcbnew.NETINFO_ITEM(board, "/" + net)  # come le etichette dello schema
                board.Add(reti[net])

    for rif, _, valore, impronta, lcsc, pins, (x, y, rot, lato) in COMPONENTI:
        fp = carica_impronta(impronta)
        fp.SetReference(rif)
        fp.SetValue(valore)
        fp.SetFPIDAsString(impronta)
        fp.SetPath(pcbnew.KIID_PATH(f"/{uid(rif)}"))
        fp.SetField("LCSC", lcsc)
        if not lcsc:  # piazzole: non vanno in distinta né nel file di montaggio
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp)
        fp.SetPosition(punto(x, y))
        fp.SetOrientationDegrees(rot)
        if lato == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for pad in fp.Pads():
            n = pad.GetNumber()
            chiave = int(n) if n.isdigit() else n
            if chiave in pins:
                pad.SetNet(reti[pins[chiave]])
            elif rif == "U3" and n in ("", "9"):   # pad termico della flash
                pad.SetNet(reti["GND"])
        # in serigrafia solo i riferimenti, piccoli; nascosti valore, codice LCSC e testi delle librerie
        for campo in fp.GetFields():
            campo.SetVisible(campo.IsReference())
        for disegno in fp.GraphicalItems():
            if isinstance(disegno, pcbnew.PCB_TEXT):
                disegno.SetVisible(False)
        # riferimenti sullo strato Fab (documentazione): in serigrafia sarebbero sotto 0,8 mm, illeggibili per JLC
        fp.Reference().SetLayer(pcbnew.B_Fab if lato == "B" else pcbnew.F_Fab)
        fp.Reference().SetTextSize(punto(0.5, 0.5))
        fp.Reference().SetTextThickness(mm(0.08))

    # piani di massa: interno 1 e 2 interi, sopra e sotto riempimento di massa
    strati = (pcbnew.In1_Cu,) if solo_piano_interno else (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    for layer in strati:
        zona(board, "GND", layer, 0.25, 0.25, SCHEDA_L - 0.25, SCHEDA_H - 0.25, reti)

    # zona dell'antenna: niente rame su nessuno strato (foglio Raytac, 3,8 mm dal bordo)
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetLayerSet(pcbnew.LSET.AllCuMask())
    k.SetDoNotAllowTracks(True)
    k.SetDoNotAllowVias(True)
    k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowPads(False)
    k.SetDoNotAllowFootprints(False)
    for x, y in ((0, 0), (SCHEDA_L, 0), (SCHEDA_L, ANTENNA_H), (0, ANTENNA_H)):
        k.AppendCorner(punto(x, y), -1)
    k.SetZoneName("antenna")
    board.Add(k)

    # testo in serigrafia sotto
    t = pcbnew.PCB_TEXT(board)
    t.SetText("SwimTimer tag v0.1")
    t.SetLayer(pcbnew.B_SilkS)
    t.SetPosition(punto(SCHEDA_L / 2, 14.0))
    t.SetTextSize(punto(0.8, 0.8))
    t.SetTextThickness(mm(0.12))
    t.SetMirrored(True)
    board.Add(t)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(QUI / "swimtag.kicad_pcb"))
    print("scritto swimtag.kicad_pcb:", len(COMPONENTI), "componenti,", len(reti), "reti")


if __name__ == "__main__":
    main()
