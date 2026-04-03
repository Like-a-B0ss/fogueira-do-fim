from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame
from pygame import Vector2

from ...core.config import CAMP_CENTER, WORLD_HEIGHT, WORLD_WIDTH, angle_to_vector, clamp
from ...core.models import InterestPoint, WorldFeature

if TYPE_CHECKING:
    from ...app.session import Game


def generate_world_features(game: "Game") -> list[WorldFeature]:
    plan = (
        ("grove", 4, (170, 290)),
        ("meadow", 3, (150, 250)),
        ("swamp", 2, (140, 220)),
        ("ruin", 2, (120, 180)),
    )
    features: list[WorldFeature] = []
    for kind, count, radius_range in plan:
        created = 0
        attempts = 0
        while created < count and attempts < 500:
            attempts += 1
            radius = game.random.uniform(*radius_range)
            pos = game.random_world_pos(180)
            if pos.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 320:
                continue
            if any(pos.distance_to(feature.pos) < (radius + feature.radius) * 0.72 for feature in features):
                continue
            features.append(WorldFeature(kind, pos, radius, game.random.random()))
            created += 1
    return features


def generate_interest_points(game: "Game") -> list[InterestPoint]:
    templates = {
        "grove": [
            ("herb_cache", "ervas silvestres"),
            ("hunter_blind", "posto de cacador"),
        ],
        "meadow": [
            ("lost_cart", "carroca esquecida"),
            ("flower_shrine", "canteiro raro"),
        ],
        "swamp": [
            ("sunken_cache", "caixa semi-afundada"),
            ("reed_nest", "ninho entre juncos"),
        ],
        "ruin": [
            ("tool_crate", "caixote de oficina"),
            ("alarm_nest", "sirene quebrada"),
        ],
    }

    interest_points: list[InterestPoint] = []
    for feature in game.world_features:
        event_kind, label = game.random.choice(templates[feature.kind])
        angle = game.random.uniform(0, math.tau)
        offset = angle_to_vector(angle) * game.random.uniform(feature.radius * 0.18, feature.radius * 0.55)
        pos = Vector2(feature.pos) + offset
        pos.x = clamp(pos.x, 70, WORLD_WIDTH - 70)
        pos.y = clamp(pos.y, 70, WORLD_HEIGHT - 70)
        interest_points.append(
            InterestPoint(
                feature_kind=feature.kind,
                event_kind=event_kind,
                label=label,
                pos=pos,
                radius=26 if feature.kind != "ruin" else 30,
                pulse=game.random.uniform(0, math.tau),
            )
        )
    return interest_points


def create_fog_of_war_surface(game: "Game") -> pygame.Surface:
    game.fog_reveals = []
    game.fog_reveal_keys = set()
    game.record_fog_reveal(CAMP_CENTER, game.camp_clearance_radius() + 120)
    game.record_fog_reveal(game.player.pos, 156)
    return pygame.Surface((1, 1), pygame.SRCALPHA)


def fog_reveal_key(_game: "Game", center: Vector2, radius: float) -> tuple[int, int, int]:
    return (int(center.x // 26), int(center.y // 26), int(radius // 8))


def record_fog_reveal(game: "Game", center: Vector2, radius: float) -> None:
    key = game.fog_reveal_key(center, radius)
    if key in getattr(game, "fog_reveal_keys", set()):
        return
    game.fog_reveal_keys.add(key)
    game.fog_reveals.append((Vector2(center), float(radius)))


def visible_fog_reveals(game: "Game", view_rect: pygame.Rect) -> list[tuple[Vector2, float]]:
    margin_rect = view_rect.inflate(420, 420)
    visible: list[tuple[Vector2, float]] = []
    for center, radius in getattr(game, "fog_reveals", []):
        if margin_rect.collidepoint(int(center.x), int(center.y)):
            visible.append((center, radius))
    return visible


def reveal_world_around_player(game: "Game") -> None:
    game.record_fog_reveal(game.player.pos, 186)
    if game.player.distance_to(game.bonfire_pos) < game.camp_clearance_radius() + 40:
        game.record_fog_reveal(CAMP_CENTER, game.camp_clearance_radius() + 88)
    for survivor in game.living_survivors():
        game.record_fog_reveal(survivor.pos, 92)


def feature_label(_game: "Game", kind: str) -> str:
    return {
        "grove": "Bosque Fechado",
        "meadow": "Clareira Alta",
        "swamp": "Brejo Escuro",
        "ruin": "Ruinas Velhas",
        "forest": "Mata Profunda",
        "ashland": "Cinzas Frias",
        "redwood": "Bosque Gigante",
        "quarry": "Pedreira Morta",
        "camp": "Clareira do Campo",
    }.get(kind, "Mata Fechada")









