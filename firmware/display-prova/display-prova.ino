// Display di prova (LilyGO T-RGB 2,8"): riceve gli annunci BLE del tag "SwimTag",
// che contengono l'ultimo campione di accelerometro e giroscopio, senza collegarsi.
// - corona esterna: le 3 linee dell'accelerazione, in senso orario (un giro = 15 s)
// - centro: cronometro. Parte con un colpo secco, si ferma quando il tag è vicino
//   e fermo da 3 s, con l'ora dell'ultimo movimento. Un tocco sullo schermo azzera.
// Doppio buffer: si disegna nel buffer nascosto e lo si mostra al vsync (niente tremolio).
// Driver del display: src/trgb (da LilyGo-T-RGB, adattato).
#include <Wire.h>
#include <Adafruit_GFX.h>  // disegno nel framebuffer (GFXcanvas16) e font
#include <Fonts/FreeSansBold24pt7b.h>
#include <Fonts/FreeSans12pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include "src/trgb/LilyGo_RGBPanel.h"

const char *NOME_TAG = "SwimTag";
const int SOGLIA_VICINO = -72;       // dBm: sopra = vicino (da tarare in vasca)
const uint32_t TAG_PERSO_MS = 3000;
const float SOGLIA_SPINTA_G = 0.8;   // accelerazione oltre la gravità che fa partire il tempo
const float SOGLIA_CALMA_G = 0.10;   // sotto questa e sotto SOGLIA_CALMA_DPS il tag è fermo
const float SOGLIA_CALMA_DPS = 20;
const uint32_t CALMA_MS = 3000;

// Geometria: centro, corona del grafico (circa 1/10 del raggio)
const int CX = 240, CY = 240;
const int R_DENTRO = 214, R_FUORI = 238;
const int CAMPIONI_GIRO = 300;       // 20 campioni/s: un giro ogni 15 s
const int VUOTO = 8;                 // campioni non disegnati davanti alla lancetta

// Colori RGB565, come la pagina tools/assi.html in tema scuro
const uint16_t NERO = 0x0000, BIANCO = 0xFFFF, GRIGIO = 0x8410, GRIGIO_SCURO = 0x2945;
const uint16_t ARANCIO = 0xFD20, AZZURRO = 0x5D9F, VERDE = 0x07E0;
const uint16_t COLORE_ASSE[3] = {0xFB4B, 0x4E11, 0x6D1F};  // X rosso, Y verde, Z blu

LilyGo_RGBPanel panel;

// Tela che disegna direttamente nel framebuffer nascosto
class Tela : public GFXcanvas16 {
 public:
  Tela() : GFXcanvas16(480, 480, false) {}
  void usa(uint16_t *b) { buffer = b; }
} tela;

struct Campione {
  uint8_t numero;
  int8_t rssi;
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
    String md = d.getManufacturerData();
    if (md.length() != 15 || (uint8_t)md[0] != 0xFF || (uint8_t)md[1] != 0xFF) return;
    Campione c;
    c.numero = md[2];
    c.rssi = d.getRSSI();
    memcpy(c.assi, md.c_str() + 3, 12);
    xQueueSend(coda, &c, 0);
  }
} ascolto;

// Storico per la corona: NAN = campione perso
float storico[3][CAMPIONI_GIRO];
uint32_t scritti = 0;
int ultimoNumero = -1;

float sinT[CAMPIONI_GIRO], cosT[CAMPIONI_GIRO];

// Cronometro
float rssiMedio = -127;
bool inCorsa = false;
uint32_t avvio = 0, tempoMs = 0, ultimoMovimento = 0;

void aggiungi(float ax, float ay, float az) {
  int i = scritti % CAMPIONI_GIRO;
  storico[0][i] = ax;
  storico[1][i] = ay;
  storico[2][i] = az;
  scritti++;
}

void elabora(const Campione &c) {
  uint32_t ora = millis();
  float a[3], g[3];
  for (int i = 0; i < 3; i++) {
    a[i] = c.assi[i] / 16384.0;
    g[i] = c.assi[i + 3] / 16.4;
  }

  // Campioni persi: buchi nella corona, così il tempo resta in scala
  int salto = ultimoNumero < 0 ? 1 : (uint8_t)(c.numero - ultimoNumero);
  if (salto == 0) return;  // annuncio ripetuto
  if (salto > 20) salto = 1;
  for (int k = 1; k < salto; k++) aggiungi(NAN, NAN, NAN);
  ultimoNumero = c.numero;
  aggiungi(a[0], a[1], a[2]);

  float dinamica = fabsf(sqrtf(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) - 1.0f);
  float rotazione = sqrtf(g[0] * g[0] + g[1] * g[1] + g[2] * g[2]);
  if (dinamica > SOGLIA_CALMA_G || rotazione > SOGLIA_CALMA_DPS) ultimoMovimento = ora;

  if (!inCorsa && dinamica > SOGLIA_SPINTA_G) {
    inCorsa = true;
    avvio = ora;
  }
  bool vicino = rssiMedio > SOGLIA_VICINO;
  if (inCorsa && vicino && ora - ultimoMovimento >= CALMA_MS) {
    inCorsa = false;
    tempoMs = ultimoMovimento - avvio;  // ora dell'arrivo, non della fine della calma
  }
}

void testoCentrato(const char *s, int y, const GFXfont *font, uint8_t scala, uint16_t colore) {
  tela.setFont(font);
  tela.setTextSize(scala);
  int16_t x1, y1;
  uint16_t w, h;
  tela.getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  tela.setTextColor(colore);
  tela.setCursor(CX - w / 2 - x1, y);
  tela.print(s);
}

int raggio(float v) {
  if (v < -2) v = -2;
  if (v > 2) v = 2;
  return R_DENTRO + (int)((v + 2) / 4 * (R_FUORI - R_DENTRO));
}

void disegnaCorona() {
  tela.drawCircle(CX, CY, R_DENTRO - 2, GRIGIO_SCURO);
  tela.drawCircle(CX, CY, (R_DENTRO + R_FUORI) / 2, GRIGIO_SCURO);  // 0 g
  if (scritti < 2) return;
  uint32_t primo = scritti > CAMPIONI_GIRO ? scritti - CAMPIONI_GIRO + VUOTO : 0;
  for (int asse = 0; asse < 3; asse++) {
    for (uint32_t j = primo + 1; j < scritti; j++) {
      int i0 = (j - 1) % CAMPIONI_GIRO, i1 = j % CAMPIONI_GIRO;
      float v0 = storico[asse][i0], v1 = storico[asse][i1];
      if (isnan(v0) || isnan(v1)) continue;
      int r0 = raggio(v0), r1 = raggio(v1);
      // Due linee affiancate per uno spessore di 2 pixel
      for (int d = 0; d < 2; d++) {
        tela.drawLine(CX + (r0 + d) * sinT[i0], CY - (r0 + d) * cosT[i0],
                      CX + (r1 + d) * sinT[i1], CY - (r1 + d) * cosT[i1], COLORE_ASSE[asse]);
      }
    }
  }
  // Lancetta sulla posizione attuale
  int i = (scritti - 1) % CAMPIONI_GIRO;
  tela.drawLine(CX + (R_DENTRO - 4) * sinT[i], CY - (R_DENTRO - 4) * cosT[i],
                CX + (R_FUORI + 1) * sinT[i], CY - (R_FUORI + 1) * cosT[i], GRIGIO);
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

  for (int i = 0; i < CAMPIONI_GIRO; i++) {
    float t = 2 * PI * i / CAMPIONI_GIRO;  // da mezzogiorno, in senso orario
    sinT[i] = sinf(t);
    cosT[i] = cosf(t);
  }

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
  bool presente = visto && ora - visto < TAG_PERSO_MS;
  if (presente) rssiMedio = rssiMedio < -120 ? rssiUltimo : rssiMedio * 0.9 + rssiUltimo * 0.1;
  else rssiMedio = -127;

  Campione c;
  while (xQueueReceive(coda, &c, 0) == pdTRUE) elabora(c);

  // Tocco: azzera il cronometro
  int16_t tx, ty;
  static uint32_t ultimoTocco = 0;
  if (panel.getPoint(&tx, &ty, 1) && ora - ultimoTocco > 500) {
    ultimoTocco = ora;
    inCorsa = false;
    tempoMs = 0;
  }
  if (inCorsa) tempoMs = ora - avvio;

  tela.usa(panel.bufferNascosto());
  tela.fillScreen(NERO);
  disegnaCorona();

  testoCentrato("SwimTimer", 150, &FreeSans12pt7b, 1, GRIGIO);
  char buf[40];
  uint32_t dec = tempoMs / 100;
  snprintf(buf, sizeof(buf), "%lu:%02lu.%lu", dec / 600, (dec / 10) % 60, dec % 10);
  testoCentrato(buf, 275, &FreeSansBold24pt7b, 2, inCorsa ? ARANCIO : BIANCO);

  const char *stato = inCorsa ? "in corsa" : tempoMs ? "arrivato" : "pronto: colpo secco per partire";
  testoCentrato(stato, 320, &FreeSans9pt7b, 1, inCorsa ? ARANCIO : tempoMs ? VERDE : GRIGIO);

  if (presente) snprintf(buf, sizeof(buf), "%s  %d dBm", rssiMedio > SOGLIA_VICINO ? "vicino" : "lontano", (int)rssiMedio);
  else snprintf(buf, sizeof(buf), "tag non trovato");
  testoCentrato(buf, 355, &FreeSans9pt7b, 1, AZZURRO);
  testoCentrato("tocca per azzerare", 385, &FreeSans9pt7b, 1, GRIGIO_SCURO);

  panel.mostra();

  static uint32_t ultimoLog = 0;
  if (ora - ultimoLog >= 1000) {
    ultimoLog = ora;
    Serial.printf("R,%lu,rssi=%d,media=%d,campioni=%lu,inCorsa=%d,tempo=%lu\n",
                  ora, presente ? (int)rssiUltimo : -127, (int)rssiMedio, scritti, inCorsa, tempoMs);
  }
}
