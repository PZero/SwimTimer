"""Converte centroid_nextpcb.csv e bom_nextpcb.csv di una cartella in xlsx (Python di sistema con openpyxl)."""
import csv
import sys
from pathlib import Path

import openpyxl

cartella = Path(sys.argv[1])
for nome, num in (("centroid_nextpcb", (3, 4, 5)), ("bom_nextpcb", (1,))):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet"
    for i, riga in enumerate(csv.reader((cartella / f"{nome}.csv").open(encoding="utf-8"))):
        ws.append([(int(c) if nome == "bom_nextpcb" else float(c)) if i and k in num else c for k, c in enumerate(riga)])
    wb.save(cartella / f"{nome}.xlsx")
