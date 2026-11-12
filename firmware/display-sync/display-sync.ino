// Display di sincronizzazione SwimTimer (LilyGO T-RGB, ESP32-S3R8): riceve i blocchi .swr dalle tag
// (fino a 3 insieme), li salva sulla microSD, li rilegge e solo allora li conferma (docs/SINCRONIZZAZIONE.md).
// Core 0: BLE e scrittore SD. Core 1 (loop): schermata, che legge solo una copia dello stato.
// Con -DSWIM_DEMO=1 (ambiente "demo") le tag sono simulate e il BLE e' spento.
#include <Arduino.h>
#include "protocollo.h"
#include "stato.h"
#include "ricezione.h"
#include "sd_scrittore.h"
#include "trasporto.h"
#include "ui.h"
#include "web.h"

void setup() {
  Serial.begin(115200);
  // Prova del CRC32 (valore noto di "123456789"): se non torna, il resto non ha senso
  const uint8_t prova[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
  if (crc32Blocco(prova, sizeof(prova)) != 0xCBF43926u) Serial.println("ERRORE: CRC32 sbagliato");

  statoInit();
  uiInit();        // display e tele in PSRAM
  ricezioneInit(); // buffer dei blocchi (2 x 4 KB per tag) in PSRAM
  sdInit();        // microSD (1 bit) e task scrittore
  trasportoInit(); // BLE (scansione e collegamenti) oppure demo
  webInit();       // Wi-Fi AP "SwimTimer" + pagina di stato; se fallisce la scheda continua a scaricare
#if SWIM_DEMO
  Serial.println("Modalita' DEMO: tag simulate");
#endif
}

// Riepilogo sulla seriale ogni 5 s (diagnosi senza guardare lo schermo)
static void riepilogo() {
  static uint32_t ultimo = 0;
  if (millis() - ultimo < 5000) return;
  ultimo = millis();
  static StatoCopia c;
  statoCopia(c);
  LOGF("[%lus] avvio %d SD %s err %u liberi %lu MB sess %lu\n", (unsigned long)(millis() / 1000), (int)esp_reset_reason(),
       c.sd.pronta ? "ok" : "no", c.sd.errore, (unsigned long)c.sd.liberiMb, (unsigned long)c.sd.sessione);
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    const TagStato &t = c.tag[i];
    if (!t.usata) continue;
    int n[4] = {0, 0, 0, 0};
    for (int b = 0; b < 512; b++) n[mappaGet(t.mappa, b)]++;
    LOGF("  tag%d %08lX rssi %d/%d st %u coll %u attesa %u salvati %lu errCrc %lu anom %lu stop %u bps %lu | lib %d ap %d att %d ok %d\n",
         i + 1, (unsigned long)t.id, t.rssi, t.rssiGrezzo, t.stato, t.collegata, t.inAttesa, (unsigned long)t.salvati,
         (unsigned long)t.errCrc, (unsigned long)t.anomalie, t.ultimoStop, (unsigned long)t.bps, n[0], n[1], n[2], n[3]);
  }
}

void loop() {
  uiAggiorna();
  riepilogo();
  delay(10);
}
