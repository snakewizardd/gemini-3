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
