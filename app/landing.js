/* SwimTimer - pagina pubblica: pulsante «Accedi con Google» e grafici DIMOSTRATIVI.
 * I dati dei grafici sono inventati qui (generatore pseudo-casuale con seme fisso): nessuna registrazione reale. */
import { osserva, accedi } from './comune/fb.js';

// ---------------------------------------------------------------- accesso
const msg = document.getElementById('msgAccesso');
let dentro = false;
document.querySelectorAll('[data-accedi]').forEach(b => b.addEventListener('click', async () => {
  if (dentro) { location.href = 'area/'; return; }
  try { await accedi(); location.href = 'area/'; }
  catch (e) { msg.textContent = 'Accesso non riuscito (' + (e.code || e.message) + '). Riprova.'; msg.classList.add('err'); }
}));
osserva(u => {
  dentro = !!u;
  document.querySelectorAll('[data-accedi]').forEach(b => { b.textContent = u ? 'Vai all\'area riservata' : 'Accedi con Google'; });
});

// ---------------------------------------------------------------- dati dimostrativi (inventati)
function rng(seme) { let s = seme >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const R = rng(20261108), N = 700, FS = 50, T = N / FS;      // 14 s a 50 Hz
const gauss = (x, c, w) => Math.exp(-(((x - c) / w) ** 2));
const t = Array.from({ length: N }, (_, i) => i / FS);
// bracciata ~0,9 Hz; virata: avvicinamento ~6,2 s, capriola ~6,4-7,1 s, spinta sul muro ~7,2 s, planata, ripresa ~8,8 s
const acc = t.map(x => {
  const nuoto = (x < 6.3 || x > 8.8) ? 0.34 * Math.sin(2 * Math.PI * 0.9 * x) + 0.12 * Math.sin(2 * Math.PI * 1.8 * x + 1) : 0.03;
  const urto = 2.2 * gauss(x, 7.2, 0.07) + 0.9 * gauss(x, 6.35, 0.12);
  const rumore = (R() - 0.5) * 0.08;
  return Math.max(0.05, 1 + nuoto + urto + rumore);
});
const gir = t.map(x => {
  const nuoto = (x < 6.3 || x > 8.8) ? 60 * Math.abs(Math.sin(2 * Math.PI * 0.9 * x + 0.6)) : 8;
  const capriola = 620 * gauss(x, 6.75, 0.28);
  return Math.max(0, nuoto + capriola + (R() - 0.5) * 18);
});
const tempi = [38.9, 41.2, 41.8, 42.3, 42.9, 43.6, 43.1, 42.4];      // tempi per vasca inventati (s, 25 m)

// ---------------------------------------------------------------- disegno SVG
const W = 560, H = 230, M = { l: 40, r: 10, t: 12, b: 26 };
const NS = 'http://www.w3.org/2000/svg';
const scala = (a0, a1, b0, b1) => v => b0 + (v - a0) / (a1 - a0) * (b1 - b0);
function svg(contenuto) { return `<svg viewBox="0 0 ${W} ${H}" xmlns="${NS}" aria-hidden="true">${contenuto}</svg>`; }
function assi(x, y, yTicks, xTicks, unita) {
  let s = '';
  for (const v of yTicks) s += `<line x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}" style="stroke:var(--griglia)"/><text x="${M.l - 6}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`;
  for (const v of xTicks) s += `<text x="${x(v)}" y="${H - 8}" text-anchor="middle">${v}</text>`;
  return s + `<text x="${M.l + 2}" y="${M.t - 2}" >${unita}</text><text x="${W - M.r}" y="${H - 8}" text-anchor="end">s</text>`;
}
function linea(x, y, serie, stile) {
  const d = serie.map((v, i) => (i ? 'L' : 'M') + x(t[i]).toFixed(1) + ' ' + y(v).toFixed(1)).join('');
  return `<path d="${d}" fill="none" style="${stile}" stroke-width="1.5" stroke-linejoin="round"/>`;
}
function fascia(x, a, b, etichetta, colore) {
  return `<rect x="${x(a)}" y="${M.t}" width="${x(b) - x(a)}" height="${H - M.t - M.b}" style="fill:${colore};opacity:.12"/><text x="${(x(a) + x(b)) / 2}" y="${M.t + 11}" text-anchor="middle" style="fill:${colore};font-weight:600">${etichetta}</text>`;
}
function grafico(id, serie, ymax, yTicks, unita, stile) {
  const x = scala(0, T, M.l, W - M.r), y = scala(0, ymax, H - M.b, M.t);
  const b = fascia(x, 6.2, 7.2, 'virata', 'var(--attenzione)') + fascia(x, 7.2, 8.8, 'planata', 'var(--accento-2)');
  document.getElementById(id).innerHTML = svg(b + assi(x, y, yTicks, [0, 2, 4, 6, 8, 10, 12, 14], unita) + linea(x, y, serie, stile));
}
grafico('gAcc', acc, 4, [0, 1, 2, 3, 4], 'g', 'stroke:var(--accento)');
grafico('gGir', gir, 800, [0, 200, 400, 600, 800], 'gradi/s', 'stroke:var(--accento-2)');

(function barre() {
  const n = tempi.length, bw = (W - M.l - M.r) / n, y = scala(30, 46, H - M.b, M.t + 6);
  let s = '';
  for (const v of [30, 34, 38, 42, 46]) s += `<line x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}" style="stroke:var(--griglia)"/><text x="${M.l - 6}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`;
  tempi.forEach((v, i) => {
    const x0 = M.l + i * bw + bw * 0.18, w = bw * 0.64, h = y(30) - y(v);
    s += `<rect x="${x0}" y="${y(v)}" width="${w}" height="${h}" rx="4" style="fill:${i === 0 ? 'var(--accento-2)' : 'var(--accento)'}"/>`
      + `<text x="${x0 + w / 2}" y="${y(v) - 5}" text-anchor="middle" style="fill:var(--testo)">${v.toFixed(1)}</text>`
      + `<text x="${x0 + w / 2}" y="${H - 8}" text-anchor="middle">${i + 1}</text>`;
  });
  s += `<text x="${M.l + 2}" y="${M.t - 2}">s</text><text x="${W - M.r}" y="${H - 8}" text-anchor="end">vasca</text>`;
  document.getElementById('gTempi').innerHTML = svg(s);
})();
