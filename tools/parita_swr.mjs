// Controllo di parita' swr.js / swr.py su un .swr qualsiasi (anche una registrazione vera: resta fuori dal repository).
// Decodifica il file con swr.js (qui) e con swr.py (python, via firmware/xiao-stream/scarica.py converti),
// poi confronta i due CSV riga per riga. Esce con codice 0 se identici, 1 se differiscono, 2 per errori d'uso.
//
//   node tools/parita_swr.mjs registrazioni/20261108_101500.swr [--grezzo] [--python python3]
//
// Servono node (>= 14) e Python 3. Non serve pyserial. I CSV temporanei vanno nella cartella temporanea del sistema.
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';

const qui = dirname(fileURLToPath(import.meta.url));
const SWR = createRequire(import.meta.url)('./swr.js');
const args = process.argv.slice(2);
const grezzo = args.includes('--grezzo');
const ip = args.indexOf('--python');
const python = ip >= 0 ? args[ip + 1] : (process.platform === 'win32' ? 'python' : 'python3');
const file = args.find((a, i) => !a.startsWith('--') && args[i - 1] !== '--python');
if (!file) { console.error('uso: node tools/parita_swr.mjs file.swr [--grezzo] [--python comando]'); process.exit(2); }

const tmp = mkdtempSync(join(tmpdir(), 'parita_swr_'));
try {
  const es = SWR.decodifica(new Uint8Array(readFileSync(file)));
  const js = SWR.scriviCsv(es, grezzo).replace(/\r\n/g, '\n');

  const csvPy = join(tmp, 'py.csv');
  const cartellaPy = resolve(qui, '..', 'firmware', 'xiao-stream');
  const r = spawnSync(python, ['-I', '-c',
    'import sys; sys.path.insert(0, sys.argv[1]); import swr; ' +
    'es = swr.decodifica(open(sys.argv[2], "rb").read()); ' +
    'n = swr.scrivi_csv(es, sys.argv[3], sys.argv[4] == "1"); print(swr.riassunto(es)); print("righe python:", n)',
    cartellaPy, resolve(file), csvPy, grezzo ? '1' : '0'], { encoding: 'utf8' });
  if (r.status !== 0) { console.error('swr.py non eseguito:\n' + (r.stderr || r.error)); process.exit(2); }
  const py = readFileSync(csvPy, 'utf8').replace(/\r\n/g, '\n');

  console.log(r.stdout.trim());
  const a = py.split('\n'), b = js.split('\n');
  console.log('righe swr.js: ' + (b.length - 2));
  if (js === py) { console.log('PARITA OK: CSV identici (' + (b.length - 2) + ' campioni)'); process.exit(0); }
  let diffs = 0;
  for (let i = 0; i < Math.max(a.length, b.length) && diffs < 5; i++) {
    if (a[i] !== b[i]) { diffs++; console.error('riga ' + (i + 1) + '\n  swr.py: ' + a[i] + '\n  swr.js: ' + b[i]); }
  }
  console.error('PARITA FALLITA');
  process.exit(1);
} finally { rmSync(tmp, { recursive: true, force: true }); }
