// SwimTimer - lettura del FIFO dell'LSM6DS3TR-C con controllo dell'allineamento (0.6.1). Solo C++ standard, SENZA Arduino: l'I2C, il tempo e
// l'uscita dei campioni sono iniettati (template Hw). Il port Python equivalente, riga per riga, e' fifo_sim.py (provato in test_swr.py con
// segnale sintetico: gravita' + rotazione + urti + sfasamenti iniettati). Se si cambia un algoritmo qui, va cambiato anche li'.
//
// MISURATO sulla tag con PROVA_FIFO (2026-11-11, tag ferma su USB):
//  - il flusso del FIFO si SFASA DAVVERO da solo, ~5 volte al minuto (si perdono 1-2 parole nel flusso). Senza rimedio da quel punto in poi
//    i campioni risultano con acc e giro scambiati/mescolati: e' il difetto visto in piscina. Causa NON trovata (letture da 2/4/6 byte,
//    100 kHz, margine di 12 parole: nessun effetto).
//  - il registro FIFO_PATTERN (FIFO_STATUS3/4) e' esatto per una parte degli slittamenti, ma a volte legge un valore falso, e a volte lo
//    slittamento non compare affatto nei registri; DIFF_FIFO e PATTERN non sono assestati per ~1 ms dopo una lettura del FIFO; con FIFO
//    vuoto il pattern non e' significativo (legge 5).
// LIVELLO 1 (registri): a ogni chiamata, almeno 8 ms dopo l'ultimo accesso, si legge lo stato. Pattern 0: gli insiemi della chiamata
//  precedente (la "batch", max 40) vanno al codificatore. Pattern != 0 si agisce solo se CONFERMATO dopo 2 ms e COERENTE con DIFF
//  (DIFF mod 6 == (6 - pattern) % 6): la batch e' sospetta e si butta, si scartano 6-pattern parole.
// LIVELLO 2 (contenuto): fra due campioni a 208 Hz nessun canale cambia di colpo. Uno sfasamento scambia acc e giro e la somma delle
//  differenze fra insiemi consecutivi supera SWRF_SPIKE; ma anche un urto vero la supera. Al primo salto si smette di leggere; alla
//  chiamata dopo si leggono 35 parole fresche (5 insiemi per ogni scostamento s = 0..5). Per ogni s le 5 serie temporali (un campione ogni
//  6 parole) vengono assegnate ai 6 canali e se ne prende la MEDIANA: costo(s) = somma sui canali di |mediana - canale dell'ultimo insieme
//  buono|. La mediana su 5 campioni ignora un urto lungo fino a 2 campioni; fino a 2 campioni di urto non spostano la scelta. Si cambia s
//  solo se costo(s) < SWRF_ACCETTA_MAX e costo(s) * SWRF_FATTORE < costo(0); altrimenti (urto vero o dubbio) s = 0, nessuno scarto e
//  l'insieme sospetto si tiene. (Una prima versione misurava la coerenza interna fra insiemi consecutivi: sbagliata, perche' confronta
//  sempre lo stesso canale con se' stesso e non dipende dall'allineamento; con gli urti dava falsi riallineamenti.)
// Ogni scarto con dati gia' accettati e' un DISALLINEAMENTO: chiusura della pagina dati (gap) e conteggio; all'avvio o dopo il reset del
// FIFO (nessun campione ancora accettato) non conta.
#pragma once
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#define SWRF_REG_STATUS1 0x3A      // FIFO_STATUS1..4: DIFF_FIFO (12 bit), flag, FIFO_PATTERN (10 bit)
#define SWRF_REG_OUT_L 0x3E        // FIFO_DATA_OUT_L
#define SWRF_REG_CTRL5 0x0A        // FIFO_CTRL5
#define SWRF_VB_MAX 40
#define SWRF_SPIKE 1000UL          // somma delle differenze fra due insiemi consecutivi oltre la quale si sospetta uno sfasamento
#define SWRF_ACCETTA_MAX 800UL     // costo massimo (coerenza interna) perche' uno scostamento sia accettato
#define SWRF_FATTORE 4UL           // il costo dello scostamento deve essere almeno 4 volte minore di quello con s = 0
#define SWRF_FINESTRA 35           // parole lette per la ricerca (5 insiemi a ogni scostamento fino a 5)
#define SWRF_NINS 5                // insiemi della finestra
#define SWRF_BLOCCO_I2C 24         // byte massimi per transazione I2C: il buffer di Wire e' di 32 byte (una lettura piu' lunga perde parole e SFASA il FIFO)

static inline uint16_t swrfSatSomma(uint16_t a, uint32_t b) { uint32_t s = (uint32_t)a + b; return s > 0xFFFE ? 0xFFFE : (uint16_t)s; }

// Hw deve offrire:
//   uint32_t ms();                                          tempo in ms
//   bool leggi(uint8_t reg, uint8_t *buf, uint8_t n);      lettura I2C con autoincremento (false = errore)
//   void scrivi(uint8_t reg, uint8_t v);
//   void attendi(uint32_t ms);
//   bool fermo();                                           true = la registrazione si sta chiudendo (non si fa piu' niente)
//   void erroreI2c();                                       una lettura e' fallita (l'Hw decide dopo quanti errori fermarsi)
//   void campione(const int16_t *s, uint32_t t);            campione accettato: ax ay az gx gy gz, tempo in ms
//   void chiudiPagina();   void gap();                      chiude la pagina dati in corso e marca la successiva con il flag di interruzione
//   void evento(uint8_t tipo, uint16_t a, uint16_t b);     1 = overrun, 2 = allineamento iniziale (a = parole scartate)
//   void traccia(const char *tag, uint32_t a, uint32_t b, uint32_t c);   diagnostica (solo prova)
template <class Hw>
struct SwrFifo {
  Hw &hw;
  explicit SwrFifo(Hw &h) : hw(h) { azzera(); }

  bool allinea = true;                         // false solo nelle prove (lettura "vecchia maniera")
  int16_t batch[SWRF_VB_MAX][6];               // insiemi letti alla chiamata precedente, in attesa della conferma del pattern
  uint32_t batchT[SWRF_VB_MAX];
  uint8_t batchN = 0;
  uint32_t ultAcc = 0;                         // ms dell'ultimo accesso al FIFO
  int16_t ultLetto[6];                         // ultimo insieme letto (riferimento di continuita')
  bool ultLettoOk = false;
  bool sospetto = false;                       // salto di contenuto: alla chiamata dopo si cerca lo scostamento
  int16_t sospSet[6];
  uint32_t sospT = 0;
  uint32_t campAvvio = 0;                      // campioni accettati dall'avvio o dall'ultimo reset del FIFO (0 = allineamento iniziale "gratis")
  // statistiche
  uint16_t statDisall = 0;                     // riallineamenti con dati scartati
  uint16_t statScartate = 0;                   // parole scartate (somma saturata a 0xFFFE)
  uint8_t statOverrun = 0;
  uint16_t disallNuovi = 0;                    // non ancora scritti nel diario
  uint16_t nSospetti = 0;                      // salti di contenuto visti (anche urti veri)
  uint16_t nRc = 0;                            // ricerche dello scostamento eseguite
  uint16_t nRcSpostati = 0;                    // ricerche che hanno trovato s != 0 (riallineamenti dal contenuto)

  void azzera() { batchN = 0; ultAcc = 0; ultLettoOk = false; sospetto = false; campAvvio = 0; }
  void azzeraStat() { statDisall = statScartate = disallNuovi = nSospetti = nRc = nRcSpostati = 0; statOverrun = 0; }

  static uint32_t distanza(const int16_t *a, const int16_t *b) {
    uint32_t d = 0;
    for (int i = 0; i < 6; i++) d += (uint32_t)abs((int)a[i] - (int)b[i]);
    return d;
  }
  // insieme logico (ax ay az gx gy gz) formato dalle 6 parole W[k..k+5] in ordine FIFO (gx gy gz ax ay az)
  static void insieme(const int16_t *W, int k, int16_t *out) {
    out[0] = W[k + 3]; out[1] = W[k + 4]; out[2] = W[k + 5]; out[3] = W[k]; out[4] = W[k + 1]; out[5] = W[k + 2];
  }
  // lettura di n byte (pari) in blocchi da SWRF_BLOCCO_I2C: ogni transazione resta sotto il limite del buffer di Wire
  bool leggiBlocchi(uint8_t *b, uint16_t n) {
    for (uint16_t o = 0; o < n; o += SWRF_BLOCCO_I2C) {
      uint8_t k = (n - o) > SWRF_BLOCCO_I2C ? SWRF_BLOCCO_I2C : (uint8_t)(n - o);
      if (!hw.leggi(SWRF_REG_OUT_L, b + o, k)) return false;
    }
    return true;
  }
  void commit() {
    for (uint8_t i = 0; i < batchN && !hw.fermo(); i++) { hw.campione(batch[i], batchT[i]); campAvvio++; }
    batchN = 0;
  }
  void accoda(const int16_t *s, uint32_t t) {
    if (batchN >= SWRF_VB_MAX) return;
    memcpy(batch[batchN], s, 12); batchT[batchN] = t; batchN++;
    memcpy(ultLetto, s, 12); ultLettoOk = true;
  }
  void riallineamento(uint32_t scartate) {      // dati gia' accettati e ora incerti: pagina chiusa con flag di interruzione
    hw.chiudiPagina();
    hw.gap();
    statDisall++; disallNuovi++;
    statScartate = swrfSatSomma(statScartate, scartate);
  }

  void servi() {
    if (hw.fermo()) return;
    uint32_t ora = hw.ms();
    if (ora - ultAcc < 8) return;                        // stato non ancora assestato
    uint8_t st[4];
    if (!hw.leggi(SWRF_REG_STATUS1, st, 4)) { hw.erroreI2c(); return; }
    if (st[1] & 0x40) {                                  // overrun: FIFO ripartito, i campioni persi si vedono dal flag e dal tempo
      batchN = 0; sospetto = false; ultLettoOk = false;
      hw.chiudiPagina();
      hw.gap();
      if (statOverrun < 255) statOverrun++;
      hw.evento(1, statOverrun, 0);
      hw.scrivi(SWRF_REG_CTRL5, 0x00);
      hw.scrivi(SWRF_REG_CTRL5, 0x2E);
      campAvvio = 0;
      ultAcc = hw.ms();
      return;
    }
    uint16_t parole = st[0] | ((st[1] & 0x0F) << 8);
    uint16_t pat = st[2] | ((st[3] & 0x03) << 8);
    if (parole == 0) { ultAcc = ora; return; }           // FIFO vuoto: pattern non verificabile, la batch aspetta
    if (pat != 0 && pat < 6 && allinea && (uint16_t)((6 - pat) % 6) == (parole % 6)) {   // livello 1: puntatore sfasato
      hw.attendi(2);                                     // conferma con lo stato ormai assestato
      uint8_t st2[4];
      if (!hw.leggi(SWRF_REG_STATUS1, st2, 4)) { hw.erroreI2c(); return; }
      uint16_t pat2 = st2[2] | ((st2[3] & 0x03) << 8);
      uint16_t parole2 = st2[0] | ((st2[1] & 0x0F) << 8);
      if (pat2 != pat || parole2 == 0 || (uint16_t)((6 - pat2) % 6) != (parole2 % 6)) { ultAcc = hw.ms(); return; }
      parole = parole2;
      uint8_t da = 6 - pat;
      if (parole < da) { ultAcc = hw.ms(); return; }     // la parola che manca non e' ancora arrivata
      uint8_t scarto[12];
      if (!hw.leggi(SWRF_REG_OUT_L, scarto, da * 2)) { hw.erroreI2c(); return; }
      hw.traccia("DISC", pat, parole, batchN);
      if (campAvvio == 0 && batchN == 0) {               // allineamento iniziale: niente e' stato perso
        hw.evento(2, da, 0);
      } else {                                           // batch buttata: dati incerti, ~20-40 ms persi
        uint32_t persi = da + 6u * batchN;
        batchN = 0;
        riallineamento(persi);
      }
      ultLettoOk = false; sospetto = false;
      ultAcc = hw.ms();
      return;                                            // dopo lo scarto lo stato si riassesta: si rivaluta alla chiamata dopo
    }
    commit();                                            // pattern 0: la batch della chiamata precedente e' valida
    if (hw.fermo()) return;
    if (sospetto) {                                      // livello 2: ricerca dello scostamento con 35 parole fresche
      if (parole < SWRF_FINESTRA + 6) { ultAcc = ora; return; }
      uint8_t b[SWRF_FINESTRA * 2];
      if (!leggiBlocchi(b, SWRF_FINESTRA * 2)) { hw.erroreI2c(); ultAcc = hw.ms(); return; }
      int16_t W[SWRF_FINESTRA + 6];
      for (int i = 0; i < SWRF_FINESTRA; i++) W[i] = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
      uint32_t c[6]; uint8_t best = 0;
      for (int s = 0; s < 6; s++) {
        uint32_t costo = 0;
        for (int ch = 0; ch < 6; ch++) {
          int16_t v[SWRF_NINS];
          for (int m = 0; m < SWRF_NINS; m++) { int16_t t6[6]; insieme(W, s + 6 * m, t6); v[m] = t6[ch]; }
          for (int x = 1; x < SWRF_NINS; x++) { int16_t k = v[x]; int y = x - 1; while (y >= 0 && v[y] > k) { v[y + 1] = v[y]; y--; } v[y + 1] = k; }   // mediana
          costo += (uint32_t)abs((int)v[SWRF_NINS / 2] - (int)ultLetto[ch]);
        }
        c[s] = costo;
        if (c[s] < c[best]) best = s;
      }
      if (best != 0 && !(c[best] < SWRF_ACCETTA_MAX && c[best] * SWRF_FATTORE < c[0])) best = 0;   // non convincente: era un urto vero
      nRc++;
      if (best != 0) nRcSpostati++;
      uint8_t extra = best + 1;                          // parole che completano il 6o insieme
      uint8_t b2[12];
      if (!hw.leggi(SWRF_REG_OUT_L, b2, extra * 2)) { hw.erroreI2c(); ultAcc = hw.ms(); return; }
      for (int i = 0; i < extra; i++) W[SWRF_FINESTRA + i] = (int16_t)(b2[2 * i] | (b2[2 * i + 1] << 8));
      hw.traccia("RC", best, c[0], c[best]);
      if (best != 0) {                                   // sfasamento confermato dal contenuto: dati incerti
        riallineamento(best + 6u);                       // le parole scartate piu' l'insieme sospetto buttato
      } else if (batchN < SWRF_VB_MAX) {                 // urto vero: l'insieme sospetto era buono
        accoda(sospSet, sospT);
      }
      for (int k = 0; k < SWRF_NINS + 1; k++) {          // 6 insiemi, ~4,8 ms l'uno, l'ultimo al tempo attuale
        int16_t t[6];
        insieme(W, best + 6 * k, t);
        accoda(t, ora - ((uint32_t)(SWRF_NINS - k) * 4800UL + 500) / 1000);
      }
      sospetto = false;
      ultAcc = hw.ms();
      return;
    }
    uint16_t sets = parole / 6;
    if (sets > SWRF_VB_MAX - 8) sets = SWRF_VB_MAX - 8;
    for (uint16_t k = 0; k < sets && !sospetto;) {
      uint8_t n = (sets - k) >= 2 ? 2 : 1;
      uint8_t b[24];
      if (!hw.leggi(SWRF_REG_OUT_L, b, 12 * n)) { hw.erroreI2c(); ultAcc = hw.ms(); return; }
      for (uint8_t j = 0; j < n; j++, k++) {
        int16_t w[6], s[6];
        for (int i = 0; i < 6; i++) w[i] = (int16_t)(b[12 * j + 2 * i] | (b[12 * j + 2 * i + 1] << 8));
        insieme(w, 0, s);
        uint32_t t = ora - ((uint32_t)(sets - 1 - k) * 4800UL + 500) / 1000;                // ms prima di adesso
        if (sospetto) break;                                                                // trovato nel blocco da 2: il resto dell'insieme letto si perde
        if (ultLettoOk && allinea && distanza(s, ultLetto) > SWRF_SPIKE) {                  // livello 2: salto di contenuto
          sospetto = true; nSospetti++;
          memcpy(sospSet, s, 12); sospT = t;
          break;                                                                            // gli insiemi dopo non si leggono: restano nel FIFO
        }
        accoda(s, t);
      }
    }
    ultAcc = hw.ms();
  }
};
