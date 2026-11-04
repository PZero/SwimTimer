# Schema del tag (prototipo)

Componenti in `hardware/bom.md`. Nomi dei pin come serigrafati sulle schede.

**Stato:** prototipo saldato e verificato il 2026-10-24 (partitori su GPIO 1 e 2 aggiunti il 2026-10-25, da verificare con il firmware 0.4.1) con `firmware/test-collegamenti` e `tools/assi.html` (accelerometro e giroscopio rispondono su tutti gli assi).

## Schema a blocchi
```
LiPo 3,7 V ──(interruttore on/off facoltativo)──► BAT+/BAT−  ESP32-S3 SuperMini (caricatore integrato, carica dalla USB-C)
                                                                │ 3V3, GND, GPIO 8, 9, 4
                                                                ▼
                                                           GY-BMI160 (I2C)
```

## Collegamenti
| Da | A | Note |
|---|---|---|
| LiPo + (rosso) | ESP32 **BAT+** (retro) | interruttore on/off in serie (montato il 2026-10-25: con interruttore aperto e USB collegata il partitore legge ~4,2 V del caricatore, non la batteria) |
| LiPo − (nero) | ESP32 **BAT−** (retro) | |
| ESP32 **3V3** | BMI160 **3V3** | |
| ESP32 **GND** | BMI160 **GND** | |
| ESP32 **GPIO 8** | BMI160 **SDA** | pin I2C predefiniti dell'ESP32-S3 in Arduino |
| ESP32 **GPIO 9** | BMI160 **SCL** | |
| ESP32 **3V3** | BMI160 **CS** | CS alto = modalità I2C |
| ESP32 **GND** | BMI160 **SAO** (SDO) | indirizzo I2C 0x68 |
| ESP32 **GPIO 4** | BMI160 **INT1** | risveglio al movimento (risparmio batteria) |
| BAT+ → 100 kΩ → **GPIO 1** → 100 kΩ → GND | partitore | livello batteria (la pagina mostra V e %, in carica con correzione di 0,05 V, misurata col tester) |
| pin **5V** → 100 kΩ → **GPIO 2** → 100 kΩ → GND | partitore | alimentazione USB presente (>4 V): serve a sapere se è in carica; con la 5V a 0 V il partitore legge 0 |
| ESP32 **GPIO 48** | LED RGB WS2812 integrato | riscontro: colori in `tools/index.html` (pulsante LED) |

Pin del BMI160 non usati: VIN, INT2, OCS, ASCX, ASDX.

## Note sull'alimentazione
- Usare una LiPo **con protezione propria**: il caricatore integrato di solito non protegge dalla scarica eccessiva.
- Con la batteria quasi scarica (~3,4 V) il regolatore dà meno di 3,3 V: il firmware deve spegnersi sotto ~3,3 V.
- Spegnimento nella versione sigillata: sonno profondo con risveglio dal BMI160 (INT1) o interruttore magnetico (reed).

## Alternativa scartata: TP4056 esterno
Usata solo se la scheda non avesse il caricatore: LiPo su B+/B− del TP4056, OUT+ → interruttore → pin **5V** dell'ESP32 (mai 3V3), OUT− → GND. Interruttore spento quando si usa la USB dell'ESP32. Corrente di carica di serie ~1 A: per LiPo sotto i 1000 mAh sostituire la resistenza di programmazione (3,3 kΩ ≈ 350 mA, 4,7 kΩ ≈ 250 mA).

**Nota del 2026-10-25:** il sensore è andato in latch-up dopo uno spegnimento brusco (3V3 dell'ESP32 a 0 V, si sbloccava solo staccando GND). Sul prototipo si spegne tutto con l'interruttore; la soluzione vera (alimentazione del sensore commutata) è per la scheda nRF52840, vedi `docs/LEZIONI-APPRESE.md`.
