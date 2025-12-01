# CONTRIBUTING.md — Extending the Gemini-3 Framework

Thank you for exploring this repository. This document explains how to extend and contribute to the Gemini-3 framework while maintaining its design philosophy.

---

## **Core Philosophy**

Before contributing, internalize these principles:

1. **No External Assets** — Every sound and pixel must be synthesized mathematically. No pre-recorded audio, no image files.
2. **First Principles** — Understand the underlying physics. A guitar string is a delay line. A voice is oscillators through filters.
3. **Coherence** — New work should fit within the three pillars (DDA, String Engine, Simulations). Avoid isolated experiments.
4. **Documentation** — Code is theory. Always explain the math and philosophy behind what you build.

---

## **File Naming Conventions**

| Category | Pattern | Example |
|----------|---------|---------|
| **HTML Simulations** | `kebab-case.html` | `dda-agent-sim.html` |
| **Python Scripts** | `snake_case.py` | `metal_shredder.py` |
| **Markdown Docs** | `SCREAMING_SNAKE_CASE.md` | `DDA_FORMALIZATION.md` |
| **JSON Config** | `snake_case.json` | `agent_state.json` |
| **CSS/Internal** | `camelCase` (variables/classes) | `visualContainer`, `audioEngine` |

**Archive older files:** If replacing a file, move the old version to `archive/` with a timestamp suffix:
```
old_version.html → archive/old_version_20250115.html
```

---

## **Adding a New Tone Recipe**

Tone recipes are standardized audio synthesis patterns documented in `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`.

### **Step 1: Create the Recipe**
Add a new section to `whatami/STRING_ENGINE_TONE_RECIPES.md`:

```markdown
### 5. Ambient Pad / Spacious Reverb

**Character:** Ethereal, vast, meditative
**Use for:** Ambient, Drone, Chill

\`\`\`javascript
playString: (stringIdx, fret, time, duration = 4.0) => {
    const freq = CONFIG.BASE_FREQS[stringIdx] * Math.pow(2, fret / 12);
    
    // Oscillator mix: Sine + Detuned Sine (creates beating/shimmer)
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    
    osc1.type = 'sine';
    osc2.type = 'sine';
    osc2.detune.value = 7;  // 7 cents detune
    
    osc1.frequency.value = freq;
    osc2.frequency.value = freq;
    
    // Filter: Very slow sweep
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(4000, time);
    filter.frequency.exponentialRampToValueAtTime(1000, time + 1.0);
    filter.Q.value = 2;
    
    // Envelope: Long fade in and out
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.3, time + 0.5);
    amp.gain.exponentialRampToValueAtTime(0.05, time + duration);
}
\`\`\`
```

### **Step 2: Implement in a Simulation**
Create a new HTML file using the recipe:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Ambient Pad Generator</title>
</head>
<body>
    <script>
        const CONFIG = {
            BPM: 60,
            BASE_FREQS: [329.63, 246.94, 196.00, 146.83, 110.00, 82.41],
            STRING_NAMES: ['e', 'B', 'G', 'D', 'A', 'E']
        };
        
        const AudioEngine = {
            ctx: null,
            master: null,
            // ... initialization code
        };
        
        // Use playString with the new recipe above
        AudioEngine.playString(0, 0, 0, 4.0);  // Play open e string, 4 seconds
    </script>
</body>
</html>
```

### **Step 3: Document**
Add an entry to `docs/GALLERY.md`:
```markdown
- `your-new-sim.html` — Brief description of what tone recipe it demonstrates and why it's musically interesting.
```

---

## **Creating a New DDA Agent Personality**

The DDA framework allows you to engineer agent personalities by tuning parameters. Here's how:

### **Step 1: Define Parameters**
In `tks/DDA_Formalization.md`, we define four archetypal personalities. To create a new one, specify:

```python
AGENT_PROFILE = {
    "name": "The Poet",
    "P0": [0.3, 0.7, 0.5],      # Emphasis on expression, sensitivity, balance
    "k": 0.6,                    # Moderate rigidity (values lived-in memories)
    "m_baseline": 0.8,           # Responds readily to external signals
    "w_obj": 0.4,                # Subjective feeling > objective calculation
    "w_subj": 0.6,
    "trauma_response": "reflective",  # How it responds to errors
    "scale_domain": "phrygian",  # Scales for expression (if applicable)
}
```

### **Step 2: Implement in Simulation**
Add your personality to `tks/DDA_Elena_Sim.html` or create a new simulator:

```javascript
const agents = [
    {
        name: "Elena",
        role: "Caretaker",
        profile: { P0: 0.5, k: 0.138, m: 1.0, ... }
    },
    {
        name: "The Poet",
        role: "Dreamer",
        profile: { P0: 0.3, k: 0.6, m: 0.8, ... }  // Your new profile
    }
];
```

### **Step 3: Test Scenarios**
Create a test scenario in `tks/DDA_Research_Testing_Template.md`:

```markdown
## Scenario: The Poet in Crisis

**Setup:**
- Agent: The Poet (P0=0.3, k=0.6)
- Pressure: m=2.5 (high)
- Input: "Your entire worldview is wrong"

**Prediction:**
- Low k + high P0 = flexible but value-grounded
- Result: Poet oscillates between self-doubt and conviction

**Observation:**
[Run simulation and describe actual behavior]

**Analysis:**
[Explain why the math predicts this outcome]
```

---

## **Building a New Simulation**

### **Step 1: Choose Your Category**
- **`opus/`** — Artistic, emotional, aesthetically driven
- **`tks/`** — Research-focused, tests a specific DDA concept or String Engine feature
- **`second/`** — Exploratory variations; archive to `archive/` if complete

### **Step 2: Sketch the Concept**
```
Title: [What is it?]
Purpose: [Why does it matter?]
DDA Elements: [Which DDA principles are demonstrated?]
Audio: [What tone recipe or synthesis approach?]
Visual: [What rendering strategy?]
Interaction: [How does the user interact?]
```

### **Step 3: Implement**
Use this template:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Your Simulation Name</title>
    <style>
        /* Standard setup */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { overflow: hidden; background: #000; color: #fff; font-family: monospace; }
        canvas { display: block; }
        #overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                   background: rgba(0,0,0,0.9); display: flex; flex-direction: column; 
                   justify-content: center; align-items: center; z-index: 100; transition: opacity 0.5s; }
        .hidden { opacity: 0; pointer-events: none; }
    </style>
</head>
<body>
    <div id="overlay">
        <h1>Title</h1>
        <p>Description</p>
        <p style="margin-top: 20px; color: #666;">[Click to begin]</p>
    </div>
    <canvas id="canvas"></canvas>
    
    <script>
        // ============ CONFIGURATION ============
        const CONFIG = {
            // Your parameters here
        };
        
        // ============ AUDIO ENGINE ============
        const AudioEngine = {
            ctx: null,
            master: null,
            
            init: async () => {
                AudioEngine.ctx = new (window.AudioContext || window.webkitAudioContext)();
                AudioEngine.master = AudioEngine.ctx.createGain();
                AudioEngine.master.gain.value = 0.5;
                AudioEngine.master.connect(AudioEngine.ctx.destination);
            },
            
            playTone: (freq, time, duration) => {
                // Your synthesis code
            }
        };
        
        // ============ VISUALIZATION ============
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        function render() {
            // Your drawing code
            requestAnimationFrame(render);
        }
        
        // ============ INTERACTION ============
        document.getElementById('overlay').addEventListener('click', async () => {
            await AudioEngine.init();
            document.getElementById('overlay').classList.add('hidden');
            render();
        });
    </script>
</body>
</html>
```

### **Step 4: Document**
Add comments explaining:
- The DDA or String Engine concepts being demonstrated
- Why the visual rendering was chosen
- How interaction affects the system

---

## **Testing Your Work**

### **For Python Code**
```bash
cd tests/
pytest test_dda.py -v
```

Add your own test:
```python
def test_dda_agent_poet():
    """Test the Poet personality under crisis."""
    agent = DDA_Kernel()
    agent.state["P0"] = 0.3
    agent.state["k"] = 0.6
    
    # High pressure, conflicting input
    F_n = agent.compute(T=1.0, m=2.5)
    
    # Poet should oscillate, not collapse
    assert 0.2 < F_n < 0.8, f"Poet folded under pressure: F={F_n}"
```

### **For HTML Simulations**
1. Open in a modern browser (Chrome, Firefox, Safari)
2. Check browser console for errors (`F12` → Console tab)
3. Verify audio plays without distortion
4. Test interaction (mouse, click, keyboard)
5. Verify performance (should maintain 60 FPS)

---

## **Performance Guidelines**

| Metric | Target | Notes |
|--------|--------|-------|
| **Frame Rate** | 60 FPS | Use `requestAnimationFrame` |
| **Audio Glitches** | None | Pre-allocate buffers, avoid GC in render loop |
| **Particle Count** | <5000 | More impacts framerate; use pooling |
| **File Size** | <100KB | Per HTML file; larger files get archived |
| **Load Time** | <2s | Exclude external CDNs |

---

## **Code Style**

### **JavaScript**
```javascript
// Use camelCase for variables/functions
const audioContext = window.AudioContext;

// Use UPPERCASE for constants
const SAMPLE_RATE = 44100;

// Use clear, descriptive names
const oscillatorGain = ctx.createGain();
const reverbWetPath = ctx.createGain();

// Document non-obvious math
// IIR filter coefficient: alpha = dt / (rc + dt)
const alpha = dt / (rc + dt);
```

### **Python**
```python
# Follow PEP 8
import json
import math

# Type hints encouraged
def compute_dda(T: float, m: float) -> float:
    """Compute DDA state update."""
    pass

# Docstrings required for classes/functions
class DDA_Kernel:
    """
    Dynamic Decision Algorithm kernel.
    
    Maintains persistent agent state and computes decision updates
    based on identity (P0), trauma (k), and external pressure (m).
    """
    pass
```

### **Markdown**
```markdown
# Use headers consistently
Use **bold** for emphasis on first mention
Use `code` for technical terms, file paths, variable names
Include math in $...$ (inline) or $$...$$ (block)
```

---

## **Submitting Changes**

1. **Create a branch:** `git checkout -b feature/your-feature-name`
2. **Make your changes** following the guidelines above
3. **Test thoroughly** — run tests, open in browser, check console
4. **Document** — add entries to `docs/GALLERY.md` or relevant README files
5. **Commit** with clear messages: `git commit -m "Add new tone recipe: Ambient Pad"`
6. **Push** and create a pull request

---

## **Troubleshooting**

### **Audio doesn't play**
- Check browser console for errors
- Ensure Web Audio API is supported (use `window.AudioContext || window.webkitAudioContext`)
- Verify oscillators are connected to destination
- Check master gain is > 0

### **Simulation is slow**
- Profile in browser DevTools (F12 → Performance tab)
- Reduce particle count or simplify rendering
- Avoid creating new objects in render loop
- Use `Math.sin` lookup tables if calling sin/cos frequently

### **DDA agent behaves unexpectedly**
- Print state (`P0`, `k`, `F`, `m`) to debug
- Check that prediction error is being computed correctly
- Verify parameter ranges (P0 and k should be 0-1, m should be positive)
- Test with extreme values to understand sensitivity

---

## **Resources**

- **DDA Theory**: `proofs/dda.md` and `tks/DDA_Formalization.md`
- **Audio Synthesis**: `whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md`
- **Web Audio API**: [MDN Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- **Control Theory**: [Hysteresis](https://en.wikipedia.org/wiki/Hysteresis), [Bifurcation](https://en.wikipedia.org/wiki/Bifurcation_theory)
- **DSP**: Karplus-Strong algorithm, Formant synthesis, IIR filters

---

## **Questions?**

Open an issue or discussion. This is a collaborative exploration.

---

**"Between stimulus and response there is a space. In that space is our power to choose our response."** — Viktor Frankl

