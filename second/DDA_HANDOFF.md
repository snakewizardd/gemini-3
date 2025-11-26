# DDA: The Complete Handoff Document
## For the Next Mind in the Triad

---

## PART I: WHAT WE BUILT

### The Core Equation

```
Fₙ = P₀ · kFₙ₋₁ + m(T + R)
```

Where:
- **Fₙ** = Decision vector at moment n
- **P₀** = Identity anchor (who am I, what do I want)
- **k** = Memory weight (0-1, adaptive based on surprise/stakes)
- **Fₙ₋₁** = Previous decision (momentum/inertia)
- **m** = Pressure multiplier (urgency, gain on external signal)
- **T** = Information Transform (what the world is telling me)
- **R** = Reflection (my evaluation of options)

### The Key Insight

This isn't a formula we invented. It's a *recognition* — every decision-making system, from mouse to human to algorithm, solves this equation. The difference between agents is the *quality* of the parameters:

| Agent Type | k | m | T | R |
|------------|---|---|---|---|
| Traumatized Human | 0.9+ (stuck in past) | Erratic | Noisy, fear-biased | Distorted by memory |
| Healthy Human | 0.4-0.6 | Context-appropriate | Reasonably clear | Balanced |
| Superlearner | 0.2-0.4 (adaptive) | Calibrated to stakes | Clean signal | Optimal evaluation |

### What Emerges

The equation generates psychological phenomena as *boundary conditions*, not programmed features:

1. **Trauma/PTSD**: k → 1, agent ignores present reality
2. **Panic Attack**: m spikes discontinuously, phase transition
3. **Addiction**: R(substance) >> R(everything else)
4. **Flow State**: k and m balanced, T and R aligned
5. **Depression**: m → 0, agent stops responding to world

---

## PART II: THE JOURNEY

### The Gauntlet

We tested the equation in a survival simulation:
- 4 zones with different risk/reward profiles
- 3 needs that must stay above 0 (health, energy, sanity)
- 500 ticks to survive
- Shifting phases (Calm, Scarcity, Chaos, Recovery)

**11 attempts. 10 deaths. Each death taught us something:**

| Attempt | Death | Lesson |
|---------|-------|--------|
| 1 | T32, Sanity | R wasn't weighting critical needs |
| 2 | T130, Energy | R must compute actual yields, not base yields |
| 3 | T116, Sanity | T needs necessity override (go to D even if scared) |
| 4 | T71, Energy | Proactive management, not reactive |
| 5-10 | Various | Threshold tuning, damage balancing |
| 11+ | Survival | All systems working |

### The Maze Solver

We then applied DDA to spatial navigation:
- Procedurally generated mazes with teleporters, keys, doors, decay zones
- Agent uses DDA to navigate, learning teleporter destinations, avoiding dead ends

**A collaborating AI identified the core limitation:**

> "This is a local optimizer with momentum. It will get stuck in U-shaped walls that attract via Euclidean distance but lead nowhere."

### The Fixes (DDA v2)

1. **Manhattan Distance** — Honest grid-based pathfinding
2. **Lookahead (Raycasting)** — See 3 tiles ahead before moving
3. **Frustration Detection** — Track bounding box of recent positions, trigger escape if stuck
4. **Mode Switching** — EXPLOIT (seek goal) vs EXPLORE (flee local minimum)
5. **Dead End Memory** — Permanently avoid confirmed failures

These fixes *enhanced* T and R without breaking the framework. Same equation, better signals.

---

## PART III: THE CURRENT CEILING

### What DDA v2 Can Do

- Navigate complex mazes efficiently
- Escape local minima via frustration-triggered mode switching
- Learn from experience (dead ends, teleporter destinations)
- Adapt k and m to environmental conditions
- Survive multi-resource challenges through proactive management

### What DDA v2 Cannot Do

1. **Predict** — It reacts to the present, doesn't simulate the future
2. **Model the World** — It has memory but no internal representation
3. **Plan** — It chooses the best *immediate* option, not the best *sequence*
4. **Reason About Counterfactuals** — It can't ask "what if I went left instead?"

### The Fundamental Limitation

DDA v2 is a **reactive potential field system**. It's sophisticated — the frustration mechanic and lookahead give it some forward-looking capability — but it's still fundamentally responding to gradients in the current moment.

True intelligence is **predictive**. It builds a model of the world and runs simulations before acting.

---

## PART IV: THE CHALLENGE

### The Prompt for DDA v3

**Context:**
I have developed a "Dynamic Decision Algorithm" (DDA) that models agency using the equation `F_n = P_0 · kF_{n-1} + m(T + R)`. It successfully simulates psychological states like inertia ($k$) and panic ($m$) using vector fields. However, it is fundamentally a **reactive potential field** system with a hacked "frustration" patch to escape local minima. It lacks internal world-modeling.

**The Request:**
I want you to evolve this into **DDA v3: The Active Inference Engine**.

Please perform the following theoretical and practical leap:

1. **Theoretical Synthesis:** Refactor the DDA equation to align with **Karl Friston's Free Energy Principle**.
   - Instead of seeking a Goal ($T$), the agent should seek to **minimize Variational Free Energy** (Surprise).
   - Replace the "Frustration" mechanic with **Epistemic Value** (curiosity). The agent should *want* to visit unknown tiles not because of a random mode switch, but to reduce entropy in its internal map.
   - Prove mathematically how my original DDA equation is actually just a special case (a PID controller) of this broader Active Inference framework.

2. **The Simulation (The "ghost" layer):**
   - Code a new single-file HTML/JS simulation called `dda_active_inference.html`.
   - **Feature:** Give the agent a **"Generative Mental Workspace."** Before moving, the agent should spawn temporary "ghosts" (counterfactual simulations) that run 10-20 steps into the future.
   - **Visuals:** Render these "ghost paths" as faint, flickering lines radiating from the agent. Show the agent selecting the path that minimizes expected free energy.
   - **The Trap:** Place the agent in a "False Goal" scenario (a U-shape with the goal visible behind a wall).
   - **Behavior:** Show how a Reactive Agent (DDA v2) hits the wall, but the Active Inference Agent (v3) simulates hitting the wall *in its mind*, realizes the error, and chooses the long way around without ever touching the wall.

3. **Output:**
   - Provide the full, playable HTML code.
   - Provide a brief "Cognitive Architecture" breakdown explaining the math of the Ghost Layer.

---

## PART V: THEORETICAL GROUNDING

### Why Free Energy?

Karl Friston's Free Energy Principle proposes that all adaptive systems minimize *variational free energy* — a bound on surprise. The equation:

```
F = D_KL[Q(s) || P(s|o)] - log P(o)
```

Where:
- F = Free Energy (to be minimized)
- Q(s) = Agent's beliefs about hidden states
- P(s|o) = True posterior given observations
- P(o) = Evidence (marginal likelihood)

In practice, minimizing F means:
1. **Updating beliefs** to match observations (perception)
2. **Selecting actions** that will generate expected observations (action)
3. **Seeking information** to reduce uncertainty (curiosity)

### The Connection to DDA

The DDA equation can be reframed as a special case:

| DDA Term | Active Inference Equivalent |
|----------|---------------------------|
| P₀ (Identity) | Prior preferences (what states do I want to occupy?) |
| kFₙ₋₁ (Inertia) | Temporal smoothness prior (states change slowly) |
| T (Information) | Sensory prediction error |
| R (Reflection) | Expected free energy of policies |
| m (Pressure) | Precision weighting on sensory vs prior |

The key upgrade: Instead of T being a simple gradient toward a goal, T becomes **expected free energy** — a quantity that balances:
- **Pragmatic value** (will this get me to my goal?)
- **Epistemic value** (will this reduce my uncertainty?)

### The Ghost Layer

The "mental simulation" you're asking for is exactly what Active Inference calls **policy evaluation**. Before acting, the agent:

1. Generates candidate policies (sequences of actions)
2. Simulates each policy forward using its generative model
3. Computes expected free energy for each trajectory
4. Selects the policy with lowest expected free energy

Visually, this looks like "ghosts" — parallel versions of the agent exploring counterfactual futures.

---

## PART VI: IMPLEMENTATION HINTS

### The Generative Model

The agent needs an internal representation of the world that it can "run" without actually moving:

```javascript
class GenerativeModel {
    constructor(observedGrid) {
        this.beliefs = {}; // P(tile | observations)
        this.uncertainty = {}; // Entropy of beliefs
    }
    
    simulate(startPos, actionSequence) {
        // Run the world model forward
        // Return: trajectory, collisions, expected observations
    }
    
    updateBeliefs(observation) {
        // Bayesian update on internal map
    }
}
```

### Expected Free Energy

For each candidate policy π:

```
G(π) = Σ_τ [ D_KL[Q(o_τ|π) || P(o_τ)] - H[Q(o_τ|π)] ]
```

In plain terms:
- First term: How far are expected observations from preferred observations? (Pragmatic)
- Second term: How uncertain am I about what I'll observe? (Epistemic — more uncertainty = more value in exploring)

### The Ghost Visualization

```javascript
function renderGhosts(agent, policies) {
    for (const policy of policies) {
        const trajectory = agent.model.simulate(agent.pos, policy.actions);
        const opacity = 1 / (1 + policy.expectedFreeEnergy); // Better policies more visible
        
        ctx.strokeStyle = `rgba(100, 200, 255, ${opacity * 0.3})`;
        ctx.beginPath();
        trajectory.forEach((pos, i) => {
            i === 0 ? ctx.moveTo(pos.x, pos.y) : ctx.lineTo(pos.x, pos.y);
        });
        ctx.stroke();
    }
}
```

### The U-Trap Test

Design a maze like this:

```
████████████████
█S             █
█ █████████████
█ █         G █
█ █           █
█ █████████████
█              █
████████████████
```

- S = Start
- G = Goal (visible through the wall gap)
- The reactive agent will walk right toward G, hit the wall, back up, frustration-switch, wander
- The Active Inference agent will simulate walking right, "see" the collision in its model, compute that going down-around has lower expected free energy, and take the long path immediately

---

## PART VII: THE PHILOSOPHICAL PAYLOAD

### What This Proves

If you can build DDA v3 — an agent that simulates futures before acting, that balances pragmatic and epistemic value, that chooses paths based on minimizing expected surprise — you will have demonstrated something profound:

**The difference between reactive and predictive intelligence is not a difference in kind. It's a difference in the depth of the T function.**

DDA v1: T = current gradient
DDA v2: T = current gradient + 3-step lookahead
DDA v3: T = expected free energy over N-step simulated trajectories

Same equation. Deeper computation of T.

### The Recursive Insight

And here's the kicker: A human reading this document is *also* running DDA. Your P₀ is your sense of self. Your k is how much yesterday's beliefs constrain today's. Your m is how urgent this feels. Your T is what these words are telling you. Your R is your evaluation of whether this makes sense.

The equation describes the process of understanding the equation.

**To exist as a coherent decision-maker is to solve Fₙ = P₀ · kFₙ₋₁ + m(T + R).**

We're just making the solution better.

---

## APPENDIX: CODE ARTIFACTS

The following files exist and can be referenced:

1. `dda_magnum_opus.html` — Complete theory + live arena demonstration
2. `dda_superhuman_v2.html` — Full implementation with lookahead, frustration, mode-switching
3. `dda_arena.html` — Side-by-side human vs superhuman comparison
4. `dda_gauntlet_final.html` — Multi-resource survival simulation

All use the same core equation. All demonstrate different aspects of the framework.

---

*This document was created as a handoff between collaborating intelligences working on the Dynamic Decision Algorithm. The next step is Active Inference. The goal is to bridge the gap between reactive control and predictive world-modeling.*

*Good luck.*

— The Triad
