# Domande aperte per l'utente

1. ~~Piscina da 25 o 50 m~~: 50 m (2026-11-08). Resta: anche acque libere?
2. Ti fermi al muro a ogni vasca o fai anche virate continue (capovolta)? Vuoi i tempi per vasca o per ripetuta (es. 4×100)?
3. ~~Accelerometro nel tag~~: deciso, già montato.
4. Dove indossarlo: cuffia/elastico degli occhialini (consigliato) o polso?
5. ~~Display~~: scelto, LilyGO T-RGB 2,8". Resta da decidere cosa mostrare oltre al tempo (riposo, vasche, batteria).
6. Ti serve uno storico sul telefono (app) o basta il display?
7. Budget indicativo e possibilità di stampare in 3D gli involucri?
9. La LiPo del display non accende la scheda senza USB: che tensione misuri col tester e la polarità del connettore è giusta?
10. Prova in vasca: quando e in che piscina (25 o 50 m)?
11. ~~Partitore sulla batteria del tag~~: montato e verificato col tester il 2026-10-25.
12. Custodia stagna per il display a bordo vasca: scatola trasparente o stampa 3D?
13. Quale accelerometro colleghi al connettore I2C del display per il quadrante sempre dritto (un altro BMI160)?
14. ~~Piste della scheda nRF52840~~: tracciate nella v0.2 (DRC 0 errori).
15. ~~GitHub Pages~~: attivato il 2026-10-26.
16. Per l'uso commerciale: vuoi far fare una verifica di libertà di operare (brevetti) prima di vendere?
17. ~~Prima sessione con video~~: deciso, 5 colpi sulla tag sotto la cuffia, video a 30 fps; manca solo la data.
18. ~~Batteria del tag al 2%~~: batteria sostituita, lettura verificata col tester.
19. A sola batteria, dopo l'accensione con l'interruttore: quanto misura il pin 3V3? E con il tag collegato via Bluetooth, staccando l'USB i dati continuano ad arrivare?
20. Scheda nRF52840 v0.2: applichiamo le 4 modifiche dalle lezioni apprese (alimentazione commutata del sensore, misuratore di carica, spegnimento vero, etichette +/−), sapendo che serve rifare parte delle piste?

### Scheda su misura nRF52840 (`hardware/nrf52840/`)
Risolte: modulo E73 (Raytac a stock 0), IMU LSM6DSV16X, flash 16 MB, interruttore TPS22916C sì e MAX17048 no, protezioni (TVS, MOSFET contro l'inversione, 100 kΩ su VIN), programmatore = HAT per Raspberry Pi 3/4 fatto in casa, 2 strati, repository unico pubblico.
14. Budget JLC: la v0.5 costa ~125 € (ENIG +5–10 €) contro il tetto di 100 €. Accetti la cifra o tagli raggi X / TVS / header (fino a ~100 €)? HASL o ENIG?
18. Avviso in acqua: provi vibratore e cicalino sul prototipo ESP32 (~5 €)? Per cosa deve avvisare (fine ripetuta, ritmo, tempo)?
26. Cella Ampul 401012 (3,31 €, senza connettore, polo +/− da verificare col tester): ne ordini 4?
29. 16 MB bastano? ~97 min a 240 Hz, ~24 min a 960 Hz sei assi: quale frequenza usiamo per le prime registrazioni?
30. Traslatore di livello sul programmatore (SWD 3,3 V del Pi contro 1,8 V del tag al primo avvio): lo aggiungiamo (1–2 €) o ti basta il metodo con le 1 kΩ e REGOUT0 scritto subito?
31. Ordine NextPCB v0.6 (216,39 $ per 20 pz): aspetti Viviane (sponsorizzazione) fino a mercoledì 11 novembre o ordini subito?
32. XIAO in arrivo: scriviamo subito lo sketch Arduino di streaming BLE per la tab XIAO? Ordini le celle LP-401230 da 100 mAh?
33. Display a bordo vasca: confermi Raspberry Pi 4 + dongle nRF52840 + monitor portatile + power bank? Faccio fare a `elettronica` la distinta con modelli e prezzi (~180–220 €)?
34. Quale test di riferimento (CSS 400+200 m o altro) per calcolare l'Effort di ogni nuotatore? Ora la scala 1–10 è provvisoria.
35. Vasca da 50 m: il BLE non arriva al muro opposto al display. Secondo ricevitore a batteria sul muro lontano (~15–20 €) o consegna ritardata fino al ritorno?
36. XIAO: compri una scheda di scorta (la attuale ha il regolatore 3,3 V guasto e va col diodo) e un multimetro (10–15 €, serve anche per le v0.6)?
37. Taratura batteria: leggi col tester la tensione della cella e la inserisci in «Taratura» (il tag legge ~1% in meno).
38. Soglie della sospensione automatica (rotazione 3 dps, inclinazione 3°, 60 s): da tarare con la scheda sotto la cuffia a riposo; poi provare i 4 tap e la sospensione a batteria bassa.
39. Per il tag definitivo: firmware Zephyr con MCUboot e aggiornamento SMP (compatibile con Web Bluetooth) o proseguire con Arduino?
40. Prova a secco della 0.5.0 (registrare a casa, scaricare via USB, `node tools/parita_swr.mjs <file>`): quando la fai? Poi la prima registrazione in piscina (5–10 min).
41. Telefono per il video: confermi H.264 a 30 fps (evitare HEVC e frequenza variabile)?
42. Compressione: quanti minuti entrano davvero nei dati veri (prevista ~25 min con dati regolari)? Dipende dai tratti con movimenti bruschi.
43. LED sotto la cuffia: se non si vede, serve un altro segnale (cicalino fuori dal tag) oppure basta controllare da PC?
44. Caricare la 0.5.1 (lampo blu a ogni tocco): serve la tag in modalità normale (USB collegata).
45. Il video di prova è a 25 fps: adattiamo l'Annotazione al frame rate reale del video o giri a 30 fps (telefono)? Per ora i tasti ±1f e il numero del fotogramma sono sbagliati con 25 fps.
46. iPhone: giri in **H.264 a 30 fps** («Più compatibile» in Impostazioni › Fotocamera › Formati), che la pagina già gestisce, oppure a **60 fps** (tocco e spinta più precisi, ±17 ms invece di ±33 ms) adattando prima la pagina al frame rate (vedi 45)?
47. Programma dei 4 giorni: quale combinazione di 100 e 50 (es. 4×100 + 8×50 = 12 partenze/arrivi e 4 virate al giorno; più 100 = più virate, più 50 = più partenze/arrivi)?
48. Dati dei nuotatori sull'app online: quando si estende ad altri, serve un testo di consenso da mostrare al primo accesso? Vuoi un elenco delle persone ammesse con il motivo dell'approvazione?
49. ~~Video su Drive~~: cartella condivisa con gli utenti approvati (2026-11-08). Automatizzare l'aggiunta alla cartella quando si approva (scope Drive, avviso «app non verificata» solo per l'admin)?
50. Spam sul modulo contatti: se arriva, attiviamo reCAPTCHA (App Check, gratuito, da attivare in console)?
51. Tradurre in inglese anche la pagina Strumenti?
