// SwimTimer - protocollo di sincronizzazione tag -> display, versione 1 (docs/SINCRONIZZAZIONE.md §7).
// Lato tag. Il riferimento binario e' firmware/display-sync/protocollo.h: i due file devono combaciare byte per byte.
// Solo C++ standard (nessuna dipendenza da Arduino): costruzione dell'annuncio e dei messaggi.
#pragma once
#include <stdint.h>
#include <string.h>

#define SYNC_VERSIONE 1
#define SYNC_FRAMMENTO 128
#define SYNC_N_FRAMMENTI 32
#define SYNC_FINESTRA 2
#define SYNC_LEN_ANNUNCIO 22   // dati produttore compreso il company ID 0xFFFF
#define SYNC_LEN_STATO 151

// Stato annunciato
enum : uint8_t { ST_SONNO = 0, ST_PRONTA = 1, ST_REGISTRA = 2, ST_PIENA = 4, ST_ERRORE = 5, ST_SINCRONIZZA = 6 };
// Messaggi D->T (CONTROLLO)
enum : uint8_t { M_PRONTO = 0x10, M_CONFERMA = 0x11, M_RIPETI = 0x12, M_STOP = 0x13 };
// Messaggi T->D (DATI)
enum : uint8_t { M_MAPPA = 0x01, M_BLOCCO = 0x02, M_FRAMMENTO = 0x03, M_CONFERMATO = 0x04, M_FINE = 0x05, M_ERRORE = 0x06 };
// Codici dell'ERRORE T->D
enum : uint8_t { E_CRC_CONFERMA = 1, E_SEQ_SCONOSCIUTO = 2, E_FLASH = 3 };
// Bit di errore dell'annuncio
#define ERR_IMU 0x01
#define ERR_FLASH 0x02
#define ERR_BATT 0x04
#define SYNC_COLORE_NESSUNO 0xFF

static inline void sw16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
static inline void sw32(uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }

struct SyncAnnuncio {
  uint32_t id, ultimoSeq;
  uint8_t stato, batt20, pctMem, errori, colore;
  uint16_t inAttesa, secReg;
};

// 22 byte: 0xFFFF, 'S','W', versione, id, stato, batteria, % memoria, in attesa, ultimo seq, secondi, errori, colore
static inline void syncAnnuncioCodifica(const SyncAnnuncio &a, uint8_t *o) {
  o[0] = 0xFF; o[1] = 0xFF; o[2] = 'S'; o[3] = 'W'; o[4] = SYNC_VERSIONE;
  sw32(o + 5, a.id);
  o[9] = a.stato; o[10] = a.batt20; o[11] = a.pctMem;
  sw16(o + 12, a.inAttesa);
  sw32(o + 14, a.ultimoSeq);
  sw16(o + 18, a.secReg);
  o[20] = a.errori; o[21] = a.colore;
}

// MAPPA: tipo, millis tag, blocco aperto (0xFFFF = nessuno), 128 byte (512 x 2 bit). Lunghezza 135.
static inline uint16_t syncMappa(uint8_t *o, uint32_t millisTag, uint16_t aperto, const uint8_t *mappa128) {
  o[0] = M_MAPPA; sw32(o + 1, millisTag); sw16(o + 5, aperto); memcpy(o + 7, mappa128, 128);
  return 135;
}
// BLOCCO: tipo, seq, blocco fisico, crc32, millis del primo campione. Lunghezza 15.
static inline uint16_t syncBlocco(uint8_t *o, uint32_t seq, uint16_t fisico, uint32_t crc, uint32_t millisPrimo) {
  o[0] = M_BLOCCO; sw32(o + 1, seq); sw16(o + 5, fisico); sw32(o + 7, crc); sw32(o + 11, millisPrimo);
  return 15;
}
// FRAMMENTO: tipo, seq, indice (0..31), 128 byte. Lunghezza 134.
static inline uint16_t syncFrammentoIntest(uint8_t *o, uint32_t seq, uint8_t indice) {
  o[0] = M_FRAMMENTO; sw32(o + 1, seq); o[5] = indice;
  return 6;   // poi seguono 128 byte di dati
}
