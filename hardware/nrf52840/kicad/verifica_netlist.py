"""Confronta la netlist esportata da KiCad con dati_scheda.py.  Uso: python verifica_netlist.py file.net"""
import re
import sys

from dati_scheda import reti

t = open(sys.argv[1], encoding="utf-8").read()
t = t[t.index("(nets"):]
got = {}
for blocco in re.split(r"\(net\s*\n", t)[1:]:
    nome = re.search(r'\(name "([^"]*)"\)', blocco).group(1).lstrip("/")
    nodi = set(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blocco))
    if not nome.startswith("unconnected"):
        got[nome] = nodi
attese = {k: set(v) for k, v in reti().items()}
diff = [k for k in attese if got.get(k) != attese[k]] + [k for k in got if k not in attese]
for k in diff:
    print("DIFF", k, attese.get(k, set()) ^ got.get(k, set()))
print(f"reti attese {len(attese)}, nello schema {len(got)}, differenze {len(diff)}")
sys.exit(1 if diff else 0)
