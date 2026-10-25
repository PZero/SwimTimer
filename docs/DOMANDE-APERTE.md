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
14. Confermi il passo intermedio con la **Seeed XIAO nRF52840 Sense** (~15 $) prima di disegnare la scheda?
15. Modulo: **Raytac MDBT50Q-1MV2** (10,5 × 15,5 mm, certificato, ~10 $) o Ebyte E73 (13 × 18 mm, ~6 $)? L'ISP1807 (8 × 8 mm) lo terrei per la seconda versione.
16. IMU: va bene il **LSM6DSV16X** impostato a **±4 g**? Ha un terzo del rumore del BMI160; il fondo scala si cambia via firmware (anche ±2 g), ma il BMI160 a ±2 g oggi satura in spinta e virata.
17. ~~Sensore di pressione~~: deciso, MS5837-02BA (porta esposta con O-ring).
18. ~~Vibratore~~: deciso. Resta: per cosa vibrare (fine vasca, ritmo, tempo di ripetuta)? E accetti una cella da 30–40 mAh se lo spessore lo permette, per reggere meglio i picchi?
19. Ingombro massimo accettabile sotto la cuffia? Stima attuale ~18 × 26 × 9 mm, ~6 g. Con 1–2 mm in più di spessore si può salire a una cella da 40 mAh.
20. Quanti prototipi e che budget (proposta: 5 pezzi, ~150–250 $ tutto compreso)?
21. Custodia di ricarica: stampa 3D tua, solo USB-C o anche con batteria interna?
22. Hai un programmatore SWD (J-Link, ST-Link, Raspberry Pi Pico) per il primo caricamento?
