// SwimTimer - driver minimo della flash QSPI della XIAO nRF52840 Sense (Puya P25Q16H, 2 MB) sopra nrfx_qspi.
// Perche' non Adafruit_SPIFlash: la libreria utente omonima (versione piu' recente) rompe la compilazione di Bluefruit.
// Stessa sequenza della libreria (QE, lettura 0x6B quad, scrittura 0x32 quad, WREN esplicito, attesa del bit WIP).
// Tutti gli accessi sono a indirizzi multipli di 4; la scrittura e' una pagina da 256 byte alla volta.
#pragma once
#include <Arduino.h>
#include "nrfx_qspi.h"

class FlashQspi {
 public:
  bool begin() {
    if (attiva) return true;
    nrfx_qspi_config_t cfg = {};
    cfg.xip_offset = 0;
    cfg.pins.sck_pin = (uint8_t)g_ADigitalPinMap[PIN_QSPI_SCK];
    cfg.pins.csn_pin = (uint8_t)g_ADigitalPinMap[PIN_QSPI_CS];
    cfg.pins.io0_pin = (uint8_t)g_ADigitalPinMap[PIN_QSPI_IO0];
    cfg.pins.io1_pin = (uint8_t)g_ADigitalPinMap[PIN_QSPI_IO1];
    cfg.pins.io2_pin = (uint8_t)g_ADigitalPinMap[PIN_QSPI_IO2];
    cfg.pins.io3_pin = (uint8_t)g_ADigitalPinMap[PIN_QSPI_IO3];
    cfg.prot_if.readoc = NRF_QSPI_READOC_READ4O;     // 0x6B
    cfg.prot_if.writeoc = NRF_QSPI_WRITEOC_PP4O;     // 0x32
    cfg.prot_if.addrmode = NRF_QSPI_ADDRMODE_24BIT;
    cfg.prot_if.dpmconfig = false;
    cfg.phy_if.sck_delay = 1;
    cfg.phy_if.dpmen = false;
    cfg.phy_if.spi_mode = NRF_QSPI_MODE_0;
    cfg.phy_if.sck_freq = NRF_QSPI_FREQ_32MDIV2;      // 16 MHz (32 MHz non e' affidabile su nRF52840)
    cfg.irq_priority = 7;
    if (nrfx_qspi_init(&cfg, NULL, NULL) != NRFX_SUCCESS) return false;   // senza callback: API bloccante
    attiva = true;
    delay(6);
    uint8_t id[3] = {0, 0, 0};
    if (!leggiCmd(0x9F, id, 3) || id[0] != 0x85 || id[2] != 0x15) { end(); return false; }   // Puya, 2 MB
    uint8_t s2 = 0;
    leggiCmd(0x35, &s2, 1);
    if (!(s2 & 0x02)) {                                 // bit QE (quad enable)
      wren();
      const uint8_t d[2] = {0x00, 0x02};
      scriviCmd(0x01, d, 2);
      attendi(100);
    }
    return true;
  }
  void end() {
    if (!attiva) return;
    attendi(100);
    nrfx_qspi_uninit();
    attiva = false;
  }
  uint32_t size() const { return 2UL * 1024 * 1024; }

  // lunghezza qualsiasi, indirizzo multiplo di 4; ritorna len se ok, 0 se errore
  uint32_t readBuffer(uint32_t addr, uint8_t *buf, uint32_t len) {
    if (!attiva || (addr & 3)) return 0;
    uint32_t resto = len;
    while (resto) {
      uint32_t n = min(resto, (uint32_t)sizeof(tmp));
      uint32_t n4 = (n + 3) & ~3UL;
      if (!attendi(100)) return 0;
      if (nrfx_qspi_read(tmp, n4, addr) != NRFX_SUCCESS) return 0;
      memcpy(buf, tmp, n);
      buf += n; addr += n; resto -= n;
    }
    return len;
  }
  // una pagina (non oltre il confine di 256 byte), indirizzo multiplo di 4
  uint32_t writeBuffer(uint32_t addr, const uint8_t *buf, uint32_t len) {
    if (!attiva || (addr & 3) || len == 0 || len > 256 || (addr & 255) + len > 256) return 0;
    if (!attendi(100)) return 0;
    wren();
    memset(tmp, 0xFF, sizeof(tmp));
    memcpy(tmp, buf, len);
    uint32_t n4 = (len + 3) & ~3UL;
    if (nrfx_qspi_write(tmp, n4, addr) != NRFX_SUCCESS) return 0;
    return len;
  }
  bool eraseChip() {
    if (!attiva || !attendi(100)) return false;
    wren();
    if (!comando(0xC7, NULL, 0, NULL, 0)) return false;
    return attendi(60000);                              // tipico 5-15 s
  }
  // attende la fine di una scrittura/cancellazione (bit WIP del registro di stato)
  bool attendi(uint32_t timeoutMs) {
    uint32_t t0 = millis();
    while (true) {
      uint8_t st = 0xFF;
      if (!leggiCmd(0x05, &st, 1)) return false;
      if (!(st & 0x01)) return true;
      if (millis() - t0 > timeoutMs) return false;
      delay(1);
    }
  }

 private:
  bool attiva = false;
  alignas(4) uint8_t tmp[256];
  bool comando(uint8_t op, const uint8_t *tx, uint8_t nTx, uint8_t *rx, uint8_t nRx) {
    nrf_qspi_cinstr_conf_t c = {};
    c.opcode = op;
    c.length = (nrf_qspi_cinstr_len_t)((nTx > nRx ? nTx : nRx) + 1);
    c.io2_level = true;
    c.io3_level = true;
    c.wipwait = false;
    c.wren = false;
    return nrfx_qspi_cinstr_xfer(&c, tx, rx) == NRFX_SUCCESS;
  }
  bool leggiCmd(uint8_t op, uint8_t *rx, uint8_t n) { return comando(op, NULL, 0, rx, n); }
  bool scriviCmd(uint8_t op, const uint8_t *tx, uint8_t n) { return comando(op, tx, n, NULL, 0); }
  void wren() { comando(0x06, NULL, 0, NULL, 0); }
};
