#!/usr/bin/env python3
"""Host del ricevitore SwimTimer (firmware/ricevitore, ricevitore-0.1.5).

Legge i frame USB (firmware/ricevitore/PROTOCOLLO-USB.md), verifica CRC32 del frame, CRC32 del blocco e CRC16 di ogni
pagina .swr, salva il blocco nel file della tag come fa il display (<cartella>/<id 8 hex>/tag.swr + tag.idx, blocchi da 4096 B
in coda, indice "seq,offset,crc32,stato"), lo rilegge dal disco e solo allora risponde OK al ricevitore: e' l'OK che fa partire
la conferma alla tag. Senza OK la tag tiene il blocco. Funziona uguale su Windows e Linux (Raspberry Pi).

Uso:  python ricevitore_host.py --porta COM19 --cartella dati/
"""
import argparse
import os
import struct
import sys
import time
import zlib

import serial  # pyserial

SYNC = b"\xa5\x5a"
INTEST = 13
MAX_PAYLOAD = 4200
BLOCCO = 4096
PAGINA = 256

FR_BLOCCO, FR_STAT, FR_EVENTO, FR_HELLO = 0x01, 0x02, 0x03, 0x04
FR_OK, FR_ERR, FR_PRESENZA = 0x20, 0x21, 0x22
ERR_DISCO, ERR_SCRITTURA, ERR_DATI = 1, 2, 3
MIN_LIBERO = 50 * 1024 * 1024

LINK = {0: "non vista", 1: "vista", 2: "connessione", 3: "sicurezza", 4: "attiva"}
STATO = {0: "sonno", 1: "pronta", 2: "registra", 4: "piena", 5: "errore", 6: "sincronizza"}


# ---------- CRC ----------
def crc16_swr(dati, crc=0xFFFF):
    """CRC16-CCITT init 0xFFFF, come firmware/xiao-stream/swr_formato.h."""
    for b in dati:
        x = ((crc >> 8) ^ b) & 0xFF
        x ^= x >> 4
        crc = ((crc << 8) ^ (x << 12) ^ (x << 5) ^ x) & 0xFFFF
    return crc


def pagina_valida(p):
    """Pagina tutta 0xFF = vuota = valida; altrimenti CRC16 (byte 0..13 e 16..255, conferma a 0xFF) contro [14..15]."""
    if p.count(0xFF) == PAGINA:
        return True
    t = bytearray(p)
    if t[0] == 0xB1:  # intestazione di blocco: campo conferma considerato 0xFF
        if t[1] == 2:
            t[16] = 0xFF
        else:
            t[252:256] = b"\xff\xff\xff\xff"
    c = crc16_swr(t[:14])
    c = crc16_swr(t[16:], c)
    return c == struct.unpack_from("<H", p, 14)[0]


def blocco_valido(b):
    return all(pagina_valida(b[i * PAGINA:(i + 1) * PAGINA]) for i in range(BLOCCO // PAGINA))


# ---------- frame ----------
def codifica(tipo, id_tag, num, payload=b""):
    corpo = struct.pack("<BIIH", tipo, id_tag, num, len(payload)) + payload
    return SYNC + corpo + struct.pack("<I", zlib.crc32(corpo) & 0xFFFFFFFF)


class Parser:
    def __init__(self):
        self.buf = bytearray()
        self.crc_errati = 0

    def aggiungi(self, dati):
        self.buf += dati
        while True:
            i = self.buf.find(SYNC)
            if i < 0:
                del self.buf[:-1]  # puo' restare l'inizio di un sincronismo
                return
            if i:
                del self.buf[:i]
            if len(self.buf) < INTEST:
                return
            ln = struct.unpack_from("<H", self.buf, 11)[0]
            if ln > MAX_PAYLOAD:
                del self.buf[:1]
                continue
            tot = INTEST + ln + 4
            if len(self.buf) < tot:
                return
            corpo = bytes(self.buf[2:INTEST + ln])
            crc = struct.unpack_from("<I", self.buf, INTEST + ln)[0]
            if zlib.crc32(corpo) & 0xFFFFFFFF != crc:
                self.crc_errati += 1
                del self.buf[:1]  # riprende la ricerca dal byte successivo
                continue
            tipo, id_tag, num, _ = struct.unpack_from("<BIIH", corpo)
            payload = corpo[11:]
            del self.buf[:tot]
            yield tipo, id_tag, num, payload


# ---------- archivio ----------
class Archivio:
    def __init__(self, cartella):
        self.cartella = cartella
        self.visti = {}  # id -> {seq: crc} dei blocchi gia' scritti
        self.fh = {}  # (id, nome file) -> file aperto (aperti una volta sola: niente open/close per blocco)
        self.idx_sporco = False  # righe dell'indice scritte ma non ancora con fsync
        self.t = {"scrittura": 0.0, "rilettura": 0.0, "indice": 0.0}  # ms dell'ultimo salva()

    def apri(self, id_tag, nome, modo):
        k = (id_tag, nome)
        f = self.fh.get(k)
        if f is None or f.closed:
            f = self.fh[k] = open(os.path.join(self.percorso(id_tag), nome), modo)
        return f

    def sincronizza_indice(self):
        """fsync degli indici (al massimo ogni 2 s, dal ciclo principale): l'indice si puo' rifare dal .swr, il dato no."""
        if not self.idx_sporco:
            return
        self.idx_sporco = False
        for (id_tag, nome), f in self.fh.items():
            if nome == "tag.idx" and not f.closed:
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

    def percorso(self, id_tag):
        d = os.path.join(self.cartella, "%08x" % id_tag)
        os.makedirs(d, exist_ok=True)
        return d

    def carica(self, id_tag):
        if id_tag in self.visti:
            return self.visti[id_tag]
        m = {}
        idx = os.path.join(self.percorso(id_tag), "tag.idx")
        if os.path.exists(idx):
            with open(idx, "r", encoding="ascii", errors="replace") as f:
                for riga in f:
                    p = riga.strip().split(",")
                    if len(p) == 4 and p[3] == "scritto":
                        try:
                            m[int(p[0])] = int(p[2], 16)
                        except ValueError:
                            pass
        self.visti[id_tag] = m
        return m

    def salva(self, id_tag, seq, crc, blocco):
        """Scrive, rilegge dal disco e verifica il CRC32. Ritorna (esito, errore). esito True = OK da mandare.
        Regola: l'OK parte solo dopo flush+fsync del .swr e rilettura corretta del blocco. L'indice (seq,offset,crc) viene
        solo svuotato (flush) a ogni blocco e sincronizzato ogni 2 s: se si perdesse dopo un'interruzione il blocco resta comunque
        nel .swr (la tag lo ha gia' confermato), si perderebbe solo l'informazione per riconoscere un doppione."""
        try:
            noti = self.carica(id_tag)
            if seq in noti and noti[seq] == crc:
                return True, None  # doppione: solo conferma
            anomalia = seq in noti  # stesso seq con CRC diverso
            t0 = time.perf_counter()
            f = self.apri(id_tag, "tag.anomalia" if anomalia else "tag.swr", "ab+")
            off = f.seek(0, os.SEEK_END)
            f.write(blocco)
            f.flush()
            os.fsync(f.fileno())
            t1 = time.perf_counter()
            f.seek(off)
            riletto = f.read(BLOCCO)
            t2 = time.perf_counter()
            if len(riletto) != BLOCCO or zlib.crc32(riletto) & 0xFFFFFFFF != crc:
                return False, "rilettura diversa dalla scrittura"
            fi = self.apri(id_tag, "tag.idx", "a")
            fi.write("%d,%d,%08x,%s\n" % (seq, off, crc, "anomalia" if anomalia else "scritto"))
            fi.flush()
            self.idx_sporco = True
            t3 = time.perf_counter()
            self.t = {"scrittura": (t1 - t0) * 1000, "rilettura": (t2 - t1) * 1000, "indice": (t3 - t2) * 1000}
        except OSError as e:
            return False, "errore disco: %s" % e
        if not anomalia:
            noti[seq] = crc
        return True, ("anomalia: stesso seq con CRC diverso" if anomalia else None)


def spazio_libero(cartella):
    try:
        st = os.statvfs(cartella)
        return st.f_bavail * st.f_frsize
    except AttributeError:  # Windows
        import shutil
        return shutil.disk_usage(cartella).free


# ---------- principale ----------
class Host:
    def __init__(self, args):
        self.cartella = args.cartella
        os.makedirs(self.cartella, exist_ok=True)
        self.arch = Archivio(self.cartella)
        self.log = open(args.log or os.path.join(self.cartella, "ricevitore.log"), "a", encoding="utf-8", buffering=1)
        self.stat = {}  # id -> ultimo STAT decodificato
        self.salvati = {}
        self.ultima_riga = 0
        self.ultimo_sync_idx = 0
        self.misure = []  # (validazione, scrittura+fsync, rilettura, indice, totale) ms degli ultimi blocchi

    def scrivi_log(self, testo, stampa=False):
        riga = time.strftime("%Y-%m-%d %H:%M:%S ") + testo
        self.log.write(riga + "\n")
        if stampa:
            print(riga, flush=True)

    def blocco(self, ser, id_tag, seq, payload):
        if len(payload) != 10 + BLOCCO:
            self.scrivi_log("tag %08x seq %d: lunghezza blocco %d errata, scartato" % (id_tag, seq, len(payload)), True)
            return
        t_in = time.perf_counter()
        fisico, crc, millis_tag = struct.unpack_from("<HII", payload)
        dati = payload[10:]
        if zlib.crc32(dati) & 0xFFFFFFFF != crc:
            self.scrivi_log("tag %08x seq %d: CRC32 del blocco errato, nessun OK" % (id_tag, seq), True)
            return
        if not blocco_valido(dati):
            self.scrivi_log("tag %08x seq %d: CRC16 di una pagina errato, ERR" % (id_tag, seq), True)
            ser.write(codifica(FR_ERR, id_tag, seq, bytes([ERR_DATI])))
            return
        if spazio_libero(self.cartella) < MIN_LIBERO:
            self.scrivi_log("tag %08x seq %d: disco quasi pieno (< 50 MB), ERR" % (id_tag, seq), True)
            ser.write(codifica(FR_ERR, id_tag, seq, bytes([ERR_DISCO])))
            return
        t_val = time.perf_counter()
        ok, nota = self.arch.salva(id_tag, seq, crc, dati)
        if not ok:
            self.scrivi_log("tag %08x seq %d: %s, ERR" % (id_tag, seq, nota), True)
            ser.write(codifica(FR_ERR, id_tag, seq, bytes([ERR_SCRITTURA])))
            return
        if nota:
            self.scrivi_log("tag %08x seq %d: %s" % (id_tag, seq, nota), True)
        ser.write(codifica(FR_OK, id_tag, seq, struct.pack("<I", crc)))
        t_fine = time.perf_counter()
        a = self.arch.t
        self.misure.append(((t_val - t_in) * 1000, a["scrittura"], a["rilettura"], a["indice"], (t_fine - t_in) * 1000))
        if len(self.misure) >= 10:
            m = [sum(x[i] for x in self.misure) / len(self.misure) for i in range(5)]
            self.scrivi_log("host: medie su 10 blocchi, ms per blocco: validazione %.1f, scrittura+fsync %.1f, rilettura %.1f, "
                            "indice %.1f, totale (frame ricevuto -> OK scritto) %.1f" % tuple(m), True)
            self.misure = []
        self.salvati[id_tag] = self.salvati.get(id_tag, 0) + 1
        self.scrivi_log("tag %08x: blocco %d salvato (fisico %d, millis tag %d), OK inviato" % (id_tag, seq, fisico, millis_tag))

    def stat_rx(self, id_tag, payload):
        if len(payload) < 33:
            return
        (slot, link, rssi, stato, batt, pct, err, attesa, bps, ric, conf, scart, msavv, ultseq, eta) = struct.unpack(
            "<BBbBBBBHIIIHIIH", payload[:33])
        self.stat[id_tag] = dict(slot=slot, link=link, rssi=rssi, stato=stato, batt=batt * 20, pct=pct, err=err, attesa=attesa,
                                 bps=bps, ric=ric, conf=conf, scart=scart, msavv=msavv, ultseq=ultseq, eta=eta)

    def riga_stat(self):
        if not self.stat:
            return "nessuna tag vista"
        parti = []
        for id_tag, s in sorted(self.stat.items()):
            parti.append("%08x %s %s RSSI %d dBm %.1f KB/s | in memoria %d ric %d conf %d salvati %d scart %d | batt %d mV mem %d%% | avv->coll %s" % (
                id_tag, LINK.get(s["link"], "?"), STATO.get(s["stato"], "?"), s["rssi"], s["bps"] / 1024.0, s["attesa"], s["ric"],
                s["conf"], self.salvati.get(id_tag, 0), s["scart"], s["batt"], s["pct"],
                ("%d ms" % s["msavv"]) if s["msavv"] else "-"))
        return " || ".join(parti)

    def gira(self, ser):
        p = Parser()
        ultima_presenza = 0
        while True:
            ora = time.time()
            if ora - ultima_presenza >= 1.0:
                ser.write(codifica(FR_PRESENZA, 0, 0))
                ultima_presenza = ora
            if ora - self.ultimo_sync_idx >= 2.0:
                self.ultimo_sync_idx = ora
                self.arch.sincronizza_indice()
            dati = ser.read(max(1, ser.in_waiting))
            for tipo, id_tag, num, payload in p.aggiungi(dati) if dati else ():
                if tipo == FR_BLOCCO:
                    self.blocco(ser, id_tag, num, payload)
                elif tipo == FR_STAT:
                    self.stat_rx(id_tag, payload)
                elif tipo == FR_EVENTO:
                    self.scrivi_log("EVENTO tag %08x num %d: %s" % (id_tag, num, payload.decode("ascii", "replace")), True)
                elif tipo == FR_HELLO:
                    if not getattr(self, "hello", False):
                        self.scrivi_log("ricevitore: %s" % payload.decode("ascii", "replace"), True)
                        self.hello = True
            if ora - self.ultima_riga >= 1.0:
                self.ultima_riga = ora
                riga = self.riga_stat() + ("  [frame con CRC errato: %d]" % p.crc_errati if p.crc_errati else "")
                self.scrivi_log(riga, True)


def main():
    ap = argparse.ArgumentParser(description="Host del ricevitore SwimTimer")
    ap.add_argument("--porta", required=True, help="porta seriale (COM19, /dev/ttyACM0)")
    ap.add_argument("--cartella", default="dati", help="cartella di destinazione (default: dati/)")
    ap.add_argument("--log", help="file di log (default: <cartella>/ricevitore.log)")
    args = ap.parse_args()
    host = Host(args)
    while True:
        try:
            with serial.Serial(args.porta, 115200, timeout=0.05, write_timeout=2) as ser:
                ser.dtr = True
                host.scrivi_log("porta %s aperta" % args.porta, True)
                host.hello = False
                host.gira(ser)
        except (serial.SerialException, OSError) as e:
            host.scrivi_log("porta seriale: %s; nuovo tentativo fra 2 s" % e, True)
            time.sleep(2)
        except KeyboardInterrupt:
            host.scrivi_log("interrotto dall'utente", True)
            return 0


if __name__ == "__main__":
    sys.exit(main())
