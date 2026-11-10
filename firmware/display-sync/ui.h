// Interfaccia (core 1): legge solo una copia dello stato e ridisegna ~5 volte al secondo.
#pragma once

void uiInit();       // display, tele in PSRAM, schermata di avvio
void uiAggiorna();   // da chiamare dal loop(): ridisegna se e' passato il tempo
