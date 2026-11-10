// SwimTimer - memoria ad anello di 512 blocchi da 4 KB sulla flash QSPI (formato 2, docs/SINCRONIZZAZIONE.md §1 e §8).
// Regola che non si viola mai: un blocco NON confermato non viene mai cancellato ne' riscritto.
// Stato dei blocchi in RAM (ricavato all'avvio dalle intestazioni): libero, aperto, da validare (chiuso non confermato),
// confermato, anomalo (contenuto non riconosciuto: non si tocca). Un blocco "aperto" esiste solo in RAM durante la registrazione:
// dopo un riavvio i blocchi scritti a meta' sono semplicemente "da validare" (le pagine mai scritte restano 0xFF = vuote).
#pragma once
#include <Arduino.h>
#include "flash_qspi.h"
#include "swr_formato.h"

enum : uint8_t { BL_LIBERO = 0, BL_APERTO = 1, BL_DA_VALIDARE = 2, BL_CONFERMATO = 3, BL_ANOMALO = 4 };
enum EsitoScansione : uint8_t { SC_OK = 0, SC_FORMATO1 = 1, SC_ESTRANEA = 2 };
enum : uint8_t { AN_OK = 0, AN_PIENA = 1, AN_FLASH = 2 };

class SwrAnello {
 public:
  FlashQspi *f = nullptr;
  uint32_t idTag = 0;
  uint32_t seq[SWR_N_BLOCCHI];
  uint8_t st[SWR_N_BLOCCHI];
  uint32_t maxSeq = 0;
  int16_t aperto = -1;                 // blocco aperto in scrittura (-1 = nessuno)
  uint8_t paginaNext = 0;              // prossima pagina (1..15) da scrivere nel blocco aperto
  int16_t ultimo = -1;                 // ultimo blocco aperto: la ricerca del successivo parte da qui (ordine ad anello)
  uint16_t nDaValidare = 0, nConfermati = 0, nAnomali = 0, nLiberi = 0;
  uint8_t ultimoErrore = AN_OK;
  volatile uint32_t chiusure = 0;      // contatore dei blocchi chiusi (serve a riprendere l'invio dopo FINE)

  void inizia(FlashQspi *flash, uint32_t id) { f = flash; idTag = id; }

  // Legge le 512 intestazioni. SC_FORMATO1: flash con il formato vecchio (non si tocca); SC_ESTRANEA: contenuto non nostro
  // (nessun blocco valido e pagine non vuote); SC_OK altrimenti (anche flash vuota).
  EsitoScansione scansiona() {
    uint8_t b[SWR_PAGINA];
    uint16_t validi = 0, vecchio = 0, strani = 0;
    maxSeq = 0; aperto = -1; ultimo = -1; paginaNext = 0;
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++) {
      seq[i] = 0; st[i] = BL_LIBERO;
      f->readBuffer((uint32_t)i * SWR_BLOCCO_BYTE, b, SWR_PAGINA);
      bool ff = true;
      for (int k = 0; k < SWR_PAGINA; k++) if (b[k] != 0xFF) { ff = false; break; }
      if (ff) continue;
      uint32_t s = swrLeggi32(b + 17);
      if (swrIntestazioneBloccoValida(b) && s != 0 && s != 0xFFFFFFFFu && (uint16_t)(b[2] | (b[3] << 8)) == i * SWR_PAGINE_BLOCCO) {
        validi++;
        seq[i] = s;
        st[i] = swrConfermato(b) ? BL_CONFERMATO : BL_DA_VALIDARE;
        if (s > maxSeq) { maxSeq = s; ultimo = i; }
      } else {
        st[i] = BL_ANOMALO;
        strani++;
        if ((b[0] == SWR_T_SEGMENTO || b[0] == SWR_T_DATI || b[0] == SWR_T_CHIUSURA)) {
          uint16_t crc = swrCrc16(b, 14);
          crc = swrCrc16(b + 16, SWR_PAGINA - 16, crc);
          if (b[14] == (crc & 0xFF) && b[15] == (crc >> 8)) vecchio++;
        }
      }
    }
    ricalcola();
    if (validi == 0 && vecchio > 0) return SC_FORMATO1;
    if (validi == 0 && strani > 0) return SC_ESTRANEA;
    return SC_OK;
  }

  void azzeraRam() {
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++) { seq[i] = 0; st[i] = BL_LIBERO; }
    maxSeq = 0; aperto = -1; ultimo = -1; paginaNext = 0;
    ricalcola();
  }

  void ricalcola() {
    nDaValidare = nConfermati = nAnomali = nLiberi = 0;
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++) {
      switch (st[i]) {
        case BL_LIBERO: nLiberi++; break;
        case BL_DA_VALIDARE: nDaValidare++; break;
        case BL_CONFERMATO: nConfermati++; break;
        case BL_ANOMALO: nAnomali++; break;
        default: break;
      }
    }
  }

  // % di memoria con dati non ancora confermati (da validare + aperto)
  uint8_t pctNonConfermata() const { return (uint8_t)(((uint32_t)nDaValidare + (aperto >= 0 ? 1 : 0)) * 100UL / SWR_N_BLOCCHI); }

  // ---- apertura di un blocco ----
  // Sceglie il blocco libero successivo (ordine ad anello); se non c'e', il confermato piu' vecchio (da cancellare);
  // se non c'e' nemmeno quello: -1 (memoria piena).
  int16_t scegli() const {
    int16_t p = ultimo < 0 ? 0 : (ultimo + 1) % SWR_N_BLOCCHI;
    for (uint16_t k = 0; k < SWR_N_BLOCCHI; k++) {
      uint16_t i = (p + k) % SWR_N_BLOCCHI;
      if (st[i] == BL_LIBERO) return i;
    }
    int16_t m = -1;
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++)
      if (st[i] == BL_CONFERMATO && (m < 0 || seq[i] < seq[m])) m = i;
    return m;
  }

  bool settoreVuoto(uint16_t b) {
    uint8_t buf[SWR_PAGINA];
    for (int p = 0; p < SWR_PAGINE_BLOCCO; p++) {
      if (f->readBuffer((uint32_t)b * SWR_BLOCCO_BYTE + p * SWR_PAGINA, buf, SWR_PAGINA) != SWR_PAGINA) return false;
      for (int k = 0; k < SWR_PAGINA; k++) if (buf[k] != 0xFF) return false;
    }
    return true;
  }

  // Apre un nuovo blocco e vi scrive l'intestazione (pagina 0). Ritorna false: ultimoErrore = AN_PIENA o AN_FLASH.
  bool apri(uint32_t millisRif, uint16_t mv, int8_t temp, uint8_t flag, uint16_t segmento) {
    if (aperto >= 0) chiudi();
    for (int tentativo = 0; tentativo < 4; tentativo++) {
      int16_t b = scegli();
      if (b < 0) { ultimoErrore = AN_PIENA; return false; }
      uint32_t ind = (uint32_t)b * SWR_BLOCCO_BYTE;
      // un confermato si cancella (solo ora che serve); un libero si controlla, e se non e' vuoto (cancellazione interrotta) si cancella
      if (st[b] == BL_CONFERMATO || !settoreVuoto(b)) {
        if (!f->eraseSector(ind) || !settoreVuoto(b)) { st[b] = BL_ANOMALO; ricalcola(); continue; }
      }
      uint8_t h[SWR_PAGINA];
      uint32_t nuovo = maxSeq + 1;
      swrIntestazioneBlocco(h, b * SWR_PAGINE_BLOCCO, millisRif, mv, temp, flag, segmento, nuovo, idTag);
      if (f->writeBuffer(ind, h, SWR_PAGINA) != SWR_PAGINA) { st[b] = BL_ANOMALO; ricalcola(); ultimoErrore = AN_FLASH; return false; }
      st[b] = BL_APERTO; seq[b] = nuovo; maxSeq = nuovo;
      aperto = b; ultimo = b; paginaNext = 1;
      ricalcola();
      ultimoErrore = AN_OK;
      return true;
    }
    ultimoErrore = AN_FLASH;
    return false;
  }

  bool haPosto() const { return aperto >= 0 && paginaNext < SWR_PAGINE_BLOCCO; }
  uint16_t numeroPagina() const { return aperto * SWR_PAGINE_BLOCCO + paginaNext; }

  // Scrive la pagina nel blocco aperto; se era l'ultima il blocco si chiude
  bool scriviPagina(const uint8_t *pag) {
    if (!haPosto()) return false;
    uint32_t ind = (uint32_t)aperto * SWR_BLOCCO_BYTE + paginaNext * SWR_PAGINA;
    if (f->writeBuffer(ind, pag, SWR_PAGINA) != SWR_PAGINA) { ultimoErrore = AN_FLASH; return false; }
    paginaNext++;
    if (paginaNext >= SWR_PAGINE_BLOCCO) chiudi();
    return true;
  }

  void chiudi() {
    if (aperto < 0) return;
    st[aperto] = BL_DA_VALIDARE;
    aperto = -1; paginaNext = 0;
    chiusure = chiusure + 1;
    ricalcola();
  }

  // ---- lettura e conferma ----
  int16_t trovaSeq(uint32_t s) const {
    if (s == 0) return -1;
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++)
      if (seq[i] == s && (st[i] == BL_DA_VALIDARE || st[i] == BL_CONFERMATO)) return i;
    return -1;
  }
  // blocco da validare con seq piu' basso, escludendo fino a due seq (quelli gia' in volo)
  int16_t piuVecchioDaValidare(uint32_t escludi1, uint32_t escludi2) const {
    int16_t m = -1;
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++)
      if (st[i] == BL_DA_VALIDARE && seq[i] != escludi1 && seq[i] != escludi2 && (m < 0 || seq[i] < seq[m])) m = i;
    return m;
  }
  uint32_t seqPiuVecchioDaValidare() const {
    int16_t m = piuVecchioDaValidare(0, 0);
    return m < 0 ? 0 : seq[m];
  }
  bool leggi(uint16_t b, uint16_t off, uint8_t *buf, uint16_t n) {
    return f->readBuffer((uint32_t)b * SWR_BLOCCO_BYTE + off, buf, n) == n;
  }
  // CRC32 del blocco (4096 byte, campo conferma della pagina 0 a 0xFF)
  bool crcBlocco(uint16_t b, uint32_t &crc) {
    uint8_t buf[SWR_PAGINA];
    uint32_t c = 0xFFFFFFFFu;
    for (int p = 0; p < SWR_PAGINE_BLOCCO; p++) {
      if (f->readBuffer((uint32_t)b * SWR_BLOCCO_BYTE + p * SWR_PAGINA, buf, SWR_PAGINA) != SWR_PAGINA) return false;
      if (p == 0) swrConfermaFF(buf);
      c = swrCrc32Aggiorna(c, buf, SWR_PAGINA);
    }
    crc = ~c;
    return true;
  }
  // Marca confermato: scrive la parola 252..255 a 0x00 e rilegge l'intestazione (deve risultare confermata e valida).
  bool conferma(uint16_t b) {
    // parola 252..255 tutta a 0x00: e' l'unico contenuto della parola, quindi la riscrittura non tocca altri dati
    const uint8_t w[SWR_LEN_CONFERMA] = {0x00, 0x00, 0x00, 0x00};
    uint32_t base = (uint32_t)b * SWR_BLOCCO_BYTE;
    if (f->writeBuffer(base + SWR_OFF_CONFERMA, w, SWR_LEN_CONFERMA) != SWR_LEN_CONFERMA) return false;
    uint8_t h[SWR_PAGINA];   // rilettura dell'intera intestazione: conferma presente E intestazione ancora valida
    if (f->readBuffer(base, h, SWR_PAGINA) != SWR_PAGINA || !swrConfermato(h) || !swrIntestazioneBloccoValida(h)) return false;
    st[b] = BL_CONFERMATO;
    ricalcola();
    return true;
  }

  // Mappa 512 x 2 bit (blocco i nei bit 2*(i%4) del byte i/4): 0 libero, 1 aperto (o anomalo), 2 da validare, 3 confermato
  void mappa(uint8_t *out) const {
    memset(out, 0, 128);
    for (uint16_t i = 0; i < SWR_N_BLOCCHI; i++) {
      uint8_t v = 0;
      switch (st[i]) {
        case BL_APERTO: case BL_ANOMALO: v = 1; break;
        case BL_DA_VALIDARE: v = 2; break;
        case BL_CONFERMATO: v = 3; break;
        default: v = 0;
      }
      out[i / 4] |= v << (2 * (i % 4));
    }
  }
};
