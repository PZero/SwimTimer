/* SwimTimer - SHA-256 incrementale in JavaScript puro.
 * SubtleCrypto non offre l'hash a blocchi: per i video (centinaia di MB) si legge il file a fette da 4 MiB e si aggiorna
 * lo stato, cosi' la memoria resta bassa e si puo' mostrare l'avanzamento. Per file piccoli (.swr) si usa SubtleCrypto. */
const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]);

export class Sha256 {
  constructor() {
    this.h = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
    this.buf = new Uint8Array(64); this.nbuf = 0; this.len = 0; this.w = new Uint32Array(64);
  }
  _blocco(b, o) {
    const w = this.w, h = this.h;
    for (let i = 0; i < 16; i++, o += 4) w[i] = (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3];
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15], c = w[i - 2];
      const s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
      const s1 = ((c >>> 17) | (c << 15)) ^ ((c >>> 19) | (c << 13)) ^ (c >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
    }
    let a = h[0], b2 = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
    for (let i = 0; i < 64; i++) {
      const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      const ch = (e & f) ^ (~e & g);
      const t1 = (hh + S1 + ch + K[i] + w[i]) | 0;
      const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      const mj = (a & b2) ^ (a & c) ^ (b2 & c);
      const t2 = (S0 + mj) | 0;
      hh = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b2; b2 = a; a = (t1 + t2) | 0;
    }
    h[0] = (h[0] + a) | 0; h[1] = (h[1] + b2) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0;
    h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0; h[6] = (h[6] + g) | 0; h[7] = (h[7] + hh) | 0;
  }
  update(data) {
    let i = 0; const n = data.length; this.len += n;
    if (this.nbuf) {
      while (this.nbuf < 64 && i < n) this.buf[this.nbuf++] = data[i++];
      if (this.nbuf === 64) { this._blocco(this.buf, 0); this.nbuf = 0; }
    }
    for (; i + 64 <= n; i += 64) this._blocco(data, i);
    while (i < n) this.buf[this.nbuf++] = data[i++];
    return this;
  }
  digest() {
    const bits = this.len * 8, pad = new Uint8Array(((this.nbuf < 56 ? 56 : 120) - this.nbuf) + 8);
    pad[0] = 0x80;
    const dv = new DataView(pad.buffer);
    dv.setUint32(pad.length - 8, Math.floor(bits / 4294967296)); dv.setUint32(pad.length - 4, bits >>> 0);
    const len = this.len; this.update(pad); this.len = len;
    return Array.from(this.h, v => (v >>> 0).toString(16).padStart(8, '0')).join('');
  }
}

/** SHA-256 (esadecimale) di un ArrayBuffer/Uint8Array in memoria (usa SubtleCrypto se disponibile). */
export async function sha256Bytes(bytes) {
  const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (globalThis.crypto && crypto.subtle) {
    const h = await crypto.subtle.digest('SHA-256', u8);
    return Array.from(new Uint8Array(h), b => b.toString(16).padStart(2, '0')).join('');
  }
  return new Sha256().update(u8).digest();
}

/** SHA-256 di un File/Blob a fette da 4 MiB; `avanzamento(fatti, totale)` opzionale. */
export async function sha256File(file, avanzamento) {
  const s = new Sha256(), FETTA = 4 * 1024 * 1024;
  for (let o = 0; o < file.size; o += FETTA) {
    s.update(new Uint8Array(await file.slice(o, Math.min(file.size, o + FETTA)).arrayBuffer()));
    if (avanzamento) avanzamento(Math.min(file.size, o + FETTA), file.size);
    await new Promise(r => setTimeout(r));   // cede il thread: la pagina resta reattiva
  }
  return s.digest();
}
