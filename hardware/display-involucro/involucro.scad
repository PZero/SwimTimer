// SwimTimer - involucro del display LilyGO T-RGB 2.8" (OpenSCAD, parametrico). Misure in mm.
// Vaso stampato chiuso dietro + tappo in silicone (esistente) davanti + forcella con snodo dentato (inclinazione regolabile).
// Il display (vetro) si appoggia sul bordo del vaso; il tappo calza sul bordo (scanalatura 6 x 7 mm) e lo stringe.
// Snodo: due perni dentati sui fianchi del vaso (pieni: la parete NON e' forata), dadi M5 imprigionati nei perni,
// viti M5 x 25 dalla forcella con pomello stampato. Scatti da 360/DENTI gradi.
// Parti da stampare: "vaso" (bocca in alto), "forcella" (base sul piano), "pomello" (x2).
// Stampa (A1 mini, PLA): 5 perimetri, 6 strati sopra/sotto, 0,2 mm, riempimento 100% su bordo, perni e bracci.
// Minuteria: 2 viti M5 x 25 a testa esagonale, 2 dadi M5, 2 rondelle M5.

PARTE = "assieme";           // "assieme", "vaso", "forcella", "pomello"
ALFA  = 30;                  // inclinazione del display verso il basso, solo per l'assieme (0..60)

// ---- misure prese (2026-11-11) ----
D_BORDO     = 93.5;   // diametro esterno del bordo del vaso (vetro originale 94; proposta 93): da provare 93..94
SCAN_LARG   = 6;      // larghezza della scanalatura del tappo
SCAN_PROF   = 7;      // profondita' della scanalatura del tappo
TAPPO_DMAX  = 112;    // diametro esterno massimo del tappo
TAPPO_D16   = 99;     // diametro esterno del tappo a 16 mm di altezza
DISP_VETRO  = 93;     // diametro del vetro (con l'anello adesivo 3M)
DISP_CORPO  = 76;     // corpo del display dietro al vetro: STIMATO dalla foto, da misurare
DISP_SPESS  = 10;     // spessore del solo display
DISP_TOT    = 18;     // display + elettronica + connettori
PILA_D      = 18.6;   // 18350
PILA_L      = 38;

// ---- scelte di progetto ----
PARETE   = 3;
BORDO_SP = SCAN_LARG - 0.5;          // spessore del bordo che entra nella scanalatura
BORDO_H  = SCAN_PROF + 1;
FONDO    = 3;
H        = FONDO + PILA_D + 3 + DISP_TOT + 1;   // altezza del vaso (bocca)
PERNO_D  = 24;        // perni dello snodo
PERNO_L  = 12;        // sporgenza dei perni dalla parete (il tappo da 112 deve passare fra i bracci)
PERNO_Z  = 13;        // quota dell'asse dei perni sul vaso (dietro al tappo)
DENTI    = 24;        // 15 gradi a scatto
DENTE_H  = 1.5;
BRACCIO  = 7;         // spessore dei bracci della forcella
GIOCO    = 0.5;
FORO_M5  = 5.5;
DADO_M5  = 8.4;       // apertura chiave del dado + gioco
FORO_CORDA = 5;

R  = D_BORDO / 2;
RI = R - PARETE;
Y_DENTI = R + PERNO_L;                             // faccia dentata del perno
Y_BRACCIO = Y_DENTI + DENTE_H + GIOCO;             // faccia interna del braccio
Z_ASSE = sqrt(pow(TAPPO_DMAX / 2, 2) + pow(H + 3.5 - PERNO_Z, 2)) + 4;   // asse alto abbastanza per ogni inclinazione
$fn = 120;

module dentatura(d) {         // denti radiali triangolari su una faccia (asse Z), altezza DENTE_H
  w = PI * d / DENTI;
  for (i = [0 : DENTI - 1]) rotate([0, 0, i * 360 / DENTI])
    rotate([90, 0, 90]) linear_extrude(d / 2 - 3) translate([0, 0]) polygon([[-w / 2, 0], [w / 2, 0], [0, DENTE_H]]);
}

// ================= vaso =================
module occhiello() {
  difference() {
    hull() { translate([-4, -3, 0]) cube([1, 6, 14]); translate([-11, 0, 7]) rotate([90, 0, 0]) cylinder(d = 14, h = 6, center = true); }
    translate([-11, 0, 7]) rotate([90, 0, 0]) cylinder(d = FORO_CORDA, h = 10, center = true);
  }
}
module culla_pile() {         // due 18350 coricate sul fondo, lato -X (in alto quando e' montato), lontano dall'antenna
  for (y = [-PILA_L / 2 + 6, PILA_L / 2 - 6])
    difference() {
      translate([-RI + 3, y - 2, FONDO]) cube([2 * PILA_D + 4, 4, PILA_D / 2]);
      for (x = [-RI + 5 + PILA_D / 2, -RI + 5 + 1.5 * PILA_D + 1])
        translate([x, 0, FONDO + PILA_D / 2]) rotate([90, 0, 0]) cylinder(d = PILA_D + 0.6, h = PILA_L + 10, center = true);
    }
}
module perno(s) {             // s = +1 / -1: lato Y. Pieno, con un piede a 45 gradi per stamparlo senza supporti
  mirror([0, s < 0 ? 1 : 0, 0]) difference() {
    union() {
      hull() {
        translate([0, R - 4, PERNO_Z]) rotate([-90, 0, 0]) cylinder(d = PERNO_D, h = PERNO_L + 4);
        translate([-PERNO_D / 2, R - 4, 0]) cube([PERNO_D, PERNO_L + 4, 1]);
      }
      translate([0, Y_DENTI, PERNO_Z]) rotate([-90, 0, 0]) dentatura(PERNO_D);
    }
    translate([0, R - 1, PERNO_Z]) rotate([-90, 0, 0]) cylinder(d = FORO_M5, h = PERNO_L + 5);           // foro della vite (non arriva alla parete)
    translate([-DADO_M5 / 2, Y_DENTI - 9, PERNO_Z - DADO_M5 / sqrt(3) / 1]) cube([DADO_M5, 4.4, 30]);      // tasca del dado, aperta in alto
  }
}
module vaso() {
  difference() {
    union() { cylinder(r = R, h = H); perno(1); perno(-1); }
    translate([0, 0, FONDO]) cylinder(r = RI, h = H - FONDO - BORDO_H - (BORDO_SP - PARETE));
    translate([0, 0, H - BORDO_H - (BORDO_SP - PARETE) - 0.01]) cylinder(r1 = RI, r2 = R - BORDO_SP, h = BORDO_SP - PARETE + 0.02);
    translate([0, 0, H - BORDO_H - 0.01]) cylinder(r = R - BORDO_SP, h = BORDO_H + 1);
    translate([0, 0, H - 0.6]) difference() { cylinder(r = R + 1, h = 1); cylinder(r = R - 0.6, h = 1); }
  }
  culla_pile();
  translate([-R + 0.5, 0, 0]) occhiello();
  translate([RI - 1.2, -12, H - DISP_TOT - 14]) cube([1.2, 24, 1.2]);              // costola guida per l'antenna (lato basso)
}

// ================= forcella =================
BASE_X = 90; BASE_Y = 2 * (Y_BRACCIO + BRACCIO) + 10; BASE_Z = 5;
module braccio(s) {
  mirror([0, s < 0 ? 1 : 0, 0]) difference() {
    union() {
      hull() {
        translate([-BASE_X / 2 + 10, Y_BRACCIO, 0]) cube([BASE_X - 20, BRACCIO, BASE_Z]);
        translate([0, Y_BRACCIO, Z_ASSE]) rotate([-90, 0, 0]) cylinder(d = PERNO_D + 4, h = BRACCIO);
      }
      translate([0, Y_BRACCIO, Z_ASSE]) rotate([90, 0, 0]) rotate([0, 0, 180 / DENTI]) dentatura(PERNO_D);
    }
    translate([0, 0, Z_ASSE]) rotate([-90, 0, 0]) cylinder(d = FORO_M5, h = 200);
  }
}
module forcella() {
  difference() {
    translate([-BASE_X / 2, -BASE_Y / 2, 0]) minkowski() { translate([4, 4, 0]) cube([BASE_X - 8, BASE_Y - 8, BASE_Z - 1]); cylinder(r = 4, h = 1, $fn = 32); }
    for (x = [-BASE_X / 2 + 9, BASE_X / 2 - 9]) translate([x, 0, -1]) cylinder(d = FORO_CORDA + 1, h = 10);   // passacorda / viti nel piano
  }
  braccio(1); braccio(-1);
}
module pomello() {
  difference() {
    union() { cylinder(d = 28, h = 10, $fn = 8); cylinder(d = 14, h = 14); }
    translate([0, 0, 3]) cylinder(d = 8.4 / cos(30), h = 20, $fn = 6);            // testa esagonale M5 (8 mm) incassata
    translate([0, 0, -1]) cylinder(d = FORO_M5, h = 20);
  }
}

// ================= elementi solo per il disegno =================
module tappo() {
  color("burlywood") rotate_extrude() polygon([
    [R + 0.2, H - 16], [TAPPO_DMAX / 2, H - 16], [TAPPO_DMAX / 2 - 1, H - 11], [TAPPO_D16 / 2, H + 0],
    [TAPPO_D16 / 2 - 2, H + 3.5], [DISP_VETRO / 2 - 6, H + 3.5], [DISP_VETRO / 2 - 7, H + 1.6], [R + 0.2, H + 1.6]]);
}
module display() {
  color([0.05, 0.05, 0.08]) translate([0, 0, H]) cylinder(d = DISP_VETRO, h = 1.5);
  color([0.6, 0.6, 0.62]) translate([0, 0, H - DISP_SPESS + 1.5]) cylinder(d = DISP_CORPO, h = DISP_SPESS - 1.5);
  color([0.1, 0.1, 0.1]) translate([0, 0, H - DISP_TOT + 1.5]) cylinder(d = 62, h = DISP_TOT - DISP_SPESS);
}
module pile() {
  color("royalblue") for (x = [-RI + 5 + PILA_D / 2, -RI + 5 + 1.5 * PILA_D + 1])
    translate([x, 0, FONDO + PILA_D / 2]) rotate([90, 0, 0]) cylinder(d = PILA_D, h = PILA_L, center = true);
}
module antenna() { color("gold") translate([RI - 2.2, -12, H - DISP_TOT - 12.8]) cube([1, 24, 8]); }

// asse dei perni = asse Y; il display guarda verso +X e in basso di ALFA gradi
module posa(a) { translate([0, 0, Z_ASSE]) rotate([0, 90 + a, 0]) translate([0, 0, -PERNO_Z]) children(); }
module assieme(a) {
  posa(a) { color("lightsteelblue") vaso(); tappo(); display(); pile(); antenna(); }
  color("darkseagreen") forcella();
  for (s = [-1, 1]) color("dimgray") translate([0, s * (Y_BRACCIO + BRACCIO), Z_ASSE]) rotate([s * -90, 0, 0]) pomello();
  color([0.85, 0.85, 0.8]) translate([-160, -100, -40]) cube([210, 200, 40]);          // bordo vasca
  color([0.55, 0.75, 0.95, 0.4]) translate([50, -100, -40]) cube([80, 200, 1]);        // acqua (indicativa)
}

if (PARTE == "vaso") vaso();
else if (PARTE == "forcella") forcella();
else if (PARTE == "pomello") pomello();
else assieme(ALFA);
