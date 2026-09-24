#!/usr/bin/env node
// Inspection: render stills at chosen times (seconds) or at the default key moments.
//   node scripts/preview.mjs [t1 t2 ...]
// Writes output/preview/f<frame>_<label>.png (downscaled contact sheet via ffmpeg too).
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import puppeteer from 'puppeteer';
import { startServer, ROOT } from './serve.mjs';

const OUT = path.join(ROOT, 'output', 'preview');
fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) fs.unlinkSync(path.join(OUT, f));
const ev = JSON.parse(fs.readFileSync(path.join(ROOT, 'output', 'events.json'), 'utf8'));
const sec = Object.fromEntries(ev.sections.map(s => [s.id, s]));
const bar = (b, p = 0) => ev.bars[b].t0 + (ev.bars[b].t1 - ev.bars[b].t0) * p / 12;
const DEFAULT = [
  ['intro-sigh', bar(0, 7.5)], ['verse1-call', bar(4, 3.5)], ['verse1-cry', bar(10, 1.2)], ['chorus1', bar(12, 3)],
  ['chorus1-high', bar(16, 1)], ['verse2', bar(22, 1)], ['chorus2', bar(30, 3)], ['break', bar(35, 4)],
  ['solo-open', bar(36, 4)], ['solo-mid', bar(44, 1)], ['summit', bar(50, 3)], ['stop-bend', bar(51, 8)],
  ['ignition', bar(52, 0.5)], ['final', bar(55, 0)], ['outro', bar(61, 6)], ['last-note', bar(63, 3)], ['end', ev.meta.duration - 0.6]
];
const times = process.argv.length > 2 ? process.argv.slice(2).map((v, i) => ['t' + i, Number(v)]) : DEFAULT;

const { server, port } = await startServer({});
const browser = await puppeteer.launch({ headless: 'new', protocolTimeout: 0, args: ['--enable-gpu', '--use-gl=angle', '--use-angle=d3d11', '--headless=new', '--ignore-gpu-blocklist'] });
try {
  const page = await browser.newPage();
  const errs = []; page.on('pageerror', e => errs.push(String(e))); page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto(`http://127.0.0.1:${port}/render/index.html`);
  await page.waitForFunction('window.ready === true || window.initError', { timeout: 120000 });
  const initErr = await page.evaluate(() => window.initError);
  if (initErr) throw new Error(initErr);
  console.log('[preview] renderer:', await page.evaluate(() => window.renderer));
  const files = [];
  for (const [label, t] of times) {
    const fr = Math.round(t * 60);
    const t0 = Date.now();
    const b64 = await page.evaluate(i => window.renderFrame(i), fr);
    const ms = Date.now() - t0;
    const st = await page.evaluate(tt => window.visualStateAt(tt), fr / 60);
    const f = path.join(OUT, `f${String(fr).padStart(5, '0')}_${label}.png`);
    fs.writeFileSync(f, Buffer.from(b64, 'base64')); files.push(f);
    console.log(`[preview] ${label.padEnd(14)} t=${(fr / 60).toFixed(2).padStart(7)} ${st.section.padEnd(8)} bar ${st.bar} notes ${st.notes.length} ${ms} ms`);
  }
  if (errs.length) console.log('[preview] page errors:', errs);
  // contact sheet
  const list = path.join(OUT, 'list.txt');
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  files.forEach(f => args.push('-i', f));
  const cols = 4, rows = Math.ceil(files.length / cols);
  let filt = files.map((f, i) => `[${i}:v]scale=480:270[s${i}]`).join(';') + ';';
  const blanks = cols * rows - files.length;
  for (let i = 0; i < blanks; i++) filt += `color=black:s=480x270:d=1[b${i}];`;
  const ins = files.map((f, i) => `[s${i}]`).join('') + Array.from({ length: blanks }, (_, i) => `[b${i}]`).join('');
  const layout = Array.from({ length: cols * rows }, (_, i) => `${(i % cols) * 480}_${Math.floor(i / cols) * 270}`).join('|');
  filt += `${ins}xstack=inputs=${cols * rows}:layout=${layout}[out]`;
  args.push('-filter_complex', filt, '-map', '[out]', '-frames:v', '1', path.join(OUT, 'contact_sheet.png'));
  const r = spawnSync('ffmpeg', args, { encoding: 'utf8' });
  if (r.status !== 0) console.log(r.stderr); else console.log('[preview] contact sheet: output/preview/contact_sheet.png');
} finally { await browser.close(); server.close(); }
