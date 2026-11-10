// Ricezione dei messaggi DATI: parser delle notifiche, buffer dei blocchi in PSRAM.
// ricezioneNotifica() gira nel task BT: solo copie veloci, la verifica e' dello scrittore SD.
#pragma once
#include "protocollo.h"

enum TipoLavoro : uint8_t { L_BLOCCO, L_FALLITO, L_CONFERMATO };

struct Lavoro {
  uint8_t tipo;
  uint8_t tag;
  uint8_t slot;   // L_BLOCCO: buffer del blocco
  uint32_t seq;
};

struct IntestazioneBlocco {
  uint32_t seq, crc, millisTag;
  uint16_t fisico;
};

void ricezioneInit();
void ricezioneNotifica(int tag, const uint8_t *d, size_t n);
void ricezioneReset(int tag);                       // collegamento caduto: butta il blocco a meta'
uint8_t *ricezioneBuffer(int tag, int slot);
const IntestazioneBlocco &ricezioneIntestazione(int tag, int slot);
void ricezioneLibera(int tag, int slot);            // lo scrittore SD ha finito col buffer
uint32_t ricezioneByteAcc(int tag);                 // byte ricevuti dall'ultima chiamata
