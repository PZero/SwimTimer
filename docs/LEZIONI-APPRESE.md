# Lezioni apprese dal prototipo (ESP32-S3 SuperMini + GY-BMI160)

Cosa non è andato bene col prototipo e che cosa deve garantire la scheda miniaturizzata (nRF52840). Ogni voce: **problema → requisito per la scheda**. Da verificare sulla v0.2 prima dell'ordine.

## Sensore inerziale

1. **Reset dell'accelerometro impossibile senza dissaldare.** Dopo uno spegnimento brusco il BMI160 andava in latch-up: assorbiva molta corrente, il 3V3 crollava a 0 V e ripartiva solo staccando GND. Un'altra volta teneva SDA a 0 V.
   → Alimentazione del sensore **commutata** dal microcontrollore (load switch, es. TPS22916, o P-MOSFET), con scarica rapida dell'uscita.
   → **Tutto** ciò che sul sensore va alto (CS, SDO/indirizzo, pull-up I2C) va preso dal lato commutato, mai dal 3V3 sempre acceso: altrimenti il sensore resta alimentato attraverso i pin e non si resetta.
   → Il firmware deve poter mettere bassi i pin del sensore prima di spegnerlo (nessun pin con pull-up fisso verso il 3V3 principale).
   → Valutare **SPI** al posto dell'I2C: niente bus bloccato.

2. **Tap simulato poco affidabile** (riconosciuto circa 1 volta su 10). Il tap è calcolato dal firmware sui campioni a ~44 Hz reali, troppo pochi per un colpo che dura pochi millisecondi; il motore tap del BMI160 non funzionava perché non aveva un pin d'interrupt mappato.
   → **Entrambi gli interrupt del sensore (INT1, INT2) collegati** a GPIO in grado di svegliare il micro.
   → Usare il **riconoscimento tap in hardware** del sensore (singolo/doppio tap a frequenza interna alta), non quello simulato. Valutare un sensore con motore tap ben documentato (es. LSM6DSO/LSM6DSOX, LIS2DW12) se il BMI160 resta incerto.
   → Il tap deve funzionare anche col micro in sonno.

3. **Campioni persi** (100 Hz nominali, ~44 Hz reali) durante le scritture in flash.
   → Usare la **FIFO** del sensore con interrupt di soglia; flash scritta a blocchi.

4. **Fondo scala perso**: scritto a sensore sospeso, non veniva applicato (±2 g invece di ±16 g).
   → Firmware: configurazione scritta a sensore attivo e **sempre riletta**. Vale per qualsiasi sensore.

## Batteria e alimentazione

5. **Valori batteria inaffidabili con e senza carica** (2% letto, 3,5 V; in carica la pagina toglieva 0,15 V fissi e segnava 29% invece di ~65%, ma la crescita misurata è solo 0,03–0,05 V e dipende dalla corrente; non si capiva se fosse la pila o la misura).
   → **Misuratore di carica** (es. MAX17048) oppure partitore ad alta impedenza **scollegabile** (FET) con condensatore sull'ingresso ADC.
   → Segnale di **stato del caricatore** (CHG/STDBY) e presenza USB letti da GPIO: sapere sempre se è in carica, e tarare la stima separatamente nei due casi.
   → Punto di test su VBAT.
   → Con USB collegata e batteria **staccata** (interruttore aperto, saldatura fredda) il pin BAT mostra comunque ~4,2–4,3 V, la tensione del caricatore: la misura sembra "batteria piena". Serve un modo per sapere se la batteria è davvero collegata (misura a carica sospesa o misuratore di carica).

6. **Nessun modo di spegnere tutto**: batteria saldata sui pad, niente interruttore; per sbloccare bisognava dissaldare (ora c'è un interruttore provvisorio).
   → Spegnimento vero compatibile con la custodia stagna: reed + magnete, ship mode del caricatore, o interruttore di carico comandato. Il reset all'inserimento in custodia della v0.2 va in questa direzione.

7. **Regolatore in protezione per corto a valle** (il 3V3 a 0 V ha salvato l'ESP32).
   → Regolatore con limitazione di corrente e protezione termica; protezione dall'inversione della batteria.

8. **Display a batteria che non si accende** (sospetto polarità del connettore).
   → Connettore batteria polarizzato, + e − serigrafati, protezione da inversione.

9. **Riavvii spontanei** del tag.
   → Condensatori di riserva vicino alla radio, brown-out abilitato, **motivo del reset salvato** e leggibile via BLE.

## Diagnosi e programmazione

10. **Guasto difficile da capire**: niente porta USB visibile, solo il LED di carica acceso.
    → **Punti di test** accessibili: 3V3, VBAT, GND, SDA/SCL (o SPI), e una piazzola/0 Ω in serie per misurare la corrente.
    → LED di stato pilotabile dal firmware (riscontro: registra, dorme, errore sensore).

11. **Non si entrava in modalità BOOT** con la batteria collegata; con firmware bloccato la USB spariva.
    → Piazzole **SWD** (pogo pin) sempre accessibili e reset raggiungibile; aggiornamento via BLE con ritorno automatico alla versione precedente (già provato sul prototipo).

12. **Vibrazione non pilotabile direttamente da un GPIO.**
    → Se serve il riscontro aptico: driver a MOSFET con diodo di ricircolo già sulla scheda.

## Radio

13. **Il BLE non attraversa l'acqua.**
    → La logica e la memoria stanno sul tag; antenna lontana da batteria e corpo, area libera da rame come da datasheet.

## Firmware, prove e metodo (incidente in vasca del 2026-11-11 e giornata di correzioni)

Ogni voce: **cosa è successo → regola**.

14. **Lo stato «sto registrando» viveva solo in RAM.** La tag si è riavviata dopo 10:42 e il ramo predefinito di `setup()` era la modalità normale (PRONTA, tocchi ignorati): tutto il nuoto perso.
    → Ogni stato importante deve sopravvivere al riavvio (marca in GPREGRET2 **e** file in flash: il reset del watchdog azzera la marca, la seconda rete ha salvato la ripresa).
    → Il ramo predefinito di ogni decisione è quello sicuro (registrare o dormire), mai quello comodo al banco.
15. **Nessuno stato deve essere silenzioso.** LED spenti a batteria + memoria piena = la tag non partiva e nessuno lo sapeva.
    → A batteria i LED si accendono solo nella gestione dei tocchi (blu, verde, rosso 2 s, 3 lampi verdi) e negli errori all'avvio; la pagina della scheda mostra gli avvisi con l'azione da fare.
16. **Memoria piena = la tag non registra più** (decisione: si ferma, non sovrascrive). Prima di ogni seduta controllare «Da scaricare 0 %» o `MEM` via USB.
17. **FIFO dell'LSM6 disallineato** (acc e giro scambiati) e lettura I2C oltre 32 byte che perde dati. Un controllo che sposta dati va provato con **urti e movimento reali** e non deve poter creare l'errore che cura. Con la scheda collegata i riallineamenti salgono a ~40/min (da capire).
18. **La quiete non scattava** (bias del giroscopio imparato solo in quiete: se > 3 °/s non si impara mai). Correzione caricata ma **non ancora verificata**.
19. **USB: una lettura di 0,5 s non basta.** Un disturbo mandava in sonno la tag collegata, e al risveglio da USB VBUS non era ancora assestato → di nuovo a dormire. Regole: 2 s per «USB staccata», attesa fino a 1 s all'avvio da USB, mai System OFF con VBUS presente (`NOTA 11`). Conseguenza non voluta: dalla pagina del PC la tag su USB non si spegne più (si riavvia).
20. **Scritture in flash interna con il BLE collegato bloccano fino a 2 s** (overrun). Si misurano sempre con il BLE collegato e lo scarico attivo, non in annuncio.
21. **Wi-Fi e BLE sulla stessa radio (ESP32-S3):** con la scansione BLE all'80 % la rete SwimTimer spariva; ora al 30 %. L'iPhone su una rete senza internet manda le richieste in cellulare: **disattivare Dati cellulari e Assistenza Wi-Fi**.
22. **Collegamento BLE sempre aperto** (tag vicina): la tag annuncia SINCRONIZZA e la pagina mostrava SCARICA invece di REGISTRA; la mappa non si aggiornava. La prova che i dati arrivano è «Ultimo blocco salvato su SD».
23. **Hardware fragile:** smontando il display per le misure si è strappata la piattina → schermo perso. Non smontare i moduli con piattine senza un motivo; fotografare e misurare da montati.
24. **Prima di caricare una pagina web, controllare la sintassi del JavaScript** (un apostrofo ha rotto tutta la pagina).
25. **Sapere sempre quale tag e quale firmware.** Due tag con firmware diversi hanno confuso le prove: prima di provare, controllare `DIARIO` (riga `AVV … PROVE`) e il seriale USB (`…4A510689`, `…447B0247`).
26. **Il diario è il primo strumento di diagnosi**: ha risolto in pochi minuti USB instabile, memoria piena, riprese. Svuotarlo prima di una prova (`DIARIO,CANC`).

## Gestione dei token (PRIORITÀ: dimezzare il costo)

27. **Un agente ripreso porta con sé tutta la sua cronologia**: tre giri dello stesso agente sono costati 420k, 600k e 740k token. → Per ogni nuovo giro un agente **nuovo** con un incarico breve; mai riprendere un agente lungo.
28. **File enormi riletti più volte** (`xiao-stream.ino` > 2600 righe). → Grep + lettura a righe; dividere il file in moduli.
29. **Prove hardware senza limite** e revisioni con simulazioni non richieste. → Al massimo 3 tentativi, poi rapporto; revisore solo su `git diff`, un giro per modifica.
30. **Sessioni troppo lunghe**: la conversazione del coordinatore cresce e ogni passo costa di più. → Un obiettivo per sessione, `/clear` tra un obiettivo e l'altro, lettura iniziale solo di `docs/STATO.md`.
31. **Molti passaggi a mano per caricare il display** (BOT+RST, poi RST, ogni volta). → Raggruppare le modifiche e caricare una volta; valutare l'aggiornamento senza pulsanti.
