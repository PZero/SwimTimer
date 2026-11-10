/* SwimTimer - decodificatore del formato .swr (gemello di firmware/xiao-stream/swr.py).
 * Formati 1 (lineare) e 2 (blocchi da 16 pagine con seq e conferma, docs/SINCRONIZZAZIONE.md §8).
 * Stesse regole e stessi risultati: pagine da 256 byte, intestazione da 16 byte con CRC16, dati a delta,
 * tempo dei campioni ricavato dai millis di pagina con una regressione sulle pagine contigue.
 * Funziona nel browser (globale SWR) e con node (module.exports). Nessun dato reale. */
(function (radice) {
  'use strict';
  const PAGINA = 256, TOT_PAGINE = 8192;
  const T_SEGMENTO = 0xA5, T_DATI = 0xD1, T_CHIUSURA = 0xE0;
  const FLAG_PRIMA = 0x01, FLAG_GAP = 0x02;
  const MOTIVI = { 1: 'quiete', 2: 'memoria piena', 3: 'batteria', 4: 'USB collegata', 5: 'errore flash/IMU' };
  const ODR_HZ_NOMINALE = 2083 / 10.0;
  const MS_PER_CAMPIONE = 1000.0 / ODR_HZ_NOMINALE;
  const G_PER_LSB = 488 / 1e6;
  const DPS_PER_LSB = 35 / 1e3;

  /** CRC16-CCITT (init 0xFFFF) sul tratto [da, a) di `d`. */
  function crc16(d, crc, da, a) {
    crc = crc === undefined ? 0xFFFF : crc; da = da || 0; a = a === undefined ? d.length : a;
    for (let i = da; i < a; i++) {
      let x = ((crc >> 8) ^ d[i]) & 0xFF;
      x ^= x >> 4;
      crc = ((crc << 8) ^ (x << 12) ^ (x << 5) ^ x) & 0xFFFF;
    }
    return crc;
  }
  const crcPagina = pag => crc16(pag, crc16(pag, 0xFFFF, 0, 14), 16, PAGINA);

  /** Decodifica il payload di una pagina dati: Int16Array di n*6 valori (ax ay az gx gy gz). */
  function decodificaDati(pag) {
    const dv = new DataView(pag.buffer, pag.byteOffset, PAGINA);
    const n = pag[1];
    const out = new Int16Array(n * 6);
    if (n === 0) return out;
    let pos = 16;
    const cur = new Int32Array(6);
    for (let i = 0; i < 6; i++) cur[i] = dv.getInt16(pos + 2 * i, true);
    pos += 12;
    out.set(cur, 0);
    for (let k = 1; k < n; k++) {
      if (pos >= PAGINA) throw new Error('pagina troncata');
      if (pag[pos] === 0x80) {
        if (pos + 13 > PAGINA) throw new Error('escape oltre la pagina');
        for (let i = 0; i < 6; i++) cur[i] = dv.getInt16(pos + 1 + 2 * i, true);
        pos += 13;
      } else {
        if (pos + 6 > PAGINA) throw new Error('delta oltre la pagina');
        for (let i = 0; i < 6; i++) {
          const v = cur[i] + dv.getInt8(pos + i);
          if (v < -32768 || v > 32767) throw new Error('campione fuori scala');
          cur[i] = v;
        }
        pos += 6;
      }
      out.set(cur, k * 6);
    }
    return out;
  }

  const T_BLOCCO = 0xB1, PAG_BLOCCO = 16, TOT_BLOCCHI = TOT_PAGINE / PAG_BLOCCO;

  /** CRC16 dell'intestazione di blocco (formato 2): come crcPagina ma con il byte 16 (conferma) considerato 0xFF. */
  // Campo conferma: formato 2 (solo 2026-11-10) byte 16; formato 3 parola 252..255 (la flash Puya riscrive l'intera parola)
  function confermaFF(pag) {
    const t = Uint8Array.from(pag.subarray ? pag.subarray(0, PAGINA) : pag.slice(0, PAGINA));
    if (t[1] === 2) t[16] = 0xFF; else t.fill(0xFF, 252, 256);
    return t;
  }
  function eConfermato(pag) {
    if (pag[1] === 2) return pag[16] !== 0xFF;
    for (let i = 252; i < 256; i++) if (pag[i] !== 0xFF) return true;
    return false;
  }
  function crcBlocco(pag) {
    const t = confermaFF(pag);
    return crc16(t, crc16(t, 0xFFFF, 0, 14), 16, PAGINA);
  }
  const paginaVuota = pag => { for (let i = 0; i < PAGINA; i++) if (pag[i] !== 0xFF) return false; return true; };

  /** Elabora una pagina .swr 1 (segmento/dati/chiusura). `p` = pagina fisica, `ordine` = posizione logica (contigue = consecutive). */
  function elaboraPagina(es, pag, p, ordine) {
    const dv = new DataView(pag.buffer, pag.byteOffset, PAGINA);
    const tipo = pag[0], param = pag[1], numero = dv.getUint16(2, true), millis = dv.getUint32(4, true);
    const mv = dv.getUint16(8, true), temp = dv.getInt8(10), flag = pag[11], seg = dv.getUint16(12, true), crc = dv.getUint16(14, true);
    if (crc !== crcPagina(pag)) {
      es.pagineCorrotte.push(p);
      es.problemi.push('pagina ' + p + ': CRC errata (pagina scartata)');
      return;
    }
    if (numero !== p) es.problemi.push('pagina ' + p + ': numero interno ' + numero + ' diverso dalla posizione');
    if (tipo === T_SEGMENTO) {
      let ver = '';
      for (let i = 30; i < 38 && pag[i] !== 0; i++) ver += pag[i] < 128 ? String.fromCharCode(pag[i]) : '�';
      es.segmenti[seg] = {
        idx: seg, pagina: p, millis, mvInizio: mv, odrX10: dv.getUint16(16, true), ugLsb: dv.getUint16(18, true), mdpsLsb: dv.getUint16(20, true),
        bias: [dv.getInt16(22, true), dv.getInt16(24, true), dv.getInt16(26, true)], causa: pag[28], tocchi: pag[29], versione: ver,
        chiuso: false, motivo: null, campioni: null, pagine: null, mvFine: null
      };
    } else if (tipo === T_DATI) {
      if (!(seg in es.segmenti)) { es.problemi.push('pagina ' + p + ': dati del segmento ' + seg + ' senza pagina di segmento valida'); return; }
      let camp;
      try { camp = decodificaDati(pag); } catch (e) {
        es.pagineCorrotte.push(p);
        es.problemi.push('pagina ' + p + ': dati non decodificabili (' + e.message + ')');
        return;
      }
      es.pagineDati.push({ pagina: p, ordine, seg, millis, mv, temp, flag, campioni: camp });
      if (flag & FLAG_GAP) es.problemi.push('pagina ' + p + ': interruzione dei dati (overrun del FIFO) prima di questa pagina');
    } else if (tipo === T_CHIUSURA) {
      if (seg in es.segmenti) {
        Object.assign(es.segmenti[seg], { chiuso: true, motivo: param, campioni: dv.getUint32(16, true), pagine: dv.getUint32(20, true), mvFine: mv });
      } else es.problemi.push('pagina ' + p + ': chiusura del segmento ' + seg + ' senza segmento');
    } else {
      es.problemi.push('pagina ' + p + ': tipo 0x' + tipo.toString(16).toUpperCase().padStart(2, '0') + ' sconosciuto');
    }
  }

  /** Formato 2: blocchi da 16 pagine, pagina 0 = intestazione 0xB1 con seq; i blocchi si elaborano in ordine di seq. */
  function decodificaFormato2(immagine, es) {
    const nBlocchi = Math.floor(immagine.length / (PAGINA * PAG_BLOCCO));
    const blocchi = [];
    es.formato = 2;
    es.blocchi = { totale: nBlocchi, validi: 0, confermati: 0, liberi: 0 };
    for (let b = 0; b < nBlocchi; b++) {
      const base = b * PAG_BLOCCO;
      const h = immagine.subarray(base * PAGINA, (base + 1) * PAGINA);
      if (paginaVuota(h)) { es.blocchi.liberi++; continue; }
      const dv = new DataView(h.buffer, h.byteOffset, PAGINA);
      if (h[0] !== T_BLOCCO || (h[1] !== 2 && h[1] !== 3) || dv.getUint16(14, true) !== crcBlocco(h)) {
        es.pagineCorrotte.push(base);
        es.problemi.push('blocco ' + b + ': intestazione non valida (blocco scartato)');
        continue;
      }
      if (dv.getUint16(2, true) !== base) es.problemi.push('blocco ' + b + ': pagina fisica interna ' + dv.getUint16(2, true) + ' diversa dalla posizione');
      const seq = dv.getUint32(17, true), confermato = eConfermato(h);
      blocchi.push({ b, base, seq, confermato, idTag: dv.getUint32(21, true) });
      es.blocchi.validi++;
      if (confermato) es.blocchi.confermati++;
    }
    blocchi.sort((x, y) => x.seq - y.seq || x.b - y.b);
    for (let i = 1; i < blocchi.length; i++) if (blocchi[i].seq === blocchi[i - 1].seq) es.problemi.push('blocchi ' + blocchi[i - 1].b + ' e ' + blocchi[i].b + ': stesso seq ' + blocchi[i].seq);
    es.listaBlocchi = blocchi;
    for (const bl of blocchi) {
      es.pagineUsate += 1;
      for (let k = 1; k < PAG_BLOCCO; k++) {
        const p = bl.base + k, pag = immagine.subarray(p * PAGINA, (p + 1) * PAGINA);
        if (paginaVuota(pag)) continue;
        es.pagineUsate++;
        elaboraPagina(es, pag, p, bl.seq * PAG_BLOCCO + k);
      }
    }
  }

  /** Decodifica un'immagine .swr (Uint8Array), formato 1 o 2 (riconosciuto dalla pagina 0 = intestazione di blocco 0xB1, formato 2). */
  function decodifica(immagine) {
    const es = { problemi: [], pagineCorrotte: [], segmenti: {}, pagineDati: [], pagineUsate: 0, dimensione: immagine.length, formato: 1 };
    if (immagine.length % PAGINA) es.problemi.push("file troncato: " + immagine.length + " byte non e' multiplo di " + PAGINA);
    const nPag = Math.floor(immagine.length / PAGINA);
    // formato 2/3: almeno un blocco inizia con l'intestazione 0xB1 (il blocco 0 puo' essere vuoto)
    let anello = false;
    for (let i = 0; i + 1 < immagine.length; i += PAGINA * PAG_BLOCCO) if (immagine[i] === T_BLOCCO && (immagine[i + 1] === 2 || immagine[i + 1] === 3)) { anello = true; break; }
    if (nPag && anello) decodificaFormato2(immagine, es);
    else {
      for (let p = 0; p < nPag; p++) {
        const pag = immagine.subarray(p * PAGINA, (p + 1) * PAGINA);
        let libera = true;
        for (let i = 0; i < 16; i++) if (pag[i] !== 0xFF) { libera = false; break; }
        if (libera) break;
        es.pagineUsate = p + 1;
        elaboraPagina(es, pag, p, p);
      }
    }
    for (const k of Object.keys(es.segmenti)) {
      const s = es.segmenti[k];
      if (!s.chiuso) es.problemi.push('segmento ' + s.idx + " senza chiusura (batteria scarica o spegnimento: la fine e' l'ultima pagina valida)");
    }
    return es;
  }

  /** Per un gruppo di pagine contigue: [t0_ms, ms_per_campione] per pagina (regressione millis ~ indice). */
  function adattaTempi(pagine) {
    const n = pagine.length, idx = [], ms = pagine.map(p => p.millis);
    let c = 0;
    for (const pg of pagine) { idx.push(c); c += pg.campioni.length / 6; }
    let b = MS_PER_CAMPIONE, a = ms[0];
    if (n >= 3) {
      let si = 0, sm = 0;
      for (let k = 0; k < n; k++) { si += idx[k]; sm += ms[k]; }
      const mi = si / n, mm = sm / n;
      let den = 0;
      for (let k = 0; k < n; k++) den += (idx[k] - mi) ** 2;
      if (den > 0) {
        let num = 0;
        for (let k = 0; k < n; k++) num += (idx[k] - mi) * (ms[k] - mm);
        const bb = num / den;
        if (Math.abs(bb - MS_PER_CAMPIONE) < 0.05 * MS_PER_CAMPIONE) { b = bb; a = mm - b * mi; }
      }
    }
    return idx.map(i => [a + b * i, b]);
  }

  /** Serie di un segmento: {seg, n, t (s dall'inizio del segmento), pagina, mv, d: [ax..gz Int16Array]} come righe() di swr.py. */
  function serie(es, seg) {
    const pagine = es.pagineDati.filter(p => p.seg === seg);
    let n = 0;
    for (const p of pagine) n += p.campioni.length / 6;
    const out = { seg, n, t: new Float64Array(n), pagina: new Uint16Array(n), mv: new Uint16Array(n), d: [0, 1, 2, 3, 4, 5].map(() => new Int16Array(n)) };
    if (!n) return out;
    const gruppi = [];
    let cur = [pagine[0]];
    for (let i = 1; i < pagine.length; i++) {
      const pg = pagine[i];
      if (pg.ordine !== cur[cur.length - 1].ordine + 1 || (pg.flag & FLAG_GAP)) { gruppi.push(cur); cur = []; }
      cur.push(pg);
    }
    gruppi.push(cur);
    let tInizio = null, i = 0;
    for (const g of gruppi) {
      const tempi = adattaTempi(g);
      for (let q = 0; q < g.length; q++) {
        const pg = g[q], t0 = tempi[q][0], b = tempi[q][1];
        if (tInizio === null) tInizio = t0;
        const m = pg.campioni.length / 6;
        for (let k = 0; k < m; k++, i++) {
          out.t[i] = (t0 + b * k - tInizio) / 1000.0;
          out.pagina[i] = pg.pagina; out.mv[i] = pg.mv;
          for (let j = 0; j < 6; j++) out.d[j][i] = pg.campioni[k * 6 + j];
        }
      }
    }
    return out;
  }

  const segmentiConDati = es => [...new Set(es.pagineDati.map(p => p.seg))].sort((a, b) => a - b);

  /** CSV identico a swr.scrivi_csv (terminatore di riga \r\n come il modulo csv di Python). */
  function scriviCsv(es, grezzo) {
    const righe = [(grezzo ? ['seg', 'pagina', 'n', 't_s', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mV']
      : ['seg', 'pagina', 'n', 't_s', 'ax_g', 'ay_g', 'az_g', 'gx_dps', 'gy_dps', 'gz_dps', 'mV']).join(',')];
    for (const seg of segmentiConDati(es)) {
      const s = serie(es, seg);
      for (let i = 0; i < s.n; i++) {
        const r = [seg, s.pagina[i], i, s.t[i].toFixed(4)];
        for (let j = 0; j < 6; j++) {
          const v = s.d[j][i];
          r.push(grezzo ? v : j < 3 ? (v * G_PER_LSB).toFixed(5) : (v * DPS_PER_LSB).toFixed(3));
        }
        r.push(s.mv[i]);
        righe.push(r.join(','));
      }
    }
    return righe.join('\r\n') + '\r\n';
  }

  /** Fondo scala dai LSB del segmento (LSM6: 0,061/0,122/0,244/0,488 mg; 4,375/8,75/17,5/35/70 mdps). */
  function fondoScala(seg) {
    const vicino = (v, tab) => tab.reduce((m, x) => Math.abs(x[0] - v) < Math.abs(m[0] - v) ? x : m)[1];
    return {
      acc_g: vicino(seg.ugLsb, [[61, 2], [122, 4], [244, 8], [488, 16]]),
      gyro_dps: vicino(seg.mdpsLsb, [[4.375, 125], [8.75, 250], [17.5, 500], [35, 1000], [70, 2000]])
    };
  }

  function riassunto(es) {
    const out = ['pagine usate: ' + es.pagineUsate + ' (' + (100 * es.pagineUsate / TOT_PAGINE).toFixed(1) + '% della memoria), formato ' + es.formato + (es.blocchi ? ', blocchi ' + es.blocchi.validi + ' (' + es.blocchi.confermati + ' confermati)' : '') + ', segmenti: ' + Object.keys(es.segmenti).length];
    for (const k of Object.keys(es.segmenti).map(Number).sort((a, b) => a - b)) {
      const s = es.segmenti[k];
      const camp = es.pagineDati.filter(p => p.seg === k).reduce((a, p) => a + p.campioni.length / 6, 0);
      out.push('  segmento ' + k + ': ' + camp + ' campioni (~' + (camp / ODR_HZ_NOMINALE).toFixed(1) + ' s), batteria ' + s.mvInizio + ' mV' +
        (s.mvFine ? ' -> ' + s.mvFine + ' mV' : '') + ', fine: ' + (s.chiuso ? (MOTIVI[s.motivo] || 'senza chiusura') : 'senza chiusura'));
    }
    if (es.problemi.length) { out.push('PROBLEMI (' + es.problemi.length + '):'); es.problemi.forEach(p => out.push('  - ' + p)); } else out.push('nessun problema rilevato');
    return out.join('\n');
  }

  const API = { TOT_BLOCCHI, PAG_BLOCCO, PAGINA, TOT_PAGINE, MOTIVI, ODR_HZ_NOMINALE, MS_PER_CAMPIONE, G_PER_LSB, DPS_PER_LSB, crc16, crcPagina, crcBlocco, decodificaDati, decodifica, serie, segmentiConDati, scriviCsv, fondoScala, riassunto };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  radice.SWR = API;
})(typeof window !== 'undefined' ? window : globalThis);
