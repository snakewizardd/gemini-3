# FILAMENT — storyboard

**Premise.** The inside of the amplifier, at night, at the scale of a cathedral. An obsidian
floor that is also a black mirror. Rows of vacuum tubes stand on it in a strict grid (domain
repetition). Above the central aisle, six strings of liquid metal run from the bridge (near,
`z = 2`) to the nut (far, `z = 40`). The music is the current running through this machine.
The film's arc is thermal: **cold → warming → burning → afterglow → cooling → dark.**
One tube — the *voice tube*, the A tube nearest the verse hand position — is the first light
and the last to go out.

Everything is one continuous world and one pure function `draw(gl, t)`; no 2D canvas, no
images, no text in the frame. All light is emitted by the filaments, the plates and the strings.

## Palette

| Name | Hex | Use |
|---|---|---|
| Obsidian | `#050407` | floor, chassis, sockets, the ground state |
| Smoke | `#120C0A` | fog / air between rows |
| Moon-violet | `#2A2440` | a single dim rim light from above so black stays readable |
| Ember | `#7A1E05` | a cold filament, red-plating in overdrive |
| Amber | `#FF8A1E` | warm filament, clean tone |
| Gold | `#FFC35A` | strings, full chorus light |
| White-hot | `#FFF1D6` | strike points at high velocity, the climax |

Colour temperature is not decoration: filament colour is a black-body ramp driven by each
tube's current (brightness), shifted hotter by harmonic pressure.

## Motion language

- The camera never drifts randomly. It **follows the fretting hand**: its z-position tracks a
  smoothed average of where the lead notes are fretted (fret → `z = 2 + 38·2^(−fret/12)`).
- Camera speed is proportional to musical activity; when the lead rests, the camera almost
  stops. Silence *suspends* the world.
- Only one hard cut in the film: the solo downbeat, hidden inside the darkness of the break.

## Scenes (one per section, transitions on section boundaries)

| Section | Bars / time | Scene | Transition in |
|---|---|---|---|
| Intro | 0–3 · 0:00–0:14 | **Cold chassis.** Near-black; camera low on the floor, looking down the aisle at the voice tube. The unanswered sigh (G→A bend) pushes one string sideways and makes the voice tube's filament begin to glow. | fade from black (first 1.2 s is silence) |
| Verse I | 4–11 · 0:14–0:41 | **Close to the string.** Camera at string height beside the hand position; strike points flare where notes are fretted; the A-minor tubes glow dim amber. | 4 s dolly |
| Chorus I | 12–19 · 0:41–1:08 | **The row.** Camera rises and pulls back, revealing the rows; strummed chords ignite tubes by pitch class. | 3 s crane |
| Verse II | 20–27 · 1:08–1:35 | **Mirror.** Back at string height from the other side of the aisle; the row stays faintly warm (memory of the chorus). | 3 s |
| Chorus II | 28–35 · 1:35–2:01 | **The field.** Higher and wider; outer columns begin to light. Bar 35 (the break): the band stops — every chord-light drains, only the lone lead string burns. Camera freezes. | 3 s |
| Solo | 36–51 · 2:01–2:55 | **Overdrive.** Hard cut (in darkness) into the aisle at the nut end; the camera travels toward the bridge, its speed = tension. Plates **red-plate** (the real glow of overdriven tubes), the strings go molten (fBM flow), heat haze rises. Bar 51 stop-time: the world stops; the G→G♯→A climax bend drags the string sideways a full string-spacing; on the arrival at A an ignition wave runs outward from the strike point and lights **every** tube. | cut |
| Final chorus | 52–59 · 2:55–3:21 | **Afterglow.** Crane up over the incandescent field; everything warm, strings gold. | 3.5 s crane |
| Outro | 60–63 · 3:21–3:39 | **Cooling.** Tubes go dark from the outside in, toward the voice tube; the camera descends back to the intro framing. The last low A lights the voice tube once more; the hand-mute kills the chord and its filament cools to black. Final image: black. | whole outro |

## Musical parameter → visual mapping (the shared state)

| Musical parameter (source) | Visual consequence | Why |
|---|---|---|
| Lead note **onset / velocity** (`events.json`) | Strike-point light on that note's string at that note's fret position; white-hot at high velocity | the note *lives* somewhere physical |
| **Pitch / fret** (`str`, `fret`) | Position along the string; higher register = nearer the bridge = nearer the camera in the solo | the solo's climb is a journey |
| **Bend** (cents, from the same stage curves the engine plays) | Lateral displacement of the string, triangular from nut → finger → bridge; 200 c = one string spacing | a real bend physically pushes the string |
| **Vibrato** (depth, rate, onset) | The bend displacement oscillates at the vibrato rate with the same delayed onset | vibrato is visible hand motion |
| **Slide** | The strike light travels along the string over the slide time | |
| Sustain / envelope | Strike light widens and flows along the string while the note rings | current flowing |
| **Chord tones** (rhythm, organ, bass) | Tubes lit by pitch class; rows are ordered by the **circle of fifths**, so consonant chords light compact clusters and altered chords scatter | harmonic pressure = spatial coherence |
| Score **tension** | How far the light spreads to the outer columns; camera speed in the solo | |
| **Drive** (solo tone arc) | Red-plating, molten strings, heat haze | the amp is literally working harder |
| **Silence** (breaks, rests) | Chord light drains, camera freezes | silence suspends the world |
| **Climax** (bar 51 bend arrival) | Ignition wave from the strike point across the whole field | the one transformation |
| **Resolution** (outro) | Cooling from the outside in, return to the intro framing, last filament out on the hand-mute | the premise resolves |
| `u_rms` (telemetry) | global breathing of fog scattering | |
| `u_sub_bass` | slow ripple rings in the obsidian mirror | |
| `u_lead_transients` (1.5–4.5 kHz) | string specular sheen | |
| `u_highs` | glints on tube glass | cymbals |
| `u_attack_transient` | chromatic aberration pulse (post pass) | pick strikes as optical shock |
