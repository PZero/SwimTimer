"""Verifica indipendente della scheda v0.4 economica (revisione del 2026-11-03).

Uso: python verifica_v04.py <file.kicad_pcb> <net.xml> [cpl.csv bom.csv]
Legge il PCB, la netlist esportata (kicad-cli sch export netlist --format kicadxml)
e confronta con una tabella ATTESA scritta a mano dai fogli tecnici (non copiata dallo script di generazione).
"""
import re, sys, math, csv
import xml.etree.ElementTree as ET


def parse(txt):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', txt)
    pos = 0

    def rd():
        nonlocal pos
        t = tok[pos]
        pos += 1
        if t == '(':
            l = []
            while tok[pos] != ')':
                l.append(rd())
            pos += 1
            return l
        return t[1:-1] if t.startswith('"') else t
    return rd()


def find(n, key):
    return [c for c in n if isinstance(c, list) and c and c[0] == key]


def load_pcb(path):
    root = parse(open(path, encoding='utf-8').read())
    fps = {}
    for fp in find(root, 'footprint'):
        at = find(fp, 'at')[0]
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        ref = [p[2] for p in find(fp, 'property') if p[1] == 'Reference'][0]
        layer = find(fp, 'layer')[0][1]
        pads = {}
        for p in find(fp, 'pad'):
            pa = find(p, 'at')[0]
            px, py = float(pa[1]), float(pa[2])
            sz = find(p, 'size')[0]
            net = find(p, 'net')
            th = math.radians(rot)
            ax = x + px * math.cos(th) + py * math.sin(th)
            ay = y - px * math.sin(th) + py * math.cos(th)
            pads[p[1]] = dict(local=(px, py), abs=(round(ax, 3), round(ay, 3)), size=(float(sz[1]), float(sz[2])),
                              net=(net[0][-1] if net else None), type=p[2], shape=p[3])
        fps[ref] = dict(fp=fp[1], at=(x, y, rot), layer=layer, pads=pads)
    return root, fps


def load_net(path):
    r = ET.parse(path).getroot()
    nets = {}
    for n in r.find('nets'):
        for nd in n.findall('node'):
            nets[(nd.get('ref'), nd.get('pin'))] = n.get('name')
    return nets


def norm(n):
    return None if n is None else n.lstrip('/')


# --- tabella ATTESA, ricavata dai fogli tecnici e dall'intenzione di progetto (progetto.md v0.4) ---
ATT = {}
# E73-2G4M08S1C (manuale Ebyte v1.9, par. 3, tabella pin): pad -> rete
for p in (5, 21, 24):
    ATT[('U1', str(p))] = 'GND'
ATT[('U1', '19')] = 'VDD'            # VDD (uscita REG0 in modo alta tensione)
ATT[('U1', '23')] = 'VBAT'           # VDDH = cella
ATT[('U1', '26')] = 'RESET'          # P0.18/RESET
ATT[('U1', '37')] = 'SWDIO'
ATT[('U1', '39')] = 'SWDCLK'
ATT[('U1', '11')] = 'IMU_CS'         # P0.00
ATT[('U1', '13')] = 'IMU_MISO'       # P0.01
ATT[('U1', '15')] = 'IMU_MOSI'       # P0.05
ATT[('U1', '17')] = 'IMU_SCK'        # P1.09
ATT[('U1', '28')] = 'FL_MISO'        # P0.15
ATT[('U1', '30')] = 'FL_CS'          # P0.17
ATT[('U1', '33')] = 'FL_MOSI'        # P0.13
ATT[('U1', '35')] = 'FL_SCK'         # P0.24
ATT[('U1', '32')] = 'CHG_N'          # P0.20
ATT[('U1', '34')] = 'LED'            # P0.22
ATT[('U1', '12')] = 'IMU_INT1'       # P0.26
ATT[('U1', '14')] = 'IMU_INT2'       # P0.06
# LSM6DSV16X (AN5763 rev.2, tab.1 e fig.1): SPI 4 fili, SDx/SCx a GND, OCS_Aux/SDO_Aux liberi
imu = {1: 'IMU_MISO', 2: 'GND', 3: 'GND', 4: 'IMU_INT1', 5: 'VDD', 6: 'GND', 7: 'GND', 8: 'VDD', 9: 'IMU_INT2',
       12: 'IMU_CS', 13: 'IMU_SCK', 14: 'IMU_MOSI'}
for k, v in imu.items():
    ATT[('U2', str(k))] = v
# W25Q128JV SOIC-8 208 mil (Winbond rev.F, par.3.3)
flash = {1: 'FL_CS', 2: 'FL_MISO', 3: 'FL_IO23', 4: 'GND', 5: 'FL_MOSI', 6: 'FL_SCK', 7: 'FL_IO23', 8: 'VDD'}
for k, v in flash.items():
    ATT[('U3', str(k))] = v
# BQ25101 DSBGA YFP (TI SLUSBV8C, par.6)
for k, v in {'A1': 'VBAT', 'A2': 'VIN_D', 'B1': 'TS', 'B2': 'ISET', 'C1': 'CHG_N', 'C2': 'GND'}.items():
    ATT[('U4', k)] = v
for ref, (a, b) in {'R1': ('ISET', 'GND'), 'R2': ('TS', 'GND'), 'R3': ('LED_K', 'LED'), 'R4': ('FL_IO23', 'VDD'),
                    'R5': ('FL_CS', 'VDD'), 'R6': ('IMU_CS', 'VDD'), 'C1': ('VDD', 'GND'), 'C2': ('VDD', 'GND'),
                    'C3': ('VDD', 'GND'), 'C4': ('VDD', 'GND'), 'C5': ('VIN_D', 'GND'), 'C6': ('VBAT', 'GND'),
                    'C7': ('VBAT', 'GND')}.items():
    ATT[(ref, '1')] = a
    ATT[(ref, '2')] = b
ATT[('D1', '2')] = 'VDD'       # anodo su VDD
ATT[('D1', '1')] = 'LED_K'     # catodo verso R3
ATT[('D2', '1')] = 'VIN_D'     # catodo verso il caricatore
ATT[('D2', '2')] = 'VIN'       # anodo al contatto di ricarica
ATT[('J1', '1')] = 'VBAT'
ATT[('J1', '2')] = 'GND'
for i, n in enumerate(['VDD', 'SWDIO', 'SWDCLK', 'RESET', 'GND'], 1):
    ATT[('TP%d' % i, '1')] = n
ATT[('TP6', '1')] = 'VIN'
ATT[('TP7', '1')] = 'GND'

if __name__ == '__main__':
    pcb, netxml = sys.argv[1], sys.argv[2]
    root, fps = load_pcb(pcb)
    nets = load_net(netxml)
    bad = 0
    for (ref, pin), exp in sorted(ATT.items()):
        got = norm(nets.get((ref, pin)))
        if got != exp:
            bad += 1
            print('SCHEMA DIVERSO', ref, pin, 'atteso', exp, 'trovato', got)
    for (ref, pin), n in sorted(nets.items()):
        if (ref, pin) not in ATT and not n.startswith('unconnected'):
            print('PIN COLLEGATO NON ATTESO', ref, pin, n)
    for ref, f in fps.items():
        for pn, p in f['pads'].items():
            sn = norm(nets.get((ref, pn)))
            pnet = norm(p['net'])
            if sn and sn.startswith('unconnected'):
                sn = None
            if sn != pnet:
                bad += 1
                print('PCB != SCHEMA', ref, pn, sn, pnet)
    print('pin attesi:', len(ATT), 'differenze:', bad)
    if len(sys.argv) > 4:
        cpl = {r['Designator']: r for r in csv.DictReader(open(sys.argv[3]))}
        bom = {}
        for r in csv.DictReader(open(sys.argv[4])):
            for d in r['Designator'].split(','):
                bom[d] = r
        pcbmont = {r for r, f in fps.items() if not r.startswith('TP')}
        print('in PCB non in CPL:', sorted(pcbmont - set(cpl)))
        print('in CPL non in PCB:', sorted(set(cpl) - pcbmont))
        print('in PCB non in BOM:', sorted(pcbmont - set(bom)))
        print('in BOM non in PCB:', sorted(set(bom) - pcbmont))
        for r, c in sorted(cpl.items()):
            f = fps.get(r)
            if not f:
                continue
            x = float(c['Mid X'].replace('mm', ''))
            y = float(c['Mid Y'].replace('mm', ''))
            print(r, 'CPL', x, y, c['Rotation'], 'PCB', f['at'], f['layer'])
