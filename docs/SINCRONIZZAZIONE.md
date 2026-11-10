# Sincronizzazione tag → display (BOZZA, da approvare)

**Stato:** proposta del 2026-11-10, nessun firmware scritto. Display di riferimento: LilyGO T-RGB (ESP32-S3R8, 8 MB PSRAM, microSD). Tag: XIAO nRF52840 Sense, flash QSPI 2 MB.

## Obiettivi
1. **Vedere** da bordo vasca, senza collegarsi, se la tag è accesa, cosa sta facendo, batteria, memoria.
2. **Scaricare** i dati automaticamente a ogni sosta al muro, senza gesti.
3. **Nessun dato perso**: la tag libera un blocco solo dopo una conferma che dimostra che il blocco è sulla SD, integro.
4. **Memoria «estesa»**: la flash diventa un anello; si riscrive solo ciò che è confermato.
5. **Fine sessione verificabile**: il display dice per ogni tag se la sessione è completa e leggibile, o cosa manca.

## Invariante (la regola che non si viola mai)
> La tag non sovrascrive **mai** un blocco che non ha ricevuto una conferma valida.
> Il display conferma un blocco **solo** dopo averlo scritto sulla SD, riletto dalla SD e verificato.

Se la memoria si riempie di blocchi non confermati, la tag **ferma la registrazione** (come oggi: `SWR_STOP_PIENA`) e lo segnala. Meglio perdere il futuro che il passato.

## 1. Unità di scambio: il blocco da 4 KB
- La flash si cancella a **settori da 4 KB** = 16 pagine `.swr` da 256 B. Il blocco di scambio coincide con il settore: 512 blocchi in 2 MB.
- Ogni blocco ha un **numero di sequenza globale `seq` a 32 bit**, crescente, mai riutilizzato (sopravvive a cancellazioni e riavvii: all'avvio la tag lo ricava dal massimo trovato in flash).
- Le pagine restano decodificabili da sole (CRC16 per pagina, come oggi). In più il blocco chiuso ha un **CRC32** dei suoi 4096 byte.
- Un blocco si «chiude» quando l'ultima pagina è scritta. Il blocco aperto (al massimo ~3 s di dati a 208 Hz) **si può inviare in anteprima ma non si conferma**; si conferma quando si chiude (o alla chiusura del segmento, con riempimento).

### Stato di un blocco sulla tag
| stato | come si riconosce in flash | si può riscrivere? |
|---|---|---|
| libero | settore tutto 0xFF | sì |
| aperto | prime pagine scritte, ultima vuota | no |
| chiuso, non confermato | 16 pagine valide, byte `conferma` = 0xFF | **no** |
| confermato | byte `conferma` = 0x00 | sì, ma solo quando serve spazio |

Il byte `conferma` sta nell'intestazione della prima pagina del blocco ed è **escluso dal CRC**: la flash NOR può portare bit da 1 a 0 senza cancellare, quindi la marcatura è una sola scrittura di un byte, atomica, e lo stato vive insieme ai dati (niente tabelle separate da tenere coerenti). Un valore intermedio (corrente mancata durante la scrittura) vale come «confermato»: la conferma era già arrivata e verificata.

**Cancellazione pigra:** i blocchi confermati non si cancellano subito; restano come seconda copia finché lo spazio serve (si cancella il più vecchio confermato, appena prima di scriverci). Così, se la SD si rompe dopo, i dati recenti sono ancora sulla tag.

## 2. Annuncio (sempre, senza connessione)
La tag annuncia anche in registrazione (oggi in vasca il BLE è spento). Costo stimato: ~10–30 µA medi con intervallo 1 s, trascurabile rispetto a IMU + flash. Dati produttore (≤ 24 B):

| campo | byte | note |
|---|---|---|
| versione protocollo | 1 | |
| id tag | 4 | dall'id univoco del chip (FICR) |
| stato | 1 | vado in sonno / pronta / registra / memoria piena / errore / sincronizza |
| batteria | 1 | mV/20 |
| % memoria non confermata | 1 | |
| blocchi in attesa | 2 | chiusi non confermati |
| ultimo `seq` scritto | 4 | |
| tempo di registrazione | 2 | s nel segmento corrente |
| errori | 1 | bit: IMU, flash, batteria bassa, … |

Ritmo: **fisso, ~200 ms**, sempre (costo stimato 30–50 µA, trascurabile con la cella da 1000 mAh). La tag **non interpreta il movimento** (decisione 2026-11-10): niente rilevamento «fermo al muro»; il display si collega appena la sente, cioè quando la testa è fuori dall'acqua a portata.

Sul display: elenco delle tag viste, con «visto N s fa», stato, batteria, memoria. Questo risolve da solo il problema «non so se è accesa».

## 3. Scarico (con connessione)
Il display si collega da solo quando vede una tag con blocchi in attesa. Parametri: PHY 2M, MTU 247, DLE, intervallo 7,5–15 ms. **È la tag a spingere i dati**: il display non chiede blocchi, riceve, verifica e conferma.

1. **PRONTO** (scrittura del display, cifrata) → «SD ok, posso ricevere». Il display lo manda solo se la SD è presente e ha spazio; senza PRONTO la tag non trasmette (il display può restare collegato solo per lo stato).
2. La tag invia **in automatico il blocco non confermato più vecchio**: prima un'intestazione `(seq, CRC32, pagine)`, poi le 16 pagine in notifiche (ognuna con `seq` e indice di pagina).
3. Il display, in PSRAM: CRC16 di ogni pagina, CRC32 del blocco contro l'intestazione, continuità di `seq` rispetto all'ultimo salvato.
4. **Scrittura su SD**: accoda il blocco nel file della tag, `fsync`, **rilegge dalla SD** e ricalcola il CRC32. Poi aggiorna l'indice (vedi §4).
5. **CONFERMA (seq, CRC32)** → la tag controlla che il CRC32 coincida con quello del proprio blocco, marca il byte `conferma`, lo rilegge, risponde **CONFERMATO seq** e **passa da sola al blocco successivo**. Il display segna il blocco «confermato» nell'indice.
6. Quando non restano blocchi chiusi da confermare, la tag manda **FINE** (con l'ultimo `seq` e l'eventuale blocco aperto in anteprima) e il display chiude il collegamento.

**Errori: nessun rinvio a tempo.** Dentro un collegamento il BLE è già affidabile (ogni pacchetto è confermato e ritrasmesso dal livello radio): o arriva in ordine, o il collegamento cade. Quindi:
- la tag, dopo aver spedito, **aspetta la conferma senza limite di tempo** finché il collegamento è vivo; non rimanda mai di sua iniziativa;
- rinvia un blocco solo se il display lo chiede: **RIPETI seq** (blocco incompleto o CRC sbagliato; dopo 3 tentativi falliti il display segnala l'errore e chiude);
- se il display non può confermare (SD piena o in errore) manda **STOP** e chiude: niente attese a vuoto;
- se il collegamento cade (testa sott'acqua, nuotatore ripartito, display spento) tutto ciò che non è confermato riparte, al collegamento successivo, dal blocco non confermato più vecchio. Un display bloccato viene scoperto dal *supervision timeout* del collegamento (~2 s), non da un timer del protocollo.

**Finestra di 2 blocchi:** mentre il display scrive e rilegge il blocco *n* sulla SD (decine di ms), la tag sta già trasmettendo *n+1*. Così la radio non resta mai ferma ad aspettare la SD. Le conferme restano una per blocco e in ordine; la tag non va mai oltre 2 blocchi trasmessi e non confermati.

Interruzione in qualsiasi punto (il nuotatore riparte, la testa va sott'acqua): nessun danno. Ciò che non è confermato viene reinviato alla sosta successiva; il display riconosce i doppioni da `(id tag, seq, CRC32)` e non li scrive due volte. Stesso `seq` con CRC diverso = anomalia: si tengono entrambi e si segnala.

### Sicurezza della conferma
La conferma è l'unico messaggio che autorizza la riscrittura, quindi deve arrivare **solo dal proprio display**: tag e display si associano una volta (bonding LE Secure Connections) e la caratteristica CONFERMA richiede il collegamento cifrato. Un telefono qualsiasi può leggere lo stato, non può far cancellare niente.

### Più tag insieme (fase attuale: 3)
- Il display tiene fino a **3 collegamenti contemporanei** (lo stack BLE dell'ESP32 ne regge di più); la banda radio si divide tra le tag, ma resta molto più lenta della SD.
- Uso dei core dell'ESP32-S3:
  - **core 0**: stack BLE e ricezione; ogni tag ha il suo buffer in PSRAM (2 blocchi × 4 KB, 24 KB in tutto);
  - **un solo task «scrittore SD»** con una coda: riceve i blocchi completi e verificati da qualsiasi tag, li scrive, rilegge e verifica uno alla volta, poi rimette in coda la conferma per la tag giusta. Un solo scrittore = nessun accesso concorrente al file system;
  - **core 1**: interfaccia e schermo, che leggono solo una copia dello stato, senza mai aspettare SD o BLE. Grafica come in `firmware/display-prova`: **niente LVGL**, Adafruit GFX 1.11.11 con due `GFXcanvas16` 480×480 in PSRAM (sfondo + composto) copiati con `panel.pushColors`, driver LilyGO copiato in `src/trgb`, PlatformIO espressif32 6.9.0 (core Arduino 2.0.17).
- Le conferme di tag diverse sono indipendenti: una tag lenta o in errore non blocca le altre.

## 4. Sulla SD del display
```
/swim/<id tag>/<data>_<n>.swr    blocchi così come sono in flash (si leggono con swr.py / swr.js)
/swim/<id tag>/<data>_<n>.idx    una riga per blocco: seq, offset, CRC32, stato (scritto|confermato)
```
- Indice in sola aggiunta: la riga si scrive **dopo** l'`fsync` dei dati. Al riavvio il display ricontrolla la coda del file contro l'indice.
- Il display **non conferma** se: SD assente, piena (< 50 MB liberi), errore di scrittura o di rilettura. In quel caso mostra l'errore e lascia i dati sulla tag.
- Ora: il T-RGB non ha un orologio a batteria; il display salva a ogni collegamento la coppia `millis tag ↔ millis display` (e l'ora se impostata), così i tempi si ricostruiscono dopo.

## 5. Fine sessione
A ogni collegamento e a fine sessione il display mostra per tag: blocchi ricevuti, buchi di `seq` (devono essere zero), CRC tutti ok, blocchi ancora sulla tag. **«Completa»** solo se nessun buco e nessun blocco in attesa. Lo scarico USB attuale resta come riserva e legge anche i blocchi già confermati.

## 6. Schermata di stato delle tag (da progettare dopo)
Requisiti dell'utente, per ogni tag:
- **accesa / spenta / registra**;
- **mappa dei blocchi in memoria**: confermati, in trasmissione, da validare (più liberi e blocco aperto).

Bozza grafica: `docs/img/mockup-stato-tag.png` (quadrante in **3 spicchi da 120°**, uno per tag, tag 1 in alto e poi in senso orario; sul bordo dello spicchio i 512 blocchi in 4 file da 128; dentro nome, stato, batteria, blocchi da validare, ultimo contatto; al centro lo stato della SD).

Cosa serve al protocollo per mostrarlo:
- «Spenta» non si distingue da «fuori portata» o «sott'acqua»: la tag, prima di andare in sonno, annuncia per ~2 s lo stato **«vado in sonno»** (con il motivo); se il display l'ha sentito mostra «spenta», altrimenti «non vista da N s».
- La mappa dei 512 blocchi richiede 2 bit per blocco = **128 B**: troppi per l'annuncio (che porta solo i conteggi), quindi la tag la manda **all'inizio di ogni collegamento**; durante lo scarico il display la aggiorna da sé (in trasmissione → confermato) senza altri messaggi.

## 7. Formato dei messaggi (versione protocollo 1)
Interi little-endian. CRC32 = IEEE 802.3 (poly 0xEDB88320, init/xorout 0xFFFFFFFF), lo stesso dell'OTA.

### Annuncio (dati produttore, company ID 0xFFFF di prova)
| off | campo | tipo |
|---|---|---|
| 0 | company 0xFFFF | u16 |
| 2 | magia `'S','W'` | 2 B |
| 4 | versione protocollo = 1 | u8 |
| 5 | id tag (FICR DEVICEID[0]) | u32 |
| 9 | stato: 0 vado in sonno, 1 pronta, 2 registra, 3 riservato (non usato), 4 memoria piena, 5 errore, 6 sincronizza | u8 |
| 10 | batteria mV/20 | u8 |
| 11 | % memoria non confermata | u8 |
| 12 | blocchi chiusi non confermati | u16 |
| 14 | ultimo `seq` scritto | u32 |
| 18 | secondi di registrazione del segmento | u16 |
| 20 | bit di errore (0 IMU, 1 flash, 2 batteria bassa) | u8 |

| 21 | colore della tag: indice 0–9 nella tavolozza sotto, 0xFF = non impostato | u8 |

Nome nella risposta alla scansione (nome locale completo): il **nome scelto dall'utente** (max **11** caratteri ASCII stampabili: con 12 il servizio 7a1e0001 non sta più nella scan response e la pagina non trova la tag), oppure `ST-xxxx` (ultime 4 cifre esadecimali dell'id) se non impostato. Il display usa scansione attiva per leggerlo.

**Nome e colore** si impostano dalla pagina `tools/index.html` con i comandi testuali sulla caratteristica comandi esistente `7a1e0004`: `NOME,<testo>` (vuoto = cancella) e `COLORE,<0-9>` (`COLORE,-1` = cancella); risposte `K nome <testo>`, `K colore <n>`, errori `X nome ...`/`X colore ...`. Salvati nell'InternalFS della tag (`/nome.bin`, come `/vcal.bin`), restano dopo riavvio e OTA. Il display li mostra nello spicchio (nome al posto di `ST-xxxx`, colore per sfondo, arco e pallino); senza colore usa quello dello spicchio.

Tavolozza (la stessa di `tools/display.html`): 0 blu `#3b82f6`, 1 arancione `#f97316`, 2 viola `#a855f7`, 3 ciano `#06b6d4`, 4 rosa `#ec4899`, 5 giallo `#eab308`, 6 bianco `#e5e7eb`, 7 verde lime `#84cc16`, 8 rosso `#ef4444`, 9 marrone `#a16207`.

### Servizio GATT di sincronizzazione `7a1e0101-5b1d-4c8e-9f3a-1d2c3b4a5e60`
- `7a1e0102-…` **CONTROLLO** (scrittura con risposta, richiede collegamento cifrato): display → tag.
- `7a1e0103-…` **DATI** (notifiche): tag → display. MTU richiesto 247.

| tipo | nome | verso | contenuto dopo il byte di tipo |
|---|---|---|---|
| 0x10 | PRONTO | D→T | versione u8 |
| 0x11 | CONFERMA | D→T | seq u32, crc32 u32 |
| 0x12 | RIPETI | D→T | seq u32 |
| 0x13 | STOP | D→T | motivo u8 (1 SD piena, 2 errore SD, 3 troppi errori) |
| 0x01 | MAPPA | T→D | millis tag u32, blocco aperto u16, 128 B (512 × 2 bit, blocco *i* nei bit 2·(i%4) del byte i/4: 0 libero, 1 aperto, 2 da validare, 3 validato) |
| 0x02 | BLOCCO | T→D | seq u32, blocco fisico u16, crc32 u32, millis del primo campione u32 |
| 0x03 | FRAMMENTO | T→D | seq u32, indice u8 (0..31), 128 B (frammento *k* = byte 128·k … del blocco da 4096 B) |
| 0x04 | CONFERMATO | T→D | seq u32 |
| 0x05 | FINE | T→D | ultimo seq u32 |
| 0x06 | ERRORE | T→D | codice u8 (1 CRC della conferma diverso, 2 seq sconosciuto, 3 flash) |

Dopo PRONTO la tag manda MAPPA, poi BLOCCO + 32 FRAMMENTI per il blocco non confermato più vecchio, e al più un secondo blocco prima della prima CONFERMA (finestra 2).

### Caratteristica di stato per la pagina `tools/index.html`
`7a1e0104-…` **STATO SYNC** (lettura + notifica ogni 2 s, nessuna cifratura richiesta, sola lettura): versione u8, id u32, stato u8, batteria mV/20 u8, % memoria non confermata u8, blocchi in attesa u16, ultimo seq u32, secondi di registrazione u16, errori u8, blocco aperto u16, seq più vecchio non confermato u32, mappa 128 B (stessa codifica di MAPPA) = **151 B**. La pagina **non può confermare** (CONTROLLO richiede il bonding col display). La tag accetta **2 collegamenti** contemporanei (display + pagina).

## 8. Formato della flash della tag (formato `.swr` 2)
- Blocco = settore da 4 KB = 16 pagine. **Pagina 0 del blocco = intestazione di blocco**, tipo `0xB1`; pagine 1–15 = pagine `.swr` del formato 1, invariate (segmento 0xA5, dati 0xD1, chiusura 0xE0; `[2..3]` = numero di pagina fisica).
- Intestazione di blocco (**formato 3**, dal 2026-11-10 sera): `[0]` 0xB1, `[1]` formato = 3, `[2..3]` pagina fisica, `[4..7]` millis, `[8..9]` mV, `[10]` temperatura, `[11]` flag, `[12..13]` segmento, `[14..15]` CRC16 (byte 0..13 e 16..255 con il campo conferma **considerato 0xFF**), `[16]` riservato 0xFF, `[17..20]` seq u32, `[21..24]` id tag u32, `[25..251]` 0xFF, **`[252..255]` conferma**: 4 × 0xFF = no, altro = confermato (la tag scrive 4 × 0x00).
- **Perché la conferma ha una parola di 4 byte tutta sua:** la flash Puya della XIAO, riscrivendo una parola da 4 byte già programmata, la **sostituisce** invece di fare l'AND dei bit. Nel formato 2 la conferma stava nel byte 16 e la scrittura `00 FF FF FF` rovinava i byte 17..19 del seq: intestazioni non valide e seq riusati (185 anomalie al display il 2026-11-10). Il formato 2 si legge ancora (conferma nel byte 16), non si scrive più.
- **Il seq non si riusa mai**, nemmeno dopo un azzeramento: prima di cancellare la flash la tag salva il massimo usato in `/seq.bin` (InternalFS); senza file parte da 1000.
- Contenuto della flash non riconosciuto: **non si cancella mai da solo** (4 lampi viola, si scarica con DUMP e si azzera esplicitamente).
- Il CRC32 del blocco (messaggio BLOCCO) si calcola sui 4096 B con il campo conferma a 0xFF.
- Le pagine non scritte di un blocco chiuso restano tutte 0xFF e sono **valide** (vuote) per il display e per i programmi su PC.
- Un blocco si chiude quando è pieno o quando il segmento finisce (le pagine restanti restano vuote); il segmento successivo comincia un blocco nuovo.
- All'avvio la tag legge le 512 intestazioni: ricava seq massimo, blocco aperto, blocchi confermati e non confermati. Spazio: si scrive nel blocco libero successivo; se non c'è, si cancella il **confermato più vecchio**; se tutti sono non confermati, **memoria piena**: stop della registrazione.
- Capacità utile: 15/16 della flash (~6% in meno rispetto al formato 1).

## Numeri da verificare
- Produzione: **si resta a 208 Hz** (decisione 2026-11-10) ≈ 1,25 KB/s (≈ 75 KB per minuto di nuoto).
- Trasferimento atteso con notifiche + 2M PHY: 30–80 KB/s (l'OTA attuale, con scritture con risposta da Windows, fa ~1 KB/s: non è indicativo). 4 min di nuoto a 208 Hz ≈ 300 KB ≈ 4–10 s di sosta. **Da misurare sul muro, con la tag sotto la cuffia.**
- Tempo da «fermo» a «collegato»: obiettivo < 1,5 s.

## Impatti sulle altre aree
- **Formato `.swr`:** numero di pagina 16 bit → `seq` di blocco 32 bit + byte `conferma` fuori CRC; anello invece di scrittura lineare; cambiano `swr_formato.h`, `swr.py`, `swr.js` e lo scarico USB (formato 2).
- **Firmware tag:** BLE acceso in registrazione (rivede la decisione del 2026-11-07), bonding; nessuna interpretazione del movimento.
- **Display T-RGB:** SD + BLE centrale + schermo insieme; c'è già stata contesa sulla PSRAM con il pannello RGB (decisione 2026-10-24): le scritture SD vanno provate per tremolio. Verificare quali pin usa la SD sul T-RGB.
- **Architettura display:** il Pi 4 proposto il 2026-11-06 salva solo eventi; questo protocollo trasporta il raw. Il T-RGB diventa il display «di sviluppo/1–3 nuotatori»; lo stesso protocollo serve poi alla base di ricarica.
