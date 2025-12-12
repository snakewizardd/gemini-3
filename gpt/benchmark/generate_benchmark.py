import csv
from dataclasses import dataclass
from typing import Optional

@dataclass
class TestCase:
    question: str
    expected_response: str
    test_method: str
    passing_score: Optional[int] = None

test_cases = [
    TestCase(
        question="""Design a browser-based audio synthesis architecture that generates all sound mathematically at runtime with zero pre-recorded samples or audio assets. The system should physically model plucked string vibration using the wave equation and Karplus-Strong variants, producing guitar-like timbres from pure mathematics. Address: (1) the differential equations governing string displacement and how boundary conditions produce harmonic spectra, (2) Web Audio API architecture including AudioWorklet for sample-by-sample processing and scheduling strategies to avoid glitches, (3) how damping coefficients, string tension, and excitation position map to timbral parameters a composer can control, (4) the philosophical implications — what does it mean that no recording of a physical instrument is required, that the sound is generated rather than reproduced? Provide implementation architecture and explain how a composer's mindset differs when the instrument itself is a mathematical object they can modify.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Formalize a theory of agency for dynamical systems where the central problem is identity preservation under pressure. Traditional state estimation (Kalman filtering) treats uncertainty as noise to be filtered out. But for an agent — an entity with selfhood — there is something to preserve beyond accurate state estimates: coherence of identity through time, under adversarial conditions, resource scarcity, or entropic dissolution. Define mathematically what 'identity' means in this context (not a label, but a dynamical invariant the system works to maintain). Construct state equations that include identity variables alongside physical state. Derive an objective function that balances task performance (survival, goal achievement) with identity preservation. Show a scenario where this formulation produces qualitatively different decisions than classical optimal control. What does it mean for an algorithm to 'want' to remain itself?""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Articulate and defend the philosophical position that complex aesthetic phenomena — the expressiveness of a flamenco guitar, the tension in a Wagner climax, the groove of electronic dance music — can emerge from well-chosen mathematical structures executed at runtime. This is not the claim that music can be analyzed mathematically (obvious) but the stronger claim that the generative source can be pure formalism: differential equations, control systems, dynamical processes. Address: What is gained when art 'runs' rather than exists as a fixed artifact? What is the relationship between constraint and creativity when the constraint is physical law (modeled)? How does this position handle the objection that mathematical generation is cold, mechanical, lacking human expressiveness? Provide concrete examples of how specific mathematical structures produce specific aesthetic effects — not metaphorically but causally.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Write a complete JavaScript/Web Audio API system that composes and synthesizes a musical piece entirely at runtime from mathematical first principles. Requirements: (1) All timbres must be generated from waveform mathematics — physical modeling of strings, modal synthesis, or waveshaping — with no samples loaded. (2) Harmonic progressions must emerge from formal rules (voice leading constraints, tension functions, Markov processes over chord states) rather than hardcoded sequences. (3) The piece must exhibit macro-structure (tension, release, climax, resolution) that emerges from system dynamics rather than explicit programming of sections. (4) Include extensive comments explaining the causal chain from each mathematical choice to its perceptual/aesthetic consequence. The code should demonstrate that complex musicality requires no irreducible magic — only well-chosen equations.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""There exists a deep structural connection between: (a) physical modeling synthesis where sound emerges from differential equations of vibrating systems, (b) agent-based decision systems where behavior emerges from optimization under uncertainty with identity constraints, (c) adaptive trading strategies where position sizing responds to multi-timeframe market dynamics, and (d) generative art where aesthetic form emerges from executed formalism. Identify the common mathematical and philosophical substrate unifying these domains. What are the shared primitives (state spaces, dynamics, objective functions, constraints)? Why does insisting on first-principles derivation rather than heuristic tuning produce qualitatively different results? Propose a unified formal framework where a 'composition' in one domain maps structurally to solutions in the others.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Design an agent-based simulation where entities forage for resources in a hostile environment while maintaining identity coherence. The key formal challenge: define 'identity' not as a label or fixed property but as a dynamical invariant — a quantity or structure the agent's decisions work to preserve, analogous to how a thermostat preserves temperature or a gyroscope preserves orientation. Specify: (1) The state space, including physical variables (position, energy) and identity variables (what are they? how do they evolve?). (2) Environmental pressures that threaten identity dissolution (scarcity, predation, noise, assimilation pressure). (3) The decision rule: how the agent chooses actions that balance survival with selfhood preservation. (4) Emergent phenomena: what collective behaviors arise when agents with identity-preservation objectives interact? (5) The philosophical payoff: what does this model teach us about the nature of agency, autonomy, and self?""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Construct a mathematical framework for understanding timbre as the solution to a physical differential equation rather than as a spectral fingerprint. Start from the wave equation for a vibrating string with realistic boundary conditions (bridge impedance, nut reflection, fret contact). Derive how the initial excitation (pluck position, velocity profile) determines the mixture of harmonics. Show how damping (frequency-dependent, material-based) shapes the amplitude envelope of each partial independently. Explain how nonlinearities (string stretching, soundboard coupling) introduce the subtle inharmonicities that distinguish living sound from sterile synthesis. Then address: if we can derive all of this, what is the ontological status of the resulting 'sound'? Is a guitar tone generated from equations the 'same' as one from a wooden instrument? What does identity mean for a timbre?""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Formalize trading as a control theory problem where the system must maintain 'strategic identity' under market pressure. Define: (1) State variables spanning multiple timeframes (tick, minute, hour, day) capturing price, volatility regime, momentum, and drawdown. (2) Control inputs: position size, direction, and hedge ratios. (3) Dynamics: how state evolves including regime-switching and feedback from the agent's own positions. (4) Objective function that balances return maximization with drawdown management and — critically — strategic coherence (not abandoning a valid strategy under temporary adversity vs. recognizing genuine regime change). (5) The formal analog to 'identity preservation': what does it mean for a trading system to remain itself through a drawdown? How is this different from simple risk management? Derive the optimal control law and discuss when this formulation outperforms standard Kelly/mean-variance approaches.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Create a complete taxonomy of how mathematical structure produces aesthetic effect in generative music. For each mechanism, specify: the formal apparatus (equations, algorithms, constraints), the perceptual result (what the listener experiences), and the compositional technique (how a composer exploits it). Cover at minimum: (1) Spectral evolution — how time-varying filter coefficients create timbral motion. (2) Harmonic field dynamics — how movement through pitch-class space creates tension/release. (3) Rhythmic entrainment — how coupled oscillators produce groove. (4) Stochastic variation — how controlled randomness creates humanization vs. chaos. (5) Emergent form — how macro-structure (phrases, sections, climax) arises from local rules. (6) Physical modeling expressiveness — how performance parameters (pluck velocity, position, damping) map to emotional intensity. This taxonomy should function as an engineering manual for mathematical aesthetics.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""A skeptic argues: 'Algorithmic and generative art is an interesting technical exercise but fundamentally limited. Mathematics produces patterns; humans produce meaning. The expressiveness of a master guitarist comes from embodied experience, emotion, intention — things that cannot be captured in equations. At best, generative systems produce impressive simulations that lack authentic artistic content.' Respond to this critique from within the generative formalism paradigm. Concede what is valid in the objection. Then argue: What does 'meaning' mean, and why should it require biological substrate? How does the generative paradigm actually address expression, intention, and emotional content — not by ignoring them but by formalizing them? Where are the genuine current limitations vs. limitations in principle? What would it take to fully rebut the skeptic — and is that goal even coherent?""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Derive a state-space model for a target tracking system where the target is not a passive object following stochastic dynamics but an agent with intentions — specifically, an agent attempting to evade the tracker while preserving its own operational coherence. Classical tracking (Kalman, extended Kalman, particle filters) assumes the target's motion is generated by a known dynamics model plus noise. But an evasive agent chooses actions to defeat prediction while maintaining its ability to achieve goals. Formalize: (1) The target's decision problem: minimize trackability while preserving goal-pursuit capability. (2) The tracker's inference problem: estimate state while modeling the target's agency. (3) The resulting game-theoretic structure. (4) How tracking performance differs when the tracker correctly models agency vs. assumes passive dynamics. Show mathematically why 'identity preservation' in the target's objective function is not merely evasion but something richer.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Design a real-time visualization system (WebGL/Three.js) for mathematically-generated music that reveals formal structure rather than producing arbitrary audio-reactive graphics. The constraint: every visual element must correspond to a specific mathematical object in the synthesis — not 'frequency drives color' loosely, but precise mapping where watching teaches you about the generative process. Address: (1) How to visualize the physical state of modeled vibrating strings (displacement, velocity field, mode shapes). (2) How to represent harmonic relationships spatially (pitch space, chord geometry, voice leading paths). (3) How to show compositional logic (tension functions, formal boundaries, motivic development). (4) The design philosophy: visualization as pedagogy for generative formalism, making the mathematics visible. (5) Implementation architecture for real-time performance. The result should let a viewer understand how the music is being made by watching it.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Propose and develop a unified formal ontology where 'compositions' exist simultaneously in multiple domains: as sound synthesis specifications, as agent decision policies, as trading strategies, and as mathematical objects. The ontology should define: (1) Primitive elements (what are the atoms of this formal universe?). (2) Composition operators (how do primitives combine?). (3) Domain projections (how does an object in the unified space manifest as music vs. agent behavior vs. trading logic?). (4) Invariants under projection (what properties are preserved across domains?). (5) The aesthetic dimension: what makes some objects in this space 'beautiful' and others not — can we formalize this? This is speculative formal philosophy: you are constructing a mathematical universe where art, agency, and strategy are faces of the same structure. Argue for why this unification is meaningful rather than merely notational.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Historically situate and extend the lineage: Xenakis applied stochastic processes to composition. Chowning discovered FM synthesis while modeling vibrato. The spectralists (Grisey, Murail) derived harmony from acoustic analysis. Roads and others developed granular synthesis. Physical modeling (Karplus-Strong, waveguides) enabled virtual instruments. Now articulate what the next position in this sequence should be — a synthesis framework where: all sound is generated from first-principles physics at runtime, compositional logic emerges from dynamical systems rather than explicit notation, the instrument and the piece are unified in a single mathematical object, and the system runs in a browser with no assets. What specific technical and conceptual advances does this require beyond existing work? What becomes possible that was not possible before? What is the aesthetic payoff — not just 'we can do it' but 'it produces new artistic possibilities'?""",
        expected_response="",
        test_method="GeneralQuality"
    ),
    TestCase(
        question="""Write a formal specification for what it would mean to 'solve' generative music — to have a system that, given high-level aesthetic intent (mood, genre, narrative arc, emotional trajectory), produces complete musical works with the sophistication of expert human composers, synthesized in real-time from mathematical first principles. Specify: (1) The input representation: how is aesthetic intent formalized? (2) The architecture: what components are required (physical modeling synthesis, compositional logic, performance modeling, form generation)? (3) The evaluation criteria: what distinguishes success from failure — and who/what judges? (4) The current gaps: what don't we know how to do yet? (5) The philosophical questions: if such a system existed, would it be 'composing'? Does the question matter? This is a research agenda for the field of mathematical aesthetics as practice.""",
        expected_response="",
        test_method="GeneralQuality"
    ),
]

output_file = "mathematical_aesthetics_eval.csv"

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['question', 'expectedResponse', 'testMethodType', 'passingScore'])
    
    for tc in test_cases:
        writer.writerow([
            tc.question,
            tc.expected_response,
            tc.test_method,
            tc.passing_score if tc.passing_score else ''
        ])

print(f"Generated {len(test_cases)} self-contained master prompts")
print("\nCore domains tested:")
domains = [
    "1. Physical modeling synthesis architecture",
    "2. Agency/identity as dynamical invariant", 
    "3. Philosophy of executable aesthetics",
    "4. Full implementation challenge",
    "5. Cross-domain unification",
    "6. Agent simulation with identity",
    "7. Timbre as differential equation",
    "8. Trading as control theory",
    "9. Math→aesthetics taxonomy",
    "10. Defense against skeptic",
    "11. Adversarial tracking with agency",
    "12. Visualization of formal structure",
    "13. Unified formal ontology",
    "14. Historical positioning + extension",
    "15. Research agenda specification"
]
for d in domains:
    print(f"  {d}")