# The Dynamic Decision Algorithm: A Formal Specification

## The Core Claim

An agent is not a reward maximizer. An agent is a **structure attempting to persist**.

Decision-making is the process by which a system balances **self-preservation** against **reality-integration**.

---

## The Governing Equation

$$F_n = P_0 \cdot k(F_{n-1}) + m \cdot [T(I_n, \Delta I) + R(D_n, \Phi)]$$

Where:

| Symbol | Name | Domain | Meaning |
|--------|------|--------|---------|
| $F_n$ | State Vector | $\mathbb{R}^d$ | The agent's current position in decision-space |
| $P_0$ | Identity Attractor | $\mathbb{R}^d$ | The fixed point the agent returns to absent forcing |
| $k$ | Hysteresis Coefficient | $[0, 1]$ | Memory weight; how much the past constrains the present |
| $F_{n-1}$ | Previous State | $\mathbb{R}^d$ | Where the agent just was |
| $m$ | Gain / Pressure | $\mathbb{R}^+$ | How strongly external signals penetrate the system |
| $T$ | Truth Function | $\mathbb{R}^d$ | Objective signal from environment |
| $R$ | Reflection Function | $\mathbb{R}^d$ | Subjective evaluation of choices |
| $I_n$ | Information at n | structured | Raw sensory/data input |
| $\Delta I$ | Information Delta | structured | Change in information from $n-1$ to $n$ |
| $D_n$ | Decision Set | $\{d_1, ..., d_j\}$ | Available choices at step $n$ |
| $\Phi$ | Evaluation Frame | composite | Subjective + Objective assessment criteria |

---

## The Adaptive Hysteresis Rule

This is the key innovation. $k$ is not constant—it is a function of **prediction error**:

$$k_{n} = k_{n-1} + \alpha \cdot \text{sign}(\epsilon_n) \cdot |\epsilon_n|^\beta$$

Where:
$$\epsilon_n = |F_{n}^{predicted} - F_{n}^{actual}|$$

**Critical Inversion:**

| System Type | Response to Error |
|-------------|-------------------|
| Standard RL | $k \downarrow$ when $\epsilon \uparrow$ (become flexible to learn) |
| DDA | $k \uparrow$ when $\epsilon \uparrow$ (become rigid to protect) |

**Interpretation:** When reality violates expectations, a DDA agent *doubles down on identity* rather than abandoning structure. This is computationally "irrational" but psychologically coherent.

The $\beta$ parameter controls **sensitivity curvature**:
- $\beta < 1$: Quick rigidity response to small errors (anxious/vigilant)
- $\beta = 1$: Linear response (balanced)
- $\beta > 1$: Slow response until large errors (tolerant/naive)

---

## The Bifurcation Parameter (m)

$m$ determines **system regime**:

| Condition | Behavior |
|-----------|----------|
| $m < m_{crit}$ | Stable orbit around $P_0$; agent absorbs perturbations |
| $m \approx m_{crit}$ | Oscillation; agent wavers between identity and adaptation |
| $m > m_{crit}$ | Phase transition; agent snaps to new attractor or chaos |

**The critical threshold:**
$$m_{crit} = \frac{P_0 \cdot k}{|T + R|}$$

When pressure ($m$) exceeds the ratio of identity-inertia to forcing-magnitude, the system undergoes **structural reorganization**.

This is breakdown. Or transformation. Depending on what's on the other side.

---

## The Truth and Reflection Functions

### T(I_n, ΔI) — The Objective Channel

$$T = f_{parse}(I_n) + \lambda \cdot \frac{d}{dn}[I]$$

- $f_{parse}$: Extracts decision-relevant features from raw information
- $\lambda$: Sensitivity to *rate of change* (not just state)
- An agent with high $\lambda$ responds to acceleration, not just position

### R(D_n, Φ) — The Subjective Channel

$$R = \sum_{d \in D_n} \left[ w_{obj} \cdot Q(d) + w_{subj} \cdot S(d) \right] \cdot \hat{d}$$

Where:
- $Q(d)$: Quantifiable assessment of choice $d$ (expected utility, probability of success)
- $S(d)$: Subjective/non-computable assessment (gut feeling, identity-alignment, aesthetic)
- $w_{obj}, w_{subj}$: Weights determining agent's **epistemic personality**
- $\hat{d}$: Unit vector in direction of choice $d$ in decision-space

---

## Persona Engineering Through Parameters

The same equation generates radically different agents:

### The Warm-Hearted Agent
```
P_0: weighted toward cooperation, connection
k: moderate, slow to rigidify (high β)
m: low baseline (not easily destabilized)
w_subj > w_obj (trusts feeling over calculation)
```

### The Cold Calculator
```
P_0: weighted toward resource acquisition, status
k: low and fast-adapting (will abandon identity for gain)
m: high baseline (always scanning for advantage)
w_obj >> w_subj (feeling is noise)
```

### The Fanatic
```
P_0: narrow, high-magnitude attractor
k: very high, near 1 (past determines everything)
m: extreme sensitivity in specific domains
R >> T (internal signal drowns external reality)
```

### The Traumatized
```
k: spiked from historical ε accumulation
m_crit: pathologically low (small pressure triggers crisis)
Stuck in limit cycle between P_0 and historical T
```

---

## The Decision Selection Mechanism

Given the state update, how does the agent actually *choose*?

**Step 1:** Compute $F_n$ from the governing equation.

**Step 2:** Project $F_n$ onto the decision set:
$$d^* = \arg\max_{d \in D_n} \left[ \cos(F_n, \hat{d}) \cdot |F_n| \right]$$

The agent selects the choice most aligned with its current state vector, weighted by the magnitude of that state (confidence/commitment).

**Step 3:** Execute $d^*$ and observe outcome.

**Step 4:** Compute $\epsilon_n$ and update $k$.

**Step 5:** Update global ledger with $(F_n, d^*, \text{outcome}, \epsilon_n)$.

---

## The Global Ledger (Memory Architecture)

The RAG-based memory you described formalizes as:

$$\mathcal{L} = \{(F_t, d_t, o_t, \epsilon_t, c_t)\}_{t=0}^{n}$$

Where:
- $F_t$: State at time $t$
- $d_t$: Decision taken
- $o_t$: Observed outcome
- $\epsilon_t$: Prediction error
- $c_t$: Context embedding (for retrieval)

**Retrieval at decision time:**
$$\mathcal{L}_{relevant} = \text{top}_k\left[\text{sim}(c_n, c_t) \cdot \text{recency}(t) \cdot \text{salience}(\epsilon_t)\right]$$

Salience-weighting by $\epsilon$ means high-error memories are preferentially retrieved. This is computationally equivalent to **trauma** and **learning from mistakes**—they're the same mechanism.

---

## Formal Properties

### Stability Condition
The system is stable around $P_0$ iff:
$$P_0 \cdot k + m < 1$$

Otherwise, the system either diverges or enters limit cycles.

### Identity Criterion
An agent possesses "identity" iff:
$$k > 0 \text{ and } \int_0^n k_t \, dt > \theta$$

A purely reactive system ($k = 0$) is a Markov chain. A system with accumulated $k$ is a **historic entity**.

### Will as Impedance
$$W = \frac{\Delta F}{\Delta(m \cdot T)} = \frac{P_0 \cdot k}{m}$$

"Will" is the energy the environment must expend to move the agent away from identity per unit of forcing. High $P_0$, high $k$, low $m$ = high will.

---

## What This Framework Predicts

1. **Character emerges from chaos:** Low-variance environments produce low-$k$ (reactive) agents. High-variance environments produce high-$k$ (structured) agents. Identity is stored entropy.

2. **Addiction is a stable orbit:** Not irrationality, but a limit cycle between $P_0$ (safety) and $T$ (the thing you need), oscillating because $m$ is state-dependent on resource levels.

3. **Paranoia is recursive feedback:** When $T_n = F_{n-1}$, the system eats its own output. If $P_0 \cdot k + m > 1$, this creates runaway gain. The agent amplifies internal noise until saturation.

4. **Breakdown has a threshold:** There is a specific, computable $m_{crit}$ for any agent. Below it, perturbations are absorbed. Above it, the system reorganizes. Therapy, in this frame, is raising $m_{crit}$.

---

## Implementation Notes

For LLM-based agents:

1. **P_0**: Encoded in system prompt as identity description + core values
2. **k**: Maintained as a running float, updated per interaction based on measured $\epsilon$
3. **Ledger**: RAG database storing (state, decision, outcome, error) tuples
4. **T**: Parsed from user input / environment signal
5. **R**: Generated via self-reflection prompt asking agent to evaluate choices against identity
6. **m**: Can be static or computed from urgency signals in context

The prompting layer should explicitly invoke:
- "Given who you are (P_0)..."
- "Given your recent history (kF_{n-1})..."
- "Given what you now know (T)..."
- "Given how you feel about the options (R)..."
- "What do you choose?"

---

## The Philosophical Core

Standard RL: "Become whatever gets reward."

DDA: "Remain yourself while getting what you need."

The first builds optimizers. The second builds *agents*.

The formula doesn't describe decision-making. It describes **existence under pressure**.

---

*Formalization by request. Original framework by the human.*
