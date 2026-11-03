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
from dati_scheda import DISTANZA, N_STRATI, NOME, PISTA, SCHEDA_H_TOT as SCHEDA_H, SCHEDA_L

QUI = Path(__file__).parent
PCB = QUI / f"{NOME}.kicad_pcb"
LAVORO = QUI / "sbroglio"


def main():
    passate = sys.argv[1] if len(sys.argv) > 1 else "30"
    LAVORO.mkdir(exist_ok=True)
    dsn, ses = LAVORO / f"{NOME}.dsn", LAVORO / f"{NOME}.ses"
    genera_pcb.main(solo_piano_interno=True)
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        sys.exit("esportazione DSN non riuscita")
    # margine sul minimo JLC (5 um a 4 strati, 20 um a 2 strati) (0,1 mm): Freerouting arrotonda le posizioni e a volte resta 1 um sotto
    dist = round(DISTANZA * 1000)
    dsn.write_text(dsn.read_text(encoding="utf-8").replace(f"(clearance {dist})", f"(clearance {dist + (35 if N_STRATI == 2 else 20)})"), encoding="utf-8")
    ses.unlink(missing_ok=True)
    subprocess.run([os.environ.get("JAVA25", "java"), "-jar", os.environ["FREEROUTING_JAR"],
                    "-de", str(dsn), "-do", str(ses), "-mp", passate, "--gui.enabled=false"],
                   check=True, cwd=LAVORO)
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        sys.exit("importazione SES non riuscita")
    # Freerouting traccia alcune piste di massa sotto 0,1 mm: le porto al minimo JLC
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < pcbnew.FromMM(min(PISTA, 0.1) if N_STRATI == 4 else PISTA):
            t.SetWidth(pcbnew.FromMM(min(PISTA, 0.1) if N_STRATI == 4 else PISTA))
    reti = {n.GetNetname().lstrip("/"): n for n in board.GetNetsByName().values()}
    for layer in ((pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu) if N_STRATI == 4 else (pcbnew.F_Cu,)):   # 2 strati: B.Cu ha gia' la massa piena
        genera_pcb.zona(board, "GND", layer, 0.25, 0.25, SCHEDA_L - 0.25, SCHEDA_H - 0.25, reti)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(PCB))
    print("piste:", sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"),
          "via:", sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA"))


if __name__ == "__main__":
    main()
