# Ricerca: algoritmi IMU per il nuoto (tag sulla testa)

Data ricerca: 2026-10-25. Ricerca in rete condotta da un subagente. Convenzioni:
- **[F]** = riportato da una fonte (con link); **[D]** = deduzione nostra, da verificare.
- Alcune fonti (Mooney 2016 su PMC, Hamidi Rad su PMC, Delhaye 2022 su PMC, Shell 2021 PDF, Bächlin & Tröster 2012) non sono state aperte per intero (blocchi 403/CAPTCHA): di queste si riporta solo quanto visibile negli abstract/risultati di ricerca, e le cifre vanno ricontrollate prima di citarle altrove.

## 1. Sintesi

1. **Non esiste uno standard.** Esistono famiglie di metodi (soglie/regole su assetto e rotazione, FFT/autocorrelazione per la frequenza, classificatori su feature, CNN/LSTM su finestre) ma ogni gruppo usa sensore, posizione e protocollo diversi.
2. **Quasi tutta la letteratura usa sacro, polso o schiena**; la testa è minoritaria (il review 2022 di Sensors, citato in una ricerca, ne conta 7 su 18 contro 8 sulla zona lombare [F]). Il metodo più vicino al nostro caso è il **brevetto FORM (US 11833392, occhialini, 6 assi senza magnetometro)**: è descritto con filtri, soglie e finestre concreti e ci conviene prenderlo come base.
3. **Filtri**: passa-basso Butterworth 2° ordine a 10 Hz su ~100 Hz (brevetto FORM) per la fusione di assetto; passa-basso a 2 Hz per segmentare nuoto/virata da accelerometro (Topalovic 2014, polso); passa-banda 0,1-2 Hz per il dorso.
4. **Orientamento**: il brevetto FORM stima roll/pitch con filtro di Kalman e ruota gli assi giroscopio sull'asse antero-posteriore del nuotatore: coerente con la nostra calibrazione (gravità + cenno in avanti).
5. **Respirazione (stile libero)**: picchi del roll della testa >= 45° (FORM); in alternativa velocità angolare longitudinale con zero-crossing (Sensors 2022, IMU sotto doppia cuffia). Il roll dà anche il lato.
6. **Frequenza di bracciata**: dagli intervalli tra respiri (FORM) o FFT (roll per stile libero, accelerazione/roll per dorso). Con la testa **non** si vede direttamente la bracciata: è una stima [D, coerente con i brevetti].
7. **Stile**: su testa la letteratura è scarsa. Il dorso è più difficile da leggere perché la testa non cambia assetto come negli altri stili. Un dispositivo commerciale sotto la cuffia (TritonWear) ha sbagliato circa il 51% del tempo per stile in uno studio indipendente: **cautela**.
8. **Virate**: heading integrato dal giroscopio, variazione ~180° in finestra di ~6 s (FORM). Gli occhialini FORM contano le vasche al 99,8% (studio finanziato dall'azienda).
9. **Dataset pubblici**: l'unico trovato con etichette di stile e virate è quello di Brunner (smartwatch al polso, 40 nuotatori, 30 Hz). Nessun dataset pubblico con IMU sulla testa trovato: **dovremo costruirci il nostro**.
10. **Consiglio**: partire da regole fisiche (assetto, rotazione, FFT) con i parametri del brevetto FORM, registrare sessioni con video e dati grezzi a >= 100 Hz sul tag futuro (50 Hz sul BMI160 attuale), poi eventualmente un piccolo classificatore sulle feature raccolte.

## 2. Metodo consigliato per evento

### 2.1 Pre-elaborazione e orientamento
- FORM: campionamento ~100 Hz, Butterworth 2° ordine passa-basso a 10 Hz, roll/pitch con filtro di Kalman (Lee et al. 2012), nessun magnetometro [F: brevetto FORM].
- Calibrazione di montaggio: **[D]** gravità da fermo per l'asse verticale + cenno in avanti per l'asse antero-posteriore, poi ruotare tutti i dati nel sistema "testa". Il brevetto FORM fa un'operazione analoga per il giroscopio ("assi ruotati sull'asse antero-posteriore") [F].
- Sacro (altro posizionamento): fusione giroscopio+accelerometro con Madgwick, calibrazione funzionale a terra e 5 s in posizione eretta in acqua prima di ogni vasca [F: Hamidi Rad 2021]. Utile come idea per un "azzeramento" in vasca.

### 2.2 Respirazione (lato e frequenza)
- **Roll della testa**: picchi >= 45° = respiro; se i picchi di un lato sono in media >40° più grandi dell'altro, si ignora il lato debole; servono >= 3 respiri, altrimenti si ricade sulla FFT del roll [F: brevetto FORM].
- **Velocità angolare longitudinale (asse X)**: zero-crossing; il massimo/minimo prima = uscita del volto, dopo = rientro. IMU a 285 Hz, ±16 g, ±2000 °/s, sotto due cuffie, regione occipitale; 12 nuotatori, 100 m a stile libero. Errore (RMSE) < 0,005 s sull'ingresso; correlazione r = 0,916 (ingresso) e 0,856 (uscita); 90° percentile dell'errore 0,060 s / 0,197 s [F: [Sensors 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8879882/)]. Filtro non riportato.
- Lato: segno del roll al picco [D].
- Farfalla/rana: respiro dai picchi di accelerazione verticale (compensata dalla gravità) < -2,5 m/s² oppure dai picchi in avanti > 1 m/s² [F: brevetto FORM].

### 2.3 Frequenza e conteggio bracciate
- **Stile libero**: dagli intervalli tra respiri: bracciate pari per respiro dallo stesso lato, dispari per lato opposto; candidati tra 38 e 85 bracciate/min (alzati fino a 105 se molte righe vuote); media dei candidati selezionati [F: brevetto FORM].
- **Farfalla/rana**: tre candidati per coppia di picchi; limiti iniziali 17-37 bracciate/min (fino a 62); in rana si usa quasi sempre il primo candidato [F: brevetto FORM].
- **Dorso**: passa-banda 0,1-2 Hz, FFT su accelerazione verticale, in avanti e roll; si sceglie il segnale con ampiezza FFT normalizzata media più bassa e se ne prende il picco; correzione lineare finale. Validazione su 80 vasche, 20 nuotatori: errori in gran parte < 10%, metà dei casi < 3% [F: brevetto FORM].
- **Con sensore sulla cuffia**: segnale di movimento + analisi in frequenza per la frequenza di bracciata; 6 nuotatori d'élite, 15 settimane [F: Procedia Engineering 2016, solo abstract, [link](https://spiral.imperial.ac.uk/entities/publication/b9371f2a-ea86-4a61-a583-db4cf41ac367) (indicato in ricerca)]. Per gli accelerometri in genere: errore di frequenza ~0,72 bracc/min (13 nuotatori d'élite, limiti -2,20 / +1,90) [F: [PMC5469343](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5469343/)].
- Sacro/schiena: picchi della velocità angolare longitudinale (libero e dorso) o mediolaterale (rana e farfalla) per separare i cicli [F: Hamidi Rad 2021].

### 2.4 Stile
- FORM: confronto con profili ideali di accelerazione/velocità angolare o classificatore (es. SVM) [F: brevetto]. Occhialini FORM: 99,7% di stile corretto in 2.354 vasche, 36 nuotatori ricreativi, ma studio con coinvolgimento dell'azienda; IMU a 9 assi [F: [Eisenhardt 2023](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2023.1188102/full)].
- CNN su finestre 6 s (30 Hz, 11 canali, passo ~83% sovrapposizione): F1 97,4% (stile), 99,2% (conteggio vasche) con smartwatch al polso [F: [Brunner 2019](https://tik-old.ee.ethz.ch/file/0f8e59e6f86814ae7d7cb042effa8a5b/Swimming_paper_ISWC2019___camera_ready.pdf)]. Funziona per il polso: **[D]** non è garantito per la testa.
- Soglie su accelerometro filtrato a 2 Hz (polso, 100 Hz): nuoto/virata 100%, stile libero/rana/dorso 100%, farfalla 95%, 10 nuotatori [F: [Topalovic 2014](https://www.scitepress.org/Papers/2014/51345/51345.pdf)].
- Sacro, 35 nuotatori, 8 classi (4 stili, riposo, spinta dal muro, subacquea, virata): F1 0,96, precisione temporale 0,02 s [F: [Delhaye 2022](https://www.mdpi.com/1424-8220/22/15/5786), solo abstract].
- Testa: dorso più difficile perché l'assetto cambia poco (riportato in una sintesi di ricerca di un vecchio studio con accelerometro sulla testa, fonte primaria non individuata).
- **Avvertenza**: TritonWear (sotto cuffia, occipitale) in uno studio indipendente ha sbagliato il tempo per stile del 51% e sottostimato la distanza; uno studio precedente su 20 giovani nuotatori era più favorevole (tempi parziali, velocità, bracciate con CV < 5%) [F: [Shell 2021](https://lida.sport-iat.de/ta/Record/4073410?lng=en), [Butterfield/Movement & Sport Sciences 2019](https://research.stmarys.ac.uk/id/eprint/3372)].

### 2.5 Virate (capriola e aperte) e vasche
- FORM: assi giroscopio ruotati sull'asse antero-posteriore, heading integrato su finestre di ~6 s ogni 1,75 s, partenza heading ~90° (o 270°) per evitare il salto 0/360°, filtro mediano, virata se max-min ≈ 180° (anche 175°); finestre sovrapposte unite; tempo di virata = fine finestra precedente o picco di accelerazione alla spinta [F: brevetto].
- Occhialini FORM: conteggio vasche 99,8% su 2.354 vasche [F: Eisenhardt 2023].
- Sacro: fasi per vasca (spinta, scivolata, preparazione bracciata, nuoto) con approccio macro-micro e 4 telecamere subacquee come riferimento; errore all'inizio fase di virata 24 ± 97 ms [F: Hamidi Rad ECSS 2020, abstract; [Hamidi Rad 2021](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2021.793302/full) senza dettagli di virata/partenza].
- Virata a capriola vs aperta: **nessuna fonte specifica trovata**. [D] distinguere dalla velocità angolare di pitch/roll durante la rotazione (capriola = grande rotazione sul piano sagittale) e dall'impulso alla spinta.

### 2.6 Partenza (tuffo e dal muro), arrivo, fase subacquea
- Nessuna fonte con sensore sulla testa trovata per tuffo/arrivo. Nel sacro si distinguono "partenza", "spinta dal muro" e "subacquea" come classi di una rete neurale (Delhaye 2022) [F, solo abstract].
- Brevetto FORM: la virata si data con il picco di accelerazione alla spinta [F].
- [D] Partenza dal muro: picco di accelerazione + scivolata a velocità decrescente; tuffo: caduta libera/impatto con l'acqua + assetto in avanti; arrivo: ultimo ciclo di bracciata seguito da arresto e/o impatto con il muro. Da calibrare con i nostri dati.

### 2.7 Segmentazione nuoto/riposo
- Soglie su accelerometro dopo passa-basso 2 Hz; due impulsi "nuoto" a distanza < 2,5 s vengono uniti [F: Topalovic 2014].

## 3. Fonti principali

| Fonte | Anno | Posizione | Metodo | Accuratezza | Link |
|---|---|---|---|---|---|
| Mooney et al., Inertial sensor technology for elite swimming performance analysis: a systematic review (Sensors) | 2016 | review (varie) | rassegna di rilevamento partenze/virate/nuoto | n/d (non letto per intero) | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4732051/ |
| Brevetto FORM Athletica, US 11833392 | 2023 (priorità 2018) | testa (occhialini) | Butterworth 10 Hz, Kalman, heading, picchi roll, FFT | dorso: errori per lo più < 10% | https://patents.google.com/patent/US11833392B2/en |
| Sensors 22(4):1419, Integrated timing of stroking, breathing, kicking | 2022 | testa (occipitale, 2 cuffie), polso, caviglia | zero-crossing velocità angolare | RMSE < 0,005 s; r 0,86-0,92 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8879882/ |
| Eisenhardt et al., FORM goggles (Front. Sports Act. Living) | 2023 | testa (occhialini, 9 assi) | ML a bordo | stile 99,7%; vasche 99,8%; bracciate MAPE 6,4% | https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2023.1188102/full |
| Shell et al., head-worn inertial sensor (IJSPP) | 2021 | testa sotto cuffia (TritonWear) | commerciale | stile errato ~51%; distanza sottostimata | https://lida.sport-iat.de/ta/Record/4073410?lng=en |
| Cap-mounted tri-axial accelerometer (Procedia Eng. 147) | 2016 | cuffia | movimento + frequenza | n/d (solo abstract) | https://spiral.imperial.ac.uk/entities/publication/b9371f2a-ea86-4a61-a583-db4cf41ac367 |
| Brunner et al., ISWC | 2019 | polso (smartwatch) | CNN su finestre 6 s, 30 Hz | F1 97,4% stile; 99,2% vasche | https://tik-old.ee.ethz.ch/file/0f8e59e6f86814ae7d7cb042effa8a5b/Swimming_paper_ISWC2019___camera_ready.pdf |
| Delhaye et al., single IMU deep learning (Sensors 22:5786) | 2022 | sacro | deep learning, 8 classi | F1 0,96; 0,02 s | https://www.mdpi.com/1424-8220/22/15/5786 |
| Hamidi Rad et al., single sacrum IMU (Front. Bioeng. Biotechnol.) | 2021 | sacro, 500 Hz, ±16 g, ±2000 °/s | fasi + regressione LASSO | R2 > 0,75; RMSE rel. < 10% | https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2021.793302/full |
| Topalovic et al., KU Leuven | 2014 | polso, 100 Hz | passa-basso 2 Hz + soglie | 100% nuoto/virate; farfalla 95% | https://www.scitepress.org/Papers/2014/51345/51345.pdf |
| Using tri-axial accelerometry in daily elite swim training | 2017 | accelerometri | confronto con video | stima frequenza ±~2 bracc/min | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5469343/ |
| Dadashi et al., front crawl phases (J. Sports Sci.) | 2013 | avambracci + sacro | fasi e coordinazione | validato vs video (cifre non lette) | non aperto |
| Bächlin & Tröster, Pervasive and Mobile Computing 8(1) | 2012 | citata: vari | non letto | n/d | https://dblp.org/pid/48/3200 |

Non trovati con fonte primaria: Stamm, Siirtola, Jensen, Le Sage, Davey, Ganzevles (solo tesi "Tracking swim training", https://research.vu.nl/en/publications/tracking-swim-training/), Garmin/Apple/Moov (solo validazioni esterne: Apple errore conteggio bracciate ~6-9%, Garmin fino a ~20% in due studi citati in sintesi di ricerca, non aperti).

## 4. Dataset e codice riutilizzabili

| Risorsa | Contenuto | Licenza | Link |
|---|---|---|---|
| Brunner et al. 2019 | 40 nuotatori, smartwatch al polso, ~17 h; acc+giro+mag+pressione+luce, ricampionato a 30 Hz; etichette: nullo, libero, rana, dorso, farfalla, virata | **non dichiarata** | https://github.com/brunnergino/swimming-recognition-lap-counting |
| SwimXYZ | video e moti sintetici (SMPL), niente IMU | da verificare | https://zenodo.org/record/8399376 |

- Il repository Brunner dichiara che codice e dati grezzi "saranno aggiunti"; al momento è disponibile solo il dato pre-elaborato [F, verificato 2026-10-25]. Utile solo per provare idee sull'etichettatura/modelli, non per la testa.
- Nessun dataset pubblico con IMU sulla testa trovato. Dati di Sensors 2022 (testa): su richiesta; Hamidi Rad 2021: su richiesta a ricercatori qualificati.
- Codice di riferimento: nessun repository GitHub con filtri/algoritmi su testa trovato. Il brevetto FORM è l'unica descrizione dettagliata. **Attenzione [D]**: un brevetto concesso può limitare l'uso commerciale; per un progetto personale/open source va valutato prima di copiarlo alla lettera.

## 5. Raccomandazioni per SwimTimer

(Deduzioni nostre fondate sulle fonti sopra, dove non indicato diversamente.)

- **Frequenza di campionamento**: FORM lavora a ~100 Hz con taglio a 10 Hz; gli studi su testa/polso usano 100-285 Hz; il dataset Brunner è a 30 Hz. Il BMI160 a ~50 Hz è sufficiente per roll, bracciate e virate (segnali sotto ~10 Hz), ma **insufficiente per sincronizzare partenza e urti con precisione**: registrare a 100 Hz o più quando possibile. [D]
- **Fondo scala**: gli studi usano ±16 g e ±2000 °/s. Il ±2 g del BMI160 satura sui tuffi e sugli urti con il muro; **LSM6DSV16X ±16 g è la scelta giusta**; giroscopio ≥ ±1000-2000 °/s per le capriole. [D]
- **Posizione**: occipitale sotto la cuffia (usata da studi su Sensors 2022, TritonWear e Procedia 2016). Fissarlo bene (due cuffie, fascetta) per ridurre artefatti da scivolamento. Registrare in ogni sessione la posizione esatta (foto). [D]
- **Cosa registrare nelle sessioni con video**: dati IMU grezzi (nessun filtro), timestamp, video laterale e subacqueo se possibile con un segnale di sincronizzazione (battito di mani/salto prima di partire, che dà un picco chiaro nell'IMU), lunghezza vasca, stile dichiarato, lato di respirazione abituale, calibrazione iniziale (fermo + cenno), eventuali sessioni a andature diverse. Solo dati anonimi nel repository (vincolo del progetto).
- **Etichette suggerite** (allineate a Delhaye 2022 e Brunner): riposo/fuori acqua, tuffo, spinta dal muro, subacquea (con/senza ondulazioni), nuoto per stile (4), virata (capriola/aperta), arrivo, respiro (evento con lato), ciclo di bracciata (evento), più "drill/altro". Etichettare eventi con istante (s) per respiro, bracciata e contatto con il muro, e intervalli per stile e fasi.
- **Strategia**: 1) regole fisiche con i parametri FORM come punto di partenza; 2) confronto con video; 3) solo se le regole non bastano (soprattutto stile e dorso) classificatore leggero su feature (SVM/random forest) addestrato sui nostri dati; CNN/LSTM solo se avremo molti dati. [D]
- **Rischi**: dorso (assetto poco variabile), distinzione capriola/aperta, rana e farfalla (respiro non a ogni ciclo), bracciata solo dedotta dalla testa, differenze tra nuotatori.
