from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Vector2

if TYPE_CHECKING:
    from ...entities import Survivor
    from ...app.session import Game


def survivor_focus_override(game: "Game", survivor: "Survivor") -> tuple[str, object | Vector2 | None] | None:
    assigned_building = game.building_by_id(getattr(survivor, "assigned_building_id", None))
    if game.focus_mode == "fortify":
        defense_target = game.closest_defense_target(survivor)
        if assigned_building and getattr(survivor, "assigned_building_kind", None) == "torre" and survivor.energy > 18:
            return ("watchtower", assigned_building)
        if defense_target and survivor.energy > 22:
            return ("guard", survivor.guard_pos)
        if game.has_damaged_barricade() and game.wood > 0 and survivor.energy > 24:
            barricade = game.weakest_barricade()
            if barricade:
                return ("repair", barricade)
    elif game.focus_mode == "morale":
        if game.available_fuel() > 0 and (game.bonfire_heat < 60 or game.bonfire_ember_bed < 28):
            return ("tend_fire", game.bonfire_pos)
        if game.food >= 2 and game.available_fuel() > 0 and survivor.energy > 24:
            kitchen = assigned_building if assigned_building and getattr(survivor, "assigned_building_kind", None) == "cozinha" else None
            if kitchen:
                return ("cookhouse", kitchen)
            return ("cook", game.kitchen_pos)
        if game.average_morale() < 64 and survivor.energy > 24:
            return ("socialize", game.bonfire_pos)
    elif game.focus_mode == "supply":
        if assigned_building and getattr(survivor, "assigned_building_kind", None) == "serraria" and game.logs >= 2 and survivor.energy > 24:
            return ("sawmill", assigned_building)
        if (
            assigned_building
            and getattr(survivor, "assigned_building_kind", None) == "horta"
            and not game.is_night
            and survivor.energy > 24
            and game.garden_is_ready(assigned_building)
        ):
            return ("garden", assigned_building)
        if not game.buildings_of_kind("serraria") and survivor.role in {"artesa", "lenhador"} and game.logs > 0 and survivor.energy > 24:
            return ("roughcut", game.workshop_pos)
    return None









