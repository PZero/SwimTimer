// Strutture condivise tra BLE (ble_rx.cpp), assemblaggio blocchi (blocchi.cpp) e USB (usb_frame.cpp).
#pragma once
#include <Arduino.h>
// Serve l'accesso a BLEClientCharacteristic::_adamsg (semaforo della risposta di scrittura, privato): vedi bleScriviUna()
#define private public
#include <bluefruit.h>
#undef private
#include "protocollo.h"

enum Fase : uint8_t { F_IDLE = 0, F_CONNETTE, F_CONN_OK, F_SICUREZZA, F_SICURA, F_ATTIVA, F_CHIUSURA };

struct TagInfo {
  volatile bool usata;
  uint32_t id;
  ble_gap_addr_t addr;
  volatile int8_t rssi;
  volatile uint8_t stato, batt20, pctMem, errori;
  volatile uint16_t inAttesa;
  volatile uint32_t ultimoSeq, vistoMs, primoVistoMs;
  volatile Fase fase;
  volatile uint16_t conn;
  uint32_t tFase, ultimoTent, msAvv, ultimoMsg;
  uint32_t pausa;                                       // ms di attesa dopo l'ultimo tentativo (1000 transitorio, 4000 errore vero)
  uint32_t t0, tConn, tSic, tMtu, tDisc;                // tempi di fase (millis): t0 = avvistamento utile (senza la pausa fra tentativi)
  uint32_t tConnect;                                    // millis di connect() (0.1.5)
  uint32_t msMotivo[5];                                 // ms in cui la tag, vista, non e' stata collegata: host assente / inAttesa 0 / sonno / pausa / altra tag in connessione
  uint32_t ricevuti, confermati, bytes;
  uint16_t scartati;
};
extern TagInfo tags[SYNC_MAX_TAG];

struct RxMsg { uint8_t tag, len; uint32_t t; uint8_t d[248]; };   // t = millis di arrivo (preso nel callback)

// BLE
void bleInit();
void bleGestisci(uint32_t now);
bool bleProssimo(RxMsg &m);                       // estrae una notifica dalla coda (nessun lavoro nei callback)
void bleScartaTag(int s);                         // marca da scartare le notifiche in coda di una tag
bool bleSvuotata(int s);                          // true (una volta) se la coda ha perso notifiche della tag
bool bleScollegata(int s);                        // true (una volta) dopo una disconnessione
bool bleScrivi(int s, const uint8_t *b, uint8_t n);  // accoda un comando su CONTROLLO (una scrittura alla volta, in ordine); false = coda piena
void bleChiudi(int s);                            // chiude dopo aver svuotato la coda CONTROLLO (es. STOP)
int tagPerId(uint32_t id);
extern volatile uint32_t ultimaPresenza;          // millis dell'ultimo PRESENZA/OK dell'host (0 = mai)

// Blocchi
void blocchiElabora(uint32_t now);
void blocchiHost(uint8_t tipo, uint32_t id, uint32_t num, const uint8_t *p, uint16_t len);
void statInvia(uint32_t now);

// USB
void usbInit();
void usbInvia(uint8_t tipo, uint32_t id, uint32_t num, const uint8_t *p1, uint16_t l1, const uint8_t *p2 = nullptr, uint16_t l2 = 0);
void usbLeggi();
extern volatile uint32_t loopMaxMs;               // massimo intervallo fra due giri del loop dall'ultimo azzeramento
void evento(uint32_t id, uint32_t num, const char *txt);   // solo dal loop, mai dai callback BLE
