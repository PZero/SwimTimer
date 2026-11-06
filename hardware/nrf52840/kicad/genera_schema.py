"""Genera swimtag_<variante>.kicad_sch dai dati di dati_scheda.py.

Schema "a etichette": ogni simbolo ha un'etichetta di rete su ogni pin, i pin non usati hanno
la crocetta di non collegamento. Uso (Python di KiCad o normale):  python genera_schema.py
"""
import re
import uuid
import os
from pathlib import Path

from dati_scheda import COMPONENTI, DNP, NC_U1, NOME, VARIANTE, VERSIONE

QUI = Path(__file__).parent
KICAD = Path(os.environ.get("KICAD_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
SIMBOLI_KICAD = KICAD / "share" / "kicad" / "symbols"
LIB_LOCALE = QUI / "lib" / "swimtag.kicad_sym"
PROGETTO = NOME
REV = VERSIONE.lstrip("v")
NS = uuid.UUID("6f1d3c52-6a47-4c55-9a8e-0d7c1b3a5e01")


def uid(*parti):
    """UUID stabile: rigenerare lo schema non cambia gli identificativi (utile per git e per il PCB)."""
    return str(uuid.uuid5(NS, "/".join(map(str, parti))))


RADICE = uid("radice")


def blocco(testo, inizio):
    """Restituisce la sottostringa a parentesi bilanciate che parte da 'inizio'."""
    livello = 0
    for i in range(inizio, len(testo)):
        if testo[i] == "(":
            livello += 1
        elif testo[i] == ")":
            livello -= 1
            if livello == 0:
                return testo[inizio:i + 1]
    raise ValueError("parentesi non bilanciate")


def simbolo(file_lib, nome):
    testo = file_lib.read_text(encoding="utf-8")
    m = re.search(r'\(symbol "%s"\s' % re.escape(nome), testo)
    if not m:
        raise KeyError(nome)
    return testo, blocco(testo, m.start())


def simbolo_piatto(libreria, nome):
    """Simbolo pronto per lib_symbols, con 'extends' risolto copiando le unità del padre."""
    file_lib = LIB_LOCALE if libreria == "swimtag" else SIMBOLI_KICAD / f"{libreria}.kicad_sym"
    testo, s = simbolo(file_lib, nome)
    m = re.search(r'\(extends "([^"]+)"\)', s)
    if m:
        padre = m.group(1)
        _, sp = simbolo(file_lib, padre)
        unita = [blocco(sp, u.start()) for u in re.finditer(r'\(symbol "%s_\d+_\d+"' % re.escape(padre), sp)]
        unita = [u.replace(f'"{padre}_', f'"{nome}_') for u in unita]
        # opzioni del padre (pin_names, pin_numbers...) che il figlio non ha
        extra = []
        for chiave in ("pin_numbers", "pin_names", "exclude_from_sim", "in_bom", "on_board"):
            mm = re.search(r"\(%s[\s)]" % chiave, sp)
            if mm and not re.search(r"\(%s[\s)]" % chiave, s):
                extra.append(blocco(sp, mm.start()))
        s = s.replace(m.group(0), "\n".join(extra))
        s = s[:s.rstrip().rfind(")")] + "\n" + "\n".join(unita) + "\n)"
    return s.replace(f'(symbol "{nome}"', f'(symbol "{libreria}:{nome}"', 1)


def pin_del_simbolo(s):
    """{numero: (x, y, angolo)} in coordinate del simbolo (y verso l'alto)."""
    pins = {}
    for m in re.finditer(r"\(pin\s+\w+\s+\w+\s*\(at ([-\d.]+) ([-\d.]+) ?([-\d.]*)\)", s):
        resto = blocco(s, m.start())
        num = re.search(r'\(number "([^"]*)"', resto).group(1)
        pins[num] = (float(m.group(1)), float(m.group(2)), int(float(m.group(3) or 0)))
    return pins


def nomi_pin(lib_id):
    """{numero: nome} dei pin di un simbolo (serve a dare ai pad non collegati il nome di rete che KiCad assegna: unconnected-(U1-nome-PadN))."""
    libreria, nome = lib_id.split(":")
    s = simbolo_piatto(libreria, nome)
    res = {}
    for m in re.finditer(r"\(pin\s+\w+\s+\w+\s*\(at ", s):
        resto = blocco(s, m.start())
        num = re.search(r'\(number "([^"]*)"', resto).group(1)
        res[num] = re.search(r'\(name "([^"]*)"', resto).group(1)
    return res


def griglia(v):
    return round(round(v / 1.27) * 1.27, 4)


def main():
    lib_symbols, simboli, etichette, croci = {}, [], [], []
    # posizioni sullo schema: modulo a sinistra, il resto in colonne
    pos = {"U1": (50.8, 101.6), "U2": (162.56, 50.8), "U3": (162.56, 101.6), "U4": (162.56, 152.4),
           "U5": (243.84, 50.8), "Q1": (243.84, 101.6)}
    col, riga = 0, 0
    for rif, lib_id, valore, impronta, lcsc, pins, _ in COMPONENTI:
        libreria, nome = lib_id.split(":")
        if lib_id not in lib_symbols:
            lib_symbols[lib_id] = simbolo_piatto(libreria, nome)
            if nome.startswith("W25Q"):   # flash: i pin sono collegati solo da etichette (niente driver nello schema, ERC)
                lib_symbols[lib_id] = re.sub(r"\(pin (power_in|input|output|bidirectional) ", "(pin passive ", lib_symbols[lib_id])
            if nome.startswith(("MCP73831", "TPS22917")):   # v0.6: i pin di alimentazione/uscita dei due circuiti integrati sono collegati solo da etichette (ERC)
                lib_symbols[lib_id] = re.sub(r"\(pin (power_in|power_out|input|output|open_collector|tri_state) ", "(pin passive ", lib_symbols[lib_id])
            if "TagConnect" in nome:   # i pin VCC/GND del connettore di programmazione non sono alimentazioni da pilotare (ERC)
                lib_symbols[lib_id] = lib_symbols[lib_id].replace("power_in", "passive")
        if rif not in pos:
            pos[rif] = (215.9 + 25.4 * (col % 6), 139.7 + 20.32 * (riga // 6))
            col += 1
            riga += 1
        x, y = map(griglia, pos[rif])
        sp = pin_del_simbolo(lib_symbols[lib_id])
        prop = lambda n, v, dy, nascosta=False: (  # noqa: E731
            f'(property "{n}" "{v}" (at {x} {y + dy} 0) (effects (font (size 1.27 1.27))'
            f'{" (hide yes)" if nascosta else ""}))')
        pin_uuid = " ".join(f'(pin "{n}" (uuid "{uid(rif, "pin", n)}"))' for n in sp)
        simboli.append(
            f'(symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom {"yes" if lcsc and rif not in DNP else "no"}) '
            f'(on_board yes) (dnp {"yes" if rif in DNP else "no"}) (uuid "{uid(rif)}")\n'
            f'  {prop("Reference", rif, -3.81)}\n  {prop("Value", valore, 3.81)}\n'
            f'  {prop("Footprint", impronta, 0, True)}\n  {prop("Datasheet", "", 0, True)}\n'
            f'  {prop("LCSC", lcsc, 0, True)}\n  {pin_uuid}\n'
            f'  (instances (project "{PROGETTO}" (path "/{RADICE}" (reference "{rif}") (unit 1)))))')
        nc = NC_U1 if rif == "U1" else []
        for num, (px, py, ang) in sp.items():
            ax, ay = round(x + px, 4), round(y - py, 4)
            chiave = int(num) if num.isdigit() else num
            if chiave in pins:
                verso = {0: 180, 90: 270, 180: 0, 270: 90}[ang % 360]
                giust = "right" if verso in (180, 270) else "left"
                etichette.append(
                    f'(label "{pins[chiave]}" (at {ax} {ay} {verso}) (effects (font (size 1.0 1.0)) '
                    f'(justify {giust} bottom)) (uuid "{uid(rif, "lab", num)}"))')
            elif chiave in nc or rif != "U1":
                croci.append(f'(no_connect (at {ax} {ay}) (uuid "{uid(rif, "nc", num)}"))')
    testo = (
        f'(kicad_sch (version 20250114) (generator "genera_schema.py") (generator_version "9.0")\n'
        f'(uuid "{RADICE}") (paper "A3")\n'
        f'(title_block (title "SwimTimer - tag nRF52840") (rev "{REV}") (comment 1 "Variante {VARIANTE}. Generato da dati_scheda.py: modificare i dati, non lo schema"))\n'
        f'(lib_symbols\n' + "\n".join(lib_symbols.values()) + "\n)\n"
        + "\n".join(simboli + etichette + croci)
        + '\n(sheet_instances (path "/" (page "1")))\n)\n')
    (QUI / f"{PROGETTO}.kicad_sch").write_text(testo, encoding="utf-8")
    print(f"scritto {PROGETTO}.kicad_sch: {len(simboli)} simboli, {len(etichette)} etichette, {len(croci)} pin liberi")


if __name__ == "__main__":
    main()
