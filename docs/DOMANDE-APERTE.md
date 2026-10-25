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
14. Con 50 € facciamo la tappa XIAO nRF52840 Sense (anche resinata, da usare in vasca)? La scheda su misura con 2 tag costa ~130–150 € tutto compreso.
15. ~~Modulo~~: MDBT50Q-1MV2. Se l'ingombro non basta: ISP1807 (8 × 8 mm, tag ~12 × 14 × 7 mm, ~+3 $ a pezzo)?
16. ~~IMU~~: LSM6DSV16X a ±4 g.
17. ~~Sensore di pressione~~: MS5837-02BA.
18. Avviso in acqua: proviamo sulla XIAO vibratore e cicalino (tipo FINIS Tempo Trainer) e scegliamo quello che si sente meglio? Per cosa deve avvisare (fine ripetuta, ritmo, tempo)?
19. Cella da 15–20 mAh invece di 40 (bastano per 3 h)? Memoria da 32 MB o 16 MB (più piccola, un allenamento e mezzo)?
20. Misure massime accettabili per il tag (stima con MDBT50Q: ~14 × 19 × 8 mm)?
21. Hai una stampante 3D (custodia, attrezzo di programmazione, stampo per la resina)? Resina o filamento?
22. Hai un programmatore SWD? Altrimenti un Raspberry Pi Pico (~5 €) col firmware debugprobe.
