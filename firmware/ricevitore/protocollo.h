// Protocollo tag <-> ricevitore (docs/SINCRONIZZAZIONE.md §7, versione 1) e formato dei frame USB (PROTOCOLLO-USB.md).
// Solo costanti e funzioni pure. Copia ridotta di firmware/display-sync/protocollo.h (stessi valori).
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define RIC_VERSIONE "ricevitore-0.1.6"

#define SYNC_VERSIONE 1
#define SYNC_MAX_TAG 2
#define SYNC_BLOCCO 4096
#define SYNC_FRAMMENTO 128               // frammento della versione 1 (tag <= 0.6.1)
#define SYNC_N_FRAMMENTI 32
#define SYNC_VERSIONE_PRONTO 2           // 0.1.6: dichiara nel PRONTO la versione 2 (frammenti da 238, DIAGNOSI); una tag vecchia risponde come prima
#define SYNC_FRAMMENTO2 238              // 244 di payload ATT (MTU 247) - 6 di intestazione; 18 frammenti per blocco, l'ultimo da 50 byte
#define SYNC_FINESTRA 2
#define SYNC_MAX_TENTATIVI 3
#define SYNC_MTU 247

#define SYNC_UUID_SERVIZIO "7a1e0101-5b1d-4c8e-9f3a-1d2c3b4a5e60"
#define SYNC_UUID_CONTROLLO "7a1e0102-5b1d-4c8e-9f3a-1d2c3b4a5e60"  // central -> tag, scrittura con risposta, cifrata
#define SYNC_UUID_DATI "7a1e0103-5b1d-4c8e-9f3a-1d2c3b4a5e60"       // tag -> central, notifiche

enum StatoAnnuncio : uint8_t { ST_SONNO = 0, ST_PRONTA = 1, ST_REGISTRA = 2, ST_PIENA = 4, ST_ERRORE = 5, ST_SINCRONIZZA = 6 };
// central -> tag
enum : uint8_t { M_PRONTO = 0x10, M_CONFERMA = 0x11, M_RIPETI = 0x12, M_STOP = 0x13 };
// tag -> central
enum : uint8_t { M_MAPPA = 0x01, M_BLOCCO = 0x02, M_FRAMMENTO = 0x03, M_CONFERMATO = 0x04, M_FINE = 0x05, M_ERRORE = 0x06, M_DIAGNOSI = 0x07 };
#define LEN_BLOCCO (1 + 4 + 2 + 4 + 4)
#define LEN_FRAMMENTO_INTEST (1 + 4 + 1)   // tipo, seq, indice; poi 128 o 238 byte (la dimensione la dice il BLOCCO, byte 15)
#define LEN_DIAG_FISSI 27                  // DIAGNOSI: vedi docs/SINCRONIZZAZIONE.md
enum : uint8_t { STOP_SD_PIENA = 1, STOP_ERRORE_SD = 2, STOP_TROPPI_ERRORI = 3 };

// ---- frame USB ----
#define FR_S0 0xA5
#define FR_S1 0x5A
#define FR_INTEST 13            // sync(2) tipo(1) id(4) num(4) len(2)
#define FR_MAX_PAYLOAD 4200
// dispositivo -> host
enum : uint8_t { FR_BLOCCO = 0x01, FR_STAT = 0x02, FR_EVENTO = 0x03, FR_HELLO = 0x04 };
// host -> dispositivo
enum : uint8_t { FR_OK = 0x20, FR_ERR = 0x21, FR_PRESENZA = 0x22 };

static inline uint16_t leggi16(const uint8_t *p) { return p[0] | (p[1] << 8); }
static inline uint32_t leggi32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static inline void scrivi16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
static inline void scrivi32(uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }

// CRC32 IEEE 802.3 (poly 0xEDB88320). Stato grezzo (init 0xFFFFFFFF), il risultato e' ~stato; vale 0xCBF43926 su "123456789".
static inline uint32_t crc32Agg(uint32_t crc, const uint8_t *p, size_t n) {
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
static inline uint32_t crc32Blocco(const uint8_t *p, size_t n) { return ~crc32Agg(0xFFFFFFFFu, p, n); }
