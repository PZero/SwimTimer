"""Aggiunge a lib/ simbolo e impronta del modulo Ebyte E73-2G4M08S1C (LCSC C356849), idempotente.

L'impronta (lib/swimtag.pretty/WIRELM-SMD_E73-2G4M08S1C.kicad_mod) e il modello 3D vengono da LCSC con
easyeda2kicad (pip install easyeda2kicad; easyeda2kicad --full --lcsc_id=C356849 --output e73) e sono gia' copiati qui.
Quote verificate sul foglio Ebyte (E73-2G4M08S1C User Manual v1.9, cap. 3): 13,0 x 18,0 x 3,0 mm, passo 1,27 mm;
pad perimetrali 0,8 x 1,0 mm (nell'impronta 0,9 x 2,0: 1 mm di bordo di saldatura fuori dal modulo) e pad interni 0,8 x 0,8
(0,9 x 0,9) a 2,1 mm dal bordo; il pad 1 e il pad 43 sono a 3,97 mm dal bordo dell'antenna.
Questo script riscrive solo il simbolo, con i nomi dei piedini presi dalla tabella del cap. 3 (nome del chip nRF52840).
"""
import re
from pathlib import Path

QUI = Path(__file__).parent
SYM = QUI / "lib" / "swimtag.kicad_sym"
FP = QUI / "lib" / "swimtag.pretty" / "WIRELM-SMD_E73-2G4M08S1C.kicad_mod"

# numero pad -> nome (foglio Ebyte, tabella cap. 3)
NOMI = {1: "P1.11", 2: "P1.10", 3: "P0.03/AIN1", 4: "P0.28/AIN4", 5: "GND", 6: "P1.13", 7: "P0.02/AIN0", 8: "P0.29/AIN5",
        9: "P0.31/AIN7", 10: "P0.30/AIN6", 11: "P0.00/XL1", 12: "P0.26", 13: "P0.01/XL2", 14: "P0.06", 15: "P0.05/AIN3",
        16: "P0.08", 17: "P1.09", 18: "P0.04/AIN2", 19: "VDD", 20: "P0.12", 21: "GND", 22: "P0.07", 23: "VDDH", 24: "GND",
        25: "DCCH", 26: "P0.18/RESET", 27: "VBUS", 28: "P0.15", 29: "USB_D-", 30: "P0.17", 31: "USB_D+", 32: "P0.20",
        33: "P0.13", 34: "P0.22", 35: "P0.24", 36: "P1.00", 37: "SWDIO", 38: "P1.02", 39: "SWDCLK", 40: "P1.04",
        41: "P0.09/NFC1", 42: "P1.06", 43: "P0.10/NFC2"}


def simbolo():
    # layout come easyeda2kicad: sinistra 1-10, sotto 11-25, destra 26-43
    sinistra = [(n, 12.70 - 2.54 * i) for i, n in enumerate(range(1, 11))]
    sotto = [(n, -19.05 + 2.54 * i) for i, n in enumerate(range(11, 26))]
    destra = [(n, -19.05 + 2.54 * i) for i, n in enumerate(range(26, 44))]
    s = ['  (symbol "E73-2G4M08S1C"', '    (in_bom yes)', '    (on_board yes)']
    props = (("Reference", "U", 29.21, False), ("Value", "E73-2G4M08S1C", -30.48, False),
             ("Footprint", "swimtag:WIRELM-SMD_E73-2G4M08S1C", -33.02, True),
             ("Datasheet", "https://lcsc.com/product-detail/C356849.html", -35.56, True), ("LCSC Part", "C356849", -38.10, True))
    for i, (n, v, dy, nasc) in enumerate(props):
        s.append(f'    (property\n      "{n}"\n      "{v}"\n      (id {i})\n      (at 0 {dy:.2f} 0)\n'
                 f'      (effects (font (size 1.27 1.27) ){" hide" if nasc else ""} )\n    )')
    s.append('    (symbol "E73-2G4M08S1C_0_1"\n      (rectangle\n        (start -26.67 25.40)\n        (end 27.94 -22.86)\n'
             '        (stroke (width 0) (type default))\n        (fill (type background))\n      )')

    def pin(n, x, y, ang):
        return (f'      (pin unspecified line\n        (at {x:.2f} {y:.2f} {ang})\n        (length 2.54)\n'
                f'        (name "{NOMI[n]}" (effects (font (size 1.27 1.27))))\n'
                f'        (number "{n}" (effects (font (size 1.27 1.27))))\n      )')
    for n, y in sinistra:
        s.append(pin(n, -29.21, y, 0))
    for n, x in sotto:
        s.append(pin(n, x, -25.40, 90))
    for n, y in destra:
        s.append(pin(n, 30.48, -y if False else y, 180))
    s.append('    )\n  )\n')
    return "\n".join(s)


def main():
    t = SYM.read_text(encoding="utf-8")
    if '(symbol "E73-2G4M08S1C"' not in t:
        t = t.rstrip()
        t = t[:-1].rstrip() + "\n\n" + simbolo() + ")\n"
        SYM.write_text(t, encoding="utf-8")
        print("aggiunto simbolo E73-2G4M08S1C")
    f = FP.read_text(encoding="utf-8")
    f = f.replace("easyeda2kicad:WIRELM", "swimtag:WIRELM").replace('(model "e73.3dshapes/', '(model "${KIPRJMOD}/lib/swimtag.3dshapes/')
    f = re.sub(r"\n\t\(fp_line \(start ([-\d.]+) ([-\d.]+)\) \(end \1 \2\) \(layer F.SilkS\) \(width 0.25\)\)", "", f)  # linee di lunghezza zero
    FP.write_text(f, encoding="utf-8")


if __name__ == "__main__":
    main()
