"""Dati del tag SwimTimer nRF52840: componenti, collegamenti e posizioni.

Unica fonte per lo schema (genera_schema.py) e il PCB (genera_pcb.py), così restano coerenti.
Coordinate PCB in mm, origine in alto a sinistra della scheda, y verso il basso.
Disposizione B (compatta): scheda 17,5 x 22,5 mm, componenti sul lato sopra; sotto solo
contatti di ricarica, piazzole SWD, batteria e vibratore. Antenna del modulo sul bordo alto (3,8 mm senza rame).
"""

SCHEDA_L = 17.5   # larghezza (x)
SCHEDA_H = 22.5   # altezza (y)
ANTENNA_H = 3.8   # striscia senza rame sotto l'antenna (foglio Raytac)

# Impronte standard di KiCad
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"

# Pin del modulo non usati (restano senza collegamento)
NC_U1 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 21, 23, 25, 26, 31, 34, 35,
         47, 48, 49, 50, 52, 54, 56, 57, 58, 59, 60, 61]

TP1MM = "TestPoint:TestPoint_Pad_1.0x1.0mm"
TPSWD = "TestPoint:TestPoint_Pad_D1.0mm"  # SWD su due file sfalsate (passo 1,5 mm in x, 2 mm in y) per la pinza pogo

# rif, simbolo, valore, impronta, LCSC, collegamenti {pin: rete}, (x, y, rotazione, lato)
COMPONENTI = [
    ("U1", "swimtag:MDBT50Q-1MV2", "MDBT50Q-1MV2", "swimtag:COMM-SMD_MDBT50Q-1MV2-1", "C5118826",
     {**{p: "GND" for p in (1, 2, 15, 33, 55)},
      28: "VDD", 30: "VBAT", 32: "VIN_D",
      16: "I2C_SCL", 19: "I2C_SDA", 20: "CHG_N", 22: "LED", 24: "MOT_PWM",
      27: "IMU_INT1", 29: "IMU_INT2", 36: "IMU_MISO", 37: "IMU_MOSI", 38: "IMU_CS", 39: "IMU_SCK",
      40: "RESET", 41: "QSPI_CS", 42: "QSPI_SCK", 43: "QSPI_IO1", 44: "QSPI_IO0",
      45: "QSPI_IO3", 46: "QSPI_IO2", 51: "SWDIO", 53: "SWDCLK"},
     (5.55, 9.55, 0, "F")),
    ("U2", "swimtag:LSM6DSV16XTR", "LSM6DSV16X", "swimtag:LGA-14_L3.0-W2.5-P0.50-BR", "C5267406",
     {1: "IMU_MISO", 2: "GND", 3: "GND", 4: "IMU_INT1", 5: "VDD", 6: "GND", 7: "GND", 8: "VDD",
      9: "IMU_INT2", 12: "IMU_CS", 13: "IMU_SCK", 14: "IMU_MOSI"},
     (12.44, 14.65, 180, "F")),
    ("U3", "swimtag:W25Q256JVEIQTR", "W25Q256JVEIQ", "swimtag:WSON-8_L8.0-W6.10-P1.27-BL-EP", "C97522",
     {1: "QSPI_CS", 2: "QSPI_IO1", 3: "QSPI_IO2", 4: "GND", 5: "QSPI_IO0", 6: "QSPI_SCK",
      7: "QSPI_IO3", 8: "VDD", 9: "GND"},
     (13.95, 8.58, 180, "F")),
    ("U4", "swimtag:BQ25101YFPR", "BQ25101", "swimtag:DSBGA-6_L0.9-W1.6-R2-C3-P0.40-BL", "C478468",
     {"A2": "VIN_D", "A1": "VBAT", "B1": "TS", "B2": "ISET", "C1": "CHG_N", "C2": "GND"},
     (15.75, 14.2, 90, "F")),
    ("U5", "swimtag:MS5837-02BA", "MS5837-02BA", "swimtag:LGA-4_L3.3-W3.3-P2.00-TL", "C2887129",
     {1: "GND", 2: "VDD", 3: "I2C_SCL", 4: "I2C_SDA"},
     (1.95, 18.6, 0, "F")),
    ("Q1", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917",
     {1: "MOT_PWM", 2: "GND", 3: "MOT_N"}, (5.7, 18.75, 0, "F")),
    ("D1", "Device:D", "1N4148WS", "Diode_SMD:D_SOD-323", "C2128",
     {1: "VBAT", 2: "MOT_N"}, (8.75, 18.9, 90, "F")),
    ("D2", "Device:LED", "rosso", LED0603, "C2286", {1: "LED_K", 2: "VBAT"}, (14.5, 18.25, 0, "F")),
    ("R1", "Device:R", "10k", R0402, "C25744", {1: "ISET", 2: "GND"}, (14.6, 14.35, 90, "F")),
    ("R2", "Device:R", "10k", R0402, "C25744", {1: "TS", 2: "GND"}, (16.9, 14.35, 90, "F")),
    ("R3", "Device:R", "100k", R0402, "C25741", {1: "MOT_PWM", 2: "GND"}, (5.7, 16.2, 0, "F")),
    ("R4", "Device:R", "1k", R0402, "C11702", {1: "LED_K", 2: "LED"}, (16.75, 19.95, 90, "F")),
    ("R5", "Device:R", "10k", R0402, "C25744", {1: "I2C_SDA", 2: "VDD"}, (11.4, 18.3, 0, "F")),  # pull-up I2C (TE)
    ("R6", "Device:R", "10k", R0402, "C25744", {1: "I2C_SCL", 2: "VDD"}, (11.2, 21.5, 0, "F")),
    ("C1", "Device:C", "10u", C0402, "C15525", {1: "VDD", 2: "GND"}, (7.67, 16.2, 0, "F")),  # VDD del modulo (pin 28)
    ("C2", "Device:C", "100n", C0402, "C1525", {1: "VDD", 2: "GND"}, (11.9, 16.55, 0, "F")),  # IMU Vdd_IO (pin 5)
    ("C3", "Device:C", "100n", C0402, "C1525", {1: "VDD", 2: "GND"}, (15.32, 16.3, 90, "F")),  # flash VCC
    ("C4", "Device:C", "100n", C0402, "C1525", {1: "VDD", 2: "GND"}, (1.95, 16.2, 0, "F")),
    ("C5", "Device:C", "10u", C0402, "C15525", {1: "VIN_D", 2: "GND"}, (16.37, 16.3, 90, "F")),  # ingresso caricatore e VBUS
    ("C6", "Device:C", "100n", C0402, "C1525", {1: "VDD", 2: "GND"}, (13.83, 16.55, 0, "F")),  # IMU Vdd (pin 8)
    ("C7", "Device:C", "10u", C0402, "C15525", {1: "VBAT", 2: "GND"}, (9.6, 16.2, 0, "F")),  # VDDH (pin 30) e uscita caricatore (1-10 uF)
    # Protezione dei contatti di ricarica e reset all'inserimento nella custodia
    ("D3", "swimtag:SD05.TCT", "SD05 TVS 5V", "swimtag:SOD-323_L1.8-W1.3-LS2.5-RD", "C85201",
     {1: "VIN", 2: "GND"}, (2.0, 21.5, 0, "F")),
    ("D4", "swimtag:B5819WS_C22624", "B5819WS", "swimtag:SOD-323_L1.8-W1.3-LS2.5-RD", "C22624",
     {1: "VIN_D", 2: "VIN"}, (5.6, 21.5, 0, "F")),
    ("Q2", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917",
     {1: "RST_G", 2: "GND", 3: "RESET"}, (14.2, 20.82, 0, "F")),
    ("C8", "Device:C", "100n", C0402, "C1525", {1: "VIN_D", 2: "RST_G"}, (7.75, 21.5, 90, "F")),
    ("R7", "Device:R", "1M", R0402, "C26083", {1: "RST_G", 2: "GND"}, (9.25, 21.5, 0, "F")),
    # Piazzole tutte sul lato sotto: ricarica (a filo della resina), SWD (annegate),
    # batteria e vibratore (fili saldati a mano che girano intorno al bordo)
    ("TP1", "Connector:TestPoint", "VIN", "TestPoint:TestPoint_Pad_D2.5mm", "", {1: "VIN"}, (2.5, 21.0, 0, "B")),
    ("TP2", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_D2.5mm", "", {1: "GND"}, (6.7, 21.0, 0, "B")),
    ("TP3", "Connector:TestPoint", "SWD_VDD", TPSWD, "", {1: "VDD"}, (10.0, 18.6, 0, "B")),
    ("TP4", "Connector:TestPoint", "SWDIO", TPSWD, "", {1: "SWDIO"}, (11.5, 20.6, 0, "B")),
    ("TP5", "Connector:TestPoint", "SWDCLK", TPSWD, "", {1: "SWDCLK"}, (13.0, 18.6, 0, "B")),
    ("TP6", "Connector:TestPoint", "RESET", TPSWD, "", {1: "RESET"}, (14.5, 20.6, 0, "B")),
    ("TP7", "Connector:TestPoint", "SWD_GND", TPSWD, "", {1: "GND"}, (16.0, 18.6, 0, "B")),
    ("TP8", "Connector:TestPoint", "BAT+", TP1MM, "", {1: "VBAT"}, (1.0, 14.5, 0, "B")),
    ("TP9", "Connector:TestPoint", "BAT-", TP1MM, "", {1: "GND"}, (1.0, 16.5, 0, "B")),
    ("TP10", "Connector:TestPoint", "MOT+", TP1MM, "", {1: "VBAT"}, (16.7, 5.5, 0, "B")),
    ("TP11", "Connector:TestPoint", "MOT-", TP1MM, "", {1: "MOT_N"}, (16.7, 7.5, 0, "B")),
]


def reti():
    """{rete: [(rif, pin), ...]} dai collegamenti dei componenti."""
    r = {}
    for rif, _, _, _, _, pins, _ in COMPONENTI:
        for pin, net in pins.items():
            r.setdefault(net, []).append((rif, str(pin)))
    return r
