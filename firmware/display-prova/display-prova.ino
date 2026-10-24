// Display di prova (LilyGO T-RGB 2,8"): pace clock da piscina con 4 lancette.
// Riceve gli annunci BLE del tag "SwimTag" (ultimo campione di accelerometro e
// giroscopio) senza collegarsi e riconosce partenza e arrivo:
// - partenza: colpo secco (accelerazione oltre SOGLIA_SPINTA_G)
// - arrivo: tag vicino e fermo da 3 s; il tempo vale fino all'ultimo movimento
// Livelli: sfondo (quadrante, disegnato una volta), lancette (ogni secondo),
// segni (pallino verde alla partenza, rosso all'arrivo, tempo in grande per 3 s).
// Ogni volta si compone il risultato in memoria e lo si copia sullo schermo in un colpo.
// Un tocco sullo schermo toglie i segni; le lancette continuano a girare.
// Driver del display: src/trgb (LilyGo-T-RGB). Si compila con PlatformIO (platformio.ini).
#include <Wire.h>
#include <Adafruit_GFX.h>  // disegno in memoria (GFXcanvas16) e font
#include <Fonts/FreeSansBold24pt7b.h>
#include <Fonts/FreeSansBold18pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <driver/rtc_io.h>
#include "src/trgb/LilyGo_RGBPanel.h"

const char *NOME_TAG = "SwimTag";
const int SOGLIA_VICINO = -72;       // dBm: sopra = vicino (da tarare in vasca)
const uint32_t TAG_PERSO_MS = 3000;
const float SOGLIA_SPINTA_G = 0.8;   // accelerazione oltre la gravità che fa partire il tempo
const float SOGLIA_CALMA_G = 0.10;   // sotto questa e sotto SOGLIA_CALMA_DPS il tag è fermo
const float SOGLIA_CALMA_DPS = 20;
const uint32_t CALMA_MS = 3000;
const uint32_t SCRITTA_MS = 3000;    // durata della scritta con il tempo
const uint32_t SOSPENSIONE_MS = 300000;  // 5 minuti senza tag né tocchi: sonno profondo

// Geometria del quadrante
const int CX = 240, CY = 240;
const int R_TACCHE = 236, R_NUMERI = 192, R_LANCETTA = 200, R_SEGNI = 222;

// Colori RGB565
const uint16_t NERO = 0x0000, BIANCO = 0xFFFF, GRIGIO = 0x8410, BLU_BORDO = 0x10A6;
const uint16_t VERDE = 0x0560, GIALLO = 0xFEA0, ROSSO = 0xE8C4, AZZURRO = 0x3B7F;
// Lancette in senso orario dalla verde, come nei pace clock
const uint16_t COLORE_LANCETTA[4] = {VERDE, NERO, GIALLO, ROSSO};

LilyGo_RGBPanel panel;
GFXcanvas16 *sfondo, *composto;

struct Campione {
  uint8_t numero;
  int16_t assi[6];  // grezzi: ax, ay, az (16384/g), gx, gy, gz (16,4 per °/s)
};
QueueHandle_t coda;
volatile int rssiUltimo = -127;
volatile uint32_t visto = 0;

class Ascolto : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice d) override {
    if (!d.haveName() || d.getName() != NOME_TAG) return;
    rssiUltimo = d.getRSSI();
    visto = millis();
    if (!d.haveManufacturerData()) return;
    std::string md = d.getManufacturerData();
    if (md.length() != 15 || (uint8_t)md[0] != 0xFF || (uint8_t)md[1] != 0xFF) return;
    Campione c;
    c.numero = md[2];
    memcpy(c.assi, md.c_str() + 3, 12);
    xQueueSend(coda, &c, 0);
  }
} ascolto;

// Stato del cronometro e dei segni
float rssiMedio = -127;
int ultimoNumero = -1;
bool inCorsa = false, segnoPartenza = false, segnoArrivo = false;
float angoloPartenza = 0, angoloArrivo = 0;  // posizione della lancetta verde, in secondi
uint32_t avvio = 0, tempoMs = 0, ultimoMovimento = 0, scrittaFino = 0;
bool daRidisegnare = true;

// Lancette continue (prova) oppure a scatti di un secondo, come i pace clock classici
const bool LANCETTE_CONTINUE = true;
const uint32_t PASSO_MS = LANCETTE_CONTINUE ? 66 : 1000;  // circa 15 immagini al secondo

float secondiQuadrante(uint32_t ms) {
  return LANCETTE_CONTINUE ? (ms % 60000) / 1000.0f : (ms / 1000) % 60;
}

void punto(float secondi, float r, int16_t &x, int16_t &y) {
  float t = 2 * PI * secondi / 60;  // da mezzogiorno, in senso orario
  x = CX + r * sinf(t);
  y = CY - r * cosf(t);
}

void partenza(uint32_t ora) {
  inCorsa = true;
  avvio = ora;
  segnoPartenza = true;
  segnoArrivo = false;
  angoloPartenza = secondiQuadrante(ora);
  daRidisegnare = true;
}

void arrivo(uint32_t momento) {
  inCorsa = false;
  tempoMs = momento - avvio;  // ora dell'arrivo, non della fine della calma
  segnoArrivo = true;
  angoloArrivo = secondiQuadrante(momento);
  scrittaFino = millis() + SCRITTA_MS;
  daRidisegnare = true;
}

void azzera() {
  inCorsa = segnoPartenza = segnoArrivo = false;
  tempoMs = 0;
  scrittaFino = 0;
  daRidisegnare = true;
}

void elabora(const Campione &c) {
  uint32_t ora = millis();
  if (ultimoNumero >= 0 && c.numero == ultimoNumero) return;  // annuncio ripetuto
  ultimoNumero = c.numero;
  float a[3], g[3];
  for (int i = 0; i < 3; i++) {
    a[i] = c.assi[i] / 16384.0;
    g[i] = c.assi[i + 3] / 16.4;
  }
  float dinamica = fabsf(sqrtf(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) - 1.0f);
  float rotazione = sqrtf(g[0] * g[0] + g[1] * g[1] + g[2] * g[2]);
  if (dinamica > SOGLIA_CALMA_G || rotazione > SOGLIA_CALMA_DPS) ultimoMovimento = ora;

  if (!inCorsa && dinamica > SOGLIA_SPINTA_G) partenza(ora);
  bool vicino = rssiMedio > SOGLIA_VICINO;
  if (inCorsa && vicino && ora - ultimoMovimento >= CALMA_MS) arrivo(ultimoMovimento);
}

void testoCentrato(GFXcanvas16 &tela, const char *s, int y, const GFXfont *font, uint8_t scala, uint16_t colore) {
  tela.setFont(font);
  tela.setTextSize(scala);
  int16_t x1, y1;
  uint16_t w, h;
  tela.getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  tela.setTextColor(colore);
  tela.setCursor(CX - w / 2 - x1, y);
  tela.print(s);
}

// Livello 1: quadrante bianco con tacche e numeri, come un pace clock
void disegnaSfondo() {
  GFXcanvas16 &t = *sfondo;
  t.fillScreen(BLU_BORDO);
  t.fillCircle(CX, CY, 239, BIANCO);
  for (int s = 0; s < 60; s++) {
    bool lunga = s % 5 == 0;
    int16_t x0, y0, x1, y1;
    float rInterno = lunga ? R_TACCHE - 22 : R_TACCHE - 12;
    for (float d = -0.12; d <= 0.12; d += 0.04) {  // tacche spesse
      punto(s + (lunga ? d * 1.5 : d * 0.6), rInterno, x0, y0);
      punto(s + (lunga ? d * 1.5 : d * 0.6), R_TACCHE, x1, y1);
      t.drawLine(x0, y0, x1, y1, NERO);
    }
  }
  t.setFont(&FreeSansBold18pt7b);
  t.setTextSize(1);
  t.setTextColor(NERO);
  for (int n = 0; n < 60; n += 5) {
    char buf[4];
    snprintf(buf, sizeof(buf), "%d", n);
    int16_t x, y, x1, y1;
    uint16_t w, h;
    punto(n, R_NUMERI, x, y);
    t.getTextBounds(buf, 0, 0, &x1, &y1, &w, &h);
    t.setCursor(x - w / 2 - x1, y - h / 2 - y1);
    t.print(buf);
  }
}

// Livello 2: una lancetta affusolata dal centro verso il bordo
void lancetta(GFXcanvas16 &t, float secondi, uint16_t colore) {
  int16_t xp, yp, xa, ya, xb, yb, xc, yc;
  punto(secondi, R_LANCETTA, xp, yp);            // punta
  punto(secondi + 15, 7, xa, ya);                // base, lato destro
  punto(secondi - 15, 7, xb, yb);                // base, lato sinistro
  punto(secondi + 30, 22, xc, yc);               // coda corta
  t.fillTriangle(xp, yp, xa, ya, xb, yb, colore);
  t.fillTriangle(xc, yc, xa, ya, xb, yb, colore);
}

// Livello 3: pallino in prossimità della punta della lancetta verde
void segno(GFXcanvas16 &t, float secondi, uint16_t colore) {
  int16_t x, y;
  punto(secondi, R_SEGNI, x, y);
  t.fillCircle(x, y, 11, NERO);
  t.fillCircle(x, y, 9, colore);
}

uint32_t durataComposizione = 0;

void componi(uint32_t ora) {
  uint32_t t0 = millis();
  GFXcanvas16 &t = *composto;
  memcpy(t.getBuffer(), sfondo->getBuffer(), 480 * 480 * 2);

  float s = secondiQuadrante(ora);
  for (int i = 3; i >= 0; i--) lancetta(t, s + 15 * i, COLORE_LANCETTA[i]);  // la verde sopra
  t.fillCircle(CX, CY, 12, NERO);
  t.fillCircle(CX, CY, 5, GRIGIO);

  if (segnoPartenza) segno(t, angoloPartenza, VERDE);
  if (segnoArrivo) segno(t, angoloArrivo, ROSSO);
  if (ora < scrittaFino) {
    char buf[16];
    uint32_t dec = tempoMs / 100;
    snprintf(buf, sizeof(buf), "%lu:%02lu.%lu", dec / 600, (dec / 10) % 60, dec % 10);
    t.fillRoundRect(CX - 160, CY - 58, 320, 116, 18, NERO);
    testoCentrato(t, buf, CY + 34, &FreeSansBold24pt7b, 2, BIANCO);
  }

  // Indicatore del tag: piccolo testo sotto il centro
  bool presente = visto && (int32_t)(ora - visto) < (int32_t)TAG_PERSO_MS;  // con segno: visto può essere appena dopo ora (task BLE)
  char stato[32];
  if (presente) snprintf(stato, sizeof(stato), "tag %s %d dBm", rssiMedio > SOGLIA_VICINO ? "vicino" : "lontano", (int)rssiMedio);
  else snprintf(stato, sizeof(stato), "tag non trovato");
  testoCentrato(t, stato, CY + 110, &FreeSans9pt7b, 1, inCorsa ? AZZURRO : GRIGIO);

  // Batteria del display: partitore interno della T-RGB (metà tensione su GPIO 4).
  // La lettura richiede circa 40 ms, quindi solo ogni 10 s.
  static uint32_t ultimaBatteria = 0;
  static uint16_t batteriaMv = 0;
  if (!batteriaMv || ora - ultimaBatteria >= 10000) {
    ultimaBatteria = ora;
    batteriaMv = panel.getBattVoltage();
  }
  int percento = constrain((int)((batteriaMv - 3000) * 100L / 1200), 0, 100);
  char batteria[32];
  snprintf(batteria, sizeof(batteria), "batteria %.2f V  %d%%", batteriaMv / 1000.0, percento);
  testoCentrato(t, batteria, CY + 135, &FreeSans9pt7b, 1, percento < 20 ? ROSSO : GRIGIO);

  // Sullo schermo in un colpo (il driver copia nel framebuffer e gestisce la cache)
  panel.pushColors(0, 0, 480, 480, t.getBuffer());
  durataComposizione = millis() - t0;
}

void setup() {
  Serial.begin(115200);
  // Il driver riconosce da solo il modello dal chip del touch
  if (!panel.begin()) {
    Serial.println("Display non riconosciuto");
    while (true) delay(1000);
  }
  const char *modelli[] = {"sconosciuto", "2,1\" mezzo cerchio", "2,1\" cerchio", "2,8\""};
  Serial.printf("T-RGB modello: %s, touch: %s\n", modelli[panel.getModel()], panel.getTouchModelName());
  panel.setBrightness(16);

  sfondo = new GFXcanvas16(480, 480);
  composto = new GFXcanvas16(480, 480);
  if (!sfondo->getBuffer() || !composto->getBuffer()) {
    Serial.println("Memoria insufficiente per i livelli (PSRAM?)");
    while (true) delay(1000);
  }
  disegnaSfondo();

  // Diagnosi: perché la scheda è partita (per capire risvegli spontanei o errori)
  esp_reset_reason_t motivo = esp_reset_reason();
  const char *avvio = "accensione";
  if (motivo == ESP_RST_DEEPSLEEP) {
    esp_sleep_wakeup_cause_t causa = esp_sleep_get_wakeup_cause();
    avvio = causa == ESP_SLEEP_WAKEUP_EXT1 ? "risveglio: tocco"
          : causa == ESP_SLEEP_WAKEUP_EXT0 ? "risveglio: tasto BOOT" : "risveglio: altro";
  } else if (motivo == ESP_RST_PANIC) avvio = "riavvio per errore";
  else if (motivo == ESP_RST_BROWNOUT) avvio = "riavvio: tensione bassa";
  else if (motivo == ESP_RST_INT_WDT || motivo == ESP_RST_TASK_WDT || motivo == ESP_RST_WDT) avvio = "riavvio: watchdog";
  Serial.printf("Avvio: %s (reset %d)\n", avvio, (int)motivo);
  composto->fillScreen(NERO);
  testoCentrato(*composto, avvio, CY, &FreeSans9pt7b, 1, BIANCO);
  panel.pushColors(0, 0, 480, 480, composto->getBuffer());
  delay(2000);

  coda = xQueueCreate(64, sizeof(Campione));
  BLEDevice::init("");
  BLEScan *scan = BLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(&ascolto, true);  // true: riceve anche gli annunci ripetuti
  scan->setActiveScan(false);
  scan->setInterval(100);
  scan->setWindow(99);
  scan->start(0, nullptr, false);  // durata 0 = scansione continua
  Serial.println("BLE: ricerca di SwimTag avviata");
}

void loop() {
  uint32_t ora = millis();
  bool presente = visto && (int32_t)(ora - visto) < (int32_t)TAG_PERSO_MS;  // con segno: visto può essere appena dopo ora (task BLE)

  Campione c;
  while (xQueueReceive(coda, &c, 0) == pdTRUE) elabora(c);

  // Tocco: toglie i segni, le lancette continuano
  int16_t tx, ty;
  static uint32_t ultimoTocco = 0;
  if (ora - ultimoTocco > 300 && panel.getPoint(&tx, &ty, 1)) {
    ultimoTocco = ora;
    azzera();
  }

  // Comandi di prova dalla seriale: s = partenza, a = arrivo, r = azzera
  while (Serial.available()) {
    char k = Serial.read();
    if (k == 's') partenza(ora);
    if (k == 'a' && inCorsa) arrivo(ora);
    if (k == 'r') azzera();
  }

  // Si ricompone a ogni passo delle lancette, a ogni evento e quando scade la scritta
  static uint32_t ultimoSecondo = UINT32_MAX;
  static bool scrittaVisibile = false;
  uint32_t secondo = ora / PASSO_MS;
  bool scritta = ora < scrittaFino;
  if (secondo != ultimoSecondo || scritta != scrittaVisibile || daRidisegnare) {
    ultimoSecondo = secondo;
    scrittaVisibile = scritta;
    daRidisegnare = false;
    if (presente) rssiMedio = rssiMedio < -120 ? rssiUltimo : rssiMedio * 0.7 + rssiUltimo * 0.3;
    else rssiMedio = -127;
    componi(ora);
    // Solo se c'è spazio: con il core 2.x la seriale USB blocca il programma
    // quando il PC è collegato ma nessuno legge
    if (Serial.availableForWrite() > 120)
      Serial.printf("R,%lu,rssi=%d,inCorsa=%d,tempo=%lu,componi_ms=%lu\n",
                  ora, presente ? (int)rssiUltimo : -127, inCorsa, tempoMs, durataComposizione);
  }

  // Sonno profondo dopo SOSPENSIONE_MS senza tag, tocchi o cronometro in corsa;
  // un tocco sullo schermo lo risveglia (il firmware riparte da capo)
  uint32_t ultimaAttivita = max((uint32_t)visto, ultimoTocco);
  if (!inCorsa && (int32_t)(ora - ultimaAttivita) > (int32_t)SOSPENSIONE_MS) {
    GFXcanvas16 &t = *composto;
    t.fillScreen(NERO);
    testoCentrato(t, "in sospensione", CY - 10, &FreeSansBold18pt7b, 1, BIANCO);
    testoCentrato(t, "tocca per riattivare", CY + 30, &FreeSans9pt7b, 1, GRIGIO);
    panel.pushColors(0, 0, 480, 480, t.getBuffer());
    delay(1500);
    BLEDevice::deinit(false);
    // Nel sonno GPIO1 (interrupt del touch) resterebbe senza pull-up e potrebbe
    // risvegliare la scheda da solo; il tasto BOOT (GPIO0) è il risveglio di riserva
    rtc_gpio_pullup_en(GPIO_NUM_1);
    rtc_gpio_pulldown_dis(GPIO_NUM_1);
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);
    panel.enableTouchWakeup();
    panel.sleep();
  }
  delay(5);
}
