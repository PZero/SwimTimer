// SwimTimer - scatola di PROVA della stazione a bordo vasca (OpenSCAD, parametrico). Misure in mm.
// Dal basso: coperchio -> cella LiPo -> PowerPack V1.2 -> distanziali -> Raspberry Pi 3 B -> display (poggia sulle porte USB, sul GPIO).
// In uso la scatola sta in piedi con il display in verticale: il lato +X (USB, ricevitore XIAO) e' IN ALTO,
// il lato -X (SD, interruttore del PowerPack) e' IN BASSO. Acqua = scende verso -X.
// Parti: "corpo" (tubo con fronte e finestra, aperto dietro), "coperchio" (piastra, 4 viti M3),
// "assieme" (anteprima), "corpo_stampa" (corpo capovolto, fronte sul piano, senza supporti).
// Solo il display e' avvitato (4 alette 80x65, viti da dietro). Pi e PowerPack pendono dal display (GPIO + distanziali).
// Riferimento: X lungo il Pi (0 = lato SD), Y corto (0 = lato HDMI/micro-USB), Z dal piano interno del coperchio.

PARTE = "assieme";   // "assieme", "corpo", "coperchio", "corpo_stampa", "prolunga"

// ======== MISURE DA VERIFICARE COL CALIBRO (vedi LEGGIMI.md) ========
// Ricavate dalle foto dell'utente (2026-11-14); (S) = stimato dalla foto, da verificare.
// -- Raspberry Pi 3 Model B (misure ufficiali) --
PI_L = 85;  PI_W = 56;  PI_T = 1.4;
PI_FORI_X = 58;  PI_FORI_Y = 49;  PI_FORO_OFF = 3.5;
PI_USB_H = 16;                    // altezza porte USB sopra il PCB
PI_HDMI_X = 32;                   // centro HDMI dal lato SD
PI_PWR_X = 10.6;                  // micro-USB di alimentazione dal lato SD (lato Y basso)
// -- RPi PowerPack V1.2 (85 x 56 misurato dall'utente; stesso orientamento del Pi, fori coincidenti) --
BAT_L = 85;  BAT_W = 56;
BAT_CELL = 9;                     // (S) cella LiPo SOTTO la scheda
BAT_GAP = 0.4;                    // nastro/gioco tra cella e scheda
BAT_PCB_T = 1.6;
BAT_COMP_H = 7.5;                 // (S) altezza USB-A sopra la scheda
BAT_DIST = 11;                    // distanziali M2.5 tra PowerPack e Pi (11 mm commerciali)
BAT_Z = BAT_CELL + BAT_GAP;       // faccia inferiore della scheda
BAT_H = BAT_Z + BAT_PCB_T + BAT_COMP_H;   // quota massima dei componenti
BAT_CHG_X = 47.6;                 // (S) micro-USB di ricarica dal lato SD, sul lato lungo delle porte (Y basso)
BAT_SW_Y = 28.4;                  // (S) interruttore ON/OFF: posizione in Y dal lato porte, sul lato corto (-X)
// -- prolunga dell'interruttore (parte stampata a parte; misure (S) dalla foto, da verificare) --
SW_LEV_W = 2.0;  SW_LEV_OUT = 2.5;  // levetta: larghezza (Y) e sporgenza oltre il bordo della scheda (-X)
SW_CORSA = 3;                       // corsa ON/OFF lungo Y
SW_ZC = BAT_Z + BAT_PCB_T + 1.5;    // quota dell'asse della levetta
PRO_W = 4;  PRO_H = 3.5;  FORK_T = 1.5;  FORK_GAP = SW_LEV_W + 0.5;
KNOB_X = 6;  KNOB_Y = 12;           // pomello fuori dalla parete (spessore = PRO_H, stampa piatta)
SLOT_W = FORK_GAP + 2*FORK_T + SW_CORSA + 1;   // la forcella passa dalla feritoia, il pomello no
BAT_PLUG_OUT = 36;                // (S) sporgenza della spina USB-A (con guaina) oltre il bordo del PowerPack.
                                  // Con spina ad angolo retto o piatta si puo' scendere a ~8 (scatola piu' stretta).
// -- Waveshare 4inch HDMI LCD (con alette di fissaggio) --
DISP_L = 98.5;  DISP_W = 56.5;    // PCB (S)
DISP_TAB_W = 75;                  // (S) larghezza con le 4 alette (lato corto), dalla foto
DISP_FORI_L = 80;  DISP_FORI_W = 65;   // interasse fori: misurato dall'utente
DISP_PCB_T = 1.6;
DISP_PANEL_T = 7.2;               // (S) pannello + touch sopra il PCB (dalla foto di fianco)
ACT_L = 86.4;  ACT_W = 51.84;     // area attiva (480x800 a passo 0,108)
ACT_OFF_X = (DISP_L - ACT_L) / 2; // (S) area attiva centrata sui fori (a occhio sulle foto)
ACT_OFF_Y = (DISP_W - ACT_W) / 2;
YC = PI_W / 2;                    // asse di simmetria Pi / PowerPack / display (lato corto)
DISP_Y0 = YC - DISP_W / 2;
// fori: [y assoluto, x dal bordo corto del PCB]
DISP_FORI = [[YC - DISP_FORI_W/2, DISP_L/2 - DISP_FORI_L/2], [YC + DISP_FORI_W/2, DISP_L/2 - DISP_FORI_L/2],
             [YC - DISP_FORI_W/2, DISP_L/2 + DISP_FORI_L/2], [YC + DISP_FORI_W/2, DISP_L/2 + DISP_FORI_L/2]];
VITE_PILOTA = 2.6;                // foro pilota per M3 autofilettante (foro alette ~4 mm (S): usare rondella)
TORR_D = 8;                       // torrette del display
GAP_PI_DISP = 16.5;               // dal lato alto del PCB del Pi al lato basso del PCB display: il display poggia sulle porte USB
DISP_OVER = 13;                   // (S) sporgenza del display oltre il Pi dal lato SD (X negativo)
HDMI_U_OUT = 5;                   // (S) sporgenza dell'adattatore HDMI a U oltre il bordo del Pi: resta INTERNO (nessuna apertura)
// -- XIAO nRF52840 (ricevitore) --
XIAO_L = 21;  XIAO_W = 17.8;  XIAO_T = 3.5;
// ======== SCELTE DI PROGETTO ========
PARETE = 2;  TOL = 0.4;
SHEET_T = 1.0;                    // lastrina trasparente (PET/policarbonato) incollata DIETRO il fronte
FRONTE = 2 + SHEET_T;             // fronte: 2 mm davanti alla lastrina = bordo sovrapposto
FINESTRA_M = 0.5;                 // margine della finestra oltre l'area attiva
POCKET_M = 1.2;                   // la lastrina e' piu' grande della finestra di questo margine per lato
COPERCHIO_T = 2;  GIOCO_COP = 0.3;
PILOTA_COP = 2.6;                 // M3 x 8 autofilettanti, 4 pezzi
E_RUN = 36;                       // vano cavo/spina USB oltre il lato USB del Pi
PART = 2;                         // parete di separazione del vano XIAO
BAY_L = 23;                       // vano XIAO (in alto)
Z_PI = BAT_Z + BAT_PCB_T + BAT_DIST;
Z_DISP_B = Z_PI + PI_T + GAP_PI_DISP;
Z_DISP_T = Z_DISP_B + DISP_PCB_T;
Z_FIN = Z_DISP_T + DISP_PANEL_T + 0.3;      // faccia interna del fronte
Z_TOP = Z_FIN + FRONTE;
RING_D = 12;  RING_HOLE = 5;  RING_T = 6;  RING_OUT = 9;   // anelli per il cordino (foro >= 4)

X0 = -max(DISP_OVER, 0) - TOL;
XP = max(PI_L, DISP_L - DISP_OVER) + TOL;       // fine zona Pi
XPART0 = XP + E_RUN;  XPART1 = XPART0 + PART;
X1 = XPART1 + BAY_L;
CH_Y = max(BAT_PLUG_OUT, HDMI_U_OUT + 2, DISP_TAB_W/2 - YC);   // canale sul lato Y basso: spina USB-A + cavo + adattatore HDMI
Y0 = -CH_Y - TOL;  Y1 = YC + max(PI_W, DISP_TAB_W)/2 + TOL;
LI = X1 - X0;  WI = Y1 - Y0;
YB = (Y0 + Y1) / 2;                              // asse del vano XIAO
XB0 = XPART1 + 0.5;                              // bordo USB-C dello XIAO
$fn = 40;

echo(str("Esterno ", LI+2*PARETE, " x ", WI+2*PARETE, " x ", Z_TOP+COPERCHIO_T, "  (piano 180x180)"));
echo(str("Porte USB del Pi fino a z=", Z_PI+PI_T+PI_USB_H, "; PCB display a z=", Z_DISP_B, "; margine ", GAP_PI_DISP - PI_USB_H, " mm (il PCB poggia sulle porte)"));
echo(str("Componenti PowerPack fino a z=", BAT_H, "; Pi (faccia inferiore) a z=", Z_PI, "; margine ", Z_PI - BAT_H));
if (DISP_OVER < 9) echo("ATTENZIONE: DISP_OVER < 9, le torrette del coperchio non entrano");

function DISP_X0() = -DISP_OVER;
module box(x0,y0,z0,x1,y1,z1) translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);

// torrette per le viti del coperchio sui muri corti (rampa a 45 gradi sopra: niente supporti)
PAD_D = 7;  PAD_W = 9;  PAD_H = 23;  PAD_Y = [YB - 16, YB + 16];
module pad(xw, dir, y)
  translate([xw, y + PAD_W/2, 0]) scale([dir,1,1]) rotate([90,0,0]) linear_extrude(PAD_W)
    polygon([[-1,0],[PAD_D,0],[PAD_D,PAD_H],[0,PAD_H+PAD_D],[-1,PAD_H+PAD_D]]);
module pad_fori(xw, dir, r) for (y = PAD_Y) translate([xw + dir*3.5, y, -1]) cylinder(d=r, h=PAD_H - 2);

// feritoie con alette inclinate: l'imbocco esterno e' piu' in basso (verso -X) di quello interno
module feritoie(x_from, x_to, z0, z1, lato) {
  sh = PARETE + 0.6;
  yo = (lato == 0) ? Y0 - PARETE - 0.2 : Y1 + PARETE + 0.2;
  yi = (lato == 0) ? Y0 + 0.2 : Y1 - 0.2;
  for (x = [x_from : 4.5 : x_to])
    translate([0,0,z0]) linear_extrude(z1 - z0)
      polygon([[x,yo],[x+2.2,yo],[x+2.2+sh,yi],[x+sh,yi]]);
}

// anello per il cordino: piano dell'anello parallelo agli strati di stampa (asse del foro = Z di stampa)
RING_X = XP + 14;  RING_Z = 16;
module anello_corpo(lato) {
  yw = (lato == 0) ? Y0 - PARETE : Y1 + PARETE;
  s = (lato == 0) ? -1 : 1;
  // mensola a 45 gradi verso il fronte (= verso il piano di stampa): senza, l'anello e' uno sbalzo flottante
  hull() {
    translate([RING_X, yw + s*RING_OUT, RING_Z]) cylinder(d=RING_D, h=RING_T);
    translate([RING_X - 8, min(yw - s*1, yw + s*1) , RING_Z]) cube([16, 2, RING_T + RING_GUSSET]);
  }
}
RING_GUSSET = RING_OUT + RING_D / 2;   // altezza della mensola alla parete (45 gradi)
module anello_foro(lato) {
  yw = (lato == 0) ? Y0 - PARETE : Y1 + PARETE;
  s = (lato == 0) ? -1 : 1;
  translate([RING_X, yw + s*RING_OUT, RING_Z - 1]) cylinder(d=RING_HOLE, h=RING_T + RING_GUSSET + 2);   // il foro attraversa anche la mensola
}

// cuneo a 45 gradi sopra un'apertura laterale (lato Y basso): lo scolo cade a -X dell'apertura
WEDGE_OUT = 8;
module gocciolatoio(xa, z0, z1)
  translate([0,0,z0]) linear_extrude(z1 - z0)
    polygon([[xa, Y0 - PARETE + 0.01], [xa, Y0 - PARETE - WEDGE_OUT], [xa + WEDGE_OUT, Y0 - PARETE + 0.01]]);

APERTURA_RICARICA = false;        // la scatola si apre a casa per ricaricare: niente foro ne gocciolatoio (era uno sbalzo flottante)
CHG_W = 15;  CHG_H = 12;          // apertura per la spina micro-USB di ricarica
CHG_ZC = BAT_Z + BAT_PCB_T + 1.3; // quota del centro della presa micro-USB

module corpo() {
  difference() {
    union() {
      difference() {
        box(X0-PARETE, Y0-PARETE, -COPERCHIO_T, X1+PARETE, Y1+PARETE, Z_TOP);
        box(X0, Y0, -COPERCHIO_T-1, X1, Y1, Z_FIN);
        box(X0-1, Y0-1, -COPERCHIO_T-1, X1+1, Y1+1, 0);         // battuta del coperchio (resta 1 mm)
      }
      // parete di separazione del vano XIAO
      box(XPART0, Y0 - 0.5, 0, XPART1, Y1 + 0.5, Z_FIN + 0.01);
      // Pi e PowerPack NON poggiano sulla scatola: il Pi e' innestato sul GPIO del display, il PowerPack sta sui distanziali del Pi
      // torrette del display, dal fronte (sulle 4 alette)
      for (h = DISP_FORI) translate([DISP_X0() + h[1], h[0], Z_DISP_T]) cylinder(d=TORR_D, h=Z_FIN - Z_DISP_T + 0.01);
      // torrette del coperchio (lati corti)
      for (y = PAD_Y) { pad(X0, 1, y); pad(X1, -1, y); }
      // vano XIAO: 4 piedini e guide laterali, sul fronte; fermo lato antenna
      for (xx = [XB0 - 0.3, XB0 + XIAO_L - 2.7], yy = [YB - XIAO_W/2 - 0.3, YB + XIAO_W/2 - 2.7])
        box(xx, yy, Z_FIN - 3, xx + 3, yy + 3, Z_FIN + 0.01);
      for (xx = [XB0 + 2, XB0 + XIAO_L - 8], yy = [YB - XIAO_W/2 - 1.5, YB + XIAO_W/2 + 0.3])
        box(xx, yy, Z_FIN - 3 - XIAO_T - 0.8, xx + 6, yy + 1.2, Z_FIN + 0.01);
      box(XB0 + XIAO_L + 0.3, YB - 5, Z_FIN - 3 - XIAO_T - 0.8, XB0 + XIAO_L + 1.5, YB + 5, Z_FIN + 0.01);
      // anelli cordino
      anello_corpo(0);  anello_corpo(1);
      // gocciolatoio sopra l'apertura della ricarica (+X = alto)
      if (APERTURA_RICARICA) gocciolatoio(BAT_CHG_X + CHG_W/2, CHG_ZC - CHG_H/2, Z_PI - 2);
    }
    anello_foro(0);  anello_foro(1);
    // fori pilota display
    for (h = DISP_FORI) translate([DISP_X0() + h[1], h[0], Z_DISP_T]) cylinder(d=VITE_PILOTA, h=Z_FIN - Z_DISP_T + 0.8);
    // fori pilota coperchio
    pad_fori(X0, 1, PILOTA_COP);  pad_fori(X1, -1, PILOTA_COP);
    // finestra + sede della lastrina (dietro, bordo sovrapposto davanti)
    translate([DISP_X0() + ACT_OFF_X - FINESTRA_M, DISP_Y0 + ACT_OFF_Y - FINESTRA_M, Z_FIN - 1])
      cube([ACT_L + 2*FINESTRA_M, ACT_W + 2*FINESTRA_M, FRONTE + 2]);
    translate([DISP_X0() + ACT_OFF_X - FINESTRA_M - POCKET_M, DISP_Y0 + ACT_OFF_Y - FINESTRA_M - POCKET_M, Z_FIN - 0.01])
      cube([ACT_L + 2*(FINESTRA_M + POCKET_M), ACT_W + 2*(FINESTRA_M + POCKET_M), SHEET_T + 0.01]);
    // ricarica del PowerPack (micro-USB sul lato Y basso)
    if (APERTURA_RICARICA) box(BAT_CHG_X - CHG_W/2, Y0 - PARETE - 1, CHG_ZC - CHG_H/2, BAT_CHG_X + CHG_W/2, Y0 + 1, CHG_ZC + CHG_H/2);
    // interruttore ON/OFF del PowerPack: feritoia sul fondo (-X) per la prolunga a pomello; drena anche l'acqua
    box(X0 - PARETE - 1, BAT_SW_Y - SLOT_W/2, SW_ZC - PRO_H/2 - 0.5, X0 + 1, BAT_SW_Y + SLOT_W/2, SW_ZC + PRO_H/2 + 0.5);
    // passaggio USB-C dello XIAO nella parete di separazione
    box(XPART0 - 1, YB - 7, Z_FIN - 11, XPART1 + 1, YB + 7, Z_FIN - 3);
    // prese d'aria con alette (basso: batteria; alto: Pi; mai sopra lo schermo)
    feritoie(68, 84, 4, BAT_H - 2, 0);
    feritoie(55, 82, Z_PI + PI_T + 2, Z_DISP_B - 2, 0);
    feritoie(8, 82, 4, BAT_H - 2, 1);
    feritoie(8, 82, Z_PI + PI_T + 2, Z_DISP_B - 2, 1);
  }
}

module coperchio() {
  cw = LI + 2 - GIOCO_COP;  cd = WI + 2 - GIOCO_COP;
  difference() {
    union() {
      translate([X0 - 1 + GIOCO_COP/2, Y0 - 1 + GIOCO_COP/2, -COPERCHIO_T]) cube([cw, cd, COPERCHIO_T]);
      // fermi del PowerPack (X)
      for (y = [4, 44]) { box(-1.8, y, 0, -0.4, y + 8, 6); box(BAT_L + 0.4, y, 0, BAT_L + 1.8, y + 8, 6); }
      // premischeda dello XIAO (da coprire con 1,5 mm di gommapiuma adesiva)
      box(XB0 + XIAO_L/2 - 4, YB - 4, 0, XB0 + XIAO_L/2 + 4, YB + 4, Z_FIN - 3 - XIAO_T - 1.5);
    }
    for (xw = [[X0, 1], [X1, -1]], y = PAD_Y) translate([xw[0] + xw[1]*3.5, y, -COPERCHIO_T - 0.01]) {
      cylinder(d=3.4, h=COPERCHIO_T + 0.02);
      translate([0,0,COPERCHIO_T - 1.6]) cylinder(d1=3.4, d2=6.2, h=1.62);
    }
  }
}

module fantasmi() {
  %translate([12,8,0]) cube([60,40,BAT_CELL]);                                   // cella (ingombro stimato)
  %translate([0,0,BAT_Z]) cube([BAT_L,BAT_W,BAT_PCB_T]);                        // scheda PowerPack
  %translate([3,0,BAT_Z+BAT_PCB_T]) cube([31,13,BAT_COMP_H]);                   // 2 USB-A
  %translate([0,0,Z_PI]) cube([PI_L, PI_W, PI_T]);
  %translate([DISP_X0(), DISP_Y0, Z_DISP_B]) cube([DISP_L, DISP_W, DISP_PCB_T + DISP_PANEL_T]);
  for (sx = [-1, 1]) %translate([DISP_X0() + DISP_L/2 + sx*DISP_FORI_L/2 - 5, YC - DISP_TAB_W/2, Z_DISP_B]) cube([10, DISP_TAB_W, DISP_PCB_T]);
  %translate([PI_HDMI_X - 10, -HDMI_U_OUT, Z_PI + PI_T]) cube([20, HDMI_U_OUT, GAP_PI_DISP]);   // adattatore HDMI a U
  %translate([XB0, YB - XIAO_W/2, Z_FIN - 3 - XIAO_T]) cube([XIAO_L, XIAO_W, XIAO_T]);
}

// prolunga: si infila da fuori nella feritoia; la forcella abbraccia la levetta, il pomello resta fuori
module prolunga() {
  xo = X0 - PARETE;                                         // faccia esterna della parete
  translate([0, BAT_SW_Y, SW_ZC - PRO_H/2]) {
    translate([xo - KNOB_X, -KNOB_Y/2, 0]) cube([KNOB_X - 0.3, KNOB_Y, PRO_H]);            // pomello
    translate([xo - 0.5, -PRO_W/2, 0]) cube([-SW_LEV_OUT - 0.3 - xo + 0.5, PRO_W, PRO_H]); // asta
    for (s = [-1, 1]) translate([-SW_LEV_OUT - 0.3, s > 0 ? FORK_GAP/2 : -FORK_GAP/2 - FORK_T, 0])
      cube([SW_LEV_OUT - 0.5 + 0.3, FORK_T, PRO_H]);                                     // forcella
    translate([-SW_LEV_OUT - 0.9, -FORK_GAP/2 - FORK_T, 0]) cube([0.61, FORK_GAP + 2*FORK_T, PRO_H]);
  }
}

if (PARTE == "assieme") { corpo(); color("orange") coperchio(); fantasmi(); color("red") prolunga(); }
else if (PARTE == "corpo") corpo();
else if (PARTE == "coperchio") translate([0,0,COPERCHIO_T]) coperchio();
else if (PARTE == "prolunga") translate([0,0,-(SW_ZC - PRO_H/2)]) prolunga();
else if (PARTE == "corpo_stampa") translate([0,0,Z_TOP]) rotate([180,0,0]) corpo();
