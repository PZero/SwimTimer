"""Port Python di swr_fifo.h (lettura del FIFO dell'LSM6DS3TR-C con controllo dell'allineamento) e simulatore del sensore.

Serve a PROVARE l'algoritmo con segnale sintetico, perche' sul PC non c'e' un compilatore C++: la classe SwrFifo e' scritta riga per riga come
quella del C++ (stessi nomi, stesso ordine delle istruzioni); test_swr.py controlla anche che le costanti coincidano con quelle di swr_fifo.h.
Se si cambia l'algoritmo in swr_fifo.h va cambiato anche qui (e viceversa). Solo dati inventati.

Il simulatore (SimImu) produce insiemi da 6 parole [gx gy gz ax ay az] a 208,3 Hz con gravita' + rotazione + rumore, urti da N g su 1-3
campioni e sfasamenti iniettati (si perdono k parole dal flusso). Il registro FIFO_PATTERN e' modellato in due modi: "visibile" (l'etichetta
segue la posizione vera della parola: dopo la perdita il pattern e' sfasato) o "invisibile" (l'etichetta e' un contatore contiguo: lo
sfasamento non compare nei registri), con una probabilita' di lettura falsa del pattern (come misurato sulla tag).
"""
import math
import random

SWRF_REG_STATUS1 = 0x3A
SWRF_REG_OUT_L = 0x3E
SWRF_REG_CTRL5 = 0x0A
SWRF_VB_MAX = 40
SWRF_SPIKE = 1000
SWRF_ACCETTA_MAX = 800
SWRF_FATTORE = 4
SWRF_FINESTRA = 35
SWRF_NINS = 5
SWRF_BLOCCO_I2C = 24

ACC_1G = 2049            # LSB per g a +-16 g (488 ug/LSB)


def sat_somma(a, b):
    return min(a + b, 0xFFFE)


class SwrFifo:
    def __init__(self, hw):
        self.hw = hw
        self.allinea = True
        self.batch = []                  # lista di (insieme, t)
        self.ultAcc = 0
        self.ultLetto = None
        self.sospetto = False
        self.sospSet = None
        self.sospT = 0
        self.campAvvio = 0
        self.statDisall = 0
        self.statScartate = 0
        self.statOverrun = 0
        self.disallNuovi = 0
        self.nSospetti = 0
        self.nRc = 0
        self.nRcSpostati = 0
        self.azzera()

    def azzera(self):
        self.batch = []
        self.ultAcc = 0
        self.ultLetto = None
        self.sospetto = False
        self.campAvvio = 0

    @staticmethod
    def distanza(a, b):
        return sum(abs(a[i] - b[i]) for i in range(6))

    @staticmethod
    def insieme(W, k):
        return [W[k + 3], W[k + 4], W[k + 5], W[k], W[k + 1], W[k + 2]]

    def leggi_blocchi(self, n):
        out = []
        for o in range(0, n, SWRF_BLOCCO_I2C):
            b = self.hw.leggi(SWRF_REG_OUT_L, min(SWRF_BLOCCO_I2C, n - o))
            if b is None:
                return None
            out += b
        return out

    def commit(self):
        for s, t in self.batch:
            if self.hw.fermo():
                break
            self.hw.campione(s, t)
            self.campAvvio += 1
        self.batch = []

    def accoda(self, s, t):
        if len(self.batch) >= SWRF_VB_MAX:
            return
        self.batch.append((list(s), t))
        self.ultLetto = list(s)

    def riallineamento(self, scartate):
        self.hw.chiudiPagina()
        self.hw.gap()
        self.statDisall += 1
        self.disallNuovi += 1
        self.statScartate = sat_somma(self.statScartate, scartate)

    def servi(self):
        hw = self.hw
        if hw.fermo():
            return
        ora = hw.ms()
        if ora - self.ultAcc < 8:
            return
        st = hw.leggi(SWRF_REG_STATUS1, 4)
        if st is None:
            hw.erroreI2c()
            return
        if st[1] & 0x40:
            self.batch = []
            self.sospetto = False
            self.ultLetto = None
            hw.chiudiPagina()
            hw.gap()
            if self.statOverrun < 255:
                self.statOverrun += 1
            hw.evento(1, self.statOverrun, 0)
            hw.scrivi(SWRF_REG_CTRL5, 0x00)
            hw.scrivi(SWRF_REG_CTRL5, 0x2E)
            self.campAvvio = 0
            self.ultAcc = hw.ms()
            return
        parole = st[0] | ((st[1] & 0x0F) << 8)
        pat = st[2] | ((st[3] & 0x03) << 8)
        if parole == 0:
            self.ultAcc = ora
            return
        if pat != 0 and pat < 6 and self.allinea and ((6 - pat) % 6) == (parole % 6):
            hw.attendi(2)
            st2 = hw.leggi(SWRF_REG_STATUS1, 4)
            if st2 is None:
                hw.erroreI2c()
                return
            pat2 = st2[2] | ((st2[3] & 0x03) << 8)
            parole2 = st2[0] | ((st2[1] & 0x0F) << 8)
            if pat2 != pat or parole2 == 0 or ((6 - pat2) % 6) != (parole2 % 6):
                self.ultAcc = hw.ms()
                return
            parole = parole2
            da = 6 - pat
            if parole < da:
                self.ultAcc = hw.ms()
                return
            if hw.leggi(SWRF_REG_OUT_L, da * 2) is None:
                hw.erroreI2c()
                return
            hw.traccia("DISC", pat, parole, len(self.batch))
            if self.campAvvio == 0 and len(self.batch) == 0:
                hw.evento(2, da, 0)
            else:
                persi = da + 6 * len(self.batch)
                self.batch = []
                self.riallineamento(persi)
            self.ultLetto = None
            self.sospetto = False
            self.ultAcc = hw.ms()
            return
        self.commit()
        if hw.fermo():
            return
        if self.sospetto:
            if parole < SWRF_FINESTRA + 6:
                self.ultAcc = ora
                return
            b = self.leggi_blocchi(SWRF_FINESTRA * 2)
            if b is None:
                hw.erroreI2c()
                self.ultAcc = hw.ms()
                return
            W = [_i16(b[2 * i] | (b[2 * i + 1] << 8)) for i in range(SWRF_FINESTRA)]
            c = [0] * 6
            best = 0
            for s in range(6):
                costo = 0
                for ch in range(6):
                    v = sorted(self.insieme(W, s + 6 * m)[ch] for m in range(SWRF_NINS))
                    costo += abs(v[SWRF_NINS // 2] - self.ultLetto[ch])
                c[s] = costo
                if c[s] < c[best]:
                    best = s
            if best != 0 and not (c[best] < SWRF_ACCETTA_MAX and c[best] * SWRF_FATTORE < c[0]):
                best = 0
            self.nRc += 1
            if best != 0:
                self.nRcSpostati += 1
            extra = best + 1
            b2 = hw.leggi(SWRF_REG_OUT_L, extra * 2)
            if b2 is None:
                hw.erroreI2c()
                self.ultAcc = hw.ms()
                return
            for i in range(extra):
                W.append(_i16(b2[2 * i] | (b2[2 * i + 1] << 8)))
            hw.traccia("RC", best, c[0], c[best])
            if best != 0:
                self.riallineamento(best + 6)
            elif len(self.batch) < SWRF_VB_MAX:
                self.accoda(self.sospSet, self.sospT)
            for k in range(SWRF_NINS + 1):
                self.accoda(self.insieme(W, best + 6 * k), ora - ((SWRF_NINS - k) * 4800 + 500) // 1000)
            self.sospetto = False
            self.ultAcc = hw.ms()
            return
        sets = parole // 6
        if sets > SWRF_VB_MAX - 8:
            sets = SWRF_VB_MAX - 8
        k = 0
        while k < sets and not self.sospetto:
            n = 2 if (sets - k) >= 2 else 1
            b = hw.leggi(SWRF_REG_OUT_L, 12 * n)
            if b is None:
                hw.erroreI2c()
                self.ultAcc = hw.ms()
                return
            for j in range(n):
                w = [_i16(b[12 * j + 2 * i] | (b[12 * j + 2 * i + 1] << 8)) for i in range(6)]
                s = self.insieme(w, 0)
                t = ora - ((sets - 1 - k) * 4800 + 500) // 1000
                k += 1
                if self.sospetto:
                    break
                if self.ultLetto is not None and self.allinea and self.distanza(s, self.ultLetto) > SWRF_SPIKE:
                    self.sospetto = True
                    self.nSospetti += 1
                    self.sospSet = s
                    self.sospT = t
                    break
                self.accoda(s, t)
        self.ultAcc = hw.ms()


def _i16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _clip(v):
    return max(-32768, min(32767, int(round(v))))


# ----------------------------------------------------------------------------------------------- simulatore
class SimImu:
    """Sensore + bus I2C + uscita dei campioni (fa anche da Hw per SwrFifo). Tempo in microsecondi."""

    def __init__(self, seme=1, pattern_visibile=True, p_pattern_falso=0.02, rumore=3):
        self.r = random.Random(seme)
        self.t_us = 0
        self.prossimo = 0.0
        self.periodo = 4800.0
        self.coda = []                    # (parola, etichetta)
        self.contatore = 0
        self.visibile = pattern_visibile
        self.p_falso = p_pattern_falso
        self.rumore = rumore
        self.ultima_lettura_us = -10 ** 9
        self.sfasamenti = []              # (tempo_us, parole) da iniettare: dopo quel tempo si perdono k parole dal flusso
        self.urti = []                    # (tempo_us, ampiezza_g, n_campioni)
        self.veri = {}                    # insieme vero (tupla ax ay az gx gy gz) -> indice
        self.n_generati = 0
        self.accettati = []               # (insieme, t)
        self.pagine_chiuse = 0
        self.gap_n = 0
        self.letture = 0
        self.urto_attivo = 0
        self.urto_vettore = (0, 0, 0)
        self.perdi_ora = 0

    # --- segnale
    def _insieme_vero(self, t_us):
        t = t_us / 1e6
        a = 0.9 * math.sin(2 * math.pi * t / 3.1)                 # inclinazione che oscilla: gravita' + rotazione
        da = 0.9 * 2 * math.pi / 3.1 * math.cos(2 * math.pi * t / 3.1)
        ax = ACC_1G * math.sin(a); az = ACC_1G * math.cos(a); ay = 0.2 * ACC_1G * math.sin(2 * math.pi * t / 1.7)
        gy = da / (2 * math.pi) * 360 / 0.035                    # rad/s -> dps -> LSB (35 mdps)
        gx = 150 * math.sin(2 * math.pi * t / 0.9) / 0.035 * 0.1
        gz = 60 * math.cos(2 * math.pi * t / 1.3) / 0.035 * 0.1
        n = self.rumore
        s = [ax + self.r.randint(-n, n), ay + self.r.randint(-n, n), az + self.r.randint(-n, n),
             gx + self.r.randint(-n, n), gy + self.r.randint(-n, n), gz + self.r.randint(-n, n)]
        return [_clip(v) for v in s]

    def _genera_fino_a(self):
        while self.prossimo <= self.t_us:
            tg = int(self.prossimo)
            s = self._insieme_vero(tg)
            # urti: si aggiungono all'accelerazione per 1-3 campioni
            while self.urti and self.urti[0][0] <= tg:
                _, amp, n = self.urti.pop(0)
                self.urto_attivo = n
                ax = self.r.choice([-1, 1]) * amp * ACC_1G * self.r.uniform(0.5, 1.0)
                ay = self.r.choice([-1, 1]) * amp * ACC_1G * self.r.uniform(0.0, 0.6)
                az = self.r.choice([-1, 1]) * amp * ACC_1G * self.r.uniform(0.0, 0.6)
                self.urto_vettore = (ax, ay, az)
            if self.urto_attivo > 0:
                self.urto_attivo -= 1
                for i in range(3):
                    s[i] = _clip(s[i] + self.urto_vettore[i])
            self.veri[tuple(s)] = self.n_generati
            self.n_generati += 1
            parole = [s[3], s[4], s[5], s[0], s[1], s[2]]          # ordine FIFO: gx gy gz ax ay az
            while self.sfasamenti and self.sfasamenti[0][0] <= tg:
                self.perdi_ora = self.sfasamenti.pop(0)[1]
            for idx, w in enumerate(parole):
                if self.perdi_ora > 0:
                    self.perdi_ora -= 1                            # parola persa nel flusso (il contatore delle parole scritte non avanza)
                    continue
                etichetta = idx if self.visibile else self.contatore % 6
                self.coda.append((w, etichetta))
                self.contatore += 1
            self.prossimo += self.periodo

    def avanza(self, us):
        self.t_us += us
        self._genera_fino_a()

    # --- interfaccia Hw
    def ms(self):
        return self.t_us // 1000

    def attendi(self, ms):
        self.avanza(ms * 1000)

    def leggi(self, reg, n):
        self.letture += 1
        self.avanza(150 + 25 * n)                                   # ~400 kHz
        if reg == SWRF_REG_STATUS1:
            diff = len(self.coda)
            if self.coda:
                pat = self.coda[0][1]
            else:
                pat = 5
            instabile = (self.t_us - self.ultima_lettura_us) < 1000   # registri non assestati subito dopo una lettura del FIFO
            if instabile or self.r.random() < self.p_falso:
                pat = self.r.randint(1, 5)
            return [diff & 0xFF, (diff >> 8) & 0x0F, pat & 0xFF, pat >> 8][:n]
        if reg == SWRF_REG_OUT_L:
            if n > 32:                                                  # buffer di Wire da 32 byte: la lettura si interrompe a meta' e le parole sono perse
                for _ in range(16):
                    if self.coda:
                        self.coda.pop(0)
                self.ultima_lettura_us = self.t_us
                return None
            out = []
            for _ in range(n // 2):
                w = self.coda.pop(0)[0] if self.coda else 0
                out.append(w & 0xFF)
                out.append((w >> 8) & 0xFF)
            self.ultima_lettura_us = self.t_us
            return out
        return [0] * n

    def scrivi(self, reg, v):
        pass

    def fermo(self):
        return False

    def erroreI2c(self):
        pass

    def campione(self, s, t):
        self.accettati.append((tuple(s), t))

    def chiudiPagina(self):
        self.pagine_chiuse += 1

    def gap(self):
        self.gap_n += 1

    def evento(self, tipo, a, b):
        pass

    def traccia(self, tag, a, b, c):
        pass

    # --- esecuzione
    def esegui(self, fifo, durata_s, passo_ms=20):
        fine = self.t_us + int(durata_s * 1e6)
        while self.t_us < fine:
            self.avanza(passo_ms * 1000)
            fifo.servi()

    def campioni_sbagliati(self, dopo_us=0):
        """Campioni accettati che NON sono un insieme vero generato (cioe' mescolati/scambiati): ritorna (sbagliati, totale)."""
        sb = 0
        for s, t in self.accettati:
            if s not in self.veri:
                sb += 1
        return sb, len(self.accettati)
