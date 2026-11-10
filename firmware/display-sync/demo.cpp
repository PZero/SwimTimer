// Modalita' DEMO (-DSWIM_DEMO=1): niente BLE; 3 tag simulate con dati INVENTATI.
// Le tag simulate producono gli stessi messaggi di una tag vera (annuncio, MAPPA, BLOCCO, FRAMMENTI,
// CONFERMATO, FINE) e li passano a ricezioneNotifica(): da li' in poi la pipeline e' quella reale
// (verifica -> coda SD -> scrittura/rilettura -> CONFERMA -> mappa). I comandi (PRONTO, CONFERMA,
// RIPETI, STOP) tornano a questo file tramite trasportoInvia().
//   tag 0: registra, ogni tanto va "al muro" e scarica
//   tag 1: come la 0 ma ogni 4 blocchi il primo invio e' corrotto (prova RIPETI) e ogni tanto sparisce
//   tag 2: dopo ~70 s annuncia "vado in sonno" e tace (SPENTA), poi si riaccende
#include "protocollo.h"
#if SWIM_DEMO
#include <Arduino.h>
#include "ricezione.h"
#include "stato.h"
#include "trasporto.h"

enum Fase : uint8_t { F_REG, F_MURO, F_SCARICO, F_SPARITA, F_SONNO, F_SPENTA };

struct SimTag {
  uint32_t id;
  uint8_t colore;                     // 0..9 o 0xFF (nessuno)
  char nome[SYNC_NOME_MAX + 1];       // "" = ST-xxxx
  uint8_t batt20;
  uint8_t blocco[SYNC_N_BLOCCHI];     // 0 libero, 1 aperto, 2 da validare, 3 validato
  uint32_t seqDi[SYNC_N_BLOCCHI], crcDi[SYNC_N_BLOCCHI];
  bool inviato[SYNC_N_BLOCCHI], riprova[SYNC_N_BLOCCHI];
  uint16_t aperto = 0;
  uint32_t seqProssimo = 1;
  uint8_t fase = F_REG;
  uint32_t inizioFase = 0, ultimoAnn = 0, ultimoBlocco = 0, prossimoEvento = 0, secReg = 0, inizioReg = 0;
  uint32_t periodoBlocco, sogliaAttesa;
  bool collegata = false, pronto = false;
  int volo[2] = {-1, -1};             // blocchi inviati e non confermati
  int inTx = -1, fr = 0;              // blocco in corso di invio e prossimo frammento
  bool corrompi = false;
  uint8_t erroreSd = 0;
};
static SimTag tg[SYNC_MAX_TAG];
static QueueHandle_t codaCmd;
static uint8_t tmp[SYNC_BLOCCO];

static int attese(const SimTag &t) {
  int n = 0;
  for (int i = 0; i < SYNC_N_BLOCCHI; i++) n += t.blocco[i] == 2;
  return n;
}

// Blocco inventato: 16 pagine .swr (tipo dati, intestazione plausibile, payload pseudo-casuale, CRC16 giusto)
static void generaBlocco(uint32_t id, uint32_t seq, uint8_t *b) {
  uint32_t x = id * 2654435761u + seq * 40503u + 1;
  for (int p = 0; p < SYNC_PAGINE_BLOCCO; p++) {
    uint8_t *pg = b + p * SYNC_PAGINA;
    memset(pg, 0xFF, SYNC_PAGINA);
    for (int i = 16; i < SYNC_PAGINA; i++) { x = x * 1664525u + 1013904223u; pg[i] = x >> 24; }
    pg[0] = 0xD1; pg[1] = 40;
    scrivi16(pg + 2, (seq * 16 + p) & 0xFFFF);
    scrivi32(pg + 4, seq * 3000 + p * 190);
    scrivi16(pg + 8, 3900);
    pg[10] = 24; pg[11] = 0;
    scrivi16(pg + 12, 1);
    paginaSigilla(pg);
  }
  // formato 2: pagina 0 = intestazione di blocco 0xB1 (conferma 0xFF, seq, id), ultime pagine vuote ogni 5 blocchi (fine segmento)
  uint8_t *h = b;
  memset(h, 0xFF, SYNC_PAGINA);
  h[0] = 0xB1; h[1] = 2;
  scrivi16(h + 2, 0); scrivi32(h + 4, seq * 3000); scrivi16(h + 8, 3900); h[10] = 24; h[11] = 0; scrivi16(h + 12, 1);
  scrivi32(h + 17, seq); scrivi32(h + 21, id);
  paginaSigilla(h);
  if (seq % 5 == 0) memset(b + 12 * SYNC_PAGINA, 0xFF, 4 * SYNC_PAGINA);
}

static void annuncia(int i, uint8_t stato) {
  SimTag &t = tg[i];
  int a = attese(t);
  Annuncio an = {t.id, stato, t.batt20, (uint8_t)(a * 100 / SYNC_N_BLOCCHI), 0, (uint16_t)a, (uint16_t)t.secReg, t.seqProssimo - 1,
                 t.colore, {0}};
  strlcpy(an.nome, t.nome, sizeof(an.nome));
  statoAnnuncio(an, -60 - i * 7);
}

static void mandaMappa(int i) {
  SimTag &t = tg[i];
  uint8_t m[LEN_MAPPA];
  m[0] = M_MAPPA;
  scrivi32(m + 1, millis());
  scrivi16(m + 5, t.aperto);
  memset(m + 7, 0, 128);
  for (int b = 0; b < SYNC_N_BLOCCHI; b++) mappaSet(m + 7, b, t.blocco[b]);
  ricezioneNotifica(i, m, sizeof(m));
}

static void inviaBloccoHdr(int i, int b) {
  SimTag &t = tg[i];
  uint8_t m[LEN_BLOCCO];
  m[0] = M_BLOCCO;
  scrivi32(m + 1, t.seqDi[b]);
  scrivi16(m + 5, b);
  scrivi32(m + 7, t.crcDi[b]);
  scrivi32(m + 11, t.seqDi[b] * 3000);
  ricezioneNotifica(i, m, sizeof(m));
  t.inTx = b;
  t.fr = 0;
  t.inviato[b] = true;
  t.corrompi = (i == 1 && t.seqDi[b] % 4 == 0 && !t.riprova[b]);  // la tag 1 sbaglia ogni 4 blocchi, solo la prima volta
}

static void chiudiCollegamento(int i, bool fine) {
  SimTag &t = tg[i];
  if (fine) {
    uint8_t m[5] = {M_FINE};
    scrivi32(m + 1, t.seqProssimo - 1);
    ricezioneNotifica(i, m, sizeof(m));
  }
  ricezioneReset(i);
  { StatoLock l; gStato.tag[i].collegata = false; }
  t.collegata = t.pronto = false;
  t.volo[0] = t.volo[1] = -1;
  t.inTx = -1;
  memset(t.inviato, 0, sizeof(t.inviato));
  t.fase = F_REG;
  t.inizioFase = t.ultimoBlocco = millis();
}

static bool sdOk() {
  StatoLock l;
  return gStato.sd.pronta && gStato.sd.liberiMb >= 50;
}

static void comando(const Comando &c) {
  SimTag &t = tg[c.tag];
  if (!t.collegata) return;
  switch (c.tipo) {
    case M_PRONTO: t.pronto = true; break;
    case M_CONFERMA: {
      for (int k = 0; k < 2; k++) {
        int b = t.volo[k];
        if (b < 0 || t.seqDi[b] != c.seq) continue;
        if (t.crcDi[b] != c.crc) { uint8_t e[2] = {M_ERRORE, 1}; ricezioneNotifica(c.tag, e, 2); break; }
        t.blocco[b] = 3;  // validato: la tag lo puo' riscrivere
        t.volo[k] = -1;
        uint8_t m[5] = {M_CONFERMATO};
        scrivi32(m + 1, c.seq);
        ricezioneNotifica(c.tag, m, 5);
        break;
      }
      break;
    }
    case M_RIPETI:
      for (int k = 0; k < 2; k++) {
        int b = t.volo[k];
        if (b >= 0 && t.seqDi[b] == c.seq) { t.volo[k] = -1; t.inviato[b] = false; t.riprova[b] = true; if (t.inTx == b) t.inTx = -1; }
      }
      break;
    case M_STOP:
      chiudiCollegamento(c.tag, false);
      t.prossimoEvento = millis() + 10000;  // pausa prima di riprovare
      break;
  }
}

static void passoTag(int i, uint32_t ora) {
  SimTag &t = tg[i];
  switch (t.fase) {
    case F_REG:
      if (ora - t.ultimoAnn >= 1000) { t.ultimoAnn = ora; t.secReg = (ora - t.inizioReg) / 1000; annuncia(i, ST_REGISTRA); }
      if (ora - t.ultimoBlocco >= t.periodoBlocco) {  // chiude il blocco aperto e ne apre un altro
        t.ultimoBlocco = ora;
        int b = t.aperto;
        t.blocco[b] = 2;
        t.seqDi[b] = t.seqProssimo++;
        generaBlocco(t.id, t.seqDi[b], tmp);
        t.crcDi[b] = crc32Blocco(tmp, SYNC_BLOCCO);
        t.inviato[b] = t.riprova[b] = false;
        int n = (b + 1) % SYNC_N_BLOCCHI;
        while (t.blocco[n] == 2) n = (n + 1) % SYNC_N_BLOCCHI;  // memoria piena improbabile con questi tempi
        t.aperto = n;
        t.blocco[n] = 1;
      }
      if (attese(t) >= (int)t.sogliaAttesa && ora >= t.prossimoEvento) { t.fase = F_MURO; t.inizioFase = ora; t.ultimoAnn = 0; }
      if (i == 1 && ora >= t.prossimoEvento && ora - t.inizioReg > 30000 && (ora / 1000) % 60 == 45) {
        t.fase = F_SPARITA; t.inizioFase = ora;  // la tag 1 esce dalla portata
      }
      if (i == 2 && ora - t.inizioReg > 70000) {
        t.fase = F_SONNO; t.inizioFase = ora; t.ultimoAnn = 0;
      }
      break;
    case F_MURO:  // tag a portata (testa fuori dall'acqua): il display si collega se la SD e' pronta
      if (ora - t.ultimoAnn >= 50) { t.ultimoAnn = ora; annuncia(i, ST_REGISTRA); }
      if (ora - t.inizioFase > 600 && sdOk()) {
        t.fase = F_SCARICO;
        t.collegata = true;
        { StatoLock l; gStato.tag[i].collegata = true; gStato.tag[i].ultimoStop = 0; }
        mandaMappa(i);
        Comando p = {(uint8_t)i, M_PRONTO, 0, 0, 0};
        trasportoInvia(p);
      } else if (ora - t.inizioFase > 20000) { t.fase = F_REG; t.ultimoBlocco = ora; t.prossimoEvento = ora + 5000; }
      break;
    case F_SCARICO: {
      if (!t.pronto) break;
      if (t.inTx >= 0) {  // 4 frammenti ogni passo (~25 KB/s)
        generaBlocco(t.id, t.seqDi[t.inTx], tmp);
        for (int k = 0; k < 4 && t.fr < SYNC_N_FRAMMENTI; k++, t.fr++) {
          uint8_t m[LEN_FRAMMENTO];
          m[0] = M_FRAMMENTO;
          scrivi32(m + 1, t.seqDi[t.inTx]);
          m[5] = t.fr;
          memcpy(m + 6, tmp + t.fr * SYNC_FRAMMENTO, SYNC_FRAMMENTO);
          if (t.corrompi && t.fr == 5) m[6 + 17] ^= 0x40;  // un bit sbagliato
          ricezioneNotifica(i, m, sizeof(m));
          if (t.collegata == false) return;  // STOP arrivato nel frattempo
        }
        if (t.fr >= SYNC_N_FRAMMENTI) { t.inTx = -1; }
        break;
      }
      int vol = (t.volo[0] >= 0) + (t.volo[1] >= 0);
      int prossimo = -1;  // blocco da validare piu' vecchio non ancora inviato (per seq)
      for (int b = 0; b < SYNC_N_BLOCCHI; b++)
        if (t.blocco[b] == 2 && !t.inviato[b] && (prossimo < 0 || t.seqDi[b] < t.seqDi[prossimo])) prossimo = b;
      if (prossimo >= 0 && vol < SYNC_FINESTRA) {
        for (int k = 0; k < 2; k++) if (t.volo[k] < 0) { t.volo[k] = prossimo; break; }
        inviaBloccoHdr(i, prossimo);
      } else if (prossimo < 0 && vol == 0) {
        chiudiCollegamento(i, true);  // FINE
      }
      break;
    }
    case F_SPARITA:  // fuori portata 14 s: niente annunci
      if (ora - t.inizioFase > 14000) { t.fase = F_REG; t.prossimoEvento = ora + 20000; t.ultimoBlocco = ora; }
      break;
    case F_SONNO:  // "vado in sonno" per ~2 s, poi silenzio
      if (ora - t.ultimoAnn >= 100) { t.ultimoAnn = ora; annuncia(i, ST_SONNO); }
      if (ora - t.inizioFase > 2000) { t.fase = F_SPENTA; t.inizioFase = ora; }
      break;
    case F_SPENTA:
      if (ora - t.inizioFase > 40000) { t.fase = F_REG; t.inizioReg = t.ultimoBlocco = ora; }
      break;
  }
}

static void demoTask(void *) {
  uint32_t ultimo = 0;
  for (;;) {
    Comando c;
    while (xQueueReceive(codaCmd, &c, 0) == pdTRUE) comando(c);
    uint32_t ora = millis();
    if (ora - ultimo >= 20) {
      ultimo = ora;
      for (int i = 0; i < SYNC_MAX_TAG; i++) passoTag(i, ora);
      static uint32_t ultimoSec = 0;
      if (ora - ultimoSec >= 1000) {
        ultimoSec = ora;
        for (int i = 0; i < SYNC_MAX_TAG; i++) {
          uint32_t b = ricezioneByteAcc(i);
          StatoLock l;
          gStato.tag[i].bps = b;
        }
      }
    }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

void trasportoInit() {
  codaCmd = xQueueCreate(32, sizeof(Comando));
  const uint32_t ids[3] = {0x1000A3F2, 0x20007C10, 0x3000E95B};
  const uint8_t bat[3] = {200, 190, 180};
  const uint32_t periodo[3] = {2500, 3500, 3000}, soglia[3] = {5, 4, 4};
  for (int i = 0; i < SYNC_MAX_TAG; i++) {
    SimTag &t = tg[i];
    memset(t.blocco, 0, sizeof(t.blocco));
    t.id = ids[i];
    // nomi e colori inventati: tag 1 = "Lorenzo" arancione, tag 2 = nome lungo viola, tag 3 senza (ST-xxxx e colore dello spicchio)
    const uint8_t col[3] = {1, 2, SYNC_COLORE_NESSUNO};
    const char *nomi[3] = {"Lorenzo", "Giulia Rossi 2", ""};
    t.colore = col[i];
    strlcpy(t.nome, nomi[i], sizeof(t.nome));
    t.batt20 = bat[i];
    t.periodoBlocco = periodo[i];
    t.sogliaAttesa = soglia[i];
    t.blocco[0] = 1;
    // alcuni blocchi gia' validati per riempire la mappa (come dopo allenamenti precedenti)
    for (int b = 1; b < 60 + i * 40; b++) { t.blocco[b] = 3; t.seqDi[b] = t.seqProssimo++; }
    t.aperto = 60 + i * 40;
    t.blocco[t.aperto] = 1;
    t.blocco[0] = 3; t.seqDi[0] = t.seqProssimo++;
    t.prossimoEvento = 8000 + i * 4000;
    t.inizioReg = t.ultimoBlocco = millis();
  }
  xTaskCreatePinnedToCore(demoTask, "demo", 8192, nullptr, 2, nullptr, 0);
  LOGF("DEMO: 3 tag simulate (dati inventati)\n");
}

bool trasportoInvia(const Comando &c) { return xQueueSend(codaCmd, &c, 0) == pdTRUE; }

void trasportoChiudi(int tag) {
  // La demo chiude dal proprio task per non toccare lo stato da due parti
  Comando c = {(uint8_t)tag, M_STOP, 0, 0, 0};
  xQueueSend(codaCmd, &c, 0);
}

#endif  // SWIM_DEMO
