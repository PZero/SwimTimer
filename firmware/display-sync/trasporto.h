// Interfaccia verso il "lato tag": la implementano ble_sync.cpp (tag reali) o demo.cpp (SWIM_DEMO=1).
// Le notifiche dalla tag entrano in ricezioneNotifica(); i comandi escono da trasportoInvia().
#pragma once
#include "protocollo.h"

void trasportoInit();                       // avvia scansione/collegamenti (o la demo)
bool trasportoInvia(const Comando &c);      // accoda un comando per la tag; non blocca
void trasportoChiudi(int tag);              // chiede di chiudere il collegamento con la tag
