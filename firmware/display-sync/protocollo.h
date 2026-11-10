// Protocollo di sincronizzazione tag -> display, versione 1 (docs/SINCRONIZZAZIONE.md §7).
// Solo costanti, strutture e funzioni pure (CRC, lettura/scrittura little-endian).
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#ifndef SWIM_DEMO
#define SWIM_DEMO 0  // 1 = tag simulate, nessun BLE (ambiente "demo")
#endif

// Verifica del CRC16 di ogni pagina .swr. Formato 2 (docs/SINCRONIZZAZIONE.md §8): pagina tutta 0xFF = vuota = valida;
// pagina 0xB1 (intestazione di blocco) = CRC16 con il byte 16 (conferma) considerato 0xFF; altre pagine: byte 0..13 e 16..255.
#define SYNC_VERIFICA_CRC16_PAGINA 1

#define SYNC_VERSIONE 1
#define SYNC_MAX_TAG 3
#define SYNC_BLOCCO 4096        // byte di un blocco (= settore flash della tag)
#define SYNC_FRAMMENTO 128      // byte di dati in un frammento
#define SYNC_N_FRAMMENTI 32     // 4096 / 128
#define SYNC_PAGINA 256         // pagina .swr
#define SYNC_PAGINE_BLOCCO 16
#define SYNC_N_BLOCCHI 512      // blocchi della flash da 2 MB
#define SYNC_FINESTRA 2         // blocchi trasmessi e non confermati, al massimo
#define SYNC_MAX_TENTATIVI 3    // RIPETI prima di STOP motivo 3

// UUID del servizio GATT di sincronizzazione
#define SYNC_UUID_SERVIZIO "7a1e0101-5b1d-4c8e-9f3a-1d2c3b4a5e60"
#define SYNC_UUID_CONTROLLO "7a1e0102-5b1d-4c8e-9f3a-1d2c3b4a5e60"  // D->T, scrittura con risposta, cifrata
#define SYNC_UUID_DATI "7a1e0103-5b1d-4c8e-9f3a-1d2c3b4a5e60"       // T->D, notifiche
#define SYNC_MTU 247

// Stato annunciato dalla tag
enum StatoAnnuncio : uint8_t {
  ST_SONNO = 0, ST_PRONTA = 1, ST_REGISTRA = 2, ST_RISERVATO_3 = 3 /* era "al muro": tolto, la tag non interpreta il movimento */, ST_PIENA = 4, ST_ERRORE = 5, ST_SINCRONIZZA = 6
};

// Messaggi D->T (CONTROLLO)
enum : uint8_t { M_PRONTO = 0x10, M_CONFERMA = 0x11, M_RIPETI = 0x12, M_STOP = 0x13 };
// Messaggi T->D (DATI)
enum : uint8_t {
  M_MAPPA = 0x01, M_BLOCCO = 0x02, M_FRAMMENTO = 0x03, M_CONFERMATO = 0x04, M_FINE = 0x05, M_ERRORE = 0x06
};
// Lunghezze dei messaggi T->D (compreso il byte di tipo)
#define LEN_MAPPA (1 + 4 + 2 + 128)
#define LEN_BLOCCO (1 + 4 + 2 + 4 + 4)
#define LEN_FRAMMENTO (1 + 4 + 1 + SYNC_FRAMMENTO)
// Motivi di STOP
enum : uint8_t { STOP_SD_PIENA = 1, STOP_ERRORE_SD = 2, STOP_TROPPI_ERRORI = 3 };

// ---- lettura/scrittura little-endian ----
static inline uint16_t leggi16(const uint8_t *p) { return p[0] | (p[1] << 8); }
static inline uint32_t leggi32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static inline void scrivi16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
static inline void scrivi32(uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }

// ---- CRC ----
// CRC32 IEEE 802.3 (poly 0xEDB88320, init/xorout 0xFFFFFFFF), a nibble; vale 0xCBF43926 su "123456789".
static inline uint32_t crc32Blocco(const uint8_t *p, size_t n, uint32_t crc = 0xFFFFFFFFu) {
  static const uint32_t T[16] = {0x00000000, 0x1DB71064, 0x3B6E20C8, 0x26D930AC, 0x76DC4190, 0x6B6B51F4,
                                 0x4DB26158, 0x5005713C, 0xEDB88320, 0xF00F9344, 0xD6D6A3E8, 0xCB61B38C,
                                 0x9B64C2B0, 0x86D3D2D4, 0xA00AE278, 0xBDBDF21C};
  while (n--) {
    crc ^= *p++;
    crc = (crc >> 4) ^ T[crc & 15];
    crc = (crc >> 4) ^ T[crc & 15];
  }
  return ~crc;
}

// CRC16-CCITT (init 0xFFFF): lo stesso di firmware/xiao-stream/swr_formato.h
static inline uint16_t crc16Swr(const uint8_t *p, uint32_t n, uint16_t crc = 0xFFFF) {
  while (n--) {
    uint8_t x = (crc >> 8) ^ *p++;
    x ^= x >> 4;
    crc = (crc << 8) ^ ((uint16_t)(x << 12)) ^ ((uint16_t)(x << 5)) ^ (uint16_t)x;
  }
  return crc;
}

// CRC16 di una pagina: byte 0..13 e 16..255; per l'intestazione di blocco 0xB1 il byte 16 (conferma) vale 0xFF nel calcolo
static inline uint16_t crc16Pagina(const uint8_t *p) {
  uint16_t c = crc16Swr(p, 14);
  if (p[0] == 0xB1) {  // campo conferma a 0xFF: formato 2 byte 16, formato 3 parola 252..255
    uint8_t t[SYNC_PAGINA];
    memcpy(t, p, SYNC_PAGINA);
    if (t[1] == 2) t[16] = 0xFF;
    else memset(t + 252, 0xFF, 4);
    return crc16Swr(t + 16, SYNC_PAGINA - 16, c);
  }
  return crc16Swr(p + 16, SYNC_PAGINA - 16, c);
}

// Pagina .swr da 256 byte: vuota (tutta 0xFF) = valida; altrimenti CRC16 contro quello a 14..15
static inline bool paginaValida(const uint8_t *p) {
  bool vuota = true;
  for (int i = 0; i < SYNC_PAGINA; i++)
    if (p[i] != 0xFF) { vuota = false; break; }
  if (vuota) return true;
  return crc16Pagina(p) == leggi16(p + 14);
}

// Scrive in `p` il CRC16 della pagina (usato dalla demo)
static inline void paginaSigilla(uint8_t *p) { scrivi16(p + 14, crc16Pagina(p)); }

// Tutte le pagine del blocco (se la verifica e' attiva)
static inline bool bloccoPagineValide(const uint8_t *b) {
#if SYNC_VERIFICA_CRC16_PAGINA
  for (int i = 0; i < SYNC_PAGINE_BLOCCO; i++)
    if (!paginaValida(b + i * SYNC_PAGINA)) return false;
#endif
  return true;
}

// ---- colore e nome della tag (§7) ----
#define SYNC_COLORE_NESSUNO 0xFF
#define SYNC_NOME_MAX 12
// Tavolozza 0..9 (la stessa di tools/display.html), RGB 8 bit
static const uint8_t SYNC_TAVOLOZZA[10][3] = {
    {0x3b, 0x82, 0xf6}, {0xf9, 0x73, 0x16}, {0xa8, 0x55, 0xf7}, {0x06, 0xb6, 0xd4}, {0xec, 0x48, 0x99},
    {0xea, 0xb3, 0x08}, {0xe5, 0xe7, 0xeb}, {0x84, 0xcc, 0x16}, {0xef, 0x44, 0x44}, {0xa1, 0x62, 0x07}};

// ---- annuncio (dati produttore) ----
struct Annuncio {
  uint32_t id;
  uint8_t stato, batt20, pctMem, errori;
  uint16_t inAttesa, secReg;
  uint32_t ultimoSeq;
  uint8_t colore;            // 0..9, 0xFF = non impostato (byte 21 dell'annuncio)
  char nome[SYNC_NOME_MAX + 1];  // nome locale dalla scan response ("" = non ancora letto); lo riempie lo scanner
};

// md = dati produttore comprensivi del company ID (come li da' getManufacturerData)
static inline bool annuncioLeggi(const uint8_t *md, size_t n, Annuncio &a) {
  if (n < 21 || md[0] != 0xFF || md[1] != 0xFF || md[2] != 'S' || md[3] != 'W' || md[4] != SYNC_VERSIONE) return false;
  a.id = leggi32(md + 5);
  a.stato = md[9];
  a.batt20 = md[10];
  a.pctMem = md[11];
  a.inAttesa = leggi16(md + 12);
  a.ultimoSeq = leggi32(md + 14);
  a.secReg = leggi16(md + 18);
  a.errori = md[20];
  a.colore = (n >= 22 && md[21] <= 9) ? md[21] : SYNC_COLORE_NESSUNO;
  a.nome[0] = 0;
  return true;
}

// ---- comandi display -> tag ----
struct Comando {
  uint8_t tag;     // indice dello spicchio (0..2)
  uint8_t tipo;    // M_PRONTO, M_CONFERMA, M_RIPETI, M_STOP
  uint8_t motivo;  // solo STOP
  uint32_t seq, crc;
};

// Codifica il comando nel buffer (almeno 10 byte); ritorna la lunghezza
static inline size_t comandoCodifica(const Comando &c, uint8_t *o) {
  o[0] = c.tipo;
  switch (c.tipo) {
    case M_PRONTO: o[1] = SYNC_VERSIONE; return 2;
    case M_CONFERMA: scrivi32(o + 1, c.seq); scrivi32(o + 5, c.crc); return 9;
    case M_RIPETI: scrivi32(o + 1, c.seq); return 5;
    case M_STOP: o[1] = c.motivo; return 2;
  }
  return 1;
}
