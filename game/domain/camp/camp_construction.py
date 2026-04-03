from __future__ import annotations

import math

from pygame import Vector2

from ...core.config import CAMP_CENTER, PALETTE, angle_to_vector, clamp
from ...core.models import Barricade, Building, BuildingRequest, DamagePulse


def create_build_recipes(world) -> list[dict[str, object]]:
    return [
        {"kind": "barraca", "label": "Barraca", "wood": 5, "scrap": 1, "size": 34, "hint": "+2 camas"},
        {"kind": "torre", "label": "Torre", "wood": 8, "scrap": 4, "size": 28, "hint": "vigia especializado"},
        {"kind": "horta", "label": "Horta", "wood": 3, "scrap": 1, "size": 30, "hint": "mais comida"},
        {"kind": "anexo", "label": "Anexo", "wood": 7, "scrap": 5, "size": 32, "hint": "reforca barricadas"},
        {"kind": "serraria", "label": "Serraria", "wood": 7, "scrap": 2, "size": 34, "hint": "toras viram tabuas"},
        {"kind": "cozinha", "label": "Cozinha", "wood": 6, "scrap": 2, "size": 34, "hint": "refeicoes em lote"},
        {"kind": "enfermaria", "label": "Enfermaria", "wood": 6, "scrap": 4, "size": 34, "hint": "cura e remedios"},
    ]


def building_count(world, kind: str) -> int:
    return sum(1 for building in world.buildings if building.kind == kind)


def requested_building_count(world, kind: str) -> int:
    return sum(1 for request in world.build_requests if request.kind == kind)


def build_specialty_role(world, kind: str) -> str | None:
    return {
        "torre": "vigia",
        "horta": "cozinheiro",
        "anexo": "artesa",
        "serraria": "lenhador",
        "cozinha": "cozinheiro",
        "enfermaria": "mensageiro",
    }.get(kind)


def build_request_by_uid(world, uid: int | None) -> BuildingRequest | None:
    if uid is None:
        return None
    for request in world.build_requests:
        if request.uid == uid:
            return request
    return None


def active_build_requests(world) -> list[BuildingRequest]:
    return list(world.build_requests)


def prune_build_requests(world) -> None:
    """Limpa pedidos que perderam o morador responsavel ou o espaco reservado."""
    valid_names = {survivor.name for survivor in world.survivors if survivor.is_alive()}
    kept: list[BuildingRequest] = []
    for request in world.build_requests:
        if request.requester_name not in valid_names:
            continue
        kept.append(request)
    world.build_requests = kept


def pending_build_request_for_survivor(world, survivor) -> BuildingRequest | None:
    for request in world.build_requests:
        if request.requester_name == survivor.name:
            return request
    return None


def requested_building_total(world, kind: str) -> int:
    return world.building_count(kind) + world.requested_building_count(kind)


def desired_survivor_build_kind(world, survivor) -> str | None:
    """Escolhe a obra que o morador quer ver no acampamento antes de pedir ao chefe."""
    if world.pending_build_request_for_survivor(survivor):
        return None
    if world.active_dynamic_events or world.player_sleeping or world.is_night:
        return None
    if survivor.energy < 34 or survivor.health < 46 or survivor.exhaustion > 62:
        return None

    if world.spare_beds() <= 0 and world.requested_building_total("barraca") < max(1, 1 + world.camp_level):
        return "barraca"
    if survivor.role == "lenhador" and world.requested_building_total("serraria") < 1:
        return "serraria"
    if survivor.role == "cozinheiro" and world.requested_building_total("cozinha") < 1:
        return "cozinha"
    if survivor.role == "mensageiro" and world.requested_building_total("enfermaria") < 1:
        return "enfermaria"
    if survivor.role == "cozinheiro" and world.food < 10 and world.requested_building_total("horta") < max(1, world.camp_level):
        return "horta"
    if survivor.role == "artesa" and world.weakest_barricade_health() < 86 and world.requested_building_total("anexo") < max(1, world.camp_level):
        return "anexo"
    desired_towers = 1 + (1 if world.camp_level >= 2 else 0) + (1 if len(world.survivors) >= 8 else 0)
    if survivor.role == "vigia" and world.requested_building_total("torre") < desired_towers:
        return "torre"
    if world.economy_phase_key() != "early" and world.food < 8 and world.requested_building_total("horta") < max(1, world.camp_level):
        return "horta"
    return None


def find_build_request_site(world, kind: str, survivor=None) -> Vector2 | None:
    """Reserva um ponto valido dentro da base para a futura obra do morador."""
    rect = world.camp_rect(-48)
    origin = Vector2(survivor.pos) if survivor is not None else Vector2(CAMP_CENTER)
    candidates: list[tuple[float, Vector2]] = []
    for grid_y in range(int(rect.top), int(rect.bottom) + 1, 32):
        for grid_x in range(int(rect.left), int(rect.right) + 1, 32):
            candidate = world.building_center_snapped(Vector2(grid_x, grid_y))
            if not world.is_valid_build_position(kind, candidate):
                continue
            score = candidate.distance_to(origin)
            score += candidate.distance_to(world.workshop_pos) * 0.18
            if kind == "torre":
                score -= candidate.distance_to(CAMP_CENTER) * 0.32
            elif kind == "horta":
                score += candidate.distance_to(world.kitchen_pos) * 0.08
            elif kind == "serraria":
                score += candidate.distance_to(world.stockpile_pos) * 0.04
            elif kind == "enfermaria":
                score += candidate.distance_to(world.kitchen_pos) * 0.06
            candidates.append((score, candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return Vector2(candidates[0][1])


def propose_survivor_build_request(world, survivor) -> BuildingRequest | None:
    """Transforma a necessidade do morador em sugestao de chat, sem reservar obra no chao."""
    kind = world.desired_survivor_build_kind(survivor)
    if not kind:
        return None
    recipe = world.build_recipe_for(kind)
    survivor.build_request_cooldown = world.random.uniform(64.0, 92.0)
    wood_cost, scrap_cost = world.build_cost_for(kind)
    bark_text, reason = world.contextual_build_request_reason(survivor, kind)
    world.trigger_survivor_bark(survivor, bark_text, PALETTE["accent_soft"], duration=3.0)
    world.add_chat_message(
        survivor.name,
        f"acha que a base precisa de {str(recipe['label']).lower()} porque {reason}. Custo: {wood_cost} tabuas e {scrap_cost} sucata.",
        PALETTE["accent_soft"],
        source="npc",
    )
    world.set_event_message(f"{survivor.name} sugeriu {str(recipe['label']).lower()} no chat do acampamento.", duration=5.2)
    return None


def approve_build_request(world, request: BuildingRequest) -> tuple[bool, str]:
    """Confirma o pedido do morador e libera os recursos da obra."""
    if request not in world.build_requests:
        return False, "Esse pedido nao existe mais."
    if request.approved:
        return False, "Essa obra ja foi aprovada."
    world.build_requests.remove(request)
    if not world.is_valid_build_position(request.kind, request.pos):
        return False, "O ponto reservado foi perdido. O morador precisa planejar de novo."
    world.build_requests.append(request)
    wood_cost, scrap_cost = world.build_cost_for(request.kind)
    if world.wood < wood_cost or world.scrap < scrap_cost:
        return False, f"Faltam {wood_cost} tabuas e {scrap_cost} sucata para liberar essa obra."
    world.wood -= wood_cost
    world.scrap -= scrap_cost
    request.approved = True
    request.assigned_to = request.requester_name
    requester = next((survivor for survivor in world.survivors if survivor.name == request.requester_name and survivor.is_alive()), None)
    if requester:
        requester.decision_timer = 0.0
        requester.morale = clamp(requester.morale + 4.0, 0, 100)
        world.adjust_trust(requester, 2.4)
        world.trigger_survivor_bark(requester, "Boa. Eu mesmo levanto isso.", PALETTE["heal"], duration=2.8)
    world.add_chat_message("radio", f"Obra aprovada: {request.label.lower()} vai sair do papel.", PALETTE["heal"], source="system")
    world.set_event_message(f"Voce aprovou {request.label.lower()}. Agora a equipe vai levantar a estrutura.", duration=5.2)
    return True, f"{request.label} aprovada."


def complete_build_request(world, request: BuildingRequest) -> Building | None:
    """Transforma a obra aprovada em um predio pronto quando o trabalho acaba."""
    if request not in world.build_requests:
        return None
    world.build_requests.remove(request)
    if not world.is_valid_build_position(request.kind, request.pos):
        world.set_event_message(f"A obra de {request.label.lower()} perdeu espaco e foi cancelada.", duration=4.8)
        return None
    building = Building(
        uid=world.next_building_uid,
        kind=request.kind,
        pos=Vector2(request.pos),
        size=request.size,
    )
    world.next_building_uid += 1
    world.buildings.append(building)
    world.refresh_barricade_strength()
    world.assign_building_specialists()
    world.spawn_floating_text(request.label.lower(), request.pos, PALETTE["accent_soft"])
    world.emit_embers(request.pos, 6, smoky=True)
    world.set_event_message(f"{request.label} pronta na clareira.", duration=4.8)
    return building


def camp_sleep_slots(world) -> list[dict[str, object]]:
    slots: list[dict[str, object]] = []
    for index, tent in enumerate(world.tents):
        base_pos = Vector2(tent["pos"])
        angle = float(tent["angle"])
        scale = float(tent["scale"])
        facing = angle_to_vector(angle)
        slots.append(
            {
                "kind": "tent",
                "index": index,
                "building_uid": None,
                "pos": base_pos,
                "sleep_pos": base_pos - facing * (6 * scale),
                "interact_pos": base_pos + facing * (24 * scale),
                "radius": 20 + 8 * scale,
                "label": "barraca",
            }
        )
    for building in world.buildings:
        if building.kind != "barraca":
            continue
        for bed_index, x_offset in enumerate((-12, 12)):
            slots.append(
                {
                    "kind": "barraca",
                    "index": bed_index,
                    "building_uid": building.uid,
                    "pos": Vector2(building.pos),
                    "sleep_pos": Vector2(building.pos) + Vector2(x_offset, 4),
                    "interact_pos": Vector2(building.pos) + Vector2(0, 22),
                    "radius": building.size * 0.72,
                    "label": "barraca extra",
                }
            )
    return slots


def nearest_sleep_slot(world, pos: Vector2, max_distance: float = 82.0) -> dict[str, object] | None:
    candidates = []
    for slot in world.camp_sleep_slots():
        distance = Vector2(slot["interact_pos"]).distance_to(pos)
        if distance <= max_distance:
            candidates.append((distance, slot))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def total_bed_capacity(world) -> int:
    return len(world.camp_sleep_slots())


def expansion_cost(world) -> tuple[int, int]:
    base_logs = 8 + world.camp_level * 5
    base_scrap = 4 + world.camp_level * 3
    phase = world.economy_phase_key()
    multiplier = {
        "early": 1.0,
        "mid": 1.04,
        "late": 1.12,
    }[phase]
    return max(1, math.ceil(base_logs * multiplier)), max(1, math.ceil(base_scrap * multiplier))


def can_expand_camp(world) -> bool:
    log_cost, scrap_cost = world.expansion_cost()
    return world.camp_level < world.max_camp_level and world.logs >= log_cost and world.scrap >= scrap_cost


def spare_beds(world) -> int:
    return max(0, world.total_bed_capacity() - len(world.survivors))


def building_by_id(world, uid: int | None) -> Building | None:
    if uid is None:
        return None
    for building in world.buildings:
        if building.uid == uid:
            return building
    return None


def building_center_snapped(world, pos: Vector2) -> Vector2:
    rect = world.camp_rect(-36)
    grid = 32
    snapped_x = round((pos.x - CAMP_CENTER.x) / grid) * grid + CAMP_CENTER.x
    snapped_y = round((pos.y - CAMP_CENTER.y) / grid) * grid + CAMP_CENTER.y
    return Vector2(
        clamp(snapped_x, rect.left + 20, rect.right - 20),
        clamp(snapped_y, rect.top + 20, rect.bottom - 20),
    )


def placement_size_for(world, kind: str) -> float:
    return float(world.build_recipe_for(kind)["size"])


def build_placement_profile(world, kind: str) -> dict[str, float]:
    """Controla o quanto cada estrutura precisa respirar dentro da base."""
    profiles = {
        "barraca": {"edge": 10, "core": 26, "tent": 10, "building": 8, "wall": 16},
        "torre": {"edge": 12, "core": 34, "tent": 16, "building": 10, "wall": 12},
        "horta": {"edge": 10, "core": 22, "tent": 10, "building": 8, "wall": 14},
        "anexo": {"edge": 10, "core": 26, "tent": 12, "building": 10, "wall": 16},
        "serraria": {"edge": 12, "core": 28, "tent": 14, "building": 10, "wall": 16},
        "cozinha": {"edge": 12, "core": 28, "tent": 14, "building": 10, "wall": 16},
        "enfermaria": {"edge": 12, "core": 28, "tent": 14, "building": 10, "wall": 16},
    }
    return profiles.get(kind, {"edge": 12, "core": 28, "tent": 12, "building": 10, "wall": 16})


def placement_collision_radius(world, kind: str) -> float:
    """Aproxima o footprint real da estrutura para liberar mais espaco util."""
    return world.placement_size_for(kind) * 0.72


def is_valid_build_position(world, kind: str, pos: Vector2) -> bool:
    radius = world.placement_collision_radius(kind)
    profile = world.build_placement_profile(kind)
    if not world.point_in_camp_square(pos, padding=-(radius + profile["edge"])):
        return False
    core_positions = [
        world.bonfire_pos,
        world.stockpile_pos,
        world.kitchen_pos,
        world.workshop_pos,
        world.radio_pos,
    ]
    if any(pos.distance_to(core) < radius + profile["core"] for core in core_positions):
        return False
    if any(pos.distance_to(Vector2(tent["pos"])) < radius + profile["tent"] for tent in world.tents):
        return False
    if any(
        pos.distance_to(building.pos) < radius + building.size * 0.68 + profile["building"]
        for building in world.buildings
    ):
        return False
    if any(
        request.approved and pos.distance_to(request.pos) < radius + request.size * 0.68 + profile["building"]
        for request in world.build_requests
    ):
        return False
    if any(pos.distance_to(barricade.pos) < radius + profile["wall"] for barricade in world.barricades):
        return False
    return True


def player_building_reach(world, kind: str) -> float:
    return {
        "serraria": 110.0,
        "cozinha": 104.0,
        "horta": 98.0,
        "anexo": 106.0,
        "torre": 112.0,
        "enfermaria": 104.0,
    }.get(kind, 100.0)


def nearest_player_usable_building(world, pos: Vector2, max_distance: float = 116.0) -> Building | None:
    allowed = {"serraria", "cozinha", "horta", "anexo", "torre", "enfermaria"}
    candidates = [
        building
        for building in world.buildings
        if building.kind in allowed and building.pos.distance_to(pos) <= min(max_distance, world.player_building_reach(building.kind))
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda building: building.pos.distance_to(pos))


def player_building_prompt(world, building: Building, player) -> str:
    kind = building.kind
    if kind == "serraria":
        if world.logs >= 2:
            return "E usar serraria"
        return "Serraria sem toras"
    if kind == "cozinha":
        if world.food >= 2 and world.available_fuel() > 0:
            return "E cozinhar em lote"
        if world.available_fuel() <= 0:
            return "Cozinha sem combustivel"
        return "Cozinha sem insumos"
    if kind == "horta":
        if world.is_night:
            return "Horta descansando a noite"
        if not world.garden_is_ready(building):
            return "Horta crescendo"
        return "E colher horta"
    if kind == "anexo":
        weakest = world.weakest_barricade()
        if weakest and weakest.health < weakest.max_health and world.wood > 0:
            return "E montar kit de reparo"
        return "Anexo pronto para manutencao"
    if kind == "torre":
        if world.find_closest_zombie(building.pos, 250):
            return "E usar torre de vigia"
        return "Torre em vigia"
    if kind == "enfermaria":
        if world.has_medical_supplies() and player.health < player.max_health - 8:
            return "E tratar ferimentos"
        if world.herbs > 0 and world.scrap > 0:
            return "E preparar remedio"
        return "Enfermaria tranquila"
    return "E usar estrutura"


def use_building_as_player(world, building: Building, player) -> bool:
    kind = building.kind
    if kind == "serraria":
        if world.logs < 2:
            world.spawn_floating_text("faltam toras", building.pos, PALETTE["muted"])
            return False
        produced = world.sawmill_output("lenhador")
        if not world.consume_resource("logs", 2):
            return False
        stored = world.add_resource_bundle({"wood": produced})
        world.spawn_floating_text(world.bundle_summary(stored or {"wood": produced}), building.pos, PALETTE["accent_soft"])
        world.impact_burst(building.pos, PALETTE["accent_soft"], radius=12, shake=0.45, ember_count=3, smoky=True)
        world.set_event_message("A serraria mordeu as toras e soltou tabuas para a base.", duration=4.6)
        return True
    if kind == "cozinha":
        if world.food < 2:
            world.spawn_floating_text("faltam insumos", building.pos, PALETTE["muted"])
            return False
        if world.available_fuel() <= 0:
            world.spawn_floating_text("sem combustivel", building.pos, PALETTE["muted"])
            return False
        produced = world.cookhouse_output("cozinheiro")
        if not world.consume_resource("food", 2) or not world.consume_fuel(1):
            return False
        stored = world.add_resource_bundle({"meals": produced})
        world.spawn_floating_text(world.bundle_summary(stored or {"meals": produced}), building.pos, PALETTE["morale"])
        world.emit_embers(building.pos, 5)
        world.set_event_message("A cozinha encheu o ar com comida quente para a clareira.", duration=4.6)
        return True
    if kind == "horta":
        if world.is_night:
            world.spawn_floating_text("horta fechada", building.pos, PALETTE["muted"])
            return False
        if not world.garden_is_ready(building):
            world.spawn_floating_text("ainda crescendo", building.pos, PALETTE["muted"])
            return False
        bundle = world.garden_harvest_bundle("cozinheiro")
        stored = world.add_resource_bundle(bundle)
        world.start_garden_regrow(building)
        world.spawn_floating_text(world.bundle_summary(stored or bundle), building.pos, PALETTE["heal"])
        world.set_event_message("A horta rendeu um pouco de folego para o estoque.", duration=4.2)
        return True
    if kind == "anexo":
        weakest = world.weakest_barricade()
        if not weakest or weakest.health >= weakest.max_health or world.wood <= 0:
            world.spawn_floating_text("sem reparo urgente", building.pos, PALETTE["muted"])
            return False
        world.wood -= 1
        weakest.repair(world.workbench_repair_amount())
        world.spawn_floating_text("kit de reparo", weakest.pos, PALETTE["heal"])
        world.impact_burst(weakest.pos, PALETTE["heal"], radius=12, shake=0.55, ember_count=2, smoky=True)
        world.set_event_message("O anexo virou manutencao rapida na linha defensiva.", duration=4.4)
        return True
    if kind == "torre":
        zombie = world.find_closest_zombie(building.pos, 250)
        if not zombie:
            world.spawn_floating_text("sem alvo na mata", building.pos, PALETTE["muted"])
            return False
        zombie.health -= 28
        zombie.stagger = max(zombie.stagger, 0.18)
        world.damage_pulses.append(DamagePulse(Vector2(zombie.pos), 14, 0.24, PALETTE["accent_soft"]))
        world.spawn_floating_text("tiro da torre", building.pos, PALETTE["energy"])
        return True
    if kind == "enfermaria":
        if world.has_medical_supplies() and player.health < player.max_health - 8:
            if world.medicine > 0:
                world.medicine -= 1
                player.health = clamp(player.health + 26, 0, player.max_health)
                world.spawn_floating_text("curativo pesado", building.pos, PALETTE["heal"])
            elif world.herbs > 0:
                world.herbs -= 1
                player.health = clamp(player.health + 14, 0, player.max_health)
                world.spawn_floating_text("ervas medicinais", building.pos, PALETTE["heal"])
            return True
        if world.herbs > 0 and world.scrap > 0:
            world.herbs -= 1
            world.scrap -= 1
            produced = world.clinic_medicine_output()
            stored = world.add_resource_bundle({"medicine": produced})
            world.spawn_floating_text(world.bundle_summary(stored or {"medicine": produced}), building.pos, PALETTE["heal"])
            world.set_event_message("A enfermaria montou remedios de campo para a proxima crise.", duration=4.8)
            return True
        world.spawn_floating_text("sem uso imediato", building.pos, PALETTE["muted"])
        return False
    return False


def place_building(world, kind: str, pos: Vector2) -> bool:
    recipe = world.build_recipe_for(kind)
    snapped = world.building_center_snapped(pos)
    wood_cost, scrap_cost = world.build_cost_for(recipe)
    if world.wood < wood_cost or world.scrap < scrap_cost:
        world.set_event_message("Faltam recursos para essa construcao.", duration=3.4)
        return False
    if not world.is_valid_build_position(kind, snapped):
        world.set_event_message("Nao ha espaco livre nesse ponto do acampamento.", duration=3.4)
        return False

    world.wood -= wood_cost
    world.scrap -= scrap_cost
    world.buildings.append(
        Building(
            uid=world.next_building_uid,
            kind=kind,
            pos=snapped,
            size=float(recipe["size"]),
        )
    )
    world.next_building_uid += 1
    world.refresh_barricade_strength()
    world.assign_building_specialists()
    world.spawn_floating_text(str(recipe["label"]).lower(), snapped, PALETTE["accent_soft"])
    world.set_event_message(f"{recipe['label']} erguida na clareira.", duration=4.8)
    world.emit_embers(snapped, 6, smoky=True)
    return True


def refresh_barricade_strength(world) -> None:
    bonus_health = world.building_count("anexo") * 18
    bonus_tier = world.building_count("anexo")
    for barricade in world.barricades:
        ratio = 1.0 if barricade.max_health <= 0 else barricade.health / barricade.max_health
        spike_health = getattr(barricade, "spike_level", 0) * 18
        barricade.max_health = 110 + (1 + world.camp_level) * 28 + bonus_health + spike_health
        barricade.tier = 1 + world.camp_level + bonus_tier
        barricade.health = clamp(barricade.max_health * ratio, 0.0, barricade.max_health)


def barricade_upgrade_cost(world, barricade: Barricade) -> tuple[int, int]:
    level = getattr(barricade, "spike_level", 0)
    wood_cost = 2 + level * 2
    scrap_cost = 1 + level
    return wood_cost, scrap_cost


def can_upgrade_barricade(world, barricade: Barricade) -> bool:
    if getattr(barricade, "spike_level", 0) >= 3:
        return False
    wood_cost, scrap_cost = world.barricade_upgrade_cost(barricade)
    return world.wood >= wood_cost and world.scrap >= scrap_cost


def upgrade_barricade(world, barricade: Barricade) -> bool:
    if getattr(barricade, "spike_level", 0) >= 3:
        world.spawn_floating_text("spikes no limite", barricade.pos, PALETTE["muted"])
        return False
    wood_cost, scrap_cost = world.barricade_upgrade_cost(barricade)
    if world.wood < wood_cost or world.scrap < scrap_cost:
        world.spawn_floating_text(
            f"precisa {wood_cost} tabuas e {scrap_cost} sucata",
            barricade.pos,
            PALETTE["muted"],
        )
        return False
    ratio = 1.0 if barricade.max_health <= 0 else barricade.health / barricade.max_health
    world.wood -= wood_cost
    world.scrap -= scrap_cost
    barricade.spike_level = getattr(barricade, "spike_level", 0) + 1
    world.refresh_barricade_strength()
    barricade.health = clamp(max(barricade.health, barricade.max_health * ratio + 12), 0.0, barricade.max_health)
    world.spawn_floating_text(f"spikes nv {barricade.spike_level}", barricade.pos, PALETTE["accent_soft"])
    world.set_event_message("As defesas ganharam spikes mais agressivos.", duration=4.6)
    world.impact_burst(barricade.pos, PALETTE["accent_soft"], radius=13, shake=0.7, ember_count=3, smoky=True)
    return True


def workbench_repair_amount(world) -> float:
    phase_bonus = {
        "early": 0,
        "mid": 4,
        "late": 8,
    }[world.economy_phase_key()]
    return 18 + world.building_count("anexo") * 10 + phase_bonus


def can_use_workshop_saw(world) -> bool:
    """Libera a oficina inicial para cortar toras em tabuas antes da serraria."""
    return not world.buildings_of_kind("serraria") and world.logs > 0


def workshop_plank_bundle(world, role: str | None = None) -> dict[str, int]:
    """A oficina e lenta: serve para destravar o comeco, nao para substituir a serraria."""
    produced = 2
    if role in {"artesa", "lenhador"} and world.random.random() < 0.3:
        produced += 1
    return {"wood": produced}


def cut_planks_at_workshop(world, *, role: str | None = None) -> dict[str, int] | None:
    """Converte uma tora em poucas tabuas, sem a eficiencia de uma serraria real."""
    if not world.can_use_workshop_saw():
        return None
    if not world.consume_resource("logs", 1):
        return None
    bundle = world.workshop_plank_bundle(role)
    stored = world.add_resource_bundle(bundle)
    if not stored:
        world.logs += 1
        return None
    return stored


def buildings_of_kind(world, kind: str) -> list[Building]:
    return [building for building in world.buildings if building.kind == kind]


def nearest_building_of_kind(world, kind: str, pos: Vector2) -> Building | None:
    matches = world.buildings_of_kind(kind)
    if not matches:
        return None
    return min(matches, key=lambda building: building.pos.distance_to(pos))


def generate_tents(world) -> list[dict[str, Vector2 | float]]:
    base_offsets = [
        Vector2(-0.78, -0.5),
        Vector2(0.76, -0.5),
        Vector2(0.82, -0.06),
        Vector2(0.74, 0.38),
        Vector2(0.56, 0.72),
        Vector2(-0.56, 0.72),
        Vector2(-0.78, 0.36),
        Vector2(-0.82, -0.04),
    ]
    tents: list[dict[str, Vector2 | float]] = []
    initial_half_size = 214

    if hasattr(world, "tents") and len(getattr(world, "tents", [])) >= len(base_offsets):
        for tent in list(world.tents[: len(base_offsets)]):
            tents.append(
                {
                    "pos": Vector2(tent["pos"]),
                    "angle": float(tent["angle"]),
                    "scale": float(tent["scale"]),
                    "tone": float(tent["tone"]),
                }
            )
    else:
        for offset in base_offsets:
            pos = CAMP_CENTER + Vector2(offset.x * initial_half_size, offset.y * initial_half_size)
            facing = CAMP_CENTER - pos
            angle = math.atan2(facing.y, facing.x) if facing.length_squared() > 0 else 0.0
            tents.append(
                {
                    "pos": pos,
                    "angle": angle,
                    "scale": world.random.uniform(0.94, 1.14),
                    "tone": world.random.uniform(0.0, 1.0),
                }
            )
    return tents


def generate_barricades(world) -> list[Barricade]:
    barricades: list[Barricade] = []
    segments_per_side = 4 + world.camp_level
    half = world.camp_half_size + 24
    spacing = (half * 2) / segments_per_side
    span = spacing * 0.84
    tier = 1 + world.camp_level
    max_health = 110 + tier * 28
    for index in range(segments_per_side):
        offset = -half + spacing * (index + 0.5)
        barricades.append(Barricade(-math.pi / 2, CAMP_CENTER + Vector2(offset, -half), Vector2(1, 0), span=span, tier=tier, max_health=max_health, health=max_health))
        barricades.append(Barricade(0.0, CAMP_CENTER + Vector2(half, offset), Vector2(0, 1), span=span, tier=tier, max_health=max_health, health=max_health))
        barricades.append(Barricade(math.pi / 2, CAMP_CENTER + Vector2(-offset, half), Vector2(-1, 0), span=span, tier=tier, max_health=max_health, health=max_health))
        barricades.append(Barricade(math.pi, CAMP_CENTER + Vector2(-half, -offset), Vector2(0, -1), span=span, tier=tier, max_health=max_health, health=max_health))
    return barricades


def reflow_barricades_for_current_camp_size(world) -> None:
    """Redistribui os segmentos existentes ao redor do novo tamanho da base."""
    if not world.barricades:
        world.barricades = world.generate_barricades()
        return

    half = world.camp_half_size + 24
    side_map: dict[str, list[Barricade]] = {"top": [], "right": [], "bottom": [], "left": []}

    for barricade in world.barricades:
        angle = float(barricade.angle)
        if abs(angle - (-math.pi / 2)) < 0.01:
            side_map["top"].append(barricade)
        elif abs(angle - 0.0) < 0.01:
            side_map["right"].append(barricade)
        elif abs(angle - (math.pi / 2)) < 0.01:
            side_map["bottom"].append(barricade)
        else:
            side_map["left"].append(barricade)

    side_map["top"].sort(key=lambda barricade: barricade.pos.x)
    side_map["right"].sort(key=lambda barricade: barricade.pos.y)
    side_map["bottom"].sort(key=lambda barricade: barricade.pos.x, reverse=True)
    side_map["left"].sort(key=lambda barricade: barricade.pos.y, reverse=True)

    for side, group in side_map.items():
        if not group:
            continue
        spacing = (half * 2) / len(group)
        span = spacing * 0.84
        for index, barricade in enumerate(group):
            offset = -half + spacing * (index + 0.5)
            if side == "top":
                barricade.angle = -math.pi / 2
                barricade.tangent = Vector2(1, 0)
                barricade.pos = CAMP_CENTER + Vector2(offset, -half)
            elif side == "right":
                barricade.angle = 0.0
                barricade.tangent = Vector2(0, 1)
                barricade.pos = CAMP_CENTER + Vector2(half, offset)
            elif side == "bottom":
                barricade.angle = math.pi / 2
                barricade.tangent = Vector2(-1, 0)
                barricade.pos = CAMP_CENTER + Vector2(-offset, half)
            else:
                barricade.angle = math.pi
                barricade.tangent = Vector2(0, -1)
                barricade.pos = CAMP_CENTER + Vector2(-half, -offset)
            barricade.span = span


def expand_camp(world) -> bool:
    if not world.can_expand_camp():
        return False

    log_cost, scrap_cost = world.expansion_cost()
    world.logs -= log_cost
    world.scrap -= scrap_cost
    world.camp_level += 1
    world.layout_camp_core()
    world.path_network = world.generate_path_network()
    world.tents = world.generate_tents()
    world.reflow_barricades_for_current_camp_size()
    world.refresh_barricade_strength()
    world.sync_survivor_assignments()
    world.terrain_surface = world.build_terrain_surface()
    world.record_fog_reveal(CAMP_CENTER, world.camp_clearance_radius() + 120)
    world.set_event_message("A oficina abriu mais espaco e reforcou o quadrado do acampamento.", duration=7.0)
    world.spawn_floating_text("acampamento ampliado", world.workshop_pos, PALETTE["accent_soft"])
    world.emit_embers(world.workshop_pos, 10, smoky=True)
    return True









