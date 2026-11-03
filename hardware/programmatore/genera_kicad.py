"""Genera il progetto KiCad dell'adattatore: swimtag_programmatore.kicad_pro / _sch / _pcb.

Le coordinate vengono lette dal PCB del tag (vedi modello.py). Uso:  python genera_kicad.py [--drc]
Con --drc esegue anche DRC ed ERC con kicad-cli (percorso in KICAD_CLI o default di Windows).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from modello import QUI, LARG_PISTA, DIST_MIN, HAT_R, costruisci, uid

NOME = "swimtag_programmatore"
VERSIONE = "0.4"
OFF = (60.0, 100.0)    # spostamento sul foglio A4 di KiCad (le coordinate dell'adattatore possono essere negative)
KICAD_CLI = os.environ.get("KICAD_CLI", str(Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"))


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if "." in f"{v:.4f}" else f"{v}"


def testo_silk(x, y, s, h=1.0, rot=0, strato="F.SilkS"):
    return (f'\t(gr_text "{s}"\n\t\t(at {f(x + OFF[0])} {f(y + OFF[1])} {rot})\n\t\t(layer "{strato}")\n'
            f'\t\t(uuid "{uid("txt", s, x, y)}")\n\t\t(effects (font (size {h} {h}) (thickness {round(h * 0.15, 2)}))))\n')


def contorno(m):
    """Contorno dell'HAT con angoli arrotondati (gr_line + gr_arc)."""
    xmin, ymin, xmax, ymax = m["bordo"]
    r = HAT_R
    k = 1 - 0.70710678
    s = []
    def ln(a, b, n):
        s.append(f'\t(gr_line\n\t\t(start {f(a[0] + OFF[0])} {f(a[1] + OFF[1])})\n\t\t(end {f(b[0] + OFF[0])} {f(b[1] + OFF[1])})\n'
                 f'\t\t(stroke (width 0.1) (type default))\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid("edge", n)}")\n\t)\n')
    def arco(a, mid, b, n):
        s.append(f'\t(gr_arc\n\t\t(start {f(a[0] + OFF[0])} {f(a[1] + OFF[1])})\n\t\t(mid {f(mid[0] + OFF[0])} {f(mid[1] + OFF[1])})\n'
                 f'\t\t(end {f(b[0] + OFF[0])} {f(b[1] + OFF[1])})\n\t\t(stroke (width 0.1) (type default))\n\t\t(layer "Edge.Cuts")\n'
                 f'\t\t(uuid "{uid("edge", n)}")\n\t)\n')
    ln((xmin + r, ymin), (xmax - r, ymin), 1)
    ln((xmax, ymin + r), (xmax, ymax - r), 2)
    ln((xmax - r, ymax), (xmin + r, ymax), 3)
    ln((xmin, ymax - r), (xmin, ymin + r), 4)
    arco((xmax - r, ymin), (xmax - r * k, ymin + r * k), (xmax, ymin + r), 5)
    arco((xmax, ymax - r), (xmax - r * k, ymax - r * k), (xmax - r, ymax), 6)
    arco((xmin + r, ymax), (xmin + r * k, ymax - r * k), (xmin, ymax - r), 7)
    arco((xmin, ymin + r), (xmin + r * k, ymin + r * k), (xmin + r, ymin), 8)
    return "".join(s)


def testo_rame(t):
    return (f'\t(gr_text "{t["s"]}"\n\t\t(at {f(t["cx"] + OFF[0])} {f(t["cy"] + OFF[1])} 0)\n\t\t(layer "F.Cu")\n'
            f'\t\t(uuid "{uid("txt-rame", t["s"])}")\n\t\t(effects (font (size {t["h"]} {t["h"]}) (thickness 0.5))))\n')


def pcb(m):
    righe = [
        '(kicad_pcb\n\t(version 20260206)\n\t(generator "genera_kicad.py")\n\t(generator_version "10.0")\n'
        '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)\n\t(paper "A4")\n\t(layers\n'
        '\t\t(0 "F.Cu" signal)\n\t\t(2 "B.Cu" signal)\n\t\t(5 "F.SilkS" user "F.Silkscreen")\n\t\t(1 "F.Mask" user)\n'
        '\t\t(3 "B.Mask" user)\n\t\t(17 "Dwgs.User" user "User.Drawings")\n\t\t(19 "Cmts.User" user "User.Comments")\n'
        '\t\t(25 "Edge.Cuts" user)\n\t\t(31 "F.CrtYd" user "F.Courtyard")\n\t\t(35 "F.Fab" user)\n\t)\n'
        '\t(setup\n\t\t(pad_to_mask_clearance 0)\n\t\t(allow_soldermask_bridges_in_footprints no)\n\t)\n']
    gruppi = {}
    for q in m["pads"]:
        gruppi.setdefault(q["ref"], []).append(q)
    for ref, pads in gruppi.items():
        ox, oy = pads[0]["x"], pads[0]["y"]
        info = m["fp"][ref]
        s = [f'\t(footprint "{info["lib"]}"\n\t\t(layer "F.Cu")\n\t\t(uuid "{uid("fp", ref)}")\n'
             f'\t\t(at {f(ox + OFF[0])} {f(oy + OFF[1])})\n'
             f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 -3.2 0)\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n'
             f'\t\t\t(uuid "{uid("fp", ref, "r")}")\n\t\t\t(effects (font (size 1 1) (thickness 0.15))))\n'
             f'\t\t(property "Value" "{info["valore"]}"\n\t\t\t(at 0 3.2 0)\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n'
             f'\t\t\t(uuid "{uid("fp", ref, "v")}")\n\t\t\t(effects (font (size 1 1) (thickness 0.15))))\n'
             f'\t\t(path "/{uid("sym", ref)}")\n\t\t(attr through_hole exclude_from_pos_files exclude_from_bom)\n']
        for q in pads:
            net = f'\n\t\t\t(net "{q["rete"]}")' if q["rete"] else ""
            at = f'(at {f(q["x"] - ox)} {f(q["y"] - oy)})'
            if q["npth"]:
                s.append(f'\t\t(pad "" np_thru_hole circle\n\t\t\t{at}\n\t\t\t(size {f(q["foro"])} {f(q["foro"])})\n'
                         f'\t\t\t(drill {f(q["foro"])})\n\t\t\t(layers "*.Cu" "*.Mask")\n\t\t\t(uuid "{uid("pad", ref, q["num"])}")\n\t\t)\n')
            elif q.get("smd"):
                s.append(f'\t\t(pad "{q["num"]}" smd rect\n\t\t\t{at}\n\t\t\t(size {f(q["w"])} {f(q["h"])})\n'
                         f'\t\t\t(layers "F.Cu" "F.Mask"){net}\n\t\t\t(uuid "{uid("pad", ref, q["num"])}")\n\t\t)\n')
            else:
                forma = "oval" if q["forma"] == "oval" else "circle"
                s.append(f'\t\t(pad "{q["num"]}" thru_hole {forma}\n\t\t\t{at}\n\t\t\t(size {f(q["w"])} {f(q["h"])})\n'
                         f'\t\t\t(drill {f(q["foro"])})\n\t\t\t(layers "F.Cu" "F.Mask"){net}\n\t\t\t(uuid "{uid("pad", ref, q["num"])}")\n\t\t)\n')
        s.append('\t)\n')
        righe.append("".join(s))
    for k, (rete, pts) in enumerate(m["piste"]):
        for i in range(len(pts) - 1):
            (xa, ya), (xb, yb) = pts[i], pts[i + 1]
            righe.append(f'\t(segment\n\t\t(start {f(xa + OFF[0])} {f(ya + OFF[1])})\n\t\t(end {f(xb + OFF[0])} {f(yb + OFF[1])})\n'
                         f'\t\t(width {LARG_PISTA})\n\t\t(layer "F.Cu")\n\t\t(net "{rete}")\n\t\t(uuid "{uid("seg", k, i)}")\n\t)\n')
    righe.append(contorno(m))
    righe.append(f'\t(gr_rect\n\t\t(start {f(m["x0"] + OFF[0])} {f(m["y0"] + OFF[1])})\n\t\t(end {f(m["x1"] + OFF[0])} {f(m["y1"] + OFF[1])})\n'
                 f'\t\t(stroke (width 0.15) (type dash))\n\t\t(fill no)\n\t\t(layer "Dwgs.User")\n\t\t(uuid "{uid("tag")}")\n\t)\n')
    for t in m["testi"]:
        righe.append(testo_rame(t))
    righe.append(testo_silk(m["x0"] + m["W"] / 2, m["y0"] - 2.5, "TAG (faccia in giu')", 0.8))
    righe.append(testo_silk(18.5, m["vp"] + 2.2, "VDD solo tester", 0.8))
    righe.append('(embedded_fonts no)\n)\n')
    return "".join(righe)


def sch(m):
    """Schema 'a etichette': ogni simbolo ha le etichette di rete sui pin."""
    gruppi = {}
    for q in m["pads"]:
        if q["rete"] or q["ref"][0] in "JR PFD":
            gruppi.setdefault(q["ref"], []).append(q)
    def simbolo(nome, nums):
        npin = len(nums)
        h = 2.54 * npin + 1.27
        pins = ""
        for i, nn in enumerate(nums):
            pins += (f'(pin passive line (at -5.08 {-2.54 * i - 2.54:g} 0) (length 2.54) '
                     f'(name "{nn}" (effects (font (size 1.27 1.27)))) (number "{nn}" (effects (font (size 1.27 1.27)))))\n')
        return (f'(symbol "SwimJig:{nome}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)\n'
                f'(property "Reference" "X" (at 0 1.27 0) (effects (font (size 1.27 1.27))))\n'
                f'(property "Value" "{nome}" (at 0 {-h - 1.27:g} 0) (effects (font (size 1.27 1.27))))\n'
                f'(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                f'(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                f'(symbol "{nome}_0_1" (rectangle (start -2.54 0) (end 5.08 {-h:g}) (stroke (width 0.254) (type default)) (fill (type background))))\n'
                f'(symbol "{nome}_1_1"\n{pins})\n)')
    lib, inst, lab = {}, [], []
    ordine = list(gruppi)
    for k, ref in enumerate(ordine):
        pads = sorted(gruppi[ref], key=lambda q: q["num"])
        n = len(pads)
        nums = [q["num"] if q["num"] else "1" for q in pads]
        nome = f"Sym{n}pin" if ref != "J1" else "SymHAT"
        if nome not in lib:
            lib[nome] = simbolo(nome, nums)
        kk = k if ref != "J1" else 0
        x, y = 50.8 + 38.1 * (kk % 6), 50.8 + 40.64 * (kk // 6)
        if ref == "J1":
            x, y = 330.2, 50.8
        x, y = round(x / 1.27) * 1.27, round(y / 1.27) * 1.27
        info = m["fp"][ref]
        inst.append(
            f'(symbol (lib_id "SwimJig:{nome}") (at {x:g} {y:g} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
            f'(uuid "{uid("sym", ref)}")\n'
            f'  (property "Reference" "{ref}" (at {x:g} {y - 2.54:g} 0) (effects (font (size 1.27 1.27))))\n'
            f'  (property "Value" "{info["valore"]}" (at {x:g} {y + 2.54 * n + 3.81:g} 0) (effects (font (size 1.0 1.0))))\n'
            f'  (property "Footprint" "{info["lib"]}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            f'  (property "Datasheet" "" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            + "".join(f'  (pin "{i + 1}" (uuid "{uid("pin", ref, i + 1)}"))\n' for i in range(n))
            + f'  (instances (project "{NOME}" (path "/{uid("radice")}" (reference "{ref}") (unit 1)))))')
        for i, q in enumerate(pads):
            ax, ay = x - 5.08, y + 2.54 * i + 2.54
            if q["rete"]:
                lab.append(f'(label "{q["rete"].lstrip("/")}" (at {ax:g} {ay:g} 180) (effects (font (size 1.0 1.0)) (justify right bottom)) '
                           f'(uuid "{uid("lab", ref, i)}"))')
            else:
                lab.append(f'(no_connect (at {ax:g} {ay:g}) (uuid "{uid("nc", ref, i)}"))')
    return (f'(kicad_sch (version 20250114) (generator "genera_kicad.py") (generator_version "9.0")\n(uuid "{uid("radice")}") (paper "A2")\n'
            f'(title_block (title "SwimTag - adattatore di programmazione e collaudo") (rev "{VERSIONE}") '
            f'(comment 1 "Generato da genera_kicad.py dal PCB del tag"))\n(lib_symbols\n' + "\n".join(lib.values()) + "\n)\n"
            + "\n".join(inst + lab) + '\n(sheet_instances (path "/" (page "1")))\n)\n')


def progetto():
    return json.dumps({
        "board": {"design_settings": {
            "rules": {"min_clearance": DIST_MIN, "min_track_width": 0.6, "min_copper_edge_clearance": 0.5,
                      "min_hole_clearance": 0.5, "min_hole_to_hole": 0.5, "min_through_hole_diameter": 0.6,
                      "min_text_height": 0.8},
            "rule_severities": {"silk_over_copper": "ignore", "silk_overlap": "ignore", "silk_edge_clearance": "ignore",
                                "annular_width": "warning", "lib_footprint_issues": "ignore",
                                "lib_footprint_mismatch": "ignore", "footprint_type_mismatch": "ignore",
                                "solder_mask_bridge": "ignore", "padstack": "ignore"}}},
        "erc": {"rule_severities": {"lib_symbol_issues": "ignore", "footprint_link_issues": "ignore",
                                    "lib_symbol_mismatch": "ignore"}},
        "meta": {"filename": NOME + ".kicad_pro", "version": 3},
        "net_settings": {"classes": [{"name": "Default", "clearance": DIST_MIN, "track_width": LARG_PISTA,
                                      "via_diameter": 1.6, "via_drill": 0.8}], "meta": {"version": 4}},
    }, indent=2)


def main():
    m = costruisci()
    for a in m["avvisi"]:
        print("AVVISO:", a)
    (QUI / f"{NOME}.kicad_pcb").write_text(pcb(m), encoding="utf-8")
    (QUI / f"{NOME}.kicad_sch").write_text(sch(m), encoding="utf-8")
    (QUI / f"{NOME}.kicad_pro").write_text(progetto(), encoding="utf-8")
    print("scritti", NOME + ".kicad_pcb/.kicad_sch/.kicad_pro", "scheda", [round(v, 2) for v in m["bordo"]])
    if "--drc" in sys.argv:
        for cmd, out in ((["pcb", "drc", "--severity-all", "--format", "report", "-o", "drc.rpt", f"{NOME}.kicad_pcb"], "drc.rpt"),
                         (["sch", "erc", "--severity-all", "-o", "erc.rpt", f"{NOME}.kicad_sch"], "erc.rpt")):
            subprocess.run([KICAD_CLI] + cmd, cwd=QUI)
            if (QUI / out).exists():
                print((QUI / out).read_text(encoding="utf-8", errors="replace")[:3000])


if __name__ == "__main__":
    main()
