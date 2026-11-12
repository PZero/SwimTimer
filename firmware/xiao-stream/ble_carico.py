"""Misura degli stalli di diarioFlush/regScrivi e del servizio del FIFO con un CLIENT BLE COLLEGATO (bleak).

Si collega alla tag (modalita' normale su USB, build di prova -DPROVE_GUASTI=1), abilita le notifiche (log 0005, stato 0003, stato sync
0104) e manda sulla caratteristica COMANDI 0004 `PROVA_FIFO,<secondi>,5` (modo 6 = con la regola del ciclo di registrazione: niente flash finche' c'e' un client collegato): la tag fa girare il servizio del FIFO come in registrazione (un
giro ogni 20 ms), con un diarioFlush ogni 10 s e un regScrivi ogni 60 s su file di prova, e alla fine risponde con due righe K:
  n.. ok.. sw.. dis.. sos.. rc.. bn..          campioni, plausibili, scambiati, riallineamenti, sospetti, ricerche, ricerche con s != 0
  gmax<ms> ovr<n> dia<ms> reg<ms>            intervallo massimo fra due servizi del FIFO, overrun, massimo diarioFlush, massimo regScrivi
Criterio (revisione): gmax < 1000 ms e ovr 0.
Limite: la sincronizzazione vera (il display che scarica i blocchi) non si puo' riprodurre dal PC (CONTROLLO richiede il bonding cifrato);
con questo client c'e' una connessione attiva con gli eventi radio a 7,5-15 ms, ma senza il traffico di notifiche dei blocchi.

Uso:  python ble_carico.py [--secondi 180] [--nome auto]     (richiede: pip install bleak)
"""
import argparse
import asyncio
import time

UUID_COMANDI = "7a1e0004-5b1d-4c8e-9f3a-1d2c3b4a5e60"
UUID_RISPOSTE = "7a1e0005-5b1d-4c8e-9f3a-1d2c3b4a5e60"
UUID_STATO = "7a1e0003-5b1d-4c8e-9f3a-1d2c3b4a5e60"
UUID_SYNC_STATO = "7a1e0104-5b1d-4c8e-9f3a-1d2c3b4a5e60"
UUID_SERVIZIO = "7a1e0001-5b1d-4c8e-9f3a-1d2c3b4a5e60"


async def main(args):
    from bleak import BleakClient, BleakScanner
    dev = await BleakScanner.find_device_by_filter(
        lambda d, ad: (args.nome == "auto" and UUID_SERVIZIO in [u.lower() for u in (ad.service_uuids or [])])
        or (args.nome != "auto" and ((d.name or ad.local_name or "").startswith(args.nome) or d.address.upper() == args.nome.upper())),
        timeout=15)
    if dev is None:
        raise SystemExit("tag non trovata")
    risposte = []
    n_notifiche = {"0005": 0, "0003": 0, "0104": 0}

    def cb_risposte(_, d):
        n_notifiche["0005"] += 1
        t = bytes(d).decode("utf-8", "replace")
        if t.startswith("K"):
            risposte.append(t[1:])
            print("  <- " + t[1:], flush=True)

    async with BleakClient(dev) as c:
        await c.start_notify(UUID_RISPOSTE, cb_risposte)
        for u, k in ((UUID_STATO, "0003"), (UUID_SYNC_STATO, "0104")):
            try:
                await c.start_notify(u, lambda _, d, k=k: n_notifiche.__setitem__(k, n_notifiche[k] + 1))
            except Exception as e:
                print("notifiche %s non abilitate: %s" % (k, e))
        print("collegato a %s, avvio PROVA_FIFO,%d,%d" % (dev.address, args.secondi, args.modo), flush=True)
        t0 = time.time()
        await c.write_gatt_char(UUID_COMANDI, ("PROVA_FIFO,%d,%d" % (args.secondi, args.modo)).encode(), response=False)
        while len(risposte) < 2 and time.time() - t0 < args.secondi + 90:      # le due righe K finali
            await asyncio.sleep(0.5)
        print("notifiche ricevute durante la prova:", n_notifiche)
        print("durata %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--secondi", type=int, default=180)
    ap.add_argument("--nome", default="auto")
    ap.add_argument("--modo", type=int, default=5, help="5 = stalli grezzi (flash anche con il client collegato); 6 = con la regola del ciclo (niente flash con un client collegato)")
    asyncio.run(main(ap.parse_args()))
