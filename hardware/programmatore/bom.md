# Distinta componenti dell'adattatore HAT (v0.4)

Prezzi indicativi (novembre 2026), IVA e spedizione escluse. I link sono ricerche di catalogo: controllare codice e giacenza al momento dell'acquisto. Spedizioni dalla Cina (AliExpress, LCSC) 1-3 settimane; distributori europei (Mouser, Farnell, RS) 2-4 giorni.

| Q.ta | Riferimenti | Componente | Codice / tipo | Prezzo | Dove |
|---|---|---|---|---|---|
| 7 (+3 scorta) | P1-P7 | Pogo pin, testa a corona a 4 punte | **P75-E2** | ~2-3 EUR per 10 pz | [LCSC](https://www.lcsc.com/search?q=P75-E2), AliExpress "P75-E2 pogo pin" |
| 7 (+3 scorta) | P1-P7 | Ricettacolo a saldare per P75 | **R75-2W** (o R75-3S) | ~2 EUR per 10 pz | [LCSC](https://www.lcsc.com/search?q=R75-2W) |
| 1 | J1 | **Header femmina 2x20 (40 pin)**, passo 2,54 mm, altezza 8,5 mm, per HAT (non il "GPIO stacking" a code lunghe) | "Raspberry Pi 40 pin female header 2x20" | ~1-2 EUR | [LCSC](https://www.lcsc.com/search?q=female+header+2x20), Pimoroni, Adafruit |
| 4 | - | Distanziale M2,5 femmina-femmina, **11 mm** | kit distanziali M2,5 | ~3 EUR (kit) | AliExpress / Amazon |
| 4 + 4 | - | Viti M2,5 x 6 (e dadi/viti per il lato Pi se si vuole fissare) | kit viti M2,5 | ~1 EUR | ferramenta |
| 1 | - | Basetta FR4 1,6 mm, rame su una faccia, 100 x 160 mm (ne ricavi 2) | normale, non fotosensibile | ~4-6 EUR | AliExpress / Amazon "single side copper clad 100x160" |
| 1 striscia | JP1 (3), J2 (2), J3 (2), J4 (1), battute S1-S3 (3 pin) | Header maschio 1x40, passo 2,54 mm | generico | ~0,5 EUR | [LCSC](https://www.lcsc.com/search?q=pin+header+1x40) |
| 2 (+1) | JP1, J3 | Ponticello (jumper cap) 2,54 mm | generico | ~0,3 EUR | come sopra |
| 4 | R1-R4 | Resistenza 1 kohm 1/4 W 5 %, foro passante | generica | ~0,1 EUR | qualsiasi |
| 1 | D1 | LED verde 3 mm, foro passante | generico | ~0,1 EUR | qualsiasi |
| 1 | F1 | PTC radiale, hold 0,1 A, passo 5,08 mm | es. Bourns MF-R010 o Littelfuse RXEF010 | ~0,4 EUR | [Mouser](https://www.mouser.it/c/?q=PTC%20100mA%20radial), Farnell |
| 3 | S4-S6 | Blocchetto 2,54 x 2,54 x 2,5 mm (corpo di plastica di un header senza pin) per gli appoggi del tag | ricavato da un header | - | cianoacrilico o biadesivo |
| - | - | Carta lucida (rivista patinata o carta fotografica glossy), persolfato di sodio o cloruro ferrico, punte 0,8 / 1,0 / 1,5 / 2,75 mm | consumabili | ~10-15 EUR | negozi di elettronica / AliExpress |

Totale: circa 25-30 EUR di componenti piu' 10-15 EUR di consumabili. Rispetto alla versione a cavetti dupont: **eliminati** J1 a 4 pin, J5 e i cavetti, il morsetto a vite J2 (sostituito da un header 1x2 +5V esterno/GND); **aggiunti** header femmina 2x20 e 4 distanziali da 11 mm.

**Pogo, due alternative a confronto.** P75-E2 + R75 (scelto): richiesto, comunissimo, molla robusta; il foro del ricettacolo e' ~1,5 mm e lascia 0,25 mm di rame intorno (piazzola ovale 2,0 x 3,2 mm). P50 + R50: foro ~1,0 mm (anello 0,5 mm, piu' facile a mano) ma molla piu' debole e punta piu' fragile. Se il foro da 1,5 mm strappa il rame, passare a P50/R50 cambiando `FORO_POGO` in `modello.py` e rigenerando. **Diametro esterno del ricettacolo, corsa e forza vanno verificati sul datasheet del venditore o con il calibro sul pezzo arrivato** (i dati online sono discordi: corpo 1,0-1,3 mm, lunghezza 16,5 mm, corsa totale ~2,5 mm, 3 A).

**Connettore: scelta.** Header femmina 2x20 completo (40 pin, non un pezzo da 11-12 pin): non puo' scorrere di una posizione sul connettore del Pi, e insieme ai 4 fori M2,5 dell'HAT l'innesto avviene in un solo verso. Alternativa scartata: header femmina parziale 1x6 sui soli pin pari (meno costoso ma innestabile sfalsato).
