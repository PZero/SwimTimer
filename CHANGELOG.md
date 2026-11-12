# Changelog

## 2026-11-12 (base station Raspberry Pi 3, final architecture, crash analysis)
- **Base station** `stazione/rpi/` (LEGGIMI.md, `swim-firstrun.sh`, `user-data.esempio`): headless Raspberry Pi 3 (Raspberry Pi OS Lite 64-bit, trixie) with cloud-init on first boot, fallback `systemd.run=` script, network diagnostics in `/boot/firmware/diag.txt`, Waveshare 4" HDMI settings. Credentials are placeholders only.
- **Architecture decided:** tag (XIAO nRF52840) -> receiver (XIAO, USB) -> Raspberry Pi 3 -> 15.6" HDMI monitor (HTML page). Tests with 2 tags in raw mode, events only in normal operation.
- **Crash analysis (2026-11-11 pool incident)** in `docs/STATO.md`: reset cause not logged by 0.6.0; hypotheses are battery/3V3 contact or stack overflow in BLE callbacks; tag 0.6.2 will add prevention and report the reset reason to the receiver.
- **Docs:** `docs/STATO.md` rewritten, decisions and open questions updated. README: target chain and base station sections. No firmware changed.

## 2026-11-12 (tag firmware 0.6.1, display without screen, enclosure)
- **Pool incident (2026-11-11):** a tag restarted during a recording and came back in normal mode, where touches were ignored; the swim was not recorded. Analysis kept outside the repository; the fixes are in this entry.
- **XIAO firmware 0.6.1 (test build, `-prove` for the test commands)** (`firmware/xiao-stream`, details in `LEGGIMI.md`, test log in `PROVA-0.6.1.md`): without USB the tag records or sleeps (normal mode only with USB); automatic resume after a crash or watchdog reset, at most 3 in a row (counter in RAM and flash); 8 s watchdog; fault context and persistent diary (`DIARIO`); IMU FIFO realignment with a content check (`swr_fifo.h`, simulated by `fifo_sim.py`); continuous session time (start-up 500 ms, measured with `misura_avvio.py`); USB rules (2 s absence, waits for VBUS, never System OFF with VBUS); LEDs for touches visible on battery only in the touch handling; name and colour settable only over USB; standby command `M_SONNO` (0x14) on the sync channel. The published OTA release stays 0.5.4.
- **Verified on battery:** resume after crash and watchdog (3 crashes and 3 blocks, refusal on the 4th), USB stability, start-up time, impact and FIFO cut tests. Memory-full diagnosis solved after a verified copy.
- **Not verified yet:** standby from the display page, rest stop (3 min still) on tag `447B0247`, idle on the charger (with USB the tag stays awake and restarts instead of sleeping). Tracked as open issues in `docs/STATO.md`.
- **Display firmware** `firmware/display-sync` (T-RGB): the screen is broken, so the board works without it. It downloads the tags to the microSD, creates the Wi-Fi network «SwimTimer» and serves a status page for iPhone at `http://192.168.4.1` (warnings with the action to take, REGISTRA also during a download, last block saved to SD, standby button for the tags). The network password is in `segreti.h`, excluded from git; the template is `segreti.esempio.h`. Bluetooth scan at 30 % duty cycle (at 80 % the Wi-Fi network disappeared). Preview with invented data: `web/anteprima.html`.
- **Display enclosure** `hardware/display-involucro/`: parametric OpenSCAD design (PLA vase, silicone cap, fork with a 15° detent swivel), STL files and renders. Fit on the real board still to be checked.
- **Repository:** new `revisore` agent (`.claude/agents/revisore.md`), token-saving rules in `CLAUDE.md`, expanded lessons learned (`docs/LEZIONI-APPRESE.md`).
- **README:** firmware, status and folder structure sections updated; roadmap rewritten for the next pool session.

## 2026-11-10 (tag to display synchronization)
- **Sync protocol** (`docs/SINCRONIZZAZIONE.md`, Italian): 4 KB blocks; the tag pushes the oldest unconfirmed block over BLE (service `7a1e0101`: encrypted CONTROL with bonding, DATA notifications, 151-byte SYNC STATE); the display verifies it (CRC32 + page CRC16), writes it to microSD, reads it back and only then confirms; no timed resend; window of 2; global sequence number never reused. Invariant: the tag never overwrites an unconfirmed block; full memory stops recording.
- **XIAO firmware 0.6.0** (`firmware/xiao-stream`): ring flash of 512 blocks, `.swr` format 3 (header 0xB1 with sequence number; confirmation in word 252..255 because the Puya flash replaces the 4-byte word instead of ANDing it: format 2 put it in byte 16 and corrupted the sequence number, found and fixed, no data lost); BLE always on, also while recording (200 ms advertising with state, battery, memory, colour), 2 connections; settable name (up to 11 characters) and colour (palette of 10); LEDs off on battery; unrecognised memory never erased. The published `release/xiao.bin` stays 0.5.4.
- **Display firmware** `firmware/display-sync` (LilyGO T-RGB, PlatformIO, Adafruit GFX, no LVGL): dial in 3 sectors of 120 degrees with the 512-block map, tag name and colour, battery, signal; up to 3 tags at once; single SD writer task; never in standby; boot log on SD; DEMO mode with 3 simulated tags. Mockup: `docs/img/mockup-stato-tag.png` (invented data).
- **Tools page:** Synchronization panel (state, block map, name and colour), `.swr` reader for formats 1/2/3 (`tools/swr.js`, copies in `app/`), test `tools/test_swr2.mjs`. Edge recommended.
- **Dry run:** 2 tags x 15 min next to the display: 666 blocks saved and confirmed, 0 CRC errors, 0 anomalies, ring memory on both tags, no display restart; up to 8 KB/s against 1.25 KB/s in production. Weak signal on the T-RGB (-57/-64 dBm at 10 cm), to be tuned.
- **Display SD layout:** one folder per tag (`/swim/<tag id>/` with `tag.swr`, `tag.idx`, `tag.anomalia`) instead of one per display boot; the boot log, with the reset reason, goes to `/swim/avvii.txt`.
- **Tools page, multi-file and sync:** several `.swr` files can be opened at once (merged by block sequence number, duplicates dropped); the page reads the format-3 `MEM` and `DUMP` over USB; on connect it asks the tag for its real name and colour; position warnings only for full flash images.
- **Tag firmware 0.6.0, SLEEP during recording:** the SLEEP command works while recording; it closes the segment with stop reason 6 ("SLEEP command"). `NOME` and `COLORE` without argument return the current value.
- **SD check from the PC:** the display SD card read on a PC gave 2408 blocks from two real tags, no sequence gaps, no overruns, about 1.27 M samples decoded.
- **Next:** stability (ERROR advertisement before sleep, display timeout/watchdog), signal tuning, long-duration test and edge cases.
- **README:** new "Tag to display synchronization" section, status, firmware, tools, folder tree and roadmap updated.

## 2026-11-09/10 (first pool test: OpenCV, IMU test bench, video v3)
- **Published firmware release 0.5.4:** `firmware/xiao-stream/release/xiao.bin` + `xiao.json` (155,684 bytes, CRC32 `b771d198`), built from the same source as the tag used in the pool test, with `-fmacro-prefix-map` for both C and C++ (no local paths in the binary). The page's BLE update now installs 0.5.4 instead of 0.4.2; the OTA install of this package is not yet tested.
- **First pool test video (2.5 minutes, original generated music):** YouTube IT https://youtu.be/J01CR2nldp8, EN https://youtu.be/bs7WDUuwb-A; shown first in the landing page and at the top of the README. Real images and data from the author's own session (author's choice): images, thumbnails and `.mp4` files stay out of the repository. Sources: `media/video/genera_video_v3.py`, `musica_v3.py`, `testi_v3_en.py`, `prepara_img_v3.py`, `STORYBOARD_v3.md`.
- **Annotation editor** (members' area and tools page): the event list no longer scrolls the page; the real video frame rate is measured while playing (50 fps instead of a fixed 30) for frame steps and frame numbers; a clicked event is moved frame by frame with the arrow keys (Shift ±10, Esc releases it).
- **OpenCV on the underwater video** (`analisi/video/`): stabilisation (ECC), median background, skin-colour filter against bubbles, distance of the body from the wall frame by frame; automatic classification of starts, turns and finishes used as the new reference.
- **IMU test bench** (`analisi/imu/`): session loader and dataset format, streaming simulator with a causality check for the finish, evaluation per event type, video-data time mapping, sample-rate experiment (104/52/26 Hz) and recording minutes in 2 MiB. Data and results stay out of the repository.
- **Pool test notes:** results (one session, one swimmer, indicative only): IMU finish filters 10/15 within +/-0.88 s; OpenCV reference starts 14/14 +/-0.14 s, finishes +/-0.4 s, turns +/-0.45 s; IMU finish detector recall 57% +/-0.8 s, notification in 0.9 s; at 52 Hz no loss and about 55 minutes in 2 MiB (17.6 at 214 Hz); clock ratio k about 0.9993. Decision: structured method with leave-one-session-out validation and a neural network only for the finish (notification <= 1.5 s, time dated back to the touch), compared with a classical method.
- **README:** updated date, new "Analysis" section, folder tree and roadmap.

## 2026-11-08 (bilingual site, contacts, online tools, progress video)
- **Bilingual site (IT/EN):** language selector on the landing page and the members' area; the choice is kept in the browser (`app/comune/i18n.js`).
- **Contact form:** public form on the landing page with the project address SmartSwimTimer@gmail.com; messages are stored in Firestore (`contatti`), created by anyone with validated fields, readable only by the administrator. Anti-spam: hidden field and 60-second pause. New "Messages" page in the administrator's area with an unread counter.
- **Poolside display section:** screenshot (`app/img/display_demo.png`, `media/display/`) and live demo at `/display/?demo&vel=10`; `tools/display.html` accepts the `?demo&vel=` parameters.
- **Tools page on Firebase at `/strumenti/`:** copied at deploy by `firebase/prepara-strumenti.mjs` (generated folders ignored by git). New **Upload online** button sends a `.swr` file to the shared archive of approved members (`app/comune/sessioni.js`, `online-strumenti.js`); on the GitHub Pages copy the button points to the Firebase site.
- **Videos:** shared through a Google Drive folder with the approved members; no video files on Firebase.
- **Progress update video (2 minutes, original generated music):** YouTube IT https://youtu.be/_Htx2DawnF8, EN https://youtu.be/JLs5JJG4JG8; shown first in the landing page above the first presentation (IT https://youtu.be/_2UzpOqblVI, EN https://youtu.be/EVrdSybpnE4). Sources in `media/video/` (`genera_video_v2.py`, `musica_v2.py`, `testi_v2_en.py`, `img_v2/`, thumbnails); the `.mp4` files are not in the repository.
- **Firestore rules:** 17 emulator tests, including contact messages.
- **README:** new progress video at the top, online app section (IT/EN, contacts, display, `/strumenti/`, Drive folder), folder tree, status, roadmap and privacy notes updated.

## 2026-11-08 (firmware 0.5.4)
- **Firmware XIAO 0.5.4:** charge current raised to 100 mA (P0.13 driven low, kept in System OFF); the test board, powered from the cell through a diode because of its dead 3.3 V regulator, stayed at 3.57 V while charging at 50 mA. Flashed over BLE from the PC with the same OTA protocol as the page.

## 2026-11-08 (XIAO-only tools page, firmware 0.5.2/0.5.3)
- **Firmware XIAO 0.5.3:** plugging USB in during a pool recording now closes the recording cleanly (new stop reason 4 "USB connected", also in `swr.py`/`swr.js`) and restarts the tag in normal mode, so it can be read from the page; before, the recording loop ignored serial commands and the page reported "MEM does not respond". Flashed and checked (`K mem 2204 8192`).
- **Firmware XIAO 0.5.2:** no automatic sleep while USB power (VBUS) is present, even with no serial port open; before, the tag went to sleep after 60 s on the desk and disappeared from USB. Flashed over USB and checked (still on the port after 80 s at rest).
- **`tools/index.html` reorganised for the XIAO only** (3028 → ~1700 lines): one connection panel (USB via Web Serial filtered on Seeed VID 0x2886, Bluetooth, Demo) showing link, firmware version and battery; tabs Live / Recording / Annotation / Firmware. The Recording tab uses the shared USB port (no own Connect button); USB log lines go to the live log.
- **Removed** all ESP32-only parts: "Reg. ESP32" tab, ESP32 USB link (VID 0x303a), radar, motion interpretation, event log, LED legend, ESP32 branches of the OTA update (only XIAO-signed images accepted); `tools/assi.html` (old BMI160 axes page) deleted. ESP32 firmware stays in `firmware/`.
- **Test campaign 1 planned** (docs): swimmer alone, 50 m pool, drills at one wall for turns, starts and finishes, iPhone/Insta360 video; filters developed in the web page only.
- **Verification status**: page tested in the browser with Demo and simulated USB/BLE ports, not yet with the real XIAO.
- **Online collaboration app (new, Firebase Spark, no Storage, no Cloud Functions):** public landing page (`app/`, <https://swimtimer-pzero.web.app>) and members' area (`app/area/`, `/area/`) with Google login. Every new account is **pending** until the administrator approves it; pending, refused and revoked accounts read nothing. Raw `.swr` sessions are stored in Firestore in chunks; videos are shared as Google Drive or YouTube links with SHA-256 and metadata (no video files on Firebase); annotations carry the author.
- **Data model** documented in `docs/MODELLO-DATI.md`. **Security rules** in `firebase/firestore.rules`: the administrator is recognised by Firebase user ID, not by e-mail; **14 rule tests** on the Firestore emulator (`cd firebase/test; npm test`).
- **Automatic cache refresh:** the deploy hook writes `app/versione.json`; open pages compare it with the version they loaded and reload when it changes. HTML, JS, CSS and JSON are served with `no-cache`.
- **Fix of the administrator check:** the members' area remembers only a positive answer in the session (a "no" is checked again every time), so an approved administrator is recognised without stale results.
- **Rule tests independent of the real UID:** the tests replace the administrator ID in the rules with a test ID before loading them into the emulator, so the repository tests do not depend on the real account.
- **README** rewritten for the XIAO-only tools page, firmware 0.5.2/0.5.3, the online app and test campaign 1 (planned: one swimmer, 50 m pool, wall drills, training for verification, video from iPhone and Insta360, hand annotation before the filters).

## 2026-11-07 (annotation tab fix)
- **Fix:** the Annotation tab collapsed its cards on large screens (single-screen layout forced `min-height: 0`), so the video box had height 0; the Recording/Annotation cards now scroll normally.
- `annotazione.css` and `annotazione.js` are loaded with a version query (`?v=2`) so browsers do not keep stale copies.
- New warning when the opened video plays audio only (no video track decoded, typically HEVC/H.265 from phones), with conversion hints.
- **Known issue:** the page assumes 30 fps; a 25 fps video gives wrong frame stepping and frame numbers (event times in seconds stay correct).

## 2026-11-07 (pool recording mode)
- **README:** new section "Test methodology: raw data, video and hand annotation" (XIAO tag, 5-tap sync, USB download, X alignment, B/R/V/F/P/A annotation, then filters and comparison); stale lines on the XIAO fixed (Arduino firmware, USB download, board in use).
- **Release binary:** rebuilt the published `firmware/xiao-stream/release/xiao.bin` (still 0.4.2, same source) with `-fmacro-prefix-map`, removing a local build path that contained the Windows user name; `xiao.json` updated (144916 bytes, CRC32 `740823a6`).
- **XIAO firmware 0.5.0 "pool recording mode"** in `firmware/xiao-stream/`: records the raw IMU to the 2 MB QSPI flash (208 Hz, +-16 g, +-1000 dps, 256-byte pages with CRC16, int8 delta compression, about 25 min) with BLE off. Start: 2 taps, blue LED, 2 taps; new wake-ups append a segment; erase: 2 taps, blue LED, 6 taps, 2 confirmation taps. Stops after 180 s of rest, memory full or battery < 3.3 V. Data survives battery loss; download over USB only. New `flash_qspi.h` (direct `nrfx_qspi` driver) and `swr_formato.h`.
- **Fix of the 2-tap wake bug**: the Adafruit bootloader clears `RESETREAS`, so the reset cause was lost; a marker is now written in `GPREGRET2` before every System OFF.
- **0.5.1** (compiled, not yet flashed): the blue LED blinks off at each counted tap.
- **`.swr` format** with decoders `swr.py` and `tools/swr.js`, download tool `scarica.py`, 11 unit tests (`test_swr.py`, invented data only) and `tools/parita_swr.mjs` (parity check, to be run on a real recording).
- **Web page `tools/index.html`**: new "Recording" tab (Web Serial download/erase, open `.swr`) and "Annotation" tab (raw-data charts with zoom, video at 30 fps, sync with key X on the 5th tap, events B/R/V/F/P/A saved in video time, project JSON and CSV export). Old tab renamed "Reg. ESP32".
- **Verification status**: nothing above is tested on hardware or with real video; the page was tested with simulated data only; the C++ encoder was never run on a PC.
- **Next**: dry run of 0.5.0 at home, first pool session with video, hand annotation of all events, then filter development and comparison.
- README: new "Pool recording mode" subsection, status table, folder tree and roadmap updated.

## 2026-11-07
- **XIAO streaming firmware 0.4.2** in `firmware/xiao-stream/` (Seeed XIAO nRF52840 Sense, Arduino, core Seeeduino:nrf52 + Bluefruit, with `LEGGIMI.md`). Same `SwimTag` BLE protocol as the ESP32 tag: 16-byte data at 25 Hz from an IMU averaged at 208 Hz, 12-byte status (charge, VBUS, die temperature, divider), commands, log, version. The "XIAO" tab of `tools/index.html` now works over Web Bluetooth. Gyroscope bias calibration reduces head drift.
- **BLE firmware update for the XIAO**: own OTA on characteristic `0006` (staging in flash, CRC32, board signature check, RAM installer), tested on the board 0.4.0 -> 0.4.1 -> 0.4.2. Nordic legacy DFU is not usable from the browser (Web Bluetooth blocklist). `firmware/xiao-stream/release/xiao.bin` and `xiao.json` published by GitHub Pages (workflow updated); the "Tag firmware" dialog handles the XIAO too.
- **Sleep**: "Sleep" command and automatic sleep after 60 s of "still enough" (1 s averages: rotation < 3 dps, tilt < 3 deg), never during an OTA or with the serial port open. Wake with 4 taps (two IMU hardware double-taps) or USB. Sleep on low battery (< 3.3 V).
- **"Tag log" panel** over BLE and rebuilt **Battery panel** for the XIAO (charge state, % from LiPo curve, time to full / runtime, chart, VCAL calibration with a multimeter).
- **Verification status**: double tap, OTA and sleep tested on the board; 4-tap wake, low-battery sleep, Battery panel with the board and VCAL calibration **not yet tested**.
- **Bench note**: one XIAO lost its 3.3 V regulator while soldering the cell; used on the bench with a silicon diode.
- README: new "XIAO streaming firmware" subsection, folder tree and roadmap updated.

## 2026-11-06
- **Board v0.6 "Rev0"** (nRF52840 tag, 4 layers, no BGA): MCP73831 charger, TPS22917 load switch, J1 left DNP, D4 + R2 added, D3 replaced by LC05CI. Design kept at 4 layers on purpose.
- **NextPCB order files** in `hardware/nrf52840/kicad/nextpcb/v0.6/` (Gerber, BOM, CPL, `NOTE_ORDINE.md`). Quote for 20 boards: 216.39 USD after coupon.
- **Panel generators** `crea_pannelli.py`, `cuci_massa.py`, `esporta_nextpcb.py`, `verifica_v06.py` in `hardware/nrf52840/kicad/`. Panels v0.5 3x1 and 2x1 were rejected by the Rev0 review.
- **XIAO documentation** in `hardware/xiao/`.
- **Charging base** redesigned as a slot-based base with NFC tokens (planned, see `docs/DECISIONI.md`).
- **README** now in English only (decision of 2026-11-06); no Italian copy. Working documents in `docs/` remain in Italian.
- **English presentation video** (https://youtu.be/EVrdSybpnE4): `genera_video.py --lingua en`, `media/video/testi_en.py`, `miniatura_youtube_en.png`; linked in the README.
- Repository description and commit messages switched to English.
- **"XIAO" tab** in `tools/index.html`: IMU-oriented 3D XIAO model, head-mounting calibration (Calibra/Annuisci), wireframe half-bust with the Lee Perry-Smith head scan (CC BY 3.0, from CDN) and procedural neck/shoulders, Ricentra, Demo testa, axis check. Waits for a XIAO sketch using the `SwimTag` BLE protocol.
- **XIAO tab update**: old procedural grey shoulders removed; "axis check" shows 10 s scrolling accelerometer and gyroscope charts instead of the value table; "component side" and "USB-C towards" settings removed (tag always on the right, components facing out: gravity is enough for in-plane rotation); eyes drawn as green wireframe, solid red only during the blink; inner mouth surfaces of the head scan hidden; front view perpendicular to the screen.
- **XIAO tab, swim cap and eyes**: optional orange swim cap on the head scan (new "Cuffia" checkbox, on by default, choice remembered; dense grid plus translucent shell); eyes repositioned on the eye sockets measured on the head's depth map.
- **Poolside display mockup** `tools/display.html` (standalone, English UI, invented data): one row per swimmer with colour code, state (Swimming/Rest/Waiting/Done), running time and distance, last time with distance, pace and per-lap splits, **Effort 1-10** on the last segment only (provisional, CSS/pace based, reference test to be agreed) and history of the last 10 segments (newest enters on the left and blinks for 5 s). Large clock restarting when the first swimmer begins a new segment, previous lap duration in grey beside it, stops at the end of the workout. Generic segment model (no workout loaded, the display will be offline), 25/50 m pool, single entry point `ricevi({tag, tipo, t_ms})` for a future BLE source. Demo mode: 7 swimmers staggered by 3-5 s (400 warm-up, 4x100 technique, 3x(300 + 4x100), 200 cool-down), speeds 1x/5x/10x/30x, simulated phase shown under the date.
- **Proposed display architecture** (not yet confirmed), documented in the README: Raspberry Pi 4 + USB nRF52840 dongle + 15.6 inch portable monitor + USB-C PD power bank, Wi-Fi off, native program; about 13 W, about 2 h on battery; up to 10 tags connected; tags record events with their own clock and keep them until the display confirms; only events stored (about 60 KB for 10 tags in 2 h). Open problem: BLE does not reach the opposite wall in a 50 m pool.
- `.claude/launch.json` to serve the page locally.
- Security check on the public repository (tracked and untracked files): no keys, tokens, passwords, `.env` or personal data. Absolute paths with the Windows user name were not found.

## 2026-11-04
- Allineamento del ramo della scheda con `main` del repository pubblico (firmware 0.4.3, pagina di analisi `tools/index.html`, documenti).
- **Scheda v0.5** (commit 01c6b8b), 21,59 x 28,0 mm (a 26-27,5 lo sbroglio a 2 strati non chiude), 2 strati: TPS22916C (U6) su VDD_IMU con ON su P0.04 e R7 1 MOhm, R6 su VDD_IMU, C5 4,7 uF 10 V, C7 tolto e C6 4,7 uF, R8 100 kOhm VIN-GND, TVS D3 PTVSLC3D5VB prima di D2, AO3401A (Q1) con R9 contro l'inversione della cella, TP8 VDD_IMU, IMU_MISO/CS su P0.08/P0.12 (XL1/XL2 liberi), serigrafia 1,0 mm. DRC 0, ERC 0 errori, `verifica_v05.py` 100/100 pin, 28 reti, 369 piste, 36 via. File JLC in `jlc/v0.5_swimtag_economica/` (v0.4 congelata). Costo stimato circa 125 EUR (sopra il tetto di 100): tagli possibili senza raggi X ~109, senza TVS ~105, senza header ~100,5.
- Revisioni esterne (Gemini, Copilot) raccolte in `hardware/nrf52840/revisioni_esterne.md` (ex `revisioni_esterne_v0.4.md`): modifiche applicate nella v0.5; S1 di Copilot (TS con 10 kOhm a massa) e' un falso positivo, confermato dal foglio TI; testo inviato in `revisione_esterna_v0.4.md`.
- Nuovi sfondi tecnici sulla v0.5 in `hardware/wallpaper_v0.5/` (20 PNG 1170 x 2532, stessi nomi della v0.4).
- README riscritto da zero (storia v0.1-v0.4, v0.4 in dettaglio, programmatore, galleria dei 20 sfondi, rigenerazione, flusso d'ordine JLC, roadmap, privacy).

## 2026-11-03
- v0.4 ricompattata a 21,59 x 26,0 mm (era 22,86): E73 a 0,3 mm dal bordo sinistro, pinout cambiato (CHG_N P0.20, LED P0.22, INT1 P0.26, INT2 P0.06). 2 strati, DRC 0, 313 piste, 29 via. 20,32 mm non chiude lo sbroglio.
- LED 0603 KT-0603R (C2286, basic) con anodo su VDD: -3,07 $ di caricamento extended. File JLC rigenerati; costo stimato circa 87-91 EUR per 2 schede.
- Verifica indipendente `hardware/nrf52840/verifica_v0.4.md` (65 test, 0 bloccanti, sul commit 8fd6cc0) e script `kicad/verifica_v04.py`; consiglia ENIG per BQ25101 (0,4 mm) e IMU (0,5 mm).
- Programmatore HAT per Raspberry Pi 3/4 in `hardware/programmatore/` (pogo sulle 7 piazzole, toner transfer, OpenOCD, ricarica con PTC e ponticello, PDF con stampe 1:1); DRC 0, ERC 0; non costruito.
- Generatore dei 20 sfondi tecnici in `hardware/wallpaper_v0.4/` (PNG 1170 x 2532 e 1080 x 2400).
- Decisione: regola "niente saldature" solo per il tag; il programmatore lo salda l'utente.

## 2026-11-02
- Nuova scheda v0.4 "economica" (budget <= 100 EUR): E73, LSM6DSV16X, flash 16 MB W25Q128JVSIQ (basic), BQ25101 con TS 10 k a massa, 1 LED, header batteria SMD 1,27 mm (C55213900), Schottky 1N5819WS sui contatti di ricarica, lettura batteria con VDDHDIV5. Tolti pressione, MAX17048, TPS22916C, vibratore, Tag-Connect, TVS, reset all'inserimento.
- 2 strati 0,8 mm HASL senza piombo, scheda 22,86 x 26 mm, DRC 0. Sotto: 5 pogo SWD e 2 contatti di ricarica su griglia 2,54 mm. File in `kicad/jlc/v0.4_swimtag_economica/`, disegno `ingombro_v0.4.svg`.

## 2026-11-01
- Tag v0.3 di collaudo, variante 1c: scheda 26 x 30 mm, 4 strati 0,8 mm, una faccia, tag finito circa 29 x 33 x 9,2 mm. Netlist 36/36, DRC 0 errori, 609 piste, 80 via. File JLC in `hardware/nrf52840/kicad/jlc/v0.3_swimtag_collaudo/`.
- Modulo Ebyte E73 al posto del Raytac (stock 0); cella Ampul 401012 (40 mAh, PCM, 1 C) su JST SH; sensori su interruttore di carico TPS22916C; MAX17048 su secondo bus I2C; TS del BQ25101 da GPIO; 2 x 47 uF; 0 ohm tra cella e circuito; Tag-Connect TC2030-NL per SWD (VDD solo come riferimento); piazzole di prova; contatti di ricarica a 4,2 mm per una futura base a più posti.
- Vibratore non montato sui 2 tag di collaudo (nessun motore SMD montabile da JLC a rifusione); restano pilotaggio e piazzole MOT+/MOT-.
- Nuovi: 8 wallpaper tecnici PNG 1170 x 2532 in `hardware/nrf52840/wallpaper/png/`, script `genera_wallpaper.py` e `genera_pdf.py`, PDF di progetto `hardware/nrf52840/SwimTag_v0.3_collaudo.pdf` (14 pagine); `ingombro.svg` generato dal PCB reale.
- Costo stimato 2 tag JLC circa 120-130 $ più cella e cavo Tag-Connect (non ancora ordinato, anteprima JLC da fare).
- README: sezione nRF52840 aggiornata alla v0.3; `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati.

## 2026-10-25 / 2026-10-26
- Scheda su misura nRF52840 (`hardware/nrf52840/`): studio dei progetti SlimeVR, distinta (`bom.md`), progetto (`progetto.md`) e ingombro in scala (`ingombro.svg`).
- Progetto KiCad generato da script (`kicad/`, `dati_scheda.py` come unica fonte): v0.1, poi v0.2 con scheda 17,5 × 22,5 mm a 4 strati.
- Sbroglio automatico con Freerouting 2.5.0 (Java 25): DRC 0 errori.
- Verifiche sui datasheet (ST AN5763, TE MS5837, TI BQ25101, Raytac) con 4 correzioni, registrate in `verifiche.md`.
- Protezione dei contatti di ricarica (TVS SD05 e Schottky B5819WS) e reset all'inserimento nella custodia.
- File per JLC in `kicad/jlc/`: Gerber (zip), BOM, CPL, render, PDF dello schema.
- Documenti aggiornati: `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md`.
- README: nuova sezione sulla scheda nRF52840, mappa delle cartelle e roadmap.
## 2026-10-26
- `tools/index.html`: card Batteria rifatta con grafico (finestra 1-10 min) di GPIO 1, GPIO 2 e tensione stimata a riposo; livello target in % impostabile con quanto manca (% e V); etichette "misurata" e "A riposo (stima)"; correzione in carica da 0,15 a 0,05 V (misura col tester: 3,84 V a riposo, 3,87 V in carica); la Demo simula anche il partitore 5V.
- Il progetto della scheda nRF52840 (KiCad, Gerber, BOM, v0.2) è ora nel repository privato `PZero/SwimTimer-nrf52840`; questo repository resta pubblico per GitHub Pages.
- GitHub Pages attivato: pagina online su https://pzero.github.io/SwimTimer/ con il firmware 0.4.3 pubblicato.
- Prototipo: batteria sostituita, interruttore generale montato, partitore verificato col tester. Il BMI160 è andato in latch-up dopo uno spegnimento brusco; si usa l'interruttore.
- Problema aperto: a sola batteria il tag non parte (LED rosso acceso, niente lampo blu né Bluetooth), diagnosi in corso.
- Firmware invariato (0.4.3); una 0.4.4 è stata provata e scartata.
- Nuovo `docs/LEZIONI-APPRESE.md`: 13 lezioni per la scheda nRF52840 e confronto con la v0.2.
- `hardware/schema.md`, `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati; README aggiornato.

## 2026-10-25 (sera)
- Tag, firmware 0.4.3 (`firmware/test-collegamenti`): corretto un difetto reale; il BMI160 restava a ±2 g (le scritture del fondo scala, fatte a sensore sospeso, andavano perse) mentre la pagina leggeva ±16 g, quindi da fermo si vedevano 8 g invece di 1 g. Ora fondo scala e frequenze si impostano a sensori accesi e vengono riletti (fino a 5 tentativi); in seriale "BMI160: fondo scala ±16 g verificato".
- `tools/index.html`: avviso negli eventi se da fermo il modulo dell'accelerazione non vale circa 1 g (scala incoerente tra tag e pagina).
- Problemi aperti: batteria del tag letta a 3,5 V (quasi scarica, circa 2%), da verificare col tester; vibrazione sospesa in attesa di un modulo con transistor (GPIO 5 libero). La 0.4.3 non è ancora provata sul tag.
- README aggiornato alla versione 0.4.3; `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md`, `hardware/bom.md` aggiornati.

## 2026-10-25
- Tag, firmware 0.4.2 (`firmware/test-collegamenti`): accelerometro a ±16 g e 100 Hz; registrazione di sessioni su LittleFS con doppio tap (avvio) e triplo tap (fine); tap riconosciuti dai campioni (salto oltre 0,8 g, escluso con giroscopio oltre 300 °/s); scaricamento via Bluetooth o USB.
- Aggiornamento del firmware via Bluetooth (due copie del programma, `partitions.csv`), ritorno automatico alla versione precedente, marcatore `SWIMTAG_VER=x.y.z;` nel .bin; stessa versione rifiutata, precedente con conferma.
- Stato esteso del tag (batteria da partitore su GPIO 1, pin 5V su GPIO 2, motivo dell'ultimo riavvio), sblocco automatico del bus I2C, LED RGB come riscontro. Caratteristiche BLE: dati `7a1e0002`, stato `7a1e0003`, comandi `7a1e0004`, risposte `7a1e0005`, OTA `7a1e0006`, versione `7a1e0007`.
- `tools/index.html` (nuova pagina di analisi): schede "Dal vivo" e "Registrazioni", batteria, orientamento 3D, radar con scia di 15 s, interpretazione, eventi, traccia con zoom, finestre Firmware e LED, Demo; Bluetooth (Chrome, Edge, Bluefy su iPhone) o USB. `tools/assi.html` resta la vecchia pagina.
- `tools/index.html`: corretto `versioneDaBin`, che si fermava alla prima occorrenza di `SWIMTAG_VER=%s;` (formato) e non trovava il marcatore vero; ora riconosce il marcatore anche dopo il formato.
- `.github/workflows/pages.yml`: compila il firmware (arduino-cli, core esp32 3.3.12) e pubblica pagina, `firmware/tag.bin` e `firmware/tag.json` su GitHub Pages. Da attivare in Settings, Pages, Source: GitHub Actions.
- `docs/RICERCA-ALGORITMI.md`: ricerca sugli algoritmi IMU per il nuoto; base utile il brevetto FORM US 11833392; nessun dataset pubblico con IMU sulla testa.
- Hardware: partitori 2×100 kΩ su GPIO 1 e GPIO 2; BMI160 a ±16 g (`hardware/bom.md`, `hardware/schema.md`).
- `.gitignore`: escluso `versione.h`, scritto dalla CI.
- Stato: 0.4.0, 0.4.1 e 0.4.2 compilano; la 0.4.2 non è provata sul tag; frequenza reale in registrazione circa 44 Hz (FIFO del BMI160 da fare). Display invariato.
- README aggiornato: funzionalità, canali BLE, stato e comandi, pagina di analisi, aggiornamento del firmware, CI, privacy, brevetti, roadmap.
- `docs/STATO.md`, `docs/DECISIONI.md`, `docs/DOMANDE-APERTE.md` aggiornati.

## 2026-10-24
- Impostazione del progetto: struttura, agenti, comandi `/stato` e `/fine-sessione`, documenti iniziali.
- Analisi dell'idea iniziale (tag BLE + display a bordo vasca) in `docs/IDEA.md`.
- Logica di partenza e arrivo (spinta, calma, virata parziale) e logiche aggiuntive da valutare in `docs/IDEA.md`.
- Distinta componenti (`hardware/bom.md`) e schema del tag prototipo (`hardware/schema.md`).
- Tag di prova: ESP32-S3 SuperMini + BMI160, batteria LiPo sui pad BAT+/BAT-. Sensore verificato su tutti gli assi.
- `firmware/test-collegamenti`: test del bus I2C del BMI160 e invio delle righe dati a circa 50 Hz.
- `tools/assi.html`: pagina Web Serial (Chrome/Edge) con valori e grafici dei 3 assi.
- README completato con architettura, hardware, firmware, uso e roadmap.
- Display scelto: LilyGO T-RGB. Schema del tag riscritto con la batteria sui pad BAT (TP4056 come alternativa scartata).
- `firmware/test-collegamenti`: servizio GATT BLE (25 Hz) e annuncio `SwimTag` con i dati (20 Hz) per il display. Libreria BLE del core esp32 3.3.12, NimBLE-Arduino scartata perché va in crash.
- `tools/assi.html`: pulsante "Collega via Bluetooth" (Web Bluetooth, Chrome/Edge su desktop e Android) accanto a quello USB.
- `firmware/display-prova` (nuovo): firmware di prova per il display LilyGO T-RGB 2,8" (GT911). Riceve gli annunci del tag senza collegarsi, doppio framebuffer, corona dei 3 assi, cronometro di prova. Driver `src/trgb` adattato da LilyGo-T-RGB 1.0.5 (MIT).
- Distinta e stato: display 2,8" con touch GT911 verificato; `docs/STATO.md`, `docs/DECISIONI.md` e `docs/DOMANDE-APERTE.md` aggiornati.
- README aggiornato: canali BLE e flusso dei dati, firmware del display, compilazione con le librerie, struttura delle cartelle, roadmap.
- `firmware/display-prova`: corretta la ricaduta immediata in sonno profondo (sottrazione senza segno in overflow, ora confronti con segno); risveglio anche dal pulsante BOOT (GPIO 0); pull-up RTC su GPIO 1 durante il sonno; motivo dell'avvio mostrato per 2 s.
- `hardware/bom.md`: aggiunte LiPo 1000 mAh del display (caricatore TP4065) e accelerometro I2C da collegare (SDA 8, SCL 48).
- Problema aperto: il display a batteria, senza USB, non si accende.
