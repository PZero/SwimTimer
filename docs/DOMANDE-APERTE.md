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
40. ~~Prova a secco della 0.5.0~~: fatta, e la prima registrazione in vasca è stata il test 1 del 2026-11-09.
41. ~~Telefono per il video a 30 fps~~: superato (Insta360, 50 fps).
42. ~~Compressione~~: misurata sui dati veri, 17,6 min a 214 Hz, 31,5 a 104, 55 a 52, 102 a 26 (sotto i 52 Hz la compressione delta non basta).
43. ~~LED sotto la cuffia~~: LED spenti a batteria (2026-11-10); lo stato si vede sul display e sulla pagina.
44. Caricare la 0.5.1 (lampo blu a ogni tocco): serve la tag in modalità normale (USB collegata).
45. ~~Frame rate dell'Annotazione~~: risolto il 2026-11-10, la pagina misura gli fps veri (50 fps nel test 1).
46. ~~iPhone 30 o 60 fps~~: superato, l'editor segue gli fps reali; il test 1 è stato ripreso con Insta360 a 50 fps.
47. Programma dei 4 giorni: quale combinazione di 100 e 50 (es. 4×100 + 8×50 = 12 partenze/arrivi e 4 virate al giorno; più 100 = più virate, più 50 = più partenze/arrivi)?
48. Dati dei nuotatori sull'app online: quando si estende ad altri, serve un testo di consenso da mostrare al primo accesso? Vuoi un elenco delle persone ammesse con il motivo dell'approvazione?
49. ~~Video su Drive~~: cartella condivisa con gli utenti approvati (2026-11-08). Automatizzare l'aggiunta alla cartella quando si approva (scope Drive, avviso «app non verificata» solo per l'admin)?
50. Spam sul modulo contatti: se arriva, attiviamo reCAPTCHA (App Check, gratuito, da attivare in console)?
51. Tradurre in inglese anche la pagina Strumenti?
52. ~~Frequenza di campionamento~~: si resta a 208 Hz (2026-11-10); la memoria si «estende» con lo scarico al muro.
53. Prossima seduta: ripetute da 100 m con la camera attaccata al muro di partenza (partenza e arrivo davanti alla camera)? Hai una seconda camera in prestito per i 50 m (serve sync doppio e due video nell'editor)?
54. Pausa di ~50 s tra 504 e 530 s del video del 9/11: ti sei fermato a lungo, oppure l'Insta360 ha tagliato un pezzo?
55. Video v3: correggere la frase «deriva dello 0,24%» (probabilmente k ≈ 0,9993) e rigenerare IT/EN, oppure lasciare così?
56. Pubblicare il pacchetto OTA 0.5.4 è fatto: lo provi sul tag (aggiornamento dalla pagina Strumenti) e controlli nel log `crc ok` e `boot xiao-0.5.4`?
57. Video da Drive nell'editor: abiliti la Google Drive API nel progetto `swimtimer-pzero` (gratuita, ma il file va condiviso «chiunque abbia il link»), o lasciamo il file locale?
58. Segnale del display: facciamo le misure a 10 cm / 1 m / 3 m (e tag ruotata) per tarare la scala in %? Se il margine a bordo vasca è scarso, valutiamo un'antenna esterna o un ricevitore diverso.
59. ~~Verifica della SD dal PC~~: fatta il 2026-11-10 (nessun buco, nessun errore). Cancelli le cartelle della DEMO nella SD (`1000a3f2`, `20007c10`, `3000e95b`)?
60. Display T-RGB come display «di sviluppo» per 1–3 nuotatori e Pi 4 + dongle per 10: confermi questa divisione?
61. **Stati della tag con l'USB:** sul caricatore deve andare in idle da sola (come la svegli: tocchi? scollegando?); al PC resta sveglia per lavorarci. E dalla pagina del PC, con la tag su USB, «spegni» deve davvero spegnerla (oggi si riavvia)? Da progettare insieme prima del codice.
62. Ordini un **T-RGB 2,8″** nuovo (circa 45 €)? E un'antenna 2,4 GHz **U.FL/IPEX-1** dopo aver controllato lo schema?
63. Il **Raspberry Pi 3 con monitor HDMI**: lo teniamo come idea per una stazione con corrente (più nuotatori, tabellone), da valutare con l'architettura definitiva?
64. Diario nella memoria esterna della tag (niente blocchi con il BLE collegato): accetti di riservare uno dei 512 blocchi (cambia la mappa del display)?
