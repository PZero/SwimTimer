// Ricevitore SwimTimer 0.1.6 (XIAO nRF52840 Sense, Bluefruit, ruolo central).
// Scarica i blocchi da 2 tag (firmware 0.6.1 e 0.6.2; con la 0.6.2 frammenti da 238 B e DIAGNOSI) e li inoltra all'host via USB seriale (PROTOCOLLO-USB.md).
// Regola: la CONFERMA alla tag parte solo dopo l'OK dell'host (blocco salvato e riletto). Senza host nessun collegamento.
// Compilazione: arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense firmware/ricevitore
#include "ric.h"

void setup() {
  usbInit();
  bleInit();
  pinMode(LED_BLUE, OUTPUT);
  digitalWrite(LED_BLUE, HIGH);   // LED spento (logica invertita)
}

volatile uint32_t loopMaxMs = 0;

void loop() {
  static uint32_t ultimoGiro = 0;
  static uint32_t ultimoStat = 0, ultimoHello = 0;
  uint32_t now = millis();
  if (ultimoGiro && now - ultimoGiro > loopMaxMs) loopMaxMs = now - ultimoGiro;
  ultimoGiro = now;
  usbLeggi();
  bleGestisci(now);
  blocchiElabora(now);
  if (!ultimoHello || now - ultimoHello >= 10000) {
    ultimoHello = now ? now : 1;
    usbInvia(FR_HELLO, 0, 0, (const uint8_t *)RIC_VERSIONE, strlen(RIC_VERSIONE));
  }
  if (now - ultimoStat >= 1000) {
    ultimoStat = now;
    statInvia(now);
    bool host = ultimaPresenza && (now - ultimaPresenza) < 3000;
    digitalWrite(LED_BLUE, host ? LOW : HIGH);   // LED blu acceso = host presente
  }
  delay(1);
}
