# Video di presentazione di SwimTimer

**Pubblicati su YouTube** — primo test in vasca (v3): italiano https://youtu.be/J01CR2nldp8 · inglese https://youtu.be/bs7WDUuwb-A. Aggiornamento novembre 2026 (v2): italiano https://youtu.be/_Htx2DawnF8 · inglese https://youtu.be/JLs5JJG4JG8. Prima presentazione (v0.5): italiano https://youtu.be/_2UzpOqblVI · inglese https://youtu.be/EVrdSybpnE4.

Video da 120 s (1920x1080, 30 fps, H.264 + AAC 192 kbps 48 kHz) con musica originale.

## Come si rigenera
```
python media/video/genera_video.py                 # musica + miniatura + video
python media/video/genera_video.py --no-musica     # riusa musica_originale.wav
python media/video/genera_video.py --solo-musica   # solo la colonna sonora
python media/video/genera_video.py --anteprima 12 47.5 --dir cartella   # fotogrammi PNG a tempi scelti
python media/video/genera_video.py --lingua en     # versione inglese: SwimTimer_presentazione_en.mp4 e miniatura_youtube_en.png
```
Servono Python 3.11 con numpy e Pillow, ffmpeg nel PATH e il font Bahnschrift di Windows.
Il video usa solo le tavole in `hardware/wallpaper_v0.5/png/`, i render della scheda
(`hardware/nrf52840/kicad/jlc/v0.5_swimtag_economica/`) e quelli del programmatore (`hardware/programmatore/img/`).

## Musica
`musica.py` sintetizza tutto da zero con numpy (cassa, hi-hat, clap, basso, pad, arpeggio, lead, riser, riverbero):
nessun campione, loop o brano esistente. La musica e' quindi originale, generata da codice e priva di diritti di terzi.
120 BPM, progressione Am9 - Fmaj7 - Dm9 - Em7, intro di 4 battute, drop al secondo 40 (sezione "tag v0.5"),
parte calma durante "stato", chiusura con accordo finale. Circa -16 LUFS, picchi sotto -1 dBFS, fade-in 1 s e fade-out 2 s.
I tagli di scena cadono sempre sui battiti (ogni 5 s = 10 battiti).

## Descrizione YouTube (pronta)
**Titolo:** SwimTimer: i tuoi tempi in vasca, senza fermarti e senza pulsanti (prototipo v0.5)

**Descrizione:**
SwimTimer e' un progetto per prendere i tempi mentre si nuota, senza fermarsi e senza premere pulsanti.
Un piccolo tag Bluetooth sotto la cuffia, con sensore di movimento a 6 assi, riconosce partenze, virate e arrivi.
I dati si scaricano fuori dall'acqua e un display a bordo vasca mostra i tempi.
In questo video: la scheda v0.5 (nRF52840, IMU LSM6DSV16X, flash 16 MB, cella LiPo 40 mAh, 21,59 x 28 mm),
le protezioni, le verifiche di progetto (DRC 0 errori, netlist 100/100) e il programmatore HAT per Raspberry Pi.
Le schede sono progettate e in arrivo: siamo in fase di prototipo, con le prime prove in vasca da fare.
Codice e documenti: repository GitHub PZero/SwimTimer.

**Tag:** SwimTimer, nuoto, cronometro, tag BLE, nRF52840, elettronica, progetto fai da te, piscina

*Musica originale generata per questo video.*

## Versione inglese
Pubblicata su YouTube: https://youtu.be/EVrdSybpnE4 (italiana: https://youtu.be/_2UzpOqblVI).
Stesse scene, musica e durata; cambiano solo i testi a schermo (`testi_en.py`, dizionario italiano → inglese).
Le tavole tecniche di sfondo restano quelle originali, con alcune scritte in italiano.

**Title:** SwimTimer: your lap times in the pool, no stopping and no buttons (prototype v0.5)

**Description:**
SwimTimer is an open project to time your swim without stopping and without pressing buttons.
A small Bluetooth tag under the swim cap, with a 6-axis motion sensor, detects starts, turns and finishes.
Data is downloaded out of the water and a poolside display shows your times.
In this video: the v0.5 board (nRF52840, LSM6DSV16X IMU, 16 MB flash, 40 mAh LiPo cell, 21.59 x 28 mm),
its protections, the design checks (0 DRC errors, 100/100 netlist pins) and the Raspberry Pi HAT programmer.
The boards are designed and on the way: this is the prototype stage, with the first pool tests still to come.
Code and documents: GitHub repository PZero/SwimTimer.

**Tags:** SwimTimer, swimming, lap timer, BLE tag, nRF52840, electronics, DIY project, swimming pool, wearable

*Original music generated for this video.*

---

# Video «A che punto siamo» (v2, novembre 2026)

120 s esatti, 1920x1080, 30 fps, H.264 (yuv420p, BT.709) + AAC 192 kbps 48 kHz, in due versioni con gli stessi tagli e la stessa musica:
`SwimTimer_avanzamento_it.mp4` e `SwimTimer_avanzamento_en.mp4`; miniature YouTube `miniatura_avanzamento_it.png` / `_en.png` (1280x720).
Nessun voice-over: solo testi a schermo (tipografia cinetica, Bahnschrift + Consolas per le formule) e musica originale.

## Come si rigenera
```
python media/video/genera_video_v2.py --clip-dir CARTELLA_VIDEO                         # musica + miniatura + video IT
python media/video/genera_video_v2.py --lingua en --no-musica --clip-dir CARTELLA_VIDEO  # versione EN (stessa musica)
python media/video/genera_video_v2.py --anteprima 5 30 50 --dir CARTELLA --clip-dir CARTELLA_VIDEO   # fotogrammi PNG
python media/video/genera_video_v2.py --solo-musica                                     # solo musica_v2.wav
python media/video/musica_v2.py percorso.wav                                            # colonna sonora da sola
```
`CARTELLA_VIDEO` contiene i 5 video originali dell'autore (WhatsApp, elencati in `CLIP` dentro lo script; predefinita
`~/Downloads/VideoTMP`). Non stanno nel repository: lo script ne estrae spezzoni di 6 s **senza audio** (`-an`), con
stabilizzazione leggera (`deshake`) sui verticali e un color grading comune, in una cache temporanea fuori dal repo
(variabile `SWIMTIMER_CLIP_CACHE` per cambiarla). Servono Python 3.11 con numpy e Pillow, ffmpeg nel PATH, i font Bahnschrift e Consolas di Windows.

## Materiale
- `img_v2/`: schermate fatte apposta, **solo dati inventati**: pagina Strumenti (Dal vivo in Demo, Registrazione, Firmware,
  Annotazione con un `.swr` sintetico generato con `firmware/xiao-stream/swr.py` e un video sintetico), display a bordo vasca
  (`tools/display.html?demo`), landing pubblica IT/EN (riquadro del video YouTube sfocato) e area riservata ricreata in locale con
  Firebase simulato (utenti `marco@example.com` ecc.). Nessuna email o foto reale.
- Render della scheda v0.6 (`hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/`).
- I grafici dei filtri sono calcolati con numpy su segnali inventati (fusione complementare, passa-basso, varianza mobile, autocorrelazione).
- Lo spezzone «cuffia» mostra il volto dell'autore (scelta dell'autore).

## Scene (tagli sui battiti, 120 BPM)
0 apertura · 6 la sfida · 12 il tag XIAO · 20 firmware OTA + scheda v0.6 · 26 testa 3D dal vivo · 32 analisi dal vivo ·
38 metodo dei test (sync con 5 tocchi) · 44 annotazione → dataset di verità (build-up) · **48 drop: filtri** (fusione, pulizia,
fermo/nuoto, cadenza e confidenza) · 72 piattaforma online · 78 accesso con approvazione · 84 collaborazione (SHA-256, autori) ·
90 display a bordo vasca · 96 prototipi (mockup e display rotondo) · 102 roadmap · 110 chiusura (sito, email, GitHub).

## Musica (`musica_v2.py`)
Originale, sintetizzata con numpy (riusa gli strumenti di `musica.py` e aggiunge un lead «saw» additivo e un sub-basso):
re minore, 120 BPM, progressione Dm9 - Bbmaj9 - Gm7/D - A7sus4; intro, groove, build-up 44-48 s con rullo e riser,
drop a 48 s sulla sezione filtri, pausa a 102 s, finale a 110 s e stacco netto a 118 s. Circa -16 LUFS, picchi sotto -1 dBFS.

## YouTube - italiano
**Titolo:** SwimTimer: a che punto siamo - tag, dati grezzi, filtri e piattaforma (novembre 2026)

**Descrizione:**
SwimTimer è un progetto aperto per prendere i tempi in vasca senza fermarsi e senza premere pulsanti:
un piccolo tag sotto la cuffia riconosce partenze, virate e arrivi, e un display a bordo vasca mostra i tempi.
In questo aggiornamento:
- il tag di prova XIAO nRF52840 Sense: IMU a 6 assi a 208 Hz, registrazione grezza su flash da 2 MB con compressione delta e CRC per pagina, Bluetooth spento in acqua, aggiornamento del firmware via Bluetooth (OTA);
- la scheda su misura v0.6 in arrivo;
- la testa 3D che segue i movimenti dal vivo e la pagina di analisi;
- il metodo dei test: video e dati grezzi sincronizzati con 5 tocchi, annotazione manuale di partenze, virate e arrivi per un dataset di verità;
- i filtri: fusione sensoriale (complementare / Madgwick), passa-basso e stima del bias del giroscopio, segmentazione fermo/nuoto con varianza mobile e soglie adattive, firma della virata, cadenza con autocorrelazione, punteggio di confidenza;
- la piattaforma online: sito pubblico IT/EN, accesso con Google solo dopo l'approvazione dell'amministratore, sessioni condivise, video verificati con impronta SHA-256, annotazioni con autore;
- il display a bordo vasca (mockup con dati inventati) e i prossimi passi: prima campagna di test in vasca da 50 m.
Sito: https://swimtimer-pzero.web.app · Contatti: SmartSwimTimer@gmail.com · Codice: GitHub PZero/SwimTimer
Musica originale generata per questo video. Le registrazioni, i nuotatori e i tempi mostrati sono inventati.

**Tag:** SwimTimer, nuoto, cronometro, piscina, tag BLE, nRF52840, XIAO, IMU, sensor fusion, filtro di Madgwick, elaborazione dei segnali, Firebase, progetto open source, wearable

## YouTube - English
**Title:** SwimTimer progress update - tag, raw data, filters and platform (November 2026)

**Description:**
SwimTimer is an open project to time your swim without stopping and without pressing buttons:
a small tag under the swim cap detects starts, turns and finishes, and a poolside display shows your times.
In this update:
- the XIAO nRF52840 Sense test tag: 6-axis IMU at 208 Hz, raw recording to 2 MB flash with delta compression and per-page CRC, Bluetooth off in the water, firmware updates over Bluetooth (OTA);
- the custom v0.6 board on the way;
- the live 3D head that follows your movements and the analysis page;
- the test method: video and raw data synchronised with 5 taps, hand annotation of starts, turns and finishes to build a ground-truth dataset;
- the filters: sensor fusion (complementary / Madgwick), low-pass filtering and gyro bias estimation, rest/swim segmentation with moving variance and adaptive thresholds, turn signature, stroke cadence via autocorrelation, confidence scores;
- the online platform: public IT/EN site, Google sign-in only after admin approval, shared sessions, videos verified by SHA-256 fingerprint, annotations with author;
- the poolside display (mockup with made-up data) and next steps: the first test campaign in a 50 m pool.
Site: https://swimtimer-pzero.web.app · Contact: SmartSwimTimer@gmail.com · Code: GitHub PZero/SwimTimer
Original music generated for this video. Recordings, swimmers and times shown are made up.

**Tags:** SwimTimer, swimming, lap timer, swimming pool, BLE tag, nRF52840, XIAO, IMU, sensor fusion, Madgwick filter, signal processing, Firebase, open source project, wearable

---

# Video «Il primo test in vasca» (v3, novembre 2026)

**Pubblicato su YouTube:** italiano https://youtu.be/J01CR2nldp8 · inglese https://youtu.be/bs7WDUuwb-A.

150 s, 1920x1080, 30 fps, H.264 + AAC 192 kbps 48 kHz, italiano ed inglese, musica originale `musica_v3.py` (stessi strumenti di v2,
sezioni ridistribuite: drop a 76 s sulla parte OpenCV, stacco a 148 s). Sequenza approvata: `STORYBOARD_v3.md`.
**Dati reali** della sessione del 9/11/2026 dell'autore (scelta dell'autore): fotogrammi del video subacqueo, grafici IMU, schermate
dell'editor e della pagina di analisi. Per questo le immagini, il video e le miniature **non stanno nel repository**: si generano in una cartella locale.

## Come si rigenera
```
python media/video/prepara_img_v3.py --video VIDEO.mp4 --swr SESSIONE.swr --viz viz.json --segnali video_segnali.npz --pelle pelle.npz --v160 v160.npy --out CARTELLA_IMG
python media/video/genera_video_v3.py --img CARTELLA_IMG                         # musica + miniatura + video IT
python media/video/genera_video_v3.py --img CARTELLA_IMG --lingua en --no-musica # versione EN
python media/video/genera_video_v3.py --img CARTELLA_IMG --anteprima 6 46 106 --dir CARTELLA
```
I file `video_segnali.npz`, `pelle.npz` e `v160.npy` vengono dagli script di `analisi/video/` (estrai, stabilizza, segnali, pelle);
`viz.json` è il blocco di dati della pagina di analisi IMU. Gli screenshot della pagina di analisi e dell'editor si fanno con Chrome headless.

## Scene (tagli sui battiti, 120 BPM)
0 gancio: il tocco fotogramma per fotogramma · 8 la prova del 9/11 · 18 sincronia (picco di 11,4 g) · 26 etichette a mano (78 eventi) ·
36 filtri sui dati IMU · 52 risultati dei filtri (arrivo ±0,88 s, obiettivo ±0,3 s non raggiunto) · 62 colpo di scena: etichette imprecise ·
**76 drop: OpenCV** (stabilizzazione, maschera, filtro pelle) · 88 distanza dal muro e chimografo · 100 un arrivo, tre viste ·
110 risultati OpenCV · 118 la decisione: metodo strutturato e rete neurale solo per l'arrivo · 132 prossimi passi · 142 chiusura.

## YouTube - italiano
**Titolo:** SwimTimer: il primo test in vasca - filtri IMU, OpenCV e rete neurale (novembre 2026)

**Descrizione:**
Primo test vero in vasca di SwimTimer, il progetto aperto per prendere i tempi senza fermarsi e senza premere pulsanti.
Una Insta360 sul fondo vicino al muro, un tag XIAO nRF52840 Sense sotto la cuffia: 8:50 di video a 50 fps e 17 minuti di dati IMU a 214 Hz.
In questo video:
- la sincronia video-dati con un colpo sul tag (picco di 11,4 g);
- 78 eventi etichettati a mano e i filtri sui dati IMU (orientamento della testa con il filtro di Mahony, viso al cielo, capriola, scivolata);
- i risultati: arrivi trovati 10 su 15, errore ±0,88 s, obiettivo ±0,3 s non raggiunto;
- il colpo di scena: lo stesso arrivo etichettato due volte cambia fino a 0,45 s, il riferimento era impreciso;
- OpenCV: stabilizzazione, sottrazione dello sfondo, filtro colore pelle contro le bolle, distanza dal muro fotogramma per fotogramma;
  partenze trovate 14 su 14 con ±0,14 s, nessun errore sul tipo di evento;
- la decisione: metodo strutturato (dataset, banco di prova in streaming, validazione su sessioni nuove) e una piccola rete neurale
  solo per l'arrivo, con notifica entro 1,5 s e tempo datato all'istante del tocco;
- i prossimi passi: ripetute da 100 m, camera sul muro, sincronia a inizio e fine.
Sito: https://swimtimer-pzero.web.app · Contatti: SmartSwimTimer@gmail.com · Codice: GitHub PZero/SwimTimer
Musica originale generata per questo video. Le immagini e i dati sono della sessione reale dell'autore.

**Tag:** SwimTimer, nuoto, cronometro, piscina, IMU, OpenCV, visione artificiale, rete neurale, TinyML, nRF52840, XIAO, Insta360, wearable, progetto open source

## YouTube - English
**Title:** SwimTimer: the first pool test - IMU filters, OpenCV and a neural network (November 2026)

**Description:**
The first real pool test of SwimTimer, the open project to time your swim without stopping and without pressing buttons.
An Insta360 on the pool floor next to the wall, a XIAO nRF52840 Sense tag under the swim cap: 8:50 of video at 50 fps and 17 minutes of IMU data at 214 Hz.
In this video:
- video-data sync with one tap on the tag (11.4 g peak);
- 78 hand-labelled events and the filters on the IMU data (head orientation with a Mahony filter, face up, flip turn, glide);
- the results: 10 of 15 finishes found, ±0.88 s error, the ±0.3 s target not reached;
- the plot twist: the same finish labelled twice moves by up to 0.45 s, the reference itself was inaccurate;
- OpenCV: stabilisation, background subtraction, a skin-colour filter against bubbles, distance from the wall frame by frame;
  14 of 14 starts found within ±0.14 s, no event-type errors;
- the decision: a structured method (dataset, streaming test bench, validation on new sessions) and a small neural network
  only for the finish, notifying within 1.5 s with the time back-dated to the touch;
- next steps: 100 m repeats, a camera on the wall, sync at start and end.
Site: https://swimtimer-pzero.web.app · Contact: SmartSwimTimer@gmail.com · Code: GitHub PZero/SwimTimer
Original music generated for this video. Images and data come from the author's real session.

**Tags:** SwimTimer, swimming, lap timer, swimming pool, IMU, OpenCV, computer vision, neural network, TinyML, nRF52840, XIAO, Insta360, wearable, open source project
