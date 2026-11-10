# Video v3 «Il primo test in vasca» – sequenza da approvare

Stesso stile dei video precedenti: 120 s, 1920x1080, 30 fps, IT ed EN, solo testi a schermo e musica originale, tagli sui battiti (120 BPM).

| Tempo | Scena | Testo a schermo (IT) | Immagini |
|---|---|---|---|
| 0–6 | **Gancio** | «Quando tocca davvero il muro?» · contatore che avanza di 0,02 s | Fotogramma subacqueo dal fondo: la mano arriva sul bordo, avanzamento fotogramma per fotogramma, poi fermo immagine |
| 6–14 | **La prova del 9 novembre** | Insta360 X4 sul fondo · 8:50 di video a 50 fps · tag XIAO in testa · 17 min di dati a 214 Hz (memoria piena) | Inquadratura larga dal fondo + scheda con i numeri della registrazione |
| 14–20 | **Sincronizzazione** | Un colpo sul tag = picco di 11,4 g = istante zero | Grafico dell'accelerazione con il picco + fotogramma del colpo (X a 0,82 s) |
| 20–30 | **Etichette a mano** | 78 eventi: 15 arrivi, 14 partenze, 12 virate, 36 bracciate | Schermata dell'editor di annotazione con video, grafici IMU e lista eventi |
| 30–46 | **I filtri sui dati IMU** | Orientamento della testa (Mahony) · viso al cielo / testa giù · quiete e scivolata · regole per arrivo, partenza, virata | Grafici IMU con le etichette A/P/V sovrapposte + testa 3D orientata; animazione delle soglie |
| 46–54 | **Risultati dei filtri** | Arrivi trovati 10 su 15 · errore ±0,88 s · tempo partenza→arrivo ±1,47 s · obiettivo ±0,3 s: **non raggiunto** | Tabella animata, valori in rosso |
| 54–64 | **Colpo di scena** | Lo stesso arrivo etichettato due volte: 152,06 → 151,62 s (−0,44) · 188,82 → 189,28 s (+0,46) · editor a 30 fps su video a 50 fps · orologi che derivano dello 0,24% · «Il problema era il riferimento» | Due fotogrammi dello stesso arrivo affiancati con le due etichette |
| 64–84 | **OpenCV** (drop musicale) | Stabilizzazione dell'immagine · sottrazione dello sfondo · filtro colore pelle contro le bolle · distanza del corpo dal muro, fotogramma per fotogramma | Prima/dopo della maschera · chimografo (tempo × distanza dal muro) · **arrivo completo**: 3 fotogrammi + curva della distanza dal muro + grafico IMU dello stesso istante |
| 84–92 | **Risultati OpenCV** | Partenze 14 su 14, ±0,14 s · tipo di evento: 0 errori · arrivi ±0,4 s, virate ±0,45 s · dal fondo il muro è una fascia: prossima volta camera sul muro | Fogli di confronto automatico / manuale |
| 92–106 | **La decisione** | Metodo strutturato: dataset, banco di prova in streaming, validazione su sessioni nuove · rete neurale solo per l'arrivo: notifica entro 1,5 s, tempo datato all'indietro al tocco · piccola rete 1D int8 sul nRF52840, confrontata con un metodo classico | Schema a blocchi: regola-porta → rete → tempo del tocco; linea del tempo tocco / notifica |
| 106–114 | **Prossimi passi** | Ripetute da 100 m · camera attaccata al muro · sync a inizio e fine · frequenza più bassa (52–104 Hz) per sedute più lunghe · editor a fotogrammi veri | Elenco animato + editor con un'etichetta spostata con le frecce |
| 114–120 | **Chiusura** | swimtimer-pzero.web.app · GitHub PZero/SwimTimer | Logo e indirizzi |

## Da decidere
- **Dati e immagini reali**: i video precedenti usavano solo dati inventati. Qui ci sarebbero fotogrammi subacquei tuoi e dati IMU veri della tua sessione, pubblicati su YouTube.
- **Durata** 120 s come i precedenti, oppure più lunga (es. 150 s) per dare respiro ai risultati.
- **Frequenza di campionamento**: i numeri della scena 106–114 si aggiornano quando arriva il rapporto del banco di prova.
