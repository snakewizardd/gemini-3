#!/usr/bin/env node
// FILAMENT — deterministic headless capture + FFmpeg mux.
// Every frame is drawn at the exact time t = frame / 60 by the pure draw(gl, t) in render/index.html,
// captured as PNG and piped straight into FFmpeg's stdin together with the String Engine master.
//
//   node render.mjs                       full film → output/final_render.mp4 (+ copy output/final.mp4)
//   node render.mjs --workers 3           parallel capture pages (output is identical; frames are pure)
//   node render.mjs --frames 0:600 --out output/test.mp4     partial render (inspection)
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';
import { startServer } from './scripts/serve.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
process.chdir(ROOT);
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const WORKERS = Math.max(1, Number(arg('--workers', 3)));
const OUT = arg('--out', 'output/final_render.mp4');
const telemetry = JSON.parse(fs.readFileSync('output/telemetry.json', 'utf8'));
const events = JSON.parse(fs.readFileSync('output/events.json', 'utf8'));
const TOTAL = telemetry.total_frames;
const [F0, F1] = (arg('--frames', `0:${TOTAL}`)).split(':').map(Number);
const partial = F0 !== 0 || F1 !== TOTAL;
if (!fs.existsSync('output/audio/clapton_master.wav')) throw new Error('missing output/audio/clapton_master.wav — run: node scripts/render_audio.mjs');

const log = (...a) => console.log('[video]', ...a);
const { server, port } = await startServer({});
const browser = await puppeteer.launch({
  headless: 'new', protocolTimeout: 0,
  args: ['--enable-gpu', '--use-gl=angle', '--headless=new', '--use-angle=d3d11', '--ignore-gpu-blocklist', '--disable-background-timer-throttling']
});
const requests = new Set();
let ff;
try {
  const pages = [];
  for (let w = 0; w < WORKERS; w++) {
    const page = await browser.newPage();
    page.on('pageerror', e => { throw new Error('page error: ' + e); });
    page.on('request', r => requests.add(r.url().replace(`http://127.0.0.1:${port}`, '')));
    await page.setViewport({ width: 1920, height: 1080 });
    // inject telemetry + events before any page script runs
    await page.evaluateOnNewDocument((ev, tel) => { window.FILAMENT_INJECT = { events: ev, telemetry: tel }; }, events, telemetry);
    await page.goto(`http://127.0.0.1:${port}/render/index.html`, { waitUntil: 'load' });
    await page.waitForFunction('window.ready === true || window.initError', { timeout: 120000 });
    const err = await page.evaluate(() => window.initError);
    if (err) throw new Error(err);
    pages.push(page);
  }
  log('renderer:', await pages[0].evaluate(() => window.renderer));
  log(`frames ${F0}..${F1 - 1} of ${TOTAL} @ ${telemetry.fps} fps, ${WORKERS} capture page(s) → ${OUT}`);

  const ffArgs = ['-y', '-f', 'image2pipe', '-vcodec', 'png', '-r', '60', '-i', '-'];
  if (partial) ffArgs.push('-ss', (F0 / 60).toFixed(6), '-t', ((F1 - F0) / 60).toFixed(6));
  ffArgs.push('-i', 'output/audio/clapton_master.wav', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '320k', OUT);
  log('ffmpeg', ffArgs.join(' '));
  ff = spawn('ffmpeg', ffArgs, { stdio: ['pipe', 'ignore', 'pipe'] });
  let ffErr = '';
  ff.stderr.on('data', d => { ffErr = (ffErr + d).slice(-4000); });
  const ffDone = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exited ' + c + '\n' + ffErr))));
  const write = buf => new Promise((res, rej) => { if (ff.stdin.write(buf)) res(); else ff.stdin.once('drain', res); ff.stdin.once('error', rej); });

  const t0 = Date.now();
  const inflight = new Map();
  const request = i => pages[(i - F0) % WORKERS].evaluate(k => window.renderFrame(k), i).then(b64 => Buffer.from(b64, 'base64'));
  let next = F0;
  const LOOKAHEAD = WORKERS * 2;
  while (next < F1 && inflight.size < LOOKAHEAD) { inflight.set(next, request(next)); next++; }
  for (let i = F0; i < F1; i++) {
    const png = await inflight.get(i); inflight.delete(i);
    if (next < F1) { inflight.set(next, request(next)); next++; }
    await write(png);
    const done = i - F0 + 1;
    if (done % 300 === 0 || i === F1 - 1) {
      const el = (Date.now() - t0) / 1000, fps = done / el;
      log(`frame ${i + 1}/${F1} (${(100 * done / (F1 - F0)).toFixed(1)}%)  ${fps.toFixed(2)} fps  eta ${((F1 - F0 - done) / fps / 60).toFixed(1)} min`);
    }
  }
  ff.stdin.end();
  await ffDone;
  log(`encoded ${OUT} in ${((Date.now() - t0) / 60000).toFixed(1)} min`);
  if (!partial && path.resolve(OUT) === path.resolve('output/final_render.mp4')) {
    fs.copyFileSync('output/final_render.mp4', 'output/final.mp4');
    log('copied → output/final.mp4');
  }
  const external = [...requests].filter(u => !/^\/(render\/index\.html|src\/visual\.js|favicon\.ico)$/.test(u));
  log('requests made by the renderer:', [...requests].join(', '), external.length ? ' UNEXPECTED: ' + external.join(', ') : '(all local code, no media)');
} finally {
  if (ff && ff.exitCode === null && !ff.stdin.writableEnded) ff.stdin.end();
  await browser.close();
  server.close();
}
