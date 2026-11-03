"""Dati del tag SwimTimer nRF52840 v0.4 "economica": solo registrazione dei dati grezzi dell'IMU.

Caricato da dati_scheda.py quando SWIMTAG_VARIANTE=economica (la v0.3 collaudo resta rigenerabile con la variante "collaudo").
Contenuto: modulo E73, IMU LSM6DSV16X, flash SPI 16 MB, caricatore BQ25101, 1 LED, header batteria.
Tolti rispetto alla v0.3: MS5837, MAX17048, TPS22916C, vibratore (Q1, D1, R3), Tag-Connect, piazzole di prova, protezione/reset
dei contatti (TVS, MOSFET), 2 x 47 uF, 0 ohm BAT/VBAT.
Scheda a 2 strati, 0,8 mm, HASL senza piombo, componenti solo sopra (JLC Economic).
Coordinate in mm, origine in alto a sinistra della scheda, y verso il basso; vedi cerca_posizioni.py per la ricerca delle posizioni.
"""

VERSIONE = "v0.4"
TITOLO_SERIGRAFIA = "v0.4 economica"
N_STRATI = 2
SPESSORE = 0.8
# regole JLC 2 strati: piste/distanze 5 mil (0,127), via 0,6 / 0,3, anello 0,15, foro-rame 0,2 (capacita' standard, senza sovrapprezzo)
PISTA, DISTANZA, VIA_D, VIA_FORO = 0.127, 0.127, 0.6, 0.3
ANTENNA_H = 3.7          # come v0.3: striscia senza rame dal bordo alto, tutti gli strati
GRIGLIA = 2.54           # le piazzole del lato sotto sono su questa griglia, misurata dal bordo sinistro e dal bordo alto (antenna)

MOD_X = 7.8              # centro del modulo E73 (pad esterni a 7,5 mm dal centro): i pad sinistri stanno a 0,3 mm dal bordo
try:
    from posizioni_economica import POS, SCHEDA_L, SCHEDA_H_TOT
except ImportError:      # prima della ricerca delle posizioni (cerca_posizioni.py)
    POS, SCHEDA_L, SCHEDA_H_TOT = {}, 20.32, 26.0

def _p(rif):
    return POS.get(rif, (0.0, 0.0, 0, "F"))

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
SOIC8 = "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm"
HDR127 = "swimtag:HDR-SMD_2P-P1.27-V-M-LS4.2-R1"
PAD20 = "swimtag:TestPoint_Pad_D2.0mm_NoCY"   # piazzole pogo SWD: Ø 2,0 mm (senza courtyard: sul passo 2,54 si sovrapporrebbero)
PAD25 = "TestPoint:TestPoint_Pad_D2.5mm"   # contatti di ricarica: Ø 2,5 mm

# Pin del modulo E73 (numero del pad): vedi il commento in dati_scheda.py per la tabella delle funzioni.
# SPI veloci solo su pad non "bassa frequenza" (Nordic PS): IMU su 11/13/15/17 (P0.00, P0.01, P0.05, P1.09: fila bassa, pad esterni),
# flash su 33/35 (P0.13, P0.24, pad esterni destri) e 28/30 (P0.15, P0.17, pad interni destri). Segnali lenti sulla colonna sinistra.
PINS_U1 = {
    5: "GND", 21: "GND", 24: "GND", 19: "VDD", 23: "VBAT", 26: "RESET", 37: "SWDIO", 39: "SWDCLK",
    32: "CHG_N", 34: "LED", 12: "IMU_INT1", 14: "IMU_INT2",   # pad interni (P0.20, P0.22 a destra; P0.26, P0.06 in basso): la colonna sinistra non ha spazio per le piste
    11: "IMU_CS", 13: "IMU_MISO", 15: "IMU_MOSI", 17: "IMU_SCK",
    33: "FL_MOSI", 35: "FL_SCK", 28: "FL_MISO", 30: "FL_CS",
    18: "SENS_ON",   # ON del TPS22916C (pad interno in basso, P0.04): segnale statico
}
NC_U1 = [n for n in range(1, 44) if n not in PINS_U1]

COMPONENTI = [
    ("U1", "swimtag:E73-2G4M08S1C", "E73-2G4M08S1C", "swimtag:WIRELM-SMD_E73-2G4M08S1C", "C356849", PINS_U1, _p("U1")),
    ("U2", "swimtag:LSM6DSV16XTR", "LSM6DSV16X", "swimtag:LGA-14_L3.0-W2.5-P0.50-BR", "C5267406",
     {1: "IMU_MISO", 2: "GND", 3: "GND", 4: "IMU_INT1", 5: "VDD_IMU", 6: "GND", 7: "GND", 8: "VDD_IMU",
      9: "IMU_INT2", 12: "IMU_CS", 13: "IMU_SCK", 14: "IMU_MOSI"}, _p("U2")),
    # flash 16 MB in SOIC-8 208 mil (Basic JLC, nessun costo di caricamento): SPI semplice, IO2/IO3 (WP#/HOLD#) alti tramite R4
    ("U3", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", SOIC8, "C97521",
     {1: "FL_CS", 2: "FL_MISO", 3: "FL_IO23", 4: "GND", 5: "FL_MOSI", 6: "FL_SCK", 7: "FL_IO23", 8: "VDD"}, _p("U3")),
    # interruttore di carico dell'IMU (come v0.3, 2026-11-03): un IMU in latch-up dentro la resina si sblocca solo togliendo l'alimentazione
    ("U6", "swimtag:TPS22916CYFPR", "TPS22916C", "swimtag:DSBGA-4_L0.78-W0.78-P0.40", "C2680319",
     {"A2": "VDD", "A1": "VDD_IMU", "B2": "SENS_ON", "B1": "GND"}, _p("U6")),
    ("U4", "swimtag:BQ25101YFPR", "BQ25101", "swimtag:DSBGA-6_L0.9-W1.6-R2-C3-P0.40-BL", "C478468",
     {"A2": "VIN_D", "A1": "VBAT", "B1": "TS", "B2": "ISET", "C1": "CHG_N", "C2": "GND"}, _p("U4")),
    ("D1", "Device:LED", "rosso 0603", LED0603, "C2286", {1: "LED_K", 2: "VDD"}, _p("D1")),   # KT-0603R (Basic JLC): anodo su VDD (1,8 V al primo avvio: niente corrente nei diodi di protezione del pin), 1 k -> ~1,4 mA a VDD 3,3 V
    ("D2", "swimtag:B5819WS_C22624", "1N5819WS", "swimtag:SOD-323_L1.8-W1.3-LS2.5-RD", "C191023",
     {1: "VIN_D", 2: "VIN"}, _p("D2")),     # in serie al contatto VIN: polarita' inversa e nessun ritorno della batteria verso l'esterno
    ("R1", "Device:R", "10k", R0402, "C25744", {1: "ISET", 2: "GND"}, _p("R1")),     # 13,5 mA di carica
    ("R2", "Device:R", "10k", R0402, "C25744", {1: "TS", 2: "GND"}, _p("R2")),       # TS senza NTC: 10k verso massa
    ("R3", "Device:R", "1k", R0402, "C11702", {1: "LED_K", 2: "LED"}, _p("R3")),
    ("R4", "Device:R", "10k", R0402, "C25744", {1: "FL_IO23", 2: "VDD"}, _p("R4")),
    ("R5", "Device:R", "100k", R0402, "C25741", {1: "FL_CS", 2: "VDD"}, _p("R5")),   # CS flash alto mentre i GPIO sono flottanti
    ("R6", "Device:R", "100k", R0402, "C25741", {1: "IMU_CS", 2: "VDD_IMU"}, _p("R6")),  # CS IMU alto all'accensione; su VDD_IMU (non su VDD) per non alimentare l'IMU spento dal pin
    ("R7", "Device:R", "1M", R0402, "C26083", {1: "SENS_ON", 2: "GND"}, _p("R7")),    # pull-down su ON: IMU spento all'avvio e a GPIO flottante
    ("C1", "Device:C", "10u", C0402, "C15525", {1: "VDD", 2: "GND"}, _p("C1")),      # VDD del modulo (pad 19)
    ("C2", "Device:C", "100n", C0402, "C1525", {1: "VDD_IMU", 2: "GND"}, _p("C2")),      # IMU Vdd_IO (pin 5)
    ("C3", "Device:C", "100n", C0402, "C1525", {1: "VDD", 2: "GND"}, _p("C3")),      # flash VCC
    ("C4", "Device:C", "100n", C0402, "C1525", {1: "VDD_IMU", 2: "GND"}, _p("C4")),      # IMU Vdd (pin 8)
    ("C5", "Device:C", "4u7", C0402, "C23733", {1: "VIN_D", 2: "GND"}, _p("C5")),    # ingresso caricatore: 4,7 uF 10 V X5R (Basic) su 5 V; TI chiede >= 1 uF
    ("C6", "Device:C", "4u7", C0402, "C23733", {1: "VBAT", 2: "GND"}, _p("C6")),     # uscita caricatore (1-10 uF TI) e VDDH: da solo, con i 4,7 uF gia' nel modulo
    # connettore batteria: due pin header SMD 1,27 mm (fili della cella saldati ai pin); 1 = + (VBAT), 2 = - (GND)
    ("J1", "Connector_Generic:Conn_01x02", "BATT header 1.27", HDR127, "C55213900", {1: "VBAT", 2: "GND"}, _p("J1")),
    # lato sotto (solo rame, non montate): 5 piazzole pogo SWD Ø 2,0 sulla griglia 2,54 mm; 2 contatti di ricarica Ø 2,5
    ("TP1", "Connector:TestPoint", "VDD", PAD20, "", {1: "VDD"}, _p("TP1")),
    ("TP2", "Connector:TestPoint", "SWDIO", PAD20, "", {1: "SWDIO"}, _p("TP2")),
    ("TP3", "Connector:TestPoint", "SWDCLK", PAD20, "", {1: "SWDCLK"}, _p("TP3")),
    ("TP4", "Connector:TestPoint", "RESET", PAD20, "", {1: "RESET"}, _p("TP4")),
    ("TP5", "Connector:TestPoint", "GND", PAD20, "", {1: "GND"}, _p("TP5")),
    ("TP6", "Connector:TestPoint", "VIN", PAD25, "", {1: "VIN"}, _p("TP6")),
    ("TP7", "Connector:TestPoint", "GND", PAD25, "", {1: "GND"}, _p("TP7")),
]

SOPRA_FISSI = ("J1", "U3")   # componenti superiori con posizione fissata a mano (oltre al modulo): header batteria in basso a sinistra, flash in basso a destra
ROT_OK = {}


def fissi(W, H):
    """Posizioni (x, y, rot) delle piazzole del lato sotto, sulla griglia 2,54 mm dal bordo sinistro e dal bordo alto.
    SWD: riga di 5 a y = 12,70 (5 passi); ricarica: VIN e GND a 5,08 mm l'uno dall'altro (2 passi), 5,08 mm sotto la riga SWD.
    Le colonne partono da x = 5,08 mm (2 passi dal bordo) e si centrano sulla scheda al passo intero piu' vicino."""
    g = GRIGLIA
    col0 = round((W / 2 - 2 * g) / g) * g        # prima colonna SWD: multiplo di 2,54 mm
    ys, yc = 5 * g, 7 * g
    d = {}
    for i, rif in enumerate(("TP1", "TP2", "TP3", "TP4", "TP5")):
        d[rif] = (round(col0 + i * g, 3), round(ys, 3), 0)
    d["TP6"] = (round(col0 + 1 * g, 3), round(yc, 3), 0)      # VIN, sotto la colonna di SWDIO
    d["TP7"] = (round(col0 + 3 * g, 3), round(yc, 3), 0)      # GND, sotto la colonna di RESET
    d["U3"] = (round(W - 0.35 - 4.7, 2), round(H - 0.35 - 2.94, 2), 0)   # flash SOIC-8 (9,4 x 5,9 mm) nell'angolo in basso a destra
    d["J1"] = (round(0.35 + 2.7, 2), round(H - 0.35 - 1.4, 2), 90)   # header in orizzontale nell'angolo in basso a sinistra
    return d


# Attrazione componente -> pin (usata da cerca_posizioni.py): {rif: ((componente, pin), peso)}; il pin del condensatore "1" e' quello verso l'alimentazione
ATTRAZIONI = {
    "C1": (("U1", "19"), 4.0),
    "C2": (("U2", "5"), 4.0), "C4": (("U2", "8"), 4.0), "C3": (("U3", "8"), 4.0),
    "C5": (("U4", "A2"), 4.0), "C6": (("U4", "A1"), 4.0), "R1": (("U4", "B2"), 3.0), "R2": (("U4", "B1"), 3.0),
    "R4": (("U3", "3"), 2.0), "R5": (("U3", "1"), 1.5), "R6": (("U2", "12"), 1.5), "R3": (("D1", "1"), 3.0), "U6": (("U2", "5"), 3.0), "R7": (("U6", "B2"), 2.0), "U2": (("U1", "15"), 3.0),
}
