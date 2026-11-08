/* SwimTimer - area riservata: accesso, approvazione, elenco sessioni/video/annotazioni, amministrazione, editor.
 * Letture parsimoniose (piano Spark): niente listener in tempo reale; 3 query all'apertura dell'elenco (sessioni, video,
 * annotazioni), tenute in memoria finche' non si preme «Aggiorna»; i chunk .swr (immutabili) prima dalla cache locale. */
import { auth, db, osserva, accedi, esci, assicuraUtente, collection, doc, getDocs, getDoc, getDocFromCache, setDoc, addDoc, updateDoc,
  deleteDoc, query, where, limit, serverTimestamp, Bytes, getCountFromServer } from '../comune/fb.js';
import { sha256Bytes, sha256File } from '../comune/sha256.js';
import { caricaSessione as caricaBytes, fmtByte, controllaSwr } from '../comune/sessioni.js';

const SWR = window.SWR, SD = window.SwimDati;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const t = window.t, loc = () => window.SwimI18n.locale();
const RE_LINK = /^https:\/\/(drive\.google\.com|docs\.google\.com|youtu\.be|www\.youtube\.com|youtube\.com)\/.*/;
const fmtData = ts => ts && ts.toDate ? ts.toDate().toLocaleString(loc(), { dateStyle: 'short', timeStyle: 'short' }) : '–';
const fmtDur = s => { s = Math.round(s); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };

let utente = null;          // utente Firebase
let profilo = null;         // documento users/{uid}
let admin = false;
let D = { sessioni: [], video: [], annot: [], caricato: false };
let ctx = null;             // contesto dell'editor aperto

function toast(msg) { const e = $('toast'); e.textContent = msg; e.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => e.classList.remove('on'), 3500); }
let vistaCorrente = null;
const mostra = id => (vistaCorrente = id, ['vistaLogin', 'vistaStato', 'vistaSessioni', 'vistaAdmin', 'vistaMessaggi', 'vistaEditor']).forEach(v => { $(v).hidden = v !== id; });
const approvato = () => admin || (profilo && profilo.stato === 'approvato');

// ------------------------------------------------------------------ accesso
$('btnAccedi').onclick = async () => {
  $('erroreLogin').textContent = '';
  try { await accedi(); } catch (e) { $('erroreLogin').textContent = t('a.accessoErr', { e: e.code || e.message }); }
};
$('btnEsci').onclick = () => esci();

osserva(async u => {
  utente = u; profilo = null; admin = false; D = { sessioni: [], video: [], annot: [], caricato: false };
  $('nav').hidden = $('utente').hidden = !u;
  if (!u) { mostra('vistaLogin'); return; }
  $('nomeUtente').textContent = u.displayName || u.email;
  if (u.photoURL) $('foto').src = u.photoURL; else $('foto').removeAttribute('src');
  try {
    profilo = await assicuraUtente(u);
    admin = await sonoAdmin(u);
  } catch (e) {
    $('vistaStato').innerHTML = `<h1>${t('a.errore')}</h1><p class="err">${esc(e.code || e.message)}</p><p class="tenue">${t('a.erroreT')}</p>`;
    mostra('vistaStato'); return;
  }
  $('navAdmin').hidden = $('navMsg').hidden = !admin;
  if (admin) aggiornaBadge();
  instrada();
});

/** L'amministratore si riconosce dalle regole: solo lui puo' elencare users. Esito in sessionStorage (una lettura per sessione). */
async function sonoAdmin(u) {
  const k = 'swt.admin.' + u.uid;
  const c = sessionStorage.getItem(k);
  if (c === '1') return true;                    // si ricorda solo il SI': un "no" si ricontrolla sempre (regole appena aggiornate)
  let r = false;
  try { await getDocs(query(collection(db(), 'users'), limit(1))); r = true; } catch (e) { r = false; }
  if (r) sessionStorage.setItem(k, '1'); else sessionStorage.removeItem(k);
  return r;
}

function schermataStato() {
  const st = profilo.stato;
  const testi = {
    in_attesa: [t('a.att.h'), t('a.att.t', { email: '<b>' + esc(profilo.email) + '</b>' })],
    rifiutato: [t('a.rif.h'), t('a.rif.t')],
    revocato: [t('a.rev.h'), t('a.rev.t')]
  }[st] || [t('a.sconosciuto'), esc(st)];
  $('vistaStato').innerHTML = `<h1>${testi[0]}</h1><p class="tenue">${testi[1]}</p><p><button id="btnRiprova">${t('a.ricontrolla')}</button> <button id="btnEsci2">${t('a.esci')}</button></p>`;
  $('btnRiprova').onclick = async () => { admin = await sonoAdmin(utente); $('navAdmin').hidden = $('navMsg').hidden = !admin; profilo = await assicuraUtente(utente); instrada(); };
  $('btnEsci2').onclick = () => esci();
  mostra('vistaStato');
}

// ------------------------------------------------------------------ instradamento (hash)
window.addEventListener('hashchange', instrada);
async function instrada() {
  if (!utente || !profilo) return;
  if (!approvato()) return schermataStato();
  const h = location.hash.replace(/^#/, '') || 'sessioni';
  const p = h.split('/');
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('attivo', a.dataset.v === p[0]));
  if (p[0] !== 'annota' && ctx) chiudiEditor();
  try {
    if (p[0] === 'admin' && admin) return await vistaAdmin();
    if (p[0] === 'messaggi' && admin) return await vistaMessaggi();
    if (p[0] === 'annota' && p.length >= 4) return await apriEditor(p[1], p[2], p[3]);
    return await vistaSessioni();
  } catch (e) { console.error(e); toast(t('a.erroreToast', { e: e.code || e.message })); }
}

// ------------------------------------------------------------------ dati (letture una tantum)
async function carica(forza) {
  if (D.caricato && !forza) return;
  const d = db();
  const [s, v, a] = await Promise.all([getDocs(collection(d, 'sessioni')), getDocs(collection(d, 'video')), getDocs(collection(d, 'annotazioni'))]);
  const m = x => ({ id: x.id, ...x.data() });
  D = { sessioni: s.docs.map(m), video: v.docs.map(m), annot: a.docs.map(m), caricato: true };
  const ms = x => (x && x.toMillis ? x.toMillis() : 0);
  D.sessioni.sort((x, y) => String(y.data).localeCompare(String(x.data)) || ms(y.caricatoIl) - ms(x.caricatoIl));
  D.video.sort((x, y) => ms(x.caricatoIl) - ms(y.caricatoIl));
  D.annot.sort((x, y) => ms(y.aggiornato) - ms(x.aggiornato));
}
const puoGestire = x => admin || (x.caricatoDa && x.caricatoDa.uid === utente.uid);

// ------------------------------------------------------------------ elenco sessioni
async function vistaSessioni() {
  mostra('vistaSessioni');
  if (!D.caricato) $('vistaSessioni').innerHTML = '<div class="scheda vuoto">' + t('a.caricamento') + '</div>';
  await carica(false);
  disegnaSessioni();
  evidenziaSessione();
}
/** #sessioni/<id> (link dalla pagina Strumenti): porta alla sessione e la evidenzia. */
function evidenziaSessione() {
  const id = location.hash.replace(/^#/, '').split('/')[1];
  if (!id || !/^[A-Za-z0-9]+$/.test(id)) return;
  const e = document.querySelector(`[data-sid="${id}"]`);
  if (e && e.tagName === 'ARTICLE') { e.scrollIntoView({ block: 'center' }); e.classList.add('sess-evid'); }
}
function disegnaSessioni() {
  const el = $('vistaSessioni');
  let h = `<div class="barra-titolo"><h1>${t('a.nav.sessioni')}</h1><div class="riga"><button id="bAgg" class="piccolo">${t('a.aggiorna')}</button><button id="bNuova" class="primario">${t('a.caricaSwr')}</button></div></div>`;
  if (!D.sessioni.length) h += '<div class="scheda vuoto">' + t('a.nessunaSess') + '</div>';
  h += '<div class="pila">' + D.sessioni.map(sessioneHtml).join('') + '</div>';
  el.innerHTML = h;
  $('bNuova').onclick = () => dialogoSessione();
  $('bAgg').onclick = async () => { await carica(true); disegnaSessioni(); toast(t('a.elencoAgg')); };
}
function sessioneHtml(s) {
  const mie = puoGestire(s);
  const videos = D.video.filter(v => v.sessioneId === s.id);
  return `<article class="scheda" data-sid="${esc(s.id)}">
    <div class="sess-testa"><div>
      <h3>${esc(s.titolo)} ${s.completa ? '' : '<span class="chip att">' + t('a.incompleto') + '</span>'}</h3>
      <div class="meta"><b>${esc(s.data)}</b> · ${t('a.caricataDa')} <b>${esc(s.caricatoDa.nome)}</b> ${t('a.il')} ${fmtData(s.caricatoIl)} · ${fmtByte(s.byte)} · <span class="mono" title="sha256 ${esc(s.sha256)}">${esc(s.sha256.slice(0, 10))}…</span></div>
      ${s.nota ? `<p class="nota-sess">${esc(s.nota)}</p>` : ''}</div>
      <div class="riga"><button class="piccolo" data-act="nuovo-video" data-sid="${esc(s.id)}" ${s.completa ? '' : 'disabled'}>${t('a.aggVideo')}</button>
        ${mie ? `<button class="piccolo" data-act="mod-sess" data-sid="${esc(s.id)}">${t('a.modifica')}</button><button class="piccolo pericolo" data-act="del-sess" data-sid="${esc(s.id)}">${t('a.elimina')}</button>` : ''}</div></div>
    <div class="sotto">${videos.length ? videos.map(v => videoHtml(v)).join('') : '<div class="meta">' + t('a.nessunVideo') + '</div>'}</div>
  </article>`;
}
function videoHtml(v) {
  const ann = D.annot.filter(a => a.videoId === v.id);
  const mie = puoGestire(v);
  return `<div class="video-riga">
    <div class="titolo"><div><b>${esc(v.nome)}</b> <span class="meta">${fmtByte(v.byte)} · ${fmtDur(v.durata_s)} · ${esc(v.fps)} fps · ${t('a.da')} ${esc(v.caricatoDa.nome)} · <a href="${esc(v.link)}" target="_blank" rel="noopener noreferrer">${t('a.apriVideo')}</a></span></div>
      <div class="riga"><button class="piccolo primario" data-act="nuova-ann" data-sid="${esc(v.sessioneId)}" data-vid="${esc(v.id)}">${t('a.nuovaAnn')}</button>
      ${mie ? `<button class="piccolo pericolo" data-act="del-video" data-vid="${esc(v.id)}">${t('a.eliminaVideo')}</button>` : ''}</div></div>
    ${ann.map(a => annotHtml(a)).join('')}
  </div>`;
}
function annotHtml(a) {
  const mia = a.autore.uid === utente.uid;
  return `<div class="annot ${mia ? 'mia' : ''}"><div><b>${esc(a.autore.nome)}</b>${mia ? ' <span class="chip ok">' + t('a.tua') + '</span>' : ''} · <span class="meta">${t('a.nEventi', { n: a.eventi.length })} · ${t('a.aggiornata')} ${fmtData(a.aggiornato)}</span></div>
    <div class="azioni"><button class="piccolo" data-act="apri-ann" data-sid="${esc(a.sessioneId)}" data-vid="${esc(a.videoId)}" data-aid="${esc(a.id)}">${t('a.apri')}</button>
    ${mia ? '' : `<button class="piccolo" data-act="dup-ann" data-aid="${esc(a.id)}">${t('a.duplica')}</button>`}
    ${mia || admin ? `<button class="piccolo pericolo" data-act="del-ann" data-aid="${esc(a.id)}">${t('a.elimina')}</button>` : ''}</div></div>`;
}

$('vistaSessioni').addEventListener('click', async e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const { act, sid, vid, aid } = b.dataset;
  try {
    if (act === 'nuovo-video') dialogoVideo(sid);
    else if (act === 'mod-sess') dialogoSessione(D.sessioni.find(s => s.id === sid));
    else if (act === 'del-sess') await eliminaSessione(sid);
    else if (act === 'del-video') await eliminaVideo(vid);
    else if (act === 'nuova-ann') location.hash = `#annota/${sid}/${vid}/nuova`;
    else if (act === 'apri-ann') location.hash = `#annota/${sid}/${vid}/${aid}`;
    else if (act === 'dup-ann') { const n = await duplica(aid); location.hash = `#annota/${n.sessioneId}/${n.videoId}/${n.id}`; }
    else if (act === 'del-ann') await eliminaAnnotazione(aid);
  } catch (err) { console.error(err); toast(t('a.opErr', { e: err.code || err.message })); }
});

// ------------------------------------------------------------------ dialoghi
const dlg = $('dlg');
function apriDialogo(html) { dlg.innerHTML = html; if (!dlg.open) dlg.showModal(); return dlg; }
dlg.addEventListener('cancel', e => { if (dlg.dataset.occupato === '1') e.preventDefault(); });
function chiudiDialogo() { dlg.dataset.occupato = '0'; dlg.close(); }

function dialogoSessione(s) {
  const nuova = !s;
  const oggi = new Date().toISOString().slice(0, 10);
  apriDialogo(`<form method="dialog" id="fSess"><h3>${nuova ? t('a.ds.hNuova') : t('a.ds.hMod')}</h3>
    ${nuova ? '<label>' + t('a.ds.file') + '<input type="file" id="fFile" accept=".swr,application/octet-stream" required></label>' : ''}
    <label>${t('a.ds.titolo')}<input type="text" id="fTit" maxlength="120" required value="${esc(s ? s.titolo : '')}" placeholder="${esc(t('a.ds.phTitolo'))}"></label>
    <label>${t('a.ds.data')}<input type="date" id="fData" required value="${esc(s ? s.data : oggi)}"></label>
    <label>${t('a.ds.nota')}<textarea id="fNota" rows="3" maxlength="1000">${esc(s ? s.nota || '' : '')}</textarea></label>
    <div class="meta">${nuova ? t('a.ds.info') : ''}</div>
    <div class="barra" id="fBarra" hidden><div></div></div><div class="meta" id="fMsg"></div>
    <div class="azioni"><button type="button" id="fAnnulla">${t('a.annulla')}</button><button class="primario" id="fOk">${nuova ? t('a.carica') : t('a.salva')}</button></div></form>`);
  $('fAnnulla').onclick = chiudiDialogo;
  $('fSess').onsubmit = async ev => {
    ev.preventDefault();
    const tit = $('fTit').value.trim(), data = $('fData').value, nota = $('fNota').value.trim();
    $('fOk').disabled = true; dlg.dataset.occupato = '1';
    try {
      if (nuova) await caricaSessione($('fFile').files[0], tit, data, nota, (f, t, m) => { $('fBarra').hidden = false; $('fBarra').firstElementChild.style.width = (100 * f / t) + '%'; $('fMsg').textContent = m; });
      else { const dati = { titolo: tit, data, completa: s.completa }; if (nota) dati.nota = nota; else if (s.nota) dati.nota = ''; await updateDoc(doc(db(), 'sessioni', s.id), dati); await carica(true); }
      chiudiDialogo(); disegnaSessioni(); toast(nuova ? t('a.sessCaricata') : t('a.sessAgg'));
    } catch (err) { console.error(err); $('fMsg').className = 'meta err'; $('fMsg').textContent = err.message || err.code; $('fOk').disabled = false; dlg.dataset.occupato = '0'; }
  };
}

async function caricaSessione(file, titolo, data, nota, prog) {
  if (!file) throw new Error(t('a.scegliSwr'));
  const bytes = new Uint8Array(await file.arrayBuffer());
  await caricaBytes(bytes, { titolo, data, nota, utente, prog });
  await carica(true);
}

function dialogoVideo(sid) {
  const s = D.sessioni.find(x => x.id === sid);
  apriDialogo(`<form method="dialog" id="fVid"><h3>${t('a.dv.h', { titolo: esc(s.titolo) })}</h3>
    <p class="meta">${t('a.dv.info')}</p>
    <label>${t('a.dv.file')}<input type="file" id="vFile" accept="video/*" required></label>
    <div class="barra" id="vBarra" hidden><div></div></div><div class="meta" id="vInfo"></div>
    <label>${t('a.dv.link')}<input type="url" id="vLink" required maxlength="500" placeholder="https://drive.google.com/file/d/…"></label>
    <label>${t('a.dv.fps')}<input type="number" id="vFps" min="1" max="240" step="0.001" value="30"></label>
    <div class="meta" id="vMsg"></div>
    <div class="azioni"><button type="button" id="vAnnulla">${t('a.annulla')}</button><button class="primario" id="vOk" disabled>${t('a.dv.salva')}</button></div></form>`);
  let info = null;
  $('vAnnulla').onclick = chiudiDialogo;
  $('vFile').onchange = async () => {
    const f = $('vFile').files[0]; info = null; $('vOk').disabled = true; if (!f) return;
    dlg.dataset.occupato = '1'; $('vBarra').hidden = false;
    try {
      const durata = await durataVideo(f);
      const sha = await sha256File(f, (a, tot) => { $('vBarra').firstElementChild.style.width = (100 * a / tot) + '%'; $('vInfo').textContent = t('a.dv.sha', { p: Math.round(100 * a / tot) }); });
      info = { nome: f.name.slice(0, 200), byte: f.size, sha256: sha, durata_s: durata };
      $('vInfo').innerHTML = `${esc(f.name)} · ${fmtByte(f.size)} · ${fmtDur(durata)} · <span class="mono">${sha.slice(0, 12)}…</span>`;
      const dup = D.video.find(v => v.sessioneId === sid && v.sha256 === sha);
      $('vMsg').textContent = dup ? t('a.dv.dup', { nome: dup.nome }) : '';
      $('vOk').disabled = false;
    } catch (e) { $('vInfo').textContent = t('a.dv.illeggibile', { e: e.message }); }
    dlg.dataset.occupato = '0';
  };
  $('fVid') && ($('fVid').onsubmit = async ev => {
    ev.preventDefault();
    const link = $('vLink').value.trim(), fps = Number($('vFps').value);
    if (!RE_LINK.test(link)) { $('vMsg').className = 'meta err'; $('vMsg').textContent = t('a.dv.linkErr'); return; }
    if (!(fps > 0 && fps <= 240)) { $('vMsg').className = 'meta err'; $('vMsg').textContent = t('a.dv.fpsErr'); return; }
    $('vOk').disabled = true;
    try {
      await addDoc(collection(db(), 'video'), { sessioneId: sid, link, ...info, fps, caricatoDa: { uid: utente.uid, nome: (utente.displayName || utente.email || 'Utente').slice(0, 100) }, caricatoIl: serverTimestamp() });
      await carica(true); chiudiDialogo(); disegnaSessioni(); toast(t('a.dv.ok'));
    } catch (err) { console.error(err); $('vMsg').className = 'meta err'; $('vMsg').textContent = err.message || err.code; $('vOk').disabled = false; }
  });
}
function durataVideo(file) {
  return new Promise((ok, ko) => {
    const v = document.createElement('video'), url = URL.createObjectURL(file);
    v.preload = 'metadata';
    v.onloadedmetadata = () => { const d = v.duration; URL.revokeObjectURL(url); isFinite(d) && d > 0 ? ok(d) : ko(new Error(t('a.dv.durErr'))); };
    v.onerror = () => { URL.revokeObjectURL(url); ko(new Error(t('a.dv.fmtErr'))); };
    v.src = url;
  });
}

// ------------------------------------------------------------------ eliminazioni
async function eliminaSessione(sid) {
  const s = D.sessioni.find(x => x.id === sid);
  const video = D.video.filter(v => v.sessioneId === sid), ann = D.annot.filter(a => a.sessioneId === sid);
  const altrui = [...video.filter(v => v.caricatoDa.uid !== utente.uid), ...ann.filter(a => a.autore.uid !== utente.uid)];
  if (altrui.length && !admin) { toast(t('a.del.sessAltrui')); return; }
  if (!confirm(t('a.del.sessConf', { titolo: s.titolo, v: video.length, a: ann.length }))) return;
  for (const a of ann) await deleteDoc(doc(db(), 'annotazioni', a.id));
  for (const v of video) await deleteDoc(doc(db(), 'video', v.id));
  for (let i = 0; i < (s.nChunk || 6); i++) { try { await deleteDoc(doc(db(), 'sessioni', sid, 'chunk', String(i))); } catch (e) { /* assente */ } }
  await deleteDoc(doc(db(), 'sessioni', sid));
  await carica(true); disegnaSessioni(); toast(t('a.del.sessOk'));
}
async function eliminaVideo(vid) {
  const ann = D.annot.filter(a => a.videoId === vid);
  if (ann.some(a => a.autore.uid !== utente.uid) && !admin) { toast(t('a.del.videoAltrui')); return; }
  if (!confirm(t('a.del.videoConf', { a: ann.length }))) return;
  for (const a of ann) await deleteDoc(doc(db(), 'annotazioni', a.id));
  await deleteDoc(doc(db(), 'video', vid));
  await carica(true); disegnaSessioni(); toast(t('a.del.videoOk'));
}
async function eliminaAnnotazione(aid) {
  if (!confirm(t('a.del.annConf'))) return;
  await deleteDoc(doc(db(), 'annotazioni', aid));
  await carica(true); disegnaSessioni(); toast(t('a.del.annOk'));
}
async function duplica(aid) {
  let a = D.annot.find(x => x.id === aid);
  if (!a) { const sn = await getDoc(doc(db(), 'annotazioni', aid)); if (!sn.exists()) throw new Error(t('a.annNonTrovata')); a = { id: sn.id, ...sn.data() }; }
  const copia = {
    sessioneId: a.sessioneId, videoId: a.videoId, autore: { uid: utente.uid, nome: (utente.displayName || utente.email || 'Utente').slice(0, 100) },
    eventi: a.eventi, offset_s: a.offset_s ?? null, sync: a.sync ?? null, anticipo_ms: a.anticipo_ms || 0,
    creato: serverTimestamp(), aggiornato: serverTimestamp()
  };
  if (Number.isInteger(a.segmento)) copia.segmento = a.segmento;
  const r = await addDoc(collection(db(), 'annotazioni'), copia);
  await carica(true); toast(t('a.copiaOk'));
  return { id: r.id, sessioneId: a.sessioneId, videoId: a.videoId };
}

// ------------------------------------------------------------------ editor di annotazione
async function leggiSessioneBytes(s) {
  const parti = [];
  for (let i = 0; i < s.nChunk; i++) {
    const rif = doc(db(), 'sessioni', s.id, 'chunk', String(i));
    let snap;
    try { snap = await getDocFromCache(rif); } catch (e) { snap = await getDoc(rif); }   // i chunk non cambiano: prima la cache locale
    if (!snap.exists()) throw new Error(t('a.pezzoMancante', { i: i + 1 }));
    parti.push(snap.data().data.toUint8Array());
  }
  const tot = parti.reduce((a, p) => a + p.length, 0), out = new Uint8Array(tot);
  let o = 0; for (const p of parti) { out.set(p, o); o += p.length; }
  return out;
}

async function apriEditor(sid, vid, aid) {
  if (![sid, vid, aid].every(x => /^[A-Za-z0-9]+$/.test(x))) return vistaSessioni();
  if (ctx) chiudiEditor();
  mostra('vistaEditor');
  $('vistaAnn').hidden = true;
  $('intestaAnn').innerHTML = '<span class="tenue">' + t('a.ed.caricamento') + '</span>';
  await carica(false);
  let s = D.sessioni.find(x => x.id === sid), v = D.video.find(x => x.id === vid);
  if (!s || !v) { await carica(true); s = D.sessioni.find(x => x.id === sid); v = D.video.find(x => x.id === vid); }
  if (!s || !v) { $('intestaAnn').innerHTML = '<span class="err">' + t('a.ed.nonTrovati') + '</span> <a href="#sessioni">' + t('a.ed.tornaElenco') + '</a>'; return; }
  let ann = null;
  if (aid !== 'nuova') {
    const sn = await getDoc(doc(db(), 'annotazioni', aid));
    if (!sn.exists()) { $('intestaAnn').innerHTML = '<span class="err">' + t('a.annNonTrovata') + '</span> <a href="#sessioni">' + t('a.ed.tornaElenco') + '</a>'; return; }
    ann = { id: sn.id, ...sn.data() };
  }
  const bytes = await leggiSessioneBytes(s);
  const sha = await sha256Bytes(bytes);
  ctx = { s, v, ann, aid: ann ? ann.id : null, mia: !ann || ann.autore.uid === utente.uid };
  window.SwimAnnotazione.azzera();
  await SD.carica(s.titolo + '.swr', bytes);
  window.SwimAnnotazione.carica(ann);
  window.SwimAnnotazione.stato.avviso = (sha !== s.sha256 ? t('a.ed.shaDiverso') + ' ' : '')
    + (Number(v.fps) !== 30 ? t('a.ed.fps', { fps: v.fps }) : '');
  intestaEditor();
  $('vistaAnn').hidden = false;
  window.SwimAnnotazione.aggiorna();
  window.SwimAnnotazione.controllaCopiaLocale(ann && ann.aggiornato && ann.aggiornato.toMillis ? ann.aggiornato.toMillis() : 0);
}
function intestaEditor() {
  const { s, v, ann, mia } = ctx;
  $('intestaAnn').innerHTML = `<div><h2>${esc(s.titolo)} <span class="tenue">· ${esc(s.data)}</span></h2>
    <div class="meta">${t('a.ed.video')} <b>${esc(v.nome)}</b> (${fmtDur(v.durata_s)}, ${esc(v.fps)} fps) · <a href="${esc(v.link)}" target="_blank" rel="noopener noreferrer">${t('a.ed.apriVideo')}</a> · ${ann ? t('a.ed.annDi', { nome: '<b>' + esc(ann.autore.nome) + '</b>' }) : t('a.ed.nuovaAnn')}${mia ? '' : ' · <span class="err">' + t('a.ed.soloLettura') + '</span>'}</div></div>
    <div class="riga"><a href="#sessioni"><button class="piccolo">${t('a.ed.elenco')}</button></a>${mia ? '' : '<button class="piccolo primario" id="bDupEd">' + t('a.duplica') + '</button>'}</div>`;
  const b = $('bDupEd');
  if (b) b.onclick = async () => { try { const n = await duplica(ctx.aid); location.hash = `#annota/${n.sessioneId}/${n.videoId}/${n.id}`; } catch (e) { toast(t('a.opErr', { e: e.code || e.message })); } };
}
function chiudiEditor() {
  if (!ctx) return;
  const SA = window.SwimAnnotazione;
  if (SA.stato.sporco && ctx.mia && confirm(t('a.ed.salvaChiudi'))) SA.salvaOra();
  ctx = null; SA.azzera(); SD.svuota();
}

// ganci usati da annotazione.js (salvataggio online, verifica del video)
window.SwimOnline = {
  chiave: () => ctx ? (ctx.aid ? 'a:' + ctx.aid : 'n:' + ctx.v.id + ':' + (utente ? utente.uid : '')) : null,
  puoSalvare: () => !!(ctx && ctx.mia),
  motivo: () => ctx && !ctx.mia ? t('a.ed.motivo') : '',
  async salva(a) {
    const c = ctx;            // il contesto puo' cambiare durante l'attesa (cambio pagina)
    const nome = (utente.displayName || utente.email || 'Utente').slice(0, 100);
    const dati = { eventi: a.eventi, offset_s: a.offset_s, sync: a.sync, anticipo_ms: a.anticipo_ms, aggiornato: serverTimestamp() };
    if (Number.isInteger(a.segmento)) dati.segmento = a.segmento;
    if (c.aid) { await updateDoc(doc(db(), 'annotazioni', c.aid), dati); }
    else {
      const r = await addDoc(collection(db(), 'annotazioni'), { ...dati, sessioneId: c.s.id, videoId: c.v.id, autore: { uid: utente.uid, nome }, creato: serverTimestamp() });
      c.aid = r.id; c.ann = { id: r.id, autore: { uid: utente.uid, nome } };
      if (ctx === c) { history.replaceState(null, '', `#annota/${c.s.id}/${c.v.id}/${r.id}`); intestaEditor(); }   // senza riattivare l'instradamento
    }
    D.caricato = false;      // l'elenco si rilegge alla prossima apertura
  },
  async verificaVideo(file, avanz) {
    const v = ctx && ctx.v; if (!v) return { ok: false, avviso: '' };
    if (file.size !== v.byte) return { ok: false, avviso: t('a.vv.dim', { s: fmtByte(file.size), nome: v.nome, b: fmtByte(v.byte) }) };
    const sha = await sha256File(file, avanz);
    if (sha !== v.sha256) return { ok: false, avviso: t('a.vv.sha', { nome: v.nome }) };
    return { ok: true, avviso: '' };
  }
};

// ------------------------------------------------------------------ amministrazione utenti
const ms = x => (x && x.toMillis ? x.toMillis() : 0);
const nomeStato = st => t('a.stato.' + st);
async function vistaAdmin() {
  mostra('vistaAdmin');
  $('vistaAdmin').innerHTML = '<div class="scheda vuoto">' + t('a.caricamento') + '</div>';
  const sn = await getDocs(collection(db(), 'users'));
  const utenti = sn.docs.map(d => ({ uid: d.id, ...d.data() }));
  utenti.sort((a, b) => ms(b.creato) - ms(a.creato));
  const gruppo = (titolo, stati, azioni) => {
    const li = utenti.filter(u => stati.includes(u.stato));
    return `<div class="scheda"><header><h2>${titolo} <small>${li.length}</small></h2></header>${li.length ? `<div class="tab-scroll"><table class="utenti"><thead><tr><th>${t('a.ad.utente')}</th><th>Email</th><th>${t('a.ad.richiesta')}</th><th>${t('a.ad.stato')}</th><th></th></tr></thead><tbody>` +
      li.map(u => `<tr><td>${u.foto ? `<img src="${esc(u.foto)}" alt="" referrerpolicy="no-referrer">` : ''}${esc(u.nome)}${u.uid === utente.uid ? ' <span class="chip">' + t('a.ad.tu') + '</span>' : ''}</td><td>${esc(u.email)}</td><td>${fmtData(u.creato)}</td><td><span class="chip ${u.stato === 'approvato' ? 'ok' : u.stato === 'in_attesa' ? 'att' : 'no'}">${esc(nomeStato(u.stato))}</span></td>
      <td class="riga">${azioni.map(([a, et, cls]) => `<button class="piccolo ${cls || ''}" data-uid="${esc(u.uid)}" data-stato="${a}">${et}</button>`).join('')}</td></tr>`).join('') + '</tbody></table></div>' : '<div class="vuoto">' + t('a.ad.nessuno') + '</div>'}</div>`;
  };
  $('vistaAdmin').innerHTML = `<div class="barra-titolo"><h1>${t('a.nav.utenti')}</h1><button class="piccolo" id="bAggU">${t('a.aggiorna')}</button></div><div class="pila">
    ${gruppo(t('a.ad.inAttesa'), ['in_attesa'], [['approvato', t('a.ad.approva'), 'primario'], ['rifiutato', t('a.ad.rifiuta'), 'pericolo']])}
    ${gruppo(t('a.ad.approvati'), ['approvato'], [['revocato', t('a.ad.revoca'), 'pericolo']])}
    ${gruppo(t('a.ad.rifRev'), ['rifiutato', 'revocato'], [['approvato', t('a.ad.approva')]])}</div>`;
  $('bAggU').onclick = vistaAdmin;
  $('vistaAdmin').onclick = async e => {
    const b = e.target.closest('button[data-stato]'); if (!b) return;
    b.disabled = true;
    try { await updateDoc(doc(db(), 'users', b.dataset.uid), { stato: b.dataset.stato, deciso: serverTimestamp(), decisoDa: utente.uid }); toast(t('a.ad.statoAgg')); await vistaAdmin(); }
    catch (err) { toast(t('a.opErr', { e: err.code || err.message })); b.disabled = false; }
  };
}

// ------------------------------------------------------------------ messaggi del modulo contatti (solo amministratore)
let MSG = [];
/** Numero di messaggi non letti: una query di conteggio (costa pochissime letture). */
async function aggiornaBadge() {
  try {
    const c = await getCountFromServer(query(collection(db(), 'contatti'), where('letto', '==', false)));
    mostraBadge(c.data().count);
  } catch (e) { console.error(e); }
}
function mostraBadge(n) { const b = $('badgeMsg'); b.hidden = !n; b.textContent = n > 99 ? '99+' : String(n); }
async function vistaMessaggi() {
  mostra('vistaMessaggi');
  $('vistaMessaggi').innerHTML = '<div class="scheda vuoto">' + t('a.caricamento') + '</div>';
  const sn = await getDocs(collection(db(), 'contatti'));
  MSG = sn.docs.map(d => ({ id: d.id, ...d.data() })).sort((a, b) => ms(b.creato) - ms(a.creato));
  disegnaMessaggi();
}
function disegnaMessaggi() {
  const nonLetti = MSG.filter(m => m.letto !== true).length;
  mostraBadge(nonLetti);
  const el = $('vistaMessaggi');
  el.innerHTML = `<div class="barra-titolo"><h1>${t('a.nav.messaggi')} <small class="tenue">${t('a.msg.nonLetti', { n: nonLetti })}</small></h1><button class="piccolo" id="bAggM">${t('a.aggiorna')}</button></div>`
    + (MSG.length ? '<div class="pila">' + MSG.map(m => {
      const ogg = encodeURIComponent(t('a.msg.oggetto'));
      return `<article class="scheda messaggio ${m.letto === true ? '' : 'nuovo'}" data-id="${esc(m.id)}">
        <div class="sess-testa"><div><b>${esc(m.nome || t('a.msg.anonimo'))}</b> · <a href="mailto:${esc(m.email)}?subject=${ogg}">${esc(m.email)}</a>
          <div class="meta">${fmtData(m.creato)} · ${esc((m.lingua || '').toUpperCase())}</div></div>
          <div class="riga">${m.letto === true ? `<button class="piccolo" data-m="nonletto">${t('a.msg.segnaNonLetto')}</button>` : `<button class="piccolo primario" data-m="letto">${t('a.msg.segnaLetto')}</button>`}
          <button class="piccolo pericolo" data-m="elimina">${t('a.elimina')}</button></div></div>
        <div class="testo">${esc(m.messaggio)}</div></article>`;
    }).join('') + '</div>' : '<div class="scheda vuoto">' + t('a.msg.nessuno') + '</div>');
  $('bAggM').onclick = vistaMessaggi;
}
$('vistaMessaggi').addEventListener('click', async e => {
  const b = e.target.closest('button[data-m]'); if (!b) return;
  const id = b.closest('[data-id]').dataset.id, m = MSG.find(x => x.id === id);
  b.disabled = true;
  try {
    if (b.dataset.m === 'elimina') {
      if (!confirm(t('a.msg.confElimina'))) { b.disabled = false; return; }
      await deleteDoc(doc(db(), 'contatti', id)); MSG = MSG.filter(x => x.id !== id); toast(t('a.msg.eliminato'));
    } else {
      const letto = b.dataset.m === 'letto';
      await updateDoc(doc(db(), 'contatti', id), { letto }); m.letto = letto;
    }
    disegnaMessaggi();
  } catch (err) { toast(t('a.opErr', { e: err.code || err.message })); b.disabled = false; }
});

// ------------------------------------------------------------------ cambio lingua: ridisegna la vista corrente
document.addEventListener('swt-lingua', () => {
  document.getElementById('toast').textContent = '';
  if (!utente) return;
  if (vistaCorrente === 'vistaStato' && profilo) schermataStato();
  else if (vistaCorrente === 'vistaSessioni') disegnaSessioni();
  else if (vistaCorrente === 'vistaAdmin') vistaAdmin().catch(console.error);
  else if (vistaCorrente === 'vistaMessaggi') disegnaMessaggi();
  else if (vistaCorrente === 'vistaEditor' && ctx) { intestaEditor(); window.SwimAnnotazione.aggiorna(); }
});
