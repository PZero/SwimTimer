# SwimTimer

Automatic lap times in the pool: a tag under the swim cap and a poolside display detect start and finish, with no buttons.

![Status](https://img.shields.io/badge/status-ESP32%20prototype%20working-yellow) ![Board](https://img.shields.io/badge/nRF52840%20tag-v0.6%20Rev0%20ready%20for%20preview-green) ![Repository](https://img.shields.io/badge/repository-public-blue) ![License](https://img.shields.io/badge/license-to%20be%20defined-lightgrey)

Updated on **2026-11-06**. Single public repository `PZero/SwimTimer`: ESP32 prototype, firmware, analysis web page (GitHub Pages: https://pzero.github.io/SwimTimer/), nRF52840 tag (KiCad, Gerber, JLCPCB and NextPCB files), programmer HAT, technical wallpapers and video.

> **Language.** This README is in English. Internal working documents in [`docs/`](docs/) (state, decisions, requirements, design) are written in Italian.

### Presentation video (2 minutes)

[![SwimTimer: presentation video on YouTube](media/video/miniatura_youtube_en.png)](https://youtu.be/EVrdSybpnE4)

Watch it on YouTube: **https://youtu.be/EVrdSybpnE4** (Italian version: https://youtu.be/_2UzpOqblVI; original music generated for the video; sources in [`media/video/`](media/video/)).

![Render of the v0.6 Rev0 tag, top view](hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/render_sopra.png)

## Table of contents
- [What is SwimTimer](#what-is-swimtimer)
- [Current status](#current-status)
- [System architecture](#system-architecture)
- [ESP32 prototype, firmware 0.4.3 and analysis page](#esp32-prototype-firmware-043-and-analysis-page)
- [nRF52840 tag](#nrf52840-tag)
- [XIAO nRF52840 Sense test tags](#xiao-nrf52840-sense-test-tags)
- [External reviews](#external-reviews-v04)
- [Programmer HAT for Raspberry Pi 3/4](#programmer-hat-for-raspberry-pi-34)
- [Planned features and ideas](#planned-features-and-ideas)
- [Technical wallpaper gallery](#technical-wallpaper-gallery)
- [Repository structure](#repository-structure)
- [How to regenerate the files](#how-to-regenerate-the-files)
- [Ordering flow: JLCPCB and NextPCB](#ordering-flow-jlcpcb-and-nextpcb)
- [Roadmap and open issues](#roadmap-and-open-issues)
- [Privacy and security](#privacy-and-security)
- [License and author](#license-and-author)

## What is SwimTimer

**Problem.** In the pool, lap times and rests get lost. Looking at a watch or pressing a button interrupts the workout.

**Solution.** A small tag with an inertial sensor (accelerometer and gyroscope) is worn under the swim cap. It detects the wall push-off (start), the turns and the stillness at the finish on its own. A poolside display shows the times.

**Physical constraint.** 2.4 GHz BLE does not travel through water. Time is not measured with the radio signal: the sensor on the tag decides. BLE is used only out of the water, to detect proximity to the display and to transfer data. Full feasibility analysis: [`docs/IDEA.md`](docs/IDEA.md) (in Italian).

## Current status

| Area | Status |
|---|---|
| ESP32-S3 + BMI160 prototype, firmware **0.4.3**, analysis page | Working on the bench; no pool tests yet |
| LilyGO T-RGB display (4-hand pace clock) | Working on the bench |
| nRF52840 tag **v0.5 "economy"** | Ready: 21.59 x 28.0 mm, 2 layers, DRC 0, ERC 0 errors, `verifica_v05.py` 100/100 pins. JLCPCB files plus NextPCB files (single board and 3x1 / 2x1 panels); JLC placement preview checked, Q1 and U6 rotations fixed (commit `dea9744`) |
| nRF52840 tag **v0.6 "Rev0"** (new) | 4 layers 0.8 mm, 21.59 x 28.5 mm, no BGA (NextPCB Rev0 rejects pitch below 0.45 mm). Files generated; JLC rotations of the new SOT-23 parts still to verify in a JLC preview |
| XIAO nRF52840 Sense test tags | Bill of materials and procedure written ([`hardware/xiao/README.md`](hardware/xiao/README.md)); not yet ordered |
| Order | **Not placed yet**: preview, finish choice (HASL/ENIG), DFM ticket and cost decision pending |
| nRF52840 tag firmware | To be written (Zephyr / nRF Connect SDK) |
| Programmer HAT for Raspberry Pi 3/4 | Designed, regenerated on v0.5 (TP1-TP7 unchanged), DRC 0; **not built yet** |

## System architecture

```mermaid
flowchart LR
  subgraph TAG[Tag under the swim cap]
    IMU[6-axis IMU] -- SPI --> MCU[nRF52840 / ESP32-S3<br/>BLE]
    FL[Flash] -- SPI --> MCU
    CEL[LiPo cell] --> MCU
  end
  MCU -- "BLE advertising (out of the water)" --> DSP[Poolside display<br/>LilyGO T-RGB 2.8 inch]
  MCU -- "GATT / OTA (out of the water)" --> WEB[Analysis page<br/>Web Bluetooth]
  MCU -. "flash recording,<br/>downloaded later" .-> WEB
  DSP -- "pace clock, times" --> SWI[Swimmer]
  CHG[Charging base / programmer] -- "contacts under the tag" --> TAG
```

- **Tag.** Under the cap, pressed against the skull. It decides START, turns and STOP on its own using the IMU and logs raw data to flash.
- **Poolside display.** Receives the tag's BLE advertisements without connecting. Shows a 4-hand pace clock. Goes to sleep after 5 minutes without a tag.
- **Web page.** `tools/index.html`: live data, recordings, calibration, firmware update over Bluetooth.
- **BLE out of the water.** Underwater the signal disappears within a few centimetres: during the swim the tag works alone and hands over its data when the swimmer emerges or at the end of the session.

## ESP32 prototype, firmware 0.4.3 and analysis page

The prototype is used to tune the algorithms before the custom board exists.

**Tag (prototype).** ESP32-S3 SuperMini + BMI160 (GY-BMI160), LiPo with main switch. Bill of materials: [`hardware/bom.md`](hardware/bom.md). Wiring: [`hardware/schema.md`](hardware/schema.md) (both in Italian).

**Firmware 0.4.3** (`firmware/test-collegamenti`, arduino-cli, core `esp32:esp32` 3.3.12):
- +/-16 g and 100 Hz, set with the sensors on and read back (up to 5 attempts);
- flash with two program copies and about 1.9 MB of LittleFS (about 40 minutes at 50 Hz);
- double tap = start recording, triple tap = stop (software detection, unreliable: about 1 in 10);
- BLE with data, status, commands, OTA and version; the same commands over USB; Bluetooth update with automatic rollback to the previous version;
- automatic I2C bus recovery, RGB LED feedback, last reset reason, voltage dividers on GPIO 1 (battery) and GPIO 2 (5V pin).

**Analysis page** [`tools/index.html`](tools/index.html), online at <https://pzero.github.io/SwimTimer/> (GitHub Pages of the **public** repository, firmware 0.4.3 published):
- "Live" tab (battery, 3D orientation, radar with 15 s trail, interpretation, events, charts) and "Recordings" tab;
- automatic calibration, Firmware and LED windows, Demo mode;
- Bluetooth (Chrome, Edge, Bluefy on iPhone) or USB;
- battery card with GPIO 1, GPIO 2 and estimated resting voltage charts.
- "XIAO" tab: 3D XIAO model oriented live by the IMU; head-mounting calibration (right temple, Calibra / Annuisci buttons); wireframe half-bust whose head follows the movements (red eyes at start), Ricentra, Demo testa and axis check. It waits for a XIAO sketch that sends the same `SwimTag` BLE protocol.
- Head model: scan by Lee Perry-Smith (Infinite-Realities), licensed CC BY 3.0, loaded from the three.js CDN; neck and shoulders are procedural.

`tools/assi.html` is the old 3-axis page, kept for reference.

**Display** (`firmware/display-prova`): LilyGO T-RGB 2.8 inch, PlatformIO with espressif32 6.9.0, driver copied and adapted in `src/trgb/` (MIT license, Xinyuan-LilyGO).

**Build and upload the tag firmware:**
```
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc --upload -p <COM> firmware/test-collegamenti
```

Related documents (in Italian): [`docs/RICERCA-ALGORITMI.md`](docs/RICERCA-ALGORITMI.md) (algorithm research), [`docs/LEZIONI-APPRESE.md`](docs/LEZIONI-APPRESE.md) (13 prototype lessons for the miniaturised board), [`docs/REQUISITI.md`](docs/REQUISITI.md) (requirements), [`docs/DESIGN.md`](docs/DESIGN.md) (design).

## nRF52840 tag

**Goal.** Replace the prototype with a miniature tag for the swim cap, assembled by the fab, with contact charging and programming through pads on the underside. Design document: [`hardware/nrf52840/progetto.md`](hardware/nrf52840/progetto.md) (Italian).

### Version history

| Version | Date | Board | Content | Outcome |
|---|---|---|---|---|
| v0.1 | 2026-10-25 | 17.5 x 20.5 mm, 4 layers | Raytac MDBT50Q, LSM6DSV16X, MS5837, 32 MB flash, BQ25101, vibration motor | Superseded |
| v0.2 | 2026-10-25 | 17.5 x 22.5 mm, 4 layers | Added TVS, Schottky and reset on insertion into the case; DRC 0 | Historical |
| v0.3 test (1c) | 2026-11-01 | 26 x 30 mm, 4 layers 0.8 mm | Ebyte E73 (Raytac out of stock), TPS22916C, MAX17048, Ampul 401012 cell on JST SH, Tag-Connect, test pads; motor not fitted; DRC 0, 609 tracks, 80 vias | Ready, never ordered (~120-130 USD) |
| v0.4 economy | 2026-11-02 | 22.86 x 26 mm, 2 layers | IMU recording only, budget <= 100 EUR: removed pressure sensor, MAX17048, TPS22916C, motor, Tag-Connect, TVS; 16 MB flash | Compacted |
| v0.4 compacted | 2026-11-03 | **21.59 x 26 mm**, 2 layers | 0603 *basic* LED with anode on VDD, pinout changed, DRC 0, JLC files regenerated | Verified (65 tests, 0 blocking) |
| v0.5 economy | 2026-11-04 | **21.59 x 28.0 mm**, 2 layers | TPS22916C on VDD_IMU, TVS, AO3401A against reversed cell, 100 kOhm VIN-GND, TP8, IMU_MISO/CS on P0.08/P0.12; DRC 0, ERC 0 | **Ready**, not ordered; 2026-11-05: Q1 and U6 rotations fixed after the JLC preview (`dea9744`) |
| v0.6 "Rev0" | 2026-11-06 | **21.59 x 28.5 mm**, 4 layers 0.8 mm | No BGA: MCP73831 (SOT-23-5) instead of BQ25101, TPS22917 (SOT-23-6) instead of TPS22916C; J1 not assembled | **Files generated**, JLC rotations to verify |

### v0.6 "Rev0" (new)

Project `kicad/swimtag_v06.*` (`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`), data in `kicad/dati_v06.py`, positions in `kicad/posizioni_v06.py`. v0.5 stays unchanged.

**Why.** The NextPCB Rev0 service rejects BGA parts with pitch below 0.45 mm (the BQ25101 DSBGA is 0.4 mm). v0.6 removes all BGA parts.

| Change vs v0.5 | Detail |
|---|---|
| Charger | **MCP73831T-2ACI/OT** (SOT-23-5) replaces the BQ25101; PROG 66.5 kOhm = **15 mA**; STAT drives CHG_N through a 1N4148WS (D4) with a 100 kOhm pull-up |
| Load switch | **TPS22917DBVR** (SOT-23-6) replaces the TPS22916C (U6), still on VDD_IMU with ON on P0.04 |
| Stack-up | **4 layers, 0.8 mm**, In1 = ground plane |
| Size | **21.59 x 28.5 mm** |
| J1 | Not assembled (DNP): the battery wires are soldered by hand to the J1 pads |

**Files.**
- Gerber, BOM and CPL for JLCPCB: `hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/` (also `schema.pdf` and renders).
- NextPCB: `hardware/nrf52840/kicad/nextpcb/v0.6/` (`bom_nextpcb.csv/.xlsx`, `cpl_nextpcb.csv`, `centroid_nextpcb.xlsx/.zip`, `swimtag_gerber.zip`, `assembly_top_render.png`, `assembly_pin1.png` with the pin-1 markers).
- Verification script: `kicad/verifica_v06.py`; assembly drawing: `kicad/disegno_montaggio_v06.py`.

**Still to do.** Check in a JLC preview the rotations of the new SOT-23 parts (MCP73831, TPS22917, D4), then order.

### NextPCB files for v0.5

NextPCB is the alternative to JLCPCB for the v0.5 board (2 layers). Files in `hardware/nrf52840/kicad/nextpcb/`:

| Folder | Content |
|---|---|
| `v0.5/` | Single board: Gerber zip, BOM, CPL, centroid, assembly render |
| `v0.5_pannello_3x1/` | 3 x 1 panel: `pannello_3x1.kicad_pcb`, Gerber, BOM, CPL, DRC report |
| `v0.5_pannello_2x1/` | 2 x 1 panel: same files |

Panels use **mouse bites** (no V-cut). **J1 is not assembled**: the user solders the battery wires to the J1 pads. Panels are built with `kicad/crea_pannelli.py`; the NextPCB export is `kicad/esporta_nextpcb.py`.

### v0.5 in detail

v0.5 derives from v0.4 with the changes decided after the [external reviews](#external-reviews-v04). Read first the "Revisione v0.5" block in [`hardware/nrf52840/progetto.md`](hardware/nrf52840/progetto.md). v0.4 is **historical**: frozen files in `kicad/jlc/v0.4_swimtag_economica/`, regenerable from commit `8fd6cc0`.

**Dimensions.** **21.59 x 28.0 mm**, 2 layers, 0.8 mm, 25 components per board, 369 tracks, 36 vias. At 26-27.5 mm the 2-layer routing does not complete (0.4 mm BGA of the BQ25101 and the IMU MISO line). Finished tag about 25 x 31 mm with resin.

**Changes vs v0.4:**

| Ref. | Change | LCSC | JLC type |
|---|---|---|---|
| U6 | TPS22916C: VDD -> VDD_IMU for the IMU, ON on P0.04 (`SENS_ON`) with R7 1 MOhm; R6 (CS pull-up) on VDD_IMU | C2680319 | extended |
| C5 | 4.7 uF 10 V at the BQ25101 input (was 10 uF 6.3 V) | C23733 | basic |
| C6, C7 | C6 4.7 uF 10 V on VBAT, C7 removed | C23733 | basic |
| R8 | 100 kOhm between VIN and GND: no electrolysis between the contacts in water | C25741 | basic |
| D3 | Bidirectional TVS PTVSLC3D5VB on the VIN contact, before D2 | C41408025 | extended |
| Q1, R9 | AO3401A against reversed cell, gate to GND with 100 kOhm | C15127 | basic |
| TP8 | `VDD_IMU` pad, 0.8 mm dia., underside, at (17.78; 12.70) mm | copper only | |

Other changes: IMU_MISO on P0.08 (pad 16) and IMU_CS on P0.12 (pad 20), so XL1/XL2 stay free; 1.0 mm silkscreen; track-free zone on F.Cu at the centre under the module. Pads TP1-TP7 keep the v0.4 coordinates: the programmer HAT remains valid. To test on the bench: Q1 with the cell connected correctly and reversed.

**Checks.** DRC 0 errors and 0 warnings, 0 unconnected, schematic/PCB parity 0, ERC 0 errors (41 harmless `pin_to_pin` warnings from the generated symbols), 28 nets, `kicad/verifica_v05.py`: 100 expected pins out of 100, 0 differences.

**v0.5 pinout changes** (the rest is as in the v0.4 table below):

| E73 pad | GPIO | Net |
|---|---|---|
| 16 | P0.08 | IMU_MISO |
| 20 | P0.12 | IMU_CS (R6 100 kOhm to VDD_IMU) |
| 18 | P0.04 | SENS_ON (R7 1 MOhm to GND) |

P0.00/P0.01 (XL1/XL2) are free; LFCLK stays on the RC oscillator.

#### v0.5 costs
Estimate from the real JLC cart of 2026-11-03 (v0.4, 128.46 EUR), recomputed and not rebuilt in the cart. Standard PCBA assembly is mandatory (E73, IMU, BQ25101). **About 125 EUR with X-ray and coupons, above the 100 EUR cap** (ENIG: +5-10 EUR).

| Cut (cumulative) | Estimated total |
|---|---|
| None (full v0.5, X-ray, coupon) | ~125 EUR |
| No X-ray (risk on unverified BGA/LGA) | ~109 EUR |
| + no TVS D3 | ~105 EUR |
| + no J1 header (wires on pads) | ~100.5 EUR |

All of these give up protection or checks: the user decides. Cell, programmer and pogo pins are excluded.

**Check in the JLC preview:** rotations of U6, Q1, D1, D3, J1 (and U2, U4, D2); the TPS22916C is probably "Standard only". Q1 and U6 were already corrected on 2026-11-05 (`dea9744`).

### v0.4 in detail (historical)

**Purpose.** Two prototypes to record raw IMU data and tune the filters, at minimum cost. Data in `kicad/dati_economica.py`, positions in `kicad/posizioni_economica.py`, dimensioned drawing in [`hardware/nrf52840/ingombro_v0.4.svg`](hardware/nrf52840/ingombro_v0.4.svg).

**Dimensions.** Board **21.59 x 26.0 mm** (8.5 pitches of 2.54 mm), **2 layers**, 0.8 mm, components on top only, 313 tracks, 29 vias. Finished tag about 25 x 29 mm with 1.5 mm of resin. At 20.32 mm the 2-layer routing does not complete (about 100 Freerouting runs, never DRC 0).

**Components (LCSC codes):**

| Function | Component | LCSC | JLC type |
|---|---|---|---|
| Microcontroller and BLE | Ebyte E73-2G4M08S1C (nRF52840), VDDH from the cell, REGOUT0 at 3.3 V from UICR | C356849 | extended |
| 6-axis IMU | ST LSM6DSV16X, SPI with INT1/INT2 | C5267406 | extended |
| 16 MB flash | Winbond W25Q128JVSIQ, SOIC-8, plain SPI | C97521 | basic |
| Charger | TI BQ25101 (TS 10 kOhm to ground, ISET 10 kOhm = 13.5 mA) | C478468 | extended |
| LED | KT-0603R red, anode on VDD | C2286 | basic |
| Charge protection | 1N5819WS Schottky in series with the contacts | C191023 | basic |
| Cell | 1.27 mm 1 x 2 SMD header (wires soldered to the cell) | C55213900 | extended |
| Passives | 6 resistors, 7 capacitors | see `bom_jlc.csv` | basic |

Full bill of materials and rotations: `hardware/nrf52840/kicad/jlc/v0.4_swimtag_economica/` (`bom_jlc.csv`, `cpl_jlc.csv`). Other alternatives considered (WSON flash, JST SH, NTC): [`hardware/nrf52840/progetto.md`](hardware/nrf52840/progetto.md).

**Underside, 2.54 mm grid** (perfboard and pogo pins):

| Pad | Net | x (mm) | y (mm) | Dia. |
|---|---|---|---|---|
| TP1 | VDD (reference only) | 5.08 | 12.70 | 2.0 |
| TP2 | SWDIO | 7.62 | 12.70 | 2.0 |
| TP3 | SWDCLK | 10.16 | 12.70 | 2.0 |
| TP4 | RESET | 12.70 | 12.70 | 2.0 |
| TP5 | GND | 15.24 | 12.70 | 2.0 |
| TP6 | VIN (charge) | 7.62 | 17.78 | 2.5 |
| TP7 | GND (charge) | 12.70 | 17.78 | 2.5 |

Coordinates from the top-left corner (antenna side), board seen from above. Silkscreen ticks every 2.54 mm on the left and top edges.

**Pinout for the firmware** (all signals at 3.3 V after REGOUT0). Full table in [`hardware/nrf52840/verifica_v0.4.md`](hardware/nrf52840/verifica_v0.4.md), section 3 (Italian).

| E73 pad | GPIO | Net | Notes |
|---|---|---|---|
| 11 | P0.00 | IMU_CS | R6 100 kOhm to VDD; pin XL1: **LFCLK not from XTAL** |
| 13 | P0.01 | IMU_MISO | pin XL2 |
| 15 | P0.05 | IMU_MOSI | |
| 17 | P1.09 | IMU_SCK | SPI up to 8 MHz |
| 12 | P0.26 | IMU_INT1 | |
| 14 | P0.06 | IMU_INT2 | |
| 30 | P0.17 | FL_CS | R5 100 kOhm to VDD |
| 28 | P0.15 | FL_MISO | |
| 33 | P0.13 | FL_MOSI | |
| 35 | P0.24 | FL_SCK | /WP and /HOLD high: plain SPI only |
| 32 | P0.20 | CHG_N | internal pull-up; low = charging |
| 34 | P0.22 | LED | active low, about 1.4 mA |
| 26 | P0.18 | RESET | after writing `UICR.PSELRESET` |
| 37 / 39 | SWDIO / SWDCLK | SWD | pogo TP2 / TP3 |
| 23 | VDDH | VBAT | battery with SAADC channel `VDDHDIV5`, no divider |

This is the v0.4 pinout: in v0.5 IMU_CS and IMU_MISO change and SENS_ON is added (see above). UICR registers to write once over SWD: `REGOUT0` (0x10001304) = `0xFFFFFFFD` (3.3 V), `PSELRESET[0]` and `[1]` (0x10001200 / 0x10001204) = `0x12`.

**Main choices.**
- **16 MB flash** SOIC-8 *basic*: 4.93 USD for 2 boards versus 9.83 USD for the WSON. Duration: about 24 minutes at 960 Hz (six axes, 16 bit), about 97 minutes at 240 Hz, about 3 hours at 120 Hz.
- **0603 *basic* LED** with anode on VDD: saves 3.07 USD of extended loading fee and injects no current into the pin at first power-up (VDD at 1.8 V with empty UICR).
- **1.27 mm SMD header** instead of JST SH: 10.4 vs 26.6 mm², cheaper.
- **2 layers, lead-free HASL**: routing completes without touching the antenna zone (3.7 mm without copper).
- **Removed:** pressure sensor (no depth available), MAX17048, motor, Tag-Connect, TVS, reset on insertion.

**Real costs from the v0.4 JLC cart** (2026-11-03, 22.86 x 26 mm board, before the *basic* LED and the TPS22916C). E73, IMU (LGA) and BQ25101 (BGA) can be assembled **only with Standard PCBA**, not Economic:

| Item | EUR |
|---|---|
| 5 PCBs 2 layers HASL (offer) | 1.79 |
| Standard setup | 23.02 |
| Stencil | 7.39 |
| Components for 2 boards | 26.95 |
| Extended loading (5 types) | 16.63 |
| SMT assembly | 0.66 |
| X-ray | 8.85 |
| Packaging | 0.45 |
| Shipping | 9.62 |
| VAT, temporary duty and EU handling fees | 31.32 |
| **Total** | **128.46** |

Reductions: *PCBA Special Offer* coupon (-8.05 EUR, expires 2026-11-29) and *JLCONE PCB* (up to -1.79 EUR), *basic* LED already done (about -4 EUR with VAT). The TPS22916C adds one extended loading fee (about +4.5 EUR with VAT). For v0.5 see [v0.5 costs](#v05-costs).

### Independent verification (v0.4)

Document: [`hardware/nrf52840/verifica_v0.4.md`](hardware/nrf52840/verifica_v0.4.md) (Italian). Carried out on 2026-11-03 by a reviewer agent on commit `8fd6cc0`, with `kicad-cli` 10.0.6 and the script `kicad/verifica_v04.py` (expected table written by hand from the datasheets).

**Result: 65 tests, 0 blocking defects.** Netlist: 85 expected pins, 0 differences; PCB and schematic match; pinouts and footprints consistent with the datasheets.

Main warnings:
- **HASL or ENIG finish.** HASL with the 0.4 mm BGA of the BQ25101 is discouraged by JLC; the review recommends ENIG (costs more). The user chooses at order time.
- **IMU LGA (U2):** orientation to confirm in the JLC preview and pad dimensions to compare with the DS13510 mechanical drawing (not reached).
- **Polarity of LED (D1), Schottky (D2) and header (J1)** and rotations of E73, IMU, BQ25101: confirm in the JLC preview. The header is symmetric: no reverse-cell protection (mark the wires).
- **Voltage margin:** VDD follows VDDH - 0.3 V below 3.6 V and the flash needs at least 2.7 V: battery cut-off in firmware at 3.2-3.3 V.
- **External current from VDD:** 5 mA with radio above +4 dBm: do not write to flash while BLE transmits at high power.
- **Charger:** C5 rated >= 10 V, consider removing C6 or C7; with a 5.0 V input and the Schottky the margin on VIN-DPM is narrow; load during charging prevents termination (10 h timer).
- **Antenna:** the Ebyte datasheet does not dimension the keep-out zone; a range test before the resin is mandatory.
- **Firmware:** no DC/DC, LFCLK from the RC oscillator (P0.00/P0.01 used as GPIO), no USB events.
- **TPS22916C:** applied in v0.5. Firmware: SPI, CS and INT low before removing power and a 5-10 ms wait at power-up. The v0.5 check is `kicad/verifica_v05.py` (100/100 pins).

### Related documents
- [`hardware/nrf52840/bom.md`](hardware/nrf52840/bom.md): bill of materials with LCSC codes and alternatives (Italian).
- [`hardware/nrf52840/verifiche.md`](hardware/nrf52840/verifiche.md): datasheet checks (v0.2/v0.3, Italian).
- [`hardware/nrf52840/SwimTag_v0.3_collaudo.pdf`](hardware/nrf52840/SwimTag_v0.3_collaudo.pdf): historical v0.3 PDF.
- Renders: `hardware/nrf52840/kicad/jlc/v0.6_swimtag_v06/render_sopra.png`, `render_sotto.png`, `render_3d.png` (v0.5 in `v0.5_swimtag_economica/`, v0.4 in `v0.4_swimtag_economica/`).
- [`hardware/nrf52840/saldatura_cella_v0.5.png`](hardware/nrf52840/saldatura_cella_v0.5.png): where to solder the cell wires.
- [`hardware/nrf52840/revisioni_esterne.md`](hardware/nrf52840/revisioni_esterne.md): outcome of the Gemini and Copilot reviews (Italian).

## XIAO nRF52840 Sense test tags

A cheap path to test now, while the custom boards are in the making: two **Seeed XIAO nRF52840 Sense** boards (same SoC, Zephyr / nRF Connect SDK firmware), worn under the cap. They record the IMU to flash while in the water and download the data over BLE out of the water. Full bill of materials, procedures, risks and sources (Italian): [`hardware/xiao/README.md`](hardware/xiao/README.md).

- **Board.** XIAO nRF52840 Sense (LSM6DS3TR-C IMU on I2C, 2 MB QSPI flash, TI BQ25101 charger), about 16 EUR each with VAT.
- **Cell.** **LP-401230, 100 mAh** with protection (30.5 x 12.0 x 4.05 mm). The 40 mAh cell used on the custom boards is **unsuitable**: the XIAO charger delivers at least 50 mA, i.e. 1.25 C on 40 mAh.
- **IMU power.** The IMU is powered from pin P1.08 (IMU_PWR): the firmware power-cycles it to clear a latch-up and switches it off during sleep.
- **Waterproofing for tests.** Vacuum bag for the first tests; potting (epoxy) is evaluated in the document and requires a dry run on a dummy sample first.
- **Soldering.** Only the two cell wires to the BAT pads on the back.

## External reviews (v0.4)

The v0.4 design document was given to two external reviewers on 2026-11-04. Outcomes and actions: [`hardware/nrf52840/revisioni_esterne.md`](hardware/nrf52840/revisioni_esterne.md). The text that was sent: [`hardware/nrf52840/revisione_esterna_v0.4.md`](hardware/nrf52840/revisione_esterna_v0.4.md). The decided changes are in v0.5.

- **Gemini (3 rounds):** PCB changes: 100 kOhm VIN-GND, IMU_CS and IMU_MISO off XL1/XL2, ENIG finish (order option). Confirmed correct: E73, IMU on SPI, flash, BQ25101 BGA, TPS22916C. Firmware requirements: undervoltage threshold, System OFF while charging, IMU with low signals before power-down, radio within +4 dBm with flash, UICR at first boot.
- **Copilot (sign-off, "I would not sign yet"):** S1 (TS with 10 kOhm to ground as a blocking error) is a **false positive**: the TI datasheet (SLUSBV8C p. 3) prescribes exactly 10 kOhm to VSS when the NTC is not used; 50 uA x 10 kOhm = 0.5 V. Valid points: VDD_IMU test point (TP8), DFM ticket to JLC for the two 0.4 mm packages, drying the board **without the cell** before the resin.
- **Applied in v0.5:** TPS22916C, TVS D3, Q1 against reversed cell, R8, TP8, new GPIOs. **Still to do:** ENIG, DFM ticket, firmware (undervoltage, charging, IMU sequences), range test, level shifter on SWD. The review request for v0.5 (confirmation round before ordering) is in [`hardware/nrf52840/revisione_esterna_v0.5.md`](hardware/nrf52840/revisione_esterna_v0.5.md).

## Programmer HAT for Raspberry Pi 3/4

Single-sided board, hand-built with **toner transfer**, with the shape and holes of a Raspberry Pi HAT (65 x 56.5 mm). It plugs onto the 40-pin header of a Pi 3 or 4. Seven **pogo** pins land on the pads under the tag: 5 for SWD debug and 2 for charging. The Pi programs with **OpenOCD** bit-banging the GPIOs and can charge the cell while the tag is connected.

![Programmer, render](hardware/programmatore/img/render_top.png)

- **Header connections:** pin 2 (5 V, charging only, via PTC and jumper), 12 (RESET, GPIO18), 18 (SWDIO, GPIO24), 20 (GND), 22 (SWCLK, GPIO25). 1 kOhm series resistors on SWD and RESET.
- **Golden rule:** never the Pi's 3.3 V on the tag's VDD. The tag is powered by its cell; at first boot its VDD is 1.8 V until `UICR.REGOUT0` is written.
- **Charging:** VIN and GND pogo pins charge the 401012 cell through the BQ25101 (13.5 mA, about 3-3.5 hours from empty). Jumper JP1: none = charging off (default), 1-2 = Pi 5 V, 2-3 = external 5 V.
- **Alignment:** three stop pins on the edges with the tag's notches, estimated error about +/-0.3 mm.
- **OpenOCD:** file `swimtag_pi.cfg` (driver `bcm2835gpio`, peripheral base 0x3F000000 for Pi 3 and 0xFE000000 for Pi 4). Pi 5 not supported.
- **DRC 0, ERC 0** with `kicad-cli` 10.0.6.
- **Not tested physically:** the board has not been built. Known risks: 1.8 V levels on the tag (1 kOhm resistors are not a level translation), pogo hole to verify on the real part, header position to verify on a real Pi.

**Documentation:**
- [`hardware/programmatore/Programmatore_SwimTag_v0.5.pdf`](hardware/programmatore/Programmatore_SwimTag_v0.5.pdf): schematic, bill of materials, procedure, OpenOCD (Italian). The 1:1 prints are on pages 6 (mirrored copper), 7 (components), 8 (2:1 enlargement) and 9 (drill map).
- [`hardware/programmatore/README.md`](hardware/programmatore/README.md): details, pinout, procedure and limits (Italian).
- [`hardware/programmatore/bom.md`](hardware/programmatore/bom.md): bill of materials with prices.
- [`hardware/programmatore/stampa/`](hardware/programmatore/stampa/): 1:1 print sheets.

## Planned features and ideas

Not implemented. They come from design discussions and are recorded in [`docs/DECISIONI.md`](docs/DECISIONI.md) and [`docs/DESIGN.md`](docs/DESIGN.md) (Italian).

- **Team charging base with slots (planned).** A base that charges several tags at once. Each swimmer owns a passive **NFC token** and leaves it in the slot of the tag they take; this associates swimmer and tag. The base **arms** the tag, and at the end of the workout downloads its data and sends it to the poolside display. An unarmed tag does not record. Reasons: the display is not a touch screen and may be far from the athletes, no phone is needed at the pool, and the token deters theft.
- **"% effort" on the display (idea).** Estimated from pace relative to the swimmer's personal Critical Swim Speed (CSS), plus stroke-rate and stroke-length fatigue. It is an **effort estimate, explicitly not physiological stress**: no heart rate or other physiological sensor is used.
- **Final version without external flash (idea).** The tag would record only events (start, turns, stop), with a circular buffer of about 10 s in RAM. This removes the flash and the long raw recordings, which remain a development tool.
- **Other items.** Vibration motor and pressure sensor in the final version (removed from the economy boards).

## Technical wallpaper gallery

Twenty 1170 x 2532 px drawing sheets generated from the real PCBs (blueprint, OLED, technical paper, copper on green). Generated on **v0.5**. Full images in [`hardware/wallpaper_v0.5/png/`](hardware/wallpaper_v0.5/png/) (files `NN_name_1170x2532.png`, same names as v0.4).

| &nbsp; | &nbsp; | &nbsp; | &nbsp; |
|---|---|---|---|
| <img src="hardware/wallpaper_v0.5/png/01_tag_pianta_1170x2532.png" width="180"><br>**01** Tag plan | <img src="hardware/wallpaper_v0.5/png/02_tag_esploso_1170x2532.png" width="180"><br>**02** Exploded view | <img src="hardware/wallpaper_v0.5/png/03_tag_sezione_1170x2532.png" width="180"><br>**03** Section | <img src="hardware/wallpaper_v0.5/png/04_tag_dettagli_1170x2532.png" width="180"><br>**04** Details |
| <img src="hardware/wallpaper_v0.5/png/05_e73_antenna_1170x2532.png" width="180"><br>**05** E73 and antenna | <img src="hardware/wallpaper_v0.5/png/06_e73_piedinatura_1170x2532.png" width="180"><br>**06** E73 pinout | <img src="hardware/wallpaper_v0.5/png/07_rame_superiore_1170x2532.png" width="180"><br>**07** Top copper | <img src="hardware/wallpaper_v0.5/png/08_rame_inferiore_1170x2532.png" width="180"><br>**08** Bottom copper |
| <img src="hardware/wallpaper_v0.5/png/09_maschera_serigrafia_1170x2532.png" width="180"><br>**09** Mask and silkscreen | <img src="hardware/wallpaper_v0.5/png/10_quattro_strati_1170x2532.png" width="180"><br>**10** Layers (stack view) | <img src="hardware/wallpaper_v0.5/png/11_mappa_fori_1170x2532.png" width="180"><br>**11** Drill map | <img src="hardware/wallpaper_v0.5/png/12_zona_carica_1170x2532.png" width="180"><br>**12** Charging zone |
| <img src="hardware/wallpaper_v0.5/png/13_quote_posizione_1170x2532.png" width="180"><br>**13** Dimensions and positions | <img src="hardware/wallpaper_v0.5/png/14_piazzole_servizio_1170x2532.png" width="180"><br>**14** Service pads | <img src="hardware/wallpaper_v0.5/png/15_tre_viste_1170x2532.png" width="180"><br>**15** Three views | <img src="hardware/wallpaper_v0.5/png/16_isometrica_distinta_1170x2532.png" width="180"><br>**16** Isometric with BOM |
| <img src="hardware/wallpaper_v0.5/png/17_programmatore_pianta_1170x2532.png" width="180"><br>**17** Programmer, plan | <img src="hardware/wallpaper_v0.5/png/18_programmatore_pogo_1170x2532.png" width="180"><br>**18** Programmer, pogo pins | <img src="hardware/wallpaper_v0.5/png/19_programmatore_hat_1170x2532.png" width="180"><br>**19** Programmer, HAT | <img src="hardware/wallpaper_v0.5/png/20_programmatore_toner_1170x2532.png" width="180"><br>**20** Programmer, toner transfer |

**How to regenerate them.** `python hardware/wallpaper_v0.5/genera.py` (requires `kicad-cli` and PyMuPDF). Options: `--solo 1 3 12`, `--bozza`, `--forza` to redo the 3D renders too. The v0.4 wallpapers remain in [`hardware/wallpaper_v0.4/png/`](hardware/wallpaper_v0.4/png/) (historical). The v0.3 wallpapers, old and historical only, are in [`hardware/nrf52840/wallpaper/png/`](hardware/nrf52840/wallpaper/png/).

## Repository structure

```
SwimTimer/
├── docs/                         idea, state, decisions, open questions, requirements, design, lessons, algorithms (Italian)
├── firmware/
│   ├── test-collegamenti/        ESP32-S3 tag: firmware 0.4.3
│   └── display-prova/            T-RGB display
├── tools/                        index.html (analysis page), assi.html (old)
├── media/video/                  presentation video generator, thumbnail, music
├── hardware/
│   ├── bom.md, schema.md         ESP32 prototype
│   ├── xiao/                     XIAO nRF52840 Sense test tags (README.md)
│   ├── nrf52840/                 custom board: progetto.md, bom.md, verifiche.md, verifica_v0.4.md,
│   │   │                         revisioni_esterne.md, revisione_esterna_v0.4.md / v0.5.md, ingombro*.svg, v0.3 PDF and wallpapers
│   │   └── kicad/                scripts, KiCad projects (swimtag, _collaudo, _economica, _v06),
│   │                             jlc/ (v0.3 ... v0.6), nextpcb/ (v0.5, panels 3x1 and 2x1, v0.6),
│   │                             verifica_v04/v05/v06.py
│   ├── programmatore/            Raspberry Pi HAT: KiCad, PDF, 1:1 prints, scripts
│   ├── wallpaper_v0.5/           genera.py, estrai_dati.py, render/, png/ (20 wallpapers, v0.5)
│   └── wallpaper_v0.4/           v0.4 wallpapers (historical)
├── CHANGELOG.md                  changes by date
├── CLAUDE.md                     project working rules
└── README.md                     this file
```

## How to regenerate the files

All commands from the repository root. Scripts are in `hardware/nrf52840/kicad/`.

| What | Command | Notes |
|---|---|---|
| Schematic and PCB (v0.5) | `SWIMTAG_VARIANTE=economica python hardware/nrf52840/kicad/genera_schema.py` and `genera_pcb.py` | data in `dati_economica.py`, positions in `posizioni_economica.py` |
| Routing | `sbroglia.py` | Freerouting 2.5.0, Java 25; non-deterministic: repeat until DRC is 0 |
| Netlist check | `verifica_netlist.py` | compares the netlist with the data |
| Independent check | `python hardware/nrf52840/kicad/verifica_v05.py <pcb> <net.xml> [cpl.csv bom.csv]` | EXPECTED table hand-written from datasheets (`verifica_v04.py` for v0.4, `verifica_v06.py` for v0.6) |
| JLC files | `SWIMTAG_VARIANTE=economica python hardware/nrf52840/kicad/esporta_jlc.py` | writes to `jlc/v0.5_swimtag_economica/` |
| NextPCB files | `python hardware/nrf52840/kicad/esporta_nextpcb.py` | writes to `nextpcb/`; panels with `crea_pannelli.py`; XLSX from CSV with `csv_a_xlsx.py` |
| v0.6 board | `dati_v06.py`, `posizioni_v06.py`, `genera_schema.py` / `genera_pcb.py`, `cuci_massa.py` (ground stitching), `disegno_montaggio_v06.py` | project `swimtag_v06.*`; check the scripts' arguments before running |
| Programmer | `cd hardware/programmatore; python genera_kicad.py --drc` then `python genera_pdf.py` | re-reads TP1-TP7 from the tag PCB; PDF needs PyMuPDF and `kicad-cli` |
| Wallpapers | `python hardware/wallpaper_v0.5/genera.py` | see gallery |

v0.4 is regenerated from commit `8fd6cc0`; v0.3 with `SWIMTAG_VARIANTE=collaudo` (default).

## Ordering flow: JLCPCB and NextPCB

The v0.5 board is verified (DRC/ERC, `verifica_v05.py`). **Do not order** before: cost decision (~125 EUR against the 100 EUR cap), JLC preview, HASL/ENIG choice, DFM ticket. For v0.6, also verify the rotations of the SOT-23 parts.

**JLCPCB**
1. Regenerate the JLC files and check `bom_jlc.csv` and `cpl_jlc.csv`.
2. Upload the Gerber zip (`swimtag_gerber.zip`) in the PCB order: 2 layers (v0.5) or 4 layers (v0.6), 0.8 mm, **lead-free HASL or ENIG** (user's choice, see the verification).
3. **Standard PCBA** assembly service (mandatory for v0.5: E73, IMU and BQ25101 are "Standard only"), top side, **PCBA Qty = 2**; if asked, process edges "Added by JLCPCB".
4. Upload BOM and CPL and check in the preview the rotations and pin 1 of E73, IMU (LGA), BQ25101 (BGA), TPS22916C (U6, probably "Standard only"), Q1 (SOT-23), flash (U3 at 270 degrees), LED (D1), Schottky (D2), TVS (D3) and header (J1); E73 stock.
5. Apply the **coupons** from the Coupon Center: *PCBA Special Offer* (8.05 EUR) and *JLCONE PCB* (order from the JLCONE app).
6. Enable **Confirm Parts Placement** (0.45 EUR) to approve placement before production.
7. Add **X-ray** for E73, IMU, BQ25101 and the other parts with hidden pads (about +10 USD).
8. Open a DFM ticket with JLC for the two 0.4 mm packages (BQ25101 and TPS22916C).
9. Check the total (target <= 100 EUR with VAT, see cuts in [v0.5 costs](#v05-costs)), then pay. Cell, pogo pins and programmer are excluded.

**NextPCB**
1. Use the files in `hardware/nrf52840/kicad/nextpcb/` (`v0.5`, panels `v0.5_pannello_3x1` / `v0.5_pannello_2x1`, or `v0.6`): Gerber zip, BOM, CPL/centroid.
2. Panels use mouse bites; J1 is not assembled (solder the cell wires by hand).
3. The Rev0 service rejects BGA parts with pitch below 0.45 mm: this is why v0.6 exists.
4. Check pin 1 and rotations in `assembly_top_render.png` and `assembly_pin1.png` (v0.6) before paying.

## Roadmap and open issues

**nRF52840 board**
1. Decide the cost: ~125 EUR against the 100 EUR cap (cuts: X-ray, TVS, header), or the NextPCB route with v0.6.
2. Verify the v0.6 SOT-23 rotations in a JLC preview; choose HASL/ENIG, DFM ticket, order 2 boards.
3. Bench test of Q1 with the cell connected correctly and reversed (v0.5); first power-up from a supply limited to about 50 mA.
4. Build the programmer, write UICR, antenna range test before the resin (antenna 0.3 mm from the edge, 28 mm board).
5. Firmware on Zephyr / nRF Connect SDK (SPI, flash, recording, MCUboot, sleep with IMU INT), then pool tests.
6. Final version: motor, pressure sensor, multi-slot charging base with NFC association (see [Planned features and ideas](#planned-features-and-ideas)).

**XIAO test tags**
- Order 2 boards and the 100 mAh cells, dry-run the waterproofing, port the firmware to the XIAO.

**ESP32 prototype**
- On battery only, the tag does not flash blue and is not visible over Bluetooth (red LED on, 3.87 V at the pads).
- BMI160 latch-up after abrupt power-offs: the main switch is used.
- Battery-powered display does not turn on without USB.
- Unreliable software tap; BMI160 FIFO reading (about 44 Hz real).
- Sessions recorded with video, algorithm tuning, pool test.

**General risks**
- Patents in the field (FORM US 11833392): freedom-to-operate check before any commercial use.
- BLE does not cross water; waterproof case and resin to be defined.
- No automated tests.

Details: [`docs/STATO.md`](docs/STATO.md) (Italian). Decisions: [`docs/DECISIONI.md`](docs/DECISIONI.md) (Italian). Changes: [`CHANGELOG.md`](CHANGELOG.md).

## Contributing

Contributions are not open yet. Issues and suggestions are welcome on GitHub. Working documents are in Italian; code, scripts and this README accept English.

## Privacy and security

- No credentials in the repository: if needed, only in `.env` (excluded from git) and as CI secrets.
- No real personal data: swim sessions are health data and stay local (`dati/`, excluded from git). Tests use invented data only.
- Since 2026-11-04 the whole project, hardware included, lives in this single public repository; the old private repository `PZero/SwimTimer-nrf52840` is retired.
- Possible companion app: Firebase free Spark plan, no Cloud Functions.

## License and author

Project license: to be defined (no `LICENSE` file). The driver in `firmware/display-prova/src/trgb/` is under the MIT license (Copyright 2024 Xinyuan-LilyGO), with its own `LICENSE` file.

Author: PZero (GitHub `PZero`).
