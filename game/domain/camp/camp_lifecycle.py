from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import Vector2

from ...entities import Zombie
from ...core.config import CAMP_CENTER, PALETTE, angle_to_vector, clamp

if TYPE_CHECKING:
    from ...app.session import Game
    from ...entities import Survivor


def average_morale(game: "Game") -> float:
    alive = [survivor.morale for survivor in game.survivors if survivor.is_alive()]
    return sum(alive) / len(alive) if alive else 0.0


def average_insanity(game: "Game") -> float:
    alive = [getattr(survivor, "insanity", 0.0) for survivor in game.survivors if survivor.is_alive()]
    return sum(alive) / len(alive) if alive else 0.0


def average_health(game: "Game") -> float:
    alive = [survivor.health for survivor in game.survivors if survivor.is_alive()]
    return sum(alive) / len(alive) if alive else 0.0


def audio_tension(game: "Game") -> float:
    zombie_factor = clamp(len(game.zombies) / 10, 0.0, 1.0)
    spawn_factor = clamp(game.spawn_budget / 14, 0.0, 1.0) if game.is_night else 0.0
    fire_factor = 1.0 - clamp(game.bonfire_heat / 100, 0.0, 1.0)
    barricade_factor = 1.0 - clamp(game.weakest_barricade_health() / 100, 0.0, 1.0)
    health_factor = 1.0 - clamp(game.player.health / game.player.max_health, 0.0, 1.0)
    morale_factor = 1.0 - clamp(game.average_morale() / 100, 0.0, 1.0)
    insanity_factor = clamp(game.average_insanity() / 100, 0.0, 1.0)
    weather_factor = game.weather_precipitation_factor() * 0.08
    weather_factor += game.weather_mist_factor() * 0.05
    weather_factor += game.weather_wind_factor() * 0.04
    weather_factor += game.weather_storm_factor() * 0.08
    base = 0.18 if game.is_night else 0.04
    tension = (
        base
        + zombie_factor * 0.42
        + spawn_factor * 0.16
        + fire_factor * 0.12
        + barricade_factor * 0.14
        + health_factor * 0.1
        + morale_factor * 0.06
        + insanity_factor * 0.08
        + weather_factor
        + (0.12 if getattr(game, "horde_active", False) else 0.0)
    )
    return clamp(tension, 0.0, 1.0)


def tension_label(game: "Game") -> str:
    tension = game.audio_tension()
    if getattr(game, "horde_active", False):
        return "Noite de horda"
    if tension >= 0.8:
        return "Horda em cima"
    if tension >= 0.56:
        return "Sob pressao"
    if tension >= 0.32:
        return "Inquieta"
    return "Estavel"


def living_survivors(game: "Game") -> list["Survivor"]:
    return [survivor for survivor in game.survivors if survivor.is_alive() and not game.is_survivor_on_expedition(survivor)]


def begin_night(game: "Game") -> None:
    if game.day <= 3:
        horde_chance = 0.0
    else:
        horde_chance = min(0.04 + (game.day - 3) * 0.022, 0.32)
    game.horde_active = game.random.random() < horde_chance
    if game.day <= 2:
        game.spawn_budget = 1 + game.day + (1 if game.horde_active else 0)
        game.spawn_timer = 2.8
    else:
        game.spawn_budget = 2 + game.day + (2 if game.horde_active else 0)
        game.spawn_timer = 2.35
    game.bonfire_ember_bed = clamp(game.bonfire_ember_bed + 8, 0, 100)
    game.emit_embers(game.bonfire_pos, 20)
    game.spawn_floating_text("a floresta acordou", game.bonfire_pos, PALETTE["danger_soft"])
    if game.horde_active:
        boss_angle = game.random.uniform(0, math.tau)
        boss_distance = game.camp_clearance_radius() + game.random.uniform(250, 340)
        boss_pos = CAMP_CENTER + angle_to_vector(boss_angle) * boss_distance
        boss = Zombie(boss_pos, game.day, boss_profile=game.create_horde_boss_profile())
        boss.anchor = Vector2(CAMP_CENTER)
        boss.camp_pressure = 1.0
        game.zombies.append(boss)
        game.set_event_message("Anoiteceu com horda. Um chefe podre esta puxando a mata inteira para cima do acampamento.")
    else:
        game.set_event_message("Anoiteceu. A mata aperta o cerco ao redor do campo.")
    game.audio.play_transition("nightfall")


def begin_day(game: "Game") -> None:
    game.day += 1
    game.horde_active = False
    used_meals, used_food, ration_deficit = game.apply_daily_rations()
    game.add_resource_bundle(
        {
            "food": game.building_count("horta"),
            "meals": 1 if game.building_count("cozinha") > 0 else 0,
            "herbs": 1 if game.building_count("enfermaria") > 0 else 0,
        }
    )
    game.bonfire_heat = clamp(game.bonfire_heat + 12, 0, 100)
    game.bonfire_ember_bed = clamp(game.bonfire_ember_bed + 10, 0, 100)
    for survivor in game.survivors:
        if survivor.is_alive():
            survivor.energy = clamp(survivor.energy + 25, 0, 100)
            survivor.morale = clamp(survivor.morale + 8, 0, 100)
            survivor.sleep_debt = clamp(getattr(survivor, "sleep_debt", 0.0) - 18, 0, 100)
    game.try_recruit_survivor()
    game.normalize_stockpile()
    game.spawn_floating_text(f"amanheceu - dia {game.day}", game.bonfire_pos, PALETTE["accent_soft"])
    phase_label = game.economy_phase_label()
    if ration_deficit > 0:
        game.set_event_message(
            f"O amanhecer cobrou caro. Faltaram racoes na fase de {phase_label} e a base sentiu o tranco.",
            duration=6.4,
        )
    elif used_meals > 0 or used_food > 0:
        game.set_event_message(
            f"O amanhecer consumiu {used_meals} refeicoes e {used_food} insumos. A base entrou em {phase_label}.",
            duration=6.2,
        )
    else:
        game.set_event_message(f"O amanhecer trouxe folego para a sociedade da clareira. Fase: {phase_label}.")
    game.audio.play_transition("daybreak")









