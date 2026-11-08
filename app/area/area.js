/* SwimTimer - area riservata: accesso, approvazione, elenco sessioni/video/annotazioni, amministrazione, editor.
 * Letture parsimoniose (piano Spark): niente listener in tempo reale; 3 query all'apertura dell'elenco (sessioni, video,
 * annotazioni), tenute in memoria finche' non si preme «Aggiorna»; i chunk .swr (immutabili) prima dalla cache locale. */
import { auth, db, osserva, accedi, esci, assicuraUtente, collection, doc, getDocs, getDoc, getDocFromCache, setDoc, addDoc, updateDoc,
  deleteDoc, query, where, limit, serverTimestamp, Bytes } from '../comune/fb.js';
import { sha256Bytes, sha256File } from '../comune/sha256.js';

const SWR = window.SWR, SD = window.SwimDati;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const CHUNK = 800 * 1024;                       // <= 900000 consentiti dalle regole (limite documento 1 MiB)
const MAX_SWR = 4 * 1024 * 1024;
const RE_LINK = /^https:\/\/(drive\.google\.com|docs\.google\.com|youtu\.be|www\.youtube\.com|youtube\.com)\/.*/;
const fmtByte = n => n >= 1048576 ? (n / 1048576).toFixed(1) + ' MiB' : (n / 1024).toFixed(0) + ' KiB';
const fmtData = ts => ts && ts.toDate ? ts.toDate().toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' }) : '–';
const fmtDur = s => { s = Math.round(s); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };

let utente = null;          // utente Firebase
let profilo = null;         // documento users/{uid}
let admin = false;
let D = { sessioni: [], video: [], annot: [], caricato: false };
let ctx = null;             // contesto dell'editor aperto

function toast(t) { const e = $('toast'); e.textContent = t; e.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => e.classList.remove('on'), 3500); }
const mostra = id => ['vistaLogin', 'vistaStato', 'vistaSessioni', 'vistaAdmin', 'vistaEditor'].forEach(v => { $(v).hidden = v !== id; });
const approvato = () => admin || (profilo && profilo.stato === 'approvato');

// ------------------------------------------------------------------ accesso
$('btnAccedi').onclick = async () => {
  $('erroreLogin').textContent = '';
  try { await accedi(); } catch (e) { $('erroreLogin').textContent = 'Accesso non riuscito: ' + (e.code || e.message); }
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
    $('vistaStato').innerHTML = `<h1>Errore</h1><p class="err">${esc(e.code || e.message)}</p><p class="tenue">Controlla la connessione e ricarica la pagina.</p>`;
    mostra('vistaStato'); return;
  }
  $('navAdmin').hidden = !admin;
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
    in_attesa: ['Account in attesa di approvazione', 'Hai effettuato l\'accesso come <b>' + esc(profilo.email) + '</b>. L\'amministratore deve approvare il tuo account prima che tu possa vedere sessioni, video e annotazioni. Riprova più tardi.'],
    rifiutato: ['Richiesta di accesso rifiutata', 'L\'amministratore non ha approvato questo account. Se pensi sia un errore, contatta chi gestisce il progetto.'],
    revocato: ['Accesso revocato', 'L\'accesso di questo account è stato revocato dall\'amministratore.']
  }[st] || ['Stato account non riconosciuto', esc(st)];
  $('vistaStato').innerHTML = `<h1>${testi[0]}</h1><p class="tenue">${testi[1]}</p><p><button id="btnRiprova">Ricontrolla</button> <button id="btnEsci2">Esci</button></p>`;
  $('btnRiprova').onclick = async () => { admin = await sonoAdmin(utente); $('navAdmin').hidden = !admin; profilo = await assicuraUtente(utente); instrada(); };
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
    if (p[0] === 'annota' && p.length >= 4) return await apriEditor(p[1], p[2], p[3]);
    return await vistaSessioni();
  } catch (e) { console.error(e); toast('Errore: ' + (e.code || e.message)); }
}

// ------------------------------------------------------------------ dati (letture una tantum)
async function carica(forza) {
  if (D.caricato && !forza) return;
  const d = db();
  const [s, v, a] = await Promise.all([getDocs(collection(d, 'sessioni')), getDocs(collection(d, 'video')), getDocs(collection(d, 'annotazioni'))]);
  const m = x => ({ id: x.id, ...x.data() });
  D = { sessioni: s.docs.map(m), video: v.docs.map(m), annot: a.docs.map(m), caricato: true };
  const t = x => (x && x.toMillis ? x.toMillis() : 0);
  D.sessioni.sort((x, y) => String(y.data).localeCompare(String(x.data)) || t(y.caricatoIl) - t(x.caricatoIl));
  D.video.sort((x, y) => t(x.caricatoIl) - t(y.caricatoIl));
  D.annot.sort((x, y) => t(y.aggiornato) - t(x.aggiornato));
}
const puoGestire = x => admin || (x.caricatoDa && x.caricatoDa.uid === utente.uid);

// ------------------------------------------------------------------ elenco sessioni
async function vistaSessioni() {
  mostra('vistaSessioni');
  if (!D.caricato) $('vistaSessioni').innerHTML = '<div class="scheda vuoto">Caricamento…</div>';
  await carica(false);
  disegnaSessioni();
}
function disegnaSessioni() {
  const el = $('vistaSessioni');
  let h = `<div class="barra-titolo"><h1>Sessioni</h1><div class="riga"><button id="bAgg" class="piccolo">Aggiorna</button><button id="bNuova" class="primario">Carica registrazione .swr</button></div></div>`;
  if (!D.sessioni.length) h += '<div class="scheda vuoto">Nessuna sessione. Carica la prima registrazione .swr scaricata dal tag.</div>';
  h += '<div class="pila">' + D.sessioni.map(sessioneHtml).join('') + '</div>';
  el.innerHTML = h;
  $('bNuova').onclick = () => dialogoSessione();
  $('bAgg').onclick = async () => { await carica(true); disegnaSessioni(); toast('Elenco aggiornato'); };
}
function sessioneHtml(s) {
  const mie = puoGestire(s);
  const videos = D.video.filter(v => v.sessioneId === s.id);
  return `<article class="scheda" data-sid="${esc(s.id)}">
    <div class="sess-testa"><div>
      <h3>${esc(s.titolo)} ${s.completa ? '' : '<span class="chip att">caricamento incompleto</span>'}</h3>
      <div class="meta"><b>${esc(s.data)}</b> · caricata da <b>${esc(s.caricatoDa.nome)}</b> il ${fmtData(s.caricatoIl)} · ${fmtByte(s.byte)} · <span class="mono" title="sha256 ${esc(s.sha256)}">${esc(s.sha256.slice(0, 10))}…</span></div>
      ${s.nota ? `<p class="nota-sess">${esc(s.nota)}</p>` : ''}</div>
      <div class="riga"><button class="piccolo" data-act="nuovo-video" data-sid="${esc(s.id)}" ${s.completa ? '' : 'disabled'}>Aggiungi video</button>
        ${mie ? `<button class="piccolo" data-act="mod-sess" data-sid="${esc(s.id)}">Modifica</button><button class="piccolo pericolo" data-act="del-sess" data-sid="${esc(s.id)}">Elimina</button>` : ''}</div></div>
    <div class="sotto">${videos.length ? videos.map(v => videoHtml(v)).join('') : '<div class="meta">Nessun video collegato. I video non si caricano qui: si registra il link (Google Drive o YouTube non in elenco) e l\'impronta del file.</div>'}</div>
  </article>`;
}
function videoHtml(v) {
  const ann = D.annot.filter(a => a.videoId === v.id);
  const mie = puoGestire(v);
  return `<div class="video-riga">
    <div class="titolo"><div><b>${esc(v.nome)}</b> <span class="meta">${fmtByte(v.byte)} · ${fmtDur(v.durata_s)} · ${esc(v.fps)} fps · da ${esc(v.caricatoDa.nome)} · <a href="${esc(v.link)}" target="_blank" rel="noopener noreferrer">apri il video</a></span></div>
      <div class="riga"><button class="piccolo primario" data-act="nuova-ann" data-sid="${esc(v.sessioneId)}" data-vid="${esc(v.id)}">Nuova annotazione</button>
      ${mie ? `<button class="piccolo pericolo" data-act="del-video" data-vid="${esc(v.id)}">Elimina video</button>` : ''}</div></div>
    ${ann.map(a => annotHtml(a)).join('')}
  </div>`;
}
function annotHtml(a) {
  const mia = a.autore.uid === utente.uid;
  return `<div class="annot ${mia ? 'mia' : ''}"><div><b>${esc(a.autore.nome)}</b>${mia ? ' <span class="chip ok">tua</span>' : ''} · <span class="meta">${a.eventi.length} eventi · aggiornata ${fmtData(a.aggiornato)}</span></div>
    <div class="azioni"><button class="piccolo" data-act="apri-ann" data-sid="${esc(a.sessioneId)}" data-vid="${esc(a.videoId)}" data-aid="${esc(a.id)}">Apri</button>
    ${mia ? '' : `<button class="piccolo" data-act="dup-ann" data-aid="${esc(a.id)}">Duplica come mia</button>`}
    ${mia || admin ? `<button class="piccolo pericolo" data-act="del-ann" data-aid="${esc(a.id)}">Elimina</button>` : ''}</div></div>`;
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
  } catch (err) { console.error(err); toast('Operazione non riuscita: ' + (err.code || err.message)); }
});

// ------------------------------------------------------------------ dialoghi
const dlg = $('dlg');
function apriDialogo(html) { dlg.innerHTML = html; if (!dlg.open) dlg.showModal(); return dlg; }
dlg.addEventListener('cancel', e => { if (dlg.dataset.occupato === '1') e.preventDefault(); });
function chiudiDialogo() { dlg.dataset.occupato = '0'; dlg.close(); }

function dialogoSessione(s) {
  const nuova = !s;
  const oggi = new Date().toISOString().slice(0, 10);
  apriDialogo(`<form method="dialog" id="fSess"><h3>${nuova ? 'Carica registrazione .swr' : 'Modifica sessione'}</h3>
    ${nuova ? '<label>File .swr (scaricato dal tag)<input type="file" id="fFile" accept=".swr,application/octet-stream" required></label>' : ''}
    <label>Titolo<input type="text" id="fTit" maxlength="120" required value="${esc(s ? s.titolo : '')}" placeholder="es. Prova vasca 25 m, 5 min"></label>
    <label>Data della prova<input type="date" id="fData" required value="${esc(s ? s.data : oggi)}"></label>
    <label>Nota (facoltativa)<textarea id="fNota" rows="3" maxlength="1000">${esc(s ? s.nota || '' : '')}</textarea></label>
    <div class="meta">${nuova ? 'Il file viene controllato (formato .swr), ne viene calcolato lo sha256 e viene caricato a pezzi nell\'archivio condiviso. Nessun dato reale nel repository: qui solo nell\'archivio privato.' : ''}</div>
    <div class="barra" id="fBarra" hidden><div></div></div><div class="meta" id="fMsg"></div>
    <div class="azioni"><button type="button" id="fAnnulla">Annulla</button><button class="primario" id="fOk">${nuova ? 'Carica' : 'Salva'}</button></div></form>`);
  $('fAnnulla').onclick = chiudiDialogo;
  $('fSess').onsubmit = async ev => {
    ev.preventDefault();
    const tit = $('fTit').value.trim(), data = $('fData').value, nota = $('fNota').value.trim();
    $('fOk').disabled = true; dlg.dataset.occupato = '1';
    try {
      if (nuova) await caricaSessione($('fFile').files[0], tit, data, nota, (f, t, m) => { $('fBarra').hidden = false; $('fBarra').firstElementChild.style.width = (100 * f / t) + '%'; $('fMsg').textContent = m; });
      else { const dati = { titolo: tit, data, completa: s.completa }; if (nota) dati.nota = nota; else if (s.nota) dati.nota = ''; await updateDoc(doc(db(), 'sessioni', s.id), dati); await carica(true); }
      chiudiDialogo(); disegnaSessioni(); toast(nuova ? 'Sessione caricata' : 'Sessione aggiornata');
    } catch (err) { console.error(err); $('fMsg').className = 'meta err'; $('fMsg').textContent = err.message || err.code; $('fOk').disabled = false; dlg.dataset.occupato = '0'; }
  };
}

async function caricaSessione(file, titolo, data, nota, prog) {
  if (!file) throw new Error('Scegli un file .swr');
  if (file.size > MAX_SWR) throw new Error('File troppo grande (massimo ' + fmtByte(MAX_SWR) + ')');
  prog(0, 1, 'Lettura e controllo del file…');
  const bytes = new Uint8Array(await file.arrayBuffer());
  let es;
  try { es = SWR.decodifica(bytes); } catch (e) { throw new Error('File non valido (non è una registrazione .swr): ' + e.message); }
  if (!SWR.segmentiConDati(es).length) throw new Error('Il file non contiene campioni di movimento.');
  const sha = await sha256Bytes(bytes);
  await carica(false);
  const dup = D.sessioni.find(s => s.sha256 === sha);
  if (dup) throw new Error('Questa registrazione è già stata caricata: «' + dup.titolo + '» (' + dup.caricatoDa.nome + ').');
  const n = Math.ceil(bytes.length / CHUNK);
  const ref = doc(collection(db(), 'sessioni'));
  const dati = { titolo, data, caricatoDa: { uid: utente.uid, nome: (utente.displayName || utente.email || 'Utente').slice(0, 100) }, caricatoIl: serverTimestamp(), sha256: sha, byte: bytes.length, nChunk: n, completa: false };
  if (nota) dati.nota = nota;
  await setDoc(ref, dati);
  try {
    for (let i = 0; i < n; i++) {
      prog(i, n, `Caricamento del pezzo ${i + 1} di ${n}…`);
      await setDoc(doc(ref, 'chunk', String(i)), { n: i, data: Bytes.fromUint8Array(bytes.slice(i * CHUNK, (i + 1) * CHUNK)) });
    }
    await updateDoc(ref, { completa: true });
  } catch (e) {                                  // caricamento interrotto: ripulisce quel che c'e'
    for (let i = 0; i < n; i++) { try { await deleteDoc(doc(ref, 'chunk', String(i))); } catch (x) { /* ignora */ } }
    try { await deleteDoc(ref); } catch (x) { /* ignora */ }
    throw e;
  }
  prog(n, n, 'Fatto.');
  await carica(true);
}

function dialogoVideo(sid) {
  const s = D.sessioni.find(x => x.id === sid);
  apriDialogo(`<form method="dialog" id="fVid"><h3>Aggiungi video a «${esc(s.titolo)}»</h3>
    <p class="meta">Il video <b>non</b> viene caricato qui. Scegli il file locale (ne calcoliamo impronta, dimensione e durata nel browser), caricalo tu su Google Drive o YouTube (non in elenco) e incolla il link.</p>
    <label>File video locale (MP4 H.264, 30 fps)<input type="file" id="vFile" accept="video/*" required></label>
    <div class="barra" id="vBarra" hidden><div></div></div><div class="meta" id="vInfo"></div>
    <label>Link Google Drive o YouTube<input type="url" id="vLink" required maxlength="500" placeholder="https://drive.google.com/file/d/…"></label>
    <label>Fotogrammi al secondo<input type="number" id="vFps" min="1" max="240" step="0.001" value="30"></label>
    <div class="meta" id="vMsg"></div>
    <div class="azioni"><button type="button" id="vAnnulla">Annulla</button><button class="primario" id="vOk" disabled>Salva video</button></div></form>`);
  let info = null;
  $('vAnnulla').onclick = chiudiDialogo;
  $('vFile').onchange = async () => {
    const f = $('vFile').files[0]; info = null; $('vOk').disabled = true; if (!f) return;
    dlg.dataset.occupato = '1'; $('vBarra').hidden = false;
    try {
      const durata = await durataVideo(f);
      const sha = await sha256File(f, (a, t) => { $('vBarra').firstElementChild.style.width = (100 * a / t) + '%'; $('vInfo').textContent = 'Calcolo impronta sha256: ' + Math.round(100 * a / t) + '%'; });
      info = { nome: f.name.slice(0, 200), byte: f.size, sha256: sha, durata_s: durata };
      $('vInfo').innerHTML = `${esc(f.name)} · ${fmtByte(f.size)} · ${fmtDur(durata)} · <span class="mono">${sha.slice(0, 12)}…</span>`;
      const dup = D.video.find(v => v.sessioneId === sid && v.sha256 === sha);
      $('vMsg').textContent = dup ? 'Attenzione: questo stesso file è già registrato per la sessione («' + dup.nome + '»).' : '';
      $('vOk').disabled = false;
    } catch (e) { $('vInfo').textContent = 'Impossibile leggere il video: ' + e.message; }
    dlg.dataset.occupato = '0';
  };
  $('fVid') && ($('fVid').onsubmit = async ev => {
    ev.preventDefault();
    const link = $('vLink').value.trim(), fps = Number($('vFps').value);
    if (!RE_LINK.test(link)) { $('vMsg').className = 'meta err'; $('vMsg').textContent = 'Il link deve iniziare con https:// e puntare a Google Drive o YouTube.'; return; }
    if (!(fps > 0 && fps <= 240)) { $('vMsg').className = 'meta err'; $('vMsg').textContent = 'Fotogrammi al secondo non validi.'; return; }
    $('vOk').disabled = true;
    try {
      await addDoc(collection(db(), 'video'), { sessioneId: sid, link, ...info, fps, caricatoDa: { uid: utente.uid, nome: (utente.displayName || utente.email || 'Utente').slice(0, 100) }, caricatoIl: serverTimestamp() });
      await carica(true); chiudiDialogo(); disegnaSessioni(); toast('Video registrato');
    } catch (err) { console.error(err); $('vMsg').className = 'meta err'; $('vMsg').textContent = err.message || err.code; $('vOk').disabled = false; }
  });
}
function durataVideo(file) {
  return new Promise((ok, ko) => {
    const v = document.createElement('video'), url = URL.createObjectURL(file);
    v.preload = 'metadata';
    v.onloadedmetadata = () => { const d = v.duration; URL.revokeObjectURL(url); isFinite(d) && d > 0 ? ok(d) : ko(new Error('durata non leggibile')); };
    v.onerror = () => { URL.revokeObjectURL(url); ko(new Error('formato non riconosciuto dal browser (prova un MP4 H.264)')); };
    v.src = url;
  });
}

// ------------------------------------------------------------------ eliminazioni
async function eliminaSessione(sid) {
  const s = D.sessioni.find(x => x.id === sid);
  const video = D.video.filter(v => v.sessioneId === sid), ann = D.annot.filter(a => a.sessioneId === sid);
  const altrui = [...video.filter(v => v.caricatoDa.uid !== utente.uid), ...ann.filter(a => a.autore.uid !== utente.uid)];
  if (altrui.length && !admin) { toast('Non puoi eliminarla: ci sono video o annotazioni di altri utenti collegati.'); return; }
  if (!confirm(`Eliminare definitivamente «${s.titolo}» con ${video.length} video e ${ann.length} annotazioni collegati? L'operazione non si può annullare.`)) return;
  for (const a of ann) await deleteDoc(doc(db(), 'annotazioni', a.id));
  for (const v of video) await deleteDoc(doc(db(), 'video', v.id));
  for (let i = 0; i < (s.nChunk || 6); i++) { try { await deleteDoc(doc(db(), 'sessioni', sid, 'chunk', String(i))); } catch (e) { /* assente */ } }
  await deleteDoc(doc(db(), 'sessioni', sid));
  await carica(true); disegnaSessioni(); toast('Sessione eliminata');
}
async function eliminaVideo(vid) {
  const ann = D.annot.filter(a => a.videoId === vid);
  if (ann.some(a => a.autore.uid !== utente.uid) && !admin) { toast('Non puoi eliminarlo: ci sono annotazioni di altri utenti.'); return; }
  if (!confirm(`Eliminare il riferimento al video e le ${ann.length} annotazioni collegate? (Il file su Drive/YouTube non viene toccato.)`)) return;
  for (const a of ann) await deleteDoc(doc(db(), 'annotazioni', a.id));
  await deleteDoc(doc(db(), 'video', vid));
  await carica(true); disegnaSessioni(); toast('Video eliminato');
}
async function eliminaAnnotazione(aid) {
  if (!confirm('Eliminare questa annotazione?')) return;
  await deleteDoc(doc(db(), 'annotazioni', aid));
  await carica(true); disegnaSessioni(); toast('Annotazione eliminata');
}
async function duplica(aid) {
  let a = D.annot.find(x => x.id === aid);
  if (!a) { const sn = await getDoc(doc(db(), 'annotazioni', aid)); if (!sn.exists()) throw new Error('annotazione non trovata'); a = { id: sn.id, ...sn.data() }; }
  const copia = {
    sessioneId: a.sessioneId, videoId: a.videoId, autore: { uid: utente.uid, nome: (utente.displayName || utente.email || 'Utente').slice(0, 100) },
    eventi: a.eventi, offset_s: a.offset_s ?? null, sync: a.sync ?? null, anticipo_ms: a.anticipo_ms || 0,
    creato: serverTimestamp(), aggiornato: serverTimestamp()
  };
  if (Number.isInteger(a.segmento)) copia.segmento = a.segmento;
  const r = await addDoc(collection(db(), 'annotazioni'), copia);
  await carica(true); toast('Copia creata: ora è tua');
  return { id: r.id, sessioneId: a.sessioneId, videoId: a.videoId };
}

// ------------------------------------------------------------------ editor di annotazione
async function leggiSessioneBytes(s) {
  const parti = [];
  for (let i = 0; i < s.nChunk; i++) {
    const rif = doc(db(), 'sessioni', s.id, 'chunk', String(i));
    let snap;
    try { snap = await getDocFromCache(rif); } catch (e) { snap = await getDoc(rif); }   // i chunk non cambiano: prima la cache locale
    if (!snap.exists()) throw new Error('pezzo ' + (i + 1) + ' della registrazione mancante');
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
  $('intestaAnn').innerHTML = '<span class="tenue">Caricamento dei dati dall\'archivio…</span>';
  await carica(false);
  let s = D.sessioni.find(x => x.id === sid), v = D.video.find(x => x.id === vid);
  if (!s || !v) { await carica(true); s = D.sessioni.find(x => x.id === sid); v = D.video.find(x => x.id === vid); }
  if (!s || !v) { $('intestaAnn').innerHTML = '<span class="err">Sessione o video non trovati.</span> <a href="#sessioni">Torna all\'elenco</a>'; return; }
  let ann = null;
  if (aid !== 'nuova') {
    const sn = await getDoc(doc(db(), 'annotazioni', aid));
    if (!sn.exists()) { $('intestaAnn').innerHTML = '<span class="err">Annotazione non trovata.</span> <a href="#sessioni">Torna all\'elenco</a>'; return; }
    ann = { id: sn.id, ...sn.data() };
  }
  const bytes = await leggiSessioneBytes(s);
  const sha = await sha256Bytes(bytes);
  ctx = { s, v, ann, aid: ann ? ann.id : null, mia: !ann || ann.autore.uid === utente.uid };
  window.SwimAnnotazione.azzera();
  await SD.carica(s.titolo + '.swr', bytes);
  window.SwimAnnotazione.carica(ann);
  window.SwimAnnotazione.stato.avviso = (sha !== s.sha256 ? 'ATTENZIONE: i dati scaricati non corrispondono all\'impronta registrata della sessione. ' : '')
    + (Number(v.fps) !== 30 ? `Il video è registrato a ${v.fps} fps ma lo strumento lavora a 30 fps: i tempi per fotogramma potrebbero non essere esatti.` : '');
  intestaEditor();
  $('vistaAnn').hidden = false;
  window.SwimAnnotazione.aggiorna();
  window.SwimAnnotazione.controllaCopiaLocale(ann && ann.aggiornato && ann.aggiornato.toMillis ? ann.aggiornato.toMillis() : 0);
}
function intestaEditor() {
  const { s, v, ann, mia } = ctx;
  $('intestaAnn').innerHTML = `<div><h2>${esc(s.titolo)} <span class="tenue">· ${esc(s.data)}</span></h2>
    <div class="meta">Video <b>${esc(v.nome)}</b> (${fmtDur(v.durata_s)}, ${esc(v.fps)} fps) · <a href="${esc(v.link)}" target="_blank" rel="noopener noreferrer">apri il video su Drive/YouTube</a> · ${ann ? `annotazione di <b>${esc(ann.autore.nome)}</b>` : 'nuova annotazione (tua)'}${mia ? '' : ' · <span class="err">sola lettura</span>'}</div></div>
    <div class="riga"><a href="#sessioni"><button class="piccolo">← Elenco</button></a>${mia ? '' : '<button class="piccolo primario" id="bDupEd">Duplica come mia</button>'}</div>`;
  const b = $('bDupEd');
  if (b) b.onclick = async () => { try { const n = await duplica(ctx.aid); location.hash = `#annota/${n.sessioneId}/${n.videoId}/${n.id}`; } catch (e) { toast('Operazione non riuscita: ' + (e.code || e.message)); } };
}
function chiudiEditor() {
  if (!ctx) return;
  const SA = window.SwimAnnotazione;
  if (SA.stato.sporco && ctx.mia && confirm('Ci sono modifiche non ancora salvate online. Salvarle ora? (Annulla: restano solo nella copia locale del browser.)')) SA.salvaOra();
  ctx = null; SA.azzera(); SD.svuota();
}

// ganci usati da annotazione.js (salvataggio online, verifica del video)
window.SwimOnline = {
  chiave: () => ctx ? (ctx.aid ? 'a:' + ctx.aid : 'n:' + ctx.v.id + ':' + (utente ? utente.uid : '')) : null,
  puoSalvare: () => !!(ctx && ctx.mia),
  motivo: () => ctx && !ctx.mia ? 'Annotazione di un altro autore: sola lettura. Usa «Duplica come mia» per modificarla.' : '',
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
    if (file.size !== v.byte) return { ok: false, avviso: `ATTENZIONE: il file scelto (${fmtByte(file.size)}) ha una dimensione diversa dal video registrato «${v.nome}» (${fmtByte(v.byte)}): non è lo stesso video, gli eventi potrebbero non combaciare.` };
    const sha = await sha256File(file, avanz);
    if (sha !== v.sha256) return { ok: false, avviso: `ATTENZIONE: l'impronta sha256 del file scelto non corrisponde a quella del video registrato «${v.nome}»: non è lo stesso file (o è stato ricodificato).` };
    return { ok: true, avviso: '' };
  }
};

// ------------------------------------------------------------------ amministrazione utenti
async function vistaAdmin() {
  mostra('vistaAdmin');
  $('vistaAdmin').innerHTML = '<div class="scheda vuoto">Caricamento…</div>';
  const sn = await getDocs(collection(db(), 'users'));
  const utenti = sn.docs.map(d => ({ uid: d.id, ...d.data() }));
  const t = x => (x && x.toMillis ? x.toMillis() : 0);
  utenti.sort((a, b) => t(b.creato) - t(a.creato));
  const gruppo = (titolo, stati, azioni) => {
    const li = utenti.filter(u => stati.includes(u.stato));
    return `<div class="scheda"><header><h2>${titolo} <small>${li.length}</small></h2></header>${li.length ? `<div class="tab-scroll"><table class="utenti"><thead><tr><th>Utente</th><th>Email</th><th>Richiesta</th><th>Stato</th><th></th></tr></thead><tbody>` +
      li.map(u => `<tr><td>${u.foto ? `<img src="${esc(u.foto)}" alt="" referrerpolicy="no-referrer">` : ''}${esc(u.nome)}${u.uid === utente.uid ? ' <span class="chip">tu</span>' : ''}</td><td>${esc(u.email)}</td><td>${fmtData(u.creato)}</td><td><span class="chip ${u.stato === 'approvato' ? 'ok' : u.stato === 'in_attesa' ? 'att' : 'no'}">${esc(u.stato.replace('_', ' '))}</span></td>
      <td class="riga">${azioni.map(([a, et, cls]) => `<button class="piccolo ${cls || ''}" data-uid="${esc(u.uid)}" data-stato="${a}">${et}</button>`).join('')}</td></tr>`).join('') + '</tbody></table></div>' : '<div class="vuoto">Nessuno.</div>'}</div>`;
  };
  $('vistaAdmin').innerHTML = `<div class="barra-titolo"><h1>Utenti</h1><button class="piccolo" id="bAggU">Aggiorna</button></div><div class="pila">
    ${gruppo('In attesa di approvazione', ['in_attesa'], [['approvato', 'Approva', 'primario'], ['rifiutato', 'Rifiuta', 'pericolo']])}
    ${gruppo('Approvati', ['approvato'], [['revocato', 'Revoca', 'pericolo']])}
    ${gruppo('Rifiutati o revocati', ['rifiutato', 'revocato'], [['approvato', 'Approva']])}</div>`;
  $('bAggU').onclick = vistaAdmin;
  $('vistaAdmin').onclick = async e => {
    const b = e.target.closest('button[data-stato]'); if (!b) return;
    b.disabled = true;
    try { await updateDoc(doc(db(), 'users', b.dataset.uid), { stato: b.dataset.stato, deciso: serverTimestamp(), decisoDa: utente.uid }); toast('Stato aggiornato'); await vistaAdmin(); }
    catch (err) { toast('Operazione non riuscita: ' + (err.code || err.message)); b.disabled = false; }
  };
}
