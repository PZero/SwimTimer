// SwimTimer - tipi di dati della 0.6.1 usati dallo sketch (in un header perche' il generatore di prototipi di Arduino li userebbe
// nei prototipi delle funzioni prima che lo sketch li definisca).
#pragma once
#include <stdint.h>

// Contesto del guasto, salvato in RAM "noinit" da HardFault_Handler e dall'IRQ del watchdog (vedi xiao-stream.ino)
struct CtxGuasto { uint32_t magic, tipo, pc, lr, cfsr, hfsr, fase, chk; };

// Record del diario persistente: 12 byte (sec dall'avvio, tipo, 3 parametri e un parametro a 32 bit)
struct __attribute__((packed)) RecDiario { uint16_t sec; uint8_t tipo, p1; uint16_t p2, p3; uint32_t p4; };

// Blocco del tempo di sessione continuo (RAM NOBITS): vedi xiao-stream.ino, tempoAvvio()
struct CtxTempo { uint32_t magic, nAvvii, scarto, margine, msReset, msVivo, flags, chk; };

// Eventi VBUS in RAM noinit (0.6.4), vedi xiao-stream.ino: ultTipo 0 mai, 1 vista, 2 persa; prec = evento di un avvio precedente
struct CtxVbus { uint32_t magic; uint16_t su, giu; uint32_t ultMs; uint8_t ultTipo, prec, pad[2]; uint32_t chk; };
