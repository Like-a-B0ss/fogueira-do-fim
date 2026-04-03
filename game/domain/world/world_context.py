from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Vector2

from ...core.config import PALETTE, clamp

if TYPE_CHECKING:
    from ...core.models import InterestPoint, WorldFeature
    from ...app.session import Game


def feature_at_pos(game: "Game", pos: Vector2) -> "WorldFeature" | None:
    inside = [
        feature
        for feature in [*game.world_features, *game.endless_features]
        if pos.distance_to(feature.pos) <= feature.radius * 0.96
    ]
    if inside:
        return min(inside, key=lambda feature: pos.distance_to(feature.pos))
    return None


def surface_audio_at(game: "Game", pos: Vector2) -> str:
    if game.point_in_camp_square(pos, padding=-28):
        return "camp"
    if game.is_near_path(pos, 34):
        return "path"
    feature = game.feature_at_pos(pos)
    if not feature:
        return "forest"
    if feature.kind == "meadow":
        return "meadow"
    if feature.kind == "swamp":
        return "swamp"
    if feature.kind in {"ruin", "quarry", "ashland"}:
        return "ruin"
    return "forest"


def unresolved_interest_points(game: "Game") -> list["InterestPoint"]:
    return [point for point in game.interest_points if not point.resolved]


def resolve_interest_point(game: "Game", interest_point: "InterestPoint") -> None:
    if interest_point.resolved:
        return

    interest_point.resolved = True
    living = game.living_survivors()

    if interest_point.event_kind == "herb_cache":
        game.add_resource_bundle({"food": 1, "herbs": 2})
        for survivor in living:
            survivor.health = clamp(survivor.health + 7, 0, survivor.max_health)
        game.player.health = clamp(game.player.health + 10, 0, game.player.max_health)
        game.set_event_message("Ervas silvestres renderam mantimentos e curativos.")
    elif interest_point.event_kind == "hunter_blind":
        game.add_resource_bundle({"logs": 1, "wood": 1, "food": 1})
        game.player.stamina = clamp(game.player.stamina + 14, 0, game.player.max_stamina)
        game.set_event_message("Um posto de cacador trouxe madeira seca e carne aproveitavel.")
    elif interest_point.event_kind == "lost_cart":
        game.add_resource_bundle({"food": 2, "logs": 1})
        for survivor in living:
            survivor.morale = clamp(survivor.morale + 4, 0, 100)
        game.set_event_message("A carroca esquecida ainda guardava provisoes intactas.")
    elif interest_point.event_kind == "flower_shrine":
        game.add_resource_bundle({"meals": 1, "herbs": 1})
        for survivor in living:
            survivor.morale = clamp(survivor.morale + 7, 0, 100)
        game.set_event_message("A clareira florida acalmou o grupo e elevou a moral.")
    elif interest_point.event_kind == "sunken_cache":
        game.add_resource_bundle({"scrap": 2})
        game.player.stamina = clamp(game.player.stamina - 10, 0, game.player.max_stamina)
        game.set_event_message("A caixa semi-afundada cedeu sucata util, mas drenou seu folego.")
    elif interest_point.event_kind == "reed_nest":
        game.add_resource_bundle({"food": 1, "herbs": 1})
        game.set_event_message("O ninho nos juncos virou refeicao para o campo.")
    elif interest_point.event_kind == "tool_crate":
        game.add_resource_bundle({"scrap": 2, "wood": 1})
        weakest = game.weakest_barricade()
        if weakest:
            weakest.repair(18)
        game.set_event_message("Ferramentas velhas renderam sucata e reforcaram a defesa.")
    elif interest_point.event_kind == "alarm_nest":
        game.add_resource_bundle({"scrap": 1})
        game.spawn_local_zombies(interest_point.pos, 2)
        game.screen_shake = max(game.screen_shake, 3.2)
        game.set_event_message("A sirene morta chiou e puxou dois zumbis da mata.")
        game.audio.play_alert(source_pos=interest_point.pos)
    else:
        game.add_resource_bundle({"food": 1})
        game.set_event_message("Algo util foi encontrado na exploracao.")

    game.spawn_floating_text(interest_point.label, interest_point.pos, PALETTE["accent_soft"])
    game.emit_embers(interest_point.pos, 4, smoky=True)
    game.audio.play_interact(source_pos=interest_point.pos)


def update_player_biome(game: "Game") -> None:
    region = game.current_named_region()
    if game.point_in_camp_square(game.player.pos, padding=140):
        biome_key = "camp"
        region_key: tuple[int, int] | str = "camp"
        region_label = "Clareira do Campo"
    else:
        feature = game.feature_at_pos(game.player.pos)
        biome_key = feature.kind if feature else game.chunk_biome_kind(*game.chunk_key_for_pos(game.player.pos))
        region_key = tuple(region["key"]) if region else game.region_key_for_pos(game.player.pos)
        region_label = str(region["name"]) if region else game.feature_label(biome_key)
    label = game.feature_label(biome_key)
    game.current_zone_boss_label = game.zone_boss_status_text(region, short=True)
    if region_key != game.current_region_key:
        game.current_region_key = region_key
        game.current_region_label = region_label
        game.spawn_floating_text(region_label.lower(), game.player.pos + Vector2(0, -60), PALETTE["accent_soft"])
    if biome_key != game.current_biome_key:
        game.current_biome_key = biome_key
        game.current_biome_label = label
        game.spawn_floating_text(label.lower(), game.player.pos + Vector2(0, -38), PALETTE["muted"])









