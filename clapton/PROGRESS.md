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
  2.5 s lookahead (12 s when the tab is hidden); pause = `ctx.suspend()`; restart closes the context.

