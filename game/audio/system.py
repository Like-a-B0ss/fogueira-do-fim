from __future__ import annotations

import random

import pygame
from pygame import Vector2

from . import runtime as audio_runtime
from . import synthesis as audio_synthesis


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
        self.scene_music_tag = ""
        self.frontend_phrase_index = 0
        self.master_volume = 0.86
        self.ambience_volume = 0.92
        self.music_volume = 1.0
        self.listener_pos = Vector2()

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

    def set_listener_position(self, pos: Vector2) -> None:
        """Atualiza a posicao do ouvinte para o audio posicional."""
        self.listener_pos = Vector2(pos)

    def play_ui(self, cue: str = "ui") -> None:
        cue_map = {
            "ui": "ui_confirm",
            "focus": "ui_focus",
            "back": "ui_back",
            "order": "ui_order",
        }
        self._play(cue_map.get(cue, "ui_confirm"), volume_scale=0.52)

    def play_attack(self, *, source_pos: Vector2 | None = None) -> None:
        self._play("attack", volume_scale=0.6, source_pos=source_pos, max_distance=190.0)

    def play_interact(self, cue: str = "interact", *, source_pos: Vector2 | None = None) -> None:
        cue_map = {
            "interact": "interact",
            "repair": "impact_wood",
            "salvage": "impact_wood",
            "bonfire": "interact",
        }
        max_distance = 165.0 if source_pos is not None else 210.0
        if cue in {"repair", "salvage"}:
            max_distance = 130.0
        self._play(cue_map.get(cue, "interact"), volume_scale=0.58, source_pos=source_pos, max_distance=max_distance)

    def play_alert(self, *, source_pos: Vector2 | None = None) -> None:
        self._play("alert", volume_scale=0.72, source_pos=source_pos, max_distance=340.0)

    def play_transition(self, cue: str = "transition") -> None:
        cue_map = {
            "transition": "transition_start",
            "start": "transition_start",
            "restart": "transition_restart",
            "nightfall": "transition_nightfall",
            "daybreak": "transition_daybreak",
        }
        self._play(cue_map.get(cue, "transition_start"), volume_scale=0.68)

    def debug_cue_names(self) -> list[str]:
        return sorted(self.cues)

    def play_debug_cue(self, cue: str) -> bool:
        if cue not in self.cues:
            return False
        category = "sfx"
        if cue.startswith("music_"):
            category = "music"
        elif cue.startswith("ambient_") or cue.startswith("zombie_"):
            category = "ambience"
        self._play(cue, volume_scale=0.86, category=category)
        return True

    def play_impact(self, cue: str = "flesh", *, source_pos: Vector2 | None = None) -> None:
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
        max_distance = 155.0 if source_pos is not None else 250.0
        if cue == "wood":
            max_distance = 125.0
        self._play(target, volume_scale=volume_map.get(cue, 0.54), source_pos=source_pos, max_distance=max_distance)

    def update(self, game, dt: float) -> None:
        audio_runtime.update(self, game, dt)

    def _update_player_steps(self, game, dt: float) -> None:
        audio_runtime.update_player_steps(self, game, dt)

    def _update_bonfire(self, game) -> None:
        audio_runtime.update_bonfire(self, game)

    def _update_biome_ambience(self, game) -> None:
        audio_runtime.update_biome_ambience(self, game)

    def _update_weather(self, game) -> None:
        audio_runtime.update_weather(self, game)

    def _update_zombie_ambience(self, game) -> None:
        audio_runtime.update_zombie_ambience(self, game)

    def _update_music(self, game) -> None:
        audio_runtime.update_music(self, game)

    def apply_settings(self, settings: dict[str, float]) -> None:
        self.master_volume = float(settings.get("master_volume", self.master_volume))
        self.ambience_volume = float(settings.get("ambience_volume", self.ambience_volume))
        self.music_volume = float(settings.get("music_volume", self.music_volume))

    def _distance_gain(
        self,
        source_pos: Vector2 | None,
        *,
        min_distance: float = 22.0,
        max_distance: float = 260.0,
    ) -> float:
        if source_pos is None:
            return 1.0
        distance = self.listener_pos.distance_to(Vector2(source_pos))
        if distance <= min_distance:
            return 1.0
        if distance >= max_distance:
            return 0.0
        t = (distance - min_distance) / max(1.0, max_distance - min_distance)
        return max(0.0, (1.0 - t) ** 3.4)

    def _play(
        self,
        cue: str,
        *,
        volume_scale: float = 1.0,
        category: str = "sfx",
        source_pos: Vector2 | None = None,
        max_distance: float = 260.0,
    ) -> None:
        if not self.available:
            return
        variants = self.cues.get(cue)
        if not variants:
            return
        sound = self.rng.choice(variants)
        category_scale = {
            "sfx": 1.0,
            "ambience": self.ambience_volume * 1.35,
            "music": self.music_volume * 1.55,
        }.get(category, 1.0)
        distance_scale = self._distance_gain(source_pos, max_distance=max_distance)
        if distance_scale <= 0.0:
            return
        final_volume = max(0.0, min(1.0, volume_scale * self.master_volume * category_scale * distance_scale))
        channel = sound.play()
        if channel is not None:
            channel.set_volume(final_volume)

    def _build_sound_bank(self) -> dict[str, list[pygame.mixer.Sound]]:
        return audio_synthesis.build_sound_bank(self)

    def _osc(self, waveform: str, phase: float, rng: random.Random) -> float:
        return audio_synthesis.osc(waveform, phase, rng)

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
        return audio_synthesis.envelope(
            self,
            index,
            frame_count,
            attack=attack,
            decay=decay,
            sustain_level=sustain_level,
            release=release,
            duration=duration,
        )

    def _synth(self, duration: float, layers: list[dict[str, float | str | tuple]]) -> pygame.mixer.Sound:
        return audio_synthesis.synth(self, duration, layers)

    def _make_ui_confirm(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ui_confirm(self, seed)

    def _make_ui_focus(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ui_focus(self, seed)

    def _make_ui_back(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ui_back(self, seed)

    def _make_ui_order(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ui_order(self, seed)

    def _make_attack(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_attack(self, seed)

    def _make_interact(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_interact(self, seed)

    def _make_alert(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_alert(self, seed)

    def _make_impact_flesh(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_impact_flesh(self, seed)

    def _make_impact_wood(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_impact_wood(self, seed)

    def _make_impact_body(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_impact_body(self, seed)

    def _make_transition_start(self) -> pygame.mixer.Sound:
        return audio_synthesis.make_transition_start(self)

    def _make_transition_restart(self) -> pygame.mixer.Sound:
        return audio_synthesis.make_transition_restart(self)

    def _make_transition_nightfall(self) -> pygame.mixer.Sound:
        return audio_synthesis.make_transition_nightfall(self)

    def _make_transition_daybreak(self) -> pygame.mixer.Sound:
        return audio_synthesis.make_transition_daybreak(self)

    def _make_step_camp(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_step_camp(self, seed)

    def _make_step_path(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_step_path(self, seed)

    def _make_step_forest(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_step_forest(self, seed)

    def _make_step_meadow(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_step_meadow(self, seed)

    def _make_step_swamp(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_step_swamp(self, seed)

    def _make_step_ruin(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_step_ruin(self, seed)

    def _make_bonfire_pop(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_bonfire_pop(self, seed)

    def _make_night_chirp(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_night_chirp(self, seed)

    def _make_day_bird(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_day_bird(self, seed)

    def _make_ambient_wind(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ambient_wind(self, seed)

    def _make_ambient_rain(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ambient_rain(self, seed)

    def _make_ambient_grove(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ambient_grove(self, seed)

    def _make_ambient_swamp(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ambient_swamp(self, seed)

    def _make_ambient_ruin(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ambient_ruin(self, seed)

    def _make_ambient_dread(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_ambient_dread(self, seed)

    def _make_zombie_groan(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_zombie_groan(self, seed)

    def _make_zombie_far(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_zombie_far(self, seed)

    def _make_zombie_horde(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_zombie_horde(self, seed)

    def _make_music_calm(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_music_calm(self, seed)

    def _make_music_dread(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_music_dread(self, seed)

    def _make_music_threat(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_music_threat(self, seed)

    def _make_music_horde(self, seed: int) -> pygame.mixer.Sound:
        return audio_synthesis.make_music_horde(self, seed)

    def _make_music_frontend(self, seed: int, profile: str = "veil") -> pygame.mixer.Sound:
        return audio_synthesis.make_music_frontend(self, seed, profile)







