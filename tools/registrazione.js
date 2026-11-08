/* SwimTimer - scheda «Registrazione»: scarico via USB (Web Serial) della memoria della XIAO e apertura di file .swr.
 * La porta seriale è quella unica della pagina (window.UsbXiao, definita in index.html con il filtro USB della XIAO): qui non si apre
 * nessuna porta. Protocollo seriale (firmware 0.5.0, vedi firmware/xiao-stream/scarica.py): MEM -> "K mem <usate> <totali>";
 * DUMP -> "SWR1 <pagine>\n", pagine da 256 byte, "\nEND <pagine>\n"; ERASE -> "K erase ok" (5-15 s).
 * Espone window.SwimDati (il .swr corrente, condiviso con la scheda Annotazione). I dati restano nel browser. */
(function () {
  'use strict';
  const SWR = window.SWR, UsbXiao = window.UsbXiao;
  const radice = document.getElementById('vistaSwr');
  if (!radice || !SWR || !UsbXiao) return;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const pad = n => String(n).padStart(2, '0');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const marcaTempo = () => { const d = new Date(); return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '_' + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds()); };

  // ---------------------------------------------------------------- dati condivisi
  const ascoltatori = [];
  async function impronta(bytes) {           // SHA-256 del primo MiB (identifica il file senza incorporarlo)
    try {
      if (!(window.crypto && crypto.subtle)) return null;
      const h = await crypto.subtle.digest('SHA-256', bytes.slice(0, 1 << 20));
      return Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (e) { return null; }
  }
  const SwimDati = {
    nome: null, bytes: null, es: null, seg: null, impronta: null, _serie: null, _durate: null,
    su(fn) { ascoltatori.push(fn); },
    _emetti() { ascoltatori.forEach(f => { try { f(); } catch (e) { console.error(e); } }); },
    async carica(nome, bytes) {
      const es = SWR.decodifica(bytes);
      const segs = SWR.segmentiConDati(es);
      let migliore = null, max = -1;
      for (const s of segs) {            // segmento predefinito: il piu' lungo
        const n = es.pagineDati.filter(p => p.seg === s).reduce((a, p) => a + p.campioni.length / 6, 0);
        if (n > max) { max = n; migliore = s; }
      }
      Object.assign(this, { nome, bytes, es, seg: migliore, _serie: null, _durate: null });
      this.impronta = await impronta(bytes);
      this._emetti();
    },
    scegliSegmento(seg) { if (this.es && seg !== this.seg) { this.seg = seg; this._serie = null; this._emetti(); } },
    serie() {
      if (!this.es || this.seg === null) return null;
      if (!this._serie || this._serie.seg !== this.seg) this._serie = SWR.serie(this.es, this.seg);
      return this._serie;
    },
    durata(seg) {                         // secondi del segmento (dall'ultimo campione + 1 periodo)
      if (!this.es) return 0;
      this._durate = this._durate || {};
      if (!(seg in this._durate)) {
        const s = SWR.serie(this.es, seg), sg = this.es.segmenti[seg];
        this._durate[seg] = s.n ? s.t[s.n - 1] + 10 / (sg ? sg.odrX10 : SWR.ODR_HZ_NOMINALE * 10) : 0;
      }
      return this._durate[seg];
    },
    apriDialogo() { ingressoFile.click(); },
    // --- salvataggio: showSaveFilePicker se c'e', altrimenti download
    async destinazione(nome, desc, ext, mime) {
      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({ suggestedName: nome, types: [{ description: desc, accept: { [mime]: [ext] } }] });
          return { handle };
        } catch (e) { if (e && e.name === 'AbortError') throw e; }   // altri errori (es. attivazione scaduta): download
      }
      return { download: true, nome };
    },
    async scrivi(dest, parti, mime) {
      const blob = new Blob(parti, { type: mime });
      if (dest.handle) { const w = await dest.handle.createWritable(); await w.write(blob); await w.close(); return dest.handle.name; }
      const url = URL.createObjectURL(blob), a = document.createElement('a');
      a.href = url; a.download = dest.nome; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      return dest.nome;
    },
    /** @returns nome del file salvato, oppure null se l'utente annulla */
    async salva(nome, parti, desc, ext, mime) {
      try { return await this.scrivi(await this.destinazione(nome, desc, ext, mime), parti, mime); }
      catch (e) { if (e && e.name === 'AbortError') return null; throw e; }
    }
  };
  window.SwimDati = SwimDati;

  const ingressoFile = document.createElement('input');
  ingressoFile.type = 'file'; ingressoFile.accept = '.swr,application/octet-stream';
  ingressoFile.addEventListener('change', async () => {
    const f = ingressoFile.files[0]; ingressoFile.value = '';
    if (!f) return;
    try { await SwimDati.carica(f.name, new Uint8Array(await f.arrayBuffer())); } catch (e) { stato('Impossibile leggere ' + f.name + ': ' + e.message, 'err'); }
  });

  // ---------------------------------------------------------------- porta seriale
  class Seriale {
    constructor() { this.buf = new Uint8Array(1 << 16); this.len = 0; this.attesa = null; this.attivo = false; UsbXiao.suDati(v => this._push(v)); }
    get chiusa() { return !UsbXiao.aperta; }
    _push(v) {
      if (!this.attivo) return;                 // fuori dalle operazioni il flusso (log, acc/gyro) lo gestisce index.html
      if (this.len + v.length > this.buf.length) { const n = new Uint8Array(Math.max(this.buf.length * 2, this.len + v.length)); n.set(this.buf.subarray(0, this.len)); this.buf = n; }
      this.buf.set(v, this.len); this.len += v.length; this._sveglia();
    }
    _sveglia() { if (this.attesa) { const f = this.attesa; this.attesa = null; f(); } }
    _aspetta(ms) { return new Promise(ok => { const t = setTimeout(() => { this.attesa = null; ok(); }, ms); this.attesa = () => { clearTimeout(t); ok(); }; }); }
    svuota() { this.len = 0; }
    consuma(n) { const out = this.buf.slice(0, n); this.buf.copyWithin(0, n, this.len); this.len -= n; return out; }
    async scrivi(testo) { await UsbXiao.scrivi(testo); }
    /** Occupa la porta: il testo non viene più interpretato da index.html e i byte arrivano qui. */
    async sessione(fn) {
      UsbXiao.esclusivo = true; this.attivo = true; this.len = 0;
      try { return await fn(); } finally { this.attivo = false; UsbXiao.esclusivo = false; this.len = 0; }
    }
    /** Una riga di testo (senza \n) o null allo scadere del tempo. */
    async riga(timeout) {
      const fine = Date.now() + timeout;
      for (;;) {
        const i = this.buf.subarray(0, this.len).indexOf(10);
        if (i >= 0) return new TextDecoder('latin1').decode(this.consuma(i + 1)).trim();
        if (this.chiusa) throw new Error('porta chiusa');
        const resto = fine - Date.now();
        if (resto <= 0) return null;
        await this._aspetta(resto);
      }
    }
    /** Invia il comando e ritorna la prima riga che inizia con uno dei prefissi. */
    async comando(testo, prefissi, timeout) {
      await sleep(200); this.svuota();
      await this.scrivi('\n' + testo + '\n');
      const fine = Date.now() + timeout;
      for (;;) {
        const r = await this.riga(Math.max(1, fine - Date.now()));
        if (r === null) throw new Error('nessuna risposta a ' + testo);
        if (prefissi.some(p => r.startsWith(p))) return r;
      }
    }
    /** DUMP: ritorna i byte delle pagine. */
    async dump(avanzamento) {
      await sleep(200); this.svuota();
      await this.scrivi('\nDUMP\n');
      let n = null;
      const fine = Date.now() + 15000;
      while (n === null) {
        const r = await this.riga(Math.max(1, fine - Date.now()));
        if (r === null) throw new Error('nessuna risposta a DUMP');
        const m = /^SWR1 (\d+)/.exec(r);
        if (m) n = Number(m[1]);
      }
      if (n === 0) return new Uint8Array(0);
      const tot = n * SWR.PAGINA;
      let visto = -1, ultimo = Date.now();
      while (this.len < tot) {
        if (this.chiusa) throw new Error('porta chiusa durante lo scarico');
        if (this.len !== visto) { visto = this.len; ultimo = Date.now(); avanzamento(Math.min(this.len, tot), tot); }
        else if (Date.now() - ultimo > 10000) throw new Error('scarico interrotto a ' + this.len + ' di ' + tot + ' byte');
        await this._aspetta(500);
      }
      const dati = this.consuma(tot);
      avanzamento(tot, tot);
      let fineOk = false;
      for (let k = 0; k < 3 && !fineOk; k++) { const r = await this.riga(3000); if (r === null) break; fineOk = r === 'END ' + n; }
      this.fineOk = fineOk;
      return dati;
    }
  }

  // ---------------------------------------------------------------- interfaccia
  radice.innerHTML = `
  <section class="scheda s12 swr-scheda">
    <header><h2>Memoria del tag <small>via USB · la porta si collega dal pannello in alto</small></h2></header>
    <div class="swr-riga">
      <button id="rgMem" disabled>MEM</button>
      <button id="rgScarica" class="primario" disabled>Scarica</button>
      <button id="rgAzzera" disabled>Azzera</button>
      <span class="pillola" id="rgPillola"><span class="punto"></span><span id="rgStatoPorta">Non collegato</span></span>
    </div>
    <div class="avanzamento" id="rgAvanz" hidden><div class="barra"><div id="rgBarra"></div></div><span id="rgAvanzTesto" class="mono"></span></div>
    <p class="swr-stato" id="rgStato" aria-live="polite">Collega la XIAO con il pulsante «USB» in alto (modalità normale, non in registrazione): la memoria si legge da sola.</p>
    <div class="swr-mem" id="rgMemInfo"></div>
    <p class="ann-nota">I dati restano nel browser: nessun file viene inviato a server. Le registrazioni sono dati di salute: non metterle nel repository.</p>
  </section>
  <section class="scheda s12 swr-scheda">
    <header><h2>File .swr <small>riassunto e scelta del segmento</small></h2>
      <div class="swr-riga"><button id="rgApri">Apri .swr dal disco</button><button id="rgVaiAnn" disabled>Annota con un video →</button></div></header>
    <div id="rgRiass"></div>
  </section>`;
  const $ = id => document.getElementById(id);
  const porta = new Seriale();
  let occupato = false, ultimoScarico = null;   // ultimoScarico = pagine dell'ultimo DUMP riuscito

  function stato(testo, tipo) { const e = $('rgStato'); e.textContent = testo; e.className = 'swr-stato' + (tipo ? ' ' + tipo : ''); }
  function pulsanti() {
    const c = !porta.chiusa;
    for (const id of ['rgMem', 'rgScarica', 'rgAzzera']) $(id).disabled = !c || occupato;
    $('rgPillola').className = 'pillola' + (c ? ' attivo' : '');
    $('rgStatoPorta').textContent = c ? 'USB collegata' : 'Non collegato';
  }
  function avanz(fatti, tot) {
    $('rgAvanz').hidden = false;
    $('rgBarra').style.width = (100 * fatti / tot).toFixed(1) + '%';
    $('rgAvanzTesto').textContent = (100 * fatti / tot).toFixed(0) + '%  ' + (fatti / 1024).toFixed(0) + ' / ' + (tot / 1024).toFixed(0) + ' KB';
  }
  async function conOccupato(fn) {
    if (occupato) return;
    occupato = true; pulsanti();
    try { await porta.sessione(fn); } catch (e) { if (!(e && e.name === 'AbortError')) stato('Errore: ' + (e && e.message || e), 'err'); else stato('Annullato.'); }
    finally { occupato = false; $('rgAvanz').hidden = true; pulsanti(); }
  }
  async function leggiMem() {
    const r = await porta.comando('MEM', ['K mem', 'X'], 15000);
    const m = /^K mem (\d+) (\d+)/.exec(r);
    if (!m) throw new Error('risposta a MEM: ' + r);
    const usate = Number(m[1]), tot = Number(m[2]);
    const p = tot ? 100 * usate / tot : 0;
    let extra = '';
    const D = SwimDati;
    if (D.es && ultimoScarico === usate) extra = ' · ' + Object.keys(D.es.segmenti).length + ' segmento/i (dall\'ultimo scarico)';
    $('rgMemInfo').innerHTML = '<b>Memoria</b>: ' + usate + ' di ' + tot + ' pagine (' + p.toFixed(1) + '%) · ~' + (usate * SWR.PAGINA / 1024).toFixed(0) + ' KB' + extra +
      '<span class="barra"><div style="width:' + p.toFixed(1) + '%"></div></span>';
    return { usate, tot };
  }

  // La porta la apre e la chiude il pannello di collegamento della pagina: qui si reagisce ai cambi di stato
  UsbXiao.suStato(aperta => {
    porta._sveglia(); pulsanti();
    if (!aperta) { if (!occupato) { stato('USB scollegata.'); $('rgMemInfo').innerHTML = ''; } return; }
    stato('USB collegata: leggo la memoria…');
    conOccupato(async () => {
      try { await leggiMem(); stato('USB collegata. Memoria letta.'); }
      catch (e) { stato('Collegato, ma MEM non risponde: ' + e.message + ' (la tag è in modalità normale con l\'USB?)', 'err'); }
    });
  });
  $('rgMem').addEventListener('click', () => conOccupato(async () => { await leggiMem(); stato('Memoria letta.'); }));
  $('rgScarica').addEventListener('click', () => conOccupato(async () => {
    const nome = marcaTempo() + '.swr';
    const { usate } = await leggiMem();
    if (!usate) { stato('Memoria vuota: niente da scaricare.'); return; }
    // la destinazione si sceglie PRIMA dello scarico (showSaveFilePicker vuole un gesto recente dell'utente)
    const dest = await SwimDati.destinazione(nome, 'Registrazione SwimTimer', '.swr', 'application/octet-stream');
    stato('Scarico di ' + usate + ' pagine in corso...');
    const bytes = await porta.dump(avanz);
    if (!bytes.length) { stato('Memoria vuota.'); return; }
    const salvato = await SwimDati.scrivi(dest, [bytes], 'application/octet-stream');
    ultimoScarico = bytes.length / SWR.PAGINA;
    await SwimDati.carica(salvato || nome, bytes);
    const note = [];
    if (porta.fineOk === false) note.push('manca la riga finale END');
    if (SwimDati.es.pagineCorrotte.length) note.push(SwimDati.es.pagineCorrotte.length + ' pagine corrotte');
    stato('Scaricato e salvato come ' + (salvato || nome) + ' (' + bytes.length + ' byte)' + (note.length ? ' · attenzione: ' + note.join(', ') : '') +
      (dest.download ? ' · salvato nella cartella dei download del browser' : ''), note.length ? 'err' : 'ok');
  }));
  $('rgAzzera').addEventListener('click', () => conOccupato(async () => {
    const { usate } = await leggiMem();
    const nonScaricata = usate > 0 && ultimoScarico !== usate;
    if (!confirm('Cancellare TUTTA la memoria della tag (' + usate + ' pagine)?' + (nonScaricata ? '\n\nATTENZIONE: questa memoria non risulta scaricata in questa sessione.' : '') + '\n\nL\'operazione non si può annullare.')) { stato('Azzeramento annullato.'); return; }
    const r = prompt('Seconda conferma: scrivi AZZERA per cancellare definitivamente la memoria della tag.');
    if (r === null || r.trim().toUpperCase() !== 'AZZERA') { stato('Azzeramento annullato.'); return; }
    stato('Cancellazione in corso (5-15 s)...');
    const ris = await porta.comando('ERASE', ['K erase', 'X'], 90000);
    if (!ris.startsWith('K erase')) throw new Error('risposta a ERASE: ' + ris);
    ultimoScarico = null;
    await leggiMem();
    stato('Memoria azzerata.', 'ok');
  }));
  $('rgApri').addEventListener('click', () => SwimDati.apriDialogo());
  $('rgVaiAnn').addEventListener('click', () => { if (typeof window.mostraVista === 'function') window.mostraVista('ann'); });
  if (!('serial' in navigator)) stato('Web Serial non è disponibile in questo browser: usa Chrome o Edge (https o localhost). Puoi comunque aprire un .swr dal disco.', 'err');
  pulsanti();

  // ---------------------------------------------------------------- riassunto del file
  const fmtDurata = s => s >= 60 ? Math.floor(s / 60) + ' min ' + (s % 60).toFixed(0) + ' s' : s.toFixed(1) + ' s';
  function renderRiassunto() {
    const D = SwimDati, box = $('rgRiass');
    $('rgVaiAnn').disabled = !D.es;
    if (!D.es) { box.innerHTML = '<p class="tenue">Nessun file aperto: scarica dalla tag o apri un .swr.</p>'; return; }
    const es = D.es, segs = SWR.segmentiConDati(es), sg = es.segmenti[D.seg];
    let h = '<div class="swr-kv"><span>File</span><b>' + esc(D.nome) + '</b><span>Dimensione</span><b>' + (es.dimensione / 1024).toFixed(0) + ' KB · ' + es.pagineUsate + ' pagine usate</b>' +
      '<span>Pagine corrotte</span><b class="' + (es.pagineCorrotte.length ? 'err' : 'ok') + '">' + (es.pagineCorrotte.length ? es.pagineCorrotte.length + ' (' + es.pagineCorrotte.slice(0, 8).join(', ') + (es.pagineCorrotte.length > 8 ? '…' : '') + ')' : 'nessuna') + '</b>' +
      '<span>Impronta SHA-256 (primo MiB)</span><b class="mono">' + (D.impronta ? D.impronta.slice(0, 16) + '…' : 'non disponibile') + '</b></div>';
    if (!segs.length) h += '<p class="err">Nessun segmento con dati.</p>';
    else {
      h += '<label class="swr-riga">Segmento da analizzare <select id="rgSeg">' + segs.map(s => {
        const x = es.segmenti[s];
        return '<option value="' + s + '"' + (s === D.seg ? ' selected' : '') + '>Segmento ' + s + ' · ' + fmtDurata(D.durata(s)) + ' · ' + (x.chiuso ? 'chiuso (' + (SWR.MOTIVI[x.motivo] || 'motivo ' + x.motivo) + ')' : 'NON chiuso') + '</option>';
      }).join('') + '</select></label>';
      const fs = SWR.fondoScala(sg);
      h += '<div class="swr-kv"><span>Durata</span><b>' + fmtDurata(D.durata(D.seg)) + '</b><span>Chiusura</span><b class="' + (sg.chiuso ? 'ok' : 'err') + '">' +
        (sg.chiuso ? 'chiuso: ' + (SWR.MOTIVI[sg.motivo] || sg.motivo) + ' · ' + sg.campioni + ' campioni' : 'senza chiusura (batteria o spegnimento: dati fino all\'ultima pagina valida)') + '</b>' +
        '<span>ODR</span><b>' + (sg.odrX10 / 10).toFixed(1) + ' Hz</b><span>Fondo scala</span><b>±' + fs.acc_g + ' g · ±' + fs.gyro_dps + ' dps</b>' +
        '<span>Batteria</span><b>' + sg.mvInizio + ' mV' + (sg.mvFine ? ' → ' + sg.mvFine + ' mV' : '') + '</b><span>Firmware</span><b>' + esc(sg.versione || '?') + '</b></div>';
    }
    if (es.problemi.length) h += '<details class="swr-problemi"><summary>' + es.problemi.length + ' avvisi</summary><ul>' + es.problemi.map(p => '<li>' + esc(p) + '</li>').join('') + '</ul></details>';
    box.innerHTML = h;
    const sel = $('rgSeg');
    if (sel) sel.addEventListener('change', () => SwimDati.scegliSegmento(Number(sel.value)));
  }
  SwimDati.su(renderRiassunto);
  renderRiassunto();
})();
