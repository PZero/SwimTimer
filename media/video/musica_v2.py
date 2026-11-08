"""Colonna sonora ORIGINALE del video «SwimTimer: a che punto siamo» (v2), sintetizzata da zero con numpy.

Nessun campione, loop o brano esistente. Riusa gli strumenti di base di musica.py (cassa, hi-hat, clap, basso, pad,
pluck, riser, impatto, riverbero) e aggiunge un lead «saw» additivo e un sub-basso.
Elettronica moderna a 120 BPM in re minore, progressione originale Dm9 - Bbmaj9 - Gm7/D - A7sus4.
Sezioni (battute da 2 s): intro 0-12 s, groove 12-44 s, build-up 44-48 s, DROP 48-72 s (filtri),
piattaforma 72-90 s, display 90-102 s, pausa 102-110 s, finale 110-118 s, stacco netto a 118 s.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import musica as m  # noqa: E402  strumenti di base (stesso SR, BPM, durata)

SR, BEAT, BAR, DUR, N = m.SR, m.BEAT, m.BAR, m.DUR, m.N
tt = m.tt
rng = np.random.default_rng(20261108)
m.rng = rng                      # rumore (hi-hat, clap, riser) con un seme diverso dal primo video

B_GROOVE, B_BUILD, B_DROP, B_PLAT, B_DISP, B_BREAK, B_CLOSE, B_STOP = 6, 22, 24, 36, 45, 51, 55, 59
BASS = [38, 34, 38, 33]
CHORDS = [[50, 53, 57, 60, 64], [46, 50, 53, 57, 60], [50, 53, 55, 58, 62], [52, 55, 57, 62, 64]]
# melodia del lead (crome) per accordo: originale
MEL = {0: [74, None, 72, 74, None, 77, 76, None], 1: [74, None, 72, None, 70, 69, None, 65],
       2: [70, None, 69, 70, None, 74, 72, None], 3: [76, None, 74, 73, None, 69, None, None]}
CUTS = [6, 12, 20, 26, 32, 38, 44, 48, 54, 60, 66, 72, 78, 84, 90, 96, 102, 110]


def saw_note(f, dur=0.45, bright=1.0):
    n = int((dur + 0.25) * SR)
    t = tt(n)
    s = np.zeros(n)
    for det in (-0.006, 0.0, 0.006):
        for k in range(1, 13):
            fk = f * k * (1 + det)
            if fk > SR / 2.2:
                break
            s += np.sin(2 * np.pi * fk * t + k * det * 50) / k * (bright if k > 3 else 1.0)
    env = np.minimum(t / 0.01, 1.0) * np.where(t < dur, np.exp(-t / 0.9), np.exp(-dur / 0.9) * np.exp(-(t - dur) / 0.08))
    return s * env * 0.22


def sub(f, dur):
    n = int(dur * SR)
    t = tt(n)
    return np.sin(2 * np.pi * f * t) * np.minimum(t / 0.01, 1) * np.exp(-t / (dur * 0.8)) * 0.9


def sec_gain(t):
    """Dinamica per sezione: groove contenuto, drop pieno."""
    b = t / BAR
    if b < B_BUILD:
        return 0.72
    if b < B_DROP:
        return 0.8
    if b < B_PLAT:
        return 1.0
    if b < B_DISP:
        return 0.8
    if b < B_BREAK:
        return 0.88
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

    nb = int(DUR / BAR)
    K, HC, HO, CL = m.kick(), m.hat(False), m.hat(True), m.clap()
    kick_times = []

    def kick_on(b):
        return (B_GROOVE <= b < B_BUILD) or (B_DROP <= b < B_BREAK) or (B_CLOSE <= b < B_STOP)

    for b in range(nb):
        t0 = b * BAR
        ci = b % 4 if b < B_STOP else 0
        ch, root = CHORDS[ci], BASS[ci]
        # pad (in pausa e nel build piu' presente)
        if b < B_STOP:
            g = 0.75 if b < 3 else (1.0 if (B_BREAK <= b < B_CLOSE or B_BUILD <= b < B_DROP) else 0.8)
            for mm in ch:
                put('pad', m.pad_note(mm, BAR), t0, pan=rng.uniform(-0.4, 0.4), g=g)
        # arpeggio a sedicesimi
        if 1 <= b < B_STOP:
            pat = [0, 2, 4, 2, 3, 4, 6, 4, 0, 2, 4, 5, 3, 4, 7, 4] if b >= B_DROP else [0, None, 2, 4, None, 3, 4, None, 2, None, 4, 3, None, 6, 4, None]
            vol = 0.45 if b < B_GROOVE else (0.75 if b < B_DROP else 0.9)
            if B_BUILD <= b < B_DROP:
                vol = 0.55 + 0.4 * (b - B_BUILD) / 2
            tones = ch + [x + 12 for x in ch] + [ch[0] + 24]
            for s_, idx in enumerate(pat):
                if idx is None:
                    continue
                put('arp', m.pluck(m.mtof(tones[idx] + 12), 0.4, 0.11), t0 + s_ * BEAT / 4, pan=0.5 if s_ % 2 else -0.5, g=0.13 * vol)
        # lead saw: drop, display, finale
        lead = (B_DROP <= b < B_PLAT) or (B_DISP + 2 <= b < B_BREAK) or (B_CLOSE <= b < B_STOP)
        if lead:
            gl = 1.0 if B_DROP <= b < B_PLAT else 0.75
            for s_, note in enumerate(MEL[ci]):
                if note is not None:
                    put('lead', saw_note(m.mtof(note), 0.36), t0 + s_ * BEAT / 2, pan=0.1, g=0.27 * gl)
                    put('lead', saw_note(m.mtof(note - 12), 0.36, 0.6), t0 + s_ * BEAT / 2, pan=-0.1, g=0.11 * gl)
        # cassa
        if kick_on(b):
            for k in range(4):
                put('drums', K, t0 + k * BEAT, 0, 0.95)
                kick_times.append(t0 + k * BEAT)
        # hi-hat
        if 3 <= b < B_STOP and not (B_BREAK <= b < B_CLOSE - 1):
            for k in range(4):
                put('drums', HO, t0 + k * BEAT + BEAT / 2, 0.25, 0.28 if b >= B_GROOVE else 0.15)
                if b >= B_DROP and not (B_BREAK <= b < B_CLOSE):
                    for q, gq in ((0, 0.2), (0.25, 0.09), (0.75, 0.11)):
                        put('drums', HC, t0 + k * BEAT + q * BEAT, -0.3 if q else 0.3, gq)
        # clap su 2 e 4
        if (B_GROOVE + 4 <= b < B_BUILD) or (B_DROP <= b < B_BREAK) or (B_CLOSE <= b < B_STOP):
            for k in (1, 3):
                put('drums', CL, t0 + k * BEAT, 0, 0.34 if b >= B_DROP else 0.24)
        # basso
        if kick_on(b):
            for k in range(4):
                put('bass', m.bass_note(m.mtof(root), 0.22), t0 + k * BEAT + BEAT / 2, 0, 0.55)
            if b >= B_DROP:
                put('bass', sub(m.mtof(root - 12), 0.9), t0, 0, 0.5)
                put('bass', m.bass_note(m.mtof(root + 12), 0.18), t0 + 3.75 * BEAT, 0, 0.3)
        elif B_BREAK <= b < B_CLOSE or b < B_GROOVE and b >= 2:
            put('bass', m.bass_note(m.mtof(root), 1.6) * 0.7, t0, 0, 0.45)
        elif B_BUILD <= b < B_DROP:
            for k in range(8):
                put('bass', m.bass_note(m.mtof(root), 0.15), t0 + k * BEAT / 2, 0, 0.25 + 0.2 * (b - B_BUILD))

    # apertura, build-up e drop
    put('fx', m.impact() * 0.55, 0.05, 0, 0.7)
    put('fx', m.riser(BAR * 2), (B_GROOVE - 2) * BAR, 0, 0.45)
    put('fx', m.riser(2 * BAR), B_BUILD * BAR, 0, 0.6)
    for s_ in range(32):                                          # rullo che accelera
        ts = B_BUILD * BAR + (s_ * BEAT / 4 if s_ < 16 else 4 * BEAT + (s_ - 16) * BEAT / 4)
        put('drums', CL, ts, 0, 0.04 + 0.2 * s_ / 31)
    put('fx', m.impact(), B_DROP * BAR, 0, 1.0)
    put('drums', HO, B_DROP * BAR, 0.3, 0.5)
    put('fx', m.riser(BAR), (B_CLOSE - 1) * BAR, 0, 0.7)
    put('fx', m.impact() * 0.7, B_CLOSE * BAR, 0, 0.8)
    # stacco finale: accordo pieno + impatto a 118 s, poi solo la coda del riverbero
    tf = B_STOP * BAR
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
    p = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent / 'musica_v2.wav')
    y, lufs, peak = compose(p)
    print(f'LUFS integrati {lufs}, picco {peak} dBFS')
