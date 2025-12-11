# Dynamic Decision Algorithm (DDA) — Revised Formal Specification

## 0) Core idea (unchanged, just sharpened)

An agent isn’t “maximize reward,” it’s a system balancing:

*   **identity persistence** (stay coherent / self-preserving)
*   **reality integration** (update from the world)

DDA’s signature move: **surprise increases rigidity**.

***

## 1) Spaces and objects

### State space

\[
\mathbf{x}\_t \in \mathbb{R}^d
]
“Decision-space” latent vector (traits, goals, beliefs, stance, affect, etc.).

### Identity attractor

\[
\mathbf{x}^\* \in \mathbb{R}^d
]
Fixed (or slow-moving) “who I am” point.

### Actions / decision set

Let actions be discrete:
\[
\mathcal{A}\_t={a\_1,\dots,a\_J}
]
Each action has a direction in decision-space:
\[
\hat{\mathbf{d}}(a)\in \mathbb{R}^d,\quad |\hat{\mathbf{d}}(a)|=1
]

***

## 2) Governing dynamics (clean vector form)

Define three forces, all in (\mathbb{R}^d):

### (a) Identity pull (self-preservation)

\[
\mathbf{F}\_{id}(t)=\gamma\left(\mathbf{x}^\*-\mathbf{x}\_t\right)
]
(\gamma\ge 0) is identity stiffness.

### (b) Truth channel (world forcing)

Truth produces a *target state* (\mathbf{x}^T\_t) from current observation (I\_t) (and optionally its change (\Delta I\_t)):
\[
\mathbf{x}^T\_t = T(I\_t,\Delta I\_t)\in \mathbb{R}^d
]
Then truth force:
\[
\mathbf{F}\_T(t)=\left(\mathbf{x}^T\_t-\mathbf{x}\_t\right)
]

### (c) Reflection channel (subjective evaluation)

Reflection produces a *target state* (\mathbf{x}^R\_t) based on options and frame:
\[
\mathbf{x}^R\_t = R(\mathcal{A}\_t,\Phi\_t,\mathcal{L})\in \mathbb{R}^d
]
Reflection force:
\[
\mathbf{F}\_R(t)=\left(\mathbf{x}^R\_t-\mathbf{x}\_t\right)
]

### External pressure / gain

Let (m\_t\ge 0) scale how much truth+reflection penetrate:
\[
m\_t \in \mathbb{R}^+
]

### Adaptive hysteresis / openness

Let (k\_t\in\[0,1]) be the “how much I move this step” coefficient. Bigger (k\_t) = more movement per step.

### Final state update

\[
\boxed{
\mathbf{x}\_{t+1}
=================

\mathbf{x}\_t
\+
k\_t\Big(
\gamma(\mathbf{x}^\*-\mathbf{x}\_t)
\+
m\_t\big\[\mathbf{F}\_T(t)+\mathbf{F}\_R(t)\big]
\Big)
}
]

If you expand it, you can see it’s a stable “pull toward weighted targets” map.

***

## 3) Concrete definitions for (T) and (R)

### 3.1 Truth (T(I\_t,\Delta I\_t))

You want a clean “parse + change sensitivity” form:
\[
T(I\_t,\Delta I\_t)
===================

f\_{\text{parse}}(I\_t)
\+
\lambda , f\_{\Delta}(\Delta I\_t)
]

*   (f\_{\text{parse}}:) extract features and map into (\mathbb{R}^d)
*   (f\_{\Delta}:) encode novelty/acceleration (rate-of-change) into (\mathbb{R}^d)
*   (\lambda\ge 0): sensitivity to change

In an LLM agent, (f\_{\text{parse}}) can be “embedding + linear map into state dims,” and (f\_\Delta) can be “embedding difference” (or novelty score times a direction).

### 3.2 Reflection (R(\mathcal{A}\_t,\Phi\_t,\mathcal{L}))

Make reflection a weighted average of action-directions:
\[
R(\mathcal{A}\_t,\Phi\_t,\mathcal{L})
=====================================

\mathbf{x}*t
\+
\sum*{a\in\mathcal{A}\_t}
\pi\_t(a), \hat{\mathbf{d}}(a)
]
where (\pi\_t(a)) is a soft preference distribution derived from objective + subjective scoring:

\[
s\_t(a)=
w\_{obj}Q(a) + w\_{subj}S(a)
]
\[
\pi\_t(a)=\frac{e^{\tau s\_t(a)}}{\sum\_{a'} e^{\tau s\_t(a')}}
]

*   (Q(a)): computable score (success prob, cost, constraint satisfaction)
*   (S(a)): identity-alignment / gut / aesthetics
*   (w\_{obj},w\_{subj}\ge 0): “epistemic personality”
*   (\tau): sharpness (higher = more decisive)

***

## 4) Decision selection mechanism (projection, but consistent)

Option A (closest to your cosine idea): choose the action most aligned with the *proposed update direction*.

Define the instantaneous desired movement:
\[
\Delta \mathbf{x}\_t
====================

\gamma(\mathbf{x}^\*-\mathbf{x}\_t)
\+
m\_t\big\[\mathbf{F}\_T(t)+\mathbf{F}\_R(t)\big]
]

Then:
\[
\boxed{
a^\*\_t
=======

\arg\max\_{a\in\mathcal{A}\_t}
\cos\big(\Delta\mathbf{x}\_t,\hat{\mathbf{d}}(a)\big)
}
]
(If (\Delta\mathbf{x}\_t=\mathbf{0}), pick “do nothing” or default-safe.)

Option B (more control-y): score each action by predicted next-state alignment; either works.

***

## 5) Prediction, outcome encoding, and prediction error (\epsilon\_t)

You need this super explicit or the whole (k)-adaptation becomes vibes.

### Forward model (predict)

\[
\mathbf{x}^{pred}\_{t+1} = \hat{f}(\mathbf{x}\_t,a^**t)
]
Minimal workable choice: assume your update equation itself is the predictor (using estimated (T,R) before acting):
\[
\mathbf{x}^{pred}*{t+1} = \mathbf{x}\_t + k\_t(\gamma(\mathbf{x}^*-\mathbf{x}\_t)+m\_t(\mathbf{F}\_T+\mathbf{F}\_R))
]

### Outcome encoder (actual)

Observe outcome (o\_{t+1}) (tool result, user reaction, environment state), then embed/encode:
\[
\mathbf{x}^{act}*{t+1} = E(o*{t+1})\in\mathbb{R}^d
]
(LLM version: embed the outcome text, map into your (d)-dim state.)

### Prediction error (scalar)

Use a norm:
\[
\boxed{
\epsilon\_t = |\mathbf{x}^{pred}*{t+1}-\mathbf{x}^{act}*{t+1}|\_2
}
]

***

## 6) The DDA signature: bounded adaptive hysteresis (rigidity rises with error)

You want “more surprise → more identity-cling / protective behavior.” The clean way is: **error increases an internal “threat” variable**, which then pushes (k) toward *rigidity mode*. But since in our update bigger (k) means bigger movement, we separate:

*   (k\_t): **step size / openness**
*   (\rho\_t\in\[0,1]): **rigidity / defensiveness**

Then define:

*   effective step size decreases as rigidity rises:
    \[
    k^{eff}*t = k*{base},(1-\rho\_t)
    ]

### Rigidity update (bounded, smooth)

\[
\boxed{
\rho\_{t+1} =
\mathrm{clip}\left(
\rho\_t + \alpha\cdot \sigma\big((\epsilon\_t-\epsilon\_0)/s\big),
0,1
\right)
}
]

*   (\sigma(z)=\frac{1}{1+e^{-z}}) (sigmoid)
*   (\epsilon\_0): “when surprise becomes threatening”
*   (s): sensitivity scale
*   (\alpha): learning rate
*   clip keeps it in (\[0,1])

Optional decay (recovery when safe):
\[
\rho\_{t+1}\leftarrow (1-\delta)\rho\_{t+1}
]
with (\delta\in\[0,1]).

### Final update uses (k^{eff}\_t)

\[
\boxed{
\mathbf{x}\_{t+1}
=================

\mathbf{x}\_t
\+
k^{eff}\_t\Big(
\gamma(\mathbf{x}^\*-\mathbf{x}\_t)
\+
m\_t(\mathbf{F}\_T+\mathbf{F}\_R)
\Big)
}
]

This nails your inversion *without* exploding or making “rigidity” accidentally mean “move more.”

***

## 7) Pressure (m\_t) and a real (m\_{crit}) (derived)

Ignore the forcing targets for stability and look at contraction around the fixed point. With bounded targets, the “danger” is when the linear part stops contracting.

From the expanded update, the coefficient on (\mathbf{x}*t) becomes:
\[
\mathbf{x}*{t+1}
================

\Big(1-k^{eff}\_t(\gamma+2m\_t)\Big)\mathbf{x}\_t

*   \text{(bounded target terms)}
    ]

A sufficient contraction condition (scalar bound) is:
\[
\boxed{
|1-k^{eff}\_t(\gamma+2m\_t)| < 1
}
]
which implies:
\[
0 < k^{eff}\_t(\gamma+2m\_t) < 2
]

Solve for the “critical” (m) (upper edge):
\[
\boxed{
m\_{crit}(t)=\frac{1}{2}\left(\frac{2}{k^{eff}\_t}-\gamma\right)
}
]
Interpretation:

*   if rigidity rises ((\rho\uparrow \Rightarrow k^{eff}\downarrow)), then (m\_{crit}) **drops**: you become easier to destabilize under pressure. That matches trauma/anxiety dynamics pretty nicely.

***

## 8) Global ledger / memory (RAG) with salience = surprise

Ledger:
\[
\mathcal{L}={(\mathbf{x}*t,a\_t,o*{t+1},\epsilon\_t,\mathbf{c}*t)}*{t=0}^{N}
]

*   (\mathbf{c}\_t): context embedding at time (t)

Retrieve with similarity + recency + error salience:
\[
\mathcal{L}*{rel}=\text{top}*K\ \text{by}\\
\underbrace{\mathrm{sim}(\mathbf{c}*t,\mathbf{c}*{now})}*{\text{relevance}}
\cdot
\underbrace{e^{-\lambda\_r (now-t)}}*{\text{recency}}
\cdot
\underbrace{(1+\lambda\_\epsilon,\epsilon\_t)}\_{\text{salience/trauma}}
]

***

## 9) Formal properties (clean versions)

### Identity / historicity criterion

Identity exists when:

1.  (\gamma>0) (there is an attractor pull), and
2.  rigidity has nonzero mass over time:
    \[
    \int\_0^T \rho\_t,dt > \Theta
    ]
    Meaning: the system doesn’t just react; it *remembers itself under threat*.

### Will / impedance (environmental effort needed to move you)

Given the environment is trying to push via truth force (\mathbf{F}\_T), the effective response magnitude is proportional to (k^{eff}m\_t). So define impedance:
\[
\boxed{
W\_t = \frac{\gamma}{m\_t}\cdot \frac{1}{k^{eff}\_t}
}
]
Higher (W\_t) = more “will” / resistance: strong identity stiffness, low openness, low external gain.

***

## 10) LLM implementation notes (actually implementable)

*   **(\mathbf{x}\_t)**: a (d)-dim float vector stored in memory (not the prompt).
*   **(\mathbf{x}^\*)**: derived from system prompt values; encode once (embedding of values) or hand-build it.
*   **(T(I,\Delta I))**:
    *   (I\_t): user message + tool outputs
    *   (f\_{\text{parse}}): embedding → linear projection to (d)
    *   (\Delta I\_t): difference in embeddings or novelty score
*   **(R(\mathcal{A},\Phi,\mathcal{L}))**:
    *   generate candidate actions
    *   score with (Q) (constraints, success probability) and (S) (identity alignment, style)
*   **Outcome encoder (E(o))**: embed the observed outcome (user reaction / tool result) and project into (d).
*   **Rigidity (\rho)**: persistent scalar; increase with error, decay slowly when safe.
*   **Safety**: if (m\_t > m\_{crit}(t)), you can trigger “protect mode” (reduce actions, ask clarifying qs, retreat to identity-safe defaults).

***

## Symbol table (quick)

| Symbol            | Meaning                         |
| ----------------- | ------------------------------- |
| (\mathbf{x}\_t)   | agent state in (\mathbb{R}^d)   |
| (\mathbf{x}^\*)   | identity attractor              |
| (\gamma)          | identity stiffness              |
| (m\_t)            | external pressure/gain          |
| (\mathbf{x}^T\_t) | truth target state              |
| (\mathbf{x}^R\_t) | reflection target state         |
| (\rho\_t)         | rigidity/defensiveness (\[0,1]) |
| (k^{eff}\_t)      | effective openness/step size    |
| (\epsilon\_t)     | prediction error norm           |
| (\mathcal{L})     | memory ledger                   |

***

