# Python Folder Index

The `python/` folder contains synthesis scripts and utilities that generate **procedural audio** via WAV file creation, demonstrating the String Engine framework implemented in pure Python DSP. Complements the HTML5 real-time synthesis in `opus/` with offline rendering capabilities.

## Files Overview

### 🔧 Synthesis Scripts (Python)

| File | Type | Description | Size | Purpose |
|------|------|-------------|------|---------|
| **[creator_engine.py](creator_engine.py)** | Python | Local brief generator that turns recipient, occasion, key, mode, and palette into a Suno prompt plus visualizer handoff | ~250 lines | Repeatable creator workflow bridge |
| **[attempt.py](attempt.py)** | Python | Full DSP pipeline: Karplus-Strong string synthesis, distortion, cabinet filtering, delay, reverb mastering. Metal guitar tone with 170 BPM fast tempo | 260 lines | High-gain metal synthesis engine |
| **[dragonfire.py](dragonfire.py)** | Python | Dragon-themed composition script with aggressive harmonics, extreme filtering, and dynamic parameter evolution over time | ~280 lines | Cinematic/aggressive synthesis |
| **[cyber_entry.py](cyber_entry.py)** | Python | Cyberpunk/industrial aesthetic synthesis with harsh timbres, rapid envelope modulation, and synchronized effects processing | ~250 lines | Cyber/industrial audio generation |
| **[voodoo.py](voodoo.py)** | Python | Mystical/occult aesthetic synthesis featuring unusual harmonic relationships, phase distortion, and ritualistic timing patterns | ~270 lines | Mystical/experimental audio |
| **[under_a_glass_moon.py](under_a_glass_moon.py)** | Python | Epic orchestral-scale synthesis with layered strings, pads, and complex timing relationships; generates long-form composition | ~300 lines | Orchestral/epic composition |
| **[gr.py](gr.py)** | Python | Guitar reflex synthesis demonstrating Karplus-Strong variations, finger picking patterns, and realistic plucking dynamics | ~240 lines | Guitar-specific synthesis |

### 🎵 Generated Audio Outputs (WAV Files)

| File | Duration | Source | Characteristics |
|------|----------|--------|-----------------|
| **guitar_universe.wav** | Variable | `attempt.py` output | High-gain metal guitar with spatial effects |
| **high_iq_solo.html.wav** | Variable | Synthesis output | Intelligent/melodic guitar solo |
| **under_a_glass_moon_intro.wav** | Variable | `under_a_glass_moon.py` intro | Epic orchestral introduction |
| **welcome_to_the_jungle.wav** | Variable | Synthesis output | Rhythmic/percussive composition |
| **voodoo_blues_universe.wav** | Variable | `voodoo.py` output | Blues-influenced mystical audio |

### 📦 Model & Utilities

| File | Type | Description | Size | Purpose |
|------|------|-------------|------|---------|
| **yolov8n.pt** | ML Model | YOLOv8 Nano object detection model (280MB+) | ~280MB | Potential ML inference utility (not currently used in audio) |

## Technical Architecture

### DSP Pipeline (All Scripts)

Each Python script implements this standard signal processing chain:

```
1. OSCILLATOR GENERATION
   └─ Base frequency selection (guitar strings: E2-E4)
   └─ Karplus-Strong delay-line feedback
   └─ Envelope shaping (ADSR)

2. DISTORTION STAGE
   └─ Input gain multiplier (50-200x for metal tone)
   └─ Soft clipping or aggressive saturation
   └─ Harmonic enrichment

3. FILTERING
   └─ Low-pass cabinet filter (4-6kHz cutoff)
   └─ Resonance/Q peak for presence

4. TIME EFFECTS
   └─ Delay (0.25-0.5s feedback loop)
   └─ Reverb convolution or algorithmic

5. MASTERING
   └─ Compression limiting
   └─ Final gain staging (0.6-0.8)
   └─ WAV export at 44.1kHz 16-bit

```

### Standard Tuning

```python
STRINGS = {
    'E2': 82.41,    # Low E string
    'A2': 110.00,   # A
    'D3': 146.83,   # D
    'G3': 196.00,   # G
    'B3': 246.94,   # B
    'E4': 329.63    # High E string
}
```

## Usage Patterns

### Running a Synthesis Script

```bash
python creator_engine.py    # Generates a shareable music/video brief
python attempt.py           # Generates WAV file with metal guitar tone
python dragonfire.py        # Aggressive dragon-themed composition
python voodoo.py            # Mystical/experimental audio
```

**Output**:
- `creator_engine.py` prints a Markdown or JSON brief for external Suno/video workflows
- Synthesis scripts create `[script_name]_output.wav` in the same directory

### Key Configuration Parameters (All Scripts)

```python
CONFIG = {
    'SAMPLE_RATE': 44100,           # CD quality
    'BPM': 170,                     # Beats per minute
    'DISTORTION_GAIN': 50.0,        # Input multiplier
    'CAB_CUTOFF': 4000,             # Lowpass Hz
    'DELAY_TIME': 0.35,             # Seconds
    'DELAY_FEEDBACK': 0.4,          # 0.0-0.9
    'MASTER_VOL': 0.6               # Output level
}
```

## Comparative Aesthetics

| Script | Aesthetic | BPM | Gain | Cutoff | Character |
|--------|-----------|-----|------|--------|-----------|
| `attempt.py` | Metal/Aggressive | 170 | 50+ | 4kHz | High-energy shred |
| `dragonfire.py` | Cinematic/Intense | 140-160 | 75+ | 3.5kHz | Dangerous/explosive |
| `cyber_entry.py` | Industrial/Harsh | 180+ | 100+ | 2kHz | Dystopian/cold |
| `voodoo.py` | Mystical/Chaotic | 60-90 | 30 | 5kHz | Ritualistic/occult |
| `under_a_glass_moon.py` | Orchestral/Epic | 80 | 10-20 | 8kHz+ | Sweeping/emotional |
| `gr.py` | Guitar/Naturalistic | 90-120 | 20 | 5.5kHz | Realistic picking |

## Cross-References

- **Main Documentation**: [README.md](../README.md)
- **String Engine Reference**: [whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md](../whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md)
- **Web Audio Equivalents**: [opus/INDEX.md](../opus/INDEX.md)
- **Master Index**: [docs/INDEX.md](../docs/INDEX.md)
- **Gallery**: [docs/GALLERY.md](../docs/GALLERY.md)

## Key Insights

Python scripts enable **offline rendering** and **programmatic control** impossible in real-time browser contexts:

✅ **Advantages**:
- Longer render times = higher quality
- Batch parameter sweeps and variations
- Full algorithmic composition control
- Perfect reproducibility

🎯 **Best For**:
- Studio-quality audio generation
- Experimentation with DSP parameters
- Creating reference implementations
- Understanding synthesis mathematics deeply
- Converting gemini-3 aesthetics into a repeatable person-specific workflow

---

*Last updated: Current session | Part of comprehensive repository documentation*
