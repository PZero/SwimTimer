// BLE centrale: scansione continua degli annunci, collegamento automatico (fino a 3 tag),
// sicurezza LE Secure Connections con bonding Just Works, PRONTO, comandi verso la tag.
// Libreria BLE del core (Bluedroid). Le notifiche vanno a ricezioneNotifica() (task BT: solo copie).
#include "protocollo.h"
#if !SWIM_DEMO
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEClient.h>
#include <BLESecurity.h>
#include <esp_gap_ble_api.h>
#include "ricezione.h"
#include "stato.h"
#include "trasporto.h"

static const uint32_t PAUSA_TENTATIVI_MS = 4000;   // tra due tentativi di collegamento alla stessa tag
static const uint32_t VISTA_RECENTE_MS = 3000;     // collegare solo una tag che annuncia adesso
static const uint32_t MIN_LIBERO_MB_BLE = 50;      // come lo scrittore SD: senza spazio non ci si collega

struct Rete {
  esp_bd_addr_t addr;
  esp_ble_addr_type_t tipoAddr = BLE_ADDR_TYPE_PUBLIC;
  bool haAddr = false;
  BLEClient *cli = nullptr;
  BLERemoteCharacteristic *ctrl = nullptr;
  volatile bool cifrato = false;
  volatile bool chiudi = false;
  volatile bool connettendo = false;
  uint32_t ultimoTentativo = 0;
  volatile uint32_t tPronto = 0;   // millis() dell'invio di PRONTO
};
static Rete rete[SYNC_MAX_TAG];
static QueueHandle_t codaCmd;
static SemaphoreHandle_t mtxCollega;

// ---- callback del collegamento (una istanza per tag) ----
class CbClient : public BLEClientCallbacks {
 public:
  int tag = 0;
  void onConnect(BLEClient *) override {}
  void onDisconnect(BLEClient *) override {
    LOGF("tag %d: scollegata\n", tag);
    rete[tag].cifrato = false;
    rete[tag].ctrl = nullptr;
    rete[tag].tPronto = 0;
    ricezioneReset(tag);
    StatoLock l;
    gStato.tag[tag].collegata = false;
  }
};
static CbClient cbClient[SYNC_MAX_TAG];

// ---- sicurezza: Just Works (nessun PIN), si registra solo l'esito ----
class Sicurezza : public BLESecurityCallbacks {
  uint32_t onPassKeyRequest() override { return 0; }
  void onPassKeyNotify(uint32_t) override {}
  bool onSecurityRequest() override { return true; }
  bool onConfirmPIN(uint32_t) override { return true; }
  void onAuthenticationComplete(esp_ble_auth_cmpl_t c) override {
    for (int i = 0; i < SYNC_MAX_TAG; i++)
      if (rete[i].haAddr && memcmp(rete[i].addr, c.bd_addr, 6) == 0) rete[i].cifrato = c.success;
    LOGF("sicurezza: %s\n", c.success ? "cifrato" : "FALLITA");
  }
};

// ---- scansione: annunci 'SW' versione 1 ----
class Ascolto : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice d) override {
    if (!d.haveManufacturerData()) return;
    std::string md = d.getManufacturerData();
    Annuncio a;
    if (!annuncioLeggi((const uint8_t *)md.data(), md.size(), a)) return;
    if (d.haveName()) {  // il nome locale e' nella scan response (scansione attiva): solo ASCII stampabile, max 12 caratteri
      std::string n = d.getName();
      int k = 0;
      for (size_t j = 0; j < n.size() && k < SYNC_NOME_MAX; j++)
        if (n[j] >= 0x20 && n[j] <= 0x7E) a.nome[k++] = n[j];
      a.nome[k] = 0;
    }
    int i = statoAnnuncio(a, d.getRSSI());
    if (i < 0) return;
    memcpy(rete[i].addr, *d.getAddress().getNative(), 6);
    rete[i].tipoAddr = d.getAddressType();
    rete[i].haAddr = true;
  }
};
static Ascolto ascolto;

static void avviaScansione() {
  BLEScan *s = BLEDevice::getScan();
  s->setAdvertisedDeviceCallbacks(&ascolto, true);  // true: anche gli annunci ripetuti
  s->setActiveScan(true);  // serve per leggere il nome (scan response)
  s->setInterval(100);
  s->setWindow(30);   // 30% del tempo: il resto alla radio per il Wi-Fi (con 80% la rete SwimTimer spariva, 2026-11-11)
  s->start(0, nullptr, false);  // durata 0 = continua
}

static void cmdFallito(int i);

static void inviaSonno(int i);
// ---- collegamento di una tag (task a parte: connect() blocca) ----
static void collegaTask(void *arg) {
  int i = (int)(intptr_t)arg;
  Rete &r = rete[i];
  xSemaphoreTake(mtxCollega, portMAX_DELAY);  // un collegamento alla volta
  bool ok = false;
  BLEDevice::getScan()->stop();  // con la scansione attiva il collegamento puo' fallire
  do {
    if (!r.cli) {
      r.cli = BLEDevice::createClient();
      cbClient[i].tag = i;
      r.cli->setClientCallbacks(&cbClient[i]);
    }
    r.cifrato = false;
    r.chiudi = false;
    if (!r.cli->connect(BLEAddress(r.addr), r.tipoAddr)) break;
    r.cli->setMTU(SYNC_MTU);
    // PHY 2M preferito e intervallo 7,5-15 ms (la tag puo' comunque rifiutare)
    esp_ble_gap_set_prefered_phy(r.addr, 0, ESP_BLE_GAP_PHY_2M_PREF_MASK, ESP_BLE_GAP_PHY_2M_PREF_MASK, 0);
    esp_ble_conn_update_params_t p = {};
    memcpy(p.bda, r.addr, 6);
    p.min_int = 6; p.max_int = 12; p.latency = 0; p.timeout = 200;  // 7,5-15 ms, supervision 2 s
    esp_ble_gap_update_conn_params(&p);
    // Collegamento cifrato (bonding Just Works): la CONFERMA lo richiede
    esp_ble_set_encryption(r.addr, ESP_BLE_SEC_ENCRYPT);
    for (int k = 0; k < 60 && !r.cifrato && r.cli->isConnected(); k++) delay(100);
    if (!r.cifrato) break;
    BLERemoteService *sv = r.cli->getService(SYNC_UUID_SERVIZIO);
    if (!sv) break;
    r.ctrl = sv->getCharacteristic(SYNC_UUID_CONTROLLO);
    BLERemoteCharacteristic *dati = sv->getCharacteristic(SYNC_UUID_DATI);
    if (!r.ctrl || !dati) break;
    dati->registerForNotify([i](BLERemoteCharacteristic *, uint8_t *d, size_t n, bool) { ricezioneNotifica(i, d, n); });
    {
      StatoLock l;
      gStato.tag[i].collegata = true;
      gStato.tag[i].ultimoStop = 0;
    }
    Comando pronto = {(uint8_t)i, M_PRONTO, 0, 0, 0};
    uint8_t buf[10];
    size_t n = comandoCodifica(pronto, buf);
    r.ctrl->writeValue(buf, n, true);  // SD ok: la tag puo' mandare
    r.tPronto = millis() ? millis() : 1;
    ok = true;
    LOGF("tag %d: collegata, PRONTO inviato\n", i);
    bool sonno;
    { StatoLock l; sonno = gStato.tag[i].cmd == CMD_ATTESA; }
    if (sonno) inviaSonno(i);   // standby richiesto: subito dopo PRONTO (i collegamenti di scarico durano pochi secondi)
  } while (false);
  if (!ok && r.cli && r.cli->isConnected()) r.cli->disconnect();
  if (!ok) cmdFallito(i);   // collegamento di sincronizzazione fallito con uno standby in attesa: conta come tentativo
  r.ultimoTentativo = millis();
  r.connettendo = false;
  avviaScansione();
  xSemaphoreGive(mtxCollega);
  vTaskDelete(nullptr);
}

// ---- standby dalla pagina web: M_SONNO sul canale di sincronizzazione cifrato (dopo PRONTO) ----
// Con la tag collegata il comando parte da bleTask a nessun blocco in trasmissione (interrompere uno scarico a meta' lascerebbe
// blocchi aperti sulla SD e sulla tag); con la tag non collegata, al prossimo annuncio parte collegaTask anche senza blocchi da scaricare.
static const uint32_t ATTESA_EFFETTO_MS = 15000;   // dopo l'invio: se la tag e' ancora vista attiva dopo questo tempo, nuovo tentativo
static const uint32_t FINE_ESITO_MS = 60000;       // poi lo stato "inviato" si cancella
static const uint32_t DOPO_PRONTO_MS = 1500;       // attesa dopo PRONTO: la tag deve avere il tempo di annunciare il primo blocco

static void cmdFallito(int i) {
  StatoLock l;
  TagStato &t = gStato.tag[i];
  if (t.cmd != CMD_ATTESA) return;
  if (++t.cmdTent >= 3) t.cmd = CMD_ERRORE;   // altrimenti resta in attesa: riprova al prossimo annuncio
}

// Invia M_SONNO sul collegamento di sincronizzazione gia' aperto (da bleTask)
static void inviaSonno(int i) {
  Rete &r = rete[i];
  uint8_t buf[10];
  Comando c = {(uint8_t)i, M_SONNO, 0, 0, 0};
  size_t n = comandoCodifica(c, buf);
  r.ctrl->writeValue(buf, n, true);   // con risposta: se ritorna con il collegamento ancora vivo, o caduto dopo, la tag l'ha ricevuto
  StatoLock l;
  gStato.tag[i].cmd = CMD_INVIATO;    // la verifica dei 15 s in valutaCollegamenti decide se e' servito
  gStato.tag[i].cmdMs = millis() ? millis() : 1;
  LOGF("tag %d: SONNO inviato\n", i);
}

static bool sdOk() {
  StatoLock l;
  return gStato.sd.pronta && gStato.sd.liberiMb >= MIN_LIBERO_MB_BLE;
}

static void valutaCollegamenti(uint32_t ora) {
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    Rete &r = rete[i];
    bool vuole = false, sonnoSolo = false;
    {
      StatoLock l;
      TagStato &t = gStato.tag[i];
      bool fresca = t.usata && (ora - t.vistoMs) < VISTA_RECENTE_MS;
      if (t.cmd == CMD_INVIATO) {   // verifica dell'effetto: dopo 15 s la tag non deve piu' annunciare uno stato attivo
        uint32_t da = ora - t.cmdMs;
        if (da >= FINE_ESITO_MS) t.cmd = CMD_NESSUNO;
        else if (da >= ATTESA_EFFETTO_MS && fresca && t.stato != ST_SONNO) {
          if (++t.cmdTent >= 3) t.cmd = CMD_ERRORE; else t.cmd = CMD_ATTESA;
        }
      }
      // collegamento di sincronizzazione: per scaricare blocchi oppure (anche senza blocchi) per portare M_SONNO dopo PRONTO
      bool sonno = t.cmd == CMD_ATTESA && t.stato != ST_SONNO;
      vuole = t.usata && !t.collegata && fresca && (sonno || (t.inAttesa > 0 && t.stato != ST_SONNO));
      sonnoSolo = sonno;   // M_SONNO non scrive sulla SD: il collegamento serve anche con la SD non pronta
    }
    if (!(vuole && (sonnoSolo || sdOk())) || !r.haAddr || r.connettendo || ora - r.ultimoTentativo < PAUSA_TENTATIVI_MS) continue;
    r.connettendo = true;
    xTaskCreatePinnedToCore(collegaTask, "collega", 8192, (void *)(intptr_t)i, 2, nullptr, 0);
  }
}

static void bleTask(void *) {
  uint32_t ultimoSec = 0, ultimaValutazione = 0;
  for (;;) {
    Comando c;
    while (xQueueReceive(codaCmd, &c, pdMS_TO_TICKS(20)) == pdTRUE) {
      Rete &r = rete[c.tag];
      if (!r.cli || !r.cli->isConnected() || !r.ctrl) continue;  // collegamento caduto: la tag reinviera'
      uint8_t buf[10];
      size_t n = comandoCodifica(c, buf);
      r.ctrl->writeValue(buf, n, true);
    }
    uint32_t ora = millis();
    for (int i = 0; i < SYNC_MAX_TAG; i++) {   // standby in attesa con la tag collegata: dopo PRONTO e a nessun blocco in trasmissione
      Rete &r = rete[i];
      if (!r.cli || !r.ctrl || !r.tPronto || !r.cli->isConnected() || ora - r.tPronto < DOPO_PRONTO_MS) continue;
      bool via;
      {
        StatoLock l;
        TagStato &t = gStato.tag[i];
        via = t.collegata && t.cmd == CMD_ATTESA && t.txFisico[0] == 0xFFFF && t.txFisico[1] == 0xFFFF;
      }
      if (via) inviaSonno(i);
    }
    for (int i = 0; i < SYNC_MAX_TAG; i++) {
      Rete &r = rete[i];
      if (r.chiudi && r.cli && r.cli->isConnected()) { r.chiudi = false; r.cli->disconnect(); }
    }
    if (ora - ultimoSec >= 1000) {  // byte/s per la schermata
      ultimoSec = ora;
      for (int i = 0; i < SYNC_MAX_TAG; i++) {
        uint32_t b = ricezioneByteAcc(i);
        StatoLock l;
        gStato.tag[i].bps = b;
      }
    }
    if (ora - ultimaValutazione >= 200) {
      ultimaValutazione = ora;
      valutaCollegamenti(ora);
    }
  }
}

void trasportoInit() {
  codaCmd = xQueueCreate(32, sizeof(Comando));
  mtxCollega = xSemaphoreCreateMutex();
  BLEDevice::init("");
  BLEDevice::setMTU(SYNC_MTU);
  BLEDevice::setSecurityCallbacks(new Sicurezza());
  BLESecurity *sec = new BLESecurity();
  sec->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_BOND);  // LE Secure Connections + bonding
  sec->setCapability(ESP_IO_CAP_NONE);                  // Just Works
  sec->setInitEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);
  esp_ble_gap_set_prefered_default_phy(ESP_BLE_GAP_PHY_2M_PREF_MASK | ESP_BLE_GAP_PHY_1M_PREF_MASK,
                                       ESP_BLE_GAP_PHY_2M_PREF_MASK | ESP_BLE_GAP_PHY_1M_PREF_MASK);
  avviaScansione();
  xTaskCreatePinnedToCore(bleTask, "ble", 6144, nullptr, 2, nullptr, 0);
  LOGF("BLE: scansione avviata\n");
}

bool trasportoInvia(const Comando &c) { return xQueueSend(codaCmd, &c, 0) == pdTRUE; }

void trasportoChiudi(int tag) { rete[tag].chiudi = true; }

#endif  // !SWIM_DEMO
