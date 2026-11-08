// Test delle regole Firestore con l'emulatore. Solo dati inventati.
// L'UID admin delle regole e' quello reale: i test lo sostituiscono con un UID di prova prima di caricarle nell'emulatore.
import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { initializeTestEnvironment, assertFails, assertSucceeds } from '@firebase/rules-unit-testing';
import { doc, getDoc, getDocs, setDoc, updateDoc, deleteDoc, collection, serverTimestamp, Bytes } from 'firebase/firestore';

const ADMIN = 'uid-admin-prova';
const regole = fs.readFileSync(new URL('../firestore.rules', import.meta.url), 'utf8').replace(/(request\.auth\.uid == ')[^']+(')/, `$1${ADMIN}$2`);
let env;
const ctx = uid => env.authenticatedContext(uid).firestore();
const anon = () => env.unauthenticatedContext().firestore();

before(async () => { env = await initializeTestEnvironment({ projectId: 'demo-swimtimer', firestore: { rules: regole, host: '127.0.0.1', port: 8080 } }); });
after(async () => { await env.cleanup(); });
beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async c => {
    const d = c.firestore();
    const u = (uid, stato) => setDoc(doc(d, 'users', uid), { nome: 'Utente ' + uid, email: uid + '@esempio.test', stato, creato: new Date() });
    await u('ana', 'approvato'); await u('bruno', 'approvato'); await u('carla', 'in_attesa'); await u('dino', 'rifiutato'); await u('elia', 'revocato');
    await setDoc(doc(d, 'sessioni', 's1'), { titolo: 'Prova', data: '2026-01-01', caricatoDa: { uid: 'ana', nome: 'Ana' }, caricatoIl: new Date(), sha256: 'a'.repeat(64), byte: 1000, nChunk: 1, completa: true });
    await setDoc(doc(d, 'sessioni', 's1', 'chunk', '0'), { n: 0, data: Bytes.fromUint8Array(new Uint8Array(10)) });
    await setDoc(doc(d, 'video', 'v1'), { sessioneId: 's1', link: 'https://drive.google.com/file/d/xyz', nome: 'a.mp4', sha256: 'b'.repeat(64), byte: 5, fps: 30, durata_s: 10, caricatoDa: { uid: 'ana', nome: 'Ana' }, caricatoIl: new Date() });
    await setDoc(doc(d, 'annotazioni', 'n1'), { sessioneId: 's1', videoId: 'v1', autore: { uid: 'ana', nome: 'Ana' }, eventi: [], offset_s: null, sync: null, anticipo_ms: 0, creato: new Date(), aggiornato: new Date() });
  });
});

const nuovoUtente = (extra = {}) => ({ nome: 'Nuovo', email: 'nuovo@esempio.test', stato: 'in_attesa', creato: serverTimestamp(), ...extra });

test('anonimo: non legge nulla di privato e non scrive', async () => {
  const d = anon();
  await assertFails(getDoc(doc(d, 'users', 'ana')));
  await assertFails(getDocs(collection(d, 'sessioni')));
  await assertFails(getDoc(doc(d, 'sessioni', 's1')));
  await assertFails(getDoc(doc(d, 'sessioni', 's1', 'chunk', '0')));
  await assertFails(getDocs(collection(d, 'video')));
  await assertFails(getDocs(collection(d, 'annotazioni')));
  await assertFails(setDoc(doc(d, 'users', 'x'), nuovoUtente()));
});

test('utente in attesa / rifiutato / revocato: non legge sessioni, video, annotazioni, chunk', async () => {
  for (const uid of ['carla', 'dino', 'elia']) {
    const d = ctx(uid);
    await assertFails(getDocs(collection(d, 'sessioni')));
    await assertFails(getDoc(doc(d, 'sessioni', 's1', 'chunk', '0')));
    await assertFails(getDocs(collection(d, 'video')));
    await assertFails(getDocs(collection(d, 'annotazioni')));
    await assertSucceeds(getDoc(doc(d, 'users', uid)));       // legge solo il proprio profilo
  }
});

test('utente approvato: legge tutto il materiale condiviso, non gli altri profili ne\' l\'elenco utenti', async () => {
  const d = ctx('bruno');
  await assertSucceeds(getDocs(collection(d, 'sessioni')));
  await assertSucceeds(getDoc(doc(d, 'sessioni', 's1', 'chunk', '0')));
  await assertSucceeds(getDocs(collection(d, 'video')));
  await assertSucceeds(getDocs(collection(d, 'annotazioni')));
  await assertFails(getDoc(doc(d, 'users', 'ana')));
  await assertFails(getDocs(collection(d, 'users')));
});

test('registrazione: crea solo il proprio documento e sempre in_attesa', async () => {
  const d = ctx('nuovo');
  await assertSucceeds(setDoc(doc(d, 'users', 'nuovo'), nuovoUtente()));
  await env.clearFirestore();
  await assertFails(setDoc(doc(d, 'users', 'nuovo'), nuovoUtente({ stato: 'approvato' })));
  await assertFails(setDoc(doc(d, 'users', 'altro'), nuovoUtente()));
  await assertFails(setDoc(doc(d, 'users', 'nuovo'), nuovoUtente({ ruolo: 'admin' })));
  await assertFails(setDoc(doc(d, 'users', 'nuovo'), nuovoUtente({ creato: new Date(0) })));
});

test('un utente non puo\' auto-approvarsi ne\' cambiare lo stato', async () => {
  const c = ctx('carla');
  await assertFails(updateDoc(doc(c, 'users', 'carla'), { stato: 'approvato' }));
  await assertFails(updateDoc(doc(c, 'users', 'carla'), { stato: 'approvato', nome: 'X' }));
  await assertFails(setDoc(doc(c, 'users', 'carla'), nuovoUtente({ stato: 'approvato' })));   // set su doc esistente = update
  await assertFails(deleteDoc(doc(c, 'users', 'carla')));
  await assertFails(updateDoc(doc(ctx('dino'), 'users', 'dino'), { stato: 'approvato' }));
  await assertFails(updateDoc(doc(ctx('bruno'), 'users', 'carla'), { stato: 'approvato' }));  // un approvato non approva altri
  await assertSucceeds(updateDoc(doc(c, 'users', 'carla'), { nome: 'Carla Rossi' }));         // nome/foto si'
});

test('amministratore: elenca utenti e cambia stato; gli altri campi no', async () => {
  const a = ctx(ADMIN);
  await assertSucceeds(getDocs(collection(a, 'users')));
  await assertSucceeds(updateDoc(doc(a, 'users', 'carla'), { stato: 'approvato', deciso: serverTimestamp(), decisoDa: ADMIN }));
  await assertSucceeds(updateDoc(doc(a, 'users', 'bruno'), { stato: 'revocato' }));
  await assertFails(updateDoc(doc(a, 'users', 'carla'), { stato: 'superuser' }));
  await assertFails(updateDoc(doc(a, 'users', 'carla'), { email: 'x@y.test' }));
  await assertSucceeds(getDocs(collection(a, 'sessioni')));     // l'admin legge anche senza essere 'approvato' nel documento
});

test('dopo la revoca l\'accesso ai dati cade subito', async () => {
  await assertSucceeds(getDocs(collection(ctx('bruno'), 'sessioni')));
  await assertSucceeds(updateDoc(doc(ctx(ADMIN), 'users', 'bruno'), { stato: 'revocato' }));
  await assertFails(getDocs(collection(ctx('bruno'), 'sessioni')));
});

const nuovaSessione = (uid, extra = {}) => ({ titolo: 'Nuova', data: '2026-02-02', caricatoDa: { uid, nome: uid }, caricatoIl: serverTimestamp(), sha256: 'c'.repeat(64), byte: 2000, nChunk: 1, completa: false, ...extra });

test('sessioni: creazione con autore e timestamp corretti, upload a chunk, completamento', async () => {
  const d = ctx('bruno');
  await assertSucceeds(setDoc(doc(d, 'sessioni', 's2'), nuovaSessione('bruno')));
  await assertSucceeds(setDoc(doc(d, 'sessioni', 's2', 'chunk', '0'), { n: 0, data: Bytes.fromUint8Array(new Uint8Array(800 * 1024)) }));
  await assertSucceeds(updateDoc(doc(d, 'sessioni', 's2'), { completa: true }));
  // dopo il completamento i chunk non si aggiungono piu'
  await assertFails(setDoc(doc(d, 'sessioni', 's2', 'chunk', '1'), { n: 1, data: Bytes.fromUint8Array(new Uint8Array(10)) }));
  // non si torna indietro
  await assertFails(updateDoc(doc(d, 'sessioni', 's2'), { completa: false }));
});

test('sessioni: validazioni (autore falso, timestamp falso, campi extra, dimensioni)', async () => {
  const d = ctx('bruno');
  await assertFails(setDoc(doc(d, 'sessioni', 'x1'), nuovaSessione('ana')));                       // autore diverso
  await assertFails(setDoc(doc(d, 'sessioni', 'x2'), nuovaSessione('bruno', { caricatoIl: new Date(0) })));
  await assertFails(setDoc(doc(d, 'sessioni', 'x3'), nuovaSessione('bruno', { extra: 1 })));
  await assertFails(setDoc(doc(d, 'sessioni', 'x4'), nuovaSessione('bruno', { sha256: 'corto' })));
  await assertFails(setDoc(doc(d, 'sessioni', 'x5'), nuovaSessione('bruno', { byte: 10 * 1024 * 1024 })));
  await assertFails(setDoc(doc(d, 'sessioni', 'x6'), nuovaSessione('bruno', { titolo: '' })));
  await assertFails(setDoc(doc(d, 'sessioni', 'x7'), nuovaSessione('bruno', { completa: true })));
  await assertFails(setDoc(doc(ctx('carla'), 'sessioni', 'x8'), nuovaSessione('carla')));          // in attesa
  await setDoc(doc(d, 'sessioni', 's3'), nuovaSessione('bruno'));
  await assertFails(setDoc(doc(d, 'sessioni', 's3', 'chunk', '0'), { n: 0, data: Bytes.fromUint8Array(new Uint8Array(950000)) })); // oltre 900000
  await assertFails(setDoc(doc(d, 'sessioni', 's3', 'chunk', '0'), { n: 1, data: Bytes.fromUint8Array(new Uint8Array(10)) }));      // n incoerente col percorso
  await assertFails(setDoc(doc(ctx('ana'), 'sessioni', 's3', 'chunk', '0'), { n: 0, data: Bytes.fromUint8Array(new Uint8Array(10)) })); // chunk su sessione altrui
});

test('sessioni: solo il proprietario (o l\'admin) modifica ed elimina; campi immutabili', async () => {
  await assertSucceeds(updateDoc(doc(ctx('ana'), 'sessioni', 's1'), { titolo: 'Rinominata' }));
  await assertFails(updateDoc(doc(ctx('bruno'), 'sessioni', 's1'), { titolo: 'Hack' }));
  await assertFails(updateDoc(doc(ctx('ana'), 'sessioni', 's1'), { sha256: 'd'.repeat(64) }));
  await assertFails(updateDoc(doc(ctx('ana'), 'sessioni', 's1'), { caricatoDa: { uid: 'bruno', nome: 'x' } }));
  await assertFails(deleteDoc(doc(ctx('bruno'), 'sessioni', 's1', 'chunk', '0')));
  await assertFails(deleteDoc(doc(ctx('bruno'), 'sessioni', 's1')));
  await assertSucceeds(deleteDoc(doc(ctx('ana'), 'sessioni', 's1', 'chunk', '0')));
  await assertSucceeds(deleteDoc(doc(ctx('ana'), 'sessioni', 's1')));
});

test('sessioni: l\'admin puo\' eliminare quelle altrui', async () => {
  await assertSucceeds(deleteDoc(doc(ctx(ADMIN), 'sessioni', 's1', 'chunk', '0')));
  await assertSucceeds(deleteDoc(doc(ctx(ADMIN), 'sessioni', 's1')));
});

const nuovoVideo = (uid, extra = {}) => ({ sessioneId: 's1', link: 'https://youtu.be/abc', nome: 'p.mp4', sha256: 'e'.repeat(64), byte: 100, fps: 30, durata_s: 60.5, caricatoDa: { uid, nome: uid }, caricatoIl: serverTimestamp(), ...extra });

test('video: solo riferimenti validi; link solo Drive/YouTube; modifiche e cancellazioni del proprietario', async () => {
  const d = ctx('bruno');
  await assertSucceeds(setDoc(doc(d, 'video', 'v2'), nuovoVideo('bruno')));
  await assertFails(setDoc(doc(d, 'video', 'v3'), nuovoVideo('bruno', { link: 'https://sito-losco.example/x' })));
  await assertFails(setDoc(doc(d, 'video', 'v4'), nuovoVideo('bruno', { link: 'http://drive.google.com/x' })));
  await assertFails(setDoc(doc(d, 'video', 'v5'), nuovoVideo('bruno', { sessioneId: 'inesistente' })));
  await assertFails(setDoc(doc(d, 'video', 'v6'), nuovoVideo('ana')));
  await assertFails(setDoc(doc(d, 'video', 'v7'), nuovoVideo('bruno', { fps: 0 })));
  await assertSucceeds(updateDoc(doc(d, 'video', 'v2'), { link: 'https://drive.google.com/file/d/nuovo' }));
  await assertFails(updateDoc(doc(d, 'video', 'v2'), { sha256: 'f'.repeat(64) }));
  await assertFails(updateDoc(doc(ctx('ana'), 'video', 'v2'), { nome: 'x.mp4' }));
  await assertFails(deleteDoc(doc(ctx('ana'), 'video', 'v2')));
  await assertSucceeds(deleteDoc(doc(d, 'video', 'v2')));
});

const nuovaAnn = (uid, extra = {}) => ({ sessioneId: 's1', videoId: 'v1', autore: { uid, nome: uid }, eventi: [{ tipo: 'B', t_video_s: 1.5, nota: '' }], offset_s: 0.123, sync: { video_s: 1, dati_s: 1.123 }, anticipo_ms: 0, creato: serverTimestamp(), aggiornato: serverTimestamp(), ...extra });

test('annotazioni: l\'autore e\' request.auth.uid, solo l\'autore modifica, gli altri leggono e duplicano', async () => {
  const b = ctx('bruno');
  await assertSucceeds(setDoc(doc(b, 'annotazioni', 'n2'), nuovaAnn('bruno')));                // nuova o "duplica come mia"
  await assertFails(setDoc(doc(b, 'annotazioni', 'n3'), nuovaAnn('ana')));                      // firma altrui
  await assertFails(setDoc(doc(b, 'annotazioni', 'n4'), nuovaAnn('bruno', { creato: new Date(0) })));
  await assertFails(setDoc(doc(b, 'annotazioni', 'n5'), nuovaAnn('bruno', { anticipo_ms: 99999 })));
  await assertFails(setDoc(doc(b, 'annotazioni', 'n6'), nuovaAnn('bruno', { eventi: 'non una lista' })));
  await assertFails(setDoc(doc(ctx('carla'), 'annotazioni', 'n7'), nuovaAnn('carla')));
  await assertSucceeds(updateDoc(doc(b, 'annotazioni', 'n2'), { eventi: [], aggiornato: serverTimestamp() }));
  await assertFails(updateDoc(doc(b, 'annotazioni', 'n2'), { eventi: [], aggiornato: new Date(0) }));
  await assertFails(updateDoc(doc(b, 'annotazioni', 'n2'), { autore: { uid: 'ana', nome: 'x' }, aggiornato: serverTimestamp() }));
  await assertFails(updateDoc(doc(b, 'annotazioni', 'n2'), { videoId: 'altro', aggiornato: serverTimestamp() }));
  await assertFails(updateDoc(doc(b, 'annotazioni', 'n1'), { eventi: [], aggiornato: serverTimestamp() })); // di Ana
  await assertFails(updateDoc(doc(ctx(ADMIN), 'annotazioni', 'n1'), { eventi: [], aggiornato: serverTimestamp() })); // nemmeno l'admin modifica
  await assertFails(deleteDoc(doc(b, 'annotazioni', 'n1')));
  await assertSucceeds(deleteDoc(doc(ctx(ADMIN), 'annotazioni', 'n1')));                       // l'admin elimina
  await assertSucceeds(deleteDoc(doc(b, 'annotazioni', 'n2')));
});

test('collezioni non previste: nessun accesso', async () => {
  await assertFails(setDoc(doc(ctx('ana'), 'altro', 'x'), { a: 1 }));
  await assertFails(getDoc(doc(ctx(ADMIN), 'altro', 'x')));
});
