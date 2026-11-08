// Prima di ogni deploy dell'hosting scrive app/versione.json con un identificativo unico.
// Le pagine lo confrontano con quello letto all'apertura: se cambia, si ricaricano da sole (vedi app/comune/versione.js).
import { writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
let git = '';
try { git = execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { /* fuori da git */ }
const versione = new Date().toISOString().replace(/[-:]/g, '').slice(0, 15) + (git ? '-' + git : '');
writeFileSync(new URL('../app/versione.json', import.meta.url), JSON.stringify({ versione }) + '\n');
console.log('versione del sito: ' + versione);
