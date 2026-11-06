# Note per l'ordine NextPCB Rev0 – SwimTag v0.6 (20 pz, pannello 2×2)

Testo da incollare nelle note dell'ordine (o da mandare a Shelly), poi la lista di controllo per l'anteprima.

## Testo per le note (inglese)

```
SwimTag v0.6 – Rev0 PCBA, 4 layers 0.8 mm, ENIG, 5 panels 2x2 = 20 boards.

1. PANELIZATION: please use 2 mm gaps between boards in BOTH X and Y, with tab
   routing / mouse bites. NO V-cut: the module and other parts are within
   0.3-0.6 mm of the left and right board edges.

2. U1 (Ebyte E73-2G4M08S1C): the placement preview shows only a centroid marker,
   without the module outline. Please make sure that:
   - pin 1 is at the top-left corner, next to the white silkscreen dot;
   - the antenna end of the module faces the top edge of the board, over the
     copper-free keep-out area marked by the silkscreen outline;
   - the metal shield is on top (castellated pads down).
   Please confirm the U1 orientation with an image before assembly.

3. J1 (battery pads) is intentionally NOT assembled (DNP): I will solder the
   battery wires by hand.

4. D3: replaced with Leiditech LC05CI (bidirectional TVS, SOD-323), no polarity.

5. U2 (LSM6DSV16X, LGA-14) and U3 (W25Q128, SOIC-8): in the placement preview
   the pin-1 marker was at the BOTTOM-RIGHT; I rotated both by 180° in the
   preview. Pin 1 must be at the TOP-LEFT (pin-1 dot on the silkscreen).
   Please double-check these two parts.

   D1 (red LED KT-0603R): the preview showed the cathode at the bottom; I
   rotated it by 180°. The cathode must be at the TOP (pad 1, net LED_K),
   the anode at the bottom (VDD).

6. Please send me the component placement / orientation for approval before
   assembly. Polarized parts: U1, U2 (LGA-14), U3 (SOIC-8), U4 (SOT-23-5),
   U6 (SOT-23-6), Q1 (SOT-23), D1 (LED), D2, D4 (cathode = pad 1).

Thank you!
```

## Sostituzioni scelte su HQ Online

| Rif | Originale | Scelto | Note |
|---|---|---|---|
| D3 | PTVSLC3D5VB | **Leiditech LC05CI** | TVS bidirezionale 5 V, SOD-323: nessuna polarità |
| C2, C3, C4 | CL05B104KO5NNNC | _da annotare_ | 100 nF 0402, X7R/X5R, ≥ 16 V |
| C5, C6 | CL05A475MP5NRNC | _da annotare_ | 4,7 µF 0402, X5R, ≥ 10 V |
| R3 | 0402WGF1001TCE | _da annotare_ | 1 kΩ 0402 |

## Controllo dell'anteprima (riferimento: `assembly_pin1.png`)

| Rif | Atteso | Esito |
|---|---|---|
| U1 E73 | pin 1 in alto a sinistra, antenna verso il bordo alto (solo baricentro nell'anteprima) | in nota |
| U2 LGA-14 | pin 1 in alto a sinistra | ✅ dopo la rotazione di 180° fatta nell'anteprima |
| U3 SOIC-8 | pin 1 in alto a sinistra | ✅ dopo la rotazione di 180° fatta nell'anteprima |
| D2 | catodo a sinistra | ✅ (barra magenta a sinistra) |
| U4 SOT-23-5 | pin 1 (STAT) in alto a sinistra | ok a prima vista |
| U6 SOT-23-6 | pin 1 (VIN) in basso a sinistra | ok a prima vista |
| Q1 SOT-23 | pin 1 (gate) in basso a sinistra, pin singolo in alto | ok a prima vista |
| D1 LED | catodo in alto (pad 1 = LED_K) | ✅ dopo la rotazione di 180° fatta nell'anteprima |
| D4 | catodo a sinistra (pad 1 = CHG_STAT) | ✅ |
| D3 | bidirezionale (LC05CI) | nessuna polarità |

Altro: finitura ENIG, spessore 0,8 mm, rame interno 0,5 oz, Tented Vias; totale entro il coupon Rev0 da 500 $ (spedizione esclusa).
