from __future__ import annotations

import math

import pygame
from pygame import Vector2


SCREEN_WIDTH = 1480
SCREEN_HEIGHT = 900
FPS = 60

WORLD_WIDTH = 2800
WORLD_HEIGHT = 2100
CHUNK_SIZE = 360

CAMP_CENTER = Vector2(WORLD_WIDTH * 0.52, WORLD_HEIGHT * 0.56)
CAMP_RADIUS = 320

DAY_SECONDS = 240.0
MINUTES_PER_SECOND = 24 * 60 / DAY_SECONDS
START_TIME_MINUTES = 7 * 60 + 15
DAWN_MINUTES = 6 * 60
DUSK_MINUTES = 18 * 60 + 30


PALETTE = {
    "bg": (16, 22, 20),
    "forest_floor": (28, 48, 34),
    "forest_floor_dark": (18, 31, 24),
    "forest_floor_light": (55, 88, 58),
    "clearing": (63, 77, 49),
    "path": (97, 80, 56),
    "path_light": (141, 116, 75),
    "wood": (128, 92, 58),
    "wood_dark": (72, 47, 31),
    "accent": (205, 161, 84),
    "accent_soft": (232, 193, 118),
    "ui_bg": (18, 26, 28),
    "ui_panel": (28, 39, 42),
    "ui_line": (87, 112, 112),
    "text": (228, 224, 209),
    "muted": (147, 160, 146),
    "danger": (201, 78, 62),
    "danger_soft": (227, 118, 97),
    "heal": (112, 190, 128),
    "energy": (116, 155, 216),
    "morale": (218, 181, 89),
    "night": (10, 20, 31),
    "fog": (60, 84, 92),
    "light": (255, 190, 112),
    "ember": (244, 140, 72),
}


ROLE_COLORS = {
    "lenhador": (192, 148, 96),
    "vigia": (120, 171, 200),
    "batedora": (166, 197, 123),
    "artesa": (218, 144, 111),
    "cozinheiro": (225, 191, 111),
    "mensageiro": (182, 143, 201),
}


FOCUS_LABELS = {
    "balanced": "Equilibrio",
    "supply": "Suprimentos",
    "fortify": "Fortificar",
    "morale": "Moral",
}


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
