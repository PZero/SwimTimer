// SwimTimer - XIAO nRF52840 Sense: streaming IMU via BLE, log, sospensione, OTA via BLE (0.4.0)
// Core: Seeeduino:nrf52 (non mbed) con Bluefruit. Protocollo e uso: vedi LEGGIMI.md
#include <Arduino.h>
#include <Wire.h>
#include <bluefruit.h>
#include <stdarg.h>
#include "nrf_gpio.h"
#include <InternalFileSystem.h>
#include <flash/flash_nrf5x.h>   // scrittura flash compatibile con il SoftDevice (sd_flash_*)

#define VER_NUM "0.4.2"
#define VERSIONE "xiao-" VER_NUM
// Marcatore cercato nel binario dalla pagina (come per l'ESP32) e dall'OTA del tag
__attribute__((used)) static const char marcatoreVersione[] = "SWIMTAG_VER=" VER_NUM ";";
// Firma della scheda: l'OTA rifiuta le immagini che non la contengono (es. il firmware dell'ESP32)
#define FIRMA_SCHEDA "SWIMTAG_BOARD=xiao-nrf52840;"
__attribute__((used)) static const char marcatoreScheda[] = FIRMA_SCHEDA;

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
// Risveglio con 4 tocchi: il primo doppio tap sveglia il chip, che aspetta un SECONDO doppio tap per
// RISVEGLIO_FINESTRA_MS; se non arriva torna subito in System OFF (senza BLE, USB ne' log).
#define RISVEGLIO_FINESTRA_MS 2000
#define RISVEGLIO_PAUSA_MS 150   // dopo l'accensione dell'IMU si ignorano i residui del primo gesto
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
BLECharacteristic carOta(UUID_BASE(0006));
BLECharacteristic carVersione(UUID_BASE(0007));
BLEDfu bledfu;   // servizio DFU Nordic legacy: la pagina lo usa per far entrare il tag nel bootloader OTA

// bit del byte flag di stato
#define FLAG_USB    0x01
#define FLAG_IMU_OK 0x02
#define FLAG_REG    0x04
#define FLAG_G16    0x10

static volatile bool otaAttivo = false;      // aggiornamento OTA in corso: niente sospensione, ne' per quiete, ne' per batteria bassa, ne' da comando
static volatile uint32_t ultimoComando = 0;   // millis dell'ultimo comando ricevuto via BLE
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
static void vaInSospensione(bool soloUsb = false);
#define VCAL_FILE "/vcal.bin"
static float vcalFattore = 2.96f;   // rapporto del partitore 1M/510k (nominale); si taratura col comando VCAL,<mV letti col tester>

static void vcalCarica() {
  InternalFS.begin();
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  uint32_t v = 0;
  if (f.open(VCAL_FILE, Adafruit_LittleFS_Namespace::FILE_O_READ)) { f.read((uint8_t *)&v, 4); f.close(); }
  if (v >= 2000 && v <= 4000) vcalFattore = v / 1000.0f;
}
static void vcalSalva(float fattore) {
  uint32_t v = (uint32_t)lroundf(fattore * 1000.0f);
  InternalFS.remove(VCAL_FILE);
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  if (f.open(VCAL_FILE, Adafruit_LittleFS_Namespace::FILE_O_WRITE)) { f.write((uint8_t *)&v, 4); f.close(); }
}

// Tensione sul pin in mV (prima del partitore): 24 letture a 1 ms, media delle 16 centrali (scarta i picchi dovuti
// alle trasmissioni radio, che abbassano un attimo la tensione)
static float batteriaPinMv() {
  analogReference(AR_INTERNAL_3_0);
  analogReadResolution(12);
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(VBAT_ENABLE, LOW);  // abilita il partitore
  delay(3);
  uint16_t r[24];
  for (int i = 0; i < 24; i++) { r[i] = analogRead(PIN_VBAT); delay(1); }
  pinMode(VBAT_ENABLE, INPUT);     // mai HIGH: lo rilascio in alta impedenza
  for (int i = 1; i < 24; i++) { uint16_t x = r[i]; int j = i - 1; while (j >= 0 && r[j] > x) { r[j + 1] = r[j]; j--; } r[j + 1] = x; }
  uint32_t somma = 0;
  for (int i = 4; i < 20; i++) somma += r[i];
  return (somma / 16.0f) * 3000.0f / 4095.0f;
}
static uint16_t batteriaMv() {
  float mv = batteriaPinMv() * vcalFattore;
  return mv < 2000 ? 0 : (uint16_t)mv;
}

static bool vbusPresente() {
  uint32_t r = 0;
  sd_power_usbregstatus_get(&r);
  return r & 1;   // VBUSDETECT
}

// STATO (12 byte, compatibile con il formato a 8 byte): mV, flag, causa, millis, poi
//  [8] flag2: bit0 VBUS presente, bit1 carica completata, bit2 in carica, bit3 batteria bassa (< 3,4 V)
//  [9] temperatura del die in gradi (int8), [10-11] fattore del partitore x1000
static void aggiornaStato(bool forzaLog) {
  static bool vbusPrec = false, caricaPrec = false, bassaLog = false;
  static uint32_t ultimoLogBat = 0;
  static uint8_t contaSotto = 0;
  uint8_t s[12];
  uint16_t mv = batteriaMv();
  bool vbus = vbusPresente(), carica = digitalRead(PIN_NCHG) == LOW;
  bool cella = mv > 0;
  bool completata = vbus && !carica && cella;
  bool bassa = cella && !vbus && mv < 3400;
  uint8_t flag = FLAG_G16;
  if (imuOk) flag |= FLAG_IMU_OK;
  if (vbus || carica) flag |= FLAG_USB;
  uint32_t t = millis();
  int32_t temp = 0;
  sd_temp_get(&temp);
  s[0] = mv & 0xFF; s[1] = mv >> 8; s[2] = flag; s[3] = causaReset;
  memcpy(s + 4, &t, 4);
  s[8] = (vbus ? 1 : 0) | (completata ? 2 : 0) | (carica ? 4 : 0) | (bassa ? 8 : 0);
  s[9] = (int8_t)(temp / 4);
  uint16_t k = (uint16_t)lroundf(vcalFattore * 1000.0f);
  s[10] = k & 0xFF; s[11] = k >> 8;
  carStato.write(s, 12);
  if (Bluefruit.connected()) carStato.notify(s, 12);
  if (forzaLog || vbus != vbusPrec || carica != caricaPrec || t - ultimoLogBat > 60000UL) {
    ultimoLogBat = t; vbusPrec = vbus; caricaPrec = carica;
    logRiga("bat %u mV usb %d carica %d", mv, vbus, carica);
  }
  // Batteria bassa: avviso sotto 3,4 V, sospensione sotto 3,3 V (5 letture di fila) solo a batteria, mai con la USB
  if (cella && !vbus) {
    if (mv < 3400 && !bassaLog) { bassaLog = true; logRiga("batteria bassa %u mV", mv); }
    if (mv > 3500) bassaLog = false;
    if (mv < 3300) {
      if (++contaSotto >= 5) { logRiga("bat < 3,3 V: sospensione"); vaInSospensione(true); }
    } else contaSotto = 0;
  } else contaSotto = 0;
}

// ---------------- Sospensione (System OFF, risveglio con 4 tap o USB) ----------------
// IMU: giroscopio spento, accelerometro a basso consumo con rilevazione hardware del doppio tap su INT1
static void configuraTap() {
  i2cScrivi(REG_CTRL2_G, 0x00);              // giroscopio spento
  i2cScrivi(REG_CTRL1_XL, 0x60);             // acc 416 Hz, +-2 g (minimo per il tap hardware)
  i2cScrivi(REG_CTRL6_C, 0x10);              // acc in modalita' a basso consumo
  i2cScrivi(REG_TAP_CFG, 0x8F);              // interrupt abilitati, tap su X/Y/Z, LIR = latch (INT1 resta alto finche' si legge TAP_SRC)
  i2cScrivi(REG_TAP_THS_6D, TAP_SOGLIA & 0x1F);
  i2cScrivi(REG_INT_DUR2, 0x7F);             // DUR 7 (max ~0,5 s fra i due tap), QUIET 3, SHOCK 3
  i2cScrivi(REG_WAKE_UP_THS, 0x80);          // SINGLE_DOUBLE_TAP = 1: doppio tap
  i2cScrivi(REG_MD1_CFG, 0x08);              // doppio tap su INT1
}
// Legge TAP_SRC (azzera il latch) e attende che INT1 torni bassa. Ritorna il valore letto di TAP_SRC.
static uint8_t attendiInt1Bassa(uint32_t ms) {
  uint8_t x = 0, src = 0;
  i2cLeggi(REG_ALL_INT_SRC, &x, 1);
  uint32_t t0 = millis();
  do { i2cLeggi(REG_TAP_SRC, &src, 1); } while (digitalRead(PIN_INT1_ASSOLUTO) && millis() - t0 < ms && (delay(5), true));
  return src;
}
static void vaInSospensione(bool soloUsb) {
  if (otaAttivo) { logRiga("sospensione rinviata: OTA"); return; }
  logRiga(soloUsb ? "sospensione (solo USB)" : "sospensione (4 tap/USB)");
  for (int i = 0; i < 150; i++) { inviaLog(); delay(2); }   // lascia partire le ultime righe
  Bluefruit.Advertising.restartOnDisconnect(false);
  Bluefruit.Advertising.stop();
  if (connHdl != BLE_CONN_HANDLE_INVALID) { Bluefruit.disconnect(connHdl); delay(300); }
  digitalWrite(LED_RED, HIGH); digitalWrite(LED_GREEN, HIGH); digitalWrite(LED_BLUE, HIGH);

  if (soloUsb) {
    digitalWrite(PIN_LSM6DS3TR_C_POWER, LOW);   // batteria quasi scarica: IMU spento, si riparte solo con l'USB
  } else {
    if (imuOk) {
      configuraTap();
      delay(50);
      attendiInt1Bassa(1000);
    }
    nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
  }
  if (Serial) { Serial.flush(); delay(20); }
  sd_power_system_off();
  while (true) __WFE();
}

// Risveglio dal doppio tap: chiamata a inizio setup(), prima di USB e BLE. Ritorna true se arriva il secondo doppio tap.
// All'uscita da System OFF i pin tornano al default: l'IMU perde l'alimentazione (P1.08) e quindi la configurazione,
// perche' il reset dura piu' dei suoi tempi di spegnimento. Si riaccende, si riconfigura il tap e si ascolta.
static bool risveglioQuattroTap() {
  NRF_P1->PIN_CNF[8] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos) | (GPIO_PIN_CNF_DRIVE_H0H1 << GPIO_PIN_CNF_DRIVE_Pos);
  NRF_P1->OUTSET = 1UL << 8;
  pinMode(16, INPUT_PULLUP); pinMode(17, INPUT_PULLUP);
  pinMode(PIN_INT1_ASSOLUTO, INPUT);
  delay(40);
  Wire1.begin();
  Wire1.setClock(400000);
  uint8_t id = 0;
  bool secondo = false;
  if (!i2cLeggi(REG_WHO_AM_I, &id, 1) || id != 0x6A) return true;   // IMU muto: avvio normale
  configuraTap();
  delay(RISVEGLIO_PAUSA_MS);
  attendiInt1Bassa(100);                                            // azzera il latch del primo gesto
  uint32_t t0 = millis();
  while (millis() - t0 < RISVEGLIO_FINESTRA_MS) {
    if (digitalRead(PIN_INT1_ASSOLUTO)) {
      uint8_t src = 0;
      i2cLeggi(REG_TAP_SRC, &src, 1);
      if (src & 0x10) { secondo = true; break; }                    // DOUBLE_TAP
    }
    delay(5);
  }
  if (secondo) return true;
  // falso risveglio: di nuovo System OFF con la stessa configurazione
  attendiInt1Bassa(300);
  nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
  NRF_POWER->SYSTEMOFF = POWER_SYSTEMOFF_SYSTEMOFF_Enter;
  while (true) __WFE();
}

// ---------------- Comandi (caratteristica 0004) ----------------
// Coda di 4 comandi: la callback BLE copia il testo, li esegue il loop.
#define CMD_LEN 64
static char cmdCoda[4][CMD_LEN];
static volatile uint8_t cmdTesta = 0, cmdCodaI = 0;

static void inComando(uint16_t, BLECharacteristic *, uint8_t *d, uint16_t len) {
  ultimoComando = millis();
  if ((uint8_t)(cmdTesta - cmdCodaI) >= 4) return;   // coda piena
  if (len >= CMD_LEN) len = CMD_LEN - 1;
  char *dst = cmdCoda[cmdTesta & 3];
  memcpy(dst, d, len);
  dst[len] = 0;
  cmdTesta = cmdTesta + 1;
}

static void rispondi(char tipo, const char *testo) {
  char out[48]; out[0] = tipo;
  strncpy(out + 1, testo, sizeof(out) - 2); out[sizeof(out) - 1] = 0;
  if (connHdl != BLE_CONN_HANDLE_INVALID) carRisposte.notify(connHdl, out, strlen(out));
}

// ---------------- Controllo del bootloader (solo log, utile a validare l'OTA) ----------------
#define APP_BASE      0x27000UL                 // inizio dell'app dopo il SoftDevice S140 v7 (linker del core)
#define STAGING_BASE  0x80000UL                 // zona di appoggio dell'immagine ricevuta (dentro la regione app, dopo l'app attuale)
#define APP_MAX_BYTE  (STAGING_BASE - APP_BASE) // 0x59000 = 356 KB: massimo di una nuova app (e fine massima dell'app attuale)
#define BL_SETTINGS   0xFF000UL                 // pagina delle impostazioni dell'Adafruit nRF52 Bootloader

extern "C" uint32_t __etext, __data_start__, __data_end__;

static uint16_t crc16Ccitt(const uint8_t *p, uint32_t n) {   // stessa funzione del bootloader (crc16_compute, init 0xFFFF)
  uint16_t crc = 0xFFFF;
  while (n--) {
    uint8_t x = (crc >> 8) ^ *p++;
    x ^= x >> 4;
    crc = (crc << 8) ^ ((uint16_t)(x << 12)) ^ ((uint16_t)(x << 5)) ^ (uint16_t)x;
  }
  return crc;
}

static void controllaBootloader() {
  const uint32_t *w = (const uint32_t *)BL_SETTINGS;
  uint16_t bank0 = w[0] & 0xFFFF, crcSalvato = w[0] >> 16;
  uint32_t dim = w[2];
  uint32_t fineApp = (uint32_t)&__etext + ((uint32_t)&__data_end__ - (uint32_t)&__data_start__);
  if (bank0 == 1 && dim <= APP_MAX_BYTE) {
    uint16_t c = crc16Ccitt((const uint8_t *)APP_BASE, dim);
    logRiga("bl bank0 ok crc %04X %s dim %lu", crcSalvato, (crcSalvato == 0 || c == crcSalvato) ? "=" : "!=", (unsigned long)dim);
  } else {
    logRiga("bl bank0 0x%X dim %lu", bank0, (unsigned long)dim);
  }
  logRiga("app fine 0x%lX staging 0x%lX", (unsigned long)fineApp, STAGING_BASE);
}

// ---------------- OTA via BLE (caratteristica 0006, stesso protocollo dell'ESP32) ----------------
// Comandi (0004): OTA,<byte>,<crc32 hex>,<versione>[,forza] · OTAEND · OTAABORT. Scritture sulla 0006 = uint32 offset LE + dati.
// Flusso: l'immagine (.bin dell'app, che parte da APP_BASE) viene scritta in STAGING_BASE con l'API flash del SoftDevice;
// a OTAEND si controllano lunghezza, CRC32 e marcatore di versione, poi si copia sull'app da una routine in RAM
// con SoftDevice e interrupt spenti, aggiornando le impostazioni del bootloader (bank_0, CRC16, dimensione).
#define OTA_ANELLO 8192
static uint8_t otaAnello[OTA_ANELLO];
static volatile uint32_t otaTesta = 0, otaCoda = 0;
static uint32_t otaTotale = 0, otaCrcAtteso = 0, otaScritti = 0, otaUltimoPct = 0;
static volatile uint32_t otaAccettati = 0, otaCrc = 0xFFFFFFFFu;
static uint32_t otaTabella[256];
static char otaVer[16];
static volatile char otaMsgTipo = 0;
static char otaMsgTesto[40];
static volatile uint32_t otaInstallaAlle = 0;   // millis a cui avviare l'installazione (0 = nessuna)

static void otaMessaggio(char tipo, const char *testo) {
  if (otaMsgTipo) return;
  strlcpy(otaMsgTesto, testo, sizeof(otaMsgTesto));
  otaMsgTipo = tipo;
}

static void inOta(uint16_t, BLECharacteristic *, uint8_t *d, uint16_t len) {
  if (!otaAttivo || otaInstallaAlle || len < 5) return;
  uint32_t off; memcpy(&off, d, 4);
  uint16_t n = len - 4;
  char msg[40];
  if (off != otaAccettati) { snprintf(msg, sizeof(msg), "ota offset,%lu", (unsigned long)otaAccettati); otaMessaggio('X', msg); return; }
  if ((uint64_t)otaAccettati + n > otaTotale) { otaMessaggio('X', "ota dati oltre la dimensione"); return; }
  for (int i = 0; i < 100 && OTA_ANELLO - (otaTesta - otaCoda) < n; i++) delay(5);   // il loop svuota l'anello in flash
  if (OTA_ANELLO - (otaTesta - otaCoda) < n) { snprintf(msg, sizeof(msg), "ota offset,%lu", (unsigned long)otaAccettati); otaMessaggio('X', msg); return; }
  uint32_t t = otaTesta;
  uint32_t c = otaCrc;
  for (uint16_t i = 0; i < n; i++) {
    uint8_t b = d[4 + i];
    otaAnello[(t + i) & (OTA_ANELLO - 1)] = b;
    c = otaTabella[(c ^ b) & 0xFF] ^ (c >> 8);
  }
  otaCrc = c;
  otaAccettati += n;
  otaTesta = t + n;
}

static void otaAnnulla() {
  otaAttivo = false; otaInstallaAlle = 0;
  otaCoda = otaTesta = 0; otaMsgTipo = 0;
}

static bool otaSvuota() {
  while (otaCoda != otaTesta) {
    uint32_t c = otaCoda, disp = otaTesta - c;
    size_t pos = c & (OTA_ANELLO - 1);
    size_t n = min((size_t)disp, (size_t)(OTA_ANELLO - pos));
    if (flash_nrf5x_write(STAGING_BASE + otaScritti, otaAnello + pos, n) != (int)n) return false;
    otaScritti += n;
    otaCoda = c + n;
  }
  return true;
}

// Confronto di versioni "a.b.c": -1 se a<b, 0 uguali, 1 se a>b, -2 se a non e' numerica
static int confrontaVer(const char *a, const char *b) {
  if (!a || !*a) return -2;
  for (const char *p = a; *p; p++) if (!isdigit((unsigned char)*p) && *p != '.') return -2;
  long va[4] = {0, 0, 0, 0}, vb[4] = {0, 0, 0, 0};
  const char *pa = a, *pb = b;
  for (int i = 0; i < 4; i++) {
    if (*pa) { va[i] = strtol(pa, (char **)&pa, 10); if (*pa == '.') pa++; }
    if (*pb) { vb[i] = strtol(pb, (char **)&pb, 10); if (*pb == '.') pb++; }
  }
  for (int i = 0; i < 4; i++) if (va[i] != vb[i]) return va[i] < vb[i] ? -1 : 1;
  return 0;
}

static void otaAvvia(char *arg) {
  if (otaAttivo) { rispondi('X', "ota gia in corso"); return; }
  char *p = arg;
  char *campi[4] = {0, 0, 0, 0};
  for (int i = 0; i < 4 && p; i++) { campi[i] = p; p = strchr(p, ','); if (p) *p++ = 0; }
  if (!campi[0] || !campi[1] || !campi[2]) { rispondi('X', "ota argomenti"); return; }
  uint32_t dim = strtoul(campi[0], nullptr, 10);
  uint32_t crc = strtoul(campi[1], nullptr, 16);
  bool forza = campi[3] && !strcasecmp(campi[3], "forza");
  int cmp = confrontaVer(campi[2], VER_NUM);
  if (cmp == -2) { rispondi('X', "ota versione mancante"); return; }
  if (cmp == 0) { rispondi('X', "ota stessa versione"); return; }
  if (cmp < 0 && !forza) { rispondi('X', "ota versione precedente"); return; }
  uint32_t fineApp = (uint32_t)&__etext + ((uint32_t)&__data_end__ - (uint32_t)&__data_start__);
  if (fineApp > STAGING_BASE) { rispondi('X', "ota app attuale troppo grande"); return; }
  if (dim < 1024 || dim > APP_MAX_BYTE) { rispondi('X', "ota dimensione non valida"); return; }
  strlcpy(otaVer, campi[2], sizeof(otaVer));
  for (uint32_t i = 0; i < 256; i++) {
    uint32_t c = i;
    for (int k = 0; k < 8; k++) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
    otaTabella[i] = c;
  }
  otaTotale = dim; otaCrcAtteso = crc;
  otaAccettati = otaScritti = otaUltimoPct = 0; otaCrc = 0xFFFFFFFFu;
  otaCoda = otaTesta = 0; otaMsgTipo = 0; otaInstallaAlle = 0;
  otaAttivo = true;
  BLEConnection *c = connHdl != BLE_CONN_HANDLE_INVALID ? Bluefruit.Connection(connHdl) : nullptr;
  uint16_t mtu = c ? c->getMtu() : 23;
  uint16_t massimo = mtu > 7 ? min((uint16_t)240, (uint16_t)(mtu - 7)) : 16;
  char r[24]; snprintf(r, sizeof(r), "ota pronto,%u", massimo);
  rispondi('K', r);
  logRiga("ota: %lu byte, v%s, blocchi %u", (unsigned long)dim, otaVer, massimo);
}

// Cerca nella flash di staging la stringa "SWIMTAG_VER=<versione>;"
static bool otaMarcatorePresente(const char *ago) {
  size_t k = strlen(ago);
  const uint8_t *m = (const uint8_t *)STAGING_BASE;
  for (uint32_t i = 0; i + k <= otaTotale; i++)
    if (m[i] == (uint8_t)ago[0] && !memcmp(m + i, ago, k)) return true;
  return false;
}

// Variabili per la routine in RAM
static uint32_t instWords = 0;
static uint32_t instSett[7];

// Copia lo staging sull'app, verifica e aggiorna le impostazioni del bootloader. Gira interamente in RAM:
// SoftDevice e interrupt spenti, nessuna chiamata a funzioni in flash. Finisce con il reset.
__attribute__((section(".data.ramfunc"), noinline, used, optimize("O1")))
void ramInstalla(uint32_t src, uint32_t dst, uint32_t words, uint32_t *sett) {
  NRF_NVMC_Type *nv = NRF_NVMC;
  nv->ICACHECNF = 0;                                          // cache istruzioni spenta
  // 1. cancella le pagine dell'app
  nv->CONFIG = NVMC_CONFIG_WEN_Een;
  for (uint32_t a = dst; a < dst + words * 4; a += 4096) {
    nv->ERASEPAGE = a;
    while (!nv->READY) {}
  }
  // 2. copia
  nv->CONFIG = NVMC_CONFIG_WEN_Wen;
  for (uint32_t i = 0; i < words; i++) {
    *(volatile uint32_t *)(dst + i * 4) = *(volatile uint32_t *)(src + i * 4);
    while (!nv->READY) {}
  }
  nv->CONFIG = NVMC_CONFIG_WEN_Ren;
  // 3. verifica; se non torna si lascia il bootloader in DFU (impostazioni vecchie = CRC non corrispondente)
  bool ok = true;
  for (uint32_t i = 0; i < words; i++)
    if (*(volatile uint32_t *)(dst + i * 4) != *(volatile uint32_t *)(src + i * 4)) { ok = false; break; }
  if (ok) {
    nv->CONFIG = NVMC_CONFIG_WEN_Een;
    nv->ERASEPAGE = BL_SETTINGS;
    while (!nv->READY) {}
    nv->CONFIG = NVMC_CONFIG_WEN_Wen;
    for (uint32_t i = 0; i < 7; i++) {
      *(volatile uint32_t *)(BL_SETTINGS + i * 4) = sett[i];
      while (!nv->READY) {}
    }
    nv->CONFIG = NVMC_CONFIG_WEN_Ren;
  }
  SCB->AIRCR = (0x5FAUL << SCB_AIRCR_VECTKEY_Pos) | SCB_AIRCR_SYSRESETREQ_Msk;   // reset di sistema
  while (true) {}
}

static void otaInstalla() {
  logRiga("ota: installazione");
  for (int i = 0; i < 100; i++) { inviaLog(); delay(2); }
  Bluefruit.Advertising.restartOnDisconnect(false);
  Bluefruit.Advertising.stop();
  if (connHdl != BLE_CONN_HANDLE_INVALID) { Bluefruit.disconnect(connHdl); delay(300); }
  if (Serial) { Serial.flush(); delay(20); }
  uint32_t words = (otaTotale + 3) / 4;
  // impostazioni del bootloader come le scrive lui a fine DFU di un'app (bootloader_dfu_update_process)
  // bank_0_crc = 0: "CRC non usato". E' il valore che il bootloader di questa scheda ha scritto da solo dopo il DFU via USB
  // (verificato leggendo la pagina delle impostazioni: bank_0 = 1, crc = 0), quindi l'app parte senza controllo CRC16.
  instSett[0] = 0x0001u;                                       // bank_0 = BANK_VALID_APP, bank_0_crc = 0
  instSett[1] = 0x00FFu | 0xFFFF0000u;                         // bank_1 = BANK_INVALID_APP (+ padding)
  instSett[2] = words * 4;                                     // bank_0_size
  instSett[3] = instSett[4] = instSett[5] = instSett[6] = 0;   // sd/bl/app size e sd_image_start
  sd_softdevice_disable();
  for (int i = 0; i < 2; i++) { NVIC->ICER[i] = 0xFFFFFFFF; NVIC->ICPR[i] = 0xFFFFFFFF; }
  __disable_irq();
  ramInstalla(STAGING_BASE, APP_BASE, words, instSett);
}

static void otaFine() {
  if (!otaAttivo) { rispondi('X', "ota non avviata"); return; }
  if (!otaSvuota()) { otaAnnulla(); rispondi('X', "ota scrittura fallita"); logRiga("ota: errore scrittura flash"); return; }
  uint32_t pad = (4 - (otaTotale & 3)) & 3;
  if (pad) { uint8_t ff[3] = {0xFF, 0xFF, 0xFF}; flash_nrf5x_write(STAGING_BASE + otaTotale, ff, pad); }
  flash_nrf5x_flush();
  uint32_t crc = ~otaCrc;
  if (otaScritti != otaTotale) { char m[40]; snprintf(m, sizeof(m), "ota incompleta,%lu", (unsigned long)otaScritti); otaAnnulla(); rispondi('X', m); logRiga("ota: incompleta %lu", (unsigned long)otaScritti); return; }
  if (crc != otaCrcAtteso) { otaAnnulla(); rispondi('X', "ota crc errato"); logRiga("ota: crc errato %08lX", (unsigned long)crc); return; }
  uint32_t sp = *(const uint32_t *)STAGING_BASE, rst = *(const uint32_t *)(STAGING_BASE + 4);
  if (sp < 0x20000000UL || sp > 0x20040000UL || !(rst & 1) || rst < APP_BASE || rst >= APP_BASE + otaTotale) {
    otaAnnulla(); rispondi('X', "ota immagine non valida"); logRiga("ota: vettori non validi"); return;
  }
  char marcaVer[40];
  snprintf(marcaVer, sizeof(marcaVer), "SWIMTAG_VER=%s;", otaVer);
  if (!otaMarcatorePresente(FIRMA_SCHEDA)) { otaAnnulla(); rispondi('X', "ota non e' un firmware xiao"); logRiga("ota: firma scheda assente"); return; }
  if (!otaMarcatorePresente(marcaVer)) { otaAnnulla(); rispondi('X', "ota versione non coincide"); logRiga("ota: marcatore versione assente"); return; }
  logRiga("ota: crc ok, v%s", otaVer);
  rispondi('K', "ota ok");
  otaInstallaAlle = millis() + 800;   // lascia partire la risposta, poi installa
  if (!otaInstallaAlle) otaInstallaAlle = 1;
}

// VCAL,<mV letti col tester>: tara il partitore sulla tensione vera (salvata in flash). VCAL senza argomento: mostra il fattore; VCAL,0: ripristina 2,96
static void comandoVcal(const char *arg) {
  char r[24];
  long mv = arg ? atol(arg) : -1;
  if (mv < 0) { snprintf(r, sizeof(r), "vcal %.3f", vcalFattore); rispondi('K', r); return; }
  if (mv == 0) { vcalFattore = 2.96f; InternalFS.remove(VCAL_FILE); }
  else {
    if (mv < 2500 || mv > 4500) { rispondi('X', "vcal fuori campo"); return; }
    float pin = batteriaPinMv();
    if (pin < 100) { rispondi('X', "vcal batteria assente"); return; }
    float f = mv / pin;
    if (f < 2.0f || f > 4.0f) { rispondi('X', "vcal fattore anomalo"); return; }
    vcalFattore = f;
    vcalSalva(f);
  }
  logRiga("vcal %.3f", vcalFattore);
  snprintf(r, sizeof(r), "vcal %.3f", vcalFattore);
  rispondi('K', r);
  aggiornaStato(false);
}

static void eseguiComandi() {
  while (cmdTesta != cmdCodaI) {
    char c[CMD_LEN]; strcpy(c, cmdCoda[cmdCodaI & 3]); cmdCodaI = cmdCodaI + 1;
    char *arg = strchr(c, ','); if (arg) *arg++ = 0;   // il comando e' fino alla prima virgola
    if (!strcmp(c, "SLEEP")) vaInSospensione();
    else if (!strcmp(c, "LIST")) rispondi('Z', "");   // nessuna registrazione: fine elenco
    else if (!strcmp(c, "VCAL")) comandoVcal(arg);
    else if (!strcmp(c, "OTA")) otaAvvia(arg ? arg : (char *)"");
    else if (!strcmp(c, "OTAEND")) otaFine();
    else if (!strcmp(c, "OTAABORT")) { if (otaAttivo) logRiga("ota: annullata"); otaAnnulla(); rispondi('K', "ota annullata"); }
    else { logRiga("cmd? %s", c); rispondi('X', "non supportato"); }
  }
}

// Chiamata dal loop: svuota l'anello in flash, manda gli avvisi, avvia l'installazione
static void servizioOta() {
  if (!otaAttivo) return;
  if (connHdl == BLE_CONN_HANDLE_INVALID && !otaInstallaAlle) { logRiga("ota: collegamento perso"); otaAnnulla(); return; }
  if (!otaSvuota()) { logRiga("ota: errore scrittura flash"); otaAnnulla(); rispondi('X', "ota scrittura fallita"); return; }
  if (otaMsgTipo) { char t = otaMsgTipo, m[40]; strlcpy(m, otaMsgTesto, sizeof(m)); otaMsgTipo = 0; rispondi(t, m); }
  uint32_t pct = otaAccettati * 100UL / otaTotale;
  if (!otaInstallaAlle && pct >= otaUltimoPct + 25) { otaUltimoPct = pct - pct % 25; logRiga("ota: ricevuto %lu%%", (unsigned long)pct); }
  if (otaInstallaAlle && (int32_t)(millis() - otaInstallaAlle) >= 0) otaInstalla();
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

  bool quattroTap = false;
  if (causaReset == 1) quattroTap = risveglioQuattroTap();   // se non arrivano 4 tap non ritorna: torna a dormire

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
  if (quattroTap) logRiga("risveglio 4 tap");
  if (*(volatile const char *)marcatoreVersione != 'S' || *(volatile const char *)marcatoreScheda != 'S') logRiga("?");   // tiene il marcatore nel binario (altrimenti il linker lo scarta)

  Bluefruit.configPrphBandwidth(BANDWIDTH_HIGH);   // MTU grande: le righe di log arrivano intere
  Bluefruit.begin();
  vcalCarica();
  Bluefruit.setTxPower(4);
  Bluefruit.setName("SwimTag");
  Bluefruit.Periph.setConnInterval(6, 12);   // 7,5-15 ms: l'OTA e il flusso dati scorrono meglio
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
  carStato.setFixedLen(12);
  carStato.begin();
  carComandi.setProperties(CHR_PROPS_WRITE | CHR_PROPS_WRITE_WO_RESP);
  carComandi.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
  carComandi.setMaxLen(64);
  carComandi.setWriteCallback(inComando);
  carComandi.begin();
  carRisposte.setProperties(CHR_PROPS_NOTIFY);
  carRisposte.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carRisposte.setMaxLen(100);
  carRisposte.setCccdWriteCallback(inCccdRisposte);
  carRisposte.begin();
  carOta.setProperties(CHR_PROPS_WRITE | CHR_PROPS_WRITE_WO_RESP);   // OTA: stesso protocollo dell'ESP32 (offset LE a 4 byte + dati)
  carOta.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
  carOta.setMaxLen(244);
  carOta.setWriteCallback(inOta);
  carOta.begin();
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
  controllaBootloader();
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
  if (Serial) {                                          // porta seriale USB aperta da un programma sul PC (DTR attivo): niente sospensione automatica
    static bool avvisato = false;
    if (!avvisato) { avvisato = true; logRiga("seriale aperta: niente sospensione"); }
    sg = 0; n = 0; secFermo = 0; rifOk = false; return;
  }
  if (Bluefruit.connected() && millis() - ultimoComando < 120000UL && ultimoComando) { sg = 0; n = 0; secFermo = 0; rifOk = false; return; }   // collegato e con comandi di recente: niente sospensione automatica
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

  if (imuOk && !otaAttivo) imuPoll();
  if (ora - ultimoDati >= 40) {            // 25 Hz
    ultimoDati += 40;
    if (ora - ultimoDati > 200) ultimoDati = ora;
    if (imuOk && !otaAttivo) {                // durante l'OTA niente flusso (e niente sospensione automatica)
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
  eseguiComandi();
  servizioOta();
  inviaLog();
  if (!Bluefruit.connected() && ora - ultimoLed >= 500) {   // blu lampeggiante = advertising
    ultimoLed = ora;
    digitalToggle(LED_BLUE);
  }
  delay(1);
}
