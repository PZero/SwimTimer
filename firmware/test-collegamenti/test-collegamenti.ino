// Test dei collegamenti del tag: bus I2C, BMI160, pin INT1 e livello batteria.
// Collegamenti in hardware/schema.md. Uscita sulla seriale USB a 115200.
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

const int PIN_SDA = 8;
const int PIN_SCL = 9;
const int PIN_INT1 = 4;
const int PIN_BATTERIA = 1;  // partitore 100k/100k, se montato

const uint8_t BMI160_ADDR = 0x68;
const uint8_t REG_CHIP_ID = 0x00;   // atteso 0xD1
const uint8_t REG_GYR_DATA = 0x0C;  // 6 byte giroscopio + 6 byte accelerometro
const uint8_t REG_PMU_STATUS = 0x03;
const uint8_t REG_CMD = 0x7E;

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

// Servizio GATT per la pagina Web Bluetooth (contratto fisso, la pagina lo usa già)
#define UUID_SERVIZIO "7a1e0001-5b1d-4c8e-9f3a-1d2c3b4a5e60"
#define UUID_DATI "7a1e0002-5b1d-4c8e-9f3a-1d2c3b4a5e60"
BLECharacteristic *caratteristicaDati = nullptr;
volatile bool clienteConnesso = false;
BLEAdvertising *annuncio = nullptr;

// Annuncio per il display (firmware/display-prova), che lo riceve senza collegarsi:
// flag + nome "SwimTag" + dati produttore (0xFFFF = sperimentale):
// 1 byte contatore, poi int16 little-endian grezzi ax, ay, az, gx, gy, gz.
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

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== SwimTimer: test collegamenti ===");

  // Server GATT: servizio con una caratteristica READ+NOTIFY da 16 byte
  BLEDevice::init("SwimTag");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new CallbackServer());
  BLEService *servizio = server->createService(UUID_SERVIZIO);
  caratteristicaDati = servizio->createCharacteristic(
      UUID_DATI, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  caratteristicaDati->addDescriptor(new BLE2902());
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
  Serial.println("BLE: annuncio come SwimTag con servizio dati");

  pinMode(PIN_INT1, INPUT);

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
  Wire.setClock(100000);

  uint8_t id = 0;
  if (!leggi(REG_CHIP_ID, &id, 1)) {
    Serial.println("BMI160: NON risponde a 0x68 (controlla SDA/SCL, alimentazione, SAO a GND, CS a 3V3)");
    return;
  }
  Serial.printf("BMI160 chip ID: 0x%02X %s\n", id, id == 0xD1 ? "(OK)" : "(ATTESO 0xD1)");
  if (id != 0xD1) return;

  // Accende accelerometro e giroscopio in modalità normale
  scrivi(REG_CMD, 0x11);
  delay(10);
  scrivi(REG_CMD, 0x15);
  delay(100);
  uint8_t pmu = 0;
  leggi(REG_PMU_STATUS, &pmu, 1);
  Serial.printf("Stato alimentazione sensori: 0x%02X %s\n", pmu, pmu == 0x14 ? "(OK)" : "(atteso 0x14)");
  sensoreOk = true;
}

// Righe dati per tools/assi.html: D,millis,ax,ay,az (g),gx,gy,gz (°/s) a 50 Hz.
// Le altre righe sono diagnostica, una al secondo.
void loop() {
  static uint32_t ultimaDiagnostica = 0;
  if (sensoreOk) {
    uint8_t b[12];
    if (leggi(REG_GYR_DATA, b, 12)) {
      int16_t v[6];
      for (int i = 0; i < 6; i++) v[i] = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
      // Fondo scala predefinito: ±2 g (16384 LSB/g), ±2000 °/s (16,4 LSB/°/s)
      // Notifica BLE a 25 Hz (un campione ogni 2): 16 byte little-endian,
      // uint32 millis, poi i sei int16 grezzi ax, ay, az, gx, gy, gz
      // Dati per l'annuncio a 20 Hz, nello stesso ordine della notifica
      int16_t assi[6] = {v[3], v[4], v[5], v[0], v[1], v[2]};
      static uint32_t ultimoAnnuncio = 0;
      static uint8_t numeroAnnuncio = 0;
      if (millis() - ultimoAnnuncio >= 50) {
        ultimoAnnuncio = millis();
        aggiornaAnnuncio(++numeroAnnuncio, assi);
      }
      static uint8_t contatore = 0;
      if (clienteConnesso && caratteristicaDati && (contatore++ & 1) == 0) {
        uint8_t pacchetto[16];
        uint32_t t = millis();
        memcpy(pacchetto, &t, 4);
        memcpy(pacchetto + 4, assi, 12);
        caratteristicaDati->setValue(pacchetto, sizeof(pacchetto));
        caratteristicaDati->notify();
      }
      Serial.printf("D,%lu,%.3f,%.3f,%.3f,%.1f,%.1f,%.1f\n", millis(),
                    v[3] / 16384.0, v[4] / 16384.0, v[5] / 16384.0,
                    v[0] / 16.4, v[1] / 16.4, v[2] / 16.4);
    } else {
      Serial.println("lettura dati fallita");
    }
  }
  if (millis() - ultimaDiagnostica >= 1000) {
    ultimaDiagnostica = millis();
    float vbat = analogReadMilliVolts(PIN_BATTERIA) * 2 / 1000.0;
    Serial.printf("%s | INT1=%d | batteria(GPIO1x2)=%.2f V\n",
                  sensoreOk ? "BMI160 OK" : "BMI160 assente", digitalRead(PIN_INT1), vbat);
  }
  delay(20);
}
