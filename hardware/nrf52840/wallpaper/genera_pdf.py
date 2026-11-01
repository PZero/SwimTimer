"""PDF della scheda v0.3 di collaudo: dati di progetto + wallpaper a tutta pagina.

Uso: python genera_pdf.py   (dopo genera_wallpaper.py)
Scrive ../SwimTag_v0.3_collaudo.pdf
"""
import csv
import json
from pathlib import Path

import pymupdf

QUI = Path(__file__).resolve().parent
NRF = QUI.parent
JLC = NRF / "kicad" / "jlc" / "v0.3_swimtag_collaudo"
OUT = NRF / "SwimTag_v0.3_collaudo.pdf"
A4 = pymupdf.paper_rect("a4")
M = 54  # margine

CSS = """
@font-face { font-family: B; src: url(bahnschrift.ttf); }
* { font-family: B, sans-serif; color: #1d232b; }
body { font-size: 9.6pt; line-height: 1.42; }
h1 { font-size: 25pt; font-weight: normal; letter-spacing: 2pt; margin: 0 0 2pt 0; color: #0c1015; }
h2 { font-size: 13pt; font-weight: bold; letter-spacing: 1.2pt; margin: 14pt 0 5pt 0; color: #0c1015; }
h3 { font-size: 10pt; font-weight: bold; margin: 10pt 0 3pt 0; color: #8a6d35; letter-spacing: .6pt; }
p { margin: 0 0 6pt 0; }
.sotto { color: #6b7480; font-size: 10pt; letter-spacing: .8pt; }
.oro { color: #8a6d35; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 8pt 0; }
th { text-align: left; font-size: 8pt; letter-spacing: .8pt; color: #6b7480; border-bottom: 0.8pt solid #8a6d35; padding: 3pt 4pt; }
td { border-bottom: 0.4pt solid #d9dde2; padding: 3pt 4pt; font-size: 8.8pt; vertical-align: top; }
td.n { text-align: right; }
.k { font-size: 20pt; color: #0c1015; }
.kl { font-size: 7.5pt; color: #6b7480; letter-spacing: .8pt; }
li { margin-bottom: 2.5pt; }
"""

FONT = pymupdf.Archive("C:/Windows/Fonts")


def pagina(doc, html, numero, titolo):
    p = doc.new_page(width=A4.width, height=A4.height)
    p.insert_htmlbox(pymupdf.Rect(M, M, A4.width - M, A4.height - M - 30), html, css=CSS, archive=FONT)
    piede(p, numero, titolo)
    return p


def piede(p, numero, titolo):
    y = A4.height - M + 6
    p.draw_line((M, y - 14), (A4.width - M, y - 14), color=(0.54, 0.43, 0.21), width=0.5)
    p.insert_htmlbox(pymupdf.Rect(M, y - 10, A4.width - M, y + 10),
                     f"<p style='font-size:7.5pt;color:#6b7480;letter-spacing:1pt'>SWIMTIMER · TAG v0.3 COLLAUDO · "
                     f"{titolo.upper()}</p>", css=CSS, archive=FONT)
    p.insert_htmlbox(pymupdf.Rect(A4.width - M - 60, y - 10, A4.width - M, y + 10),
                     f"<p style='font-size:7.5pt;color:#8a6d35;text-align:right'>{numero:02d}</p>", css=CSS, archive=FONT)


def immagine(p, rect, path):
    if Path(path).exists():
        p.insert_image(rect, filename=str(path), keep_proportion=True)


def tabella(righe, intest, num=()):
    h = "<table><tr>" + "".join(f"<th>{c}</th>" for c in intest) + "</tr>"
    for r in righe:
        h += "<tr>" + "".join(f"<td class='{'n' if i in num else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return h + "</table>"


def main():
    info = json.load(open(QUI / "png" / "info.json"))
    doc = pymupdf.open()

    # 1 · copertina scura con il render
    p = doc.new_page(width=A4.width, height=A4.height)
    p.draw_rect(p.rect, color=None, fill=(0.047, 0.063, 0.082))
    immagine(p, pymupdf.Rect(30, 150, A4.width - 30, 600), QUI / "render" / "iso_sopra.png")
    p.insert_htmlbox(pymupdf.Rect(M, 640, A4.width - M, A4.height - M), f"""
      <p style='font-size:30pt;letter-spacing:9pt;color:#e9e4d8'>SWIMTIMER</p>
      <p style='font-size:12pt;letter-spacing:2pt;color:#c9aa6c'>TAG v0.3 · VARIANTE DI COLLAUDO 1c</p>
      <p style='font-size:9.5pt;color:#7a8491;letter-spacing:.6pt;margin-top:10pt'>
      nRF52840 (Ebyte E73) · IMU LSM6DSV16X · profondità MS5837 · flash 32 MB · LiPo 40 mAh<br>
      Scheda {info['w'] - 0.1:.1f} × {info['h'] - 0.1:.1f} mm · 4 strati · 0,8 mm · {info['piste']} piste · {len(info['vias'])} via · DRC 0 errori<br>
      Progetto per JLCPCB · 1 novembre 2026</p>""".replace(".0 ×", ",0 ×").replace(".0 mm", ",0 mm"),
                     css=CSS, archive=FONT)

    # 2 · sintesi
    html = f"""
    <h1>Il tag di collaudo</h1>
    <p class='sotto'>COSA È, A COSA SERVE, COME È FATTO</p>
    <p>Due tag montati interamente da JLCPCB, da indossare a lungo sotto la cuffia per le registrazioni video
    con cui mettere a punto i filtri di partenza, virata e arrivo. Forma quasi quadrata e piatta, nessun pin che
    sporge: la programmazione passa da un'impronta Tag-Connect sul lato sotto. Nessuna saldatura a mano:
    la cella si innesta in un connettore JST.</p>
    <table><tr>
      <td><p class='k'>26 × 30</p><p class='kl'>SCHEDA · mm</p></td>
      <td><p class='k'>~29 × 33</p><p class='kl'>TAG FINITO · mm</p></td>
      <td><p class='k'>~9,2</p><p class='kl'>SPESSORE · mm</p></td>
      <td><p class='k'>40</p><p class='kl'>CELLA · mAh</p></td>
      <td><p class='k'>~120–130</p><p class='kl'>2 TAG JLC · USD</p></td></tr></table>
    <h2>Blocchi</h2>
    {tabella([
        ["Radio e calcolo", "Ebyte E73-2G4M08S1C (nRF52840)", "Raytac a stock 0; VDDH dalla cella, VDD 3,3 V da UICR"],
        ["Movimento", "LSM6DSV16X in SPI, INT1 e INT2", "tocco riconosciuto dal sensore, FIFO"],
        ["Profondità", "MS5837-02BA in I2C", "porta scoperta verso l'alto"],
        ["Memoria", "W25Q256JV 32 MB in QSPI", "3–4 allenamenti da 3 h"],
        ["Carica", "BQ25101 a 13,5 mA, TS comandato da GPIO", "carica sospendibile verso l'80 %"],
        ["Misura batteria", "MAX17048 su bus I2C separato", "pull-up sul 3,3 V sempre acceso"],
        ["Sensori commutati", "TPS22916C con scarica rapida", "reset dei sensori senza dissaldare"],
        ["Batteria", "Ampul 401012 su JST SH 1,0 mm", "4 × 10 × 12 mm, protezione integrata, 1 C"],
        ["Contatti", "2 piazzole Ø 2,5 mm a 4,2 mm, TVS + Schottky", "reset all'inserimento nella custodia"],
        ["Programmazione", "Tag-Connect TC2030-NL, VREF solo riferimento", "J-Link o Pico con traslatore"],
        ["Vibratore", "pilotaggio montato, motore non montato", "nessun motore SMD montabile da JLC"],
    ], ["BLOCCO", "SCELTA", "NOTA"])}
    <h2>Lezioni apprese dal prototipo</h2>
    {tabella([
        ["Accelerometro bloccato, reset solo dissaldando", "sensori su interruttore di carico, pull-up sul lato commutato", "risolto"],
        ["Tocco riconosciuto 1 volta su 10", "INT1 e INT2 collegati, tocco in hardware", "risolto"],
        ["Campioni persi durante le scritture", "FIFO del sensore, flash a blocchi", "firmware"],
        ["Batteria letta male, anche in carica", "MAX17048, stato di carica, TS da GPIO", "risolto"],
        ["Riavvii spontanei", "2 × 47 µF, brown-out, motivo del reset via BLE", "hw + firmware"],
        ["Polarità della batteria", "connettore polarizzato, + e − in serigrafia", "risolto"],
        ["Diagnosi difficile", "7 piazzole di prova, Tag-Connect, LED", "risolto"],
    ], ["PROBLEMA", "SOLUZIONE NELLA v0.3", "STATO"])}
    """
    p = pagina(doc, html, 2, "sintesi")

    # 3 · immagini della scheda
    p = doc.new_page(width=A4.width, height=A4.height)
    p.insert_htmlbox(pymupdf.Rect(M, M, A4.width - M, M + 60),
                     "<h1>La scheda</h1><p class='sotto'>RENDER DI KICAD · LATO SOPRA E LATO SOTTO</p>", css=CSS, archive=FONT)
    w = (A4.width - 2 * M - 16) / 2
    immagine(p, pymupdf.Rect(M, M + 70, M + w, M + 70 + w * 1.15), JLC / "render_sopra.png")
    immagine(p, pymupdf.Rect(M + w + 16, M + 70, A4.width - M, M + 70 + w * 1.15), JLC / "render_sotto.png")
    basso = pymupdf.Rect(M, M + 90 + w * 1.15, A4.width - M, A4.height - M - 40)
    p.draw_rect(basso, color=None, fill=(0.047, 0.063, 0.082))
    immagine(p, basso + (20, 20, -20, -20), QUI / "render" / "iso_sotto.png")
    piede(p, 3, "render")

    # 4 · componenti
    righe = []
    for r in csv.DictReader(open(JLC / "bom_jlc.csv", encoding="utf-8")):
        righe.append([r["Designator"], r["Comment"], r["LCSC Part #"], r["Quantity"]])
    html = f"""
    <h1>Componenti</h1><p class='sotto'>DISTINTA PER IL MONTAGGIO JLC · PER TAG</p>
    {tabella(righe, ["RIF.", "VALORE", "LCSC", "Q.TÀ"], num=(3,))}
    <h3>NON MONTATI DA JLC</h3>
    {tabella([
        ["Cella", "Ampul 401012, 40 mAh, con spina JST SH 1,0 mm", "da comprare; polarità da controllare col tester"],
        ["Vibratore", "non montato sui tag di collaudo", "arriva con la versione definitiva"],
        ["Cavo SWD", "Tag-Connect TC2030-NL", "~40 $, da verificare"],
    ], ["VOCE", "COSA", "NOTA"])}
    <p style='font-size:8pt;color:#6b7480'>Componenti extended (≈ 3 $ di caricamento ciascuno): E73, LSM6DSV16X, W25Q256,
    BQ25101, MS5837, TPS22916C, MAX17048, JST SH, SD05, B5819WS. Il resto è basic.</p>"""
    pagina(doc, html, 4, "componenti")

    # 5 · pin e piazzole
    html = f"""
    <h1>Collegamenti</h1><p class='sotto'>PIN DEL MODULO E73 E PIAZZOLE DEL LATO SOTTO</p>
    {tabella([
        ["Alimentazione", "VDD 19 · VDDH (VBAT) 23 · VBUS 27 · GND 5, 21, 24"],
        ["Sistema", "RESET 26 (P0.18) · SWDIO 37 · SWDCLK 39"],
        ["QSPI flash", "CS 12 (P0.26) · SCK 17 (P1.09) · IO0 18 (P0.04) · IO1 14 (P0.06) · IO2 15 (P0.05) · IO3 16 (P0.08)"],
        ["SPI IMU", "SCK 20 (P0.12) · MOSI 22 (P0.07) · MISO 28 (P0.15) · CS 30 (P0.17) · INT1 8 (P0.29) · INT2 7 (P0.02)"],
        ["I2C sensori", "SDA 32 (P0.20) · SCL 33 (P0.13)"],
        ["I2C misuratore", "SDA 34 (P0.22) · SCL 35 (P0.24) · ALRT 4 (P0.28)"],
        ["Controlli lenti", "TS 2 (P1.10) · CHG_N 3 (P0.03) · SENS_ON 6 (P1.13) · LED 9 (P0.31) · MOT_PWM 10 (P0.30, ≤ 10 kHz)"],
    ], ["GRUPPO", "RETE → PAD (GPIO)"])}
    <h3>LATO SOTTO</h3>
    {tabella([
        ["J4 Tag-Connect", "1 VREF · 2 SWDIO · 3 RESET · 4 SWDCLK · 5 GND · 6 non collegato"],
        ["Piazzole Ø 0,8 mm", "CHG_N · SENS_ON · VDD_SENS · FG_ALRT"],
        ["Piazzole Ø 1 mm", "VBAT · VDD · GND (tester)"],
        ["Ricarica Ø 2,5 mm", "VIN · GND a 4,2 mm tra i centri"],
        ["MOT+ / MOT−", "prova del pilotaggio del vibratore, senza fili"],
    ], ["ELEMENTO", "SEGNALI"])}
    <h3>REGOLE PER IL FIRMWARE</h3>
    <ul>
    <li>Primo flash: scrivere UICR.REGOUT0 = 3,3 V (all'avvio VDD è 1,8 V) e UICR.PSELRESET per il reset.</li>
    <li>Pin TS solo a massa (open drain): alto o flottante disattiva timer e fine carica.</li>
    <li>Con i sensori spenti: SPI e I2C bassi; IMU da riconfigurare a ogni accensione; nessun risveglio dall'IMU.</li>
    <li>MAX17048 in sleep via registro CONFIG, non tenendo basse le linee.</li>
    <li>Flash QSPI su pin non consigliati da Nordic: clock 8–16 MHz.</li>
    </ul>"""
    pagina(doc, html, 5, "collegamenti")

    # 6 · produzione
    html = f"""
    <h1>Ordine JLCPCB</h1><p class='sotto'>FILE, OPZIONI, COSTI, CONTROLLI</p>
    <h3>FILE (kicad/jlc/v0.3_swimtag_collaudo/)</h3>
    <p>swimtag_gerber.zip · bom_jlc.csv · cpl_jlc.csv · schema.pdf · render</p>
    {tabella([
        ["Strati e spessore", "4 strati · 0,8 mm · 26 × 30 mm"],
        ["Finitura", "ENIG (contatti dorati)"],
        ["Quantità", "5 PCB, 2 montati"],
        ["Montaggio", "Economic, solo lato sopra, raggi X per E73 e BGA"],
        ["Regole", "piste e distanze 0,1 mm · via 0,5 / 0,3 mm · via coperti"],
    ], ["OPZIONE", "VALORE"])}
    <h3>COSTO STIMATO PER 2 TAG (USD, SENZA IVA E SPEDIZIONE)</h3>
    {tabella([["Componenti", "~48"], ["Caricamento 10 extended", "~30"], ["PCB 4 strati ENIG × 5", "~30"],
              ["Montaggio e raggi X", "~10–15"], ["<b>Totale</b>", "<b>~120–130</b>"]], ["VOCE", "USD"], num=(1,))}
    <h3>DA CONTROLLARE NELL'ANTEPRIMA JLC</h3>
    <ul>
    <li>Rotazione e pin 1 di E73, TPS22916C, MAX17048 e del connettore JST (apertura verso il bordo sinistro).</li>
    <li>MOSFET SOT-23 (spesso +180°), polarità di LED e diodi.</li>
    <li>Impronta del MAX17048 rispetto a quella LCSC; impronta del TPS22916C disegnata da zero.</li>
    <li>Stock dei componenti extended il giorno dell'ordine.</li>
    </ul>
    <h3>PUNTI APERTI</h3>
    <ul>
    <li>Zona antenna dell'E73 non quotata da Ebyte: prova di portata prima della resina.</li>
    <li>Piani interni non interi: da migliorare nella versione definitiva.</li>
    <li>Cella con spina JST SH: da chiedere al venditore.</li>
    <li>Programmatore: J-Link EDU Mini o Pico con traslatore di livello; mai alimentare da VREF.</li>
    </ul>"""
    pagina(doc, html, 6, "ordine")

    # wallpaper a tutta pagina (formato del telefono)
    for f in sorted((QUI / "png").glob("0*.png")):
        p = doc.new_page(width=390, height=844)
        p.insert_image(p.rect, filename=str(f))

    doc.set_metadata({"title": "SwimTimer · tag v0.3 di collaudo", "author": "SwimTimer", "subject": "Scheda nRF52840"})
    doc.save(OUT, garbage=4, deflate=True)
    print("scritto", OUT, doc.page_count, "pagine")


if __name__ == "__main__":
    main()
