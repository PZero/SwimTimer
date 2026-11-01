"""Aggiunge a lib/ i simboli e le impronte v0.3 non presenti nelle librerie standard di KiCad
(TPS22916C, MAX17048) e registra le librerie standard usate (connettori, DFN). Idempotente.
Impronta del TPS22916C (YFP, DSBGA-4): vista dall'alto ON/GND sopra, VIN/VOUT sotto (datasheet TI SLVSDO5F, fig. 5-1),
passo 0,4 mm, sfere 0,25 mm. Impronta e simbolo del MAX17048 (TDFN-8 2x2): da riconfrontare con l'impronta LCSC prima dello sbroglio."""
from pathlib import Path

QUI = Path(__file__).parent
SYM = QUI / "lib" / "swimtag.kicad_sym"
PRETTY = QUI / "lib" / "swimtag.pretty"


def simbolo(nome, riferimento, impronta, lcsc, w, pins):
    """pins: (numero, nome, x, y, angolo). Stesso formato dei simboli importati da LCSC."""
    h = max(abs(p[3]) for p in pins) + 2.54
    s = [f'  (symbol "{nome}"', '    (in_bom yes)', '    (on_board yes)']
    for i, (n, v, dy, nasc) in enumerate((("Reference", riferimento, h + 2.54, False), ("Value", nome, -h - 2.54, False),
                                           ("Footprint", impronta, -h - 5.08, True), ("Datasheet", "", -h - 7.62, True),
                                           ("LCSC Part", lcsc, -h - 10.16, True))):
        s.append(f'    (property\n      "{n}"\n      "{v}"\n      (id {i})\n      (at 0 {dy:.2f} 0)\n'
                 f'      (effects (font (size 1.27 1.27) ){" hide" if nasc else ""} )\n    )')
    s.append(f'    (symbol "{nome}_0_1"\n      (rectangle\n        (start {-w} {h})\n        (end {w} {-h})\n'
             '        (stroke (width 0) (type default))\n        (fill (type background))\n      )')
    for num, nm, x, y, ang in pins:
        s.append(f'      (pin unspecified line\n        (at {x:.2f} {y:.2f} {ang})\n        (length 5.08)\n'
                 f'        (name "{nm}" (effects (font (size 1.27 1.27))))\n'
                 f'        (number "{num}" (effects (font (size 1.27 1.27))))\n      )')
    s.append('    )\n  )\n')
    return "\n".join(s)


SIMBOLI = {
    "TPS22916CYFPR": simbolo("TPS22916CYFPR", "U", "swimtag:DSBGA-4_L0.78-W0.78-P0.40", "C2680319", 7.62, [
        ("A2", "VIN", -12.70, 2.54, 0), ("B2", "ON", -12.70, -2.54, 0),
        ("A1", "VOUT", 12.70, 2.54, 180), ("B1", "GND", 12.70, -2.54, 180)]),
    "MAX17048G+T10": simbolo("MAX17048G+T10", "U", "Package_DFN_QFN:TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm", "C2682616", 7.62, [
        ("3", "VDD", -12.70, 5.08, 0), ("2", "CELL", -12.70, 2.54, 0), ("1", "CTG", -12.70, 0, 0),
        ("6", "QSTRT", -12.70, -2.54, 0),
        ("8", "SDA", 12.70, 5.08, 180), ("7", "SCL", 12.70, 2.54, 180), ("5", "ALRT", 12.70, 0, 180),
        ("4", "GND", 12.70, -2.54, 180), ("9", "EP", 12.70, -5.08, 180)]),
}

FP_TPS = """(module swimtag:DSBGA-4_L0.78-W0.78-P0.40 (layer F.Cu) (tedit 5DC5F6A4)
	(attr smd)
	(fp_text reference REF** (at 0 -1.2) (layer F.SilkS)
		(effects (font (size 0.5 0.5) (thickness 0.08)))
	)
	(fp_text value DSBGA-4_L0.78-W0.78-P0.40 (at 0 1.2) (layer F.Fab)
		(effects (font (size 0.5 0.5) (thickness 0.08)))
	)
	(property "LCSC Part" "C2680319")
	(pad A1 smd circle (at 0.20 0.20) (size 0.200 0.200) (layers F.Cu F.Paste F.Mask))
	(pad A2 smd circle (at -0.20 0.20) (size 0.200 0.200) (layers F.Cu F.Paste F.Mask))
	(pad B1 smd circle (at 0.20 -0.20) (size 0.200 0.200) (layers F.Cu F.Paste F.Mask))
	(pad B2 smd circle (at -0.20 -0.20) (size 0.200 0.200) (layers F.Cu F.Paste F.Mask))
	(fp_line (start -0.39 -0.39) (end 0.39 -0.39) (layer F.Fab) (width 0.05))
	(fp_line (start 0.39 -0.39) (end 0.39 0.39) (layer F.Fab) (width 0.05))
	(fp_line (start 0.39 0.39) (end -0.39 0.39) (layer F.Fab) (width 0.05))
	(fp_line (start -0.39 0.39) (end -0.39 -0.39) (layer F.Fab) (width 0.05))
	(fp_circle (center -0.55 0.55) (end -0.50 0.55) (layer F.SilkS) (width 0.06))
	(fp_line (start -0.6 -0.6) (end 0.6 -0.6) (layer F.CrtYd) (width 0.05))
	(fp_line (start 0.6 -0.6) (end 0.6 0.6) (layer F.CrtYd) (width 0.05))
	(fp_line (start 0.6 0.6) (end -0.6 0.6) (layer F.CrtYd) (width 0.05))
	(fp_line (start -0.6 0.6) (end -0.6 -0.6) (layer F.CrtYd) (width 0.05))
)
"""


def main():
    t = SYM.read_text(encoding="utf-8")
    for nome, s in SIMBOLI.items():
        if f'(symbol "{nome}"' not in t:
            t = t.rstrip()
            assert t.endswith(")")
            t = t[:-1].rstrip() + "\n\n" + s + ")\n"
            print("aggiunto simbolo", nome)
    SYM.write_text(t, encoding="utf-8")
    (PRETTY / "DSBGA-4_L0.78-W0.78-P0.40.kicad_mod").write_text(FP_TPS, encoding="utf-8")
    fp = QUI / "fp-lib-table"
    ft = fp.read_text(encoding="utf-8")
    for lib in ("Connector_JST", "Connector_PinHeader_1.27mm", "Package_DFN_QFN"):
        if f'(name "{lib}")' not in ft:
            ft = ft.rstrip()[:-1].rstrip() + (f'\n  (lib (name "{lib}")(type "KiCad")(uri "${{KICAD10_FOOTPRINT_DIR}}/{lib}.pretty")'
                                              '(options "")(descr ""))\n)\n')
    fp.write_text(ft, encoding="utf-8")
    sp = QUI / "sym-lib-table"
    st = sp.read_text(encoding="utf-8")
    if '(name "Connector_Generic")' not in st:
        st = st.rstrip()[:-1].rstrip() + ('\n  (lib (name "Connector_Generic")(type "KiCad")(uri "${KICAD10_SYMBOL_DIR}/Connector_Generic.kicad_sym")'
                                          '(options "")(descr ""))\n)\n')
    sp.write_text(st, encoding="utf-8")


if __name__ == "__main__":
    main()
