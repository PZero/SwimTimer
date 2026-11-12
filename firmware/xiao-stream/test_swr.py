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


def costruisci2(segmenti, mv=3900, confermati=()):
    """Formato 2: ogni segmento comincia un blocco nuovo (seq crescente da 1); blocco = intestazione + max 15 pagine, il resto 0xFF.
    Ritorna (blocchi in ordine fisico = ordine di seq, elenco)."""
    blocchi = []
    seq = 0
    for idx, (camp, chiudi) in enumerate(segmenti):
        seq += 1
        blocchi.append(dict(seq=seq, seg=idx, voci=[("seg", None)]))
        cod = swr.Codificatore()
        n_pag = 0
        flag = swr.FLAG_PRIMA

        def aggiungi_voce(voce):
            nonlocal seq
            if len(blocchi[-1]["voci"]) == 15:                 # blocco pieno: se ne apre uno nuovo
                seq += 1
                blocchi.append(dict(seq=seq, seg=idx, voci=[]))
            blocchi[-1]["voci"].append(voce)

        for i, s in enumerate(camp):
            if cod.nc and not cod.sta(s):
                aggiungi_voce(("dati", (bytes(cod.pag), cod.nc, cod.t_primo, flag)))
                flag = 0
                n_pag += 1
                cod.azzera()
            cod.aggiungi(s, int(1000 + 100000 * idx + i * swr.MS_PER_CAMPIONE))
        if cod.nc:
            aggiungi_voce(("dati", (bytes(cod.pag), cod.nc, cod.t_primo, flag)))
            n_pag += 1
        if chiudi:
            aggiungi_voce(("chiusura", (len(camp), n_pag)))
    uscita = []
    for f, b in enumerate(blocchi):
        pagine = []
        for j, (tipo, arg) in enumerate(b["voci"]):
            numero = f * 16 + 1 + j
            if tipo == "seg":
                pagine.append(swr.pagina_segmento(numero, b["seg"], mv=mv))
            elif tipo == "dati":
                pag, nc, t_primo, fl = arg
                c = swr.Codificatore()
                c.pag = bytearray(pag); c.nc = nc; c.t_primo = t_primo
                pagine.append(c.chiudi(numero, b["seg"], mv, 22, fl))
            else:
                pagine.append(swr.pagina_chiusura(numero, b["seg"], 1, arg[0], arg[1]))
        uscita.append(swr.costruisci_blocco(f, b["seq"], pagine, segmento=b["seg"], confermato=(b["seq"] in confermati)))
    return uscita, blocchi


class TestFormato2(unittest.TestCase):
    def test_crc32_valore_noto(self):
        import zlib
        self.assertEqual(zlib.crc32(b"123456789") & 0xFFFFFFFF, 0xCBF43926)     # lo stesso CRC32 di firmware e display

    def test_intestazione_conferma_fuori_dal_crc(self):
        a = swr.intestazione_blocco(32, 7)
        b = swr.intestazione_blocco(32, 7, confermato=True)
        self.assertEqual(a[252:256], b"\xff" * 4)
        self.assertEqual(b[252:256], b"\x00" * 4)
        self.assertEqual(a[16], 0xFF)                                            # byte 16 riservato, non piu' usato
        self.assertEqual(a[14:16], b[14:16])                                     # stessa CRC con o senza conferma
        self.assertEqual(swr.crc_blocco_pagina(a), struct.unpack_from("<H", a, 14)[0])
        self.assertEqual(swr.crc_blocco_pagina(b), struct.unpack_from("<H", b, 14)[0])
        c = bytearray(a)
        c[17] ^= 1                                                               # il seq e' coperto dal CRC
        self.assertNotEqual(swr.crc_blocco_pagina(c), struct.unpack_from("<H", c, 14)[0])

    def test_parola_conferma_isolata(self):
        """La flash riscrive l'intera parola da 4 byte: la conferma (252..255) non deve condividere la parola con altri dati."""
        a = bytearray(swr.intestazione_blocco(32, 0x01020304, id_tag=0xA1B2C3D4))
        self.assertEqual(swr.OFF_CONFERMA % 4, 0)
        self.assertEqual(a[swr.OFF_CONFERMA:swr.OFF_CONFERMA + 4], b"\xff" * 4)
        self.assertTrue(all(x == 0xFF for x in a[25:256]))                       # dopo id tag solo 0xFF
        a[252:256] = b"\x00\x00\x00\x00"                                      # scrittura «sostitutiva» della parola, come la Puya
        self.assertTrue(swr.e_confermato(a))
        self.assertEqual(struct.unpack_from("<I", a, 17)[0], 0x01020304)          # seq intatto
        self.assertEqual(swr.crc_blocco_pagina(a), struct.unpack_from("<H", a, 14)[0])

    def test_formato2_si_legge_ancora(self):
        """Blocchi del 2026-11-10 (formato 2, conferma nel byte 16): CRC e conferma letti con la regola vecchia."""
        a = bytearray(swr.intestazione_blocco(32, 7))
        a[1] = 2
        a[14:16] = b"\x00\x00"
        a[14:16] = struct.pack("<H", swr.crc_blocco_pagina(a))
        self.assertFalse(swr.e_confermato(a))
        a[16] = 0x00
        self.assertTrue(swr.e_confermato(a))
        self.assertEqual(swr.crc_blocco_pagina(a), struct.unpack_from("<H", a, 14)[0])

    def test_crc32_blocco_ignora_la_conferma(self):
        bl = swr.costruisci_blocco(3, 9, [])
        conf = bytearray(bl)
        conf[252:256] = b"\x00" * 4
        self.assertEqual(swr.crc32_blocco(bl), swr.crc32_blocco(bytes(conf)))
        conf[100] ^= 1
        self.assertNotEqual(swr.crc32_blocco(bl), swr.crc32_blocco(bytes(conf)))

    def test_roundtrip_piu_blocchi_in_ordine_fisico_rimescolato(self):
        camp = campioni_inventati(2500, seme=13)
        blocchi, _ = costruisci2([(camp, True)])
        self.assertGreater(len(blocchi), 3)
        rot = blocchi[2:] + blocchi[:2]                       # l'anello e' girato: ordine fisico diverso da quello di seq
        es = swr.decodifica(b"".join(rot))
        self.assertEqual(es.problemi, [])
        self.assertEqual(es.formato, 2)
        self.assertEqual([s for pg in es.pagine_dati for s in pg["campioni"]], camp)
        self.assertTrue(es.segmenti[0]["chiuso"])
        self.assertEqual(es.segmenti[0]["campioni"], len(camp))

    def test_pagine_vuote_in_coda_al_blocco_sono_valide(self):
        a, b = campioni_inventati(300, 1), campioni_inventati(200, 2)
        blocchi, _ = costruisci2([(a, True), (b, True)])      # ogni segmento in un blocco nuovo: i blocchi finiscono con pagine 0xFF
        self.assertTrue(blocchi[0].endswith(b"\xff" * 256))
        es = swr.decodifica(b"".join(blocchi))
        self.assertEqual(es.problemi, [])
        per = {0: [], 1: []}
        for pg in es.pagine_dati:
            per[pg["seg"]] += pg["campioni"]
        self.assertEqual(per, {0: a, 1: b})

    def test_conferma_scritta_non_rovina_il_blocco(self):
        camp = campioni_inventati(900, 3)
        blocchi, _ = costruisci2([(camp, True)], confermati=(1,))
        es = swr.decodifica(b"".join(blocchi))
        self.assertEqual(es.problemi, [])
        self.assertTrue(es.blocchi[0]["confermato"])
        self.assertFalse(es.blocchi[-1]["confermato"])
        self.assertEqual([s for pg in es.pagine_dati for s in pg["campioni"]], camp)

    def test_buco_di_seq_segnalato(self):
        camp = campioni_inventati(2500, seme=5)
        blocchi, _ = costruisci2([(camp, True)])
        senza = blocchi[:1] + blocchi[2:]                     # manca il blocco seq 2
        es = swr.decodifica(b"".join(senza))
        self.assertTrue(any("buco di seq" in p for p in es.problemi))

    def test_intestazione_corrotta_scarta_il_blocco(self):
        camp = campioni_inventati(2500, seme=6)
        blocchi, _ = costruisci2([(camp, True)])
        guasto = bytearray(b"".join(blocchi))
        guasto[4096 + 5] ^= 0x10                              # un bit nell'intestazione del secondo blocco
        es = swr.decodifica(bytes(guasto))
        self.assertTrue(any("intestazione non valida" in p for p in es.problemi))

    def test_pagina_dati_corrotta_dentro_un_blocco(self):
        camp = campioni_inventati(1500, seme=8)
        blocchi, _ = costruisci2([(camp, True)])
        guasto = bytearray(b"".join(blocchi))
        guasto[256 * 5 + 100] ^= 0x04                         # pagina 5 del primo blocco
        es = swr.decodifica(bytes(guasto))
        self.assertEqual(len(es.pagine_corrotte), 1)
        self.assertTrue(any("CRC" in p for p in es.problemi))

    def test_misure_della_chiusura(self):
        pag = bytearray(swr.pagina_chiusura(2, 0, 1, 100, 3))
        struct.pack_into("<HBHH", pag, 24, 480, 2, 310, 17)
        pag[14:16] = struct.pack("<H", swr.crc_pagina(pag))
        bl = swr.costruisci_blocco(0, 1, [swr.pagina_segmento(1, 0), bytes(pag)])
        es = swr.decodifica(bl)
        s = es.segmenti[0]
        self.assertEqual((s["gap_max_ms"], s["overrun"], s["apri_max_ms"], s["confermati"]), (480, 2, 310, 17))
        self.assertIn("tempi", swr.riassunto(es))

    def test_dump_formato2(self):
        camp = campioni_inventati(1200, seme=21)
        blocchi, _ = costruisci2([(camp, True)])
        img = b"".join(blocchi)
        ricevuto = scarica.leggi_dump(SerialeFinta(img, "SWR2", 4096))
        self.assertEqual(ricevuto, img)
        es = swr.decodifica(ricevuto)
        self.assertEqual([s for pg in es.pagine_dati for s in pg["campioni"]], camp)

    def test_dump_vuoto(self):
        self.assertEqual(scarica.leggi_dump(SerialeFinta(b"", "SWR2", 4096)), b"")

class TestVersione061(unittest.TestCase):
    """Campi aggiunti dalla 0.6.1: origine/contesto del guasto nel segmento, statistiche FIFO nella chiusura, campioni scambiati."""

    def _blocco(self, seg_extra=None, chiusura=None, camp=None):
        camp = camp or campioni_inventati(300, seme=5, salti=False)
        cod = swr.Codificatore()
        pagine = [swr.pagina_segmento(1, 0, versione="0.6.1", extra=seg_extra)]
        n = 0
        for s in camp:
            if cod.nc and not cod.sta(s):
                pagine.append(cod.chiudi(2 + len(pagine) - 1, 0, 3900, 22, 0)); cod.azzera(); n += 1
            cod.aggiungi(s, 1000 + n)
        if cod.nc:
            pagine.append(cod.chiudi(len(pagine) + 1, 0, 3900, 22, 0))
        if chiusura is not None:
            pagine.append(chiusura(len(pagine) + 1))
        assert len(pagine) <= 15
        return swr.costruisci_blocco(0, 1, pagine), camp

    def test_tempo_di_sessione_catena_di_riprese(self):
        # segmento 0 a tocchi (scarto 0); primo riavvio a 100000 ms con istante esatto: scarto = 0 + 100000 + 500 = 100500;
        # secondo riavvio a 40000 ms (millis del 2o avvio): scarto = 100500 + 40000 + 500 = 141000, margine cumulato
        extra0 = dict(scarto=0, torig=0, margine=0, navvii=1, tavvio=500)
        extra1 = dict(flag=swr.SEGF_RIPRESA, riprese=1, origine=1, guasto=1, scarto=100500, torig=1, margine=30, navvii=2, tavvio=500)
        extra2 = dict(flag=swr.SEGF_RIPRESA, riprese=2, origine=1, guasto=4, scarto=141000, torig=2, margine=120, navvii=3, tavvio=500)
        for extra, att in ((extra0, (0, 0, 0)), (extra1, (100500, 1, 30)), (extra2, (141000, 2, 120))):
            bl, _ = self._blocco(extra)
            sg = swr.decodifica(bl).segmenti[0]
            self.assertEqual((sg["scarto"], sg["torig"], sg["margine"]), att)
            self.assertEqual(swr.tempo_sessione_ms(sg, 5000), 5000 + att[0])
        sg = swr.decodifica(self._blocco(extra2)[0]).segmenti[0]
        self.assertEqual(sg["navvii"], 3)
        testo = swr.riassunto(swr.decodifica(self._blocco(extra2)[0]))
        self.assertIn("tempo di sessione = millis + 141000 ms (+-120 ms)", testo)
        self.assertIn("ultimo vivo", testo)

    def test_tempo_non_continuo_se_origine_sconosciuta(self):
        extra = dict(flag=swr.SEGF_RIPRESA_FLASH, riprese=1, origine=2, scarto=0, torig=3, margine=0, navvii=1)
        bl, _ = self._blocco(extra)
        es = swr.decodifica(bl)
        sg = es.segmenti[0]
        self.assertIsNone(swr.tempo_sessione_ms(sg, 5000))                 # non si inventa un tempo
        self.assertIsNone(swr.correggi_scarto(sg, 520))
        self.assertIn("TEMPO NON CONTINUO", swr.riassunto(es))

    def test_correzione_dello_scarto_con_un_t_avvio_migliore(self):
        # 2 riavvii (avvii = 3) con T_AVVIO usato 500 ms; il valore vero e' 496 ms: ogni riavvio ha sommato 4 ms di troppo
        extra = dict(flag=swr.SEGF_RIPRESA, riprese=2, origine=1, scarto=141000, torig=1, margine=60, navvii=3, tavvio=500)
        sg = swr.decodifica(self._blocco(extra)[0]).segmenti[0]
        self.assertEqual(swr.correggi_scarto(sg, 496), 141000 - 8)

    def test_segmento_senza_tempo_di_sessione(self):
        sg = swr.decodifica(self._blocco(dict(flag=0, riprese=0, origine=0))[0]).segmenti[0]    # campi 0.6.1 senza i byte 64..73
        self.assertNotIn("scarto", sg)
        self.assertIsNone(swr.tempo_sessione_ms(sg, 1000))

    def test_segmento_vecchio_senza_campi_nuovi(self):
        bl, _ = self._blocco()
        s = swr.decodifica(bl).segmenti[0]
        self.assertNotIn("seg_flag", s)                              # file 0.5/0.6.0: campi assenti, nessun errore
        self.assertNotIn("origine:", swr.riassunto(swr.decodifica(bl)))

    def test_segmento_con_ripresa_e_contesto_del_guasto(self):
        extra = dict(flag=swr.SEGF_RIPRESA | swr.SEGF_CONTESTO, riprese=2, marca=0xD1, guasto=1, resetreas=0x4,
                     pc=0x0002A1B4, lr=0x0002A1C1, cfsr=0x00000400, hfsr=0x40000000, fase=12, origine=1)
        bl, camp = self._blocco(extra)
        es = swr.decodifica(bl)
        s = es.segmenti[0]
        self.assertEqual((s["seg_flag"], s["riprese"], s["marca"], s["guasto"], s["resetreas"], s["origine"]),
                         (5, 2, 0xD1, 1, 4, 1))
        self.assertEqual((s["pc"], s["lr"], s["cfsr"], s["hfsr"], s["fase"]), (0x2A1B4, 0x2A1C1, 0x400, 0x40000000, 12))
        self.assertEqual([c for pg in es.pagine_dati for c in pg["campioni"]], camp)   # i dati non cambiano
        testo = swr.riassunto(es)
        self.assertIn("ripresa dopo riavvio (marca)", testo)
        self.assertIn("HardFault", testo)
        self.assertIn("0x0002A1B4", testo)
        self.assertIn("reset software", testo)

    def test_guasto_watchdog_senza_contesto(self):
        bl, _ = self._blocco(dict(flag=swr.SEGF_RIPRESA, riprese=1, guasto=4, resetreas=0x2, origine=1))
        testo = swr.riassunto(swr.decodifica(bl))
        self.assertIn("watchdog", testo)

    def test_chiusura_con_statistiche_fifo(self):
        bl, _ = self._blocco(chiusura=lambda n: swr.pagina_chiusura(n, 0, 1, 300, 3, disall=4, scartate=17))
        s = swr.decodifica(bl).segmenti[0]
        self.assertEqual((s["disallineamenti"], s["parole_scartate"]), (4, 17))
        self.assertIn("4 disallineamenti, 17 parole scartate", swr.riassunto(swr.decodifica(bl)))

    def test_chiusura_vecchia_senza_statistiche(self):
        bl, _ = self._blocco(chiusura=lambda n: swr.pagina_chiusura(n, 0, 1, 300, 3))
        s = swr.decodifica(bl).segmenti[0]
        self.assertNotIn("disallineamenti", s)

    def test_campioni_scambiati_rilevati(self):
        # tag ferma a faccia in su: acc ~ 1 g su z (2048 LSB), giro ~ 0. Un tratto di 40 campioni e' scambiato (giro <-> acc).
        r = random.Random(3)
        buoni = [(r.randint(-8, 8), r.randint(-8, 8), 2048 + r.randint(-6, 6), r.randint(-4, 4), r.randint(-4, 4), r.randint(-4, 4)) for _ in range(160)]
        camp = list(buoni)
        for i in range(60, 100):                                      # 40 campioni scambiati
            ax, ay, az, gx, gy, gz = buoni[i]
            camp[i] = (gx, gy, gz, ax, ay, az)
        bl, _ = self._blocco(camp=camp)
        es = swr.decodifica(bl)
        sc, tot = swr.conta_scambiati(es)
        self.assertEqual((sc, tot), (40, 160))
        self.assertIn("SCAMBIATI", swr.riassunto(es))

    def test_interruzioni_raggruppate(self):
        def blocco(n):
            pagine = [swr.pagina_segmento(1, 0)]
            for i in range(n):
                c = swr.Codificatore()
                c.aggiungi((1, 2, 2048, 3, 4, 5), 1000 + i)
                pagine.append(c.chiudi(2 + i, 0, 3900, 22, swr.FLAG_GAP))
            return swr.costruisci_blocco(0, 1, pagine)
        poche = swr.decodifica(blocco(3))
        self.assertEqual(sum("interruzione" in p for p in poche.problemi), 3)          # poche: una riga ciascuna
        molte = swr.decodifica(blocco(9))
        righe = [p for p in molte.problemi if "interruzione" in p]
        self.assertEqual(len(righe), 1)                                                # tante: una riga sola con il totale
        self.assertIn("9 pagine", righe[0])

    def test_dati_normali_non_segnalati(self):
        # rotazione vera di 71 dps (= 2043 LSB nelle unita' del giro 35 mdps) con la gravita' sull'accelerometro: NON e' uno scambio
        camp = [(3, -2, 2048, 2043, 5, -4) for _ in range(120)]
        bl, _ = self._blocco(camp=camp)
        es = swr.decodifica(bl)
        self.assertEqual(swr.conta_scambiati(es)[0], 0)
        self.assertNotIn("SCAMBIATI", swr.riassunto(es))

class TestFifo(unittest.TestCase):
    """Algoritmo di lettura del FIFO (port Python di swr_fifo.h) con segnale sintetico: gravita' + rotazione + urti + sfasamenti iniettati."""

    def test_costanti_uguali_a_quelle_del_cpp(self):
        import re
        import fifo_sim
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "swr_fifo.h"), encoding="utf-8") as fh:
            h = fh.read()
        for nome in ("SWRF_VB_MAX", "SWRF_SPIKE", "SWRF_ACCETTA_MAX", "SWRF_FATTORE", "SWRF_FINESTRA", "SWRF_REG_STATUS1", "SWRF_REG_OUT_L", "SWRF_REG_CTRL5"):
            m = re.search(r"#define %s\s+(0x[0-9A-Fa-f]+|\d+)" % nome, h)
            self.assertIsNotNone(m, nome)
            self.assertEqual(int(m.group(1), 0), getattr(fifo_sim, nome), nome)

    def _urti(self, n, spaziatura_us, seme):
        r = random.Random(seme)
        return [(2_000_000 + i * spaziatura_us + r.randint(0, 20000), r.choice([5, 10, 20]), r.randint(1, 3)) for i in range(n)]

    def test_nessun_falso_riallineamento_su_10000_urti(self):
        import fifo_sim
        sim = fifo_sim.SimImu(seme=11, pattern_visibile=True, p_pattern_falso=0.02)
        n = 10000
        sim.urti = self._urti(n, 100_000, 5)
        f = fifo_sim.SwrFifo(sim)
        sim.esegui(f, 2 + n * 0.1 + 1)
        sbagliati, totale = sim.campioni_sbagliati()
        self.assertGreater(totale, 100000)
        self.assertGreater(f.nSospetti, n // 4)                      # gli urti vengono notati (sospetti) ...
        self.assertEqual(f.nRcSpostati, 0)                           # ... ma NESSUNO diventa un riallineamento (0 falsi su 10000)
        self.assertEqual(f.statDisall, 0)
        self.assertEqual(sbagliati, 0)                               # e nessun campione accettato e' mescolato

    def _prova_sfasamenti(self, visibile, con_urti, seme):
        import fifo_sim
        sim = fifo_sim.SimImu(seme=seme, pattern_visibile=visibile, p_pattern_falso=0.02)
        r = random.Random(seme + 100)
        n = 400
        t_sf = [3_000_000 + i * 2_000_000 + r.randint(0, 400_000) for i in range(n)]
        sim.sfasamenti = [(t, r.randint(1, 5)) for t in t_sf]
        if con_urti:
            sim.urti = [(t + r.randint(-300_000, 300_000), r.choice([5, 10, 20]), r.randint(1, 3)) for t in t_sf[::2]]
            sim.urti.sort()
        f = fifo_sim.SwrFifo(sim)
        sim.esegui(f, 3 + n * 2 + 3)
        # ogni sfasamento e' "trovato" se fra 0,8 s dopo e (poco prima del) il successivo non ci sono campioni mescolati
        sbagliati_t = [t for s, t in sim.accettati if s not in sim.veri]
        trovati = 0
        for i, t in enumerate(t_sf):
            fine = t_sf[i + 1] if i + 1 < n else t + 2_000_000
            if not any(t / 1000 + 800 <= x < fine / 1000 - 100 for x in sbagliati_t):     # 100 ms di tolleranza: i tempi dei campioni sono stimati
                trovati += 1
        return trovati / n, f

    def test_sfasamenti_trovati_pattern_visibile(self):
        frac, f = self._prova_sfasamenti(True, False, 21)
        self.assertGreaterEqual(frac, 0.95, "trovati %.3f" % frac)

    def test_sfasamenti_trovati_pattern_invisibile(self):
        # lo sfasamento non compare nei registri: serve il controllo sul contenuto. Media su 3 semi (il campione e' piccolo: 400 sfasamenti ciascuno)
        fr = [self._prova_sfasamenti(False, False, seme)[0] for seme in (31, 32, 33)]
        self.assertGreaterEqual(sum(fr) / 3, 0.95, "trovati %s" % fr)

    def test_sfasamenti_trovati_con_urti_vicini(self):
        # se uno sfasamento cade dentro la finestra di un urto (mediana su 5 campioni) la scelta e' ambigua e si resta con s = 0: limite noto
        # (misurato ~88 %, vedi LEGGIMI); qui si controlla solo che non peggiori e che i falsi restino a zero (test sui 10000 urti)
        fr = [self._prova_sfasamenti(False, True, seme)[0] for seme in (31, 32, 33)]
        self.assertGreaterEqual(sum(fr) / 3, 0.80, "trovati %s" % fr)

    def test_sfasamenti_trovati_pattern_visibile_con_urti(self):
        frac, f = self._prova_sfasamenti(True, True, 24)
        self.assertGreaterEqual(frac, 0.95, "trovati %.3f" % frac)

    def test_senza_controllo_lo_sfasamento_resta(self):
        import fifo_sim
        sim = fifo_sim.SimImu(seme=3, pattern_visibile=False)
        sim.sfasamenti = [(2_000_000, 3)]
        f = fifo_sim.SwrFifo(sim)
        f.allinea = False
        sim.esegui(f, 10)
        sbagliati, totale = sim.campioni_sbagliati()
        self.assertGreater(sbagliati, totale // 2)                   # la lettura "vecchia maniera" da quel punto e' tutta scambiata

    def test_senza_sfasamenti_nessun_evento(self):
        import fifo_sim
        sim = fifo_sim.SimImu(seme=4, pattern_visibile=True)
        f = fifo_sim.SwrFifo(sim)
        sim.esegui(f, 60)
        self.assertEqual((f.statDisall, f.nRcSpostati, sim.campioni_sbagliati()[0]), (0, 0, 0))


class SerialeFinta:
    """Simula la porta: rumore di log, poi SWR1 (pagine da 256) o SWR2 (blocchi da 4096) + dati + END."""
    def __init__(self, dati, sigla="SWR1", unita=256):
        n = len(dati) // unita
        self.rx = bytearray(b"12.3 bat 3900 mV usb 1 carica 0\nacc 1 2 3 | gyro 4 5 6\n")
        self.dati = dati
        self.dopo = sigla.encode() + b" %d\n" % n + dati + b"\nEND %d\n" % n
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
