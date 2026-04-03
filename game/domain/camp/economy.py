from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...core.config import PALETTE, clamp, lerp

if TYPE_CHECKING:
    from ...core.models import Building
    from ...app.session import Game


def build_recipe_for(game: "Game", kind: str) -> dict[str, object]:
    for recipe in game.build_recipes:
        if recipe["kind"] == kind:
            return recipe
    raise KeyError(kind)


def economy_phase_score(game: "Game") -> int:
    infrastructure = sum(
        game.building_count(kind)
        for kind in ("serraria", "cozinha", "enfermaria", "horta", "anexo", "torre")
    )
    return max(0, game.day - 1) + game.camp_level * 2 + min(6, infrastructure)


def economy_phase_key(game: "Game") -> str:
    score = game.economy_phase_score()
    if score >= 9:
        return "late"
    if score >= 4:
        return "mid"
    return "early"


def economy_phase_label(game: "Game") -> str:
    return {
        "early": "escassez",
        "mid": "estabilizacao",
        "late": "expedicoes",
    }[game.economy_phase_key()]


def build_cost_for(game: "Game", recipe_or_kind: dict[str, object] | str) -> tuple[int, int]:
    recipe = game.build_recipe_for(recipe_or_kind) if isinstance(recipe_or_kind, str) else recipe_or_kind
    phase = game.economy_phase_key()
    multiplier = {
        "early": 1.0,
        "mid": 1.06,
        "late": 1.14,
    }[phase]
    wood_cost = max(1, math.ceil(int(recipe["wood"]) * multiplier))
    scrap_cost = max(0, math.ceil(int(recipe["scrap"]) * multiplier))
    return wood_cost, scrap_cost


def sawmill_output(game: "Game", role: str) -> int:
    base = 5 if role == "lenhador" else 4
    phase_bonus = {
        "early": -1,
        "mid": 0,
        "late": 1,
    }[game.economy_phase_key()]
    return max(3, base + phase_bonus)


def cookhouse_output(game: "Game", role: str) -> int:
    base = 4 if role == "cozinheiro" else 3
    phase_bonus = {
        "early": 0,
        "mid": 0,
        "late": 1,
    }[game.economy_phase_key()]
    return max(2, base + phase_bonus)


def garden_harvest_bundle(game: "Game", role: str) -> dict[str, int]:
    phase = game.economy_phase_key()
    if phase == "early":
        bundle = {"food": 1}
    elif phase == "mid":
        bundle = {"food": 1}
        if game.random.random() < 0.35:
            bundle["herbs"] = 1
    else:
        bundle = {"food": 2}
        if game.random.random() < (0.6 if role == "cozinheiro" else 0.4):
            bundle["herbs"] = 1
    if role == "cozinheiro" and phase != "early" and game.random.random() < 0.25:
        bundle["food"] = bundle.get("food", 0) + 1
    return bundle


def garden_regrow_duration(game: "Game") -> float:
    return {
        "early": 38.0,
        "mid": 31.0,
        "late": 25.0,
    }[game.economy_phase_key()]


def garden_is_ready(_game: "Game", building: "Building" | None) -> bool:
    return bool(building and building.kind == "horta" and building.work_phase <= 0.0)


def start_garden_regrow(game: "Game", building: "Building") -> None:
    if building.kind == "horta":
        building.work_phase = game.garden_regrow_duration()


def update_buildings(game: "Game", dt: float) -> None:
    for building in game.buildings:
        if building.kind != "horta" or building.work_phase <= 0.0:
            continue
        if game.is_night:
            continue
        building.work_phase = max(0.0, building.work_phase - dt)


def clinic_medicine_output(game: "Game") -> int:
    return 2 if game.economy_phase_key() == "late" else 1


def daily_ration_demand(game: "Game") -> int:
    population = 1 + len(game.living_survivors())
    phase = game.economy_phase_key()
    factor = {
        "early": 0.42,
        "mid": 0.72,
        "late": 0.96,
    }[phase]
    floor = {
        "early": 2,
        "mid": 3,
        "late": 4,
    }[phase]
    return max(floor, math.ceil(population * factor))


def apply_daily_rations(game: "Game") -> tuple[int, int, int]:
    demand = game.daily_ration_demand()
    used_meals = 0
    used_food = 0
    while demand >= 2 and game.meals > 0:
        game.meals -= 1
        used_meals += 1
        demand -= 2
    while demand > 0 and game.food > 0:
        game.food -= 1
        used_food += 1
        demand -= 1

    deficit = max(0, demand)
    if deficit > 0:
        for survivor in game.living_survivors():
            survivor.morale = clamp(survivor.morale - deficit * 3.8, 0, 100)
            survivor.energy = clamp(survivor.energy - deficit * 2.5, 0, 100)
            game.adjust_trust(survivor, -deficit * 1.0)
    return used_meals, used_food, deficit


def stockpile_capacity(game: "Game", resource: str) -> int:
    if game.unlimited_resources_enabled():
        return 9999
    base = {
        "logs": 26,
        "wood": 34,
        "food": 24,
        "herbs": 12,
        "scrap": 24,
        "meals": 18,
        "medicine": 10,
    }[resource]
    camp_bonus = game.camp_level * 6
    annex_bonus = game.building_count("anexo") * 8
    specialty_bonus = {
        "logs": game.building_count("serraria") * 8,
        "wood": game.building_count("serraria") * 6,
        "food": game.building_count("cozinha") * 5 + game.building_count("horta") * 4,
        "herbs": game.building_count("enfermaria") * 4,
        "scrap": game.building_count("anexo") * 4,
        "meals": game.building_count("cozinha") * 6,
        "medicine": game.building_count("enfermaria") * 5,
    }[resource]
    bed_bonus = game.building_count("barraca") * 2
    return base + camp_bonus + annex_bonus + specialty_bonus + bed_bonus


def normalize_stockpile(game: "Game") -> None:
    for resource in ("logs", "wood", "food", "herbs", "scrap", "meals", "medicine"):
        current = int(getattr(game, resource))
        setattr(game, resource, int(clamp(current, 0, game.stockpile_capacity(resource))))


def add_resource_bundle(game: "Game", bundle: dict[str, int]) -> dict[str, int]:
    stored: dict[str, int] = {}
    for resource, amount in bundle.items():
        if amount <= 0:
            continue
        current = int(getattr(game, resource))
        capacity = game.stockpile_capacity(resource)
        accepted = max(0, min(amount, capacity - current))
        if accepted:
            setattr(game, resource, current + accepted)
            stored[resource] = accepted
    return stored


def consume_resource(game: "Game", resource: str, amount: int) -> bool:
    if getattr(game, resource) < amount:
        return False
    setattr(game, resource, getattr(game, resource) - amount)
    return True


def has_resource_bundle(game: "Game", bundle: dict[str, int]) -> bool:
    for resource, amount in bundle.items():
        if getattr(game, resource) < amount:
            return False
    return True


def consume_resource_bundle(game: "Game", bundle: dict[str, int]) -> bool:
    if not game.has_resource_bundle(bundle):
        return False
    for resource, amount in bundle.items():
        setattr(game, resource, getattr(game, resource) - amount)
    return True


def available_fuel(game: "Game") -> int:
    return game.logs + game.wood


def consume_fuel(game: "Game", amount: int = 1) -> bool:
    spent = 0
    while spent < amount and game.logs > 0:
        game.logs -= 1
        spent += 1
    while spent < amount and game.wood > 0:
        game.wood -= 1
        spent += 1
    return spent == amount


def add_fuel_to_bonfire(game: "Game") -> tuple[bool, str, tuple[int, int, int]]:
    if game.logs > 0:
        game.logs -= 1
        game.bonfire_heat = clamp(game.bonfire_heat + 18, 0, 100)
        game.bonfire_ember_bed = clamp(game.bonfire_ember_bed + 16, 0, 100)
        return True, "tora na fogueira", PALETTE["light"]
    if game.wood > 0:
        game.wood -= 1
        game.bonfire_heat = clamp(game.bonfire_heat + 10, 0, 100)
        game.bonfire_ember_bed = clamp(game.bonfire_ember_bed + 7, 0, 100)
        return True, "tabua no fogo", PALETTE["light"]
    return False, "sem combustivel", PALETTE["danger_soft"]


def bonfire_stage(game: "Game") -> str:
    level = game.bonfire_heat * 0.7 + game.bonfire_ember_bed * 0.3
    if level >= 76:
        return "alta"
    if level >= 44:
        return "estavel"
    if level >= 18:
        return "fraca"
    return "brasas"


def update_bonfire(game: "Game", dt: float) -> None:
    weather_drag = game.weather_precipitation_factor() * 0.38
    weather_drag += game.weather_wind_factor() * 0.14
    weather_drag += game.weather_mist_factor() * 0.05
    weather_drag += game.weather_storm_factor() * 0.16

    dark_factor = game.visual_darkness_factor()
    ember_decay = lerp(0.11, 0.18, dark_factor) + weather_drag * 0.55
    game.bonfire_ember_bed = clamp(game.bonfire_ember_bed - ember_decay * dt, 0, 100)

    target_heat = clamp(game.bonfire_ember_bed + lerp(10, 18, dark_factor), 0, 100)
    cooling = lerp(0.66, 1.08, dark_factor) + weather_drag
    if game.bonfire_heat > target_heat:
        overshoot = 1.0 + max(0.0, game.bonfire_heat - target_heat) / 38
        game.bonfire_heat = clamp(game.bonfire_heat - cooling * overshoot * dt, 0, 100)
    else:
        game.bonfire_heat = clamp(
            game.bonfire_heat + min(0.9, (target_heat - game.bonfire_heat) * 0.08) * dt,
            0,
            100,
        )









