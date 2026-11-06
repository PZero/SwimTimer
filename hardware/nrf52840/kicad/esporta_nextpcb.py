"""File per l'ordine Rev0 PCBA di NextPCB della scheda singola v0.6 -> nextpcb/v0.6/ (stessi formati di nextpcb/v0.5/).

Uso (Python di KiCad, SWIMTAG_VARIANTE=v06):  python.exe esporta_nextpcb.py
  swimtag_gerber.zip      Gerber RS-274X + fori Excellon (4 strati: F.Cu, In1.Cu, In2.Cu, B.Cu)
  bom_nextpcb.csv / .xlsx Designator, Quantity, Value, Description, Manufacturer, MPN, Footprint, LCSC Part # (J1 DNP escluso)
  cpl_nextpcb.csv         centroide nativo KiCad (Ref,Val,Package,PosX,PosY,Rot,Side): rotazioni NATIVE, nessuna correzione JLC
  centroid_nextpcb.xlsx/.zip  lo stesso centroide in xlsx / zippato (come nella v0.5)
  assembly_top_render.png render 3D dall'alto
Dopo: python csv_a_xlsx-equivalente e' integrato qui (serve openpyxl: se manca nel Python di KiCad, i .xlsx si fanno con il Python di sistema: python esporta_nextpcb.py --xlsx).
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

QUI = Path(__file__).parent
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
CLI = KICAD / "bin" / "kicad-cli.exe"
OUT = QUI / "nextpcb" / "v0.6"
PCB = QUI / "swimtag_v06.kicad_pcb"
SCH = QUI / "swimtag_v06.kicad_sch"
BOM_V05 = QUI / "nextpcb" / "v0.5" / "bom_nextpcb.csv"
STRATI = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

# componenti nuovi della v0.6 (gli altri si leggono dalla BOM v0.5 tramite il codice LCSC): codice -> (descrizione, produttore, MPN)
NUOVI = {
    "C424093": ("Li-ion charger 4.20V 15-500mA SOT-23-5", "Microchip", "MCP73831T-2ACI/OT"),
    "C2681320": ("load switch 1-5.5V 2A SOT-23-6", "Texas Instruments", "TPS22917DBVR"),
    "C2128": ("Switching diode 100V 150mA SOD-323", "JSCJ", "1N4148WS"),
    "C172114": ("66.5k 1% 0402", "Walsin", "WR04X6652FTL"),
}


def cli(*a):
    subprocess.run([str(CLI), *map(str, a)], check=True, capture_output=True)


def chiave_nat(d):
    m = re.match(r"([A-Za-z]+)(\d+)", d)
    return (m.group(1), int(m.group(2)))


def bom():
    noti = {}
    with BOM_V05.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            noti[r["LCSC Part #"]] = (r["Description"], r["Manufacturer"], r["MPN"])
    noti.update(NUOVI)
    tmp = OUT / "bom_kicad.csv"
    cli("sch", "export", "bom", "--fields", "Value,Reference,Footprint,LCSC,${QUANTITY}",
        "--labels", "Value,Designator,Footprint,LCSC,Quantity", "--ref-range-delimiter", "",
        "--group-by", "Value,Footprint,LCSC", "--exclude-dnp", "-o", tmp, SCH)
    righe = []
    with tmp.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            des = sorted((d.strip() for d in r["Designator"].replace(";", ",").split(",") if d.strip()), key=chiave_nat)
            if not r["LCSC"]:       # piazzole: fuori dalla BOM
                continue
            desc, prod, mpn = noti[r["LCSC"]]
            righe.append((des, r["Value"], desc, prod, mpn, r["Footprint"].split(":")[-1], r["LCSC"]))
    tmp.unlink()
    righe.sort(key=lambda x: chiave_nat(x[0][0]))
    with (OUT / "bom_nextpcb.csv").open("w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Quantity", "Value", "Description", "Manufacturer", "MPN", "Footprint", "LCSC Part #"])
        for des, val, desc, prod, mpn, fp, lcsc in righe:
            w.writerow([",".join(des), len(des), val, desc, prod, mpn, fp, lcsc])
    return righe


def xlsx():
    import openpyxl
    for nome, num in (("centroid_nextpcb", (3, 4, 5)), ("bom_nextpcb", (1,))):
        src = OUT / ("cpl_nextpcb.csv" if nome == "centroid_nextpcb" else "bom_nextpcb.csv")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet"
        for i, riga in enumerate(csv.reader(src.open(encoding="utf-8"))):
            ws.append([(int(c) if nome == "bom_nextpcb" else float(c)) if i and k in num else c for k, c in enumerate(riga)])
        wb.save(OUT / f"{nome}.xlsx")


def main():
    if "--xlsx" in sys.argv:
        return xlsx()
    OUT.mkdir(parents=True, exist_ok=True)
    gerber = OUT / "gerber"
    shutil.rmtree(gerber, ignore_errors=True)
    gerber.mkdir()
    cli("pcb", "export", "gerbers", "--layers", STRATI, "--subtract-soldermask", "-o", gerber, PCB)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", gerber, PCB)
    with zipfile.ZipFile(OUT / "swimtag_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gerber.iterdir()):
            z.write(f, f.name)
    shutil.rmtree(gerber)       # come nella v0.5 singola: solo lo zip
    cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "--exclude-dnp",
        "-o", OUT / "cpl_nextpcb.csv", PCB)
    with zipfile.ZipFile(OUT / "centroid_nextpcb.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(OUT / "cpl_nextpcb.csv", "cpl_nextpcb.csv")
    righe = bom()
    cli("pcb", "render", "-o", OUT / "assembly_top_render.png", "-w", "1600", "-h", "1100", "--quality", "high",
        "--background", "opaque", "--side", "top", PCB)
    try:
        xlsx()
    except ImportError:
        print("openpyxl non trovato: eseguire  python esporta_nextpcb.py --xlsx  con il Python di sistema")
    print("nextpcb/v0.6:", len(righe), "righe di BOM")


if __name__ == "__main__":
    main()
