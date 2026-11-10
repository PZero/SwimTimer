// Stato condiviso tra BLE, scrittore SD e interfaccia. Si scrive e si legge solo
// con il mutex (statoBlocca/statoSblocca); l'interfaccia ne prende una copia.
#pragma once
#include <Arduino.h>
#include "protocollo.h"

// Log sulla seriale solo se c'e' spazio (con il core 2.x la seriale USB blocca se nessuno legge)
#define LOGF(...) do { if (Serial.availableForWrite() > 120) Serial.printf(__VA_ARGS__); } while (0)

enum ErrSd : uint8_t { SD_OK = 0, SD_ASSENTE, SD_PIENA, SD_ERR_SCRITTURA, SD_ERR_RILETTURA };

struct TagStato {
  bool usata;              // spicchio assegnato
  uint32_t id;
  uint8_t stato, batt20, pctMem, errori;
  uint8_t colore;          // 0..9 nella tavolozza, 0xFF = non impostato
  char nome[SYNC_NOME_MAX + 1];  // nome scelto dall'utente ("" = usare ST-xxxx)
  uint16_t inAttesa, secReg;
  uint32_t ultimoSeq;
  uint32_t vistoMs;        // millis dell'ultimo annuncio
  int8_t rssi;             // dBm, mediato
  int8_t rssiGrezzo;       // dBm, ultimo annuncio
  bool collegata;          // collegamento attivo
  bool mappaValida;
  uint8_t mappa[128];      // 512 x 2 bit: 0 libero, 1 aperto, 2 da validare, 3 validato
  uint16_t aperto;
  uint16_t txFisico[2];    // blocchi in trasmissione (0xFFFF = nessuno)
  uint32_t txSeq[2];
  uint32_t bps;            // byte/s ricevuti (media dell'ultimo secondo)
  uint32_t salvati;        // blocchi salvati e verificati in questa sessione
  uint32_t errCrc;         // blocchi scartati (CRC o frammenti mancanti)
  uint32_t anomalie;       // stesso seq con CRC diverso
  uint8_t ultimoStop;      // ultimo motivo di STOP inviato (0 = nessuno)
};

struct SdStato {
  bool pronta;
  uint8_t errore;          // ErrSd
  uint32_t liberiMb, totaleMb;
  uint32_t sessione;
};

struct StatoCopia {
  TagStato tag[SYNC_MAX_TAG];
  SdStato sd;
};

extern StatoCopia gStato;

void statoInit();
void statoBlocca();
void statoSblocca();
// Aggiorna lo spicchio della tag dell'annuncio (lo assegna se nuova). Ritorna l'indice o -1 se i 3 spicchi sono pieni.
int statoAnnuncio(const Annuncio &a, int rssi);
void statoCopia(StatoCopia &out);

static inline uint8_t mappaGet(const uint8_t *m, int i) { return (m[i >> 2] >> (2 * (i & 3))) & 3; }
static inline void mappaSet(uint8_t *m, int i, uint8_t v) {
  m[i >> 2] = (m[i >> 2] & ~(3 << (2 * (i & 3)))) | ((v & 3) << (2 * (i & 3)));
}

struct StatoLock {
  StatoLock() { statoBlocca(); }
  ~StatoLock() { statoSblocca(); }
};
