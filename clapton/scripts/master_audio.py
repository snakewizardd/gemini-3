"""FILAMENT mastering: String Engine float render -> -14 LUFS, <= -1 dBTP, 24-bit PCM stereo.

Loudness follows ITU-R BS.1770-4 (K-weighting, 400 ms blocks, absolute + relative gating).
True peak is measured with 4x polyphase oversampling. The limiter is a look-ahead
gain computer driven by the oversampled peak envelope, so inter-sample peaks are controlled.
Deterministic: TPDF dither uses a fixed-seed generator.
"""
import argparse
import json
import os

import numpy as np
from scipy.signal import lfilter, resample_poly, oaconvolve
from scipy.ndimage import minimum_filter1d
from scipy.io import wavfile

TARGET_LUFS = -14.0
CEILING_DBTP = -1.5          # margin below the -1 dBTP requirement


def k_weight(x, sr):
    assert sr == 48000, "K-weighting coefficients are for 48 kHz"
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)


def integrated_lufs(x, sr):
    y = k_weight(x, sr)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    n = 1 + (len(y) - blk) // hop
    idx = np.arange(n) * hop
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    ms = (cs[idx + blk] - cs[idx]) / blk                    # mean square per channel per block
    z = ms.sum(axis=1)
    lk = -0.691 + 10 * np.log10(np.maximum(z, 1e-12))
    g = lk > -70
    rel = -0.691 + 10 * np.log10(z[g].mean()) - 10
    g2 = g & (lk > rel)
    return -0.691 + 10 * np.log10(z[g2].mean())


def true_peak_db(x):
    up = resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def limit(x, sr, ceiling_db):
    """Look-ahead true-peak limiter (vectorised).
    need[n]  = gain that keeps every 4x-oversampled sample under the ceiling.
    m        = sliding minimum of need over W  (look-ahead + hold)
    gain     = m smoothed by a Hann kernel of half-width <= W/2, which guarantees gain <= need.
    """
    ceil = 10 ** (ceiling_db / 20)
    up = np.abs(resample_poly(x, 4, 1, axis=0)).max(axis=1)
    up = np.pad(up, (0, max(0, len(x) * 4 - len(up))), constant_values=0)[: len(x) * 4]
    need = np.minimum(1.0, ceil / np.maximum(up, 1e-9)).reshape(len(x), 4).min(axis=1)
    half = int(0.008 * sr)                                   # 8 ms each side
    m = minimum_filter1d(need, size=2 * half + 1, mode='nearest')
    k = np.hanning(2 * half + 1)
    k /= k.sum()
    gain = np.minimum(oaconvolve(m, k, mode='same'), m)
    limit.last_gain = gain
    return x * gain[:, None], float(20 * np.log10(gain.min()))


def write_wav24(path, x, sr):
    rng = np.random.default_rng(20260924)
    lsb = 1.0 / (2 ** 23)
    d = (rng.random(x.shape) - rng.random(x.shape)) * lsb    # TPDF dither
    q = np.clip(np.round((x + d) * (2 ** 23 - 1)), -(2 ** 23), 2 ** 23 - 1).astype(np.int32)
    b = q.astype('<i4').view(np.uint8).reshape(-1, 4)[:, :3].reshape(-1)
    ch = x.shape[1]
    with open(path, 'wb') as f:
        data_len = len(b)
        f.write(b'RIFF'); f.write((36 + data_len).to_bytes(4, 'little')); f.write(b'WAVE')
        f.write(b'fmt '); f.write((16).to_bytes(4, 'little')); f.write((1).to_bytes(2, 'little'))
        f.write(ch.to_bytes(2, 'little')); f.write(sr.to_bytes(4, 'little'))
        f.write((sr * ch * 3).to_bytes(4, 'little')); f.write((ch * 3).to_bytes(2, 'little')); f.write((24).to_bytes(2, 'little'))
        f.write(b'data'); f.write(data_len.to_bytes(4, 'little')); f.write(b.tobytes())
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--sr', type=int, default=48000)
    ap.add_argument('--out', required=True)
    ap.add_argument('--lead', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    sr = a.sr
    L = np.fromfile(os.path.join(a.inp, 'ch0.f32'), dtype='<f4').astype(np.float64)
    R = np.fromfile(os.path.join(a.inp, 'ch1.f32'), dtype='<f4').astype(np.float64)
    lead = np.fromfile(os.path.join(a.inp, 'ch2.f32'), dtype='<f4')
    x = np.stack([L, R], axis=1)
    x -= x.mean(axis=0)                                      # remove any DC
    raw_lufs = integrated_lufs(x, sr)
    raw_tp = true_peak_db(x)
    gain_db = TARGET_LUFS - raw_lufs
    y = x
    red = 0.0
    for it in range(6):
        y, red = limit(x * 10 ** (gain_db / 20), sr, CEILING_DBTP)
        lufs = integrated_lufs(y, sr)
        err = TARGET_LUFS - lufs
        if abs(err) < 0.05:
            break
        gain_db += err
    tp = true_peak_db(y)
    guard = 0
    while tp > CEILING_DBTP + 0.05 and guard < 4:            # tighten if the oversampled peak still pokes out
        y, red = limit(y, sr, CEILING_DBTP - 0.2 * (guard + 1))
        tp = true_peak_db(y)
        guard += 1
    q = write_wav24(a.out, y, sr)
    clipped = int(np.sum(np.abs(q) >= 2 ** 23 - 1))
    wavfile.write(a.lead, sr, (lead / max(1e-9, float(np.max(np.abs(lead)))) * 0.9).astype(np.float32))
    rep = {
        'sample_rate': sr, 'channels': 2, 'bits': 24, 'samples': int(len(y)), 'duration_s': len(y) / sr,
        'raw_lufs': round(float(raw_lufs), 3), 'raw_true_peak_dbtp': round(float(raw_tp), 3),
        'gain_db': round(float(gain_db), 3), 'max_gain_reduction_db': round(red, 3),
        'lufs_integrated': round(float(integrated_lufs(y, sr)), 3), 'true_peak_dbtp': round(float(tp), 3),
        'clipped_samples': clipped,
        'pct_time_gr_over_1db': round(float(np.mean(limit.last_gain < 10 ** (-1 / 20)) * 100), 3),
        'pct_time_gr_over_3db': round(float(np.mean(limit.last_gain < 10 ** (-3 / 20)) * 100), 3),
    }
    with open(a.report, 'w') as f:
        json.dump(rep, f, indent=2)
    print('[master]', json.dumps(rep))


if __name__ == '__main__':
    main()
