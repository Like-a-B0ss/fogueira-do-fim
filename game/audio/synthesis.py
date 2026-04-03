from __future__ import annotations

import math
import random
from array import array

import pygame


def build_sound_bank(audio) -> dict[str, list[pygame.mixer.Sound]]:
    return {
        "ui_confirm": [make_ui_confirm(audio, seed) for seed in (1, 2, 3)],
        "ui_focus": [make_ui_focus(audio, seed) for seed in (4, 5, 6)],
        "ui_back": [make_ui_back(audio, seed) for seed in (7, 8)],
        "ui_order": [make_ui_order(audio, seed) for seed in (9, 10)],
        "attack": [make_attack(audio, seed) for seed in (11, 12, 13)],
        "interact": [make_interact(audio, seed) for seed in (14, 15, 16)],
        "alert": [make_alert(audio, seed) for seed in (17, 18)],
        "impact_flesh": [make_impact_flesh(audio, seed) for seed in (19, 20, 21)],
        "impact_wood": [make_impact_wood(audio, seed) for seed in (22, 23, 24)],
        "impact_body": [make_impact_body(audio, seed) for seed in (25, 26, 27)],
        "transition_start": [make_transition_start(audio)],
        "transition_restart": [make_transition_restart(audio)],
        "transition_nightfall": [make_transition_nightfall(audio)],
        "transition_daybreak": [make_transition_daybreak(audio)],
        "step_camp": [make_step_camp(audio, seed) for seed in (31, 32, 33, 34)],
        "step_path": [make_step_path(audio, seed) for seed in (35, 36, 37, 38)],
        "step_forest": [make_step_forest(audio, seed) for seed in (39, 40, 41, 42)],
        "step_meadow": [make_step_meadow(audio, seed) for seed in (43, 44, 45, 46)],
        "step_swamp": [make_step_swamp(audio, seed) for seed in (47, 48, 49, 50)],
        "step_ruin": [make_step_ruin(audio, seed) for seed in (51, 52, 53, 54)],
        "ambient_bonfire": [make_bonfire_pop(audio, seed) for seed in (61, 62, 63, 64)],
        "ambient_night": [make_night_chirp(audio, seed) for seed in (65, 66, 67)],
        "ambient_day": [make_day_bird(audio, seed) for seed in (68, 69, 70)],
        "ambient_wind": [make_ambient_wind(audio, seed) for seed in (71, 72, 73)],
        "ambient_rain": [make_ambient_rain(audio, seed) for seed in (74, 75, 76)],
        "ambient_grove": [make_ambient_grove(audio, seed) for seed in (77, 78, 79)],
        "ambient_swamp": [make_ambient_swamp(audio, seed) for seed in (80, 81, 82)],
        "ambient_ruin": [make_ambient_ruin(audio, seed) for seed in (83, 84, 85)],
        "ambient_dread": [make_ambient_dread(audio, seed) for seed in (86, 87, 88)],
        "zombie_groan": [make_zombie_groan(audio, seed) for seed in (91, 92, 93)],
        "zombie_far": [make_zombie_far(audio, seed) for seed in (96, 97, 98)],
        "zombie_horde": [make_zombie_horde(audio, seed) for seed in (94, 95)],
        "music_calm": [make_music_calm(audio, seed) for seed in (101, 102)],
        "music_dread": [make_music_dread(audio, seed) for seed in (107, 108)],
        "music_threat": [make_music_threat(audio, seed) for seed in (103, 104)],
        "music_horde": [make_music_horde(audio, seed) for seed in (105, 106)],
    }


def osc(waveform: str, phase: float, rng: random.Random) -> float:
    if waveform == "sine":
        return math.sin(phase)
    if waveform == "triangle":
        return (2 / math.pi) * math.asin(math.sin(phase))
    if waveform == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    if waveform == "saw":
        cycle = phase / math.tau
        return 2.0 * (cycle - math.floor(cycle + 0.5))
    if waveform == "noise":
        return rng.uniform(-1.0, 1.0)
    return math.sin(phase)


def envelope(
    audio,
    index: int,
    frame_count: int,
    *,
    attack: float,
    decay: float,
    sustain_level: float,
    release: float,
    duration: float,
) -> float:
    total_env = attack + decay + release
    if total_env > duration and total_env > 0:
        scale = duration / total_env
        attack *= scale
        decay *= scale
        release *= scale

    attack_frames = max(1, int(attack * audio.sample_rate))
    decay_frames = max(0, int(decay * audio.sample_rate))
    release_frames = max(1, int(release * audio.sample_rate))
    sustain_frames = max(0, frame_count - attack_frames - decay_frames - release_frames)

    if index < attack_frames:
        return index / attack_frames

    offset = index - attack_frames
    if offset < decay_frames and decay_frames > 0:
        return 1.0 - (1.0 - sustain_level) * (offset / decay_frames)

    offset -= decay_frames
    if offset < sustain_frames:
        return sustain_level

    offset -= sustain_frames
    if release_frames <= 0:
        return 0.0
    return sustain_level * max(0.0, 1.0 - offset / release_frames)


def synth(audio, duration: float, layers: list[dict[str, float | str | tuple]]) -> pygame.mixer.Sound:
    frame_count = max(1, int(duration * audio.sample_rate))
    mix = [0.0] * frame_count

    for layer in layers:
        rng = random.Random(layer.get("seed", 0))
        start = float(layer.get("start", 0.0))
        layer_duration = float(layer.get("duration", duration - start))
        start_index = max(0, int(start * audio.sample_rate))
        length = min(frame_count - start_index, max(1, int(layer_duration * audio.sample_rate)))
        if length <= 0:
            continue

        phase = float(layer.get("phase", 0.0))
        waveform = str(layer.get("waveform", "sine"))
        start_freq = float(layer.get("start_freq", 440.0))
        end_freq = float(layer.get("end_freq", start_freq))
        volume = float(layer.get("volume", 0.5))
        attack = float(layer.get("attack", 0.005))
        decay = float(layer.get("decay", 0.05))
        sustain_level = float(layer.get("sustain_level", 0.35))
        release = float(layer.get("release", 0.05))
        vibrato_rate = float(layer.get("vibrato_rate", 0.0))
        vibrato_depth = float(layer.get("vibrato_depth", 0.0))
        harmonics = tuple(layer.get("harmonics", ()))

        for i in range(length):
            t = i / max(1, length - 1)
            freq = start_freq + (end_freq - start_freq) * t
            if vibrato_rate and vibrato_depth:
                freq *= 1.0 + math.sin(i / audio.sample_rate * math.tau * vibrato_rate) * vibrato_depth
            phase += math.tau * freq / audio.sample_rate
            sample = osc(waveform, phase, rng)
            for harmonic_mult, harmonic_gain in harmonics:
                sample += osc("sine", phase * harmonic_mult, rng) * harmonic_gain
            env = envelope(
                audio,
                i,
                length,
                attack=attack,
                decay=decay,
                sustain_level=sustain_level,
                release=release,
                duration=layer_duration,
            )
            mix[start_index + i] += sample * env * volume

    peak = max(0.001, max(abs(sample) for sample in mix))
    normalize = min(0.98 / peak, 1.0)

    pcm = array("h")
    for sample in mix:
        value = int(max(-32767, min(32767, sample * normalize * 32767)))
        if audio.channels == 2:
            pcm.append(value)
            pcm.append(value)
        else:
            pcm.append(value)
    return pygame.mixer.Sound(buffer=pcm.tobytes())


def make_ui_confirm(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.14,
        [
            {"waveform": "triangle", "start_freq": 760 + seed * 6, "end_freq": 1020 + seed * 8, "volume": 0.42, "attack": 0.003, "decay": 0.025, "sustain_level": 0.18, "release": 0.045, "harmonics": ((2.0, 0.12),), "seed": seed},
            {"waveform": "noise", "start": 0.0, "duration": 0.03, "volume": 0.08, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.012, "seed": seed * 13},
        ],
    )


def make_ui_focus(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.2,
        [
            {"waveform": "sine", "start_freq": 620 + seed * 4, "end_freq": 820 + seed * 7, "volume": 0.34, "attack": 0.002, "decay": 0.03, "sustain_level": 0.22, "release": 0.04, "seed": seed},
            {"waveform": "triangle", "start": 0.055, "duration": 0.13, "start_freq": 920 + seed * 5, "end_freq": 1260 + seed * 7, "volume": 0.28, "attack": 0.002, "decay": 0.024, "sustain_level": 0.2, "release": 0.05, "harmonics": ((2.0, 0.1),), "seed": seed * 17},
        ],
    )


def make_ui_back(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.18,
        [
            {"waveform": "triangle", "start_freq": 540 + seed * 5, "end_freq": 360 + seed * 3, "volume": 0.3, "attack": 0.002, "decay": 0.03, "sustain_level": 0.18, "release": 0.05, "seed": seed},
            {"waveform": "triangle", "start": 0.055, "duration": 0.08, "start_freq": 430 + seed * 3, "end_freq": 270 + seed * 2, "volume": 0.23, "attack": 0.002, "decay": 0.024, "sustain_level": 0.1, "release": 0.04, "seed": seed * 11},
        ],
    )


def make_ui_order(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.24,
        [
            {"waveform": "sine", "start_freq": 420 + seed * 3, "end_freq": 610 + seed * 4, "volume": 0.34, "attack": 0.008, "decay": 0.045, "sustain_level": 0.24, "release": 0.08, "vibrato_rate": 6.0, "vibrato_depth": 0.018, "seed": seed},
            {"waveform": "triangle", "start": 0.04, "duration": 0.1, "start_freq": 690 + seed * 5, "end_freq": 820 + seed * 4, "volume": 0.14, "attack": 0.003, "decay": 0.02, "sustain_level": 0.14, "release": 0.04, "seed": seed * 19},
        ],
    )


def make_attack(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.22,
        [
            {"waveform": "noise", "start_freq": 0.0, "end_freq": 0.0, "volume": 0.22, "attack": 0.001, "decay": 0.018, "sustain_level": 0.0, "release": 0.045, "seed": seed * 3},
            {"waveform": "saw", "start_freq": 340 + seed * 8, "end_freq": 120 + seed * 2, "volume": 0.34, "attack": 0.001, "decay": 0.02, "sustain_level": 0.06, "release": 0.05, "harmonics": ((2.0, 0.09),), "seed": seed},
            {"waveform": "sine", "start": 0.022, "duration": 0.11, "start_freq": 150 + seed * 3, "end_freq": 86 + seed * 2, "volume": 0.17, "attack": 0.002, "decay": 0.018, "sustain_level": 0.08, "release": 0.04, "seed": seed * 7},
        ],
    )


def make_interact(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.18,
        [
            {"waveform": "noise", "duration": 0.04, "volume": 0.11, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.015, "seed": seed * 5},
            {"waveform": "triangle", "start_freq": 480 + seed * 4, "end_freq": 660 + seed * 6, "volume": 0.28, "attack": 0.003, "decay": 0.03, "sustain_level": 0.14, "release": 0.05, "seed": seed},
            {"waveform": "sine", "start": 0.04, "duration": 0.08, "start_freq": 980 + seed * 10, "end_freq": 1220 + seed * 9, "volume": 0.14, "attack": 0.002, "decay": 0.018, "sustain_level": 0.08, "release": 0.03, "seed": seed * 13},
        ],
    )


def make_alert(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.48,
        [
            {"waveform": "square", "start_freq": 286 + seed * 2, "end_freq": 226 + seed * 2, "volume": 0.2, "attack": 0.003, "decay": 0.06, "sustain_level": 0.22, "release": 0.12, "seed": seed},
            {"waveform": "triangle", "start_freq": 412 + seed * 3, "end_freq": 350 + seed * 3, "volume": 0.18, "attack": 0.003, "decay": 0.06, "sustain_level": 0.18, "release": 0.1, "seed": seed * 7},
            {"waveform": "noise", "start": 0.0, "duration": 0.09, "volume": 0.09, "attack": 0.001, "decay": 0.012, "sustain_level": 0.0, "release": 0.04, "seed": seed * 17},
        ],
    )


def make_impact_flesh(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.16,
        [
            {"waveform": "noise", "duration": 0.03, "volume": 0.14, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.02, "seed": seed},
            {"waveform": "sine", "start": 0.005, "duration": 0.09, "start_freq": 124 + seed * 3, "end_freq": 76 + seed * 2, "volume": 0.2, "attack": 0.002, "decay": 0.02, "sustain_level": 0.08, "release": 0.03, "seed": seed * 5},
            {"waveform": "triangle", "start": 0.016, "duration": 0.05, "start_freq": 302 + seed * 4, "end_freq": 182 + seed * 2, "volume": 0.09, "attack": 0.001, "decay": 0.01, "sustain_level": 0.05, "release": 0.02, "seed": seed * 9},
        ],
    )


def make_impact_wood(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.18,
        [
            {"waveform": "noise", "duration": 0.035, "volume": 0.12, "attack": 0.001, "decay": 0.009, "sustain_level": 0.0, "release": 0.018, "seed": seed},
            {"waveform": "square", "start": 0.004, "duration": 0.05, "start_freq": 282 + seed * 6, "end_freq": 152 + seed * 3, "volume": 0.13, "attack": 0.001, "decay": 0.012, "sustain_level": 0.04, "release": 0.02, "seed": seed * 7},
            {"waveform": "sine", "start": 0.01, "duration": 0.11, "start_freq": 178 + seed * 4, "end_freq": 102 + seed * 2, "volume": 0.14, "attack": 0.002, "decay": 0.014, "sustain_level": 0.08, "release": 0.03, "seed": seed * 11},
        ],
    )


def make_impact_body(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.2,
        [
            {"waveform": "noise", "duration": 0.04, "volume": 0.13, "attack": 0.001, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed},
            {"waveform": "sine", "start": 0.006, "duration": 0.12, "start_freq": 114 + seed * 2, "end_freq": 70 + seed, "volume": 0.2, "attack": 0.002, "decay": 0.022, "sustain_level": 0.08, "release": 0.035, "seed": seed * 5},
        ],
    )


def make_transition_start(audio) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.55,
        [
            {"waveform": "triangle", "start_freq": 260, "end_freq": 328, "volume": 0.18, "attack": 0.02, "decay": 0.08, "sustain_level": 0.28, "release": 0.14, "seed": 121},
            {"waveform": "sine", "start": 0.06, "duration": 0.36, "start_freq": 390, "end_freq": 492, "volume": 0.14, "attack": 0.01, "decay": 0.06, "sustain_level": 0.22, "release": 0.12, "seed": 122},
            {"waveform": "sine", "start": 0.1, "duration": 0.26, "start_freq": 520, "end_freq": 656, "volume": 0.11, "attack": 0.01, "decay": 0.04, "sustain_level": 0.18, "release": 0.1, "seed": 123},
        ],
    )


def make_transition_restart(audio) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.33,
        [
            {"waveform": "triangle", "start_freq": 620, "end_freq": 420, "volume": 0.26, "attack": 0.005, "decay": 0.04, "sustain_level": 0.16, "release": 0.07, "seed": 124},
            {"waveform": "sine", "start": 0.065, "duration": 0.14, "start_freq": 520, "end_freq": 300, "volume": 0.14, "attack": 0.004, "decay": 0.03, "sustain_level": 0.08, "release": 0.05, "seed": 125},
        ],
    )


def make_transition_nightfall(audio) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.68,
        [
            {"waveform": "saw", "start_freq": 240, "end_freq": 130, "volume": 0.18, "attack": 0.02, "decay": 0.08, "sustain_level": 0.18, "release": 0.18, "seed": 126},
            {"waveform": "sine", "start": 0.05, "duration": 0.5, "start_freq": 180, "end_freq": 110, "volume": 0.12, "attack": 0.02, "decay": 0.06, "sustain_level": 0.16, "release": 0.16, "seed": 127},
            {"waveform": "noise", "start": 0.02, "duration": 0.18, "volume": 0.05, "attack": 0.003, "decay": 0.02, "sustain_level": 0.0, "release": 0.05, "seed": 128},
        ],
    )


def make_transition_daybreak(audio) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.6,
        [
            {"waveform": "triangle", "start_freq": 310, "end_freq": 420, "volume": 0.14, "attack": 0.02, "decay": 0.06, "sustain_level": 0.22, "release": 0.14, "seed": 129},
            {"waveform": "sine", "start": 0.08, "duration": 0.22, "start_freq": 520, "end_freq": 760, "volume": 0.14, "attack": 0.01, "decay": 0.04, "sustain_level": 0.16, "release": 0.08, "seed": 130},
            {"waveform": "sine", "start": 0.18, "duration": 0.18, "start_freq": 680, "end_freq": 980, "volume": 0.12, "attack": 0.008, "decay": 0.03, "sustain_level": 0.12, "release": 0.06, "seed": 131},
        ],
    )


def make_step_camp(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.13,
        [
            {"waveform": "noise", "duration": 0.038, "volume": 0.09, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.016, "seed": seed},
            {"waveform": "sine", "start": 0.006, "duration": 0.07, "start_freq": 128 + seed * 2, "end_freq": 88 + seed, "volume": 0.1, "attack": 0.002, "decay": 0.015, "sustain_level": 0.06, "release": 0.022, "seed": seed * 5},
        ],
    )


def make_step_path(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.12,
        [
            {"waveform": "noise", "duration": 0.028, "volume": 0.1, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.014, "seed": seed},
            {"waveform": "triangle", "start": 0.004, "duration": 0.05, "start_freq": 240 + seed * 3, "end_freq": 150 + seed * 2, "volume": 0.08, "attack": 0.001, "decay": 0.01, "sustain_level": 0.04, "release": 0.016, "seed": seed * 3},
            {"waveform": "sine", "start": 0.01, "duration": 0.05, "start_freq": 120 + seed, "end_freq": 92 + seed, "volume": 0.06, "attack": 0.002, "decay": 0.01, "sustain_level": 0.03, "release": 0.015, "seed": seed * 7},
        ],
    )


def make_step_forest(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.16,
        [
            {"waveform": "noise", "duration": 0.055, "volume": 0.12, "attack": 0.001, "decay": 0.016, "sustain_level": 0.0, "release": 0.024, "seed": seed},
            {"waveform": "sine", "start": 0.008, "duration": 0.08, "start_freq": 116 + seed * 2, "end_freq": 76 + seed, "volume": 0.08, "attack": 0.002, "decay": 0.014, "sustain_level": 0.04, "release": 0.02, "seed": seed * 5},
        ],
    )


def make_step_meadow(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.14,
        [
            {"waveform": "noise", "duration": 0.04, "volume": 0.08, "attack": 0.001, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed},
            {"waveform": "triangle", "start": 0.008, "duration": 0.065, "start_freq": 144 + seed * 2, "end_freq": 96 + seed, "volume": 0.08, "attack": 0.002, "decay": 0.014, "sustain_level": 0.04, "release": 0.02, "seed": seed * 7},
        ],
    )


def make_step_swamp(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.19,
        [
            {"waveform": "noise", "duration": 0.06, "volume": 0.14, "attack": 0.001, "decay": 0.014, "sustain_level": 0.0, "release": 0.03, "seed": seed},
            {"waveform": "saw", "start": 0.005, "duration": 0.09, "start_freq": 92 + seed, "end_freq": 52 + seed, "volume": 0.08, "attack": 0.001, "decay": 0.012, "sustain_level": 0.06, "release": 0.028, "seed": seed * 5},
            {"waveform": "sine", "start": 0.02, "duration": 0.07, "start_freq": 166 + seed * 2, "end_freq": 118 + seed, "volume": 0.05, "attack": 0.002, "decay": 0.01, "sustain_level": 0.04, "release": 0.02, "seed": seed * 11},
        ],
    )


def make_step_ruin(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.14,
        [
            {"waveform": "noise", "duration": 0.03, "volume": 0.09, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.014, "seed": seed},
            {"waveform": "square", "start": 0.004, "duration": 0.045, "start_freq": 410 + seed * 5, "end_freq": 242 + seed * 3, "volume": 0.08, "attack": 0.001, "decay": 0.01, "sustain_level": 0.03, "release": 0.018, "seed": seed * 3},
            {"waveform": "sine", "start": 0.01, "duration": 0.06, "start_freq": 132 + seed, "end_freq": 96 + seed, "volume": 0.05, "attack": 0.002, "decay": 0.012, "sustain_level": 0.03, "release": 0.018, "seed": seed * 7},
        ],
    )


def make_bonfire_pop(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.12,
        [
            {"waveform": "noise", "duration": 0.05, "volume": 0.12, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.02, "seed": seed},
            {"waveform": "sine", "start": 0.01, "duration": 0.07, "start_freq": 140 + seed * 4, "end_freq": 92 + seed * 2, "volume": 0.09, "attack": 0.002, "decay": 0.012, "sustain_level": 0.06, "release": 0.03, "seed": seed * 3},
        ],
    )


def make_night_chirp(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.24,
        [
            {"waveform": "sine", "start_freq": 1820 + seed * 18, "end_freq": 1540 + seed * 9, "volume": 0.09, "attack": 0.004, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed},
            {"waveform": "sine", "start": 0.08, "duration": 0.07, "start_freq": 2060 + seed * 16, "end_freq": 1660 + seed * 8, "volume": 0.08, "attack": 0.003, "decay": 0.018, "sustain_level": 0.0, "release": 0.025, "seed": seed * 7},
        ],
    )


def make_day_bird(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.32,
        [
            {"waveform": "sine", "start_freq": 980 + seed * 15, "end_freq": 1310 + seed * 18, "volume": 0.08, "attack": 0.006, "decay": 0.025, "sustain_level": 0.0, "release": 0.03, "vibrato_rate": 8.0, "vibrato_depth": 0.03, "seed": seed},
            {"waveform": "sine", "start": 0.09, "duration": 0.09, "start_freq": 860 + seed * 10, "end_freq": 1180 + seed * 12, "volume": 0.07, "attack": 0.004, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed * 11},
        ],
    )


def make_ambient_wind(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.88,
        [
            {"waveform": "noise", "duration": 0.88, "volume": 0.1, "attack": 0.08, "decay": 0.16, "sustain_level": 0.18, "release": 0.2, "seed": seed},
            {"waveform": "sine", "start": 0.04, "duration": 0.7, "start_freq": 220 + seed * 2, "end_freq": 148 + seed, "volume": 0.035, "attack": 0.1, "decay": 0.12, "sustain_level": 0.1, "release": 0.18, "seed": seed * 3},
        ],
    )


def make_ambient_rain(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.72,
        [
            {"waveform": "noise", "duration": 0.72, "volume": 0.11, "attack": 0.03, "decay": 0.06, "sustain_level": 0.22, "release": 0.12, "seed": seed},
            {"waveform": "noise", "start": 0.05, "duration": 0.1, "volume": 0.06, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.016, "seed": seed * 5},
            {"waveform": "noise", "start": 0.22, "duration": 0.08, "volume": 0.05, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.016, "seed": seed * 7},
            {"waveform": "noise", "start": 0.44, "duration": 0.08, "volume": 0.05, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.016, "seed": seed * 11},
        ],
    )


def make_ambient_grove(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.62,
        [
            {"waveform": "noise", "duration": 0.4, "volume": 0.07, "attack": 0.02, "decay": 0.03, "sustain_level": 0.08, "release": 0.08, "seed": seed},
            {"waveform": "triangle", "start": 0.16, "duration": 0.22, "start_freq": 292 + seed * 2, "end_freq": 182 + seed, "volume": 0.03, "attack": 0.02, "decay": 0.03, "sustain_level": 0.06, "release": 0.06, "seed": seed * 5},
        ],
    )


def make_ambient_swamp(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.54,
        [
            {"waveform": "sine", "start_freq": 182 + seed * 3, "end_freq": 144 + seed * 2, "volume": 0.05, "attack": 0.01, "decay": 0.04, "sustain_level": 0.12, "release": 0.08, "vibrato_rate": 5.0, "vibrato_depth": 0.04, "seed": seed},
            {"waveform": "sine", "start": 0.18, "duration": 0.14, "start_freq": 288 + seed * 4, "end_freq": 222 + seed * 3, "volume": 0.04, "attack": 0.01, "decay": 0.03, "sustain_level": 0.08, "release": 0.05, "seed": seed * 7},
            {"waveform": "noise", "start": 0.06, "duration": 0.12, "volume": 0.03, "attack": 0.005, "decay": 0.015, "sustain_level": 0.0, "release": 0.03, "seed": seed * 11},
        ],
    )


def make_ambient_ruin(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.6,
        [
            {"waveform": "square", "start": 0.04, "duration": 0.08, "start_freq": 312 + seed * 3, "end_freq": 250 + seed * 2, "volume": 0.04, "attack": 0.003, "decay": 0.02, "sustain_level": 0.04, "release": 0.03, "seed": seed},
            {"waveform": "noise", "start": 0.08, "duration": 0.05, "volume": 0.03, "attack": 0.002, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed * 5},
            {"waveform": "sine", "start": 0.18, "duration": 0.22, "start_freq": 178 + seed * 2, "end_freq": 132 + seed, "volume": 0.03, "attack": 0.02, "decay": 0.03, "sustain_level": 0.06, "release": 0.05, "seed": seed * 9},
        ],
    )


def make_ambient_dread(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        1.18,
        [
            {"waveform": "sine", "start_freq": 66 + seed, "end_freq": 54 + seed, "volume": 0.055, "attack": 0.08, "decay": 0.12, "sustain_level": 0.16, "release": 0.24, "vibrato_rate": 0.7, "vibrato_depth": 0.025, "seed": seed},
            {"waveform": "triangle", "start": 0.14, "duration": 0.74, "start_freq": 98 + seed, "end_freq": 82 + seed, "volume": 0.032, "attack": 0.08, "decay": 0.1, "sustain_level": 0.1, "release": 0.18, "seed": seed * 3},
            {"waveform": "noise", "start": 0.04, "duration": 0.22, "volume": 0.012, "attack": 0.01, "decay": 0.03, "sustain_level": 0.0, "release": 0.04, "seed": seed * 5},
        ],
    )


def make_zombie_groan(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.72,
        [
            {"waveform": "saw", "start_freq": 118 + seed * 2, "end_freq": 78 + seed, "volume": 0.08, "attack": 0.03, "decay": 0.08, "sustain_level": 0.14, "release": 0.16, "vibrato_rate": 4.0, "vibrato_depth": 0.03, "seed": seed},
            {"waveform": "sine", "start": 0.04, "duration": 0.5, "start_freq": 94 + seed, "end_freq": 66 + seed, "volume": 0.05, "attack": 0.04, "decay": 0.06, "sustain_level": 0.1, "release": 0.14, "seed": seed * 7},
            {"waveform": "noise", "start": 0.02, "duration": 0.12, "volume": 0.02, "attack": 0.004, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed * 13},
        ],
    )


def make_zombie_far(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        0.96,
        [
            {"waveform": "sine", "start_freq": 84 + seed, "end_freq": 58 + seed, "volume": 0.05, "attack": 0.05, "decay": 0.08, "sustain_level": 0.14, "release": 0.2, "vibrato_rate": 3.2, "vibrato_depth": 0.045, "seed": seed},
            {"waveform": "saw", "start": 0.08, "duration": 0.46, "start_freq": 126 + seed, "end_freq": 88 + seed, "volume": 0.028, "attack": 0.03, "decay": 0.06, "sustain_level": 0.08, "release": 0.12, "seed": seed * 3},
            {"waveform": "noise", "start": 0.03, "duration": 0.16, "volume": 0.01, "attack": 0.004, "decay": 0.018, "sustain_level": 0.0, "release": 0.025, "seed": seed * 7},
        ],
    )


def make_zombie_horde(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        1.1,
        [
            {"waveform": "saw", "start_freq": 104 + seed, "end_freq": 62 + seed, "volume": 0.08, "attack": 0.04, "decay": 0.1, "sustain_level": 0.18, "release": 0.18, "seed": seed},
            {"waveform": "triangle", "start": 0.06, "duration": 0.74, "start_freq": 136 + seed * 2, "end_freq": 88 + seed, "volume": 0.05, "attack": 0.03, "decay": 0.08, "sustain_level": 0.12, "release": 0.16, "seed": seed * 5},
            {"waveform": "noise", "start": 0.02, "duration": 0.2, "volume": 0.03, "attack": 0.01, "decay": 0.02, "sustain_level": 0.0, "release": 0.04, "seed": seed * 11},
        ],
    )


def make_music_calm(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        1.45,
        [
            {"waveform": "triangle", "start_freq": 196 + seed * 2, "end_freq": 220 + seed * 2, "volume": 0.05, "attack": 0.08, "decay": 0.14, "sustain_level": 0.16, "release": 0.24, "seed": seed},
            {"waveform": "sine", "start": 0.18, "duration": 0.72, "start_freq": 294 + seed * 3, "end_freq": 330 + seed * 3, "volume": 0.045, "attack": 0.06, "decay": 0.1, "sustain_level": 0.14, "release": 0.18, "seed": seed * 3},
            {"waveform": "sine", "start": 0.44, "duration": 0.58, "start_freq": 392 + seed * 3, "end_freq": 440 + seed * 4, "volume": 0.03, "attack": 0.05, "decay": 0.08, "sustain_level": 0.1, "release": 0.14, "seed": seed * 5},
        ],
    )


def make_music_dread(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        1.58,
        [
            {"waveform": "sine", "start_freq": 72 + seed, "end_freq": 62 + seed, "volume": 0.055, "attack": 0.1, "decay": 0.14, "sustain_level": 0.18, "release": 0.28, "vibrato_rate": 0.5, "vibrato_depth": 0.018, "seed": seed},
            {"waveform": "triangle", "start": 0.24, "duration": 0.7, "start_freq": 108 + seed, "end_freq": 96 + seed, "volume": 0.03, "attack": 0.08, "decay": 0.1, "sustain_level": 0.1, "release": 0.18, "seed": seed * 3},
            {"waveform": "noise", "start": 0.0, "duration": 0.14, "volume": 0.012, "attack": 0.008, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed * 5},
        ],
    )


def make_music_threat(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        1.28,
        [
            {"waveform": "saw", "start_freq": 110 + seed * 2, "end_freq": 92 + seed, "volume": 0.06, "attack": 0.03, "decay": 0.08, "sustain_level": 0.16, "release": 0.18, "seed": seed},
            {"waveform": "triangle", "start": 0.12, "duration": 0.58, "start_freq": 164 + seed * 2, "end_freq": 132 + seed, "volume": 0.045, "attack": 0.03, "decay": 0.06, "sustain_level": 0.12, "release": 0.14, "seed": seed * 3},
            {"waveform": "noise", "start": 0.0, "duration": 0.09, "volume": 0.015, "attack": 0.004, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed * 7},
        ],
    )


def make_music_horde(audio, seed: int) -> pygame.mixer.Sound:
    return synth(
        audio,
        1.52,
        [
            {"waveform": "saw", "start_freq": 92 + seed, "end_freq": 66 + seed, "volume": 0.07, "attack": 0.04, "decay": 0.1, "sustain_level": 0.18, "release": 0.22, "seed": seed},
            {"waveform": "square", "start": 0.18, "duration": 0.56, "start_freq": 138 + seed * 2, "end_freq": 102 + seed, "volume": 0.03, "attack": 0.02, "decay": 0.05, "sustain_level": 0.08, "release": 0.12, "seed": seed * 3},
            {"waveform": "triangle", "start": 0.42, "duration": 0.54, "start_freq": 162 + seed * 2, "end_freq": 118 + seed, "volume": 0.038, "attack": 0.03, "decay": 0.05, "sustain_level": 0.1, "release": 0.14, "seed": seed * 5},
            {"waveform": "noise", "start": 0.0, "duration": 0.12, "volume": 0.016, "attack": 0.005, "decay": 0.016, "sustain_level": 0.0, "release": 0.024, "seed": seed * 7},
        ],
    )







