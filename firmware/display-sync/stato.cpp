#include "stato.h"

StatoCopia gStato;
static SemaphoreHandle_t mtx;

void statoInit() {
  mtx = xSemaphoreCreateMutex();
  memset(&gStato, 0, sizeof(gStato));
  for (int i = 0; i < SYNC_MAX_TAG; i++) gStato.tag[i].txFisico[0] = gStato.tag[i].txFisico[1] = 0xFFFF;
}

void statoBlocca() { xSemaphoreTake(mtx, portMAX_DELAY); }
void statoSblocca() { xSemaphoreGive(mtx); }

int statoAnnuncio(const Annuncio &a, int rssi) {
  StatoLock l;
  int idx = -1;
  for (int i = 0; i < SYNC_MAX_TAG; i++)
    if (gStato.tag[i].usata && gStato.tag[i].id == a.id) idx = i;
  if (idx < 0)  // nuova: primo spicchio libero (tag 1 in alto, poi in senso orario)
    for (int i = 0; i < SYNC_MAX_TAG && idx < 0; i++)
      if (!gStato.tag[i].usata) {
        idx = i;
        gStato.tag[i].usata = true;
        gStato.tag[i].id = a.id;
      }
  if (idx < 0) return -1;
  TagStato &t = gStato.tag[idx];
  t.stato = a.stato;
  if (a.stato == ST_SONNO && t.cmd == CMD_ATTESA) { t.cmd = CMD_INVIATO; t.cmdMs = millis() ? millis() : 1; }   // gia' in sonno: standby ottenuto
  t.batt20 = a.batt20;
  t.pctMem = a.pctMem;
  t.errori = a.errori;
  t.colore = a.colore;
  if (a.nome[0]) strlcpy(t.nome, a.nome, sizeof(t.nome));
  t.inAttesa = a.inAttesa;
  t.secReg = a.secReg;
  t.ultimoSeq = a.ultimoSeq;
  t.vistoMs = millis();
  t.rssiGrezzo = (int8_t)rssi;
  t.rssi = (t.rssi == 0) ? (int8_t)rssi : (int8_t)((3 * t.rssi + rssi) / 4);   // media mobile: l'RSSI di un annuncio oscilla di +-10 dB
  return idx;
}

void statoCopia(StatoCopia &out) {
  StatoLock l;
  out = gStato;
}
