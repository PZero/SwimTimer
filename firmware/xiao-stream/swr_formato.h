// SwimTimer - formato .swr della registrazione in vasca (formato 1 dalla 0.5.0, formato 2 dalla 0.6.0). Solo C++ standard, senza Arduino:
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
//
// FORMATO 2 (0.6.0, docs/SINCRONIZZAZIONE.md §8): la flash e' un anello di 512 blocchi da 4 KB (= settore) di 16 pagine.
//   Pagina 0 del blocco = intestazione di blocco, tipo 0xB1:
//     [0] 0xB1  [1] formato = 2  [2..3] numero di pagina fisica  [4..7] millis  [8..9] mV  [10] temp  [11] flag  [12..13] segmento
//     [14..15] CRC16 (come le altre pagine, ma con il campo CONFERMA considerato 0xFF)
//     [16] riservato 0xFF  [17..20] seq u32 (globale, mai riutilizzato)  [21..24] id tag u32  [25..251] 0xFF
//     [252..255] CONFERMA (formato 3): 4 x 0xFF = non confermato, altro = confermato. Parola di 4 byte TUTTA SUA:
//     la flash Puya riscrive l'intera parola da 4 byte (non fa l'AND dei bit), quindi nella parola non deve esserci altro.
//     Formato 2 (solo 2026-11-10, da leggere ma non scrivere): conferma nel byte 16 (rovinava il seq ai byte 17..19).
//   Pagine 1..15 = pagine del formato 1 (segmento 0xA5, dati 0xD1, chiusura 0xE0), [2..3] = numero di pagina fisica.
//   Pagine non scritte di un blocco chiuso = tutte 0xFF = valide (vuote).
//   CRC32 del blocco (messaggio BLOCCO): IEEE 802.3 sui 4096 byte con il byte 16 della pagina 0 a 0xFF.
#pragma once
#include <stdint.h>
#include <string.h>

#define SWR_PAGINA 256
#define SWR_TOT_PAGINE 8192            // 2 MB / 256
#define SWR_T_SEGMENTO 0xA5
#define SWR_T_DATI 0xD1
#define SWR_T_CHIUSURA 0xE0
#define SWR_FORMATO 1                  // versione scritta nella pagina di segmento
#define SWR_FORMATO_FLASH 3            // formato della flash (intestazione di blocco)
#define SWR_T_BLOCCO 0xB1
#define SWR_BLOCCO_BYTE 4096
#define SWR_PAGINE_BLOCCO 16
#define SWR_N_BLOCCHI 512
#define SWR_OFF_CONFERMA 252
#define SWR_LEN_CONFERMA 4
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
#define SWR_STOP_COMANDO 6    // SLEEP dalla pagina (o da un altro client BLE) durante la registrazione

static inline uint16_t swrCrc16(const uint8_t *p, uint32_t n, uint16_t crc = 0xFFFF) {
  while (n--) {
    uint8_t x = (crc >> 8) ^ *p++;
    x ^= x >> 4;
    crc = (crc << 8) ^ ((uint16_t)(x << 12)) ^ ((uint16_t)(x << 5)) ^ (uint16_t)x;
  }
  return crc;
}

// CRC16 di una pagina con il byte 16 considerato 0xFF (intestazione di blocco)
// Porta a 0xFF il campo conferma (formato 2: byte 16; formato 3: byte 252..255)
static inline void swrConfermaFF(uint8_t *pag) {
  if (pag[1] == 2) pag[16] = 0xFF;
  else memset(pag + SWR_OFF_CONFERMA, 0xFF, SWR_LEN_CONFERMA);
}
static inline bool swrConfermato(const uint8_t *pag) {
  if (pag[1] == 2) return pag[16] != 0xFF;
  for (int i = 0; i < SWR_LEN_CONFERMA; i++) if (pag[SWR_OFF_CONFERMA + i] != 0xFF) return true;
  return false;
}
static inline uint16_t swrCrc16Blocco(const uint8_t *pag) {
  uint8_t t[SWR_PAGINA];
  memcpy(t, pag, SWR_PAGINA);
  swrConfermaFF(t);
  uint16_t crc = swrCrc16(t, 14);
  return swrCrc16(t + 16, SWR_PAGINA - 16, crc);
}

// Intestazione di blocco (pagina 0): conferma = 0xFF, resto 0xFF
static inline void swrIntestazioneBlocco(uint8_t *pag, uint16_t numeroPagina, uint32_t millis, uint16_t mv, int8_t temp,
                                         uint8_t flag, uint16_t segmento, uint32_t seq, uint32_t idTag) {
  memset(pag, 0xFF, SWR_PAGINA);
  pag[0] = SWR_T_BLOCCO; pag[1] = SWR_FORMATO_FLASH;
  pag[2] = numeroPagina & 0xFF; pag[3] = numeroPagina >> 8;
  for (int i = 0; i < 4; i++) pag[4 + i] = (millis >> (8 * i)) & 0xFF;
  pag[8] = mv & 0xFF; pag[9] = mv >> 8;
  pag[10] = (uint8_t)temp; pag[11] = flag;
  pag[12] = segmento & 0xFF; pag[13] = segmento >> 8;
  for (int i = 0; i < 4; i++) { pag[17 + i] = (seq >> (8 * i)) & 0xFF; pag[21 + i] = (idTag >> (8 * i)) & 0xFF; }
  uint16_t crc = swrCrc16Blocco(pag);
  pag[14] = crc & 0xFF; pag[15] = crc >> 8;
}
static inline bool swrIntestazioneBloccoValida(const uint8_t *pag) {
  return pag[0] == SWR_T_BLOCCO && pag[1] == SWR_FORMATO_FLASH && swrCrc16Blocco(pag) == (uint16_t)(pag[14] | (pag[15] << 8));
}
static inline uint32_t swrLeggi32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

// CRC32 IEEE 802.3 (poly 0xEDB88320), a nibble. Si usa a pezzi: stato iniziale 0xFFFFFFFF, alla fine ~stato.
static inline uint32_t swrCrc32Aggiorna(uint32_t crc, const uint8_t *p, uint32_t n) {
  static const uint32_t T[16] = {0x00000000, 0x1DB71064, 0x3B6E20C8, 0x26D930AC, 0x76DC4190, 0x6B6B51F4,
                                 0x4DB26158, 0x5005713C, 0xEDB88320, 0xF00F9344, 0xD6D6A3E8, 0xCB61B38C,
                                 0x9B64C2B0, 0x86D3D2D4, 0xA00AE278, 0xBDBDF21C};
  while (n--) {
    crc ^= *p++;
    crc = (crc >> 4) ^ T[crc & 15];
    crc = (crc >> 4) ^ T[crc & 15];
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
