// Un solo task "scrittore SD" (core 0): verifica, salva, rilegge, indicizza e solo allora conferma.
#pragma once
#include "ricezione.h"

void sdInit();                    // da chiamare dopo uiInit(): monta la SD e avvia il task
void sdAccoda(const Lavoro &l);   // da qualsiasi task (non blocca)
