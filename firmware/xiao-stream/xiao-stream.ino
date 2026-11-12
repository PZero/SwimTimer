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
#include "swr_tipi.h"          // struct CtxGuasto e RecDiario (fuori dallo sketch: il generatore di prototipi di Arduino le userebbe prima di definirle)
#include "swr_fifo.h"          // lettura del FIFO con controllo dell'allineamento (provata con fifo_sim.py)
#include "swr_sync.h"          // costanti e messaggi del protocollo di sincronizzazione (identici a display-sync/protocollo.h)
#include <flash/flash_nrf5x.h>   // scrittura flash compatibile con il SoftDevice (sd_flash_*)

#ifndef PROVE_GUASTI
#define PROVE_GUASTI 0          // predefinito 0 (rilascio). Per la prova a secco: compilare con -DPROVE_GUASTI=1 (versione "0.6.1-prove")
#endif
#define VER_NUM "0.6.3"
#if PROVE_GUASTI
#define VER_SUF "-prove"        // la build di prova si riconosce da VERSIONE, dal diario (AVV ... PROVE) e dalla pagina di segmento ("0.6.1p")
#define VER_SEG "p"
#else
#define VER_SUF ""
#define VER_SEG ""
#endif
#define VERSIONE "xiao-" VER_NUM VER_SUF
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
#define VBUS_ATTESA_AVVIO_MS 1000  // avvio causato dall'USB: attesa massima perche' VBUSDETECT si assesti
#define VBUS_ASSENZA_N 20          // USB staccata = 20 letture consecutive senza VBUS, una ogni 100 ms (2 s)
#define QUIETE_REG_S 180         // la registrazione si chiude dopo tanti secondi "abbastanza fermo" (soglie QUIETE_*)
#define BAT_MIN_AVVIO_MV 3400    // sotto questa tensione al risveglio non si registra
#define BAT_STOP_MV 3300         // sotto questa tensione (3 letture di fila, ogni 5 s) la registrazione si chiude
// (Correzione 0.6.1: RESETREAS lo azzera il core in init(), non il bootloader; la copia e' in readResetReason(), vedi setup().)
// Prima di ogni System OFF si scrive questa marca in GPREGRET2 (che il bootloader non tocca); all'avvio la si legge.
#define MARCA_SLEEP 0xB7
// ---- 0.6.1: regole di modo, ripresa automatica, watchdog, diario, prove (vedi LEGGIMI.md, sezione "0.6.1") ----
// Marca "registrazione in corso" in GPREGRET2 (0xD0 | numero di riprese consecutive, 0..15): scritta all'avvio della registrazione, sostituita da
// MARCA_SLEEP alla chiusura ordinata. Se al boot (senza USB) c'e' ancora, la tag si e' riavviata registrando: riprende da sola.
// Il bootloader Adafruit NON usa GPREGRET2 (solo GPREGRET, con i valori 0xB1 0xA8 0x4E 0x57 0x6D): fonte main.c 0.6.2.
#define MARCA_REGISTRA 0xD0
#define MAX_RIPRESE 3            // riprese automatiche consecutive senza una chiusura ordinata, poi sonno con annuncio ERRORE
#define WDT_SECONDI 8            // timeout del watchdog hardware (servito da cane() in ogni loop e attesa lunga)
// PROVE_GUASTI = 1: comandi di prova PROVA_CRASH (HardFault vero), PROVA_BLOCCO (ciclo infinito: scatta il watchdog), PROVA_RESET
// (reset software). Si accettano sulla caratteristica COMANDI 0004 (APERTA: chiunque in portata puo' mandarli) anche in registrazione, e
// sulla seriale. Servono alla prova a secco: PORTARE A 0 PER IL RILASCIO.

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
static bool inVasca = false;           // modalita' vasca (registrazione): niente LED di collegamento, solo il comando SLEEP
static volatile bool sonnoDaSync = false;      // M_SONNO ricevuto in modalita' normale: il loop chiama vaInSospensione()
static volatile bool sonnoRichiesto = false;  // SLEEP ricevuto in registrazione: chiude il segmento e va in sonno
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
static bool annErrore = false;         // annuncia ST_ERRORE (riprese esaurite) prima di dormire
static volatile uint16_t diaInvioN = 0;   // record del diario ancora da mandare via BLE (comando DIARIO)
static void notificaTutti(BLECharacteristic &c, const void *p, uint16_t n);
static bool sdAttivo() { uint8_t e = 0; sd_softdevice_is_enabled(&e); return e != 0; }

// ================= 0.6.1: watchdog hardware e contesto del guasto =================
// WDT dell'nRF52: una volta avviato non si ferma fino al reset; CONFIG.SLEEP = Run (continua a contare mentre la CPU dorme nel
// FreeRTOS idle, altrimenti non scatterebbe mai), HALT = Pause. Timeout = (CRV+1)/32768 s. Si serve scrivendo 0x6E524635 in RR[0].
// ---- Tempo di sessione continuo dopo le riprese (0.6.1) ----
// Dopo un riavvio millis() riparte da 0. Per mantenere la sincronizzazione con il video ogni segmento ripreso salva nella pagina di segmento
// lo SCARTO (ms) da sommare ai suoi millis per avere il tempo di sessione: scarto = scarto del segmento precedente + istante del reset
// (millis del vecchio avvio) + T_AVVIO_MS (tempo fra il reset e millis() = 0 del nuovo avvio, bootloader compreso, MISURATO con
// misura_avvio.py). L'istante del reset lo salvano HardFault_Handler e l'IRQ del watchdog (origine "gestore", esatto); senza gestore
// (assert del SoftDevice, reset software, lockup) si usa l'ultimo servizio del watchdog (cane(): "ultimo vivo") piu' 8 s se la causa
// e' il watchdog. RAM persa (brownout, System OFF) = origine "sconosciuta": il tempo NON e' continuo. Il blocco sta in RAM NOBITS come il
// contesto del guasto; i contatori cambiano solo all'avvio (checksum), msReset e msVivo si aggiornano senza checksum.
#define TEMPO_MAGIC 0x54454D50UL
#define TF_RESET_VALIDO 1                  // msReset scritto da un gestore di guasto
#define TF_PERSO 2                         // continuita' persa nella catena di riprese
#ifndef T_AVVIO_MS
#define T_AVVIO_MS 500                     // MISURATO 2026-11-11 con USB seriale (misura_avvio.py): crash 495,0-518,1 ms (media 499,8, n=10), watchdog 495,2-496,0 (media 495,6, n=6)
#endif
#define T_AVVIO_ERR_MS 30                  // incertezza di T_AVVIO_MS: scarto massimo misurato da 500 ms e variazione min-max (23 ms)
static CtxTempo ctxTempo __attribute__((section(".noinit,\"aw\",%nobits@")));
static uint32_t tempoChk(const CtxTempo &t) { return t.magic ^ t.nAvvii ^ t.scarto ^ t.margine ^ 0x5A5A1234UL; }
static volatile bool wdtSospeso = false;   // vero = non si serve piu' il watchdog (flusso dati fermo in registrazione): scattera' il reset e la ripresa
static inline void cane() {                // serve il watchdog (ricarica) e segna "ultimo vivo" per il tempo di sessione
  if (wdtSospeso) return;
  NRF_WDT->RR[0] = 0x6E524635UL;
  ctxTempo.msVivo = millis();
}
static void wdtAvvia() {
  NRF_WDT->CONFIG = (WDT_CONFIG_SLEEP_Run << WDT_CONFIG_SLEEP_Pos) | (WDT_CONFIG_HALT_Pause << WDT_CONFIG_HALT_Pos);
  NRF_WDT->CRV = WDT_SECONDI * 32768UL - 1;
  NRF_WDT->RREN = WDT_RREN_RR0_Enabled << WDT_RREN_RR0_Pos;
  NRF_WDT->EVENTS_TIMEOUT = 0;
  NRF_WDT->INTENSET = WDT_INTENSET_TIMEOUT_Msk;       // l'evento TIMEOUT arriva ~2 cicli di LFCLK (61 us) prima del reset: basta a salvare PC e LR
  NVIC_SetPriority(WDT_IRQn, 3);                      // 0, 1 e 4 sono del SoftDevice
  NVIC_ClearPendingIRQ(WDT_IRQn);
  NVIC_EnableIRQ(WDT_IRQn);
  NRF_WDT->TASKS_START = 1;
  cane();
}

// Contesto del guasto in RAM "noinit" (fuori da .data/.bss: lo startup non lo azzera; con il reset la RAM si conserva se il
// bootloader non la sporca: verificato in prova, vedi LEGGIMI). Valido solo se magic e checksum tornano. Letto e azzerato al boot.
#define CTX_MAGIC 0x53474C31UL
static CtxGuasto ctxRam __attribute__((section(".noinit,\"aw\",%nobits@")));
static uint32_t faseRam __attribute__((section(".noinit,\"aw\",%nobits@")));      // ultima "fase" del programma (0x5A5A5A00 | n): dove si trovava prima del guasto
#define FASE(n) (faseRam = 0x5A5A5A00UL | (uint32_t)(n))
static uint32_t ctxChk(const CtxGuasto &c) { return c.magic ^ c.tipo ^ c.pc ^ c.lr ^ c.cfsr ^ c.hfsr ^ c.fase ^ 0xA5A5A5A5UL; }
static void ctxSalva(uint32_t tipo, uint32_t pc, uint32_t lr) {
  ctxRam.tipo = tipo; ctxRam.pc = pc; ctxRam.lr = lr;
  ctxRam.cfsr = SCB->CFSR; ctxRam.hfsr = SCB->HFSR;
  ctxRam.fase = ((faseRam & 0xFFFFFF00UL) == 0x5A5A5A00UL) ? (faseRam & 0xFF) : 0;
  ctxRam.magic = CTX_MAGIC;
  ctxRam.chk = ctxChk(ctxRam);
  if (ctxTempo.magic == TEMPO_MAGIC) { ctxTempo.msReset = millis(); ctxTempo.flags |= TF_RESET_VALIDO; }   // istante del reset (tempo di sessione)
}
static inline bool spValido(const uint32_t *sp) { return (uint32_t)sp >= 0x20000000UL && (uint32_t)sp < 0x2003FFE0UL && !((uint32_t)sp & 3); }
// HardFault: sostituisce quello del core (che faceva solo NVIC_SystemReset). Salva PC e LR del frame di eccezione e riavvia.
extern "C" __attribute__((used, noreturn)) void guastoC(uint32_t *sp) {
  if (spValido(sp)) ctxSalva(SWR_GUASTO_HARDFAULT, sp[6], sp[5]); else ctxSalva(SWR_GUASTO_HARDFAULT, 0, 0);
  NVIC_SystemReset();
  while (true) {}
}
extern "C" __attribute__((naked)) void HardFault_Handler(void) {
  __asm volatile("tst lr, #4\n\t"
                 "ite eq\n\t"
                 "mrseq r0, msp\n\t"
                 "mrsne r0, psp\n\t"
                 "b guastoC\n\t");
}
// Watchdog: l'IRQ TIMEOUT scatta pochi microsecondi prima del reset; salva PC e LR di dove era bloccato il programma
extern "C" __attribute__((used)) void wdtIsrC(uint32_t *sp) {
  NRF_WDT->EVENTS_TIMEOUT = 0;
  if (spValido(sp)) ctxSalva(SWR_GUASTO_WDT, sp[6], sp[5]); else ctxSalva(SWR_GUASTO_WDT, 0, 0);
}
extern "C" __attribute__((naked)) void WDT_IRQHandler(void) {
  __asm volatile("tst lr, #4\n\t"
                 "ite eq\n\t"
                 "mrseq r0, msp\n\t"
                 "mrsne r0, psp\n\t"
                 "push {r4, lr}\n\t"
                 "bl wdtIsrC\n\t"
                 "pop {r4, pc}\n\t");
}
// Dati del boot corrente (compilati in setup(), usati nel diario e nella pagina di segmento)
static uint32_t bootRr = 0;                 // RESETREAS grezzo (letto dal core in init() prima di azzerarlo: readResetReason())
static uint8_t bootMarca = 0;               // GPREGRET2 all'avvio
static CtxGuasto bootCtx;                   // contesto salvato dal guasto precedente (se valido)
static bool bootCtxValido = false;
static uint8_t bootGuasto = SWR_GUASTO_NESSUNO, bootFase = 0;
// tempo di sessione di questo avvio (calcolato in tempoAvvio(), scritto nella pagina di segmento)
static uint32_t bootScarto = 0, bootResetMs = 0;         // scarto (ms) e istante del reset precedente usato (millis del vecchio avvio)
static uint16_t bootMargine = 0;                         // margine d'errore cumulato (ms)
static uint8_t bootNAvvii = 1, bootOrigScarto = SWR_TORIG_NESSUNA;
static bool bootGestore = false;                         // l'istante del reset precedente l'ha scritto un gestore di guasto (anche se la catena e' persa)
// Calcola lo scarto di questo avvio dal blocco lasciato dall'avvio precedente e lo riscrive per il prossimo.
static void tempoAvvio(uint32_t rr) {
  CtxTempo &t = ctxTempo;
  bool valido = t.magic == TEMPO_MAGIC && t.chk == tempoChk(t);
  uint32_t scarto = 0, margine = 0, avvii = 1, flags = 0;
  if (!valido) {                                           // RAM persa: prima accensione, brownout, uscita da System OFF
    bootOrigScarto = SWR_TORIG_SCONOSCIUTA; flags = TF_PERSO; bootResetMs = 0;
  } else {
    avvii = t.nAvvii + 1;
    margine = t.margine;
    bootGestore = (t.flags & TF_RESET_VALIDO) != 0;
    if (t.flags & TF_RESET_VALIDO) { bootOrigScarto = SWR_TORIG_GESTORE; bootResetMs = t.msReset; margine += T_AVVIO_ERR_MS; }
    else {
      bootOrigScarto = SWR_TORIG_VIVO;
      bootResetMs = t.msVivo + ((rr & POWER_RESETREAS_DOG_Msk) ? WDT_SECONDI * 1000UL : 0);       // il watchdog scatta 8 s dopo l'ultimo servizio
      margine += T_AVVIO_ERR_MS + 60;
    }
    if (t.flags & TF_PERSO) { bootOrigScarto = SWR_TORIG_SCONOSCIUTA; flags = TF_PERSO; }         // la catena aveva gia' perso la continuita'
    else scarto = t.scarto + bootResetMs + T_AVVIO_MS;
  }
  bootScarto = scarto; bootMargine = margine > 0xFFFE ? 0xFFFE : (uint16_t)margine; bootNAvvii = avvii > 255 ? 255 : (uint8_t)avvii;
  t.magic = TEMPO_MAGIC; t.nAvvii = avvii; t.scarto = scarto; t.margine = margine; t.flags = flags; t.msReset = 0; t.msVivo = 0;
  t.chk = tempoChk(t);
}
// Partenza a tocchi: una nuova sessione, il tempo comincia da qui (scarto 0, nessun margine)
static void tempoNuovaCatena() {
  CtxTempo &t = ctxTempo;
  bootScarto = 0; bootMargine = 0; bootNAvvii = 1; bootOrigScarto = SWR_TORIG_NESSUNA; bootResetMs = 0;
  t.magic = TEMPO_MAGIC; t.nAvvii = 1; t.scarto = 0; t.margine = 0; t.flags = 0; t.msReset = 0; t.msVivo = 0;
  t.chk = tempoChk(t);
}
static bool bootWdtGiaAttivo = false;       // il WDT risultava gia' avviato al boot (sopravvissuto al reset?)
static uint8_t sonnoMotivo = 0;             // perche' si va in sonno (diario): 1 comando, 2 quiete, 3 batteria, 4 USB staccata

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
  if (diaInvioN) return;               // DIARIO in corso: prima si manda quello (diarioInvioServi)
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

// ---------------- Diario persistente (0.6.1) ----------------
// File /dia.bin dell'InternalFS (stessa flash interna di bonding, nome, vcal), record fissi da 12 byte, al massimo DIARIO_FILE_MAX byte:
// quando sta per superarlo si tiene la coda piu' recente (meta') e si riparte. Gli eventi si accodano in RAM (diario()) e si scrivono
// in flash solo in diarioFlush(): al boot, ai cambi di modo, a fine registrazione e, in registrazione, al massimo ogni 120 s (una
// scrittura da 400-800 ms, misurato: il FIFO dell'IMU tiene ~1,6 s). Mai scritture flash dalle callback BLE. diario() puo' essere chiamato
// anche dalle callback BLE (altro task): la coda in RAM si tocca solo dentro una sezione critica; diarioFlush copia e svuota la coda nella
// sezione critica e scrive la copia fuori: gli eventi che arrivano durante la scrittura restano nella coda nuova, nessuno si perde.
#define DIARIO_FILE "/dia.bin"
static const char *diaFile = DIARIO_FILE;               // PROVA_TEMPI lo cambia per misurare senza toccare il diario vero
#define DIARIO_REC 12
#define DIARIO_FILE_MAX 2400            // 200 record
#define DIARIO_RAM 40
enum : uint8_t { DIA_AVVIO = 1, DIA_MODO, DIA_USB, DIA_REG_INIZIO, DIA_REG_FINE, DIA_OVERRUN, DIA_DISALL, DIA_BATT, DIA_CONN, DIA_GUASTO,
                 DIA_GUASTO2, DIA_FALSO, DIA_RIPRESA, DIA_NOTA, DIA_WDT, DIA_PERSI, DIA_SYNC };
static RecDiario diaRam[DIARIO_RAM];
static uint8_t diaIni = 0, diaPend = 0;
static uint16_t diaPersi = 0;
static uint16_t diaInvioIdx = 0;

static void diario(uint8_t tipo, uint8_t p1 = 0, uint16_t p2 = 0, uint16_t p3 = 0, uint32_t p4 = 0);
static const char *diaModo(uint8_t m) { return m == 0 ? "normale" : m == 1 ? "vasca" : "sonno"; }
static void diarioTesto(const RecDiario &r, char *o, size_t n) {
  switch (r.tipo) {
    case DIA_AVVIO: snprintf(o, n, "AVV causa%u rr%03X marca%02X vbus%u%s", r.p1, r.p2, r.p3 >> 8, r.p3 & 1, (r.p3 & 2) ? " PROVE" : ""); break;
    case DIA_MODO: snprintf(o, n, "MODO %s mot%u %umV", diaModo(r.p1), r.p2, r.p3); break;
    case DIA_USB: snprintf(o, n, "USB %s %umV", r.p1 == 0 ? "staccata" : r.p1 == 1 ? "PC" : "caricatore", r.p2); break;
    case DIA_REG_INIZIO: snprintf(o, n, "REG+ or%u seg%u %umV rip%lu", r.p1, r.p2, r.p3, (unsigned long)r.p4); break;
    case DIA_REG_FINE: snprintf(o, n, "REG- mot%u seg%u %umV %lus", r.p1, r.p2, r.p3, (unsigned long)r.p4); break;
    case DIA_OVERRUN: snprintf(o, n, "OVERRUN n%u gapmax%u", r.p1, r.p2); break;
    case DIA_DISALL: snprintf(o, n, r.p1 ? "FIFO iniz scarto%uw" : "FIFO riall +%u tot%u", r.p2, r.p3); break;
    case DIA_BATT: snprintf(o, n, "BAT %umV usb%u carica%u", r.p2, r.p1 & 1, (r.p1 >> 1) & 1); break;
    case DIA_CONN: snprintf(o, n, "CONN %s h%u 0x%02X", r.p1 ? "su" : "giu", r.p2, r.p3); break;
    case DIA_GUASTO: snprintf(o, n, "GUASTO t%u fase%u pc%08lX", r.p1, r.p2, (unsigned long)r.p4); break;
    case DIA_GUASTO2: snprintf(o, n, "  lr%08lX cfsr%04X%04X", (unsigned long)r.p4, r.p3, r.p2); break;
    case DIA_FALSO: snprintf(o, n, "FALSO risveglio tocchi%u marca%02X", r.p1, r.p2); break;
    case DIA_RIPRESA: snprintf(o, n, "RIPRESA %u/%u or%u", r.p1, r.p2, r.p3); break;
    case DIA_NOTA: snprintf(o, n, "NOTA %u %u %u %lu", r.p1, r.p2, r.p3, (unsigned long)r.p4); break;
    case DIA_WDT: snprintf(o, n, "WDT gia' attivo al boot=%u", r.p1); break;
    case DIA_PERSI: snprintf(o, n, "PERSI %u eventi (RAM piena)", r.p2); break;
    case DIA_SYNC: snprintf(o, n, "SYNC ev%u h%u %u", r.p1, r.p2, r.p3); break;
    default: snprintf(o, n, "?%u", r.tipo);
  }
}
static void diarioLinea(const RecDiario &r, char *o, size_t n) {
  char t[40];
  diarioTesto(r, t, sizeof(t));
  snprintf(o, n, "%us %s", r.sec, t);
}
static void diario(uint8_t tipo, uint8_t p1, uint16_t p2, uint16_t p3, uint32_t p4) {
  RecDiario r;
  uint32_t s = millis() / 1000;
  r.sec = s > 65535 ? 65535 : (uint16_t)s; r.tipo = tipo; r.p1 = p1; r.p2 = p2; r.p3 = p3; r.p4 = p4;
  taskENTER_CRITICAL();
  if (diaPend >= DIARIO_RAM) { diaIni = (diaIni + 1) % DIARIO_RAM; diaPend--; diaPersi++; }   // RAM piena: si perde il piu' vecchio
  diaRam[(diaIni + diaPend) % DIARIO_RAM] = r;
  diaPend++;
  taskEXIT_CRITICAL();
  char l[48];
  diarioTesto(r, l, sizeof(l));
  logRiga("D %s", l);                                   // lo stesso evento nel log (seriale e pagina BLE)
}
static uint8_t diaTamp[DIARIO_FILE_MAX / 2];
static RecDiario diaCopia[DIARIO_RAM];                  // copia della coda per la scrittura (fuori dalla sezione critica)
static uint16_t statDiaMs = 0, statRegMs = 0;           // durata massima di una scrittura del diario / di /reg.bin (nel diario a fine registrazione)
static void diarioFlush() {
  if (!diaPend) return;
  uint32_t tIni = millis();
  if (diaPersi) { uint16_t p = diaPersi; diaPersi = 0; diario(DIA_PERSI, 0, p); }
  taskENTER_CRITICAL();                                  // copia e svuota la coda: i nuovi eventi vanno nella coda vuota
  uint8_t nCopia = diaPend;
  for (uint8_t i = 0; i < nCopia; i++) diaCopia[i] = diaRam[(diaIni + i) % DIARIO_RAM];
  diaPend = 0; diaIni = 0;
  taskEXIT_CRITICAL();
  InternalFS.begin();
  using namespace Adafruit_LittleFS_Namespace;
  uint32_t n = (uint32_t)nCopia * DIARIO_REC;
  uint32_t size = 0;
  { File f(InternalFS); if (f.open(diaFile, FILE_O_READ)) { size = f.size(); f.close(); } }
  uint32_t tieni = 0;
  if (size + n > DIARIO_FILE_MAX) {                      // fa posto: si tiene la coda piu' recente (la meta')
    tieni = DIARIO_FILE_MAX / 2 / DIARIO_REC * DIARIO_REC;
    if (tieni > size) tieni = size;
    File f(InternalFS);
    if (f.open(diaFile, FILE_O_READ)) { f.seek(size - tieni); f.read(diaTamp, tieni); f.close(); } else tieni = 0;
    InternalFS.remove(diaFile);
  }
  File f(InternalFS);
  if (f.open(diaFile, FILE_O_WRITE)) {
    if (tieni) f.write(diaTamp, tieni);
    for (uint8_t i = 0; i < nCopia; i++) f.write((const uint8_t *)&diaCopia[i], DIARIO_REC);
    f.close();
  }
  uint32_t dt = millis() - tIni;
  if (dt > statDiaMs) statDiaMs = dt > 65535 ? 65535 : (uint16_t)dt;
}
static uint32_t diarioRecord() {                          // numero di record in flash
  InternalFS.begin();
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  uint32_t s = 0;
  if (f.open(diaFile, Adafruit_LittleFS_Namespace::FILE_O_READ)) { s = f.size(); f.close(); }
  return s / DIARIO_REC;
}
static bool diarioLeggi(uint32_t idx, RecDiario *r) {
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  bool ok = false;
  if (f.open(diaFile, Adafruit_LittleFS_Namespace::FILE_O_READ)) {
    if (f.seek(idx * DIARIO_REC)) ok = f.read((uint8_t *)r, DIARIO_REC) == DIARIO_REC;
    f.close();
  }
  return ok;
}
// Seriale: stampa tutto il diario (record in flash)
static void diarioStampa(Stream &s) {
  diarioFlush();
  uint32_t n = diarioRecord();
  s.printf("DIARIO %lu\n", (unsigned long)n);
  for (uint32_t i = 0; i < n; i++) {
    RecDiario r; char l[64];
    if (!diarioLeggi(i, &r)) break;
    diarioLinea(r, l, sizeof(l));
    s.println(l);
    if ((i & 15) == 0) cane();
  }
  s.println("END");
}
// BLE: DIARIO[,n] manda gli ultimi n record (default 40) come righe di log 'G' (una per giro del loop)
static void diarioAvviaInvio(const char *arg);
static void diarioInvioServi() {
  if (!diaInvioN) return;
  if (connHdl == BLE_CONN_HANDLE_INVALID) { diaInvioN = 0; return; }
  RecDiario r; char l[LOG_LEN], out[LOG_LEN + 1];
  if (!diarioLeggi(diaInvioIdx, &r)) { diaInvioN = 0; return; }
  diarioLinea(r, l, sizeof(l));
  out[0] = 'G';
  snprintf(out + 1, LOG_LEN, "%s", l);
  if (carRisposte.notify(connHdl, out, strlen(out))) { diaInvioIdx++; diaInvioN--; }
}
static void diarioAvviaInvio(const char *arg) {
  diarioFlush();
  uint32_t tot = diarioRecord();
  uint32_t n = arg && *arg ? (uint32_t)atol(arg) : 40;
  if (n > tot) n = tot;
  diaInvioIdx = tot - n;
  diaInvioN = n;
}

// Stato "registrazione in corso" persistente (/reg.bin: [0] attiva, [1] riprese consecutive): seconda rete se GPREGRET2 si perde (brownout).
// Azzerato alla chiusura ordinata e quando si entra in modalita' normale con l'USB (una registrazione orfana non riparte piu').
#define REG_FILE "/reg.bin"
// File di 3 byte [attiva, riprese, checksum]. Scrittura ATOMICA: si scrive /reg.tmp e lo si rinomina su /reg.bin (lfs_rename e' atomico:
// un guasto a meta' lascia o il vecchio file o il nuovo). Mancante = nessuna registrazione attiva (la marca in GPREGRET2 copre il resto);
// presente ma corrotto = prudenza: attiva con riprese al massimo, cosi' la prossima ripresa viene rifiutata.
#define REG_TMP "/reg.tmp"
static uint8_t regCk(uint8_t a, uint8_t r) { return (uint8_t)(a ^ r ^ 0x5A); }
static void regStato(uint8_t &attiva, uint8_t &riprese) {
  InternalFS.begin();
  Adafruit_LittleFS_Namespace::File f(InternalFS);
  attiva = 0; riprese = 0;
  if (!f.open(REG_FILE, Adafruit_LittleFS_Namespace::FILE_O_READ)) return;
  uint8_t b[3] = {0, 0, 0};
  int n = f.read(b, 3);
  f.close();
  if (n != 3 || b[2] != regCk(b[0], b[1]) || b[0] > 1 || b[1] > 15) { attiva = 1; riprese = MAX_RIPRESE; return; }
  attiva = b[0]; riprese = b[1];
}
static void regScrivi(uint8_t attiva, uint8_t riprese) {
  uint8_t a, r;
  regStato(a, r);
  if (a == attiva && r == riprese) return;                // niente scritture inutili
  uint32_t tIni = millis();
  uint8_t b[3] = {attiva, riprese, regCk(attiva, riprese)};
  InternalFS.remove(REG_TMP);
  { Adafruit_LittleFS_Namespace::File f(InternalFS); if (f.open(REG_TMP, Adafruit_LittleFS_Namespace::FILE_O_WRITE)) { f.write(b, 3); f.close(); } }
  InternalFS.rename(REG_TMP, REG_FILE);
  uint32_t dt = millis() - tIni;
  if (dt > statRegMs) statRegMs = dt > 65535 ? 65535 : (uint16_t)dt;
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
  while (millis() - t0 < 1100) { cane(); imuPoll(); delay(1); }
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
static void sistemaOff(uint8_t marca);
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
      if (++contaSotto >= 5) { logRiga("bat < 3,3 V: sospensione"); sonnoMotivo = 3; vaInSospensione(true); }
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
// Un solo lampo da 15 ms anche a batteria (aggira ledScrivi): per i pochi casi silenziosi in cui la tag deve dire "sono viva ma non
// registro / mi sono ripresa". Consumo: ~15 ms x pochi mA = ~0,05 mC a evento, trascurabile (una cella da 40 mAh = 144 C).
static void lampoBreve(bool r, bool g, bool b) {
  if (r) { pinMode(LED_RED, OUTPUT); digitalWrite(LED_RED, LOW); }
  if (g) { pinMode(LED_GREEN, OUTPUT); digitalWrite(LED_GREEN, LOW); }
  if (b) { pinMode(LED_BLUE, OUTPUT); digitalWrite(LED_BLUE, LOW); }
  delay(15);
  if (r) digitalWrite(LED_RED, HIGH);
  if (g) digitalWrite(LED_GREEN, HIGH);
  if (b) digitalWrite(LED_BLUE, HIGH);
}
// Eccezione (2026-11-11, richiesta dell'utente): durante la gestione dei tocchi i LED si vedono anche a batteria
// (risveglio: blu, finestra dei tocchi di conferma: verde, falso risveglio: rosso 2 s; esito: 3 lampi verdi o i lampi di errore).
static bool ledTocchi = false;
static inline void ledScrivi(uint8_t pin, uint8_t livello) {
  bool usb = NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk;
  digitalWrite(pin, (livello == LOW && !usb && !ledTocchi) ? HIGH : livello);
}

static void vaInSospensione(bool soloUsb) {
  if (otaAttivo) { logRiga("sospensione rinviata: OTA"); return; }
  logRiga(soloUsb ? "sospensione (solo USB)" : "sospensione (4 tap/USB)");
  diario(DIA_MODO, 2, sonnoMotivo, ultimaMv);
  diarioFlush();
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
  sistemaOff(MARCA_SLEEP);                                   // con l'USB presente annulla il sonno e riavvia (NOTA 11)
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
    cane();
    uint32_t limite = (n >= 2) ? ultimo + gapMs : t0 + finestraMs;
    if (ora >= limite) break;
    if (lampeggia) ledScrivi(LED_RED, ((ora / 100) & 1) ? HIGH : LOW);
    // blu = sveglia, aspetta; verde = finestra dei tocchi di conferma aperta (si spegne per TOCCO_LAMPO_MS a ogni tocco contato)
    if (invitoBlu) {
      bool aperta = ora - t0 >= ignoraMs, lampo = n > 0 && ora - ultimo < TOCCO_LAMPO_MS;
      ledScrivi(LED_BLUE, aperta ? HIGH : LOW);
      ledScrivi(LED_GREEN, (aperta && !lampo) ? LOW : HIGH);
    }
    if (i2cLeggi(REG_TAP_SRC, &src, 1) && (src & 0x20)) {           // SINGLE_TAP
      if (ora - t0 >= ignoraMs && (n == 0 || ora - ultimo >= RISVEGLIO_DEBOUNCE_MS)) {
        n++; ultimo = ora;
        if (invitoBlu) ledScrivi(LED_GREEN, HIGH);
        if (n >= massimo) break;
      }
    }
    delay(5);
  }
  if (lampeggia) ledScrivi(LED_RED, HIGH);
  if (invitoBlu) { ledScrivi(LED_BLUE, HIGH); ledScrivi(LED_GREEN, HIGH); }
  return n;
}

// Risveglio dal doppio tap: chiamata a inizio setup(), prima di USB e BLE. Ritorna true se arrivano altri tocchi
// (almeno RISVEGLIO_TAP_EXTRA); i tocchi extra contati (max 6) restano in tocchiExtra: 2..5 = registra (2 tocchi, blu, 2 tocchi),
// 6 = azzera (2 tocchi, blu, 6 tocchi).
// All'uscita da System OFF i pin tornano al default: l'IMU perde l'alimentazione (P1.08) e quindi la configurazione,
// perche' il reset dura piu' dei suoi tempi di spegnimento. Si riaccende, si riconfigura il tap e si ascolta.
static uint8_t tocchiExtra = 0;
static bool imuMutoAlRisveglio = false;
// Accende l'IMU (P1.08), riavvia l'I2C e verifica il WHO_AM_I (fino a 4 tentativi da 40 ms: puo' metterci di piu' a partire).
// Serve al risveglio a tocchi, alla ripresa automatica e al sonno senza BLE (dopo un reset i pin tornano al default e l'IMU e' spento).
static bool imuAccendi() {
  NRF_P1->PIN_CNF[8] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos) | (GPIO_PIN_CNF_DRIVE_H0H1 << GPIO_PIN_CNF_DRIVE_Pos);
  NRF_P1->OUTSET = 1UL << 8;
  pinMode(16, INPUT_PULLUP); pinMode(17, INPUT_PULLUP);
  pinMode(PIN_INT1_ASSOLUTO, INPUT);
  delay(40);
  Wire1.begin();
  Wire1.setClock(400000);
  uint8_t id = 0;
  bool ok = false;
  for (int i = 0; i < 4 && !ok; i++) {
    ok = i2cLeggi(REG_WHO_AM_I, &id, 1) && id == 0x6A;
    if (!ok) delay(40);
  }
  return ok;
}
static bool risveglioQuattroTap() {
  ledTocchi = true;                                                 // LED visibili anche a batteria per tutta la gestione dei tocchi
  pinMode(LED_RED, OUTPUT); pinMode(LED_GREEN, OUTPUT); pinMode(LED_BLUE, OUTPUT);
  ledScrivi(LED_RED, HIGH); ledScrivi(LED_GREEN, HIGH); ledScrivi(LED_BLUE, LOW);   // blu subito: sveglia, aspetta
  if (!imuAccendi()) { imuMutoAlRisveglio = true; return true; }    // IMU muto: avvio normale (almeno si raggiunge via USB)
  configuraTap();
  // Conferma in SOFTWARE su tocchi singoli (non il DOUBLE_TAP hardware, che nell'oscillazione residua del primo gesto
  // poteva scattare da solo e svegliare la tag con 2 soli tocchi).
  i2cScrivi(REG_WAKE_UP_THS, 0x00);                                 // SINGLE_DOUBLE_TAP = 0: tocco singolo
  i2cScrivi(REG_MD1_CFG, 0x40);                                     // tocco singolo su INT1 (solo per coerenza: si legge TAP_SRC)
  tocchiExtra = contaTocchi(RISVEGLIO_FINESTRA_MS, RISVEGLIO_PAUSA_MS, RISVEGLIO_GAP_MS, 6, false, true);
  if (tocchiExtra >= RISVEGLIO_TAP_EXTRA) return true;
  ledScrivi(LED_RED, LOW); delay(2000); ledScrivi(LED_RED, HIGH);  // falso risveglio: rosso 2 s, poi si spegne e torna a dormire
  configuraTap();                                                   // torna alla configurazione del doppio tap per dormire
  delay(20);
  // falso risveglio: di nuovo System OFF con la stessa configurazione
  attendiInt1Bassa(300);
  nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
#if PROVE_GUASTI
  diario(DIA_FALSO, tocchiExtra, bootMarca);                        // per contare i falsi risvegli (borsa scossa): una scrittura flash, solo in fase di prova
  diarioFlush();
#endif
  if (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) { NRF_POWER->GPREGRET2 = 0; NVIC_SystemReset(); }   // USB arrivata nel frattempo: niente sonno
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

extern "C" uint32_t __etext, __data_start__, __data_end__, __bss_start__, __bss_end__;

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
static volatile bool otaMsgOffset = false;   // 0.6.2: il testo "ota offset,N" lo compone il loop (la callback non usa snprintf)
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
  if (off != otaAccettati) { if (!otaMsgTipo) { otaMsgOffset = true; otaMessaggio('X', ""); } return; }
  if ((uint64_t)otaAccettati + n > otaTotale) { otaMessaggio('X', "ota dati oltre la dimensione"); return; }
  for (int i = 0; i < 100 && OTA_ANELLO - (otaTesta - otaCoda) < n; i++) delay(5);   // il loop svuota l'anello in flash
  if (OTA_ANELLO - (otaTesta - otaCoda) < n) { if (!otaMsgTipo) { otaMsgOffset = true; otaMessaggio('X', ""); } return; }
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
    NRF_WDT->RR[0] = 0x6E524635UL;                            // watchdog: l'installazione dura qualche secondo e a interrupt spenti nessuno lo serve
    nv->ERASEPAGE = a;
    while (!nv->READY) {}
  }
  // 2. copia
  nv->CONFIG = NVMC_CONFIG_WEN_Wen;
  for (uint32_t i = 0; i < words; i++) {
    if (!(i & 1023)) NRF_WDT->RR[0] = 0x6E524635UL;
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

#if PROVE_GUASTI
// Comandi di prova per la prova a secco (PROVE_GUASTI): provocano davvero il guasto, per verificare ripresa, contesto e watchdog
static void provaFifo(uint32_t sec, uint8_t modo, uint16_t khz);
static void provaComando(const char *c, const char *arg) {
  if (!strcmp(c, "PROVA_TEMPI")) {                       // durata di diarioFlush (anche con rotazione del file) e regScrivi, con il BLE in annuncio
    if (inVasca) { rispondi('X', "registrazione in corso"); return; }
    uint8_t a0, r0; regStato(a0, r0);
    diaFile = "/dia_t.bin"; InternalFS.remove(diaFile);
    uint16_t maxN = 0, maxRot = 0, maxReg = 0;
    for (int giro = 0; giro < 230; giro++) {              // 230 flush da 1 record: a 200 record il file ruota (tiene la meta.) al flush 201
      diario(DIA_NOTA, 99, giro);
      statDiaMs = 0; diarioFlush(); cane();
      uint16_t d = statDiaMs;
      if (giro >= 199 && giro <= 201) { if (d > maxRot) maxRot = d; } else if (d > maxN) maxN = d;

    }
    { uint16_t m = 0; for (int i = 0; i < 6; i++) { statRegMs = 0; regScrivi(1, (i & 1) ? 2 : 3); if (statRegMs > m) m = statRegMs; cane(); } maxReg = m; }
    regScrivi(a0, r0);
    InternalFS.remove(diaFile); diaFile = DIARIO_FILE;
    char r[48]; snprintf(r, sizeof(r), "tempi dia%u rot%u reg%u", maxN, maxRot, maxReg);
    logRiga("%s ms", r);
    if (Serial && !dumpInCorso) Serial.printf("TEMPI %s\n", r);
    rispondi('K', r);
  } else if (!strcmp(c, "PROVA_TEMPO")) {                // millis() attuale: misura_avvio.py lo interroga piu' volte per legare tempo PC e millis
    char r[24]; snprintf(r, sizeof(r), "t%lu", (unsigned long)millis());
    if (Serial && !dumpInCorso) Serial.printf("TEMPO %lu\n", (unsigned long)millis());
    rispondi('K', r);
  } else if (!strcmp(c, "PROVA_AVVIO")) {                // dati del tempo di sessione di questo avvio: n avvii, origine, istante grezzo del reset precedente, scarto, margine
    char r[48];
    snprintf(r, sizeof(r), "av n%u o%u r%lu s%lu m%u g%u", bootNAvvii, bootOrigScarto, (unsigned long)bootResetMs, (unsigned long)bootScarto, bootMargine, bootGestore);
    if (Serial && !dumpInCorso) Serial.printf("AVVIO %s\n", r);
    rispondi('K', r);
  } else if (!strcmp(c, "PROVA_CRASH")) {
    logRiga("PROVA_CRASH: HardFault");
    rispondi('K', "prova crash");
    diario(DIA_NOTA, 1, inVasca);
    diarioFlush();
    delay(150);                                          // lascia partire la risposta
    volatile uint32_t *p = (volatile uint32_t *)0xF0000000UL;
    *p = 0xDEAD;                                         // BusFault (non abilitato) -> HardFault
    __asm volatile("udf #0");
  } else if (!strcmp(c, "PROVA_BLOCCO")) {
    logRiga("PROVA_BLOCCO: ciclo infinito (watchdog %d s)", WDT_SECONDI);
    rispondi('K', "prova blocco");
    diario(DIA_NOTA, 2, inVasca);
    diarioFlush();
    delay(150);
    FASE(99);
    while (true) { __asm volatile("nop"); }              // nessuno serve il watchdog
  } else if (!strcmp(c, "PROVA_FIFO")) {                 // PROVA_FIFO,<secondi>[,<modo>[,<kHz>]]  (modi: vedi provaFifo)
    uint32_t sec = arg && *arg ? (uint32_t)atol(arg) : 10;
    const char *v = arg ? strchr(arg, ',') : nullptr;
    uint8_t modo = 0; uint16_t khz = 400;
    if (v) { modo = (uint8_t)atoi(v + 1); const char *k = strchr(v + 1, ','); if (k) khz = (uint16_t)atoi(k + 1); }
    provaFifo(sec, modo, khz);
  } else if (!strcmp(c, "PROVA_RESET")) {
    logRiga("PROVA_RESET: reset software");
    rispondi('K', "prova reset");
    diario(DIA_NOTA, 3, inVasca);
    diarioFlush();
    delay(150);
    NVIC_SystemReset();
  } else {
    rispondi('X', "prova sconosciuta");
  }
}
#endif

static void eseguiComandi() {
  while (cmdTesta != cmdCodaI) {
    char c[CMD_LEN]; strcpy(c, cmdCoda[cmdCodaI & 3]); cmdCodaI = cmdCodaI + 1;
    char *arg = strchr(c, ','); if (arg) *arg++ = 0;   // il comando e' fino alla prima virgola
#if PROVE_GUASTI
    if (!strncmp(c, "PROVA_", 6)) { provaComando(c, arg); continue; }   // anche in registrazione
#endif
    if (inVasca) {                                     // in registrazione: solo SLEEP (chiude il segmento e dorme), il resto no
      if (!strcmp(c, "SLEEP")) { sonnoRichiesto = true; sonnoMotivo = 1; logRiga("sospensione da comando: chiudo la registrazione"); rispondi('K', "sospensione: chiudo la registrazione"); }
      else rispondi('X', "registrazione in corso");
    }
    else if (!strcmp(c, "SLEEP")) { sonnoMotivo = 1; vaInSospensione(); }
    else if (!strcmp(c, "LIST")) rispondi('Z', "");   // nessuna registrazione: fine elenco
    else if (!strcmp(c, "VCAL")) {                    // VCAL senza argomento = lettura; con argomento solo con USB (come nome e colore)
      if (arg && !vbusPresente()) rispondi('X', "solo con USB");
      else comandoVcal(arg);
    }
    else if (!strcmp(c, "DIARIO")) { diarioAvviaInvio(arg); rispondi('K', "diario"); }   // DIARIO[,n]: ultimi n record come righe di log
    else if (!strcmp(c, "NOME")) {                    // NOME (senza virgola) = chiede il nome attuale; NOME,<testo> lo imposta; NOME, lo cancella
      if (!arg) { char r[24]; snprintf(r, sizeof(r), "nome %s", tagNome); rispondi('K', r); }
      else if (!vbusPresente()) rispondi('X', "solo con USB");   // 0.6.1: nome e colore si cambiano solo con l'USB (a batteria la tag non e' in modalita' normale)
      else comandoNome(arg);
    }
    else if (!strcmp(c, "COLORE")) {
      if (arg && *arg && !vbusPresente()) rispondi('X', "solo con USB");
      else comandoColore(arg);
    }
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
  if (otaMsgTipo) {
    char t = otaMsgTipo, m[40]; strlcpy(m, otaMsgTesto, sizeof(m));
    if (otaMsgOffset) { otaMsgOffset = false; snprintf(m, sizeof(m), "ota offset,%lu", (unsigned long)otaAccettati); }
    otaMsgTipo = 0; rispondi(t, m);
  }
  uint32_t pct = otaAccettati * 100UL / otaTotale;
  if (!otaInstallaAlle && pct >= otaUltimoPct + 25) { otaUltimoPct = pct - pct % 25; logRiga("ota: ricevuto %lu%%", (unsigned long)pct); }
  if (otaInstallaAlle && (int32_t)(millis() - otaInstallaAlle) >= 0) otaInstalla();
}

static void inCccdRisposte(uint16_t h, BLECharacteristic *, uint16_t valore) {
  if (valore & 1) { connHdl = h; logInvio = logN > LOG_RIGHE ? logN - LOG_RIGHE : 0; risposteAttive = true; }   // rimanda il buffer
  else if (h == connHdl) risposteAttive = false;
}

// 0.6.2: le callback BLE (task "Callback", stack 3 KB fisso nel core) non usano snprintf/vsnprintf ne' buffer: copiano l'evento in una coda
// e basta; log, diario e richieste di PHY/DLE/intervallo le fa connEventiServi() dal loop (chiamata da syncServi()).
struct EvConn { uint16_t h; uint8_t su, motivo; };
static EvConn evConn[8];
static volatile uint8_t evConnT = 0, evConnC = 0;
static volatile uint8_t evConnPersi = 0;
static void evConnAccoda(uint16_t h, uint8_t su, uint8_t motivo) {
  if ((uint8_t)(evConnT - evConnC) >= 8) { evConnPersi++; return; }
  evConn[evConnT & 7] = {h, su, motivo};
  evConnT = evConnT + 1;
}
static void inConnessione(uint16_t h) {
  if (connHdl == BLE_CONN_HANDLE_INVALID) connHdl = h;   // provvisorio: la pagina vera e' chi scrive i comandi o abilita 0005
  if (!inVasca) { ledScrivi(LED_BLUE, HIGH); ledScrivi(LED_GREEN, LOW); }   // verde fisso
  evConnAccoda(h, 1, 0);
}
static void inDisconnessione(uint16_t h, uint8_t motivo) {
  if (h == connHdl) { connHdl = BLE_CONN_HANDLE_INVALID; risposteAttive = false; }
  if (!inVasca) ledScrivi(LED_GREEN, HIGH);
  evConnAccoda(h, 0, motivo);
}
// Dal loop: log + diario e, a ogni nuovo collegamento, richiesta di PHY 2M, DLE 251 e intervallo 7,5-15 ms (0.6.2). Il central (ricevitore,
// display) lo fa gia' da solo: se una procedura del link e' in corso il SoftDevice risponde BUSY e si ignora. L'intervallo si chiede nella
// forma 7,5-15 ms (non fisso a 7,5): con due tag il ricevitore sceglie 11,25-15 ms e non deve litigare con la tag.
static void connEventiServi() {
  while (evConnC != evConnT) {
    EvConn e = evConn[evConnC & 7];
    evConnC = evConnC + 1;
    if (e.su) {
      logRiga("connesso %u", e.h);
      diario(DIA_CONN, 1, e.h);
      BLEConnection *c = Bluefruit.Connection(e.h);
      if (c && c->connected()) {
        c->requestPHY(BLE_GAP_PHY_2MBPS);
        c->requestDataLengthUpdate();
        if (c->getConnectionInterval() > 12) {
          ble_gap_conn_params_t cp = {6, 12, 0, 200};
          sd_ble_gap_conn_param_update(e.h, &cp);
        }
      }
    } else {
      logRiga("disconnesso %u (0x%02X)", e.h, e.motivo);
      diario(DIA_CONN, 0, e.h, e.motivo);
    }
  }
  if (evConnPersi) { uint8_t p = evConnPersi; evConnPersi = 0; diario(DIA_NOTA, 12, p); }   // eventi di collegamento persi (coda piena)
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
  anello.ciclo = cane;                   // la scansione dei 512 blocchi serve il watchdog
  flash.ciclo = cane;                    // le attese lunghe del chip (cancellazione fino a 15 s) servono il watchdog
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
static uint8_t syncVer = 1;                     // versione dichiarata dal central nel PRONTO (1 = frammenti da 128, 2 = da 238 con MTU 247)
static uint8_t txFrag = SYNC_FRAMMENTO, txNFrag = SYNC_N_FRAMMENTI;   // frammento e numero di frammenti del blocco in trasmissione
static bool diagDaInviare = false, diagPronta = false;
static uint8_t diagTent = 0;   // tentativi falliti di invio della DIAGNOSI
static uint8_t diagBuf[244];
static uint16_t diagLen = 0;

// 0.6.2: stack libero minimo (byte) dei task, da FreeRTOS (uxTaskGetSystemState): loop (4 KB), Callback (3 KB), BLE (5 KB). Le dimensioni
// sono costanti del core (main.cpp, bluefruit.cpp) e non si cambiano dallo sketch. Sotto 512 B liberi si scrive una NOTA 13 nel diario
// (task, byte liberi): e' il segnale che lo stack e' vicino al limite, prima di un eventuale HardFault.
static uint16_t stkLibero[3] = {0xFFFF, 0xFFFF, 0xFFFF};
static void stackMonitor() {
  static uint32_t t = 0;
  if (millis() - t < 5000) return;
  t = millis();
  TaskStatus_t st[12];
  UBaseType_t n = uxTaskGetSystemState(st, 12, NULL);
  static bool zeroNotato = false;
  if (n == 0 && !zeroNotato) { zeroNotato = true; diario(DIA_NOTA, 18, 0); }   // FreeRTOS non restituisce task: monitor cieco, lo si dice una volta
  for (UBaseType_t i = 0; i < n; i++) {
    int k = !strcmp(st[i].pcTaskName, "loop") ? 0 : !strncmp(st[i].pcTaskName, "Callbac", 7) ? 1 : !strcmp(st[i].pcTaskName, "BLE") ? 2 : -1;
    if (k < 0) continue;
    uint32_t b = (uint32_t)st[i].usStackHighWaterMark * 4;
    uint16_t v = b > 0xFFFE ? 0xFFFE : (uint16_t)b;
    if (v < stkLibero[k]) {
      bool nuovo = v < 512 && stkLibero[k] - v >= 64;
      stkLibero[k] = v;
      if (nuovo) diario(DIA_NOTA, 13, k, v);
    }
  }
}

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
  if (annErrore) return ST_ERRORE;
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
  {   // 0.6.2: 100 ms se ci sono blocchi in attesa (il display li vede prima), 200 ms altrimenti; il cambio vale al riavvio dell'annuncio
    uint16_t iv = (anelloOk && anello.nDaValidare > 0) ? 160 : 320;   // unita' di 0,625 ms
    Bluefruit.Advertising.setInterval(iv, iv);
  }
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
    case M_SONNO: break;
    default: return;
  }
  cmdSy[cmdSyT & 15] = c;
  cmdSyT = cmdSyT + 1;
}

static void syncReset() {
  syncAttivo = false; syncErrore = false; mappaDaInviare = false; fineInviata = false; diagDaInviare = false; diagPronta = false; diagTent = 0; syncVer = 1;
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
      if (!anelloOk || (c.motivo != SYNC_VERSIONE && c.motivo != SYNC_VERSIONE_PRONTO2)) { logRiga("sync: PRONTO ignorato"); continue; }
      if (syncAttivo && c.conn != syncConn && connessioneViva(syncConn)) continue;   // un solo display alla volta
      syncReset();
      syncConn = c.conn; syncAttivo = true; mappaDaInviare = true;
      syncVer = c.motivo; diagDaInviare = (c.motivo >= SYNC_VERSIONE_PRONTO2);   // la DIAGNOSI solo ai central che la conoscono
      chiusureViste = anello.chiusure;
      logRiga("sync: pronto (conn %u) v%u", c.conn, c.motivo);
      diario(DIA_SYNC, 1, c.conn);
      continue;
    }
    if (!syncAttivo || c.conn != syncConn) continue;
    if (c.tipo == M_SONNO) {   // stessa richiesta del comando testuale SLEEP; solo con sessione valida (dopo PRONTO)
      logRiga("sync: SONNO ricevuto");
      diario(DIA_SYNC, 5, c.conn);
      sonnoMotivo = 1;
      if (inVasca) sonnoRichiesto = true; else sonnoDaSync = true;
    }
    else if (c.tipo == M_CONFERMA) syncConferma(c.seq, c.crc);
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
      diario(DIA_SYNC, 2, c.conn, c.motivo);
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
  BLEConnection *cn = Bluefruit.Connection(syncConn);
  txFrag = (syncVer >= SYNC_VERSIONE_PRONTO2 && cn && cn->getMtu() >= 247) ? SYNC_FRAMMENTO2 : SYNC_FRAMMENTO;   // ricaduta a 128 se un lato non lo supporta
  txNFrag = (SYNC_BLOCCO_BYTE + txFrag - 1) / txFrag;
  return true;
}

// Un messaggio del blocco in corso (BLOCCO, poi 32 frammenti da 128 o 18 da 238). false = coda radio piena (si riprova) o errore
static bool syncPasso() {
  uint8_t m[6 + SYNC_FRAMMENTO2];
  if (txFase == 0) {
    uint16_t n = (syncVer >= SYNC_VERSIONE_PRONTO2) ? syncBlocco2(m, txSeq, txBlk, txCrc, txMillis, txFrag) : syncBlocco(m, txSeq, txBlk, txCrc, txMillis);
    if (!syncInvia(m, n)) return false;
    txFase = 1;
    return true;
  }
  uint8_t idx = txFase - 1;
  uint16_t off = (uint16_t)idx * txFrag;
  uint16_t len = SYNC_BLOCCO_BYTE - off < txFrag ? SYNC_BLOCCO_BYTE - off : txFrag;
  syncFrammentoIntest(m, txSeq, idx);
  if (!anello.leggi(txBlk, off, m + 6, len)) { uscErrore(E_FLASH); syncErrore = true; txAttiva = false; return false; }
  for (uint16_t q = SWR_OFF_CONFERMA; q < SWR_OFF_CONFERMA + SWR_LEN_CONFERMA; q++)   // CRC32 con la conferma a 0xFF (byte 252..255 del blocco)
    if (q >= off && q < off + len) m[6 + q - off] = 0xFF;
  if (!syncInvia(m, 6 + len)) return false;
  if (++txFase > txNFrag) txAttiva = false;
  return true;
}

// DIAGNOSI: motivo dell'ultimo reset, contesto del guasto, stack libero e ultime righe del diario in flash (gia' scritte: nessuna scrittura qui)
static void diagCostruisci() {
  static char testo[244 - SYNC_DIAG_FISSI];
  uint32_t n = diarioRecord(), da = n > 8 ? n - 8 : 0;
  RecDiario r; char l[64];
  uint16_t tot = 0; uint8_t nr = 0;
  uint32_t i0 = n;                                         // dal piu' recente al piu' vecchio finche' le righe entrano
  while (i0 > da) {
    if (!diarioLeggi(i0 - 1, &r)) break;
    diarioLinea(r, l, sizeof(l));
    uint16_t k = strlen(l) + 1;
    if (tot + k > sizeof(testo)) break;
    tot += k; i0--; nr++;
  }
  uint16_t pos = 0;
  for (uint32_t i = i0; i < n; i++) {
    if (!diarioLeggi(i, &r)) break;
    diarioLinea(r, l, sizeof(l));
    uint16_t k = strlen(l);
    if (pos + k + 1 > sizeof(testo)) break;
    memcpy(testo + pos, l, k); pos += k; testo[pos++] = '\n';
  }
  diagLen = syncDiagnosi(diagBuf, causaReset, bootGuasto, bootRr, bootCtxValido ? bootCtx.pc : 0, bootCtxValido ? bootCtx.lr : 0,
                         bootCtxValido ? bootCtx.cfsr : 0, stkLibero[0], stkLibero[1], stkLibero[2], nr, testo, pos);
  diagPronta = true;
}

// Chiamata a ogni giro del loop: non blocca mai (si ferma quando la coda radio e' piena o dopo 40 messaggi, poi torna a registrare)
static void syncServi() {
  if (!bleOk) return;
  connEventiServi();
  stackMonitor();
  syncElabora();
  if (!syncAttivo) return;
  BLEConnection *c = Bluefruit.Connection(syncConn);
  if (!c || !c->connected()) { logRiga("sync: collegamento perso"); diario(DIA_SYNC, 3, syncConn); syncReset(); return; }
  if (!carSyncDati.notifyEnabled(syncConn) || c->getMtu() < 138) return;   // MAPPA = 135 byte + 3 di intestazione ATT
  if (anello.chiusure != chiusureViste) { chiusureViste = anello.chiusure; fineInviata = false; }
  for (uint8_t budget = 40; budget; budget--) {   // 0.6.2: si invia finche' la coda radio accetta (hvx -> RESOURCES), con un tetto di sicurezza
    if (mappaDaInviare) {
      uint8_t m[135], mp[128];
      anello.mappa(mp);
      syncMappa(m, millis(), anello.aperto >= 0 ? (uint16_t)anello.aperto : 0xFFFF, mp);
      if (!syncInvia(m, 135)) return;
      mappaDaInviare = false;
      continue;
    }
    if (diagDaInviare) {
      if (!diagPronta) diagCostruisci();
      if (c->getMtu() < diagLen + 3) {   // 0.6.2: la DIAGNOSI non entra nell'MTU del collegamento: si rinuncia, i blocchi proseguono
        diagDaInviare = false;
        diario(DIA_NOTA, 14, c->getMtu(), diagLen);
        logRiga("sync: diagnosi non inviata, MTU %u < %u", c->getMtu(), diagLen + 3);
        continue;
      }
      if (!syncInvia(diagBuf, diagLen)) {
        // coda piena: normale, si riprova al giro dopo; ma un guasto vero non deve bloccare i blocchi (3 giri falliti, poi si rinuncia)
        if (++diagTent >= 3) { diagDaInviare = false; diario(DIA_NOTA, 15, diagTent); logRiga("sync: diagnosi rinunciata dopo %u tentativi", diagTent); continue; }
        return;
      }
      diagDaInviare = false;
      logRiga("sync: diagnosi inviata (%u B)", diagLen);
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
        diario(DIA_SYNC, 4, 0, anello.nDaValidare);
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
  while (millis() - t0 < ms) { cane(); syncServi(); annuncioAggiorna(false); statoSyncServi(false); delay(2); }
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

#define HVN_CODA 8   // 0.6.2: 8 notifiche in coda per collegamento (prima 4). Se Bluefruit.begin() fallisse per RAM del SoftDevice: log 'BLE begin KO', tornare a 6 o 4
// Avvio del BLE (modalita' normale e vasca): 2 collegamenti periferici (display + pagina web), MTU 247, servizi
static void bleIniz(bool vasca) {
  tagId = NRF_FICR->DEVICEID[0];
  Bluefruit.configPrphConn(247, 6, HVN_CODA, 1);   // MTU 247, evento 7,5 ms (6 x 1,25 ms: massimo utile con intervallo 7,5 ms), HVN_CODA notifiche in coda per collegamento
  Bluefruit.configAttrTableSize(0x1400);   // 5 KB: il predefinito del nRF52840 e' 4 KB (0x1000), con 3 KB i servizi non entravano tutti
  Bluefruit.autoConnLed(false);             // mai il lampeggio automatico del BLE: consuma e con il BLE sempre acceso non dice niente
  bleOk = Bluefruit.begin(2, 0);
  if (!bleOk) {   // ripiego unico (niente loop di riavvii): coda ridotta a 4
    logRiga("BLE begin KO con coda %u (RAM del SoftDevice?), riprovo con 4", HVN_CODA);
    diario(DIA_NOTA, 16, HVN_CODA);
    Bluefruit.configPrphConn(247, 6, 4, 1);
    bleOk = Bluefruit.begin(2, 0);
    if (!bleOk) { logRiga("BLE begin KO anche con coda 4"); diario(DIA_NOTA, 16, 4); return; }
  }
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
  if (carControllo.begin() != ERROR_NONE) { logRiga("BLE: carControllo.begin KO"); diario(DIA_NOTA, 17, 0); }
  carSyncDati.setProperties(CHR_PROPS_NOTIFY);
  carSyncDati.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carSyncDati.setMaxLen(244);   // 0.6.2: frammenti da 238 + 6 e DIAGNOSI
  if (carSyncDati.begin() != ERROR_NONE) { logRiga("BLE: carSyncDati.begin KO"); diario(DIA_NOTA, 17, 1); }
  carSyncStato.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  carSyncStato.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  carSyncStato.setFixedLen(SYNC_LEN_STATO);
  if (carSyncStato.begin() != ERROR_NONE) { logRiga("BLE: carSyncStato.begin KO"); diario(DIA_NOTA, 17, 2); }
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
static bool vProva = false;                         // PROVA_FIFO: i campioni non si registrano, si contano soltanto



static uint32_t pN = 0, pSwap = 0, pBuoni = 0; static float pSomma = 0;

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
  // Con la tensione USB presente il System OFF non si risveglierebbe piu' (il risveglio da USB e' sul fronte di VBUS):
  // invece di dormire si riavvia, e con l'USB l'avvio va in modalita' normale. Diario NOTA 11.
  if (vbusOra()) {
    logRiga("sonno annullato: USB presente");
    diario(DIA_NOTA, 11, marca);
    diarioFlush();
    gpregretImposta(0);
    NVIC_SystemReset();
  }
  if (sdAttivo()) { gpregretImposta(marca); sd_power_system_off(); }
  else { NRF_POWER->GPREGRET2 = marca; NRF_POWER->SYSTEMOFF = POWER_SYSTEMOFF_SYSTEMOFF_Enter; }
  while (true) __WFE();
}

static void vServi();
static void attendi(uint32_t ms) {   // attesa che continua a svuotare il FIFO dell'IMU
  uint32_t t0 = millis();
  while (millis() - t0 < ms) { cane(); if (vAttivo) vServi(); delay(vAttivo ? 10 : 1); }
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
  // Bias: si impara anche quando la media e' alta ma orientamento e lettura sono stabili da un secondo all'altro.
  // Prima si imparava solo in quiete: con un bias > QUIETE_GYRO_DPS la tag non risultava mai ferma e la registrazione
  // non si chiudeva mai (visto il 2026-11-11 sulla tag 447B0247 ferma sul tavolo).
  static float bmPrec[3]; static bool bmOk = false;
  bool letturaStabile = bmOk;
  for (int i = 0; i < 3; i++) if (fabsf(bm[i] - bmPrec[i]) * 0.035f > 1.0f) letturaStabile = false;
  for (int i = 0; i < 3; i++) bmPrec[i] = bm[i];
  bmOk = true;
  if (rifOk && ang < QUIETE_ANGOLO_GRADI && letturaStabile)
    for (int i = 0; i < 3; i++) bias[i] += 0.3f * (bm[i] - bias[i]);
  if (rifOk && gMed < QUIETE_GYRO_DPS && ang < QUIETE_ANGOLO_GRADI) {
    secFermo++;
  } else {
    for (int i = 0; i < 3; i++) rif[i] = a[i];
    rifOk = true; secFermo = 0;
  }
  if (secFermo >= QUIETE_REG_S && !vMotivo) vMotivo = SWR_STOP_QUIETE;
}

static void vCampione(const int16_t *s, uint32_t t) {
  if (vMotivo) return;
  if (vProva) {                                           // prova a secco del FIFO: nessuna scrittura in flash
    float a = sqrtf((float)s[0] * s[0] + (float)s[1] * s[1] + (float)s[2] * s[2]) * (SWR_ACC_UG_LSB / 1e6f);
    float g = sqrtf((float)s[3] * s[3] + (float)s[4] * s[4] + (float)s[5] * s[5]) * (SWR_ACC_UG_LSB / 1e6f);   // il "giro" letto come accelerometro
    pN++; pSomma += a;
    if (a > 0.85f && a < 1.15f) pBuoni++;                  // a riposo |a| = 1 g: se e' fuori, il campione e' disallineato
    if (g > 0.8f && g < 1.2f && a < 0.5f) pSwap++;         // lo stesso criterio di swr.py (conta_scambiati)
    return;
  }
  if (cod.nc && !cod.sta(s)) vChiudiPagina();
  if (vMotivo) return;
  cod.aggiungi(s, t);
  vCampioni++;
  vQuiete(s);
}

// Svuota il FIFO dell'IMU (6 parole da 16 bit per campione: Gx Gy Gz Ax Ay Az) e codifica i campioni. L'ALGORITMO (verifica del pattern,
// controllo sul contenuto, riallineamento) sta in swr_fifo.h, senza Arduino e con I2C iniettato: e' provato con un segnale sintetico dal port
// Python fifo_sim.py (test_swr.py). Qui c'e' solo l'adattatore all'hardware.
struct FifoHw {
  uint32_t ms() { return millis(); }
  bool leggi(uint8_t reg, uint8_t *b, uint8_t n) { bool ok = i2cLeggi(reg, b, n); if (ok) vErrI2c = 0; return ok; }
  void scrivi(uint8_t reg, uint8_t v) { i2cScrivi(reg, v); }
  void attendi(uint32_t m) { delay(m); }
  bool fermo() { return vMotivo != 0; }
  void erroreI2c() { if (++vErrI2c > 100) vMotivo = SWR_STOP_ERRORE; }
  void campione(const int16_t *s, uint32_t t) { vCampione(s, t); }
  void chiudiPagina() { vChiudiPagina(); }
  void gap() { vFlagsProx |= SWR_FLAG_GAP; }
  void evento(uint8_t tipo, uint16_t a, uint16_t b) { (void)b; if (tipo == 1) diario(DIA_OVERRUN, a, statGapMax); else diario(DIA_DISALL, 1, a, 0); }
  void traccia(const char *tag, uint32_t a, uint32_t b, uint32_t c) { if (vProva && Serial) Serial.printf("%s %lu %lu %lu\n", tag, (unsigned long)a, (unsigned long)b, (unsigned long)c); }
};
static FifoHw fifoHw;
static SwrFifo<FifoHw> fifo(fifoHw);
static void vServi() { fifo.servi(); }

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
  if (!i2cLeggi(REG_CTRL1_XL, &v, 1) || v != 0x54) return false;
  uint8_t g = 0, f = 0;                                  // 0.6.1: controlla anche giroscopio e FIFO (prima si guardava solo l'accelerometro)
  if (!i2cLeggi(REG_CTRL2_G, &g, 1) || g != 0x58) { logRiga("IMU giro 0x%02X?", g); return false; }
  if (!i2cLeggi(REG_FIFO_CTRL5, &f, 1) || f != 0x2E) { logRiga("IMU fifo 0x%02X?", f); return false; }
  if (!i2cLeggi(REG_FIFO_CTRL3, &f, 1) || f != 0x09) { logRiga("IMU fifo3 0x%02X?", f); return false; }
  fifo.campAvvio = 0; fifo.batchN = 0; fifo.ultAcc = 0;                       // il primo vServi() allinea il FIFO al pattern G,XL (FIFO_STATUS3/4)
  return true;
}

// PROVA_FIFO,<secondi>[,<modo>]: a secco, in modalita' normale (USB). Fa girare vServi() sull'IMU vero senza scrivere in flash e conta i
// campioni "scambiati" (stesso criterio di swr.py). modo 0 = normale; 1 = a meta' tempo si tolgono 3 parole al FIFO (si simula una lettura
// I2C interrotta): deve risultare 1 disallineamento, 3 parole scartate e 0 scambiati; 2 = come 1 ma SENZA riallineamento (la lettura di
// prima della 0.6.1): dopo il taglio tutti i campioni risultano scambiati, che e' proprio il difetto visto in piscina.
static void provaFifo(uint32_t sec, uint8_t modo, uint16_t khz = 400) {
  if (inVasca) { rispondi('X', "registrazione in corso"); return; }
  if (sec < 1) sec = 1;
  if (sec > (modo >= 5 ? 600UL : 60UL)) sec = (modo >= 5 ? 600UL : 60UL);
  if (!vImuAvvia()) { logRiga("prova fifo: IMU KO"); rispondi('X', "prova fifo: IMU"); imuOk = imuInit(); return; }
  vProva = true; fifo.azzera(); fifo.azzeraStat(); fifo.allinea = (modo != 2 && modo != 3); Wire1.setClock(khz * 1000UL);
  uint8_t reg0a = 0, reg0r = 0;
  if (modo == 5 || modo == 6) {                          // carico di registrazione con il BLE: ogni 10 s un diarioFlush e ogni 60 s un regScrivi (su file di prova)
    diarioFlush(); regStato(reg0a, reg0r);
    diaFile = "/dia_t.bin"; InternalFS.remove(diaFile);
    statDiaMs = 0; statRegMs = 0;
  }
  pN = pSwap = pBuoni = 0; pSomma = 0; vMotivo = 0; vErrI2c = 0;
  if (modo == 4) {                                       // esperimento: lettura a FASE FISSA dopo il dato pronto (DRDY dell'accelerometro su INT1, impulso da 75 us)
    i2cScrivi(0x0B, 0x80);                               // DRDY_PULSE_CFG_G: DRDY a impulsi
    i2cScrivi(0x0D, 0x01);                               // INT1_CTRL: INT1_DRDY_XL
    pinMode(PIN_INT1_ASSOLUTO, INPUT);
  }
  uint32_t t0 = millis();
  bool tagliato = false;
  uint32_t tServ = 0, gMax = 0, tFl = millis(), tRg = millis();
  uint8_t nRg = 0;
  while (millis() - t0 < sec * 1000UL) {
    cane();

    if (modo == 5 || modo == 6) {                        // 5 = stalli grezzi; 6 = con la regola del ciclo (niente flash se c'e' un client BLE collegato)
      bool libero = modo == 5 || Bluefruit.Periph.connected() == 0;
      if (libero && millis() - tFl >= 10000UL) { tFl = millis(); diario(DIA_NOTA, 97, nRg); diarioFlush(); }
      if (libero && millis() - tRg >= 60000UL) { tRg = millis(); regScrivi(1, (nRg++ & 1) ? 2 : 3); }
    }
    if ((modo == 1 || modo == 2) && !tagliato && millis() - t0 >= sec * 500UL) {
      uint8_t x[6];
      i2cLeggi(REG_FIFO_OUT_L, x, 6);                    // 3 parole tolte a mano: il puntatore di lettura si sfasa di 3
      tagliato = true;
      fifo.ultAcc = millis();                                // il registro di stato si assesta dopo ~1 ms: come per ogni altro accesso
      logRiga("prova fifo: 3 parole tolte");
    }
    if (modo == 4) {                                     // 4 impulsi DRDY (~19 ms), poi si aspetta meta' periodo (2,4 ms) e si legge: fase costante rispetto al campionamento
      uint8_t n = 0; uint32_t tw = millis();
      while (n < 4 && millis() - tw < 60) { if (digitalRead(PIN_INT1_ASSOLUTO)) { n++; while (digitalRead(PIN_INT1_ASSOLUTO) && millis() - tw < 60) {} } }
      delayMicroseconds(2400);
      fifo.ultAcc = 0;
      vServi();
    } else {
      { uint32_t o = millis(), g = o - tServ; if (tServ && g > gMax) gMax = g; tServ = o; }   // intervallo fra due servizi del FIFO (con gli stalli)
      vServi();
      delay(20);
    }
  }
  vProva = false; fifo.allinea = true; Wire1.setClock(400000);
  i2cScrivi(REG_FIFO_CTRL5, 0x00);
  char r[48];
  snprintf(r, sizeof(r), "n%lu ok%lu sw%lu d%u s%u r%u b%u", (unsigned long)pN, (unsigned long)pBuoni, (unsigned long)pSwap, fifo.statDisall, fifo.nSospetti, fifo.nRc, fifo.nRcSpostati);
  logRiga("fifo %s", r);
  rispondi('K', r);
  char r2[48];
  snprintf(r2, sizeof(r2), "gmax%lu ovr%u dia%u reg%u", (unsigned long)gMax, fifo.statOverrun, statDiaMs, statRegMs);    // modo 5: stalli reali con il BLE
  logRiga("%s", r2);
  if (Serial && !dumpInCorso) Serial.printf("FIFO2 %s\n", r2);
  rispondi('K', r2);
  if (modo == 5 || modo == 6) { InternalFS.remove(diaFile); diaFile = DIARIO_FILE; regScrivi(reg0a, reg0r); }
  fifo.azzeraStat();
  imuOk = imuInit();                                     // riporta l'IMU alla configurazione della modalita' normale
  if (imuOk) calibraBoot();
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

// Sonno senza BLE (avvio senza ragione per registrare): IMU con il doppio tap come sorgente di risveglio, poi System OFF con MARCA_SLEEP.
static void dormiSenzaBle() {
  if (imuAccendi()) {
    configuraTap();
    delay(50);
    attendiInt1Bassa(1000);
  }
  nrf_gpio_cfg_sense_input(PIN_INT1_ASSOLUTO, NRF_GPIO_PIN_NOPULL, NRF_GPIO_PIN_SENSE_HIGH);
  sistemaOff(MARCA_SLEEP);
}

// Seconda rete della ripresa: l'ultimo blocco per seq contiene pagine di segmento/dati ma NON la pagina di chiusura del suo segmento
// (la chiusura finisce sempre nell'ultimo blocco del segmento). Le pagine si scrivono in ordine: la prima 0xFF chiude l'elenco.
static bool ultimoSegmentoAperto() {
  if (!anelloOk || anello.maxSeq == 0 || anello.ultimo < 0) return false;
  bool dati = false, chiusura = false;
  for (uint8_t p = 1; p < SWR_PAGINE_BLOCCO; p++) {
    uint8_t h[4];
    if (!anello.leggi(anello.ultimo, p * SWR_PAGINA, h, 4)) return false;
    if (h[0] == 0xFF) break;
    if (h[0] == SWR_T_SEGMENTO || h[0] == SWR_T_DATI) dati = true;
    else if (h[0] == SWR_T_CHIUSURA) chiusura = true;
  }
  return dati && !chiusura;
}

// Uscita anticipata dalla modalita' vasca (prima o durante l'avvio della registrazione). hw = guasto dell'IMU o della flash: durante una
// ripresa (origine != 0) si riprova con un RESET (riaccende l'IMU e il QSPI e consuma una ripresa: il limite MAX_RIPRESE chiude il ciclo).
// In ogni altro caso lo stato "registrazione in corso" va DISARMATO (marca e /reg.bin): una cella ricollegata giorni dopo non deve riprendere
// da sola. Un solo lampo rosso da 15 ms anche a batteria.
static void uscitaAnticipata(uint8_t origine, uint8_t riprese, bool hw) {
  lampoBreve(true, false, false);
  if (origine != 0 && hw && riprese <= MAX_RIPRESE) {
    regScrivi(1, riprese);
    gpregretImposta(MARCA_REGISTRA | (riprese > 15 ? 15 : riprese));
    diario(DIA_NOTA, 9, riprese, origine);
    diarioFlush();
    NVIC_SystemReset();
  }
  gpregretImposta(MARCA_SLEEP);
  regScrivi(0, 0);
}

// origine: 0 = 4 tocchi; 1 = ripresa dopo un riavvio inatteso (marca GPREGRET2); 2 = ripresa dalla seconda rete (stato in /reg.bin + flash).
// Le riprese non hanno il rito dei tocchi, aprono un NUOVO segmento e annotano la causa nella pagina di segmento (swr_formato.h, byte 38..63).
static void modalitaVasca(uint8_t origine) {
  inVasca = true;
  if (origine == 0) tempoNuovaCatena();                      // partenza a tocchi: il tempo di sessione comincia qui
  uint8_t riprese = 0;                                       // riprese automatiche consecutive senza chiusura ordinata (serve anche alle uscite anticipate)
  if (origine != 0) {
    uint8_t att = 0, rip = 0;
    regStato(att, rip);
    uint8_t dalMarca = ((bootMarca & 0xF0) == MARCA_REGISTRA) ? (bootMarca & 0x0F) : 0;     // il conteggio sta anche nella marca: vale il maggiore dei due
    riprese = (rip > dalMarca ? rip : dalMarca) + 1;                                         // (con /reg.bin cancellato o corrotto la tag si ferma comunque)
  }
  tagId = NRF_FICR->DEVICEID[0];
  pinMode(LED_RED, OUTPUT); pinMode(LED_GREEN, OUTPUT); pinMode(LED_BLUE, OUTPUT);
  ledSet(0);
  pinMode(PIN_NCHG, INPUT_PULLUP);
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
  if (origine != 0) { lampoBreve(true, true, false); imuMutoAlRisveglio = !imuAccendi(); }  // ripresa dopo guasto: lampo giallo; l'IMU va riacceso qui (dopo il reset e' spento)
  if (imuMutoAlRisveglio) { uscitaAnticipata(origine, riprese, true); lampi(LED_R, 10, 60, 60); dormiVasca(false); }   // IMU muto: lampo rosso; in ripresa reset
  vcalCarica();
  vMv = batteriaMv();
  ultimaMv = vMv;
  if (vMv > 0 && vMv < BAT_MIN_AVVIO_MV) { uscitaAnticipata(origine, riprese, false); lampi(LED_R, 3, 200, 200); dormiVasca(false); }   // batteria troppo scarica: non si registra
  if (!memInit()) { uscitaAnticipata(origine, riprese, true); lampi(LED_R, 10, 60, 60); dormiVasca(false); }
  if (origine == 0 && tocchiExtra >= 6) vAzzera();                                                           // 2 tocchi, blu, 6 tocchi: azzeramento
  EsitoScansione es = memScansiona();
  if (es == SC_FORMATO1) {                                                                   // dati del formato 1: NON si cancellano da soli
    uscitaAnticipata(origine, riprese, false);
    lampi(LED_R | LED_B, 4, 250, 250);                                                       // 4 lampi viola: scaricare con DUMP, poi azzerare a tocchi
    dormiVasca(false);
  }
  if (es == SC_ESTRANEA) {                                                                   // contenuto non riconosciuto: MAI cancellato da solo
    uscitaAnticipata(origine, riprese, false);
    lampi(LED_R | LED_B, 4, 250, 250);                                                       // come il formato 1: scaricare con DUMP, poi azzerare
    dormiVasca(false);
  }
  if (origine == 2 && !ultimoSegmentoAperto()) {                                             // seconda rete: se l'ultimo segmento e' chiuso non c'e' niente da riprendere
    diario(DIA_NOTA, 2, 0);
    regScrivi(0, 0);
    diarioFlush();
    dormiVasca(false);
  }
  bleIniz(true);                                                                             // BLE acceso anche in registrazione
  if (origine != 0) {
    diario(DIA_RIPRESA, riprese, MAX_RIPRESE, origine);
    if (riprese > MAX_RIPRESE) {                                                             // protezione dai cicli: niente piu' riprese, annuncio ERRORE, sonno
      diario(DIA_NOTA, 3, riprese);
      lampoBreve(true, false, false);                                                        // lampo rosso anche a batteria: rifiuto della quarta ripresa
      gpregretImposta(MARCA_SLEEP);
      regScrivi(0, 0);
      diarioFlush();
      annErrore = true; annuncioAggiorna(true); bleServi(3000); annErrore = false;
      dormiVasca(false);
    }
  }
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
    uscitaAnticipata(origine, riprese, !piena);                                              // memoria piena: stato disarmato; errore flash: in ripresa reset
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
  memset(p + 30, 0, 8); strncpy((char *)p + 30, VER_NUM VER_SEG, 7);
  // 0.6.1: origine del segmento (tocchi o ripresa automatica) e contesto del guasto precedente (swr_formato.h, byte 38..63)
  p[SWR_SEG_OFF_FLAG] = (origine == 1 ? SWR_SEGF_RIPRESA : origine == 2 ? SWR_SEGF_RIPRESA_FLASH : 0) | (bootCtxValido ? SWR_SEGF_CONTESTO : 0);
  p[SWR_SEG_OFF_RIPRESE] = riprese; p[SWR_SEG_OFF_MARCA] = bootMarca; p[SWR_SEG_OFF_GUASTO] = bootGuasto;
  memcpy(p + SWR_SEG_OFF_RESETREAS, &bootRr, 4);
  memcpy(p + SWR_SEG_OFF_PC, &bootCtx.pc, 4); memcpy(p + SWR_SEG_OFF_LR, &bootCtx.lr, 4);
  memcpy(p + SWR_SEG_OFF_CFSR, &bootCtx.cfsr, 4); memcpy(p + SWR_SEG_OFF_HFSR, &bootCtx.hfsr, 4);
  p[SWR_SEG_OFF_FASE] = bootFase; p[SWR_SEG_OFF_ORIGINE] = origine;
  // tempo di sessione continuo (swr_formato.h byte 64..73): tempo di sessione = millis + scarto
  memcpy(p + SWR_SEG_OFF_SCARTO, &bootScarto, 4);
  p[SWR_SEG_OFF_TORIG] = bootOrigScarto;
  memcpy(p + SWR_SEG_OFF_MARGINE, &bootMargine, 2);
  p[SWR_SEG_OFF_NAVVII] = bootNAvvii;
  { uint16_t ta = T_AVVIO_MS; memcpy(p + SWR_SEG_OFF_TAVVIO, &ta, 2); }
  diario(DIA_NOTA, 10, bootOrigScarto, bootMargine, bootScarto);
  swrIntestazione(p, SWR_T_SEGMENTO, SWR_FORMATO, anello.numeroPagina(), millis(), vMv, vTemp, 0, vSeg);
  if (!anello.scriviPagina(p)) { uscitaAnticipata(origine, riprese, true); lampi(LED_R, 10, 60, 60); dormiVasca(false); }
  vPagineSeg++;
  regScrivi(1, riprese);                                 // seconda rete (brownout: GPREGRET2 si perde)
  gpregretImposta(MARCA_REGISTRA | (riprese > 15 ? 15 : riprese));   // rete principale: sopravvive a reset software, watchdog e HardFault
  diario(DIA_REG_INIZIO, origine, vSeg, vMv, riprese);
  diarioFlush();
  cane();
  if (!vImuAvvia()) { uscitaAnticipata(origine, riprese, true); lampi(LED_R, 10, 60, 60); dormiVasca(false); }   // IMU che non parte: in ripresa reset (riaccende l'IMU)
  vAttivo = true;
  lampi(LED_G, 3, 150, 150);                             // registrazione avviata (nel frattempo il FIFO viene svuotato)
  ledTocchi = false;                                     // fine della gestione dei tocchi: da qui LED di nuovo spenti a batteria

  uint32_t tBat = millis(), tLed = millis(), tFifo = 0, tDia = millis(), tVivo = millis(), campPrec = 0;
  bool resetRip = (riprese == 0);                       // il contatore delle riprese si azzera anche dopo 10 min di registrazione stabile
  uint8_t sotto = 0;
  while (!vMotivo) {
    FASE(10);
    {                                                    // vitalita' del flusso dati: se i campioni non crescono per 5 s si smette di servire il
      uint32_t o2 = millis();                            // watchdog (IMU o FIFO bloccati): scatta il reset e la ripresa automatica, che riaccende l'IMU.
      if (vCampioni != campPrec) { campPrec = vCampioni; tVivo = o2; }   // Chiudere con ERRORE perderebbe il resto dell'allenamento; la ripresa e'
      else if (o2 - tVivo > 5000UL && !wdtSospeso) {                      // comunque limitata a MAX_RIPRESE consecutive.
        wdtSospeso = true;
        logRiga("flusso dati fermo: reset");
        diario(DIA_NOTA, 6, 0, 0, vCampioni);
        diarioFlush();
      }
      if (!resetRip && !wdtSospeso && o2 - vInizioMs >= 600000UL && Bluefruit.Periph.connected() == 0) {   // 10 min stabili: catena finita (solo senza client BLE: regScrivi puo' durare 2 s)
        resetRip = true;
        vServi();                                        // regScrivi dura fino a ~1,2 s (misurato): FIFO svuotato prima; succede al massimo una volta per catena
        regScrivi(1, 0);
        fifo.ultAcc = 0;
        gpregretImposta(MARCA_REGISTRA);
        diario(DIA_NOTA, 5, riprese);
        tVivo = millis(); campPrec = vCampioni;          // stallo pianificato
      }
    }
    cane();
    uint32_t ora = millis();
    if (ora - tFifo >= 20) {                             // FIFO (1,6 s di capienza): servito almeno ogni 20 ms quando il loop gira veloce
      if (tFifo) { uint32_t gap = ora - tFifo; if (gap > statGapMax) statGapMax = gap > 65535 ? 65535 : (uint16_t)gap; }
      tFifo = ora;
      vServi();
    }
    syncServi();                                         // invio a pezzi dei blocchi: non blocca la registrazione
    eseguiComandi();                                     // solo SLEEP e' accettato in registrazione
    if (sonnoRichiesto && !vMotivo) vMotivo = SWR_STOP_COMANDO;
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
    // Diario in flash: MISURATO (PROVA_TEMPI, BLE in annuncio) 400-600 ms per scrittura, 800 ms con rotazione del file: il FIFO (1,6 s) lo regge,
    // ma e' uno stallo vero. Per questo al massimo ogni 120 s, dopo aver svuotato il FIFO, e con un solo record cumulativo per i riallineamenti.
    // MISURATO con un client BLE collegato (ble_carico.py): diarioFlush fino a 931 ms, regScrivi 2014 ms, overrun del FIFO: con un collegamento
    // attivo la flash interna e gli slot radio si contendono e gli stalli superano 1 s. Quindi NIENTE scritture flash nel ciclo finche' un client
    // e' collegato (il display si collega solo per scaricare, a bordo vasca): gli eventi restano in RAM (40 posti) e si scrivono dopo lo scollegamento
    // o alla chiusura. Se la RAM sta per riempirsi (>= 32 eventi) si scrive comunque.
    if ((diaPend || fifo.disallNuovi) && millis() - tDia >= 120000UL && (Bluefruit.Periph.connected() == 0 || diaPend >= DIARIO_RAM - 8)) {
      tDia = millis(); FASE(14);
      vServi();                                                                                  // FIFO svuotato subito prima dello stallo
      if (fifo.disallNuovi) { diario(DIA_DISALL, 0, fifo.disallNuovi, fifo.statDisall); fifo.disallNuovi = 0; }
      diarioFlush();
      fifo.ultAcc = 0;
      tVivo = millis(); campPrec = vCampioni;            // lo stallo e' pianificato: non conta come flusso fermo
    }
    delay(syncAttivo ? 2 : 40);
  }
  // chiusura sicura: pagina parziale, pagina di chiusura, poi sospensione
  vAttivo = false;
  wdtSospeso = false;                                    // dopo l'uscita dal ciclo il watchdog si serve di nuovo (la chiusura e gli annunci durano piu' di 8 s)
  cane();
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
    p[26] = fifo.statOverrun;
    p[27] = statApriMax & 0xFF; p[28] = statApriMax >> 8;
    p[29] = statConfermati & 0xFF; p[30] = statConfermati >> 8;
    p[SWR_CHIUS_OFF_DISALL] = fifo.statDisall & 0xFF; p[SWR_CHIUS_OFF_DISALL + 1] = fifo.statDisall >> 8;      // 0.6.1
    { uint16_t sc = fifo.statScartate > 0xFFFE ? 0xFFFE : fifo.statScartate; p[SWR_CHIUS_OFF_SCARTATE] = sc & 0xFF; p[SWR_CHIUS_OFF_SCARTATE + 1] = sc >> 8; }
    swrIntestazione(p, SWR_T_CHIUSURA, motivo, anello.numeroPagina(), millis(), vMv, vTemp, 0, vSeg);
    anello.scriviPagina(p);
  }
  anello.chiudi();                                       // da qui il blocco e' "da validare" e si puo' inviare
  gpregretImposta(MARCA_SLEEP);                          // chiusura ordinata: niente ripresa automatica. PRIMA la marca (e' istantanea) ...
  regScrivi(0, 0);                                       // ... poi il file (~1 s): un guasto in mezzo lascia la marca gia' disarmata
  {
    uint32_t dur = (millis() - vInizioMs) / 1000;
    if (fifo.disallNuovi) { diario(DIA_DISALL, 0, fifo.disallNuovi, fifo.statDisall); fifo.disallNuovi = 0; }
    diario(DIA_REG_FINE, motivo, vSeg, vMv, dur);
    diario(DIA_NOTA, 4, fifo.statOverrun, fifo.statDisall);
    diario(DIA_NOTA, 7, statDiaMs, statRegMs, statGapMax);        // misure: massimo di diarioFlush e regScrivi (ms) e massimo intervallo fra letture del FIFO
    diarioFlush();
  }
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
  static char buf[32]; static uint8_t n = 0;
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
            cane();
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
          cane();
          Serial.write(blocco, np * SWR_PAGINA);
        }
        Serial.printf("\nEND %lu\n", (unsigned long)usate);
        Serial.flush();
        dumpInCorso = false;
      }
    } else if (!strcmp(buf, "DIARIO")) {
      diarioStampa(Serial);
    } else if (!strcmp(buf, "DIARIO,CANC")) {
      InternalFS.remove(diaFile); diaPend = 0; Serial.println("K diario cancellato");
#if PROVE_GUASTI
    } else if (!strncmp(buf, "PROVA_", 6)) {
      { char *a = strchr(buf, ','); if (a) *a++ = 0; provaComando(buf, a); }
#endif
    } else if (buf[0]) {
      Serial.println("X comando");
    }
  }
}

// USB staccata in modalita' normale (VBUS sparito per ~0,5 s) = sonno subito: a batteria la modalita' normale non esiste (0.6.1).
// Distingue PC (enumerazione USB: tud_mounted) da caricatore (VBUS senza enumerazione) e lo scrive nel diario.
static void controlloUsb() {
  static uint32_t t = 0;
  static uint8_t assente = 0;
  static int8_t tipoPrec = -1;
  uint32_t ora = millis();
  if (ora - t < 100) return;
  t = ora;
  if (!vbusPresente()) {
    if (++assente >= VBUS_ASSENZA_N && !otaAttivo) {         // 2 s di assenza continua (prima 0,5 s: bastava un disturbo)
      logRiga("USB staccata: sonno");
      diario(DIA_USB, 0, 0, 0);
      sonnoMotivo = 4;
      vaInSospensione();
    }
    return;
  }
  assente = 0;
  int8_t tipo = TinyUSBDevice.mounted() ? 1 : 2;
  if (tipo != tipoPrec) { tipoPrec = tipo; diario(DIA_USB, tipo, ultimaMv); }
}

void setup() {
  // Causa del reset: il core azzera RESETREAS in init() (wiring.c) PRIMA di setup() ma ne conserva una copia, readResetReason().
  // Il bootloader Adafruit NON lo azzera (main.c 0.6.2): la nota della 0.5.0 era sbagliata, vedi LEGGIMI.
  uint32_t rr = readResetReason();
  bootRr = rr;
  bootWdtGiaAttivo = NRF_WDT->RUNSTATUS & WDT_RUNSTATUS_RUNSTATUS_Msk;   // il WDT sopravvive al reset? (si logga: ipotesi da verificare)
  // contesto del guasto precedente e fase del programma (RAM noinit), da leggere prima di riscriverli
  bootCtxValido = ctxRam.magic == CTX_MAGIC && ctxRam.chk == ctxChk(ctxRam) && (rr & (POWER_RESETREAS_DOG_Msk | POWER_RESETREAS_SREQ_Msk | POWER_RESETREAS_LOCKUP_Msk));
  if (bootCtxValido) bootCtx = ctxRam; else memset(&bootCtx, 0, sizeof(bootCtx));
  ctxRam.magic = 0;
  bootFase = ((faseRam & 0xFFFFFF00UL) == 0x5A5A5A00UL && (rr & (POWER_RESETREAS_DOG_Msk | POWER_RESETREAS_SREQ_Msk | POWER_RESETREAS_LOCKUP_Msk))) ? (faseRam & 0xFF) : 0;
  tempoAvvio(rr);                                          // prima di wdtAvvia(): cane() sovrascrive "ultimo vivo"
  wdtAvvia();
  FASE(1);
  if (rr & POWER_RESETREAS_VBUS_Msk) causaReset = 7;
  else if (rr & POWER_RESETREAS_OFF_Msk) causaReset = 1;
  else if (rr & POWER_RESETREAS_DOG_Msk) causaReset = 3;
  else if (rr & POWER_RESETREAS_SREQ_Msk) causaReset = 5;
  else if (rr & POWER_RESETREAS_LOCKUP_Msk) causaReset = 6;
  else if (rr & POWER_RESETREAS_RESETPIN_Msk) causaReset = 8;
  else causaReset = 0;
  if (bootCtxValido && bootCtx.tipo >= 1 && bootCtx.tipo <= 5) bootGuasto = bootCtx.tipo;
  else if (rr & POWER_RESETREAS_DOG_Msk) bootGuasto = SWR_GUASTO_WDT;
  else if (rr & POWER_RESETREAS_LOCKUP_Msk) bootGuasto = SWR_GUASTO_ALTRO;
  uint8_t marca = NRF_POWER->GPREGRET2;                      // marca lasciata prima di System OFF / durante la registrazione
  NRF_POWER->GPREGRET2 = 0;
  bootMarca = marca;
  bool vbusAvvio = NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk;
  // Risveglio causato dall'USB ma VBUS non ancora visto (lettura non assestata o contatto incerto, visto il 2026-11-11:
  // 3 avvii causa7 vbus0 di fila, ognuno tornato a dormire): si aspetta fino a 1 s prima di decidere. Diario NOTA 12.
  uint16_t attesaVbus = 0;
  if ((rr & POWER_RESETREAS_VBUS_Msk) && !vbusAvvio) {
    uint32_t t0 = millis();
    while (!vbusAvvio && millis() - t0 < VBUS_ATTESA_AVVIO_MS) {
      delay(10); cane();
      vbusAvvio = NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk;
    }
    attesaVbus = (uint16_t)(millis() - t0);
  }
  bool dormiva = marca == MARCA_SLEEP || (marca & 0xF0) == MARCA_FALSO;
  if (dormiva && !vbusAvvio && causaReset != 7) causaReset = 1;   // risveglio da doppio tap (la marca resta come conferma)

  bool quattroTap = false;
  if (causaReset == 1) quattroTap = risveglioQuattroTap();   // se non arrivano 4 tap non ritorna: torna a dormire
  cane();

  // Diario: avvio con causa, marca e contesto del guasto (in RAM; in flash al primo diarioFlush)
  {
    uint16_t comp = (rr & 0xF) | (((rr >> 16) & 0xF) << 4) | (((rr >> 20) & 1) << 8);
    diario(DIA_AVVIO, causaReset, comp, (uint16_t)(marca << 8) | (vbusAvvio ? 1 : 0) | (PROVE_GUASTI ? 2 : 0));
    {                                                        // il contesto del guasto deve stare fuori da [__bss_start__, __bss_end__): altrimenti lo startup lo azzera
      uint32_t ca = (uint32_t)&ctxRam;
      bool inBss = ca >= (uint32_t)&__bss_start__ && ca < (uint32_t)&__bss_end__;
      logRiga("ctx %08lX%s", (unsigned long)ca, inBss ? " IN BSS!" : "");
      if (inBss) diario(DIA_NOTA, 8, 0, 0, ca);
    }
    if (bootGuasto != SWR_GUASTO_NESSUNO || bootCtxValido) {
      diario(DIA_GUASTO, bootGuasto, bootFase, 0, bootCtx.pc);
      diario(DIA_GUASTO2, 0, (uint16_t)(bootCtx.cfsr & 0xFFFF), (uint16_t)(bootCtx.cfsr >> 16), bootCtx.lr);
    }
    if (bootWdtGiaAttivo) diario(DIA_WDT, 1);
    if (attesaVbus) diario(DIA_NOTA, 12, vbusAvvio, attesaVbus);   // NOTA 12 <vbus visto 0/1> <ms attesi> (NOTA 10 = tempo di sessione)
  }

  // ---- REGOLE DI MODO (0.6.1) ----
  // senza USB la modalita' normale non esiste: o si registra (4 tocchi, o ripresa dopo un riavvio inatteso) o si dorme
  if (!vbusAvvio) {
    if (quattroTap) { modalitaVasca(0); }                    // non ritorna
    if ((marca & 0xF0) == MARCA_REGISTRA) { modalitaVasca(1); }   // riavviata in registrazione (rete principale)
    if (!dormiva) {                                          // seconda rete (marca persa: brownout): stato in /reg.bin + ultimo segmento senza chiusura
      uint8_t att = 0, rip = 0;
      regStato(att, rip);
      if (att) { modalitaVasca(2); }
    }
    lampoBreve(false, false, true);                          // un lampo blu da 15 ms: "ci sono ma non registro" (anche a batteria)
    sonnoMotivo = 5;                                         // nessuna ragione per registrare (es. batteria appena collegata): sonno
    diario(DIA_MODO, 2, sonnoMotivo, 0);
    diarioFlush();
    dormiSenzaBle();                                         // non ritorna
  }
  // da qui: USB presente (PC o caricatore), modalita' normale, mai registrazione. Una registrazione orfana non riparte piu'.
  {
    uint8_t att = 0, rip = 0;
    regStato(att, rip);
    if (att) { regScrivi(0, 0); diario(DIA_NOTA, 1, rip); }
  }

  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) { cane(); delay(10); }   // attende l'enumerazione/DTR (PC): con un caricatore scade e basta

  pinMode(LED_RED, OUTPUT); pinMode(LED_GREEN, OUTPUT); pinMode(LED_BLUE, OUTPUT);
  ledScrivi(LED_RED, HIGH); ledScrivi(LED_GREEN, HIGH); ledScrivi(LED_BLUE, HIGH);
  pinMode(PIN_NCHG, INPUT_PULLUP);
  pinMode(PIN_CHARGING_CURRENT, OUTPUT); digitalWrite(PIN_CHARGING_CURRENT, LOW);   // P0.13 basso: carica a 100 mA (resta impostato anche in System OFF)
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);

  const char *nomi[] = {"accensione", "doppio tap", "?", "watchdog", "?", "software", "lockup", "USB", "pin reset"};
  logRiga("boot %s, causa %s (RESETREAS 0x%lX)", VERSIONE, nomi[causaReset], (unsigned long)rr);
  logRiga("marca %02X vbus %d wdt-gia %d", marca, vbusAvvio, bootWdtGiaAttivo);
  if (bootGuasto) logRiga("guasto t%u fase%u pc%08lX lr%08lX", bootGuasto, bootFase, (unsigned long)bootCtx.pc, (unsigned long)bootCtx.lr);
  if (quattroTap) logRiga("risveglio 4 tap");
  if (*(volatile const char *)marcatoreVersione != 'S' || *(volatile const char *)marcatoreScheda != 'S') logRiga("?");   // tiene il marcatore nel binario (altrimenti il linker lo scarta)

  bleIniz(false);                       // BLE: 2 collegamenti, servizi 7a1e0001 (pagina) e 7a1e0101 (display), annuncio di sincronizzazione
  cane();
  if (memInit()) {                      // anche in modalita' normale la flash si scansiona: il display puo' scaricare con l'USB collegata
    EsitoScansione es = memScansiona();
    logRiga("memoria: %s, da validare %u, confermati %u, liberi %u, seq %lu", es == SC_OK ? "formato 3" : es == SC_FORMATO1 ? "FORMATO 1 (non toccata)" : "estranea",
            anello.nDaValidare, anello.nConfermati, anello.nLiberi, (unsigned long)anello.maxSeq);
  } else logRiga("flash non risponde");
  cane();

  imuOk = imuInit();   // dopo il BLE: se l'IMU non risponde il tag resta comunque visibile
  logRiga(imuOk ? "IMU ok" : "IMU NON risponde");
  cane();
  if (imuOk) calibraBoot();
  aggiornaStato(true);
  diario(DIA_BATT, (vbusPresente() ? 1 : 0) | ((digitalRead(PIN_NCHG) == LOW) ? 2 : 0), ultimaMv);
  diario(DIA_MODO, 0, 0, ultimaMv);
  diarioFlush();
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
    sonnoMotivo = 2;
    vaInSospensione();
  }
}

void loop() {
  static uint32_t ultimoDati = 0, ultimoStato = 0, ultimoLed = 0;
  cane(); FASE(20);
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
  FASE(21);
  servizioOta();
  FASE(22);
  controlloUsb();                           // USB staccata -> sonno subito (a batteria la modalita' normale non esiste)
  diarioInvioServi();
  { static uint32_t tDia = 0; if (diaPend && !diaInvioN && millis() - tDia >= 10000UL) { tDia = millis(); diarioFlush(); } }
  inviaLog();
  syncServi();                              // sincronizzazione con il display (anche con l'USB collegata)
  if (sonnoDaSync) { sonnoDaSync = false; sonnoMotivo = 1; vaInSospensione(); }   // M_SONNO (con l'USB: riavvio, NOTA 11)
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
