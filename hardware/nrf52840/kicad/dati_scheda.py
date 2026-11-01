"""Dati del tag SwimTimer nRF52840 v0.3: componenti, collegamenti e posizioni.

Unica fonte per lo schema (genera_schema.py) e il PCB (genera_pcb.py), così restano coerenti.
Coordinate PCB in mm, origine in alto a sinistra della scheda, y verso il basso.
Modulo Ebyte E73-2G4M08S1C (v0.3: il Raytac MDBT50Q-1MV2 e' a stock 0, sostituito il 2026-11-01), antenna sul bordo alto
(3,7 mm senza rame). Componenti solo sul lato sopra (montaggio JLC su un lato); sotto contatti di ricarica, piazzole SWD e vibratore.
"""

import os

# Varianti generate dagli stessi dati (variabile d'ambiente SWIMTAG_VARIANTE):
#   "collaudo"   : primi 2 tag, variante 1c (quasi quadrata, indossabile): Tag-Connect + piazzole di prova sotto, 0 ohm sulla corrente
#   "definitiva" : piu' piccola possibile, senza piazzole di prova (DA FARE)
VARIANTE = os.environ.get("SWIMTAG_VARIANTE", "collaudo")
if VARIANTE not in ("collaudo", "definitiva"):
    raise SystemExit(f"VARIANTE sconosciuta: {VARIANTE}")
if VARIANTE == "definitiva":
    raise NotImplementedError("variante definitiva: non ancora implementata (v0.3 solo collaudo)")

NOME = f"swimtag_{VARIANTE}"   # nome dei file KiCad generati

from posizioni_collaudo import POS, SCHEDA_L, SCHEDA_H_TOT   # misure e posizioni (x, y, rotazione, lato) della variante 1c, vedi cerca_posizioni.py
ANTENNA_H = 3.7   # striscia senza rame sotto l'antenna: dal bordo al pad 1/43 del modulo (a 3,97 mm dal bordo, foglio Ebyte); Ebyte non da' una quota di rispetto

# Impronte standard di KiCad
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"

C0805 = "Capacitor_SMD:C_0805_2012Metric"
JST_SH = "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal"

# Pin del modulo non usati (restano senza collegamento): P1.11 (1), XL1/XL2 (11, 13: tenuti per un eventuale quarzo a
# 32 kHz), DCCH (25), USB D-/D+ (29, 31), P1.00 (36), P1.02 (38), P1.04 (40), NFC (41, 43), P1.06 (42)
NC_U1 = [1, 11, 13, 25, 29, 31, 36, 38, 40, 41, 42, 43]

TP1MM = "TestPoint:TestPoint_Pad_1.0x1.0mm"
TPSWD = "TestPoint:TestPoint_Pad_D1.0mm"  # piazzole per il tester
TP08 = "swimtag:TestPoint_Pad_D0.8mm"
TC2030 = "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical"

# rif, simbolo, valore, impronta, LCSC, collegamenti {pin: rete}, (x, y, rotazione, lato)
COMPONENTI = [
    # Modulo Ebyte E73-2G4M08S1C (nRF52840, 13 x 18 mm, antenna ceramica), ruotato di 180 gradi: antenna sul bordo alto.
    # Piedini dal foglio Ebyte (cap. 3): VDD 19, VDDH 23, VBUS 27, RESET P0.18 26, SWDIO 37, SWDCLK 39, GND 5/21/24.
    # Segnali veloci (SPI, I2C, QSPI) solo su pin senza "bassa frequenza" (Nordic PS, tabella aQFN73: tutti i P1.01-P1.07,
    # P1.10-P1.15, P0.02, P0.03, P0.09, P0.10, P0.28-P0.31). I segnali lenti stanno sulla colonna sinistra (pin 2-10).
    ("U1", "swimtag:E73-2G4M08S1C", "E73-2G4M08S1C", "swimtag:WIRELM-SMD_E73-2G4M08S1C", "C356849",
     {**{p: "GND" for p in (5, 21, 24)},
      19: "VDD", 23: "VBAT", 27: "VIN_D", 26: "RESET", 37: "SWDIO", 39: "SWDCLK",
      # lenti (colonna sinistra, P0.02/03/28-31 e P1.10/P1.13 sono "bassa frequenza": PWM del vibratore <= 10 kHz)
      2: "TS", 3: "CHG_N", 4: "FG_ALRT", 6: "SENS_ON", 7: "IMU_INT2", 8: "IMU_INT1", 9: "LED", 10: "MOT_PWM",
      # QSPI sui 6 pin della fila bassa piu' vicini alla flash (qualsiasi GPIO: registri PSEL)
      12: "QSPI_CS", 14: "QSPI_IO1", 15: "QSPI_IO2", 16: "QSPI_IO3", 17: "QSPI_SCK", 18: "QSPI_IO0",
      # IMU in SPI
      20: "IMU_SCK", 22: "IMU_MOSI", 28: "IMU_MISO", 30: "IMU_CS",
      # I2C sensori (pressione) e I2C misuratore di carica
      32: "I2C_SDA", 33: "I2C_SCL", 34: "FG_SDA", 35: "FG_SCL"},
     POS["U1"]),
    ("U2", "swimtag:LSM6DSV16XTR", "LSM6DSV16X", "swimtag:LGA-14_L3.0-W2.5-P0.50-BR", "C5267406",
     {1: "IMU_MISO", 2: "GND", 3: "GND", 4: "IMU_INT1", 5: "VDD_SENS", 6: "GND", 7: "GND", 8: "VDD_SENS",
      9: "IMU_INT2", 12: "IMU_CS", 13: "IMU_SCK", 14: "IMU_MOSI"},
     POS["U2"]),
    ("U3", "swimtag:W25Q256JVEIQTR", "W25Q256JVEIQ", "swimtag:WSON-8_L8.0-W6.10-P1.27-BL-EP", "C97522",
     {1: "QSPI_CS", 2: "QSPI_IO1", 3: "QSPI_IO2", 4: "GND", 5: "QSPI_IO0", 6: "QSPI_SCK",
      7: "QSPI_IO3", 8: "VDD", 9: "GND"},
     POS["U3"]),
    ("U4", "swimtag:BQ25101YFPR", "BQ25101", "swimtag:DSBGA-6_L0.9-W1.6-R2-C3-P0.40-BL", "C478468",
     {"A2": "VIN_D", "A1": "BAT", "B1": "TS", "B2": "ISET", "C1": "CHG_N", "C2": "GND"},
     POS["U4"]),
    ("U5", "swimtag:MS5837-02BA", "MS5837-02BA", "swimtag:LGA-4_L3.3-W3.3-P2.00-TL", "C5785272",
     {1: "GND", 2: "VDD_SENS", 3: "I2C_SCL", 4: "I2C_SDA"},
     POS["U5"]),
    ("Q1", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917",
     {1: "MOT_PWM", 2: "GND", 3: "MOT_N"}, POS["Q1"]),
    ("D1", "Device:D", "1N4148WS", "Diode_SMD:D_SOD-323", "C2128",
     {1: "VBAT", 2: "MOT_N"}, POS["D1"]),
    ("D2", "Device:LED", "rosso", LED0603, "C2286", {1: "LED_K", 2: "VBAT"}, POS["D2"]),
    ("R1", "Device:R", "10k", R0402, "C25744", {1: "ISET", 2: "GND"}, POS["R1"]),
    ("R2", "Device:R", "10k", R0402, "C25744", {1: "TS", 2: "GND"}, POS["R2"]),
    ("R3", "Device:R", "100k", R0402, "C25741", {1: "MOT_PWM", 2: "GND"}, POS["R3"]),
    ("R4", "Device:R", "1k", R0402, "C11702", {1: "LED_K", 2: "LED"}, POS["R4"]),
    ("R5", "Device:R", "10k", R0402, "C25744", {1: "I2C_SDA", 2: "VDD_SENS"}, POS["R5"]),  # pull-up I2C (TE)
    ("R6", "Device:R", "10k", R0402, "C25744", {1: "I2C_SCL", 2: "VDD_SENS"}, POS["R6"]),
    ("C1", "Device:C", "10u", C0402, "C15525", {1: "VDD", 2: "GND"}, POS["C1"]),  # VDD del modulo (pin 28)
    ("C2", "Device:C", "100n", C0402, "C1525", {1: "VDD_SENS", 2: "GND"}, POS["C2"]),  # IMU Vdd_IO (pin 5)
    ("C3", "Device:C", "100n", C0402, "C1525", {1: "VDD", 2: "GND"}, POS["C3"]),  # flash VCC
    ("C4", "Device:C", "100n", C0402, "C1525", {1: "VDD_SENS", 2: "GND"}, POS["C4"]),
    ("C5", "Device:C", "10u", C0402, "C15525", {1: "VIN_D", 2: "GND"}, POS["C5"]),  # ingresso caricatore e VBUS
    ("C6", "Device:C", "100n", C0402, "C1525", {1: "VDD_SENS", 2: "GND"}, POS["C6"]),  # IMU Vdd (pin 8)
    ("C7", "Device:C", "10u", C0402, "C15525", {1: "VBAT", 2: "GND"}, POS["C7"]),  # VDDH (pin 30), 10 uF come da Raytac
    # Protezione dei contatti di ricarica e reset all'inserimento nella custodia
    ("D3", "swimtag:SD05.TCT", "SD05 TVS 5V", "swimtag:SOD-323_L1.8-W1.3-LS2.5-RD", "C85201",
     {1: "VIN", 2: "GND"}, POS["D3"]),
    ("D4", "swimtag:B5819WS_C22624", "B5819WS", "swimtag:SOD-323_L1.8-W1.3-LS2.5-RD", "C22624",
     {1: "VIN_D", 2: "VIN"}, POS["D4"]),
    ("Q2", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917",
     {1: "RST_G", 2: "GND", 3: "RESET"}, POS["Q2"]),
    ("C8", "Device:C", "100n", C0402, "C1525", {1: "VIN_D", 2: "RST_G"}, POS["C8"]),
    ("R7", "Device:R", "1M", R0402, "C26083", {1: "RST_G", 2: "GND"}, POS["R7"]),
    # Lato sotto (solo piazzole, non montate da JLC): contatti di ricarica Ø 2,5 mm (VIN, GND) a 4,2 mm, a filo della resina;
    # Tag-Connect TC2030-NL per SWD (annegato); piazzole di prova; vibratore (fili saldati a mano sulle piazzole MOT+/MOT-)
    ("TP1", "Connector:TestPoint", "VIN", "TestPoint:TestPoint_Pad_D2.5mm", "", {1: "VIN"}, POS["TP1"]),
    ("TP2", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_D2.5mm", "", {1: "GND"}, POS["TP2"]),
    # Tag-Connect TC2030-NL (pinout standard ARM SWD: 1 VREF, 2 SWDIO, 3 nRESET, 4 SWCLK, 5 GND, 6 SWO non usato)
    ("J4", "Connector:Conn_ARM_SWD_TagConnect_TC2030-NL", "TC2030-NL", TC2030, "",
     {1: "VDD", 2: "SWDIO", 3: "RESET", 4: "SWDCLK", 5: "GND"}, POS["J4"]),
    # piazzole di prova Ø 0,8 mm (segnali) e Ø 1 mm (tester: VBAT, VDD, GND)
    ("TP3", "Connector:TestPoint", "CHG_N", TP08, "", {1: "CHG_N"}, POS["TP3"]),
    ("TP4", "Connector:TestPoint", "SENS_ON", TP08, "", {1: "SENS_ON"}, POS["TP4"]),
    ("TP5", "Connector:TestPoint", "VDD_SENS", TP08, "", {1: "VDD_SENS"}, POS["TP5"]),
    ("TP6", "Connector:TestPoint", "FG_ALRT", TP08, "", {1: "FG_ALRT"}, POS["TP6"]),
    ("TP7", "Connector:TestPoint", "VBAT", TPSWD, "", {1: "VBAT"}, POS["TP7"]),
    ("TP8", "Connector:TestPoint", "VDD", TPSWD, "", {1: "VDD"}, POS["TP8"]),
    ("TP9", "Connector:TestPoint", "GND", TPSWD, "", {1: "GND"}, POS["TP9"]),
    ("TP10", "Connector:TestPoint", "MOT+", TP1MM, "", {1: "VBAT"}, POS["TP10"]),
    ("TP11", "Connector:TestPoint", "MOT-", TP1MM, "", {1: "MOT_N"}, POS["TP11"]),
]


# ---- v0.3: aggiunte comuni alle varianti ----
COMPONENTI += [
    # interruttore di carico dei sensori: VDD -> VDD_SENS, acceso da GPIO (P0.05); QOD 150 ohm scarica l'uscita a spento
    ("U6", "swimtag:TPS22916CYFPR", "TPS22916C", "swimtag:DSBGA-4_L0.78-W0.78-P0.40", "C2680319",
     {"A2": "VDD", "A1": "VDD_SENS", "B2": "SENS_ON", "B1": "GND"}, POS["U6"]),
    ("R8", "Device:R", "1M", R0402, "C26083", {1: "SENS_ON", 2: "GND"}, POS["R8"]),  # pull-down su ON (ridondante con il "smart pulldown" 750 k interno)
    # misuratore di carica MAX17048 sul VBAT (lato sistema), secondo bus I2C con pull-up su VDD sempre acceso
    ("U7", "swimtag:MAX17048G+T10", "MAX17048", "Package_DFN_QFN:TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm", "C2682616",
     {1: "GND", 2: "VBAT", 3: "VBAT", 4: "GND", 5: "FG_ALRT", 6: "GND", 7: "FG_SCL", 8: "FG_SDA", 9: "GND"},
     POS["U7"]),
    ("C9", "Device:C", "100n", C0402, "C1525", {1: "VBAT", 2: "GND"}, POS["C9"]),  # bypass VDD del MAX17048
    ("R9", "Device:R", "10k", R0402, "C25744", {1: "FG_SDA", 2: "VDD"}, POS["R9"]),
    ("R10", "Device:R", "10k", R0402, "C25744", {1: "FG_SCL", 2: "VDD"}, POS["R10"]),
    # 2 x 47 uF sulla batteria (lato sistema, a valle del ponticello): vibratore e picchi radio
    ("C10", "Device:C", "47u", C0805, "C16780", {1: "VBAT", 2: "GND"}, POS["C10"]),
    ("C11", "Device:C", "47u", C0805, "C16780", {1: "VBAT", 2: "GND"}, POS["C11"]),
    ("C12", "Device:C", "10u", C0402, "C15525", {1: "BAT", 2: "GND"}, POS["C12"]),  # uscita BQ25101 (1-10 uF), lato batteria
    # connettore batteria: JST SH 1,0 mm laterale; + (BAT) e - (GND)
    ("J1", "Connector_Generic:Conn_01x02", "BATT JST-SH", JST_SH, "C160402", {1: "BAT", 2: "GND"}, POS["J1"]),
]

# 0 ohm tra la cella/caricatore (BAT) e il circuito (VBAT): dissaldandolo a banco il tester va in serie (misura della corrente)
COMPONENTI += [
    ("R11", "Device:R", "0", R0402, "C17168", {1: "BAT", 2: "VBAT"}, POS["R11"]),
]


def reti():
    """{rete: [(rif, pin), ...]} dai collegamenti dei componenti."""
    r = {}
    for rif, _, _, _, _, pins, _ in COMPONENTI:
        for pin, net in pins.items():
            r.setdefault(net, []).append((rif, str(pin)))
    return r
