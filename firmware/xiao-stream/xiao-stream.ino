// SwimTimer - XIAO nRF52840 Sense: streaming IMU via BLE, log, sospensione, OTA via BLE, registrazione in vasca e
// sincronizzazione con il display (0.6.0, docs/SINCRONIZZAZIONE.md)
// Core: Seeeduino:nrf52 (non mbed) con Bluefruit. Protocollo e uso: vedi LEGGIMI.md
#include <Arduino.h>
#include <Wire.h>
#include <bluefruit.h>
#include <stdarg.h>
#include "nrf_gpio.h"
#include <InternalFileSystem.h>
#include "flash_qspi.h"          // flash QSPI da 2 MB della XIAO (registrazione in vasca), sopra nrfx_qspi
#include "swr_formato.h"
#include "swr_anello.h"        // memoria ad anello di 512 blocchi (formato 2)
#include "swr_sync.h"          // costanti e messaggi del protocollo di sincronizzazione (identici a display-sync/protocollo.h)
#include <flash/flash_nrf5x.h>   // scrittura flash compatibile con il SoftDevice (sd_flash_*)

#define VER_NUM "0.6.0"
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
// HICHG P0.13 (PIN_CHARGING_CURRENT): uscita bassa = carica a 100 mA (dalla 0.5.4; in ingresso sarebbe 50 mA); ~CHG P0.17 = 23 (LOW in carica)
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
// Risveglio con 4 tocchi: il primo doppio tap (2 tocchi) sveglia il chip, che poi conta in software
// RISVEGLIO_TAP_EXTRA tocchi singoli entro RISVEGLIO_FINESTRA_MS; se non arrivano torna subito in System OFF
// (senza BLE, USB ne' log).
#define RISVEGLIO_FINESTRA_MS 3000
#define TOCCO_LAMPO_MS 120     // il blu si spegne per questo tempo a ogni tocco contato
#define MARCA_FALSO 0xC0   // 0xC0 | tocchi visti: sospensione dopo un falso risveglio (diagnostica)
#define RISVEGLIO_PAUSA_MS 150   // dopo l'accensione dell'IMU si ignorano le oscillazioni residue del primo gesto
#define RISVEGLIO_TAP_EXTRA 2    // tocchi singoli ancora da vedere dopo il doppio tap che ha svegliato il chip
#define RISVEGLIO_GAP_MS 900     // dal 2o tocco extra in poi: tempo massimo fra due tocchi (poi la sequenza e' finita)
#define RISVEGLIO_DEBOUNCE_MS 100 // due eventi piu' vicini di cosi' sono lo stesso tocco (rimbalzo)
// Modalita' vasca (0.5.0): 4 tocchi senza USB = sveglia e registra su flash, BLE spento.
#define QUIETE_REG_S 180         // la registrazione si chiude dopo tanti secondi "abbastanza fermo" (soglie QUIETE_*)
#define BAT_MIN_AVVIO_MV 3400    // sotto questa tensione al risveglio non si registra
#define BAT_STOP_MV 3300         // sotto questa tensione (3 letture di fila, ogni 5 s) la registrazione si chiude
// Il bootloader Adafruit azzera RESETREAS prima di lanciare l'app: la causa "uscita da System OFF" non e' leggibile.
// Prima di ogni System OFF si scrive questa marca in GPREGRET2 (che il bootloader non tocca); all'avvio la si legge.
#define MARCA_SLEEP 0xB7
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
#define REG_FIFO_CTRL3 0x08
#define REG_FIFO_CTRL5 0x0A
#define REG_FIFO_STATUS1 0x3A
#define REG_FIFO_OUT_L 0x3E

// ---- UUID ----
#define UUID_BASE(n) "7a1e" #n "-5b1d-4c8e-9f3a-1d2c3b4a5e60"
BLEService servizio(UUID_BASE(0001));
BLECharacteristic carDati(UUID_BASE(0002));
BLECharacteristic carStato(UUID_BASE(0003));
BLECharacteristic carComandi(UUID_BASE(0004));
BLECharacteristic carRisposte(UUID_BASE(0005));
BLECharacteristic carOta(UUID_BASE(0006));
BLECharacteristic carVersione(UUID_BASE(0007));
BLEService servizioSync(UUID_BASE(0101));        // sincronizzazione con il display (docs/SINCRONIZZAZIONE.md §7)
BLECharacteristic carControllo(UUID_BASE(0102)); // display -> tag, scrittura cifrata
BLECharacteristic carSyncDati(UUID_BASE(0103));  // tag -> display, notifiche
BLECharacteristic carSyncStato(UUID_BASE(0104)); // lettura + notifica ogni 2 s, per la pagina web
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
static uint16_t connHdl = BLE_CONN_HANDLE_INVALID;   // collegamento della pagina web (servizio 7a1e0001): quello che abilita le notifiche su 0005
static bool inVasca = false;           // modalita' vasca (registrazione): niente LED di collegamento, niente comandi
static bool advAbilitato = false;      // l'annuncio deve restare acceso (spento prima di dormire e durante l'installazione OTA)
static bool bleOk = false;             // Bluefruit.begin riuscito
static uint16_t ultimaMv = 0;          // ultima tensione letta
static uint32_t tagId = 0;             // id univoco (FICR DEVICEID[0])
static char tagNome[13] = "";          // nome scelto dall'utente (max 12 caratteri ASCII), vuoto = ST-xxxx
static uint8_t tagColore = SYNC_COLORE_NESSUNO;   // indice 0..9 nella tavolozza, 0xFF = non impostato
static void annuncioAggiorna(bool forza);
static void scanRispostaImposta();
static void sonnoAnnuncia(bool piena);
static void bleSpegni();
static void notificaTutti(BLECharacteristic &c, const void *p, uint16_t n);
static bool sdAttivo() { uint8_t e = 0; sd_softdevice_is_enabled(&e); return e != 0; }

// ---------------- Log circolare ----------------
static char logBuf[LOG_RIGHE][LOG_LEN];
static uint32_t logN = 0, logInvio = 0;   // righe scritte, prossima da inviare
static volatile bool risposteAttive = false;
static volatile bool dumpInCorso = false;   // durante DUMP niente testo sulla seriale (sporcherebbe il binario)

static void logRiga(const char *fmt, ...) {
  char msg[LOG_LEN - 8];
  va_list ap; va_start(ap, fmt); vsnprintf(msg, sizeof(msg), fmt, ap); va_end(ap);
  uint32_t t = millis();
  snprintf(logBuf[logN % LOG_RIGHE], LOG_LEN, "%lu.%lu %s", (unsigned long)(t / 1000), (unsigned long)((t / 100) % 10), msg);
  if (Serial && !dumpInCorso) Serial.println(logBuf[logN % LOG_RIGHE]);
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
  ultimaMv = mv;
  carStato.write(s, 12);
  notificaTutti(carStato, s, 12);
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
// LED spenti a batteria (sotto la cuffia non si vedono e consumano, decisione 2026-11-10): si accendono solo con l'USB alimentata.
// Tutte le scritture dei LED passano di qui (attivi bassi: LOW = acceso). I tempi delle sequenze restano uguali.
static inline void ledScrivi(uint8_t pin, uint8_t livello) {
  bool usb = NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk;
  digitalWrite(pin, (livello == LOW && !usb) ? HIGH : livello);
}

static void vaInSospensione(bool soloUsb) {
  if (otaAttivo) { logRiga("sospensione rinviata: OTA"); return; }
  logRiga(soloUsb ? "sospensione (solo USB)" : "sospensione (4 tap/USB)");
  for (int i = 0; i < 150; i++) { inviaLog(); delay(2); }   // lascia partire le ultime righe
  sonnoAnnuncia(false);                                      // "vado in sonno" per ~2 s (e attende un display che sta scaricando)
  bleSpegni();
  Bluefruit.Advertising.restartOnDisconnect(false);
  Bluefruit.Advertising.stop();
  if (connHdl != BLE_CONN_HANDLE_INVALID) { Bluefruit.disconnect(connHdl); delay(300); }
  ledScrivi(LED_RED, HIGH); ledScrivi(LED_GREEN, HIGH); ledScrivi(LED_BLUE, HIGH);

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
  sd_power_gpregret_clr(1, 0xFF);
  sd_power_gpregret_set(1, MARCA_SLEEP);
  sd_power_system_off();
  while (true) __WFE();
}

// Conta in software i tocchi singoli (TAP_SRC bit SINGLE_TAP; l'IMU deve essere in modalita' tocco singolo).
//  - i primi ignoraMs ms non contano (oscillazione residua del gesto precedente)
//  - fino a 2 tocchi vale la finestra totale finestraMs; dal 2o in poi ogni tocco deve arrivare entro gapMs dal precedente
//  - si ferma a `massimo` tocchi; lampeggia = LED rosso a 5 Hz (conferma dell'azzeramento). Ritorna i tocchi contati.
static uint8_t contaTocchi(uint32_t finestraMs, uint32_t ignoraMs, uint32_t gapMs, uint8_t massimo, bool lampeggia, bool invitoBlu = false) {
  uint8_t n = 0, src = 0;
  uint32_t t0 = millis(), ultimo = 0;
  i2cLeggi(REG_TAP_SRC, &src, 1);                                   // azzera il latch
  while (true) {
    uint32_t ora = millis();
    uint32_t limite = (n >= 2) ? ultimo + gapMs : t0 + finestraMs;
    if (ora >= limite) break;
    if (lampeggia) ledScrivi(LED_RED, ((ora / 100) & 1) ? HIGH : LOW);
    // blu acceso = invito ai tocchi; si spegne per TOCCO_LAMPO_MS a ogni tocco contato (riscontro visivo)
    if (invitoBlu && ora - t0 >= ignoraMs) ledScrivi(LED_BLUE, (n > 0 && ora - ultimo < TOCCO_LAMPO_MS) ? HIGH : LOW);
    if (i2cLeggi(REG_TAP_SRC, &src, 1) && (src & 0x20)) {           // SINGLE_TAP
      if (ora - t0 >= ignoraMs && (n == 0 || ora - ultimo >= RISVEGLIO_DEBOUNCE_MS)) {
        n++; ultimo = ora;
        if (invitoBlu) ledScrivi(LED_BLUE, HIGH);
        if (n >= massimo) break;
      }
    }
    delay(5);
  }
  if (lampeggia) ledScrivi(LED_RED, HIGH);
  if (invitoBlu) ledScrivi(LED_BLUE, HIGH);
  return n;
}

// Risveglio dal doppio tap: chiamata a inizio setup(), prima di USB e BLE. Ritorna true se arrivano altri tocchi
// (almeno RISVEGLIO_TAP_EXTRA); i tocchi extra contati (max 6) restano in tocchiExtra: 2..5 = registra (2 tocchi, blu, 2 tocchi),
// 6 = azzera (2 tocchi, blu, 6 tocchi).
// All'uscita da System OFF i pin tornano al default: l'IMU perde l'alimentazione (P1.08) e quindi la configurazione,
// perche' il reset dura piu' dei suoi tempi di spegnimento. Si riaccende, si riconfigura il tap e si ascolta.
static uint8_t tocchiExtra = 0;
static bool imuMutoAlRisveglio = false;
static bool risveglioQuattroTap() {
  NRF_P1->PIN_CNF[8] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos) | (GPIO_PIN_CNF_DRIVE_H0H1 << GPIO_PIN_CNF_DRIVE_Pos);
  NRF_P1->OUTSET = 1UL << 8;
  pinMode(16, INPUT_PULLUP); pinMode(17, INPUT_PULLUP);
  pinMode(PIN_INT1_ASSOLUTO, INPUT);
  delay(40);
  Wire1.begin();
  Wire1.setClock(400000);
  uint8_t id = 0;
  bool ok = false;
  for (int i = 0; i < 4 && !ok; i++) {                              // l'IMU puo' metterci piu' di 40 ms a partire
    ok = i2cLeggi(REG_WHO_AM_I, &id, 1) && id == 0x6A;
    if (!ok) delay(40);
  }
  if (!ok) { imuMutoAlRisveglio = true; return true; }              // IMU muto: avvio normale (almeno si raggiunge via USB)
  configuraTap();
  // Conferma in SOFTWARE su tocchi singoli (non il DOUBLE_TAP hardware, che nell'oscillazione residua del primo gesto
  // poteva scattare da solo e svegliare la tag con 2 soli tocchi).
  i2cScrivi(REG_WAKE_UP_THS, 0x00);                                 // SINGLE_DOUBLE_TAP = 0: tocco singolo
  i2cScrivi(REG_MD1_CFG, 0x40);                                     // tocco singolo su INT1 (solo per coerenza: si legge TAP_SRC)
  pinMode(LED_BLUE, OUTPUT); ledScrivi(LED_BLUE, HIGH);
  tocchiExtra = contaTocchi(RISVEGLIO_FINESTRA_MS, RISVEGLIO_PAUSA_MS, RISVEGLIO_GAP_MS, 6, false, true);
  if (tocchiExtra >= RISVEGLIO_TAP_EXTRA) return true;
  configuraTap();                                                   // torna alla configurazione del doppio tap per dormire
  delay(20);
  // falso risveglio: di nuovo System OFF con la stessa configurazione
  attendiInt1Bassa(300);
  nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
  NRF_POWER->GPREGRET2 = MARCA_FALSO | (tocchiExtra & 0x0F);   // falso risveglio: la marca vale come sleep e mostra i tocchi visti
  NRF_POWER->SYSTEMOFF = POWER_SYSTEMOFF_SYSTEMOFF_Enter;
  while (true) __WFE();
}

// ---------------- Nome e colore della tag (InternalFS /nome.bin: [0] colore, [1] lunghezza, [2..] testo) ----------------
#define NOME_FILE "/nome.bin"
static void nomeCarica() {
  InternalFS.begin();
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  uint8_t b[14] = {SYNC_COLORE_NESSUNO, 0};
  if (f.open(NOME_FILE, Adafruit_LittleFS_Namespace::FILE_O_READ)) { f.read(b, sizeof(b)); f.close(); }
  tagColore = (b[0] <= 9) ? b[0] : SYNC_COLORE_NESSUNO;
  uint8_t n = b[1] <= 12 ? b[1] : 0;
  bool ok = true;
  for (uint8_t i = 0; i < n; i++) if (b[2 + i] < 0x20 || b[2 + i] > 0x7E) ok = false;
  if (!ok) n = 0;
  memcpy(tagNome, b + 2, n); tagNome[n] = 0;
}
static void nomeSalva() {
  uint8_t b[14];
  memset(b, 0, sizeof(b));
  b[0] = tagColore; b[1] = strlen(tagNome); memcpy(b + 2, tagNome, b[1]);
  InternalFS.remove(NOME_FILE);
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  if (f.open(NOME_FILE, Adafruit_LittleFS_Namespace::FILE_O_WRITE)) { f.write(b, sizeof(b)); f.close(); }
}

// ---------------- Base del numero di sequenza (InternalFS /seq.bin) ----------------
// Il seq dei blocchi non si riusa MAI, nemmeno dopo un azzeramento: prima di cancellare la flash si salva il massimo
// usato, e dopo la scansione il seq riparte da li'. Senza file: 1000 (sopra i seq usati il 2026-11-10, prima della base).
#define SEQ_FILE "/seq.bin"
#define SEQ_BASE_INIZIALE 1000UL
static uint32_t seqBaseCarica() {
  InternalFS.begin();
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  uint32_t v = SEQ_BASE_INIZIALE;
  if (f.open(SEQ_FILE, Adafruit_LittleFS_Namespace::FILE_O_READ)) { uint32_t x; if (f.read((uint8_t *)&x, 4) == 4 && x != 0xFFFFFFFFu) v = x; f.close(); }
  return v;
}
static void seqBaseSalva(uint32_t v) {
  InternalFS.begin();
  InternalFS.remove(SEQ_FILE);
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  if (f.open(SEQ_FILE, Adafruit_LittleFS_Namespace::FILE_O_WRITE)) { f.write((const uint8_t *)&v, 4); f.close(); }
}
// Da chiamare PRIMA di ogni cancellazione totale della flash
static void seqBasePrimaDiCancellare(uint32_t maxUsato) {
  uint32_t b = seqBaseCarica();
  if (maxUsato > b) b = maxUsato;
  seqBaseSalva(b);
}

// ---------------- Comandi (caratteristica 0004) ----------------
// Coda di 4 comandi: la callback BLE copia il testo, li esegue il loop.
#define CMD_LEN 64
static char cmdCoda[4][CMD_LEN];
static volatile uint8_t cmdTesta = 0, cmdCodaI = 0;

static void inComando(uint16_t h, BLECharacteristic *, uint8_t *d, uint16_t len) {
  ultimoComando = millis();
  connHdl = h;   // le risposte vanno a chi ha scritto il comando
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

static void inOta(uint16_t h, BLECharacteristic *, uint8_t *d, uint16_t len) {
  connHdl = h;
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
  advAbilitato = false;
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

// NOME,<testo>: nome della tag (max 12 caratteri ASCII stampabili, vuoto = cancella). Risposte K nome <testo> / X nome ...
static void comandoNome(const char *t) {
  size_t n = strlen(t);
  if (n > 12) { rispondi('X', "nome troppo lungo (max 12)"); return; }
  for (size_t i = 0; i < n; i++) if ((uint8_t)t[i] < 0x20 || (uint8_t)t[i] > 0x7E) { rispondi('X', "nome carattere non valido"); return; }
  memcpy(tagNome, t, n); tagNome[n] = 0;
  nomeSalva();
  logRiga("nome '%s'", tagNome);
  char r[24]; snprintf(r, sizeof(r), "nome %s", tagNome);
  rispondi('K', r);
  scanRispostaImposta();
  annuncioAggiorna(true);
}
// COLORE,<0-9>: indice nella tavolozza; COLORE,-1 cancella. Risposte K colore <n> / X colore ...
static void comandoColore(const char *a) {
  if (!a || !*a) { char r[24]; snprintf(r, sizeof(r), "colore %d", tagColore == SYNC_COLORE_NESSUNO ? -1 : tagColore); rispondi('K', r); return; }
  char *fine; long v = strtol(a, &fine, 10);
  if (*fine || v < -1 || v > 9) { rispondi('X', "colore fuori campo (0-9 o -1)"); return; }
  tagColore = v < 0 ? SYNC_COLORE_NESSUNO : (uint8_t)v;
  nomeSalva();
  logRiga("colore %ld", v);
  char r[24]; snprintf(r, sizeof(r), "colore %ld", v);
  rispondi('K', r);
  annuncioAggiorna(true);
}

static void eseguiComandi() {
  while (cmdTesta != cmdCodaI) {
    char c[CMD_LEN]; strcpy(c, cmdCoda[cmdCodaI & 3]); cmdCodaI = cmdCodaI + 1;
    char *arg = strchr(c, ','); if (arg) *arg++ = 0;   // il comando e' fino alla prima virgola
    if (inVasca) rispondi('X', "registrazione in corso");   // in vasca nessun comando (OTA e sospensione compresi)
    else if (!strcmp(c, "SLEEP")) vaInSospensione();
    else if (!strcmp(c, "LIST")) rispondi('Z', "");   // nessuna registrazione: fine elenco
    else if (!strcmp(c, "VCAL")) comandoVcal(arg);
    else if (!strcmp(c, "NOME")) comandoNome(arg ? arg : "");
    else if (!strcmp(c, "COLORE")) comandoColore(arg);
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

static void inCccdRisposte(uint16_t h, BLECharacteristic *, uint16_t valore) {
  if (valore & 1) { connHdl = h; logInvio = logN > LOG_RIGHE ? logN - LOG_RIGHE : 0; risposteAttive = true; }   // rimanda il buffer
  else if (h == connHdl) risposteAttive = false;
}

static void inConnessione(uint16_t h) {
  if (connHdl == BLE_CONN_HANDLE_INVALID) connHdl = h;   // provvisorio: la pagina vera e' chi scrive i comandi o abilita 0005
  if (!inVasca) { ledScrivi(LED_BLUE, HIGH); ledScrivi(LED_GREEN, LOW); }   // verde fisso
  logRiga("connesso %u", h);
}
static void inDisconnessione(uint16_t h, uint8_t motivo) {
  if (h == connHdl) { connHdl = BLE_CONN_HANDLE_INVALID; risposteAttive = false; }
  if (!inVasca) ledScrivi(LED_GREEN, HIGH);
  logRiga("disconnesso %u (0x%02X)", h, motivo);
}

// Notifica a tutti i collegamenti che hanno abilitato la caratteristica (pagina web e, se serve, display)
static void notificaTutti(BLECharacteristic &c, const void *p, uint16_t n) {
  for (uint8_t i = 0; i < BLE_MAX_CONNECTION; i++) {
    BLEConnection *k = Bluefruit.Connection(i);
    if (k && k->connected() && c.notifyEnabled(i)) c.notify(i, p, n);
  }
}

// ================= Memoria di registrazione (flash QSPI 2 MB, formato 2: swr_formato.h e swr_anello.h) =================
static FlashQspi flash;
static bool flashPronta = false;
static SwrAnello anello;
static bool anelloOk = false;         // flash vuota o in formato 2, scansionata: si puo' registrare e sincronizzare
static bool formatoVecchio = false;   // trovata flash in formato 1: non si tocca (DUMP la legge, AZZERA a tocchi la cancella)
static uint32_t memPagine = SWR_TOT_PAGINE;

static bool memInit() {
  if (flashPronta) return true;
  if (!flash.begin()) return false;
  memPagine = min((uint32_t)SWR_TOT_PAGINE, (uint32_t)(flash.size() / SWR_PAGINA));
  flashPronta = memPagine >= 64;
  return flashPronta;
}
static EsitoScansione memScansiona() {
  anello.inizia(&flash, tagId);
  EsitoScansione e = anello.scansiona();
  { uint32_t b = seqBaseCarica(); if (anello.maxSeq < b) anello.maxSeq = b; }   // seq mai riusato dopo un azzeramento
  anelloOk = (e == SC_OK);
  formatoVecchio = (e == SC_FORMATO1);
  return e;
}
// ---- formato 1 (solo per DUMP e MEM di una flash vecchia) ----
static bool memPaginaLibera(uint32_t p) {   // intestazione tutta 0xFF = mai scritta
  uint8_t h[16];
  flash.readBuffer(p * SWR_PAGINA, h, 16);
  for (int i = 0; i < 16; i++) if (h[i] != 0xFF) return false;
  return true;
}
static uint32_t memPrimaLibera() {   // prima pagina libera del formato 1 (ricerca binaria)
  uint32_t lo = 0, hi = memPagine;
  while (lo < hi) {
    uint32_t m = (lo + hi) / 2;
    if (memPaginaLibera(m)) hi = m; else lo = m + 1;
  }
  return lo;
}

// ================= Annuncio e sincronizzazione con il display =================
static bool annSonno = false, annPiena = false;
static uint32_t vInizioMs = 0;
static uint8_t advMd[SYNC_LEN_ANNUNCIO];
static uint32_t advTUlt = 0;

// stato della sincronizzazione (un solo display alla volta)
static uint16_t syncConn = BLE_CONN_HANDLE_INVALID;
static bool syncAttivo = false, syncErrore = false, mappaDaInviare = false, fineInviata = false;
static uint32_t finSeq[SYNC_FINESTRA];          // blocchi trasmessi e non ancora confermati (finestra di 2)
static uint8_t finN = 0;
static uint32_t ripSeq[2];                      // blocchi da ritrasmettere (RIPETI)
static uint8_t ripN = 0;
static bool txAttiva = false;                   // trasmissione di un blocco in corso
static uint32_t txSeq = 0, txCrc = 0, txMillis = 0, chiusureViste = 0;
static int16_t txBlk = 0;
static uint8_t txFase = 0;                      // 0 = intestazione BLOCCO, 1..32 = frammento fase-1
static uint16_t statConfermati = 0;             // blocchi confermati dall'avvio

struct CmdSync { uint16_t conn; uint8_t tipo, motivo; uint32_t seq, crc; };
static CmdSync cmdSy[16];
static volatile uint8_t cmdSyT = 0, cmdSyC = 0;
static uint8_t uscBuf[8][9];
static uint8_t uscLen[8];
static uint8_t uscT = 0, uscC = 0;

static uint8_t erroriAnnuncio() {
  uint8_t e = 0;
  if (!inVasca && !imuOk) e |= ERR_IMU;
  if (!flashPronta || formatoVecchio || anello.ultimoErrore == AN_FLASH) e |= ERR_FLASH;
  if (ultimaMv > 0 && ultimaMv < 3400) e |= ERR_BATT;
  return e;
}
static uint8_t statoAnnuncio() {
  if (annSonno) return ST_SONNO;
  if (annPiena) return ST_PIENA;
  if (erroriAnnuncio() & (ERR_IMU | ERR_FLASH)) return ST_ERRORE;
  if (syncAttivo) return ST_SINCRONIZZA;
  return inVasca ? ST_REGISTRA : ST_PRONTA;
}
static uint16_t secondiRegistrazione() {
  if (!inVasca) return 0;
  uint32_t s = (millis() - vInizioMs) / 1000;
  return s > 65535 ? 65535 : (uint16_t)s;
}
static void annuncioCostruisci(uint8_t *md) {
  SyncAnnuncio a;
  a.id = tagId;
  a.stato = statoAnnuncio();
  uint16_t b = ultimaMv / 20;
  a.batt20 = b > 255 ? 255 : (uint8_t)b;
  a.pctMem = anelloOk ? anello.pctNonConfermata() : 0;
  a.inAttesa = anelloOk ? anello.nDaValidare : 0;
  a.ultimoSeq = anelloOk ? anello.maxSeq : 0;
  a.secReg = secondiRegistrazione();
  a.errori = erroriAnnuncio();
  a.colore = tagColore;
  syncAnnuncioCodifica(a, md);
}

// Riscrive i dati dell'annuncio quando cambia qualcosa (subito) o ogni 2 s (per i secondi di registrazione).
// Il cambio richiede stop/start dell'advertising (la libreria riscrive il buffer sul posto): qualche ms ogni 2 s al massimo.
// Se c'e' un solo collegamento l'advertising riparte, cosi' il secondo (display + pagina) puo' collegarsi.
static void annuncioAggiorna(bool forza) {
  if (!bleOk || otaAttivo) return;   // durante l'OTA l'annuncio non si tocca
  uint8_t md[SYNC_LEN_ANNUNCIO];
  annuncioCostruisci(md);
  uint32_t t = millis();
  uint8_t a[SYNC_LEN_ANNUNCIO], b[SYNC_LEN_ANNUNCIO];   // confronto senza i secondi di registrazione (byte 18..19)
  memcpy(a, md, sizeof(a)); memcpy(b, advMd, sizeof(b));
  a[18] = a[19] = b[18] = b[19] = 0;
  bool sostanziale = memcmp(a, b, sizeof(a)) != 0;
  bool fermo = advAbilitato && !Bluefruit.Advertising.isRunning() && Bluefruit.Periph.connected() < 2;
  if (!forza && !fermo && !(sostanziale && t - advTUlt >= 200) && !(t - advTUlt >= 2000)) return;
  memcpy(advMd, md, sizeof(md));
  advTUlt = t;
  Bluefruit.Advertising.stop();
  Bluefruit.Advertising.clearData();
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  if (!Bluefruit.Advertising.addManufacturerData(md, SYNC_LEN_ANNUNCIO)) logRiga("annuncio: dati produttore KO");
  if (advAbilitato && Bluefruit.Periph.connected() < 2) Bluefruit.Advertising.start(0);
}

// Risposta alla scansione: nome locale (nome scelto dall'utente o ST-xxxx) e, se c'e' posto (nome <= 11 caratteri), il servizio 7a1e0001
static void scanRispostaImposta() {
  char nome[16];
  if (tagNome[0]) strlcpy(nome, tagNome, sizeof(nome));
  else snprintf(nome, sizeof(nome), "ST-%04X", (unsigned)(tagId & 0xFFFF));
  Bluefruit.setName(nome);
  Bluefruit.ScanResponse.clearData();
  Bluefruit.ScanResponse.addName();
  if (strlen(nome) <= 11) Bluefruit.ScanResponse.addService(servizio);
}

static bool connessioneViva(uint16_t h) {
  BLEConnection *c = Bluefruit.Connection(h);
  return c && c->connected();
}

// CONTROLLO (display -> tag): la callback copia soltanto, il loop elabora (la flash non si tocca dalla callback)
static void inControllo(uint16_t h, BLECharacteristic *, uint8_t *d, uint16_t len) {
  if (len < 1 || (uint8_t)(cmdSyT - cmdSyC) >= 16) return;
  CmdSync c; c.conn = h; c.tipo = d[0]; c.motivo = 0; c.seq = 0; c.crc = 0;
  switch (d[0]) {
    case M_PRONTO: if (len < 2) return; c.motivo = d[1]; break;
    case M_CONFERMA: if (len < 9) return; c.seq = swrLeggi32(d + 1); c.crc = swrLeggi32(d + 5); break;
    case M_RIPETI: if (len < 5) return; c.seq = swrLeggi32(d + 1); break;
    case M_STOP: if (len < 2) return; c.motivo = d[1]; break;
    default: return;
  }
  cmdSy[cmdSyT & 15] = c;
  cmdSyT = cmdSyT + 1;
}

static void syncReset() {
  syncAttivo = false; syncErrore = false; mappaDaInviare = false; fineInviata = false;
  syncConn = BLE_CONN_HANDLE_INVALID;
  finN = 0; ripN = 0; txAttiva = false; uscT = uscC = 0;
}
static void uscAccoda(const uint8_t *p, uint8_t n) {
  if ((uint8_t)(uscT - uscC) >= 8) return;
  memcpy(uscBuf[uscT & 7], p, n);
  uscLen[uscT & 7] = n;
  uscT = uscT + 1;
}
static void uscErrore(uint8_t codice) { uint8_t m[2] = {M_ERRORE, codice}; uscAccoda(m, 2); }

// Notifica diretta al SoftDevice (non blocca: se la coda e' piena ritorna false e si riprova al giro dopo)
static bool syncInvia(const uint8_t *p, uint16_t n) {
  ble_gatts_hvx_params_t h;
  memset(&h, 0, sizeof(h));
  uint16_t l = n;
  h.handle = carSyncDati.handles().value_handle;
  h.type = BLE_GATT_HVX_NOTIFICATION;
  h.p_len = &l;
  h.p_data = p;
  return sd_ble_gatts_hvx(syncConn, &h) == NRF_SUCCESS && l == n;
}

static void finRimuovi(uint32_t s) {
  for (uint8_t i = 0; i < finN; i++) if (finSeq[i] == s) { memmove(finSeq + i, finSeq + i + 1, (finN - i - 1) * 4); finN--; break; }
}
static bool finPresente(uint32_t s) { for (uint8_t i = 0; i < finN; i++) if (finSeq[i] == s) return true; return false; }
static void ripRimuovi(uint32_t s) {
  for (uint8_t i = 0; i < ripN; i++) if (ripSeq[i] == s) { memmove(ripSeq + i, ripSeq + i + 1, (ripN - i - 1) * 4); ripN--; break; }
}

// CONFERMA (seq, crc32): il blocco si marca confermato SOLO se il CRC32 coincide con quello ricalcolato dalla flash
static void syncConferma(uint32_t seq, uint32_t crc) {
  int16_t b = anello.trovaSeq(seq);
  if (b < 0) { uscErrore(E_SEQ_SCONOSCIUTO); return; }
  if (anello.st[b] == BL_DA_VALIDARE) {
    uint32_t c;
    if (!anello.crcBlocco(b, c)) { uscErrore(E_FLASH); return; }
    if (c != crc) { uscErrore(E_CRC_CONFERMA); return; }
    if (!anello.conferma(b)) { uscErrore(E_FLASH); return; }   // scrittura del byte 16 + rilettura
    statConfermati++;
  }   // gia' confermato (doppione): si risponde comunque CONFERMATO
  uint8_t m[5]; m[0] = M_CONFERMATO; sw32(m + 1, seq);
  uscAccoda(m, 5);
  finRimuovi(seq);
  ripRimuovi(seq);
  if (txAttiva && txSeq == seq) txAttiva = false;
}

static void syncElabora() {
  while (cmdSyC != cmdSyT) {
    CmdSync c = cmdSy[cmdSyC & 15];
    cmdSyC = cmdSyC + 1;
    if (c.tipo == M_PRONTO) {
      if (!anelloOk || c.motivo != SYNC_VERSIONE) { logRiga("sync: PRONTO ignorato"); continue; }
      if (syncAttivo && c.conn != syncConn && connessioneViva(syncConn)) continue;   // un solo display alla volta
      syncReset();
      syncConn = c.conn; syncAttivo = true; mappaDaInviare = true;
      chiusureViste = anello.chiusure;
      logRiga("sync: pronto (conn %u)", c.conn);
      continue;
    }
    if (!syncAttivo || c.conn != syncConn) continue;
    if (c.tipo == M_CONFERMA) syncConferma(c.seq, c.crc);
    else if (c.tipo == M_RIPETI) {
      int16_t b = anello.trovaSeq(c.seq);
      if (b < 0 || anello.st[b] != BL_DA_VALIDARE) { uscErrore(E_SEQ_SCONOSCIUTO); continue; }
      if (txAttiva && txSeq == c.seq) { txFase = 0; continue; }          // sta partendo proprio quello: ricomincia
      if (!finPresente(c.seq)) { if (finN >= SYNC_FINESTRA) continue; finSeq[finN++] = c.seq; }
      bool presente = false;
      for (uint8_t i = 0; i < ripN; i++) if (ripSeq[i] == c.seq) presente = true;
      if (!presente && ripN < 2) ripSeq[ripN++] = c.seq;
    } else if (c.tipo == M_STOP) {
      logRiga("sync: STOP motivo %u", c.motivo);
      syncReset();
    }
  }
}

// Sceglie il prossimo blocco da trasmettere: prima i RIPETI, poi il non confermato piu' vecchio se la finestra ha posto
static bool syncAvviaTx() {
  if (syncErrore) return false;
  int16_t b = -1;
  uint32_t s = 0;
  while (ripN > 0 && b < 0) {
    s = ripSeq[0];
    memmove(ripSeq, ripSeq + 1, (--ripN) * 4);
    b = anello.trovaSeq(s);
    if (b >= 0 && anello.st[b] != BL_DA_VALIDARE) b = -1;
  }
  if (b < 0 && finN < SYNC_FINESTRA) {
    b = anello.piuVecchioDaValidare(finN > 0 ? finSeq[0] : 0, finN > 1 ? finSeq[1] : 0);
    if (b >= 0) { s = anello.seq[b]; finSeq[finN++] = s; }
  }
  if (b < 0) return false;
  uint32_t crc;
  uint8_t t4[4];
  if (!anello.crcBlocco(b, crc) || !anello.leggi(b, 4, t4, 4)) { uscErrore(E_FLASH); syncErrore = true; return false; }
  txSeq = s; txBlk = b; txCrc = crc; txMillis = swrLeggi32(t4); txFase = 0; txAttiva = true;
  return true;
}

// Un messaggio del blocco in corso (BLOCCO, poi 32 FRAMMENTI). false = coda radio piena (si riprova) o errore
static bool syncPasso() {
  uint8_t m[SYNC_FRAMMENTO + 6];
  if (txFase == 0) {
    uint16_t n = syncBlocco(m, txSeq, txBlk, txCrc, txMillis);
    if (!syncInvia(m, n)) return false;
    txFase = 1;
    return true;
  }
  uint8_t idx = txFase - 1;
  syncFrammentoIntest(m, txSeq, idx);
  if (!anello.leggi(txBlk, idx * SYNC_FRAMMENTO, m + 6, SYNC_FRAMMENTO)) { uscErrore(E_FLASH); syncErrore = true; txAttiva = false; return false; }
  if (idx == 1) memset(m + 6 + (SWR_OFF_CONFERMA - SYNC_FRAMMENTO), 0xFF, SWR_LEN_CONFERMA);   // CRC32 con la conferma a 0xFF (byte 252..255 = frammento 1)
  if (!syncInvia(m, 6 + SYNC_FRAMMENTO)) return false;
  if (++txFase > SYNC_N_FRAMMENTI) txAttiva = false;
  return true;
}

// Chiamata a ogni giro del loop: non blocca mai (al massimo ~10 messaggi, poi torna a registrare)
static void syncServi() {
  if (!bleOk) return;
  syncElabora();
  if (!syncAttivo) return;
  BLEConnection *c = Bluefruit.Connection(syncConn);
  if (!c || !c->connected()) { logRiga("sync: collegamento perso"); syncReset(); return; }
  if (!carSyncDati.notifyEnabled(syncConn) || c->getMtu() < 138) return;   // MAPPA = 135 byte + 3 di intestazione ATT
  if (anello.chiusure != chiusureViste) { chiusureViste = anello.chiusure; fineInviata = false; }
  for (uint8_t budget = 10; budget; budget--) {
    if (mappaDaInviare) {
      uint8_t m[135], mp[128];
      anello.mappa(mp);
      syncMappa(m, millis(), anello.aperto >= 0 ? (uint16_t)anello.aperto : 0xFFFF, mp);
      if (!syncInvia(m, 135)) return;
      mappaDaInviare = false;
      continue;
    }
    if (uscC != uscT) {
      if (!syncInvia(uscBuf[uscC & 7], uscLen[uscC & 7])) return;
      uscC = uscC + 1;
      continue;
    }
    if (!txAttiva && !syncAvviaTx()) {
      if (!syncErrore && !fineInviata && finN == 0 && ripN == 0 && anello.nDaValidare == 0) {   // niente da confermare: FINE
        uint8_t m[5]; m[0] = M_FINE; sw32(m + 1, anello.maxSeq);
        uscAccoda(m, 5);
        fineInviata = true;
        continue;
      }
      return;
    }
    if (!syncPasso()) return;
  }
}

// STATO SYNC (0104): 151 byte, lettura + notifica ogni 2 s (la pagina web non puo' confermare)
static void statoSyncServi(bool forza) {
  static uint32_t t = 0;
  if (!bleOk || (!forza && millis() - t < 2000)) return;
  t = millis();
  uint8_t s[SYNC_LEN_STATO];
  uint16_t b = ultimaMv / 20;
  s[0] = SYNC_VERSIONE; sw32(s + 1, tagId); s[5] = statoAnnuncio(); s[6] = b > 255 ? 255 : (uint8_t)b;
  s[7] = anelloOk ? anello.pctNonConfermata() : 0;
  sw16(s + 8, anelloOk ? anello.nDaValidare : 0);
  sw32(s + 10, anelloOk ? anello.maxSeq : 0);
  sw16(s + 14, secondiRegistrazione());
  s[16] = erroriAnnuncio();
  sw16(s + 17, anelloOk && anello.aperto >= 0 ? (uint16_t)anello.aperto : 0xFFFF);
  sw32(s + 19, anelloOk ? anello.seqPiuVecchioDaValidare() : 0);
  if (anelloOk) anello.mappa(s + 23); else memset(s + 23, 0, 128);
  carSyncStato.write(s, SYNC_LEN_STATO);
  for (uint8_t i = 0; i < BLE_MAX_CONNECTION; i++) {
    if (syncAttivo && i == syncConn) continue;     // il display sta scaricando: la sua coda radio serve ai blocchi
    BLEConnection *k = Bluefruit.Connection(i);
    if (k && k->connected() && k->getMtu() >= 154 && carSyncStato.notifyEnabled(i)) carSyncStato.notify(i, s, SYNC_LEN_STATO);
  }
}

static void bleServi(uint32_t ms) {
  uint32_t t0 = millis();
  while (millis() - t0 < ms) { syncServi(); annuncioAggiorna(false); statoSyncServi(false); delay(2); }
}
static void bleSpegni() {
  if (!bleOk) return;
  advAbilitato = false;
  Bluefruit.Advertising.restartOnDisconnect(false);
  Bluefruit.Advertising.stop();
  for (uint8_t i = 0; i < BLE_MAX_CONNECTION; i++) if (connessioneViva(i)) Bluefruit.disconnect(i);
  delay(150);
}
// Prima di dormire: annuncia "vado in sonno" (stato 0) per ~2 s; se la memoria e' piena prima annuncia lo stato 4 per 2 s.
// Se un display sta scaricando si aspetta la fine (FINE, STOP o collegamento perso), al massimo 60 s per non scaricare la batteria.
static void sonnoAnnuncia(bool piena) {
  if (!bleOk) return;
  if (piena) { annPiena = true; annuncioAggiorna(true); bleServi(2000); annPiena = false; }
  annSonno = true;
  annuncioAggiorna(true);
  statoSyncServi(true);
  bleServi(2000);
  uint32_t t0 = millis();
  while (syncAttivo && millis() - t0 < 60000UL) {
    bleServi(20);
    if (fineInviata && uscC == uscT) { bleServi(300); break; }
  }
}

// Avvio del BLE (modalita' normale e vasca): 2 collegamenti periferici (display + pagina web), MTU 247, servizi
static void bleIniz(bool vasca) {
  tagId = NRF_FICR->DEVICEID[0];
  Bluefruit.configPrphConn(247, 6, 4, 1);   // MTU 247, evento 7,5 ms, 4 notifiche in coda per collegamento
  Bluefruit.configAttrTableSize(0x1400);   // 5 KB: il predefinito del nRF52840 e' 4 KB (0x1000), con 3 KB i servizi non entravano tutti
  Bluefruit.autoConnLed(false);             // mai il lampeggio automatico del BLE: consuma e con il BLE sempre acceso non dice niente
  bleOk = Bluefruit.begin(2, 0);
  if (!bleOk) { logRiga("BLE begin KO (RAM del SoftDevice?)"); return; }
  vcalCarica();
  nomeCarica();
  Bluefruit.setTxPower(4);
  Bluefruit.Periph.setConnInterval(6, 12);   // 7,5-15 ms: l'OTA e i blocchi scorrono meglio
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

  servizioSync.begin();
  carControllo.setProperties(CHR_PROPS_WRITE);
  carControllo.setPermission(SECMODE_NO_ACCESS, SECMODE_ENC_NO_MITM);   // solo collegamento cifrato (bonding Just Works): la CONFERMA autorizza la riscrittura
  carControllo.setMaxLen(16);
  carControllo.setWriteCallback(inControllo);
  carControllo.begin();
  carSyncDati.setProperties(CHR_PROPS_NOTIFY);
  carSyncDati.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carSyncDati.setMaxLen(135);
  carSyncDati.begin();
  carSyncStato.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  carSyncStato.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carSyncStato.setFixedLen(SYNC_LEN_STATO);
  carSyncStato.begin();
  uint8_t zero[SYNC_LEN_STATO] = {0};
  carSyncStato.write(zero, SYNC_LEN_STATO);

  scanRispostaImposta();
  Bluefruit.Advertising.restartOnDisconnect(false);   // riparte annuncioAggiorna(): serve anche con 1 collegamento su 2
  Bluefruit.Advertising.setInterval(320, 320);        // 200 ms, sempre (anche in registrazione)
  advAbilitato = true;
  annuncioAggiorna(true);
}

// ================= Modalita' vasca (registrazione su flash; dalla 0.6.0 il BLE resta acceso) =================
#define LED_R 1
#define LED_G 2
#define LED_B 4
static void ledSet(uint8_t m) {   // LED RGB attivi bassi
  ledScrivi(LED_RED, (m & LED_R) ? LOW : HIGH);
  ledScrivi(LED_GREEN, (m & LED_G) ? LOW : HIGH);
  ledScrivi(LED_BLUE, (m & LED_B) ? LOW : HIGH);
}

static SwrCodificatore cod;
static uint32_t vCampioni = 0, vPagineSeg = 0;
static uint16_t vSeg = 0, vMv = 0;
static int8_t vTemp = 0;
static uint8_t vFlagsProx = SWR_FLAG_PRIMA, vMotivo = 0, vErrI2c = 0;
static bool vAttivo = false;   // registrazione avviata: attendi() serve anche il FIFO
// misure per la verifica dei tempi (finiscono nella pagina di chiusura, byte 24..30)
static uint16_t statGapMax = 0, statApriMax = 0;
static uint8_t statOverrun = 0;

static int8_t tempDie() {
  if (sdAttivo()) { int32_t t = 0; sd_temp_get(&t); return (int8_t)(t / 4); }
  NRF_TEMP->EVENTS_DATARDY = 0;
  NRF_TEMP->TASKS_START = 1;
  uint32_t t0 = millis();
  while (!NRF_TEMP->EVENTS_DATARDY && millis() - t0 < 5) { }
  int32_t t = NRF_TEMP->TEMP;
  NRF_TEMP->TASKS_STOP = 1;
  return (int8_t)(t / 4);
}
static bool vbusOra() {
  if (sdAttivo()) return vbusPresente();
  return NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk;
}
static void gpregretImposta(uint8_t v) {
  if (sdAttivo()) { sd_power_gpregret_clr(1, 0xFF); if (v) sd_power_gpregret_set(1, v); }
  else NRF_POWER->GPREGRET2 = v;
}
static void sistemaOff(uint8_t marca) {
  if (sdAttivo()) { gpregretImposta(marca); sd_power_system_off(); }
  else { NRF_POWER->GPREGRET2 = marca; NRF_POWER->SYSTEMOFF = POWER_SYSTEMOFF_SYSTEMOFF_Enter; }
  while (true) __WFE();
}

static void vServi();
static void attendi(uint32_t ms) {   // attesa che continua a svuotare il FIFO dell'IMU
  uint32_t t0 = millis();
  while (millis() - t0 < ms) { if (vAttivo) vServi(); delay(vAttivo ? 10 : 1); }
}
static void lampi(uint8_t colore, uint8_t n, uint16_t onMs, uint16_t offMs) {
  for (uint8_t i = 0; i < n; i++) { ledSet(colore); attendi(onMs); ledSet(0); if (i + 1 < n) attendi(offMs); }
}

static void dormiVasca(bool soloUsb, bool piena = false) {
  ledSet(0);
  vAttivo = false;
  if (!soloUsb) sonnoAnnuncia(piena);   // batteria quasi scarica: niente attese
  bleSpegni();
  if (flashPronta) flash.end();
  if (soloUsb) {
    i2cScrivi(REG_FIFO_CTRL5, 0x00); i2cScrivi(REG_CTRL2_G, 0x00); i2cScrivi(REG_CTRL1_XL, 0x00);
    digitalWrite(PIN_LSM6DS3TR_C_POWER, LOW);   // batteria quasi scarica: IMU spento, si riparte solo con l'USB
  } else {
    i2cScrivi(REG_FIFO_CTRL5, 0x00); i2cScrivi(REG_FIFO_CTRL3, 0x00);
    configuraTap();
    delay(50);
    attendiInt1Bassa(1000);
    nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
  }
  sistemaOff(MARCA_SLEEP);
}

// Chiude la pagina dati del codificatore: la scrive nel blocco aperto (se non c'e', ne apre uno; se la memoria e' piena
// di blocchi non confermati la registrazione si ferma: mai si sovrascrive un non confermato).
static void vChiudiPagina() {
  if (cod.nc == 0) return;
  if (!anello.haPosto()) {
    uint32_t t0 = millis();
    bool ok = anello.apri(cod.tPrimo, vMv, vTemp, 0, vSeg);
    uint32_t dt = millis() - t0;
    if (dt > statApriMax) statApriMax = dt > 65535 ? 65535 : (uint16_t)dt;
    if (!ok) { vMotivo = anello.ultimoErrore == AN_PIENA ? SWR_STOP_PIENA : SWR_STOP_ERRORE; return; }
  }
  cod.chiudi(anello.numeroPagina(), vSeg, vMv, vTemp, vFlagsProx);
  vFlagsProx &= ~(SWR_FLAG_PRIMA | SWR_FLAG_GAP);
  if (!anello.scriviPagina(cod.pag)) { vMotivo = SWR_STOP_ERRORE; return; }
  vPagineSeg++;
  cod.azzera();
}

// Quiete: stesse soglie della sospensione automatica (rotazione media < QUIETE_GYRO_DPS, gravita' entro QUIETE_ANGOLO_GRADI),
// valutate su blocchi da ~1 s; dopo QUIETE_REG_S secondi di fila la registrazione si chiude.
static void vQuiete(const int16_t *s) {
  static float ga[3], gg[3]; static int ng = 0;          // gruppo di 8 campioni (~38 ms)
  static float sa[3], sg3[3], sgm; static int nb = 0;    // blocco da ~1 s
  static float rif[3], bias[3]; static bool rifOk = false;
  static int secFermo = 0;
  for (int i = 0; i < 3; i++) { ga[i] += s[i]; gg[i] += s[3 + i]; }
  if (++ng < 8) return;
  float g2 = 0;
  for (int i = 0; i < 3; i++) {
    gg[i] /= ng;                                          // media del gruppo (LSB grezzi)
    float w = (gg[i] - bias[i]) * 0.035f;                 // dps
    g2 += w * w;
    sa[i] += ga[i] / ng / 2048.0f;
    sg3[i] += gg[i];
    ga[i] = 0; gg[i] = 0;
  }
  sgm += sqrtf(g2); nb++;
  ng = 0;
  if (nb < 26) return;
  float a[3], an = 0, gMed = sgm / nb, bm[3];
  for (int i = 0; i < 3; i++) { a[i] = sa[i] / nb; an += a[i] * a[i]; sa[i] = 0; bm[i] = sg3[i] / nb; sg3[i] = 0; }
  sgm = 0; nb = 0;
  an = sqrtf(an);
  if (an < 0.5f) return;
  for (int i = 0; i < 3; i++) a[i] /= an;
  float ang = 0;
  if (rifOk) ang = acosf(constrain(a[0] * rif[0] + a[1] * rif[1] + a[2] * rif[2], -1.0f, 1.0f)) * 57.2958f;
  if (rifOk && gMed < QUIETE_GYRO_DPS && ang < QUIETE_ANGOLO_GRADI) {
    secFermo++;
    for (int i = 0; i < 3; i++) bias[i] += 0.1f * (bm[i] - bias[i]);   // in quiete il giroscopio misura il suo bias
  } else {
    for (int i = 0; i < 3; i++) rif[i] = a[i];
    rifOk = true; secFermo = 0;
  }
  if (secFermo >= QUIETE_REG_S && !vMotivo) vMotivo = SWR_STOP_QUIETE;
}

static void vCampione(const int16_t *s, uint32_t t) {
  if (vMotivo) return;
  if (cod.nc && !cod.sta(s)) vChiudiPagina();
  if (vMotivo) return;
  cod.aggiungi(s, t);
  vCampioni++;
  vQuiete(s);
}

// Svuota il FIFO dell'IMU (6 parole da 16 bit per campione: Gx Gy Gz Ax Ay Az) e codifica i campioni
static void vServi() {
  if (vMotivo) return;
  uint8_t st[2];
  if (!i2cLeggi(REG_FIFO_STATUS1, st, 2)) { if (++vErrI2c > 100) vMotivo = SWR_STOP_ERRORE; return; }
  vErrI2c = 0;
  uint32_t tr = millis();
  if (st[1] & 0x40) {                                    // overrun: FIFO ripartito, i campioni persi si vedono dal flag e dal tempo
    vChiudiPagina();
    vFlagsProx |= SWR_FLAG_GAP;
    if (statOverrun < 255) statOverrun++;
    i2cScrivi(REG_FIFO_CTRL5, 0x00);
    i2cScrivi(REG_FIFO_CTRL5, 0x2E);
    return;
  }
  uint16_t parole = st[0] | ((st[1] & 0x0F) << 8);
  uint16_t insiemi = parole / 6;
  if (insiemi > 120) insiemi = 120;                      // al massimo ~0,6 s per chiamata
  for (uint16_t k = 0; k < insiemi && !vMotivo;) {
    uint8_t n = min((uint16_t)2, (uint16_t)(insiemi - k));
    uint8_t b[24];
    if (!i2cLeggi(REG_FIFO_OUT_L, b, 12 * n)) { if (++vErrI2c > 100) vMotivo = SWR_STOP_ERRORE; return; }
    for (uint8_t j = 0; j < n; j++, k++) {
      int16_t w[6], s[6];
      for (int i = 0; i < 6; i++) w[i] = (int16_t)(b[12 * j + 2 * i] | (b[12 * j + 2 * i + 1] << 8));
      s[0] = w[3]; s[1] = w[4]; s[2] = w[5]; s[3] = w[0]; s[4] = w[1]; s[5] = w[2];   // ax ay az gx gy gz
      uint32_t eta = ((uint32_t)(insiemi - 1 - k) * 4800UL + 500) / 1000;                // ms prima della lettura
      vCampione(s, tr - eta);
    }
  }
}

static bool vImuAvvia() {
  i2cScrivi(REG_CTRL3_C, 0x01);                          // reset software: tutto ai valori di default
  delay(20);
  i2cScrivi(REG_CTRL3_C, 0x44);                          // BDU + auto-incremento indirizzo
  i2cScrivi(REG_FIFO_CTRL5, 0x00);                       // FIFO in bypass (svuotato)
  i2cScrivi(REG_FIFO_CTRL3, 0x09);                       // giroscopio e accelerometro nel FIFO, senza decimazione
  i2cScrivi(REG_CTRL1_XL, 0x54);                         // 208 Hz, +-16 g
  i2cScrivi(REG_CTRL2_G, 0x58);                          // 208 Hz, +-1000 dps
  i2cScrivi(REG_FIFO_CTRL5, 0x2E);                       // FIFO continuo a 208 Hz
  uint8_t v = 0;
  return i2cLeggi(REG_CTRL1_XL, &v, 1) && v == 0x54;
}

static void vAzzera() {
  bool vuota = true;                                                           // gia' vuota? (tutti i blocchi liberi)
  anello.inizia(&flash, tagId); anello.scansiona(); vuota = (anello.nLiberi == SWR_N_BLOCCHI);
  if (vuota) { lampi(LED_B, 1, 300, 0); dormiVasca(false); }
  uint8_t n = contaTocchi(4000, 600, 900, 2, true);                           // conferma: 2 tocchi mentre il LED rosso lampeggia
  if (n >= 2) {
    ledSet(LED_R);
    seqBasePrimaDiCancellare(anello.maxSeq);
    flash.eraseChip();                                                         // alcuni secondi
    ledSet(0);
    lampi(LED_B, 3, 150, 150);
  }
  dormiVasca(false);
}

static void modalitaVasca() {
  inVasca = true;
  tagId = NRF_FICR->DEVICEID[0];
  pinMode(LED_RED, OUTPUT); pinMode(LED_GREEN, OUTPUT); pinMode(LED_BLUE, OUTPUT);
  ledSet(0);
  pinMode(PIN_NCHG, INPUT_PULLUP);
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
  if (imuMutoAlRisveglio) { lampi(LED_R, 10, 60, 60); dormiVasca(false); }
  vcalCarica();
  vMv = batteriaMv();
  ultimaMv = vMv;
  if (vMv > 0 && vMv < BAT_MIN_AVVIO_MV) { lampi(LED_R, 3, 200, 200); dormiVasca(false); }   // batteria troppo scarica: non si registra
  if (!memInit()) { lampi(LED_R, 10, 60, 60); dormiVasca(false); }
  if (tocchiExtra >= 6) vAzzera();                                                           // 2 tocchi, blu, 6 tocchi: azzeramento
  EsitoScansione es = memScansiona();
  if (es == SC_FORMATO1) {                                                                   // dati del formato 1: NON si cancellano da soli
    lampi(LED_R | LED_B, 4, 250, 250);                                                       // 4 lampi viola: scaricare con DUMP, poi azzerare a tocchi
    dormiVasca(false);
  }
  if (es == SC_ESTRANEA) {                                                                   // contenuto non riconosciuto: MAI cancellato da solo
    lampi(LED_R | LED_B, 4, 250, 250);                                                       // come il formato 1: scaricare con DUMP, poi azzerare
    dormiVasca(false);
  }
  bleIniz(true);                                                                             // BLE acceso anche in registrazione
  vSeg = 0;
  if (anello.maxSeq && anello.ultimo >= 0) {                                                 // numero del segmento = quello dell'ultimo blocco + 1
    uint8_t g[2];
    if (anello.leggi(anello.ultimo, 12, g, 2)) vSeg = (g[0] | (g[1] << 8)) + 1;
  }
  vPagineSeg = 0; vCampioni = 0;
  vTemp = tempDie();
  vInizioMs = millis();
  // il segmento comincia sempre in un blocco nuovo
  if (!anello.apri(millis(), vMv, vTemp, 0, vSeg)) {
    bool piena = anello.ultimoErrore == AN_PIENA;
    lampi(LED_R, piena ? 5 : 10, piena ? 150 : 60, piena ? 150 : 60);
    dormiVasca(false, piena);                                                                // memoria piena: serve conferma dal display o azzeramento
  }
  uint8_t p[SWR_PAGINA];
  memset(p, 0xFF, sizeof(p));
  p[16] = SWR_ODR_X10 & 0xFF; p[17] = SWR_ODR_X10 >> 8;
  p[18] = SWR_ACC_UG_LSB & 0xFF; p[19] = SWR_ACC_UG_LSB >> 8;
  p[20] = SWR_GIRO_MDPS_LSB; p[21] = 0;
  memset(p + 22, 0, 6);                                  // bias del giroscopio non misurato (si stima a casa)
  p[28] = causaReset; p[29] = tocchiExtra;
  memset(p + 30, 0, 8); strncpy((char *)p + 30, VER_NUM, 7);
  swrIntestazione(p, SWR_T_SEGMENTO, SWR_FORMATO, anello.numeroPagina(), millis(), vMv, vTemp, 0, vSeg);
  if (!anello.scriviPagina(p)) { lampi(LED_R, 10, 60, 60); dormiVasca(false); }
  vPagineSeg++;
  if (!vImuAvvia()) { lampi(LED_R, 10, 60, 60); dormiVasca(false); }
  vAttivo = true;
  lampi(LED_G, 3, 150, 150);                             // registrazione avviata (nel frattempo il FIFO viene svuotato)

  uint32_t tBat = millis(), tLed = millis(), tFifo = 0;
  uint8_t sotto = 0;
  while (!vMotivo) {
    uint32_t ora = millis();
    if (ora - tFifo >= 20) {                             // FIFO (1,6 s di capienza): servito almeno ogni 20 ms quando il loop gira veloce
      if (tFifo) { uint32_t gap = ora - tFifo; if (gap > statGapMax) statGapMax = gap > 65535 ? 65535 : (uint16_t)gap; }
      tFifo = ora;
      vServi();
    }
    syncServi();                                         // invio a pezzi dei blocchi: non blocca la registrazione
    annuncioAggiorna(false);
    statoSyncServi(false);
    ora = millis();
    if (ora - tBat >= 5000) {
      tBat = ora;
      vMv = batteriaMv(); vTemp = tempDie(); ultimaMv = vMv;
      if (vMv > 0 && vMv < BAT_STOP_MV) { if (++sotto >= 3 || vMv < 3100) vMotivo = SWR_STOP_BATTERIA; } else sotto = 0;
    }
    if (!vMotivo && vbusOra()) vMotivo = SWR_STOP_USB;   // USB collegata: chiude e riparte in modalita' normale
    if (ora - tLed >= 8000 && !vMotivo) {                // un lampo ogni 8 s
      tLed = ora;
      if (vMv > 0 && vMv < 3500) lampi(LED_R, 1, 30, 0);
      else if (anello.pctNonConfermata() >= 80) lampi(LED_R | LED_G, 2, 30, 100);   // quasi tutta la memoria e' non confermata
      else lampi(LED_G, 1, 30, 0);
    }
    delay(syncAttivo ? 2 : 40);
  }
  // chiusura sicura: pagina parziale, pagina di chiusura, poi sospensione
  vAttivo = false;
  uint8_t motivo = vMotivo;
  vMotivo = 0;
  vChiudiPagina();
  if (vMotivo) motivo = vMotivo;                         // memoria piena o errore flash durante la scrittura dell'ultima pagina
  vMotivo = 0;
  bool posto = anello.haPosto();
  if (!posto && motivo != SWR_STOP_PIENA && motivo != SWR_STOP_ERRORE)
    posto = anello.apri(millis(), vMv, vTemp, 0, vSeg);  // la chiusura va in un blocco nuovo se l'ultimo e' pieno
  if (posto) {
    memset(p, 0xFF, sizeof(p));
    memcpy(p + 16, &vCampioni, 4); memcpy(p + 20, &vPagineSeg, 4);
    p[24] = statGapMax & 0xFF; p[25] = statGapMax >> 8;        // misure per la verifica dei tempi
    p[26] = statOverrun;
    p[27] = statApriMax & 0xFF; p[28] = statApriMax >> 8;
    p[29] = statConfermati & 0xFF; p[30] = statConfermati >> 8;
    swrIntestazione(p, SWR_T_CHIUSURA, motivo, anello.numeroPagina(), millis(), vMv, vTemp, 0, vSeg);
    anello.scriviPagina(p);
  }
  anello.chiudi();                                       // da qui il blocco e' "da validare" e si puo' inviare
  if (motivo == SWR_STOP_PIENA) lampi(LED_R, 5, 150, 150);
  else if (motivo == SWR_STOP_BATTERIA) lampi(LED_R, 3, 200, 200);
  else if (motivo == SWR_STOP_ERRORE) lampi(LED_R, 10, 60, 60);
  if (motivo == SWR_STOP_USB) {                          // riavvio: con VBUS presente al boot si entra in modalita' normale (seriale, BLE)
    lampi(LED_G | LED_B, 2, 150, 150);
    bleSpegni();
    if (flashPronta) flash.end();
    gpregretImposta(0);
    NVIC_SystemReset();
  }
  dormiVasca(motivo == SWR_STOP_BATTERIA, motivo == SWR_STOP_PIENA);
}

// ================= Comandi da seriale (modalita' normale, con USB): DUMP, MEM, ERASE =================
static void comandiSeriale() {
  static char buf[24]; static uint8_t n = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c != '\n') { if (n < sizeof(buf) - 1) buf[n++] = c; continue; }
    buf[n] = 0; n = 0;
    if (!strcmp(buf, "DUMP") || !strcmp(buf, "MEM") || !strcmp(buf, "ERASE")) {
      if (!memInit()) { Serial.println("X flash"); continue; }
      if (!strcmp(buf, "MEM")) {
        if (anelloOk)   // formato 2 (o vuota)
          Serial.printf("K mem formato3 da_validare %u confermati %u liberi %u anomali %u seq %lu\n", anello.nDaValidare, anello.nConfermati,
                        anello.nLiberi, anello.nAnomali, (unsigned long)anello.maxSeq);
        else
          Serial.printf("K mem %lu %lu\n", (unsigned long)memPrimaLibera(), (unsigned long)memPagine);   // formato 1: pagine usate / totali
      } else if (!strcmp(buf, "ERASE")) {
        seqBasePrimaDiCancellare(anello.maxSeq);
        flash.eraseChip();
        anello.inizia(&flash, tagId); anello.azzeraRam(); anelloOk = true; formatoVecchio = false;
        { uint32_t b = seqBaseCarica(); if (anello.maxSeq < b) anello.maxSeq = b; }
        Serial.println("K erase ok");
      } else if (anelloOk) {   // formato 2: i blocchi non vuoti, in ordine fisico (si riordinano per seq lato PC), 4096 byte ciascuno
        uint16_t nb = 0;
        for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++) if (anello.st[i] != BL_LIBERO) nb++;
        dumpInCorso = true;
        Serial.printf("SWR2 %u\n", nb);
        static uint8_t blocco[1024];
        for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++) {
          if (anello.st[i] == BL_LIBERO) continue;
          for (uint16_t k = 0; k < SWR_BLOCCO_BYTE; k += sizeof(blocco)) {
            flash.readBuffer((uint32_t)i * SWR_BLOCCO_BYTE + k, blocco, sizeof(blocco));
            Serial.write(blocco, sizeof(blocco));
          }
        }
        Serial.printf("\nEND %u\n", nb);
        Serial.flush();
        dumpInCorso = false;
      } else {                 // formato 1 (flash vecchia): pagine fino alla prima libera, come in 0.5.x
        uint32_t usate = memPrimaLibera();
        dumpInCorso = true;
        Serial.printf("SWR1 %lu\n", (unsigned long)usate);
        static uint8_t blocco[1024];
        for (uint32_t p = 0; p < usate; p += 4) {
          uint32_t np = min((uint32_t)4, usate - p);
          flash.readBuffer(p * SWR_PAGINA, blocco, np * SWR_PAGINA);
          Serial.write(blocco, np * SWR_PAGINA);
        }
        Serial.printf("\nEND %lu\n", (unsigned long)usate);
        Serial.flush();
        dumpInCorso = false;
      }
    } else if (buf[0]) {
      Serial.println("X comando");
    }
  }
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
  uint8_t marca = NRF_POWER->GPREGRET2;                      // marca lasciata prima di System OFF (RESETREAS e' azzerato dal bootloader)
  NRF_POWER->GPREGRET2 = 0;
  bool vbusAvvio = NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk;
  if ((marca == MARCA_SLEEP || (marca & 0xF0) == MARCA_FALSO) && !vbusAvvio && causaReset != 7) causaReset = 1;   // risveglio da doppio tap

  bool quattroTap = false;
  if (causaReset == 1) quattroTap = risveglioQuattroTap();   // se non arrivano 4 tap non ritorna: torna a dormire
  // 4 tocchi SENZA USB = modalita' vasca (BLE mai avviato, non ritorna). Con l'USB collegata: modalita' normale.
  if (quattroTap && !vbusAvvio) modalitaVasca();

  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 2000) delay(10);

  pinMode(LED_RED, OUTPUT); pinMode(LED_GREEN, OUTPUT); pinMode(LED_BLUE, OUTPUT);
  ledScrivi(LED_RED, HIGH); ledScrivi(LED_GREEN, HIGH); ledScrivi(LED_BLUE, HIGH);
  pinMode(PIN_NCHG, INPUT_PULLUP);
  pinMode(PIN_CHARGING_CURRENT, OUTPUT); digitalWrite(PIN_CHARGING_CURRENT, LOW);   // P0.13 basso: carica a 100 mA (resta impostato anche in System OFF)
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);

  const char *nomi[] = {"accensione", "doppio tap", "?", "watchdog", "?", "software", "lockup", "USB", "pin reset"};
  logRiga("boot %s, causa %s (RESETREAS 0x%lX)", VERSIONE, nomi[causaReset], (unsigned long)rr);
  logRiga("marca %02X vbus %d", marca, vbusAvvio);
  if (quattroTap) logRiga("risveglio 4 tap");
  if (*(volatile const char *)marcatoreVersione != 'S' || *(volatile const char *)marcatoreScheda != 'S') logRiga("?");   // tiene il marcatore nel binario (altrimenti il linker lo scarta)

  bleIniz(false);                       // BLE: 2 collegamenti, servizi 7a1e0001 (pagina) e 7a1e0101 (display), annuncio di sincronizzazione
  if (memInit()) {                      // anche in modalita' normale la flash si scansiona: il display puo' scaricare con l'USB collegata
    EsitoScansione es = memScansiona();
    logRiga("memoria: %s, da validare %u, confermati %u, liberi %u, seq %lu", es == SC_OK ? "formato 3" : es == SC_FORMATO1 ? "FORMATO 1 (non toccata)" : "estranea",
            anello.nDaValidare, anello.nConfermati, anello.nLiberi, (unsigned long)anello.maxSeq);
  } else logRiga("flash non risponde");

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
  if (vbusPresente()) {                                  // alimentata dall'USB (PC o caricatore): niente sospensione automatica
    static bool avvisatoUsb = false;
    if (!avvisatoUsb) { avvisatoUsb = true; logRiga("USB collegata: niente sospensione"); }
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
      notificaTutti(carDati, p, 16);
      controllaInattivita(ora);
    }
  }
  if (ora - ultimoStato >= 1000) {         // 1 Hz
    ultimoStato = ora;
    if (!imuOk) {                          // riprova l'init e lo segnala
      imuOk = imuInit();
      logRiga(imuOk ? "IMU ok (ripristinato)" : "IMU NON risponde");
    } else if (Serial && !dumpInCorso) {
      Serial.printf("acc %d %d %d | gyro %d %d %d\n", acc[0], acc[1], acc[2], gir[0], gir[1], gir[2]);
    }
    aggiornaStato(false);
  }
  eseguiComandi();
  if (Serial) comandiSeriale();
  servizioOta();
  inviaLog();
  syncServi();                              // sincronizzazione con il display (anche con l'USB collegata)
  annuncioAggiorna(false);
  statoSyncServi(false);
  if (!Bluefruit.connected() && ora - ultimoLed >= 500) {   // blu lampeggiante = advertising
    ultimoLed = ora;
    static bool bluAcceso = false;   // blu lampeggiante = advertising (solo con l'USB: ledScrivi)
    bluAcceso = !bluAcceso;
    ledScrivi(LED_BLUE, bluAcceso ? LOW : HIGH);
  }
  delay(1);
}
