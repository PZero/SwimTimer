/* Aggiornamento automatico del sito.
 * All'apertura legge /versione.json (scritto a ogni deploy da firebase/scrivi-versione.mjs).
 * Quando la pagina torna in primo piano, e comunque ogni 5 minuti, lo rilegge: se la versione è cambiata
 * azzera le memorie di sessione del sito (swt.*) e ricarica la pagina, così nessuno resta con file vecchi.
 * Non ricarica se c'è un salvataggio in sospeso (window.swtModificheInSospeso() === true): avvisa soltanto. */
(function () {
  const tt = (k, it) => (window.t ? window.t(k) : it);
  let caricata = null, avvisato = false;
  async function leggi() {
    try { const r = await fetch('/versione.json', { cache: 'no-store' }); if (!r.ok) return null; return (await r.json()).versione || null; }
    catch (e) { return null; }
  }
  function avviso(testo) {
    let el = document.getElementById('swtAvvisoVersione');
    if (!el) {
      el = document.createElement('div'); el.id = 'swtAvvisoVersione';
      el.style.cssText = 'position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:9999;background:#0b6e99;color:#fff;padding:10px 16px;border-radius:10px;font:500 14px Inter,system-ui,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.25);cursor:pointer';
      el.onclick = () => location.reload();
      document.body.appendChild(el);
    }
    el.textContent = testo;
  }
  async function controlla() {
    const v = await leggi();
    if (!v) return;
    if (caricata === null) { caricata = v; document.documentElement.dataset.versione = v; const s = document.getElementById('versioneSito'); if (s) s.textContent = v; return; }
    if (v === caricata) return;
    for (let i = sessionStorage.length - 1; i >= 0; i--) { const k = sessionStorage.key(i); if (k && k.startsWith('swt.')) sessionStorage.removeItem(k); }
    if (typeof window.swtModificheInSospeso === 'function' && window.swtModificheInSospeso()) {
      if (!avvisato) { avvisato = true; avviso(tt('v.salva', 'Nuova versione del sito: salva il lavoro e tocca qui per aggiornare')); }
      return;
    }
    avviso(tt('v.aggiorno', 'Nuova versione del sito: aggiornamento…'));
    setTimeout(() => location.reload(), 600);
  }
  controlla();
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') controlla(); });
  window.addEventListener('pageshow', e => { if (e.persisted) controlla(); });   // pagina ripresa dalla cache "indietro/avanti" (Safari)
  setInterval(controlla, 5 * 60 * 1000);
})();
