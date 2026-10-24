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

## Logica partenza/arrivo (ipotesi del 2026-10-24)
Ipotesi: display solo sul lato di partenza, distanze multiple di 100 m (in vasca da 25 m si finisce sempre sul lato del display).

- **START**: picco di spinta dal muro (accelerometro), confermato dalla sparizione del segnale BLE.
- **STOP**: tag vicino al display (RSSI alto) **e** calma per almeno ~3 s. L'ora di STOP non è quella in cui si conferma la calma, ma quella della **decelerazione all'arrivo** (il tag la memorizza e la usa a posteriori).
- **Virata (rischio di STOP falso)**: dura meno di 1–2 s ed è seguita subito da una nuova spinta, quindi non supera mai i ~3 s di calma → il cronometro non si ferma. La virata viene registrata come **parziale**.
- **Fermata a metà vasca o sul lato opposto** (occhialini, crampo): calma ma tag lontano dal display → nessuno STOP.
- **Conteggio vasche**: ogni virata riconosciuta = una vasca; a fine prova vasche × lunghezza vasca = distanza, utile come controllo (es. 200 m = 8 vasche da 25 m).
- **Riposo**: da STOP alla spinta successiva.

## Logiche aggiuntive possibili (da valutare)
| Logica | Sensore | Cosa dà | Note |
|---|---|---|---|
| Inversione di direzione | magnetometro (bussola) | ogni vasca la direzione ruota di 180° → conteggio vasche robusto | conta la variazione relativa, non il nord esatto |
| Profondità | sensore di pressione impermeabile (es. MS5837) | testa sott'acqua / fuori; scivolata dopo la spinta; capriola | conferma START e virata in modo indipendente dal BLE |
| Bracciate | giroscopio | conteggio bracciate, frequenza, riconoscimento dello stile | utile per statistiche, non per i tempi |
| Gesto manuale | accelerometro | doppio colpetto sul tag = START/STOP forzato o annulla | rimedio per i casi sbagliati |
| Partenza comandata | display | il display dà il via (luce/beep) secondo una serie impostata (es. 4×100 rec. 20 s) | START certo; diventa anche un "pace clock" |
| Arrivo al muro | sensore sul display (distanza a infrarossi/ToF, o piastra a tocco) | STOP preciso come nelle gare | più ingombrante; il display va fissato al bordo |

Combinazione consigliata: accelerometro + giroscopio + magnetometro (+ pressione) nel tag, BLE solo per prossimità e invio dei dati.

## Dove mettere il tag
- **Cuffia/elastico degli occhialini, dietro la testa**: è la parte che emerge più spesso (respirazione) ed è la più vicina al muro all'arrivo. Candidato preferito.
- Polso: emerge a ogni bracciata, ma all'arrivo può essere lontano dal display.

## Componenti candidati (da verificare)
- Tag: Seeed **XIAO nRF52840 Sense** (BLE, sensore inerziale e ricarica batteria integrati, 21×17 mm) + batteria LiPo piccola, resinato in un guscio.
- Display: **ESP32** con display grande e luminoso, leggibile da 2–3 m con gli occhialini (es. cifre LED a 7 segmenti alte 5–10 cm o matrice LED), a batteria.

## Primo esperimento proposto
Prima di costruire: due schede BLE qualsiasi, una in un sacchetto stagno sulla cuffia, l'altra a bordo vasca che registra RSSI e accelerazioni. Si fanno alcune vasche e si guardano i dati per tarare la logica.
