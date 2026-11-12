// Pagina di stato via Wi-Fi AP (vedi web.h). Il server e' sincrono (WebServer del core) ma in un task suo:
// il loop dello schermo, il BLE (core 0) e lo scrittore SD non lo aspettano mai.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "stato.h"
#include "web.h"
#include "pagina.h"

#if __has_include("segreti.h")
#include "segreti.h"
#else
#error "Manca segreti.h: copia segreti.esempio.h in segreti.h e scegli la password del Wi-Fi (8-63 caratteri)"
#endif

static const char *WIFI_SSID = "SwimTimer";
static const int WIFI_CANALE = 1;

static WebServer *server = nullptr;
static StatoCopia copia;                 // usata solo dal task web
static uint32_t salvPrec[SYNC_MAX_TAG], salvMs[SYNC_MAX_TAG];   // ultimo blocco salvato su SD (prova che i dati arrivano)
static uint32_t prontaDa[SYNC_MAX_TAG];  // millis da cui la tag e' PRONTA (0 = non lo e')

// Stessa logica di vista() in ui.cpp
static const char *parolaStato(const TagStato &t, uint32_t ora, bool &nonVista) {
  nonVista = (int32_t)(ora - t.vistoMs) > 10000;
  // Registra anche mentre scarica: la tag annuncia SINCRONIZZA durante lo scarico, ma il timer di registrazione dice la verita'
  if (!nonVista && t.secReg > 0 && t.stato != ST_SONNO && t.stato != ST_PRONTA && t.stato != ST_ERRORE && t.stato != ST_PIENA) return "REGISTRA";
  if (t.collegata || (t.stato == ST_SINCRONIZZA && !nonVista)) return "SCARICA";
  if (t.stato == ST_SONNO) return "SPENTA";
  if (nonVista) return "NON VISTA";
  switch (t.stato) {
    case ST_PRONTA: return "PRONTA";
    case ST_REGISTRA: return "REGISTRA";
    case ST_PIENA: return "MEM. PIENA";
    default: return "ERRORE";
  }
}

// Stessa curva LiPo di ui.cpp / tools/index.html
static const int16_t LIPO_MV[] = {4200, 4150, 4110, 4080, 4020, 3980, 3950, 3910, 3870, 3850, 3840, 3820, 3800, 3790, 3770, 3750, 3730, 3710, 3690, 3610, 3270};
static const int8_t LIPO_PCT[] = {100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0};
static int percentualeLipo(int mv) {
  if (mv >= LIPO_MV[0]) return 100;
  for (int i = 1; i < (int)(sizeof(LIPO_MV) / sizeof(LIPO_MV[0])); i++)
    if (mv >= LIPO_MV[i])
      return LIPO_PCT[i] + (LIPO_PCT[i - 1] - LIPO_PCT[i]) * (mv - LIPO_MV[i]) / (LIPO_MV[i - 1] - LIPO_MV[i]);
  return 0;
}

static const char *causaRiavvio(int r) {
  static const char *nomi[] = {"?", "accensione", "esterno", "software", "panic", "wdt int", "wdt task", "wdt", "sonno", "calo tensione", "sdio"};
  return (r >= 0 && r <= 10) ? nomi[r] : "?";
}

static void aggiornaPronta(uint32_t ora) {
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    const TagStato &t = copia.tag[i];
    bool nv = false;
    bool pronta = t.usata && !strcmp(parolaStato(t, ora, nv), "PRONTA");
    if (t.salvati != salvPrec[i]) { salvPrec[i] = t.salvati; salvMs[i] = ora ? ora : 1; }
    if (!pronta) prontaDa[i] = 0;
    else if (!prontaDa[i]) prontaDa[i] = ora ? ora : 1;
  }
}

static void rispondiStato() {
  uint32_t ora = millis();
  statoCopia(copia);
  aggiornaPronta(ora);
  String j;
  j.reserve(3000);
  char b[460];
  snprintf(b, sizeof(b),
           "{\"up\":%lu,\"avvii\":%lu,\"causa\":\"%s\",\"heap\":%u,\"sd\":{\"ok\":%d,\"err\":%u,\"liberi\":%lu,\"tot\":%lu,\"sess\":%lu},\"tag\":[",
           (unsigned long)(ora / 1000), (unsigned long)copia.sd.sessione, causaRiavvio((int)esp_reset_reason()), (unsigned)ESP.getFreeHeap(),
           copia.sd.pronta ? 1 : 0, copia.sd.errore, (unsigned long)copia.sd.liberiMb, (unsigned long)copia.sd.totaleMb,
           (unsigned long)copia.sd.sessione);
  j += b;
  static const uint8_t fallback[3][3] = {{255, 80, 160}, {120, 140, 255}, {255, 220, 60}};
  bool primo = true;
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    const TagStato &t = copia.tag[i];
    if (!t.usata) continue;
    bool nv;
    const char *st = parolaStato(t, ora, nv);
    const uint8_t *c = t.colore <= 9 ? SYNC_TAVOLOZZA[t.colore] : fallback[i];
    bool personale = t.nome[0] && !(strlen(t.nome) == 7 && !strncmp(t.nome, "ST-", 3));
    char nome[24];
    if (personale) {  // il nome arriva dall'aria: niente virgolette o barre nel JSON
      strlcpy(nome, t.nome, sizeof(nome));
      for (char *p = nome; *p; p++)
        if (*p == '"' || *p == '\\' || (uint8_t)*p < 32 || (uint8_t)*p > 126) *p = '?';
    } else snprintf(nome, sizeof(nome), "ST-%04lX", (unsigned long)(t.id & 0xFFFF));
    int pct = t.batt20 ? percentualeLipo(t.batt20 * 20) : -1;
    int rp = constrain((t.rssi + 100) * 100 / 60, 0, 100);   // -100 dBm = 0 %, -40 dBm = 100 %
    uint32_t pr = prontaDa[i] ? (ora - prontaDa[i]) / 1000 : 0;
    if (!primo) j += ',';
    primo = false;
    snprintf(b, sizeof(b),
             "{\"i\":%d,\"nome\":\"%s\",\"id\":\"%08lX\",\"col\":\"#%02x%02x%02x\",\"st\":\"%s\",\"vista\":%lu,\"reg\":%u,\"pronta\":%lu,",
             i + 1, nome, (unsigned long)t.id, c[0], c[1], c[2], st, (unsigned long)((ora - t.vistoMs) / 1000), t.secReg, (unsigned long)pr);
    j += b;
    snprintf(b, sizeof(b),
             "\"batt\":%d,\"mv\":%u,\"rssi\":%d,\"rssip\":%d,\"mem\":%u,\"att\":%u,\"salv\":%lu,\"crc\":%lu,\"anom\":%lu,\"seq\":%lu,\"bps\":%lu,\"ultsalv\":%ld,\"scar\":%d,\"coll\":%d,\"tx\":[%d,%d],\"cmd\":\"%s\",\"mappa\":\"",
             pct, t.batt20 * 20, t.rssi, rp, t.pctMem, t.inAttesa, (unsigned long)t.salvati, (unsigned long)t.errCrc, (unsigned long)t.anomalie,
             (unsigned long)t.ultimoSeq, (unsigned long)t.bps, salvMs[i] ? (long)((ora - salvMs[i]) / 1000) : -1L,
             (t.collegata || t.stato == ST_SINCRONIZZA) ? 1 : 0, t.collegata ? 1 : 0,
             t.txFisico[0] == 0xFFFF ? -1 : (int)t.txFisico[0], t.txFisico[1] == 0xFFFF ? -1 : (int)t.txFisico[1],
             t.cmd == CMD_ATTESA ? "attesa" : t.cmd == CMD_INVIATO ? "inviato" : t.cmd == CMD_ERRORE ? "errore" : "");
    j += b;
    if (t.mappaValida) {
      static const char hex[] = "0123456789abcdef";
      for (int k = 0; k < 128; k++) { j += hex[t.mappa[k] >> 4]; j += hex[t.mappa[k] & 15]; }
    }
    j += "\"}";
  }
  j += "]}";
  server->sendHeader("Cache-Control", "no-store");
  server->send(200, "application/json", j);
}

static void rispondiPagina() {
  server->sendHeader("Cache-Control", "no-store");
  server->send_P(200, "text/html; charset=utf-8", PAGINA_HTML);
}

// POST /comando  tag=<id esadecimale>&c=sonno : mette in coda lo standby; lo invia il BLE al prossimo contatto
static void riceviComando() {
  server->sendHeader("Cache-Control", "no-store");
  if (server->arg("c") != "sonno") { server->send(400, "text/plain", "comando sconosciuto"); return; }
  uint32_t id = strtoul(server->arg("tag").c_str(), nullptr, 16);
  bool trovata = false;
  {
    StatoLock l;
    for (int i = 0; i < SYNC_MAX_TAG; i++)
      if (gStato.tag[i].usata && gStato.tag[i].id == id) {
        trovata = true;
        if (gStato.tag[i].cmd != CMD_ATTESA) { gStato.tag[i].cmd = CMD_ATTESA; gStato.tag[i].cmdTent = 0; }
      }
  }
  if (trovata) LOGF("WEB: standby richiesto per %08lX\n", (unsigned long)id);
  server->send(trovata ? 200 : 404, "application/json", trovata ? "{\"ok\":1}" : "{\"ok\":0}");
}

static void webTask(void *) {
  for (;;) {
    server->handleClient();
    // anche senza richieste teniamo aggiornato "PRONTA da": l'avviso non deve dipendere da chi guarda
    static uint32_t ult = 0;
    if (millis() - ult > 1000) { ult = millis(); statoCopia(copia); aggiornaPronta(millis()); }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

void webInit() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(IPAddress(192, 168, 4, 1), IPAddress(192, 168, 4, 1), IPAddress(255, 255, 255, 0));
  if (!WiFi.softAP(WIFI_SSID, WIFI_PASSWORD, WIFI_CANALE, 0, 4)) {
    LOGF("WEB: softAP fallito, niente pagina (la scheda continua a scaricare)\n");
    return;
  }
  server = new WebServer(80);
  server->on("/", HTTP_GET, rispondiPagina);
  server->on("/stato", HTTP_GET, rispondiStato);
  server->on("/comando", HTTP_POST, riceviComando);
  server->onNotFound([]() { server->send(404, "text/plain", "non trovato"); });
  server->begin();
  if (xTaskCreatePinnedToCore(webTask, "web", 8192, nullptr, 1, nullptr, 1) != pdPASS) {
    LOGF("WEB: task non creato\n");
    return;
  }
  LOGF("WEB: AP '%s' canale %d su %s, heap libero %u, PSRAM libera %u\n", WIFI_SSID, WIFI_CANALE, WiFi.softAPIP().toString().c_str(),
       (unsigned)ESP.getFreeHeap(), (unsigned)ESP.getFreePsram());
}
