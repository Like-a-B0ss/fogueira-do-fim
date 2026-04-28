from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import Vector2

from ...entities import Survivor, Zombie
from ...core.config import CAMP_CENTER, angle_to_vector, clamp

if TYPE_CHECKING:
    from ...app.session import Game


def active_zombie_cap(game: "Game", *, pressure: bool = False) -> int:
    base = 6 + min(8, game.day * 2)
    if getattr(game, "horde_active", False):
        base += 5
    if pressure:
        base += 2
    return min(24, base)


def living_zombie_count(game: "Game") -> int:
    return sum(1 for zombie in game.zombies if zombie.is_alive())


def can_spawn_zombie(game: "Game", *, pressure: bool = False) -> bool:
    return living_zombie_count(game) < active_zombie_cap(game, pressure=pressure)


def spawn_local_zombies(
    game: "Game",
    center: Vector2,
    count: int,
    *,
    pressure: bool = False,
    spawn_source: str = "",
    summon_chain_budget: int | None = None,
) -> None:
    for _ in range(count):
        if not can_spawn_zombie(game, pressure=pressure):
            return
        pos = game.safe_zombie_spawn_position(center, 130, 220)
        zombie = Zombie(pos, game.day)
        zombie.anchor = Vector2(center)
        defense = game.tower_defense_bonus() if center.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 420 else 0.0
        zombie.camp_pressure = clamp((0.78 if pressure else 0.52) + center.distance_to(CAMP_CENTER) / 950 - defense * 0.38, 0.25, 1.0)
        zombie.spawn_source = spawn_source
        zombie.summon_chain_budget = summon_chain_budget
        game.zombies.append(zombie)


def spawn_forest_ambient_zombie(game: "Game", *, anchor: Vector2 | None = None, radius: float | None = None) -> None:
    if not can_spawn_zombie(game):
        return
    center = Vector2(anchor) if anchor is not None else Vector2(game.player.pos)
    if radius is None:
        min_distance = 260.0
        max_distance = 520.0
    else:
        min_distance = max(42.0, radius * 0.45)
        max_distance = max(68.0, radius)
    pos = game.safe_zombie_spawn_position(center, min_distance, max_distance)
    zombie = Zombie(pos, game.day)
    zombie.anchor = Vector2(center)
    zombie.camp_pressure = clamp(pos.distance_to(CAMP_CENTER) / 900, 0.18, 0.72)
    game.zombies.append(zombie)


def safe_zombie_spawn_position(game: "Game", center: Vector2, min_distance: float, max_distance: float) -> Vector2:
    safe_radius = game.camp_clearance_radius() + 120
    for _ in range(48):
        angle = game.random.uniform(0, math.tau)
        distance = game.random.uniform(min_distance, max_distance)
        pos = Vector2(center) + angle_to_vector(angle) * distance
        if pos.distance_to(CAMP_CENTER) < safe_radius:
            continue
        if game.point_in_camp_square(pos, padding=96):
            continue
        if pos.distance_to(game.player.pos) < 120:
            continue
        return pos
    fallback = Vector2(center) - Vector2(CAMP_CENTER)
    if fallback.length_squared() <= 0.01:
        fallback = angle_to_vector(game.random.uniform(0, math.tau))
    else:
        fallback = fallback.normalize()
    return Vector2(CAMP_CENTER) + fallback * max(safe_radius + 36, min_distance)


def camp_invader_zombies(game: "Game") -> list[Zombie]:
    invaders: list[Zombie] = []
    safe_radius = game.camp_clearance_radius() + 84
    for zombie in game.zombies:
        if not zombie.is_alive():
            continue
        if game.point_in_camp_square(zombie.pos, padding=54) or zombie.pos.distance_to(CAMP_CENTER) < safe_radius:
            invaders.append(zombie)
    return invaders


def closest_defense_target(game: "Game", survivor: Survivor) -> Zombie | None:
    invaders = game.camp_invader_zombies()
    if invaders:
        return min(
            invaders,
            key=lambda zombie: (
                zombie.pos.distance_to(CAMP_CENTER),
                zombie.pos.distance_to(game.player.pos),
                zombie.pos.distance_to(survivor.pos),
            ),
        )
    nearby = [zombie for zombie in game.zombies if zombie.is_alive() and zombie.pos.distance_to(survivor.pos) < 128]
    if nearby:
        return min(nearby, key=lambda zombie: zombie.pos.distance_to(survivor.pos))
    if game.is_night:
        perimeter = [
            zombie
            for zombie in game.zombies
            if zombie.is_alive() and zombie.pos.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 180
        ]
        if perimeter:
            return min(perimeter, key=lambda zombie: zombie.pos.distance_to(survivor.pos))
    return None


def survivor_should_seek_shelter(_game: "Game", survivor: Survivor, zombie: Zombie) -> bool:
    if survivor.health < 38 or survivor.energy < 18:
        return True
    if survivor.state in {"sleep", "rest", "treatment"} and zombie.pos.distance_to(survivor.pos) < 140:
        return True
    if survivor.role in {"cozinheiro", "mensageiro"} and zombie.pos.distance_to(survivor.pos) < 170:
        return True
    if survivor.exhaustion > 84 or survivor.insanity > 88:
        return True
    return False


def survivor_should_engage(game: "Game", survivor: Survivor, zombie: Zombie) -> bool:
    base_invaded = game.point_in_camp_square(zombie.pos, padding=54) or zombie.pos.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 92
    if survivor.role == "vigia":
        return survivor.energy > 18 and survivor.health > 28
    if survivor.has_trait("corajoso"):
        return survivor.energy > 24 and survivor.health > 34
    if survivor.has_trait("leal") and base_invaded:
        return survivor.energy > 24 and survivor.health > 34
    if survivor.role in {"lenhador", "artesa", "batedora"} and base_invaded:
        return survivor.energy > 30 and survivor.health > 48
    return zombie.pos.distance_to(survivor.pos) < 64 and survivor.health > 52 and survivor.energy > 32


def survivor_attack_damage(_game: "Game", survivor: Survivor) -> float:
    damage = 14.0
    if survivor.role == "vigia":
        damage += 6.0
    elif survivor.role in {"lenhador", "artesa"}:
        damage += 3.0
    elif survivor.role == "batedora":
        damage += 2.0
    if survivor.has_trait("corajoso"):
        damage += 3.0
    if survivor.has_trait("teimoso"):
        damage += 1.0
    if survivor.has_trait("gentil"):
        damage -= 1.0
    return damage


def find_closest_zombie(game: "Game", pos: Vector2, radius: float) -> Zombie | None:
    living = [zombie for zombie in game.zombies if zombie.is_alive()]
    if not living:
        return None
    zombie = min(living, key=lambda item: item.pos.distance_to(pos))
    if zombie.pos.distance_to(pos) <= radius:
        return zombie
    return None


def create_horde_boss_profile(game: "Game") -> dict[str, object]:
    return {
        "name": "Chefe da Horda",
        "variant": "boss",
        "weapon": "lamina presa",
        "radius": 34,
        "speed": 86 + game.day * 2.0,
        "health": 390 + game.day * 34,
        "damage": 24 + game.day * 1.25,
        "body": (130, 106, 84),
        "accent": (78, 46, 36),
        "zone_key": ("horda", game.day),
        "zone_label": "Noite da Horda",
        "anchor": Vector2(CAMP_CENTER),
        "alert_radius": 420,
    }


def spawn_night_zombie(game: "Game") -> None:
    if not can_spawn_zombie(game, pressure=True):
        game.spawn_budget = max(0, game.spawn_budget - 1)
        return
    spawn_center = CAMP_CENTER
    if game.player.pos.distance_to(CAMP_CENTER) > game.camp_clearance_radius() + 320:
        spawn_center = Vector2(game.player.pos)
    if spawn_center == CAMP_CENTER:
        pos = game.safe_zombie_spawn_position(
            spawn_center,
            game.camp_clearance_radius() + 480,
            game.camp_clearance_radius() + 690,
        )
    else:
        pos = game.safe_zombie_spawn_position(spawn_center, 240, 420)
    zombie = Zombie(pos, game.day)
    zombie.anchor = Vector2(spawn_center)
    tower_pressure = game.tower_defense_bonus() * 0.42
    zombie.camp_pressure = clamp((0.92 if spawn_center == CAMP_CENTER or game.horde_active else 0.6) - tower_pressure, 0.35, 1.0)
    game.zombies.append(zombie)
    game.spawn_budget -= 1
