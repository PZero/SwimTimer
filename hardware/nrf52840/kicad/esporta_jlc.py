"""Esporta i file per l'ordine JLCPCB in jlc/: Gerber + fori (zip), BOM e CPL nel formato JLC, render.

Uso (Python normale o di KiCad):  python esporta_jlc.py
"""
import csv
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

QUI = Path(__file__).parent
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
CLI = KICAD / "bin" / "kicad-cli.exe"
from dati_scheda import NOME
OUT = QUI / "jlc" / f"v0.3_{NOME}"
PCB = QUI / f"{NOME}.kicad_pcb"
SCH = QUI / f"{NOME}.kicad_sch"
STRATI = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def cli(*argomenti):
    subprocess.run([str(CLI), *map(str, argomenti)], check=True, capture_output=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gerber = OUT / "gerber"
    shutil.rmtree(gerber, ignore_errors=True)
    gerber.mkdir()
    cli("pcb", "export", "gerbers", "--layers", STRATI, "--subtract-soldermask", "-o", gerber, PCB)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", gerber, PCB)
    with zipfile.ZipFile(OUT / "swimtag_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gerber.iterdir()):
            z.write(f, f.name)

    # BOM: un rigo per valore/impronta/codice LCSC, piazzole escluse (in_bom no nello schema)
    cli("sch", "export", "bom", "--fields", "Value,Reference,Footprint,LCSC,${QUANTITY}",
        "--labels", "Comment,Designator,Footprint,LCSC Part #,Quantity",
        "--group-by", "Value,Footprint,LCSC", "--exclude-dnp", "-o", OUT / "bom_jlc.csv", SCH)

    # CPL: posizioni dei componenti montati da JLC (solo lato sopra)
    pos = OUT / "pos_kicad.csv"
    cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front",
        "-o", pos, PCB)
    with pos.open(encoding="utf-8") as f, (OUT / "cpl_jlc.csv").open("w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in csv.DictReader(f):
            w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                        "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]) % 360:.0f}'])
    pos.unlink()

    for lato, extra in (("sopra", ["--side", "top"]), ("sotto", ["--side", "bottom"]),
                        ("3d", ["--rotate", "-40,0,30", "--perspective"])):
        cli("pcb", "render", "-o", OUT / f"render_{lato}.png", "-w", "1200", "-h", "1000",
            "--quality", "high", "--background", "opaque", *extra, PCB)
    cli("sch", "export", "pdf", "-o", OUT / "schema.pdf", SCH)
    print("file per JLC in", OUT)


if __name__ == "__main__":
    main()
