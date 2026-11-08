/* SwimTimer - inizializzazione Firebase (SDK modulare da CDN gstatic, versione fissa).
 * La configurazione web di Firebase (apiKey ecc.) NON e' un segreto: identifica il progetto; la sicurezza e' nelle regole
 * Firestore (firebase/firestore.rules). Nessun service account, token o .env nel repository. */
import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js';
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithRedirect, onAuthStateChanged, signOut }
  from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js';
import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager, doc, getDoc, setDoc, serverTimestamp }
  from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';

// riesporta tutte le funzioni Firestore (stessa versione dell'SDK) cosi' le pagine importano da un solo punto
export * from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';

export const configFirebase = {
  apiKey: 'AIzaSyAhssbBPJxJkf2D6E52YJCaMeOWC_zzzc4',
  authDomain: 'swimtimer-pzero.firebaseapp.com',
  projectId: 'swimtimer-pzero',
  appId: '1:450232758651:web:17fc9b4da04e3eb0234dde',
  messagingSenderId: '450232758651'
};

export const app = initializeApp(configFirebase);
export const auth = getAuth(app);
auth.languageCode = 'it';

let _db = null;
/** Firestore con cache persistente (IndexedDB): le letture ripetute (soprattutto i chunk, immutabili) non contano come letture. */
export function db() {
  if (!_db) {
    try { _db = initializeFirestore(app, { localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }) }); }
    catch (e) { _db = initializeFirestore(app, {}); }
  }
  return _db;
}

export function osserva(cb) { return onAuthStateChanged(auth, cb); }
export function esci() { return signOut(auth); }

/** Accesso con Google (popup; se il browser lo blocca, redirect). */
export async function accedi() {
  const p = new GoogleAuthProvider();
  p.setCustomParameters({ prompt: 'select_account' });
  try { return await signInWithPopup(auth, p); }
  catch (e) {
    if (e && (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment')) return signInWithRedirect(auth, p);
    throw e;
  }
}

/** Legge users/{uid}; al primo accesso lo crea con stato 'in_attesa'. Restituisce i dati del documento. */
export async function assicuraUtente(user) {
  const d = db(), rif = doc(d, 'users', user.uid);
  const snap = await getDoc(rif);
  const nome = (user.displayName || user.email || 'Utente').slice(0, 100);
  const email = (user.email || '').slice(0, 200);
  if (!snap.exists()) {
    const nuovo = { nome, email, stato: 'in_attesa', creato: serverTimestamp() };
    if (user.photoURL) nuovo.foto = user.photoURL.slice(0, 500);
    await setDoc(rif, nuovo);
    const s2 = await getDoc(rif);
    return s2.data();
  }
  const dati = snap.data();
  // aggiorna nome/foto se cambiati su Google (non puo' mai toccare lo stato: lo vietano le regole)
  const upd = {};
  if (dati.nome !== nome) upd.nome = nome;
  if (user.photoURL && dati.foto !== user.photoURL.slice(0, 500)) upd.foto = user.photoURL.slice(0, 500);
  if (Object.keys(upd).length) { try { await setDoc(rif, upd, { merge: true }); Object.assign(dati, upd); } catch (e) { /* non critico */ } }
  return dati;
}
