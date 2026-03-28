from __future__ import annotations

import math
import random
from array import array

import pygame


class AudioSystem:
    def __init__(self) -> None:
        self.available = False
        self.sample_rate = 22050
        self.channels = 1
        self.rng = random.Random(4171)
        self.cues: dict[str, list[pygame.mixer.Sound]] = {}
        self.bonfire_timer = 0.45
        self.ambience_timer = 3.2
        self.weather_timer = 2.6
        self.zombie_timer = 5.4
        self.music_timer = 1.8
        self.step_timer = 0.0
        self.master_volume = 0.86
        self.ambience_volume = 0.92
        self.music_volume = 0.84

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=self.channels, buffer=512)
            init = pygame.mixer.get_init()
            if init:
                self.sample_rate, _, self.channels = init
            pygame.mixer.set_num_channels(24)
            self.available = True
            self.cues = self._build_sound_bank()
        except pygame.error:
            self.available = False

    def play_ui(self, cue: str = "ui") -> None:
        cue_map = {
            "ui": "ui_confirm",
            "focus": "ui_focus",
            "back": "ui_back",
            "order": "ui_order",
        }
        self._play(cue_map.get(cue, "ui_confirm"), volume_scale=0.52)

    def play_attack(self) -> None:
        self._play("attack", volume_scale=0.6)

    def play_interact(self, cue: str = "interact") -> None:
        cue_map = {
            "interact": "interact",
            "repair": "impact_wood",
            "salvage": "impact_wood",
            "bonfire": "interact",
        }
        self._play(cue_map.get(cue, "interact"), volume_scale=0.58)

    def play_alert(self) -> None:
        self._play("alert", volume_scale=0.72)

    def play_transition(self, cue: str = "transition") -> None:
        cue_map = {
            "transition": "transition_start",
            "start": "transition_start",
            "restart": "transition_restart",
            "nightfall": "transition_nightfall",
            "daybreak": "transition_daybreak",
        }
        self._play(cue_map.get(cue, "transition_start"), volume_scale=0.68)

    def play_impact(self, cue: str = "flesh") -> None:
        cue_map = {
            "flesh": "impact_flesh",
            "wood": "impact_wood",
            "body": "impact_body",
        }
        volume_map = {
            "flesh": 0.54,
            "wood": 0.5,
            "body": 0.56,
        }
        target = cue_map.get(cue, "impact_flesh")
        self._play(target, volume_scale=volume_map.get(cue, 0.54))

    def update(self, game, dt: float) -> None:
        if not self.available or not game.scenes.is_gameplay():
            return

        self.bonfire_timer -= dt
        self.ambience_timer -= dt
        self.weather_timer -= dt
        self.zombie_timer -= dt
        self.music_timer -= dt

        self._update_player_steps(game, dt)
        self._update_bonfire(game)
        self._update_biome_ambience(game)
        self._update_weather(game)
        self._update_zombie_ambience(game)
        self._update_music(game)

    def _update_player_steps(self, game, dt: float) -> None:
        if not game.player.is_alive():
            return

        speed = game.player.velocity.length()
        if speed < 22:
            self.step_timer = min(self.step_timer, 0.06)
            return

        speed_ratio = max(0.5, min(1.9, speed / max(1.0, game.player.speed)))
        sprinting = speed_ratio > 1.18
        self.step_timer -= dt * speed_ratio
        if self.step_timer > 0:
            return

        surface = game.surface_audio_at(game.player.pos)
        cue = {
            "camp": "step_camp",
            "path": "step_path",
            "meadow": "step_meadow",
            "swamp": "step_swamp",
            "ruin": "step_ruin",
        }.get(surface, "step_forest")
        volume = 0.11 + (0.05 if sprinting else 0.0)
        if surface == "swamp":
            volume += 0.04
        elif surface == "ruin":
            volume += 0.03
        elif surface == "path":
            volume += 0.02
        self._play(cue, volume_scale=volume)

        cadence = 0.36 if not sprinting else 0.24
        if surface == "swamp":
            cadence += 0.05
        elif surface == "path":
            cadence -= 0.03
        self.step_timer = max(0.11, cadence * self.rng.uniform(0.88, 1.08))

    def _update_bonfire(self, game) -> None:
        if self.bonfire_timer > 0:
            return
        intensity = min(1.0, (game.bonfire_heat * 0.65 + game.bonfire_ember_bed * 0.35) / 100)
        if intensity <= 0.12:
            return
        self._play("ambient_bonfire", volume_scale=0.08 + intensity * 0.22, category="ambience")
        self.bonfire_timer = self.rng.uniform(0.22, 0.62) * (1.25 - intensity * 0.38)

    def _update_biome_ambience(self, game) -> None:
        if self.ambience_timer > 0:
            return

        biome = getattr(game, "current_biome_key", "camp")
        weather_kind = getattr(game, "weather_kind", "clear")
        daylight = game.daylight_factor() if hasattr(game, "daylight_factor") else (0.0 if game.is_night else 1.0)

        if daylight < 0.18:
            options = [("ambient_night", 0.15)]
            if biome == "swamp":
                options.append(("ambient_swamp", 0.17))
            elif biome == "grove":
                options.append(("ambient_grove", 0.13))
            elif biome == "ruin":
                options.append(("ambient_ruin", 0.14))
            cue, volume = self.rng.choice(options)
            self._play(cue, volume_scale=volume, category="ambience")
            self.ambience_timer = self.rng.uniform(4.2, 6.8)
            return

        if weather_kind == "rain":
            if biome == "swamp":
                self._play("ambient_swamp", volume_scale=0.14, category="ambience")
            elif self.rng.random() < 0.4:
                self._play("ambient_grove", volume_scale=0.1, category="ambience")
            self.ambience_timer = self.rng.uniform(5.6, 8.8)
            return
        if weather_kind == "cloudy":
            options = [("ambient_day", 0.08)]
            if biome == "swamp":
                options.append(("ambient_swamp", 0.1))
            elif biome == "ruin":
                options.append(("ambient_ruin", 0.11))
            elif biome == "grove":
                options.append(("ambient_grove", 0.09))
            cue, volume = self.rng.choice(options)
            self._play(cue, volume_scale=volume, category="ambience")
            self.ambience_timer = self.rng.uniform(5.2, 8.2)
            return

        options = [("ambient_day", 0.12)]
        if biome == "grove":
            options.append(("ambient_grove", 0.12))
        elif biome == "swamp":
            options.append(("ambient_swamp", 0.13))
        elif biome == "ruin":
            options.append(("ambient_ruin", 0.12))
        cue, volume = self.rng.choice(options)
        self._play(cue, volume_scale=volume, category="ambience")
        self.ambience_timer = self.rng.uniform(5.4, 9.6)

    def _update_weather(self, game) -> None:
        if self.weather_timer > 0:
            return

        weather_kind = getattr(game, "weather_kind", "clear")
        strength = float(getattr(game, "weather_strength", 0.0))
        if weather_kind == "rain":
            self._play("ambient_rain", volume_scale=0.15 + strength * 0.18, category="ambience")
            if strength > 0.58 and self.rng.random() < 0.35:
                self._play("ambient_wind", volume_scale=0.08 + strength * 0.05, category="ambience")
            self.weather_timer = self.rng.uniform(1.5, 2.5)
        elif weather_kind == "cloudy":
            if self.rng.random() < 0.58:
                self._play("ambient_wind", volume_scale=0.05 + strength * 0.06, category="ambience")
            self.weather_timer = self.rng.uniform(3.8, 6.4)
        elif weather_kind == "wind":
            self._play("ambient_wind", volume_scale=0.12 + strength * 0.14, category="ambience")
            self.weather_timer = self.rng.uniform(2.4, 4.2)
        else:
            if strength > 0.52 and self.rng.random() < 0.42:
                self._play("ambient_wind", volume_scale=0.07 + strength * 0.05, category="ambience")
            self.weather_timer = self.rng.uniform(5.4, 8.2)

    def _update_zombie_ambience(self, game) -> None:
        if self.zombie_timer > 0:
            return

        visible_threat = len(game.zombies)
        distant_threat = max(0.0, game.spawn_budget / 12) if game.is_night else 0.0
        pressure = min(1.0, visible_threat / 12 + distant_threat * 0.35)
        if pressure <= 0.06:
            self.zombie_timer = self.rng.uniform(4.8, 7.2)
            return

        if visible_threat >= 7 or game.audio_tension() >= 0.82:
            self._play("zombie_horde", volume_scale=0.14 + pressure * 0.16, category="ambience")
        else:
            self._play("zombie_groan", volume_scale=0.11 + pressure * 0.14, category="ambience")

        interval_low = 2.0 + (1.0 - pressure) * 2.2
        interval_high = 3.8 + (1.0 - pressure) * 3.4
        self.zombie_timer = self.rng.uniform(interval_low, interval_high)

    def _update_music(self, game) -> None:
        if self.music_timer > 0:
            return

        tension = game.audio_tension()
        if game.weather_kind == "rain":
            tension = min(1.0, tension + game.weather_strength * 0.08)
        elif game.weather_kind == "cloudy":
            tension = min(1.0, tension + game.weather_strength * 0.03)
        elif game.weather_kind == "wind":
            tension = min(1.0, tension + game.weather_strength * 0.04)

        if tension >= 0.82:
            self._play("music_horde", volume_scale=0.12 + tension * 0.07, category="music")
            self.music_timer = self.rng.uniform(2.8, 4.4)
        elif tension >= 0.46:
            self._play("music_threat", volume_scale=0.1 + tension * 0.06, category="music")
            self.music_timer = self.rng.uniform(4.0, 6.2)
        elif not game.is_night and self.rng.random() < 0.62:
            self._play("music_calm", volume_scale=0.08, category="music")
            self.music_timer = self.rng.uniform(6.0, 9.6)
        else:
            self.music_timer = self.rng.uniform(5.4, 8.4)

    def apply_settings(self, settings: dict[str, float]) -> None:
        self.master_volume = float(settings.get("master_volume", self.master_volume))
        self.ambience_volume = float(settings.get("ambience_volume", self.ambience_volume))
        self.music_volume = float(settings.get("music_volume", self.music_volume))

    def _play(self, cue: str, *, volume_scale: float = 1.0, category: str = "sfx") -> None:
        if not self.available:
            return
        variants = self.cues.get(cue)
        if not variants:
            return
        sound = self.rng.choice(variants)
        category_scale = {
            "sfx": 1.0,
            "ambience": self.ambience_volume,
            "music": self.music_volume,
        }.get(category, 1.0)
        sound.set_volume(max(0.0, min(1.0, volume_scale * self.master_volume * category_scale)))
        sound.play()

    def _build_sound_bank(self) -> dict[str, list[pygame.mixer.Sound]]:
        return {
            "ui_confirm": [self._make_ui_confirm(seed) for seed in (1, 2, 3)],
            "ui_focus": [self._make_ui_focus(seed) for seed in (4, 5, 6)],
            "ui_back": [self._make_ui_back(seed) for seed in (7, 8)],
            "ui_order": [self._make_ui_order(seed) for seed in (9, 10)],
            "attack": [self._make_attack(seed) for seed in (11, 12, 13)],
            "interact": [self._make_interact(seed) for seed in (14, 15, 16)],
            "alert": [self._make_alert(seed) for seed in (17, 18)],
            "impact_flesh": [self._make_impact_flesh(seed) for seed in (19, 20, 21)],
            "impact_wood": [self._make_impact_wood(seed) for seed in (22, 23, 24)],
            "impact_body": [self._make_impact_body(seed) for seed in (25, 26, 27)],
            "transition_start": [self._make_transition_start()],
            "transition_restart": [self._make_transition_restart()],
            "transition_nightfall": [self._make_transition_nightfall()],
            "transition_daybreak": [self._make_transition_daybreak()],
            "step_camp": [self._make_step_camp(seed) for seed in (31, 32, 33, 34)],
            "step_path": [self._make_step_path(seed) for seed in (35, 36, 37, 38)],
            "step_forest": [self._make_step_forest(seed) for seed in (39, 40, 41, 42)],
            "step_meadow": [self._make_step_meadow(seed) for seed in (43, 44, 45, 46)],
            "step_swamp": [self._make_step_swamp(seed) for seed in (47, 48, 49, 50)],
            "step_ruin": [self._make_step_ruin(seed) for seed in (51, 52, 53, 54)],
            "ambient_bonfire": [self._make_bonfire_pop(seed) for seed in (61, 62, 63, 64)],
            "ambient_night": [self._make_night_chirp(seed) for seed in (65, 66, 67)],
            "ambient_day": [self._make_day_bird(seed) for seed in (68, 69, 70)],
            "ambient_wind": [self._make_ambient_wind(seed) for seed in (71, 72, 73)],
            "ambient_rain": [self._make_ambient_rain(seed) for seed in (74, 75, 76)],
            "ambient_grove": [self._make_ambient_grove(seed) for seed in (77, 78, 79)],
            "ambient_swamp": [self._make_ambient_swamp(seed) for seed in (80, 81, 82)],
            "ambient_ruin": [self._make_ambient_ruin(seed) for seed in (83, 84, 85)],
            "zombie_groan": [self._make_zombie_groan(seed) for seed in (91, 92, 93)],
            "zombie_horde": [self._make_zombie_horde(seed) for seed in (94, 95)],
            "music_calm": [self._make_music_calm(seed) for seed in (101, 102)],
            "music_threat": [self._make_music_threat(seed) for seed in (103, 104)],
            "music_horde": [self._make_music_horde(seed) for seed in (105, 106)],
        }

    def _osc(self, waveform: str, phase: float, rng: random.Random) -> float:
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

    def _envelope(
        self,
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

        attack_frames = max(1, int(attack * self.sample_rate))
        decay_frames = max(0, int(decay * self.sample_rate))
        release_frames = max(1, int(release * self.sample_rate))
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

    def _synth(self, duration: float, layers: list[dict[str, float | str | tuple]]) -> pygame.mixer.Sound:
        frame_count = max(1, int(duration * self.sample_rate))
        mix = [0.0] * frame_count

        for layer in layers:
            rng = random.Random(layer.get("seed", 0))
            start = float(layer.get("start", 0.0))
            layer_duration = float(layer.get("duration", duration - start))
            start_index = max(0, int(start * self.sample_rate))
            length = min(frame_count - start_index, max(1, int(layer_duration * self.sample_rate)))
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
                    freq *= 1.0 + math.sin(i / self.sample_rate * math.tau * vibrato_rate) * vibrato_depth
                phase += math.tau * freq / self.sample_rate
                sample = self._osc(waveform, phase, rng)
                for harmonic_mult, harmonic_gain in harmonics:
                    sample += self._osc("sine", phase * harmonic_mult, rng) * harmonic_gain
                env = self._envelope(
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
            if self.channels == 2:
                pcm.append(value)
                pcm.append(value)
            else:
                pcm.append(value)
        return pygame.mixer.Sound(buffer=pcm.tobytes())

    def _make_ui_confirm(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.14,
            [
                {"waveform": "triangle", "start_freq": 760 + seed * 6, "end_freq": 1020 + seed * 8, "volume": 0.42, "attack": 0.003, "decay": 0.025, "sustain_level": 0.18, "release": 0.045, "harmonics": ((2.0, 0.12),), "seed": seed},
                {"waveform": "noise", "start": 0.0, "duration": 0.03, "volume": 0.08, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.012, "seed": seed * 13},
            ],
        )

    def _make_ui_focus(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.2,
            [
                {"waveform": "sine", "start_freq": 620 + seed * 4, "end_freq": 820 + seed * 7, "volume": 0.34, "attack": 0.002, "decay": 0.03, "sustain_level": 0.22, "release": 0.04, "seed": seed},
                {"waveform": "triangle", "start": 0.055, "duration": 0.13, "start_freq": 920 + seed * 5, "end_freq": 1260 + seed * 7, "volume": 0.28, "attack": 0.002, "decay": 0.024, "sustain_level": 0.2, "release": 0.05, "harmonics": ((2.0, 0.1),), "seed": seed * 17},
            ],
        )

    def _make_ui_back(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.18,
            [
                {"waveform": "triangle", "start_freq": 540 + seed * 5, "end_freq": 360 + seed * 3, "volume": 0.3, "attack": 0.002, "decay": 0.03, "sustain_level": 0.18, "release": 0.05, "seed": seed},
                {"waveform": "triangle", "start": 0.055, "duration": 0.08, "start_freq": 430 + seed * 3, "end_freq": 270 + seed * 2, "volume": 0.23, "attack": 0.002, "decay": 0.024, "sustain_level": 0.1, "release": 0.04, "seed": seed * 11},
            ],
        )

    def _make_ui_order(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.24,
            [
                {"waveform": "sine", "start_freq": 420 + seed * 3, "end_freq": 610 + seed * 4, "volume": 0.34, "attack": 0.008, "decay": 0.045, "sustain_level": 0.24, "release": 0.08, "vibrato_rate": 6.0, "vibrato_depth": 0.018, "seed": seed},
                {"waveform": "triangle", "start": 0.04, "duration": 0.1, "start_freq": 690 + seed * 5, "end_freq": 820 + seed * 4, "volume": 0.14, "attack": 0.003, "decay": 0.02, "sustain_level": 0.14, "release": 0.04, "seed": seed * 19},
            ],
        )

    def _make_attack(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.22,
            [
                {"waveform": "noise", "start_freq": 0.0, "end_freq": 0.0, "volume": 0.22, "attack": 0.001, "decay": 0.018, "sustain_level": 0.0, "release": 0.045, "seed": seed * 3},
                {"waveform": "saw", "start_freq": 340 + seed * 8, "end_freq": 120 + seed * 2, "volume": 0.34, "attack": 0.001, "decay": 0.02, "sustain_level": 0.06, "release": 0.05, "harmonics": ((2.0, 0.09),), "seed": seed},
                {"waveform": "sine", "start": 0.022, "duration": 0.11, "start_freq": 150 + seed * 3, "end_freq": 86 + seed * 2, "volume": 0.17, "attack": 0.002, "decay": 0.018, "sustain_level": 0.08, "release": 0.04, "seed": seed * 7},
            ],
        )

    def _make_interact(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.18,
            [
                {"waveform": "noise", "duration": 0.04, "volume": 0.11, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.015, "seed": seed * 5},
                {"waveform": "triangle", "start_freq": 480 + seed * 4, "end_freq": 660 + seed * 6, "volume": 0.28, "attack": 0.003, "decay": 0.03, "sustain_level": 0.14, "release": 0.05, "seed": seed},
                {"waveform": "sine", "start": 0.04, "duration": 0.08, "start_freq": 980 + seed * 10, "end_freq": 1220 + seed * 9, "volume": 0.14, "attack": 0.002, "decay": 0.018, "sustain_level": 0.08, "release": 0.03, "seed": seed * 13},
            ],
        )

    def _make_alert(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.48,
            [
                {"waveform": "square", "start_freq": 286 + seed * 2, "end_freq": 226 + seed * 2, "volume": 0.2, "attack": 0.003, "decay": 0.06, "sustain_level": 0.22, "release": 0.12, "seed": seed},
                {"waveform": "triangle", "start_freq": 412 + seed * 3, "end_freq": 350 + seed * 3, "volume": 0.18, "attack": 0.003, "decay": 0.06, "sustain_level": 0.18, "release": 0.1, "seed": seed * 7},
                {"waveform": "noise", "start": 0.0, "duration": 0.09, "volume": 0.09, "attack": 0.001, "decay": 0.012, "sustain_level": 0.0, "release": 0.04, "seed": seed * 17},
            ],
        )

    def _make_impact_flesh(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.16,
            [
                {"waveform": "noise", "duration": 0.03, "volume": 0.14, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.02, "seed": seed},
                {"waveform": "sine", "start": 0.005, "duration": 0.09, "start_freq": 124 + seed * 3, "end_freq": 76 + seed * 2, "volume": 0.2, "attack": 0.002, "decay": 0.02, "sustain_level": 0.08, "release": 0.03, "seed": seed * 5},
                {"waveform": "triangle", "start": 0.016, "duration": 0.05, "start_freq": 302 + seed * 4, "end_freq": 182 + seed * 2, "volume": 0.09, "attack": 0.001, "decay": 0.01, "sustain_level": 0.05, "release": 0.02, "seed": seed * 9},
            ],
        )

    def _make_impact_wood(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.18,
            [
                {"waveform": "noise", "duration": 0.035, "volume": 0.12, "attack": 0.001, "decay": 0.009, "sustain_level": 0.0, "release": 0.018, "seed": seed},
                {"waveform": "square", "start": 0.004, "duration": 0.05, "start_freq": 282 + seed * 6, "end_freq": 152 + seed * 3, "volume": 0.13, "attack": 0.001, "decay": 0.012, "sustain_level": 0.04, "release": 0.02, "seed": seed * 7},
                {"waveform": "sine", "start": 0.01, "duration": 0.11, "start_freq": 178 + seed * 4, "end_freq": 102 + seed * 2, "volume": 0.14, "attack": 0.002, "decay": 0.014, "sustain_level": 0.08, "release": 0.03, "seed": seed * 11},
            ],
        )

    def _make_impact_body(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.2,
            [
                {"waveform": "noise", "duration": 0.04, "volume": 0.13, "attack": 0.001, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed},
                {"waveform": "sine", "start": 0.006, "duration": 0.12, "start_freq": 114 + seed * 2, "end_freq": 70 + seed, "volume": 0.2, "attack": 0.002, "decay": 0.022, "sustain_level": 0.08, "release": 0.035, "seed": seed * 5},
            ],
        )

    def _make_transition_start(self) -> pygame.mixer.Sound:
        return self._synth(
            0.55,
            [
                {"waveform": "triangle", "start_freq": 260, "end_freq": 328, "volume": 0.18, "attack": 0.02, "decay": 0.08, "sustain_level": 0.28, "release": 0.14, "seed": 121},
                {"waveform": "sine", "start": 0.06, "duration": 0.36, "start_freq": 390, "end_freq": 492, "volume": 0.14, "attack": 0.01, "decay": 0.06, "sustain_level": 0.22, "release": 0.12, "seed": 122},
                {"waveform": "sine", "start": 0.1, "duration": 0.26, "start_freq": 520, "end_freq": 656, "volume": 0.11, "attack": 0.01, "decay": 0.04, "sustain_level": 0.18, "release": 0.1, "seed": 123},
            ],
        )

    def _make_transition_restart(self) -> pygame.mixer.Sound:
        return self._synth(
            0.33,
            [
                {"waveform": "triangle", "start_freq": 620, "end_freq": 420, "volume": 0.26, "attack": 0.005, "decay": 0.04, "sustain_level": 0.16, "release": 0.07, "seed": 124},
                {"waveform": "sine", "start": 0.065, "duration": 0.14, "start_freq": 520, "end_freq": 300, "volume": 0.14, "attack": 0.004, "decay": 0.03, "sustain_level": 0.08, "release": 0.05, "seed": 125},
            ],
        )

    def _make_transition_nightfall(self) -> pygame.mixer.Sound:
        return self._synth(
            0.68,
            [
                {"waveform": "saw", "start_freq": 240, "end_freq": 130, "volume": 0.18, "attack": 0.02, "decay": 0.08, "sustain_level": 0.18, "release": 0.18, "seed": 126},
                {"waveform": "sine", "start": 0.05, "duration": 0.5, "start_freq": 180, "end_freq": 110, "volume": 0.12, "attack": 0.02, "decay": 0.06, "sustain_level": 0.16, "release": 0.16, "seed": 127},
                {"waveform": "noise", "start": 0.02, "duration": 0.18, "volume": 0.05, "attack": 0.003, "decay": 0.02, "sustain_level": 0.0, "release": 0.05, "seed": 128},
            ],
        )

    def _make_transition_daybreak(self) -> pygame.mixer.Sound:
        return self._synth(
            0.6,
            [
                {"waveform": "triangle", "start_freq": 310, "end_freq": 420, "volume": 0.14, "attack": 0.02, "decay": 0.06, "sustain_level": 0.22, "release": 0.14, "seed": 129},
                {"waveform": "sine", "start": 0.08, "duration": 0.22, "start_freq": 520, "end_freq": 760, "volume": 0.14, "attack": 0.01, "decay": 0.04, "sustain_level": 0.16, "release": 0.08, "seed": 130},
                {"waveform": "sine", "start": 0.18, "duration": 0.18, "start_freq": 680, "end_freq": 980, "volume": 0.12, "attack": 0.008, "decay": 0.03, "sustain_level": 0.12, "release": 0.06, "seed": 131},
            ],
        )

    def _make_step_camp(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.13,
            [
                {"waveform": "noise", "duration": 0.038, "volume": 0.09, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.016, "seed": seed},
                {"waveform": "sine", "start": 0.006, "duration": 0.07, "start_freq": 128 + seed * 2, "end_freq": 88 + seed, "volume": 0.1, "attack": 0.002, "decay": 0.015, "sustain_level": 0.06, "release": 0.022, "seed": seed * 5},
            ],
        )

    def _make_step_path(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.12,
            [
                {"waveform": "noise", "duration": 0.028, "volume": 0.1, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.014, "seed": seed},
                {"waveform": "triangle", "start": 0.004, "duration": 0.05, "start_freq": 240 + seed * 3, "end_freq": 150 + seed * 2, "volume": 0.08, "attack": 0.001, "decay": 0.01, "sustain_level": 0.04, "release": 0.016, "seed": seed * 3},
                {"waveform": "sine", "start": 0.01, "duration": 0.05, "start_freq": 120 + seed, "end_freq": 92 + seed, "volume": 0.06, "attack": 0.002, "decay": 0.01, "sustain_level": 0.03, "release": 0.015, "seed": seed * 7},
            ],
        )

    def _make_step_forest(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.16,
            [
                {"waveform": "noise", "duration": 0.055, "volume": 0.12, "attack": 0.001, "decay": 0.016, "sustain_level": 0.0, "release": 0.024, "seed": seed},
                {"waveform": "sine", "start": 0.008, "duration": 0.08, "start_freq": 116 + seed * 2, "end_freq": 76 + seed, "volume": 0.08, "attack": 0.002, "decay": 0.014, "sustain_level": 0.04, "release": 0.02, "seed": seed * 5},
            ],
        )

    def _make_step_meadow(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.14,
            [
                {"waveform": "noise", "duration": 0.04, "volume": 0.08, "attack": 0.001, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed},
                {"waveform": "triangle", "start": 0.008, "duration": 0.065, "start_freq": 144 + seed * 2, "end_freq": 96 + seed, "volume": 0.08, "attack": 0.002, "decay": 0.014, "sustain_level": 0.04, "release": 0.02, "seed": seed * 7},
            ],
        )

    def _make_step_swamp(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.19,
            [
                {"waveform": "noise", "duration": 0.06, "volume": 0.14, "attack": 0.001, "decay": 0.014, "sustain_level": 0.0, "release": 0.03, "seed": seed},
                {"waveform": "saw", "start": 0.005, "duration": 0.09, "start_freq": 92 + seed, "end_freq": 52 + seed, "volume": 0.08, "attack": 0.001, "decay": 0.012, "sustain_level": 0.06, "release": 0.028, "seed": seed * 5},
                {"waveform": "sine", "start": 0.02, "duration": 0.07, "start_freq": 166 + seed * 2, "end_freq": 118 + seed, "volume": 0.05, "attack": 0.002, "decay": 0.01, "sustain_level": 0.04, "release": 0.02, "seed": seed * 11},
            ],
        )

    def _make_step_ruin(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.14,
            [
                {"waveform": "noise", "duration": 0.03, "volume": 0.09, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.014, "seed": seed},
                {"waveform": "square", "start": 0.004, "duration": 0.045, "start_freq": 410 + seed * 5, "end_freq": 242 + seed * 3, "volume": 0.08, "attack": 0.001, "decay": 0.01, "sustain_level": 0.03, "release": 0.018, "seed": seed * 3},
                {"waveform": "sine", "start": 0.01, "duration": 0.06, "start_freq": 132 + seed, "end_freq": 96 + seed, "volume": 0.05, "attack": 0.002, "decay": 0.012, "sustain_level": 0.03, "release": 0.018, "seed": seed * 7},
            ],
        )

    def _make_bonfire_pop(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.12,
            [
                {"waveform": "noise", "duration": 0.05, "volume": 0.12, "attack": 0.001, "decay": 0.01, "sustain_level": 0.0, "release": 0.02, "seed": seed},
                {"waveform": "sine", "start": 0.01, "duration": 0.07, "start_freq": 140 + seed * 4, "end_freq": 92 + seed * 2, "volume": 0.09, "attack": 0.002, "decay": 0.012, "sustain_level": 0.06, "release": 0.03, "seed": seed * 3},
            ],
        )

    def _make_night_chirp(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.24,
            [
                {"waveform": "sine", "start_freq": 1820 + seed * 18, "end_freq": 1540 + seed * 9, "volume": 0.09, "attack": 0.004, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed},
                {"waveform": "sine", "start": 0.08, "duration": 0.07, "start_freq": 2060 + seed * 16, "end_freq": 1660 + seed * 8, "volume": 0.08, "attack": 0.003, "decay": 0.018, "sustain_level": 0.0, "release": 0.025, "seed": seed * 7},
            ],
        )

    def _make_day_bird(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.32,
            [
                {"waveform": "sine", "start_freq": 980 + seed * 15, "end_freq": 1310 + seed * 18, "volume": 0.08, "attack": 0.006, "decay": 0.025, "sustain_level": 0.0, "release": 0.03, "vibrato_rate": 8.0, "vibrato_depth": 0.03, "seed": seed},
                {"waveform": "sine", "start": 0.09, "duration": 0.09, "start_freq": 860 + seed * 10, "end_freq": 1180 + seed * 12, "volume": 0.07, "attack": 0.004, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed * 11},
            ],
        )

    def _make_ambient_wind(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.88,
            [
                {"waveform": "noise", "duration": 0.88, "volume": 0.1, "attack": 0.08, "decay": 0.16, "sustain_level": 0.18, "release": 0.2, "seed": seed},
                {"waveform": "sine", "start": 0.04, "duration": 0.7, "start_freq": 220 + seed * 2, "end_freq": 148 + seed, "volume": 0.035, "attack": 0.1, "decay": 0.12, "sustain_level": 0.1, "release": 0.18, "seed": seed * 3},
            ],
        )

    def _make_ambient_rain(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.72,
            [
                {"waveform": "noise", "duration": 0.72, "volume": 0.11, "attack": 0.03, "decay": 0.06, "sustain_level": 0.22, "release": 0.12, "seed": seed},
                {"waveform": "noise", "start": 0.05, "duration": 0.1, "volume": 0.06, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.016, "seed": seed * 5},
                {"waveform": "noise", "start": 0.22, "duration": 0.08, "volume": 0.05, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.016, "seed": seed * 7},
                {"waveform": "noise", "start": 0.44, "duration": 0.08, "volume": 0.05, "attack": 0.001, "decay": 0.008, "sustain_level": 0.0, "release": 0.016, "seed": seed * 11},
            ],
        )

    def _make_ambient_grove(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.62,
            [
                {"waveform": "noise", "duration": 0.4, "volume": 0.07, "attack": 0.02, "decay": 0.03, "sustain_level": 0.08, "release": 0.08, "seed": seed},
                {"waveform": "triangle", "start": 0.16, "duration": 0.22, "start_freq": 292 + seed * 2, "end_freq": 182 + seed, "volume": 0.03, "attack": 0.02, "decay": 0.03, "sustain_level": 0.06, "release": 0.06, "seed": seed * 5},
            ],
        )

    def _make_ambient_swamp(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.54,
            [
                {"waveform": "sine", "start_freq": 182 + seed * 3, "end_freq": 144 + seed * 2, "volume": 0.05, "attack": 0.01, "decay": 0.04, "sustain_level": 0.12, "release": 0.08, "vibrato_rate": 5.0, "vibrato_depth": 0.04, "seed": seed},
                {"waveform": "sine", "start": 0.18, "duration": 0.14, "start_freq": 288 + seed * 4, "end_freq": 222 + seed * 3, "volume": 0.04, "attack": 0.01, "decay": 0.03, "sustain_level": 0.08, "release": 0.05, "seed": seed * 7},
                {"waveform": "noise", "start": 0.06, "duration": 0.12, "volume": 0.03, "attack": 0.005, "decay": 0.015, "sustain_level": 0.0, "release": 0.03, "seed": seed * 11},
            ],
        )

    def _make_ambient_ruin(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.6,
            [
                {"waveform": "square", "start": 0.04, "duration": 0.08, "start_freq": 312 + seed * 3, "end_freq": 250 + seed * 2, "volume": 0.04, "attack": 0.003, "decay": 0.02, "sustain_level": 0.04, "release": 0.03, "seed": seed},
                {"waveform": "noise", "start": 0.08, "duration": 0.05, "volume": 0.03, "attack": 0.002, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed * 5},
                {"waveform": "sine", "start": 0.18, "duration": 0.22, "start_freq": 178 + seed * 2, "end_freq": 132 + seed, "volume": 0.03, "attack": 0.02, "decay": 0.03, "sustain_level": 0.06, "release": 0.05, "seed": seed * 9},
            ],
        )

    def _make_zombie_groan(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            0.72,
            [
                {"waveform": "saw", "start_freq": 118 + seed * 2, "end_freq": 78 + seed, "volume": 0.08, "attack": 0.03, "decay": 0.08, "sustain_level": 0.14, "release": 0.16, "vibrato_rate": 4.0, "vibrato_depth": 0.03, "seed": seed},
                {"waveform": "sine", "start": 0.04, "duration": 0.5, "start_freq": 94 + seed, "end_freq": 66 + seed, "volume": 0.05, "attack": 0.04, "decay": 0.06, "sustain_level": 0.1, "release": 0.14, "seed": seed * 7},
                {"waveform": "noise", "start": 0.02, "duration": 0.12, "volume": 0.02, "attack": 0.004, "decay": 0.02, "sustain_level": 0.0, "release": 0.03, "seed": seed * 13},
            ],
        )

    def _make_zombie_horde(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            1.1,
            [
                {"waveform": "saw", "start_freq": 104 + seed, "end_freq": 62 + seed, "volume": 0.08, "attack": 0.04, "decay": 0.1, "sustain_level": 0.18, "release": 0.18, "seed": seed},
                {"waveform": "triangle", "start": 0.06, "duration": 0.74, "start_freq": 136 + seed * 2, "end_freq": 88 + seed, "volume": 0.05, "attack": 0.03, "decay": 0.08, "sustain_level": 0.12, "release": 0.16, "seed": seed * 5},
                {"waveform": "noise", "start": 0.02, "duration": 0.2, "volume": 0.03, "attack": 0.01, "decay": 0.02, "sustain_level": 0.0, "release": 0.04, "seed": seed * 11},
            ],
        )

    def _make_music_calm(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            1.45,
            [
                {"waveform": "triangle", "start_freq": 196 + seed * 2, "end_freq": 220 + seed * 2, "volume": 0.05, "attack": 0.08, "decay": 0.14, "sustain_level": 0.16, "release": 0.24, "seed": seed},
                {"waveform": "sine", "start": 0.18, "duration": 0.72, "start_freq": 294 + seed * 3, "end_freq": 330 + seed * 3, "volume": 0.045, "attack": 0.06, "decay": 0.1, "sustain_level": 0.14, "release": 0.18, "seed": seed * 3},
                {"waveform": "sine", "start": 0.44, "duration": 0.58, "start_freq": 392 + seed * 3, "end_freq": 440 + seed * 4, "volume": 0.03, "attack": 0.05, "decay": 0.08, "sustain_level": 0.1, "release": 0.14, "seed": seed * 5},
            ],
        )

    def _make_music_threat(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            1.28,
            [
                {"waveform": "saw", "start_freq": 110 + seed * 2, "end_freq": 92 + seed, "volume": 0.06, "attack": 0.03, "decay": 0.08, "sustain_level": 0.16, "release": 0.18, "seed": seed},
                {"waveform": "triangle", "start": 0.12, "duration": 0.58, "start_freq": 164 + seed * 2, "end_freq": 132 + seed, "volume": 0.045, "attack": 0.03, "decay": 0.06, "sustain_level": 0.12, "release": 0.14, "seed": seed * 3},
                {"waveform": "noise", "start": 0.0, "duration": 0.09, "volume": 0.015, "attack": 0.004, "decay": 0.012, "sustain_level": 0.0, "release": 0.02, "seed": seed * 7},
            ],
        )

    def _make_music_horde(self, seed: int) -> pygame.mixer.Sound:
        return self._synth(
            1.52,
            [
                {"waveform": "saw", "start_freq": 92 + seed, "end_freq": 66 + seed, "volume": 0.07, "attack": 0.04, "decay": 0.1, "sustain_level": 0.18, "release": 0.22, "seed": seed},
                {"waveform": "square", "start": 0.18, "duration": 0.56, "start_freq": 138 + seed * 2, "end_freq": 102 + seed, "volume": 0.03, "attack": 0.02, "decay": 0.05, "sustain_level": 0.08, "release": 0.12, "seed": seed * 3},
                {"waveform": "triangle", "start": 0.42, "duration": 0.54, "start_freq": 162 + seed * 2, "end_freq": 118 + seed, "volume": 0.038, "attack": 0.03, "decay": 0.05, "sustain_level": 0.1, "release": 0.14, "seed": seed * 5},
                {"waveform": "noise", "start": 0.0, "duration": 0.12, "volume": 0.016, "attack": 0.005, "decay": 0.016, "sustain_level": 0.0, "release": 0.024, "seed": seed * 7},
            ],
        )
