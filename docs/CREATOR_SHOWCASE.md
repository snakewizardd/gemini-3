# Creator Showcase and Engine

This repository already contains the proof that you create your own music.

The strongest public-facing sentence is:

`I build systems that generate music, tone, and visuals from mathematics, then I turn those systems into songs, performances, and videos.`

## The Files That Best Prove It

### 1. `opus/romance.html`
This is the cleanest "I create my own music" file in the repo. It is musical first, legible to a normal listener, and rooted in your actual synthesis language instead of borrowed assets.

Why it works:
- Romantic and human on first contact
- Procedural synthesis, not sample playback
- Strong enough to share without needing a long explanation

### 2. `second/golden_hour_song.html`
This is your best bridge into "date-safe" work. It keeps your authorship, but it is warm, cinematic, and emotionally accessible.

Why it works:
- Immediate emotional readability
- Piano, pad, and visual language fit a personal dedication
- Already structured like a narrative rather than a tech demo

### 3. `second/wonderful_tonight.html`
This is useful because it proves you can do restraint. It is not only about intensity or abstraction. It shows you can shape tenderness and space.

Why it works:
- Acoustic fingerstyle framing
- Familiar emotional register
- Good reference for a softer custom piece

### 4. `second/gemini_guitar_opus.html`
This is one of the strongest "engine" files in the archive. It reads as a self-composing guitar system rather than a fixed composition.

Why it works:
- Explicit theory, chord, and scale model
- Real-time generative behavior
- Strong visual identity without losing the music core

### 5. `second/metal_guitar_engine.html`
This is the loud proof of authorship. If someone doubts that the repo contains genuine instrument design and composition logic, this file answers that directly.

Why it works:
- Full instrument/tone pipeline
- Tab-style compositional structure
- Clear relationship between theory, synthesis, and visualization

### 6. `opus/lilypond.html`
This is the "serious craft" artifact. It shows scale, patience, and compositional ambition.

Why it works:
- Large-form construction
- Multi-voice logic
- Strong evidence that the repo contains more than sketches

### 7. `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`
This is the canonical proof that your music work is not accidental. It documents the engine logic behind the sound.

Why it works:
- Makes the repo legible to technical people
- Shows repeatable method, not one-off luck
- Connects tone recipes to implementation

### 8. `whatami/README.md`
This is the artist statement. It explains your worldview clearly enough that other people can understand what the code is trying to become.

### 9. `tests/test_string_engine.py`
This matters more than it looks. It proves the engine has fundamentals, not just vibes.

Why it works:
- Oscillators, envelopes, filters, and Karplus-Strong are treated as testable primitives
- Lets you say the music engine is formalized enough to validate

## If You Want One Shareable Stack

If you want the shortest set of files to show someone, use this:

1. `opus/romance.html`
2. `second/golden_hour_song.html`
3. `second/gemini_guitar_opus.html`
4. `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`

That stack says:
- I can compose
- I can design sound
- I can build the engine
- I can make something beautiful instead of only experimental

## Two Lanes You Already Have

### Signature Lane
Use this when you want to front your ideaship and show that the work is truly yours.

Anchor files:
- `second/gemini_guitar_opus.html`
- `second/metal_guitar_engine.html`
- `opus/lilypond.html`
- `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`

Traits:
- More mathematical
- More authored and strange
- Better for "this is my system"

### Intimate Lane
Use this when the goal is a personal piece for someone specific, including a future proposal or early romantic gift.

Anchor files:
- `opus/romance.html`
- `second/golden_hour_song.html`
- `second/wonderful_tonight.html`
- `opus/evening.html`

Traits:
- More immediate
- More emotionally legible
- Better for "I made this for you"

### Techno Lane
Use this when the goal is altered-state propulsion: body pressure, sub-bass authority, and a spiritual or ritual atmosphere.

Anchor files:
- `opus/temple_of_e.html`
- `second/housebeat.html`
- `opus/annihilate.html`
- `second/sensorium.html`
- `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`

Traits:
- Bass first
- Hypnotic repetition with controlled evolution
- Better for consciousness-inducing tracks and stem-reactive visuals

Direct artifact:
- `opus/temple_of_e.html` is the built E Aeolian consciousness-engine piece: bass-dominant techno with synchronized sacred-geometry visuals.

## What Was Missing

The repo already had compositions, engines, theory, and visuals.

What it did not have was a small repeatable bridge from:

`person + occasion + key + mood + visual palette`

to:

`music brief + Suno prompt + visualizer handoff + delivery note`

That bridge now lives in `python/creator_engine.py`.

## Engine Workflow

1. Pick a lane: `signature`, `romantic`, `cinematic`, `playful`, or `techno`.
2. Decide how much of your weirdness to front with `--signature-level low|medium|high`.
3. Generate a brief locally with `python/creator_engine.py`.
4. Feed the generated Suno prompt into your external Copilot Studio or Suno workflow.
5. Use the generated visual brief as the handoff for your stem-driven visualizer pipeline.
6. Deliver the final piece as a song, video, or both.

## Example Commands

Proposal-leaning, warm, accessible:

```bash
python python/creator_engine.py --profile romantic --recipient "Her Name" --occasion proposal --key Db --mode major --tempo 84 --motif "golden hour over water" --visual-seed "amber, rose, ivory" --signature-level medium
```

More authored, still intimate:

```bash
python python/creator_engine.py --profile romantic --recipient "Her Name" --occasion first-gift --key E --mode dorian --tempo 92 --motif "city lights and after-midnight honesty" --visual-seed "cyan, gold, midnight blue" --signature-level high
```

Pure ideaship:

```bash
python python/creator_engine.py --profile signature --occasion portfolio --key E --mode dorian --tempo 110 --motif "self-composing electric prayer" --visual-seed "cyan, magenta, gold" --signature-level high
```

Bass-first techno:

```bash
python python/creator_engine.py --profile techno --occasion consciousness-state --key E --mode aeolian --tempo 132 --motif "ritual thump, spiritual submersion, consciousness induction" --visual-seed "obsidian, cyan, molten gold" --signature-level high
```

## How To Talk About It

If you want a plain sentence for other people:

`I do not just prompt songs. I build the theory, synthesis logic, visual systems, and creative workflow that let me author songs and music videos in my own way.`

If you want the softer version:

`I make original music by designing the musical system first, then I turn it into songs and visual pieces for specific people and moments.`
