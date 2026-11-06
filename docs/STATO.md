# Stato del progetto

**Ultimo aggiornamento:** 2026-11-06. Tutto il progetto è nel repository unico e pubblico `PZero/SwimTimer` (`main`). Fase: ideazione/prototipo; ordine dei primi 20 tag in preparazione su NextPCB; mockup del display a bordo vasca in corso.

## Fotografia
- **Scheda v0.6 "Rev0"** (`hardware/nrf52840/kicad/swimtag_v06.*`): 4 strati 0,8 mm, 21,59 × 28,5 mm, senza BGA. MCP73831 (15 mA), TPS22917, J1 DNP, D4 + R2 per CHG_N. DRC 0, ERC 0. Uscite in `nextpcb/v0.6/` (con `NOTE_ORDINE.md`) e `jlc/v0.6_swimtag_v06/`. La v0.5 resta come riferimento.
- **Preventivo NextPCB Rev0 in carrello:** 20 pz (5 pannelli 2×2, V-cut), **216,39 $** con coupon (~10,8 $/tag) più spedizione e IVA; consegna stimata 2026-11-12. Si resta a 4 strati. Anteprima componenti controllata; D3 = LC05CI; C2–C6 e R3 da annotare.
- **XIAO nRF52840 Sense** come tag di prova o definitivo: `hardware/xiao/` (cella LP-401230 100 mAh, minimo 50 mA di carica, riavvio IMU via P1.08).
- Associazione nuotatore–tag con base di ricarica a slot + gettone NFC; versione finale senza flash esterna (buffer RAM ~10 s, solo eventi).
- **Display a bordo vasca (architettura proposta, da confermare):** Raspberry Pi 4 + dongle USB nRF52840 + monitor portatile 15,6" + power bank PD, Wi-Fi spento, programma nativo; ~13 W, 2 h a batteria; fino a 10 tag in connessione. Il tag manda eventi col proprio orario e li tiene finché il display conferma.
- **Mockup `tools/display.html`** (solo HTML, UI in inglese): cronometro grande che riparte al primo nuotatore di ogni segmento con la durata del giro precedente in grigio; una riga per nuotatore con colore, stato (Swimming/Rest/Waiting/Done), tempo in corso, ultimo tempo, passo e parziali, **Effort 1–10** dell'ultimo segmento e storico degli ultimi 10 (il nuovo lampeggia 5 s e gli altri slittano a destra). Segmenti generici, vasca 25/50 m. Demo: 7 nuotatori, riscaldamento, tecnica, 3×(300 + 4×100), defaticamento, con la fase mostrata sotto la data. Provato solo nel browser.
- Prototipo ESP32-S3 + BMI160 (firmware 0.4.3, `tools/index.html`, LilyGO T-RGB): funzionante sul tavolo, nessuna prova in vasca. Firmware nRF52840: da scrivere.
- **Pagina `tools/index.html`, tab XIAO:** modellino 3D orientato dall'IMU, calibrazione sulla tempia destra, testa scansionata (CC BY 3.0), cuffia arancione facoltativa. Provata solo con la demo.
- README solo in inglese; `docs/` in italiano; commit in inglese. Video: https://youtu.be/EVrdSybpnE4 (en), https://youtu.be/_2UzpOqblVI (it).

## Prossimi passi
1. Aspettare il contatto di Viviane (NextPCB); scadenza consigliata mercoledì 2026-11-11, poi ordinare o meno. Prima: incollare `NOTE_ORDINE.md`, scrivere a Shelly (V-cut e U1), leggere i termini "No Touch", annotare gli MPN per C2–C6 e R3.
2. **XIAO in arrivo il 2026-11-07:** sketch Arduino con il protocollo BLE 'SwimTag' (16 byte, 25 Hz); poi «Verifica assi» e prova delle 3 fasi. Celle LP-401230 da ordinare.
3. **Display:** confermare l'architettura Pi + dongle e far preparare la distinta; scegliere il test per l'Effort; decidere il ricevitore al muro opposto (vasca da 50 m); collegare `ricevi()` a una sorgente BLE reale; incorporare i font per l'uso offline.
4. A schede arrivate: prova a banco (Q1, ~50 mA), REGOUT0 a 3,0 V, programmatore, prova di portata antenna.
5. Firmware: SPI, registrazione, sonno con INT dell'IMU, power-cycle dell'IMU, NFC/base a slot, eventi con orario e conferma.
6. Prototipo ESP32: sessioni con video, prova in vasca. Cancellare a mano `C:\swt_chk`.

## Problemi aperti
- Rischio V-cut con componenti a 0,3–0,6 mm dal bordo (note a NextPCB forse ignorate nel Rev0).
- Livello CHG_N con D4 borderline a VDD 1,8 V; fix: REGOUT0 3,0 V o Schottky.
- Latch-up del BMI160 e riavvii del tag ESP32 a batteria; tap software poco affidabile.
- Brevetti (FORM US 11833392): verifica di libertà di operare prima di vendere.
- Il BLE non attraversa l'acqua e in vasca da 50 m non arriva al muro opposto al display; custodia stagna da definire. Nessun test automatico.
- Zona antenna dell'E73 non quotata: prova di portata obbligatoria. Monitor ~300 nit: non leggibile al sole.
- Effort provvisorio: scala 1–10 tarata a occhio, test di riferimento da concordare.

## Decisioni in attesa dell'utente
- Ordine NextPCB dopo Viviane; acquisto XIAO e celle; architettura del display (Pi + dongle + monitor); test per l'Effort; ricevitore al muro opposto. Vedi `docs/DOMANDE-APERTE.md` (33–35).

## Riferimenti
- Scheda: `hardware/nrf52840/progetto.md`, `kicad/nextpcb/v0.6/NOTE_ORDINE.md`; XIAO: `hardware/xiao/README.md`; programmatore: `hardware/programmatore/README.md`.
- Prototipo: `hardware/bom.md`, `docs/LEZIONI-APPRESE.md`, `docs/RICERCA-ALGORITMI.md`. Display: `tools/display.html`.
