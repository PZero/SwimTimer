// Prima di ogni deploy copia le pagine locali di tools/ dentro il sito (cartelle ignorate da git: app/strumenti/, app/display/),
// cosi' il codice non si duplica a mano:
//   tools/index.html + registrazione.js + annotazione.js/css + swr.js  -> app/strumenti/
//   firmware/xiao-stream/release/xiao.bin + xiao.json                  -> app/strumenti/firmware/   (la pagina li cerca in firmware/xiao.json)
//   tools/display.html                                                 -> app/display/index.html
import { cpSync, mkdirSync, rmSync, existsSync } from 'node:fs';
const radice = new URL('../', import.meta.url);
const p = rel => new URL(rel, radice);
for (const d of ['app/strumenti', 'app/display']) rmSync(p(d), { recursive: true, force: true });
mkdirSync(p('app/strumenti/firmware'), { recursive: true });
mkdirSync(p('app/display'), { recursive: true });
for (const f of ['index.html', 'registrazione.js', 'annotazione.js', 'annotazione.css', 'swr.js']) cpSync(p('tools/' + f), p('app/strumenti/' + f));
for (const f of ['xiao.bin', 'xiao.json']) {
  if (!existsSync(p('firmware/xiao-stream/release/' + f))) throw new Error('manca firmware/xiao-stream/release/' + f);
  cpSync(p('firmware/xiao-stream/release/' + f), p('app/strumenti/firmware/' + f));
}
cpSync(p('tools/display.html'), p('app/display/index.html'));
console.log('copiati in app/: strumenti/ (con firmware/) e display/');
