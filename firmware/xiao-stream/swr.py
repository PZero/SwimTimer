"""SwimTimer - formato .swr della registrazione in vasca (XIAO, firmware 0.5.0 formato 1, 0.6.0 formato 2).

Codifica (usata solo nei test, per generare dati inventati) e decodifica del formato descritto in
swr_formato.h. Formato 1: sequenza di pagine da 256 byte. Formato 2 (0.6.0): blocchi da 4096 byte (16 pagine); la pagina 0 di
ogni blocco e' l'intestazione (0xB1, seq, byte di conferma fuori dal CRC), le pagine 1..15 sono pagine del formato 1; i blocchi si
riordinano per seq, le pagine tutte 0xFF sono vuote. Ogni pagina dati si decodifica da sola.
Nessun dato reale: i test usano solo campioni inventati.
"""
import csv
import statistics
import struct

PAGINA = 256
TOT_PAGINE = 8192
BLOCCO = 4096
PAGINE_BLOCCO = 16
N_BLOCCHI = 512
T_BLOCCO = 0xB1
FORMATO_FLASH = 3          # 2 = conferma nel byte 16 (solo 2026-11-10, si legge ancora); 3 = conferma nei byte 252..255
OFF_CONFERMA, LEN_CONFERMA = 252, 4
T_SEGMENTO, T_DATI, T_CHIUSURA = 0xA5, 0xD1, 0xE0
FLAG_PRIMA, FLAG_GAP = 0x01, 0x02
MOTIVI = {1: "quiete", 2: "memoria piena", 3: "batteria", 4: "USB collegata", 5: "errore flash/IMU"}
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


def _conferma_ff(pag):
    """Copia della pagina 0 con il campo conferma a 0xFF (formato 2: byte 16; formato 3: parola 252..255)."""
    t = bytearray(pag[:PAGINA])
    if t[1] == 2:
        t[16] = 0xFF
    else:
        t[OFF_CONFERMA:OFF_CONFERMA + LEN_CONFERMA] = b"\xff" * LEN_CONFERMA
    return t


def e_confermato(pag):
    """Blocco confermato dal display (formato 2: byte 16; formato 3: parola 252..255)."""
    if pag[1] == 2:
        return pag[16] != 0xFF
    return any(x != 0xFF for x in pag[OFF_CONFERMA:OFF_CONFERMA + LEN_CONFERMA])


def crc_blocco_pagina(pag):
    """CRC16 dell'intestazione di blocco: byte 0..13 e 16..255 con il campo conferma considerato 0xFF."""
    t = _conferma_ff(pag)
    return crc16(bytes(t[16:PAGINA]), crc16(bytes(t[0:14])))


def crc32_blocco(blocco):
    """CRC32 IEEE del blocco da 4096 byte con il campo conferma della pagina 0 a 0xFF (messaggio BLOCCO del protocollo)."""
    import zlib
    b = bytearray(blocco)
    b[:PAGINA] = _conferma_ff(b[:PAGINA])
    return zlib.crc32(bytes(b)) & 0xFFFFFFFF


def intestazione_blocco(numero_pagina, seq, id_tag=0x12345678, millis=0, mv=4000, temp=22, flag=0, segmento=0, confermato=False):
    """Pagina 0 di un blocco (formato 3)."""
    pag = bytearray(b"\xff" * PAGINA)
    pag[0:14] = struct.pack("<BBHIHbBH", T_BLOCCO, FORMATO_FLASH, numero_pagina, millis, mv, temp, flag, segmento)
    pag[17:25] = struct.pack("<II", seq, id_tag)
    pag[14:16] = struct.pack("<H", crc_blocco_pagina(pag))
    if confermato:
        pag[OFF_CONFERMA:OFF_CONFERMA + LEN_CONFERMA] = b"\x00" * LEN_CONFERMA
    return bytes(pag)


def costruisci_blocco(indice_fisico, seq, pagine, **kw):
    """Blocco da 4096 byte: intestazione + fino a 15 pagine (le altre restano 0xFF)."""
    assert len(pagine) <= PAGINE_BLOCCO - 1
    b = bytearray(intestazione_blocco(indice_fisico * PAGINE_BLOCCO, seq, **kw))
    for p in pagine:
        b += p
    b += b"\xff" * (BLOCCO - len(b))
    return bytes(b)


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
    """Decodifica un'immagine .swr: formato 2 (blocchi, primo byte 0xB1) o formato 1 (pagine concatenate; le pagine
    libere 0xFF alla fine sono ignorate)."""
    es = Esito()
    es.dimensione = len(immagine)
    es.formato = 1
    es.totale_pagine = TOT_PAGINE
    es.blocchi = []
    # formato 2/3: almeno un blocco inizia con 0xB1 (il blocco 0 puo' essere vuoto)
    if any(immagine[i] == T_BLOCCO for i in range(0, len(immagine), BLOCCO)):
        es.formato = 2
        es.totale_pagine = N_BLOCCHI * (PAGINE_BLOCCO - 1)
        return _decodifica_formato2(es, immagine)
    if len(immagine) % PAGINA:
        es.avvisa("file troncato: %d byte non e' multiplo di %d" % (len(immagine), PAGINA))
    n_pag = len(immagine) // PAGINA
    for p in range(n_pag):
        pag = immagine[p * PAGINA:(p + 1) * PAGINA]
        if pag[:16] == b"\xff" * 16:
            break                                            # prima pagina libera: fine dei dati
        es.pagine_usate = p + 1
        _pagina(es, p, pag, p)
    _fine(es)
    return es


def _decodifica_formato2(es, immagine):
    if len(immagine) % BLOCCO:
        es.avvisa("file troncato: %d byte non e' multiplo di %d" % (len(immagine), BLOCCO))
    blocchi = []
    for i in range(len(immagine) // BLOCCO):
        b = immagine[i * BLOCCO:(i + 1) * BLOCCO]
        h = b[:PAGINA]
        valida = (h[0] == T_BLOCCO and h[1] in (2, FORMATO_FLASH)
                  and struct.unpack_from("<H", h, 14)[0] == crc_blocco_pagina(h))
        if not valida:
            es.avvisa("blocco %d nel file: intestazione non valida (blocco scartato)" % i)
            es.pagine_corrotte.append(i * PAGINE_BLOCCO)
            continue
        seq, id_tag = struct.unpack_from("<II", h, 17)
        blocchi.append(dict(seq=seq, id_tag=id_tag, pagina0=struct.unpack_from("<H", h, 2)[0],
                            confermato=e_confermato(h), dati=b, crc32=crc32_blocco(b)))
    blocchi.sort(key=lambda x: x["seq"])
    es.blocchi = [dict(seq=b["seq"], confermato=b["confermato"], crc32=b["crc32"]) for b in blocchi]
    visti = set()
    for a, b in zip(blocchi, blocchi[1:]):
        if a["seq"] == b["seq"]:
            es.avvisa("seq %d presente due volte (ultima copia: %s)" % (a["seq"], "uguale" if a["crc32"] == b["crc32"] else "DIVERSA"))
        elif b["seq"] != a["seq"] + 1:
            es.avvisa("buco di seq: da %d a %d (%d blocchi mancanti)" % (a["seq"], b["seq"], b["seq"] - a["seq"] - 1))
    logico = 0
    prec = None
    for bl in blocchi:
        if prec is not None and bl["seq"] != prec + 1:
            logico += 100                                    # buco: le pagine non sono contigue
        prec = bl["seq"]
        for i in range(1, PAGINE_BLOCCO):
            pag = bl["dati"][i * PAGINA:(i + 1) * PAGINA]
            logico += 1
            if pag == b"\xff" * PAGINA:
                continue                                     # pagina vuota (valida)
            es.pagine_usate += 1
            _pagina(es, logico, pag, bl["pagina0"] + i)
    _fine(es)
    return es


def _pagina(es, p, pag, numero_atteso):
    if True:
        tipo, param, numero, millis, mv, temp, flag, seg, crc = struct.unpack_from("<BBHIHbBHH", pag, 0)
        if crc != crc_pagina(pag):
            es.pagine_corrotte.append(p)
            es.avvisa("pagina %d: CRC errata (pagina scartata)" % p)
            return
        if numero != numero_atteso:
            es.avvisa("pagina %d: numero interno %d diverso dalla posizione" % (p, numero))
        if tipo == T_SEGMENTO:
            odr, ug, mdps, bx, by, bz, causa, tocchi, ver = struct.unpack_from("<HHHhhhBB8s", pag, 16)
            es.segmenti[seg] = dict(idx=seg, pagina=p, millis=millis, mv_inizio=mv, odr_x10=odr, ug_lsb=ug, mdps_lsb=mdps,
                                    bias=(bx, by, bz), causa=causa, tocchi=tocchi, versione=ver.split(b"\0")[0].decode("ascii", "replace"),
                                    chiuso=False, motivo=None, campioni=None, pagine=None)
        elif tipo == T_DATI:
            if seg not in es.segmenti:
                es.avvisa("pagina %d: dati del segmento %d senza pagina di segmento valida" % (p, seg))
                return
            try:
                camp = decodifica_dati(pag)
            except (ValueError, struct.error) as e:
                es.pagine_corrotte.append(p)
                es.avvisa("pagina %d: dati non decodificabili (%s)" % (p, e))
                return
            es.pagine_dati.append(dict(pagina=p, seg=seg, millis=millis, mv=mv, temp=temp, flag=flag, campioni=camp))
            if flag & FLAG_GAP:
                es.avvisa("pagina %d: interruzione dei dati (overrun del FIFO) prima di questa pagina" % p)
        elif tipo == T_CHIUSURA:
            if seg in es.segmenti:
                campioni, pagine = struct.unpack_from("<II", pag, 16)
                es.segmenti[seg].update(chiuso=True, motivo=param, campioni=campioni, pagine=pagine, mv_fine=mv)
                # misure facoltative della 0.6.0 (byte 24..30; 0xFF = assenti): gap massimo del FIFO, overrun, apertura blocco, confermati
                if pag[24:26] != b"\xff\xff":
                    gap, ovr, apri, conf = struct.unpack_from("<HBHH", pag, 24)
                    es.segmenti[seg].update(gap_max_ms=gap, overrun=ovr, apri_max_ms=apri, confermati=conf)
            else:
                es.avvisa("pagina %d: chiusura del segmento %d senza segmento" % (p, seg))
        else:
            es.avvisa("pagina %d: tipo 0x%02X sconosciuto" % (p, tipo))


def _fine(es):
    for s in es.segmenti.values():
        if not s["chiuso"]:
            es.avvisa("segmento %d senza chiusura (batteria scarica, memoria piena o spegnimento: la fine e' l'ultima pagina valida)" % s["idx"])


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
    tot = getattr(esito, "totale_pagine", TOT_PAGINE)
    out = ["formato %d, pagine usate: %d (%.1f%% della memoria), segmenti: %d" % (
        getattr(esito, "formato", 1), esito.pagine_usate, 100.0 * esito.pagine_usate / tot, len(esito.segmenti))]
    bl = getattr(esito, "blocchi", [])
    if bl:
        out.append("blocchi: %d (seq %d..%d), confermati %d" % (len(bl), bl[0]["seq"], bl[-1]["seq"], sum(1 for b in bl if b["confermato"])))
    for idx in sorted(esito.segmenti):
        s = esito.segmenti[idx]
        pagine = ult.get(idx, [])
        camp = sum(len(p["campioni"]) for p in pagine)
        out.append("  segmento %d: %d campioni (~%.1f s), batteria %d mV%s, fine: %s" % (
            idx, camp, camp / ODR_HZ_NOMINALE, s["mv_inizio"],
            (" -> %d mV" % s["mv_fine"]) if s.get("mv_fine") else "",
            MOTIVI.get(s["motivo"], "senza chiusura") if s["chiuso"] else "senza chiusura"))
        if s.get("gap_max_ms") is not None:
            out.append("    tempi: massimo %d ms fra due letture del FIFO (capienza ~1600 ms), overrun %d, apertura blocco massima %d ms, "
                       "blocchi confermati %d" % (s["gap_max_ms"], s["overrun"], s["apri_max_ms"], s["confermati"]))
    if esito.problemi:
        out.append("PROBLEMI (%d):" % len(esito.problemi))
        out.extend("  - " + p for p in esito.problemi)
    else:
        out.append("nessun problema rilevato")
    return "\n".join(out)
