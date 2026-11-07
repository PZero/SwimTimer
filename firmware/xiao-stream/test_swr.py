"""Test del formato .swr e dello scarico (python -m unittest test_swr). Solo dati INVENTATI (generatore con seme fisso)."""
import csv
import os
import random
import struct
import tempfile
import unittest

import scarica
import swr


def campioni_inventati(n, seme, salti=True):
    """Camminata casuale su 6 assi (acc ~ 1 g sul Z, giro ~ 0) con variazioni piccole, qualche salto grande,
    valori ai limiti dell'int16 e differenze esattamente ai bordi dell'intervallo delta (127, 128)."""
    r = random.Random(seme)
    cur = [10, -20, 2048, 5, -3, 1]
    out = []
    for i in range(n):
        for k in range(6):
            cur[k] += r.randint(-9, 9)
        if salti and i % 37 == 5:
            cur[r.randrange(6)] += r.choice([-3000, 2500, 128, -128, 127, -127])   # fuori scala o ai bordi
        if salti and i == 11:
            cur = [32767, -32768, 32767, -32768, 32767, -32768]                     # estremi dell'int16
        if salti and i == 12:
            cur = [-32768, 32767, 0, 0, 0, 0]
        cur = [max(-32768, min(32767, v)) for v in cur]
        out.append(tuple(cur))
    return out


def costruisci(segmenti, mv=3900, jitter=0, seme=1):
    """Costruisce un'immagine: per ogni segmento (lista di campioni, chiudere?) pagina segmento, pagine dati, chiusura.
    Il tempo e' 4,8 ms per campione piu' un rumore (jitter) come nel firmware. Ritorna (immagine, attesi per segmento)."""
    r = random.Random(seme)
    img = bytearray()
    p = 0
    for idx, (camp, chiudi) in enumerate(segmenti):
        img += swr.pagina_segmento(p, idx, millis=0, mv=mv)
        p += 1
        cod = swr.Codificatore()
        n_seg_pagine = 0
        flag = swr.FLAG_PRIMA
        base = 1000.0 + 100000 * idx
        for i, s in enumerate(camp):
            if cod.nc and not cod.sta(s):
                img += cod.chiudi(p, idx, mv, 22, flag)
                flag = 0
                p += 1
                n_seg_pagine += 1
                cod.azzera()
            t = int(round(base + i * swr.MS_PER_CAMPIONE + (r.uniform(-jitter, jitter) if jitter else 0)))
            cod.aggiungi(s, t)
        if cod.nc:
            img += cod.chiudi(p, idx, mv, 22, flag)
            p += 1
            n_seg_pagine += 1
        if chiudi:
            img += swr.pagina_chiusura(p, idx, 1, len(camp), n_seg_pagine)
            p += 1
    return bytes(img), p


class TestFormato(unittest.TestCase):
    def test_crc_valore_noto(self):
        self.assertEqual(swr.crc16(b"123456789"), 0x29B1)   # CRC-16/CCITT-FALSE

    def test_roundtrip_bit_per_bit(self):
        camp = campioni_inventati(5000, seme=7)
        img, _ = costruisci([(camp, True)])
        es = swr.decodifica(img)
        self.assertEqual(es.problemi, [])
        letti = [s for pg in es.pagine_dati for s in pg["campioni"]]
        self.assertEqual(len(letti), len(camp))
        self.assertEqual(letti, camp)                      # uguaglianza esatta, campione per campione
        self.assertTrue(es.segmenti[0]["chiuso"])
        self.assertEqual(es.segmenti[0]["campioni"], len(camp))

    def test_ogni_pagina_si_decodifica_da_sola(self):
        camp = campioni_inventati(3000, seme=3)
        img, _ = costruisci([(camp, True)])
        es = swr.decodifica(img)
        atteso = list(camp)
        for pg in es.pagine_dati:
            pag = img[pg["pagina"] * 256:(pg["pagina"] + 1) * 256]
            parte = swr.decodifica_dati(pag)               # solo questa pagina, nessun contesto
            self.assertEqual(parte, atteso[:len(parte)])
            atteso = atteso[len(parte):]
        self.assertEqual(atteso, [])

    def test_bordi_delta_ed_escape(self):
        base = (0, 0, 0, 0, 0, 0)
        for d, escape in [(127, False), (-127, False), (128, True), (-128, True)]:
            cod = swr.Codificatore()
            cod.aggiungi(base, 0)
            s = (d, 0, 0, 0, 0, 0)
            cod.aggiungi(s, 5)
            self.assertEqual(cod.pos, 16 + 12 + (13 if escape else 6), "delta %d" % d)
            self.assertEqual(swr.decodifica_dati(cod.chiudi(0, 0, 0, 0, 0))[1], s)

    def test_compressione_su_dati_regolari(self):
        camp = campioni_inventati(4000, seme=11, salti=False)
        img, n_pag = costruisci([(camp, False)])
        byte_per_campione = (n_pag - 1) * 256 / len(camp)
        self.assertLess(byte_per_campione, 8.0)            # contro i 12 B grezzi
        self.assertGreater(len(camp) / ((n_pag - 1) * 20.0 + 1), 1.0)   # piu' di 20 campioni per pagina

    def test_piu_segmenti_e_segmento_senza_chiusura(self):
        a, b = campioni_inventati(900, 1), campioni_inventati(700, 2)
        img, _ = costruisci([(a, True), (b, False)])
        es = swr.decodifica(img)
        self.assertEqual(sorted(es.segmenti), [0, 1])
        self.assertTrue(es.segmenti[0]["chiuso"])
        self.assertFalse(es.segmenti[1]["chiuso"])
        self.assertTrue(any("segmento 1 senza chiusura" in p for p in es.problemi))
        per = {0: [], 1: []}
        for pg in es.pagine_dati:
            per[pg["seg"]] += pg["campioni"]
        self.assertEqual(per[0], a)
        self.assertEqual(per[1], b)

    def test_pagina_corrotta_segnalata_e_le_altre_restano(self):
        camp = campioni_inventati(2000, seme=5)
        img, _ = costruisci([(camp, True)])
        es0 = swr.decodifica(img)
        vittima = es0.pagine_dati[3]["pagina"]
        guasta = bytearray(img)
        guasta[vittima * 256 + 100] ^= 0x04                # un solo bit
        es = swr.decodifica(bytes(guasta))
        self.assertEqual(es.pagine_corrotte, [vittima])
        self.assertTrue(any("CRC" in p for p in es.problemi))
        perse = len(es0.pagine_dati[3]["campioni"])
        self.assertEqual(sum(len(p["campioni"]) for p in es.pagine_dati), len(camp) - perse)

    def test_file_troncato_e_pagine_libere(self):
        camp = campioni_inventati(500, seme=9)
        img, _ = costruisci([(camp, True)])
        es = swr.decodifica(img + b"\xff" * 256 * 5)       # pagine cancellate in coda: ignorate
        self.assertEqual(es.problemi, [])
        es = swr.decodifica(img[:-100])
        self.assertTrue(any("troncato" in p for p in es.problemi))

    def test_tempo_da_millis_con_rumore(self):
        camp = campioni_inventati(4000, seme=4, salti=False)
        img, _ = costruisci([(camp, True)], jitter=5.0)   # +-5 ms di rumore sul millis di ogni pagina
        es = swr.decodifica(img)
        rr = list(swr.righe(es))
        self.assertEqual(len(rr), len(camp))
        self.assertAlmostEqual(rr[0][3], 0.0, places=6)
        for a, b in zip(rr, rr[1:]):
            self.assertGreater(b[3], a[3])
        passo = (rr[-1][3] - rr[0][3]) / (len(rr) - 1)
        self.assertAlmostEqual(passo, swr.MS_PER_CAMPIONE / 1000.0, delta=0.0002)   # 0,2 ms su 4,8 ms

    def test_csv(self):
        camp = [(2048, 0, 0, 100, -200, 300)] * 3 + campioni_inventati(40, 8)
        img, _ = costruisci([(camp, True)], mv=3777)
        es = swr.decodifica(img)
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "prova.csv")
            n = swr.scrivi_csv(es, f)
            self.assertEqual(n, len(camp))
            with open(f, encoding="utf-8") as fh:
                righe = list(csv.DictReader(fh))
            self.assertEqual(righe[0]["mV"], "3777")
            self.assertAlmostEqual(float(righe[0]["ax_g"]), 2048 * 488e-6, places=4)
            self.assertAlmostEqual(float(righe[0]["gz_dps"]), 300 * 0.035, places=2)
            self.assertAlmostEqual(float(righe[0]["gy_dps"]), -200 * 0.035, places=2)
            swr.scrivi_csv(es, f, grezzo=True)
            with open(f, encoding="utf-8") as fh:
                g = list(csv.DictReader(fh))
            self.assertEqual([int(g[2][k]) for k in ("ax", "ay", "az", "gx", "gy", "gz")], list(camp[2]))


class SerialeFinta:
    """Simula la porta: rumore di log, poi SWR1 + pagine + END."""
    def __init__(self, dati):
        n = len(dati) // 256
        self.rx = bytearray(b"12.3 bat 3900 mV usb 1 carica 0\nacc 1 2 3 | gyro 4 5 6\n")
        self.dati = dati
        self.dopo = b"SWR1 %d\n" % n + dati + b"\nEND %d\n" % n
        self.inviato = False
        self.scritto = b""

    def reset_input_buffer(self):
        self.rx = bytearray()

    def write(self, b):
        self.scritto += b
        if b"DUMP" in b:
            self.rx += self.dopo

    def readline(self):
        i = self.rx.find(b"\n")
        if i < 0:
            return b""
        riga = bytes(self.rx[:i + 1])
        del self.rx[:i + 1]
        return riga

    def read(self, n):
        pezzo = bytes(self.rx[:n])
        del self.rx[:n]
        return pezzo


class TestScarico(unittest.TestCase):
    def test_dump_completo(self):
        camp = campioni_inventati(1500, seme=21)
        img, _ = costruisci([(camp, True)])
        ser = SerialeFinta(img)
        ricevuto = scarica.leggi_dump(ser)
        self.assertEqual(ricevuto, img)
        self.assertIn(b"DUMP", ser.scritto)
        es = swr.decodifica(ricevuto)
        self.assertEqual([s for pg in es.pagine_dati for s in pg["campioni"]], camp)


if __name__ == "__main__":
    unittest.main()
