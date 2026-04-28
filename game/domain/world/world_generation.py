from __future__ import annotations

import math

from pygame import Vector2

from ...core.config import CAMP_CENTER, CHUNK_SIZE, WORLD_HEIGHT, WORLD_WIDTH, clamp
from ...core.models import ResourceNode, WorldFeature


def random_world_pos(world, margin: float = 140) -> Vector2:
    return Vector2(
        world.random.uniform(margin, WORLD_WIDTH - margin),
        world.random.uniform(margin, WORLD_HEIGHT - margin),
    )


def hash_noise(world, x: int, y: int, seed_offset: int = 0) -> float:
    value = math.sin((x * 127.1 + y * 311.7 + world.seed_value * 17 + seed_offset * 37) * 0.137)
    return (value + 1.0) * 0.5


def chunk_key_for_pos(world, pos: Vector2) -> tuple[int, int]:
    return (math.floor(pos.x / CHUNK_SIZE), math.floor(pos.y / CHUNK_SIZE))


def chunk_origin(world, chunk_x: int, chunk_y: int) -> Vector2:
    return Vector2(chunk_x * CHUNK_SIZE, chunk_y * CHUNK_SIZE)


def ensure_endless_world(world, center: Vector2, radius: int = 3) -> None:
    base_x, base_y = world.chunk_key_for_pos(center)
    for chunk_x in range(base_x - radius, base_x + radius + 1):
        for chunk_y in range(base_y - radius, base_y + radius + 1):
            key = (chunk_x, chunk_y)
            if key not in world.generated_chunks:
                world.generate_chunk(chunk_x, chunk_y)


def generate_chunk(world, chunk_x: int, chunk_y: int) -> None:
    biome = world.chunk_biome_kind(chunk_x, chunk_y)
    region_key = world.region_key_for_chunk(chunk_x, chunk_y)
    region = world.ensure_named_region(*region_key)
    world.generated_chunks[(chunk_x, chunk_y)] = {
        "biome": biome,
        "region_key": region_key,
        "region_name": region["name"],
    }
    if biome == "forest" and world.chunk_origin(chunk_x, chunk_y).distance_to(CAMP_CENTER) < world.camp_clearance_radius() + 380:
        return

    origin = world.chunk_origin(chunk_x, chunk_y)
    center = origin + Vector2(CHUNK_SIZE * 0.5, CHUNK_SIZE * 0.5)
    feature_radius = 120 + world.hash_noise(chunk_x, chunk_y, 19) * 80
    world.endless_features.append(WorldFeature(biome, center, feature_radius, world.hash_noise(chunk_x, chunk_y, 23)))

    tree_plan = {
        "forest": (7, 13),
        "redwood": (9, 16),
        "swamp": (4, 8),
        "meadow": (1, 3),
        "ashland": (0, 2),
        "quarry": (0, 1),
        "ruin": (1, 4),
    }
    tree_count = int(world.hash_noise(chunk_x, chunk_y, 29) * (tree_plan[biome][1] - tree_plan[biome][0]) + tree_plan[biome][0])
    for index in range(tree_count):
        px = origin.x + 36 + world.hash_noise(chunk_x * 17 + index, chunk_y * 13, 31) * (CHUNK_SIZE - 72)
        py = origin.y + 36 + world.hash_noise(chunk_x * 19, chunk_y * 11 + index, 37) * (CHUNK_SIZE - 72)
        pos = Vector2(px, py)
        if pos.distance_to(CAMP_CENTER) < world.camp_clearance_radius() + 110:
            continue
        radius = 22 + int(world.hash_noise(chunk_x * 7 + index, chunk_y * 5 + index, 41) * 26)
        if biome == "redwood":
            radius += 8
        elif biome == "ashland":
            radius = max(16, radius - 6)
        elif biome == "meadow":
            radius = max(18, radius - 8)
        tone = world.hash_noise(chunk_x * 3 + index, chunk_y * 7 + index, 43)
        world.trees.append(
            {
                "pos": pos,
                "radius": int(clamp(radius, 18, 56)),
                "height": 0.84 + world.hash_noise(chunk_x * 5 + index, chunk_y * 9 + index, 47) * 0.6,
                "tone": tone,
                "lean": world.hash_noise(chunk_x * 13 + index, chunk_y * 3 + index, 53) * 0.44 - 0.22,
                "spread": 0.82 + world.hash_noise(chunk_x * 2 + index, chunk_y * 17 + index, 59) * 0.46,
                "branch_bias": world.hash_noise(chunk_x * 11 + index, chunk_y * 4 + index, 61) * 0.7 - 0.35,
                "wood_yield": max(2, int(radius * (0.14 if biome == "redwood" else 0.11))),
                "effort_required": 2 + int(radius >= 30) + int(radius >= 42),
                "effort_progress": 0,
                "harvested": False,
                "biome": biome,
            }
        )

    resource_plan = {
        "forest": (("food", "berries"), ("food", "mushrooms"), ("scrap", "cache")),
        "redwood": (("food", "mushrooms"), ("scrap", "crate"), ("scrap", "relic")),
        "swamp": (("food", "herbs"), ("food", "reeds"), ("scrap", "bogmetal")),
        "meadow": (("food", "berries"), ("food", "flowers"), ("scrap", "cart")),
        "ashland": (("scrap", "charcoal"), ("scrap", "relic"), ("food", "roots")),
        "quarry": (("scrap", "ore"), ("scrap", "stonecache"), ("food", "roots")),
        "ruin": (("scrap", "crate"), ("scrap", "relic"), ("food", "herbs")),
    }
    node_count = 1 + int(world.hash_noise(chunk_x, chunk_y, 67) * 2)
    if world.hash_noise(chunk_x, chunk_y, 69) < 0.24:
        node_count = 0
    for index in range(node_count):
        variant_kind, variant_name = resource_plan[biome][index % len(resource_plan[biome])]
        pos = Vector2(
            origin.x + 44 + world.hash_noise(chunk_x * 23 + index, chunk_y * 5, 71) * (CHUNK_SIZE - 88),
            origin.y + 44 + world.hash_noise(chunk_x * 7, chunk_y * 29 + index, 73) * (CHUNK_SIZE - 88),
        )
        if pos.distance_to(CAMP_CENTER) < world.camp_clearance_radius() + 140:
            continue
        radius = 20 if variant_kind == "food" else 24
        world.resource_nodes.append(
            ResourceNode(
                variant_kind,
                pos,
                amount=1,
                radius=radius,
                variant=variant_name,
                renewable=False,
            )
        )
