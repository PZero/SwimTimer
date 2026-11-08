/* SwimTimer - window.SwimDati per la versione ONLINE: stessa interfaccia di tools/registrazione.js (il .swr corrente condiviso con
 * annotazione.js) ma senza USB: i byte arrivano da Firestore (area.js chiama SwimDati.carica). Salvataggio file = download. */
(function () {
  'use strict';
  const SWR = window.SWR;
  const ascoltatori = [];
  async function impronta(bytes) {           // SHA-256 del primo MiB (come nella versione locale: compatibilita' dei progetti .json)
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
    svuota() { Object.assign(this, { nome: null, bytes: null, es: null, seg: null, impronta: null, _serie: null, _durate: null }); this._emetti(); },
    scegliSegmento(seg) { if (this.es && seg !== this.seg) { this.seg = seg; this._serie = null; this._emetti(); } },
    serie() {
      if (!this.es || this.seg === null) return null;
      if (!this._serie || this._serie.seg !== this.seg) this._serie = SWR.serie(this.es, this.seg);
      return this._serie;
    },
    durata(seg) {
      if (!this.es) return 0;
      this._durate = this._durate || {};
      if (!(seg in this._durate)) {
        const s = SWR.serie(this.es, seg), sg = this.es.segmenti[seg];
        this._durate[seg] = s.n ? s.t[s.n - 1] + 10 / (sg ? sg.odrX10 : SWR.ODR_HZ_NOMINALE * 10) : 0;
      }
      return this._durate[seg];
    },
    apriDialogo() { /* online: i dati si scelgono dall'elenco delle sessioni */ },
    async destinazione(nome, desc, ext, mime) {
      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({ suggestedName: nome, types: [{ description: desc, accept: { [mime]: [ext] } }] });
          return { handle };
        } catch (e) { if (e && e.name === 'AbortError') throw e; }
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
    async salva(nome, parti, desc, ext, mime) {
      try { return await this.scrivi(await this.destinazione(nome, desc, ext, mime), parti, mime); }
      catch (e) { if (e && e.name === 'AbortError') return null; throw e; }
    }
  };
  window.SwimDati = SwimDati;
})();
