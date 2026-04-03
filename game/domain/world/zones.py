from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import Vector2

from ...entities import Zombie
from ...core.config import CAMP_CENTER, CAMP_RADIUS, CHUNK_SIZE, PALETTE, clamp

if TYPE_CHECKING:
    from ...app.session import Game


def region_chunk_span(_game: "Game") -> int:
    return 3


def region_key_for_chunk(game: "Game", chunk_x: int, chunk_y: int) -> tuple[int, int]:
    span = game.region_chunk_span()
    return (math.floor(chunk_x / span), math.floor(chunk_y / span))


def region_key_for_pos(game: "Game", pos: Vector2) -> tuple[int, int]:
    return game.region_key_for_chunk(*game.chunk_key_for_pos(pos))


def region_origin(game: "Game", region_x: int, region_y: int) -> Vector2:
    span = CHUNK_SIZE * game.region_chunk_span()
    return Vector2(region_x * span, region_y * span)


def chunk_biome_kind(game: "Game", chunk_x: int, chunk_y: int) -> str:
    center = game.chunk_origin(chunk_x, chunk_y) + Vector2(CHUNK_SIZE * 0.5, CHUNK_SIZE * 0.5)
    if center.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 420:
        return "forest"
    heat = game.hash_noise(chunk_x, chunk_y, 3)
    moisture = game.hash_noise(chunk_x, chunk_y, 7)
    roughness = game.hash_noise(chunk_x, chunk_y, 11)
    if moisture > 0.72 and heat < 0.46:
        return "swamp"
    if moisture < 0.24 and roughness > 0.62:
        return "ashland"
    if roughness > 0.76 and moisture < 0.52:
        return "quarry"
    if moisture > 0.6 and heat > 0.52:
        return "redwood"
    if heat > 0.66 and moisture < 0.42:
        return "meadow"
    if roughness > 0.58:
        return "ruin"
    return "forest"


def biome_palette(_game: "Game", kind: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    palettes = {
        "forest": ((28, 48, 34), (55, 88, 58)),
        "meadow": ((78, 101, 62), (131, 154, 86)),
        "swamp": ((30, 57, 53), (70, 98, 84)),
        "ruin": ((82, 76, 66), (122, 112, 98)),
        "ashland": ((66, 58, 52), (110, 97, 88)),
        "redwood": ((48, 61, 42), (86, 112, 70)),
        "quarry": ((74, 82, 88), (122, 132, 138)),
    }
    return palettes.get(kind, palettes["forest"])


def biome_label(_game: "Game", kind: str) -> str:
    return {
        "forest": "Mata Profunda",
        "meadow": "Campos Altos",
        "swamp": "Brejo Antigo",
        "ruin": "Ruinas Perdidas",
        "ashland": "Cinzas Frias",
        "redwood": "Bosque Gigante",
        "quarry": "Pedreira Morta",
    }.get(kind, "Terras Distantes")


def generate_region_name(game: "Game", biome: str, region_x: int, region_y: int) -> str:
    fragments = {
        "forest": (
            ("Vale", "Mata", "Passagem", "Ermo"),
            ("do Lenho Seco", "das Corujas Mortas", "do Lobo Oco", "das Agulhas Baixas"),
        ),
        "meadow": (
            ("Campo", "Coroa", "Terraco", "Planicie"),
            ("das Flores Tortas", "do Vento Claro", "do Capim Antigo", "da Bruma Rasa"),
        ),
        "swamp": (
            ("Brejo", "Baixio", "Lama", "Poente"),
            ("das Febres", "dos Juncos Negros", "da Agua Surda", "do Lodo Fundo"),
        ),
        "ruin": (
            ("Ruina", "Patio", "Passo", "Marco"),
            ("das Colunas Quebradas", "do Ferro Oco", "dos Sinos Mortos", "da Muralha Cega"),
        ),
        "ashland": (
            ("Cinza", "Braseiro", "Ermo", "Costela"),
            ("do Fumo Frio", "das Brasas Mortas", "da Fuligem Longa", "do Po Negro"),
        ),
        "redwood": (
            ("Bosque", "Catedral", "Corredor", "Trono"),
            ("das Sequoias Velhas", "do Tronco Alto", "das Copas Fundas", "da Casca Rubra"),
        ),
        "quarry": (
            ("Pedreira", "Corte", "Macico", "Escarpa"),
            ("da Rocha Gasta", "dos Ecos Frios", "do Po de Ferro", "das Lajes Mortas"),
        ),
    }
    first_bank, second_bank = fragments.get(biome, fragments["forest"])
    first = first_bank[int(game.hash_noise(region_x, region_y, 91) * len(first_bank)) % len(first_bank)]
    second = second_bank[int(game.hash_noise(region_x, region_y, 97) * len(second_bank)) % len(second_bank)]
    return f"{first} {second}"


def region_has_zone_boss(game: "Game", anchor: Vector2, region_x: int, region_y: int) -> bool:
    if anchor.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + CHUNK_SIZE * 4.4:
        return False
    return game.hash_noise(region_x, region_y, 149) > 0.7


def zone_boss_blueprint(
    game: "Game",
    biome: str,
    region_name: str,
    region_key: tuple[int, int],
    anchor: Vector2,
) -> dict[str, object]:
    blueprints = {
        "forest": {
            "name": "Patriarca da Mata",
            "radius": 27,
            "speed": 82,
            "health": 280 + game.day * 24,
            "damage": 18 + game.day * 0.9,
            "body": (88, 121, 82),
            "accent": (45, 70, 41),
        },
        "meadow": {
            "name": "Arauto da Campina",
            "radius": 26,
            "speed": 92,
            "health": 260 + game.day * 22,
            "damage": 17 + game.day * 0.9,
            "body": (134, 128, 86),
            "accent": (84, 78, 44),
        },
        "swamp": {
            "name": "Matriarca do Brejo",
            "radius": 29,
            "speed": 78,
            "health": 300 + game.day * 26,
            "damage": 20 + game.day * 1.0,
            "body": (76, 117, 98),
            "accent": (36, 66, 58),
        },
        "ruin": {
            "name": "Sentinela da Ruina",
            "radius": 28,
            "speed": 80,
            "health": 310 + game.day * 25,
            "damage": 20 + game.day * 1.0,
            "body": (120, 112, 101),
            "accent": (69, 64, 58),
        },
        "ashland": {
            "name": "Rei das Cinzas",
            "radius": 30,
            "speed": 84,
            "health": 320 + game.day * 27,
            "damage": 21 + game.day * 1.1,
            "body": (132, 102, 78),
            "accent": (82, 52, 34),
        },
        "redwood": {
            "name": "Anciao das Sequoias",
            "radius": 31,
            "speed": 79,
            "health": 340 + game.day * 28,
            "damage": 22 + game.day * 1.1,
            "body": (96, 110, 72),
            "accent": (58, 48, 29),
        },
        "quarry": {
            "name": "Colosso da Pedreira",
            "radius": 33,
            "speed": 70,
            "health": 360 + game.day * 29,
            "damage": 24 + game.day * 1.2,
            "body": (124, 132, 138),
            "accent": (70, 78, 84),
        },
    }
    blueprint = dict(blueprints.get(biome, blueprints["forest"]))
    blueprint["zone_key"] = region_key
    blueprint["zone_label"] = region_name
    blueprint["anchor"] = Vector2(anchor)
    return blueprint


def region_expedition_blueprint(game: "Game", biome: str, region_x: int, region_y: int) -> dict[str, object]:
    blueprints = {
        "forest": (
            ("resina seca", {"logs": 2, "wood": 2, "medicine": 1}),
            ("caixa de trilha", {"food": 2, "scrap": 2}),
        ),
        "meadow": (
            ("fardo de sementes", {"food": 3, "herbs": 1}),
            ("kit de pastor", {"food": 2, "meals": 1, "wood": 1}),
        ),
        "swamp": (
            ("bolsa de lodo curativo", {"herbs": 3, "medicine": 1}),
            ("caixote encharcado", {"scrap": 2, "food": 1, "herbs": 1}),
        ),
        "ruin": (
            ("gaveta tecnica", {"scrap": 4, "medicine": 1}),
            ("armario tombado", {"scrap": 3, "wood": 1}),
        ),
        "ashland": (
            ("saco de carvao duro", {"logs": 2, "wood": 2, "scrap": 1}),
            ("estojo chamuscado", {"scrap": 2, "medicine": 1, "wood": 1}),
        ),
        "redwood": (
            ("troncos antigos", {"logs": 4, "wood": 2}),
            ("caixa de seiva rubra", {"logs": 3, "medicine": 1}),
        ),
        "quarry": (
            ("lote de ferragens", {"scrap": 5, "wood": 1}),
            ("bau de minerio", {"scrap": 4, "medicine": 1}),
        ),
    }
    pool = blueprints.get(biome, blueprints["forest"])
    index = int(game.hash_noise(region_x, region_y, 181) * len(pool)) % len(pool)
    label, bundle = pool[index]
    danger = {
        "forest": 0.28,
        "meadow": 0.24,
        "swamp": 0.52,
        "ruin": 0.46,
        "ashland": 0.5,
        "redwood": 0.42,
        "quarry": 0.48,
    }.get(biome, 0.36)
    danger += game.hash_noise(region_x, region_y, 187) * 0.14
    sites = 1 + int(game.hash_noise(region_x, region_y, 191) > 0.66)
    return {
        "label": label,
        "bundle": dict(bundle),
        "danger": clamp(danger, 0.18, 0.82),
        "sites": sites,
    }


def ensure_named_region(game: "Game", region_x: int, region_y: int) -> dict[str, object]:
    region_key = (region_x, region_y)
    if region_key in game.named_regions:
        return game.named_regions[region_key]

    span = CHUNK_SIZE * game.region_chunk_span()
    origin = game.region_origin(region_x, region_y)
    biome = game.chunk_biome_kind(region_x * game.region_chunk_span() + 1, region_y * game.region_chunk_span() + 1)
    anchor = origin + Vector2(span * 0.5, span * 0.5)
    anchor += Vector2(
        (game.hash_noise(region_x, region_y, 101) - 0.5) * span * 0.36,
        (game.hash_noise(region_x, region_y, 103) - 0.5) * span * 0.36,
    )
    name = game.generate_region_name(biome, region_x, region_y)
    boss_blueprint = (
        game.zone_boss_blueprint(biome, name, region_key, anchor)
        if game.region_has_zone_boss(anchor, region_x, region_y)
        else None
    )
    expedition = game.region_expedition_blueprint(biome, region_x, region_y)
    region = {
        "key": region_key,
        "name": name,
        "biome": biome,
        "anchor": anchor,
        "boss_blueprint": boss_blueprint,
        "boss_defeated": False,
        "boss_spawned": False,
        "boss_active": False,
        "expedition_label": expedition["label"],
        "expedition_bundle": expedition["bundle"],
        "expedition_danger": expedition["danger"],
        "expedition_sites": expedition["sites"],
        "expedition_last_outcome": "",
    }
    game.named_regions[region_key] = region
    return region


def named_region_at(game: "Game", pos: Vector2) -> dict[str, object] | None:
    if game.point_in_camp_square(pos, padding=140):
        return None
    return game.ensure_named_region(*game.region_key_for_pos(pos))


def zone_boss_for_region(game: "Game", region_key: tuple[int, int]) -> Zombie | None:
    for zombie in game.zombies:
        if zombie.is_alive() and getattr(zombie, "is_boss", False) and getattr(zombie, "zone_key", ()) == region_key:
            return zombie
    return None


def current_named_region(game: "Game") -> dict[str, object] | None:
    return game.named_region_at(game.player.pos)


def zone_boss_status_text(game: "Game", region: dict[str, object] | None, *, short: bool = False) -> str:
    if not region:
        return "centro seguro"
    blueprint = region.get("boss_blueprint")
    if not blueprint:
        return "sem boss" if short else "Nenhum boss domina esta zona."
    boss_name = str(blueprint["name"])
    if region.get("boss_defeated"):
        return "boss abatido" if short else f"{boss_name} foi abatido nesta zona."
    boss = game.zone_boss_for_region(tuple(region["key"]))
    if boss:
        return f"{boss_name} ativo" if short else f"{boss_name} esta ativo em {region['name']}."
    return f"{boss_name} a espreita" if short else f"{boss_name} ainda ronda {region['name']}."


def ensure_zone_boss_near_player(game: "Game") -> None:
    region = game.current_named_region()
    if not region or not region.get("boss_blueprint") or region.get("boss_defeated"):
        return
    if game.zone_boss_for_region(tuple(region["key"])):
        region["boss_active"] = True
        return
    living_bosses = [zombie for zombie in game.zombies if zombie.is_alive() and getattr(zombie, "is_boss", False)]
    if len(living_bosses) >= 2:
        return
    anchor = Vector2(region["anchor"])
    if game.player.pos.distance_to(anchor) > 430:
        return
    spawn_radius = 96 + game.hash_noise(int(anchor.x // 13), int(anchor.y // 13), 163) * 54
    spawn_pos = game.safe_zombie_spawn_position(anchor, spawn_radius, spawn_radius + 42)
    boss = Zombie(spawn_pos, game.day, boss_profile=dict(region["boss_blueprint"]))
    game.zombies.append(boss)
    region["boss_spawned"] = True
    region["boss_active"] = True
    game.spawn_floating_text(str(region["boss_blueprint"]["name"]).lower(), boss.pos, PALETTE["danger_soft"])
    game.set_event_message(f"{region['boss_blueprint']['name']} despertou em {region['name']}.")
    game.audio.play_alert(source_pos=boss.pos)


def resolve_defeated_zone_bosses(game: "Game") -> None:
    for zombie in game.zombies:
        if zombie.is_alive() or not getattr(zombie, "is_boss", False) or getattr(zombie, "death_processed", False):
            continue
        zombie.death_processed = True
        region_key = tuple(getattr(zombie, "zone_key", ()))
        region = game.named_regions.get(region_key)
        if region:
            region["boss_defeated"] = True
            region["boss_active"] = False
        reward = {"scrap": 3, "medicine": 1}
        biome = str(region["biome"]) if region else "forest"
        if biome == "swamp":
            reward["herbs"] = 2
        elif biome == "ashland":
            reward["wood"] = 3
        elif biome == "quarry":
            reward["scrap"] = 5
        elif biome == "redwood":
            reward["logs"] = 4
        elif biome == "meadow":
            reward["meals"] = 2
        game.add_resource_bundle(reward)
        for survivor in game.living_survivors():
            survivor.morale = clamp(survivor.morale + 8, 0, 100)
            game.adjust_trust(survivor, 2.0)
        game.spawn_floating_text(f"{zombie.boss_name.lower()} caiu", zombie.pos, PALETTE["morale"])
        game.spawn_floating_text(game.bundle_summary(reward), zombie.pos + Vector2(0, -22), PALETTE["accent_soft"])
        if region:
            game.set_event_message(f"{zombie.boss_name} caiu em {region['name']}. A zona cedeu recursos raros ao campo.", duration=6.6)


def camp_clearance_radius(game: "Game") -> float:
    return max(CAMP_RADIUS, game.camp_half_size * 1.46)









