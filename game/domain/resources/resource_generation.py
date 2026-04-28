from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import Vector2

from ...core.config import CAMP_CENTER, WORLD_HEIGHT, WORLD_WIDTH, angle_to_vector, clamp
from ...core.models import ResourceNode

if TYPE_CHECKING:
    from ...app.session import Game


def local_tree_density(game: "Game", pos: Vector2) -> float:
    density = 0.72
    distance_to_camp = pos.distance_to(CAMP_CENTER)
    if distance_to_camp < game.camp_clearance_radius() + 170:
        density -= 0.42

    for feature in game.world_features:
        feature_range = feature.radius * 1.28
        distance = pos.distance_to(feature.pos)
        if distance > feature_range:
            continue
        influence = 1 - distance / feature_range
        if feature.kind == "grove":
            density += 0.65 * influence
        elif feature.kind == "meadow":
            density -= 0.7 * influence
        elif feature.kind == "swamp":
            density -= 0.48 * influence
        elif feature.kind == "ruin":
            density -= 0.25 * influence

    if game.is_near_path(pos, 32):
        density -= 0.16
    return clamp(density, 0.08, 0.98)


def generate_resource_position(
    game: "Game",
    preferred_kinds: tuple[str, ...],
    min_distance: float,
    max_distance: float,
    existing_nodes: list[ResourceNode],
    radius: float,
) -> Vector2:
    for _ in range(90):
        pos: Vector2 | None = None
        matches = [feature for feature in game.world_features if feature.kind in preferred_kinds]
        if matches and game.random.random() < 0.82:
            feature = game.random.choice(matches)
            angle = game.random.uniform(0, math.tau)
            spread = game.random.uniform(feature.radius * 0.22, feature.radius * 0.92)
            pos = feature.pos + angle_to_vector(angle) * spread
            pos = Vector2(clamp(pos.x, 80, WORLD_WIDTH - 80), clamp(pos.y, 80, WORLD_HEIGHT - 80))
        else:
            pos = game.random_resource_pos(min_distance, max_distance)

        if pos.distance_to(CAMP_CENTER) < min_distance or pos.distance_to(CAMP_CENTER) > max_distance:
            continue
        if any(pos.distance_to(node.pos) < node.radius + radius + 18 for node in existing_nodes):
            continue
        return pos
    return game.random_resource_pos(min_distance, max_distance)


def generate_trees(game: "Game") -> list[dict[str, object]]:
    trees: list[dict[str, object]] = []
    attempts = 0
    while len(trees) < 190 and attempts < 6000:
        attempts += 1
        pos = Vector2(
            game.random.uniform(40, WORLD_WIDTH - 40),
            game.random.uniform(40, WORLD_HEIGHT - 40),
        )
        if pos.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + game.random.uniform(110, 250):
            continue
        if game.random.random() > game.local_tree_density(pos):
            continue

        tone = game.random.uniform(0.15, 0.85)
        radius = game.random.randint(24, 42)
        for feature in game.world_features:
            distance = pos.distance_to(feature.pos)
            if distance > feature.radius:
                continue
            influence = 1 - distance / max(1, feature.radius)
            if feature.kind == "grove":
                radius += int(8 * influence)
                tone = clamp(tone + 0.08, 0.0, 1.0)
            elif feature.kind == "swamp":
                tone = clamp(tone - 0.18, 0.0, 1.0)
            elif feature.kind == "meadow":
                radius -= int(5 * influence)
            elif feature.kind == "ruin":
                radius -= int(3 * influence)
        trees.append(
            {
                "pos": pos,
                "radius": int(clamp(radius, 18, 50)),
                "height": game.random.uniform(0.8, 1.25),
                "tone": tone,
                "lean": game.random.uniform(-0.22, 0.22),
                "spread": game.random.uniform(0.82, 1.28),
                "branch_bias": game.random.uniform(-0.35, 0.35),
                "wood_yield": max(2, int(radius * 0.1) + game.random.randint(0, 1)),
                "effort_required": 2 + int(radius >= 29) + int(radius >= 40),
                "effort_progress": 0,
                "harvested": False,
            }
        )
    return trees


def generate_resource_nodes(game: "Game") -> list[ResourceNode]:
    nodes: list[ResourceNode] = []
    base_distance = game.camp_clearance_radius()
    for _ in range(6):
        nodes.append(
            ResourceNode(
                "food",
                game.generate_resource_position(
                    ("meadow", "swamp"),
                    base_distance + 240,
                    base_distance + 620,
                    nodes,
                    22,
                ),
                amount=1,
                radius=22,
                variant="berries",
                renewable=False,
            )
        )
    for _ in range(5):
        nodes.append(
            ResourceNode(
                "scrap",
                game.generate_resource_position(
                    ("ruin",),
                    base_distance + 300,
                    base_distance + 760,
                    nodes,
                    24,
                ),
                amount=1,
                radius=24,
                variant="crate",
                renewable=False,
            )
        )
    return nodes


def random_resource_pos(game: "Game", min_distance: float, max_distance: float) -> Vector2:
    angle = game.random.uniform(0, math.tau)
    distance = game.random.uniform(min_distance, max_distance)
    pos = CAMP_CENTER + angle_to_vector(angle) * distance
    return Vector2(clamp(pos.x, 80, WORLD_WIDTH - 80), clamp(pos.y, 80, WORLD_HEIGHT - 80))
