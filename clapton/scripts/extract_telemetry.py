"""FILAMENT — offline spectral telemetry (Phase 2).

Reads output/audio/clapton_master.wav and computes, for every 1/60 s video frame:
  rms               normalized RMS energy of the frame window                      [0..1]
  sub_bass          band power 20–90 Hz          (log-compressed, 50 dB range)     [0..1]
  low_mids          band power 150–600 Hz        (string body resonance)           [0..1]
  lead_presence     band power 1.5–4.5 kHz       (guitar bite, pick transients)    [0..1]
  highs             band power 6–16 kHz                                            [0..1]
  attack_transient  positive first derivative of lead_presence (strike moments)    [0..1]

Windows: lead_presence / attack use a short causal window ending at the frame's end
(so a pick strike lands in the frame that contains it); the other bands use a 4096-sample
Hann window centred on the frame (needed to resolve 20 Hz).

Writes output/telemetry.json (frames[]) and output/telemetry.js (same data as a script
global, so the live player also works from file:// without fetch).
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, 'output', 'audio', 'clapton_master.wav')
FPS = 60


def read_wav(path):
    with open(path, 'rb') as f:
        b = f.read()
    assert b[:4] == b'RIFF' and b[8:12] == b'WAVE'
    pos, fmt, data = 12, None, None
    while pos < len(b):
        cid, size = b[pos:pos + 4], int.from_bytes(b[pos + 4:pos + 8], 'little')
        body = b[pos + 8:pos + 8 + size]
        if cid == b'fmt ':
            fmt = (int.from_bytes(body[2:4], 'little'), int.from_bytes(body[4:8], 'little'), int.from_bytes(body[14:16], 'little'))
        elif cid == b'data':
            data = body
        pos += 8 + size + (size & 1)
    ch, sr, bits = fmt
    assert bits == 24, 'expected 24-bit PCM'
    raw = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
    v = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
    v = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / (1 << 23)
    return v.reshape(-1, ch), sr


def band_power(frames_spec, freqs, lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return frames_spec[:, m].sum(axis=1)


def logn(p, rng=50.0):
    db = 10 * np.log10(np.maximum(p, 1e-20))
    hi = np.percentile(db, 99.5)
    return np.clip((db - (hi - rng)) / rng, 0, 1)


def main():
    x, sr = read_wav(WAV)
    mono = x.mean(axis=1)
    duration = len(mono) / sr
    n_frames = int(round(duration * FPS))
    hop = sr // FPS
    assert hop * FPS == sr, 'sample rate must be a multiple of 60'
    pad = 4096
    xp = np.concatenate([np.zeros(pad), mono, np.zeros(pad)])

    # long centred window (bands incl. sub-bass)
    NL = 4096
    wl = np.hanning(NL)
    centres = (np.arange(n_frames) + 0.5) * hop + pad
    idxL = (centres[:, None] - NL // 2 + np.arange(NL)[None, :]).astype(np.int64)
    specL = np.abs(np.fft.rfft(xp[idxL] * wl, axis=1)) ** 2
    fL = np.fft.rfftfreq(NL, 1 / sr)
    # short causal window ending at the frame end (lead presence / transients)
    NS = 1024
    ws = np.hanning(NS)
    ends = (np.arange(n_frames) + 1) * hop + pad
    idxS = (ends[:, None] - NS + np.arange(NS)[None, :]).astype(np.int64)
    specS = np.abs(np.fft.rfft(xp[idxS] * ws, axis=1)) ** 2
    fS = np.fft.rfftfreq(NS, 1 / sr)

    fr = mono[: n_frames * hop].reshape(n_frames, hop)
    rms = np.sqrt((fr ** 2).mean(axis=1))
    rms_n = np.clip(rms / np.percentile(rms, 99.9), 0, 1)

    sub = logn(band_power(specL, fL, 20, 90))
    lowm = logn(band_power(specL, fL, 150, 600))
    lead = logn(band_power(specS, fS, 1500, 4500))
    highs = logn(band_power(specL, fL, 6000, 16000))
    d = np.diff(lead, prepend=lead[0])
    att = np.maximum(d, 0)
    att = np.clip(att / max(1e-9, np.percentile(att[att > 0], 99.5)), 0, 1)

    r4 = lambda a: [round(float(v), 4) for v in a]
    cols = {'rms': r4(rms_n), 'sub_bass': r4(sub), 'low_mids': r4(lowm), 'lead_presence': r4(lead), 'highs': r4(highs), 'attack_transient': r4(att)}
    frames = [{'i': i, 't': round(i / FPS, 5), **{k: cols[k][i] for k in cols}} for i in range(n_frames)]
    out = {
        'source': 'output/audio/clapton_master.wav', 'sample_rate': sr, 'fps': FPS, 'duration': duration, 'total_frames': n_frames,
        'bands_hz': {'sub_bass': [20, 90], 'low_mids': [150, 600], 'lead_presence': [1500, 4500], 'highs': [6000, 16000]},
        'normalization': 'rms: / p99.9; bands: 10log10(power) mapped from (p99.5-50 dB .. p99.5) to 0..1; attack: positive d(lead_presence)/dframe / p99.5',
        'frames': frames,
    }
    path = os.path.join(ROOT, 'output', 'telemetry.json')
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    with open(os.path.join(ROOT, 'output', 'telemetry.js'), 'w') as f:
        f.write('window.FILAMENT_TELEMETRY=')
        json.dump(out, f, separators=(',', ':'))
        f.write(';\n')
    chk = json.load(open(path))
    assert chk['total_frames'] == len(chk['frames']) == n_frames
    print(f'[telemetry] {n_frames} frames @ {FPS} fps, duration {duration:.4f} s -> output/telemetry.json ({os.path.getsize(path) / 1e6:.1f} MB), parses cleanly')


if __name__ == '__main__':
    main()
