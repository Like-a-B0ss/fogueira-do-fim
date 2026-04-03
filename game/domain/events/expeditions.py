from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import Vector2

from ...entities import Survivor, Zombie
from ...core.config import CAMP_CENTER, PALETTE, angle_to_vector, clamp
from ...core.models import DamagePulse

if TYPE_CHECKING:
    from ...app.session import Game


def expedition_provision_cost(game: "Game") -> dict[str, int]:
    phase = game.economy_phase_key()
    if phase == "early":
        return {"food": 1}
    if phase == "mid":
        return {"food": 1, "meals": 1}
    return {"food": 2, "meals": 1}


def expedition_members(game: "Game") -> list[Survivor]:
    if not game.active_expedition:
        return []
    member_names = set(game.active_expedition.get("members", []))
    return [survivor for survivor in game.survivors if survivor.is_alive() and survivor.name in member_names]


def expedition_visible_members(game: "Game") -> list[Survivor]:
    expedition = game.active_expedition
    if not expedition:
        return []
    visible = game.expedition_caravan_state() is not None or str(expedition.get("skirmish_state", "")) in {"active", "resolved", "failed"}
    return game.expedition_members() if visible else []


def expedition_member_anchor(game: "Game", survivor: Survivor) -> Vector2:
    expedition = game.active_expedition
    if not expedition:
        return Vector2(game.radio_pos)
    members = game.expedition_members()
    if survivor not in members:
        return Vector2(game.radio_pos)
    index = members.index(survivor)
    caravan = game.expedition_caravan_state()
    if caravan is not None:
        start = Vector2(game.radio_pos)
        edge = game.expedition_route_edge_point(expedition)
        direction = edge - start
        if direction.length_squared() <= 0.01:
            direction = Vector2(1, 0)
        else:
            direction = direction.normalize()
        lateral = Vector2(-direction.y, direction.x)
        if caravan["phase"] == "outbound":
            center = start.lerp(edge, float(caravan["progress"]) * 0.72)
        else:
            center = edge.lerp(start, float(caravan["progress"]) * 0.72)
        row_offset = Vector2(-direction.x, -direction.y) * (16 * index)
        side_offset = lateral * ((index - (len(members) - 1) * 0.5) * 14)
        return center + row_offset + side_offset
    skirmish_pos = expedition.get("skirmish_pos")
    if skirmish_pos is not None:
        center = Vector2(skirmish_pos)
        angle = index / max(1, len(members)) * math.tau
        return center + angle_to_vector(angle) * (24 + (index % 2) * 10)
    return Vector2(game.radio_pos)


def nearest_downed_expedition_member(game: "Game", pos: Vector2, max_distance: float = 86.0) -> Survivor | None:
    downed = [
        survivor
        for survivor in game.expedition_visible_members()
        if getattr(survivor, "expedition_downed", False) and survivor.pos.distance_to(pos) <= max_distance
    ]
    if not downed:
        return None
    return min(downed, key=lambda survivor: survivor.pos.distance_to(pos))


def revive_expedition_member(game: "Game", survivor: Survivor) -> None:
    survivor.expedition_downed = False
    survivor.health = clamp(max(22.0, survivor.health + 12), 0, survivor.max_health)
    survivor.energy = clamp(survivor.energy - 4, 0, 100)
    survivor.morale = clamp(survivor.morale + 4, 0, 100)
    survivor.state_label = "de pe na trilha"
    game.adjust_trust(survivor, 3.2)
    game.spawn_floating_text("levantou", survivor.pos, PALETTE["heal"])


def update_expedition_members(game: "Game", dt: float) -> None:
    expedition = game.active_expedition
    if not expedition:
        return
    members = game.expedition_members()
    if not members:
        return
    expedition_zombies = [
        zombie
        for zombie in game.zombies
        if zombie.is_alive()
        and getattr(zombie, "expedition_skirmish", False)
        and (expedition.get("skirmish_pos") is None or zombie.pos.distance_to(Vector2(expedition["skirmish_pos"])) < 260)
    ]
    for survivor in members:
        survivor.expedition_attack_cooldown = max(0.0, getattr(survivor, "expedition_attack_cooldown", 0.0) - dt)
        anchor = game.expedition_member_anchor(survivor)
        if survivor.expedition_downed:
            survivor.pos = Vector2(anchor)
            survivor.state_label = "caido na trilha"
            continue
        state = str(expedition.get("skirmish_state", "idle"))
        if state == "active" and expedition_zombies:
            target = min(expedition_zombies, key=lambda zombie: zombie.pos.distance_to(survivor.pos))
            if survivor.pos.distance_to(target.pos) > 54:
                survivor.move_toward(target.pos, dt, 0.9)
            elif survivor.expedition_attack_cooldown <= 0:
                hit = 14 + (4 if survivor.role in {"batedora", "vigia"} else 0)
                if survivor.has_trait("corajoso"):
                    hit += 3
                target.health -= hit
                target.stagger = 0.12
                survivor.expedition_attack_cooldown = 0.82
                game.damage_pulses.append(DamagePulse(Vector2(target.pos), 10, 0.18, PALETTE["accent_soft"]))
            survivor.state_label = "segurando a trilha"
        else:
            survivor.pos = survivor.pos.lerp(anchor, min(1.0, dt * 4.2))
            survivor.state_label = "em coluna" if game.expedition_caravan_state() is not None else "reagrupando"

        if survivor.health <= 18 and not survivor.expedition_downed:
            survivor.health = clamp(survivor.health, 10, survivor.max_health)
            survivor.expedition_downed = True
            survivor.state_label = "caido na trilha"
            game.spawn_floating_text("caido", survivor.pos, PALETTE["danger_soft"])


def expedition_candidate_survivors(game: "Game") -> list[Survivor]:
    available = [
        survivor
        for survivor in game.survivors
        if survivor.is_alive()
        and not game.is_survivor_on_expedition(survivor)
        and game.dynamic_event_for_survivor(survivor) is None
        and survivor.health > 54
        and survivor.energy > 44
        and getattr(survivor, "exhaustion", 0.0) < 70
    ]
    role_priority = {"batedora": 0, "mensageiro": 1, "vigia": 2, "lenhador": 3, "artesa": 4, "cozinheiro": 5}
    available.sort(
        key=lambda survivor: (
            role_priority.get(survivor.role, 99),
            -(survivor.energy + survivor.health * 0.6 + survivor.morale * 0.35),
            survivor.name,
        )
    )
    return available


def best_expedition_region(game: "Game") -> dict[str, object] | None:
    candidates = [
        region
        for region in game.named_regions.values()
        if int(region.get("expedition_sites", 0)) > 0 and Vector2(region["anchor"]).distance_to(CAMP_CENTER) > game.camp_clearance_radius() + 180
    ]
    if not candidates:
        return None
    phase = game.economy_phase_key()
    best_region: dict[str, object] | None = None
    best_score = -9999.0
    for region in candidates:
        distance = Vector2(region["anchor"]).distance_to(CAMP_CENTER)
        reward_bundle = dict(region.get("expedition_bundle", {}))
        reward_score = sum(int(value) for value in reward_bundle.values())
        reward_score += 2 if reward_bundle.get("medicine", 0) else 0
        reward_score += 1 if reward_bundle.get("meals", 0) else 0
        danger = float(region.get("expedition_danger", 0.35))
        if region.get("boss_blueprint") and not region.get("boss_defeated"):
            danger += 0.18
        if phase == "early":
            score = reward_score * 1.2 - danger * 11.0 - distance / 210
        elif phase == "mid":
            score = reward_score * 1.6 - danger * 8.8 - distance / 290
        else:
            score = reward_score * 2.0 - danger * 7.4 - distance / 360
        if region.get("boss_blueprint") and not region.get("boss_defeated") and phase != "late":
            score -= 2.4
        if score > best_score:
            best_score = score
            best_region = region
    return best_region


def expedition_status_text(game: "Game", *, short: bool = False) -> str | None:
    expedition = game.active_expedition
    if not expedition:
        return None
    region_name = str(expedition["region_name"])
    members = ", ".join(str(name) for name in expedition["members"])
    timer = max(0, int(float(expedition["timer"])))
    if str(expedition.get("skirmish_state", "")) == "active":
        if short:
            return f"caravana em combate {timer}s"
        return f"Caravana em combate na trilha de {region_name}. Equipe: {members}. Retorno em {timer}s."
    if short:
        return f"expedicao {region_name} {timer}s"
    if bool(expedition.get("recall_ordered", False)):
        return f"Expedicao recolhendo de {region_name}. Equipe: {members}. Retorno em {timer}s."
    return f"Expedicao em {region_name}. Equipe: {members}. Retorno em {timer}s."


def expedition_route_direction(game: "Game", expedition: dict[str, object] | None = None) -> Vector2:
    expedition = expedition or game.active_expedition
    if not expedition:
        return Vector2(1, 0)
    region = game.named_regions.get(tuple(expedition["region_key"]))
    anchor = Vector2(region["anchor"]) if region else Vector2(CAMP_CENTER + Vector2(1, 0))
    direction = anchor - game.radio_pos
    if direction.length_squared() <= 0.01:
        direction = Vector2(1, 0)
    else:
        direction = direction.normalize()
    return direction


def expedition_route_edge_point(game: "Game", expedition: dict[str, object] | None = None) -> Vector2:
    direction = game.expedition_route_direction(expedition)
    return Vector2(game.radio_pos) + direction * (game.camp_clearance_radius() + 138)


def expedition_caravan_state(game: "Game") -> dict[str, object] | None:
    expedition = game.active_expedition
    if not expedition:
        return None
    departure_window = float(expedition.get("departure_window", 7.0))
    return_window = float(expedition.get("return_window", 8.0))
    elapsed = float(expedition["duration"]) - float(expedition["timer"])
    if elapsed < departure_window:
        return {"phase": "outbound", "progress": clamp(elapsed / max(0.1, departure_window), 0.0, 1.0), "dir": game.expedition_route_direction(expedition)}
    if float(expedition["timer"]) < return_window:
        progress = 1.0 - float(expedition["timer"]) / max(0.1, return_window)
        return {"phase": "inbound", "progress": clamp(progress, 0.0, 1.0), "dir": game.expedition_route_direction(expedition)}
    return None


def expedition_distress_pos(game: "Game", expedition: dict[str, object] | None = None) -> Vector2:
    expedition = expedition or game.active_expedition
    direction = game.expedition_route_direction(expedition)
    lateral = Vector2(-direction.y, direction.x)
    seed_angle = game.hash_noise(int(direction.x * 1000), int(direction.y * 1000), 211) - 0.5
    return game.expedition_route_edge_point(expedition) + lateral * (40 + seed_angle * 42)


def expedition_skirmish_pos(game: "Game", expedition: dict[str, object] | None = None) -> Vector2:
    expedition = expedition or game.active_expedition
    direction = game.expedition_route_direction(expedition)
    lateral = Vector2(-direction.y, direction.x)
    seed_angle = game.hash_noise(int(direction.x * 1000), int(direction.y * 1200), 223) - 0.5
    return game.expedition_route_edge_point(expedition) + direction * 94 + lateral * (62 * seed_angle)


def spawn_expedition_skirmish(game: "Game", pos: Vector2, count: int) -> None:
    for _ in range(count):
        angle = game.random.uniform(0, math.tau)
        distance = game.random.uniform(90, 170)
        spawn_pos = pos + angle_to_vector(angle) * distance
        zombie = Zombie(spawn_pos, game.day)
        zombie.anchor = Vector2(pos)
        zombie.camp_pressure = clamp(0.58 + pos.distance_to(CAMP_CENTER) / 1100, 0.35, 0.95)
        zombie.expedition_skirmish = True
        game.zombies.append(zombie)


def launch_best_expedition(game: "Game") -> tuple[bool, str]:
    if game.active_expedition:
        return False, "Ja existe uma expedicao longe da base."
    if game.is_night:
        return False, "Expedicoes so saem com luz de dia."
    target_region = game.best_expedition_region()
    if not target_region:
        return False, "Nenhuma regiao conhecida ainda guarda saque raro."
    candidates = game.expedition_candidate_survivors()
    team_size = 2 if game.economy_phase_key() != "late" else 3
    if len(candidates) - team_size < 2:
        return False, "A base precisa manter gente suficiente dentro do quadrado."
    members = candidates[:team_size]
    provision_cost = game.expedition_provision_cost()
    if not game.consume_resource_bundle(provision_cost):
        return False, "Faltam racoes para abastecer a expedicao."

    distance = Vector2(target_region["anchor"]).distance_to(CAMP_CENTER)
    duration = 42.0 + distance / 120 + float(target_region.get("expedition_danger", 0.35)) * 20
    duration += game.weather_precipitation_factor() * 8.0
    duration += game.weather_wind_factor() * 4.0
    duration += game.weather_mist_factor() * 3.0
    duration += game.weather_storm_factor() * 6.0
    target_region["expedition_sites"] = max(0, int(target_region.get("expedition_sites", 1)) - 1)

    for survivor in members:
        survivor.on_expedition = True
        survivor.state = "expedition"
        survivor.state_label = "em expedicao"
        survivor.velocity *= 0.0
        survivor.pos = Vector2(game.radio_pos)

    game.active_expedition = {
        "region_key": tuple(target_region["key"]),
        "region_name": str(target_region["name"]),
        "region_biome": str(target_region["biome"]),
        "members": [survivor.name for survivor in members],
        "timer": duration,
        "duration": duration,
        "danger": float(target_region.get("expedition_danger", 0.35)),
        "loot_bundle": dict(target_region.get("expedition_bundle", {})),
        "loot_label": str(target_region.get("expedition_label", "saque raro")),
        "recall_ordered": False,
        "provision_cost": provision_cost,
        "departure_window": 7.0,
        "return_window": 8.0,
        "distress_checked": False,
        "distress_resolved": False,
        "escort_bonus": False,
        "skirmish_state": "idle",
        "skirmish_pos": None,
        "skirmish_timer": 0.0,
    }
    names = ", ".join(member.name for member in members)
    game.set_event_message(f"Expedicao saiu para {target_region['name']} atras de {target_region['expedition_label']}. Equipe: {names}.", duration=6.4)
    game.spawn_floating_text("expedicao saiu", game.radio_pos, PALETTE["accent_soft"])
    return True, f"Equipe a caminho de {target_region['name']}."


def recall_active_expedition(game: "Game") -> tuple[bool, str]:
    expedition = game.active_expedition
    if not expedition:
        return False, "Nao ha expedicao para recolher."
    if bool(expedition.get("recall_ordered", False)):
        return False, "A equipe ja esta voltando."
    expedition["recall_ordered"] = True
    expedition["timer"] = min(float(expedition["timer"]), 14.0 + float(expedition["danger"]) * 8.0)
    game.set_event_message(f"Ordem de recolha enviada para {expedition['region_name']}.", duration=5.4)
    game.spawn_floating_text("recolher equipe", game.radio_pos, PALETTE["morale"])
    return True, "A equipe recebeu a ordem de retorno."


def resolve_active_expedition(game: "Game") -> None:
    expedition = game.active_expedition
    if not expedition:
        return
    members = [survivor for survivor in game.survivors if survivor.name in expedition["members"] and survivor.is_alive()]
    if not members:
        game.active_expedition = None
        return

    region = game.named_regions.get(tuple(expedition["region_key"]))
    danger = float(expedition["danger"])
    if region and region.get("boss_blueprint") and not region.get("boss_defeated"):
        danger += 0.18
    danger += game.weather_precipitation_factor() * 0.1
    danger += game.weather_wind_factor() * 0.05
    danger += game.weather_mist_factor() * 0.04
    danger += game.weather_storm_factor() * 0.08
    if expedition.get("recall_ordered", False):
        danger += 0.08

    team_power = 0.0
    for survivor in members:
        team_power += survivor.health * 0.34 + survivor.energy * 0.28 + survivor.morale * 0.18 + survivor.trust_leader * 0.2
        if survivor.role in {"batedora", "mensageiro"}:
            team_power += 8
        if survivor.has_trait("corajoso"):
            team_power += 5
        if survivor.has_trait("paranoico"):
            team_power -= 3
    team_power = team_power / max(1, len(members) * 100)
    hazard_roll = game.random.random()
    severe_threshold = clamp(0.22 + danger * 0.28 - team_power * 0.16, 0.05, 0.34)
    moderate_threshold = clamp(severe_threshold + 0.26 + danger * 0.22 - team_power * 0.12, 0.24, 0.74)

    loot_bundle = dict(expedition["loot_bundle"])
    outcome_label = "voltou inteira"
    downed_members = [survivor for survivor in members if getattr(survivor, "expedition_downed", False)]
    if hazard_roll < severe_threshold:
        lost = min(
            downed_members or members,
            key=lambda survivor: (
                survivor.health + survivor.energy * 0.7 + survivor.morale * 0.5,
                survivor.name,
            ),
        )
        lost.on_expedition = False
        lost.expedition_downed = False
        game.remove_survivor(lost)
        loot_bundle = {key: max(0, int(value * 0.45)) for key, value in loot_bundle.items()}
        for survivor in members:
            if survivor is lost:
                continue
            survivor.on_expedition = False
            survivor.expedition_downed = False
            survivor.pos = Vector2(game.radio_pos) + Vector2(game.random.uniform(-22, 22), game.random.uniform(-18, 18))
            survivor.health = clamp(survivor.health - 18, 0, survivor.max_health)
            survivor.energy = clamp(survivor.energy - 22, 0, 100)
            survivor.morale = clamp(survivor.morale - 12, 0, 100)
            survivor.insanity = clamp(survivor.insanity + 10, 0, 100)
            survivor.state_label = "voltou da mata"
        game.set_event_message(f"A expedicao voltou quebrada de {expedition['region_name']}. {lost.name} nao retornou.", duration=7.0)
        game.spawn_floating_text("expedicao ferida", game.radio_pos, PALETTE["danger_soft"])
        outcome_label = "perdeu gente"
    elif hazard_roll < moderate_threshold:
        loot_bundle = {key: max(0, int(value * 0.72)) for key, value in loot_bundle.items()}
        for survivor in members:
            survivor.on_expedition = False
            survivor.expedition_downed = False
            survivor.pos = Vector2(game.radio_pos) + Vector2(game.random.uniform(-22, 22), game.random.uniform(-18, 18))
            survivor.health = clamp(survivor.health - 12, 0, survivor.max_health)
            survivor.energy = clamp(survivor.energy - 18, 0, 100)
            survivor.morale = clamp(survivor.morale - 7, 0, 100)
            survivor.insanity = clamp(survivor.insanity + 6, 0, 100)
            survivor.state_label = "voltou ferido"
        game.set_event_message(f"A expedicao apanhou em {expedition['region_name']}, mas voltou com parte do saque.", duration=6.4)
        game.spawn_floating_text("retorno pesado", game.radio_pos, PALETTE["danger_soft"])
        outcome_label = "voltou ferida"
    else:
        if expedition.get("recall_ordered", False):
            loot_bundle = {key: max(0, int(value * 0.68)) for key, value in loot_bundle.items()}
        bonus_key = "medicine" if expedition["region_biome"] in {"swamp", "ruin"} else "scrap"
        loot_bundle[bonus_key] = loot_bundle.get(bonus_key, 0) + 1
        for survivor in members:
            survivor.on_expedition = False
            survivor.expedition_downed = False
            survivor.pos = Vector2(game.radio_pos) + Vector2(game.random.uniform(-22, 22), game.random.uniform(-18, 18))
            survivor.energy = clamp(survivor.energy - 10, 0, 100)
            survivor.morale = clamp(survivor.morale + 4, 0, 100)
            survivor.trust_leader = clamp(survivor.trust_leader + 2, 0, 100)
            survivor.state_label = "voltou da expedicao"
        game.set_event_message(f"A equipe voltou de {expedition['region_name']} com {expedition['loot_label']}.", duration=6.6)
        game.spawn_floating_text("expedicao voltou", game.radio_pos, PALETTE["morale"])

    stored = game.add_resource_bundle(loot_bundle)
    if stored:
        game.spawn_floating_text(game.bundle_summary(stored), game.stockpile_pos, PALETTE["accent_soft"])
    if region is not None:
        region["expedition_last_outcome"] = outcome_label
    game.active_expedition = None
    game.assign_building_specialists()


def update_active_expedition(game: "Game", dt: float) -> None:
    expedition = game.active_expedition
    if not expedition:
        return
    game.update_expedition_members(dt)
    elapsed = float(expedition["duration"]) - float(expedition["timer"])
    departure_window = float(expedition.get("departure_window", 7.0))
    if (
        not bool(expedition.get("escort_bonus", False))
        and elapsed <= departure_window + 2.5
        and game.player.pos.distance_to(game.expedition_route_edge_point(expedition)) < 160
    ):
        expedition["escort_bonus"] = True
        expedition["danger"] = clamp(float(expedition["danger"]) - 0.08, 0.12, 0.95)
        for survivor in game.survivors:
            if survivor.name in expedition["members"]:
                survivor.trust_leader = clamp(survivor.trust_leader + 2.0, 0, 100)
                survivor.morale = clamp(survivor.morale + 2.0, 0, 100)
        game.set_event_message("Voce escoltou a coluna ate a borda da clareira. A equipe partiu mais segura.", duration=5.4)
        game.spawn_floating_text("coluna coberta", game.expedition_route_edge_point(expedition), PALETTE["heal"])

    if (
        str(expedition.get("skirmish_state", "idle")) == "idle"
        and elapsed >= departure_window * 0.62
        and float(expedition["timer"]) > float(expedition.get("return_window", 8.0)) + 12.0
    ):
        skirmish_pos = game.expedition_skirmish_pos(expedition)
        expedition["skirmish_state"] = "active"
        expedition["skirmish_pos"] = Vector2(skirmish_pos)
        expedition["skirmish_timer"] = 20.0 + float(expedition["danger"]) * 8.0
        wave_size = 3 + int(float(expedition["danger"]) * 3.2)
        game.spawn_expedition_skirmish(skirmish_pos, wave_size)
        game.set_event_message(f"A coluna trombou mortos na trilha de {expedition['region_name']}.", duration=5.8)
        game.spawn_floating_text("contato na trilha", skirmish_pos, PALETTE["danger_soft"])

    expedition["timer"] = float(expedition["timer"]) - dt
    if str(expedition.get("skirmish_state", "")) == "active":
        expedition["skirmish_timer"] = float(expedition.get("skirmish_timer", 0.0)) - dt
        skirmish_pos = Vector2(expedition["skirmish_pos"]) if expedition.get("skirmish_pos") is not None else game.expedition_skirmish_pos(expedition)
        living_zombies = [
            zombie
            for zombie in game.zombies
            if zombie.is_alive()
            and getattr(zombie, "expedition_skirmish", False)
            and zombie.pos.distance_to(skirmish_pos) < 240
        ]
        if not living_zombies:
            expedition["skirmish_state"] = "resolved"
            expedition["danger"] = clamp(float(expedition["danger"]) - 0.12, 0.1, 0.95)
            expedition["timer"] = max(8.0, float(expedition["timer"]) - 4.0)
            loot_bundle = dict(expedition.get("loot_bundle", {}))
            bonus_key = "scrap" if expedition["region_biome"] in {"ruin", "quarry", "ashland"} else "food"
            loot_bundle[bonus_key] = loot_bundle.get(bonus_key, 0) + 1
            expedition["loot_bundle"] = loot_bundle
            game.set_event_message(f"A caravana venceu a escaramuca e retomou a trilha de {expedition['region_name']}.", duration=5.8)
            game.spawn_floating_text("rota limpa", skirmish_pos, PALETTE["heal"])
        elif float(expedition.get("skirmish_timer", 0.0)) <= 0:
            expedition["skirmish_state"] = "failed"
            expedition["danger"] = clamp(float(expedition["danger"]) + 0.12, 0.18, 1.0)
            for survivor in game.survivors:
                if survivor.name in expedition["members"]:
                    survivor.health = clamp(survivor.health - 8, 0, survivor.max_health)
                    survivor.energy = clamp(survivor.energy - 12, 0, 100)
                    survivor.morale = clamp(survivor.morale - 6, 0, 100)
            game.set_event_message(f"A caravana apanhou sozinha na trilha de {expedition['region_name']}.", duration=5.8)
            game.spawn_floating_text("coluna ferida", skirmish_pos, PALETTE["danger_soft"])

    distress_threshold = float(expedition["duration"]) * 0.46
    can_spawn_distress = (
        not bool(expedition.get("distress_checked", False))
        and elapsed >= distress_threshold
        and float(expedition["timer"]) > float(expedition.get("return_window", 8.0)) + 6.0
    )
    if can_spawn_distress:
        expedition["distress_checked"] = True
        distress_chance = 0.28 + float(expedition["danger"]) * 0.62
        distress_chance += game.weather_precipitation_factor() * 0.12
        distress_chance += game.weather_mist_factor() * 0.04
        distress_chance += game.weather_storm_factor() * 0.08
        if game.random.random() < distress_chance and not game.active_dynamic_events:
            distress_pos = game.expedition_distress_pos(expedition)
            game.spawn_dynamic_event(
                "expedicao",
                f"Socorro de expedicao: foguete vermelho riscou a trilha para {expedition['region_name']}.",
                distress_pos,
                timer=30.0,
                urgency=0.78,
                data={"expedition_region": expedition["region_name"]},
            )
    if expedition["timer"] <= 0:
        game.resolve_active_expedition()









