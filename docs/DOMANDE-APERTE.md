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
14. Budget JLC: 50 € non bastano per 2 tag (minimo ~80 € senza sensore di pressione, ~100 € completo). Quale strada: alzare il budget o rinviare il sensore di pressione?
15. ~~Modulo~~: MDBT50Q-1MV2 (ISP1807 scartato).
16. ~~IMU~~: LSM6DSV16X a ±4 g.
17. ~~Sensore di pressione~~: MS5837-02BA.
18. Avviso in acqua: ok alla prova sul prototipo ESP32 con 2 vibratori e 1 cicalino (~5 € di componenti)? Per cosa deve avvisare (fine ripetuta, ritmo, tempo)?
19. ~~Cella~~: 15–20 mAh; memoria 32 MB.
20. ~~Forma del tag~~: disposizione B compatta, ~19 × 21 × 7,2 mm.
21. ~~Stampante 3D~~: Bambu Lab A1 mini.
22. ~~Programmatore~~: da costruire (Raspberry Pi Pico con debugprobe + culla stampata con molle pogo), come la custodia di ricarica.
23. PCB v0.1 pronto (`hardware/nrf52840/kicad/jlc/`): vuoi rivederlo in KiCad prima dell'ordine JLC? Accetti l'assenza di protezione sui contatti di ricarica (TVS e diodo tolti per spazio)?
