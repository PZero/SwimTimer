"""Colonna sonora ORIGINALE del video v4 «Houston, abbiamo un problema» (180 s), sintetizzata da zero con numpy.
Stessi strumenti di musica_v3.py (cassa, hi-hat, clap, basso, pad, pluck, lead saw, sub, riser, impatto, riverbero),
120 BPM in re minore, progressione originale Dm9 - Bbmaj9 - Gm7/D - A7sus4, sezioni ridistribuite su 180 s:

  0-6 intro calma · 6-33 clip (pad e arpeggio leggeri) · 33-63 parte tesa (battito + basso a ottavi) ·
  63-78 pausa della confessione · 78-102 ripresa (cassa, clap, lead leggero) · 102-152 groove «ritmo» pieno ·
  152-162 pausa · 162-178 finale · stacco netto a 178 s, coda fino a 180 s.

Nessun campione, loop o brano esistente. Durante la clip il video attenua questa musica (vedi genera_video_v4.py).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import musica as m  # noqa: E402
import musica_v3 as m3  # noqa: E402  lead saw e sub-basso

SR, BEAT, BAR = m.SR, m.BEAT, m.BAR
DUR = 180.0
N = int(DUR * SR)
tt = m.tt
rng = np.random.default_rng(20261112)
m.rng = rng
m3.rng = rng

T_CLIP0, T_TENSE, T_BREAK, T_RISE, T_DROP, T_PAUSE, T_FIN, T_STOP = 6.0, 33.0, 63.0, 78.0, 102.0, 152.0, 162.0, 178.0
BASS = m3.BASS
CHORDS = m3.CHORDS
MEL = m3.MEL
CUTS = [6, 33, 43, 55, 63, 78, 86, 96, 102, 106, 116, 122, 134, 142, 152, 162, 172]
saw_note, sub = m3.saw_note, m3.sub


def sec_gain(t):
    if t < T_TENSE:
        return 0.72
    if t < T_BREAK:
        return 0.82
    if t < T_RISE:
        return 0.75
    if t < T_DROP:
        return 0.88
    if t < T_PAUSE:
        return 1.0
    if t < T_FIN:
        return 0.75
    return 1.0


def build():
    bus = {k: np.zeros((2, N)) for k in ('drums', 'bass', 'pad', 'arp', 'lead', 'fx')}

    def put(name, sig, t0, pan=0.0, g=1.0):
        i = int(round(t0 * SR))
        if i >= N or i < 0:
            return
        j = min(N, i + len(sig))
        seg = sig[:j - i] * g * (sec_gain(t0) if name in ('drums', 'bass', 'arp') else 1.0)
        bus[name][0, i:j] += seg * np.sqrt((1 - pan) / 2)
        bus[name][1, i:j] += seg * np.sqrt((1 + pan) / 2)

    K, HC, HO, CL = m.kick(), m.hat(False), m.hat(True), m.clap()
    kick_times = []
    nbeats = int(T_STOP / BEAT)
    for k in range(nbeats):
        t0 = k * BEAT
        bar, step = k // 4, k % 4
        ci = bar % 4
        ch, root = CHORDS[ci], BASS[ci]
        tense = T_TENSE <= t0 < T_BREAK
        brk = T_BREAK <= t0 < T_RISE
        rise = T_RISE <= t0 < T_DROP
        drop = T_DROP <= t0 < T_PAUSE
        pause = T_PAUSE <= t0 < T_FIN
        fin = T_FIN <= t0 < T_STOP
        full = drop or fin
        # pad: un accordo a battuta
        if step == 0:
            g = 0.75 if t0 < 6 else (1.0 if (brk or pause or 29 <= t0 < T_TENSE) else 0.8)
            for mm in ch:
                put('pad', m.pad_note(mm, BAR), t0, pan=rng.uniform(-0.4, 0.4), g=g)
        # arpeggio a sedicesimi
        if t0 >= 1:
            pat = ([0, 2, 4, 2, 3, 4, 6, 4, 0, 2, 4, 5, 3, 4, 7, 4] if (full or rise)
                   else [0, None, 2, 4, None, 3, 4, None, 2, None, 4, 3, None, 6, 4, None])
            vol = 0.45 if t0 < 33 else (0.7 if tense else (0.5 if (brk or pause) else (0.75 if rise else 0.9)))
            if tense:
                vol = 0.55 + 0.35 * (t0 - T_TENSE) / 30.0
            tones = ch + [x + 12 for x in ch] + [ch[0] + 24]
            for s_ in range(4):
                idx = pat[step * 4 + s_]
                if idx is not None:
                    put('arp', m.pluck(m.mtof(tones[idx] + 12), 0.4, 0.11), t0 + s_ * BEAT / 4,
                        pan=0.5 if s_ % 2 else -0.5, g=0.13 * vol)
        # lead saw
        if (T_RISE + 12 <= t0 < T_DROP) or full:
            gl = 0.55 if rise else (1.0 if t0 < 126 else 0.8)
            for h in (0, 1):                                   # melodia in crome: 2 note per battito
                note = MEL[ci][step * 2 + h]
                if note is not None:
                    tn = t0 + h * BEAT / 2
                    put('lead', saw_note(m.mtof(note), 0.36), tn, pan=0.1, g=0.27 * gl)
                    put('lead', saw_note(m.mtof(note - 12), 0.36, 0.6), tn, pan=-0.1, g=0.11 * gl)
        # cassa
        kick_now = (rise or full) or (tense and step in (0, 2))
        if kick_now:
            put('drums', K, t0, 0, 0.95 if not tense else 0.6)
            kick_times.append(t0)
        # hi-hat
        if tense:
            put('drums', HC, t0 + BEAT / 2, 0.2, 0.14)
            put('drums', HC, t0, -0.2, 0.07)
        elif rise or full:
            put('drums', HO, t0 + BEAT / 2, 0.25, 0.28)
            if full:
                for q, gq in ((0, 0.2), (0.25, 0.09), (0.75, 0.11)):
                    put('drums', HC, t0 + q * BEAT, -0.3 if q else 0.3, gq)
        elif 24 <= t0 < T_TENSE or (pause and step % 2 == 1):
            put('drums', HO, t0 + BEAT / 2, 0.25, 0.1)
        # clap su 2 e 4
        if (T_RISE + 8 <= t0 < T_DROP or full) and step in (1, 3):
            put('drums', CL, t0, 0, 0.34 if full else 0.22)
        # basso
        if rise or full:
            put('bass', m.bass_note(m.mtof(root), 0.22), t0 + BEAT / 2, 0, 0.55)
            if step == 0 and full:
                put('bass', sub(m.mtof(root - 12), 0.9), t0, 0, 0.5)
            if step == 3 and full:
                put('bass', m.bass_note(m.mtof(root + 12), 0.18), t0 + 0.75 * BEAT, 0, 0.3)
        elif tense:
            for h in (0, 1):
                put('bass', m.bass_note(m.mtof(root), 0.15), t0 + h * BEAT / 2, 0, 0.22 + 0.25 * (t0 - T_TENSE) / 30.0)
        elif step == 0 and (brk or pause or t0 >= 12):
            put('bass', m.bass_note(m.mtof(root), 1.6) * 0.7, t0, 0, 0.45)

    # effetti: aperture, salite e impatti sui punti di taglio
    put('fx', m.impact() * 0.55, 0.05, 0, 0.7)
    put('fx', m.riser(BAR * 2), T_TENSE - 4, 0, 0.45)
    put('fx', m.impact() * 0.6, T_TENSE, 0, 0.7)
    put('fx', m.riser(BAR * 2), T_RISE - 4, 0, 0.5)
    put('fx', m.impact() * 0.7, T_RISE, 0, 0.7)
    put('fx', m.riser(BAR * 2), T_DROP - 4, 0, 0.6)
    for s_ in range(32):                                          # rullo che accelera prima del groove
        ts = T_DROP - 4 + (s_ * BEAT / 4 if s_ < 16 else 4 * BEAT + (s_ - 16) * BEAT / 4)
        put('drums', CL, ts, 0, 0.04 + 0.2 * s_ / 31)
    put('fx', m.impact(), T_DROP, 0, 1.0)
    put('drums', HO, T_DROP, 0.3, 0.5)
    put('fx', m.riser(BAR * 2), T_FIN - 4, 0, 0.55)
    put('fx', m.impact() * 0.8, T_FIN, 0, 0.8)
    # stacco finale: accordo pieno + impatto, poi solo la coda del riverbero
    tf = T_STOP
    for mm in CHORDS[0] + [CHORDS[0][0] - 12, CHORDS[0][0] + 12]:
        put('pad', m.pad_note(mm, 0.5), tf, pan=rng.uniform(-0.5, 0.5), g=1.3)
    put('lead', saw_note(m.mtof(74), 0.5), tf, 0, 0.3)
    put('drums', K, tf, 0, 1.0)
    put('fx', m.impact(), tf, 0, 0.9)
    put('bass', sub(m.mtof(26), 1.2), tf, 0, 0.7)
    for tc in CUTS:
        put('fx', m.whoosh(0.5), tc - 0.12, rng.uniform(-0.4, 0.4), 0.26)

    tb = tt(int(BEAT * SR))
    curve = 1 - 0.6 * np.exp(-tb / 0.1) * np.minimum(tb / 0.003, 1)
    duck = np.ones(N)
    for tk in kick_times:
        i = int(round(tk * SR))
        j = min(N, i + len(curve))
        duck[i:j] = np.minimum(duck[i:j], curve[:j - i])
    for name in ('pad', 'bass', 'arp', 'lead'):
        bus[name] *= duck if name != 'lead' else (0.5 + 0.5 * duck)
    return bus


def compose(path, target=-16.0):
    bus = build()
    arp = m.echo(bus['arp'])
    lead = m.echo(bus['lead'], ((0.375, 0.3), (0.75, 0.14)))
    send = bus['pad'] * 0.7 + arp * 0.6 + lead * 0.7 + bus['fx'] * 0.3
    m.rng = rng
    rv = m.reverb(send, 1.8)
    mix = bus['drums'] + bus['bass'] * 0.9 + bus['pad'] * 0.82 + arp * 0.9 + lead * 0.82 + bus['fx'] * 0.8 + rv * 0.5
    t = tt(N)
    fade = np.minimum(t / 0.3, 1.0) * np.clip((DUR - 0.05 - t) / 1.6, 0, 1) ** 1.5
    mix *= fade
    gain = 0.5
    for _ in range(5):
        y = mix * gain
        y = 0.82 * np.tanh(y / 0.82)
        pk = np.max(np.abs(y))
        if pk > 0.82:
            y *= 0.82 / pk
        m.write_wav(path, y)
        lufs, peak = m.measure_lufs(path)
        if abs(lufs - target) < 0.3:
            break
        gain *= 10 ** ((target - lufs) / 20)
    return y, lufs, peak


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent / 'musica_v4.wav')
    y, lufs, peak = compose(p)
    print(f'LUFS integrati {lufs}, picco {peak} dBFS')
