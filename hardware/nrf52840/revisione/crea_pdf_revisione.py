"""Unisce in un solo PDF: descrizione (md), schema, render, BOM e CPL."""
import csv
import sys
from pathlib import Path

import markdown
import pymupdf

D = Path(sys.argv[1])
OUT = D / "SwimTag_v0.5_revisione.pdf"
A4 = pymupdf.paper_rect("a4")
CSS = """
body { font-family: sans-serif; font-size: 9pt; line-height: 1.35; }
h1 { font-size: 16pt; } h2 { font-size: 12.5pt; margin-top: 10pt; } h3 { font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; }
th, td { border: 0.5pt solid #888; padding: 2pt 3pt; font-size: 7.5pt; vertical-align: top; }
th { background: #e6eef7; }
code, pre { font-family: monospace; font-size: 7.5pt; }
pre { background: #f3f3f3; padding: 4pt; }
blockquote { color: #444; border-left: 2pt solid #999; padding-left: 6pt; }
"""


def html_a_pdf(html):
    buf = pymupdf.open()
    story = pymupdf.Story(html=html, user_css=CSS)
    pos = pymupdf.DocumentWriter(OUT.with_suffix(".tmp.pdf"))
    area = A4 + (40, 40, -40, -40)
    more = True
    while more:
        dev = pos.begin_page(A4)
        more, _ = story.place(area)
        story.draw(dev)
        pos.end_page()
    pos.close()
    buf.close()
    return pymupdf.open(OUT.with_suffix(".tmp.pdf"))


def tabella_csv(nome, titolo):
    righe = list(csv.reader((D / nome).open(encoding="utf-8")))
    h = "".join(f"<th>{c}</th>" for c in righe[0])
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in righe[1:])
    return f"<h2>{titolo}</h2><table><tr>{h}</tr>{b}</table>"


testo = (D / "revisione_esterna_v0.5.md").read_text(encoding="utf-8")
html = markdown.markdown(testo, extensions=["tables", "fenced_code"])
html += "<h2>Appendice A - schema elettrico, render e file JLC</h2><p>Seguono: schema elettrico (pagine dello schema.pdf), render del PCB (sopra, sotto, 3D), distinta BOM e posizioni CPL per JLCPCB.</p>"
html += tabella_csv("bom_jlc.csv", "Appendice B - BOM JLC (bom_jlc.csv)")
html += tabella_csv("cpl_jlc.csv", "Appendice C - CPL JLC (cpl_jlc.csv, mm, gradi)")
doc = html_a_pdf(html)

sch = pymupdf.open(D / "schema.pdf")
doc.insert_pdf(sch)
for nome, titolo in (("render_sopra.png", "Render PCB - lato sopra"), ("render_sotto.png", "Render PCB - lato sotto (piazzole SWD e ricarica)"), ("render_3d.png", "Render PCB - vista 3D")):
    p = doc.new_page(width=A4.width, height=A4.height)
    p.insert_text((40, 50), titolo, fontsize=13)
    p.insert_image(pymupdf.Rect(40, 70, A4.width - 40, A4.height - 40), filename=str(D / nome), keep_proportion=True)
doc.save(OUT, garbage=3, deflate=True)
doc.close()
OUT.with_suffix(".tmp.pdf").unlink()
print(OUT, pymupdf.open(OUT).page_count, "pagine")
