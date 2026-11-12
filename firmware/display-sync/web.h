// Punto di accesso Wi-Fi "SwimTimer" (192.168.4.1) con pagina di stato per il telefono.
// Gira in un task a bassa priorita' sul core 1: legge solo la copia dello stato, nessuna operazione lunga.
#pragma once

void webInit();   // se Wi-Fi o server falliscono, scrive il motivo sulla seriale e ritorna: il resto continua
