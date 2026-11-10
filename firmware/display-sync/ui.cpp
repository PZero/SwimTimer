// Schermata di stato delle tag (docs/img/mockup-stato-tag.png): 3 spicchi da 120 gradi, uno per tag
// (tag 1 in alto, poi in senso orario), 512 blocchi in 4 file da 128 sul bordo, testi dentro,
// disco centrale con lo stato della SD. Due tele 480x480 in PSRAM: sfondo (solo quando cambia il
// layout) e composto (a ogni ridisegno), copiato sul pannello con panel.pushColors.
#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Fonts/FreeSansBold12pt7b.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include "scheda.h"
#include "stato.h"
#include "ui.h"

// Curva LiPo (V, %) identica a CURVA_LIPO di tools/index.html
static const int16_t LIPO_MV[] = {4200, 4150, 4110, 4080, 4020, 3980, 3950, 3910, 3870, 3850, 3840, 3820, 3800, 3790, 3770, 3750, 3730, 3710, 3690, 3610, 3270};
static const int8_t LIPO_PCT[] = {100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0};
static int percentualeLipo(int mv) {
  if (mv >= LIPO_MV[0]) return 100;
  for (int i = 1; i < (int)(sizeof(LIPO_MV) / sizeof(LIPO_MV[0])); i++)
    if (mv >= LIPO_MV[i])
      return LIPO_PCT[i] + (LIPO_PCT[i - 1] - LIPO_PCT[i]) * (mv - LIPO_MV[i]) / (LIPO_MV[i - 1] - LIPO_MV[i]);
  return 0;
}

LilyGo_RGBPanel panel;

static GFXcanvas16 *sfondo, *composto;

static const int CX = 240, CY = 240;
static inline uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) { return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3); }
// Scurisce un colore RGB565 (k = 0..256)
static uint16_t scur(uint16_t c, int k) {
  int r = ((c >> 11) & 31) * k >> 8, g = ((c >> 5) & 63) * k >> 8, b = (c & 31) * k >> 8;
  return (r << 11) | (g << 5) | b;
}

// Colori come nel mockup (mockup2.py)
static const uint16_t C_NERO = 0x0000;
static const uint16_t C_LIBERO = rgb(52, 52, 58), C_OK = rgb(40, 200, 90), C_ATTESA = rgb(255, 170, 0);
static const uint16_t C_TX = rgb(0, 200, 255), C_APERTO = rgb(255, 255, 255);
static const uint16_t C_TAG[3] = {rgb(255, 80, 160), rgb(120, 140, 255), rgb(255, 220, 60)};   // colore dello spicchio se la tag non ne ha uno
// Colore della tag: quello scelto dall'utente (tavolozza del §7) oppure quello dello spicchio
static uint16_t colTag(int i, const TagStato &s) {
  if (s.colore <= 9) return rgb(SYNC_TAVOLOZZA[s.colore][0], SYNC_TAVOLOZZA[s.colore][1], SYNC_TAVOLOZZA[s.colore][2]);
  return C_TAG[i];
}
static const uint16_t C_DIV = rgb(90, 90, 100), C_BIANCO = rgb(255, 255, 255), C_GRIGIO = rgb(150, 150, 150);
static const uint16_t C_ROSSO = rgb(255, 70, 70);

// Geometria: centri degli spicchi in gradi (0 = ore 3, senso orario), file di blocchi (raggio esterno/interno)
static const float CENTRI[3] = {-90, 30, 150};
static const int FILA_RO[4] = {232, 220, 208, 196}, FILA_RI[4] = {223, 211, 199, 187};
static const float MARGINE = 4;
static const int N_COL = 128;
static float cs0[3][N_COL], sn0[3][N_COL], cs1[3][N_COL], sn1[3][N_COL];  // angoli di inizio/fine di ogni colonna

static void geometria() {
  float passo = (120 - 2 * MARGINE) / N_COL;
  for (int t = 0; t < 3; t++)
    for (int j = 0; j < N_COL; j++) {
      float a0 = (CENTRI[t] - 60 + MARGINE + j * passo) * DEG_TO_RAD;
      float a1 = a0 + passo * 0.82f * DEG_TO_RAD;
      cs0[t][j] = cosf(a0); sn0[t][j] = sinf(a0);
      cs1[t][j] = cosf(a1); sn1[t][j] = sinf(a1);
    }
}

// Testo centrato in (x, y)
static void testo(GFXcanvas16 &t, const char *s, int x, int y, const GFXfont *f, uint16_t col) {
  t.setFont(f);
  t.setTextSize(1);
  int16_t x1, y1;
  uint16_t w, h;
  t.getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  t.setTextColor(col);
  t.setCursor(x - w / 2 - x1, y - h / 2 - y1);
  t.print(s);
}

static int larghezza(GFXcanvas16 &t, const char *s, const GFXfont *f) {
  t.setFont(f);
  t.setTextSize(1);
  int16_t x1, y1;
  uint16_t w, h;
  t.getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  return w;
}

// Fascia ad anello tra due raggi, da ga a gb (gradi), a piccoli passi
static void arco(GFXcanvas16 &t, float ro, float ri, float ga, float gb, uint16_t col) {
  for (float g = ga; g < gb; g += 3) {
    float g2 = min(g + 3.0f, gb);
    float c0 = cosf(g * DEG_TO_RAD), s0 = sinf(g * DEG_TO_RAD), c1 = cosf(g2 * DEG_TO_RAD), s1 = sinf(g2 * DEG_TO_RAD);
    t.fillTriangle(CX + ro * c0, CY + ro * s0, CX + ro * c1, CY + ro * s1, CX + ri * c1, CY + ri * s1, col);
    t.fillTriangle(CX + ro * c0, CY + ro * s0, CX + ri * c1, CY + ri * s1, CX + ri * c0, CY + ri * s0, col);
  }
}

// ---- sfondo: spicchi tinti, divisori, arco colore tag; si rifa' solo se cambia quali tag ci sono ----
static uint8_t layoutUsato = 0xFF;
static uint16_t layoutColori[3];

static void disegnaSfondo(uint8_t usate, const uint16_t *col) {
  GFXcanvas16 &t = *sfondo;
  uint16_t *px = t.getBuffer();
  uint16_t tinta[3];
  for (int i = 0; i < 3; i++)  // spicchio vuoto quasi nero; con tag: colore della tag al 12 %
    tinta[i] = (usate >> i) & 1 ? scur(col[i], 31) : rgb(10, 10, 12);
  for (int y = 0; y < 480; y++)
    for (int x = 0; x < 480; x++) {
      int dx = x - CX, dy = y - CY;
      if (dx * dx + dy * dy > 239 * 239) { px[y * 480 + x] = C_NERO; continue; }
      float a = atan2f(dy, dx) * RAD_TO_DEG;           // -180..180
      float r = fmodf(a + 150 + 720, 360);               // 0..360 dall'inizio del primo spicchio
      px[y * 480 + x] = tinta[(int)(r / 120)];
    }
  for (int i = 0; i < 3; i++) {  // divisori a 120 gradi (spessi 3 px)
    float g = (CENTRI[i] + 60) * DEG_TO_RAD, c = cosf(g), s = sinf(g);
    for (int k = -1; k <= 1; k++)
      t.drawLine(CX - k * s, CY + k * c, CX + 239 * c - k * s, CY + 239 * s + k * c, C_DIV);
  }
  for (int i = 0; i < 3; i++)  // arco sottile del colore della tag sul bordo
    if ((usate >> i) & 1) arco(t, 239, 234, CENTRI[i] - 60 + MARGINE, CENTRI[i] + 60 - MARGINE, col[i]);
  layoutUsato = usate;
  memcpy(layoutColori, col, sizeof(layoutColori));
}

// ---- una tag ----
struct Vista {
  const char *stato;
  uint16_t col;
  float scuro;  // 1 = normale, <1 = attenuato (spenta, non vista)
};

static Vista vista(const TagStato &t, uint32_t ora) {
  bool nonVista = (int32_t)(ora - t.vistoMs) > 10000;
  if (t.collegata || (t.stato == ST_SINCRONIZZA && !nonVista)) return {"SCARICA", C_TX, 1};
  if (t.stato == ST_SONNO) return {"SPENTA", C_GRIGIO, 0.45f};
  if (nonVista) return {"NON VISTA", rgb(130, 130, 140), 0.7f};
  switch (t.stato) {
    case ST_PRONTA: return {"PRONTA", C_OK, 1};
    case ST_REGISTRA: return {"REGISTRA", C_ROSSO, 1};
    case ST_PIENA: return {"MEM. PIENA", rgb(255, 120, 40), 1};
    default: return {"ERRORE", rgb(255, 40, 100), 1};
  }
}

static void disegnaBlocchi(GFXcanvas16 &t, int i, const TagStato &s, float scuro) {
  int k = (int)(scuro * 256);
  uint16_t col[5] = {scur(C_LIBERO, k), scur(C_APERTO, k), scur(C_ATTESA, k), scur(C_OK, k), scur(C_TX, k)};
  for (int f = 0; f < 4; f++)
    for (int j = 0; j < N_COL; j++) {
      int b = f * N_COL + j;
      int v = s.mappaValida ? mappaGet(s.mappa, b) : 0;
      uint16_t c;
      if (v == 2 && (s.txFisico[0] == b || s.txFisico[1] == b)) c = col[4];
      else c = v == 0 ? col[0] : v == 1 ? col[1] : v == 2 ? col[2] : col[3];
      float ro = FILA_RO[f], ri = FILA_RI[f];
      int x0 = CX + ro * cs0[i][j], y0 = CY + ro * sn0[i][j], x1 = CX + ro * cs1[i][j], y1 = CY + ro * sn1[i][j];
      int x2 = CX + ri * cs1[i][j], y2 = CY + ri * sn1[i][j], x3 = CX + ri * cs0[i][j], y3 = CY + ri * sn0[i][j];
      t.fillTriangle(x0, y0, x1, y1, x2, y2, c);
      t.fillTriangle(x0, y0, x2, y2, x3, y3, c);
    }
}

static void disegnaTag(GFXcanvas16 &t, int i, const TagStato &s, uint32_t ora) {
  if (!s.usata) return;
  Vista v = vista(s, ora);
  disegnaBlocchi(t, i, s, v.scuro);

  // Testo al baricentro dello spicchio (come il mockup, un po' piu' fuori per i testi piu' larghi)
  float g = CENTRI[i] * DEG_TO_RAD;
  float rr = i == 0 ? 118 : 116;
  int x = CX + cosf(g) * rr, y = CY + sinf(g) * rr - (i == 0 ? 40 : 44);
  uint16_t bianco = v.scuro < 1 ? C_GRIGIO : C_BIANCO;

  // Nome: quello scelto dall'utente (font piu' piccolo se lungo) oppure ST-xxxx ("ST-" piccolo, le 4 cifre grandi);
  // il pallino del colore della tag sul lato esterno
  bool personale = s.nome[0] && !(strlen(s.nome) == 7 && !strncmp(s.nome, "ST-", 3));
  int x0, wtot;
  if (personale) {
    const GFXfont *f = &FreeSansBold12pt7b;
    wtot = larghezza(t, s.nome, f);
    if (wtot > 150) { f = &FreeSansBold9pt7b; wtot = larghezza(t, s.nome, f); }   // nomi lunghi: carattere piu' piccolo
    x0 = x - wtot / 2;
    testo(t, s.nome, x, y, f, bianco);
  } else {
    char hex[8], nome[8];
    snprintf(hex, sizeof(hex), "%04lX", (unsigned long)(s.id & 0xFFFF));
    snprintf(nome, sizeof(nome), "ST-");
    int wp = larghezza(t, nome, &FreeSans9pt7b), wh = larghezza(t, hex, &FreeSansBold12pt7b);
    wtot = wp + wh + 4;
    x0 = x - wtot / 2;
    testo(t, nome, x0 + wp / 2, y + 2, &FreeSans9pt7b, C_GRIGIO);
    testo(t, hex, x0 + wp + 4 + wh / 2, y, &FreeSansBold12pt7b, bianco);
  }
  int xd = (i == 2) ? x0 - 10 : x0 + wtot + 10;
  t.fillCircle(xd, y, 5, scur(colTag(i, s), (int)(v.scuro * 256)));

  // Pastiglia di stato
  y += 28;
  int wt = larghezza(t, v.stato, &FreeSansBold9pt7b);
  t.fillRoundRect(x - wt / 2 - 9, y - 12, wt + 18, 24, 12, scur(v.col, 64));
  t.drawRoundRect(x - wt / 2 - 9, y - 12, wt + 18, 24, 12, v.col);
  t.drawRoundRect(x - wt / 2 - 8, y - 11, wt + 16, 22, 11, v.col);
  testo(t, v.stato, x, y, &FreeSansBold9pt7b, v.col);

  // Batteria: stessa curva LiPo della pagina tools/index.html (CURVA_LIPO), cosi' i due numeri coincidono
  char riga[24];
  int mv = s.batt20 * 20;
  int pct = percentualeLipo(mv);
  snprintf(riga, sizeof(riga), s.batt20 ? "batteria %d%%" : "batteria ?", pct);
  y += 24;
  testo(t, riga, x, y, &FreeSans9pt7b, pct < 20 && s.batt20 ? C_ROSSO : rgb(190, 190, 190));

  // Blocchi da validare: dalla mappa se collegata, altrimenti dall'annuncio
  int da = s.inAttesa;
  if (s.collegata && s.mappaValida) {
    da = 0;
    for (int b = 0; b < SYNC_N_BLOCCHI; b++) da += mappaGet(s.mappa, b) == 2;
  }
  y += 18;
  if (s.anomalie) snprintf(riga, sizeof(riga), "%lu anomali (vedi SD)", (unsigned long)s.anomalie);
  else if (s.ultimoStop) snprintf(riga, sizeof(riga), "STOP motivo %u", s.ultimoStop);
  else if (da) snprintf(riga, sizeof(riga), "%d da validare", da);
  else snprintf(riga, sizeof(riga), "tutto validato");
  testo(t, riga, x, y, &FreeSans9pt7b, (s.anomalie || s.ultimoStop) ? C_ROSSO : rgb(190, 190, 190));

  // Segnale in % (dall'RSSI dell'ultimo annuncio) e, durante lo scarico, la velocita'; se non si sente da > 10 s: da quanto
  y += 18;
  uint32_t sec = (ora - s.vistoMs) / 1000;
  // Scala provvisoria (2026-11-10): a 10 cm il T-RGB riceve -57/-64 dBm (antenna dietro lo schermo). Da tarare a 1 e 3 m.
  int sig = constrain((s.rssi + 95) * 100 / 40, 0, 100);    // -95 dBm = 0 %, -55 dBm = 100 %
  uint16_t cRiga = rgb(190, 190, 190);
  if (sec > 10) {
    if (sec >= 60) snprintf(riga, sizeof(riga), "non vista da %lu min", (unsigned long)(sec / 60));
    else snprintf(riga, sizeof(riga), "non vista da %lu s", (unsigned long)sec);
    cRiga = C_GRIGIO;
  } else if (s.collegata) {
    uint32_t kb10 = s.bps * 10 / 1024;
    snprintf(riga, sizeof(riga), "%lu,%lu KB/s  %d%%", (unsigned long)(kb10 / 10), (unsigned long)(kb10 % 10), sig);
  } else {
    snprintf(riga, sizeof(riga), "segnale %d%%", sig);
    if (sig < 25) cRiga = C_ROSSO;
  }
  testo(t, riga, x, y, &FreeSans9pt7b, cRiga);
}

static void disegnaDisco(GFXcanvas16 &t, const SdStato &sd) {
  uint16_t bordo = sd.pronta ? C_DIV : C_ROSSO;
  t.fillCircle(CX, CY, 46, bordo);
  t.fillCircle(CX, CY, 43, rgb(14, 16, 20));
  testo(t, "SD", CX, CY - 12, &FreeSansBold9pt7b, rgb(200, 200, 200));
  char s[16];
  if (sd.pronta) {
    if (sd.liberiMb >= 1024) snprintf(s, sizeof(s), "%lu,%lu GB", (unsigned long)(sd.liberiMb / 1024), (unsigned long)(sd.liberiMb % 1024 * 10 / 1024));
    else snprintf(s, sizeof(s), "%lu MB", (unsigned long)sd.liberiMb);
    testo(t, s, CX, CY + 12, &FreeSans9pt7b, rgb(170, 170, 170));
  } else {
    const char *e = sd.errore == SD_PIENA ? "PIENA" : sd.errore == SD_ERR_SCRITTURA ? "ERR. SCR." : sd.errore == SD_ERR_RILETTURA ? "ERR. LETT." : "ASSENTE";
    testo(t, e, CX, CY + 12, &FreeSans9pt7b, C_ROSSO);
  }
}

void uiInit() {
  if (!panel.begin()) {
    Serial.println("Display non riconosciuto");
    while (true) delay(1000);
  }
  panel.setBrightness(16);
  sfondo = new GFXcanvas16(480, 480);
  composto = new GFXcanvas16(480, 480);
  if (!sfondo->getBuffer() || !composto->getBuffer()) {
    Serial.println("Memoria insufficiente per le tele (PSRAM?)");
    while (true) delay(1000);
  }
  geometria();
  composto->fillScreen(C_NERO);
  testo(*composto, "SwimTimer sync", CX, CY, &FreeSansBold12pt7b, C_BIANCO);
  panel.pushColors(0, 0, 480, 480, composto->getBuffer());
}

void uiAggiorna() {
  static uint32_t ultimo = 0;
  uint32_t ora = millis();
  if (ora - ultimo < 200) return;  // ~5 volte al secondo
  ultimo = ora;

  static StatoCopia s;
  statoCopia(s);
  uint8_t usate = 0;
  for (int i = 0; i < 3; i++) usate |= s.tag[i].usata << i;
  uint16_t colori[3];
  for (int i = 0; i < 3; i++) colori[i] = colTag(i, s.tag[i]);
  if (usate != layoutUsato || memcmp(colori, layoutColori, sizeof(colori)) != 0) disegnaSfondo(usate, colori);

  memcpy(composto->getBuffer(), sfondo->getBuffer(), 480 * 480 * 2);
  for (int i = 0; i < 3; i++) disegnaTag(*composto, i, s.tag[i], ora);
  disegnaDisco(*composto, s.sd);
  panel.pushColors(0, 0, 480, 480, composto->getBuffer());
}
