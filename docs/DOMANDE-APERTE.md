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
11. Quando monti il partitore sulla batteria del tag (due resistenze da 100 kΩ)?
12. Custodia stagna per il display a bordo vasca: scatola trasparente o stampa 3D?
13. Quale accelerometro colleghi al connettore I2C del display per il quadrante sempre dritto (un altro BMI160)?

### Scheda su misura nRF52840 (`hardware/nrf52840/`)
Risolte: modulo MDBT50Q-1MV2, IMU LSM6DSV16X ±4 g, sensore di pressione, cella 15–20 mAh con 32 MB, forma B compatta, stampante Bambu Lab A1 mini, programmatore da costruire, protezione dei contatti e reset all'inserimento (v0.2).
14. Budget JLC: 50 € non bastano; il tag di collaudo v0.3 costa ~120–130 $ per 2 tag (IVA e spedizione escluse) più cella e cavo Tag-Connect. Confermi?
18. Avviso in acqua: provi vibratore e cicalino sul prototipo ESP32 (~5 €)? Per cosa deve avvisare (fine ripetuta, ritmo, tempo)?
23. Carichi tu i file di `kicad/jlc/v0.3_swimtag_collaudo/` nell'anteprima JLC (rotazioni, stock, prezzo)?
25. Programmazione del tag v0.3: cavo Tag-Connect TC2030-NL (~40 $) con J-Link EDU Mini (si adatta a 1,8 V) o Raspberry Pi Pico + traslatore di livello?
26. Cella Ampul 401012 con spina JST SH 1,0 mm: la vende così o serve un'altra cella equivalente?
