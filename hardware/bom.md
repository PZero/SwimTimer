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

## Display
Da definire.
