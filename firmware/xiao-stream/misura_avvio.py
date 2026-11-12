"""Misura di T_AVVIO: il tempo fra il reset della tag e millis() = 0 del nuovo avvio (bootloader compreso).

Serve al tempo di sessione continuo dopo le riprese (xiao-stream.ino, tempoAvvio(); costante T_AVVIO_MS). Solo PC, niente display.
Richiede il firmware compilato con -DPROVE_GUASTI=1 (comandi PROVA_TEMPO, PROVA_AVVIO, PROVA_CRASH, PROVA_BLOCCO).

Metodo (per ogni ripetizione):
  1. PRIMA del guasto: 20 interrogazioni PROVA_TEMPO (la tag risponde con il suo millis). Per ognuna: t_pc = meta' fra invio e risposta,
     offset = t_pc - millis/1000. Si tiene l'offset della risposta con il tempo di andata e ritorno MINIMO (la piu' vicina al vero).
  2. Si manda PROVA_CRASH (HardFault) o PROVA_BLOCCO (watchdog dopo ~8 s). I gestori salvano in RAM il millis() dell'istante del reset.
  3. DOPO il riavvio: ci si riconnette, altre 20 interrogazioni -> offset_dopo (tempo PC del nuovo millis = 0).
     PROVA_AVVIO restituisce l'istante del reset salvato (r<ms>, origine o1 = gestore).
  4. t_reset_pc = offset_prima + r/1000;  T_AVVIO = offset_dopo - t_reset_pc.
Con l'USB seriale il tempo di andata e ritorno e' ~1-2 ms; con il BLE varia (decine di ms): per questo si usa il minimo di 20 prove.

Uso:
  python misura_avvio.py --seriale COM15 --guasto crash -n 10
  python misura_avvio.py --seriale COM15 --guasto blocco -n 5
  python misura_avvio.py --ble ST-0689 --guasto crash -n 10      (tag a batteria in registrazione; richiede: pip install bleak)
Stampa media, minimo e massimo di T_AVVIO e l'elenco; --csv file.csv salva le misure.
"""
import argparse
import asyncio
import re
import statistics
import sys
import time

UUID_COMANDI = "7a1e0004-5b1d-4c8e-9f3a-1d2c3b4a5e60"
UUID_RISPOSTE = "7a1e0005-5b1d-4c8e-9f3a-1d2c3b4a5e60"
N_SYNC = 20


def stima(campioni):
    """campioni: lista di (t_invio, t_risposta, millis). Ritorna (offset, rtt_min): offset = tempo PC del millis 0 della tag."""
    migliore = min(campioni, key=lambda c: c[1] - c[0])
    t_pc = (migliore[0] + migliore[1]) / 2.0
    return t_pc - migliore[2] / 1000.0, migliore[1] - migliore[0]


def riassunto(valori, nome):
    if not valori:
        print("%s: nessuna misura" % nome)
        return
    print("%s: n=%d  media %.1f ms  min %.1f ms  max %.1f ms  (dev. std %.1f ms)" % (
        nome, len(valori), statistics.mean(valori), min(valori), max(valori),
        statistics.pstdev(valori) if len(valori) > 1 else 0.0))


# ------------------------------------------------------------------ seriale USB
class Seriale:
    def __init__(self, porta):
        self.porta = porta
        self.s = None

    def apri(self, timeout=40):
        import serial
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                self.s = serial.Serial(self.porta, 115200, timeout=0.05)
                self.s.dtr = True
                return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("porta %s non disponibile" % self.porta)

    def chiudi(self):
        try:
            self.s.close()
        except Exception:
            pass

    def _riga_con(self, prefisso, timeout=2.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            l = self.s.readline().decode("utf-8", "replace").strip()
            if l.startswith(prefisso):
                return l, time.perf_counter()
        return None, None

    def sync(self):
        campioni = []
        tent = 0
        while len(campioni) < N_SYNC and tent < 400:
            tent += 1
            try:
                self.s.reset_input_buffer()
                t0 = time.perf_counter()
                self.s.write(b"PROVA_TEMPO\n")
                l, t1 = self._riga_con("TEMPO ")
            except Exception:                                    # la porta si sta ancora enumerando dopo il riavvio
                self.riconnetti()
                campioni = []
                continue
            if l:
                campioni.append((t0, t1, int(l.split()[1])))
        if len(campioni) < N_SYNC:
            raise RuntimeError("risposte insufficienti")
        return stima(campioni)

    def avvio(self):
        self.s.reset_input_buffer()
        self.s.write(b"PROVA_AVVIO\n")
        l, _ = self._riga_con("AVVIO ")
        return l

    def invia(self, cmd):
        self.s.write((cmd + "\n").encode())

    def riconnetti(self):
        self.chiudi()
        time.sleep(1.0)
        self.apri()


# ------------------------------------------------------------------ BLE (bleak)
class Ble:
    def __init__(self, nome):
        self.nome = nome
        self.client = None
        self.coda = None

    async def apri(self, timeout=60):
        from bleak import BleakClient, BleakScanner
        t0 = time.time()
        while time.time() - t0 < timeout:
            dev = await BleakScanner.find_device_by_filter(lambda d, ad: (self.nome == "auto" and "7a1e0001-5b1d-4c8e-9f3a-1d2c3b4a5e60" in [u.lower() for u in (ad.service_uuids or [])]) or (self.nome != "auto" and ((d.name or ad.local_name or "").startswith(self.nome) or d.address.upper() == self.nome.upper())), timeout=5)
            if dev is None:
                continue
            try:
                self.client = BleakClient(dev)
                await self.client.connect()
                self.coda = asyncio.Queue()

                def cb(_, dati):
                    self.coda.put_nowait((time.perf_counter(), bytes(dati)))
                await self.client.start_notify(UUID_RISPOSTE, cb)
                return
            except Exception:
                await asyncio.sleep(0.5)
        raise RuntimeError("tag %s non trovata" % self.nome)

    async def chiudi(self):
        try:
            await self.client.disconnect()
        except Exception:
            pass

    async def _cmd(self, cmd, prefisso, timeout=2.0):
        while not self.coda.empty():
            self.coda.get_nowait()
        t0 = time.perf_counter()
        await self.client.write_gatt_char(UUID_COMANDI, cmd.encode(), response=False)
        fine = t0 + timeout
        while time.perf_counter() < fine:
            try:
                t1, d = await asyncio.wait_for(self.coda.get(), timeout=max(0.01, fine - time.perf_counter()))
            except asyncio.TimeoutError:
                break
            testo = d.decode("utf-8", "replace")
            if testo.startswith(prefisso):                       # le righe di log arrivano come 'G...': si ignorano
                return t0, t1, testo
        return t0, None, None

    async def sync(self):
        campioni = []
        tent = 0
        while len(campioni) < N_SYNC and tent < 200:
            tent += 1
            t0, t1, testo = await self._cmd("PROVA_TEMPO", "Kt")
            if testo:
                campioni.append((t0, t1, int(testo[2:])))
        if len(campioni) < N_SYNC:
            raise RuntimeError("risposte insufficienti")
        return stima(campioni)

    async def avvio(self):
        _, _, testo = await self._cmd("PROVA_AVVIO", "Kav")
        return testo

    async def invia(self, cmd):
        await self.client.write_gatt_char(UUID_COMANDI, cmd.encode(), response=False)


def analizza_avvio(testo):
    """'av n<avvii> o<origine> r<reset ms> s<scarto> m<margine> g<gestore>' (o con prefisso 'AVVIO ')"""
    m = re.search(r"av n(\d+) o(\d+) r(\d+) s(\d+) m(\d+) g(\d)", testo or "")
    if not m:
        return None
    return dict(avvii=int(m.group(1)), origine=int(m.group(2)), reset_ms=int(m.group(3)), scarto=int(m.group(4)), margine=int(m.group(5)),
                gestore=int(m.group(6)))


def misura_seriale(args):
    s = Seriale(args.seriale)
    s.apri()
    risultati = []
    for i in range(args.n):
        off_prima, rtt1 = s.sync()
        s.invia("PROVA_CRASH" if args.guasto == "crash" else "PROVA_BLOCCO")
        s.riconnetti()
        off_dopo, rtt2 = s.sync()
        av = analizza_avvio(s.avvio())
        if not av or not av["gestore"]:
            print("%2d: avvio non valido o istante del reset non salvato da un gestore: %s" % (i + 1, av))
            continue
        t_reset = off_prima + av["reset_ms"] / 1000.0
        t_avvio = (off_dopo - t_reset) * 1000.0
        risultati.append(t_avvio)
        print("%2d: T_AVVIO = %.1f ms  (rtt min %.1f / %.1f ms)" % (i + 1, t_avvio, rtt1 * 1000, rtt2 * 1000))
    s.chiudi()
    return risultati


async def misura_ble(args):
    b = Ble(args.ble)
    await b.apri()
    risultati = []
    for i in range(args.n):
        off_prima, rtt1 = await b.sync()
        await b.invia("PROVA_CRASH" if args.guasto == "crash" else "PROVA_BLOCCO")
        await b.chiudi()
        await asyncio.sleep(1.0)
        await b.apri()
        off_dopo, rtt2 = await b.sync()
        av = analizza_avvio(await b.avvio())
        if not av or not av["gestore"]:
            print("%2d: avvio non valido o istante del reset non salvato da un gestore: %s" % (i + 1, av))
            continue
        t_reset = off_prima + av["reset_ms"] / 1000.0
        t_avvio = (off_dopo - t_reset) * 1000.0
        risultati.append(t_avvio)
        print("%2d: T_AVVIO = %.1f ms  (rtt min %.1f / %.1f ms)" % (i + 1, t_avvio, rtt1 * 1000, rtt2 * 1000))
    await b.chiudi()
    return risultati


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seriale", help="porta seriale USB (es. COM15)")
    g.add_argument("--ble", help="nome (prefisso) o indirizzo BLE della tag")
    ap.add_argument("--guasto", choices=["crash", "blocco"], default="crash")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--csv")
    args = ap.parse_args()
    r = misura_seriale(args) if args.seriale else asyncio.run(misura_ble(args))
    riassunto(r, "T_AVVIO %s (%s)" % (args.guasto, "USB seriale" if args.seriale else "BLE"))
    if args.csv:
        with open(args.csv, "w") as f:
            f.write("t_avvio_ms\n" + "\n".join("%.1f" % v for v in r) + "\n")


if __name__ == "__main__":
    main()
