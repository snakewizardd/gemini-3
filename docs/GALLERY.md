# GALLERY.md — Curated Simulations & Demonstrations

A guided tour through the best examples in Gemini-3, organized by theme and technical sophistication.

---

## 📑 **Quick Navigation to All Indices**

**Want to browse everything systematically?** Use these comprehensive indices:

| Index | Scope | Files | Link |
|-------|-------|-------|------|
| **Master Index** | Complete repository map | 341+ | [docs/INDEX.md](INDEX.md) |
| **Opus Index** | Masterwork simulations | 7 | [opus/INDEX.md](../opus/INDEX.md) |
| **TKS Index** | DDA research lab | 33 | [tks/INDEX.md](../tks/INDEX.md) |
| **Second Detailed Index** | Experimental archive | 277 | [second/DETAILED_INDEX.md](../second/DETAILED_INDEX.md) |
| **Python Index** | DSP synthesis scripts | 12 | [python/INDEX.md](../python/INDEX.md) |

👉 **[START HERE: Master Index](INDEX.md)** for complete file-by-file documentation with hyperlinks

---

## **Tier 1: Essential Demonstrations**

Start here to understand the core concepts.

### **The DDA Agent Simulator**
**File:** `tks/DDA_Elena_Sim.html`  
**What:** Interactive dashboard visualizing DDA agents making decisions in a scenario ("The Drowning Town")  
**Why it matters:** This is the **clearest visual explanation** of how P₀, k, F, and m interact.  
**Technical highlights:**
- Real-time state visualization
- Parameter tweaking to see personality shifts
- Multiple agents with different profiles
- Scenario branching based on DDA computations

**How to use:**
1. Open in browser
2. Select an agent (Elena, Marcus, etc.)
3. Watch their internal state (k, F, P₀) update as they face choices
4. Modify parameters to see personality changes

**Best for:** Understanding how trauma, identity, and pressure shape choices

---

### **DDA Kernel Implementation**
**File:** `proofs/ai_studio_code.py`  
**What:** The runnable DDA algorithm (170 lines, fully functional)  
**Why it matters:** Proves the DDA isn't theoretical—it's implementable and testable  
**Technical highlights:**
- JSON persistence (soul.json)
- LLM integration pattern
- State machine: perceive → feel → decide → learn
- Trauma accumulation via prediction error

**How to use:**
```bash
python proofs/ai_studio_code.py
```

**Best for:** Developers implementing DDA agents, understanding the state machine

---

## **Tier 2: Audio-Visual Artistry**

High-quality procedural synthesis demonstrating the String Engine.

### **Romance in E Minor**
**File:** `opus/romance.html`  
**What:** Classical guitar piece synthesized in real-time with reverb, nylon tone shaping  
**Why it matters:** Shows how Karplus-Strong string modeling creates "organic" sound from pure math  
**Technical highlights:**
- Triangle + sine oscillator mix (nylon tone)
- BiquadFilter envelope (attack/decay)
- Convolver reverb (cathedral impulse)
- ~8kHz low-pass cabinet simulation

**Listen for:**
- Warm, woody resonance (no samples)
- Natural decay characteristics
- Reverb tail extending into space

**Best for:** Audio engineers, understanding tone modeling

---

### **Annihilate: Aggressive Dubstep**
**File:** `opus/annihilate.html`  
**What:** High-energy aggressive visualization with glitch text, sidechain-synced canvas effects  
**Why it matters:** Demonstrates audio-visual synchronization via shared state variables  
**Technical highlights:**
- Sidechain pulse (beat syncs video scale/color)
- Glitch animation (text transform on kick)
- Canvas feedback trails (semi-transparent overlay)
- High-gain distortion via `Math.tanh()`

**Listen/watch for:**
- Visual "punch" on each kick (beatPulse variable)
- Text glitching in perfect time
- Trail effects building energy

**Best for:** Understanding audio-visual coupling, procedural distortion

---

### **Cosmic Jellyfish**
**File:** `opus/jellyfish.html`  
**What:** Organic particle system with gravitational attraction, smooth trails  
**Why it matters:** Pure procedural animation with no sprites or textures  
**Technical highlights:**
- 150 particles with distance-based physics
- Smooth HSL color cycling
- Tentacle IK-like segments
- Mouse interaction affects field

**Watch for:**
- Particle repulsion/attraction behavior
- Natural flowing motion
- Color gradients without gradients

**Best for:** Understanding particle systems, procedural animation

---

### **Evening: Cosmic Owl**
**File:** `opus/evening.html`  
**What:** Playful cosmic visualization with procedural nebula, mouse-interactive owl  
**Why it matters:** Shows personality and aesthetic taste applied to procedural generation  
**Technical highlights:**
- Perlin noise (nebula clouds)
- Multiple particle classes (eyes, body, glow)
- Zoom interactivity via mouse scroll
- Text shadow glow effects

**Interact with:**
- Move mouse to steer owl
- Click to accelerate particles
- Scroll to zoom
- Discover hidden elements

**Best for:** Understanding procedural aesthetics, user interaction patterns

---

## **Tier 3: Research & Experimentation**

Advanced simulations demonstrating specific DDA or String Engine concepts.

### **Collatz Orbital Visualization**
**File:** `second/collatz.html`  
**What:** Real-time visualization of Collatz sequence orbits using golden-angle phyllotaxis  
**Why it matters:** Shows how chaotic mathematical sequences can be rendered as beautiful spirals  
**Technical highlights:**
- Collatz 3n+1 computation
- Golden angle distribution (137.5°)
- Radial distance encoding orbit length
- Real-time metrics display

**Explore:**
1. Click "INITIALIZE DATASET"
2. Watch numbers spiral out from center
3. Observe density patterns
4. Notice gaps (proved patterns in chaos)

**Best for:** Mathematical visualization, understanding phyllotaxis

---

### **Bach Singularity**
**File:** `second/bach.html`  
**What:** Baroque cathedral visualization with hierarchical fractal structure  
**Why it matters:** Demonstrates how simple recursive rules create complexity  
**Technical highlights:**
- Recursive geometry (fractal arches)
- Radial gradient backgrounds
- Text effects with blur filters
- Modal overlay system

**Best for:** Understanding recursive procedural generation, baroque aesthetics

---

### **Blackbird (Beatles Simulation)**
**File:** `second/beatles.html`  
**What:** Acoustic fingerpicking pattern visualized with guitar tablature, lyrics  
**Why it matters:** Shows how sequential music patterns can be visualized and animated  
**Technical highlights:**
- Tab visualization (string/fret display)
- Lyric synchronization
- Measure counter
- Note event animation

**Explore:**
1. Play button starts sequence
2. Watch lyrics sync to melody
3. See measure count advance
4. Notice tab visualization updating

**Best for:** Understanding music visualization, tablature-to-audio mapping

---

## **Tier 4: Deep Research**

Advanced DDA implementations and edge cases.

### **DDA Formalization (Mathematical Spec)**
**File:** `tks/DDA_Formalization.md`  
**What:** Rigorous formal specification including adaptive hysteresis, bifurcation parameter, persona engineering  
**Why it matters:** Explains the theoretical underpinnings in mathematical language  
**Key sections:**
- Governing equation with symbol definitions
- Adaptive hysteresis rule (why trauma increases k)
- Bifurcation parameter analysis (phase regimes)
- Persona archetypes with parameter settings

**Read for:** Deep understanding of DDA mathematics

---

### **Duality: Classical Composition**
**File:** `opus/lilypond.html`  
**What:** Large-scale (3062 lines) musical composition with staff notation, synthesis  
**Why it matters:** Shows integration of music theory, synthesis, and visualization at scale  
**Technical highlights:**
- Musical score rendering
- Multi-voice synthesis (three voices)
- Classical guitar tone models
- Interactive playback controls

**Best for:** Ambitious synthesis projects, large codebase examples

---

## **Tier 5: Meta & Philosophy**

Understanding the *why* behind the work.

### **"The Silicon Alchemist" Manifesto**
**File:** `whatami/README.md`  
**What:** Philosophical essay explaining the framework's core approach  
**Why it matters:** Articulates the design philosophy and mathematics of consciousness  
**Key arguments:**
- Reality is a function, not an asset
- Procedural generation as digital alchemy
- Audio-visual unity through mathematics
- Cybernetic minimalism

**Read for:** Understanding the project's ethos and design constraints

---

### **String Engine Technical Reference**
**File:** `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`  
**What:** 1289-line comprehensive reference for audio synthesis framework  
**Why it matters:** Canonical documentation for the universal synthesis model  
**Includes:**
- Architecture (Three Pillars)
- Configuration blocks
- Tone recipes (acoustic, metal, ambient)
- DSP chains (distortion, reverb, EQ)
- Implementation patterns

**Reference for:** Building new simulations, understanding tone design

---

### **DDA Proof from First Axioms**
**File:** `proofs/dda.md`  
**What:** Mathematical derivation of DDA from philosophical axioms  
**Why it matters:** Shows DDA emerges from *first principles*, not heuristic design  
**Sections:**
- Axioms 1-4 (Inertia, Entropy, Viscosity, Pressure)
- Formula derivation via superposition
- Proof of optimization (IIR filter analogy)
- Proofs of pathologies (Trauma Lock, Panic Bifurcation)

**Read for:** Rigorous mathematical foundation

---

## **Quick Reference: By Use Case**

| Goal | Start with |
|------|-----------|
| **Understand DDA** | `tks/DDA_Elena_Sim.html` then `proofs/dda.md` |
| **Hear procedural music** | `opus/romance.html` or `opus/annihilate.html` |
| **See beautiful visuals** | `opus/jellyfish.html` or `opus/evening.html` |
| **Learn audio synthesis** | `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md` |
| **Understand the philosophy** | `whatami/README.md` |
| **See the math in action** | `second/collatz.html` |
| **Implement DDA yourself** | `proofs/ai_studio_code.py` |
| **Study personas** | `tks/DDA_Formalization.md` → Persona Engineering |
| **Generate metal music** | `python/dragonfire.py` or `python/attempt.py` |
| **Explore fractals** | `second/bach.html` or `tks/unity_of_all_beings.html` |

---

## **Recommended Tour (2 hours)**

1. **15 min** — Open `tks/DDA_Elena_Sim.html`, interact with agents
2. **10 min** — Read `whatami/README.md` (manifesto)
3. **20 min** — Read `proofs/dda.md` (formal foundation)
4. **10 min** — Open `opus/romance.html`, listen to synthesized guitar
5. **10 min** — Open `opus/jellyfish.html`, play with particles
6. **10 min** — Open `second/collatz.html`, watch math visualization
7. **15 min** — Skim `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`
8. **10 min** — Open `second/beatles.html`, see music visualization
9. **10 min** — Read `docs/DDA_VISUAL_GUIDE.md` (intuitive explanations)

---

## **For Advanced Explorers**

- **india.md** — Deep knowledge dump, notes on everything (1.8MB)
- **tks/** folder — Browse all DDA-related simulations and variations
- **python/** — Run `python/attempt.py` or `python/dragonfire.py` to generate audio
- **second/** — Sort by date to see evolution of ideas

---

## **Contribution Ideas**

See something missing? Consider adding:
- [ ] A new tone recipe (ambient, vocal, pluck-string)
- [ ] A new DDA persona simulator
- [ ] A visualization of a specific mathematical concept (mandelbrot, lorenz attractor, etc.)
- [ ] An integration of Python synthesis with HTML visualization
- [ ] A tutorial/explainer simulation

---

**"Digital Alchemy: Transmute math into soul."**

