"""Colonna sonora originale di SwimTimer, sintetizzata da zero con numpy.

Nessun campione, loop o brano esistente: tutto (cassa, hi-hat, clap, basso, pad,
arpeggio, lead, riser, riverbero) e' generato matematicamente.
120 BPM, 60 battute da 2 s = 120 s. Progressione originale: Am9 - Fmaj7 - Dm9 - Em7,
chiusura Dm9 - Em7 - Am9.
"""
import re
import subprocess
import wave
from functools import lru_cache

import numpy as np

SR = 48000
BPM = 120
BEAT = 60.0 / BPM
BAR = 4 * BEAT
DUR = 120.0
N = int(DUR * SR)

# battute (indice) delle sezioni
B_INTRO, B_GROOVE, B_BUILD, B_DROP, B_VERIFY, B_PROG, B_STATO, B_CLOSE, B_FINAL = 0, 4, 18, 20, 40, 45, 50, 55, 58

BASS = [45, 41, 38, 40]
CHORDS = [[57, 60, 64, 67, 71], [53, 57, 60, 64, 67], [50, 53, 57, 60, 64], [52, 55, 59, 62, 64]]

rng = np.random.default_rng(20261104)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tt(n):
    return np.arange(n) / SR


@lru_cache(maxsize=None)
def pad_note(m, dur):
    n = int((dur + 1.2) * SR)
    t = tt(n)
    f = mtof(m)
    s = np.zeros(n)
    for det in (-0.0035, 0.0035):
        for k in range(1, 7):
            s += np.sin(2 * np.pi * f * (1 + det) * k * t + k) / (k ** 1.4)
    env = np.minimum(t / 0.55, 1.0) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.45))
    return s * env * 0.16


def pluck(f, dur=0.5, dec=0.16, harm=4):
    n = int(dur * SR)
    t = tt(n)
    s = np.zeros(n)
    for k in range(1, harm + 1):
        s += np.sin(2 * np.pi * f * k * t) / (k ** 1.7)
    env = np.minimum(t / 0.004, 1.0) * np.exp(-t / dec)
    return s * env


def lead_note(f, dur=0.6):
    n = int(dur * SR)
    t = tt(n)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.25, 1)
    s = np.sin(2 * np.pi * f * vib * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(t / 0.008, 1.0) * np.exp(-t / 0.22)
    return s * env


def bass_note(f, dur=0.30):
    n = int(dur * SR)
    t = tt(n)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.18 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(t / 0.006, 1.0) * np.exp(-t / (dur * 0.55))
    return np.tanh(s * 1.4) * env * 0.8


def kick():
    n = int(0.42 * SR)
    t = tt(n)
    f = 46 + 110 * np.exp(-t / 0.032)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / 0.15)
    s += 0.25 * np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.004)
    return np.tanh(s * 1.3)


def hat(open_=False):
    dur = 0.28 if open_ else 0.10
    n = int(dur * SR)
    t = tt(n)
    x = rng.standard_normal(n)
    x = np.diff(x, 2, prepend=[0, 0])
    return x * np.exp(-t / (0.085 if open_ else 0.022)) * 0.35


def clap():
    n = int(0.32 * SR)
    t = tt(n)
    x = rng.standard_normal(n)
    x = np.diff(x, 1, prepend=0)
    x = np.convolve(x, np.ones(3) / 3, mode='same')
    env = sum(np.exp(-np.maximum(t - d, 0) / 0.012) * (t >= d) for d in (0, 0.011, 0.022))
    env = env + 0.9 * np.exp(-t / 0.075) * (t >= 0.03)
    return x * env * 0.55


def riser(dur):
    n = int(dur * SR)
    t = tt(n)
    u = t / dur
    x = rng.standard_normal(n)
    x = np.diff(x, 2, prepend=[0, 0])
    s = x * (u ** 2.2) * 0.45
    f = 220 * 2 ** (u * 2.6)
    s += np.sin(2 * np.pi * np.cumsum(f) / SR) * (u ** 2) * 0.25
    return s


def whoosh(dur=0.5):
    n = int(dur * SR)
    t = tt(n)
    u = t / dur
    x = rng.standard_normal(n)
    x = np.diff(x, 1, prepend=0)
    k = 8
    x = np.convolve(x, np.ones(k) / k, mode='same')
    return x * np.sin(np.pi * u) ** 2 * 0.6


def impact():
    n = int(2.2 * SR)
    t = tt(n)
    f = 38 + 50 * np.exp(-t / 0.25)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    x = rng.standard_normal(n)
    x = np.diff(x, 2, prepend=[0, 0])
    s = s * 0.9 + x * np.exp(-t / 0.45) * 0.28
    return s


def build():
    bus = {k: np.zeros((2, N)) for k in ('drums', 'bass', 'pad', 'arp', 'lead', 'fx')}

    def put(name, sig, t0, pan=0.0, g=1.0):
        i = int(round(t0 * SR))
        if i >= N:
            return
        j = min(N, i + len(sig))
        seg = sig[:j - i] * g
        a = np.sqrt((1 - pan) / 2) * np.sqrt(2)
        b = np.sqrt((1 + pan) / 2) * np.sqrt(2)
        bus[name][0, i:j] += seg * a * 0.7071
        bus[name][1, i:j] += seg * b * 0.7071

    nb = int(DUR / BAR)

    def chord_idx(b):
        if b == 56:
            return 2
        if b == 57:
            return 3
        if b >= 58:
            return 0
        return b % 4

    def kick_on(b):
        return (B_GROOVE <= b < B_BUILD) or (B_DROP <= b < B_STATO) or (B_CLOSE <= b < B_FINAL)

    K, HC, HO, CL = kick(), hat(False), hat(True), clap()
    kick_times = []

    for b in range(nb):
        t0 = b * BAR
        ci = chord_idx(b)
        ch = CHORDS[ci]
        root = BASS[ci]
        # --- pad
        if b < B_FINAL:
            for m in ch:
                put('pad', pad_note(m, BAR), t0, pan=rng.uniform(-0.35, 0.35), g=1.0)
        elif b == B_FINAL:
            for m in ch + [ch[0] - 12]:
                put('pad', pad_note(m, 3.0), t0, pan=rng.uniform(-0.4, 0.4), g=1.25)
        # --- arpeggio (16 step)
        pat = [0, None, 2, 3, None, 4, 3, None, 2, None, 3, 4, None, 6, 4, None]
        if b >= B_DROP and b % 2 == 1:
            pat = [4, None, 3, 2, None, 3, 4, None, 6, None, 4, 3, None, 2, 0, None]
        if 2 <= b < B_FINAL:
            vol = 0.5 if b < B_GROOVE else (0.8 if b < B_DROP else 1.0)
            if B_STATO <= b < B_CLOSE:
                vol = 0.9
            tones = ch + [m + 12 for m in ch]
            for s_, idx in enumerate(pat):
                if idx is None:
                    continue
                m = tones[idx] + 12
                put('arp', pluck(mtof(m), 0.45, 0.14), t0 + s_ * BEAT / 4, pan=0.45 if s_ % 2 else -0.45, g=0.17 * vol)
        # --- lead
        lead_on = (B_DROP <= b < B_VERIFY) or (B_PROG <= b < B_STATO - 1) or (B_CLOSE <= b < B_FINAL)
        if lead_on:
            tones = [m + 24 for m in ch[:4]] + [ch[0] + 36]
            lp = [4, None, 3, None, 2, 3, None, None] if b % 2 == 0 else [2, None, 4, 3, None, 2, 0, None]
            for s_, idx in enumerate(lp):
                if idx is None:
                    continue
                put('lead', lead_note(mtof(tones[idx] - 12), 0.55), t0 + s_ * BEAT / 2, pan=0.15, g=0.14)
        # --- kick
        if kick_on(b):
            for k in range(4):
                if b == B_BUILD + 1 and k == 3:
                    continue
                tk = t0 + k * BEAT
                put('drums', K, tk, 0, 0.9)
                kick_times.append(tk)
        # --- hats
        if B_INTRO + 3 <= b < B_FINAL and not (B_STATO <= b < B_CLOSE - 1 and False):
            soft = 0.6 if b < B_GROOVE else 1.0
            for k in range(4):
                put('drums', HO, t0 + k * BEAT + BEAT / 2, 0.25, 0.30 * soft)
                if b >= B_DROP and not (B_STATO <= b < B_CLOSE):
                    put('drums', HC, t0 + k * BEAT, -0.25, 0.22)
                    put('drums', HC, t0 + k * BEAT + BEAT / 4, 0.2, 0.10)
                    put('drums', HC, t0 + k * BEAT + 3 * BEAT / 4, -0.2, 0.10)
        # --- clap/snare
        if (B_GROOVE + 4 <= b < B_BUILD) or (B_DROP <= b < B_STATO - 5 + 5 and not (B_STATO <= b)) or (B_CLOSE <= b < B_FINAL):
            for k in (1, 3):
                put('drums', CL, t0 + k * BEAT, 0, 0.36 if b >= B_DROP else 0.24)
        # --- basso
        if kick_on(b):
            for k in range(4):
                put('bass', bass_note(mtof(root), 0.24), t0 + k * BEAT + BEAT / 2, 0, 0.55)
            if b >= B_DROP:
                put('bass', bass_note(mtof(root - 12), 0.8), t0, 0, 0.55)
                put('bass', bass_note(mtof(root + 12), 0.2), t0 + 3 * BEAT + BEAT * 0.75, 0, 0.3)
        elif B_STATO <= b < B_CLOSE:
            put('bass', bass_note(mtof(root), 1.6) * 0.7, t0, 0, 0.5)
        elif b >= B_GROOVE and b < B_FINAL:
            put('bass', bass_note(mtof(root), 1.0), t0, 0, 0.4)

    # --- build: rullo di rullante, riser, impatto del drop
    put('fx', riser(2 * BAR), (B_BUILD) * BAR, 0, 0.8)
    for s_ in range(16):
        put('drums', CL, (B_BUILD + 1) * BAR + s_ * BEAT / 4 + 0.0, 0, 0.10 + 0.30 * s_ / 15)
    put('fx', impact(), B_DROP * BAR, 0, 0.9)
    put('drums', HO, B_DROP * BAR, 0.3, 0.5)
    # intro: piccolo riser in battuta 3
    put('fx', riser(BAR) * 0.5, 3 * BAR, 0, 0.5)
    # secondo riser verso la chiusura (battuta 54)
    put('fx', riser(BAR), (B_CLOSE - 1) * BAR, 0, 0.7)
    put('fx', impact() * 0.6, B_CLOSE * BAR, 0, 0.7)
    # stacco finale
    put('fx', impact() * 0.55, B_FINAL * BAR, 0, 0.8)
    # whoosh ai tagli di scena
    for tc in CUTS:
        put('fx', whoosh(0.5), tc - 0.12, rng.uniform(-0.4, 0.4), 0.30)

    # --- sidechain (cassa -> pad/basso/arpeggio)
    tb = tt(int(BEAT * SR))
    curve = 1 - 0.55 * np.exp(-tb / 0.11) * np.minimum(tb / 0.003, 1)
    duck = np.ones(N)
    for tk in kick_times:
        i = int(round(tk * SR))
        j = min(N, i + len(curve))
        duck[i:j] = np.minimum(duck[i:j], curve[:j - i])
    for name in ('pad', 'bass', 'arp'):
        bus[name] *= duck
    return bus, duck


CUTS = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110]


def echo(x, times=((0.375, 0.42), (0.75, 0.22), (1.125, 0.10))):
    y = x.copy()
    for d, g in times:
        k = int(d * SR)
        y[:, k:] += x[:, :-k] * g
    return y


def reverb(x, secs=1.6, wet=1.0):
    n = int(secs * SR)
    t = tt(n)
    out = np.zeros_like(x)
    size = 1 << int(np.ceil(np.log2(x.shape[1] + n)))
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / 0.42)
        ir = np.convolve(ir, np.ones(3) / 3, mode='same')
        ir /= np.sqrt(np.sum(ir ** 2))
        X = np.fft.rfft(x[c], size)
        Y = np.fft.rfft(ir, size)
        out[c] = np.fft.irfft(X * Y, size)[:x.shape[1]]
    return out * wet


def measure_lufs(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?\d+\.\d+) LUFS', r.stderr)
    p = re.findall(r'Peak:\s+(-?\d+\.\d+) dBFS', r.stderr)
    return float(m[-1]), float(p[-1]) if p else None


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').T.copy()
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def compose(path, target=-16.0):
    bus, duck = build()
    arp = echo(bus['arp'])
    lead = echo(bus['lead'])
    send = bus['pad'] * 0.7 + arp * 0.6 + lead * 0.8 + bus['fx'] * 0.3
    rv = reverb(send, 1.7)
    mix = bus['drums'] * 1.0 + bus['bass'] * 0.9 + bus['pad'] * 0.9 + arp * 0.9 + lead * 0.9 + bus['fx'] * 0.8 + rv * 0.55
    # fade
    t = tt(N)
    fade = np.minimum(t / 1.0, 1.0) * np.minimum((DUR - t) / 2.0, 1.0)
    mix *= fade
    gain = 0.5
    for it in range(4):
        y = mix * gain
        y = 0.891 * np.tanh(y / 0.891)
        pk = np.max(np.abs(y))
        if pk > 0.891:
            y *= 0.891 / pk
        write_wav(path, y)
        lufs, peak = measure_lufs(path)
        if abs(lufs - target) < 0.4:
            break
        gain *= 10 ** ((target - lufs) / 20)
    return y, lufs, peak


def stats(y):
    out = []
    for name, a, b in [('intro 0-8', 0, 8), ('groove 8-36', 8, 36), ('build 36-40', 36, 40), ('drop 40-80', 40, 80),
                       ('verifiche 80-90', 80, 90), ('programmatore 90-100', 90, 100), ('stato 100-110', 100, 110),
                       ('chiusura 110-116', 110, 116), ('coda 116-120', 116, 120)]:
        s = y[:, int(a * SR):int(b * SR)]
        rms = 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)
        out.append(f'{name}: RMS {rms:.1f} dBFS, picco {20*np.log10(np.max(np.abs(s))+1e-12):.1f} dBFS')
    # silenzi: finestre di 0,5 s con RMS < -50 dB
    w = SR // 2
    quiet = [i * 0.5 for i in range(N // w - 4) if 20 * np.log10(np.sqrt(np.mean(y[:, i * w:(i + 1) * w] ** 2)) + 1e-12) < -50]
    out.append('finestre di silenzio (<-50 dBFS) prima del fade finale: ' + (str(quiet) if quiet else 'nessuna'))
    out.append(f'campioni a |x|>=0.999: {int(np.sum(np.abs(y) >= 0.999))}')
    return out


if __name__ == '__main__':
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else 'musica_originale.wav'
    y, lufs, peak = compose(p)
    print(f'LUFS integrati {lufs}, picco {peak} dBFS')
    print('\n'.join(stats(y)))
