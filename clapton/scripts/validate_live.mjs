#!/usr/bin/env node
// FILAMENT — live player validation (real-time AudioContext in headless Chromium).
// Exercises the actual user paths: click-to-start gesture, Space pause/resume, restart button,
// a full uninterrupted run to the ending, file:// launch, console errors, network requests.
//   node scripts/validate_live.mjs [--quick]      (--quick skips the full 3:39 run)
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import puppeteer from 'puppeteer';
import { startServer, ROOT } from './serve.mjs';

const quick = process.argv.includes('--quick');
const results = [];
const check = (name, pass, measured) => { results.push({ name, pass: !!pass, measured }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}  —  ${measured}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const { server, port } = await startServer({});
const browser = await puppeteer.launch({ headless: 'new', protocolTimeout: 0, args: ['--headless=new', '--enable-gpu', '--use-gl=angle', '--use-angle=d3d11', '--ignore-gpu-blocklist'] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  const errors = [], requests = new Set();
  page.on('pageerror', e => errors.push('pageerror: ' + e));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
  page.on('request', r => requests.add(r.url().replace(`http://127.0.0.1:${port}`, '')));
  await page.goto(`http://127.0.0.1:${port}/index.html`, { waitUntil: 'load' });
  await page.waitForFunction('window.FILAMENT_PLAYER');
  const P = () => page.evaluate(() => ({ state: FILAMENT_PLAYER.state(), s: FILAMENT_PLAYER.songTime(), audio: FILAMENT_PLAYER.audioState(), posted: { ...FILAMENT_PLAYER.posted } }));
  let p = await P();
  check('before the gesture: idle, no AudioContext', p.state === 'idle' && p.audio === 'none', JSON.stringify({ state: p.state, audio: p.audio }));
  await page.click('#veil');
  await page.waitForFunction(() => FILAMENT_PLAYER.state() === 'playing', { timeout: 20000 });
  p = await P();
  check('click gesture starts audio (AudioContext running)', p.audio === 'running', `state ${p.state}, audio ${p.audio}`);
  await sleep(4000);
  const a = await P();
  check('audio clock advances in real time', a.s > 3.3 && a.s < 4.2, `song time ${a.s.toFixed(3)} s after 4.0 s wall`);
  await page.keyboard.press('Space'); await sleep(200);
  const b = await P(); await sleep(2000); const c = await P();
  check('pause (Space): audio suspended and song time frozen', b.state === 'paused' && b.audio === 'suspended' && Math.abs(c.s - b.s) < 1e-6, `state ${b.state}/${b.audio}, Δ over 2 s = ${((c.s - b.s) * 1000).toFixed(3)} ms`);
  const camB = await page.evaluate(s => JSON.stringify(FILAMENT_PLAYER.visualState(s).camera), c.s);
  const camC = await page.evaluate(() => JSON.stringify(FILAMENT_PLAYER.visualState(FILAMENT_PLAYER.songTime()).camera));
  check('picture frozen while paused (camera state identical)', camB === camC, 'visual state is f(song time)');
  await page.keyboard.press('Space'); await sleep(2000);
  const d = await P();
  check('resume (Space): continues from the paused position', d.state === 'playing' && d.s - c.s > 1.7 && d.s - c.s < 2.3, `advanced ${(d.s - c.s).toFixed(3)} s in 2.0 s wall`);
  check('scheduler never posted an event late', d.posted.late === 0, `late=${d.posted.late}, posted lead ${d.posted.lead} / rhythm ${d.posted.rhythm} / bass ${d.posted.bass} / native ${d.posted.native}`);
  await page.click('#rs');
  await page.waitForFunction(() => FILAMENT_PLAYER.state() === 'playing', { timeout: 20000 });
  const e = await P();
  check('restart returns to the beginning', e.s < 0.6 && e.audio === 'running', `song time ${e.s.toFixed(3)} s`);
  const t1 = await P(); await sleep(2000); const t2 = await P();
  const rate = (t2.posted.ticks - t1.posted.ticks) / 2;
  check('exactly one scheduler after restart (no leaked intervals)', rate > 15 && rate < 30, `${rate.toFixed(1)} ticks/s (interval = 40 ms)`);
  // rapid input: double Space and double R must leave state and AudioContext in agreement
  await page.keyboard.press('Space'); await page.keyboard.press('Space');
  await page.evaluate(() => FILAMENT_PLAYER.idle()); await sleep(300);
  const r1 = await P();
  check('rapid double Space: state and AudioContext agree', r1.state === 'playing' && r1.audio === 'running', `state ${r1.state}, audio ${r1.audio}`);
  await page.keyboard.press('KeyR'); await page.keyboard.press('KeyR');
  await page.evaluate(() => FILAMENT_PLAYER.idle()); await sleep(300);
  const r2 = await P(); await sleep(2000); const r3 = await P();
  const rate2 = (r3.posted.ticks - r2.posted.ticks) / 2;
  check('rapid double restart: one context, one scheduler, from the top', r2.state === 'playing' && r2.audio === 'running' && r2.s < 1.0 && rate2 > 15 && rate2 < 30, `song time ${r2.s.toFixed(2)} s, ${rate2.toFixed(1)} ticks/s`);
  if (!quick) {
    const END = await page.evaluate(() => FilamentScore.meta.duration);
    const seen = new Map(); let waveSeen = false, maxLate = 0;
    const tStart = Date.now();
    for (;;) {
      const q = await page.evaluate(() => { const s = FILAMENT_PLAYER.songTime(), v = FILAMENT_PLAYER.visualState(s); return { state: FILAMENT_PLAYER.state(), s, sec: v.section, wave: v.wave[2], late: FILAMENT_PLAYER.posted.late }; });
      if (!seen.has(q.sec)) seen.set(q.sec, q.s);
      if (q.wave) waveSeen = true;
      maxLate = Math.max(maxLate, q.late);
      if (q.state === 'ended') break;
      if (Date.now() - tStart > (END + 30) * 1000) break;
      await sleep(1000);
    }
    const f = await P();
    const order = [...seen.keys()];
    check('every formal section is reached, in order', order.join('>') === 'intro>verse1>chorus1>verse2>chorus2>solo>final>outro', order.map(k => `${k}@${seen.get(k).toFixed(1)}s`).join(' '));
    check('the climax ignition occurs', waveSeen, 'ignition wave observed in the live picture');
    check('the work ends intentionally: scheduler stopped, context closed, final time held', f.state === 'ended' && f.audio === 'none' && Math.abs(f.s - END) < 1e-6, `state ${f.state}, audio ${f.audio}, song time ${f.s.toFixed(3)} / ${END.toFixed(3)} s`);
    await sleep(1500);
    const g = await P();
    check('no activity after the end (no runaway timers)', g.posted.ticks === f.posted.ticks, `ticks ${f.posted.ticks} → ${g.posted.ticks}`);
    check('no late events across the whole run', maxLate === 0, `late=${maxLate}`);
  }
  const net = [...requests];
  const bad = net.filter(u => !/^\/(index\.html|src\/(engine|composition|visual)\.js|output\/telemetry\.js|favicon\.ico)$/.test(u));
  check('only local code loaded; no media, no network beyond localhost files', bad.length === 0, net.join(', '));
  check('no console errors or unhandled exceptions', errors.length === 0, errors.length ? errors.slice(0, 5).join(' | ') : 'clean');

  // file:// launch (no server at all)
  const fp = await browser.newPage();
  const fErr = []; fp.on('pageerror', e => fErr.push(String(e))); fp.on('console', m => { if (m.type() === 'error') fErr.push(m.text()); });
  await fp.goto(pathToFileURL(path.join(ROOT, 'index.html')).href, { waitUntil: 'load' });
  await fp.waitForFunction('window.FILAMENT_PLAYER');
  await fp.click('#veil');
  await fp.waitForFunction(() => FILAMENT_PLAYER.state() === 'playing', { timeout: 20000 });
  await sleep(1500);
  const fs1 = await fp.evaluate(() => ({ s: FILAMENT_PLAYER.songTime(), a: FILAMENT_PLAYER.audioState() }));
  check('also runs from file:// (double-click index.html)', fs1.a === 'running' && fs1.s > 0.8 && fErr.length === 0, `song time ${fs1.s.toFixed(2)} s, errors ${fErr.length}`);
} finally { await browser.close(); server.close(); }
const failed = results.filter(r => !r.pass);
fs.writeFileSync(path.join(ROOT, 'output', 'live_report.json'), JSON.stringify({ when: new Date().toISOString(), quick, passed: results.length - failed.length, failed: failed.length, results }, null, 1));
console.log(`\n${results.length - failed.length}/${results.length} live checks passed`);
process.exit(failed.length ? 1 : 0);
