from __future__ import annotations

import pygame
from pygame import Vector2

from ...core.config import CAMP_CENTER, DAWN_MINUTES, DUSK_MINUTES, TESTING_SETTINGS


def unlimited_resources_enabled(world) -> bool:
    return bool(TESTING_SETTINGS.get("unlimited_resources", False))


def maintain_unlimited_resources(world) -> None:
    if not world.unlimited_resources_enabled():
        return
    reserves = {
        "logs": 9999,
        "wood": 9999,
        "food": 9999,
        "herbs": 9999,
        "scrap": 9999,
        "meals": 9999,
        "medicine": 9999,
    }
    for resource, amount in reserves.items():
        setattr(world, resource, amount)


def is_night(world) -> bool:
    time_value = world.time_minutes % (24 * 60)
    return time_value < DAWN_MINUTES or time_value >= DUSK_MINUTES


def camp_rect(world, padding: float = 0.0):
    half = world.camp_half_size + padding
    return pygame.Rect(
        int(CAMP_CENTER.x - half),
        int(CAMP_CENTER.y - half),
        int(half * 2),
        int(half * 2),
    )


def point_in_camp_square(world, pos: Vector2, padding: float = 0.0) -> bool:
    rect = world.camp_rect(padding)
    return rect.left <= pos.x <= rect.right and rect.top <= pos.y <= rect.bottom


def guard_posts(world) -> list[Vector2]:
    half = world.camp_half_size - 26
    return [
        CAMP_CENTER + Vector2(-half * 0.62, -half),
        CAMP_CENTER + Vector2(half * 0.62, -half),
        CAMP_CENTER + Vector2(half, -half * 0.22),
        CAMP_CENTER + Vector2(half, half * 0.22),
        CAMP_CENTER + Vector2(half * 0.62, half),
        CAMP_CENTER + Vector2(-half * 0.62, half),
        CAMP_CENTER + Vector2(-half, half * 0.22),
        CAMP_CENTER + Vector2(-half, -half * 0.22),
    ]


def layout_camp_core(world) -> None:
    world.camp_half_size = 214 + world.camp_level * 88
    world.stockpile_pos = CAMP_CENTER + Vector2(-world.camp_half_size * 0.1, world.camp_half_size * 0.48)
    world.bonfire_pos = Vector2(CAMP_CENTER)
    world.kitchen_pos = CAMP_CENTER + Vector2(world.camp_half_size * 0.46, world.camp_half_size * 0.16)
    world.workshop_pos = CAMP_CENTER + Vector2(-world.camp_half_size * 0.54, world.camp_half_size * 0.08)
    world.radio_pos = CAMP_CENTER + Vector2(-world.camp_half_size * 0.04, -world.camp_half_size * 0.52)


def create_recruit_pool(world) -> list[dict[str, object]]:
    return [
        {"name": "Ayla", "role": "batedora", "traits": ("sociavel", "corajoso")},
        {"name": "Ravi", "role": "lenhador", "traits": ("teimoso", "resiliente")},
        {"name": "Noa", "role": "vigia", "traits": ("corajoso", "paranoico")},
        {"name": "Breno", "role": "artesa", "traits": ("gentil", "leal")},
        {"name": "Tainah", "role": "cozinheiro", "traits": ("sociavel", "gentil")},
        {"name": "Cael", "role": "mensageiro", "traits": ("paranoico", "resiliente")},
        {"name": "Liora", "role": "batedora", "traits": ("leal", "sociavel")},
        {"name": "Davi", "role": "lenhador", "traits": ("teimoso", "rancoroso")},
        {"name": "Mina", "role": "vigia", "traits": ("corajoso", "leal")},
        {"name": "Icaro", "role": "artesa", "traits": ("gentil", "resiliente")},
        {"name": "Sara", "role": "cozinheiro", "traits": ("gentil", "paranoico")},
        {"name": "Joel", "role": "mensageiro", "traits": ("rancoroso", "resiliente")},
    ]


def is_near_path(world, pos: Vector2, radius: float) -> bool:
    radius_sq = radius * radius
    for path in world.path_network:
        for point in path[::2]:
            if pos.distance_squared_to(point) <= radius_sq:
                return True
    return False









