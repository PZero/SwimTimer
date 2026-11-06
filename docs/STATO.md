# Stato del progetto

**Ultimo aggiornamento:** 2026-11-06. Tutto il progetto è nel repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: ideazione/prototipo; ordine dei primi 20 tag in preparazione su NextPCB.

## Fotografia
- **Scheda v0.6 "Rev0"** (`hardware/nrf52840/kicad/swimtag_v06.*`): 4 strati 0,8 mm, 21,59 × 28,5 mm, senza BGA (NextPCB Rev0 rifiuta passo < 0,45 mm). MCP73831 (15 mA) al posto del BQ25101, TPS22917 al posto del TPS22916C, J1 DNP (la cella si salda a mano), D4 + R2 per CHG_N. DRC 0, ERC 0, 102 pin 0 differenze. Uscite in `nextpcb/v0.6/` (gerber, BOM, CPL, render, `assembly_pin1.png`, `NOTE_ORDINE.md`) e `jlc/v0.6_swimtag_v06/`.
- **v0.5** (2 strati, 28 mm, BQ25101 BGA) resta invariata come riferimento; pannelli 3×1 e 2×1 in `nextpcb/` rifiutati dal servizio Rev0 (niente file già pannellizzati).
- **Preventivo NextPCB Rev0 in carrello:** 20 pz (5 pannelli 2×2, V-cut richiesto dal pannello), PCB 71,49 $ + componenti 144,90 $ + SMT 252,89 $; coupon Rev0 −252,89 $ (solo SMT) → **216,39 $** (~10,8 $/tag) più spedizione e IVA di importazione. Consegna stimata 2026-11-12. Con 2 strati si risparmierebbero solo ~25–40 $ ma crescerebbe la scheda e servirebbe nuovo sbroglio: **si resta a 4 strati**.
- Anteprima componenti controllata uno per uno: U2, U3, D1 ruotati di 180° dall'utente, U4/U6/Q1/D2/D4 corretti, U1 solo baricentro (coperto da nota). Sostituzioni: D3 = Leiditech LC05CI; C2–C6 e R3 da annotare.
- **XIAO nRF52840 Sense** come tag di prova o definitivo: documentazione in `hardware/xiao/` (cella LP-401230 100 mAh, minimo 50 mA di carica, riavvio IMU via P1.08, sacchetto sottovuoto).
- Associazione nuotatore–tag con base di ricarica a slot + gettone NFC (decisione 2026-11-05); versione finale senza flash esterna (buffer RAM ~10 s, solo eventi).
- Prototipo ESP32-S3 + BMI160 (firmware 0.4.3, `tools/index.html`, display LilyGO T-RGB): funzionante sul tavolo, nessuna prova in vasca. Firmware nRF52840: da scrivere.
- README solo in inglese, senza ringraziamenti; `docs/` in italiano; da oggi commit e descrizione del repo in inglese.
- Video di presentazione in inglese (https://youtu.be/EVrdSybpnE4; `genera_video.py --lingua en`, testi in `media/video/testi_en.py`), linkato nel README; italiano https://youtu.be/_2UzpOqblVI.
- **Pagina `tools/index.html`, tab XIAO**: modellino 3D della XIAO orientato dall'IMU, calibrazione del montaggio sulla tempia destra (Calibra + Annuisci), mezzo busto wireframe con testa scansionata Lee Perry-Smith (CC BY 3.0, da CDN, ripiego procedurale), occhi rossi e testa che segue i movimenti; Demo testa. Montaggio fisso (destra, componenti verso l'esterno: niente scelte), vista frontale, occhi a griglia, interno della bocca nascosto, grafici acc/gyro in «Verifica assi». Provata solo con la demo.

## Prossimi passi
1. Aspettare il contatto di Viviane (NextPCB, programma sponsorizzazione); scadenza consigliata mercoledì 2026-11-11, poi ordinare o meno.
2. Prima di ordinare: incollare `NOTE_ORDINE.md` nelle note, scrivere a Shelly (V-cut e U1), leggere i termini "No Touch" del Rev0, annotare gli MPN scelti per C2–C6 e R3.
3. A schede arrivate: prova a banco (Q1, accensione a ~50 mA), REGOUT0 a 3,0 V (livello CHG_N 0,4 V contro VIL 0,54 V), costruire il programmatore, prova di portata antenna.
4. **XIAO in arrivo il 2026-11-07:** sketch Arduino minimo che manda il protocollo BLE 'SwimTag' (16 byte, 25 Hz, gyro scalato a 16,4 LSB/dps); poi in pagina «Verifica assi» (segno di Z, `XIAO_ASSE_USB`) e prova delle 3 fasi. Celle LP-401230 da ordinare.
5. Firmware: SPI, registrazione, sonno con INT dell'IMU, power-cycle dell'IMU (P1.08, SDA/SCL a 0), NFC/base a slot.
6. Prototipo ESP32: sessioni con video, prova in vasca. Versione inglese del video/miniatura (da confermare).
7. Cancellare a mano la cartella temporanea `C:\swt_chk`.

## Problemi aperti
- Rischio V-cut con componenti a 0,3–0,6 mm dal bordo (accettato con note a NextPCB); le note potrebbero essere ignorate nel Rev0.
- Livello CHG_N con D4 (1N4148WS) borderline a VDD 1,8 V; fix: REGOUT0 3,0 V o Schottky.
- Latch-up del BMI160 e riavvii del tag ESP32 a batteria; tap software poco affidabile.
- Brevetti (FORM US 11833392): verifica di libertà di operare per l'uso commerciale.
- Il BLE non attraversa l'acqua; custodia stagna da definire. Nessun test automatico.
- Zona antenna dell'E73 non quotata: prova di portata obbligatoria.

## Decisioni in attesa dell'utente
- Ordine NextPCB dopo Viviane; acquisto XIAO e celle; frequenza di registrazione; vibratore. Vedi `docs/DOMANDE-APERTE.md`.

## Riferimenti
- Scheda: `hardware/nrf52840/progetto.md`, `kicad/nextpcb/v0.6/NOTE_ORDINE.md`; XIAO: `hardware/xiao/README.md`; programmatore: `hardware/programmatore/README.md`.
- Prototipo: `hardware/bom.md`, `docs/LEZIONI-APPRESE.md`, `docs/RICERCA-ALGORITMI.md`.
