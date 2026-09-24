# FILAMENT

*An original blues-rock ballad in A minor (solo in D Dorian), 3:39, composed and synthesized
entirely by the String Engine, with a raymarched film in which every pixel is computed.*

The inside of a tube amplifier at night: an obsidian mirror-floor, a grid of vacuum tubes, six
strings of liquid metal. The lead guitar is a voice that sighs, is answered, climbs, stops in
silence, bends a note into the tonic — and the whole machine ignites. Then it cools, tube by
tube, back to the first one, and goes dark on the last note.

- **Entry point (interactive):** [`index.html`](index.html) — click to start; Space pause/resume; R or *restart*.
- **Finished film:** `output/final_render.mp4` (= `output/final.mp4`), 1920×1080, 60 fps, H.264 + AAC 320k.
- **Master:** `output/audio/clapton_master.wav` (= `output/song.wav`), 48 kHz / 24-bit / stereo, −14.0 LUFS, −1.5 dBTP.
- Documents: [`score.md`](score.md) · [`storyboard.md`](storyboard.md) · [`PROGRESS.md`](PROGRESS.md) (full log + check results).

## Run it

Requirements: Node ≥ 20, Python 3 with numpy + scipy (+ matplotlib for the optional analysis),
ffmpeg/ffprobe on PATH, a WebGL2 GPU. Everything runs offline.

```powershell
cd clapton
npm install                    # puppeteer (+ Chrome for Testing). If Chrome is missing:
npx puppeteer browsers install chrome
```

**Watch/listen live** (the String Engine plays the score in real time; the WAV is never loaded):

```powershell
node scripts/serve.mjs         # then open http://127.0.0.1:8765/
# or simply double-click index.html (file:// works too)
```

**Rebuild every artefact from scratch** (deterministic; the master is bit-identical on every run):

```powershell
node scripts/render_audio.mjs        # Phase 1: String Engine → output/audio/clapton_master.wav, output/song.wav, output/events.json
python scripts/extract_telemetry.py  # Phase 2: → output/telemetry.json (+ telemetry.js for the live player)
node render.mjs                      # Phase 4: headless capture → FFmpeg → output/final_render.mp4 (+ output/final.mp4)
                                     #          (same as: node scripts/render_video.js)
node scripts/qa.mjs                  # Phase 5: every acceptance check → output/qa_report.json
node scripts/validate_live.mjs       # live transport validation (plays the whole piece in real time)
```

Optional inspection tools: `python scripts/analyze_audio.py` (loudness arc, spectrogram, YIN pitch
track vs. the score's bend curves), `node scripts/inspect_mix.mjs` (lead vs. band balance),
`node scripts/preview.mjs [t …]` (stills + contact sheet).

## How it is built

| Layer | File | Notes |
|---|---|---|
| Score | `src/composition.js` | the composition as code; motifs X/Y/Z; performance → engine commands + `events.json` |
| String Engine (extended) | `src/engine.js` | Karplus–Strong worklet (from `opus/hendrix.html`) + seeded PRNG, T60 loss-compensated loop gain, shaped bends, delayed up/sym vibrato, pickup comb, pick click; FDN hall; fixed-order mixer (bit-exact) |
| Offline render CLI | `scripts/render_audio.mjs`, `render/audio.html`, `scripts/master_audio.py` | OfflineAudioContext in headless Chromium → BS.1770 loudness + 4× oversampled true-peak limiter → 24-bit |
| Telemetry | `scripts/extract_telemetry.py` | rms, 20–90 Hz, 150–600 Hz, 1.5–4.5 kHz, 6–16 kHz, attack transient per 1/60 s |
| Picture | `src/visual.js` | pure `draw(gl, t)`: SDF raymarcher (fBM + domain repetition) + post pass (CA on transients, grain, ACES) |
| Capture harness | `render/index.html` | `window.renderFrame(i)` → base64 PNG of frame *i* at *t = i/60* |
| Capture + mux | `render.mjs` | Puppeteer (`--enable-gpu --use-gl=angle --headless=new`) → `ffmpeg -f image2pipe … -crf 17 …` |
| Live player | `index.html` | audio clock authoritative, 40 ms interval / 2.5 s lookahead scheduler, pure picture |

Seeds: score performance `0x0C1A9707`; engine noise derived from the same seed per instrument;
visual grain is a hash of pixel × frame (no PRNG state). No `Math.random()` anywhere.
