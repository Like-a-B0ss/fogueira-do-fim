from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

import pygame
from pygame import Vector2


DEFAULT_GAME_SETTINGS: dict[str, object] = {
    "display": {
        "screen_width": 1280,
        "screen_height": 720,
        "fps": 60,
        "fullscreen": False,
    },
    "world": {
        "world_width": 2800,
        "world_height": 2100,
        "chunk_size": 360,
        "camp_center_ratio": [0.52, 0.56],
        "camp_radius": 320,
    },
    "day_cycle": {
        "day_seconds": 240.0,
        "start_time_minutes": 7 * 60 + 15,
        "dawn_minutes": 6 * 60,
        "dusk_minutes": 18 * 60 + 30,
    },
    "ui": {
        "runtime_defaults": {
            "master_volume": 1.0,
            "ambience_volume": 1.0,
            "music_volume": 1.0,
            "screen_shake_scale": 1.0,
            "fog_strength": 1.0,
            "ui_contrast": 1.0,
        },
        "runtime_ranges": {
            "master_volume": {"label": "Volume Geral", "step": 0.05, "min": 0.0, "max": 1.0},
            "ambience_volume": {"label": "Ambiência", "step": 0.05, "min": 0.0, "max": 1.0},
            "music_volume": {"label": "Música", "step": 0.05, "min": 0.0, "max": 1.0},
            "screen_shake_scale": {"label": "Tremor de Tela", "step": 0.1, "min": 0.0, "max": 1.4},
            "fog_strength": {"label": "Força da Neblina", "step": 0.1, "min": 0.35, "max": 1.25},
            "ui_contrast": {"label": "Contraste da HUD", "step": 0.1, "min": 0.7, "max": 1.4},
        },
        "title_background_spawn_range": [7.0, 12.0],
    },
    "gameplay": {
        "starting_resources": {
            "logs": 10,
            "wood": 9,
            "food": 9,
            "herbs": 3,
            "scrap": 6,
            "meals": 2,
            "medicine": 1,
        },
        "camp_level_start": 0,
        "max_camp_level": 5,
        "bonfire_start": {"heat": 64.0, "ember_bed": 52.0},
        "timers": {
            "dynamic_event_cooldown": 32.0,
            "spawn_timer": 4.8,
            "day_spawn_timer": 22.0,
        },
    },
    "testing": {
        "unlimited_resources": False
    },
    "weather": {
        "repeat_same_weather_chance": 0.24,
        "repeat_front_duration_scale": 0.6,
        "repeat_timer_scale": 0.84,
        "transition_duration_range": [10.0, 18.0],
        "strength_ranges": {
            "clear": [0.12, 0.5],
            "cloudy": [0.28, 0.82],
            "wind": [0.28, 0.88],
            "rain": [0.34, 0.84],
            "mist": [0.36, 0.9],
            "storm": [0.52, 0.98],
        },
        "duration_ranges": {
            "clear": [34.0, 54.0],
            "cloudy": [28.0, 46.0],
            "wind": [24.0, 42.0],
            "rain": [20.0, 38.0],
            "mist": [18.0, 32.0],
            "storm": [12.0, 22.0],
        },
        "transition_weights_early": {
            "clear": {"clear": 0.28, "cloudy": 0.32, "wind": 0.18, "mist": 0.12, "rain": 0.1},
            "cloudy": {"clear": 0.18, "cloudy": 0.28, "wind": 0.2, "rain": 0.2, "mist": 0.14},
            "wind": {"clear": 0.16, "cloudy": 0.24, "wind": 0.26, "rain": 0.18, "storm": 0.08},
            "rain": {"cloudy": 0.24, "rain": 0.28, "wind": 0.14, "mist": 0.24, "storm": 0.1},
            "mist": {"clear": 0.16, "cloudy": 0.28, "mist": 0.34, "rain": 0.22},
            "storm": {"rain": 0.4, "wind": 0.22, "cloudy": 0.26, "storm": 0.12},
        },
        "transition_weights_late": {
            "clear": {"clear": 0.22, "cloudy": 0.28, "wind": 0.18, "mist": 0.14, "rain": 0.18},
            "cloudy": {"clear": 0.14, "cloudy": 0.24, "wind": 0.16, "rain": 0.18, "mist": 0.16, "storm": 0.12},
            "wind": {"clear": 0.12, "cloudy": 0.2, "wind": 0.22, "rain": 0.2, "storm": 0.18},
            "rain": {"cloudy": 0.2, "rain": 0.22, "wind": 0.14, "mist": 0.18, "storm": 0.26},
            "mist": {"clear": 0.14, "cloudy": 0.22, "mist": 0.28, "rain": 0.2, "wind": 0.16},
            "storm": {"rain": 0.34, "wind": 0.22, "cloudy": 0.24, "storm": 0.2},
        },
        "messages": {
            "clear": "As nuvens abriram e a mata voltou a respirar.",
            "cloudy": "O céu fechou e a floresta entrou num cinza pesado.",
            "wind": "O vento virou e as copas começaram a gemer.",
            "rain": "Uma chuva correu entre as copas e desceu sobre a clareira.",
            "mist": "Uma bruma rasteira se espalhou pelo chão da mata.",
            "storm": "O horizonte escureceu e uma tempestade começou a se formar.",
        },
        "flash": {
            "storm_threshold": 0.46,
            "decay_per_second": 1.75,
            "intensity_range": [0.16, 0.34],
            "interval_range": [4.5, 8.6],
        },
    },
    "palette": {
        "bg": [16, 22, 20],
        "forest_floor": [28, 48, 34],
        "forest_floor_dark": [18, 31, 24],
        "forest_floor_light": [55, 88, 58],
        "clearing": [63, 77, 49],
        "path": [97, 80, 56],
        "path_light": [141, 116, 75],
        "wood": [128, 92, 58],
        "wood_dark": [72, 47, 31],
        "accent": [205, 161, 84],
        "accent_soft": [232, 193, 118],
        "ui_bg": [18, 26, 28],
        "ui_panel": [28, 39, 42],
        "ui_line": [87, 112, 112],
        "text": [228, 224, 209],
        "muted": [147, 160, 146],
        "danger": [201, 78, 62],
        "danger_soft": [227, 118, 97],
        "heal": [112, 190, 128],
        "energy": [116, 155, 216],
        "morale": [218, 181, 89],
        "night": [10, 20, 31],
        "fog": [60, 84, 92],
        "light": [255, 190, 112],
        "ember": [244, 140, 72],
    },
    "role_colors": {
        "lenhador": [192, 148, 96],
        "vigia": [120, 171, 200],
        "batedora": [166, 197, 123],
        "artesa": [218, 144, 111],
        "cozinheiro": [225, 191, 111],
        "mensageiro": [182, 143, 201],
    },
    "focus_labels": {
        "balanced": "Equilíbrio",
        "supply": "Suprimentos",
        "fortify": "Fortificar",
        "morale": "Moral",
    },
}


SETTINGS_FILE = Path("game_settings.json")


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def _load_external_settings() -> dict[str, object]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


GAME_SETTINGS = _deep_merge(DEFAULT_GAME_SETTINGS, _load_external_settings())


def setting(*keys: str, default: object | None = None) -> object | None:
    current: object = GAME_SETTINGS
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


DISPLAY_SETTINGS = dict(setting("display", default={}) or {})
WORLD_SETTINGS = dict(setting("world", default={}) or {})
DAY_CYCLE_SETTINGS = dict(setting("day_cycle", default={}) or {})
UI_SETTINGS = dict(setting("ui", default={}) or {})
GAMEPLAY_SETTINGS = dict(setting("gameplay", default={}) or {})
TESTING_SETTINGS = dict(setting("testing", default={}) or {})
WEATHER_SETTINGS = dict(setting("weather", default={}) or {})


SCREEN_WIDTH = int(DISPLAY_SETTINGS.get("screen_width", 1480))
SCREEN_HEIGHT = int(DISPLAY_SETTINGS.get("screen_height", 900))
FPS = int(DISPLAY_SETTINGS.get("fps", 60))

WORLD_WIDTH = int(WORLD_SETTINGS.get("world_width", 2800))
WORLD_HEIGHT = int(WORLD_SETTINGS.get("world_height", 2100))
CHUNK_SIZE = int(WORLD_SETTINGS.get("chunk_size", 360))

camp_center_ratio = WORLD_SETTINGS.get("camp_center_ratio", [0.52, 0.56])
CAMP_CENTER = Vector2(WORLD_WIDTH * float(camp_center_ratio[0]), WORLD_HEIGHT * float(camp_center_ratio[1]))
CAMP_RADIUS = float(WORLD_SETTINGS.get("camp_radius", 320))

DAY_SECONDS = float(DAY_CYCLE_SETTINGS.get("day_seconds", 240.0))
MINUTES_PER_SECOND = 24 * 60 / DAY_SECONDS
START_TIME_MINUTES = float(DAY_CYCLE_SETTINGS.get("start_time_minutes", 7 * 60 + 15))
DAWN_MINUTES = float(DAY_CYCLE_SETTINGS.get("dawn_minutes", 6 * 60))
DUSK_MINUTES = float(DAY_CYCLE_SETTINGS.get("dusk_minutes", 18 * 60 + 30))


PALETTE = {key: tuple(value) for key, value in dict(setting("palette", default={}) or {}).items()}


ROLE_COLORS = {key: tuple(value) for key, value in dict(setting("role_colors", default={}) or {}).items()}


FOCUS_LABELS = dict(setting("focus_labels", default={}) or {})


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def format_clock(total_minutes: float) -> str:
    total = int(total_minutes) % (24 * 60)
    hour = total // 60
    minute = total % 60
    return f"{hour:02d}:{minute:02d}"


def angle_to_vector(angle: float) -> Vector2:
    return Vector2(math.cos(angle), math.sin(angle))


def load_font(size: int, *, title: bool = False, bold: bool = False) -> pygame.font.Font:
    choices = "Constantia,Georgia,Cambria,Palatino Linotype,Book Antiqua"
    if title:
        choices = "Constantia,Georgia,Palatino Linotype,Cambria"
    path = pygame.font.match_font(choices, bold=bold)
    return pygame.font.Font(path, size)
