"""
creator_engine.py - generate a reusable music/video brief from gemini-3 fundamentals.
"""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from dataclasses import dataclass
from typing import Dict, List


PROFILE_LIBRARY: Dict[str, Dict[str, object]] = {
    "signature": {
        "description": "Front your own ideaship: mathematical, authored, identity-heavy.",
        "repo_refs": [
            "second/gemini_guitar_opus.html",
            "second/metal_guitar_engine.html",
            "opus/lilypond.html",
            "whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md",
        ],
        "style_core": "self-composing guitar engine, procedural synthesis, visible mathematical authorship",
        "instrumentation": "electric guitar, synthetic harmonics, sub bass, light percussive motion, spacious delay",
        "visual_language": "reactive particles, harmonic geometry, stem-aware color motion, authored camera behavior",
        "delivery_note": "Lead with authorship and engine design, not normality.",
    },
    "romantic": {
        "description": "Personal, warm, date-safe, emotionally legible.",
        "repo_refs": [
            "opus/romance.html",
            "second/golden_hour_song.html",
            "second/wonderful_tonight.html",
            "opus/evening.html",
        ],
        "style_core": "intimate melody, harmonic clarity, warmth before spectacle",
        "instrumentation": "acoustic guitar, soft piano, warm pad, restrained bass, subtle strings",
        "visual_language": "slow bloom, horizon glow, ripple trails, album-art led palette",
        "delivery_note": "Keep the first contact human and melodic; let the cleverness reveal itself later.",
    },
    "cinematic": {
        "description": "Broader, elegant, filmic, useful for shareable videos.",
        "repo_refs": [
            "second/golden_hour_song.html",
            "opus/fullclassic.html",
            "opus/festival.html",
            "second/time_fracture_zimmer.html",
        ],
        "style_core": "narrative arc, emotional lift, orchestral scale, clear section changes",
        "instrumentation": "piano, strings, synth pad, low percussion, brass swells, sub support",
        "visual_language": "big gradients, motion pulses, widescreen timing, section-aware transitions",
        "delivery_note": "Optimize for rewatchability and emotional lift.",
    },
    "playful": {
        "description": "Lighter, charming, easier to share early in a relationship.",
        "repo_refs": [
            "opus/jellyfish.html",
            "opus/evening.html",
            "opus/music-composer.html",
            "second/beatles.html",
        ],
        "style_core": "bright, memorable, affectionate, low-pressure",
        "instrumentation": "clean guitar, bells, soft synth, light groove, singable melody",
        "visual_language": "friendly motion, rounded shapes, light color cycling, simple hooks",
        "delivery_note": "Keep it charming and specific, not overwhelming.",
    },
    "techno": {
        "description": "Bass-led, consciousness-inducing, body-first but spiritually charged.",
        "repo_refs": [
            "second/housebeat.html",
            "opus/annihilate.html",
            "second/sensorium.html",
            "whatami/STRING_ENGINE_TECHNICAL_REFERENCE.md",
        ],
        "style_core": "hypnotic techno propulsion, sub pressure, ritual atmosphere, engineered transcendence",
        "instrumentation": "dominant sub bass, heavy kick, rolling toms, metallic percussion, evolving synth pulse, breath-like pad, sparse mantra vox",
        "visual_language": "kick-synced pulse fields, low-end-driven camera motion, spectral bloom, sacred geometry, restrained strobes, stem-reactive color systems",
        "delivery_note": "The bass has to command the body while the upper layers open the headspace.",
        "prompt_emphasis": "Treat the kick and bass relationship as sacred. Make the low end physical, chest-first, and continuous. Use vocals sparingly, like a mantra or invocation, only if they deepen the trance. Prioritize hypnosis, motion, and altered-state induction over pop-song structure.",
    },
}


MODE_FLAVORS: Dict[str, Dict[str, str]] = {
    "major": {
        "mood": "open, reassuring, resolved",
        "harmony": "stable cadences, bright lift, strong tonic identity",
    },
    "minor": {
        "mood": "intimate, vulnerable, serious",
        "harmony": "deeper tension, softer resolution, emotional gravity",
    },
    "aeolian": {
        "mood": "hypnotic, nocturnal, devotional",
        "harmony": "natural minor gravity, circular tension, ritual descent and lift",
    },
    "dorian": {
        "mood": "thoughtful, alive, authored",
        "harmony": "minor center with lift, elegant motion, modern soul",
    },
    "lydian": {
        "mood": "dreamlike, elevated, luminous",
        "harmony": "floating brightness, suspended wonder, upward pull",
    },
    "mixolydian": {
        "mood": "warm, grounded, groove-forward",
        "harmony": "strong hooks, less gravity, more motion",
    },
    "phrygian": {
        "mood": "dark, exotic, intense",
        "harmony": "tight tension, dramatic color, ceremonial energy",
    },
}


KEY_PALETTES: Dict[str, List[str]] = {
    "C": ["ivory", "gold", "soft blue"],
    "Db": ["amber", "rose", "ivory"],
    "D": ["sunlit orange", "cream", "teal"],
    "Eb": ["wine", "bronze", "dust pink"],
    "E": ["cyan", "gold", "midnight blue"],
    "F": ["silver", "lavender", "mist"],
    "F#": ["chrome", "ice blue", "violet"],
    "Gb": ["chrome", "ice blue", "violet"],
    "G": ["forest green", "gold", "charcoal"],
    "Ab": ["plum", "rose gold", "smoke"],
    "A": ["coral", "pearl", "deep navy"],
    "Bb": ["sepia", "brass", "cream"],
    "B": ["neon lime", "black", "silver"],
}


SIGNATURE_GUIDANCE: Dict[str, str] = {
    "low": "Favor direct melody, a simple lyric image, and restrained harmonic surprises.",
    "medium": "Keep the hook accessible, but let one or two authored harmonic or visual moves define the piece.",
    "high": "Front the system design, richer harmony, and stronger math-to-visual coupling.",
}


MODE_ALIASES: Dict[str, str] = {
    "major": "major",
    "ionian": "major",
    "minor": "minor",
    "aeolian": "aeolian",
    "natural-minor": "aeolian",
    "natural_minor": "aeolian",
}


@dataclass
class Request:
    profile: str
    recipient: str
    occasion: str
    key: str
    mode: str
    tempo: int
    motif: str
    visual_seed: str
    signature_level: str
    title_hint: str
    notes: str
    fmt: str


def humanize_slug(value: str) -> str:
    return value.replace("-", " ")


def normalize_key(raw_key: str) -> str:
    cleaned = raw_key.strip().replace(" major", "").replace(" minor", "")
    cleaned = cleaned.replace("sharp", "#").replace("flat", "b")
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned[0].upper() + cleaned[1:]
    aliases = {"C#": "Db", "D#": "Eb", "G#": "Ab", "A#": "Bb"}
    return aliases.get(cleaned, cleaned)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"


def title_candidates(req: Request) -> List[str]:
    base_target = req.recipient or "you"
    motif = req.motif.title() if req.motif else ""
    title_hint = req.title_hint.title() if req.title_hint else ""

    candidates = []
    if title_hint:
        candidates.append(title_hint)
    if req.occasion == "proposal":
        candidates.append(f"For {base_target}")
        candidates.append(f"{base_target}, Stay")
    elif req.occasion == "first-gift":
        candidates.append(f"Golden Hour For {base_target}")
        candidates.append(f"Letter To {base_target}")
    else:
        candidates.append(f"{req.key} {req.mode.title()} For {base_target}")

    if motif:
        candidates.append(motif)

    deduped = []
    seen = set()
    for item in candidates:
        if item and item.lower() not in seen:
            deduped.append(item)
            seen.add(item.lower())
    return deduped[:4]


def build_music_brief(req: Request, profile_data: Dict[str, object]) -> Dict[str, object]:
    palette = [item.strip() for item in req.visual_seed.split(",") if item.strip()]
    if not palette:
        palette = KEY_PALETTES.get(req.key, ["gold", "black", "white"])

    mode_data = MODE_FLAVORS.get(req.mode, MODE_FLAVORS["major"])

    summary = (
        f"Create an original piece for {humanize_slug(req.occasion)} in {req.key} {req.mode} at {req.tempo} BPM. "
        f"The emotional center should feel {mode_data['mood']}. "
        f"Profile lane: {req.profile}. Signature level: {req.signature_level}."
    )

    return {
        "summary": summary,
        "motif": req.motif,
        "instrumentation": profile_data["instrumentation"],
        "style_core": profile_data["style_core"],
        "harmony_direction": mode_data["harmony"],
        "signature_guidance": SIGNATURE_GUIDANCE[req.signature_level],
        "prompt_emphasis": profile_data.get(
            "prompt_emphasis",
            "Keep the arrangement emotionally clear, with a memorable hook in the first 20 seconds. Avoid generic filler lyrics. Use one vivid image that returns in the chorus. Build toward a cinematic but intimate lift.",
        ),
        "visual_palette": palette,
        "repo_dna": profile_data["repo_refs"],
        "notes": req.notes,
    }


def build_suno_prompt(req: Request, brief: Dict[str, object]) -> str:
    recipient_line = (
        f"Make it feel personally addressed to {req.recipient}. "
        if req.recipient
        else "Make it feel personally dedicated to one specific person. "
    )
    motif_line = f"Center the lyric imagery on {req.motif}. " if req.motif else ""
    notes_line = f"Extra note: {req.notes}. " if req.notes else ""

    return (
        f"Original song, {req.profile} lane, {req.key} {req.mode}, {req.tempo} BPM. "
        f"{recipient_line}"
        f"{motif_line}"
        f"Use {brief['instrumentation']}. "
        f"Core feel: {brief['style_core']}. "
        f"Harmonic direction: {brief['harmony_direction']}. "
        f"{brief['signature_guidance']} "
        f"{brief['prompt_emphasis']} "
        f"{notes_line}"
    ).strip()


def build_visual_brief(req: Request, brief: Dict[str, object], profile_data: Dict[str, object]) -> str:
    palette = ", ".join(brief["visual_palette"])
    return textwrap.dedent(
        f"""\
        Use album-art-led colors: {palette}.
        Visual language: {profile_data['visual_language']}.
        Stem mapping:
        - Vocal or lead melody: brightest ribbon or ripple layer.
        - Harmonic bed: slow background bloom and gradient drift.
        - Bass: horizon pulse and low-center expansion.
        - Percussion: transient flashes only on meaningful hits.
        - Signature instrument: give it the most detailed particle choreography.
        Keep edits synchronized to section changes, not random cuts.
        """
    ).strip()


def build_delivery_note(req: Request, profile_data: Dict[str, object]) -> str:
    occasion_lines = {
        "proposal": "Aim for 2:30 to 3:15. The emotional landing should feel committed, not theatrical.",
        "first-gift": "Aim for 1:45 to 2:40. Keep it specific, warm, and easy to replay.",
        "date-night": "Aim for 2:00 to 3:00. Make it flattering without sounding generic.",
        "portfolio": "Aim for 1:30 to 2:30. Lead with the strongest authored idea fast.",
    }
    base = occasion_lines.get(
        req.occasion,
        "Aim for 2:00 to 3:00 and make the core idea obvious quickly.",
    )
    return f"{base} {profile_data['delivery_note']}"


def render_markdown(req: Request, brief: Dict[str, object], profile_data: Dict[str, object]) -> str:
    titles = title_candidates(req)
    lines = [
        "# Creator Brief",
        "",
        "## Lane",
        f"- Profile: {req.profile}",
        f"- Description: {profile_data['description']}",
        f"- Signature level: {req.signature_level}",
        "",
        "## Title Candidates",
        f"- {titles[0]}",
        f"- {titles[1] if len(titles) > 1 else titles[0]}",
        f"- {titles[2] if len(titles) > 2 else titles[0]}",
        "",
        "## Music Brief",
        f"- Summary: {brief['summary']}",
        f"- Motif: {brief['motif'] or 'none provided'}",
        f"- Instrumentation: {brief['instrumentation']}",
        f"- Style core: {brief['style_core']}",
        f"- Harmony direction: {brief['harmony_direction']}",
        f"- Signature guidance: {brief['signature_guidance']}",
        "",
        "## Repo DNA",
        f"- {profile_data['repo_refs'][0]}",
        f"- {profile_data['repo_refs'][1]}",
        f"- {profile_data['repo_refs'][2]}",
        f"- {profile_data['repo_refs'][3]}",
        "",
        "## Suno Prompt",
        build_suno_prompt(req, brief),
        "",
        "## Visualizer Handoff",
        build_visual_brief(req, brief, profile_data),
        "",
        "## Delivery Note",
        build_delivery_note(req, profile_data),
    ]
    return "\n".join(lines)


def render_json(req: Request, brief: Dict[str, object], profile_data: Dict[str, object]) -> str:
    payload = {
        "request": req.__dict__,
        "title_candidates": title_candidates(req),
        "music_brief": brief,
        "suno_prompt": build_suno_prompt(req, brief),
        "visualizer_handoff": build_visual_brief(req, brief, profile_data),
        "delivery_note": build_delivery_note(req, profile_data),
    }
    return json.dumps(payload, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a gemini-3 music/video brief for Suno and stem-driven visual workflows."
    )
    parser.add_argument("--profile", choices=sorted(PROFILE_LIBRARY.keys()), default="romantic")
    parser.add_argument("--recipient", default="")
    parser.add_argument("--occasion", default="first-gift")
    parser.add_argument("--key", default="Db")
    parser.add_argument("--mode", default="major")
    parser.add_argument("--tempo", type=int, default=84)
    parser.add_argument("--motif", default="")
    parser.add_argument("--visual-seed", default="")
    parser.add_argument("--signature-level", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--title-hint", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--list-profiles", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_profiles:
        for name, data in PROFILE_LIBRARY.items():
            print(f"{name}: {data['description']}")
        return

    key = normalize_key(args.key)
    raw_mode = args.mode.strip().lower().replace(" ", "-")
    mode = MODE_ALIASES.get(raw_mode, raw_mode)
    if mode not in MODE_FLAVORS:
        raise SystemExit(
            f"Unsupported mode '{args.mode}'. Supported modes: {', '.join(sorted(MODE_FLAVORS))}"
        )

    req = Request(
        profile=args.profile,
        recipient=args.recipient.strip(),
        occasion=slugify(args.occasion),
        key=key,
        mode=mode,
        tempo=args.tempo,
        motif=args.motif.strip(),
        visual_seed=args.visual_seed.strip(),
        signature_level=args.signature_level,
        title_hint=args.title_hint.strip(),
        notes=args.notes.strip(),
        fmt=args.format,
    )

    profile_data = PROFILE_LIBRARY[req.profile]
    brief = build_music_brief(req, profile_data)

    if req.fmt == "json":
        print(render_json(req, brief, profile_data))
    else:
        print(render_markdown(req, brief, profile_data))


if __name__ == "__main__":
    main()
