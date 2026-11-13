// SwimTimer - protocollo di sincronizzazione tag -> display, versione 1 (docs/SINCRONIZZAZIONE.md §7).
// Lato tag. Il riferimento binario e' firmware/display-sync/protocollo.h: i due file devono combaciare byte per byte.
// Solo C++ standard (nessuna dipendenza da Arduino): costruzione dell'annuncio e dei messaggi.
#pragma once
#include <stdint.h>
#include <string.h>

#define SYNC_VERSIONE 1
#define SYNC_FRAMMENTO 128      // frammento della versione 1 (display-sync e ricevitore <= 0.1.5)
#define SYNC_N_FRAMMENTI 32
// Versione 2 (dal 0.6.2): il central la dichiara nel PRONTO (secondo byte = 2). Con MTU 247 il frammento e' di 238 byte
// (244 di payload ATT - 6 di intestazione tipo/seq/indice): 18 frammenti per blocco, l'ultimo da 50 byte. Il BLOCCO diventa di 16 byte:
// il byte 15 e' la dimensione dei frammenti di quel blocco (238 oppure 128: ricaduta se l'MTU e' minore di 247).
#define SYNC_VERSIONE_PRONTO2 2
#define SYNC_FRAMMENTO2 238
#define SYNC_BLOCCO_BYTE 4096
#define SYNC_FINESTRA 2
#define SYNC_LEN_ANNUNCIO 22   // dati produttore compreso il company ID 0xFFFF
#define SYNC_LEN_STATO 151

// Stato annunciato
enum : uint8_t { ST_SONNO = 0, ST_PRONTA = 1, ST_REGISTRA = 2, ST_PIENA = 4, ST_ERRORE = 5, ST_SINCRONIZZA = 6 };
// Messaggi D->T (CONTROLLO)
enum : uint8_t { M_PRONTO = 0x10, M_CONFERMA = 0x11, M_RIPETI = 0x12, M_STOP = 0x13, M_SONNO = 0x14 };   // M_SONNO: D->T, 1 byte, valido solo dopo PRONTO
// Messaggi T->D (DATI)
enum : uint8_t { M_MAPPA = 0x01, M_BLOCCO = 0x02, M_FRAMMENTO = 0x03, M_CONFERMATO = 0x04, M_FINE = 0x05, M_ERRORE = 0x06, M_DIAGNOSI = 0x07, M_DIAGNOSI2 = 0x08 };   // M_DIAGNOSI e M_DIAGNOSI2: solo se il PRONTO era versione 2
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

// BLOCCO versione 2: come syncBlocco + byte 15 = dimensione dei frammenti. Lunghezza 16.
static inline uint16_t syncBlocco2(uint8_t *o, uint32_t seq, uint16_t fisico, uint32_t crc, uint32_t millisPrimo, uint8_t frammento) {
  syncBlocco(o, seq, fisico, crc, millisPrimo);
  o[15] = frammento;
  return 16;
}

// DIAGNOSI (T->D, 0x07, una volta dopo MAPPA, solo con PRONTO versione 2). Lunghezza 27 + testo, al massimo 244.
//  1 versione della diagnosi (1) | 2 causa dell'ultimo reset (codici della pagina: 0 accensione, 1 tap, 3 watchdog, 5 software, 6 lockup,
//  7 USB, 8 pin) | 3 guasto (0 nessuno, 1 HardFault, 2 watchdog, 3 altro) | 4..7 RESETREAS grezzo u32 | 8..11 PC u32 | 12..15 LR u32 |
//  16..19 CFSR u32 (PC/LR/CFSR a 0 se il contesto non era valido) | 20..21, 22..23, 24..25 stack libero minimo in byte di loop, Callback,
//  BLE (u16, 0xFFFF = non misurato) | 26 numero di righe di diario | 27.. righe ASCII separate da '\n', dalla piu' vecchia.
#define SYNC_DIAG_FISSI 27
static inline uint16_t syncDiagnosi(uint8_t *o, uint8_t causa, uint8_t guasto, uint32_t rr, uint32_t pc, uint32_t lr, uint32_t cfsr,
                                    uint16_t stkLoop, uint16_t stkCb, uint16_t stkBle, uint8_t nRighe, const char *testo, uint16_t nTesto) {
  o[0] = M_DIAGNOSI; o[1] = 1; o[2] = causa; o[3] = guasto;
  sw32(o + 4, rr); sw32(o + 8, pc); sw32(o + 12, lr); sw32(o + 16, cfsr);
  sw16(o + 20, stkLoop); sw16(o + 22, stkCb); sw16(o + 24, stkBle);
  o[26] = nRighe;
  memcpy(o + SYNC_DIAG_FISSI, testo, nTesto);
  return SYNC_DIAG_FISSI + nTesto;
}

// DIAGNOSI2 (T->D, 0x08, dalla tag 0.6.4, subito dopo la DIAGNOSI, solo con PRONTO versione 2; un central che non la conosce la ignora).
// Lunghezza 30, tutto binario little endian:
//  1 versione (1) | 2..3 intervallo di connessione negoziato (unita' 1,25 ms) | 4..5 MTU | 6..7 lunghezza dati (DLE) | 8 PHY (1 = 1M, 2 = 2M) |
//  9 VBUS presente adesso | 10..11 eventi VBUS "vista" (cumulativi, in RAM noinit: sopravvivono ai reset software) | 12..13 eventi VBUS "persa" |
//  14..17 millis tag dell'ultimo evento VBUS (0 = mai; dell'avvio in cui e' avvenuto) |
//  18..19 disconnessioni con motivo HCI 0x3E | 20..21 disconnessioni totali | 22 ultimo motivo di disconnessione |
//  23 bit 0-1 tipo dell'ultimo evento VBUS (0 mai, 1 vista, 2 persa), bit 2 = evento di un avvio precedente, bit 3-7 stack totale del task BLE in KB (0 con il byte a 0 nei vecchi firmware) |
//  24..25 stack libero minimo del task BLE in byte (0xFFFF = non misurato) | 26..29 millis tag all'invio
#define SYNC_DIAG2_LEN 30
static inline uint16_t syncDiagnosi2(uint8_t *o, uint16_t intv, uint16_t mtu, uint16_t dle, uint8_t phy, uint8_t vbus, uint16_t vbusSu, uint16_t vbusGiu,
                                     uint32_t vbusMs, uint16_t n3E, uint16_t discTot, uint8_t discUlt, uint16_t stkBle, uint32_t ora) {
  o[0] = M_DIAGNOSI2; o[1] = 1;
  sw16(o + 2, intv); sw16(o + 4, mtu); sw16(o + 6, dle); o[8] = phy; o[9] = vbus;
  sw16(o + 10, vbusSu); sw16(o + 12, vbusGiu); sw32(o + 14, vbusMs);
  sw16(o + 18, n3E); sw16(o + 20, discTot); o[22] = discUlt; o[23] = 0;
  sw16(o + 24, stkBle); sw32(o + 26, ora);
  return SYNC_DIAG2_LEN;
}
