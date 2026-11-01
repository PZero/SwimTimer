"""Sbroglio automatico con Freerouting: genera il PCB, esporta il DSN, sbroglia, reimporta le piste,
aggiunge i riempimenti di massa e salva swimtag.kicad_pcb.

Da eseguire con il Python di KiCad. Servono Java 25 e il jar di Freerouting 2.5.0:
  set FREEROUTING_JAR=C:\percorso\freerouting-2.5.0.jar
  set JAVA25=C:\Program Files\Eclipse Adoptium\jdk-25...\bin\java.exe
  python.exe sbroglia.py [passate]
"""
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

import genera_pcb
from dati_scheda import NOME, SCHEDA_H_TOT as SCHEDA_H, SCHEDA_L

QUI = Path(__file__).parent
PCB = QUI / f"{NOME}.kicad_pcb"
LAVORO = QUI / "sbroglio"


def main():
    passate = sys.argv[1] if len(sys.argv) > 1 else "30"
    LAVORO.mkdir(exist_ok=True)
    dsn, ses = LAVORO / "swimtag.dsn", LAVORO / "swimtag.ses"
    genera_pcb.main(solo_piano_interno=True)
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        sys.exit("esportazione DSN non riuscita")
    ses.unlink(missing_ok=True)
    subprocess.run([os.environ.get("JAVA25", "java"), "-jar", os.environ["FREEROUTING_JAR"],
                    "-de", str(dsn), "-do", str(ses), "-mp", passate, "--gui.enabled=false"],
                   check=True, cwd=LAVORO)
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        sys.exit("importazione SES non riuscita")
    # Freerouting traccia alcune piste di massa sotto 0,1 mm: le porto al minimo JLC
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < pcbnew.FromMM(0.1):
            t.SetWidth(pcbnew.FromMM(0.1))
    reti = {n.GetNetname().lstrip("/"): n for n in board.GetNetsByName().values()}
    for layer in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        genera_pcb.zona(board, "GND", layer, 0.25, 0.25, SCHEDA_L - 0.25, SCHEDA_H - 0.25, reti)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(PCB))
    print("piste:", sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"),
          "via:", sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA"))


if __name__ == "__main__":
    main()
