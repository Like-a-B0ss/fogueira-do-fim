from __future__ import annotations

from pygame import Vector2


def nearest_interaction_hint(world) -> tuple[Vector2, str] | None:
    player = world.player
    active_event = world.active_dynamic_event()
    if active_event:
        if active_event.kind == "faccao" and player.distance_to(active_event.pos) < 118:
            humane = dict(active_event.data.get("humane", {}))
            hardline = dict(active_event.data.get("hardline", {}))
            return active_event.pos, f"E {humane.get('title', 'ceder')}  |  Q {hardline.get('title', 'pressionar')}"
        if active_event.kind == "expedicao" and player.distance_to(active_event.pos) < 122:
            return active_event.pos, "E socorrer equipe na trilha"
        if active_event.kind == "abrigo" and player.distance_to(active_event.pos) < 114:
            return active_event.pos, "E acolher forasteiro"
        if active_event.kind == "incendio" and player.distance_to(active_event.pos) < 118:
            return active_event.pos, "E conter incêndio"
        if active_event.kind == "alarme" and player.distance_to(active_event.pos) < 120:
            return active_event.pos, "E responder ao alarme da cerca"
        if active_event.kind in {"fuga", "desercao", "doenca"}:
            target = next(
                (survivor for survivor in world.survivors if survivor.name == active_event.target_name and survivor.is_alive()),
                None,
            )
            if target and player.distance_to(target.pos) < 96:
                prompt_map = {
                    "fuga": "E acalmar morador",
                    "desercao": "E impedir deserção",
                    "doenca": "E estabilizar doente",
                }
                return target.pos, prompt_map.get(active_event.kind, "E interagir")

    downed_member = world.nearest_downed_expedition_member(player.pos)
    if downed_member:
        return downed_member.pos, f"E levantar {downed_member.name.lower()} na trilha"

    for interest_point in world.interest_points:
        if not interest_point.resolved and player.distance_to(interest_point.pos) < interest_point.radius + 34:
            return interest_point.pos, f"E investigar {interest_point.label}"

    for node in world.resource_nodes:
        if node.is_available() and player.distance_to(node.pos) < 92:
            prompt = "E colher suprimentos" if node.kind == "food" else "E vasculhar sucata"
            return node.pos, prompt

    for barricade in world.barricades:
        if barricade.health < barricade.max_health and world.wood >= 1 and player.distance_to(barricade.pos) < 92:
            return barricade.pos, "E reforçar barricada"
        if player.distance_to(barricade.pos) < 92:
            if getattr(barricade, "spike_level", 0) >= 3:
                return barricade.pos, "Spikes no máximo"
            wood_cost, scrap_cost = world.barricade_upgrade_cost(barricade)
            return barricade.pos, f"E melhorar spikes ({wood_cost} tábuas, {scrap_cost} sucata)"

    if player.distance_to(world.workshop_pos) < 108:
        if world.can_use_workshop_saw():
            if world.can_expand_camp():
                return world.workshop_pos, "E cortar tábuas  |  Q ampliar acampamento"
            return world.workshop_pos, "E cortar tábuas na oficina"
        if world.can_expand_camp():
            return world.workshop_pos, "E ampliar acampamento"
        if world.camp_level < world.max_camp_level:
            log_cost, scrap_cost = world.expansion_cost()
            return world.workshop_pos, f"Precisa {log_cost} toras e {scrap_cost} sucata"
        return world.workshop_pos, "Oficina livre"

    sleep_slot = world.nearest_sleep_slot(player.pos)
    if sleep_slot and not world.player_sleeping:
        if not world.active_dynamic_events:
            return Vector2(sleep_slot["interact_pos"]), "E dormir e acelerar o tempo"
        return Vector2(sleep_slot["interact_pos"]), "Crise ativa impede descanso"

    if player.distance_to(world.radio_pos) < 104:
        if world.active_expedition:
            return world.radio_pos, "E revisar expedição  |  Q recolher equipe"
        target_region = world.best_expedition_region()
        if target_region:
            return world.radio_pos, f"E enviar expedição para {target_region['name']}"
        return world.radio_pos, "Sem região conhecida para expedição"

    if player.distance_to(world.bonfire_pos) < 100:
        if world.available_fuel() >= 1:
            return world.bonfire_pos, "E alimentar fogueira"
        return world.bonfire_pos, "Sem combustível para o fogo"

    infirmary = world.nearest_building_of_kind("enfermaria", player.pos)
    if infirmary and player.distance_to(infirmary.pos) < 96:
        if world.has_medical_supplies() and player.health < player.max_health - 8:
            return infirmary.pos, "E tratar ferimentos"
        return infirmary.pos, "Enfermaria sem uso imediato"

    manual_building = world.nearest_player_usable_building(player.pos)
    if manual_building:
        return manual_building.pos, world.player_building_prompt(manual_building, player)

    for survivor in world.survivors:
        if survivor.distance_to(player.pos) < 92:
            return survivor.pos, f"E conversar com {survivor.name.lower()}"
    return None


def mouse_interaction_target(world, cursor_world: Vector2) -> dict[str, object] | None:
    """Escolhe um alvo de interação pelo mouse para aliviar a proximidade no acampamento."""
    candidates: list[tuple[float, dict[str, object]]] = []

    def consider(kind: str, pos: Vector2, *, radius: float, reach: float, obj: object | None = None) -> None:
        distance = cursor_world.distance_to(pos)
        if distance <= radius:
            candidates.append(
                (
                    distance,
                    {
                        "kind": kind,
                        "pos": Vector2(pos),
                        "reach": reach,
                        "obj": obj,
                    },
                )
            )

    active_event = world.active_dynamic_event()
    if active_event:
        consider(f"event:{active_event.kind}", Vector2(active_event.pos), radius=44, reach=132, obj=active_event)
        if active_event.kind in {"fuga", "desercao", "doenca"}:
            target = next(
                (survivor for survivor in world.survivors if survivor.name == active_event.target_name and survivor.is_alive()),
                None,
            )
            if target:
                consider(f"event:{active_event.kind}", Vector2(target.pos), radius=36, reach=104, obj=active_event)

    downed_member = world.nearest_downed_expedition_member(cursor_world)
    if downed_member and cursor_world.distance_to(downed_member.pos) < 28:
        consider("downed_member", Vector2(downed_member.pos), radius=28, reach=112, obj=downed_member)

    for interest_point in world.interest_points:
        if not interest_point.resolved:
            consider("interest", Vector2(interest_point.pos), radius=max(28, interest_point.radius * 0.54), reach=136, obj=interest_point)

    for node in world.resource_nodes:
        if node.is_available():
            consider(f"node:{node.kind}", Vector2(node.pos), radius=30, reach=112, obj=node)

    for barricade in world.barricades:
        consider("barricade", Vector2(barricade.pos), radius=26, reach=118, obj=barricade)

    consider("workshop", Vector2(world.workshop_pos), radius=42, reach=136)
    consider("radio", Vector2(world.radio_pos), radius=42, reach=132)
    consider("bonfire", Vector2(world.bonfire_pos), radius=46, reach=130)

    for building in world.buildings:
        if building.kind in {"serraria", "cozinha", "horta", "anexo", "torre", "enfermaria", "estoque"}:
            consider(
                f"building:{building.kind}",
                Vector2(building.pos),
                radius=max(26, building.size * 0.72),
                reach=world.player_building_reach(building.kind),
                obj=building,
            )

    sleep_slot = world.nearest_sleep_slot(cursor_world)
    if sleep_slot and cursor_world.distance_to(Vector2(sleep_slot["interact_pos"])) < 44:
        consider("sleep", Vector2(sleep_slot["interact_pos"]), radius=44, reach=132, obj=sleep_slot)

    for survivor in world.survivors:
        if survivor.is_alive() and not world.is_survivor_on_expedition(survivor):
            consider("survivor", Vector2(survivor.pos), radius=28, reach=132, obj=survivor)

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def hovered_interaction_target(world) -> dict[str, object] | None:
    """Retorna o alvo atualmente sob o mouse na tela."""
    if not hasattr(world, "input_state"):
        return None
    return world.mouse_interaction_target(world.screen_to_world(world.input_state.mouse_screen))


def prompt_for_interaction_target(world, target: dict[str, object]) -> str | None:
    """Traduz um alvo do mouse para o texto curto de interação exibido na HUD."""
    kind = str(target.get("kind", ""))
    obj = target.get("obj")

    if kind.startswith("event:") and obj:
        event_kind = str(kind.split(":", 1)[1])
        if event_kind == "faccao":
            humane = dict(obj.data.get("humane", {}))
            hardline = dict(obj.data.get("hardline", {}))
            return f"E {humane.get('title', 'ceder')}  |  Q {hardline.get('title', 'pressionar')}"
        if event_kind == "expedicao":
            return "E socorrer equipe na trilha"
        if event_kind == "abrigo":
            return "E acolher forasteiro"
        if event_kind == "incendio":
            return "E conter incêndio"
        if event_kind == "alarme":
            return "E responder ao alarme da cerca"
        if event_kind == "fuga":
            return "E acalmar morador"
        if event_kind == "desercao":
            return "E impedir deserção"
        if event_kind == "doenca":
            return "E estabilizar doente"
    if kind == "downed_member" and obj:
        return f"E levantar {obj.name.lower()} na trilha"
    if kind == "interest" and obj:
        return f"E investigar {obj.label}"
    if kind == "node:food":
        return "E colher suprimentos"
    if kind == "node:scrap":
        return "E vasculhar sucata"
    if kind == "barricade" and obj:
        if obj.health < obj.max_health and world.wood >= 1:
            return "E reforçar barricada"
        if getattr(obj, "spike_level", 0) >= 3:
            return "Spikes no máximo"
        wood_cost, scrap_cost = world.barricade_upgrade_cost(obj)
        return f"E melhorar spikes ({wood_cost} tábuas, {scrap_cost} sucata)"
    if kind == "workshop":
        if world.can_use_workshop_saw():
            if world.can_expand_camp():
                return "E cortar tábuas  |  Q ampliar acampamento"
            return "E cortar tábuas na oficina"
        if world.can_expand_camp():
            return "E ampliar acampamento"
        if world.camp_level < world.max_camp_level:
            log_cost, scrap_cost = world.expansion_cost()
            return f"Precisa {log_cost} toras e {scrap_cost} sucata"
        return "Oficina livre"
    if kind == "radio":
        if world.active_expedition:
            return "E revisar expedição  |  Q recolher equipe"
        target_region = world.best_expedition_region()
        if target_region:
            return f"E enviar expedição para {target_region['name']}"
        return "Sem região conhecida para expedição"
    if kind == "bonfire":
        return "E alimentar fogueira" if world.available_fuel() >= 1 else "Sem combustível para o fogo"
    if kind == "sleep":
        return "E dormir e acelerar o tempo" if not world.active_dynamic_events else "Crise ativa impede descanso"
    if kind.startswith("building:") and obj:
        return world.player_building_prompt(obj, world.player)
    if kind == "survivor" and obj:
        return f"E conversar com {obj.name.lower()}"
    return None
