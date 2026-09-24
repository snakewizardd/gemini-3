#!/usr/bin/env node
// FILAMENT — String Engine CLI.
// Runs the String Engine (src/engine.js) on the score (src/composition.js) inside headless
// Chromium via an OfflineAudioContext (48 kHz float, sample-deterministic), then masters to
// −14 LUFS / ≤ −1 dBTP and writes 24-bit PCM stereo.
//
//   node scripts/render_audio.mjs
//
// Outputs:
//   output/audio/clapton_master.wav   48 kHz · 24-bit PCM · stereo (canonical master)
//   output/song.wav                   identical copy (acceptance-spec name)
//   output/events.json                every note event with timestamps, bends, vibrato
//   output/stems/lead_dry.wav         dry lead string (QA: onset sync)
//   output/audio/master_report.json   loudness / true-peak / gain report
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer';
import { startServer, ROOT } from './serve.mjs';

const OUT = path.join(ROOT, 'output');
const TMP = path.join(OUT, 'tmp');
for (const d of [OUT, TMP, path.join(OUT, 'audio'), path.join(OUT, 'stems')]) fs.mkdirSync(d, { recursive: true });

const log = (...a) => console.log('[audio]', ...a);
const { server, port } = await startServer({ uploadDir: TMP });
const browser = await puppeteer.launch({
  headless: 'new',
  protocolTimeout: 0,
  args: ['--headless=new', '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling']
});
let meta;
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${port}/render/audio.html`, { waitUntil: 'load' });
  await page.waitForFunction('window.ready === true');
  meta = await page.evaluate(() => window.FilamentScore.meta);
  const events = await page.evaluate(() => ({
    meta: window.FilamentScore.meta, sections: window.FilamentScore.sections, bars: window.FilamentScore.bars, events: window.FilamentScore.events
  }));
  fs.writeFileSync(path.join(OUT, 'events.json'), JSON.stringify(events));
  log(`score: ${events.events.length} events, duration ${meta.duration.toFixed(3)} s, ${meta.frames} frames @ ${meta.fps} fps`);
  log('rendering through the String Engine (OfflineAudioContext, 48 kHz)...');
  page.setDefaultTimeout(0);
  const res = await page.evaluate(() => window.renderAudio());
  log(`rendered ${res.length} samples in ${(res.ms / 1000).toFixed(1)} s`, JSON.stringify(res.stats));
  if (errors.length) throw new Error('page errors: ' + errors.join(' | '));
  if (res.stats.some(s => s.nan > 0)) throw new Error('NaN samples in render');
} finally {
  await browser.close();
  server.close();
}

log('mastering...');
const py = spawnSync('python', [path.join(ROOT, 'scripts', 'master_audio.py'),
  '--in', TMP, '--sr', String(meta.sampleRate), '--out', path.join(OUT, 'audio', 'clapton_master.wav'),
  '--lead', path.join(OUT, 'stems', 'lead_dry.wav'), '--report', path.join(OUT, 'audio', 'master_report.json')], { stdio: 'inherit' });
if (py.status !== 0) throw new Error('mastering failed');
fs.copyFileSync(path.join(OUT, 'audio', 'clapton_master.wav'), path.join(OUT, 'song.wav'));
for (const f of fs.readdirSync(TMP)) fs.unlinkSync(path.join(TMP, f));
fs.rmdirSync(TMP);
const st = fs.statSync(path.join(OUT, 'audio', 'clapton_master.wav'));
if (!st.size) throw new Error('master is empty');
log(`wrote output/audio/clapton_master.wav (${(st.size / 1048576).toFixed(1)} MiB) and output/song.wav`);
