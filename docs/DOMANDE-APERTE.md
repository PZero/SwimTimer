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
Risolte: modulo MDBT50Q-1MV2, IMU LSM6DSV16X ±4 g, sensore di pressione, cella 15–20 mAh con 32 MB, forma B compatta, stampante Bambu Lab A1 mini, programmatore da costruire, protezione dei contatti e reset all'inserimento (v0.2).
14. Budget JLC: 50 € non bastano; il tag di collaudo v0.3 costa ~120–130 $ per 2 tag (IVA e spedizione escluse) più cella e cavo Tag-Connect. Confermi?
18. Avviso in acqua: provi vibratore e cicalino sul prototipo ESP32 (~5 €)? Per cosa deve avvisare (fine ripetuta, ritmo, tempo)?
23. Carichi tu i file di `kicad/jlc/v0.3_swimtag_collaudo/` nell'anteprima JLC (rotazioni, stock, prezzo)?
25. Programmazione del tag v0.3: cavo Tag-Connect TC2030-NL (~40 $) con J-Link EDU Mini (si adatta a 1,8 V) o Raspberry Pi Pico + traslatore di livello?
26. Cella Ampul 401012 con spina JST SH 1,0 mm: la vende così o serve un'altra cella equivalente?
27. v0.4 economica: ~91-95 € stimati per 2 schede (PCB e spedizione non verificati nel carrello JLC). Taglio possibile: LED 0603 *basic* (−3,07 $). Confermi LED 0402 e flash SOIC-8 16 MB (22,86 × 26 mm)? Caricare tu `kicad/jlc/v0.4_swimtag_economica/` nell'anteprima JLC (header C55213900 nell'Economic, rotazioni, prezzi reali).
28. v0.4: 16 MB bastano per la registrazione? ~24 min a 960 Hz sei assi, ~97 min a 240 Hz; quale frequenza e quanto dura una registrazione?
