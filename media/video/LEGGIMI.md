# Video di presentazione di SwimTimer

Video da 120 s (1920x1080, 30 fps, H.264 + AAC 192 kbps 48 kHz) con musica originale.

## Come si rigenera
```
python media/video/genera_video.py                 # musica + miniatura + video
python media/video/genera_video.py --no-musica     # riusa musica_originale.wav
python media/video/genera_video.py --solo-musica   # solo la colonna sonora
python media/video/genera_video.py --anteprima 12 47.5 --dir cartella   # fotogrammi PNG a tempi scelti
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
