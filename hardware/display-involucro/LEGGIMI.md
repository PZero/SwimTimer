# Involucro del display (LilyGO T-RGB 2.8")

Modello parametrico: `involucro.scad` (OpenSCAD). Rendering in `render/`, file da stampare in `stl/`.

## Com'è fatto
- **Vaso** stampato, chiuso dietro. Il vetro del display si appoggia sul bordo del vaso (diametro esterno `D_BORDO` = 93,5 mm, spessore 5,5 mm per la scanalatura 6 × 7 mm del tappo) e il **tappo in silicone** lo stringe dall'alto.
- **Dentro:** due 18350 coricate sul fondo, sul lato che resta in alto quando è montato; una costola sulla parete opposta indica dove incollare l'antenna (lato verso l'acqua, lontano da pile e metallo). C'è spazio per una bustina di gel di silice.
- **Occhiello** per la cordina sul vaso, due fori passacorda nella base.
- **Inclinazione regolabile:** due perni dentati sui fianchi del vaso (pieni, la parete non è forata) e una forcella con i denti corrispondenti. Si stringe con 2 viti M5 × 25 (testa esagonale, dentro i pomelli stampati) e 2 dadi M5 infilati nelle tasche dei perni. Gli scatti sono di 15° (`DENTI` = 24), da 0° (display verticale) a 60° verso il basso.

## Stampa (Bambu A1 mini, PLA)
| Parte | File | Orientamento |
|---|---|---|
| Vaso | `stl/vaso.stl` | bocca in alto, senza supporti |
| Forcella | `stl/forcella.stl` | base sul piano |
| Pomello (×2) | `stl/pomello.stl` | come esportato |

Impostazioni: 5 perimetri, 6 strati sopra e sotto, strati da 0,2 mm, riempimento al 100 % su bordo, perni e bracci. Per la tenuta all'acqua, una mano di resina o vernice per plastica all'interno del vaso. Il PLA teme il caldo: non lasciarlo al sole o in auto.

## Da verificare alla prima stampa
- `DISP_CORPO` = 76 mm è **stimato dalla foto**: misurare il corpo del display dietro al vetro (deve stare in 82,5 mm).
- Calzata del tappo: se è lento o troppo duro, cambiare `D_BORDO` (93–94) e ristampare.
- Il tappo (112 mm) deve passare fra i bracci: margine di circa 3 mm per lato.

Rigenerare gli STL: `openscad -o stl/vaso.stl -D 'PARTE="vaso"' involucro.scad` (lo stesso per `forcella` e `pomello`).
