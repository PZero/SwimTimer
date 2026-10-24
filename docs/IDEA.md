# Idea iniziale (2026-10-24)

## Proposta dell'utente
- Un **tag BLE** piccolo e "intelligente" indossato dal nuotatore.
- Un **display a bordo vasca** che stima la distanza dal tag (RSSI).
- Tag vicino e fermo (più altri indizi) → **fine tempo**.
- Tag che si allontana rapidamente → **inizio tempo**.

## Analisi
**Problema fisico principale:** il BLE (2,4 GHz) è assorbito dall'acqua: sott'acqua il segnale sparisce dopo pochi centimetri. Il tag si "vede" solo quando è fuori dall'acqua.

Conseguenze:
- **Arrivo**: funziona bene. Quando ti fermi al muro la testa è fuori → RSSI alto e stabile.
- **Partenza**: la spinta dal muro avviene con la testa sott'acqua → il segnale **scompare di colpo**. Non è un allontanamento graduale, ma il momento della scomparsa è proprio un buon marcatore di partenza.
- **Durante la nuotata** il segnale è intermittente (si vede solo quando la testa emerge), quindi l'RSSI non serve a misurare la distanza percorsa.
- **Virate senza fermarsi** (capovolta): al muro la testa è sott'acqua, il display non vede niente. Servono sensori sul tag.

## Proposta migliorativa: tag con accelerometro
Il tag ha un sensore inerziale (accelerometro + giroscopio) e decide da solo i momenti chiave, con orologio interno preciso:
- **spinta dal muro**: picco di accelerazione;
- **virata**: rotazione rapida + spinta;
- **arrivo/riposo**: assenza di movimento.

Il tag memorizza gli eventi con l'ora e li invia al display ogni volta che emerge (bastano pochi millisecondi di contatto). L'RSSI resta utile come conferma "sono al muro della mia corsia" e per abbinare il tag al display.

## Dove mettere il tag
- **Cuffia/elastico degli occhialini, dietro la testa**: è la parte che emerge più spesso (respirazione) ed è la più vicina al muro all'arrivo. Candidato preferito.
- Polso: emerge a ogni bracciata, ma all'arrivo può essere lontano dal display.

## Componenti candidati (da verificare)
- Tag: Seeed **XIAO nRF52840 Sense** (BLE, sensore inerziale e ricarica batteria integrati, 21×17 mm) + batteria LiPo piccola, resinato in un guscio.
- Display: **ESP32** con display grande e luminoso, leggibile da 2–3 m con gli occhialini (es. cifre LED a 7 segmenti alte 5–10 cm o matrice LED), a batteria.

## Primo esperimento proposto
Prima di costruire: due schede BLE qualsiasi, una in un sacchetto stagno sulla cuffia, l'altra a bordo vasca che registra RSSI e accelerazioni. Si fanno alcune vasche e si guardano i dati per tarare la logica.
