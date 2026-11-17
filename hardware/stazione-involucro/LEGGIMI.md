# Scatola di PROVA della stazione a bordo vasca

`stazione.scad` (OpenSCAD, parametrico, misure in mm). Parti: `corpo` e `coperchio`. STL in `stl/` (`corpo_stampa.stl` = corpo già capovolto, `coperchio.stl`), esportati con `openscad.exe -D PARTE="..."`.
Anteprima: `PARTE="assieme"` (le schede sono fantasmi trasparenti). Misure aggiornate con le foto e le misure dell'utente del 2026-11-14; `(S)` nel `.scad` = ancora stimato.

## Come è fatta
- In uso sta **in piedi, display in verticale**: lato **+X in alto** (USB, vano ricevitore XIAO), lato **-X in basso** (SD, interruttore del PowerPack). Dal coperchio verso il fronte: **cella LiPo (~9 mm) sotto la scheda → PowerPack V1.2 (85 x 56, porte USB-A/micro-USB sopra) → 4 distanziali M2.5 da 11 mm → Raspberry Pi 3 → display** appoggiato sulle porte USB del Pi (`GAP_PI_DISP` = 16,5) e innestato sul GPIO.
- **Solo il display è avvitato**: 4 viti M3 (con rondella, il foro delle alette sembra ~4 mm) sulle 4 alette, interasse **80 x 65**, in 4 torrette da 8 mm sul fronte. Pi e PowerPack **pendono dal display** (GPIO + distanziali): niente sponde né viti proprie; il coperchio ha solo 4 fermi laterali per il PowerPack.
- **Larghezza**: le alette (75 mm) superano il Pi (56): scatola larga ~106 mm. Il lato HDMI (Y basso) ha un **canale da 36 mm** (misura dell utente: 3,6 cm per tutti i cavi) (`BAT_PLUG_OUT`) per la spina USB-A del cavo corto USB-A → micro-USB che va dal PowerPack alla micro-USB del Pi (tutto interno). L'**adattatore HDMI a U** (sporge ~5 mm dal bordo del Pi) sta dentro lo stesso canale: **nessuna apertura HDMI**.
- **Aperture**: la ricarica si fa a casa aprendo la scatola (`APERTURA_RICARICA = false`: niente foro e niente gocciolatoio, che era uno sbalzo flottante). Con `true`: (1) **micro-USB di ricarica** del PowerPack sul lato Y basso (15 x 12 mm) con **gocciolatoio a cuneo a 45°** sopra (lato +X); (2) **feritoia sul fondo (-X)** per l'interruttore ON/OFF (si sposta con una punta; è anche lo scarico dell'acqua). Le porte USB del Pi restano chiuse; la XIAO usa quella del lato +X con il cavo nel vano (`E_RUN` = 30 mm).
- **Coperchio** in una battuta (resta 1 mm di parete), **4 viti M3 x 8 autofilettanti** nelle torrette dei lati corti. Tra battuta e coperchio: nastro/gommapiuma da 1 mm per gli schizzi.
- **Schizzi**: fronte da 2 mm davanti a una **lastrina trasparente** (PET/policarbonato 1 mm, incollata da dietro, sovrapposizione 1,2 mm per lato); prese d'aria a **feritoie inclinate** (imbocco esterno più in basso, sui lati lunghi, mai sopra lo schermo); gocciolatoio sulla ricarica.
- **Cordino di sicurezza**: 2 anelli (uno per lato lungo, foro 5 mm), zona alta, piano parallelo agli strati.
- **Ricevitore XIAO** in un vano separato in cima (parete con passaggio USB-C), dietro il fronte, solo PLA attorno all'antenna, lontano dal Pi (~32 mm dalla fine del Pi). Cavo USB-C → USB-A corto (≤ 20 cm). Il 2,4 GHz non attraversa l'acqua: provare con misure reali di RSSI. Se il Bluetooth interno del Pi non serve: `dtoverlay=disable-bt`.

## Stampa (A1 mini, PLA)
- Ingombro corpo: **164,3 x 106,3 x 54 mm** (con gli anelli: ~136 mm in Y). Entra nel piano 180 x 180.
- Corpo: **fronte sul piano** (`corpo_stampa.stl` è già capovolto), nessun supporto. Il cuneo della ricarica è un prisma verticale (nessun aggetto); le torrette partono dal fronte.
- Coperchio: piatto, fermi e pilastrino in alto, nessun supporto.
- Pareti 2 mm (3 perimetri da 0,4), strati 0,2 mm, riempimento 20%; **anelli e torrette: riempimento 100% o 4+ perimetri**.

## MISURE ANCORA STIMATE, da verificare col calibro prima di stampare
Display: 1. PCB `DISP_L` x `DISP_W` (98,5 x 56,5) e larghezza con le alette `DISP_TAB_W` (75); 2. diametro dei fori delle alette (~4 mm dalla foto) e area attiva/offset (`ACT_*`, centrata); 3. altezza pannello+touch sopra il PCB `DISP_PANEL_T` (7,2 dalla foto di fianco); 4. **sporgenza oltre il Pi dal lato SD** `DISP_OVER` (13); 5. adattatore HDMI a U: larghezza (~20) e sporgenza `HDMI_U_OUT` (5).
PowerPack: 6. spessore cella `BAT_CELL` (9) e suo ingombro; 7. altezza USB-A sopra la scheda `BAT_COMP_H` (7,5); 8. posizione micro-USB di ricarica `BAT_CHG_X` (47,6 dal lato SD) e interruttore `BAT_SW_Y` (28,4 dal bordo delle porte, all'estremità -X); 9. **sporgenza della spina USB-A con guaina** `BAT_PLUG_OUT` (22): decide la larghezza della scatola (con spina ad angolo retto o piatta ~8 mm, scatola più stretta di ~14 mm); 10. che la spina micro-USB di ricarica arrivi alla presa (~22 mm di profondità dalla parete).
Distanze: 11. `GAP_PI_DISP` = 16,5 (margine di 0,5 mm sulle porte USB alte 16 mm: verificare sul pezzo montato); 12. distanziali M2.5 da 11 mm (`BAT_DIST`) con margine di 3,5 mm sopra i componenti del PowerPack.
Altro: 13. XIAO (21 x 17,8 x 3,5) e spina USB-C; 14. lastrina: 1 mm ammesso dal touch resistivo (provare 0,5 mm).

## Rischi noti
- Il Pi pende dal GPIO del display (niente sponde): con urti forti la sollecitazione va sull'header; se serve, aggiungere due appoggi sotto il Pi.
- La micro-USB del display (lato HDMI) resta chiusa e non usata: il display è alimentato dal GPIO.

## Prolunga dell'interruttore (`stl/prolunga.stl`)
Pezzo stampato a parte (PLA, piatto, senza supporti): pomello fuori dalla parete, asta nella feritoia del fondo (-X), forcella che abbraccia la levetta ON/OFF del PowerPack. Misure della levetta **stimate dalla foto** (larghezza 2 mm, sporgenza 2,5 mm, corsa 3 mm, asse a 28,4 mm dal lato porte): stampare prima questo pezzo e provarlo sulla scheda. Con `PARTE = "prolunga"` si esporta lo STL.

## Modifiche successive
- `APERTURA_RICARICA = false`: nessun foro e nessun gocciolatoio (la ricarica si fa a casa, aprendo la scatola); il gocciolatoio era uno sbalzo flottante per la stampa.
- Anelli del cordino con mensola a 45° verso il piano di stampa (senza, Bambu Studio segnalava uno sbalzo flottante).
- Spazio cavi 3,6 cm (`BAT_PLUG_OUT = 36`, `E_RUN = 36`): ingombro 164,3 × 106,3 × 54 mm.
- Distanziali PowerPack–Pi: 11 mm previsti (`BAT_DIST`); con quelli da 22 mm servirebbe una cornice di 11 mm fra corpo e coperchio (domanda 73).
