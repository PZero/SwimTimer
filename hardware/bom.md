# Distinta componenti

## Tag (prototipo, componenti già disponibili)
| Componente | Modello (dalle foto) | Funzione | Note |
|---|---|---|---|
| Microcontrollore | ESP32-S3 SuperMini (USB-C, LED RGB su GPIO 48, pulsanti BOOT/RST) | logica, BLE | pad BAT+/BAT− sul retro confermati dall utente |
| Sensore inerziale | GY-BMI160 (Bosch BMI160, 6 assi: accelerometro + giroscopio) | spinta, virata, calma | I2C, indirizzo 0x68; niente magnetometro |
| Caricabatterie | integrato nell ESP32-S3 (pad BAT+/BAT− sul retro). Il TP4056 USB-C resta di scorta | | |
| Interruttore | facoltativo, solo on/off tra batteria e BAT+ | non serve per programmare | |
| Batteria | LiPo 3,7 V a una cella (da scegliere, indicativamente 300–500 mAh) | alimentazione | |
| Partitore (facoltativo) | 2 resistenze da 100 kΩ | lettura livello batteria | |

## Display a bordo vasca
| Componente | Modello (dalle foto) | Funzione | Note |
|---|---|---|---|
| Scheda con display | LilyGO **T-RGB** V1.2 (ESP32-S3, display rotondo IPS 480×480 RGB ST7701S, touch, espansore I/O XL9535, microSD, connettore batteria) | ricezione BLE dal tag, mostra i tempi, storico su microSD | dimensione (2,1″ o 2,8″) e chip del touch da verificare collegandolo |
| Custodia | da scegliere | protezione dagli schizzi | trasparente e a tenuta; il touch si usa solo a secco |
