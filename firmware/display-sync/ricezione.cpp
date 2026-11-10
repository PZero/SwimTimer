// Ricezione: assemblaggio dei blocchi (BLOCCO + 32 FRAMMENTI) nei buffer della tag.
#include <Arduino.h>
#include "ricezione.h"
#include "sd_scrittore.h"
#include "stato.h"
#include "trasporto.h"

enum : uint8_t { S_LIBERO = 0, S_RICEVE = 1, S_CODA = 2 };

struct Slot {
  volatile uint8_t stato;
  IntestazioneBlocco h;
  uint32_t mask;  // frammenti arrivati
  uint8_t *buf;
};
struct RxTag {
  Slot s[SYNC_FINESTRA];
  int corr = -1;                // slot in ricezione
  volatile uint32_t byteAcc = 0;
};
static RxTag rx[SYNC_MAX_TAG];

void ricezioneInit() {
  for (int t = 0; t < SYNC_MAX_TAG; t++)
    for (int s = 0; s < SYNC_FINESTRA; s++) {
      rx[t].s[s].buf = (uint8_t *)ps_malloc(SYNC_BLOCCO);
      rx[t].s[s].stato = S_LIBERO;
    }
}

uint8_t *ricezioneBuffer(int tag, int slot) { return rx[tag].s[slot].buf; }
const IntestazioneBlocco &ricezioneIntestazione(int tag, int slot) { return rx[tag].s[slot].h; }
void ricezioneLibera(int tag, int slot) { rx[tag].s[slot].stato = S_LIBERO; }
uint32_t ricezioneByteAcc(int tag) {
  uint32_t v = rx[tag].byteAcc;
  rx[tag].byteAcc = 0;
  return v;
}

// Toglie il blocco `seq` dalla lista "in trasmissione"; ritorna il blocco fisico (0xFFFF se non c'era)
static uint16_t txToglie(TagStato &t, uint32_t seq) {
  for (int i = 0; i < 2; i++)
    if (t.txFisico[i] != 0xFFFF && t.txSeq[i] == seq) {
      uint16_t f = t.txFisico[i];
      t.txFisico[i] = 0xFFFF;
      return f;
    }
  return 0xFFFF;
}

static void accoda(uint8_t tipo, int tag, int slot, uint32_t seq) {
  Lavoro l = {tipo, (uint8_t)tag, (uint8_t)slot, seq};
  sdAccoda(l);
}

// Blocco rimasto a meta' (nuovo BLOCCO, FINE o frammento fuori posto): lo scrittore chiedera' RIPETI
static void scartaCorrente(int tag) {
  RxTag &r = rx[tag];
  if (r.corr < 0) return;
  Slot &s = r.s[r.corr];
  uint32_t seq = s.h.seq;
  s.stato = S_LIBERO;
  r.corr = -1;
  {
    StatoLock l;
    txToglie(gStato.tag[tag], seq);
  }
  accoda(L_FALLITO, tag, 0, seq);
}

void ricezioneReset(int tag) {
  RxTag &r = rx[tag];
  if (r.corr >= 0) {
    uint32_t seq = r.s[r.corr].h.seq;
    r.s[r.corr].stato = S_LIBERO;
    r.corr = -1;
    StatoLock l;
    txToglie(gStato.tag[tag], seq);
  }
  StatoLock l;
  gStato.tag[tag].txFisico[0] = gStato.tag[tag].txFisico[1] = 0xFFFF;
  gStato.tag[tag].bps = 0;
}

void ricezioneNotifica(int tag, const uint8_t *d, size_t n) {
  if (tag < 0 || tag >= SYNC_MAX_TAG || n < 1) return;
  RxTag &r = rx[tag];
  switch (d[0]) {
    case M_MAPPA:
      if (n >= LEN_MAPPA) {
        StatoLock l;
        TagStato &t = gStato.tag[tag];
        t.aperto = leggi16(d + 5);
        memcpy(t.mappa, d + 7, 128);
        t.mappaValida = true;
      }
      break;
    case M_BLOCCO: {
      if (n < LEN_BLOCCO) break;
      scartaCorrente(tag);  // quello di prima era incompleto
      int libero = -1;
      for (int i = 0; i < SYNC_FINESTRA; i++)
        if (rx[tag].s[i].stato == S_LIBERO) { libero = i; break; }
      if (libero < 0) {  // la tag ha superato la finestra o lo scrittore e' bloccato
        Comando c = {(uint8_t)tag, M_STOP, STOP_TROPPI_ERRORI, 0, 0};
        trasportoInvia(c);
        trasportoChiudi(tag);
        break;
      }
      Slot &s = r.s[libero];
      s.h.seq = leggi32(d + 1);
      s.h.fisico = leggi16(d + 5);
      s.h.crc = leggi32(d + 7);
      s.h.millisTag = leggi32(d + 11);
      s.mask = 0;
      s.stato = S_RICEVE;
      r.corr = libero;
      StatoLock l;  // "in trasmissione" (al piu' 2)
      TagStato &t = gStato.tag[tag];
      txToglie(t, s.h.seq);
      for (int i = 0; i < 2; i++)
        if (t.txFisico[i] == 0xFFFF) { t.txFisico[i] = s.h.fisico; t.txSeq[i] = s.h.seq; break; }
      break;
    }
    case M_FRAMMENTO: {
      if (n < LEN_FRAMMENTO) break;
      if (r.corr < 0) break;  // frammento senza intestazione: si ignora, il blocco non arrivera' completo
      Slot &s = r.s[r.corr];
      uint8_t k = d[5];
      if (leggi32(d + 1) != s.h.seq || k >= SYNC_N_FRAMMENTI) { scartaCorrente(tag); break; }
      memcpy(s.buf + k * SYNC_FRAMMENTO, d + 6, SYNC_FRAMMENTO);
      s.mask |= 1u << k;
      r.byteAcc += SYNC_FRAMMENTO;
      if (s.mask == 0xFFFFFFFFu) {  // completo: allo scrittore
        s.stato = S_CODA;
        int slot = r.corr;
        r.corr = -1;
        accoda(L_BLOCCO, tag, slot, s.h.seq);
      }
      break;
    }
    case M_CONFERMATO: {
      if (n < 5) break;
      uint32_t seq = leggi32(d + 1);
      {
        StatoLock l;  // in trasmissione -> validato: la mappa si aggiorna da sola
        TagStato &t = gStato.tag[tag];
        uint16_t f = txToglie(t, seq);
        if (f != 0xFFFF && t.mappaValida) mappaSet(t.mappa, f, 3);
        if (t.inAttesa) t.inAttesa--;
      }
      accoda(L_CONFERMATO, tag, 0, seq);
      break;
    }
    case M_FINE:
      scartaCorrente(tag);
      trasportoChiudi(tag);
      break;
    case M_ERRORE:
      LOGF("tag %d: ERRORE %u dalla tag\n", tag, n > 1 ? d[1] : 0);
      break;
  }
}
