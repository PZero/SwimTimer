# Schema del tag (prototipo)

Componenti in `hardware/bom.md`. Nomi dei pin come serigrafati sulle schede.

**Stato:** prototipo saldato e verificato il 2026-10-24 con `firmware/test-collegamenti` e `tools/assi.html` (accelerometro e giroscopio rispondono su tutti gli assi).

## Schema a blocchi
```
LiPo 3,7 V ──B+/B-── TP4056 ──OUT+── interruttore ──► 5V   ESP32-S3 SuperMini
                                OUT- ──────────────► GND        │ 3V3, GND, GPIO 8, 9, 4
                                                                ▼
                                                           GY-BMI160 (I2C)
```

## Collegamenti
| Da | A | Note |
|---|---|---|
| LiPo + (rosso) | TP4056 **B+** | |
| LiPo − (nero) | TP4056 **B−** | |
| TP4056 **OUT+** | interruttore (piedino centrale) | |
| interruttore (piedino laterale) | ESP32 **5V** | mai sul pin 3V3: la batteria carica arriva a 4,2 V |
| TP4056 **OUT−** | ESP32 **GND** | |
| ESP32 **3V3** | BMI160 **3V3** | |
| ESP32 **GND** | BMI160 **GND** | |
| ESP32 **GPIO 8** | BMI160 **SDA** | pin I2C predefiniti dell'ESP32-S3 in Arduino |
| ESP32 **GPIO 9** | BMI160 **SCL** | |
| ESP32 **3V3** | BMI160 **CS** | CS alto = modalità I2C |
| ESP32 **GND** | BMI160 **SAO** (SDO) | indirizzo I2C 0x68 |
| ESP32 **GPIO 4** | BMI160 **INT1** | risveglio al movimento (risparmio batteria) |
| OUT+ dopo l'interruttore → 100 kΩ → **GPIO 1** → 100 kΩ → GND | partitore | facoltativo: livello batteria |

Pin del BMI160 non usati: VIN, INT2, OCS, ASCX, ASDX.

## Variante: pad BAT+ / BAT− sul retro dell'ESP32 (da confermare)
Se la scheda ha un caricabatterie integrato (piccolo chip a 5 piedini vicino ai pad, es. siglato 4054):
- LiPo direttamente su **BAT+ / BAT−**, niente TP4056 e niente interruttore per la programmazione: la scheda gestisce da sola USB e batteria.
- Usare una LiPo **con protezione propria** (piccola scheda sotto la pellicola): il caricatore integrato di solito non protegge dalla scarica eccessiva.
- Un modo di spegnere il tag serve comunque: sonno profondo con risveglio dal BMI160 (INT1) e, per l'involucro sigillato, eventualmente un interruttore magnetico (reed).

## Regole d'uso
- **Programmazione dalla USB dell'ESP32**: interruttore **spento**, altrimenti i 5 V della USB tornano verso il TP4056 e la batteria.
- **Ricarica**: cavo nella USB del TP4056, preferibilmente con interruttore spento. LED rosso = in carica, blu/verde = carica.
- **Corrente di carica**: di serie ~1 A (resistenza di programmazione da 1,2 kΩ). Per una LiPo sotto i 1000 mAh va sostituita: ~3,3 kΩ ≈ 350 mA, ~4,7 kΩ ≈ 250 mA. Regola: corrente ≤ capacità della batteria (1C), meglio la metà.
- Con la batteria a fine carica (~3,4 V) il regolatore dell'ESP32 dà meno di 3,3 V: l'ESP32 funziona ancora, ma il firmware deve spegnersi sotto ~3,3 V di batteria.
