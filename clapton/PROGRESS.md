# FILAMENT — production log

Branch: `oneshot-clapton`. Project root: `clapton/` (isolated; no existing work modified).

## 0. Harmonization of the three directives

Three instructions were supplied (the chat directive "Phases 1–5", the pasted
"oneshot-clapton" spec, and the attached one-shot authorship commission). They
conflict in places; this is how each conflict was resolved into ONE work:

| Conflict | Resolution |
|---|---|
| Key: D minor/Dorian vs A minor | Home key **A minor** (verses, choruses, outro). The **solo modulates to D Dorian** (pivot A7♯9) and returns via E7♯9, so both are honoured and the modulation *is* the climax's harmonic pressure. |
| Visuals: raymarched GLSL SDF vs "pure `draw(ctx,t)`, p5/canvas" vs "no shader reel / no generic visualizer" | One **pure `draw(gl, t)`** function (ctx = WebGL2 context). All pixels come from a raymarched SDF world (fBM + domain repetition: a vacuum-tube matrix with liquid-metal strings). No 2D canvas primitives. Scene is authored per section, driven by note events. |
| Visual drivers: spectral telemetry uniforms vs note events | Both: `u_rms, u_sub_bass, u_lead_transients, u_highs, u_attack_transient` come from `telemetry.json`; pitch/bend/vibrato/onset/section/tension come from `events.json`. |
| File names (`clapton_master.wav`/`song.wav`, `final_render.mp4`/`final.mp4`, `render_video.js`/`render.mjs`) | Canonical files use the Phase names; the pasted-spec names are byte-identical copies / a shim, so every checker path exists. |
| Offline capture vs interactive transport (play/pause/restart) | Same engine + score + `draw` power both: `render/index.html` (deterministic capture harness) and `index.html` (live player, audio clock authoritative). |
| "No audio files loaded" vs live playback | The live player never loads the WAV; it runs the String Engine in real time from the same score. |
| 48 kHz / 24-bit master vs −14 LUFS / ≤ −1 dBTP | Offline render at 48 kHz float → mastering (gain + 4× oversampled true-peak limiter) → 24-bit PCM stereo. |

## 1. Environment (verified)

- Node v22.17.1, npm 10.9.2, Python 3.13 + numpy 2.3.5 + scipy 1.16.3
- ffmpeg/ffprobe 7.1.1 (libx264, aac available)
- Puppeteer 25.12.0 + Chrome for Testing 154.0.8037.57 (installed into `clapton/node_modules` + user cache)
- Headless WebGL2 renderer: `ANGLE (NVIDIA GeForce RTX 5060 Direct3D11)`; `EXT_color_buffer_float` present
- OfflineAudioContext + AudioWorklet (4 channels) confirmed working in headless Chrome over `http://127.0.0.1` (secure context required; `about:blank` fails → local server `scripts/serve.mjs`).

## 2. The String Engine (as found in the repo)

There is no AGENT.md and no CLI entrypoint in the repo; the String Engine is a
browser (Web Audio) framework documented in `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`
and realised most completely in `opus/hendrix.html` (the known-good reference):

- **Voices**: AudioWorklet Karplus–Strong string model (`strat-string`), 8 voices,
  fractional (cubic Lagrange) delay line, two-point loss filter (`S`), loop gain `g`,
  in-loop soft clip.
- **Articulations**: `pluck` (noise excitation, brightness `b`, pluck-position comb `p`),
  `legato` (hammer/pull: glide + small re-excitation), `bend` (log-period glide over `d` s),
  `damp` (loop-gain change = palm/finger mute), `vib` (depth/rate with smoothed onset).
- **Dynamics**: excitation amplitude + brightness per pick.
- **Effects**: WaveShaper fuzz / tanh amp, bandpass wah + LFO, cab EQ biquads, tape echo
  with saturated feedback, convolver room (noise impulse), stereo auto-pan, compressor + limiter,
  synthesized drums (oscillator/noise), amp→string feedback loop.
- **Render/export**: none — real-time only (click-to-start, `setInterval` lookahead scheduler).
- Randomness: `Math.random()` everywhere (non-reproducible).

Decision: build FILAMENT on a copy-and-extend of this worklet (`clapton/src/engine.js`),
leaving `opus/hendrix.html` untouched, and add the missing CLI (`scripts/render_audio.mjs`)
that runs the engine in headless Chromium through an OfflineAudioContext.

## 3. Log

- Created branch `oneshot-clapton`; scaffolded `clapton/` with `package.json`; installed puppeteer.
- First probe of AudioWorklet on `about:blank` failed (`audioWorklet` undefined → not a secure
  context). Fixed by serving over `http://127.0.0.1` with `scripts/serve.mjs`.
- Puppeteer 25 needed `npx puppeteer browsers install chrome` (Chrome for Testing 154).
- **Engine** (`src/engine.js`): copied the hendrix KS worklet and extended it (seeded PRNG, T60 gain,
  triangle+comb excitation, pick click, shaped glides, up/sym vibrato with phase reset, pickup comb,
  events via `processorOptions` or port). Graph: neck/middle pickup blend → tone knob → tube preamp
  (asymmetric tanh) → tone stack → power tube → cab; rhythm + bass strings; drawbar organ + Leslie;
  synthesized drums; echo + hall; glue compressor.
- **Score** (`src/composition.js`): 64 bars, motifs X/Y/Z/cry, 256 lead notes, 97 bend stages,
  73 vibratos; accompaniment that thins under lead onsets; tone automation arc; deterministic
  humanization. Duration 218.95 s (3:38.95).
- **Failure → fix: offline render timed out** (>180 s CDP timeout). Profiling in 10 s chunks showed
  0.12× real time, i.e. the cost was superlinear: every drum/organ node had been created up front and
  Chrome processes pending nodes every quantum. Fix: feed native commands progressively through
  `OfflineAudioContext.suspend()` with a 4 s lookahead (the same model as the live scheduler).
  Result: 219 s rendered in ~24 s.
- **Failure → fix: renders not bit-identical** (ch0 peak differed in the 7th digit). Bisection:
  the worklets were exact; divergence appeared ~5 ms after the first note. Root cause: Chromium sums
  a node's fan-in in hash-set (pointer) order, so ≥ 3 simultaneous non-zero sources round
  differently per run (2 are commutative). Replaced the ConvolverNode by a deterministic FDN hall
  worklet, routed every multi-source mix through a fixed-order `filament-mix` worklet, made each
  organ note one PeriodicWave oscillator, and gave each drum hit its own ≤2-input bus in a
  round-robin mixer slot. Result: three renders with identical FNV hashes; full master sha256 stable.
- **Tooling mistake → fix:** PowerShell 5.1 `Get-Content/Set-Content` round-trips double-encoded
  UTF-8 in files I patched; repaired byte-exactly (cp1252 → utf-8 reversal) and switched all later
  edits to Python / the edit tool.
- **Mastering** (`scripts/master_audio.py`): BS.1770-4 K-weighting + gating, 4× polyphase
  true-peak look-ahead limiter (vectorised min-filter + Hann smoothing, guarantees gain ≤ need),
  TPDF dither with fixed seed, hand-written 24-bit WAV. −14.00 LUFS / −1.50 dBTP / 0 clipped;
  limiter active on 0.019 % of samples.
- **Listening without ears** (`scripts/analyze_audio.py`): YIN pitch track of the dry lead stem vs.
  the score's intended pitch (bend stages + vibrato): median error 0.14 c — the +200 c sigh, the
  +30 c curls and the two-stage G→G♯→A climax bend are played exactly. Found: held notes decayed
  too fast → T60 now compensates the loop's two-point loss at the fundamental and scales with the
  written length (climax note T60 = 14 s).
- **Mix** (`scripts/inspect_mix.mjs`, lead-only and band-only renders): first pass had only
  1.6 LU verse→chorus contrast, +6 dB sub and −12 dB presence. Rebalanced (leaner kick/bass lows,
  brighter cabs, bus tilt EQ, quieter verse band, per-section lead level). Now band −18.5 (verse) →
  −15.7 LUFS (chorus); lead +2.6 LU over the band in the solo; presence −9.4 dB, sub +3.1 dB re mids
  (deliberately warm: neck-pickup ballad).
- **Telemetry** (`scripts/extract_telemetry.py`): 13 137 frames, parses cleanly.
- **Visuals** (`src/visual.js`), iterated through four reviewed contact sheets:
  1. first render: milky glass (halo inside every tube), brown fog, flat orange plates, strings as
     flat beams → glass became a fresnel event per shell crossing, filament core + warm in-scatter,
     near-black fog, mottled red-plating, specular-only strings;
  2. closed box plates hid the filaments; strings 4× too thick; molten halo accumulated into
     "god rays"; verse/chorus cameras were inside tube columns → two side plates + mica, strings
     with a 1-px minimum radius, narrow halos, cameras moved into aisles;
  3. strings read black from 0.3 units away → verse cameras raised, strings reflect the lit field
     (`u_field`);
  4. obsidian relief too strong (water-like) → softened.
  Motion check of the climax as a 2 fps filmstrip: summit → stop-time darkness with one white strike
  on the dragged string → ignition wave → crane up. ~110 ms/frame single page; 3 capture pages ≈ 24 fps.
- **Live player** (`index.html`): real-time String Engine from the same score; 40 ms interval,
  2.5 s lookahead (20 s when the tab is hidden); pause = `ctx.suspend()`; restart closes the context.


- **Review ? fixes (live transport).** A rubber-duck review of `index.html` found races between
  Space/restart/visibility handlers and the scheduler. Fixes: one serialized action queue
  (`FILAMENT_PLAYER.idle()`), each start owns its own AudioContext (stale ticks from a closed
  context are ignored), the complete string score is posted to the worklets at start (so a
  throttled tab can never starve the lead), native commands already in the past are dropped, a
  ConstantSource sentinel's `onended` ends the piece, and the engine revokes its worklet blob URL.
- **QA run 1: 27/28.** Visual onset check failed on 4 notes (max lag 16.75 ms > 16.7 ms): a note
  starting just after a frame boundary only became visible one frame + ? later. Fix in
  `src/visual.js`: the lead envelope's attack starts at 0.5 with a 2 ms ramp, and `activeLeads`
  includes notes younger than 0.1 s. Re-rendered the whole film (13 137 frames, ~9.5 min).
- **QA run 2: 28/28.** Live validation (full length, real time): 19/19.
- **Sustain result:** the climax bend G5 ? G?5 ? A5 is now tracked by YIN for ~3 s (it was < 1 s
  before the T60 fix). Section short-term loudness: intro ?22.3, verse 1 ?16.75, chorus 1 ?14.05,
  verse 2 ?15.47, chorus 2 ?13.6, solo ?13.04, final chorus ?13.48, outro ?20.43 LUFS.

---

## Final summary

### What was built
**FILAMENT**, an original 3:38.95 blues-rock ballad in a Clapton-inspired idiom (A minor, 72 BPM,
12/8; the solo moves to D Dorian). Form: intro ? verse ? chorus ? verse ? chorus ? solo ? final
chorus ? outro. Every sample comes from the repository's String Engine (Karplus?Strong
AudioWorklets), extended in `src/engine.js` with seeded excitation, pick attacks, bend glide curves,
up/symmetric vibrato, pickup-position comb filtering, tube saturation, cabinets, an FDN hall and
fixed-order mixers. No samples, no loops, no external audio.
The film is a raymarched GLSL SDF world (WebGL2, pure `draw(gl, t)`): a vacuum-tube matrix
(fBM plate mottling, domain repetition) above six liquid-metal strings, driven by `events.json`
(pitch, velocity, onset, duration, bend, vibrato) and `telemetry.json`. One scene per section, with
transitions on section boundaries. The final film is `output/final_render.mp4` (= `output/final.mp4`),
1920?1080, 60 fps, H.264 + AAC 320k, 388.8 MiB. `index.html` is a live, interactive version (it
synthesizes and draws in real time).

### Acceptance checks (`node scripts/qa.mjs` ? `output/qa_report.json`: 28 / 28 pass)
| Check | Measured |
|---|---|
| clapton_master.wav / song.wav exist, byte-identical | 60.14 MiB, sha256 77ee88cfac60c9a8? |
| final_render.mp4 / final.mp4 exist, byte-identical | 388.83 MiB, sha256 fe8ad0529ba64b90? |
| events.json / telemetry.json exist, parse | 0.28 MiB / 1.66 MiB |
| master format | pcm_s24le, 48 000 Hz, 2 ch |
| duration 3:15?3:45 | 218.950 s (3:38.95) |
| video stream | h264 1920?1080 yuv420p |
| solid 60 fps | r_frame_rate = avg_frame_rate = 60/1 |
| mp4 audio vs video duration < 0.05 s | 218.9500 vs 218.9500 s, ? 0.0 ms |
| song.wav vs final.mp4 < 50 ms | ? 0.0 ms |
| frame count = duration ? 60 (?1) | 13 137 vs 13 137.00 |
| stream start times | video 0.000000, audio 0.000000 |
| integrated loudness ?14 ?1 LUFS (ebur128) | ?14.0 LUFS, LRA 5.9 LU |
| true peak ? ?1 dBTP (ebur128) | ?1.5 dBTP |
| loudnorm cross-check | ?14.04 LUFS, ?1.47 dBTP |
| no clipped samples | 0 full-scale samples; sample peak ?1.51 dBFS |
| frame determinism (5 random frames, 2 browser launches) | #836 #4081 #9918 #12571 #12780 identical |
| visual onset sync ? 16.7 ms | 256 / 256 notes, max lag 16.65 ms |
| audio transient sync ? 16.7 ms | 173 / 173 picks, median 0.02 ms, max 0.21 ms |
| no external media loaded (runtime request audit) | only html/js/json |
| no media references in source (static scan) | 6 files clean |
| no Math.random() | mulberry32 / hash-based only |
| audio re-render is bit-exact | sha256 identical |
| branch | oneshot-clapton |

### Live checks (`node scripts/validate_live.mjs` ? `output/live_report.json`: 19 / 19 pass)
Idle until gesture; click starts audio; clock advances in real time (3.681 s in 4.0 s wall); pause
freezes audio and picture (? 0.000 ms over 2 s); resume continues (2.019 s in 2.0 s); 0 late events;
restart returns to 0; one scheduler (25.0 ticks/s); rapid double Space and double restart stay
consistent; all sections reached in order (intro 2.0 s ? outro 201.5 s); climax ignition observed;
intentional end (context closed, time held at 218.950 s); no activity after end; only local code
loaded; no console errors; also runs from `file://`.

### Re-render from scratch (PowerShell, from the repo root)
```
cd clapton
npm install
npx puppeteer browsers install chrome
node scripts/render_audio.mjs          # String Engine ? master ? output/audio/clapton_master.wav, song.wav, events.json, stems
python scripts/extract_telemetry.py    # ? output/telemetry.json (+ telemetry.js for the live page)
node render.mjs                        # or: node scripts/render_video.js ? output/final_render.mp4 + final.mp4
node scripts/qa.mjs                    # 28 acceptance checks
node scripts/validate_live.mjs         # 19 live-player checks (add --quick for a short run)
```
Python needs numpy and scipy; ffmpeg/ffprobe must be on PATH.

### Known limitations
- The mix is deliberately warm and dark (presence ?9.4 dB relative to the mids, neck-pickup ballad).
- The live page raymarches at 62 % resolution and upscales, to hold real time on consumer GPUs.
  The offline film is full 1080p.
- In a hidden tab the native (drum/organ) lookahead is 20 s. Strings are fully pre-queued, but a tab
  hidden for longer than timers are throttled could delay native parts.
- The WAV/MP4 masters are gitignored (large, regenerable). Their sha256 hashes are recorded above
  and in `output/qa_report.json`.
