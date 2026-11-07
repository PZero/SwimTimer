"""SwimTimer - formato .swr della registrazione in vasca (XIAO, firmware 0.5.0).

Codifica (usata solo nei test, per generare dati inventati) e decodifica del formato descritto in
swr_formato.h. Una registrazione e' una sequenza di pagine da 256 byte; ogni pagina dati si decodifica da sola.
Nessun dato reale: i test usano solo campioni inventati.
"""
import csv
import statistics
import struct

PAGINA = 256
TOT_PAGINE = 8192
T_SEGMENTO, T_DATI, T_CHIUSURA = 0xA5, 0xD1, 0xE0
FLAG_PRIMA, FLAG_GAP = 0x01, 0x02
MOTIVI = {1: "quiete", 2: "memoria piena", 3: "batteria", 5: "errore flash/IMU"}
ODR_HZ_NOMINALE = 2083 / 10.0
MS_PER_CAMPIONE = 1000.0 / ODR_HZ_NOMINALE
# unita' per LSB (valori del segmento): acc 488 ug/LSB (+-16 g), giro 35 mdps/LSB (+-1000 dps)
G_PER_LSB = 488 / 1e6
DPS_PER_LSB = 35 / 1e3


def crc16(dati, crc=0xFFFF):
    """CRC16-CCITT (init 0xFFFF), stessa forma ottimizzata del firmware (swrCrc16)."""
    for b in dati:
        x = ((crc >> 8) ^ b) & 0xFF
        x ^= x >> 4
        crc = ((crc << 8) ^ (x << 12) ^ (x << 5) ^ x) & 0xFFFF
    return crc


def crc_pagina(pag):
    return crc16(pag[16:PAGINA], crc16(pag[0:14]))


def intestazione(pag, tipo, param, numero, millis, mv, temp, flag, segmento):
    """Scrive intestazione e CRC in `pag` (bytearray da 256 byte, payload gia' dentro)."""
    pag[0:14] = struct.pack("<BBHIHbBH", tipo, param, numero, millis, mv, temp, flag, segmento)
    pag[14:16] = struct.pack("<H", crc_pagina(pag))


# ---------------------------------------------------------------- codifica (specchio di SwrCodificatore)
class Codificatore:
    def __init__(self):
        self.azzera()

    def azzera(self):
        self.pag = bytearray(b"\xff" * PAGINA)
        self.pos = 16
        self.nc = 0
        self.prev = None
        self.t_primo = 0

    @staticmethod
    def in_scala(s, p):
        return all(-127 <= s[i] - p[i] <= 127 for i in range(6))

    def sta(self, s):
        if self.nc == 0:
            return True
        return self.pos + (6 if self.in_scala(s, self.prev) else 13) <= PAGINA

    def _assoluto(self, s):
        self.pag[self.pos:self.pos + 12] = struct.pack("<6h", *s)
        self.pos += 12

    def aggiungi(self, s, t):
        if self.nc == 0:
            self.t_primo = t
            self._assoluto(s)
        elif self.in_scala(s, self.prev):
            self.pag[self.pos:self.pos + 6] = struct.pack("<6b", *[s[i] - self.prev[i] for i in range(6)])
            self.pos += 6
        else:
            self.pag[self.pos] = 0x80
            self.pos += 1
            self._assoluto(s)
        self.prev = tuple(s)
        self.nc += 1

    def chiudi(self, numero, segmento, mv, temp, flag):
        intestazione(self.pag, T_DATI, self.nc, numero, self.t_primo, mv, temp, flag, segmento)
        return bytes(self.pag)


def pagina_segmento(numero, segmento, millis=0, mv=4000, temp=22, causa=1, tocchi=2, versione="0.5.0"):
    pag = bytearray(b"\xff" * PAGINA)
    pag[16:38] = struct.pack("<HHHhhhBB8s", 2083, 488, 35, 0, 0, 0, causa, tocchi, versione.encode()[:7])
    intestazione(pag, T_SEGMENTO, 1, numero, millis, mv, temp, 0, segmento)
    return bytes(pag)


def pagina_chiusura(numero, segmento, motivo, campioni, pagine, millis=0, mv=3900, temp=22):
    pag = bytearray(b"\xff" * PAGINA)
    pag[16:24] = struct.pack("<II", campioni, pagine)
    intestazione(pag, T_CHIUSURA, motivo, numero, millis, mv, temp, 0, segmento)
    return bytes(pag)


# ---------------------------------------------------------------- decodifica
def decodifica_dati(pag):
    """Decodifica il payload di una pagina dati (solo i byte, la CRC si controlla fuori). Ritorna la lista di tuple."""
    n = pag[1]
    pos = 16
    campioni = []
    if n == 0:
        return campioni
    cur = struct.unpack_from("<6h", pag, pos)
    pos += 12
    campioni.append(cur)
    for _ in range(n - 1):
        if pos >= PAGINA:
            raise ValueError("pagina troncata")
        if pag[pos] == 0x80:
            if pos + 13 > PAGINA:
                raise ValueError("escape oltre la pagina")
            cur = struct.unpack_from("<6h", pag, pos + 1)
            pos += 13
        else:
            if pos + 6 > PAGINA:
                raise ValueError("delta oltre la pagina")
            d = struct.unpack_from("<6b", pag, pos)
            cur = tuple(cur[i] + d[i] for i in range(6))
            if any(not -32768 <= v <= 32767 for v in cur):
                raise ValueError("campione fuori scala")
            pos += 6
        campioni.append(cur)
    return campioni


class Esito:
    def __init__(self):
        self.problemi = []        # elenco di stringhe leggibili
        self.pagine_corrotte = []  # indici di pagina
        self.segmenti = {}         # idx -> dict(info)
        self.pagine_dati = []      # dict per pagina dati valida
        self.pagine_usate = 0

    def avvisa(self, testo):
        self.problemi.append(testo)


def decodifica(immagine):
    """Decodifica un'immagine .swr (pagine concatenate; le pagine libere 0xFF alla fine sono ignorate)."""
    es = Esito()
    es.dimensione = len(immagine)
    if len(immagine) % PAGINA:
        es.avvisa("file troncato: %d byte non e' multiplo di %d" % (len(immagine), PAGINA))
    n_pag = len(immagine) // PAGINA
    seg_corrente = None
    for p in range(n_pag):
        pag = immagine[p * PAGINA:(p + 1) * PAGINA]
        if pag[:16] == b"\xff" * 16:
            break                                            # prima pagina libera: fine dei dati
        es.pagine_usate = p + 1
        tipo, param, numero, millis, mv, temp, flag, seg, crc = struct.unpack_from("<BBHIHbBHH", pag, 0)
        if crc != crc_pagina(pag):
            es.pagine_corrotte.append(p)
            es.avvisa("pagina %d: CRC errata (pagina scartata)" % p)
            continue
        if numero != p:
            es.avvisa("pagina %d: numero interno %d diverso dalla posizione" % (p, numero))
        if tipo == T_SEGMENTO:
            odr, ug, mdps, bx, by, bz, causa, tocchi, ver = struct.unpack_from("<HHHhhhBB8s", pag, 16)
            es.segmenti[seg] = dict(idx=seg, pagina=p, millis=millis, mv_inizio=mv, odr_x10=odr, ug_lsb=ug, mdps_lsb=mdps,
                                    bias=(bx, by, bz), causa=causa, tocchi=tocchi, versione=ver.split(b"\0")[0].decode("ascii", "replace"),
                                    chiuso=False, motivo=None, campioni=None, pagine=None)
            seg_corrente = seg
        elif tipo == T_DATI:
            if seg not in es.segmenti:
                es.avvisa("pagina %d: dati del segmento %d senza pagina di segmento valida" % (p, seg))
                continue
            try:
                camp = decodifica_dati(pag)
            except (ValueError, struct.error) as e:
                es.pagine_corrotte.append(p)
                es.avvisa("pagina %d: dati non decodificabili (%s)" % (p, e))
                continue
            es.pagine_dati.append(dict(pagina=p, seg=seg, millis=millis, mv=mv, temp=temp, flag=flag, campioni=camp))
            if flag & FLAG_GAP:
                es.avvisa("pagina %d: interruzione dei dati (overrun del FIFO) prima di questa pagina" % p)
        elif tipo == T_CHIUSURA:
            if seg in es.segmenti:
                campioni, pagine = struct.unpack_from("<II", pag, 16)
                es.segmenti[seg].update(chiuso=True, motivo=param, campioni=campioni, pagine=pagine, mv_fine=mv)
            else:
                es.avvisa("pagina %d: chiusura del segmento %d senza segmento" % (p, seg))
        else:
            es.avvisa("pagina %d: tipo 0x%02X sconosciuto" % (p, tipo))
    for s in es.segmenti.values():
        if not s["chiuso"]:
            es.avvisa("segmento %d senza chiusura (batteria scarica o spegnimento: la fine e' l'ultima pagina valida)" % s["idx"])
    return es


def _adatta_tempi(pagine):
    """Per un gruppo di pagine contigue ritorna [(t0_ms, ms_per_campione)] per pagina, dalla regressione millis ~ indice."""
    n = len(pagine)
    idx = []
    c = 0
    for pg in pagine:
        idx.append(c)
        c += len(pg["campioni"])
    ms = [pg["millis"] for pg in pagine]
    b = MS_PER_CAMPIONE
    a = ms[0]
    if n >= 3:
        mi, mm = sum(idx) / n, sum(ms) / n
        den = sum((i - mi) ** 2 for i in idx)
        if den > 0:
            bb = sum((idx[k] - mi) * (ms[k] - mm) for k in range(n)) / den
            if abs(bb - MS_PER_CAMPIONE) < 0.05 * MS_PER_CAMPIONE:    # scarta stime assurde
                b = bb
                a = mm - b * mi
    return [(a + b * idx[k], b) for k in range(n)]


def righe(esito):
    """Genera le righe del CSV: (seg, pagina, n, t_s, ax,ay,az,gx,gy,gz grezzi, mV).
    Il tempo e' in secondi dall'inizio del segmento (millis del tag, ripuliti dal rumore con una regressione sulle pagine
    contigue); fra segmenti diversi il tempo non e' collegabile (la tag si spegne e il suo orologio riparte)."""
    per_seg = {}
    for pg in esito.pagine_dati:
        per_seg.setdefault(pg["seg"], []).append(pg)
    for seg in sorted(per_seg):
        pagine = per_seg[seg]
        # gruppi contigui: si spezza dove manca una pagina (corrotta/persa) o c'e' il flag di interruzione
        gruppi, cur = [], [pagine[0]]
        for pg in pagine[1:]:
            if pg["pagina"] != cur[-1]["pagina"] + 1 or pg["flag"] & FLAG_GAP:
                gruppi.append(cur)
                cur = []
            cur.append(pg)
        gruppi.append(cur)
        t_inizio = None
        n_seg = 0
        for g in gruppi:
            for pg, (t0, b) in zip(g, _adatta_tempi(g)):
                if t_inizio is None:
                    t_inizio = t0
                for k, s in enumerate(pg["campioni"]):
                    yield (seg, pg["pagina"], n_seg, (t0 + b * k - t_inizio) / 1000.0, *s, pg["mv"])
                    n_seg += 1


INTEST_CSV = ["seg", "pagina", "n", "t_s", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps", "mV"]
INTEST_CSV_GREZZO = ["seg", "pagina", "n", "t_s", "ax", "ay", "az", "gx", "gy", "gz", "mV"]


def scrivi_csv(esito, percorso, grezzo=False):
    n = 0
    with open(percorso, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(INTEST_CSV_GREZZO if grezzo else INTEST_CSV)
        for r in righe(esito):
            if grezzo:
                w.writerow([r[0], r[1], r[2], "%.4f" % r[3], *r[4:]])
            else:
                w.writerow([r[0], r[1], r[2], "%.4f" % r[3],
                            *["%.5f" % (v * G_PER_LSB) for v in r[4:7]],
                            *["%.3f" % (v * DPS_PER_LSB) for v in r[7:10]], r[10]])
            n += 1
    return n


def riassunto(esito):
    """Testo leggibile: segmenti, durata, problemi."""
    ult = {}
    for pg in esito.pagine_dati:
        ult.setdefault(pg["seg"], []).append(pg)
    out = ["pagine usate: %d (%.1f%% della memoria), segmenti: %d" % (
        esito.pagine_usate, 100.0 * esito.pagine_usate / TOT_PAGINE, len(esito.segmenti))]
    for idx in sorted(esito.segmenti):
        s = esito.segmenti[idx]
        pagine = ult.get(idx, [])
        camp = sum(len(p["campioni"]) for p in pagine)
        out.append("  segmento %d: %d campioni (~%.1f s), batteria %d mV%s, fine: %s" % (
            idx, camp, camp / ODR_HZ_NOMINALE, s["mv_inizio"],
            (" -> %d mV" % s["mv_fine"]) if s.get("mv_fine") else "",
            MOTIVI.get(s["motivo"], "senza chiusura") if s["chiuso"] else "senza chiusura"))
    if esito.problemi:
        out.append("PROBLEMI (%d):" % len(esito.problemi))
        out.extend("  - " + p for p in esito.problemi)
    else:
        out.append("nessun problema rilevato")
    return "\n".join(out)
