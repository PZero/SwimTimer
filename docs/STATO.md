# Stato del progetto

**Ultimo aggiornamento:** 2026-11-10. Tutto è nel repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: **primo test in vasca fatto (9/11)**; il riferimento degli eventi ora viene dal video con OpenCV; il banco di prova IMU è pronto; si decide il metodo per i filtri e la rete neurale dell'arrivo.

## Fotografia
- **Scheda v0.6 "Rev0"** (`hardware/nrf52840/kicad/`): DRC/ERC 0; preventivo NextPCB 216,39 $ per 20 pz, in attesa di Viviane (fino a mer 2026-11-11).
- **Tag XIAO nRF52840 Sense** (cella 1000 mAh, regolatore 3,3 V guasto: va con diodo): firmware **0.5.4** (carica a 100 mA, registra raw su QSPI 2 MB, 208 Hz ≈ 17,6 min). `release/xiao.bin` + `xiao.json` ora **0.5.4** (CRC32 `b771d198`); l'OTA di questo pacchetto dalla pagina non è ancora provato.
- **Test 1 in vasca (9/11):** Insta360 X4 sul fondo vicino al muro (video 50 fps, 8:50), tag in testa (17 min, 214 Hz, memoria piena). 78 etichette manuali, poi eventi **proposti da OpenCV e verificati** (14 P entro ±0,14 s, 13 A ±0,4 s, 10 V ±0,45 s, nessun errore di tipo). Dati e video restano fuori dal repo (dati di salute).
- **`analisi/video/`** (OpenCV: stabilizzazione, sfondo, filtro pelle, distanza dal muro, classificazione) e **`analisi/imu/`** (banco di prova in streaming, dataset, valutazione, esperimento frequenze, 5 test verdi). Filtri di oggi riprodotti: A 10/15 ±0,88 s; contro il riferimento OpenCV A 57% ±0,8 s (notifica 0,9 s, causale), P 71%, V 73% (precisione 47%). A **52 Hz nessuna perdita** (≈55 min nei 2 MiB); k orologi ≈ 0,9993 (la «deriva 0,24%» probabilmente non esiste).
- **App online** (Firebase Spark): https://swimtimer-pzero.web.app — landing IT/EN con i video, contatti, `/area/`, `/strumenti/`, `/display/`. Editor di annotazione (area e tools): lista senza scroll della pagina, fps reali misurati, frecce ←/→ spostano l'evento cliccato (Maiusc ±10, Esc).
- **Video YouTube v3 «Il primo test in vasca»** (150 s, dati reali dell'autore): IT https://youtu.be/J01CR2nldp8, EN https://youtu.be/bs7WDUuwb-A. Precedenti: aggiornamento nov. 2026 (IT `_Htx2DawnF8`, EN `JLs5JJG4JG8`); presentazione (IT `_2UzpOqblVI`, EN `EVrdSybpnE4`).
- **Display a bordo vasca** (da confermare): Pi 4 + dongle nRF52840 + monitor 15,6" + power bank; mockup `tools/display.html`.

## Prossimi passi
1. **Metodo filtri (fase 3):** urti >8 g come ancora per P/V; macchina a stati; rete 1D causale per l'arrivo a 26–52 Hz (validazione «una sessione esclusa»); calibrazione assi. Vedi `rapporto_fase2.md` (fuori dal repo).
2. **Seconda seduta strutturata:** ripetute da 100 m, camera attaccata al muro di partenza, colpi di sync a inizio e fine (e a ogni pausa), 3 pose di calibrazione, montaggio ruotato.
3. Firmware: frequenza a 52 Hz (≈55 min) e compressione migliore sotto i 52 Hz; provare l'OTA di `xiao.bin` 0.5.4.
4. Editor: due video insieme (seconda camera) con sync sul tempo dei dati; video da Drive (serve abilitare la Drive API del progetto, lasciato stare).
5. Decidere NextPCB dopo mer 2026-11-11; architettura display.

## Problemi aperti
- Fine video: dopo la P a 510 s i dati mostrano ~50 s di quiete che nel video non ci sono (ipotesi: il video non contiene la pausa).
- Una sola sessione e un solo nuotatore: i numeri sono ottimistici (assi stimati sull'intera sessione).
- Dal fondo il muro appare come una fascia: tocco della mano solo ±0,4 s.
- «Deriva 0,24%» detta nel video v3: probabilmente inesistente (k ≈ 0,9993).
- Messaggio di prova «Prova Inventata» da cancellare in «Messaggi». Tag: dopo reset USB una volta non rispondeva; LED poco visibile sotto la cuffia.
- Privacy: video e raw dei nuotatori sono dati di salute (consenso scritto, permesso della piscina, mai nel repo).
- Rischio V-cut v0.6; BLE non attraversa l'acqua; brevetti.

## Decisioni in attesa dell'utente
- Programma delle prossime sedute e piscina; ordine NextPCB; scheda di scorta e multimetro; architettura display; test per l'Effort; Zephyr o Arduino; correggere nel video la frase sulla deriva. Vedi `docs/DOMANDE-APERTE.md`.

## Riferimenti
- Firmware: `firmware/xiao-stream/LEGGIMI.md`. Scheda: `hardware/nrf52840/progetto.md`. Pagina locale: `tools/index.html`. App: `app/`, `firebase/`, `docs/MODELLO-DATI.md`. Analisi: `analisi/imu/README.md`, `analisi/video/`. Video: `media/video/LEGGIMI.md`.
