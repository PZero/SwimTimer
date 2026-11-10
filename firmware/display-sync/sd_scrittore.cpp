// Scrittore SD. Regola: CONFERMA solo dopo scrittura + flush/chiusura + rilettura dalla SD + CRC32 uguale.
// Struttura: /swim/sessione.txt (numero di avvio, per avvii.txt), /swim/<id 8 hex>/tag.swr (TUTTI i blocchi della tag, in coda;
// fino al 2026-11-10 un file sNNNN.swr per avvio),
// tag.idx (una riga "seq,offset,crc32,stato"), tag.anomalia (stesso seq con CRC diverso).
#include <Arduino.h>
#include <SD_MMC.h>
#include "sd_scrittore.h"
#include "scheda.h"
#include "stato.h"
#include "trasporto.h"

static const uint32_t MIN_LIBERO_MB = 50;
static const int N_NOTI = 1024;  // (seq, crc) salvati per tag, per riconoscere i doppioni

struct Voce { uint32_t seq, crc; };
struct Noti {
  Voce *v = nullptr;
  uint16_t n = 0, testa = 0;
  bool caricato = false;
};
struct Pendente { uint32_t seq, crc, off; bool uso; };

static QueueHandle_t coda;
static uint8_t *bufVerifica;          // rilettura dalla SD
static bool montata = false;
static uint32_t sessione = 0;
static Noti noti[SYNC_MAX_TAG];
static Pendente pend[SYNC_MAX_TAG][8];  // scritti, in attesa di CONFERMATO
static uint8_t tentativi[SYNC_MAX_TAG];
static uint32_t seqTent[SYNC_MAX_TAG];

static void sdImposta(bool pronta, uint8_t err) {
  StatoLock l;
  gStato.sd.pronta = pronta;
  gStato.sd.errore = err;
}

static void sdSpazio() {
  uint64_t tot = SD_MMC.totalBytes(), usati = SD_MMC.usedBytes();  // FatFs tiene il conteggio in cache
  uint32_t liberi = (tot > usati) ? (uint32_t)((tot - usati) >> 20) : 0;
  StatoLock l;
  gStato.sd.totaleMb = (uint32_t)(tot >> 20);
  gStato.sd.liberiMb = liberi;
  if (liberi < MIN_LIBERO_MB) { gStato.sd.pronta = false; gStato.sd.errore = SD_PIENA; }
  else if (gStato.sd.errore == SD_PIENA) { gStato.sd.pronta = true; gStato.sd.errore = SD_OK; }
}

static void sdSmonta() {
  SD_MMC.end();
  montata = false;
}

// Dopo il montaggio: cartella /swim e numero di sessione (incrementato a ogni avvio)
static bool sdPrepara() {
  if (SD_MMC.cardType() == CARD_NONE) return false;
  SD_MMC.mkdir("/swim");
  if (!sessione) {
    uint32_t n = 0;
    File f = SD_MMC.open("/swim/sessione.txt", FILE_READ);
    if (f) { n = f.parseInt(); f.close(); }
    sessione = n + 1;
    File w = SD_MMC.open("/swim/sessione.txt", FILE_WRITE);
    if (!w) { sessione = 0; return false; }
    w.printf("%lu\n", (unsigned long)sessione);
    w.close();
    // registro degli avvii: serve a scoprire i riavvii non voluti (watchdog, panic, calo di tensione)
    static const char *nomi[] = {"?", "accensione", "esterno", "software", "panic", "wdt int", "wdt task", "wdt", "sonno", "calo tensione", "sdio"};
    int r = (int)esp_reset_reason();
    const char *nm = (r >= 0 && r <= 10) ? nomi[r] : "?";
    File a = SD_MMC.open("/swim/avvii.txt", FILE_APPEND);
    if (a) { a.printf("sessione %lu: %s (%d)\n", (unsigned long)sessione, nm, r); a.close(); }
    LOGF("avvio: %s (%d)\n", nm, r);
    StatoLock l;
    gStato.sd.sessione = sessione;
  }
  montata = true;
  sdImposta(true, SD_OK);
  sdSpazio();
  LOGF("SD pronta: sessione %lu, liberi %lu MB\n", (unsigned long)sessione, (unsigned long)gStato.sd.liberiMb);
  return true;
}

// Nuovo tentativo di montaggio (SD inserita dopo l'avvio o rimossa e rimessa)
static void sdRiprova() {
  SD_MMC.setPins(BOARD_SDMMC_SCK, BOARD_SDMMC_CMD, BOARD_SDMMC_DAT);
  if (SD_MMC.begin("/sdcard", true, false) && sdPrepara()) return;
  SD_MMC.end();
  sdImposta(false, SD_ASSENTE);
}

// Battito: la SD risponde ancora? Aggiorna anche lo spazio libero.
static void sdControlla() {
  File d = SD_MMC.open("/swim");
  if (!d) { sdSmonta(); sdImposta(false, SD_ASSENTE); return; }
  d.close();
  sdSpazio();
}

static void percorsoTag(int tag, char *dir) {
  uint32_t id;
  { StatoLock l; id = gStato.tag[tag].id; }
  snprintf(dir, 32, "/swim/%08lx", (unsigned long)id);
}

static void riga(const char *path, uint32_t seq, uint32_t off, uint32_t crc, const char *st) {
  File f = SD_MMC.open(path, FILE_APPEND);
  if (!f) return;
  if (off == UINT32_MAX) f.printf("%lu,-1,%08lx,%s\n", (unsigned long)seq, (unsigned long)crc, st);
  else f.printf("%lu,%lu,%08lx,%s\n", (unsigned long)seq, (unsigned long)off, (unsigned long)crc, st);
  f.close();
}

static void notiAggiungi(int tag, uint32_t seq, uint32_t crc) {
  Noti &n = noti[tag];
  if (!n.v) return;
  n.v[n.testa] = {seq, crc};
  n.testa = (n.testa + 1) % N_NOTI;
  if (n.n < N_NOTI) n.n++;
}

// 0 = sconosciuto, 1 = doppione (stesso CRC), 2 = anomalia (stesso seq, CRC diverso)
static int notiCerca(int tag, uint32_t seq, uint32_t crc) {
  Noti &n = noti[tag];
  int r = 0;
  if (!n.v) return 0;
  for (int i = 0; i < n.n; i++)
    if (n.v[i].seq == seq) {
      if (n.v[i].crc == crc) return 1;
      r = 2;
    }
  return r;
}

// Alla prima connessione di una tag rilegge i suoi indici per riconoscere i blocchi gia' salvati
static void notiCarica(int tag, const char *dir) {
  Noti &n = noti[tag];
  if (n.caricato) return;
  n.caricato = true;
  if (!n.v) return;
  File d = SD_MMC.open(dir);
  if (!d) return;
  for (File e = d.openNextFile(); e; e = d.openNextFile()) {
    String nome = e.name();
    if (!nome.endsWith(".idx")) { e.close(); continue; }
    char buf[64];
    while (e.available()) {
      int k = e.readBytesUntil('\n', buf, sizeof(buf) - 1);
      buf[k] = 0;
      unsigned long seq, crc;
      long off;
      char st[16] = "";
      if (sscanf(buf, "%lu,%ld,%lx,%15s", &seq, &off, &crc, st) == 4 && !strcmp(st, "scritto")) notiAggiungi(tag, seq, crc);
    }
    e.close();
  }
  d.close();
}

// Scrive in coda al file, chiude, riapre, rilegge e confronta il CRC32 (dalla SD, non dalla cache)
static bool scriviVerifica(const char *path, const uint8_t *buf, uint32_t crc, uint32_t &off, uint8_t &err) {
  File f = SD_MMC.open(path, FILE_APPEND);
  if (!f) { err = SD_ERR_SCRITTURA; return false; }
  size_t w = f.write(buf, SYNC_BLOCCO);
  f.flush();
  f.close();
  if (w != SYNC_BLOCCO) { err = SD_ERR_SCRITTURA; return false; }
  File r = SD_MMC.open(path, FILE_READ);
  if (!r) { LOGF("rilettura: open fallita\n"); err = SD_ERR_RILETTURA; return false; }
  // offset dalla dimensione del file riaperto (size() del file in append col core 2.0.x puo' valere spazzatura)
  size_t dim = r.size();
  off = dim >= SYNC_BLOCCO ? dim - SYNC_BLOCCO : 0;
  bool okSeek = dim >= SYNC_BLOCCO && r.seek(off);
  size_t letti = okSeek ? r.read(bufVerifica, SYNC_BLOCCO) : 0;
  r.close();
  if (!okSeek || letti != SYNC_BLOCCO) {
    LOGF("rilettura: off %lu dim %u seek %d letti %u\n", (unsigned long)off, (unsigned)dim, okSeek, (unsigned)letti);
    err = SD_ERR_RILETTURA;
    return false;
  }
  if (crc32Blocco(bufVerifica, SYNC_BLOCCO) != crc) {
    // diagnosi: la sorgente e' cambiata durante la scrittura, o la SD ha restituito altro?
    int primo = -1, diversi = 0;
    for (int i = 0; i < SYNC_BLOCCO; i++)
      if (bufVerifica[i] != buf[i]) { if (primo < 0) primo = i; diversi++; }
    LOGF("rilettura: off %lu crcAtteso %08lx crcSorgente %08lx crcLetto %08lx primo %d diversi %d\n",
         (unsigned long)off, (unsigned long)crc, (unsigned long)crc32Blocco(buf, SYNC_BLOCCO),
         (unsigned long)crc32Blocco(bufVerifica, SYNC_BLOCCO), primo, diversi);
    err = SD_ERR_RILETTURA;
    return false;
  }
  return true;
}

static void invia(int tag, uint8_t tipo, uint32_t seq, uint32_t crc, uint8_t motivo) {
  Comando c = {(uint8_t)tag, tipo, motivo, seq, crc};
  trasportoInvia(c);
}

static void fermaTag(int tag, uint8_t motivo) {
  invia(tag, M_STOP, 0, 0, motivo);
  trasportoChiudi(tag);
  StatoLock l;
  gStato.tag[tag].ultimoStop = motivo;
}

// Blocco non valido (CRC, pagine, frammenti mancanti): RIPETI, dopo 3 tentativi STOP motivo 3
static void fallito(int tag, uint32_t seq) {
  { StatoLock l; gStato.tag[tag].errCrc++; }
  if (seqTent[tag] != seq) { seqTent[tag] = seq; tentativi[tag] = 0; }
  if (++tentativi[tag] > SYNC_MAX_TENTATIVI) { fermaTag(tag, STOP_TROPPI_ERRORI); return; }
  invia(tag, M_RIPETI, seq, 0, 0);
}

static void salvaBlocco(const Lavoro &w) {
  int tag = w.tag;
  uint8_t *b = ricezioneBuffer(tag, w.slot);
  IntestazioneBlocco h = ricezioneIntestazione(tag, w.slot);

  // 1. verifica: CRC32 del blocco contro BLOCCO, CRC16 di ogni pagina
  if (crc32Blocco(b, SYNC_BLOCCO) != h.crc || !bloccoPagineValide(b)) {
    ricezioneLibera(tag, w.slot);
    fallito(tag, h.seq);
    return;
  }
  // 2. SD pronta e con spazio, altrimenti niente conferma
  bool pronta;
  uint8_t err;
  { StatoLock l; pronta = gStato.sd.pronta; err = gStato.sd.errore; }
  if (!pronta || !montata) {
    ricezioneLibera(tag, w.slot);
    fermaTag(tag, err == SD_PIENA ? STOP_SD_PIENA : STOP_ERRORE_SD);
    return;
  }
  char dir[32], path[64], idx[64];
  percorsoTag(tag, dir);
  SD_MMC.mkdir(dir);
  notiCarica(tag, dir);
  int dup = notiCerca(tag, h.seq, h.crc);
  Pendente *p = nullptr;
  for (auto &x : pend[tag]) if (!x.uso) { p = &x; break; }
  if (!p) p = &pend[tag][0];  // improbabile: la finestra e' 2
  p->uso = true; p->seq = h.seq; p->crc = h.crc; p->off = UINT32_MAX;

  if (dup != 1) {  // doppione = solo conferma, niente scrittura
    // un file per tag (non per avvio del display): la registrazione resta intera e si legge da sola
    snprintf(idx, sizeof(idx), "%s/tag.idx", dir);
    snprintf(path, sizeof(path), dup == 2 ? "%s/tag.anomalia" : "%s/tag.swr", dir);
    uint8_t e = SD_OK;
    uint32_t off = 0;
    if (!scriviVerifica(path, b, h.crc, off, e)) {
      LOGF("tag %d: SD errore %u su seq %lu\n", tag, e, (unsigned long)h.seq);
      p->uso = false;
      ricezioneLibera(tag, w.slot);
      sdImposta(false, e);
      sdSmonta();  // si riprova a montare piu' tardi
      fermaTag(tag, STOP_ERRORE_SD);
      return;
    }
    p->off = off;
    riga(idx, h.seq, off, h.crc, dup == 2 ? "anomalia" : "scritto");
    if (dup == 2) { StatoLock l; gStato.tag[tag].anomalie++; }
    else notiAggiungi(tag, h.seq, h.crc);
  }
  ricezioneLibera(tag, w.slot);
  { StatoLock l; gStato.tag[tag].salvati++; }
  tentativi[tag] = 0;
  invia(tag, M_CONFERMA, h.seq, h.crc, 0);  // 3. solo ora la tag puo' liberare il blocco
}

static void confermato(const Lavoro &w) {
  for (auto &x : pend[w.tag])
    if (x.uso && x.seq == w.seq) {
      char dir[32], idx[64];
      percorsoTag(w.tag, dir);
      snprintf(idx, sizeof(idx), "%s/tag.idx", dir);
      riga(idx, x.seq, x.off, x.crc, "confermato");
      x.uso = false;
      return;
    }
}

static void sdTask(void *) {
  uint32_t ultimo = 0;
  for (;;) {
    Lavoro w;
    if (xQueueReceive(coda, &w, pdMS_TO_TICKS(500)) == pdTRUE) {
      switch (w.tipo) {
        case L_BLOCCO: salvaBlocco(w); break;
        case L_FALLITO: fallito(w.tag, w.seq); break;
        case L_CONFERMATO: confermato(w); break;
      }
    }
    uint32_t ora = millis();
    if (ora - ultimo >= 5000) {  // battito della SD
      ultimo = ora;
      if (montata) sdControlla();
      else sdRiprova();
    }
  }
}

void sdAccoda(const Lavoro &l) {
  if (xQueueSend(coda, &l, 0) != pdTRUE) {
    LOGF("coda SD piena: lavoro perso (tag %d)\n", l.tag);
    if (l.tipo == L_BLOCCO) ricezioneLibera(l.tag, l.slot);
  }
}

void sdInit() {
  coda = xQueueCreate(16, sizeof(Lavoro));
  bufVerifica = (uint8_t *)ps_malloc(SYNC_BLOCCO);
  for (int i = 0; i < SYNC_MAX_TAG; i++) noti[i].v = (Voce *)ps_malloc(sizeof(Voce) * N_NOTI);
  // Prima volta: installSD() abilita il CS sull'espansore XL9555 (IO7) e monta SD_MMC a 1 bit
  if (panel.installSD()) montata = sdPrepara();
  if (!montata) sdImposta(false, SD_ASSENTE);
  xTaskCreatePinnedToCore(sdTask, "sd", 8192, nullptr, 3, nullptr, 0);
}
