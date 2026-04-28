from __future__ import annotations

from pygame import Vector2

from ...core.config import PALETTE
from ...core.models import Ember, FloatingText


def has_damaged_barricade(world) -> bool:
    return any(b.health < b.max_health for b in world.barricades)


def weakest_barricade(world):
    if not world.barricades:
        return None
    return min(world.barricades, key=lambda barricade: barricade.health)


def weakest_barricade_health(world) -> float:
    weakest = world.weakest_barricade()
    return weakest.health if weakest else 100.0


def spawn_floating_text(world, text: str, pos: Vector2, color: tuple[int, int, int]) -> None:
    world.floating_texts.append(FloatingText(text, Vector2(pos), color))


def emit_embers(world, origin: Vector2, amount: int, *, smoky: bool = False) -> None:
    for _ in range(amount):
        velocity = Vector2(world.random.uniform(-22, 22), world.random.uniform(-58, -18))
        color = PALETTE["ember"] if not smoky else (113, 101, 89)
        world.embers.append(
            Ember(
                Vector2(origin),
                velocity,
                world.random.uniform(2, 4.5),
                world.random.uniform(0.55, 1.3),
                color,
            )
        )


def screen_to_world(world, position: Vector2) -> Vector2:
    return world.camera.screen_to_world(position)


def world_to_screen(world, position: Vector2) -> Vector2:
    return world.camera.world_to_screen(position)


def closest_barricade(world, pos: Vector2):
    if not world.barricades:
        return None
    return min(world.barricades, key=lambda barricade: barricade.pos.distance_to(pos))


def closest_target(world, pos: Vector2):
    candidates = [world.player]
    candidates.extend(world.living_survivors())
    candidates.extend(
        survivor
        for survivor in world.expedition_visible_members()
        if not getattr(survivor, "expedition_downed", False)
    )
    living = [actor for actor in candidates if actor.is_alive()]
    if not living:
        return None
    return min(living, key=lambda actor: actor.pos.distance_to(pos))
