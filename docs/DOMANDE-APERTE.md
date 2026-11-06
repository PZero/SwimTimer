# Domande aperte per l'utente

1. Piscina da 25 o 50 m? Solo piscina o anche acque libere?
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
17. Quando e dove registriamo la prima sessione con video (battito di mani per sincronizzare)?
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
32. XIAO nRF52840 Sense: ordini il pacco da 3 su Amazon (variante Sense da confermare) e le celle LP-401230 da 100 mAh?
33. Versione inglese del video di presentazione (testi, miniatura, descrizione YouTube): la facciamo?
