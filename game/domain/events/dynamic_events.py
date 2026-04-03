from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Vector2

from ...entities import Survivor
from ...core.config import CAMP_CENTER, PALETTE, clamp
from ...core.models import DynamicEvent

if TYPE_CHECKING:
    from ...app.session import Game


def create_faction_standings(_game: "Game") -> dict[str, float]:
    return {
        "andarilhos": 12.0,
        "ferro-velho": 0.0,
        "vigias_da_estrada": -6.0,
    }


def faction_label(_game: "Game", key: str) -> str:
    return {
        "andarilhos": "Andarilhos",
        "ferro-velho": "Ferro-Velho",
        "vigias_da_estrada": "Vigias da Estrada",
    }.get(key, key)


def adjust_faction_standing(game: "Game", key: str, delta: float) -> float:
    current = float(game.faction_standings.get(key, 0.0))
    current = clamp(current + delta, -100, 100)
    game.faction_standings[key] = current
    return current


def faction_standing_label(game: "Game", key: str) -> str:
    score = float(game.faction_standings.get(key, 0.0))
    if score >= 55:
        return "aliados"
    if score >= 20:
        return "proximos"
    if score >= -10:
        return "neutros"
    if score >= -40:
        return "hostis"
    return "jurados"


def strongest_faction(game: "Game") -> tuple[str, float]:
    return max(game.faction_standings.items(), key=lambda item: item[1])


def active_dynamic_event(game: "Game", kind: str | None = None) -> DynamicEvent | None:
    for event in game.active_dynamic_events:
        if not event.resolved and (kind is None or event.kind == kind):
            return event
    return None


def dynamic_event_for_survivor(game: "Game", survivor: Survivor, kind: str | None = None) -> DynamicEvent | None:
    for event in game.active_dynamic_events:
        if event.resolved:
            continue
        if event.target_name == survivor.name and (kind is None or event.kind == kind):
            return event
    return None


def dynamic_event_summary(game: "Game") -> str | None:
    event = game.active_dynamic_event()
    if not event:
        return None
    if event.kind == "faccao":
        humane = dict(event.data.get("humane", {}))
        hardline = dict(event.data.get("hardline", {}))
        return f"{game.faction_label(str(event.data.get('faction', 'andarilhos')))}: E {humane.get('title', 'negociar')}  |  Q {hardline.get('title', 'impor')}  |  {max(0, int(event.timer))}s"
    if event.kind == "expedicao":
        return f"Expedicao pede socorro: va ate o sinal vermelho e use E  |  {max(0, int(event.timer))}s"
    return f"{event.label} - {max(0, int(event.timer))}s"


def spawn_dynamic_event(
    game: "Game",
    kind: str,
    label: str,
    pos: Vector2,
    *,
    timer: float,
    urgency: float,
    target_name: str | None = None,
    building_uid: int | None = None,
    data: dict[str, object] | None = None,
) -> DynamicEvent:
    event = DynamicEvent(
        uid=game.next_dynamic_event_uid,
        kind=kind,
        label=label,
        pos=Vector2(pos),
        timer=timer,
        urgency=urgency,
        target_name=target_name,
        building_uid=building_uid,
        data=data or {},
    )
    game.next_dynamic_event_uid += 1
    game.active_dynamic_events = [event]
    game.dynamic_event_cooldown = game.random.uniform(18.0, 30.0)
    game.set_event_message(label, duration=max(5.0, min(8.0, timer * 0.5)))
    game.spawn_floating_text(label.lower(), pos, PALETTE["danger_soft"] if urgency > 0.55 else PALETTE["morale"])
    if kind in {"incendio", "alarme", "expedicao", "fuga", "desercao"}:
        burst_color = PALETTE["danger_soft"] if kind != "expedicao" else PALETTE["accent_soft"]
        game.impact_burst(pos, burst_color, radius=12, shake=0.7, ember_count=2, smoky=kind == "incendio")
    game.survivors_react_to_event(event)
    return event


def choose_fire_site(game: "Game") -> tuple[Vector2, str, int | None, str]:
    if game.buildings:
        building = game.random.choice(game.buildings)
        return Vector2(building.pos), str(building.kind), building.uid, str(building.kind)
    core_sites = [
        (game.stockpile_pos, "stockpile", None, "estoque"),
        (game.kitchen_pos, "kitchen", None, "fogao"),
        (game.workshop_pos, "workshop", None, "oficina"),
    ]
    pos, site_kind, uid, label = game.random.choice(core_sites)
    return Vector2(pos), site_kind, uid, label


def roadside_event_pos(game: "Game", *, side: str | None = None) -> Vector2:
    side = side or game.random.choice(("north", "south", "east", "west"))
    margin = 118.0
    lateral_jitter = game.random.uniform(-96, 96)
    if side == "north":
        return CAMP_CENTER + Vector2(lateral_jitter, -(game.camp_half_size + margin))
    if side == "south":
        return CAMP_CENTER + Vector2(lateral_jitter, game.camp_half_size + margin)
    if side == "east":
        return CAMP_CENTER + Vector2(game.camp_half_size + margin, lateral_jitter)
    return CAMP_CENTER + Vector2(-(game.camp_half_size + margin), lateral_jitter)


def dynamic_event_candidates(game: "Game") -> list[tuple[str, float, dict[str, object]]]:
    living = game.living_survivors()
    if not living:
        return []

    candidates: list[tuple[str, float, dict[str, object]]] = []
    if game.spare_beds() > 0 and game.next_recruit_index < len(game.recruit_pool) and game.average_morale() > 48 and game.average_trust() > 42:
        profile = game.recruit_pool[game.next_recruit_index]
        outsider_pos = game.roadside_event_pos()
        candidates.append(
            (
                "abrigo",
                0.32 + game.camp_level * 0.05,
                {
                    "pos": outsider_pos,
                    "profile": profile,
                    "visitor": {
                        "name": str(profile["name"]),
                        "title": "forasteiro",
                        "body": (144, 154, 132),
                        "accent": (112, 124, 98),
                        "prop": "bag",
                    },
                },
            )
        )

    disease_target = max(living, key=lambda survivor: survivor.exhaustion + (100 - survivor.health))
    if (
        game.weather_precipitation_factor() > 0.26
        or game.weather_mist_factor() > 0.34
        or game.herbs <= 1
        or game.average_health() < 74
    ) and not game.dynamic_event_for_survivor(disease_target):
        severity = clamp((disease_target.exhaustion - 40) / 40, 0.0, 1.0)
        candidates.append(("doenca", 0.34 + severity * 0.24, {"target": disease_target}))

    if (game.weather_wind_factor() > 0.34 or game.weather_storm_factor() > 0.3 or game.bonfire_stage() == "alta") and (game.buildings or game.wood + game.logs > 12):
        fire_pos, site_kind, building_uid, site_label = game.choose_fire_site()
        candidates.append(
            (
                "incendio",
                0.26 + game.weather_wind_factor() * 0.16 + game.weather_storm_factor() * 0.22,
                {"pos": fire_pos, "site_kind": site_kind, "building_uid": building_uid, "site_label": site_label},
            )
        )

    if game.is_night and game.barricades and (game.weakest_barricade_health() < 68 or len(game.zombies) >= 4 or getattr(game, "horde_active", False)):
        weakest = min(game.barricades, key=lambda barricade: barricade.health / max(1.0, barricade.max_health))
        candidates.append(
            (
                "alarme",
                0.24 + (1.0 - weakest.health / max(1.0, weakest.max_health)) * 0.4 + (0.18 if getattr(game, "horde_active", False) else 0.0),
                {"pos": Vector2(weakest.pos), "angle": weakest.angle},
            )
        )

    low_trust = min(living, key=lambda survivor: (survivor.trust_leader, survivor.morale))
    if low_trust.trust_leader < 38 or (low_trust.morale < 34 and low_trust.exhaustion > 56):
        exit_pos = CAMP_CENTER + Vector2(-game.camp_half_size - 94, game.random.uniform(-64, 64))
        candidates.append(("fuga", 0.34 + max(0.0, 38 - low_trust.trust_leader) * 0.008, {"target": low_trust, "pos": exit_pos}))

    deserter = min(living, key=lambda survivor: (survivor.trust_leader + survivor.morale * 0.4, survivor.energy))
    if game.average_trust() < 42 and (game.feud_count() > 0 or game.average_morale() < 46) and deserter.trust_leader < 30:
        exit_pos = CAMP_CENTER + Vector2(game.camp_half_size + 108, game.random.uniform(-80, 80))
        candidates.append(("desercao", 0.24 + max(0.0, 30 - deserter.trust_leader) * 0.01, {"target": deserter, "pos": exit_pos}))

    faction_pool = [
        key
        for key, score in game.faction_standings.items()
        if abs(score) < 72
    ]
    if faction_pool and game.day >= 2 and game.average_trust() > 26:
        faction_key = game.random.choice(faction_pool)
        roadside_pos = game.roadside_event_pos()
        faction_visuals = {
            "andarilhos": {"name": "andarilhos", "title": "familia cansada", "body": (158, 170, 126), "accent": (112, 124, 84), "prop": "bag"},
            "ferro-velho": {"name": "ferro-velho", "title": "comerciante de sucata", "body": (146, 126, 104), "accent": (112, 98, 82), "prop": "crate"},
            "vigias_da_estrada": {"name": "vigias", "title": "patrulha armada", "body": (126, 138, 154), "accent": (84, 96, 118), "prop": "pole"},
        }
        candidates.append(
            (
                "faccao",
                0.22 + game.camp_level * 0.04 + max(0.0, game.average_trust() - 40) * 0.002,
                {"faction": faction_key, "pos": roadside_pos, "visitor": dict(faction_visuals[faction_key])},
            )
        )

    return candidates


def maybe_spawn_dynamic_event(game: "Game") -> None:
    if game.active_dynamic_events or game.dynamic_event_cooldown > 0:
        return
    candidates = game.dynamic_event_candidates()
    if not candidates:
        game.dynamic_event_cooldown = game.random.uniform(8.0, 14.0)
        return

    total_weight = sum(weight for _, weight, _ in candidates)
    roll = game.random.uniform(0, total_weight)
    chosen_kind = candidates[-1]
    running = 0.0
    for candidate in candidates:
        running += candidate[1]
        if roll <= running:
            chosen_kind = candidate
            break

    kind, _, payload = chosen_kind
    if kind == "abrigo":
        profile = payload["profile"]
        game.spawn_dynamic_event(
            "abrigo",
            f"Pedido de abrigo: {profile['name']} espera no limite da mata.",
            Vector2(payload["pos"]),
            timer=28.0,
            urgency=0.32,
            data={"profile": profile},
        )
    elif kind == "doenca":
        target: Survivor = payload["target"]
        game.spawn_dynamic_event(
            "doenca",
            f"Doenca: {target.name} caiu febril e precisa de cuidado.",
            Vector2(target.pos),
            timer=34.0,
            urgency=0.62,
            target_name=target.name,
        )
    elif kind == "incendio":
        game.spawn_dynamic_event(
            "incendio",
            f"Incendio: o {payload['site_label']} pegou fogo no acampamento.",
            Vector2(payload["pos"]),
            timer=24.0,
            urgency=0.84,
            building_uid=payload["building_uid"],
            data={"site_kind": payload["site_kind"], "site_label": payload["site_label"], "tick": 1.8},
        )
    elif kind == "fuga":
        target = payload["target"]
        game.spawn_dynamic_event(
            "fuga",
            f"Fuga: {target.name} entrou em panico e correu para fora do quadrado.",
            Vector2(payload["pos"]),
            timer=22.0,
            urgency=0.72,
            target_name=target.name,
        )
    elif kind == "desercao":
        target = payload["target"]
        game.spawn_dynamic_event(
            "desercao",
            f"Desercao: {target.name} arrumou a mochila e quer sumir pela trilha.",
            Vector2(payload["pos"]),
            timer=26.0,
            urgency=0.86,
            target_name=target.name,
        )
    elif kind == "faccao":
        faction = str(payload["faction"])
        pos = Vector2(payload["pos"])
        scenarios = {
            "andarilhos": {
                "label": "Andarilhos pedem comida para uma familia ferida na trilha.",
                "humane": {
                    "title": "Partilhar mantimentos",
                    "cost": {"meals": 2, "food": 1},
                    "reward": {"morale": 7, "trust": 4, "faction": 18, "future": {"medicine": 1}},
                    "message": "A clareira dividiu comida e os Andarilhos prometeram lembrar disso.",
                },
                "hardline": {
                    "title": "Cobrar sucata pela passagem",
                    "reward": {"scrap": 3, "faction": -16, "morale": -5, "trust": -6},
                    "message": "Voce fez negocio com a fome deles. O estoque cresceu, mas o boato correu.",
                },
            },
            "ferro-velho": {
                "label": "Ferro-Velho quer um acordo por uma carroca de metal raro.",
                "humane": {
                    "title": "Troca justa",
                    "cost": {"food": 2},
                    "reward": {"scrap": 5, "faction": 14, "trust": 3, "morale": 2},
                    "message": "A troca foi limpa e o elo com Ferro-Velho ficou mais forte.",
                },
                "hardline": {
                    "title": "Tomar a carga na pressao",
                    "reward": {"scrap": 8, "faction": -20, "trust": -8, "morale": -4},
                    "message": "Voce arrancou a carga deles na pressao. Ganhou metal e perdeu palavra.",
                },
            },
            "vigias_da_estrada": {
                "label": "Os Vigias da Estrada capturaram um forasteiro e exigem sua posicao.",
                "humane": {
                    "title": "Proteger o forasteiro",
                    "cost": {"wood": 2, "medicine": 1},
                    "reward": {"faction": -8, "trust": 8, "morale": 8, "future": {"survivor": True}},
                    "message": "Voce peitou os Vigias e puxou o ferido para dentro do anel do acampamento.",
                },
                "hardline": {
                    "title": "Entregar o homem e ganhar paz",
                    "reward": {"faction": 15, "trust": -12, "morale": -10, "food": 2},
                    "message": "Os Vigias sairam satisfeitos. O campo, nem tanto.",
                },
            },
        }
        scenario = scenarios[faction]
        game.spawn_dynamic_event(
            "faccao",
            f"{game.faction_label(faction)}: {scenario['label']}",
            pos,
            timer=30.0,
            urgency=0.58,
            data={
                "faction": faction,
                "label": scenario["label"],
                "humane": scenario["humane"],
                "hardline": scenario["hardline"],
            },
        )
    elif kind == "alarme":
        angle = float(payload["angle"])
        if -0.75 <= angle <= 0.75:
            edge = "leste"
        elif 0.75 < angle < 2.35:
            edge = "sul"
        elif -2.35 < angle < -0.75:
            edge = "norte"
        else:
            edge = "oeste"
        game.spawn_dynamic_event(
            "alarme",
            f"Alarme: pancadas vieram da cerca {edge} e a linha tremeu.",
            Vector2(payload["pos"]),
            timer=20.0,
            urgency=0.78,
            data={"edge": edge, "tick": 1.2},
        )


def resolve_dynamic_event(game: "Game", event: DynamicEvent, *, accepted: bool = True) -> bool:
    if event.resolved:
        return False

    if event.kind == "doenca":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if not target:
            event.resolved = True
            return False
        if game.medicine > 0:
            game.medicine -= 1
            target.health = clamp(target.health + 24, 0, target.max_health)
        elif game.herbs > 0:
            game.herbs -= 1
            target.health = clamp(target.health + 14, 0, target.max_health)
        else:
            game.set_event_message("A enfermaria esta sem remedios para tratar a febre.", duration=4.6)
            return False
        target.energy = clamp(target.energy + 8, 0, 100)
        target.morale = clamp(target.morale + 4, 0, 100)
        target.exhaustion = clamp(target.exhaustion - 12, 0, 100)
        game.adjust_trust(target, 2.8)
        game.set_event_message(f"{target.name} foi estabilizado na enfermaria.", duration=5.4)
        game.spawn_floating_text("febre contida", target.pos, PALETTE["heal"])

    elif event.kind == "incendio":
        game.set_event_message("O incendio foi contido antes de comer a estrutura.", duration=5.2)
        game.spawn_floating_text("fogo controlado", event.pos, PALETTE["heal"])
        game.impact_burst(event.pos, PALETTE["heal"], radius=16, shake=1.4, ember_count=10, smoky=True)

    elif event.kind == "alarme":
        nearest = game.closest_barricade(event.pos)
        if nearest:
            nearest.repair(10)
        for zombie in game.zombies:
            if zombie.pos.distance_to(event.pos) < 140:
                zombie.stagger = max(zombie.stagger, 0.16)
                zombie.health -= 8
        for survivor in game.living_survivors():
            if survivor.distance_to(event.pos) < 220:
                survivor.morale = clamp(survivor.morale + 2.0, 0, 100)
                game.adjust_trust(survivor, 1.8)
        game.set_event_message(f"Voce respondeu ao alarme da cerca {event.data.get('edge', 'externa')} e a linha segurou.", duration=5.6)
        game.spawn_floating_text("linha segurou", event.pos, PALETTE["heal"])
        game.impact_burst(event.pos, PALETTE["heal"], radius=14, shake=1.2, ember_count=6, smoky=True)

    elif event.kind == "fuga":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if not target:
            event.resolved = True
            return False
        target.morale = clamp(target.morale + 6, 0, 100)
        target.energy = clamp(target.energy + 4, 0, 100)
        game.adjust_trust(target, 8.0)
        game.set_event_message(f"{target.name} respirou fundo e voltou para dentro do anel da base.", duration=5.4)
        game.spawn_floating_text("segurou a fuga", target.pos, PALETTE["morale"])

    elif event.kind == "desercao":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if not target:
            event.resolved = True
            return False
        target.morale = clamp(target.morale + 4, 0, 100)
        game.adjust_trust(target, 10.0)
        game.set_event_message(f"{target.name} desistiu da trilha e ficou no campo.", duration=5.4)
        game.spawn_floating_text("ficou", target.pos, PALETTE["morale"])

    elif event.kind == "abrigo":
        profile = dict(event.data.get("profile", {}))
        if accepted and game.spare_beds() > 0:
            recruited = game.recruit_survivor_from_profile(
                profile,
                announce_message=f"{profile['name']} foi acolhido na clareira e ganhou uma cama.",
                floating_label="abrigo aceito",
            )
            if not recruited:
                game.set_event_message("O acampamento nao tem cama livre para acolher mais alguem.", duration=4.8)
                return False
            if game.next_recruit_index < len(game.recruit_pool) and game.recruit_pool[game.next_recruit_index]["name"] == profile.get("name"):
                game.next_recruit_index += 1
        else:
            game.set_event_message(f"{profile.get('name', 'O viajante')} se foi sem conseguir abrigo.", duration=4.8)
        game.morale_flash = min(1.0, game.morale_flash + 0.08)

    elif event.kind == "expedicao":
        expedition = game.active_expedition
        if not expedition:
            event.resolved = True
            game.active_dynamic_events = []
            return False
        expedition["distress_resolved"] = True
        expedition["danger"] = clamp(float(expedition["danger"]) - 0.16, 0.12, 0.95)
        expedition["timer"] = max(8.0, float(expedition["timer"]) - 5.0)
        loot_bundle = dict(expedition.get("loot_bundle", {}))
        bonus_key = "medicine" if expedition["region_biome"] in {"swamp", "ruin"} else "scrap"
        loot_bundle[bonus_key] = loot_bundle.get(bonus_key, 0) + 1
        expedition["loot_bundle"] = loot_bundle
        for survivor in game.survivors:
            if survivor.name in expedition["members"]:
                survivor.trust_leader = clamp(survivor.trust_leader + 3.5, 0, 100)
                survivor.morale = clamp(survivor.morale + 4.0, 0, 100)
        game.set_event_message(f"Voce abriu caminho e a expedicao retomou a rota para {expedition['region_name']}.", duration=6.0)
        game.spawn_floating_text("socorro entregue", event.pos, PALETTE["heal"])

    elif event.kind == "faccao":
        faction = str(event.data.get("faction", "andarilhos"))
        branch_key = "humane" if accepted else "hardline"
        branch = dict(event.data.get(branch_key, {}))
        cost_bundle = dict(branch.get("cost", {}))
        if cost_bundle and not game.consume_resource_bundle(cost_bundle):
            game.set_event_message("Faltam recursos para sustentar essa escolha moral agora.", duration=4.8)
            return False

        reward = dict(branch.get("reward", {}))
        resource_reward = {
            key: int(value)
            for key, value in reward.items()
            if key in {"logs", "wood", "food", "herbs", "scrap", "meals", "medicine"}
        }
        if resource_reward:
            game.add_resource_bundle(resource_reward)

        for survivor in game.living_survivors():
            game.adjust_trust(survivor, float(reward.get("trust", 0.0)) * (0.85 if accepted else 1.0))
            survivor.morale = clamp(survivor.morale + float(reward.get("morale", 0.0)), 0, 100)

        game.adjust_faction_standing(faction, float(reward.get("faction", 0.0)))
        future = dict(reward.get("future", {})) if isinstance(reward.get("future", {}), dict) else {}
        if future.get("medicine"):
            game.add_resource_bundle({"medicine": int(future["medicine"])})
        if future.get("survivor") and game.spare_beds() > 0 and game.next_recruit_index < len(game.recruit_pool):
            profile = game.recruit_pool[game.next_recruit_index]
            game.next_recruit_index += 1
            game.recruit_survivor_from_profile(
                profile,
                announce_message=f"{profile['name']} foi trazido pela confusao e pediu para ficar na clareira.",
                floating_label="resgatado",
            )

        text_color = PALETTE["morale"] if accepted else PALETTE["danger_soft"]
        game.set_event_message(str(branch.get("message", "A faccao respondeu a sua escolha.")), duration=6.0)
        game.spawn_floating_text(game.faction_label(faction).lower(), event.pos, text_color)

    event.resolved = True
    game.survivors_react_to_event(event, resolved=True)
    game.active_dynamic_events = []
    game.dynamic_event_cooldown = game.random.uniform(18.0, 34.0)
    return True


def fail_dynamic_event(game: "Game", event: DynamicEvent) -> None:
    if event.kind == "doenca":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if target:
            target.health = clamp(target.health - 18, 0, target.max_health)
            target.morale = clamp(target.morale - 10, 0, 100)
            target.exhaustion = clamp(target.exhaustion + 18, 0, 100)
            game.adjust_trust(target, -4.0)
            game.set_event_message(f"A febre de {target.name} piorou por falta de cuidado.", duration=5.6)
    elif event.kind == "incendio":
        site_kind = str(event.data.get("site_kind", "stockpile"))
        if event.building_uid is not None:
            building = game.building_by_id(event.building_uid)
            if building:
                game.buildings = [item for item in game.buildings if item.uid != building.uid]
                game.assign_building_specialists()
                game.set_event_message(f"O incendio consumiu {building.kind} antes de ser apagado.", duration=5.8)
        elif site_kind == "stockpile":
            game.logs = max(0, game.logs - 4)
            game.wood = max(0, game.wood - 4)
            game.food = max(0, game.food - 2)
            game.set_event_message("As chamas comeram parte do estoque central.", duration=5.8)
        elif site_kind == "kitchen":
            game.food = max(0, game.food - 4)
            game.meals = max(0, game.meals - 3)
            game.herbs = max(0, game.herbs - 1)
            game.set_event_message("O fogo passou pelo fogao e estragou suprimentos da cozinha.", duration=5.8)
        else:
            game.wood = max(0, game.wood - 3)
            game.scrap = max(0, game.scrap - 3)
            game.set_event_message("A oficina perdeu material depois do incendio.", duration=5.8)
        game.impact_burst(event.pos, PALETTE["danger_soft"], radius=18, shake=4.4, ember_count=10, smoky=True)
    elif event.kind == "alarme":
        nearest = game.closest_barricade(event.pos)
        if nearest:
            nearest.health = clamp(nearest.health - 26, 0.0, nearest.max_health)
        for _ in range(2 + (1 if getattr(game, "horde_active", False) else 0)):
            game.spawn_forest_ambient_zombie(anchor=Vector2(event.pos), radius=120)
        for survivor in game.living_survivors():
            if survivor.distance_to(event.pos) < 220:
                survivor.insanity = clamp(survivor.insanity + 8, 0, 100)
                survivor.morale = clamp(survivor.morale - 5, 0, 100)
        game.set_event_message(f"O alarme estourou tarde demais e a cerca {event.data.get('edge', 'externa')} cedeu sob pancada.", duration=5.8)
        game.impact_burst(event.pos, PALETTE["danger_soft"], radius=20, shake=4.0, ember_count=8, smoky=True)
    elif event.kind == "fuga":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if target:
            target.morale = clamp(target.morale - 16, 0, 100)
            target.energy = clamp(target.energy - 12, 0, 100)
            target.trust_leader = clamp(target.trust_leader - 10, 0, 100)
            game.set_event_message(f"{target.name} sumiu por um tempo na mata e voltou abalado.", duration=5.8)
    elif event.kind == "desercao":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if target:
            game.remove_survivor(target)
            game.set_event_message(f"{target.name} desertou e levou sua funcao embora da clareira.", duration=6.0)
    elif event.kind == "abrigo":
        profile = event.data.get("profile", {})
        game.set_event_message(f"{profile.get('name', 'O viajante')} cansou de esperar e seguiu pela trilha.", duration=5.0)
    elif event.kind == "expedicao":
        expedition = game.active_expedition
        if expedition:
            expedition["danger"] = clamp(float(expedition["danger"]) + 0.2, 0.18, 1.0)
            expedition["timer"] = max(6.0, float(expedition["timer"]) - 2.0)
            game.set_event_message(f"O socorro falhou e a equipe sofreu mais na rota de {expedition['region_name']}.", duration=5.8)
        else:
            game.set_event_message("O pedido de socorro morreu no vento da mata.", duration=5.0)
    elif event.kind == "faccao":
        faction = str(event.data.get("faction", "andarilhos"))
        game.adjust_faction_standing(faction, -4.0)
        game.set_event_message(f"{game.faction_label(faction)} foi embora levando o impasse na memoria.", duration=5.0)

    game.survivors_react_to_event(event, resolved=False)
    game.active_dynamic_events = []
    game.dynamic_event_cooldown = game.random.uniform(20.0, 34.0)


def update_dynamic_events(game: "Game", dt: float) -> None:
    game.dynamic_event_cooldown = max(0.0, game.dynamic_event_cooldown - dt)
    game.maybe_spawn_dynamic_event()
    if not game.active_dynamic_events:
        return

    event = game.active_dynamic_events[0]
    event.timer -= dt

    if event.kind == "doenca":
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if not target:
            game.active_dynamic_events = []
            return
        event.pos = Vector2(target.pos)
        target.health = clamp(target.health - 0.42 * dt, 0, target.max_health)
        target.energy = clamp(target.energy - 0.5 * dt, 0, 100)
        target.morale = clamp(target.morale - 0.22 * dt, 0, 100)
    elif event.kind == "incendio":
        tick = float(event.data.get("tick", 0.0)) - dt
        if tick <= 0:
            event.data["tick"] = 1.8
            game.emit_embers(event.pos, 6, smoky=True)
            if event.building_uid is None:
                game.wood = max(0, game.wood - 1)
                if str(event.data.get("site_kind")) == "kitchen":
                    game.food = max(0, game.food - 1)
            game.screen_shake = max(game.screen_shake, 1.4)
        else:
            event.data["tick"] = tick
    elif event.kind == "alarme":
        tick = float(event.data.get("tick", 0.0)) - dt
        if tick <= 0:
            event.data["tick"] = game.random.uniform(0.8, 1.4)
            game.impact_burst(event.pos, PALETTE["danger_soft"], radius=9, shake=0.65, ember_count=2, smoky=True)
            for survivor in game.living_survivors():
                if survivor.distance_to(event.pos) < 220 and survivor.bark_cooldown <= 0:
                    game.trigger_survivor_bark(survivor, "Segura essa cerca!", PALETTE["danger_soft"], duration=1.8)
        else:
            event.data["tick"] = tick
    elif event.kind in {"fuga", "desercao"}:
        target = next((survivor for survivor in game.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
        if not target:
            game.active_dynamic_events = []
            return
        event.pos = Vector2(event.pos)
        target.state_label = "em fuga" if event.kind == "fuga" else "desertando"
    elif event.kind == "expedicao":
        event.pos = game.expedition_distress_pos(game.active_expedition)
    elif event.kind == "abrigo":
        event.pos = Vector2(event.pos)

    if event.timer <= 0:
        game.fail_dynamic_event(event)









