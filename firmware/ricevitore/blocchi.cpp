// Assemblaggio dei blocchi (BLOCCO + 32 FRAMMENTI), inoltro all'host, conferma alla tag SOLO dopo l'OK dell'host, statistiche.
// Tutto gira nel loop (mai nei callback BLE).
#include "ric.h"

static const uint32_t ATTESA_OK_MS = 20000;   // OK dell'host mancante: si chiude, la tag reinvia

enum : uint8_t { S_LIBERO = 0, S_RICEVE = 1, S_ATTESA_HOST = 2 };
struct Slot {
  uint8_t stato;
  uint16_t fisico;
  uint8_t frag, nFrag;                         // dimensione dei frammenti (128 o 238) e loro numero (32 o 18)
  uint32_t seq, crc, millisTag, mask, tInvio;
  uint32_t tPrimo, tUltimo, tFineUsb, usbMs;   // arrivo del primo e dell'ultimo frammento (dal callback), fine invio USB, durata invio USB
};
// Misure per blocco (0.1.5): periodo fra blocchi completi, radio (primo->ultimo frammento), USB, host (invio finito -> OK), tag (OK -> CONFERMATO)
struct Misura { uint32_t tOk, radio, usb, host, periodo; };
static Misura mq[SYNC_MAX_TAG][4];           // blocchi confermati all'host e in attesa di CONFERMATO dalla tag (finestra 2)
static uint8_t mqT[SYNC_MAX_TAG], mqC[SYNC_MAX_TAG];
static uint32_t ultCompleto[SYNC_MAX_TAG];
static uint32_t somma[SYNC_MAX_TAG][5];       // periodo, radio, usb, host, tag
static uint8_t nMis[SYNC_MAX_TAG];
static uint8_t buf[SYNC_MAX_TAG][SYNC_FINESTRA][SYNC_BLOCCO];
static Slot sl[SYNC_MAX_TAG][SYNC_FINESTRA];
static int8_t corr[SYNC_MAX_TAG] = {-1, -1};
static uint32_t ultSeqRip[SYNC_MAX_TAG];
static uint8_t nRip[SYNC_MAX_TAG];

static void comando(int s, uint8_t tipo, uint32_t seq, uint32_t crc, uint8_t motivo) {
  uint8_t b[9];
  b[0] = tipo;
  uint8_t n = 1;
  if (tipo == M_CONFERMA) { scrivi32(b + 1, seq); scrivi32(b + 5, crc); n = 9; }
  else if (tipo == M_RIPETI) { scrivi32(b + 1, seq); n = 5; }
  else if (tipo == M_STOP) { b[1] = motivo; n = 2; }
  if (!bleScrivi(s, b, n)) { evento(tags[s].id, tipo, "scrittura CONTROLLO fallita"); bleChiudi(s); }
}

static void liberaTutto(int s) {
  for (int k = 0; k < SYNC_FINESTRA; k++) sl[s][k].stato = S_LIBERO;
  corr[s] = -1;
  nRip[s] = 0;
  mqT[s] = mqC[s] = 0;
  ultCompleto[s] = 0;
}

static void ripeti(int s, uint32_t seq) {
  if (seq == ultSeqRip[s]) nRip[s]++;
  else { ultSeqRip[s] = seq; nRip[s] = 1; }
  if (nRip[s] > SYNC_MAX_TENTATIVI) {
    evento(tags[s].id, seq, "troppi RIPETI: STOP e chiusura");
    comando(s, M_STOP, 0, 0, STOP_TROPPI_ERRORI);
    bleChiudi(s);
    return;
  }
  comando(s, M_RIPETI, seq, 0, 0);
}

// Blocco rimasto a meta' (nuovo BLOCCO, FINE, frammento fuori posto, coda persa): si chiede RIPETI
static void scartaCorrente(int s) {
  if (corr[s] < 0) return;
  Slot &x = sl[s][corr[s]];
  uint32_t seq = x.seq;
  x.stato = S_LIBERO;
  corr[s] = -1;
  tags[s].scartati++;
  ripeti(s, seq);
}

static void inoltra(int s, int k, uint32_t now) {
  Slot &x = sl[s][k];
  uint8_t h[10];
  scrivi16(h, x.fisico);
  scrivi32(h + 2, x.crc);
  scrivi32(h + 6, x.millisTag);
  x.stato = S_ATTESA_HOST;
  x.tInvio = now;
  tags[s].ricevuti++;
  usbInvia(FR_BLOCCO, tags[s].id, x.seq, h, 10, buf[s][k], SYNC_BLOCCO);
  x.tFineUsb = millis();
  x.usbMs = x.tFineUsb - now;
}

static void messaggio(const RxMsg &m, uint32_t now) {
  int s = m.tag;
  const uint8_t *d = m.d;
  size_t n = m.len;
  switch (d[0]) {
    case M_BLOCCO: {
      if (n < LEN_BLOCCO) break;
      scartaCorrente(s);
      int k = -1;
      for (int i = 0; i < SYNC_FINESTRA; i++) if (sl[s][i].stato == S_LIBERO) { k = i; break; }
      if (k < 0) {   // la tag ha superato la finestra
        evento(tags[s].id, 0, "finestra superata: STOP e chiusura");
        comando(s, M_STOP, 0, 0, STOP_TROPPI_ERRORI);
        bleChiudi(s);
        break;
      }
      Slot &x = sl[s][k];
      x.seq = leggi32(d + 1);
      x.fisico = leggi16(d + 5);
      x.crc = leggi32(d + 7);
      x.millisTag = leggi32(d + 11);
      // tag 0.6.2+: byte 15 = dimensione dei frammenti (238 o 128); BLOCCO da 15 byte (tag vecchia) = 128
      x.frag = (n >= LEN_BLOCCO + 1 && (d[15] == SYNC_FRAMMENTO2 || d[15] == SYNC_FRAMMENTO)) ? d[15] : SYNC_FRAMMENTO;
      x.nFrag = (SYNC_BLOCCO + x.frag - 1) / x.frag;
      x.mask = 0;
      x.stato = S_RICEVE;
      corr[s] = k;
      break;
    }
    case M_FRAMMENTO: {
      if (n < LEN_FRAMMENTO_INTEST || corr[s] < 0) break;
      int k = corr[s];
      Slot &x = sl[s][k];
      uint8_t i = d[5];
      uint16_t off = (uint16_t)i * x.frag, ln = n - LEN_FRAMMENTO_INTEST;
      uint16_t atteso = SYNC_BLOCCO - off < x.frag ? SYNC_BLOCCO - off : x.frag;   // l'ultimo frammento e' piu' corto (50 byte con 238)
      if (leggi32(d + 1) != x.seq || i >= x.nFrag || ln != atteso) { scartaCorrente(s); break; }
      memcpy(buf[s][k] + off, d + LEN_FRAMMENTO_INTEST, ln);
      if (x.mask == 0) x.tPrimo = m.t;
      x.mask |= 1u << i;
      tags[s].bytes += ln;
      if (x.mask == (x.nFrag >= 32 ? 0xFFFFFFFFu : ((1u << x.nFrag) - 1))) {
        x.tUltimo = m.t;
        corr[s] = -1;
        if (crc32Blocco(buf[s][k], SYNC_BLOCCO) != x.crc) {
          uint32_t seq = x.seq;
          x.stato = S_LIBERO;
          tags[s].scartati++;
          evento(tags[s].id, seq, "CRC32 del blocco errato: RIPETI");
          ripeti(s, seq);
        } else {
          inoltra(s, k, now);
        }
      }
      break;
    }
    case M_CONFERMATO:
      tags[s].confermati++;
      if (mqC[s] != mqT[s]) {   // misura di questo blocco (FIFO: la tag conferma in ordine di CONFERMA)
        Misura &q = mq[s][mqC[s]++ & 3];
        uint32_t v[5] = {q.periodo, q.radio, q.usb, q.host, m.t - q.tOk};
        for (int j = 0; j < 5; j++) somma[s][j] += v[j];
        if (++nMis[s] >= 10) {
          char tx[120];
          snprintf(tx, sizeof(tx), "10 blocchi, medie ms periodo/radio/usb/host/tag %lu/%lu/%lu/%lu/%lu; loop max %lu ms",
                   (unsigned long)(somma[s][0] / 10), (unsigned long)(somma[s][1] / 10), (unsigned long)(somma[s][2] / 10),
                   (unsigned long)(somma[s][3] / 10), (unsigned long)(somma[s][4] / 10), (unsigned long)loopMaxMs);
          evento(tags[s].id, somma[s][0] / 10, tx);
          memset(somma[s], 0, sizeof(somma[s]));
          nMis[s] = 0;
          loopMaxMs = 0;
        }
      }
      break;
    case M_FINE:
      scartaCorrente(s);
      evento(tags[s].id, n >= 5 ? leggi32(d + 1) : 0, "FINE dalla tag (num = ultimo seq)");
      bleChiudi(s);
      break;
    case M_ERRORE:
      evento(tags[s].id, n > 1 ? d[1] : 0, "ERRORE dalla tag (num = codice)");
      break;
    case M_DIAGNOSI: {   // 0.1.6: motivo dell'ultimo reset della tag + ultime righe del suo diario, inoltrati come EVENTO (l'host li scrive nel log)
      if (n < LEN_DIAG_FISSI) break;
      char tx[200];   // 0.1.7: 200 (con 120 la riga, ~165 caratteri, veniva troncata)
      snprintf(tx, sizeof(tx), "DIAGNOSI tag: reset causa %u RESETREAS 0x%lX guasto %u pc 0x%lX lr 0x%lX cfsr 0x%lX; stack libero B loop/cb/ble %u/%u/%u; diario %u righe",
               d[2], (unsigned long)leggi32(d + 4), d[3], (unsigned long)leggi32(d + 8), (unsigned long)leggi32(d + 12), (unsigned long)leggi32(d + 16),
               leggi16(d + 20), leggi16(d + 22), leggi16(d + 24), d[26]);
      evento(tags[s].id, d[2], tx);
      uint32_t p = LEN_DIAG_FISSI, riga = 0;
      while (p < n) {
        char l[128] = "diario tag: ";
        size_t o = strlen(l);
        while (p < n && d[p] != '\n' && o < sizeof(l) - 1) l[o++] = (char)d[p++];
        l[o] = 0;
        while (p < n && d[p] != '\n') p++;   // riga troppo lunga: si scarta il resto
        p++;
        evento(tags[s].id, ++riga, l);
      }
      break;
    }
    case M_DIAGNOSI2: {   // 0.1.7 (tag 0.6.4+): collegamento, VBUS, disconnessioni, stack BLE; una riga key=value (l'host la legge)
      if (n < LEN_DIAG2) break;
      char tx[200];
      uint32_t iv = leggi16(d + 2) * 125;   // centesimi di ms
      snprintf(tx, sizeof(tx), "DIAGNOSI2 tag: int=%lu.%02lu mtu=%u dle=%u phy=%u vbus=%u vbus_su=%u vbus_giu=%u vbus_ms=%lu hci3E=%u disc=%u ultdisc=0x%02X stkble=%u tagms=%lu",
               (unsigned long)(iv / 100), (unsigned long)(iv % 100), leggi16(d + 4), leggi16(d + 6), d[8], d[9], leggi16(d + 10), leggi16(d + 12),
               (unsigned long)leggi32(d + 14), leggi16(d + 18), leggi16(d + 20), d[22], leggi16(d + 24), (unsigned long)leggi32(d + 26));
      evento(tags[s].id, leggi16(d + 18), tx);
      break;
    }
  }
}

void blocchiElabora(uint32_t now) {
  RxMsg m;
  for (int s = 0; s < SYNC_MAX_TAG; s++) {
    if (bleScollegata(s)) {
      if (corr[s] >= 0 || sl[s][0].stato || sl[s][1].stato) evento(tags[s].id, 0, "scollegata con blocchi non confermati: la tag li reinvia");
      bleScartaTag(s);
      liberaTutto(s);
    }
  }
  while (bleProssimo(m)) {
    if (m.len == 0) continue;   // marcata da scartare
    Fase f = tags[m.tag].fase;
    if (f == F_IDLE) { if (m.d[0] != M_FINE && m.d[0] != M_ERRORE) continue; }
    else if (f != F_ATTIVA) continue;
    tags[m.tag].ultimoMsg = now;
    for (int s = 0; s < SYNC_MAX_TAG; s++)
      if (bleSvuotata(s)) { evento(tags[s].id, 0, "coda notifiche piena: blocco scartato"); scartaCorrente(s); }
    messaggio(m, now);
  }
  for (int s = 0; s < SYNC_MAX_TAG; s++) {
    if (bleSvuotata(s)) { evento(tags[s].id, 0, "coda notifiche piena: blocco scartato"); scartaCorrente(s); }
    for (int k = 0; k < SYNC_FINESTRA; k++)
      if (sl[s][k].stato == S_ATTESA_HOST && now - sl[s][k].tInvio > ATTESA_OK_MS) {
        evento(tags[s].id, sl[s][k].seq, "OK dell'host mancante: chiusura, niente conferma");
        sl[s][k].stato = S_LIBERO;
        bleChiudi(s);
      }
  }
}

// Frame dall'host
void blocchiHost(uint8_t tipo, uint32_t id, uint32_t num, const uint8_t *p, uint16_t len) {
  if (tipo == FR_PRESENZA) { ultimaPresenza = millis() ? millis() : 1; return; }
  int s = tagPerId(id);
  if (s < 0 || (tipo != FR_OK && tipo != FR_ERR)) return;
  int k = -1;
  for (int i = 0; i < SYNC_FINESTRA; i++)
    if (sl[s][i].stato == S_ATTESA_HOST && sl[s][i].seq == num) { k = i; break; }
  if (k < 0) { evento(id, num, "OK/ERR per un blocco sconosciuto: ignorato"); return; }
  Slot &x = sl[s][k];
  if (tipo == FR_OK) {
    if (len < 4 || leggi32(p) != x.crc) { evento(id, num, "OK con CRC diverso: ignorato"); return; }
    comando(s, M_CONFERMA, x.seq, x.crc, 0);   // solo ora: l'host ha salvato e riletto il blocco
    if ((uint8_t)(mqT[s] - mqC[s]) < 4) {      // misura: periodo = distanza dal blocco completo precedente (0 se e' il primo o dopo una pausa > 5 s)
      Misura &q = mq[s][mqT[s]++ & 3];
      uint32_t per = (ultCompleto[s] && x.tUltimo - ultCompleto[s] < 5000) ? x.tUltimo - ultCompleto[s] : 0;
      q.tOk = millis();
      q.radio = x.tUltimo - x.tPrimo;
      q.usb = x.usbMs;
      q.host = q.tOk - x.tFineUsb;
      q.periodo = per ? per : q.radio + q.usb + q.host;
    }
    ultCompleto[s] = x.tUltimo;
    x.stato = S_LIBERO;
  } else {
    evento(id, num, "host: errore di salvataggio, STOP");
    comando(s, M_STOP, 0, 0, len ? p[0] : STOP_ERRORE_SD);
    x.stato = S_LIBERO;
    bleChiudi(s);
  }
}

// Statistiche di ogni secondo, un frame per tag conosciuta
void statInvia(uint32_t now) {
  for (int s = 0; s < SYNC_MAX_TAG; s++) {
    TagInfo &t = tags[s];
    if (!t.usata) continue;
    uint32_t eta = now - t.vistoMs;
    uint8_t link = 0;
    switch (t.fase) {
      case F_IDLE: link = eta < 3000 ? 1 : 0; break;
      case F_CONNETTE: case F_CONN_OK: link = 2; break;
      case F_SICUREZZA: case F_SICURA: link = 3; break;
      case F_ATTIVA: link = 4; break;
      case F_CHIUSURA: link = 0; break;
    }
    uint32_t bps = t.bytes;
    t.bytes = 0;
    uint8_t p[33];
    p[0] = s;
    p[1] = link;
    p[2] = (uint8_t)t.rssi;
    p[3] = t.stato;
    p[4] = t.batt20;
    p[5] = t.pctMem;
    p[6] = t.errori;
    scrivi16(p + 7, t.inAttesa);
    scrivi32(p + 9, bps);
    scrivi32(p + 13, t.ricevuti);
    scrivi32(p + 17, t.confermati);
    scrivi16(p + 21, t.scartati);
    scrivi32(p + 23, t.msAvv);
    scrivi32(p + 27, t.ultimoSeq);
    scrivi16(p + 31, eta > 65535 ? 65535 : eta);
    usbInvia(FR_STAT, t.id, now, p, sizeof(p));
  }
}
