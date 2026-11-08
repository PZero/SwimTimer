/* SwimTimer - «Carica online» della pagina Strumenti (solo quando e' servita da swimtimer-pzero.web.app/strumenti/).
 * Prende il .swr corrente (window.SwimDati, scheda Registrazione), controlla accesso e approvazione come l'area riservata e crea
 * sessioni/{id} + chunk con comune/sessioni.js (stessi campi e stesse regole). La pagina Strumenti resta in italiano. */
import { osserva, accedi, assicuraUtente, db, collection, getDocs, query, limit } from './fb.js';
import { caricaSessione, fmtByte } from './sessioni.js';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SD = window.SwimDati;
const btn = $('rgOnline'), box = $('rgOnlineBox');
let utente = null, aperto = false, occupato = false;

osserva(u => { utente = u; if (aperto && !occupato) disegna(); });
btn.hidden = false;
btn.addEventListener('click', () => { aperto = true; disegna(); });
SD.su(() => { btn.disabled = !SD.es; if (!SD.es) { aperto = false; box.innerHTML = ''; } });
btn.disabled = !SD.es;

async function approvato(u) {
  const p = await assicuraUtente(u);
  if (p.stato === 'approvato') return { ok: true };
  try { await getDocs(query(collection(db(), 'users'), limit(1))); return { ok: true }; } catch (e) { /* non e' admin */ }
  return { ok: false, stato: p.stato };
}

async function disegna() {
  if (!SD.es) return;
  if (!utente) {
    box.innerHTML = '<div class="ann-nota">Per caricare la registrazione nell\'archivio condiviso devi accedere con un account Google <b>approvato</b>.</div><div class="swr-riga"><button class="primario" id="rgOnlineAccedi">Accedi con Google</button></div><div class="swr-stato err" id="rgOnlineErr"></div>';
    $('rgOnlineAccedi').onclick = async () => { try { await accedi(); } catch (e) { $('rgOnlineErr').textContent = 'Accesso non riuscito (' + (e.code || e.message) + ').'; } };
    return;
  }
  box.innerHTML = '<div class="tenue">Controllo dell\'account…</div>';
  let a;
  try { a = await approvato(utente); } catch (e) { box.innerHTML = '<div class="swr-stato err">Errore: ' + esc(e.code || e.message) + '</div>'; return; }
  if (!a.ok) { box.innerHTML = '<div class="swr-stato err">L\'account ' + esc(utente.email) + ' non è approvato (stato: ' + esc(a.stato) + '). Chiedi l\'approvazione all\'amministratore dall\'<a href="/area/">area riservata</a>.</div>'; return; }
  const base = (SD.nome || 'registrazione').replace(/\.swr$/i, '');
  const m = /^(\d{4})(\d{2})(\d{2})_/.exec(base);
  const data = m ? `${m[1]}-${m[2]}-${m[3]}` : new Date().toISOString().slice(0, 10);
  box.innerHTML = `<form id="rgOnlineForm" class="rg-online">
    <div class="ann-nota">Accesso come <b>${esc(utente.displayName || utente.email)}</b>. Il file (${fmtByte(SD.bytes.length)}) viene caricato a pezzi nell'archivio privato dei membri approvati.</div>
    <label>Titolo <input type="text" id="rgoTit" maxlength="120" required value="${esc(base)}"></label>
    <label>Data della prova <input type="date" id="rgoData" required value="${data}"></label>
    <label>Nota (facoltativa) <input type="text" id="rgoNota" maxlength="1000"></label>
    <div class="swr-riga"><button class="primario" id="rgoOk">Carica</button><button type="button" id="rgoAnnulla">Annulla</button></div>
    <div class="barra" id="rgoBarra" hidden><div></div></div><div class="swr-stato" id="rgoMsg" aria-live="polite"></div></form>`;
  $('rgoAnnulla').onclick = () => { aperto = false; box.innerHTML = ''; };
  $('rgOnlineForm').onsubmit = async ev => {
    ev.preventDefault();
    occupato = true; $('rgoOk').disabled = true;
    try {
      const r = await caricaSessione(SD.bytes, {
        titolo: $('rgoTit').value.trim(), data: $('rgoData').value, nota: $('rgoNota').value.trim(), utente,
        prog: (f, t, msg) => { $('rgoBarra').hidden = false; $('rgoBarra').firstElementChild.style.width = (100 * f / t) + '%'; $('rgoMsg').textContent = msg; }
      });
      box.innerHTML = '<div class="swr-stato ok">Registrazione caricata online. <a href="/area/#sessioni/' + esc(r.id) + '" target="_blank" rel="noopener">Apri la sessione «' + esc(r.titolo) + '» nell\'area riservata</a>.</div>';
      aperto = false;
    } catch (e) {
      console.error(e);
      $('rgoMsg').className = 'swr-stato err'; $('rgoMsg').textContent = e.message || e.code; $('rgoOk').disabled = false;
    }
    occupato = false;
  };
}
