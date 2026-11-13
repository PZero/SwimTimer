#!/usr/bin/env python3
"""Pannello della stazione SwimTimer: serve pannello.html e il JSON di stato scritto da ricevitore_host.py (--stato).

Solo libreria standard. Uso:
    python3 pannello.py --stato /run/swimtimer/stato.json --porta 8080
La pagina chiede /stato.json ogni secondo. Mostra solo contatori e diagnostica, mai i dati di nuoto.
"""
import argparse
import http.server
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
_nomi = {"mtime": None, "dati": {}}


def leggi_nomi(percorso):
    """nomi.txt: una riga per tag "<id esadecimale> <nome>", '#' = commento. Riletto solo se cambia.
    Contiene nomi di persone: resta solo sul Pi, mai nel repository."""
    try:
        mt = os.path.getmtime(percorso)
    except OSError:
        return {}
    if mt != _nomi["mtime"]:
        d = {}
        with open(percorso, encoding="utf-8") as f:
            for riga in f:
                riga = riga.split("#", 1)[0].strip()
                if riga:
                    id_tag, _, nome = riga.partition(" ")
                    d[id_tag.lower()] = nome.strip()[:24]
        _nomi.update(mtime=mt, dati=d)
    return _nomi["dati"]


def crea_gestore(file_stato, file_nomi):
    class Gestore(http.server.BaseHTTPRequestHandler):
        def invia(self, codice, tipo, corpo):
            self.send_response(codice)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            percorso = self.path.split("?", 1)[0]
            if percorso in ("/", "/index.html", "/pannello.html"):
                with open(os.path.join(QUI, "pannello.html"), "rb") as f:
                    self.invia(200, "text/html; charset=utf-8", f.read())
            elif percorso == "/stato.json":
                try:
                    with open(file_stato, "rb") as f:
                        corpo = f.read()
                    nomi = leggi_nomi(file_nomi)
                    if nomi:   # aggiunge "nome" a ogni tag conosciuta
                        s = json.loads(corpo)
                        for t in s.get("tag", []):
                            t["nome"] = nomi.get(t.get("id", ""), "")
                        corpo = json.dumps(s, ensure_ascii=False).encode("utf-8")
                    self.invia(200, "application/json; charset=utf-8", corpo)
                except (OSError, ValueError):
                    self.invia(503, "application/json; charset=utf-8", b'{"errore": "host non avviato"}')
            else:
                self.invia(404, "text/plain; charset=utf-8", b"non trovato")

        def log_message(self, *a):  # niente righe per ogni richiesta (una al secondo)
            pass

    return Gestore


def main():
    ap = argparse.ArgumentParser(description="Pannello HTML della stazione SwimTimer")
    ap.add_argument("--stato", default="/run/swimtimer/stato.json", help="JSON scritto da ricevitore_host.py --stato")
    ap.add_argument("--nomi", default="/home/swim/swimtimer-dati/nomi.txt", help="nomi delle tag: righe '<id> <nome>'")
    ap.add_argument("--indirizzo", default="0.0.0.0", help="0.0.0.0 = visibile anche dal telefono in rete; 127.0.0.1 = solo locale")
    ap.add_argument("--porta", type=int, default=8080)
    a = ap.parse_args()
    srv = http.server.ThreadingHTTPServer((a.indirizzo, a.porta), crea_gestore(a.stato, a.nomi))
    print("pannello su http://%s:%d (stato: %s)" % (a.indirizzo, a.porta, a.stato), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
