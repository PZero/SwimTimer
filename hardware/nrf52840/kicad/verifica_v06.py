"""Verifica indipendente della scheda v0.6 Rev0 (da verifica_v05.py, tabella ATTESA riscritta dai fogli tecnici il 2026-11-06).

Uso: python verifica_v06.py <file.kicad_pcb> <net.xml> [cpl.csv bom.csv]
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


# --- tabella ATTESA, ricavata dai fogli tecnici e dall'intenzione di progetto (progetto.md v0.5) ---
ATT = {}
# E73-2G4M08S1C (manuale Ebyte v1.9, par. 3, tabella pin): pad -> rete
for p in (5, 21, 24):
    ATT[('U1', str(p))] = 'GND'
ATT[('U1', '19')] = 'VDD'            # VDD (uscita REG0 in modo alta tensione)
ATT[('U1', '23')] = 'VBAT'           # VDDH = cella
ATT[('U1', '26')] = 'RESET'          # P0.18/RESET
ATT[('U1', '37')] = 'SWDIO'
ATT[('U1', '39')] = 'SWDCLK'
ATT[('U1', '20')] = 'IMU_CS'         # P0.12 (v0.5: P0.00/P0.01 = XL1/XL2 liberi)
ATT[('U1', '16')] = 'IMU_MISO'       # P0.08
ATT[('U1', '18')] = 'SENS_ON'        # P0.04 -> ON del TPS22916C
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
imu = {1: 'IMU_MISO', 2: 'GND', 3: 'GND', 4: 'IMU_INT1', 5: 'VDD_IMU', 6: 'GND', 7: 'GND', 8: 'VDD_IMU', 9: 'IMU_INT2',
       12: 'IMU_CS', 13: 'IMU_SCK', 14: 'IMU_MOSI'}
for k, v in imu.items():
    ATT[('U2', str(k))] = v
# W25Q128JV SOIC-8 208 mil (Winbond rev.F, par.3.3)
flash = {1: 'FL_CS', 2: 'FL_MISO', 3: 'FL_IO23', 4: 'GND', 5: 'FL_MOSI', 6: 'FL_SCK', 7: 'FL_IO23', 8: 'VDD'}
for k, v in flash.items():
    ATT[('U3', str(k))] = v
# MCP73831T-2ACI/OT SOT-23-5 (Microchip DS20001984H, tab. 3-1): 1 STAT, 2 VSS, 3 VBAT, 4 VDD, 5 PROG
for k, v in {'1': 'CHG_STAT', '2': 'GND', '3': 'VBAT', '4': 'VIN_D', '5': 'ISET'}.items():
    ATT[('U4', k)] = v
for ref, (a, b) in {'R1': ('ISET', 'GND'), 'R2': ('CHG_N', 'VDD'), 'R3': ('LED_K', 'LED'), 'R4': ('FL_IO23', 'VDD'),
                    'R5': ('FL_CS', 'VDD'), 'R6': ('IMU_CS', 'VDD_IMU'), 'R7': ('SENS_ON', 'GND'), 'R8': ('VIN', 'GND'), 'R9': ('BAT_G', 'GND'),
                    'C1': ('VDD', 'GND'), 'C2': ('VDD_IMU', 'GND'),
                    'C3': ('VDD', 'GND'), 'C4': ('VDD_IMU', 'GND'), 'C5': ('VIN_D', 'GND'), 'C6': ('VBAT', 'GND')}.items():
    ATT[(ref, '1')] = a
    ATT[(ref, '2')] = b
ATT[('D1', '2')] = 'VDD'       # anodo su VDD
ATT[('D1', '1')] = 'LED_K'     # catodo verso R3
ATT[('D2', '1')] = 'VIN_D'     # catodo verso il caricatore
ATT[('D2', '2')] = 'VIN'       # anodo al contatto di ricarica
# TPS22917DBVR SOT-23-6 (TI SLVSDW8B, fig. 6-1): 1 VIN, 2 GND, 3 ON, 4 CT (libero), 5 QOD (su VOUT), 6 VOUT
for k, v in {'1': 'VDD', '2': 'GND', '3': 'SENS_ON', '5': 'VDD_IMU', '6': 'VDD_IMU'}.items():
    ATT[('U6', k)] = v
# D4 1N4148WS: pin 1 catodo su STAT, pin 2 anodo su CHG_N (basso solo con STAT basso)
ATT[('D4', '1')] = 'CHG_STAT'
ATT[('D4', '2')] = 'CHG_N'
# AO3401A (SOT-23: 1 G, 2 S, 3 D): drain verso la cella (+), source verso il circuito, gate a massa con 100 k
ATT[('Q1', '1')] = 'BAT_G'
ATT[('Q1', '2')] = 'VBAT'
ATT[('Q1', '3')] = 'BAT_IN'
# TVS bidirezionale sul contatto VIN, prima di D2
ATT[('D3', '1')] = 'VIN'
ATT[('D3', '2')] = 'GND'
ATT[('J1', '1')] = 'BAT_IN'
ATT[('J1', '2')] = 'GND'
for i, n in enumerate(['VDD', 'SWDIO', 'SWDCLK', 'RESET', 'GND'], 1):
    ATT[('TP%d' % i, '1')] = n
ATT[('TP6', '1')] = 'VIN'
ATT[('TP7', '1')] = 'GND'
ATT[('TP8', '1')] = 'VDD_IMU'

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
            if pnet and pnet.startswith('unconnected'):
                pnet = None
            if sn != pnet:
                bad += 1
                print('PCB != SCHEMA', ref, pn, sn, pnet)
    print('pin attesi:', len(ATT), 'differenze:', bad)
    # nessun BGA/WLCSP con passo < 0,45 mm (Rev0 NextPCB): impronte con nome BGA/CSP o pad tutti rotondi in griglia fitta
    brutti = 0
    for ref, f in fps.items():
        nm = f['fp'].upper()
        pads = [p for p in f['pads'].values() if p['type'] == 'smd']
        pitch = min((math.dist(a['abs'], b['abs']) for i, a in enumerate(pads) for b in pads[i + 1:]), default=None)
        sospetto = any(k in nm for k in ('BGA', 'CSP', 'DSBGA', 'WLCSP')) or (len(pads) >= 4 and all(p['shape'] == 'circle' for p in pads))
        if sospetto:
            brutti += 1
            print('BGA/WLCSP TROVATO', ref, f['fp'], 'passo', pitch)
        elif pitch is not None and pitch < 0.55 and ref not in ('U2',):
            print('passo fine', ref, f['fp'], round(pitch, 3))
        if ref == 'U2':
            print('U2 LGA (land grid, non BGA): passo minimo', round(pitch, 3), 'mm')
    print('BGA/WLCSP con passo < 0,45 mm:', brutti, '(atteso 0)')
    bad += brutti
    if len(sys.argv) > 4:
        cpl = {r['Designator']: r for r in csv.DictReader(open(sys.argv[3]))}
        bom = {}
        for r in csv.DictReader(open(sys.argv[4])):
            for d in r['Designator'].split(','):
                bom[d] = r
        pcbmont = {r for r, f in fps.items() if not r.startswith('TP') and r != 'J1'}   # J1 DNP
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
