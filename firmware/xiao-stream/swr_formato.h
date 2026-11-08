// SwimTimer - formato .swr della registrazione in vasca (0.5.0). Solo C++ standard, senza Arduino:
// il decodificatore Python (swr.py) fa l'operazione inversa byte per byte.
//
// La flash e' una sequenza di pagine da 256 byte, scritte una sola volta, in ordine, da 0 in avanti:
//   [0]      tipo: 0xA5 segmento (inizio di una registrazione = un risveglio), 0xD1 dati, 0xE0 chiusura. 0xFF = pagina libera
//   [1]      parametro: 0xA5 = versione del formato (1); 0xD1 = numero di campioni nella pagina; 0xE0 = motivo dello stop
//   [2..3]   uint16 numero di pagina (deve coincidere con la posizione in flash)
//   [4..7]   uint32 millis (dall'accensione) del primo campione della pagina
//   [8..9]   uint16 batteria in mV (0 = non letta)
//   [10]     int8 temperatura del die (gradi)
//   [11]     flag: bit0 = prima pagina dati del segmento, bit1 = interruzione dei dati (overrun del FIFO) prima di questa pagina
//   [12..13] uint16 indice del segmento
//   [14..15] uint16 CRC16-CCITT (init 0xFFFF) dei byte 0..13 e 16..255
//   [16..255] payload (240 byte)
// Pagina dati: campione assoluto (6 x int16 LE: ax,ay,az,gx,gy,gz = 12 byte), poi per ogni campione successivo
//   o 6 x int8 (differenze dal campione precedente, ciascuna in -127..127), oppure il byte 0x80 seguito da 12 byte assoluti
//   (escape: almeno una differenza fuori scala). I byte non usati restano 0xFF. Ogni pagina si decodifica da sola.
// Segmento (payload): [16..17] ODR x10 (2083), [18..19] ug/LSB acc (488), [20..21] mdps/LSB giro (35), [22..27] bias giro raw 3 x int16,
//   [28] causa reset, [29] tocchi extra del risveglio, [30..37] versione firmware (testo, 0-terminata)
// Chiusura (payload): [16..19] uint32 campioni totali del segmento, [20..23] uint32 pagine del segmento
#pragma once
#include <stdint.h>
#include <string.h>

#define SWR_PAGINA 256
#define SWR_TOT_PAGINE 8192            // 2 MB / 256
#define SWR_T_SEGMENTO 0xA5
#define SWR_T_DATI 0xD1
#define SWR_T_CHIUSURA 0xE0
#define SWR_FORMATO 1
#define SWR_ODR_X10 2083
#define SWR_ACC_UG_LSB 488
#define SWR_GIRO_MDPS_LSB 35
#define SWR_FLAG_PRIMA 0x01
#define SWR_FLAG_GAP 0x02
#define SWR_STOP_QUIETE 1
#define SWR_STOP_PIENA 2
#define SWR_STOP_BATTERIA 3
#define SWR_STOP_USB 4        // USB collegata durante la registrazione: chiude e riparte in modalita' normale
#define SWR_STOP_ERRORE 5

static inline uint16_t swrCrc16(const uint8_t *p, uint32_t n, uint16_t crc = 0xFFFF) {
  while (n--) {
    uint8_t x = (crc >> 8) ^ *p++;
    x ^= x >> 4;
    crc = (crc << 8) ^ ((uint16_t)(x << 12)) ^ ((uint16_t)(x << 5)) ^ (uint16_t)x;
  }
  return crc;
}

// Scrive l'intestazione e la CRC; il payload (byte 16..255) deve essere gia' nella pagina.
static inline void swrIntestazione(uint8_t *pag, uint8_t tipo, uint8_t param, uint16_t numero, uint32_t millis,
                                   uint16_t mv, int8_t temp, uint8_t flag, uint16_t segmento) {
  pag[0] = tipo; pag[1] = param;
  pag[2] = numero & 0xFF; pag[3] = numero >> 8;
  pag[4] = millis & 0xFF; pag[5] = (millis >> 8) & 0xFF; pag[6] = (millis >> 16) & 0xFF; pag[7] = millis >> 24;
  pag[8] = mv & 0xFF; pag[9] = mv >> 8;
  pag[10] = (uint8_t)temp; pag[11] = flag;
  pag[12] = segmento & 0xFF; pag[13] = segmento >> 8;
  uint16_t crc = swrCrc16(pag, 14);
  crc = swrCrc16(pag + 16, SWR_PAGINA - 16, crc);
  pag[14] = crc & 0xFF; pag[15] = crc >> 8;
}

// Codificatore delle pagine dati. Uso: se (nc > 0 && !sta(s)) { chiudi(...); scrivi pag; azzera(); } aggiungi(s, t);
struct SwrCodificatore {
  uint8_t pag[SWR_PAGINA];
  uint16_t pos;            // prossimo byte libero
  uint8_t nc;              // campioni nella pagina
  int16_t prev[6];
  uint32_t tPrimo;
  SwrCodificatore() { azzera(); }
  void azzera() { memset(pag, 0xFF, SWR_PAGINA); pos = 16; nc = 0; }
  static bool inScala(const int16_t *s, const int16_t *p) {
    for (int i = 0; i < 6; i++) { int32_t d = (int32_t)s[i] - p[i]; if (d < -127 || d > 127) return false; }
    return true;
  }
  // true se il campione entra ancora nella pagina corrente (con nc == 0 entra sempre)
  bool sta(const int16_t *s) const {
    if (nc == 0) return true;
    return pos + (inScala(s, prev) ? 6 : 13) <= SWR_PAGINA;
  }
  void aggiungi(const int16_t *s, uint32_t t) {
    if (nc == 0) {
      tPrimo = t;
      putAssoluto(s);
    } else if (inScala(s, prev)) {
      for (int i = 0; i < 6; i++) pag[pos++] = (uint8_t)(int8_t)(s[i] - prev[i]);
    } else {
      pag[pos++] = 0x80;
      putAssoluto(s);
    }
    for (int i = 0; i < 6; i++) prev[i] = s[i];
    nc++;
  }
  void putAssoluto(const int16_t *s) {
    for (int i = 0; i < 6; i++) { pag[pos++] = (uint8_t)(s[i] & 0xFF); pag[pos++] = (uint8_t)((uint16_t)s[i] >> 8); }
  }
  void chiudi(uint16_t numero, uint16_t segmento, uint16_t mv, int8_t temp, uint8_t flag) {
    swrIntestazione(pag, SWR_T_DATI, nc, numero, tPrimo, mv, temp, flag, segmento);
  }
};
