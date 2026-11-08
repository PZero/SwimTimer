/* SwimTimer - ANNOTAZIONE ONLINE (copia adattata di tools/annotazione.js): video della prova in vasca + grafici grezzi della tag,
 * sincronizzati con l'evento X (5° tocco). Gli eventi si salvano nel TEMPO DEL VIDEO; t_dati = t_video + offset.
 * Differenze rispetto alla versione locale: i dati .swr arrivano da Firestore (window.SwimDati, area/dati.js), il video si apre dal
 * file locale ma se ne verifica lo sha256 rispetto al video registrato, il progetto si salva su Firestore come annotazione
 * dell'utente tramite i ganci window.SwimOnline (definiti in area/area.js). Il video non lascia mai il browser.
 * Usa window.SWR (swr.js) e window.SwimDati. */
(function () {
  'use strict';
  const SWR = window.SWR, SD = window.SwimDati;
  const radice = document.getElementById('vistaAnn');
  if (!radice || !SWR || !SD) return;

  const FPS = 30;
  const BIAS = 0.25 / FPS;                       // per cadere dentro il fotogramma cercato
  const VEL = [0.1, 0.25, 0.5, 1, 2];
  const TIPI = {
    B: { nome: 'Bracciata', desc: 'entrata della mano in acqua', col: '#38bdf8' },
    R: { nome: 'Respirazione', desc: 'bocca fuori dall\'acqua', col: '#2dd4bf' },
    V: { nome: 'Inizio virata', desc: '', col: '#f5b041' },
    F: { nome: 'Fine virata', desc: '', col: '#fb923c' },
    P: { nome: 'Partenza', desc: '', col: '#4cc38a' },
    A: { nome: 'Arrivo', desc: '', col: '#ff6b6f' },
    X: { nome: 'Sync', desc: '5° tocco', col: '#a78bfa' }
  };
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const r6 = v => Math.round(v * 1e6) / 1e6;
  const fmtT = s => (s < 0 ? '−' : '') + Math.abs(s).toFixed(3) + ' s';

  // ---------------------------------------------------------------- stato
  const S = {
    D: null,                                      // dati derivati dal segmento scelto
    video: { nome: null, durata: 0, dimensione: 0, url: null, t: 0, nominale: 0 },
    offset: null,                                 // t_dati - t_video (s); null = non allineato
    syncDati: null,                               // t_dati del 5° picco cliccato
    eventi: [], sel: null, nextId: 1, undo: [], redo: [],
    anticipo: 0, vista: { t0: 0, t1: 30 }, segui: true, modoAcc: 'mod', modoGyr: 'mod', velIdx: 3, passoStriscia: 60,
    progetto: null,                               // attese lette da un progetto, per i controlli di coerenza
    avviso: '',                                   // avviso online (impronta del video diversa, fps diversi)
    sporco: false                                 // modifiche non ancora salvate online
  };
  window.swtModificheInSospeso = () => S.sporco;   // app/comune/versione.js non ricarica la pagina se ci sono modifiche non salvate

  // ---------------------------------------------------------------- struttura della scheda
  radice.innerHTML = `
  <section class="scheda s12 ann-sez">
    <header><h2>Annotazione <small>video + dati grezzi della tag</small></h2>
      <div class="ann-riga">
        <select id="anSeg" title="Segmento da analizzare" hidden></select>
        <button id="anVideoBtn" class="primario">Apri video (file locale)</button>
        <button id="anSalvaOnline" class="primario" disabled>Salva online</button>
        <button id="anProgApri">Importa progetto .json</button><button id="anProgSalva">Scarica progetto .json</button><button id="anCsv">Esporta eventi.csv</button>
      </div></header>
    <p class="ann-nota">I dati grezzi arrivano dall'archivio condiviso. Il video non viene caricato: si apre dal tuo computer e se ne controlla l'impronta (sha256) rispetto al video registrato. Gli eventi si salvano online come tua annotazione: «Salva online» oppure autosalvataggio dopo 15 secondi senza modifiche (e copia di sicurezza nel browser).</p>
    <div class="ann-riga"><span id="anOnline" class="tenue"></span></div>
    <div class="ann-info" id="anInfo"></div>
  </section>

  <section class="scheda s12 ann-sez ann-graf">
    <header><h2>Dati grezzi <small>rotella/pizzico = zoom · trascina = sposta · clic = marcatore di sync sul picco di |acc| · Maiusc+clic = vai lì nel video</small></h2>
      <div class="ann-riga">
        <span class="segmentato" id="anZoom"><button data-z="1">1 s</button><button data-z="5">5 s</button><button data-z="30">30 s</button><button data-z="0">Tutto</button></span>
        <label class="ann-chk"><input type="checkbox" id="anSegui" checked> Segui il video</label>
        <button class="piccolo" id="anNascondi">Nascondi grafici</button>
      </div></header>
    <div id="anGrafBox">
      <div class="ann-lane"><div class="ann-lane-tit"><span>|acc|</span><select id="anModoAcc"><option value="mod">modulo (g)</option><option value="assi">assi x y z (g)</option></select></div><canvas id="anAcc" class="ann-cv"></canvas></div>
      <div class="ann-lane"><div class="ann-lane-tit"><span>|gyro|</span><select id="anModoGyr"><option value="mod">modulo (dps)</option><option value="assi">assi x y z (dps)</option></select></div><canvas id="anGyr" class="ann-cv"></canvas></div>
      <div class="ann-lane ann-pan"><div class="ann-lane-tit"><span>Panoramica</span></div><canvas id="anPan" class="ann-cv"></canvas></div>
    </div>
  </section>

  <section class="scheda s12 ann-sez ann-vid">
    <header><h2>Video <small>frecce ±1 fotogramma (Maiusc ±10) · J/L ±5 s · Spazio play/pausa · , e . velocità</small></h2>
      <div class="ann-riga"><span class="mono" id="anTempo">–</span></div></header>
    <div class="ann-video-wrap"><video id="anVideo" playsinline preload="auto"></video><div class="ann-vuoto" id="anVuoto">Apri un video MP4 (30 fps) con «Apri video»</div></div>
    <div class="ann-riga ann-comandi">
      <button class="piccolo" data-p="-10" title="−10 fotogrammi (Maiusc+←)">−10f</button>
      <button class="piccolo" data-p="-1" title="−1 fotogramma (←)">−1f</button>
      <button class="piccolo primario" id="anPlay" title="Spazio">▶ Play</button>
      <button class="piccolo" data-p="1" title="+1 fotogramma (→)">+1f</button>
      <button class="piccolo" data-p="10" title="+10 fotogrammi (Maiusc+→)">+10f</button>
      <button class="piccolo" data-s="-5" title="−5 s (J)">−5 s</button>
      <button class="piccolo" data-s="5" title="+5 s (L)">+5 s</button>
      <span class="ann-vel"><button class="piccolo" id="anVelMeno" title="Più lento (,)">−</button><b class="mono" id="anVel">1×</b><button class="piccolo" id="anVelPiu" title="Più veloce (.)">+</button></span>
    </div>
    <div class="ann-striscia-box"><canvas id="anStr" class="ann-cv"></canvas></div>
    <div class="ann-riga"><label>Striscia <select id="anStrSpan"><option value="20">20 s</option><option value="60" selected>60 s</option><option value="300">5 min</option><option value="0">tutto</option></select></label></div>

    <div class="ann-blocchi">
      <div class="ann-blocco">
        <div class="etichetta">Sincronia</div>
        <div class="ann-kv"><span>Sync video (X)</span><b class="mono" id="anSyV">–</b><span>Sync dati (picco)</span><b class="mono" id="anSyD">–</b>
          <span>Offset t_dati − t_video</span><b><input type="number" id="anOff" step="1" class="ann-num" disabled> ms</b></div>
        <div class="ann-riga"><button class="piccolo" data-o="-s" disabled>−1 campione</button><button class="piccolo" data-o="+s" disabled>+1 campione</button>
          <button class="piccolo" data-o="-f" disabled>−1 fotogramma</button><button class="piccolo" data-o="+f" disabled>+1 fotogramma</button></div>
        <p class="ann-nota" id="anAlinea"></p>
      </div>
      <div class="ann-blocco">
        <div class="etichetta">Eventi</div>
        <div class="ann-riga" id="anTipi"></div>
        <div class="ann-riga"><label>Anticipo <input type="number" id="anAnt" class="ann-num" min="0" max="2000" step="10" value="0"> ms</label>
          <button class="piccolo" id="anUndo" title="Z">Annulla</button><button class="piccolo" id="anRedo" title="Maiusc+Z">Ripristina</button><button class="piccolo" id="anElimina" title="Canc">Elimina</button></div>
        <div class="ann-riga"><label class="ann-nota-lbl">Nota <input type="text" id="anNota" placeholder="nota dell'evento selezionato" disabled></label></div>
        <div class="ann-cont" id="anCont"></div>
      </div>
      <div class="ann-blocco ann-lista-box"><div class="etichetta">Elenco <span id="anNEv"></span></div><ol class="ann-lista" id="anLista"></ol></div>
    </div>
    <details class="ann-tasti"><summary>Scorciatoie</summary>
      <p><b>B</b> bracciata (entrata della mano in acqua) · <b>R</b> respirazione (bocca fuori dall'acqua) · <b>V</b> inizio virata · <b>F</b> fine virata · <b>P</b> partenza · <b>A</b> arrivo · <b>X</b> sync (5° tocco, senza anticipo)<br>
      <b>Z</b> annulla · <b>Maiusc+Z</b> ripristina · <b>Canc</b> elimina il selezionato · <b>Alt+←/→</b> sposta il selezionato di un fotogramma · clic su un evento: salta lì e lo seleziona<br>
      <b>←/→</b> ±1 fotogramma · <b>Maiusc+←/→</b> ±10 · <b>J/L</b> ±5 s · <b>Spazio</b> play/pausa · <b>,</b> / <b>.</b> velocità 0,1 / 0,25 / 0,5 / 1 / 2×.
      I tasti sono disattivi mentre si scrive in un campo di testo.</p></details>
  </section>`;
  const el = $('anVideo');
  $('anTipi').innerHTML = Object.keys(TIPI).map(k => `<button class="piccolo ann-tipo" data-t="${k}" title="${TIPI[k].nome}${TIPI[k].desc ? ' (' + TIPI[k].desc + ')' : ''}" style="--c:${TIPI[k].col}"><b>${k}</b> ${TIPI[k].nome}</button>`).join('');

  const ingressoVideo = Object.assign(document.createElement('input'), { type: 'file', accept: 'video/mp4,video/quicktime,video/*' });
  const ingressoProg = Object.assign(document.createElement('input'), { type: 'file', accept: '.json,application/json' });

  // ---------------------------------------------------------------- tempo del video
  const haRvfc = 'requestVideoFrameCallback' in HTMLVideoElement.prototype;
  function cbFotogramma(ora, meta) { S.video.t = meta.mediaTime; el.requestVideoFrameCallback(cbFotogramma); }
  if (haRvfc) el.requestVideoFrameCallback(cbFotogramma);
  /** Tempo del fotogramma mostrato (mediaTime reale; senza rVFC currentTime arrotondato alla griglia a 30 fps). */
  const tFrame = () => haRvfc ? S.video.t : Math.floor(el.currentTime * FPS + 1e-3) / FPS;
  const haVideo = () => !!S.video.url && S.video.durata > 0;
  function cerca(t) {
    if (!haVideo()) return;
    t = clamp(t, 0, S.video.durata);
    S.video.nominale = t;
    el.currentTime = Math.min(t + BIAS, S.video.durata);
  }
  function passo(n) {
    if (!haVideo()) return;
    el.pause();
    const base = el.seeking ? S.video.nominale : tFrame();
    cerca(base + n / FPS);
  }
  el.addEventListener('seeked', () => { if (!haRvfc) rich(); });
  el.addEventListener('loadedmetadata', () => {
    S.video.durata = el.duration; S.video.t = 0; S.video.nominale = 0;
    aggiornaTutto();
  });
  el.addEventListener('error', () => { $('anInfo').textContent = 'Video non riproducibile in questo browser (prova un MP4 H.264).'; });
  el.addEventListener('play', () => { $('anPlay').textContent = '❚❚ Pausa'; });
  el.addEventListener('pause', () => { $('anPlay').textContent = '▶ Play'; });
  function velocita(d) { S.velIdx = clamp(S.velIdx + d, 0, VEL.length - 1); el.playbackRate = VEL[S.velIdx]; $('anVel').textContent = String(VEL[S.velIdx]).replace('.', ',') + '×'; }

  // ---------------------------------------------------------------- dati
  function preparaDati() {
    const sr = SD.serie();
    S.pan = null;
    if (!sr || !sr.n) { S.D = null; return; }
    const n = sr.n, G = SWR.G_PER_LSB, P = SWR.DPS_PER_LSB;
    const a = [0, 1, 2].map(() => new Float32Array(n)), g = [0, 1, 2].map(() => new Float32Array(n));
    const am = new Float32Array(n), gm = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < 3; j++) { a[j][i] = sr.d[j][i] * G; g[j][i] = sr.d[j + 3][i] * P; }
      am[i] = Math.hypot(a[0][i], a[1][i], a[2][i]);
      gm[i] = Math.hypot(g[0][i], g[1][i], g[2][i]);
    }
    const sg = SD.es.segmenti[SD.seg];
    S.D = { n, t: sr.t, a, g, am, gm, fs: sg ? sg.odrX10 / 10 : SWR.ODR_HZ_NOMINALE, tMax: sr.t[n - 1] };
    S.vista = { t0: 0, t1: Math.min(30, Math.max(1, S.D.tMax)) };
  }
  function idxT(t) {                              // primo indice con t[i] >= t
    const T = S.D.t; let lo = 0, hi = T.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (T[m] < t) lo = m + 1; else hi = m; }
    return lo;
  }
  function impostaVista(t0, t1) {
    if (!S.D) return;
    const max = Math.max(S.D.tMax, 0.2);
    const span = clamp(t1 - t0, 0.1, max);
    t0 = clamp(t0, 0, Math.max(0, S.D.tMax - span));
    S.vista = { t0, t1: t0 + span };
    rich();
  }
  function zoomAttorno(t, fattore) {
    const { t0, t1 } = S.vista, span = t1 - t0, ns = clamp(span * fattore, 0.1, Math.max(S.D.tMax, 0.2));
    const f = (t - t0) / span;
    impostaVista(t - f * ns, t - f * ns + ns);
  }
  function centraVista(tc) { const span = S.vista.t1 - S.vista.t0; impostaVista(tc - span / 2, tc + span / 2); }
  const tDati = tv => tv + S.offset;
  const tDaVideo = tv => S.offset === null ? null : tv + S.offset;

  // ---------------------------------------------------------------- sincronia
  const eventoX = () => S.eventi.find(e => e.tipo === 'X');
  const syncVideo = () => { const x = eventoX(); return x ? x.t_video_s : null; };
  function ricalcolaOffset() { const v = syncVideo(); if (v !== null && S.syncDati !== null) S.offset = r6(S.syncDati - v); }
  function ritocca(dt) {                          // sposta l'offset; il marcatore dei dati lo segue se c'e' X
    if (S.offset === null) return;
    S.offset = r6(S.offset + dt);
    const v = syncVideo();
    if (v !== null && S.syncDati !== null) S.syncDati = r6(v + S.offset);
    dopo();
  }
  function clicSuGrafico(t, shift) {
    if (!S.D) return;
    if (shift) { if (S.offset !== null && haVideo()) cerca(t - S.offset); return; }
    const i0 = idxT(t - 0.05), i1 = Math.min(S.D.n - 1, idxT(t + 0.05));
    let best = -1, bv = -Infinity;
    for (let i = Math.min(i0, S.D.n - 1); i <= i1; i++) if (S.D.am[i] > bv) { bv = S.D.am[i]; best = i; }
    if (best < 0) return;
    S.syncDati = r6(S.D.t[best]);
    ricalcolaOffset();
    dopo();
  }

  // ---------------------------------------------------------------- eventi
  function snapshot() { S.undo.push(JSON.stringify(S.eventi)); if (S.undo.length > 200) S.undo.shift(); S.redo = []; }
  function ripristina(da, a) {
    if (!da.length) return;
    a.push(JSON.stringify(S.eventi));
    S.eventi = JSON.parse(da.pop());
    if (!S.eventi.some(e => e.id === S.sel)) S.sel = null;
    S.nextId = Math.max(S.nextId, ...S.eventi.map(e => e.id + 1), 1);
    ricalcolaOffset(); dopo();
  }
  const ordina = () => S.eventi.sort((a, b) => a.t_video_s - b.t_video_s || a.id - b.id);
  function aggiungi(tipo) {
    if (!haVideo()) return;
    let t = tFrame();
    if (tipo !== 'X') t = Math.max(0, t - S.anticipo / 1000);
    t = r6(t);
    if (S.eventi.some(e => e.tipo === tipo && Math.abs(e.t_video_s - t) < 1e-4)) return;
    snapshot();
    if (tipo === 'X') S.eventi = S.eventi.filter(e => e.tipo !== 'X');
    const e = { id: S.nextId++, t_video_s: t, tipo, nota: '' };
    S.eventi.push(e); ordina(); S.sel = e.id;
    ricalcolaOffset(); dopo();
  }
  const selezionato = () => S.eventi.find(e => e.id === S.sel);
  function seleziona(id, salta) { S.sel = id; const e = selezionato(); if (e && salta) cerca(e.t_video_s); dopo(true); }
  function elimina() {
    const e = selezionato(); if (!e) return;
    snapshot(); S.eventi = S.eventi.filter(x => x.id !== e.id); S.sel = null; dopo();
  }
  function spostaSel(n) {
    const e = selezionato(); if (!e || !haVideo()) return;
    snapshot();
    e.t_video_s = r6(clamp(e.t_video_s + n / FPS, 0, S.video.durata)); ordina();
    if (e.tipo === 'X') ricalcolaOffset();
    cerca(e.t_video_s); dopo();
  }

  // ---------------------------------------------------------------- salvataggio
  // Copia di sicurezza nel browser (una chiave per annotazione, mai dati grezzi) + autosalvataggio online con debounce di 15 s:
  // 1 scrittura ogni 15 s al massimo mentre si lavora, ben sotto le 20.000 scritture/giorno del piano Spark.
  const OL = () => window.SwimOnline || null;
  const DEBOUNCE_ONLINE_MS = 15000;
  const puoSalvare = () => !!(OL() && OL().puoSalvare && OL().puoSalvare());
  const chiaveAuto = () => OL() && OL().chiave ? 'swimtimer.ann.v2.' + OL().chiave() : null;
  let timerAuto = null, timerOnline = null;
  function autosalva() {
    S.sporco = true; aggiornaOnline();
    clearTimeout(timerAuto);
    timerAuto = setTimeout(() => {
      const k = chiaveAuto(); if (!k) return;
      try { localStorage.setItem(k, JSON.stringify({ v: 2, eventi: S.eventi, offset_s: S.offset, sync_dati_s: S.syncDati, anticipo_ms: S.anticipo, t: Date.now(), sporco: true })); } catch (e) { /* quota o privacy */ }
    }, 300);
    clearTimeout(timerOnline);
    if (puoSalvare()) timerOnline = setTimeout(() => salvaOnline(true), DEBOUNCE_ONLINE_MS);
  }
  function pulisciLocale() { const k = chiaveAuto(); if (k) { try { localStorage.removeItem(k); } catch (e) { /* ignora */ } } }
  /** Se esiste una copia locale non salvata (sporca) e piu' recente dell'annotazione online, propone di ripristinarla. */
  function controllaAutosalvataggio(aggiornatoMs) {
    const k = chiaveAuto(); if (!k) return;
    let a = null; try { a = JSON.parse(localStorage.getItem(k)); } catch (e) { /* ignora */ }
    if (a && a.sporco && a.v === 2 && a.t > (aggiornatoMs || 0) && Array.isArray(a.eventi) &&
        confirm('Trovata una copia locale non ancora salvata online (' + a.eventi.length + ' eventi). Ripristinarla?')) {
      S.eventi = a.eventi; S.offset = a.offset_s ?? null; S.syncDati = a.sync_dati_s ?? null; S.anticipo = a.anticipo_ms || 0;
      $('anAnt').value = S.anticipo;
      S.nextId = Math.max(1, ...S.eventi.map(e => e.id + 1)); ordina(); dopo();
    }
  }
  let salvando = false, ultimoErrore = false;
  async function salvaOnline(auto) {
    clearTimeout(timerOnline);
    if (!OL() || !OL().salva || salvando) return;
    if (auto && !S.sporco) return;
    salvando = true; ultimoErrore = false; aggiornaOnline();
    $('anOnline').textContent = 'Salvataggio in corso…'; $('anOnline').className = 'tenue';
    try {
      await OL().salva(costruisciAnnotazione());
      S.sporco = false; pulisciLocale();
      $('anOnline').textContent = 'Salvato online alle ' + new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); $('anOnline').className = 'ok';
    } catch (e) {
      ultimoErrore = true;
      $('anOnline').textContent = 'Salvataggio online non riuscito: ' + (e && e.message ? e.message : e) + ' (copia locale conservata)'; $('anOnline').className = 'err';
      if (auto) timerOnline = setTimeout(() => salvaOnline(true), DEBOUNCE_ONLINE_MS * 2);
    }
    salvando = false; aggiornaOnline();
  }
  function aggiornaOnline() {
    const b = $('anSalvaOnline'); if (!b) return;
    const o = $('anOnline');
    b.disabled = salvando || !puoSalvare();
    if (salvando || ultimoErrore) return;
    if (!puoSalvare()) { o.textContent = OL() && OL().motivo ? OL().motivo() : ''; o.className = 'tenue'; }
    else if (S.sporco) { o.textContent = 'Modifiche non ancora salvate online'; o.className = 'tenue'; }
  }
  /** Annotazione nel formato Firestore (docs/MODELLO-DATI.md): eventi senza id interno, tempi nel tempo del video. */
  function costruisciAnnotazione() {
    return {
      eventi: S.eventi.map(e => ({ tipo: e.tipo, t_video_s: e.t_video_s, nota: e.nota || '' })),
      offset_s: S.offset,
      sync: { video_s: syncVideo(), dati_s: S.syncDati },
      anticipo_ms: S.anticipo,
      segmento: Number.isInteger(SD.seg) ? SD.seg : null
    };
  }
  /** Carica nello stato un'annotazione letta da Firestore (o un'annotazione vuota). */
  function caricaAnnotazione(a) {
    a = a || {};
    S.eventi = (a.eventi || []).filter(e => e && TIPI[e.tipo] && Number.isFinite(e.t_video_s)).map((e, i) => ({ id: i + 1, t_video_s: e.t_video_s, tipo: e.tipo, nota: e.nota || '' }));
    S.nextId = S.eventi.length + 1; ordina();
    S.offset = Number.isFinite(a.offset_s) ? a.offset_s : null;
    S.syncDati = a.sync && Number.isFinite(a.sync.dati_s) ? a.sync.dati_s : null;
    S.anticipo = clamp(Number(a.anticipo_ms) || 0, 0, 2000); $('anAnt').value = S.anticipo;
    S.sel = null; S.undo = []; S.redo = []; S.sporco = false; ultimoErrore = false;
    if (SD.es && Number.isInteger(a.segmento) && a.segmento in SD.es.segmenti && SD.seg !== a.segmento) SD.scegliSegmento(a.segmento);
    aggiornaTutto(); aggiornaOnline();
  }
  /** Azzera il contesto (cambio di sessione/annotazione): video, eventi, avvisi. */
  function azzera() {
    clearTimeout(timerAuto); clearTimeout(timerOnline);
    el.pause();
    if (S.video.url) URL.revokeObjectURL(S.video.url);
    S.video = { nome: null, durata: 0, dimensione: 0, url: null, t: 0, nominale: 0 };
    el.removeAttribute('src'); el.load();
    S.eventi = []; S.sel = null; S.undo = []; S.redo = []; S.offset = null; S.syncDati = null; S.progetto = null; S.avviso = ''; S.sporco = false; ultimoErrore = false;
    msgInfo = ''; $('anOnline').textContent = ''; aggiornaTutto();
  }
  const nomeBase = () => (S.video.nome || 'progetto').replace(/\.[^.]+$/, '');
  function costruisciProgetto() {
    return {
      versione: 1,
      video: { nome: S.video.nome, durata_s: S.video.durata, dimensione: S.video.dimensione },
      dati: { nome: SD.nome, sha256_primi_mb: SD.impronta, segmento: SD.seg, fs: S.D ? S.D.fs : null },
      offset_s: S.offset,
      sync: { video_s: syncVideo(), dati_s: S.syncDati },
      eventi: S.eventi.map(e => ({ id: e.id, t_video_s: e.t_video_s, tipo: e.tipo, nota: e.nota || '' }))
    };
  }
  async function salvaProgetto() {
    const n = await SD.salva(nomeBase() + '.swimproj.json', [JSON.stringify(costruisciProgetto(), null, 2)], 'Progetto di annotazione SwimTimer', '.json', 'application/json');
    if (n) info('Progetto salvato: ' + n);
  }
  const csvCampo = s => /[",\n\r]/.test(s) ? '"' + String(s).replace(/"/g, '""') + '"' : String(s);
  async function esportaCsv() {
    const righe = ['t_video_s,t_dati_s,tipo,nota'];
    for (const e of S.eventi) righe.push([e.t_video_s.toFixed(6), S.offset === null ? '' : (e.t_video_s + S.offset).toFixed(6), e.tipo, csvCampo(e.nota || '')].join(','));
    const n = await SD.salva('eventi.csv', [righe.join('\n') + '\n'], 'Eventi (CSV)', '.csv', 'text/csv');
    if (n) info('Esportati ' + S.eventi.length + ' eventi in ' + n + (S.offset === null ? ' (t_dati_s vuoto: non allineato)' : ''));
  }
  async function apriProgetto(f) {
    let p;
    try { p = JSON.parse(await f.text()); } catch (e) { return info('File di progetto non valido (JSON).', true); }
    if (!p || p.versione !== 1 || !Array.isArray(p.eventi)) return info('Progetto non riconosciuto (versione o eventi mancanti).', true);
    if ((S.eventi.length) && !confirm('Sostituire i ' + S.eventi.length + ' eventi attuali con quelli del progetto?')) return;
    snapshot();
    S.eventi = p.eventi.filter(e => e && TIPI[e.tipo] && Number.isFinite(e.t_video_s)).map(e => ({ id: e.id | 0, t_video_s: e.t_video_s, tipo: e.tipo, nota: e.nota || '' }));
    const visti = new Set(); S.eventi.forEach(e => { if (visti.has(e.id)) e.id = 0; visti.add(e.id); });
    let m = Math.max(0, ...S.eventi.map(e => e.id)); S.eventi.forEach(e => { if (!e.id) e.id = ++m; });
    S.nextId = m + 1; ordina();
    S.offset = Number.isFinite(p.offset_s) ? p.offset_s : null;
    S.syncDati = p.sync && Number.isFinite(p.sync.dati_s) ? p.sync.dati_s : null;
    S.sel = null; S.progetto = p;
    if (SD.es && p.dati && Number.isFinite(p.dati.segmento) && p.dati.segmento in SD.es.segmenti && SD.seg !== p.dati.segmento) SD.scegliSegmento(p.dati.segmento);
    dopo();
    info('Progetto caricato: ' + S.eventi.length + ' eventi.' + coerenza());
  }
  function coerenza() {                           // avvisi se video/dati aperti non coincidono con quelli del progetto
    const p = S.progetto; if (!p) return '';
    const av = [];
    if (S.video.nome && p.video && (p.video.nome !== S.video.nome || p.video.dimensione !== S.video.dimensione)) av.push('il video aperto (' + S.video.nome + ') non coincide con quello del progetto (' + p.video.nome + ')');
    if (SD.es && p.dati) {
      if (p.dati.sha256_primi_mb && SD.impronta && p.dati.sha256_primi_mb !== SD.impronta) av.push('il file .swr aperto ha un\'impronta diversa da quella del progetto (' + p.dati.nome + ')');
      if (p.dati.segmento !== null && p.dati.segmento !== undefined && p.dati.segmento !== SD.seg) av.push('segmento diverso (progetto: ' + p.dati.segmento + ')');
    }
    return av.length ? ' ATTENZIONE: ' + av.join('; ') + '.' : '';
  }

  // ---------------------------------------------------------------- interfaccia: testi
  let msgInfo = '', msgErr = false;
  function info(t, err) { msgInfo = t; msgErr = !!err; aggiornaInfo(); }
  function aggiornaInfo() {
    const parti = [];
    parti.push('Dati: ' + (SD.es ? '<b>' + esc(SD.nome) + '</b>' + (S.D ? ' · segmento ' + SD.seg + ' · ' + S.D.tMax.toFixed(1) + ' s · ' + S.D.fs.toFixed(1) + ' Hz' : ' · nessun dato nel segmento') : 'nessun .swr aperto'));
    parti.push('Video: ' + (S.video.nome ? '<b>' + esc(S.video.nome) + '</b> · ' + S.video.durata.toFixed(1) + ' s' : 'nessun video'));
    const c = coerenza();
    // solo audio (videoWidth 0): tipico di un MP4 HEVC/H.265 da telefono che il browser non decodifica
    const soloAudio = haVideo() && el.readyState >= 1 && !el.videoWidth
      ? '<div class="err">Il browser riproduce solo l\'audio di questo video: probabilmente è HEVC/H.265. Convertilo in H.264 (es. HandBrake, preset «Fast 1080p30») o registra con il telefono in «Più compatibile».</div>' : '';
    $('anInfo').innerHTML = parti.join(' &nbsp;·&nbsp; ') + soloAudio + (msgInfo ? '<div class="' + (msgErr ? 'err' : 'ok') + '">' + esc(msgInfo) + '</div>' : '') + (c ? '<div class="err">' + esc(c) + '</div>' : '') + (S.avviso ? '<div class="err">' + esc(S.avviso) + '</div>' : '');
  }
  function aggiornaSegmenti() {
    const sel = $('anSeg');
    if (!SD.es) { sel.hidden = true; return; }
    const segs = SWR.segmentiConDati(SD.es);
    sel.hidden = segs.length < 2;
    sel.innerHTML = segs.map(s => `<option value="${s}"${s === SD.seg ? ' selected' : ''}>Segmento ${s} · ${SD.durata(s).toFixed(1)} s</option>`).join('');
  }
  function aggiornaTesti() {
    const t = haVideo() ? tFrame() : 0;
    $('anTempo').textContent = haVideo() ? `${t.toFixed(3)} s · fotogramma ${Math.round(t * FPS)}` + (S.offset !== null ? ` · dati ${tDati(t).toFixed(3)} s` : '') : '–';
    const v = syncVideo();
    $('anSyV').textContent = v === null ? '–' : fmtT(v);
    $('anSyD').textContent = S.syncDati === null ? '–' : fmtT(S.syncDati);
    const off = $('anOff');
    if (document.activeElement !== off) off.value = S.offset === null ? '' : (S.offset * 1000).toFixed(1);
    off.disabled = !S.D;
    radice.querySelectorAll('[data-o]').forEach(b => { b.disabled = S.offset === null; });
    $('anAlinea').textContent = S.offset !== null ? 'Allineato: i grafici seguono il video e gli eventi compaiono anche sui dati.'
      : 'Non allineato: nel video, sul fotogramma del 5° tocco, premi X; nei grafici clicca il 5° picco.' + (v !== null && S.syncDati === null ? ' (X messo: manca il picco)' : v === null && S.syncDati !== null ? ' (picco messo: manca X)' : '');
  }
  function aggiornaEventi() {
    const cont = {}; S.eventi.forEach(e => cont[e.tipo] = (cont[e.tipo] || 0) + 1);
    $('anCont').innerHTML = Object.keys(TIPI).map(k => `<span class="ann-chip" style="--c:${TIPI[k].col}"><b>${k}</b> ${cont[k] || 0}</span>`).join('');
    $('anNEv').textContent = '(' + S.eventi.length + ')';
    const sel = selezionato(), nota = $('anNota');
    nota.disabled = !sel; if (document.activeElement !== nota) nota.value = sel ? sel.nota || '' : '';
    $('anUndo').disabled = !S.undo.length; $('anRedo').disabled = !S.redo.length; $('anElimina').disabled = !sel;
    $('anLista').innerHTML = S.eventi.map(e => `<li data-id="${e.id}" class="${e.id === S.sel ? 'sel' : ''}" style="--c:${TIPI[e.tipo].col}"><b>${e.tipo}</b> <span class="mono">${e.t_video_s.toFixed(3)} s</span> <span class="tenue">f${Math.round(e.t_video_s * FPS)}</span>${e.nota ? ' · ' + esc(e.nota) : ''}</li>`).join('');
    if (sel) { const li = $('anLista').querySelector('li.sel'); if (li) li.scrollIntoView({ block: 'nearest' }); }
  }
  function aggiornaTutto() { aggiornaInfo(); aggiornaSegmenti(); aggiornaTesti(); aggiornaEventi(); $('anVuoto').hidden = !!S.video.url; rich(); }
  function dopo() { aggiornaTutto(); autosalva(); }

  // ---------------------------------------------------------------- grafici
  let sporco = true;
  function rich() { sporco = true; }
  let C = {};
  function colori() {
    const cs = getComputedStyle(document.documentElement), v = n => cs.getPropertyValue(n).trim();
    C = { griglia: v('--griglia') || '#e9edf2', tenue: v('--tenue') || '#5d6b7a', testo: v('--testo') || '#000', acc: v('--accento') || '#0a7fc2', x: v('--x') || '#e5484d', y: v('--y') || '#2f9e5b', z: v('--z') || '#3b74f0', bordo: v('--bordo') || '#ccc', sfondo: v('--card-2') || '#f7f9fb' };
  }
  function preparaCanvas(cv) {
    const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
    if (!w || !h) return null;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  }
  const passoNice = (rng, n) => { const raw = rng / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p; };
  const decimali = st => st >= 1 ? 0 : Math.min(4, Math.ceil(-Math.log10(st)));
  const FONT = '10.5px ui-monospace, "JetBrains Mono", Menlo, monospace';
  const LANE = { L: 46, R: 8, T: 6, B: 16 };

  function etichettaT(t, st) {
    if (st >= 60 || t >= 600 && st >= 1) { const m = Math.floor(t / 60); return m + ':' + String(Math.round(t - m * 60)).padStart(2, '0'); }
    return t.toFixed(decimali(st));
  }
  function disegnaLane(cv, serie, o) {
    const g = preparaCanvas(cv); if (!g) return;
    const { ctx, w, h } = g, { L, R, T, B } = LANE, pw = w - L - R, ph = h - T - B;
    ctx.font = FONT; ctx.textBaseline = 'middle';
    if (!S.D) { ctx.fillStyle = C.tenue; ctx.textAlign = 'center'; ctx.fillText('Apri un .swr per vedere i dati', w / 2, h / 2); return; }
    const { t0, t1 } = S.vista, span = t1 - t0, D = S.D;
    const i0 = Math.max(0, idxT(t0) - 1), i1 = Math.min(D.n - 1, idxT(t1) + 1);
    let lo = Infinity, hi = -Infinity;
    for (const s of serie) for (let i = i0; i <= i1; i++) { const v = s.a[i]; if (v < lo) lo = v; if (v > hi) hi = v; }
    if (o.zero) lo = Math.min(lo, 0);
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    let rng = hi - lo;
    if (rng < o.minRange) { const c = (hi + lo) / 2; lo = c - o.minRange / 2; hi = c + o.minRange / 2; if (o.zero) { lo = 0; hi = Math.max(hi, o.minRange); } }
    else { hi += rng * 0.05; if (!o.zero) lo -= rng * 0.05; }
    const y = v => T + ph * (1 - (v - lo) / (hi - lo)), x = t => L + (t - t0) / span * pw;
    // griglia
    ctx.lineWidth = 1; ctx.textAlign = 'right';
    const sy = passoNice(hi - lo, 4);
    for (let v = Math.ceil(lo / sy) * sy; v <= hi + 1e-9; v += sy) {
      const yy = Math.round(y(v)) + 0.5;
      ctx.strokeStyle = C.griglia; ctx.beginPath(); ctx.moveTo(L, yy); ctx.lineTo(w - R, yy); ctx.stroke();
      ctx.fillStyle = C.tenue; ctx.fillText((+v.toFixed(3)) + '', L - 4, yy);
    }
    const sx = passoNice(span, Math.max(2, pw / 90)); ctx.textAlign = 'center';
    for (let t = Math.ceil(t0 / sx) * sx; t <= t1 + 1e-9; t += sx) {
      const xx = Math.round(x(t)) + 0.5;
      ctx.strokeStyle = C.griglia; ctx.beginPath(); ctx.moveTo(xx, T); ctx.lineTo(xx, T + ph); ctx.stroke();
      ctx.fillStyle = C.tenue; ctx.fillText(etichettaT(t, sx), xx, h - B / 2);
    }
    ctx.fillStyle = C.tenue; ctx.textAlign = 'left'; ctx.fillText(o.unita, L + 4, T + 8);
    // serie
    ctx.save(); ctx.beginPath(); ctx.rect(L, T, pw, ph); ctx.clip();
    const nvis = i1 - i0 + 1;
    for (const s of serie) {
      ctx.strokeStyle = s.col; ctx.fillStyle = s.col; ctx.lineWidth = 1.2; ctx.beginPath();
      if (nvis > pw * 1.5) {                       // decimazione min/max per colonna
        const mn = new Float32Array(pw).fill(Infinity), mx = new Float32Array(pw).fill(-Infinity);
        for (let i = i0; i <= i1; i++) {
          const c = Math.floor((D.t[i] - t0) / span * pw); if (c < 0 || c >= pw) continue;
          const v = s.a[i]; if (v < mn[c]) mn[c] = v; if (v > mx[c]) mx[c] = v;
        }
        for (let c = 0; c < pw; c++) if (mn[c] !== Infinity) { const xx = L + c + 0.5; ctx.moveTo(xx, y(mx[c])); ctx.lineTo(xx, Math.max(y(mn[c]), y(mx[c]) + 1)); }
        ctx.stroke();
      } else {
        for (let i = i0; i <= i1; i++) { const xx = x(D.t[i]), yy = y(s.a[i]); if (i === i0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy); }
        ctx.stroke();
        if (pw / Math.max(1, nvis) > 5) for (let i = i0; i <= i1; i++) { ctx.beginPath(); ctx.arc(x(D.t[i]), y(s.a[i]), 1.8, 0, 6.2832); ctx.fill(); }
      }
    }
    sovrapposizioni(ctx, x, T, ph, t0, t1, span < 90);
    ctx.restore();
    if (serie.length > 1) { ctx.textAlign = 'left'; let xx = L + 40; for (const [n, c] of [['x', C.x], ['y', C.y], ['z', C.z]]) { ctx.fillStyle = c; ctx.fillText('● ' + n, xx, T + 8); xx += 30; } }
  }
  function sovrapposizioni(ctx, x, T, ph, t0, t1, lettere) {
    ctx.lineWidth = 1;
    if (S.syncDati !== null && S.syncDati >= t0 && S.syncDati <= t1) {
      ctx.strokeStyle = TIPI.X.col; ctx.setLineDash([4, 3]); ctx.beginPath(); const xx = Math.round(x(S.syncDati)) + 0.5; ctx.moveTo(xx, T); ctx.lineTo(xx, T + ph); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = TIPI.X.col; ctx.textAlign = 'left'; ctx.fillText('sync', xx + 3, T + ph - 6);
    }
    if (S.offset === null) return;
    for (const e of S.eventi) {
      const td = e.t_video_s + S.offset; if (td < t0 || td > t1) continue;
      const xx = Math.round(x(td)) + 0.5, col = TIPI[e.tipo].col;
      ctx.strokeStyle = col; ctx.lineWidth = e.id === S.sel ? 2.5 : 1; ctx.beginPath(); ctx.moveTo(xx, T); ctx.lineTo(xx, T + ph); ctx.stroke();
      if (lettere) { ctx.fillStyle = col; ctx.textAlign = 'center'; ctx.font = 'bold ' + FONT; ctx.fillText(e.tipo, xx, T + 7); ctx.font = FONT; }
    }
    if (haVideo()) {
      const tc = tFrame() + S.offset;
      if (tc >= t0 && tc <= t1) { const xx = Math.round(x(tc)) + 0.5; ctx.strokeStyle = '#ff3b4a'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(xx, T); ctx.lineTo(xx, T + ph); ctx.stroke(); }
    }
    ctx.lineWidth = 1;
  }
  function disegnaPanoramica() {
    const cv = $('anPan'), g = preparaCanvas(cv); if (!g) return;
    const { ctx, w, h } = g, D = S.D, L = LANE.L, R = LANE.R, pw = w - L - R, T = 3, ph = h - 6;
    ctx.font = FONT; ctx.textBaseline = 'middle';
    if (!D) return;
    if (!S.pan || S.pan.w !== pw) {
      const mn = new Float32Array(pw).fill(Infinity), mx = new Float32Array(pw).fill(-Infinity); let top = 1;
      for (let i = 0; i < D.n; i++) { const c = Math.min(pw - 1, Math.floor(D.t[i] / Math.max(D.tMax, 1e-9) * pw)); const v = D.am[i]; if (v < mn[c]) mn[c] = v; if (v > mx[c]) mx[c] = v; if (v > top) top = v; }
      S.pan = { w: pw, mn, mx, top };
    }
    const { mn, mx, top } = S.pan, y = v => T + ph * (1 - v / top), tx = t => L + t / Math.max(D.tMax, 1e-9) * pw;
    ctx.strokeStyle = C.acc; ctx.lineWidth = 1; ctx.beginPath();
    for (let c = 0; c < pw; c++) if (mn[c] !== Infinity) { ctx.moveTo(L + c + 0.5, y(mx[c])); ctx.lineTo(L + c + 0.5, Math.max(y(mn[c]), y(mx[c]) + 1)); }
    ctx.stroke();
    if (S.syncDati !== null) { ctx.strokeStyle = TIPI.X.col; ctx.beginPath(); ctx.moveTo(tx(S.syncDati) + 0.5, T); ctx.lineTo(tx(S.syncDati) + 0.5, T + ph); ctx.stroke(); }
    if (S.offset !== null) {
      for (const e of S.eventi) { const td = e.t_video_s + S.offset; if (td < 0 || td > D.tMax) continue; ctx.fillStyle = TIPI[e.tipo].col; ctx.fillRect(Math.round(tx(td)), T + ph - 5, 2, 5); }
      if (haVideo()) { ctx.strokeStyle = '#ff3b4a'; ctx.beginPath(); ctx.moveTo(tx(tFrame() + S.offset) + 0.5, T); ctx.lineTo(tx(tFrame() + S.offset) + 0.5, T + ph); ctx.stroke(); }
    }
    const xa = tx(S.vista.t0), xb = tx(S.vista.t1);
    ctx.fillStyle = 'rgba(56,189,248,.16)'; ctx.fillRect(xa, 0, Math.max(2, xb - xa), h);
    ctx.strokeStyle = C.acc; ctx.lineWidth = 1.5; ctx.strokeRect(xa + 0.5, 0.5, Math.max(2, xb - xa) - 1, h - 1);
  }
  function disegnaStriscia() {
    const cv = $('anStr'), g = preparaCanvas(cv); if (!g) return;
    const { ctx, w, h } = g; ctx.font = FONT; ctx.textBaseline = 'middle';
    const dur = S.video.durata; if (!dur) return;
    const [w0, w1] = finestraStriscia(), span = w1 - w0, x = t => 8 + (t - w0) / span * (w - 16);
    ctx.fillStyle = C.sfondo; ctx.fillRect(0, 0, w, h);
    const sx = passoNice(span, Math.max(2, w / 90)); ctx.textAlign = 'center';
    for (let t = Math.ceil(w0 / sx) * sx; t <= w1 + 1e-9; t += sx) { const xx = Math.round(x(t)) + 0.5; ctx.strokeStyle = C.griglia; ctx.beginPath(); ctx.moveTo(xx, 14); ctx.lineTo(xx, h); ctx.stroke(); ctx.fillStyle = C.tenue; ctx.fillText(etichettaT(t, sx), xx, 7); }
    for (const e of S.eventi) {
      if (e.t_video_s < w0 || e.t_video_s > w1) continue;
      const xx = Math.round(x(e.t_video_s)) + 0.5, col = TIPI[e.tipo].col;
      ctx.strokeStyle = col; ctx.lineWidth = e.id === S.sel ? 3 : 1.5; ctx.beginPath(); ctx.moveTo(xx, 16); ctx.lineTo(xx, h - 2); ctx.stroke();
      if (span <= 120) { ctx.fillStyle = col; ctx.font = 'bold ' + FONT; ctx.fillText(e.tipo, xx, h - 9); ctx.font = FONT; }
    }
    const xc = Math.round(x(haVideo() ? tFrame() : 0)) + 0.5; ctx.strokeStyle = '#ff3b4a'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(xc, 12); ctx.lineTo(xc, h); ctx.stroke(); ctx.lineWidth = 1;
  }
  function finestraStriscia() {
    const dur = S.video.durata, sp = S.passoStriscia;
    if (!sp || sp >= dur) return [0, dur];
    const w0 = clamp(tFrame() - sp / 2, 0, dur - sp); return [w0, w0 + sp];
  }
  function disegna() {
    colori();
    const D = S.D, vis = !$('anGrafBox').classList.contains('nascosto');
    if (vis) {
      disegnaLane($('anAcc'), S.modoAcc === 'mod' ? [{ a: D && D.am, col: C.acc }] : D ? [{ a: D.a[0], col: C.x }, { a: D.a[1], col: C.y }, { a: D.a[2], col: C.z }] : [], { zero: S.modoAcc === 'mod', minRange: S.modoAcc === 'mod' ? 2 : 2, unita: S.modoAcc === 'mod' ? '|acc| g' : 'acc g' });
      disegnaLane($('anGyr'), S.modoGyr === 'mod' ? [{ a: D && D.gm, col: C.acc }] : D ? [{ a: D.g[0], col: C.x }, { a: D.g[1], col: C.y }, { a: D.g[2], col: C.z }] : [], { zero: S.modoGyr === 'mod', minRange: 100, unita: S.modoGyr === 'mod' ? '|gyro| dps' : 'gyro dps' });
      disegnaPanoramica();
    }
    disegnaStriscia();
  }

  // ---------------------------------------------------------------- gesti sui grafici
  function gestiLane(cv) {
    const P = new Map(); let mosso = false, multi = false, dist0 = 0, ultimoX = 0, inizio = null;
    const rect = () => cv.getBoundingClientRect();
    const tDaX = cx => { const r = rect(), pw = r.width - LANE.L - LANE.R; return S.vista.t0 + (cx - r.left - LANE.L) / pw * (S.vista.t1 - S.vista.t0); };
    cv.addEventListener('wheel', e => {
      if (!S.D) return; e.preventDefault();
      zoomAttorno(tDaX(e.clientX), Math.exp(e.deltaY * 0.0015));
    }, { passive: false });
    cv.addEventListener('pointerdown', e => {
      if (!S.D) return; cv.setPointerCapture(e.pointerId); P.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (P.size === 1) { mosso = false; multi = false; ultimoX = e.clientX; inizio = { x: e.clientX, y: e.clientY }; }
      else { multi = true; const [a, b] = [...P.values()]; dist0 = Math.hypot(a.x - b.x, a.y - b.y); }
    });
    cv.addEventListener('pointermove', e => {
      if (!P.has(e.pointerId)) return;
      P.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (P.size >= 2) {
        const [a, b] = [...P.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (dist0 > 0 && d > 0) zoomAttorno(tDaX((a.x + b.x) / 2), dist0 / d);
        dist0 = d; mosso = true;
      } else if (P.size === 1) {
        if (inizio && Math.hypot(e.clientX - inizio.x, e.clientY - inizio.y) > 4) mosso = true;
        if (mosso && !multi) { const r = rect(), pw = r.width - LANE.L - LANE.R, dt = -(e.clientX - ultimoX) / pw * (S.vista.t1 - S.vista.t0); impostaVista(S.vista.t0 + dt, S.vista.t1 + dt); }
        ultimoX = e.clientX;
      }
    });
    const fine = e => {
      if (!P.has(e.pointerId)) return;
      P.delete(e.pointerId);
      if (!P.size && !mosso && !multi && e.type === 'pointerup') {
        const r = rect(); if (e.clientX - r.left >= LANE.L) clicSuGrafico(tDaX(e.clientX), e.shiftKey);
      }
    };
    cv.addEventListener('pointerup', fine); cv.addEventListener('pointercancel', fine);
  }
  function gestiPanoramica() {
    const cv = $('anPan'); let giu = false;
    const vai = e => { if (!S.D) return; const r = cv.getBoundingClientRect(), pw = r.width - LANE.L - LANE.R; centraVista((e.clientX - r.left - LANE.L) / pw * S.D.tMax); };
    cv.addEventListener('pointerdown', e => { giu = true; cv.setPointerCapture(e.pointerId); vai(e); });
    cv.addEventListener('pointermove', e => { if (giu) vai(e); });
    cv.addEventListener('pointerup', () => { giu = false; }); cv.addEventListener('pointercancel', () => { giu = false; });
  }
  function gestiStriscia() {
    const cv = $('anStr'); let giu = false;
    const tDaX = cx => { const r = cv.getBoundingClientRect(), [w0, w1] = finestraStriscia(); return w0 + (cx - r.left - 8) / (r.width - 16) * (w1 - w0); };
    cv.addEventListener('pointerdown', e => {
      if (!haVideo()) return; cv.setPointerCapture(e.pointerId);
      const r = cv.getBoundingClientRect(), [w0, w1] = finestraStriscia(), px = e.clientX - r.left;
      let best = null, bd = 7;
      for (const ev of S.eventi) { const d = Math.abs(8 + (ev.t_video_s - w0) / (w1 - w0) * (r.width - 16) - px); if (d < bd) { bd = d; best = ev; } }
      if (best) { seleziona(best.id, true); giu = false; } else { giu = true; el.pause(); cerca(tDaX(e.clientX)); }
    });
    cv.addEventListener('pointermove', e => { if (giu) cerca(tDaX(e.clientX)); });
    cv.addEventListener('pointerup', () => { giu = false; }); cv.addEventListener('pointercancel', () => { giu = false; });
  }
  ['anAcc', 'anGyr'].forEach(id => gestiLane($(id))); gestiPanoramica(); gestiStriscia();

  // ---------------------------------------------------------------- comandi e tastiera
  $('anSalvaOnline').addEventListener('click', () => salvaOnline(false));
  window.addEventListener('beforeunload', e => { if (S.sporco && puoSalvare()) { e.preventDefault(); e.returnValue = ''; } });
  $('anSeg').addEventListener('change', e => SD.scegliSegmento(Number(e.target.value)));
  $('anVideoBtn').addEventListener('click', () => ingressoVideo.click());
  ingressoVideo.addEventListener('change', () => {
    const f = ingressoVideo.files[0]; ingressoVideo.value = ''; if (!f) return;
    if (S.video.url) URL.revokeObjectURL(S.video.url);
    S.video = { nome: f.name, durata: 0, dimensione: f.size, url: URL.createObjectURL(f), t: 0, nominale: 0 };
    el.src = S.video.url; el.playbackRate = VEL[S.velIdx];
    S.avviso = '';
    info(''); aggiornaTutto();
    if (OL() && OL().verificaVideo) {
      const per = (fatti, tot) => info('Verifica impronta del video: ' + Math.round(100 * fatti / tot) + '%');
      Promise.resolve(OL().verificaVideo(f, per)).then(r => {
        S.avviso = r && r.avviso ? r.avviso : '';
        info(r && r.ok ? 'Video verificato: coincide con quello registrato (sha256 uguale).' : '', false);
      }).catch(e => { S.avviso = 'Verifica del video non riuscita: ' + e.message; info(''); });
    }
  });
  $('anProgApri').addEventListener('click', () => ingressoProg.click());
  ingressoProg.addEventListener('change', () => { const f = ingressoProg.files[0]; ingressoProg.value = ''; if (f) apriProgetto(f); });
  $('anProgSalva').addEventListener('click', () => salvaProgetto().catch(e => info('Salvataggio non riuscito: ' + e.message, true)));
  $('anCsv').addEventListener('click', () => esportaCsv().catch(e => info('Esportazione non riuscita: ' + e.message, true)));
  $('anZoom').addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b || !S.D) return;
    const z = Number(b.dataset.z), c = S.offset !== null && haVideo() ? tFrame() + S.offset : (S.vista.t0 + S.vista.t1) / 2;
    if (!z) impostaVista(0, S.D.tMax); else impostaVista(c - z / 2, c + z / 2);
  });
  $('anSegui').addEventListener('change', e => { S.segui = e.target.checked; });
  $('anNascondi').addEventListener('click', e => { const n = $('anGrafBox').classList.toggle('nascosto'); e.currentTarget.textContent = n ? 'Mostra grafici' : 'Nascondi grafici'; rich(); });
  $('anModoAcc').addEventListener('change', e => { S.modoAcc = e.target.value; rich(); });
  $('anModoGyr').addEventListener('change', e => { S.modoGyr = e.target.value; rich(); });
  $('anStrSpan').addEventListener('change', e => { S.passoStriscia = Number(e.target.value); rich(); });
  $('anPlay').addEventListener('click', () => { if (haVideo()) { if (el.paused) el.play(); else el.pause(); } });
  $('anVelMeno').addEventListener('click', () => velocita(-1)); $('anVelPiu').addEventListener('click', () => velocita(1));
  radice.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.p) passo(Number(b.dataset.p));
    else if (b.dataset.s) cerca((el.seeking ? S.video.nominale : tFrame()) + Number(b.dataset.s));
    else if (b.dataset.t) aggiungi(b.dataset.t);
    else if (b.dataset.o) ritocca({ '-s': -1 / (S.D ? S.D.fs : SWR.ODR_HZ_NOMINALE), '+s': 1 / (S.D ? S.D.fs : SWR.ODR_HZ_NOMINALE), '-f': -1 / FPS, '+f': 1 / FPS }[b.dataset.o]);
    b.blur();                                       // la barra spaziatrice non deve riattivare l'ultimo pulsante
  });
  $('anUndo').addEventListener('click', () => ripristina(S.undo, S.redo));
  $('anRedo').addEventListener('click', () => ripristina(S.redo, S.undo));
  $('anElimina').addEventListener('click', elimina);
  $('anAnt').addEventListener('change', e => { S.anticipo = clamp(Number(e.target.value) || 0, 0, 2000); e.target.value = S.anticipo; });
  $('anOff').addEventListener('change', e => {
    const ms = parseFloat(e.target.value); if (!Number.isFinite(ms)) return;
    if (S.offset === null) { S.offset = r6(ms / 1000); const v = syncVideo(); if (v !== null) S.syncDati = r6(v + S.offset); dopo(); } else ritocca(r6(ms / 1000) - S.offset);
  });
  $('anNota').addEventListener('change', e => { const s = selezionato(); if (s) { snapshot(); s.nota = e.target.value; dopo(); } });
  $('anLista').addEventListener('click', e => { const li = e.target.closest('li'); if (li) seleziona(Number(li.dataset.id), true); });

  document.addEventListener('keydown', e => {
    if (radice.hidden || e.ctrlKey || e.metaKey) return;
    const tg = e.target;
    if (tg && tg.closest && tg.closest('input:not([type=checkbox]),textarea,select,[contenteditable="true"]')) return;
    const k = e.key, kl = k.length === 1 ? k.toLowerCase() : k;
    let ok = true;
    if (k === 'ArrowLeft' || k === 'ArrowRight') {
      const s = k === 'ArrowLeft' ? -1 : 1;
      if (e.altKey) spostaSel(s); else passo(s * (e.shiftKey ? 10 : 1));
    } else if (e.altKey) ok = false;
    else if (kl === 'j' || kl === 'l') cerca((el.seeking ? S.video.nominale : tFrame()) + (kl === 'j' ? -5 : 5));
    else if (k === ' ') { if (haVideo()) { if (el.paused) el.play(); else el.pause(); } }
    else if (k === ',') velocita(-1); else if (k === '.') velocita(1);
    else if (kl === 'z') { if (e.shiftKey) ripristina(S.redo, S.undo); else ripristina(S.undo, S.redo); }
    else if (k === 'Delete') elimina();
    else if ('brvfpax'.includes(kl) && kl.length === 1 && !e.repeat) aggiungi(kl.toUpperCase());
    else ok = false;
    if (ok) e.preventDefault();
  });
  document.addEventListener('keyup', e => { if (!radice.hidden && e.key === ' ' && !/INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || '')) e.preventDefault(); });

  // ---------------------------------------------------------------- ciclo
  let ultimoT = -1;
  function ciclo() {
    requestAnimationFrame(ciclo);
    if (radice.hidden) return;
    const t = haVideo() ? tFrame() : 0;
    if (t !== ultimoT) {
      ultimoT = t; aggiornaTesti(); rich();
      if (S.segui && S.offset !== null && S.D && haVideo()) {
        const tc = t + S.offset, { t0, t1 } = S.vista, m = (t1 - t0) * 0.05;
        if (tc < t0 + m || tc > t1 - m) centraVista(tc);
      }
    }
    if (sporco) { sporco = false; try { disegna(); } catch (e) { console.error(e); } }
  }
  new ResizeObserver(() => { S.pan = null; rich(); }).observe(radice);
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', rich);
  SD.su(() => { preparaDati(); aggiornaTutto(); });
  velocita(0);
  preparaDati(); aggiornaTutto();
  requestAnimationFrame(ciclo);
  // visibilita' della scheda: ridisegna quando torna visibile
  new MutationObserver(() => { S.pan = null; rich(); }).observe(radice, { attributes: true, attributeFilter: ['hidden'] });
  window.SwimAnnotazione = { stato: S, carica: caricaAnnotazione, azzera, salvaOra: () => salvaOnline(false), controllaCopiaLocale: controllaAutosalvataggio, aggiorna: () => { aggiornaTutto(); aggiornaOnline(); } };
})();
