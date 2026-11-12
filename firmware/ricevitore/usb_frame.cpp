// Frame USB (PROTOCOLLO-USB.md): invio con CRC32 e parser dei frame dell'host.
#include "ric.h"

void usbInit() { Serial.begin(115200); }

static bool abbandona = false;   // true dopo un timeout di scrittura: il resto del frame in corso si salta

static void scrivi(const uint8_t *p, uint32_t n) {
  if (abbandona) return;
  uint32_t t0 = millis();
  while (n) {
    uint32_t k = n > 256 ? 256 : n;   // FIFO CDC = 256 B
    uint32_t w = Serial.write(p, k);
    if (w == 0) {
      // host fermo: si perde l'intero frame (CRC errato per l'host, niente OK, nessuna conferma)
      if (millis() - t0 > 20) { abbandona = true; return; }
      delayMicroseconds(100);   // FIFO piena: si aspetta che l'USB la svuoti, senza i >= 1 ms di delay()
      continue;
    }
    p += w;
    n -= w;
    t0 = millis();
  }
}

void usbInvia(uint8_t tipo, uint32_t id, uint32_t num, const uint8_t *p1, uint16_t l1, const uint8_t *p2, uint16_t l2) {
  if (!Serial) return;   // host non connesso (nessun DTR): il loop BLE non si blocca
  abbandona = false;
  uint8_t h[FR_INTEST];
  h[0] = FR_S0; h[1] = FR_S1; h[2] = tipo;
  scrivi32(h + 3, id);
  scrivi32(h + 7, num);
  scrivi16(h + 11, l1 + l2);
  uint32_t c = crc32Agg(0xFFFFFFFFu, h + 2, FR_INTEST - 2);
  if (p1 && l1) c = crc32Agg(c, p1, l1);
  if (p2 && l2) c = crc32Agg(c, p2, l2);
  c = ~c;
  uint8_t t[4];
  scrivi32(t, c);
  scrivi(h, FR_INTEST);
  if (p1 && l1) scrivi(p1, l1);
  if (p2 && l2) scrivi(p2, l2);
  scrivi(t, 4);
}

void evento(uint32_t id, uint32_t num, const char *txt) {
  size_t n = strlen(txt);
  if (n > 120) n = 120;
  usbInvia(FR_EVENTO, id, num, (const uint8_t *)txt, n);
}

// Parser dei frame dall'host (piccoli: al massimo 32 byte di payload)
void usbLeggi() {
  static uint8_t b[FR_INTEST + 32 + 4];
  static uint16_t pos = 0;
  static uint16_t tot = 0;   // lunghezza attesa del frame intero, 0 = intestazione non ancora completa
  while (Serial.available()) {
    int x = Serial.read();
    if (x < 0) break;
    if (pos == 0) { if (x == FR_S0) b[pos++] = x; continue; }
    if (pos == 1) {
      if (x == FR_S1) b[pos++] = x;
      else pos = (x == FR_S0) ? 1 : 0;
      continue;
    }
    b[pos++] = x;
    if (pos == FR_INTEST) {
      uint16_t len = leggi16(b + 11);
      if (len > 32) { pos = 0; continue; }
      tot = FR_INTEST + len + 4;
    }
    if (tot && pos == tot) {
      uint16_t len = tot - FR_INTEST - 4;
      uint32_t c = ~crc32Agg(0xFFFFFFFFu, b + 2, FR_INTEST - 2 + len);
      if (c == leggi32(b + FR_INTEST + len)) blocchiHost(b[2], leggi32(b + 3), leggi32(b + 7), b + FR_INTEST, len);
      pos = 0;
      tot = 0;
    }
  }
}
