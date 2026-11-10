// Prova del formato .swr 2 con dati INVENTATI generati in memoria (nessun file reale). Uso: node tools/test_swr2.mjs
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
const SWR = createRequire(import.meta.url)('./swr.js');
const P = 256, NB = 512;

function pagina(tipo, param, num, millis, mv, flag, seg, corpo) {
  const p = new Uint8Array(P).fill(0xFF), dv = new DataView(p.buffer);
  p[0] = tipo; p[1] = param; dv.setUint16(2, num, true); dv.setUint32(4, millis, true); dv.setUint16(8, mv, true);
  dv.setInt8(10, 25); p[11] = flag; dv.setUint16(12, seg, true);
  corpo(p, dv);
  dv.setUint16(14, SWR.crcPagina(p), true);
  return p;
}
const segmento = (num, seg) => pagina(0xA5, 0, num, 1000, 4000, 0, seg, (p, dv) => {
  dv.setUint16(16, 2083, true); dv.setUint16(18, 488, true); dv.setUint16(20, 35, true);
  p.fill(0, 22, 40); p[30] = 0x30;
});
const dati = (num, seg, millis, base, n) => pagina(0xD1, n, num, millis, 4000, 0, seg, (p, dv) => {
  let pos = 16;
  for (let i = 0; i < 6; i++) dv.setInt16(pos + 2 * i, base + i, true);
  pos += 12;
  for (let k = 1; k < n; k++) { for (let i = 0; i < 6; i++) dv.setInt8(pos + i, 1); pos += 6; }
});
const chiusura = (num, seg, camp, pag) => pagina(0xE0, 1, num, 9000, 3900, 0, seg, (p, dv) => { dv.setUint32(16, camp, true); dv.setUint32(20, pag, true); });
function intestazione(base, seq, confermato) {
  const p = new Uint8Array(P).fill(0xFF), dv = new DataView(p.buffer);
  p[0] = 0xB1; p[1] = 3; dv.setUint16(2, base, true); dv.setUint32(4, 1000 * seq, true); dv.setUint16(8, 4000, true);
  p[10] = 25; p[11] = 0; dv.setUint16(12, 0, true);
  p[16] = 0xFF; dv.setUint32(17, seq, true); dv.setUint32(21, 0x1234ABCD, true);
  dv.setUint16(14, SWR.crcBlocco(p), true);
  if (confermato) p.fill(0x00, 252, 256); // parola di conferma (formato 3) fuori dal CRC
  return p;
}

// Anello da 512 blocchi: i seq 10..12 stanno nei blocchi fisici 510, 511, 0 (giro), cosi' l'ordine fisico != ordine logico.
const img = new Uint8Array(NB * 16 * P).fill(0xFF);
const metti = (blocco, k, pag) => img.set(pag, (blocco * 16 + k) * P);
const blocchi = [[510, 10, true], [511, 11, false], [0, 12, false]];
for (const [b, seq, conf] of blocchi) metti(b, 0, intestazione(b * 16, seq, conf));
// seq 10: segmento 0 + 14 pagine dati (la 15 resta vuota); seq 11: 15 pagine dati; seq 12: 2 pagine dati + chiusura, resto vuoto
metti(510, 1, segmento(510 * 16 + 1, 0));
for (let k = 2; k < 15; k++) metti(510, k, dati(510 * 16 + k, 0, 2000 + 480 * (k - 2), 100, 25));
for (let k = 1; k < 16; k++) metti(511, k, dati(511 * 16 + k, 0, 2000 + 480 * (13 + k - 1), 100, 25));
metti(0, 1, dati(1, 0, 2000 + 480 * 28, 100, 25));
metti(0, 2, dati(2, 0, 2000 + 480 * 29, 100, 25));
metti(0, 3, chiusura(3, 0, 30 * 25, 30));

let es = SWR.decodifica(img);
assert.equal(es.formato, 2);
assert.deepEqual(es.problemi, []);
assert.equal(es.blocchi.validi, 3);
assert.equal(es.blocchi.confermati, 1);
assert.equal(es.blocchi.liberi, NB - 3);
assert.deepEqual(es.listaBlocchi.map(b => b.seq), [10, 11, 12]);
assert.equal(es.segmenti[0].chiuso, true);
assert.equal(es.pagineDati.length, 13 + 15 + 2);
const s = SWR.serie(es, 0);
assert.equal(s.n, 30 * 25);
for (let i = 1; i < s.n; i++) assert.ok(s.t[i] > s.t[i - 1], 'tempo crescente attraverso il giro dell\'anello');
assert.equal(s.pagina[0], 510 * 16 + 2);
assert.equal(s.pagina[s.n - 1], 2);
console.log('formato 2: ordinamento per seq, conferma, pagine vuote, giro dell\'anello: OK');

// Un intestazione corrotta scarta il blocco; il CRC non dipende dal byte di conferma
const rotto = img.slice(); rotto[(511 * 16) * P + 5] ^= 0xFF;
es = SWR.decodifica(rotto);
assert.equal(es.blocchi.validi, 2);
assert.ok(es.problemi.some(x => x.includes('blocco 511')));
const h = intestazione(0, 5, false), h2 = h.slice(); h2.fill(0x00, 252, 256);
assert.equal(h2[17], 5); // la conferma non tocca il seq
assert.equal(SWR.crcBlocco(h), SWR.crcBlocco(h2));
console.log('formato 2: intestazione corrotta scartata, CRC indipendente dalla conferma: OK');

// Formato 1 invariato (riconoscimento automatico)
const f1 = new Uint8Array(40 * P).fill(0xFF);
f1.set(segmento(0, 0), 0);
for (let k = 1; k < 5; k++) f1.set(dati(k, 0, 2000 + 480 * k, 100, 25), k * P);
f1.set(chiusura(5, 0, 100, 4), 5 * P);
es = SWR.decodifica(f1);
assert.equal(es.formato, 1);
assert.deepEqual(es.problemi, []);
assert.equal(es.pagineUsate, 6);
assert.equal(SWR.serie(es, 0).n, 100);
console.log('formato 1: invariato: OK');
