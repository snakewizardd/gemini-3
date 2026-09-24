# FILAMENT — score

Original 12/8 blues-rock ballad. **Home key A minor; the solo modulates to D Dorian.**
Dotted quarter = 72 (bar = 3.333 s; 12 eighth-triplet pulses per bar). 64 bars + ring-out,
**3:38.95**. The score is code: [`src/composition.js`](src/composition.js). Nothing is quoted from
any existing song; all motifs below were written for this piece.

## Motifs

`r` = the motif's reference tonic (A4 = 69 in verses, D5 = 74 in the solo, A5 = 81 in the final chorus).

| Motif | Shape | Function |
|---|---|---|
| **X — the sigh** | (r−2) *bent a whole step up into* r, held · turn r+3 · r (pull-off) · r−2 · **fall** to r−5 (slide) with late vibrato | the antecedent "call"; the whole piece is about finishing it |
| **Y — the answer** | r−7 · r−5 (hammer) · r−2 · r−5 (pull) · r−9 (+28 c curl) · → r−12 (resolves) *or* stops on r−5 (half cadence) | consequent |
| **Z — the lift** | r+3 (+30 c curl) · r+5 *bent to* r+7 · r+10 · r+7 (pull) · r+5 · r+3 held | chorus antecedent, reaching upward |
| **cry** | bend · release · re-bend | only at cadential pressure (bars 10, 18, 26, 34, 58) |

Transformations: X is heard sigh-only (intro), with the fall withheld (intro, outro), displaced
by half a bar (verse II), with the turn inverted upward (bars 8, 24), transposed to D (solo),
sequenced upward as rising turn cells (bar 49), completed in silence as the climax (bar 51), in
the high octave (bar 54), and finally with its fall carried all the way down to the low tonic (bar 63).

## Harmony and form

| Section | Bars | Chords (one per bar; `a|b` = half bars) | Dynamics / tone | Lead |
|---|---|---|---|---|
| Intro | 0–3 | Am(add9) · Am(add9) · Fmaj7 · Esus4\|E7 | *pp*; clean neck pickup; rolled chord, sparse arpeggio, no drums (cymbal swell into the verse) | the sigh alone (unanswered); sigh + turn with the fall withheld; B → G♯ leading tone |
| Verse I | 4–11 | Am7 · Em7 · Dm9 · Am7 · Fmaj7 · Dm7 · Esus4\|E7 · Am7 | *p*; clean, warm, space between phrases; hats + rim, arpeggiated guitar that thins wherever the lead plays | X; Y (half cadence on E); pickup; X with the turn inverted up; cry B→C→B over Esus4; G♯ → A (hammer) resolution |
| Chorus I | 12–19 | Fmaj7 · G6 · Am7 · Am7/G · Dm9 · Fmaj7 · Esus4\|E7 · E7♯9 | *mf*; drive 2.4, neck+middle; strummed 12/8, ride, organ pad | Z; answer; X with curl on the blue third; pickup; Z high (G→A bend); Y; cry D→E; the ♯9 figure G (+32 c curl — the G/G♯ ambiguity) |
| Verse II | 20–27 | as Verse I | *p–mp*; snare replaces rim; organ enters low | X displaced by half a bar; double-stop answer (F+A); inverted turn; X with slower sigh bend; cry; resolution + pickup |
| Chorus II | 28–35 | as Chorus I, but bar 35 = **A7♯9 (break)** | *mf–f*; hotter drive; bar 35: one stab, then only the lead | Z (wider vibrato); X; Z high reaching A5; **break:** the sigh an octave up (G5→A5) alone, then C♯5 — the ear turns toward D |
| **Solo** | 36–51 | **D Dorian:** Dm7 · G9 · Dm7 · G9 · B♭maj7 · C(add9) · Dm7 · Dm7 · Gm7 · C · B♭maj7 · A7sus4\|A7 · Dm7 · G9 · B♭maj7 · **E7♯9 (stop-time)** | overdriven; **"woman tone"** at first (neck, tone knob 1.45 kHz resonant), opening bar by bar to full bite (5.4 kHz, middle pickup, drive 7 → 13); fast Leslie from bar 44 | call (high) / response (low) pairs: X in D with the curl on F; Dorian B♮ answers; high call with A5 bend (the maj7 of B♭); descending sequenced turns; **1.5 bars of silence** (bars 42–43); crying bends; C→C♯ half-step bend on A7 (question); X intensified; the turn sequenced upward; **summit D6** (highest note of the work, bar 50); **bar 51: the band stops — the lead bends G5 → G♯5 (the ♯9 resolved to the major third) → A5 in silence**, holding into the final chorus |
| Final chorus | 52–59 | as Chorus I | *f → mf*; drive 4.5; ignition | the held A5 releases; X in the high octave (A5); Z; descending home to A4; cry; ♯9 figure |
| Outro | 60–63 | Am9 · Fmaj7 · Esus4\|E7 (*ritardando*) · **Am(add9)** | *p → pp*; clean again; half-time ride; tom roll under the rit. | X with the fall withheld again; Y stops on C (curl); B3 → G♯3 … → **A3**: the fall of X finally completed, at the bottom, as the last note. Chord rolled, rings 4.4 s, then hand-muted. |

Harmonic pressure (0–1, used by both the image and the analysis): tonic 0.06–0.08 · IV/iv ≈ 0.3 · Esus4 0.55 · E7 0.66 · A7♯9 0.82 · E7♯9 0.88 (1.0 at the stop).
Tension curve per bar is in `TENSION` (0.06 at the start → 1.0 at bar 51 → 0.08 at the end).

## Articulation rules (phrase function, not decoration)

- **Microtonal curls (+26…+35 c)** only on blue thirds: C over A minor, F over D minor, G over E7♯9.
- **Whole-step bends** land phrase goals (the sigh; Z's peak). **Half-step bends** ask questions (C→C♯ on A7, A→B♭ on B♭maj7).
- **Vibrato**: only on phrase-final sustains; onset delayed 0.3–2.4 s; depth grows across the form (0.2 → 0.62 semitones); `up` (finger vibrato above pitch) on fretted notes, `sym` on held bends.
- **Hammer / pull-offs** inside turns; **slides** into falls.
- **Timing**: lead laid back 8–24 ms (least in the solo), deterministic ±7 ms jitter; rhythm ±4 ms; drums ±3 ms. Rubato only at bar 51 (+15 % on the held bend) and the outro *ritardando*.
- **Accompaniment responds**: the verse arpeggios drop their upper notes and soften wherever the lead has an onset; strums duck under lead onsets.

## Sound (String Engine, extended)

Lead, rhythm and bass are Karplus–Strong strings in the AudioWorklet (`filament-string`):
triangle + pick-comb noise excitation, velocity-scaled pick click, T60-tuned loop gain
(compensated for the loss filter), shaped bends, delayed vibrato, pickup-position comb.
Lead chain: neck/middle pickup blend → tone knob → asymmetric tube preamp → tone stack → power
tube → cab. Space: deterministic FDN hall + tape echo. Organ: tonewheel drawbars (one PeriodicWave
per note) through a Leslie tremolo. Drums: synthesized. Master: −14.0 LUFS, −1.5 dBTP, 24-bit.
