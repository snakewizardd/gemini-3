#!/usr/bin/env node
// Inspection only: renders the lead alone and the band alone through the same engine/graph,
// then reports per-section loudness balance and the master's spectral balance.
//   node scripts/inspect_mix.mjs
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer';
import { startServer, ROOT } from './serve.mjs';

const TMP = path.join(ROOT, 'output', 'analysis', 'stems');
fs.mkdirSync(TMP, { recursive: true });
const { server, port } = await startServer({ uploadDir: TMP });
const browser = await puppeteer.launch({ headless: 'new', protocolTimeout: 0, args: ['--headless=new'] });
try {
  for (const [prefix, mute] of [['lead_', ['rhythm', 'bass', 'drums', 'organ']], ['band_', ['lead']]]) {
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${port}/render/audio.html`);
    await page.waitForFunction('window.ready === true');
    const r = await page.evaluate((prefix, mute) => window.renderAudio({ prefix, mute }), prefix, mute);
    console.log('[mix]', prefix, (r.ms / 1000).toFixed(1) + ' s');
    await page.close();
  }
} finally { await browser.close(); server.close(); }

const py = String.raw`
import json, os, sys
import numpy as np
from scipy.signal import lfilter, welch
root, tmp = sys.argv[1], sys.argv[2]
ev = json.load(open(os.path.join(root, 'output', 'events.json')))
rep = json.load(open(os.path.join(root, 'output', 'audio', 'master_report.json')))
g = 10 ** (rep['gain_db'] / 20)
def load(p):
    return np.stack([np.fromfile(os.path.join(tmp, p + 'ch0.f32'), '<f4'), np.fromfile(os.path.join(tmp, p + 'ch1.f32'), '<f4')], 1).astype(np.float64) * g
def kw(x):
    x = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x, axis=0)
    return lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], x, axis=0)
def lufs(x):
    z = (kw(x) ** 2).sum(1)
    return -0.691 + 10 * np.log10(max(z.mean(), 1e-12))
L, B = load('lead_'), load('band_')
out = {}
for s in ev['sections']:
    a, b = int(s['t0'] * 48000), int(s['t1'] * 48000)
    out[s['id']] = {'lead_LUFS': round(lufs(L[a:b]), 1), 'band_LUFS': round(lufs(B[a:b]), 1), 'lead_minus_band_LU': round(lufs(L[a:b]) - lufs(B[a:b]), 1)}
f, P = welch((L + B).mean(1), fs=48000, nperseg=8192)
bands = {'sub 20-90': (20, 90), 'low 90-250': (90, 250), 'lowmid 250-800': (250, 800), 'mid 800-2.5k': (800, 2500), 'pres 2.5-6k': (2500, 6000), 'air 6-16k': (6000, 16000)}
bal = {k: round(10 * np.log10(P[(f >= lo) & (f < hi)].sum() + 1e-20), 1) for k, (lo, hi) in bands.items()}
ref = bal['mid 800-2.5k']
print(json.dumps({'balance_by_section': out, 'band_energy_dB_rel_mid': {k: round(v - ref, 1) for k, v in bal.items()}}, indent=1))
`;
const res = spawnSync('python', ['-c', py, ROOT, TMP], { encoding: 'utf8' });
process.stdout.write(res.stdout); process.stderr.write(res.stderr);
for (const f of fs.readdirSync(TMP)) fs.unlinkSync(path.join(TMP, f));
fs.rmdirSync(TMP);
