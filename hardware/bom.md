# Distinta componenti

## Tag (prototipo, componenti già disponibili)
| Componente | Modello (dalle foto) | Funzione | Note |
|---|---|---|---|
| Microcontrollore | ESP32-S3 SuperMini (USB-C, LED RGB su GPIO 48, pulsanti BOOT/RST) | logica, BLE | pad BAT+/BAT− sul retro confermati dall utente |
| Sensore inerziale | GY-BMI160 (Bosch BMI160, 6 assi: accelerometro + giroscopio) | spinta, virata, calma | I2C, indirizzo 0x68; niente magnetometro; ora a ±16 g e 100 Hz (impostato a sensori accesi e riletto dal firmware 0.4.3) |
| Caricabatterie | integrato nell ESP32-S3 (pad BAT+/BAT− sul retro). Il TP4056 USB-C resta di scorta | | |
| Interruttore | facoltativo, solo on/off tra batteria e BAT+ | non serve per programmare | |
| Batteria | LiPo 3,7 V a una cella (da scegliere, indicativamente 300–500 mAh) | alimentazione | |
| Partitori | 4 resistenze da 100 kΩ (2 per la batteria su GPIO 1, 2 per il pin 5V su GPIO 2) | livello batteria e USB presente | |

## Display a bordo vasca
| Componente | Modello (dalle foto) | Funzione | Note |
|---|---|---|---|
| Scheda con display | LilyGO **T-RGB** V1.2 (ESP32-S3, display rotondo IPS 480×480 RGB ST7701S, touch, espansore I/O XL9535, microSD, connettore batteria) | ricezione BLE dal tag, mostra i tempi, storico su microSD | 2,8″, touch GT911 (verificato) |
| Batteria | LiPo 3,7 V 1000 mAh sul connettore della T-RGB (caricatore TP4065, circa 500 mA, LED rosso di carica) | alimentazione del display, autonomia stimata 4-5 ore | controllare la polarità |
| Accelerometro (da collegare) | BMI160 o altro I2C 3,3 V sul connettore I2C | quadrante sempre dritto | SDA 8, SCL 48, 0x68 |
| Custodia | da scegliere | protezione dagli schizzi | trasparente e a tenuta; il touch si usa solo a secco |
