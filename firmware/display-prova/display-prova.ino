// Display di prova (LilyGO T-RGB 2,8"): riceve gli annunci BLE del tag "SwimTag",
// che contengono l'ultimo campione di accelerometro e giroscopio, senza collegarsi.
// - corona esterna: le 3 linee dell'accelerazione, in senso orario (un giro = 15 s)
// - centro: cronometro. Parte con un colpo secco, si ferma quando il tag è vicino
//   e fermo da 3 s, con l'ora dell'ultimo movimento. Un tocco sullo schermo azzera.
// Niente tremolio: lo schermo non viene mai cancellato. La corona si aggiorna un tratto
// alla volta; i testi si preparano in un riquadro in memoria e si copiano in un colpo.
// Driver del display: src/trgb (da LilyGo-T-RGB, adattato).
#include <Wire.h>
#include <Adafruit_GFX.h>  // disegno in memoria (GFXcanvas16) e font
#include <Fonts/FreeSansBold24pt7b.h>
#include <Fonts/FreeSans12pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include "src/trgb/LilyGo_RGBPanel.h"
#include <esp_cache.h>

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
// Riquadro dei testi: il rettangolo più largo che sta dentro la corona
const int RQ_X = 70, RQ_Y = 117, RQ_L = 340, RQ_A = 246;

// Colori RGB565, come la pagina tools/assi.html in tema scuro
const uint16_t NERO = 0x0000, BIANCO = 0xFFFF, GRIGIO = 0x8410, GRIGIO_SCURO = 0x2945;
const uint16_t ARANCIO = 0xFD20, AZZURRO = 0x5D9F, VERDE = 0x07E0;
const uint16_t COLORE_ASSE[3] = {0xFB4B, 0x4E11, 0x6D1F};  // X rosso, Y verde, Z blu

LilyGo_RGBPanel panel;

// Tela che disegna direttamente nel framebuffer (per la corona)
class Tela : public GFXcanvas16 {
 public:
  Tela() : GFXcanvas16(480, 480, false) {}
  void usa(uint16_t *b) { buffer = b; }
} schermo;
GFXcanvas16 *riquadro;  // testi centrali, copiati nel framebuffer quando sono pronti

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

int raggio(float v) {
  if (v < -2) v = -2;
  if (v > 2) v = 2;
  return R_DENTRO + (int)((v + 2) / 4 * (R_FUORI - R_DENTRO));
}

// Punto della corona alla posizione (anche frazionaria) del campione, da mezzogiorno in senso orario
void punto(float pos, int r, int16_t &x, int16_t &y) {
  float t = 2 * PI * pos / CAMPIONI_GIRO;
  x = CX + r * sinf(t);
  y = CY - r * cosf(t);
}

// Scrive in PSRAM le righe da y0 a y1 rimaste nella cache della CPU,
// altrimenti il display le vede solo quando la cache si svuota da sola
void sincronizza(int y0, int y1) {
  if (y0 < 0) y0 = 0;
  if (y1 > 479) y1 = 479;
  if (y1 < y0) return;
  esp_cache_msync(panel.framebuffer() + y0 * 480, (y1 - y0 + 1) * 480 * 2,
                  ESP_CACHE_MSYNC_FLAG_DIR_C2M | ESP_CACHE_MSYNC_FLAG_UNALIGNED);
}

// Disegna il tratto appena arrivato e cancella lo spicchio davanti alla lancetta
void disegnaUltimo() {
  uint32_t j = scritti - 1;
  float e = (j + VUOTO) % CAMPIONI_GIRO;
  int16_t x0, y0, x1, y1, x2, y2, x3, y3;
  punto(e - 0.5, R_DENTRO - 1, x0, y0);
  punto(e - 0.5, R_FUORI + 2, x1, y1);
  punto(e + 1.5, R_FUORI + 2, x2, y2);
  punto(e + 1.5, R_DENTRO - 1, x3, y3);
  schermo.fillTriangle(x0, y0, x1, y1, x2, y2, NERO);
  schermo.fillTriangle(x0, y0, x2, y2, x3, y3, NERO);
  int ymin = min(min(y0, y1), min(y2, y3)), ymax = max(max(y0, y1), max(y2, y3));
  sincronizza(ymin, ymax);
  if (j == 0) return;
  int i0 = (j - 1) % CAMPIONI_GIRO, i1 = j % CAMPIONI_GIRO;
  for (int asse = 0; asse < 3; asse++) {
    float v0 = storico[asse][i0], v1 = storico[asse][i1];
    if (isnan(v0) || isnan(v1)) continue;
    int r0 = raggio(v0), r1 = raggio(v1);
    for (int d = 0; d < 2; d++) {  // spessore di 2 pixel
      schermo.drawLine(CX + (r0 + d) * sinT[i0], CY - (r0 + d) * cosT[i0],
                       CX + (r1 + d) * sinT[i1], CY - (r1 + d) * cosT[i1], COLORE_ASSE[asse]);
    }
  }
  int ya = CY - (R_FUORI + 2) * cosT[i0], yb = CY - (R_FUORI + 2) * cosT[i1];
  int yc = CY - (R_DENTRO - 1) * cosT[i0], yd = CY - (R_DENTRO - 1) * cosT[i1];
  sincronizza(min(min(ya, yb), min(yc, yd)) - 1, max(max(ya, yb), max(yc, yd)) + 1);
}

void aggiungi(float ax, float ay, float az) {
  int i = scritti % CAMPIONI_GIRO;
  storico[0][i] = ax;
  storico[1][i] = ay;
  storico[2][i] = az;
  scritti++;
  disegnaUltimo();
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

// Testo centrato orizzontalmente sullo schermo, disegnato su una tela con origine (ox, oy)
void testoCentrato(GFXcanvas16 &tela, int ox, int oy, const char *s, int y, const GFXfont *font,
                   uint8_t scala, uint16_t colore) {
  tela.setFont(font);
  tela.setTextSize(scala);
  int16_t x1, y1;
  uint16_t w, h;
  tela.getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  tela.setTextColor(colore);
  tela.setCursor(CX - ox - w / 2 - x1, y - oy);
  tela.print(s);
}

void copiaRiquadro() {
  uint16_t *fb = panel.framebuffer();
  for (int r = 0; r < RQ_A; r++)
    memcpy(fb + (RQ_Y + r) * 480 + RQ_X, riquadro->getBuffer() + r * RQ_L, RQ_L * 2);
  sincronizza(RQ_Y, RQ_Y + RQ_A - 1);
}

void disegnaTesti(bool presente) {
  GFXcanvas16 &t = *riquadro;
  t.fillScreen(NERO);
  testoCentrato(t, RQ_X, RQ_Y, "SwimTimer", 150, &FreeSans12pt7b, 1, GRIGIO);
  char buf[40];
  uint32_t dec = tempoMs / 100;
  snprintf(buf, sizeof(buf), "%lu:%02lu.%lu", dec / 600, (dec / 10) % 60, dec % 10);
  testoCentrato(t, RQ_X, RQ_Y, buf, 275, &FreeSansBold24pt7b, 2, inCorsa ? ARANCIO : BIANCO);
  const char *stato = inCorsa ? "in corsa" : tempoMs ? "arrivato" : "colpo secco per partire";
  testoCentrato(t, RQ_X, RQ_Y, stato, 320, &FreeSans9pt7b, 1, inCorsa ? ARANCIO : tempoMs ? VERDE : GRIGIO);
  if (presente) snprintf(buf, sizeof(buf), "%s  %d dBm", rssiMedio > SOGLIA_VICINO ? "vicino" : "lontano", (int)rssiMedio);
  else snprintf(buf, sizeof(buf), "tag non trovato");
  testoCentrato(t, RQ_X, RQ_Y, buf, 352, &FreeSans9pt7b, 1, AZZURRO);
  copiaRiquadro();
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

  // Sfondo disegnato una volta sola
  schermo.usa(panel.framebuffer());
  schermo.fillScreen(NERO);
  schermo.drawCircle(CX, CY, R_DENTRO - 3, GRIGIO_SCURO);
  testoCentrato(schermo, 0, 0, "tocca per azzerare", 385, &FreeSans9pt7b, 1, GRIGIO_SCURO);
  sincronizza(0, 479);
  riquadro = new GFXcanvas16(RQ_L, RQ_A);

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

  Campione c;
  while (xQueueReceive(coda, &c, 0) == pdTRUE) elabora(c);

  // Tocco: azzera il cronometro
  int16_t tx, ty;
  static uint32_t ultimoTocco = 0;
  if (ora - ultimoTocco > 300 && panel.getPoint(&tx, &ty, 1)) {
    ultimoTocco = ora;
    inCorsa = false;
    tempoMs = 0;
  }
  if (inCorsa) tempoMs = ora - avvio;

  // Testi 10 volte al secondo
  static uint32_t ultimiTesti = 0;
  if (ora - ultimiTesti >= 100) {
    ultimiTesti = ora;
    if (presente) rssiMedio = rssiMedio < -120 ? rssiUltimo : rssiMedio * 0.8 + rssiUltimo * 0.2;
    else rssiMedio = -127;
    uint32_t t0 = micros();
    disegnaTesti(presente);
    static uint32_t ultimoLog = 0;
    if (ora - ultimoLog >= 1000) {
      ultimoLog = ora;
      Serial.printf("R,%lu,rssi=%d,media=%d,campioni=%lu,inCorsa=%d,tempo=%lu,testi_us=%lu\n",
                    ora, presente ? (int)rssiUltimo : -127, (int)rssiMedio, scritti, inCorsa, tempoMs,
                    micros() - t0);
    }
  }
  delay(5);
}
