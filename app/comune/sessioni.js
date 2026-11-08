/* SwimTimer - creazione di una sessione online (sessioni/{id} + chunk), condivisa da area/area.js e dalla pagina /strumenti/.
 * Stessi campi e stesse regole di docs/MODELLO-DATI.md (sezione sessioni). Usa window.SWR (swr.js) e window.t (comune/i18n.js). */
import { db, collection, doc, getDocs, setDoc, updateDoc, deleteDoc, query, where, limit, serverTimestamp, Bytes } from './fb.js';
import { sha256Bytes } from './sha256.js';

export const CHUNK = 800 * 1024;                 // <= 900000 consentiti dalle regole (limite documento 1 MiB)
export const MAX_SWR = 4 * 1024 * 1024;
export const fmtByte = n => n >= 1048576 ? (n / 1048576).toFixed(1) + ' MiB' : (n / 1024).toFixed(0) + ' KiB';
const t = (...a) => window.t(...a);

/** Verifica il formato .swr e che ci siano campioni; restituisce la decodifica. Lancia Error con messaggio nella lingua corrente. */
export function controllaSwr(bytes) {
  if (bytes.length > MAX_SWR) throw new Error(t('s.troppoGrande', { max: fmtByte(MAX_SWR) }));
  let es;
  try { es = window.SWR.decodifica(bytes); } catch (e) { throw new Error(t('s.nonValido', { e: e.message })); }
  if (!window.SWR.segmentiConDati(es).length) throw new Error(t('s.senzaCampioni'));
  return es;
}

/** Sessione gia' presente con lo stesso sha256 (una sola lettura), oppure null. */
export async function sessioneConImpronta(sha) {
  const sn = await getDocs(query(collection(db(), 'sessioni'), where('sha256', '==', sha), limit(1)));
  return sn.empty ? null : { id: sn.docs[0].id, ...sn.docs[0].data() };
}

/** Carica i byte di una registrazione: crea la sessione (completa=false), scrive i chunk, poi imposta completa=true.
 *  utente = utente Firebase; prog(fatti, totale, messaggio). Restituisce {id, titolo}. */
export async function caricaSessione(bytes, { titolo, data, nota, utente, prog = () => {} }) {
  prog(0, 1, t('s.controllo'));
  controllaSwr(bytes);
  const sha = await sha256Bytes(bytes);
  const dup = await sessioneConImpronta(sha);
  if (dup) throw new Error(t('s.dup', { titolo: dup.titolo, nome: dup.caricatoDa.nome }));
  const n = Math.ceil(bytes.length / CHUNK);
  const ref = doc(collection(db(), 'sessioni'));
  const dati = { titolo, data, caricatoDa: { uid: utente.uid, nome: (utente.displayName || utente.email || 'Utente').slice(0, 100) }, caricatoIl: serverTimestamp(), sha256: sha, byte: bytes.length, nChunk: n, completa: false };
  if (nota) dati.nota = nota;
  await setDoc(ref, dati);
  try {
    for (let i = 0; i < n; i++) {
      prog(i, n, t('s.pezzo', { i: i + 1, n }));
      await setDoc(doc(ref, 'chunk', String(i)), { n: i, data: Bytes.fromUint8Array(bytes.slice(i * CHUNK, (i + 1) * CHUNK)) });
    }
    await updateDoc(ref, { completa: true });
  } catch (e) {                                  // caricamento interrotto: ripulisce quel che c'e'
    for (let i = 0; i < n; i++) { try { await deleteDoc(doc(ref, 'chunk', String(i))); } catch (x) { /* ignora */ } }
    try { await deleteDoc(ref); } catch (x) { /* ignora */ }
    throw e;
  }
  prog(n, n, t('s.fatto'));
  return { id: ref.id, titolo };
}
