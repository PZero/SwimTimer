#!/usr/bin/env python3
"""SwimTimer - scarico e conversione delle registrazioni in vasca della XIAO (firmware 0.5.0).

La tag va collegata via USB (modalita' normale): la registrazione si scarica dalla seriale con il comando DUMP.

    python scarica.py porte                       elenca le porte seriali
    python scarica.py mem COM5                    pagine usate / totali
    python scarica.py scarica COM5                scarica in registrazioni/AAAAmmdd_HHMMSS.swr e converte in CSV
    python scarica.py converti file.swr           converte un .swr gia' scaricato (CSV accanto al file)
    python scarica.py azzera COM5                 cancella la memoria della tag (chiede conferma)

Servono Python 3 e pyserial (pip install pyserial). I file .swr e .csv sono dati di salute: non vanno nel repository
(sono nel .gitignore, cartella registrazioni/).
"""
import argparse
import datetime
import os
import sys
import time

import swr

BAUD = 115200


def _apri(porta):
    import serial  # import qui: i test non richiedono pyserial
    s = serial.Serial(porta, BAUD, timeout=1)
    s.dtr = True   # la tag rileva la porta aperta (niente sospensione automatica)
    return s


def _comando(ser, testo, attesa_riga=None, timeout=15):
    """Svuota l'ingresso, invia il comando e legge righe finche' una inizia con uno dei prefissi di `attesa_riga`."""
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(b"\n" + testo.encode() + b"\n")
    t0 = time.time()
    while time.time() - t0 < timeout:
        riga = ser.readline().decode("ascii", "replace").strip()
        if attesa_riga and any(riga.startswith(p) for p in attesa_riga):
            return riga
    raise TimeoutError("nessuna risposta a %s" % testo)


def leggi_dump(ser, avanzamento=None, timeout_riga=15):
    """Invia DUMP e ritorna i byte. Protocollo: formato 1 'SWR1 <n>' + n pagine da 256 byte; formato 2 (0.6.0) 'SWR2 <n>' +
    n blocchi da 4096 byte; poi riga vuota e 'END <n>'. Eventuali righe di log prima dell'intestazione vengono ignorate."""
    riga = _comando(ser, "DUMP", ["SWR1 ", "SWR2 "], timeout_riga)
    n = int(riga.split()[1])
    totale = n * (swr.BLOCCO if riga.startswith("SWR2") else swr.PAGINA)
    buf = bytearray()
    ultimo_dato = time.time()
    while len(buf) < totale:
        pezzo = ser.read(min(4096, totale - len(buf)))
        if pezzo:
            buf += pezzo
            ultimo_dato = time.time()
            if avanzamento:
                avanzamento(len(buf), totale)
        elif time.time() - ultimo_dato > 10:
            raise TimeoutError("scarico interrotto a %d di %d byte" % (len(buf), totale))
    coda = b""
    t0 = time.time()
    while b"END" not in coda and time.time() - t0 < 5:
        coda += ser.read(64)
    if ("END %d" % n).encode() not in coda:
        print("attenzione: manca la riga finale END %d" % n, file=sys.stderr)
    return bytes(buf)


def _stampa_avanzamento(fatti, totale):
    sys.stderr.write("\r%6.1f%%  %d / %d byte" % (100.0 * fatti / totale, fatti, totale))
    sys.stderr.flush()
    if fatti >= totale:
        sys.stderr.write("\n")


def converti(percorso_swr, percorso_csv=None, grezzo=False):
    with open(percorso_swr, "rb") as f:
        immagine = f.read()
    es = swr.decodifica(immagine)
    if percorso_csv is None:
        percorso_csv = os.path.splitext(percorso_swr)[0] + ".csv"
    n = swr.scrivi_csv(es, percorso_csv, grezzo)
    print(swr.riassunto(es))
    print("CSV: %s (%d campioni)" % (percorso_csv, n))
    return es


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("porte")
    for nome in ("mem", "scarica", "azzera"):
        p = sp.add_parser(nome)
        p.add_argument("porta")
        if nome == "scarica":
            p.add_argument("-o", "--uscita", help="file .swr di destinazione")
            p.add_argument("--grezzo", action="store_true", help="CSV con valori grezzi (LSB) invece di g e dps")
        if nome == "azzera":
            p.add_argument("--si", action="store_true", help="non chiedere conferma")
    p = sp.add_parser("converti")
    p.add_argument("file")
    p.add_argument("-o", "--uscita", help="file CSV di destinazione")
    p.add_argument("--grezzo", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "porte":
        from serial.tools import list_ports
        for p in list_ports.comports():
            print(p.device, "-", p.description)
    elif a.cmd == "converti":
        converti(a.file, a.uscita, a.grezzo)
    elif a.cmd == "mem":
        with _apri(a.porta) as ser:
            print(_comando(ser, "MEM", ["K mem", "X"]))
    elif a.cmd == "azzera":
        if not a.si and input("Cancellare TUTTA la memoria della tag? Scrivi SI: ").strip() != "SI":
            print("annullato")
            return 1
        with _apri(a.porta) as ser:
            print(_comando(ser, "ERASE", ["K erase", "X"], timeout=90))
    elif a.cmd == "scarica":
        with _apri(a.porta) as ser:
            dati = leggi_dump(ser, _stampa_avanzamento)
        if not dati:
            print("memoria vuota")
            return 0
        percorso = a.uscita
        if not percorso:
            os.makedirs("registrazioni", exist_ok=True)
            percorso = os.path.join("registrazioni", datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".swr")
        with open(percorso, "wb") as f:
            f.write(dati)
        print("salvato %s (%d byte)" % (percorso, len(dati)))
        converti(percorso, grezzo=a.grezzo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
