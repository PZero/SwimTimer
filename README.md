# SwimTimer

Tempi automatici in piscina: un piccolo tag BLE indossato e un display a bordo vasca riconoscono partenza e arrivo, senza pulsanti.

![Stato](https://img.shields.io/badge/stato-ideazione-lightgrey)

## Indice
- [Panoramica](#panoramica)
- [Architettura](#architettura)
- [Stato del progetto](#stato-del-progetto)
- [Struttura delle cartelle](#struttura-delle-cartelle)
- [Autore](#autore)

## Panoramica
Chi nuota in piscina fatica a conoscere i propri tempi per vasca e i riposi: il cronometro a muro non sempre c'è e guardare l'orologio interrompe l'allenamento. SwimTimer registra i tempi in automatico e li mostra a bordo vasca.

## Architettura
Ipotesi iniziale, in valutazione ([`docs/IDEA.md`](docs/IDEA.md)):

```mermaid
flowchart LR
  T[Tag BLE sul nuotatore<br/>accelerometro + orologio] -- eventi via BLE quando emerge --> D[Display a bordo vasca<br/>ESP32 + cifre grandi]
  D -. facoltativo .-> A[App sul telefono]
```

Hardware, firmware e uso: da definire.

## Stato del progetto
Fase 0, ideazione. Dettagli in [`docs/STATO.md`](docs/STATO.md), decisioni in [`docs/DECISIONI.md`](docs/DECISIONI.md).

## Struttura delle cartelle
```
docs/       idea, stato, decisioni, domande aperte, requisiti, design
hardware/   componenti, schema, involucri (da creare)
firmware/   codice di tag e display (da creare)
```

## Autore
PZero
