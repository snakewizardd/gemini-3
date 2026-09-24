#!/usr/bin/env node
// FILAMENT — acceptance checks (Phase 5 + the acceptance spec). Prints a table and writes
// output/qa_report.json. Exit code 1 if any check fails.
//   node scripts/qa.mjs [--skip-audio-rerender]
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync, execFileSync } from 'node:child_process';
import puppeteer from 'puppeteer';
import { startServer, ROOT } from './serve.mjs';

process.chdir(ROOT);
const results = [];
const check = (name, pass, measured) => { results.push({ name, pass: !!pass, measured }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}  —  ${measured}`); };
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const probe = (f, extra = []) => JSON.parse(execFileSync('ffprobe', ['-v', 'error', ...extra, '-show_streams', '-show_format', '-of', 'json', f], { encoding: 'utf8', maxBuffer: 1 << 26 }));
const F = {
  master: 'output/audio/clapton_master.wav', song: 'output/song.wav', mp4: 'output/final_render.mp4', final: 'output/final.mp4',
  events: 'output/events.json', telemetry: 'output/telemetry.json', lead: 'output/stems/lead_dry.wav'
};

// 1 — files
for (const k of ['master', 'song', 'mp4', 'final', 'events', 'telemetry']) check(`exists & non-empty: ${F[k]}`, fs.existsSync(F[k]) && fs.statSync(F[k]).size > 0, fs.existsSync(F[k]) ? (fs.statSync(F[k]).size / 1048576).toFixed(2) + ' MiB' : 'missing');
const masterSha = sha(F.master);
check('song.wav is byte-identical to clapton_master.wav', masterSha === sha(F.song), 'sha256 ' + masterSha.slice(0, 16) + '…');
check('final.mp4 is byte-identical to final_render.mp4', sha(F.mp4) === sha(F.final), 'sha256 ' + sha(F.mp4).slice(0, 16) + '…');
JSON.parse(fs.readFileSync(F.telemetry, 'utf8'));
const ev = JSON.parse(fs.readFileSync(F.events, 'utf8'));

// 2 — formats & durations
const pw = probe(F.song), aw = pw.streams[0];
check('master format 48 kHz / 24-bit PCM / stereo', aw.sample_rate === '48000' && aw.codec_name === 'pcm_s24le' && aw.channels === 2, `${aw.codec_name} ${aw.sample_rate} Hz ${aw.channels} ch`);
const wavDur = Number(aw.duration);
check('song duration within 3:15–3:45', wavDur >= 195 && wavDur <= 225, `${wavDur.toFixed(3)} s (${Math.floor(wavDur / 60)}:${(wavDur % 60).toFixed(2).padStart(5, '0')})`);
const pm = probe(F.mp4, ['-count_packets']);
const vs = pm.streams.find(s => s.codec_type === 'video'), as = pm.streams.find(s => s.codec_type === 'audio');
const vDur = Number(vs.duration), aDur = Number(as.duration), mp4Dur = Number(pm.format.duration);
check('video stream: H.264 1920×1080 yuv420p', vs.codec_name === 'h264' && vs.width === 1920 && vs.height === 1080 && vs.pix_fmt === 'yuv420p', `${vs.codec_name} ${vs.width}x${vs.height} ${vs.pix_fmt}`);
check('solid 60.0 fps (r_frame_rate = avg_frame_rate = 60/1)', vs.r_frame_rate === '60/1' && vs.avg_frame_rate === '60/1', `r=${vs.r_frame_rate} avg=${vs.avg_frame_rate}`);
check('mp4 audio vs video stream duration delta < 0.05 s', Math.abs(vDur - aDur) < 0.05, `video ${vDur.toFixed(4)} s, audio ${aDur.toFixed(4)} s, Δ ${(Math.abs(vDur - aDur) * 1000).toFixed(1)} ms`);
check('song.wav vs final.mp4 duration delta < 50 ms', Math.abs(wavDur - mp4Dur) < 0.05, `wav ${wavDur.toFixed(4)} s, mp4 ${mp4Dur.toFixed(4)} s, Δ ${(Math.abs(wavDur - mp4Dur) * 1000).toFixed(1)} ms`);
const nFrames = Number(vs.nb_read_packets || vs.nb_frames);
check('video frame count = duration × 60 (±1)', Math.abs(nFrames - wavDur * 60) <= 1, `${nFrames} frames vs ${(wavDur * 60).toFixed(2)} expected`);
check('stream start times aligned', Number(vs.start_time) === 0 && Math.abs(Number(as.start_time)) < 0.001, `video ${vs.start_time}, audio ${as.start_time}`);

// 3 — loudness (ffmpeg ebur128 with true peak) + loudnorm second opinion + clipping
const eb = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', F.song, '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
const summary = eb.slice(eb.lastIndexOf('Summary:'));
const I = Number(/I:\s+(-?[\d.]+) LUFS/.exec(summary)[1]);
const TP = Number(/True peak:\s+Peak:\s+(-?[\d.]+) dBFS/.exec(summary)[1]);
const LRA = Number(/LRA:\s+(-?[\d.]+) LU/.exec(summary)[1]);
check('integrated loudness −14 LUFS ±1 (ffmpeg ebur128)', Math.abs(I + 14) <= 1, `${I} LUFS (LRA ${LRA} LU)`);
check('true peak ≤ −1 dBTP (ffmpeg ebur128 peak=true)', TP <= -1, `${TP} dBTP`);
const ln = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', F.song, '-af', 'loudnorm=I=-14:TP=-1:print_format=json', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
const lj = JSON.parse(ln.slice(ln.lastIndexOf('{'), ln.lastIndexOf('}') + 1));
check('loudnorm measurement agrees (−14 ±1 LUFS, ≤ −1 dBTP)', Math.abs(Number(lj.input_i) + 14) <= 1 && Number(lj.input_tp) <= -1, `input_i ${lj.input_i} LUFS, input_tp ${lj.input_tp} dBTP`);
{
  const b = fs.readFileSync(F.song); const d = b.indexOf('data') + 8; let clip = 0, peak = 0;
  for (let i = d; i + 2 < b.length; i += 3) { let v = b[i] | (b[i + 1] << 8) | (b[i + 2] << 16); if (v & 0x800000) v -= 0x1000000; const a = Math.abs(v); if (a > peak) peak = a; if (v >= 8388607 || v <= -8388608) clip++; }
  check('no clipped samples', clip === 0, `${clip} full-scale samples; sample peak ${(20 * Math.log10(peak / 8388608)).toFixed(2)} dBFS`);
}

// 4 — renderer determinism, visual onset sync, runtime asset audit
const { server, port } = await startServer({});
const telemetry = JSON.parse(fs.readFileSync(F.telemetry, 'utf8'));
const leads = ev.events.filter(e => e.inst === 'lead');
let seed = 20260924; const rnd = () => ((seed = (seed * 1103515245 + 12345) >>> 0) / 4294967296);
const pick = Array.from({ length: 5 }, () => Math.floor(rnd() * telemetry.total_frames)).sort((a, b) => a - b);
const requests = new Set();
async function session(fn) {
  const browser = await puppeteer.launch({ headless: 'new', protocolTimeout: 0, args: ['--enable-gpu', '--use-gl=angle', '--headless=new', '--use-angle=d3d11', '--ignore-gpu-blocklist'] });
  try {
    const page = await browser.newPage();
    page.on('request', r => requests.add(r.url().replace(`http://127.0.0.1:${port}`, '')));
    await page.setViewport({ width: 1920, height: 1080 });
    await page.goto(`http://127.0.0.1:${port}/render/index.html`);
    await page.waitForFunction('window.ready === true || window.initError', { timeout: 120000 });
    return await fn(page);
  } finally { await browser.close(); }
}
const pass1 = await session(p => p.evaluate(fr => fr.map(i => [window.renderFrameHash(i), window.renderFrame(i).length]), pick));
const pass2 = await session(p => p.evaluate(fr => fr.map(i => [window.renderFrameHash(i), window.renderFrame(i).length]), pick));
const same = pass1.every((h, i) => h[0] === pass2[i][0] && h[1] === pass2[i][1]);
check('determinism: 5 random frames rendered twice (separate browser launches) are pixel-identical', same, pick.map((f, i) => `#${f}:${pass1[i][0]}${pass1[i][0] === pass2[i][0] ? '=' : '≠' + pass2[i][0]}`).join(' '));
const sync = await session(p => p.evaluate(notes => {
  const res = [];
  for (const n of notes) {
    const f = Math.ceil(n.t * 60 - 1e-9);
    const has = fr => window.visualStateAt(fr / 60).notes.some(x => x.id === n.id);
    let first = -1; for (let k = f - 2; k <= f + 3; k++) if (has(k)) { first = k; break; }
    res.push({ id: n.id, onset: n.t, first, dt: first < 0 ? null : first / 60 - n.t });
  }
  return res;
}, leads.map(n => ({ id: n.id, t: n.t }))));
const bad = sync.filter(r => r.dt === null || r.dt < -1e-9 || r.dt > 1 / 60 + 1e-9);
const maxDt = Math.max(...sync.map(r => r.dt ?? 1));
check('sync: every lead onset appears in the picture within one frame (≤ 16.7 ms)', bad.length === 0, `${sync.length - bad.length}/${sync.length} notes, max lag ${(maxDt * 1000).toFixed(2)} ms`);
server.close();

// audio-side: the dry lead stem's transients vs events.json pick onsets
{
  const b = fs.readFileSync(F.lead);
  const dpos = b.indexOf('data') + 8, fmtTag = b.readUInt16LE(20), sr = b.readUInt32LE(24);
  const x = fmtTag === 3 ? new Float32Array(b.buffer.slice(b.byteOffset + dpos, b.byteOffset + dpos + Math.floor((b.length - dpos) / 4) * 4)) : null;
  const errs = [];
  for (const n of leads.filter(n => n.art === 'pick')) {
    const c = Math.round(n.t * sr), a = c - Math.round(0.012 * sr), z = c + Math.round(0.03 * sr);
    let mx = 0; const d = [];
    for (let i = a; i < z; i++) { const v = Math.abs(x[i] - x[i - 1]); d.push(v); if (v > mx) mx = v; }
    let base = 0; for (let i = a - Math.round(0.02 * sr); i < a; i++) base = Math.max(base, Math.abs(x[i] - x[i - 1]));
    if (mx < base * 1.5) continue;                                  // masked by a louder ringing note: skip
    const k = d.findIndex(v => v > Math.max(base * 1.2, mx * 0.35));
    errs.push((a + k) / sr - n.t);
  }
  const within = errs.filter(e => Math.abs(e) <= 1 / 60).length;
  const med = errs.map(Math.abs).sort((p, q) => p - q)[Math.floor(errs.length / 2)];
  check('sync: audio transients of the dry lead match events.json pick onsets within 16.7 ms', within === errs.length, `${within}/${errs.length} detected picks, median |Δ| ${(med * 1000).toFixed(2)} ms, max |Δ| ${(Math.max(...errs.map(Math.abs)) * 1000).toFixed(2)} ms`);
}

// 5 — assets & randomness
const allowed = /^\/(render\/index\.html|src\/visual\.js|output\/(events|telemetry)\.json|favicon\.ico)$/;
const unexpected = [...requests].filter(u => !allowed.test(u));
check('renderer loaded no external image/audio files (runtime request audit)', unexpected.length === 0, [...requests].join(', '));
const codeFiles = ['src/engine.js', 'src/composition.js', 'src/visual.js', 'render/index.html', 'render/audio.html', 'index.html'];
const media = /\.(png|jpe?g|gif|webp|bmp|mp3|wav|ogg|flac|m4a|mp4|webm)\b|new\s+Image\s*\(|new\s+Audio\s*\(|<img|<audio|<video|decodeAudioData|createImageBitmap/i;
const hits = codeFiles.filter(f => fs.readFileSync(f, 'utf8').split('\n').some(l => media.test(l.replace(/\/\/.*$/, ''))));
check('no media references in composition/engine/renderer source (static scan)', hits.length === 0, hits.length ? hits.join(', ') : codeFiles.length + ' files clean');
const mr = codeFiles.filter(f => /Math\.random\s*\(/.test(fs.readFileSync(f, 'utf8')));
check('seeded randomness only: no Math.random() in engine/score/renderer', mr.length === 0, mr.length ? mr.join(', ') : 'mulberry32 / hash-based only');

// 6 — optional: the String Engine render itself is bit-reproducible
if (!process.argv.includes('--skip-audio-rerender')) {
  fs.copyFileSync(F.master, 'output/audio/_qa_prev.wav');
  const r = spawnSync('node', ['scripts/render_audio.mjs'], { encoding: 'utf8' });
  const again = sha(F.master);
  fs.copyFileSync('output/audio/_qa_prev.wav', F.master); fs.unlinkSync('output/audio/_qa_prev.wav');
  check('determinism: re-rendering the String Engine master reproduces it bit-for-bit', r.status === 0 && again === masterSha, `sha256 ${again.slice(0, 16)}… ${again === masterSha ? '==' : '!='} ${masterSha.slice(0, 16)}…`);
}

// 7 — repo state
const branch = execFileSync('git', ['branch', '--show-current'], { encoding: 'utf8' }).trim();
check('work is on branch oneshot-clapton', branch === 'oneshot-clapton', branch);

const failed = results.filter(r => !r.pass);
fs.writeFileSync('output/qa_report.json', JSON.stringify({ when: new Date().toISOString(), passed: results.length - failed.length, failed: failed.length, results }, null, 1));
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
const st = fs.statSync(F.mp4);
console.log(`FINAL: ${path.resolve(F.mp4)}  ${(st.size / 1048576).toFixed(1)} MiB  ${vs.width}x${vs.height} @ 60 fps  ${mp4Dur.toFixed(3)} s`);
process.exit(failed.length ? 1 : 0);
