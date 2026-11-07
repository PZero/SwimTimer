// SwimTimer - XIAO nRF52840 Sense: streaming IMU via BLE, log, sospensione, DFU OTA (0.2.0)
// Core: Seeeduino:nrf52 (non mbed) con Bluefruit. Protocollo e uso: vedi LEGGIMI.md
#include <Arduino.h>
#include <Wire.h>
#include <bluefruit.h>
#include <stdarg.h>
#include "nrf_gpio.h"

#define VERSIONE "xiao-0.3.2"

// ---- Pin (numeri Arduino della variante Seeed, vedi variant.h) ----
// LED RGB attivi bassi: LED_RED/LED_GREEN/LED_BLUE (P0.26/P0.30/P0.06)
// IMU_PWR = P1.08 -> PIN_LSM6DS3TR_C_POWER (15); I2C interno su Wire1 (SDA P0.07, SCL P0.27)
// INT1 dell'IMU = P0.11 (pin assoluto 11); partitore batteria: VBAT_ENABLE (P0.14, LOW = abilitato), PIN_VBAT
// HICHG P0.13 (PIN_CHARGING_CURRENT): lasciato in ingresso = carica a 50 mA; ~CHG P0.17 = 23 (LOW in carica)
#define PIN_NCHG 23
#define PIN_INT1_ASSOLUTO 11

// ---- Parametri regolabili ----
#define TAP_SOGLIA 12          // soglia del doppio tap (0..31), 1 LSB = 62,5 mg a +-2 g: 12 = 0,75 g. Piu' basso = piu' sensibile
#define SOGLIA_BIAS_DPS 2.5f   // il giroscopio e' "fermo" se in 0,5 s ogni asse varia meno di cosi'
// Sospensione automatica: il tag dorme se resta "abbastanza fermo" per INATTIVITA_S secondi.
// Si valuta un blocco al secondo (media di 25 pacchetti, cosi' le vibrazioni del tavolo si annullano):
//  - rotazione media sotto QUIETE_GYRO_DPS (un tavolo ~0-1 dps; una testa a riposo ha spesso 3-20 dps)
//  - direzione della gravita' entro QUIETE_ANGOLO_GRADI da quella d'inizio quiete
//    (un tavolo non s'inclina; una testa, anche ferma, ondeggia di qualche grado in un minuto)
#define INATTIVITA_S 60        // 0 = mai
#define QUIETE_GYRO_DPS 3.0f
#define QUIETE_ANGOLO_GRADI 3.0f
#define LOG_RIGHE 50
#define LOG_LEN 44

// ---- LSM6DS3TR-C ----
#define IMU_ADDR 0x6A
#define REG_WHO_AM_I 0x0F
#define REG_CTRL1_XL 0x10
#define REG_CTRL2_G  0x11
#define REG_CTRL3_C  0x12
#define REG_CTRL6_C  0x15
#define REG_STATUS   0x1E
#define REG_OUTX_L_G 0x22   // 6 byte giroscopio poi 6 byte accelerometro
#define REG_TAP_SRC  0x1C
#define REG_ALL_INT_SRC 0x1A
#define REG_TAP_CFG  0x58
#define REG_TAP_THS_6D 0x59
#define REG_INT_DUR2 0x5A
#define REG_WAKE_UP_THS 0x5B
#define REG_MD1_CFG  0x5E

// ---- UUID ----
#define UUID_BASE(n) "7a1e" #n "-5b1d-4c8e-9f3a-1d2c3b4a5e60"
BLEService servizio(UUID_BASE(0001));
BLECharacteristic carDati(UUID_BASE(0002));
BLECharacteristic carStato(UUID_BASE(0003));
BLECharacteristic carComandi(UUID_BASE(0004));
BLECharacteristic carRisposte(UUID_BASE(0005));
BLECharacteristic carVersione(UUID_BASE(0007));
BLEDfu bledfu;   // servizio DFU Nordic legacy: la pagina lo usa per far entrare il tag nel bootloader OTA

// bit del byte flag di stato
#define FLAG_USB    0x01
#define FLAG_IMU_OK 0x02
#define FLAG_REG    0x04
#define FLAG_G16    0x10

static bool imuOk = false;
static uint8_t causaReset = 0;      // codici come la pagina: 0 accensione, 1 tap, 3 watchdog, 5 software, 6 altro, 7 USB, 8 pin reset
static uint16_t connHdl = BLE_CONN_HANDLE_INVALID;

// ---------------- Log circolare ----------------
static char logBuf[LOG_RIGHE][LOG_LEN];
static uint32_t logN = 0, logInvio = 0;   // righe scritte, prossima da inviare
static volatile bool risposteAttive = false;

static void logRiga(const char *fmt, ...) {
  char msg[LOG_LEN - 8];
  va_list ap; va_start(ap, fmt); vsnprintf(msg, sizeof(msg), fmt, ap); va_end(ap);
  uint32_t t = millis();
  snprintf(logBuf[logN % LOG_RIGHE], LOG_LEN, "%lu.%lu %s", (unsigned long)(t / 1000), (unsigned long)((t / 100) % 10), msg);
  if (Serial) Serial.println(logBuf[logN % LOG_RIGHE]);
  logN++;
}

// Invia al massimo una riga per chiamata (ritenta se la coda del BLE e' piena)
static void inviaLog() {
  if (connHdl == BLE_CONN_HANDLE_INVALID || !risposteAttive) return;
  if (logN - logInvio > LOG_RIGHE) logInvio = logN - LOG_RIGHE;
  if (logInvio >= logN) return;
  BLEConnection *c = Bluefruit.Connection(connHdl);
  if (!c) return;
  uint16_t massimo = c->getMtu() - 3;
  char out[LOG_LEN + 1];
  out[0] = 'G';
  strncpy(out + 1, logBuf[logInvio % LOG_RIGHE], LOG_LEN - 1);
  out[LOG_LEN] = 0;
  uint16_t n = strlen(out);
  if (n > massimo) n = massimo;
  if (carRisposte.notify(connHdl, out, n)) logInvio++;
}

// ---------------- I2C ----------------
static void i2cScrivi(uint8_t reg, uint8_t v) {
  Wire1.beginTransmission(IMU_ADDR); Wire1.write(reg); Wire1.write(v); Wire1.endTransmission();
}
static bool i2cLeggi(uint8_t reg, uint8_t *buf, uint8_t n) {
  Wire1.beginTransmission(IMU_ADDR); Wire1.write(reg);
  if (Wire1.endTransmission(true) != 0) return false;
  if (Wire1.requestFrom((uint8_t)IMU_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire1.read();
  return true;
}

static bool imuInit() {
  // uscita P1.08 con pilotaggio forte (senza, l'IMU non si accendeva in modo affidabile)
  NRF_P1->PIN_CNF[8] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos) | (GPIO_PIN_CNF_DRIVE_H0H1 << GPIO_PIN_CNF_DRIVE_Pos);
  digitalWrite(PIN_LSM6DS3TR_C_POWER, LOW);   // ciclo di alimentazione: parte da stato pulito
  delay(100);
  digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH);
  delay(50);
  pinMode(16, INPUT_PULLUP); pinMode(17, INPUT_PULLUP); delay(5);
  Wire1.begin();
  Wire1.setClock(400000);
  uint8_t id = 0;
  if (!i2cLeggi(REG_WHO_AM_I, &id, 1)) return false;
  if (id != 0x6A) { logRiga("IMU id errato 0x%02X", id); return false; }
  i2cScrivi(REG_CTRL3_C, 0x44);    // BDU + auto-incremento indirizzo
  i2cScrivi(REG_CTRL1_XL, 0x54);   // 208 Hz, +-16 g
  i2cScrivi(REG_CTRL2_G, 0x5C);    // 208 Hz, +-2000 dps
  return true;
}

// ---------------- Campionamento e media su 40 ms ----------------
static float sumA[3], sumG[3];
static uint16_t nCamp = 0;
static float bias[3];               // bias del giroscopio in LSB grezzi (70 mdps/LSB)
static bool biasNoto = false;
// finestra di 0,5 s per la stima continua del bias
static float wSum[3], wMin[3], wMax[3], wAcc;
static uint16_t wN = 0;
static int16_t acc[3], gir[3];      // ultimi valori inviati (acc a 2048 LSB/g, giro a 16,4 LSB/dps)
static float ultimoBiasLog[3];

static void finestraAzzera() {
  wN = 0; wAcc = 0;
  for (int i = 0; i < 3; i++) { wSum[i] = 0; wMin[i] = 1e9f; wMax[i] = -1e9f; }
}

// Chiude una finestra: se il tag e' fermo aggiorna il bias. Ritorna true se ha aggiornato.
static bool finestraChiudi() {
  bool agg = false;
  if (wN >= 40) {
    float m[3], intervallo = SOGLIA_BIAS_DPS / 0.070f;
    bool fermo = true;
    for (int i = 0; i < 3; i++) {
      m[i] = wSum[i] / wN;
      if (wMax[i] - wMin[i] > intervallo) fermo = false;
      if (biasNoto && fabsf(m[i] - bias[i]) > 4.0f / 0.070f) fermo = false;   // lontano dal bias noto: e' una rotazione vera
    }
    float an = wAcc / wN;   // |a| medio in g
    if (an < 0.9f || an > 1.1f) fermo = false;
    if (fermo) {
      for (int i = 0; i < 3; i++) bias[i] = biasNoto ? bias[i] + 0.5f * (m[i] - bias[i]) : m[i];
      biasNoto = true;
      agg = true;
    }
  }
  finestraAzzera();
  return agg;
}

// Legge un campione se pronto e lo accumula
static void imuPoll() {
  uint8_t st;
  if (!i2cLeggi(REG_STATUS, &st, 1) || (st & 0x03) != 0x03) return;
  uint8_t b[12];
  if (!i2cLeggi(REG_OUTX_L_G, b, 12)) return;
  float g[3], a[3];
  for (int i = 0; i < 3; i++) {
    g[i] = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
    a[i] = (int16_t)(b[6 + 2 * i] | (b[7 + 2 * i] << 8));
    sumG[i] += g[i]; sumA[i] += a[i];
    wSum[i] += g[i];
    if (g[i] < wMin[i]) wMin[i] = g[i];
    if (g[i] > wMax[i]) wMax[i] = g[i];
  }
  nCamp++;
  wAcc += sqrtf(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) / 2048.0f;
  if (++wN >= 104) {
    if (finestraChiudi()) {
      float d = 0;
      for (int i = 0; i < 3; i++) d = max(d, fabsf(bias[i] - ultimoBiasLog[i]) * 0.070f);
      if (d > 0.5f) {
        for (int i = 0; i < 3; i++) ultimoBiasLog[i] = bias[i];
        logRiga("bias gyro %.1f %.1f %.1f dps", bias[0] * 0.070f, bias[1] * 0.070f, bias[2] * 0.070f);
      }
    }
  }
}

// Calibrazione al boot: 1 s di campioni, valida solo se il tag e' fermo
static void calibraBoot() {
  finestraAzzera();
  uint32_t t0 = millis();
  while (millis() - t0 < 1100) { imuPoll(); delay(1); }
  if (wN >= 40 && finestraChiudi()) {
    for (int i = 0; i < 3; i++) ultimoBiasLog[i] = bias[i];
    logRiga("bias boot %.1f %.1f %.1f dps", bias[0] * 0.070f, bias[1] * 0.070f, bias[2] * 0.070f);
  } else {
    logRiga("bias boot: tag in moto, bias 0");
  }
  sumG[0] = sumG[1] = sumG[2] = sumA[0] = sumA[1] = sumA[2] = 0; nCamp = 0;
  finestraAzzera();
}

// Prepara il pacchetto da 16 byte con le medie dall'ultimo invio
static void preparaPacchetto(uint8_t *p, uint32_t ora) {
  if (nCamp > 0) {
    for (int i = 0; i < 3; i++) {
      float a = sumA[i] / nCamp;                       // +-16 g = 0,488 mg/LSB: gia' ~2048 LSB/g
      float g = (sumG[i] / nCamp - bias[i]) * 0.070f * 16.4f;   // 70 mdps/LSB -> 16,4 LSB/dps
      acc[i] = (int16_t)constrain(lroundf(a), -32768L, 32767L);
      gir[i] = (int16_t)constrain(lroundf(g), -32768L, 32767L);
      sumA[i] = sumG[i] = 0;
    }
    nCamp = 0;
  }
  memcpy(p, &ora, 4);
  memcpy(p + 4, acc, 6);
  memcpy(p + 10, gir, 6);
}

// ---------------- Batteria e stato ----------------
static uint16_t batteriaMv() {
  analogReference(AR_INTERNAL_3_0);
  analogReadResolution(12);
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(VBAT_ENABLE, LOW);  // abilita il partitore
  delay(2);
  uint32_t somma = 0;
  for (int i = 0; i < 8; i++) somma += analogRead(PIN_VBAT);
  pinMode(VBAT_ENABLE, INPUT);     // mai HIGH: lo rilascio in alta impedenza
  float mv = (somma / 8.0f) * 3000.0f / 4095.0f * 2.96f;   // partitore 1M/510k
  return mv < 2000 ? 0 : (uint16_t)mv;
}

static bool vbusPresente() {
  uint32_t r = 0;
  sd_power_usbregstatus_get(&r);
  return r & 1;   // VBUSDETECT
}

static void aggiornaStato(bool forzaLog) {
  static bool vbusPrec = false, caricaPrec = false;
  static uint32_t ultimoLogBat = 0;
  uint8_t s[8];
  uint16_t mv = batteriaMv();
  bool vbus = vbusPresente(), carica = digitalRead(PIN_NCHG) == LOW;
  uint8_t flag = FLAG_G16;
  if (imuOk) flag |= FLAG_IMU_OK;
  if (vbus || carica) flag |= FLAG_USB;
  uint32_t t = millis();
  s[0] = mv & 0xFF; s[1] = mv >> 8; s[2] = flag; s[3] = causaReset;
  memcpy(s + 4, &t, 4);
  carStato.write(s, 8);
  if (Bluefruit.connected()) carStato.notify(s, 8);
  if (forzaLog || vbus != vbusPrec || carica != caricaPrec || t - ultimoLogBat > 60000UL) {
    ultimoLogBat = t; vbusPrec = vbus; caricaPrec = carica;
    logRiga("bat %u mV usb %d carica %d", mv, vbus, carica);
  }
}

// ---------------- Sospensione (System OFF, risveglio con doppio tap o USB) ----------------
static void vaInSospensione() {
  logRiga("sospensione (2 tap/USB)");
  for (int i = 0; i < 150; i++) { inviaLog(); delay(2); }   // lascia partire le ultime righe
  Bluefruit.Advertising.restartOnDisconnect(false);
  Bluefruit.Advertising.stop();
  if (connHdl != BLE_CONN_HANDLE_INVALID) { Bluefruit.disconnect(connHdl); delay(300); }
  digitalWrite(LED_RED, HIGH); digitalWrite(LED_GREEN, HIGH); digitalWrite(LED_BLUE, HIGH);

  if (imuOk) {
    i2cScrivi(REG_CTRL2_G, 0x00);              // giroscopio spento
    i2cScrivi(REG_CTRL1_XL, 0x60);             // acc 416 Hz, +-2 g (minimo per il tap hardware)
    i2cScrivi(REG_CTRL6_C, 0x10);              // acc in modalita' a basso consumo
    i2cScrivi(REG_TAP_CFG, 0x8E);              // interrupt abilitati, tap su X/Y/Z
    i2cScrivi(REG_TAP_THS_6D, TAP_SOGLIA & 0x1F);
    i2cScrivi(REG_INT_DUR2, 0x7F);             // DUR 7 (max ~0,5 s fra i due tap), QUIET 3, SHOCK 3
    i2cScrivi(REG_WAKE_UP_THS, 0x80);          // SINGLE_DOUBLE_TAP = 1: doppio tap
    i2cScrivi(REG_MD1_CFG, 0x08);              // doppio tap su INT1
    delay(50);
    uint8_t x;
    i2cLeggi(REG_TAP_SRC, &x, 1); i2cLeggi(REG_ALL_INT_SRC, &x, 1);   // azzera eventuali tap pendenti
    uint32_t t0 = millis();
    while (digitalRead(PIN_INT1_ASSOLUTO) && millis() - t0 < 1000) { i2cLeggi(REG_TAP_SRC, &x, 1); delay(10); }
  }
  nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
  if (Serial) { Serial.flush(); delay(20); }
  sd_power_system_off();
  while (true) __WFE();
}

// ---------------- Comandi (caratteristica 0004) ----------------
static volatile bool cmdNuovo = false;
static char cmdTesto[24];

static void inComando(uint16_t, BLECharacteristic *, uint8_t *d, uint16_t len) {
  if (len >= sizeof(cmdTesto)) len = sizeof(cmdTesto) - 1;
  memcpy(cmdTesto, d, len);
  cmdTesto[len] = 0;
  cmdNuovo = true;
}

static void rispondi(char tipo, const char *testo) {
  char out[24]; out[0] = tipo;
  strncpy(out + 1, testo, sizeof(out) - 2); out[sizeof(out) - 1] = 0;
  if (connHdl != BLE_CONN_HANDLE_INVALID) carRisposte.notify(connHdl, out, strlen(out));
}

static void eseguiComando() {
  char c[24]; strcpy(c, cmdTesto); cmdNuovo = false;
  char *v = strchr(c, ','); if (v) *v = 0;   // il comando e' fino alla prima virgola
  if (!strcmp(c, "SLEEP")) vaInSospensione();
  else if (!strcmp(c, "LIST")) rispondi('Z', "");   // nessuna registrazione: fine elenco
  else { logRiga("comando non supportato: %s", c); rispondi('X', "non supportato"); }
}

static void inCccdRisposte(uint16_t, BLECharacteristic *, uint16_t valore) {
  if (valore & 1) { logInvio = logN > LOG_RIGHE ? logN - LOG_RIGHE : 0; risposteAttive = true; }   // rimanda il buffer
  else risposteAttive = false;
}

static void inConnessione(uint16_t h) {
  connHdl = h;
  digitalWrite(LED_BLUE, HIGH); digitalWrite(LED_GREEN, LOW);   // verde fisso
  logRiga("connesso");
}
static void inDisconnessione(uint16_t, uint8_t motivo) {
  connHdl = BLE_CONN_HANDLE_INVALID; risposteAttive = false;
  digitalWrite(LED_GREEN, HIGH);
  logRiga("disconnesso (0x%02X)", motivo);
}

void setup() {
  // Causa del reset dal registro RESETREAS (prima che il SoftDevice lo gestisca)
  uint32_t rr = NRF_POWER->RESETREAS;
  NRF_POWER->RESETREAS = rr;
  if (rr & POWER_RESETREAS_VBUS_Msk) causaReset = 7;
  else if (rr & POWER_RESETREAS_OFF_Msk) causaReset = 1;
  else if (rr & POWER_RESETREAS_DOG_Msk) causaReset = 3;
  else if (rr & POWER_RESETREAS_SREQ_Msk) causaReset = 5;
  else if (rr & POWER_RESETREAS_LOCKUP_Msk) causaReset = 6;
  else if (rr & POWER_RESETREAS_RESETPIN_Msk) causaReset = 8;
  else causaReset = 0;

  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 2000) delay(10);

  pinMode(LED_RED, OUTPUT); pinMode(LED_GREEN, OUTPUT); pinMode(LED_BLUE, OUTPUT);
  digitalWrite(LED_RED, HIGH); digitalWrite(LED_GREEN, HIGH); digitalWrite(LED_BLUE, HIGH);
  pinMode(PIN_NCHG, INPUT_PULLUP);
  pinMode(PIN_CHARGING_CURRENT, INPUT);   // P0.13 in ingresso: carica a 50 mA
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);

  const char *nomi[] = {"accensione", "doppio tap", "?", "watchdog", "?", "software", "lockup", "USB", "pin reset"};
  logRiga("boot %s, causa %s (RESETREAS 0x%lX)", VERSIONE, nomi[causaReset], (unsigned long)rr);

  Bluefruit.configPrphBandwidth(BANDWIDTH_HIGH);   // MTU grande: le righe di log arrivano intere
  Bluefruit.begin();
  Bluefruit.setTxPower(4);
  Bluefruit.setName("SwimTag");
  Bluefruit.Periph.setConnectCallback(inConnessione);
  Bluefruit.Periph.setDisconnectCallback(inDisconnessione);
  bledfu.begin();

  servizio.begin();
  carDati.setProperties(CHR_PROPS_NOTIFY);
  carDati.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carDati.setFixedLen(16);
  carDati.begin();
  carStato.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  carStato.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carStato.setFixedLen(8);
  carStato.begin();
  carComandi.setProperties(CHR_PROPS_WRITE | CHR_PROPS_WRITE_WO_RESP);
  carComandi.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
  carComandi.setMaxLen(24);
  carComandi.setWriteCallback(inComando);
  carComandi.begin();
  carRisposte.setProperties(CHR_PROPS_NOTIFY);
  carRisposte.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carRisposte.setMaxLen(100);
  carRisposte.setCccdWriteCallback(inCccdRisposte);
  carRisposte.begin();
  carVersione.setProperties(CHR_PROPS_READ);
  carVersione.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carVersione.setMaxLen(20);
  carVersione.begin();
  carVersione.write(VERSIONE);

  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addService(servizio);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(160, 160);   // 100 ms
  Bluefruit.Advertising.start(0);

  imuOk = imuInit();   // dopo il BLE: se l'IMU non risponde il tag resta comunque visibile
  logRiga(imuOk ? "IMU ok" : "IMU NON risponde");
  if (imuOk) calibraBoot();
  aggiornaStato(true);
}

// Sospensione automatica: chiamata a ogni pacchetto (25 Hz). Ogni secondo valuta un blocco:
// fermo = rotazione media bassa E gravita' nella stessa direzione d'inizio quiete.
// Dopo INATTIVITA_S blocchi fermi di fila va in sospensione (doppio tap o USB per riattivare).
// Ogni 10 s scrive nel log i valori misurati, utili per tarare le soglie.
static void controllaInattivita(uint32_t ora) {
  static float sa[3], sg; static int n = 0;
  static float rif[3]; static bool rifOk = false;
  static int secFermo = 0; static float gMax = 0, angMax = 0;
  (void)ora;
  if (INATTIVITA_S == 0) return;
  float g2 = 0;
  for (int i = 0; i < 3; i++) { sa[i] += acc[i] / 2048.0f; float w = gir[i] / 16.4f; g2 += w * w; }
  sg += sqrtf(g2);
  if (++n < 25) return;                                  // blocco di 1 s
  float a[3], an = 0, gMed = sg / n;
  for (int i = 0; i < 3; i++) { a[i] = sa[i] / n; an += a[i] * a[i]; sa[i] = 0; }
  sg = 0; n = 0;
  an = sqrtf(an);
  if (an < 0.5f) return;                                 // caduta libera / dato anomalo: ignora
  for (int i = 0; i < 3; i++) a[i] /= an;
  float ang = 0;
  if (rifOk) {
    float d = a[0] * rif[0] + a[1] * rif[1] + a[2] * rif[2];
    ang = acosf(constrain(d, -1.0f, 1.0f)) * 57.2958f;
  }
  if (rifOk && gMed < QUIETE_GYRO_DPS && ang < QUIETE_ANGOLO_GRADI) {
    secFermo++;
    gMax = max(gMax, gMed); angMax = max(angMax, ang);
  } else {                                               // movimento: nuova quiete da qui
    if (secFermo >= 10) logRiga("moto dopo %ds rot%.1f ang%.1f", secFermo, gMed, ang);
    for (int i = 0; i < 3; i++) rif[i] = a[i];
    rifOk = true; secFermo = 0; gMax = 0; angMax = 0;
  }
  if (secFermo > 0 && secFermo % 10 == 0)
    logRiga("quiete %ds rot%.1f ang%.1f", secFermo, gMax, angMax);
  if (secFermo >= INATTIVITA_S) {
    logRiga("fermo da %d s: sospensione", INATTIVITA_S);
    vaInSospensione();
  }
}

void loop() {
  static uint32_t ultimoDati = 0, ultimoStato = 0, ultimoLed = 0;
  uint32_t ora = millis();

  if (imuOk) imuPoll();
  if (ora - ultimoDati >= 40) {            // 25 Hz
    ultimoDati += 40;
    if (ora - ultimoDati > 200) ultimoDati = ora;
    if (imuOk) {
      uint8_t p[16];
      preparaPacchetto(p, ora);
      if (Bluefruit.connected()) carDati.notify(p, 16);
      controllaInattivita(ora);
    }
  }
  if (ora - ultimoStato >= 1000) {         // 1 Hz
    ultimoStato = ora;
    if (!imuOk) {                          // riprova l'init e lo segnala
      imuOk = imuInit();
      logRiga(imuOk ? "IMU ok (ripristinato)" : "IMU NON risponde");
    } else if (Serial) {
      Serial.printf("acc %d %d %d | gyro %d %d %d\n", acc[0], acc[1], acc[2], gir[0], gir[1], gir[2]);
    }
    aggiornaStato(false);
  }
  if (cmdNuovo) eseguiComando();
  inviaLog();
  if (!Bluefruit.connected() && ora - ultimoLed >= 500) {   // blu lampeggiante = advertising
    ultimoLed = ora;
    digitalToggle(LED_BLUE);
  }
  delay(1);
}
