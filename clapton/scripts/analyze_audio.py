"""FILAMENT audio inspection (the ears I don't have): writes output/analysis/*.png + a JSON summary.

- short-term loudness (3 s, BS.1770 K-weighted) across the form, against the score's tension curve
- log spectrogram of the master
- dry-lead pitch track (YIN) vs. the score's intended pitch incl. bends / curls / vibrato,
  for a few signature phrases (intro sigh, verse call, the break, the climax bend)
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import lfilter, stft

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'output', 'analysis')
os.makedirs(OUT, exist_ok=True)


def read24(path):
    with open(path, 'rb') as f:
        b = f.read()
    i = b.index(b'data') + 8
    raw = np.frombuffer(b[i:], dtype=np.uint8).reshape(-1, 3)
    v = (raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8) | (raw[:, 2].astype(np.int32) << 16))
    v = np.where(v >= 2 ** 23, v - 2 ** 24, v)
    return (v / 2 ** 23).reshape(-1, 2)


def kw(x):
    x = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x, axis=0)
    return lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], x, axis=0)


def yin(x, sr, t0, t1, fmin=150, fmax=1300, hop=0.005, win=0.03):
    n0, n1 = int(t0 * sr), int(t1 * sr)
    W = int(win * sr)
    tmax = int(sr / fmin)
    ts, fs = [], []
    for c in range(n0, n1 - W - tmax, int(hop * sr)):
        seg = x[c:c + W + tmax].astype(np.float64)
        if np.sqrt(np.mean(seg[:W] ** 2)) < 0.01:
            ts.append(c / sr); fs.append(np.nan); continue
        d = np.array([np.sum((seg[:W] - seg[tau:tau + W]) ** 2) for tau in range(1, tmax)])
        cm = d * np.arange(1, tmax) / np.maximum(np.cumsum(d), 1e-12)
        lo = int(sr / fmax)
        idx = np.where(cm[lo:] < 0.15)[0]
        if not len(idx):
            ts.append(c / sr); fs.append(np.nan); continue
        k = idx[0] + lo
        while k + 1 < len(cm) and cm[k + 1] < cm[k]:
            k += 1
        if 0 < k < len(cm) - 1:
            a, b_, c_ = cm[k - 1], cm[k], cm[k + 1]
            k = k + 0.5 * (a - c_) / max(1e-12, a - 2 * b_ + c_)
        ts.append(c / sr); fs.append(sr / (k + 1))
    return np.array(ts), np.array(fs)


def ease(c, u):
    return u if c == 'lin' else (u * u * (3 - 2 * u) if c == 'smooth' else 1 - (1 - u) ** 2.2)


def intended(ev, t):
    """Mirror of the engine's pitch model: fretted pitch + bend stages + vibrato (cents)."""
    cents = np.zeros_like(t)
    frm = 0.0
    cur = np.zeros_like(t)
    for b in ev['bends']:
        u = np.clip((t - b['t0']) / max(1e-6, b['t1'] - b['t0']), 0, 1)
        seg = b['from'] + (b['to'] - b['from']) * np.vectorize(lambda z: ease(b['c'], z))(u)
        cur = np.where(t >= b['t0'], seg, cur)
    cents += cur
    v = ev.get('vib')
    if v:
        on = t >= v['t']
        dep = v['d'] * (1 - np.exp(-(t - v['t']) / max(0.005, v['k'])))
        ph = 2 * np.pi * v['r'] * (t - v['t'])
        osc = (0.5 - 0.5 * np.cos(ph)) if v['m'] != 'sym' else 0.5 * np.sin(ph)
        cents += np.where(on, dep * osc * 100, 0)
    return 440 * 2 ** ((ev['midi'] - 69 + cents / 100) / 12)


def main():
    ev = json.load(open(os.path.join(ROOT, 'output', 'events.json')))
    x = read24(os.path.join(ROOT, 'output', 'audio', 'clapton_master.wav'))
    sr = 48000
    lead_sr, lead = wavfile.read(os.path.join(ROOT, 'output', 'stems', 'lead_dry.wav'))
    y = kw(x)
    win, hop = 3 * sr, sr // 2
    cs = np.concatenate([[0], np.cumsum((y ** 2).sum(axis=1))])
    tt, st = [], []
    for c in range(0, len(y) - win, hop):
        ms = (cs[c + win] - cs[c]) / win
        tt.append((c + win / 2) / sr); st.append(-0.691 + 10 * np.log10(max(ms, 1e-12)))
    tt, st = np.array(tt), np.array(st)
    sec_stats = {}
    for s in ev['sections']:
        m = (tt >= s['t0']) & (tt < s['t1'])
        sec_stats[s['id']] = {'short_term_lufs_mean': round(float(st[m].mean()), 2), 'max': round(float(st[m].max()), 2)}

    fig, ax = plt.subplots(3, 1, figsize=(16, 11), gridspec_kw={'height_ratios': [1.1, 1.6, 0.8]})
    ax[0].plot(tt, st, color='#d08a2a', lw=1.4, label='short-term loudness (LUFS, 3 s)')
    bt = [(b['t0'] + b['t1']) / 2 for b in ev['bars']]
    ax2 = ax[0].twinx(); ax2.plot(bt, [b['tension'] for b in ev['bars']], color='#555', lw=1, ls='--', label='score tension'); ax2.set_ylim(0, 1.05)
    for s in ev['sections']:
        ax[0].axvline(s['t0'], color='#999', lw=0.6); ax[0].text(s['t0'] + 0.5, -40, s['id'], fontsize=8)
    ax[0].set_ylim(-42, -8); ax[0].set_xlim(0, ev['meta']['duration']); ax[0].legend(loc='upper left'); ax[0].set_title('FILAMENT — loudness arc vs. tension')
    f, t, Z = stft(x.mean(axis=1), fs=sr, nperseg=4096, noverlap=3072)
    S = 20 * np.log10(np.abs(Z) + 1e-9)
    ax[1].pcolormesh(t, f, S, vmin=-110, vmax=-20, cmap='magma', shading='auto'); ax[1].set_yscale('symlog', linthresh=200); ax[1].set_ylim(40, 16000)
    ax[1].set_title('master spectrogram')
    lt = np.arange(len(lead)) / lead_sr
    env = np.sqrt(np.convolve(lead.astype(np.float64) ** 2, np.ones(2400) / 2400, mode='same'))
    ax[2].plot(lt[::240], env[::240], color='#c33', lw=0.6); ax[2].set_xlim(0, ev['meta']['duration']); ax[2].set_title('dry lead envelope')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'overview.png'), dpi=80); plt.close()

    leads = [e for e in ev['events'] if e['inst'] == 'lead']
    windows = [('intro sigh', 2.6, 4.2), ('verse call', 15.3, 19.2), ('break (bar 35)', 117.9, 121.4), ('climax bend (bar 51)', 171.4, 177.0)]
    fig, axs = plt.subplots(len(windows), 1, figsize=(14, 3.2 * len(windows)))
    errs = []
    for a_, (name, t0, t1) in zip(axs, windows):
        ts, fs = yin(lead.astype(np.float64), lead_sr, t0, t1)
        a_.plot(ts, 1200 * np.log2(fs / 440), '.', ms=2.5, color='#c33', label='measured (YIN, dry lead)')
        for e in leads:
            if e['t'] + e['dur'] < t0 or e['t'] > t1:
                continue
            tq = np.linspace(e['t'], e['t'] + e['dur'], 200)
            a_.plot(tq, 1200 * np.log2(intended(e, tq) / 440), color='#333', lw=1)
            m = (ts > e['t'] + 0.06) & (ts < e['t'] + e['dur'] - 0.03) & np.isfinite(fs)
            if m.sum() > 3:
                d = 1200 * np.log2(fs[m] / intended(e, ts[m]))
                d = (d + 600) % 1200 - 600
                errs.append(float(np.median(np.abs(d))))
        a_.set_title(name); a_.set_ylabel('cents re A4'); a_.set_xlim(t0, t1)
    axs[0].legend()
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'pitch_track.png'), dpi=80); plt.close()
    summary = {'sections': sec_stats, 'pitch_median_abs_err_cents_per_note': [round(e, 1) for e in errs],
               'pitch_err_median_cents': round(float(np.median(errs)), 2) if errs else None}
    json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
    print(json.dumps(summary))


if __name__ == '__main__':
    sys.exit(main())
