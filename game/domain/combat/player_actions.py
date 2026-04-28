from __future__ import annotations

from pygame import Vector2

from ...core.config import PALETTE, ROLE_COLORS, clamp
from ...core.models import DamagePulse


def perform_attack(player, game) -> None:
    if player.attack_cooldown > 0:
        return
    player.attack_cooldown = 0.38
    player.attack_flash = 0.22
    game.audio.play_attack(source_pos=player.pos)
    hit_any = False
    hit_count = 0
    for zombie in game.zombies:
        if not zombie.is_alive():
            continue
        offset = zombie.pos - player.pos
        distance = offset.length()
        if distance > 84 or distance <= 0.01:
            continue
        angle = player.facing.angle_to(offset)
        if abs(angle) <= 58:
            damage = 42.0
            stagger = 0.18
            knockback = 18.0
            pulse_radius = 12
            shake = 1.8
            ember_count = 2
            if zombie.variant == "runner":
                damage = 46.0
                stagger = 0.24
                knockback = 24.0
                pulse_radius = 14
                shake = 2.0
            elif zombie.variant == "brute":
                damage = 34.0
                stagger = 0.09
                knockback = 10.0
                pulse_radius = 16
                shake = 2.4
                ember_count = 3
            elif zombie.variant == "howler":
                damage = 44.0
                stagger = 0.2
                knockback = 20.0
            elif zombie.variant == "raider":
                damage = 40.0
                stagger = 0.16
                knockback = 17.0
            if zombie.is_boss:
                damage = 30.0
                stagger = 0.07
                knockback = 8.0
                pulse_radius = 18
                shake = 2.9
                ember_count = 4
                zombie.visual_state = "enraged"
            zombie.health -= damage
            zombie.stagger = max(zombie.stagger, stagger)
            zombie.pos += offset.normalize() * knockback
            hit_any = True
            hit_count += 1
            game.impact_burst(zombie.pos, PALETTE["danger_soft"], radius=14, shake=shake, ember_count=ember_count)
            game.damage_pulses.append(
                DamagePulse(Vector2(zombie.pos), pulse_radius, 0.28, PALETTE["danger_soft"])
            )
            if zombie.variant == "brute":
                game.spawn_floating_text("pancada seca", zombie.pos + Vector2(0, -18), PALETTE["danger_soft"])
            elif zombie.is_boss:
                game.spawn_floating_text("chefe ferido", zombie.pos + Vector2(0, -20), PALETTE["morale"])
            if zombie.health <= 0:
                game.spawn_floating_text("zumbi abatido", zombie.pos, PALETTE["accent_soft"])
                game.morale_flash = min(1.0, game.morale_flash + 0.15)
    if hit_any:
        label = "golpe amplo" if hit_count > 1 else "corte"
        game.spawn_floating_text(label, player.pos + player.facing * 26, PALETTE["accent_soft"])
        game.audio.play_impact("flesh", source_pos=player.pos)
        return

    best_tree: dict[str, object] | None = None
    best_distance = 96.0
    for tree in game.trees:
        if not game.tree_is_harvestable(tree):
            continue
        tree_pos = Vector2(tree["pos"])
        offset = tree_pos - player.pos
        distance = offset.length()
        if distance > best_distance or distance <= 0.01:
            continue
        angle = player.facing.angle_to(offset)
        if abs(angle) <= 54:
            best_tree = tree
            best_distance = distance

    if best_tree:
        amount = game.harvest_tree(best_tree, effort=1)
        tree_pos = Vector2(best_tree["pos"])
        if amount > 0:
            stored = game.add_resource_bundle({"logs": amount})
            game.spawn_floating_text(game.bundle_summary(stored or {"logs": amount}), tree_pos, PALETTE["accent_soft"])
            game.set_event_message("As árvores agora viram toras. Sem serraria, a oficina corta tábuas devagar para segurar o começo.", duration=4.8)
            game.impact_burst(tree_pos, PALETTE["accent_soft"], radius=13, shake=1.0, ember_count=5, smoky=True)
            game.audio.play_impact("wood", source_pos=tree_pos)
        else:
            progress = int(best_tree.get("effort_progress", 1))
            required = int(best_tree.get("effort_required", 2))
            game.spawn_floating_text(f"tronco {progress}/{required}", tree_pos + Vector2(0, -18), PALETTE["muted"])
            game.impact_burst(tree_pos, PALETTE["wood"], radius=9, shake=0.45, ember_count=2, smoky=True)
            game.audio.play_impact("wood", source_pos=tree_pos)


def perform_interaction(player, game, *, hardline: bool = False) -> None:
    if player.interact_cooldown > 0:
        return

    hovered_target = game.hovered_interaction_target()
    if hovered_target:
        target_pos = Vector2(hovered_target["pos"])
        reach = float(hovered_target.get("reach", 112.0))
        if player.distance_to(target_pos) > reach:
            game.spawn_floating_text("chegue mais perto", target_pos, PALETTE["muted"])
            game.audio.play_alert(source_pos=target_pos)
            player.interact_cooldown = 0.2
            return
        player.perform_mouse_interaction(game, target_override=hovered_target, hardline=hardline)
        return

    player.interact_cooldown = 0.35
    best_distance = 92.0
    acted = False

    active_event = game.active_dynamic_event()
    if active_event:
        if active_event.kind == "faccao" and player.distance_to(active_event.pos) < 112:
            if game.resolve_dynamic_event(active_event, accepted=not hardline):
                game.audio.play_interact(source_pos=active_event.pos)
            else:
                game.audio.play_alert(source_pos=active_event.pos)
            return
        if active_event.kind == "abrigo" and player.distance_to(active_event.pos) < 108:
            if game.resolve_dynamic_event(active_event, accepted=True):
                game.audio.play_interact(source_pos=active_event.pos)
            else:
                game.audio.play_alert(source_pos=active_event.pos)
            return
        if active_event.kind == "incendio" and player.distance_to(active_event.pos) < 112:
            if game.resolve_dynamic_event(active_event):
                game.audio.play_interact("repair", source_pos=active_event.pos)
            else:
                game.audio.play_alert(source_pos=active_event.pos)
            return
        if active_event.kind == "alarme" and player.distance_to(active_event.pos) < 116:
            if game.resolve_dynamic_event(active_event):
                game.audio.play_interact("repair", source_pos=active_event.pos)
            else:
                game.audio.play_alert(source_pos=active_event.pos)
            return
        if active_event.kind == "expedicao" and player.distance_to(active_event.pos) < 118:
            if game.resolve_dynamic_event(active_event):
                game.audio.play_interact(source_pos=active_event.pos)
            else:
                game.audio.play_alert(source_pos=active_event.pos)
            return
        if active_event.kind in {"fuga", "desercao", "doenca"}:
            target = next(
                (survivor for survivor in game.survivors if survivor.name == active_event.target_name and survivor.is_alive()),
                None,
            )
            if target and player.distance_to(target.pos) < 92:
                if game.resolve_dynamic_event(active_event):
                    game.audio.play_interact(source_pos=target.pos)
                else:
                    game.audio.play_alert(source_pos=target.pos)
                return

    downed_member = game.nearest_downed_expedition_member(player.pos)
    if downed_member:
        game.revive_expedition_member(downed_member)
        game.set_event_message(f"Você puxou {downed_member.name} de volta para a coluna.", duration=4.8)
        game.audio.play_interact("repair", source_pos=downed_member.pos)
        return

    for interest_point in game.interest_points:
        if interest_point.resolved:
            continue
        distance = player.distance_to(interest_point.pos)
        if distance < max(best_distance, interest_point.radius + 26):
            game.audio.play_interact(source_pos=interest_point.pos)
            game.resolve_interest_point(interest_point)
            return

    for node in game.resource_nodes:
        distance = player.distance_to(node.pos)
        if distance < best_distance and node.is_available():
            harvested = node.harvest()
            if harvested:
                bundle = game.add_resource_bundle(game.resource_node_bundle(node))
                color = PALETTE["heal"] if node.kind == "food" else ROLE_COLORS["mensageiro"]
                game.spawn_floating_text(game.bundle_summary(bundle or game.resource_node_bundle(node)), node.pos, color)
                game.emit_embers(node.pos, 3, smoky=True)
                game.audio.play_interact(source_pos=node.pos)
                acted = True
                break

    if acted:
        return

    for barricade in game.barricades:
        distance = player.distance_to(barricade.pos)
        if distance < best_distance and barricade.health < barricade.max_health and game.wood >= 1:
            game.wood -= 1
            barricade.repair(24)
            game.spawn_floating_text("barricada reforcada", barricade.pos, PALETTE["heal"])
            game.impact_burst(barricade.pos, PALETTE["heal"], radius=11, shake=0.55, ember_count=2, smoky=True)
            game.audio.play_interact("repair", source_pos=barricade.pos)
            game.notify_chief_task_progress("repair_barricade")
            acted = True
            break

    if acted:
        return

    for barricade in game.barricades:
        distance = player.distance_to(barricade.pos)
        if distance < best_distance:
            if game.upgrade_barricade(barricade):
                game.audio.play_interact("repair", source_pos=barricade.pos)
                return
            if getattr(barricade, "spike_level", 0) >= 3:
                game.spawn_floating_text("spikes no limite", barricade.pos, PALETTE["muted"])
                return
            return

    if player.distance_to(game.workshop_pos) < 108:
        if hardline and game.can_expand_camp():
            if game.expand_camp():
                game.audio.play_interact("repair", source_pos=game.workshop_pos)
            return
        if game.can_use_workshop_saw():
            stored = game.cut_planks_at_workshop()
            if stored:
                game.spawn_floating_text(game.bundle_summary(stored), game.workshop_pos, PALETTE["accent_soft"])
                game.set_event_message("A oficina cortou tábuas devagar. A serraria ainda segue sendo a versão eficiente.", duration=4.8)
                game.impact_burst(game.workshop_pos, PALETTE["accent_soft"], radius=11, shake=0.45, ember_count=3, smoky=True)
                game.audio.play_interact("repair", source_pos=game.workshop_pos)
                return
            game.spawn_floating_text("estoque cheio", game.workshop_pos, PALETTE["muted"])
            return
        if game.expand_camp():
            game.audio.play_interact("repair", source_pos=game.workshop_pos)
            return
        if game.camp_level < game.max_camp_level:
            log_cost, scrap_cost = game.expansion_cost()
            game.spawn_floating_text(
                f"oficina pede {log_cost} toras e {scrap_cost} sucata",
                game.workshop_pos,
                PALETTE["muted"],
            )
            return

    sleep_slot = game.nearest_sleep_slot(player.pos)
    if sleep_slot and not game.player_sleeping:
        if not game.active_dynamic_events:
            game.begin_player_sleep(sleep_slot)
            game.audio.play_interact("bonfire", source_pos=Vector2(sleep_slot["sleep_pos"]))
            return
        game.spawn_floating_text("ha crise demais para dormir", player.pos, PALETTE["danger_soft"])
        game.audio.play_alert(source_pos=player.pos)
        return

    if player.distance_to(game.bonfire_pos) < 100 and game.available_fuel() >= 1:
        fed, label, color = game.add_fuel_to_bonfire()
        if not fed:
            return
        for survivor in game.survivors:
            if survivor.distance_to(game.bonfire_pos) < 170:
                survivor.morale = clamp(survivor.morale + 3.5, 0, 100)
                game.adjust_trust(survivor, 1.1)
        game.spawn_floating_text(label, game.bonfire_pos, color)
        game.emit_embers(game.bonfire_pos, 12)
        game.audio.play_interact("bonfire", source_pos=game.bonfire_pos)
        return

    infirmary = game.nearest_building_of_kind("enfermaria", player.pos)
    if infirmary and player.distance_to(infirmary.pos) < 96 and game.has_medical_supplies() and player.health < player.max_health - 8:
        if game.medicine > 0:
            game.medicine -= 1
            player.health = clamp(player.health + 26, 0, player.max_health)
            game.spawn_floating_text("curativo pesado", infirmary.pos, PALETTE["heal"])
        elif game.herbs > 0:
            game.herbs -= 1
            player.health = clamp(player.health + 14, 0, player.max_health)
            game.spawn_floating_text("ervas medicinais", infirmary.pos, PALETTE["heal"])
        game.audio.play_interact("repair", source_pos=infirmary.pos)
        return

    usable_building = game.nearest_player_usable_building(player.pos)
    if usable_building and player.distance_to(usable_building.pos) < game.player_building_reach(usable_building.kind):
        if game.use_building_as_player(usable_building, player):
            game.audio.play_interact(
                "repair" if usable_building.kind in {"serraria", "anexo", "enfermaria"} else "bonfire",
                source_pos=usable_building.pos,
            )
        return

    if player.distance_to(game.radio_pos) < 104:
        if game.active_expedition:
            if hardline:
                recalled, message = game.recall_active_expedition()
                game.spawn_floating_text("recolha" if recalled else "aguarde", game.radio_pos, PALETTE["morale"] if recalled else PALETTE["muted"])
                if recalled:
                    game.audio.play_ui("order")
                else:
                    game.audio.play_alert(source_pos=game.radio_pos)
                if message:
                    game.set_event_message(message, duration=4.8)
                return
            status = game.expedition_status_text(short=False) or "A equipe esta fora da base."
            game.set_event_message(status, duration=5.0)
            game.spawn_floating_text("expedição", game.radio_pos, PALETTE["accent_soft"])
            game.audio.play_ui("focus")
            return
        launched, message = game.launch_best_expedition()
        game.spawn_floating_text("expedição" if launched else "sem equipe", game.radio_pos, PALETTE["accent_soft"] if launched else PALETTE["danger_soft"])
        if launched:
            game.audio.play_ui("order")
        else:
            game.audio.play_alert(source_pos=game.radio_pos)
        if message:
            game.set_event_message(message, duration=4.8)
        return

    for survivor in game.survivors:
        if survivor.is_alive() and not game.is_survivor_on_expedition(survivor) and survivor.distance_to(player.pos) < best_distance:
            game.open_survivor_dialog(survivor)
            game.spawn_floating_text(f"falando com {survivor.name.lower()}", survivor.pos, PALETTE["accent_soft"])
            game.audio.play_ui("order")
            return


def perform_mouse_interaction(
    player,
    game,
    *,
    target_override: dict[str, object] | None = None,
    hardline: bool = False,
) -> None:
    """Interage com o alvo sob o mouse para aliviar o aperto visual do acampamento."""
    if player.interact_cooldown > 0:
        return
    target = target_override or game.mouse_interaction_target(game.screen_to_world(game.input_state.mouse_screen))
    if not target:
        return

    target_pos = Vector2(target["pos"])
    reach = float(target.get("reach", 112.0))
    if player.distance_to(target_pos) > reach:
        game.spawn_floating_text("chegue mais perto", target_pos, PALETTE["muted"])
        game.audio.play_alert(source_pos=target_pos)
        player.interact_cooldown = 0.2
        return

    player.interact_cooldown = 0.35
    kind = str(target["kind"])
    obj = target.get("obj")

    if kind.startswith("event:") and obj:
        event = obj
        accepted = not hardline if getattr(event, "kind", "") == "faccao" else True
        if game.resolve_dynamic_event(event, accepted=accepted):
            if getattr(event, "kind", "") in {"incendio", "alarme"}:
                game.audio.play_interact("repair", source_pos=event.pos)
            else:
                game.audio.play_interact(source_pos=event.pos)
        else:
            game.audio.play_alert(source_pos=event.pos)
        return

    if kind == "downed_member" and obj:
        game.revive_expedition_member(obj)
        game.set_event_message(f"Você puxou {obj.name} de volta para a coluna.", duration=4.8)
        game.audio.play_interact("repair", source_pos=obj.pos)
        return

    if kind == "interest" and obj:
        game.audio.play_interact(source_pos=obj.pos)
        game.resolve_interest_point(obj)
        return

    if kind.startswith("node:") and obj and obj.is_available():
        harvested = obj.harvest()
        if harvested:
            bundle = game.add_resource_bundle(game.resource_node_bundle(obj))
            color = PALETTE["heal"] if obj.kind == "food" else ROLE_COLORS["mensageiro"]
            game.spawn_floating_text(game.bundle_summary(bundle or game.resource_node_bundle(obj)), obj.pos, color)
            game.emit_embers(obj.pos, 3, smoky=True)
            game.audio.play_interact(source_pos=obj.pos)
        return

    if kind == "barricade" and obj:
        if obj.health < obj.max_health and game.wood >= 1:
            game.wood -= 1
            obj.repair(24)
            game.spawn_floating_text("barricada reforcada", obj.pos, PALETTE["heal"])
            game.impact_burst(obj.pos, PALETTE["heal"], radius=11, shake=0.55, ember_count=2, smoky=True)
            game.audio.play_interact("repair", source_pos=obj.pos)
            game.notify_chief_task_progress("repair_barricade")
            return
        if game.upgrade_barricade(obj):
            game.audio.play_interact("repair", source_pos=obj.pos)
            return
        if getattr(obj, "spike_level", 0) >= 3:
            game.spawn_floating_text("spikes no limite", obj.pos, PALETTE["muted"])
        else:
            wood_cost, scrap_cost = game.barricade_upgrade_cost(obj)
            game.spawn_floating_text(f"pede {wood_cost} tábuas e {scrap_cost} sucata", obj.pos, PALETTE["muted"])
        return

    if kind == "workshop":
        if hardline and game.can_expand_camp():
            if game.expand_camp():
                game.audio.play_interact("repair", source_pos=game.workshop_pos)
                return
        if game.can_use_workshop_saw():
            stored = game.cut_planks_at_workshop()
            if stored:
                game.spawn_floating_text(game.bundle_summary(stored), game.workshop_pos, PALETTE["accent_soft"])
                game.set_event_message("A oficina cortou tábuas devagar. A serraria ainda segue sendo a versão eficiente.", duration=4.8)
                game.impact_burst(game.workshop_pos, PALETTE["accent_soft"], radius=11, shake=0.45, ember_count=3, smoky=True)
                game.audio.play_interact("repair", source_pos=game.workshop_pos)
                return
            game.spawn_floating_text("estoque cheio", game.workshop_pos, PALETTE["muted"])
            return
        if game.expand_camp():
            game.audio.play_interact("repair", source_pos=game.workshop_pos)
            return
        if game.camp_level < game.max_camp_level:
            log_cost, scrap_cost = game.expansion_cost()
            game.spawn_floating_text(f"oficina pede {log_cost} toras e {scrap_cost} sucata", game.workshop_pos, PALETTE["muted"])
        return

    if kind == "sleep" and obj:
        if not game.active_dynamic_events:
            game.begin_player_sleep(obj)
            game.audio.play_interact("bonfire", source_pos=target_pos)
        else:
            game.spawn_floating_text("ha crise demais para dormir", player.pos, PALETTE["danger_soft"])
            game.audio.play_alert(source_pos=player.pos)
        return

    if kind == "bonfire":
        if game.available_fuel() >= 1:
            fed, label, color = game.add_fuel_to_bonfire()
            if fed:
                for survivor in game.survivors:
                    if survivor.distance_to(game.bonfire_pos) < 170:
                        survivor.morale = clamp(survivor.morale + 3.5, 0, 100)
                        game.adjust_trust(survivor, 1.1)
                game.spawn_floating_text(label, game.bonfire_pos, color)
                game.emit_embers(game.bonfire_pos, 12)
                game.audio.play_interact("bonfire", source_pos=game.bonfire_pos)
        else:
            game.spawn_floating_text("sem combustível", game.bonfire_pos, PALETTE["muted"])
        return

    if kind.startswith("building:") and obj:
        if game.use_building_as_player(obj, player):
            game.audio.play_interact(
                "repair" if getattr(obj, "kind", "") in {"serraria", "anexo", "enfermaria"} else "bonfire",
                source_pos=obj.pos,
            )
        else:
            game.audio.play_alert(source_pos=obj.pos)
        return

    if kind == "radio":
        if game.active_expedition:
            if hardline:
                recalled, message = game.recall_active_expedition()
                game.spawn_floating_text("recolha" if recalled else "aguarde", game.radio_pos, PALETTE["morale"] if recalled else PALETTE["muted"])
                if recalled:
                    game.audio.play_ui("order")
                else:
                    game.audio.play_alert(source_pos=game.radio_pos)
                if message:
                    game.set_event_message(message, duration=4.8)
                return
            status = game.expedition_status_text(short=False) or "A equipe esta fora da base."
            game.set_event_message(status, duration=5.0)
            game.spawn_floating_text("expedição", game.radio_pos, PALETTE["accent_soft"])
            game.audio.play_ui("focus")
            return
        launched, message = game.launch_best_expedition()
        game.spawn_floating_text("expedição" if launched else "sem equipe", game.radio_pos, PALETTE["accent_soft"] if launched else PALETTE["danger_soft"])
        if launched:
            game.audio.play_ui("order")
        else:
            game.audio.play_alert(source_pos=game.radio_pos)
        if message:
            game.set_event_message(message, duration=4.8)
        return

    if kind == "survivor" and obj:
        game.open_survivor_dialog(obj)
        game.spawn_floating_text(f"falando com {obj.name.lower()}", obj.pos, PALETTE["accent_soft"])
        game.audio.play_ui("order")
