// FQBN: esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=4M
//   (partizioni in partitions.csv accanto allo sketch: due app da 1 MB per l'OTA,
//   LittleFS sulla partizione "spiffs" di circa 1,9 MB)
// Test dei collegamenti del tag: bus I2C, BMI160, pin INT1 e livello batteria.
// Collegamenti in hardware/schema.md. Uscita sulla seriale USB a 115200.
// Sonno profondo dopo INATTIVITA_MS senza movimento (se nessuna pagina è collegata
// via BLE e nessun PC via USB); risveglio dal BMI160 con l'interrupt any-motion su INT1.
// Stato del tag una volta al secondo (batteria, USB, sensore, causa avvio): sia su BLE
// (caratteristica 7a1e0003) sia sulla seriale (riga "S,...") per la pagina di analisi.
// Registrazione di sessioni sulla flash (LittleFS, /r001.bin ...) avviata con doppio tap sul
// tag e chiusa con triplo tap; elenco, scaricamento e cancellazione via BLE (7a1e0004/5) o USB.
// Formato file: record da 16 byte little-endian (campione o evento, vedi scriviCampione),
// un campione ogni lettura (100 Hz), accelerometro a ±16 g (2048 LSB/g), giroscopio a ±2000 °/s.
// Aggiornamento del firmware via BLE (OTA, 7a1e0006) con ritorno automatico alla versione
// precedente: il bootloader del core ha il rollback attivo, la nuova app resta "in prova"
// finché non è confermata (vedi confermaAggiornamento).
// Versione numerica MAJOR.MINOR.PATCH (anche 4 numeri), gestita a mano: AUMENTARLA A OGNI RILASCIO.
// Serve ai controlli dell'OTA (niente aggiornamento alla stessa versione o a una precedente).
#define FIRMWARE_VERSIONE "0.4.3"
#if __has_include("versione.h")
#include "versione.h"  // facoltativo, scritto dalla CI: #define FIRMWARE_BUILD "2026-10-25.abc1234"
#endif
#ifndef FIRMWARE_BUILD
#define FIRMWARE_BUILD "locale"
#endif
// Marcatore cercato nel binario (dalla CI e dall'OTA) per riconoscere il firmware e la sua versione
extern "C" __attribute__((used)) const char MARCATORE_VERSIONE[] = "SWIMTAG_VER=" FIRMWARE_VERSIONE ";";
#include <Wire.h>
#include <esp_ota_ops.h>
#include <esp_sleep.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <LittleFS.h>

const int PIN_SDA = 8;
const int PIN_SCL = 9;
const int PIN_INT1 = 4;
const int PIN_BATTERIA = 1;  // partitore 100k/100k da BAT+, se montato
const int PIN_VBUS = 2;      // partitore 100k/100k dal pin 5V (USB), se montato
const uint16_t VBUS_PRESENTE_MV = 4000;  // oltre: alimentazione USB collegata (in carica)

const uint8_t BMI160_ADDR = 0x68;
const uint8_t REG_CHIP_ID = 0x00;   // atteso 0xD1
const uint8_t REG_GYR_DATA = 0x0C;  // 6 byte giroscopio + 6 byte accelerometro
const uint8_t REG_PMU_STATUS = 0x03;
const uint8_t REG_INT_STATUS_0 = 0x1C;  // bit 5: single tap
const uint8_t REG_INT_TAP_0 = 0x63;     // durate del motore tap
const uint8_t REG_INT_TAP_1 = 0x64;     // bit 0-4: soglia (62,5 mg per unità a ±2 g, 500 mg a ±16 g)
const uint8_t REG_CMD = 0x7E;
const uint8_t REG_ACC_CONF = 0x40;
const uint8_t REG_ACC_RANGE = 0x41;    // 0x03 = ±2 g, 0x0C = ±16 g
const uint8_t REG_GYR_CONF = 0x42;
const uint8_t REG_INT_EN_0 = 0x50;      // bit 0-2: any-motion sugli assi x, y, z
const uint8_t REG_INT_OUT_CTRL = 0x53;  // configurazione elettrica dei pin INT
const uint8_t REG_INT_LATCH = 0x54;
const uint8_t REG_INT_MAP_0 = 0x55;     // bit 2: any-motion su INT1
const uint8_t REG_INT_MAP_2 = 0x57;     // bit 5: single tap su INT2 (non collegato, serve ad aggiornare lo stato)
const uint8_t REG_INT_MOTION_0 = 0x5F;  // durata: campioni consecutivi oltre soglia - 1
const uint8_t REG_INT_MOTION_1 = 0x60;  // soglia: 3,91 mg per unità a ±2 g

const uint32_t INATTIVITA_MS = 120000;  // 2 minuti fermo: sonno profondo
const float SOGLIA_MOVIMENTO_G = 0.10;  // come la "calma" del display
const float SOGLIA_MOVIMENTO_DPS = 20;
const uint8_t SOGLIA_RISVEGLIO = 20;    // circa 80 mg

// Letture a 100 Hz; accelerometro ±16 g = 2048 LSB/g; giroscopio ±2000 °/s = 16,4 LSB/(°/s)
const uint32_t PERIODO_US = 10000;
const float ACC_LSB_G = 2048.0;
const int16_t FONDO_SCALA_G = 16;
const int16_t FREQ_HZ = 100;

// Tap: 0 = rilevamento software sui campioni a 100 Hz (predefinito); 1 = motore tap del BMI160.
// Il single tap hardware non ha mai attivato il bit 5 di INT_STATUS_0 sul tag reale (probabilmente
// serve mapparlo su un pin), quindi si usa il software.
#define TAP_HARDWARE 0
// Software: tap = "jerk", cioè modulo della differenza vettoriale tra due campioni consecutivi
// di accelerazione (a 100 Hz, 10 ms). Un colpetto dà salti di molti g in pochi campioni, una
// bracciata o un'inclinazione lenta solo frazioni di g. Alzare se scatta a vuoto, abbassare se
// i colpetti leggeri non vengono visti.
const float TAP_JERK_G = 0.8;
const float TAP_GIRO_MAX_DPS = 300;        // oltre questa velocità angolare è un movimento ampio, non un colpetto
const uint32_t TAP_RIFIUTO_MS = 120;       // dopo un tap software, ignora i successivi per tanto
const uint8_t TAP_SOGLIA = 1;              // 1 x 500 mg (a ±16 g) = 500 mg di variazione tra campioni, come prima
const float TAP_SOGLIA_SW_G = 0.6;         // solo software: picco di |a| rispetto alla media mobile
const uint32_t TAP_MIN_MS = 120;           // tap più ravvicinati: rimbalzo, ignorati
const uint32_t TAP_MAX_MS = 600;           // oltre: nuova sequenza
const uint32_t TAP_CHIUSURA_MS = 800;      // senza tap per tanto: la sequenza è chiusa

// Registrazione
const int PIN_LED = 48;                    // WS2812 della SuperMini ESP32-S3
const uint32_t LIBERI_MIN = 16384;         // sotto questo spazio libero la registrazione si chiude
const size_t DIM_BUFFER = 512;
enum : int16_t { EV_INIZIO_TAP = 1, EV_FINE_TAP = 2, EV_FINE_PIENA = 3, EV_INIZIO_CMD = 4, EV_FINE_CMD = 5 };

bool scrivi(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(BMI160_ADDR);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool leggi(uint8_t reg, uint8_t *buf, size_t n) {
  Wire.beginTransmission(BMI160_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(BMI160_ADDR, (uint8_t)n) != n) return false;
  for (size_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

bool sensoreOk = false;
bool busBloccato = false;  // SDA ancora basso dopo lo sblocco (vedi sbloccaI2C)
uint32_t ultimoMovimento = 0;

// Prepara il BMI160 per il risveglio e mette l'ESP32 in sonno profondo
void dormi() {
  Serial.println("Nessun movimento: sonno profondo, risveglio dal BMI160 su INT1");
  Serial.flush();
  BLEDevice::deinit(false);
  scrivi(REG_CMD, 0x14);           // giroscopio sospeso
  delay(80);
  scrivi(REG_ACC_RANGE, 0x03);     // ±2 g in sonno: la soglia di risveglio resta 3,91 mg per unità
  scrivi(REG_ACC_CONF, 0x86);      // accelerometro a basso consumo: 25 Hz, senza media
  scrivi(REG_CMD, 0x12);           // accelerometro in modalità low power
  delay(10);
  scrivi(REG_INT_MOTION_0, 0x00);  // basta un campione oltre soglia
  scrivi(REG_INT_MOTION_1, SOGLIA_RISVEGLIO);
  scrivi(REG_INT_OUT_CTRL, 0x0A);  // INT1 attivo, push-pull, attivo alto
  scrivi(REG_INT_LATCH, 0x0F);     // resta alto finché non viene azzerato
  scrivi(REG_INT_MAP_0, 0x04);     // any-motion su INT1
  scrivi(REG_INT_EN_0, 0x07);      // any-motion su x, y, z
  scrivi(REG_CMD, 0xB1);           // azzera eventuali interrupt già memorizzati
  delay(50);
  esp_sleep_enable_ext0_wakeup((gpio_num_t)PIN_INT1, 1);
  esp_deep_sleep_start();
}

// Al risveglio: interrupt spenti (i sensori si accendono e si configurano in avviaSensore)
void preparaSensoriNormali() {
  scrivi(REG_INT_EN_0, 0x00);
  scrivi(REG_CMD, 0xB1);
  scrivi(REG_INT_MAP_0, 0x00);
}

// Fondo scala e frequenze, a sensori ACCESI: da sospeso il BMI160 perde le scritture ravvicinate
// (succedeva: restava a ±2 g e la pagina leggeva 8 g da fermo). Riletto e riscritto se non torna.
bool configuraFondoScala() {
  for (int tentativo = 0; tentativo < 5; tentativo++) {
    scrivi(REG_ACC_RANGE, 0x0C);  // ±16 g (2048 LSB/g)
    delayMicroseconds(500);
    scrivi(REG_GYR_CONF, 0x29);   // giroscopio 200 Hz, filtro normale (±2000 °/s resta il predefinito)
    delayMicroseconds(500);
    scrivi(REG_ACC_CONF, 0x29);   // 200 Hz, filtro normale (si legge a 100 Hz)
    delayMicroseconds(500);
    uint8_t range = 0, conf = 0;
    if (leggi(REG_ACC_RANGE, &range, 1) && leggi(REG_ACC_CONF, &conf, 1) && range == 0x0C && conf == 0x29) {
      Serial.println("BMI160: fondo scala ±16 g verificato");
      return true;
    }
    delay(5);
  }
  Serial.println("BMI160: fondo scala ±16 g NON impostato");
  return false;
}

// Motore tap: single tap, memorizzato (latch) finché non si azzera con il comando 0xB1
void configuraTap() {
#if TAP_HARDWARE
  scrivi(REG_INT_TAP_0, 0x00);          // shock 50 ms, quiet 30 ms
  scrivi(REG_INT_TAP_1, TAP_SOGLIA & 0x1F);
  scrivi(REG_INT_LATCH, 0x0F);
  scrivi(REG_INT_MAP_2, 0x20);          // single tap su INT2 (non collegato) perché lo stato si aggiorni
  scrivi(REG_INT_EN_0, 0x20);           // bit 5: single tap
  scrivi(REG_CMD, 0xB1);
#endif
}

// Sblocco del bus I2C: se un dispositivo tiene SDA basso (trasferimento interrotto da un reset),
// si danno fino a 16 impulsi su SCL finché SDA torna alto, poi una condizione di STOP.
// Da chiamare con Wire non attivo (prima di Wire.begin, o dopo Wire.end).
void sbloccaI2C() {
  pinMode(PIN_SDA, INPUT_PULLUP);
  pinMode(PIN_SCL, OUTPUT_OPEN_DRAIN);
  digitalWrite(PIN_SCL, HIGH);
  delayMicroseconds(10);
  if (digitalRead(PIN_SDA)) {  // bus libero
    pinMode(PIN_SCL, INPUT);
    busBloccato = false;
    return;
  }
  int impulsi = 0;
  while (!digitalRead(PIN_SDA) && impulsi < 16) {
    digitalWrite(PIN_SCL, LOW);
    delayMicroseconds(10);
    digitalWrite(PIN_SCL, HIGH);
    delayMicroseconds(10);
    impulsi++;
  }
  busBloccato = !digitalRead(PIN_SDA);
  if (!busBloccato) {  // STOP: SDA da basso ad alto con SCL alto
    digitalWrite(PIN_SCL, LOW);
    pinMode(PIN_SDA, OUTPUT_OPEN_DRAIN);
    digitalWrite(PIN_SDA, LOW);
    delayMicroseconds(10);
    digitalWrite(PIN_SCL, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_SDA, HIGH);
    delayMicroseconds(10);
    Serial.printf("I2C: bus sbloccato dopo %d impulsi\n", impulsi);
  } else {
    Serial.println("I2C: SDA ancora basso (corto o sensore guasto)");
  }
  pinMode(PIN_SCL, INPUT);
  pinMode(PIN_SDA, INPUT);
}

// Identifica e configura il BMI160 (Wire già avviato); true se pronto
bool avviaSensore() {
  uint8_t id = 0;
  if (!leggi(REG_CHIP_ID, &id, 1)) {
    Serial.println("BMI160: NON risponde a 0x68 (controlla SDA/SCL, alimentazione, SAO a GND, CS a 3V3)");
    return false;
  }
  Serial.printf("BMI160 chip ID: 0x%02X %s\n", id, id == 0xD1 ? "(OK)" : "(ATTESO 0xD1)");
  if (id != 0xD1) return false;

  // Accende accelerometro e giroscopio in modalità normale
  preparaSensoriNormali();
  scrivi(REG_CMD, 0x11);
  delay(10);
  scrivi(REG_CMD, 0x15);
  delay(100);
  if (!configuraFondoScala()) return false;
  configuraTap();
  uint8_t pmu = 0;
  leggi(REG_PMU_STATUS, &pmu, 1);
  Serial.printf("Stato alimentazione sensori: 0x%02X %s\n", pmu, pmu == 0x14 ? "(OK)" : "(atteso 0x14)");
  ultimoMovimento = millis();
  return true;
}

// Dopo letture ripetutamente fallite: sblocco, riavvio di Wire e riconfigurazione (circa 120 ms)
uint8_t lettureFallite = 0;
void recuperaI2C() {
  Serial.println("I2C: letture fallite, sblocco del bus e riconfigurazione");
  Wire.end();
  sbloccaI2C();
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);
  lettureFallite = 0;
  sensoreOk = avviaSensore();
}

// Servizio GATT per la pagina Web Bluetooth (contratto fisso, la pagina lo usa già)
#define UUID_SERVIZIO "7a1e0001-5b1d-4c8e-9f3a-1d2c3b4a5e60"
#define UUID_DATI "7a1e0002-5b1d-4c8e-9f3a-1d2c3b4a5e60"
// Stato (READ+NOTIFY, 1 Hz e a ogni inizio/fine registrazione), 18 byte little-endian:
// uint16 batteria in mV; uint8 flag (bit0 = USB con PC, bit1 = sensore ok, bit2 = in
// registrazione, bit3 = aggiornamento OTA in corso, bit4 = accelerometro a ±16 g, sempre 1, bit5 = alimentazione USB presente da GPIO 2); uint8 causa avvio (0 accensione, 1 risveglio dal BMI160, 2 panic, 3 watchdog, 4 brownout, 5 riavvio software, 6 altro);
// uint32 millis; uint32 byte liberi; uint16 numero di file; uint16 secondi di registrazione;
// uint16 tensione del pin 5V in mV (partitore su GPIO 2)
#define UUID_STATO "7a1e0003-5b1d-4c8e-9f3a-1d2c3b4a5e60"
// Comandi di testo (WRITE) e risposte (NOTIFY, primo byte = tipo: L Z D E K X)
#define UUID_COMANDI "7a1e0004-5b1d-4c8e-9f3a-1d2c3b4a5e60"
#define UUID_RISPOSTE "7a1e0005-5b1d-4c8e-9f3a-1d2c3b4a5e60"
// OTA: scritture (WRITE e WRITE_NR) = uint32 offset LE + dati; versione (READ) = testo ASCII
#define UUID_OTA "7a1e0006-5b1d-4c8e-9f3a-1d2c3b4a5e60"
#define UUID_VERSIONE "7a1e0007-5b1d-4c8e-9f3a-1d2c3b4a5e60"
BLECharacteristic *caratteristicaDati = nullptr;
BLECharacteristic *caratteristicaStato = nullptr;
BLECharacteristic *caratteristicaRisposte = nullptr;
BLEServer *serverBle = nullptr;
uint8_t causaAvvio = 0;
volatile bool clienteConnesso = false;
bool bleAvviato = false;          // annuncio partito (serve alla conferma dell'aggiornamento)
volatile bool otaAttivo = false;  // aggiornamento in corso (vedi sezione OTA)
BLEAdvertising *annuncio = nullptr;

// Annuncio per il display (firmware/display-prova), che lo riceve senza collegarsi:
// flag + nome "SwimTag" + dati produttore (0xFFFF = sperimentale):
// 1 byte contatore, poi int16 little-endian ax, ay, az, gx, gy, gz. Per non riprogrammare il
// display l'accelerazione resta a 16384 LSB/g (valori a 2048 LSB/g x 8, saturati a ±32767).
// L'UUID del servizio va nella risposta alla scansione per lasciare spazio ai dati.
void aggiornaAnnuncio(uint8_t contatore, const int16_t *assi) {
  uint8_t produttore[15] = {0xFF, 0xFF, contatore};
  memcpy(produttore + 3, assi, 12);
  String md;
  md.concat((const char *)produttore, sizeof(produttore));
  BLEAdvertisementData dati;
  dati.setFlags(0x06);  // general discoverable, solo BLE
  dati.setName("SwimTag");
  dati.setManufacturerData(md);
  annuncio->setAdvertisementData(dati);
}

class CallbackServer : public BLEServerCallbacks {
#if defined(CONFIG_NIMBLE_ENABLED)
  // Chiede al client un intervallo di collegamento breve (15-30 ms) per le notifiche a 25 Hz
  void onConnect(BLEServer *server, ble_gap_conn_desc *desc) override {
    server->updateConnParams(desc->conn_handle, 12, 24, 0, 400);  // unità 1,25 ms; timeout 4 s
    onConnect(server);
  }
#endif
  void onConnect(BLEServer *server) override {
    clienteConnesso = true;
    // Riprende l'annuncio anche con un client collegato: il display fa scansione per RSSI
    BLEDevice::startAdvertising();
  }
  void onDisconnect(BLEServer *server) override {
    clienteConnesso = false;
    BLEDevice::startAdvertising();
  }
};

// Coda dei comandi ricevuti via BLE: la callback li accoda, li esegue il loop
String codaComandi[4];
volatile uint8_t codaTesta = 0, codaCoda = 0;

class CallbackComandi : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    uint8_t succ = (codaTesta + 1) & 3;
    if (succ == codaCoda || v.length() == 0 || v.length() > 80) return;  // coda piena: scartato
    codaComandi[codaTesta] = v;
    codaTesta = succ;
  }
};

// ---------- LED RGB (macchina a stati non bloccante, luminosità massima 40/255) ----------
// Priorità: errore > OTA > lampi di evento > lampi periodici > stato di fondo (USB).
// Le tensioni sono quelle lette a 1 Hz da inviaStato (mvBatt, mvVbusLetto).
struct {
  uint8_t r, g, b, rimasti;
  bool acceso;
  uint32_t t;
  uint16_t msAcceso, msSpento;
} led = {0, 0, 0, 0, false, 0, 150, 150};
uint16_t mvBatt = 0, mvVbusLetto = 0;
uint32_t ledUltimo = 0xFFFFFFFFu;    // ultimo colore scritto (0xRRGGBB): evita scritture inutili

// n lampi del colore dato; il primo parte subito
void ledLampi(uint8_t r, uint8_t g, uint8_t b, uint8_t n, uint16_t msAcceso = 150, uint16_t msSpento = 150) {
  led = {r, g, b, n, false, (uint32_t)(millis() - msSpento), msAcceso, msSpento};
}

// Lampo bianco breve per ogni tap contato (non interrompe un'altra sequenza in corso)
void ledTap() {
  if (!led.rimasti) ledLampi(40, 40, 40, 1, 40, 0);
}

void ledScrivi(uint8_t r, uint8_t g, uint8_t b) {
  uint32_t c = ((uint32_t)r << 16) | ((uint32_t)g << 8) | b;
  if (c == ledUltimo) return;
  ledUltimo = c;
  rgbLedWrite(PIN_LED, r, g, b);
}

void ledAggiorna(bool inRegistrazione) {
  uint32_t ora = millis();
  // 1. errore (sensore assente o bus bloccato): rosso rapido, 5 Hz, per sempre
  if (!sensoreOk || busBloccato) {
    if ((ora / 100) & 1) ledScrivi(0, 0, 0); else ledScrivi(40, 0, 0);
    return;
  }
  // 2. OTA in corso: viola lampeggiante a 2 Hz
  if (otaAttivo) {
    if ((ora / 250) & 1) ledScrivi(0, 0, 0); else ledScrivi(30, 0, 30);
    return;
  }
  // 3. lampi di evento (avvio, tap, inizio/fine registrazione)
  if (led.rimasti) {
    if (!led.acceso && ora - led.t >= led.msSpento) {
      ledScrivi(led.r, led.g, led.b);
      led.acceso = true;
      led.t = ora;
    } else if (led.acceso && ora - led.t >= led.msAcceso) {
      ledScrivi(0, 0, 0);
      led.acceso = false;
      led.t = ora;
      led.rimasti--;
    }
    return;
  }
  // 4. lampi periodici: registrazione (rosso tenue, 3 s), client BLE (azzurro, 5 s), batteria scarica (arancio, 10 s)
  bool usb = mvVbusLetto > VBUS_PRESENTE_MV;
  if (inRegistrazione) {
    if (ora % 3000 < 40) { ledScrivi(10, 0, 0); return; }
  } else if (clienteConnesso && ora % 5000 < 60) {
    ledScrivi(0, 25, 30);
    return;
  }
  if (!usb && mvBatt > 2500 && mvBatt < 3400 && ora % 10000 < 80) {  // partitore montato e batteria sotto 3,4 V
    ledScrivi(40, 15, 0);
    return;
  }
  // 5. stato di fondo: USB presente = arancio fisso (in carica) o verde fisso (carica completa, >= 4,15 V)
  if (usb) {
    if (mvBatt < 4150) ledScrivi(20, 8, 0); else ledScrivi(0, 15, 0);
  } else {
    ledScrivi(0, 0, 0);
  }
}

// ---------- Registrazione su flash ----------
enum { FONTE_BLE = 0, FONTE_USB = 1 };
bool fsOk = false;
bool registrando = false;
File fileRec;
char nomeRec[16] = "";
uint8_t bufferRec[DIM_BUFFER];
size_t nBufferRec = 0;
uint32_t inizioRec = 0;
uint16_t numeroFile = 0;
bool getAttivo = false;  // vero durante un GET (BLE o USB)
int fonteGet = FONTE_BLE;
File fileGet;
char nomeGet[16] = "";
uint32_t offsetGet = 0, totaleGet = 0;

uint32_t byteLiberi() {
  if (!fsOk) return 0;
  return LittleFS.totalBytes() - LittleFS.usedBytes();
}

// Conta i file rNNN.bin (numeroFile) e restituisce il numero massimo usato
int scansionaFile() {
  int massimo = 0;
  uint16_t n = 0;
  if (fsOk) {
    File radice = LittleFS.open("/");
    for (File f = radice.openNextFile(); f; f = radice.openNextFile()) {
      String nome = f.name();
      if (nome.startsWith("/")) nome = nome.substring(1);
      if (nome.length() >= 5 && nome[0] == 'r' && nome.endsWith(".bin")) {
        n++;
        massimo = max(massimo, atoi(nome.c_str() + 1));
      }
    }
  }
  numeroFile = n;
  return massimo;
}

bool nomeValido(const String &n) {
  if (n.length() < 5 || n.length() > 12 || n[0] != 'r' || !n.endsWith(".bin")) return false;
  for (unsigned i = 1; i < n.length() - 4; i++) if (!isdigit(n[i])) return false;
  return true;
}

// Stato a 18 byte (vedi sopra): aggiorna la caratteristica, notifica e stampa la riga S
void inviaStato() {
  uint16_t mv = analogReadMilliVolts(PIN_BATTERIA) * 2;
  uint16_t mvVbus = analogReadMilliVolts(PIN_VBUS) * 2;
  mvBatt = mv;  // per il LED
  mvVbusLetto = mvVbus;
  uint8_t flag = ((bool)Serial ? 1 : 0) | (sensoreOk ? 2 : 0) | (registrando ? 4 : 0) | (otaAttivo ? 8 : 0) | 16 |
                 (mvVbus > VBUS_PRESENTE_MV ? 32 : 0);
  uint32_t t = millis(), liberi = byteLiberi();
  uint32_t sec = registrando ? (t - inizioRec) / 1000 : 0;
  uint16_t secondi = sec > 65535 ? 65535 : sec;
  uint8_t stato[18];
  memcpy(stato, &mv, 2);
  stato[2] = flag;
  stato[3] = causaAvvio;
  memcpy(stato + 4, &t, 4);
  memcpy(stato + 8, &liberi, 4);
  memcpy(stato + 12, &numeroFile, 2);
  memcpy(stato + 14, &secondi, 2);
  memcpy(stato + 16, &mvVbus, 2);
  if (caratteristicaStato) {
    caratteristicaStato->setValue(stato, sizeof(stato));
    if (clienteConnesso) caratteristicaStato->notify();
  }
  if (!(getAttivo && fonteGet == FONTE_USB)) {
    Serial.printf("S,%lu,%u,%u,%u,%lu,%u,%u,%u\n", (unsigned long)t, mv, flag, causaAvvio,
                  (unsigned long)liberi, numeroFile, secondi, mvVbus);
  }
}

void svuotaBuffer() {
  if (nBufferRec && fileRec) {
    if (fileRec.write(bufferRec, nBufferRec) != nBufferRec) Serial.println("X,scrittura flash fallita");
  }
  nBufferRec = 0;
}

void scriviRecord(const uint8_t *r) {
  memcpy(bufferRec + nBufferRec, r, 16);
  nBufferRec += 16;
  if (nBufferRec >= DIM_BUFFER) svuotaBuffer();
}

// Evento: millis con bit 31 a 1, codice int16, poi quattro int16 a zero; negli eventi di inizio
// (1 e 4) il secondo int16 è il fondo scala in g (16) e il terzo la frequenza in Hz (100)
void scriviEvento(int16_t codice) {
  uint8_t r[16] = {0};
  if (codice == EV_INIZIO_TAP || codice == EV_INIZIO_CMD) {
    memcpy(r + 6, &FONDO_SCALA_G, 2);
    memcpy(r + 8, &FREQ_HZ, 2);
  }
  uint32_t t = millis() | 0x80000000u;
  memcpy(r, &t, 4);
  memcpy(r + 4, &codice, 2);
  scriviRecord(r);
}

// Campione: millis (bit 31 = 0), poi ax, ay, az (2048 LSB/g), gx, gy, gz (16,4 LSB/(°/s)) grezzi
void scriviCampione(const int16_t *assi) {
  uint8_t r[16];
  uint32_t t = millis() & 0x7FFFFFFFu;
  memcpy(r, &t, 4);
  memcpy(r + 4, assi, 12);
  scriviRecord(r);
}

bool iniziaRegistrazione(int16_t codice) {
  if (registrando || getAttivo || !fsOk) return false;
  if (byteLiberi() < LIBERI_MIN) return false;
  snprintf(nomeRec, sizeof(nomeRec), "/r%03d.bin", scansionaFile() + 1);
  fileRec = LittleFS.open(nomeRec, "w");
  if (!fileRec) return false;
  nBufferRec = 0;
  inizioRec = millis();
  registrando = true;
  scriviEvento(codice);
  numeroFile++;
  ledLampi(0, 40, 0, 2);
  inviaStato();
  return true;
}

void fermaRegistrazione(int16_t codice) {
  if (!registrando) return;
  scriviEvento(codice);
  svuotaBuffer();
  fileRec.close();
  registrando = false;
  scansionaFile();
  ledLampi(40, 0, 0, 3);
  inviaStato();
}

// ---------- Risposte ai comandi (BLE: notifiche sulla 7a1e0005; USB: righe di testo) ----------
// Notifica BLE: tipo + dati. pausaMs evita di perdere notifiche in raffica.
void bleInvia(char tipo, const uint8_t *dati, size_t n, int pausaMs = 0) {
  if (!clienteConnesso || !caratteristicaRisposte) return;
  uint8_t b[250];
  if (n > sizeof(b) - 1) n = sizeof(b) - 1;
  b[0] = tipo;
  if (n) memcpy(b + 1, dati, n);
  caratteristicaRisposte->setValue(b, n + 1);
  caratteristicaRisposte->notify();
  if (pausaMs) delay(pausaMs);
}

// K = conferma, X = errore
void rispondiTesto(char tipo, const String &testo, int fonte) {
  if (fonte == FONTE_USB) Serial.printf("%c,%s\n", tipo, testo.c_str());
  else bleInvia(tipo, (const uint8_t *)testo.c_str(), testo.length());
}
void rispondiK(const String &t, int fonte) { rispondiTesto('K', t, fonte); }
void rispondiX(const String &t, int fonte) { rispondiTesto('X', t, fonte); }

void fermaGet() {
  if (fileGet) fileGet.close();
  getAttivo = false;
}

// Dimensione dei dati per notifica: MTU negoziato - 3 (ATT) - 5 (tipo + offset), al massimo 240
size_t dimChunkBle() {
  uint16_t mtu = serverBle ? serverBle->getPeerMTU(serverBle->getConnId()) : 23;
  if (mtu <= 23) return 15;  // MTU non negoziato: solo 20 byte per notifica
  return min((size_t)240, (size_t)(mtu - 8));
}

// Un passo dello scaricamento, chiamato dal loop (mai dalla callback BLE)
void servizioGet() {
  if (!getAttivo) return;
  if ((fonteGet == FONTE_BLE && !clienteConnesso) || (fonteGet == FONTE_USB && !(bool)Serial)) {
    fermaGet();
    return;
  }
  int giri = fonteGet == FONTE_BLE ? 2 : 4;  // notifiche (o righe) per ciclo del loop
  for (int k = 0; k < giri; k++) {
    if (offsetGet >= totaleGet) {
      if (fonteGet == FONTE_BLE) {
        uint8_t e[4];
        memcpy(e, &totaleGet, 4);
        bleInvia('E', e, 4);
      } else {
        Serial.printf("E,%lu\n", (unsigned long)totaleGet);
      }
      fermaGet();
      return;
    }
    uint8_t dati[4 + 240];  // BLE: offset (4 byte) + fino a 240 byte di dati
    if (fonteGet == FONTE_BLE) {
      size_t n = min(dimChunkBle(), (size_t)(totaleGet - offsetGet));
      fileGet.seek(offsetGet);
      n = fileGet.read(dati + 4, n);
      if (n == 0) { rispondiX("lettura fallita", FONTE_BLE); fermaGet(); return; }
      memcpy(dati, &offsetGet, 4);
      bleInvia('D', dati, n + 4, 8);
      offsetGet += n;
    } else {
      if (Serial.availableForWrite() < 160) return;
      size_t n = min((size_t)64, (size_t)(totaleGet - offsetGet));
      fileGet.seek(offsetGet);
      n = fileGet.read(dati, n);
      if (n == 0) { rispondiX("lettura fallita", FONTE_USB); fermaGet(); return; }
      Serial.printf("H,%lu,", (unsigned long)offsetGet);
      for (size_t i = 0; i < n; i++) Serial.printf("%02x", dati[i]);
      Serial.print("\n");
      offsetGet += n;
    }
  }
}

// ---------- Aggiornamento OTA via BLE ----------
// La callback BLE copia i dati in un anello e aggiorna offset e CRC; la scrittura in flash,
// le risposte e i comandi OTA/OTAEND/OTAABORT li esegue il loop (mai la callback).
const size_t OTA_ANELLO = 8192;            // potenza di 2
const uint32_t OTA_NOTIFICA_OGNI = 32768;  // notifica di avanzamento ogni 32 KB
uint8_t otaAnello[OTA_ANELLO];
volatile uint32_t otaTesta = 0, otaCoda = 0;  // contatori monotoni (scrive la callback, legge il loop)
const esp_partition_t *otaPartizione = nullptr;
esp_ota_handle_t otaHandle = 0;
uint32_t otaTotale = 0, otaCrcAtteso = 0;
volatile uint32_t otaAccettati = 0;  // byte copiati nell'anello (prossimo offset atteso)
uint32_t otaScritti = 0;             // byte scritti in flash
volatile uint32_t otaCrc = 0xFFFFFFFFu;  // CRC32 zlib in corso (senza inversione finale)
uint32_t otaUltimaNotifica = 0;
uint32_t otaTabella[256];
volatile char otaMsgTipo = 0;  // messaggio da notificare, preparato dalla callback
char otaMsgTesto[48];

void otaMessaggio(char tipo, const char *testo) {
  if (otaMsgTipo) return;  // uno alla volta: i successivi sono ridondanti
  strlcpy(otaMsgTesto, testo, sizeof(otaMsgTesto));
  __sync_synchronize();
  otaMsgTipo = tipo;
}

void otaCrcAgg(const uint8_t *d, size_t n) {
  uint32_t c = otaCrc;
  while (n--) c = otaTabella[(c ^ *d++) & 0xFF] ^ (c >> 8);
  otaCrc = c;
}

class CallbackOta : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    if (!otaAttivo) return;
    const uint8_t *d = c->getData();
    size_t len = c->getLength();
    if (!d || len <= 4) return;
    uint32_t off;
    memcpy(&off, d, 4);
    size_t n = len - 4;
    char msg[40];
    if (off != otaAccettati) {
      snprintf(msg, sizeof(msg), "ota offset,%lu", (unsigned long)otaAccettati);
      otaMessaggio('X', msg);
      return;
    }
    if ((uint64_t)otaAccettati + n > otaTotale) { otaMessaggio('X', "ota dati oltre la dimensione"); return; }
    // Attende (al massimo 500 ms) che il loop svuoti l'anello: la risposta BLE parte solo dopo
    for (int i = 0; i < 100 && OTA_ANELLO - (otaTesta - otaCoda) < n; i++) vTaskDelay(pdMS_TO_TICKS(5));
    if (OTA_ANELLO - (otaTesta - otaCoda) < n) {
      snprintf(msg, sizeof(msg), "ota offset,%lu", (unsigned long)otaAccettati);
      otaMessaggio('X', msg);  // anello pieno: il client riprende dall'offset atteso
      return;
    }
    uint32_t t = otaTesta;
    for (size_t i = 0; i < n; i++) otaAnello[(t + i) & (OTA_ANELLO - 1)] = d[4 + i];
    otaCrcAgg(d + 4, n);
    otaAccettati += n;
    __sync_synchronize();
    otaTesta = t + n;
  }
};

// Scrive in flash quanto c'è nell'anello; false se la scrittura fallisce
bool otaSvuotaAnello() {
  while (otaCoda != otaTesta) {
    uint32_t c = otaCoda, disponibili = otaTesta - c;
    size_t pos = c & (OTA_ANELLO - 1);
    size_t n = min((size_t)disponibili, OTA_ANELLO - pos);
    if (esp_ota_write(otaHandle, otaAnello + pos, n) != ESP_OK) return false;
    otaScritti += n;
    otaCoda = c + n;
  }
  return true;
}

void otaAnnulla() {
  if (otaAttivo) esp_ota_abort(otaHandle);
  otaAttivo = false;
  otaCoda = otaTesta = 0;
  otaMsgTipo = 0;
  ultimoMovimento = millis();  // niente sonno subito dopo
}

// Un passo dell'aggiornamento, chiamato dal loop
void servizioOta() {
  if (!otaAttivo) return;
  if (!clienteConnesso) { otaAnnulla(); inviaStato(); return; }
  if (!otaSvuotaAnello()) {
    otaAnnulla();
    bleInvia('X', (const uint8_t *)"ota scrittura fallita", 21);
    inviaStato();
    return;
  }
  if (otaMsgTipo) {
    char tipo = otaMsgTipo;
    char testo[48];
    strlcpy(testo, otaMsgTesto, sizeof(testo));
    otaMsgTipo = 0;
    bleInvia(tipo, (const uint8_t *)testo, strlen(testo));
  }
  if (otaAccettati / OTA_NOTIFICA_OGNI > otaUltimaNotifica) {
    otaUltimaNotifica = otaAccettati / OTA_NOTIFICA_OGNI;
    char testo[24];
    snprintf(testo, sizeof(testo), "ota,%lu", (unsigned long)otaAccettati);
    bleInvia('K', (const uint8_t *)testo, strlen(testo));
  }
}

char otaVersione[24];  // versione dichiarata dal client

// Confronta due versioni numeriche "a.b.c[.d]" (mancanti = 0).
// Ritorna -1/0/1 (a<b, a==b, a>b); -2 se a è vuota o non numerica.
int confrontaVersioni(const char *a, const char *b) {
  if (!a || !*a) return -2;
  for (const char *p = a; *p; p++) if (!isdigit((unsigned char)*p) && *p != '.') return -2;
  if (a[0] == '.') return -2;
  long va[4] = {0, 0, 0, 0}, vb[4] = {0, 0, 0, 0};
  const char *pa = a, *pb = b;
  for (int i = 0; i < 4; i++) {
    if (*pa) { va[i] = strtol(pa, (char **)&pa, 10); if (*pa == '.') pa++; }
    if (*pb) { vb[i] = strtol(pb, (char **)&pb, 10); if (*pb == '.') pb++; }
  }
  if (*pa) return -2;  // più di 4 parti
  for (int i = 0; i < 4; i++) if (va[i] != vb[i]) return va[i] < vb[i] ? -1 : 1;
  return 0;
}

// Cerca nella partizione scritta la stringa "SWIMTAG_VER=<versione>;"
bool otaMarcatorePresente() {
  char ago[40];
  size_t k = snprintf(ago, sizeof(ago), "SWIMTAG_VER=%s;", otaVersione);
  const size_t BLOCCO = 1024, SOVR = 32;
  static uint8_t buf[BLOCCO + SOVR];
  size_t tenuti = 0;  // byte di sovrapposizione già in buf
  for (uint32_t off = 0; off < otaTotale; off += BLOCCO) {
    size_t n = min((size_t)BLOCCO, (size_t)(otaTotale - off));
    if (esp_partition_read(otaPartizione, off, buf + tenuti, n) != ESP_OK) return false;
    size_t tot = tenuti + n;
    if (tot >= k) {
      for (size_t i = 0; i + k <= tot; i++)
        if (buf[i] == (uint8_t)ago[0] && memcmp(buf + i, ago, k) == 0) return true;
    }
    tenuti = min(tot, SOVR);
    memmove(buf, buf + tot - tenuti, tenuti);
    yield();
  }
  return false;
}

// Comando OTA,<byte>,<crc32 hex>,<versione>[,forza]: prepara la partizione di destinazione
void otaAvvia(const String &arg, int fonte) {
  if (fonte != FONTE_BLE) { rispondiX("ota solo via ble", fonte); return; }
  if (otaAttivo) { rispondiX("ota gia in corso", fonte); return; }
  if (registrando || getAttivo) { rispondiX("occupato", fonte); return; }
  // Argomenti: <byte>,<crc32 hex>,<versione>[,forza]
  int v = arg.indexOf(',');
  if (v < 0) { rispondiX("ota argomenti", fonte); return; }
  uint32_t dim = strtoul(arg.substring(0, v).c_str(), nullptr, 10);
  String resto = arg.substring(v + 1);
  int v2 = resto.indexOf(',');
  String hex = v2 < 0 ? resto : resto.substring(0, v2);
  hex.trim();
  uint32_t crc = strtoul(hex.c_str(), nullptr, 16);
  String ver = v2 < 0 ? "" : resto.substring(v2 + 1);
  bool forza = false;
  int v3 = ver.indexOf(',');
  if (v3 >= 0) {
    String opz = ver.substring(v3 + 1);
    opz.trim();
    opz.toLowerCase();
    forza = (opz == "forza");
    ver = ver.substring(0, v3);
  }
  ver.trim();
  int cmp = confrontaVersioni(ver.c_str(), FIRMWARE_VERSIONE);
  if (cmp == -2) { rispondiX("ota versione mancante", fonte); return; }
  if (cmp == 0) { rispondiX("ota stessa versione", fonte); return; }
  if (cmp < 0 && !forza) { rispondiX("ota versione precedente", fonte); return; }
  strlcpy(otaVersione, ver.c_str(), sizeof(otaVersione));
  otaPartizione = esp_ota_get_next_update_partition(nullptr);
  if (!otaPartizione) { rispondiX("ota partizione assente", fonte); return; }
  if (dim == 0 || dim > otaPartizione->size) { rispondiX("ota dimensione non valida", fonte); return; }
  if (esp_ota_begin(otaPartizione, dim, &otaHandle) != ESP_OK) { rispondiX("ota avvio fallito", fonte); return; }
  for (uint32_t i = 0; i < 256; i++) {
    uint32_t c = i;
    for (int k = 0; k < 8; k++) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
    otaTabella[i] = c;
  }
  otaTotale = dim;
  otaCrcAtteso = crc;
  otaAccettati = otaScritti = otaUltimaNotifica = 0;
  otaCrc = 0xFFFFFFFFu;
  otaCoda = otaTesta = 0;
  otaMsgTipo = 0;
  otaAttivo = true;
  uint16_t mtu = serverBle ? serverBle->getPeerMTU(serverBle->getConnId()) : 23;
  size_t massimo = mtu > 7 ? min((size_t)508, (size_t)(mtu - 7)) : 16;
  rispondiK("ota pronto," + String((unsigned)massimo), fonte);
  inviaStato();
}

// Comando OTAEND: controlla dimensione e CRC, finalizza e riavvia
void otaFine(int fonte) {
  if (!otaAttivo) { rispondiX("ota non avviata", fonte); return; }
  if (!otaSvuotaAnello()) { otaAnnulla(); rispondiX("ota scrittura fallita", fonte); inviaStato(); return; }
  uint32_t crc = ~otaCrc;
  if (otaScritti != otaTotale) {
    char m[40];
    snprintf(m, sizeof(m), "ota incompleta,%lu", (unsigned long)otaScritti);
    otaAnnulla(); rispondiX(m, fonte); inviaStato(); return;
  }
  if (crc != otaCrcAtteso) { otaAnnulla(); rispondiX("ota crc errato", fonte); inviaStato(); return; }
  if (!otaMarcatorePresente()) { otaAnnulla(); rispondiX("ota firmware non riconosciuto", fonte); inviaStato(); return; }
  if (esp_ota_end(otaHandle) != ESP_OK) {  // controlla anche intestazione e hash dell'immagine
    otaAttivo = false; otaMsgTipo = 0;
    rispondiX("ota immagine non valida", fonte); inviaStato(); return;
  }
  if (esp_ota_set_boot_partition(otaPartizione) != ESP_OK) {
    otaAttivo = false; otaMsgTipo = 0;
    rispondiX("ota partizione di avvio", fonte); inviaStato(); return;
  }
  rispondiK("ota ok", fonte);
  Serial.println("OTA completata: riavvio");
  delay(500);
  esp_restart();
}

// Rollback: il bootloader del core lo ha attivo, la nuova app parte "in prova"
// (ESP_OTA_IMG_PENDING_VERIFY). Se prima della conferma c'è un reset, torna alla versione
// precedente. Conferma dopo 20 s di funzionamento con sensore e BLE attivi.
extern "C" bool verifyRollbackLater() { return true; }  // il core non conferma da solo

void confermaAggiornamento() {
  static bool fatto = false;
  if (fatto || !bleAvviato || !sensoreOk || millis() < 20000) return;
  fatto = true;
  esp_ota_img_states_t stato;
  if (esp_ota_get_state_partition(esp_ota_get_running_partition(), &stato) == ESP_OK &&
      stato == ESP_OTA_IMG_PENDING_VERIFY) {
    esp_ota_mark_app_valid_cancel_rollback();
    Serial.println("V,confermata");
  }
}

// Esegue un comando di testo (LIST, GET, DEL, DELALL, REC, STOP, OTA...) da BLE o USB
void eseguiComando(String riga, int fonte) {
  riga.trim();
  if (riga.length() == 0) return;
  int v = riga.indexOf(',');
  String verbo = v < 0 ? riga : riga.substring(0, v);
  String arg = v < 0 ? "" : riga.substring(v + 1);
  verbo.trim();
  verbo.toUpperCase();

  if (verbo == "OTA") { otaAvvia(arg, fonte); return; }
  if (verbo == "OTAEND") { otaFine(fonte); return; }
  if (verbo == "OTAABORT") {
    if (!otaAttivo) { rispondiX("ota non avviata", fonte); return; }
    otaAnnulla();
    rispondiK("ota annullato", fonte);
    inviaStato();
    return;
  }
  if (otaAttivo) { rispondiX("aggiornamento in corso", fonte); return; }

  if (verbo == "LIST") {
    File radice = LittleFS.open("/");
    for (File f = radice.openNextFile(); f; f = radice.openNextFile()) {
      String nome = f.name();
      if (nome.startsWith("/")) nome = nome.substring(1);
      if (!nomeValido(nome)) continue;
      if (fonte == FONTE_USB) {
        Serial.printf("F,%s,%lu\n", nome.c_str(), (unsigned long)f.size());
      } else {
        String r = nome + "," + String((unsigned long)f.size());
        bleInvia('L', (const uint8_t *)r.c_str(), r.length(), 10);
      }
    }
    if (fonte == FONTE_USB) Serial.println("Z");
    else bleInvia('Z', nullptr, 0);
  } else if (verbo == "GET") {
    if (getAttivo) { rispondiX("get in corso", fonte); return; }
    int v2 = arg.indexOf(',');
    String nome = v2 < 0 ? arg : arg.substring(0, v2);
    nome.trim();
    nome.toLowerCase();
    uint32_t off = v2 < 0 ? 0 : (uint32_t)strtoul(arg.substring(v2 + 1).c_str(), nullptr, 10);
    if (!nomeValido(nome)) { rispondiX("nome non valido", fonte); return; }
    if (registrando && ("/" + nome) == nomeRec) { rispondiX("file in registrazione", fonte); return; }
    fileGet = LittleFS.open("/" + nome, "r");
    if (!fileGet) { rispondiX("file inesistente", fonte); return; }
    totaleGet = fileGet.size();
    if (off > totaleGet) { fileGet.close(); rispondiX("offset oltre la fine", fonte); return; }
    offsetGet = off;
    strlcpy(nomeGet, nome.c_str(), sizeof(nomeGet));
    fonteGet = fonte;
    getAttivo = true;
  } else if (verbo == "DEL") {
    String nome = arg;
    nome.trim();
    nome.toLowerCase();
    if (!nomeValido(nome)) { rispondiX("nome non valido", fonte); return; }
    if (registrando && ("/" + nome) == nomeRec) { rispondiX("file in registrazione", fonte); return; }
    if (getAttivo && nome == nomeGet) { rispondiX("get in corso", fonte); return; }
    if (!LittleFS.remove("/" + nome)) { rispondiX("file inesistente", fonte); return; }
    scansionaFile();
    rispondiK("del " + nome, fonte);
    inviaStato();
  } else if (verbo == "DELALL") {
    if (registrando || getAttivo) { rispondiX("occupato", fonte); return; }
    for (int giri = 0; giri < 200; giri++) {  // ogni giro cancella un file (evita di modificare la cartella mentre la scorre)
      String trovato = "";
      File radice = LittleFS.open("/");
      for (File f = radice.openNextFile(); f; f = radice.openNextFile()) {
        String nome = f.name();
        if (nome.startsWith("/")) nome = nome.substring(1);
        if (nomeValido(nome)) { trovato = nome; break; }
      }
      radice.close();
      if (trovato.length() == 0) break;
      LittleFS.remove("/" + trovato);
    }
    scansionaFile();
    rispondiK("delall", fonte);
    inviaStato();
  } else if (verbo == "REC") {
    if (getAttivo) rispondiX("get in corso", fonte);
    else if (registrando) rispondiX("gia in registrazione", fonte);
    else if (!iniziaRegistrazione(EV_INIZIO_CMD)) rispondiX("impossibile avviare", fonte);
    else rispondiK("rec", fonte);
  } else if (verbo == "STOP") {
    if (!registrando) rispondiX("non in registrazione", fonte);
    else { fermaRegistrazione(EV_FINE_CMD); rispondiK("stop", fonte); }
  } else {
    rispondiX("comando sconosciuto", fonte);
  }
}

// Righe di testo dalla seriale USB, lette senza bloccare
void leggiSeriale() {
  static String riga;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      String r = riga;
      riga = "";
      eseguiComando(r, FONTE_USB);
    } else if (c != '\r' && riga.length() < 80) {
      riga += c;
    }
  }
}

// ---------- Tap ----------
uint8_t tapContati = 0;
uint32_t ultimoTap = 0;

void tapChiudi(uint32_t ora);

void tapRilevato(uint32_t ora) {
  if (tapContati) {
    uint32_t gap = ora - ultimoTap;
    if (gap < TAP_MIN_MS) return;  // rimbalzo
    if (gap > TAP_MAX_MS) {        // troppo distante: la vecchia sequenza si chiude, ne parte una nuova
      tapChiudi(ora);
    }
  }
  tapContati++;
  ultimoTap = ora;
  ledTap();
}

// Decide: 2 tap = inizio registrazione, 3 tap = fine; altri numeri ignorati
void tapChiudi(uint32_t ora) {
  uint8_t n = tapContati;
  tapContati = 0;
  if (!n) return;
  Serial.printf("T,%lu,%u\n", (unsigned long)ora, n);
  if (clienteConnesso && !getAttivo && !otaAttivo) {
    String t = "tap," + String((unsigned)n);
    bleInvia('K', (const uint8_t *)t.c_str(), t.length());
  }
  if (n == 2 && !registrando) {
    if (getAttivo) rispondiX("get in corso", fonteGet);
    else if (!iniziaRegistrazione(EV_INIZIO_TAP)) Serial.println("X,impossibile avviare la registrazione");
  } else if (n == 3 && registrando) {
    fermaRegistrazione(EV_FINE_TAP);
  }
}

void setup() {
  Serial.setTxBufferSize(1024);
  Serial.begin(115200);
  // Senza PC collegato (batteria, caricatore) la seriale non deve rallentare il programma
  Serial.setTxTimeoutMs(0);
  delay(2000);
  esp_sleep_wakeup_cause_t causa = esp_sleep_get_wakeup_cause();
  // Causa dell'avvio: 0 accensione, 1 risveglio dal BMI160, 2 panic, 3 watchdog, 4 brownout, 5 software, 6 altro
  esp_reset_reason_t rr = esp_reset_reason();
  const char *nomeRr = "altro";
  switch (rr) {
    case ESP_RST_POWERON: causaAvvio = 0; nomeRr = "poweron"; break;
    case ESP_RST_SW: causaAvvio = 5; nomeRr = "sw"; break;
    case ESP_RST_PANIC: causaAvvio = 2; nomeRr = "panic"; break;
    case ESP_RST_INT_WDT: causaAvvio = 3; nomeRr = "int_wdt"; break;
    case ESP_RST_TASK_WDT: causaAvvio = 3; nomeRr = "task_wdt"; break;
    case ESP_RST_WDT: causaAvvio = 3; nomeRr = "wdt"; break;
    case ESP_RST_BROWNOUT: causaAvvio = 4; nomeRr = "brownout"; break;
    case ESP_RST_DEEPSLEEP: causaAvvio = (causa == ESP_SLEEP_WAKEUP_EXT0) ? 1 : 6; nomeRr = "deepsleep"; break;
    default: causaAvvio = 6; break;
  }
  Serial.printf("R,%d,%s\n", (int)rr, nomeRr);
  Serial.printf("V,%s+%s,%s\n", FIRMWARE_VERSIONE, FIRMWARE_BUILD, esp_ota_get_running_partition()->label);
  Serial.println(MARCATORE_VERSIONE);  // evita che il linker elimini il marcatore
  Serial.printf("Avvio: %s\n", causa == ESP_SLEEP_WAKEUP_EXT0 ? "risveglio dal BMI160 (movimento)" : "accensione o reset");
  Serial.println("\n=== SwimTimer: test collegamenti ===");

  fsOk = LittleFS.begin(true);  // true = formatta se il montaggio fallisce
  scansionaFile();
  Serial.printf("LittleFS: %s, liberi %lu byte, %u file\n", fsOk ? "OK" : "ERRORE",
                (unsigned long)byteLiberi(), numeroFile);

  // Server GATT: dati e stato (READ+NOTIFY), comandi (WRITE) e risposte (NOTIFY)
  BLEDevice::init("SwimTag");
  BLEDevice::setMTU(247);
  serverBle = BLEDevice::createServer();
  serverBle->setCallbacks(new CallbackServer());
  BLEService *servizio = serverBle->createService(UUID_SERVIZIO);
  caratteristicaDati = servizio->createCharacteristic(
      UUID_DATI, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  caratteristicaDati->addDescriptor(new BLE2902());
  caratteristicaStato = servizio->createCharacteristic(
      UUID_STATO, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  caratteristicaStato->addDescriptor(new BLE2902());
  BLECharacteristic *comandi = servizio->createCharacteristic(
      UUID_COMANDI, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  comandi->setCallbacks(new CallbackComandi());
  caratteristicaRisposte = servizio->createCharacteristic(UUID_RISPOSTE, BLECharacteristic::PROPERTY_NOTIFY);
  caratteristicaRisposte->addDescriptor(new BLE2902());
  BLECharacteristic *ota = servizio->createCharacteristic(
      UUID_OTA, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  ota->setCallbacks(new CallbackOta());
  BLECharacteristic *versione = servizio->createCharacteristic(UUID_VERSIONE, BLECharacteristic::PROPERTY_READ);
  versione->setValue(String(FIRMWARE_VERSIONE "+" FIRMWARE_BUILD));
  servizio->start();

  // Annuncio BLE ogni 50 ms: nome e ultimo campione (vedi aggiornaAnnuncio)
  annuncio = BLEDevice::getAdvertising();
  int16_t zero[6] = {0};
  aggiornaAnnuncio(0, zero);
  BLEAdvertisementData risposta;
  risposta.setCompleteServices(BLEUUID(UUID_SERVIZIO));
  annuncio->setScanResponseData(risposta);
  annuncio->setMinInterval(80);  // unità da 0,625 ms
  annuncio->setMaxInterval(80);
  BLEDevice::startAdvertising();
  bleAvviato = true;
  Serial.println("BLE: annuncio come SwimTag con servizio dati");

  pinMode(PIN_INT1, INPUT);

  // Prima di qualsiasi Wire.begin: sblocco del bus se un sensore tiene SDA basso
  sbloccaI2C();
  mvBatt = analogReadMilliVolts(PIN_BATTERIA) * 2;
  mvVbusLetto = analogReadMilliVolts(PIN_VBUS) * 2;
  ledLampi(0, 0, 40, 1);  // avvio: un lampo blu

  // Livelli a riposo: con le resistenze di pull-up del modulo SDA e SCL devono essere a 1
  pinMode(PIN_SDA, INPUT);
  pinMode(PIN_SCL, INPUT);
  delay(5);
  Serial.printf("Livelli a riposo senza pull-up interni: SDA(8)=%d SCL(9)=%d (attesi 1 se il modulo è alimentato)\n",
                digitalRead(PIN_SDA), digitalRead(PIN_SCL));

  // Scansione anche con pin invertiti, per scoprire SDA/SCL scambiati
  const int prove[2][2] = {{PIN_SDA, PIN_SCL}, {PIN_SCL, PIN_SDA}};
  for (int p = 0; p < 2; p++) {
    Wire.begin(prove[p][0], prove[p][1]);
    Wire.setClock(100000);
    pinMode(prove[p][0], INPUT_PULLUP);
    pinMode(prove[p][1], INPUT_PULLUP);
    Wire.begin(prove[p][0], prove[p][1]);
    Serial.printf("Scansione I2C (SDA=%d, SCL=%d): ", prove[p][0], prove[p][1]);
    int trovati = 0;
    for (uint8_t a = 1; a < 127; a++) {
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) {
        Serial.printf("0x%02X ", a);
        trovati++;
      }
    }
    Serial.println(trovati ? "" : "nessun dispositivo");
    Wire.end();
  }
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);  // 100 Hz di letture: 12 byte + tap in ~0,6 ms

  sensoreOk = avviaSensore();
}

// Righe dati per tools/assi.html: D,millis,ax,ay,az (g),gx,gy,gz (°/s) a 100 Hz.
// Le altre righe sono diagnostica, una al secondo.
void loop() {
  static uint32_t ultimaDiagnostica = 0;
  bool getUsb = getAttivo && fonteGet == FONTE_USB;

  // Comandi: seriale USB e coda BLE (la callback BLE non esegue nulla)
  leggiSeriale();
  servizioOta();
  while (codaCoda != codaTesta) {
    String c = codaComandi[codaCoda];
    codaCoda = (codaCoda + 1) & 3;
    eseguiComando(c, FONTE_BLE);
  }
  getUsb = getAttivo && fonteGet == FONTE_USB;

  // Durante l'aggiornamento OTA niente sensore: né dati, né tap, né righe D
  if (sensoreOk && !otaAttivo) {
#if TAP_HARDWARE
    // Single tap del BMI160: bit 5 di INT_STATUS_0 (memorizzato), poi azzerato
    uint8_t st = 0;
    if (leggi(REG_INT_STATUS_0, &st, 1) && (st & 0x20)) {
      scrivi(REG_CMD, 0xB1);
      tapRilevato(millis());
    }
#endif
    uint8_t b[12];
    if (leggi(REG_GYR_DATA, b, 12)) {
      int16_t v[6];
      for (int i = 0; i < 6; i++) v[i] = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
      // Fondo scala: ±16 g (2048 LSB/g), ±2000 °/s (16,4 LSB/°/s)
      // Notifica BLE a 25 Hz (un campione ogni 4): 16 byte little-endian,
      // uint32 millis, poi i sei int16 grezzi ax, ay, az (2048 LSB/g), gx, gy, gz
      int16_t assi[6] = {v[3], v[4], v[5], v[0], v[1], v[2]};
      // Dati per l'annuncio a 20 Hz: accelerazione convertita a 16384 LSB/g (x8, saturata)
      static uint32_t ultimoAnnuncio = 0;
      static uint8_t numeroAnnuncio = 0;
      if (millis() - ultimoAnnuncio >= 50) {
        ultimoAnnuncio = millis();
        int16_t ann[6];
        for (int i = 0; i < 6; i++) {
          int32_t x = i < 3 ? (int32_t)assi[i] * 8 : assi[i];
          ann[i] = x > 32767 ? 32767 : (x < -32767 ? -32767 : x);
        }
        aggiornaAnnuncio(++numeroAnnuncio, ann);
      }
      static uint8_t contatore = 0;
      // Durante un GET le notifiche dati sono sospese
      if (clienteConnesso && caratteristicaDati && !getAttivo && (contatore++ & 3) == 0) {
        uint8_t pacchetto[16];
        uint32_t t = millis();
        memcpy(pacchetto, &t, 4);
        memcpy(pacchetto + 4, assi, 12);
        caratteristicaDati->setValue(pacchetto, sizeof(pacchetto));
        caratteristicaDati->notify();
      }
      float ax = v[3] / ACC_LSB_G, ay = v[4] / ACC_LSB_G, az = v[5] / ACC_LSB_G;
      float gx = v[0] / 16.4, gy = v[1] / 16.4, gz = v[2] / 16.4;
      float modulo = sqrtf(ax * ax + ay * ay + az * az);
      float dinamica = fabsf(modulo - 1.0f);
      if (dinamica > SOGLIA_MOVIMENTO_G || sqrtf(gx * gx + gy * gy + gz * gz) > SOGLIA_MOVIMENTO_DPS)
        ultimoMovimento = millis();
#if !TAP_HARDWARE
      // Tap software: jerk tra due campioni consecutivi oltre soglia, escluso con giroscopio alto
      static float pax = 0, pay = 0, paz = 0;
      static bool haPrec = false;
      static uint32_t ultimoTapSw = 0;
      float jerk = sqrtf((ax - pax) * (ax - pax) + (ay - pay) * (ay - pay) + (az - paz) * (az - paz));
      float giro = sqrtf(gx * gx + gy * gy + gz * gz);
      pax = ax; pay = ay; paz = az;
      uint32_t oraTap = millis();
      if (haPrec && jerk > TAP_JERK_G && giro < TAP_GIRO_MAX_DPS && oraTap - ultimoTapSw >= TAP_RIFIUTO_MS) {
        ultimoTapSw = oraTap;
        tapRilevato(oraTap);
      }
      haPrec = true;
#endif
      if (registrando) scriviCampione(assi);
      lettureFallite = 0;
      if (!getUsb && Serial) {  // senza PC niente righe D: risparmia tempo al ciclo da 10 ms
        Serial.printf("D,%lu,%.3f,%.3f,%.3f,%.1f,%.1f,%.1f\n", millis(),
                      v[3] / ACC_LSB_G, v[4] / ACC_LSB_G, v[5] / ACC_LSB_G,
                      v[0] / 16.4, v[1] / 16.4, v[2] / 16.4);
      }
    } else {
      if (lettureFallite < 255) lettureFallite++;
      if (!getUsb) Serial.println("lettura dati fallita");
    }
  }
  // 20 letture fallite di fila, o sensore assente (riprova ogni 5 s): sblocco del bus e riconfigurazione
  static uint32_t ultimoRecupero = 0;
  if (!otaAttivo && (lettureFallite >= 20 || (!sensoreOk && millis() - ultimoRecupero >= 5000))) {
    ultimoRecupero = millis();
    recuperaI2C();
  }

  servizioGet();
  if (tapContati && millis() - ultimoTap >= TAP_CHIUSURA_MS) tapChiudi(millis());

  if (millis() - ultimaDiagnostica >= 1000) {
    ultimaDiagnostica = millis();
    // Memoria quasi piena: chiude la registrazione (evento 3)
    if (otaAttivo) {
      // aggiornamento in corso: nessuna riga S né notifica di stato (già inviato all'avvio)
    } else if (registrando && byteLiberi() < LIBERI_MIN) fermaRegistrazione(EV_FINE_PIENA);
    else inviaStato();
    if (!otaAttivo && !(getAttivo && fonteGet == FONTE_USB)) {
      uint32_t g1 = analogReadMilliVolts(PIN_BATTERIA), g2 = analogReadMilliVolts(PIN_VBUS);
      float vbat = g1 * 2 / 1000.0;
      Serial.printf("partitori: GPIO1=%lu mV -> batteria %.2f V | GPIO2=%lu mV -> 5V %.2f V\n",
                    (unsigned long)g1, vbat, (unsigned long)g2, g2 * 2 / 1000.0);
      Serial.printf("%s | INT1=%d | batteria(GPIO1x2)=%.2f V\n",
                    sensoreOk ? "BMI160 OK" : "BMI160 assente", digitalRead(PIN_INT1), vbat);
    }
  }
  ledAggiorna(registrando);
  // Sonno profondo solo se fermo da tempo, senza pagina collegata, senza PC sulla USB e
  // senza registrazione o scaricamento in corso
  if (sensoreOk && millis() - ultimoMovimento > INATTIVITA_MS && !clienteConnesso && !Serial &&
      !registrando && !getAttivo && !otaAttivo)
    dormi();
  confermaAggiornamento();
  // Ciclo a 100 Hz: attesa fino al prossimo multiplo di 10 ms (micros, senza deriva)
  static uint32_t prossimo = 0;
  uint32_t adesso = micros();
  if (otaAttivo) {
    prossimo = adesso;
    delay(2);
  } else {
    if (prossimo == 0 || (int32_t)(adesso - prossimo) > 50000) prossimo = adesso;  // ritardo grosso: riparte
    prossimo += PERIODO_US;
    int32_t resta = (int32_t)(prossimo - micros());
    if (resta > 1500) delay((resta - 1000) / 1000);  // cede la CPU
    while ((int32_t)(prossimo - micros()) > 0) delayMicroseconds(50);
  }
}
