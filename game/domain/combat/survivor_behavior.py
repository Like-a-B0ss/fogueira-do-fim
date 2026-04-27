from __future__ import annotations

import random
from typing import TYPE_CHECKING

from pygame import Vector2

from ...core.config import PALETTE, clamp
from ...core.models import Barricade, Building, DamagePulse, ResourceNode

if TYPE_CHECKING:
    from ...app.session import Game


STATE_LABELS = {
    "gather_wood": "coletando madeira",
    "forage": "forrageando",
    "scavenge": "buscando sucata",
    "repair": "reforcando palicadas",
    "cook": "organizando a cozinha",
    "cookhouse": "na cozinha",
    "socialize": "subindo a moral",
    "tend_fire": "cuidando do fogo",
    "roughcut": "cortando tábuas",
    "guard": "de vigia",
    "watchtower": "na torre",
    "garden": "cuidando da horta",
    "workbench": "na oficina",
    "sawmill": "na serraria",
    "clinic": "na enfermaria",
    "build_site": "levantando construção",
    "rest": "descansando",
    "sleep": "dormindo",
    "eat": "comendo",
    "treatment": "em tratamento",
    "shelter": "protegido na tenda",
    "defend": "segurando a linha",
    "deliver": "levando suprimentos",
    "wander": "rondando a base",
}


def has_trait(survivor, trait: str) -> bool:
    return trait in survivor.traits


def primary_trait(survivor) -> str:
    return survivor.traits[0] if survivor.traits else "estavel"


def update_survivor(survivor, game: "Game", dt: float) -> None:
    if not survivor.is_alive():
        return
    if game.is_survivor_on_expedition(survivor):
        survivor.state = "expedition"
        if survivor.expedition_downed:
            survivor.state_label = "caido na trilha"
        elif not survivor.state_label:
            survivor.state_label = "em expedição"
        survivor.velocity *= 0.0
        return

    _tick_survivor(survivor, dt)
    _update_memories(survivor, dt)
    _update_needs(survivor, game, dt)
    if _handle_defense(survivor, game, dt):
        return
    if _handle_crisis(survivor, game, dt):
        return

    if survivor.decision_timer <= 0:
        choose_next_task(survivor, game)
        survivor.decision_timer = random.uniform(2.8, 5.4)

    update_state(survivor, game, dt)


def choose_next_task(survivor, game: "Game") -> None:
    """Escolhe próxima tarefa usando chain-of-responsibility."""
    # Verificações em ordem de prioridade decrescente
    checks = [
        _check_critical_needs,
        _check_health_needs,
        _check_assigned_building_tasks,
        _check_essential_tasks,
        _check_rest_needs,
        _check_focus_override,
        _check_directives,
        _check_guard_duty,
        _choose_from_options,  # Fallback final
    ]
    
    # Executar verificações até uma retornar True (tarefa encontrada)
    for check in checks:
        if check(survivor, game):
            return


def _check_critical_needs(survivor, game: "Game") -> bool:
    """Verifica necessidades críticas: sono, insanidade extrema, exaustão."""
    if game.should_survivor_sleep(survivor):
        start_state(survivor, "sleep", survivor.home_pos)
        return True
    if survivor.insanity > 84:
        start_state(survivor, "wander", game.camp_perimeter_point(survivor.assigned_tent_index, jitter=42))
        return True
    if survivor.insanity > 70 and game.is_night:
        start_state(survivor, "guard", survivor.guard_pos)
        survivor.state_label = "rondando a base"
        return True
    if survivor.exhaustion > 80:
        start_state(survivor, "sleep" if game.is_night else "rest", survivor.home_pos)
        return True
    return False


def _check_health_needs(survivor, game: "Game") -> bool:
    """Verifica necessidades de saúde: doença, ferimentos."""
    if game.dynamic_event_for_survivor(survivor, "doenca") and game.can_treat_infirmary():
        infirmary = game.nearest_building_of_kind("enfermaria", survivor.pos)
        if infirmary:
            start_state(survivor, "treatment", infirmary.pos, infirmary)
            return True
    if survivor.health < 52 and game.can_treat_infirmary():
        infirmary = game.nearest_building_of_kind("enfermaria", survivor.pos)
        if infirmary:
            start_state(survivor, "treatment", infirmary.pos, infirmary)
            return True
    return False


def _check_assigned_building_tasks(survivor, game: "Game") -> bool:
    """Executa tarefas do edifício atribuído se possível."""
    # Propor construção se cooldown permitir
    if survivor.build_request_cooldown <= 0:
        game.propose_survivor_build_request(survivor)
    
    assigned_building = game.building_by_id(survivor.assigned_building_id)
    if not assigned_building:
        return False
    
    kind = survivor.assigned_building_kind
    
    # Tarefas por tipo de edifício
    if kind == "horta" and not game.is_night and survivor.energy > 28:
        start_state(survivor, "garden", assigned_building.pos, assigned_building)
        return True
    if kind == "anexo" and game.has_damaged_barricade() and survivor.energy > 28:
        start_state(survivor, "workbench", assigned_building.pos, assigned_building)
        return True
    if kind == "serraria" and game.logs >= 2 and survivor.energy > 28:
        start_state(survivor, "sawmill", assigned_building.pos, assigned_building)
        return True
    if kind == "cozinha" and game.food >= 2 and game.available_fuel() > 0 and survivor.energy > 26:
        start_state(survivor, "cookhouse", assigned_building.pos, assigned_building)
        return True
    if kind == "enfermaria" and (game.most_injured_actor() or game.herbs > 0) and survivor.energy > 24:
        start_state(survivor, "clinic", assigned_building.pos, assigned_building)
        return True
    
    return False


def _check_essential_tasks(survivor, game: "Game") -> bool:
    """Verifica tarefas essenciais: fogo, comida, reparos."""
    # Roughcut se sem serraria
    if not game.buildings_of_kind("serraria") and survivor.role in {"artesa", "lenhador"} and game.logs > 0 and survivor.energy > 28:
        start_state(survivor, "roughcut", game.workshop_pos)
        return True
    
    # Cuidar do fogo
    if game.available_fuel() > 0 and (
        (game.is_night and game.bonfire_heat < 38)
        or game.bonfire_ember_bed < 20
        or (game.focus_mode == "morale" and game.bonfire_heat < 60)
    ):
        start_state(survivor, "tend_fire", game.bonfire_pos)
        return True
    
    # Comer se muito faminto
    if survivor.hunger > 70 and (game.food > 0 or game.meals > 0):
        start_state(survivor, "eat", game.kitchen_pos)
        return True
    
    return False


def _check_rest_needs(survivor, game: "Game") -> bool:
    """Verifica se survivor precisa descansar."""
    if survivor.energy < 26 or survivor.health < 28 or survivor.exhaustion > 68:
        start_state(survivor, "rest", survivor.home_pos)
        return True
    return False


def _check_focus_override(survivor, game: "Game") -> bool:
    """Aplica override de foco do líder se houver."""
    focus_override = game.survivor_focus_override(survivor)
    if focus_override:
        _apply_focus_override(survivor, focus_override)
        return True
    return False


def _check_directives(survivor, game: "Game") -> bool:
    """Aplica diretivas se houver."""
    assigned_building = game.building_by_id(survivor.assigned_building_id)
    if _apply_directive(survivor, game, assigned_building):
        return True
    return False


def _check_guard_duty(survivor, game: "Game") -> bool:
    """Atribui guarda noturna ou sono."""
    if not game.is_night:
        return False
    
    assigned_building = game.building_by_id(survivor.assigned_building_id)
    if (
        assigned_building
        and survivor.assigned_building_kind == "torre"
        and survivor.name in game.active_guard_names()
        and survivor.energy > 22
    ):
        start_state(survivor, "watchtower", assigned_building.pos, assigned_building)
        return True
    if survivor.name in game.active_guard_names() and survivor.energy > 22:
        start_state(survivor, "guard", survivor.guard_pos)
        return True
    
    # Default noturno: dormir
    start_state(survivor, "sleep", survivor.home_pos)
    return True


def _choose_from_options(survivor, game: "Game") -> bool:
    """Fallback final: escolhe de opções disponíveis."""
    options = _task_options(survivor, game)
    choice = max(options.items(), key=lambda item: item[1] + random.uniform(-0.35, 0.35))[0]
    _apply_choice(survivor, game, choice)
    return True


def start_state(survivor, state: str, target: Vector2, ref: object | None = None) -> None:
    survivor.state = state
    survivor.target_pos = Vector2(target)
    survivor.target_ref = ref
    survivor.task_timer = 0.0
    survivor.state_label = STATE_LABELS.get(state, state)



# Dispatch padrão para atualização de estados - Eliminando if/elif chains
def _create_state_handlers():
    """Cria um dicionário de handlers para cada estado de survivor."""
    return {
        # Estados com (survivor, game, dt)
        "gather_wood": lambda s, g, dt: _update_resource_trip(s, g, dt),
        "forage": lambda s, g, dt: _update_resource_trip(s, g, dt),
        "scavenge": lambda s, g, dt: _update_resource_trip(s, g, dt),
        "deliver": lambda s, g, dt: _update_delivery(s, g, dt),
        "repair": lambda s, g, dt: _update_repair(s, g, dt),
        "cook": lambda s, g, dt: _update_cook(s, g, dt),
        "cookhouse": lambda s, g, dt: _update_cookhouse(s, g, dt),
        "socialize": lambda s, g, dt: _update_socialize(s, g, dt),
        "tend_fire": lambda s, g, dt: _update_tend_fire(s, g, dt),
        "watchtower": lambda s, g, dt: _update_watchtower(s, g, dt),
        "garden": lambda s, g, dt: _update_garden(s, g, dt),
        "workbench": lambda s, g, dt: _update_workbench(s, g, dt),
        "roughcut": lambda s, g, dt: _update_roughcut(s, g, dt),
        "sawmill": lambda s, g, dt: _update_sawmill(s, g, dt),
        "clinic": lambda s, g, dt: _update_clinic(s, g, dt),
        "treatment": lambda s, g, dt: _update_treatment(s, g, dt),
        "wander": lambda s, g, dt: _update_wander(s, g, dt),
        "eat": lambda s, g, dt: _update_eat(s, g, dt),
        # Estados com (survivor, dt)
        "sleep": lambda s, g, dt: _update_sleep(s, dt),
        "rest": lambda s, g, dt: _update_rest(s, dt),
        "shelter": lambda s, g, dt: _update_shelter(s, dt),
        # Guard com lógica simples
        "guard": lambda s, g, dt: s.move_toward(s.guard_pos, dt),
    }

_STATE_HANDLERS = _create_state_handlers()


def update_state(survivor, game: "Game", dt: float) -> None:
    """Atualiza estado do survivor usando dispatch pattern."""
    handler = _STATE_HANDLERS.get(survivor.state)
    if handler:
        handler(survivor, game, dt)
    else:
        # Estados desconhecidos zeramtimer
        survivor.decision_timer = 0


def _tick_survivor(survivor, dt: float) -> None:
    survivor.attack_cooldown = max(0.0, survivor.attack_cooldown - dt)
    survivor.decision_timer -= dt
    survivor.blink += dt * 3.0
    survivor.conflict_cooldown = max(0.0, survivor.conflict_cooldown - dt)
    survivor.bond_cooldown = max(0.0, survivor.bond_cooldown - dt)
    survivor.bark_timer = max(0.0, survivor.bark_timer - dt)
    survivor.bark_cooldown = max(0.0, survivor.bark_cooldown - dt)
    survivor.leader_directive_timer = max(0.0, survivor.leader_directive_timer - dt)
    survivor.build_request_cooldown = max(0.0, survivor.build_request_cooldown - dt)
    survivor.social_comment_cooldown = max(0.0, survivor.social_comment_cooldown - dt)
    if survivor.leader_directive_timer <= 0:
        survivor.leader_directive = None


def _update_memories(survivor, dt: float) -> None:
    kept_memories: list[dict[str, object]] = []
    for memory in survivor.social_memories:
        updated = dict(memory)
        updated["timer"] = max(0.0, float(updated.get("timer", 0.0)) - dt)
        if float(updated.get("timer", 0.0)) > 0.0:
            kept_memories.append(updated)
    survivor.social_memories = kept_memories[-8:]


def _update_needs(survivor, game: "Game", dt: float) -> None:
    hunger_rate = 1.9 if game.is_night else 1.2
    survivor.hunger = clamp(survivor.hunger + hunger_rate * dt, 0, 100)
    effort_states = {"gather_wood", "forage", "scavenge", "repair", "sawmill", "workbench", "guard", "watchtower"}
    effort_load = 0.38 if survivor.state in effort_states else 0.0
    if has_trait(survivor, "resiliente"):
        effort_load *= 0.78
    if has_trait(survivor, "teimoso"):
        effort_load *= 1.12

    exhaustion_delta = (0.34 if game.is_night else 0.16) + survivor.sleep_debt * 0.004 + effort_load
    if survivor.state in {"sleep", "rest", "treatment"}:
        exhaustion_delta -= 1.05
    elif survivor.state in {"socialize", "eat", "shelter"}:
        exhaustion_delta -= 0.24
    survivor.exhaustion = clamp(survivor.exhaustion + exhaustion_delta * dt, 0, 100)

    energy_drain = (0.62 if game.is_night else 0.34) + survivor.sleep_debt * 0.003 + survivor.exhaustion * 0.0042
    survivor.energy = clamp(survivor.energy - energy_drain * dt, 0, 100)
    if survivor.state in {"sleep", "rest", "shelter"} and survivor.distance_to(survivor.home_pos) < 28:
        survivor.sleep_debt = clamp(survivor.sleep_debt - 2.6 * dt, 0, 100)
    elif game.is_night:
        survivor.sleep_debt = clamp(survivor.sleep_debt + 0.85 * dt, 0, 100)
    else:
        survivor.sleep_debt = clamp(survivor.sleep_debt - 0.18 * dt, 0, 100)

    bonfire_safety = game.bonfire_heat * 0.6 + game.bonfire_ember_bed * 0.4
    if game.is_night and bonfire_safety < 22 and survivor.distance_to(game.bonfire_pos) > 180:
        survivor.morale = clamp(survivor.morale - 0.7 * dt, 0, 100)
    else:
        survivor.morale = clamp(survivor.morale - 0.18 * dt, 0, 100)

    insanity_delta = 0.0
    if game.is_night:
        insanity_delta += 0.16
    if bonfire_safety < 22:
        insanity_delta += 0.12
    if survivor.exhaustion > 70:
        insanity_delta += 0.2
    if survivor.morale < 42:
        insanity_delta += 0.18
    if has_trait(survivor, "paranoico"):
        insanity_delta += 0.16
    if has_trait(survivor, "gentil"):
        insanity_delta -= 0.05
    if survivor.state in {"sleep", "rest", "socialize", "eat"}:
        insanity_delta -= 0.18
    if survivor.distance_to(game.player.pos) < 160:
        insanity_delta -= 0.08
    if game.find_closest_zombie(survivor.pos, 180):
        insanity_delta += 0.2
    survivor.insanity = clamp(survivor.insanity + insanity_delta * dt, 0, 100)

    if survivor.health <= 30:
        survivor.morale = clamp(survivor.morale - 0.25 * dt, 0, 100)
    if survivor.exhaustion > 72:
        survivor.morale = clamp(survivor.morale - 0.22 * dt, 0, 100)
        survivor.trust_leader = clamp(survivor.trust_leader - 0.1 * dt, 0, 100)
    elif has_trait(survivor, "leal") and game.player.distance_to(survivor.pos) < 180:
        survivor.trust_leader = clamp(survivor.trust_leader + 0.08 * dt, 0, 100)


def _handle_defense(survivor, game: "Game", dt: float) -> bool:
    defense_target = game.closest_defense_target(survivor)
    assigned_building = game.building_by_id(survivor.assigned_building_id)
    if not defense_target:
        return False

    if game.survivor_should_seek_shelter(survivor, defense_target):
        survivor.state = "shelter"
        survivor.state_label = "se abrigando"
        shelter_anchor = (
            game.bonfire_pos
            if survivor.distance_to(game.bonfire_pos) < survivor.distance_to(survivor.home_pos) + 26
            else survivor.home_pos
        )
        survivor.target_pos = Vector2(shelter_anchor)
        survivor.move_toward(Vector2(shelter_anchor), dt, 1.08)
        return True

    if (
        assigned_building
        and survivor.assigned_building_kind == "torre"
        and survivor.name in game.active_guard_names()
        and defense_target.pos.distance_to(assigned_building.pos) < 260
    ):
        if survivor.state != "watchtower" or survivor.target_ref is not assigned_building:
            start_state(survivor, "watchtower", assigned_building.pos, assigned_building)
        update_state(survivor, game, dt)
        return True

    if not game.survivor_should_engage(survivor, defense_target):
        return False

    survivor.state = "defend"
    survivor.state_label = "segurando a linha"
    survivor.target_pos = Vector2(defense_target.pos)
    if survivor.distance_to(defense_target.pos) > 74:
        survivor.move_toward(defense_target.pos, dt, 1.04 if survivor.role == "vigia" else 0.96)
    elif survivor.attack_cooldown <= 0:
        defense_target.health -= game.survivor_attack_damage(survivor)
        defense_target.stagger = 0.14 if survivor.role == "vigia" else 0.1
        survivor.attack_cooldown = 0.72 if survivor.role == "vigia" else 0.92
        game.impact_burst(defense_target.pos, PALETTE["accent_soft"], radius=10, shake=0.85, ember_count=1)
        game.damage_pulses.append(DamagePulse(Vector2(defense_target.pos), 10, 0.22, PALETTE["accent_soft"]))
        game.audio.play_impact("flesh", source_pos=defense_target.pos)
    return True


def _handle_crisis(survivor, game: "Game", dt: float) -> bool:
    crisis = game.dynamic_event_for_survivor(survivor)
    if crisis and crisis.kind in {"fuga", "desercao"}:
        survivor.state_label = "em fuga" if crisis.kind == "fuga" else "desertando"
        survivor.move_toward(crisis.pos, dt, 1.12 if crisis.kind == "desercao" else 1.04)
        survivor.energy = clamp(survivor.energy - 0.35 * dt, 0, 100)
        survivor.morale = clamp(survivor.morale - 0.18 * dt, 0, 100)
        return True
    if crisis and crisis.kind == "doenca":
        survivor.state_label = "febril"
        survivor.health = clamp(survivor.health - 0.15 * dt, 0, survivor.max_health)
        survivor.energy = clamp(survivor.energy - 0.2 * dt, 0, 100)
        survivor.morale = clamp(survivor.morale - 0.08 * dt, 0, 100)
    return False


def _apply_focus_override(survivor, focus_override: tuple[str, object | None]) -> None:
    override_state, override_ref = focus_override
    if isinstance(override_ref, Building):
        start_state(survivor, override_state, override_ref.pos, override_ref)
    elif isinstance(override_ref, Barricade):
        start_state(survivor, override_state, override_ref.pos, override_ref)
    elif isinstance(override_ref, Vector2):
        start_state(survivor, override_state, override_ref)
    elif override_ref is not None and hasattr(override_ref, "pos"):
        start_state(survivor, override_state, override_ref.pos, override_ref)
    else:
        start_state(survivor, override_state, survivor.pos)


def _apply_directive(survivor, game: "Game", assigned_building) -> bool:
    directive = survivor.leader_directive if survivor.leader_directive_timer > 0 else None
    if directive == "rest":
        start_state(survivor, "sleep" if game.is_night else "rest", survivor.home_pos)
        return True
    if directive == "guard" and survivor.energy > 18:
        if assigned_building and survivor.assigned_building_kind == "torre":
            start_state(survivor, "watchtower", assigned_building.pos, assigned_building)
        else:
            start_state(survivor, "guard", survivor.guard_pos)
        return True
    if directive == "wood":
        node = game.closest_available_node("wood", survivor.pos)
        if node:
            target_pos = Vector2(node["pos"]) if isinstance(node, dict) else node.pos
            start_state(survivor, "gather_wood", target_pos, node)
            return True
    if directive == "food":
        node = game.closest_available_node("food", survivor.pos)
        if node:
            start_state(survivor, "forage", node.pos, node)
            return True
    if directive == "repair" and game.has_damaged_barricade() and game.wood > 0:
        barricade = game.weakest_barricade()
        if barricade:
            start_state(survivor, "repair", barricade.pos, barricade)
            return True
    if directive == "cook":
        if assigned_building and survivor.assigned_building_kind == "cozinha" and game.food >= 2 and game.available_fuel() > 0:
            start_state(survivor, "cookhouse", assigned_building.pos, assigned_building)
            return True
        if game.food >= 1 and game.available_fuel() > 0:
            start_state(survivor, "cook", game.kitchen_pos)
            return True
    if directive == "clinic":
        infirmary = game.nearest_building_of_kind("enfermaria", survivor.pos)
        if infirmary and (game.most_injured_actor() or game.herbs > 0):
            start_state(survivor, "clinic", infirmary.pos, infirmary)
            return True
    if directive == "fire" and game.available_fuel() > 0:
        start_state(survivor, "tend_fire", game.bonfire_pos)
        return True
    return False


def _task_options(survivor, game: "Game") -> dict[str, float]:
    options = {
        "gather_wood": 1.0 if game.available_node("wood") else -999,
        "forage": 1.0 if game.available_node("food") else -999,
        "scavenge": 0.8 if game.available_node("scrap") else -999,
        "repair": 0.7 if game.has_damaged_barricade() and game.wood > 0 else -999,
        "cook": 0.6 if game.food > 0 and game.available_fuel() > 0 else -999,
        "sawmill": 0.7 if game.logs >= 2 else -999,
        "roughcut": 0.55 if not game.buildings_of_kind("serraria") and game.logs > 0 else -999,
        "clinic": 0.6 if game.most_injured_actor() and game.has_medical_supplies() else -999,
        "tend_fire": 0.5 if game.available_fuel() > 0 else -999,
        "socialize": 0.5,
        "guard": 0.3,
    }

    # Bonificadores por escassez de recursos
    _apply_resource_bonuses(options, game)
    
    # Bonificadores por necessidades do grupo
    _apply_group_need_bonuses(options, game)
    
    # Bonificadores por exaustão
    if survivor.exhaustion > 58:
        for task in ["socialize", "guard", "gather_wood", "repair", "sawmill"]:
            options[task] -= [0.8, 0.8, 1.2, 1.0, 0.9][["socialize", "guard", "gather_wood", "repair", "sawmill"].index(task)]

    # Aplicar ajustes por modo de foco
    _apply_focus_mode_bonuses(options, survivor, game)
    
    # Aplicar ajustes por traits
    _apply_trait_bonuses(options, survivor, game)
    
    # Ajuste por role preferido
    preferred = {
        "lenhador": "gather_wood",
        "vigia": "guard",
        "batedora": "forage",
        "artesa": "repair",
        "cozinheiro": "cook",
        "mensageiro": "clinic",
    }.get(survivor.role, "socialize")
    options[preferred] = options.get(preferred, 0) + 2.1
    
    return options


def _apply_resource_bonuses(options: dict[str, float], game: "Game") -> None:
    """Ajusta prioridades baseado em escassez de recursos."""
    resource_thresholds = [
        ("logs", 12, ["gather_wood"], [2.6]),
        ("wood", 14, ["sawmill", "roughcut"], [2.5, 2.2]),
        ("food", 14, ["forage"], [2.4]),
        ("meals", 8, ["cook"], [2.2]),
        ("scrap", 8, ["scavenge"], [1.7]),
    ]
    
    for resource, threshold, tasks, bonuses in resource_thresholds:
        if hasattr(game, resource) and getattr(game, resource) < threshold:
            for task, bonus in zip(tasks, bonuses):
                options[task] = options.get(task, 0) + bonus


def _apply_group_need_bonuses(options: dict[str, float], game: "Game") -> None:
    """Ajusta prioridades baseado nas necessidades do grupo."""
    if game.weakest_barricade_health() < 60:
        options["repair"] = options.get("repair", 0) + 2.9
    if game.average_morale() < 56:
        options["cook"] = options.get("cook", 0) + 1.4
        options["socialize"] = options.get("socialize", 0) + 2.2
    if game.average_health() < 72:
        options["clinic"] = options.get("clinic", 0) + 2.3
    if game.bonfire_heat < 34:
        options["tend_fire"] = options.get("tend_fire", 0) + 3.2
    elif game.bonfire_ember_bed < 20:
        options["tend_fire"] = options.get("tend_fire", 0) + 2.1


def _apply_focus_mode_bonuses(options: dict[str, float], survivor, game: "Game") -> None:
    """Aplicar bonificadores baseado no modo de foco."""
    command_factor = 0.45 + survivor.trust_leader / 100
    if has_trait(survivor, "leal"):
        command_factor += 0.18
    if has_trait(survivor, "teimoso"):
        command_factor -= 0.1

    focus_bonuses = {
        "supply": {
            "gather_wood": 2.4 * command_factor,
            "forage": 2.2 * command_factor,
            "scavenge": 2.0 * command_factor,
            "sawmill": 1.8 * command_factor,
            "cook": 1.1 * command_factor,
        },
        "fortify": {
            "repair": 3.0 * command_factor,
            "guard": 1.5 * command_factor,
        },
        "morale": {
            "cook": 2.5 * command_factor,
            "tend_fire": 2.8 * command_factor,
            "socialize": 2.8 * command_factor,
            "clinic": 1.4 * command_factor,
        },
    }

    for task, bonus in focus_bonuses.get(game.focus_mode, {}).items():
        options[task] = options.get(task, 0) + bonus


def _apply_trait_bonuses(options: dict[str, float], survivor, game: "Game") -> None:
    """Aplicar bonificadores baseado em traits."""
    trait_bonuses = {
        "corajoso": {"guard": 1.9},
        "sociavel": {"socialize": 2.3, "cook": 0.8},
        "paranoico": {"guard": 1.6, "socialize": -1.4},
        "gentil": {"clinic": 1.7, "cook": 0.9},
        "rancoroso": {"socialize": -1.8, "guard": 0.6},
        "teimoso": {"repair": 1.3, "gather_wood": 0.9},
    }

    for trait, bonuses in trait_bonuses.items():
        if has_trait(survivor, trait):
            for task, bonus in bonuses.items():
                options[task] = options.get(task, 0) + bonus
    
    # Regra especial para artesã/lenhador sem serraria
    if survivor.role in {"artesa", "lenhador"} and not game.buildings_of_kind("serraria"):
        options["roughcut"] = options.get("roughcut", 0) + 1.6


def _apply_choice(survivor, game: "Game", choice: str) -> None:
    """Aplica escolha de tarefa usando dispatch pattern."""
    # Handlers para cada choice - retornam True se a tarefa foi iniciada
    handlers = {
        "gather_wood": lambda: _handle_gather_wood(survivor, game),
        "forage": lambda: _handle_forage(survivor, game),
        "scavenge": lambda: _handle_scavenge(survivor, game),
        "repair": lambda: _handle_repair(survivor, game),
        "cook": lambda: (start_state(survivor, "cook", game.kitchen_pos), True)[1],
        "sawmill": lambda: _handle_sawmill(survivor, game),
        "roughcut": lambda: (start_state(survivor, "roughcut", game.workshop_pos), True)[1],
        "clinic": lambda: _handle_clinic(survivor, game),
        "tend_fire": lambda: (start_state(survivor, "tend_fire", game.bonfire_pos), True)[1],
        "guard": lambda: (start_state(survivor, "guard", survivor.guard_pos), True)[1],
    }
    
    # Tentar handler específico, senão socializar
    if choice in handlers:
        handlers[choice]()
    else:
        start_state(survivor, "socialize", game.bonfire_pos)


def _handle_gather_wood(survivor, game: "Game") -> bool:
    """Handle gather_wood choice."""
    node = game.closest_available_node("wood", survivor.pos)
    if node:
        target_pos = Vector2(node["pos"]) if isinstance(node, dict) else node.pos
        start_state(survivor, "gather_wood", target_pos, node)
        return True
    return False


def _handle_forage(survivor, game: "Game") -> bool:
    """Handle forage choice."""
    node = game.closest_available_node("food", survivor.pos)
    if node:
        start_state(survivor, "forage", node.pos, node)
        return True
    return False


def _handle_scavenge(survivor, game: "Game") -> bool:
    """Handle scavenge choice."""
    node = game.closest_available_node("scrap", survivor.pos)
    if node:
        start_state(survivor, "scavenge", node.pos, node)
        return True
    return False


def _handle_repair(survivor, game: "Game") -> bool:
    """Handle repair choice."""
    barricade = game.weakest_barricade()
    if barricade:
        start_state(survivor, "repair", barricade.pos, barricade)
        return True
    return False


def _handle_sawmill(survivor, game: "Game") -> bool:
    """Handle sawmill choice."""
    sawmill = game.nearest_building_of_kind("serraria", survivor.pos)
    if sawmill:
        start_state(survivor, "sawmill", sawmill.pos, sawmill)
        return True
    return False


def _handle_clinic(survivor, game: "Game") -> bool:
    """Handle clinic choice."""
    infirmary = game.nearest_building_of_kind("enfermaria", survivor.pos)
    if infirmary:
        start_state(survivor, "clinic", infirmary.pos, infirmary)
        return True
    return False


def _update_resource_trip(survivor, game: "Game", dt: float) -> None:
    if not survivor.move_toward(survivor.target_pos, dt):
        return
    if survivor.state == "gather_wood":
        tree = survivor.target_ref if isinstance(survivor.target_ref, dict) else None
        if not tree or not game.tree_is_harvestable(tree):
            survivor.decision_timer = 0
            return
        survivor.task_timer += dt
        if survivor.task_timer >= 4.2:
            amount = game.harvest_tree(tree, effort=2)
            if amount:
                survivor.carry_bundle = {"logs": amount}
                start_state(survivor, "deliver", game.stockpile_pos)
                survivor.state_label = "arrastando toras"
                if survivor.distance_to(game.player.pos) < 135:
                    game.audio.play_impact("wood", source_pos=tree["pos"])
            else:
                survivor.task_timer = 0.0
                survivor.state_label = "derrubando a árvore"
        return

    node = survivor.target_ref if isinstance(survivor.target_ref, ResourceNode) else None
    if not node or not node.is_available():
        survivor.decision_timer = 0
        return
    survivor.task_timer += dt
    if survivor.task_timer >= 3.2:
        amount = node.harvest()
        if amount:
            survivor.carry_bundle = game.resource_node_bundle(node, role=survivor.role)
            start_state(survivor, "deliver", game.stockpile_pos)
            survivor.state_label = "carregando suprimentos"
        else:
            survivor.decision_timer = 0


def _update_delivery(survivor, game: "Game", dt: float) -> None:
    if survivor.move_toward(survivor.target_pos, dt, 1.1):
        stored = game.add_resource_bundle(survivor.carry_bundle)
        game.spawn_floating_text(game.bundle_summary(stored or survivor.carry_bundle), survivor.pos, PALETTE["accent_soft"])
        survivor.carry_bundle = {}
        survivor.decision_timer = 0


def _update_repair(survivor, game: "Game", dt: float) -> None:
    barricade = survivor.target_ref if isinstance(survivor.target_ref, Barricade) else None
    if not barricade or game.wood <= 0:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(barricade.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 2.4:
            game.wood -= 1
            barricade.repair(18)
            game.spawn_floating_text("palicada arrumada", barricade.pos, PALETTE["heal"])
            survivor.task_timer = 0
            survivor.decision_timer = 0.4


def _update_cook(survivor, game: "Game", dt: float) -> None:
    if survivor.move_toward(game.kitchen_pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 3.3 and game.food > 0 and game.available_fuel() > 0:
            game.food -= 1
            game.consume_fuel(1)
            game.add_resource_bundle({"meals": 1})
            for other in game.survivors:
                other.morale = clamp(other.morale + 2.5, 0, 100)
            game.spawn_floating_text("refeicao pronta", game.kitchen_pos, PALETTE["morale"])
            survivor.task_timer = 0
            survivor.decision_timer = 1.2


def _update_cookhouse(survivor, game: "Game", dt: float) -> None:
    kitchen = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    if not kitchen or game.food < 2 or game.available_fuel() <= 0:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(kitchen.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 3.8:
            produced = game.cookhouse_output(survivor.role)
            if game.consume_resource("food", 2) and game.consume_fuel(1):
                game.add_resource_bundle({"meals": produced})
                for other in game.survivors:
                    other.morale = clamp(other.morale + 3.0, 0, 100)
                game.spawn_floating_text(f"+{produced} refeicoes", kitchen.pos, PALETTE["morale"])
                survivor.task_timer = 0.2
                survivor.decision_timer = 1.0


def _update_socialize(survivor, game: "Game", dt: float) -> None:
    if survivor.move_toward(game.bonfire_pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 3.6:
            for other in game.survivors:
                if other.distance_to(game.bonfire_pos) < 200:
                    other.morale = clamp(other.morale + 2.6, 0, 100)
                    if other.is_alive():
                        game.adjust_relationship(survivor, other, 2.4 if has_trait(survivor, "sociavel") else 1.4)
            game.spawn_floating_text("historia no fogo", game.bonfire_pos, PALETTE["morale"])
            survivor.task_timer = 0.2


def _update_tend_fire(survivor, game: "Game", dt: float) -> None:
    if game.available_fuel() <= 0:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(game.bonfire_pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 2.0:
            fed, label, color = game.add_fuel_to_bonfire()
            if fed:
                game.spawn_floating_text(label, game.bonfire_pos, color)
                for other in game.survivors:
                    if other.distance_to(game.bonfire_pos) < 160:
                        other.morale = clamp(other.morale + 1.6, 0, 100)
                game.emit_embers(game.bonfire_pos, 8)
                game.audio.play_interact(source_pos=game.bonfire_pos)
            survivor.task_timer = 0.0
            survivor.decision_timer = 2.4


def _update_watchtower(survivor, game: "Game", dt: float) -> None:
    tower = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    if not tower:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(tower.pos, dt):
        zombie = game.find_closest_zombie(tower.pos, 240)
        if zombie and survivor.attack_cooldown <= 0:
            zombie.health -= 22
            zombie.stagger = 0.15
            survivor.attack_cooldown = 0.95
            game.damage_pulses.append(DamagePulse(Vector2(zombie.pos), 12, 0.22, PALETTE["accent_soft"]))
            game.spawn_floating_text("vigia", tower.pos, PALETTE["energy"])
            game.audio.play_impact("body", source_pos=tower.pos)


def _update_garden(survivor, game: "Game", dt: float) -> None:
    garden = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    if not garden:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(garden.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 4.8:
            if not game.garden_is_ready(garden):
                survivor.task_timer = 0.0
                survivor.decision_timer = 0
                return
            bundle = game.garden_harvest_bundle(survivor.role)
            game.add_resource_bundle(bundle)
            game.start_garden_regrow(garden)
            game.spawn_floating_text("colheita", garden.pos, PALETTE["heal"])
            survivor.task_timer = 0.6
            survivor.decision_timer = 1.8


def _update_workbench(survivor, game: "Game", dt: float) -> None:
    workshop = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    weakest = game.weakest_barricade()
    if not workshop or not weakest or game.wood <= 0:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(workshop.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 4.0:
            game.wood -= 1
            if game.scrap > 0:
                game.scrap -= 1
                weakest.repair(game.workbench_repair_amount())
            else:
                weakest.repair(game.workbench_repair_amount() * 0.7)
            game.spawn_floating_text("kit de reparo", weakest.pos, PALETTE["heal"])
            game.audio.play_interact("repair", source_pos=workshop.pos)
            survivor.task_timer = 0.0
            survivor.decision_timer = 1.2


def _update_roughcut(survivor, game: "Game", dt: float) -> None:
    if not game.can_use_workshop_saw():
        survivor.decision_timer = 0
        return
    if survivor.move_toward(game.workshop_pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 4.8:
            stored = game.cut_planks_at_workshop(role=survivor.role)
            if stored:
                game.spawn_floating_text(game.bundle_summary(stored), game.workshop_pos, PALETTE["accent_soft"])
                game.audio.play_interact("repair", source_pos=game.workshop_pos)
            survivor.task_timer = 0.0
            survivor.decision_timer = 1.0


def _update_sawmill(survivor, game: "Game", dt: float) -> None:
    sawmill = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    if not sawmill or game.logs < 2:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(sawmill.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 4.0:
            produced = game.sawmill_output(survivor.role)
            if game.consume_resource("logs", 2):
                game.add_resource_bundle({"wood": produced})
                game.spawn_floating_text(f"+{produced} tábuas", sawmill.pos, PALETTE["accent_soft"])
                game.audio.play_interact("repair", source_pos=sawmill.pos)
                survivor.task_timer = 0.0
                survivor.decision_timer = 1.0


def _update_clinic(survivor, game: "Game", dt: float) -> None:
    infirmary = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    if not infirmary:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(infirmary.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 3.6:
            target = game.most_injured_actor()
            if target and game.medicine > 0:
                game.medicine -= 1
                target.health = clamp(target.health + 24, 0, target.max_health)
                if _is_survivor(target):
                    target.morale = clamp(target.morale + 3, 0, 100)
                game.spawn_floating_text("tratamento", infirmary.pos, PALETTE["heal"])
                game.audio.play_interact("repair", source_pos=infirmary.pos)
            elif target and game.herbs > 0:
                game.herbs -= 1
                target.health = clamp(target.health + 14, 0, target.max_health)
                game.spawn_floating_text("ervas", infirmary.pos, PALETTE["heal"])
                game.audio.play_interact("repair", source_pos=infirmary.pos)
            elif game.herbs > 0 and game.scrap > 0:
                game.herbs -= 1
                game.scrap -= 1
                produced = game.clinic_medicine_output()
                game.add_resource_bundle({"medicine": produced})
                game.spawn_floating_text(f"+{produced} remédio", infirmary.pos, PALETTE["heal"])
                game.audio.play_interact("repair", source_pos=infirmary.pos)
            survivor.task_timer = 0.0
            survivor.decision_timer = 1.2


def _update_treatment(survivor, game: "Game", dt: float) -> None:
    infirmary = survivor.target_ref if isinstance(survivor.target_ref, Building) else None
    if not infirmary:
        survivor.decision_timer = 0
        return
    if survivor.move_toward(infirmary.pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 2.6:
            if game.medicine > 0:
                game.medicine -= 1
                survivor.health = clamp(survivor.health + 20, 0, survivor.max_health)
            elif game.herbs > 0:
                game.herbs -= 1
                survivor.health = clamp(survivor.health + 12, 0, survivor.max_health)
            survivor.energy = clamp(survivor.energy + 6, 0, 100)
            survivor.morale = clamp(survivor.morale + 3, 0, 100)
            game.audio.play_interact("repair", source_pos=infirmary.pos)
            survivor.decision_timer = 0


def _update_wander(survivor, game: "Game", dt: float) -> None:
    if survivor.move_toward(survivor.target_pos, dt, 0.92):
        survivor.morale = clamp(survivor.morale - 0.4 * dt, 0, 100)
        if survivor.task_timer <= 0:
            survivor.target_pos = game.camp_perimeter_point(survivor.assigned_tent_index + random.randint(0, 3), jitter=58)
            survivor.task_timer = 2.4
        else:
            survivor.task_timer = max(0.0, survivor.task_timer - dt)
        if survivor.insanity < 58:
            survivor.decision_timer = 0


def _update_sleep(survivor, dt: float) -> None:
    if survivor.move_toward(survivor.home_pos, dt):
        survivor.energy = clamp(survivor.energy + 24 * dt, 0, 100)
        survivor.health = clamp(survivor.health + 5 * dt, 0, survivor.max_health)
        survivor.morale = clamp(survivor.morale + 1.4 * dt, 0, 100)
        survivor.exhaustion = clamp(survivor.exhaustion - 22 * dt, 0, 100)
        if survivor.energy >= 84 and survivor.sleep_debt <= 12:
            survivor.decision_timer = 0


def _update_rest(survivor, dt: float) -> None:
    if survivor.move_toward(survivor.home_pos, dt):
        survivor.energy = clamp(survivor.energy + 18 * dt, 0, 100)
        survivor.health = clamp(survivor.health + 6 * dt, 0, survivor.max_health)
        survivor.morale = clamp(survivor.morale + 2 * dt, 0, 100)
        survivor.exhaustion = clamp(survivor.exhaustion - 14 * dt, 0, 100)
        if survivor.energy >= 72:
            survivor.decision_timer = 0


def _update_eat(survivor, game: "Game", dt: float) -> None:
    if survivor.move_toward(game.kitchen_pos, dt):
        survivor.task_timer += dt
        if survivor.task_timer >= 1.4:
            if game.meals > 0:
                game.meals -= 1
                survivor.hunger = clamp(survivor.hunger - 42, 0, 100)
            elif game.food > 0:
                game.food -= 1
                survivor.hunger = clamp(survivor.hunger - 25, 0, 100)
            survivor.energy = clamp(survivor.energy + 6, 0, 100)
            survivor.morale = clamp(survivor.morale + 4, 0, 100)
            survivor.exhaustion = clamp(survivor.exhaustion - 5, 0, 100)
            if survivor.health < survivor.max_health - 10 and game.herbs > 0:
                game.herbs -= 1
                survivor.health = clamp(survivor.health + 8, 0, survivor.max_health)
            survivor.decision_timer = 0


def _update_shelter(survivor, dt: float) -> None:
    survivor.move_toward(survivor.home_pos, dt)
    if survivor.distance_to(survivor.home_pos) < 24:
        survivor.energy = clamp(survivor.energy + 10 * dt, 0, 100)
        survivor.morale = clamp(survivor.morale + 1 * dt, 0, 100)


def _is_survivor(actor) -> bool:
    return actor.__class__.__name__ == "Survivor"









