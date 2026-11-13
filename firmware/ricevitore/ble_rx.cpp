// BLE central (Bluefruit, nRF52840): scansione degli annunci 'SW', collegamento cifrato (bonding Just Works) fino a 2 tag,
// notifiche DATI in una coda ad anello. I callback fanno solo copie e assegnazioni: tutto il resto e' nel loop.
#include "ric.h"
#include <nrf_soc.h>

TagInfo tags[SYNC_MAX_TAG];
volatile uint32_t ultimaPresenza = 0;

static const uint32_t VISTA_RECENTE_MS = 3000;    // collegare solo una tag che annuncia adesso
static const uint32_t PAUSA_BREVE_MS = 1000;      // dopo un fallimento transitorio (e dopo una sync finita)
static const uint32_t PAUSA_LUNGA_MS = 4000;      // dopo un errore vero (sicurezza, servizio non trovato, PRONTO)
static const uint32_t RISPOSTA_SCRITTURA_MS = 1500;   // attesa della risposta a una scrittura su CONTROLLO
static const uint8_t  TENT_BUSY_MAX = 100;        // 100 x 20 ms: BUSY/RESOURCES = riprova, poi si chiude
static const uint32_t TIMEOUT_CONN_MS = 5000;     // connect() senza esito
static const uint32_t TIMEOUT_SIC_MS = 8000;      // pairing/cifratura
static const uint32_t TIMEOUT_ATTIVA_MS = 15000;  // F_ATTIVA senza messaggi dalla tag
static const uint32_t HOST_PRESENTE_MS = 3000;    // senza PRESENZA non ci si collega: i dati restano sulla tag

static BLEClientService svc[SYNC_MAX_TAG] = {BLEClientService(SYNC_UUID_SERVIZIO), BLEClientService(SYNC_UUID_SERVIZIO)};
static BLEClientCharacteristic ctrl[SYNC_MAX_TAG] = {BLEClientCharacteristic(SYNC_UUID_CONTROLLO), BLEClientCharacteristic(SYNC_UUID_CONTROLLO)};
static BLEClientCharacteristic dati[SYNC_MAX_TAG] = {BLEClientCharacteristic(SYNC_UUID_DATI), BLEClientCharacteristic(SYNC_UUID_DATI)};

// ---- coda ad anello delle notifiche (produttore: task BLE, consumatore: loop) ----
#define RING_N 100   // 0.1.6: voci da 256 B (frammenti da 238): 25 KB come prima
static RxMsg ring[RING_N];
static volatile uint16_t rHead = 0, rTail = 0;
static volatile bool perse[SYNC_MAX_TAG];
static volatile bool scoll[SYNC_MAX_TAG];

static void notifica(int s, uint8_t *d, uint16_t n) {
  if (n == 0) return;
  if (d[0] == M_MAPPA) { tags[s].ultimoMsg = millis(); return; }   // la mappa non serve al ricevitore, ma in streaming (tag 0.6.4) e' il keepalive: la tag e' viva
  if (n > sizeof(ring[0].d)) n = sizeof(ring[0].d);
  uint16_t h = rHead, nh = (h + 1) % RING_N;
  if (nh == rTail) { perse[s] = true; return; }
  ring[h].tag = s;
  ring[h].len = n;
  ring[h].t = millis();
  memcpy(ring[h].d, d, n);
  __DMB();   // i dati devono essere visibili prima dell'indice
  rHead = nh;
}
static void notifica0(BLEClientCharacteristic *, uint8_t *d, uint16_t n) { notifica(0, d, n); }
static void notifica1(BLEClientCharacteristic *, uint8_t *d, uint16_t n) { notifica(1, d, n); }

bool bleProssimo(RxMsg &m) {
  if (rTail == rHead) return false;
  m = ring[rTail];
  rTail = (rTail + 1) % RING_N;
  return true;
}
void bleScartaTag(int s) {   // solo dal loop (consumatore): le voci gia' pubblicate non sono toccate dal produttore
  for (uint16_t i = rTail; i != rHead; i = (i + 1) % RING_N)
    if (ring[i].tag == s) ring[i].len = 0;
}
bool bleSvuotata(int s) { bool v = perse[s]; perse[s] = false; return v; }
bool bleScollegata(int s) { bool v = scoll[s]; scoll[s] = false; return v; }

int tagPerId(uint32_t id) {
  for (int i = 0; i < SYNC_MAX_TAG; i++) if (tags[i].usata && tags[i].id == id) return i;
  return -1;
}
static int tagPerConn(uint16_t h) {
  for (int i = 0; i < SYNC_MAX_TAG; i++) if (tags[i].conn == h && tags[i].fase != F_IDLE) return i;
  return -1;
}

// ---- coda dei comandi su CONTROLLO: una scrittura alla volta per tag, in ordine (la tag accetta solo write con risposta) ----
struct Cmd { uint8_t n; uint8_t b[9]; };
static Cmd coda[SYNC_MAX_TAG][8];
static uint8_t cT[SYNC_MAX_TAG], cC[SYNC_MAX_TAG];     // testa (scrittura) e coda (lettura), solo dal loop
static uint8_t tentBusy[SYNC_MAX_TAG];
static uint32_t cProssimo[SYNC_MAX_TAG];
static bool chiusuraRichiesta[SYNC_MAX_TAG];
static void codaVuota(int s) { cT[s] = cC[s] = 0; tentBusy[s] = 0; chiusuraRichiesta[s] = false; }

bool bleScrivi(int s, const uint8_t *b, uint8_t n) {
  if (tags[s].fase != F_ATTIVA || n > sizeof(coda[0][0].b)) return false;
  if (chiusuraRichiesta[s]) return true;   // sta per chiudere: il comando si perde, la tag reinviera' (nessuna conferma senza scrittura riuscita)
  if ((uint8_t)(cT[s] - cC[s]) >= 8) return false;
  Cmd &c = coda[s][cT[s] & 7];
  c.n = n;
  memcpy(c.b, b, n);
  cT[s]++;
  return true;
}

enum EsitoScrittura { SC_OK, SC_RIPROVA, SC_ERRORE };
// Una scrittura con risposta: sd_ble_gattc_write + attesa del WRITE_RSP su un semaforo binario nostro (0.1.7: niente piu' accesso ai membri privati
// del Bluefruit). Non si usa write_resp(): il suo timeout e' 100 ms e il semaforo dinamico puo' perdere la risposta se arriva prima dell'attesa.
// La risposta arriva a eventoSd() (task BLE, Bluefruit.setEventCallback) che registra lo stato GATT e rilascia il semaforo.
static SemaphoreHandle_t semScr[SYNC_MAX_TAG];
static volatile uint16_t scrGatt[SYNC_MAX_TAG];     // stato GATT dell'ultima risposta (0xFFFF = nessuna)
static void eventoSd(ble_evt_t *e) {
  if (e->header.evt_id != BLE_GATTC_EVT_WRITE_RSP) return;
  const ble_gattc_evt_t &g = e->evt.gattc_evt;
  for (int i = 0; i < SYNC_MAX_TAG; i++)
    if (tags[i].conn == g.conn_handle && g.params.write_rsp.handle == ctrl[i].valueHandle()) {
      scrGatt[i] = g.gatt_status;
      xSemaphoreGive(semScr[i]);
      return;
    }
}
static EsitoScrittura bleScriviUna(int s, const Cmd &c, uint32_t &er) {
  BLEClientCharacteristic &ch = ctrl[s];
  while (xSemaphoreTake(semScr[s], 0) == pdTRUE) {}   // elimina risposte tardive
  scrGatt[s] = 0xFFFF;
  ble_gattc_write_params_t p = {};
  p.write_op = BLE_GATT_OP_WRITE_REQ;
  p.handle = ch.valueHandle();
  p.len = c.n;
  p.p_value = (uint8_t *)c.b;
  er = sd_ble_gattc_write(tags[s].conn, &p);
  if (er == NRF_ERROR_BUSY || er == NRF_ERROR_RESOURCES) return SC_RIPROVA;
  if (er != NRF_SUCCESS) return SC_ERRORE;
  if (xSemaphoreTake(semScr[s], pdMS_TO_TICKS(RISPOSTA_SCRITTURA_MS)) != pdTRUE) { er = 0xFFFF; return SC_ERRORE; }   // nessuna risposta
  if (scrGatt[s] != BLE_GATT_STATUS_SUCCESS) { er = scrGatt[s]; return SC_ERRORE; }   // la tag ha rifiutato la scrittura: niente conferma
  return SC_OK;
}

static void chiudiSubito(int s) {
  codaVuota(s);
  if (tags[s].conn != 0xFFFF) {
    BLEConnection *c = Bluefruit.Connection(tags[s].conn);
    if (c) c->disconnect();
  }
}
void bleChiudi(int s) {
  if (tags[s].fase == F_ATTIVA && cT[s] != cC[s]) { chiusuraRichiesta[s] = true; return; }   // prima i comandi in coda (es. STOP)
  chiudiSubito(s);
}

static void fallita(int s, const char *msg, uint32_t now, bool lunga = false);
static void serviCoda(int s, uint32_t now) {
  TagInfo &t = tags[s];
  if (cT[s] == cC[s]) { if (chiusuraRichiesta[s]) chiudiSubito(s); return; }
  if (now < cProssimo[s]) return;
  Cmd &c = coda[s][cC[s] & 7];
  uint32_t er = 0;
  EsitoScrittura e = bleScriviUna(s, c, er);
  if (e == SC_OK) { cC[s]++; tentBusy[s] = 0; return; }
  if (e == SC_RIPROVA && tentBusy[s] < TENT_BUSY_MAX) {
    if (tentBusy[s]++ == 0) evento(t.id, c.b[0], "CONTROLLO occupato: riprovo fra 20 ms (num = tipo comando)");
    cProssimo[s] = now + 20;
    return;
  }
  evento(t.id, er, er == 0xFFFF ? "scrittura CONTROLLO senza risposta (1,5 s): chiusura, la tag reinvia" : "scrittura CONTROLLO fallita (num = codice SoftDevice): chiusura, la tag reinvia");
  fallita(s, "CONTROLLO: collegamento chiuso", now);
}

// ---- scansione ----
static void scanCb(ble_gap_evt_adv_report_t *r) {
  uint8_t md[24];
  uint8_t n = Bluefruit.Scanner.parseReportByType(r, BLE_GAP_AD_TYPE_MANUFACTURER_SPECIFIC_DATA, md, sizeof(md));
  if (n >= 21 && md[0] == 0xFF && md[1] == 0xFF && md[2] == 'S' && md[3] == 'W' && md[4] == SYNC_VERSIONE) {
    uint32_t id = leggi32(md + 5);
    int i = tagPerId(id);
    if (i < 0)
      for (int k = 0; k < SYNC_MAX_TAG; k++)
        if (!tags[k].usata) { i = k; break; }
    if (i >= 0) {
      TagInfo &t = tags[i];
      uint32_t ora = millis();
      if (!t.usata || ora - t.vistoMs > VISTA_RECENTE_MS) { t.primoVistoMs = ora; memset((void *)t.msMotivo, 0, sizeof(t.msMotivo)); }   // nuovo avvistamento
      t.id = id;
      t.addr = r->peer_addr;
      t.rssi = r->rssi;
      t.stato = md[9];
      t.batt20 = md[10];
      t.pctMem = md[11];
      t.inAttesa = leggi16(md + 12);
      t.ultimoSeq = leggi32(md + 14);
      t.errori = md[20];
      t.vistoMs = ora;
      t.usata = true;
    }
  }
  Bluefruit.Scanner.resume();
}

// ---- eventi del collegamento ----
// I callback (task BLE) impostano solo flag volatili; le transizioni di fase le fa solo il loop (evBLE()).
static volatile bool evConn[SYNC_MAX_TAG], evSic[SYNC_MAX_TAG], evDisc[SYNC_MAX_TAG];
static volatile uint8_t discMotivo[SYNC_MAX_TAG];
static const char *const NOMI_FASE[] = {"idle", "connette", "conn_ok", "sicurezza", "sicura", "attiva", "chiusura"};
static bool lento[SYNC_MAX_TAG];            // collegamento a 11,25-15 ms (vero solo se un'altra tag e' impegnata)
static bool linkFatto[SYNC_MAX_TAG];        // EVENTO sullo stato effettivo del collegamento gia' inviato
static uint8_t linkTent[SYNC_MAX_TAG];
static uint16_t linkInt[SYNC_MAX_TAG];      // ultimo intervallo riportato (unita' 1,25 ms)
static uint32_t linkT[SYNC_MAX_TAG], soloDa[SYNC_MAX_TAG];
static void connectCb(uint16_t h) {
  for (int i = 0; i < SYNC_MAX_TAG; i++)
    if (tags[i].fase == F_CONNETTE) { tags[i].conn = h; tags[i].tConn = millis(); evConn[i] = true; return; }
  Bluefruit.Connection(h)->disconnect();   // collegamento non richiesto
}
static void disconnectCb(uint16_t h, uint8_t reason) {
  int i = tagPerConn(h);
  if (i >= 0) { discMotivo[i] = reason; evDisc[i] = true; }
}
static void securedCb(uint16_t h) {
  int i = tagPerConn(h);
  if (i >= 0) { tags[i].tSic = millis(); evSic[i] = true; }
}
static void evBLE() {   // nel loop: ordine connessione, sicurezza, disconnessione
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    TagInfo &t = tags[i];
    if (evConn[i]) {
      evConn[i] = false;
      if (t.fase == F_CONNETTE) t.fase = F_CONN_OK;
      else if (t.conn != 0xFFFF) {   // arrivata dopo il timeout
        evento(t.id, 0, "collegamento arrivato dopo il timeout: chiuso");
        BLEConnection *c = Bluefruit.Connection(t.conn);
        if (c) c->disconnect();
      }
    }
    if (evSic[i]) { evSic[i] = false; if (t.fase == F_SICUREZZA) t.fase = F_SICURA; }
    if (evDisc[i]) {
      evDisc[i] = false;
      {   // mai silenzioso: motivo HCI (0x08 timeout supervisione, 0x13 chiusa dalla tag, 0x16 chiusa da noi, 0x3E connessione non stabilita)
        char tx[96];
        snprintf(tx, sizeof(tx), "disconnessa: motivo HCI 0x%02X in fase %s, %lu ms dal collegamento", discMotivo[i],
                 t.fase <= F_CHIUSURA ? NOMI_FASE[t.fase] : "?", (unsigned long)(t.tConn ? millis() - t.tConn : 0));
        evento(t.id, discMotivo[i], tx);
      }
      t.fase = F_IDLE;
      t.conn = 0xFFFF;
      codaVuota(i);
      t.vistoMs = 0;                 // niente riconnessione immediata dopo una sync finita:
      t.inAttesa = 0;                // serve un nuovo annuncio
      t.ultimoTent = millis();
      scoll[i] = true;
    }
  }
}

// ---- intervallo di connessione e stato effettivo del collegamento (0.1.5) ----
// Parametri di connessione richiesti in connect(): 7,5 ms durante cifratura e scoperta; dopo PRONTO 11,25-15 ms se c'e' un'altra tag (0.1.7: propri, non piu' _conn_param privato)
static const ble_gap_conn_params_t connParam = {6, 6, BLE_GAP_CONN_SLAVE_LATENCY, BLE_GAP_CONN_SUPERVISION_TIMEOUT_MS / 10};
static bool altraImpegnata(int s) {
  for (int k = 0; k < SYNC_MAX_TAG; k++) if (k != s && tags[k].fase != F_IDLE) return true;
  return false;
}
static void impostaIntervallo(int s, bool lenta) {
  ble_gap_conn_params_t cp = {};
  cp.min_conn_interval = lenta ? 9 : 6;
  cp.max_conn_interval = lenta ? 12 : 6;
  cp.slave_latency = 0;
  cp.conn_sup_timeout = 400;
  uint32_t er = sd_ble_gap_conn_param_update(tags[s].conn, &cp);
  if (er == NRF_SUCCESS) lento[s] = lenta;
  else evento(tags[s].id, er, "aggiornamento intervallo rifiutato (num = codice SoftDevice)");
}
static void riportaLink(int s, BLEConnection *c, const char *nota) {
  char tx[100];
  uint32_t iv = c->getConnectionInterval() * 125;   // centesimi di ms
  uint8_t ph = c->getPHY();
  snprintf(tx, sizeof(tx), "link %s: PHY %s DLE %u MTU %u intervallo %lu.%02lu ms", nota,
           ph == BLE_GAP_PHY_2MBPS ? "2M" : (ph == BLE_GAP_PHY_1MBPS ? "1M" : "?"), c->getDataLength(), c->getMtu(),
           (unsigned long)(iv / 100), (unsigned long)(iv % 100));
  evento(tags[s].id, c->getDataLength(), tx);
  linkInt[s] = c->getConnectionInterval();
}
static void verificaLink(int s, BLEConnection *c, uint32_t now) {   // in F_ATTIVA, ogni 100 ms
  if (linkFatto[s]) {
    if (c->getConnectionInterval() != linkInt[s]) riportaLink(s, c, "cambiato");
    return;
  }
  if (now < linkT[s]) return;
  bool ok2m = c->getPHY() == BLE_GAP_PHY_2MBPS, dle = c->getDataLength() >= 251;
  if ((ok2m && dle) || linkTent[s] >= 20) { riportaLink(s, c, ok2m && dle ? "effettivo" : "NON completo"); linkFatto[s] = true; return; }
  linkTent[s]++;
  linkT[s] = now + 100;
  if (!dle) c->requestDataLengthUpdate(NULL);         // il central non la chiede da solo: DLE 251 (il SoftDevice sceglie il massimo configurato)
  else if (!ok2m) c->requestPHY(BLE_GAP_PHY_2MBPS);   // una procedura LL alla volta: BUSY = si riprova
}

void bleInit() {
  for (int i = 0; i < SYNC_MAX_TAG; i++) { tags[i].conn = 0xFFFF; tags[i].fase = F_IDLE; }
  Bluefruit.configCentralConn(SYNC_MTU, 6, 3, 3);
  Bluefruit.begin(0, SYNC_MAX_TAG);
  Bluefruit.setName("SwimRx");
  Bluefruit.Security.setIOCaps(false, false, false);   // Just Works
  Bluefruit.Security.setSecuredCallback(securedCb);
  Bluefruit.Central.setConnectCallback(connectCb);
  Bluefruit.Central.setDisconnectCallback(disconnectCb);
  Bluefruit.setEventCallback(eventoSd);
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    svc[i].begin();
    ctrl[i].begin(&svc[i]);
    dati[i].begin(&svc[i]);
    semScr[i] = xSemaphoreCreateBinary();   // la risposta di scrittura non si perde se arriva prima dell'attesa
  }
  Bluefruit.Scanner.setRxCallback(scanCb);
  Bluefruit.Scanner.restartOnDisconnect(true);
  Bluefruit.Scanner.filterMSD(0xFFFF);
  Bluefruit.Scanner.setInterval(40, 40);               // 25 ms / 25 ms: sempre in ascolto (USB), cambia canale spesso; vale anche per connect()
  Bluefruit.Scanner.useActiveScan(false);
  Bluefruit.Scanner.start(0);
}

static bool bondCancellati = false;   // clearBonds() al massimo una volta per avvio, dopo un fallimento di cifratura
static void fallita(int s, const char *msg, uint32_t now, bool lunga) {
  evento(tags[s].id, 0, msg);   // un solo EVENTO per fallimento: da qui la fase non e' piu' quella che ha fallito
  tags[s].ultimoTent = now;
  tags[s].pausa = lunga ? PAUSA_LUNGA_MS : PAUSA_BREVE_MS;
  chiudiSubito(s);
  if (tags[s].conn == 0xFFFF) tags[s].fase = F_IDLE;
  else { tags[s].fase = F_CHIUSURA; tags[s].tFase = now; }   // attesa della disconnessione (evBLE la porta a F_IDLE)
}

void bleGestisci(uint32_t now) {
  evBLE();
  bool connettendo = false;
  for (int s = 0; s < SYNC_MAX_TAG; s++)
    if (tags[s].fase == F_CONNETTE) connettendo = true;
  bool host = ultimaPresenza && (now - ultimaPresenza) < HOST_PRESENTE_MS;
  static uint32_t ultimoGiro = 0;
  uint32_t dt = ultimoGiro ? (now - ultimoGiro > 500 ? 500 : now - ultimoGiro) : 0;
  ultimoGiro = now;
  for (int s = 0; s < SYNC_MAX_TAG; s++) {
    TagInfo &t = tags[s];
    switch (t.fase) {
      case F_IDLE:
        if (t.usata && now - t.vistoMs < VISTA_RECENTE_MS) {   // tag in vista: perche' non ci si collega ancora? (0.1.5)
          if (!host) t.msMotivo[0] += dt;
          else if (t.stato == ST_SONNO) t.msMotivo[2] += dt;
          else if (t.inAttesa == 0) t.msMotivo[1] += dt;
          else if (t.ultimoTent != 0 && now - t.ultimoTent < t.pausa) t.msMotivo[3] += dt;
          else if (connettendo) t.msMotivo[4] += dt;
        }
        if (host && !connettendo && t.usata && now - t.vistoMs < VISTA_RECENTE_MS && t.inAttesa > 0 && t.stato != ST_SONNO &&
            (t.ultimoTent == 0 || now - t.ultimoTent >= t.pausa)) {
          ble_gap_addr_t a = t.addr;
          t.fase = F_CONNETTE;
          t.tFase = now;
          t.msAvv = 0;
          t.tConn = t.tSic = t.tMtu = t.tDisc = 0;
          t.t0 = t.primoVistoMs;   // il conteggio parte dall'avvistamento utile, non dalla pausa fra tentativi
          if (t.ultimoTent && t.t0 < t.ultimoTent + t.pausa) t.t0 = t.ultimoTent + t.pausa;
          t.pausa = PAUSA_BREVE_MS;   // default dopo questo collegamento (fine normale); fallita() lo alza per gli errori veri
          for (int k = 0; k < SYNC_MAX_TAG; k++)   // due collegamenti a 7,5 ms non stanno insieme: la tag gia' attiva passa a 11,25-15 ms
            if (k != s && tags[k].fase == F_ATTIVA && !lento[k]) impostaIntervallo(k, true);
          {
            char tx[120];
            snprintf(tx, sizeof(tx), "connect() dopo %lu ms dall'avvistamento; attese ms host/inAttesa0/sonno/pausa/altra %lu/%lu/%lu/%lu/%lu",
                     (unsigned long)(now - t.primoVistoMs), (unsigned long)t.msMotivo[0], (unsigned long)t.msMotivo[1],
                     (unsigned long)t.msMotivo[2], (unsigned long)t.msMotivo[3], (unsigned long)t.msMotivo[4]);
            evento(t.id, now - t.primoVistoMs, tx);
          }
          t.tConnect = now;
          // come Central.connect(), ma con il codice d'errore del SoftDevice
          uint32_t er = sd_ble_gap_connect(&a, Bluefruit.Scanner.getParams(), &connParam, CONN_CFG_CENTRAL);
          if (er != NRF_SUCCESS) {
            t.fase = F_IDLE;
            t.ultimoTent = now;
            t.pausa = PAUSA_BREVE_MS;
            evento(t.id, er, "connect() rifiutata (num = codice SoftDevice: 7 stato non valido, 17 occupato, 19 memoria)");
          } else {
            connettendo = true;
          }
        }
        break;
      case F_CONNETTE:
        if (now - t.tFase > TIMEOUT_CONN_MS) {
          uint32_t ec = sd_ble_gap_connect_cancel();
          t.fase = F_IDLE;
          t.ultimoTent = now;
          t.pausa = PAUSA_BREVE_MS;
          char tx[120];
          snprintf(tx, sizeof(tx), "connect(): timeout %lu ms senza collegamento; ultimo annuncio %lu ms fa, RSSI %d, cancel %lu",
                   (unsigned long)(now - t.tFase), (unsigned long)(now - t.vistoMs), (int)t.rssi, (unsigned long)ec);
          evento(t.id, now - t.tFase, tx);
        }
        break;
      case F_CONN_OK: {
        BLEConnection *c = Bluefruit.Connection(t.conn);
        if (!c) { fallita(s, "connessione persa", now); break; }
        t.fase = F_SICUREZZA;
        t.tFase = now;
        lento[s] = false; linkFatto[s] = false; linkTent[s] = 0; linkT[s] = 0; soloDa[s] = 0; linkInt[s] = 0;
        c->requestMtuExchange(SYNC_MTU);   // in parallelo alla cifratura (solo ATT): niente attesa dopo
        if (!c->secured()) {
          // Se la tag (o Bluefruit) ha gia' avviato la cifratura, authenticate da' INVALID_STATE (8) o BUSY (17):
          // e' "procedura in corso", si aspetta il secured callback (o il polling in F_SICUREZZA).
          ble_gap_sec_params_t sp = {};   // come il predefinito di Bluefruit (bond, Just Works)
          sp.bond = 1; sp.lesc = 1; sp.io_caps = BLE_GAP_IO_CAPS_NONE; sp.min_key_size = 7; sp.max_key_size = 16;
          sp.kdist_own.enc = 1; sp.kdist_own.id = 1; sp.kdist_peer.enc = 1; sp.kdist_peer.id = 1;
          uint32_t er = sd_ble_gap_authenticate(t.conn, &sp);
          if (er == NRF_SUCCESS) evento(t.id, 0, "pairing avviato");
          else if (er == NRF_ERROR_INVALID_STATE || er == NRF_ERROR_BUSY) evento(t.id, er, "pairing gia' in corso: attesa cifratura (num = codice)");
          else { evento(t.id, er, "pairing rifiutato (num = codice SoftDevice)"); tags[s].ultimoTent = now; t.pausa = PAUSA_LUNGA_MS; bleChiudi(s); t.fase = F_CHIUSURA; t.tFase = now; }
        } else { if (!t.tSic) t.tSic = millis(); t.fase = F_SICURA; }
        break;
      }
      case F_CHIUSURA:   // attesa disconnessione: niente nuovi tentativi finche' il collegamento non e' chiuso
        if (now - t.tFase > 6000) { t.conn = 0xFFFF; t.fase = F_IDLE; t.ultimoTent = now; }
        else if (now - t.tFase > 2000 && ((now - t.tFase) / 1000) != ((now - t.tFase - 20) / 1000)) bleChiudi(s);   // riprova ogni ~secondo
        break;
      case F_SICUREZZA:
      {
        BLEConnection *c = Bluefruit.Connection(t.conn);
        if (c && c->secured()) { if (!t.tSic) t.tSic = millis(); t.fase = F_SICURA; break; }   // polling: il callback puo' mancare
        if (now - t.tFase > TIMEOUT_SIC_MS) {
          if (!bondCancellati) {   // forse chiavi diverse fra i due lati: si cancellano i bond del ricevitore (la tag sovrascrive il suo al nuovo pairing)
            bondCancellati = true;
            Bluefruit.Central.clearBonds();
            evento(t.id, 0, "cifratura fallita: bond del ricevitore cancellati (una volta)");
          }
          fallita(s, "sicurezza: timeout", now, true);
        }
        break;
      }
      case F_SICURA: {   // bloccante (~100-300 ms): scoperta servizio, notifiche, PRONTO
        BLEConnection *c = Bluefruit.Connection(t.conn);
        if (!c) { fallita(s, "connessione persa", now); break; }
        // MTU gia' richiesto in F_CONN_OK; qui solo l'attesa (passo 1 ms, al massimo 1 s) e, se serve, una nuova richiesta.
        // L'MTU va concluso PRIMA della discovery: due procedure GATT client insieme danno NRF_ERROR_BUSY.
        if (c->getMtu() < SYNC_MTU) {
          for (int k = 0; k < 1000 && c->getMtu() < SYNC_MTU; k++) { if (k == 300) c->requestMtuExchange(SYNC_MTU); delay(1); }
        }
        t.tMtu = millis();
        {   // servizio + le due caratteristiche necessarie, in un'unica scoperta
          if (!svc[s].discover(t.conn)) { fallita(s, "servizio sync non trovato", now, true); break; }
          ble_gattc_handle_range_t bck = Bluefruit.Discovery.getHandleRange();
          Bluefruit.Discovery.setHandleRange(svc[s].getHandleRange());
          uint8_t nc = Bluefruit.Discovery.discoverCharacteristic(t.conn, ctrl[s], dati[s]);
          Bluefruit.Discovery.setHandleRange(bck);
          if (nc < 2) { fallita(s, "caratteristiche sync non trovate", now, true); break; }
        }
        t.tDisc = millis();
        c->requestPHY(BLE_GAP_PHY_2MBPS);
        dati[s].setNotifyCallback(s == 0 ? notifica0 : notifica1, false);   // false: nel task BLE, solo copie
        if (!dati[s].enableNotify()) { fallita(s, "notifiche non abilitate", now); break; }
        c->monitorRssi();
        t.ultimoMsg = millis();
        t.fase = F_ATTIVA;
        codaVuota(s);
        {   // PRONTO in modo sincrono (BUSY = riprova), prima di qualunque altro comando
          uint8_t p[2] = {M_PRONTO, SYNC_VERSIONE_PRONTO};
          Cmd pr; pr.n = 2; memcpy(pr.b, p, 2);
          uint32_t er = 0;
          EsitoScrittura e = SC_RIPROVA;
          for (int k = 0; k < 50 && e == SC_RIPROVA; k++) { e = bleScriviUna(s, pr, er); if (e == SC_RIPROVA) delay(20); }
          if (e != SC_OK) {
            evento(t.id, er, "PRONTO non scritto (num = codice SoftDevice, 65535 = nessuna risposta)");
            fallita(s, "PRONTO non scritto: chiusura", now, true);
            break;
          }
        }
        // 7,5 ms finche' e' sola; 11,25-15 ms se un'altra tag e' impegnata (due collegamenti non stanno insieme nei 7,5 ms)
        if (altraImpegnata(s)) {
          impostaIntervallo(s, true);
          for (int k = 0; k < SYNC_MAX_TAG; k++) if (k != s && tags[k].fase == F_ATTIVA && !lento[k]) impostaIntervallo(k, true);
        }
        t.msAvv = millis() - t.t0;
        char tx[120];
        snprintf(tx, sizeof(tx), "PRONTO inviato; tempi cum. ms connect()/conn/cifr/mtu/disc/pronto %lu/%lu/%lu/%lu/%lu/%lu",
                 (unsigned long)(t.tConnect - t.t0), (unsigned long)(t.tConn - t.t0), (unsigned long)(t.tSic - t.t0), (unsigned long)(t.tMtu - t.t0),
                 (unsigned long)(t.tDisc - t.t0), (unsigned long)t.msAvv);
        evento(t.id, t.msAvv, tx);
        break;
      }
      case F_ATTIVA: {
        BLEConnection *c = Bluefruit.Connection(t.conn);
        if (c) {
          int8_t r = c->getRssi();
          if (r) t.rssi = r;
        }
        serviCoda(s, now);
        if (c && t.fase == F_ATTIVA) {
          verificaLink(s, c, now);
          if (lento[s] && !altraImpegnata(s)) {   // tornata sola: dopo 3 s si riporta a 7,5 ms
            if (!soloDa[s]) soloDa[s] = now ? now : 1;
            else if (now - soloDa[s] > 3000) { impostaIntervallo(s, false); soloDa[s] = 0; }
          } else soloDa[s] = 0;
        }
        if (t.fase == F_ATTIVA && now - t.ultimoMsg > TIMEOUT_ATTIVA_MS) {   // tag muta: si chiude senza confermare
          t.ultimoMsg = now;
          fallita(s, "nessun messaggio dalla tag: chiusura", now);
        }
        break;
      }
    }
  }
  if (!connettendo && !Bluefruit.Scanner.isRunning()) Bluefruit.Scanner.start(0);
}
