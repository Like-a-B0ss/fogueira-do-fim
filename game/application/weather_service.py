from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..core.config import WEATHER_SETTINGS, clamp, lerp

if TYPE_CHECKING:
    from ..app.session import Game


def weather_strength_range(_game: "Game", kind: str) -> tuple[float, float]:
    ranges = dict(WEATHER_SETTINGS.get("strength_ranges", {}))
    selected = ranges.get(kind, [0.2, 0.6])
    return float(selected[0]), float(selected[1])


def weather_duration_range(_game: "Game", kind: str) -> tuple[float, float]:
    ranges = dict(WEATHER_SETTINGS.get("duration_ranges", {}))
    selected = ranges.get(kind, [24.0, 40.0])
    return float(selected[0]), float(selected[1])


def weather_display_name(_game: "Game", kind: str, strength: float) -> str:
    strength = clamp(float(strength), 0.0, 1.0)
    if kind == "clear":
        return "ceu aberto" if strength < 0.28 else "claridade limpa"
    if kind == "cloudy":
        return "ceu nublado" if strength < 0.62 else "nuvens baixas"
    if kind == "wind":
        return "vento nas copas" if strength < 0.68 else "rajadas frias"
    if kind == "rain":
        return "chuva fina" if strength < 0.62 else "chuva fechada"
    if kind == "mist":
        return "bruma rasteira" if strength < 0.7 else "neblina densa"
    if kind == "storm":
        return "tempestade ao longe" if strength < 0.76 else "tempestade pesada"
    return "tempo instavel"


def weather_transition_options(game: "Game", previous_kind: str) -> tuple[tuple[str, ...], tuple[float, ...]]:
    table_key = "transition_weights_early" if game.day <= 2 else "transition_weights_late"
    tables = dict(WEATHER_SETTINGS.get(table_key, {}))
    mapping = dict(tables.get(previous_kind, tables.get("clear", {"clear": 1.0})))
    return tuple(mapping.keys()), tuple(float(weight) for weight in mapping.values())


def roll_weather(game: "Game", *, initial: bool = False) -> None:
    previous_kind = game.weather_target_kind if not initial else game.weather_kind
    options, weights = game.weather_transition_options(previous_kind)
    repeat_chance = float(WEATHER_SETTINGS.get("repeat_same_weather_chance", 0.24))
    if not initial and game.random.random() < repeat_chance:
        next_kind = previous_kind
    else:
        next_kind = game.random.choices(options, weights=weights, k=1)[0]

    min_strength, max_strength = game.weather_strength_range(next_kind)
    next_strength = game.random.uniform(min_strength, max_strength)
    duration_low, duration_high = game.weather_duration_range(next_kind)
    game.weather_timer = game.random.uniform(duration_low, duration_high)

    if initial:
        game.weather_kind = next_kind
        game.weather_strength = next_strength
        game.weather_target_kind = next_kind
        game.weather_target_strength = next_strength
        game.weather_front_progress = 1.0
        game.weather_front_duration = 0.0
        game.weather_label = game.weather_display_name(next_kind, next_strength)
        return

    game.weather_target_kind = next_kind
    game.weather_target_strength = next_strength
    game.weather_front_progress = 0.0
    transition_range = WEATHER_SETTINGS.get("transition_duration_range", [10.0, 18.0])
    game.weather_front_duration = game.random.uniform(
        float(transition_range[0]),
        float(transition_range[1]),
    )
    if next_kind == previous_kind:
        game.weather_front_duration *= float(WEATHER_SETTINGS.get("repeat_front_duration_scale", 0.6))
        game.weather_timer *= float(WEATHER_SETTINGS.get("repeat_timer_scale", 0.84))
    else:
        message = str(
            dict(WEATHER_SETTINGS.get("messages", {})).get(next_kind, "O tempo mudou sobre a clareira.")
        )
        game.set_event_message(message, duration=5.8)


def update_weather(game: "Game", dt: float) -> None:
    game.weather_timer -= dt
    if game.weather_timer <= 0:
        game.roll_weather()

    if game.weather_front_progress < 1.0:
        game.weather_front_progress = clamp(
            game.weather_front_progress + dt / max(0.1, game.weather_front_duration),
            0.0,
            1.0,
        )
        if game.weather_front_progress >= 1.0:
            game.weather_kind = game.weather_target_kind
            game.weather_strength = game.weather_target_strength
            game.weather_front_duration = 0.0

    game.weather_gust_phase += dt * (0.24 + game.weather_wind_factor() * 0.92)
    gust_wave = 0.5 + 0.5 * math.sin(game.weather_gust_phase)
    game.weather_gust_strength = clamp(
        game.weather_wind_factor() * (0.58 + gust_wave * 0.52),
        0.0,
        1.0,
    )

    flash_settings = dict(WEATHER_SETTINGS.get("flash", {}))
    game.weather_flash = max(
        0.0,
        game.weather_flash - dt * float(flash_settings.get("decay_per_second", 1.75)),
    )
    game.weather_flash_timer -= dt
    if (
        game.weather_storm_factor() > float(flash_settings.get("storm_threshold", 0.46))
        and game.weather_flash_timer <= 0
    ):
        intensity_range = flash_settings.get("intensity_range", [0.16, 0.34])
        interval_range = flash_settings.get("interval_range", [4.5, 8.6])
        game.weather_flash = (
            game.random.uniform(float(intensity_range[0]), float(intensity_range[1]))
            * game.weather_storm_factor()
        )
        game.weather_flash_timer = game.random.uniform(
            float(interval_range[0]),
            float(interval_range[1]),
        ) / max(0.32, game.weather_storm_factor())

    blend = game.weather_transition_factor()
    shown_kind = game.weather_target_kind if blend > 0.55 else game.weather_kind
    shown_strength = lerp(game.weather_strength, game.weather_target_strength, blend)
    game.weather_label = game.weather_display_name(shown_kind, shown_strength)
