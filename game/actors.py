from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from pygame import Vector2

from .config import CAMP_CENTER, CAMP_RADIUS, PALETTE, ROLE_COLORS, angle_to_vector, clamp
from .models import Barricade, Building, DamagePulse, ResourceNode

if TYPE_CHECKING:
    from .session import Game


class Actor:
    def __init__(self, pos: Vector2, radius: float, speed: float, health: float) -> None:
        self.pos = Vector2(pos)
        self.radius = radius
        self.speed = speed
        self.max_health = health
        self.health = health
        self.velocity = Vector2()
        self.facing = Vector2(1, 0)

    def move_toward(self, target: Vector2, dt: float, speed_scale: float = 1.0) -> bool:
        direction = target - self.pos
        distance = direction.length()
        if distance < 1:
            self.velocity *= 0.7
            return True
        if distance > 0:
            direction.scale_to_length(self.speed * speed_scale)
            self.velocity = direction
            self.facing = direction.normalize()
            step = min(distance, self.speed * speed_scale * dt)
            self.pos += self.facing * step
        return distance < max(18, self.radius + 6)

    def distance_to(self, target: Vector2) -> float:
        return self.pos.distance_to(target)

    def is_alive(self) -> bool:
        return self.health > 0


class Player(Actor):
    def __init__(self, pos: Vector2) -> None:
        super().__init__(pos, radius=18, speed=205, health=150)
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.attack_cooldown = 0.0
        self.attack_flash = 0.0
        self.interact_cooldown = 0.0
        self.last_move = Vector2(1, 0)

    def update(self, game: "Game", dt: float) -> None:
        if getattr(game, "player_sleeping", False):
            self.velocity *= 0.2
            self.stamina = clamp(self.stamina + 34 * dt, 0, self.max_stamina)
            self.health = clamp(self.health + 5 * dt, 0, self.max_health)
            slot = getattr(game, "player_sleep_slot", None)
            if slot:
                self.pos = Vector2(slot["sleep_pos"])
            return
        mouse_world = game.screen_to_world(game.input_state.mouse_screen)
        direction = mouse_world - self.pos
        if direction.length_squared() > 8:
            self.facing = direction.normalize()

        move = Vector2(game.input_state.move)
        sprinting = game.input_state.sprint
        speed_scale = 1.0
        previous_pos = Vector2(self.pos)
        if move.length_squared() > 0:
            move = move.normalize()
            self.last_move = Vector2(move)
            if sprinting and self.stamina > 5:
                speed_scale = 1.55
                self.stamina = clamp(self.stamina - 26 * dt, 0, self.max_stamina)
            else:
                self.stamina = clamp(self.stamina + 18 * dt, 0, self.max_stamina)
            self.pos += move * self.speed * speed_scale * dt
        else:
            self.stamina = clamp(self.stamina + 24 * dt, 0, self.max_stamina)

        displacement = self.pos - previous_pos
        if displacement.length_squared() > 0:
            self.velocity = displacement / max(0.0001, dt)
        else:
            self.velocity *= 0.2
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.attack_flash = max(0.0, self.attack_flash - dt)
        self.interact_cooldown = max(0.0, self.interact_cooldown - dt)

    def perform_attack(self, game: "Game") -> None:
        if self.attack_cooldown > 0:
            return
        self.attack_cooldown = 0.38
        self.attack_flash = 0.22
        game.audio.play_attack()
        hit_any = False
        for zombie in game.zombies:
            if not zombie.is_alive():
                continue
            offset = zombie.pos - self.pos
            distance = offset.length()
            if distance > 84 or distance <= 0.01:
                continue
            angle = self.facing.angle_to(offset)
            if abs(angle) <= 58:
                zombie.health -= 38
                zombie.stagger = 0.18
                zombie.pos += offset.normalize() * 18
                hit_any = True
                game.damage_pulses.append(
                    DamagePulse(Vector2(zombie.pos), 12, 0.28, PALETTE["danger_soft"])
                )
                if zombie.health <= 0:
                    game.spawn_floating_text("zumbi abatido", zombie.pos, PALETTE["accent_soft"])
                    game.morale_flash = min(1.0, game.morale_flash + 0.15)
        if hit_any:
            game.spawn_floating_text("corte", self.pos + self.facing * 26, PALETTE["accent_soft"])
            game.audio.play_impact("flesh")
            return

        best_tree: dict[str, object] | None = None
        best_distance = 96.0
        for tree in game.trees:
            if not game.tree_is_harvestable(tree):
                continue
            tree_pos = Vector2(tree["pos"])
            offset = tree_pos - self.pos
            distance = offset.length()
            if distance > best_distance or distance <= 0.01:
                continue
            angle = self.facing.angle_to(offset)
            if abs(angle) <= 54:
                best_tree = tree
                best_distance = distance

        if best_tree:
            amount = game.harvest_tree(best_tree, effort=1)
            tree_pos = Vector2(best_tree["pos"])
            if amount > 0:
                stored = game.add_resource_bundle({"logs": amount})
                game.spawn_floating_text(game.bundle_summary(stored or {"logs": amount}), tree_pos, PALETTE["accent_soft"])
                game.set_event_message("As arvores agora viram toras. Sem serraria, a madeira boa de construcao demora mais a chegar.", duration=4.8)
                game.emit_embers(tree_pos, 4, smoky=True)
                game.audio.play_impact("wood")
            else:
                progress = int(best_tree.get("effort_progress", 1))
                required = int(best_tree.get("effort_required", 2))
                game.spawn_floating_text(f"tronco {progress}/{required}", tree_pos + Vector2(0, -18), PALETTE["muted"])
                game.emit_embers(tree_pos, 2, smoky=True)
                game.audio.play_impact("wood")

    def perform_interaction(self, game: "Game", *, hardline: bool = False) -> None:
        if self.interact_cooldown > 0:
            return
        self.interact_cooldown = 0.35
        best_distance = 92.0
        acted = False

        active_event = game.active_dynamic_event()
        if active_event:
            if active_event.kind == "faccao" and self.distance_to(active_event.pos) < 112:
                if game.resolve_dynamic_event(active_event, accepted=not hardline):
                    game.audio.play_interact()
                else:
                    game.audio.play_alert()
                return
            if active_event.kind == "abrigo" and self.distance_to(active_event.pos) < 108:
                if game.resolve_dynamic_event(active_event, accepted=True):
                    game.audio.play_interact()
                else:
                    game.audio.play_alert()
                return
            if active_event.kind == "incendio" and self.distance_to(active_event.pos) < 112:
                if game.resolve_dynamic_event(active_event):
                    game.audio.play_interact("repair")
                else:
                    game.audio.play_alert()
                return
            if active_event.kind == "expedicao" and self.distance_to(active_event.pos) < 118:
                if game.resolve_dynamic_event(active_event):
                    game.audio.play_interact()
                else:
                    game.audio.play_alert()
                return
            if active_event.kind in {"fuga", "desercao", "doenca"}:
                target = next(
                    (survivor for survivor in game.survivors if survivor.name == active_event.target_name and survivor.is_alive()),
                    None,
                )
                if target and self.distance_to(target.pos) < 92:
                    if game.resolve_dynamic_event(active_event):
                        game.audio.play_interact()
                    else:
                        game.audio.play_alert()
                    return

        downed_member = game.nearest_downed_expedition_member(self.pos)
        if downed_member:
            game.revive_expedition_member(downed_member)
            game.set_event_message(f"Voce puxou {downed_member.name} de volta para a coluna.", duration=4.8)
            game.audio.play_interact("repair")
            return

        for interest_point in game.interest_points:
            if interest_point.resolved:
                continue
            distance = self.distance_to(interest_point.pos)
            if distance < max(best_distance, interest_point.radius + 26):
                game.audio.play_interact()
                game.resolve_interest_point(interest_point)
                return

        for node in game.resource_nodes:
            distance = self.distance_to(node.pos)
            if distance < best_distance and node.is_available():
                harvested = node.harvest()
                if harvested:
                    bundle = game.add_resource_bundle(game.resource_node_bundle(node))
                    color = PALETTE["heal"] if node.kind == "food" else ROLE_COLORS["mensageiro"]
                    game.spawn_floating_text(game.bundle_summary(bundle or game.resource_node_bundle(node)), node.pos, color)
                    game.emit_embers(node.pos, 3, smoky=True)
                    game.audio.play_interact()
                    acted = True
                    break

        if acted:
            return

        for barricade in game.barricades:
            distance = self.distance_to(barricade.pos)
            if distance < best_distance and barricade.health < barricade.max_health and game.wood >= 1:
                game.wood -= 1
                barricade.repair(24)
                game.spawn_floating_text("barricada reforcada", barricade.pos, PALETTE["heal"])
                game.audio.play_interact()
                acted = True
                break

        if acted:
            return

        if self.distance_to(game.workshop_pos) < 108:
            if game.expand_camp():
                game.audio.play_interact("repair")
                return
            if game.camp_level < game.max_camp_level:
                log_cost, scrap_cost = game.expansion_cost()
                game.spawn_floating_text(
                    f"oficina pede {log_cost} toras e {scrap_cost} sucata",
                    game.workshop_pos,
                    PALETTE["muted"],
                )
                return

        sleep_slot = game.nearest_sleep_slot(self.pos)
        if sleep_slot and not game.player_sleeping:
            if not game.active_dynamic_events:
                game.begin_player_sleep(sleep_slot)
                game.audio.play_interact("bonfire")
                return
            game.spawn_floating_text("ha crise demais para dormir", self.pos, PALETTE["danger_soft"])
            game.audio.play_alert()
            return

        if self.distance_to(game.bonfire_pos) < 100 and game.available_fuel() >= 1:
            fed, label, color = game.add_fuel_to_bonfire()
            if not fed:
                return
            for survivor in game.survivors:
                if survivor.distance_to(game.bonfire_pos) < 170:
                    survivor.morale = clamp(survivor.morale + 3.5, 0, 100)
                    game.adjust_trust(survivor, 1.1)
            game.spawn_floating_text(label, game.bonfire_pos, color)
            game.emit_embers(game.bonfire_pos, 12)
            game.audio.play_interact()
            return

        infirmary = game.nearest_building_of_kind("enfermaria", self.pos)
        if infirmary and self.distance_to(infirmary.pos) < 96 and game.has_medical_supplies() and self.health < self.max_health - 8:
            if game.medicine > 0:
                game.medicine -= 1
                self.health = clamp(self.health + 26, 0, self.max_health)
                game.spawn_floating_text("curativo pesado", infirmary.pos, PALETTE["heal"])
            elif game.herbs > 0:
                game.herbs -= 1
                self.health = clamp(self.health + 14, 0, self.max_health)
                game.spawn_floating_text("ervas medicinais", infirmary.pos, PALETTE["heal"])
            game.audio.play_interact("repair")
            return

        if self.distance_to(game.radio_pos) < 104:
            if game.active_expedition:
                if hardline:
                    recalled, message = game.recall_active_expedition()
                    game.spawn_floating_text("recolha" if recalled else "aguarde", game.radio_pos, PALETTE["morale"] if recalled else PALETTE["muted"])
                    if recalled:
                        game.audio.play_ui("order")
                    else:
                        game.audio.play_alert()
                    if message:
                        game.set_event_message(message, duration=4.8)
                    return
                status = game.expedition_status_text(short=False) or "A equipe esta fora da base."
                game.set_event_message(status, duration=5.0)
                game.spawn_floating_text("expedicao", game.radio_pos, PALETTE["accent_soft"])
                game.audio.play_ui("focus")
                return
            launched, message = game.launch_best_expedition()
            game.spawn_floating_text("expedicao" if launched else "sem equipe", game.radio_pos, PALETTE["accent_soft"] if launched else PALETTE["danger_soft"])
            if launched:
                game.audio.play_ui("order")
            else:
                game.audio.play_alert()
            if message:
                game.set_event_message(message, duration=4.8)
            return

        for survivor in game.survivors:
            if survivor.distance_to(self.pos) < best_distance:
                survivor.morale = clamp(survivor.morale + 7, 0, 100)
                survivor.energy = clamp(survivor.energy + 4, 0, 100)
                trust_gain = 5.0 if survivor.has_trait("leal") else 3.2
                if survivor.has_trait("teimoso"):
                    trust_gain -= 1.0
                game.adjust_trust(survivor, trust_gain)
                game.spawn_floating_text("ordem firme", survivor.pos, PALETTE["accent_soft"])
                game.audio.play_ui("order")
                return


class Survivor(Actor):
    def __init__(
        self,
        name: str,
        role: str,
        pos: Vector2,
        home_pos: Vector2,
        guard_pos: Vector2,
        traits: tuple[str, ...] = (),
    ) -> None:
        super().__init__(pos, radius=15, speed=126, health=100)
        self.name = name
        self.role = role
        self.color = ROLE_COLORS[role]
        self.traits = traits
        self.home_pos = Vector2(home_pos)
        self.guard_pos = Vector2(guard_pos)
        self.state = "idle"
        self.state_label = "avaliando"
        self.task_timer = 0.0
        self.decision_timer = random.uniform(0.2, 1.8)
        self.hunger = random.uniform(10, 24)
        self.energy = random.uniform(68, 90)
        self.morale = random.uniform(66, 84)
        self.attack_cooldown = 0.0
        self.carry_bundle: dict[str, int] = {}
        self.target_pos = Vector2(pos)
        self.target_ref: object | None = None
        self.blink = random.random() * math.tau
        self.sleep_shift = random.randint(0, 2)
        self.sleep_debt = random.uniform(8, 18)
        self.exhaustion = random.uniform(10, 24)
        self.insanity = random.uniform(6, 18)
        trust_base = 66 + (8 if "leal" in traits else 0) - (10 if "paranoico" in traits else 0)
        self.trust_leader = clamp(trust_base + random.uniform(-8, 8), 10, 100)
        self.relations: dict[str, float] = {}
        self.conflict_cooldown = 0.0
        self.bond_cooldown = 0.0
        self.assigned_tent_index = 0
        self.sleep_slot_kind = "tent"
        self.sleep_slot_building_uid: int | None = None
        self.assigned_building_id: int | None = None
        self.assigned_building_kind: str | None = None
        self.on_expedition = False
        self.expedition_downed = False
        self.expedition_attack_cooldown = 0.0

    def has_trait(self, trait: str) -> bool:
        return trait in self.traits

    def primary_trait(self) -> str:
        return self.traits[0] if self.traits else "estavel"

    def update(self, game: "Game", dt: float) -> None:
        if not self.is_alive():
            return
        if game.is_survivor_on_expedition(self):
            self.state = "expedition"
            if self.expedition_downed:
                self.state_label = "caido na trilha"
            else:
                self.state_label = "em expedicao"
            self.velocity *= 0.0
            return

        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.decision_timer -= dt
        self.blink += dt * 3.0
        self.conflict_cooldown = max(0.0, self.conflict_cooldown - dt)
        self.bond_cooldown = max(0.0, self.bond_cooldown - dt)

        hunger_rate = 1.9 if game.is_night else 1.2
        self.hunger = clamp(self.hunger + hunger_rate * dt, 0, 100)
        effort_states = {"gather_wood", "forage", "scavenge", "repair", "sawmill", "workbench", "guard", "watchtower"}
        effort_load = 0.38 if self.state in effort_states else 0.0
        if self.has_trait("resiliente"):
            effort_load *= 0.78
        if self.has_trait("teimoso"):
            effort_load *= 1.12

        exhaustion_delta = (0.34 if game.is_night else 0.16) + self.sleep_debt * 0.004 + effort_load
        if self.state in {"sleep", "rest", "treatment"}:
            exhaustion_delta -= 1.05
        elif self.state in {"socialize", "eat", "shelter"}:
            exhaustion_delta -= 0.24
        self.exhaustion = clamp(self.exhaustion + exhaustion_delta * dt, 0, 100)

        energy_drain = (0.62 if game.is_night else 0.34) + self.sleep_debt * 0.003 + self.exhaustion * 0.0042
        self.energy = clamp(self.energy - energy_drain * dt, 0, 100)
        if self.state in {"sleep", "rest", "shelter"} and self.distance_to(self.home_pos) < 28:
            self.sleep_debt = clamp(self.sleep_debt - 2.6 * dt, 0, 100)
        elif game.is_night:
            self.sleep_debt = clamp(self.sleep_debt + 0.85 * dt, 0, 100)
        else:
            self.sleep_debt = clamp(self.sleep_debt - 0.18 * dt, 0, 100)

        bonfire_safety = game.bonfire_heat * 0.6 + game.bonfire_ember_bed * 0.4
        if game.is_night and bonfire_safety < 22 and self.distance_to(game.bonfire_pos) > 180:
            self.morale = clamp(self.morale - 0.7 * dt, 0, 100)
        else:
            self.morale = clamp(self.morale - 0.18 * dt, 0, 100)
        insanity_delta = 0.0
        if game.is_night:
            insanity_delta += 0.16
        if bonfire_safety < 22:
            insanity_delta += 0.12
        if self.exhaustion > 70:
            insanity_delta += 0.2
        if self.morale < 42:
            insanity_delta += 0.18
        if self.has_trait("paranoico"):
            insanity_delta += 0.16
        if self.has_trait("gentil"):
            insanity_delta -= 0.05
        if self.state in {"sleep", "rest", "socialize", "eat"}:
            insanity_delta -= 0.18
        if self.distance_to(game.player.pos) < 160:
            insanity_delta -= 0.08
        if game.find_closest_zombie(self.pos, 180):
            insanity_delta += 0.2
        self.insanity = clamp(self.insanity + insanity_delta * dt, 0, 100)

        if self.health <= 30:
            self.morale = clamp(self.morale - 0.25 * dt, 0, 100)
        if self.exhaustion > 72:
            self.morale = clamp(self.morale - 0.22 * dt, 0, 100)
            self.trust_leader = clamp(self.trust_leader - 0.1 * dt, 0, 100)
        elif self.has_trait("leal") and game.player.distance_to(self.pos) < 180:
            self.trust_leader = clamp(self.trust_leader + 0.08 * dt, 0, 100)

        zombie = game.find_closest_zombie(self.pos, 115)
        if zombie and self.attack_cooldown <= 0:
            zombie.health -= 16
            zombie.stagger = 0.1
            self.attack_cooldown = 0.9
            self.state_label = "combatendo"
            game.damage_pulses.append(
                DamagePulse(Vector2(zombie.pos), 10, 0.22, PALETTE["accent_soft"])
            )
            game.audio.play_impact("flesh")
            return

        crisis = game.dynamic_event_for_survivor(self)
        if crisis and crisis.kind in {"fuga", "desercao"}:
            self.state_label = "em fuga" if crisis.kind == "fuga" else "desertando"
            self.move_toward(crisis.pos, dt, 1.12 if crisis.kind == "desercao" else 1.04)
            self.energy = clamp(self.energy - 0.35 * dt, 0, 100)
            self.morale = clamp(self.morale - 0.18 * dt, 0, 100)
            return
        if crisis and crisis.kind == "doenca":
            self.state_label = "febril"
            self.health = clamp(self.health - 0.15 * dt, 0, self.max_health)
            self.energy = clamp(self.energy - 0.2 * dt, 0, 100)
            self.morale = clamp(self.morale - 0.08 * dt, 0, 100)

        if self.decision_timer <= 0:
            self.choose_next_task(game)
            self.decision_timer = random.uniform(2.8, 5.4)

        self.update_state(game, dt)

    def choose_next_task(self, game: "Game") -> None:
        if game.should_survivor_sleep(self):
            self.start_state("sleep", self.home_pos)
            return
        if self.insanity > 84:
            self.start_state("wander", game.camp_perimeter_point(self.assigned_tent_index, jitter=42))
            return
        if self.insanity > 70 and game.is_night:
            self.start_state("guard", self.guard_pos)
            self.state_label = "rondando a base"
            return
        if self.exhaustion > 80:
            self.start_state("sleep" if game.is_night else "rest", self.home_pos)
            return
        if game.dynamic_event_for_survivor(self, "doenca") and game.can_treat_infirmary():
            infirmary = game.nearest_building_of_kind("enfermaria", self.pos)
            if infirmary:
                self.start_state("treatment", infirmary.pos, infirmary)
                return
        assigned_building = game.building_by_id(self.assigned_building_id)
        if assigned_building and self.assigned_building_kind == "horta" and not game.is_night and self.energy > 28:
            self.start_state("garden", assigned_building.pos, assigned_building)
            return
        if assigned_building and self.assigned_building_kind == "anexo" and game.has_damaged_barricade() and self.energy > 28:
            self.start_state("workbench", assigned_building.pos, assigned_building)
            return
        if assigned_building and self.assigned_building_kind == "serraria" and game.logs >= 2 and self.energy > 28:
            self.start_state("sawmill", assigned_building.pos, assigned_building)
            return
        if assigned_building and self.assigned_building_kind == "cozinha" and game.food >= 2 and game.available_fuel() > 0 and self.energy > 26:
            self.start_state("cookhouse", assigned_building.pos, assigned_building)
            return
        if assigned_building and self.assigned_building_kind == "enfermaria" and (game.most_injured_actor() or game.herbs > 0) and self.energy > 24:
            self.start_state("clinic", assigned_building.pos, assigned_building)
            return
        if game.available_fuel() > 0 and (
            (game.is_night and game.bonfire_heat < 38)
            or game.bonfire_ember_bed < 20
            or (game.focus_mode == "morale" and game.bonfire_heat < 60)
        ):
            self.start_state("tend_fire", game.bonfire_pos)
            return
        if self.hunger > 70 and (game.food > 0 or game.meals > 0):
            self.start_state("eat", game.kitchen_pos)
            return
        if self.health < 52 and game.can_treat_infirmary():
            infirmary = game.nearest_building_of_kind("enfermaria", self.pos)
            if infirmary:
                self.start_state("treatment", infirmary.pos, infirmary)
                return
        if self.energy < 26 or self.health < 28 or self.exhaustion > 68:
            self.start_state("rest", self.home_pos)
            return
        if game.is_night:
            if assigned_building and self.assigned_building_kind == "torre" and self.name in game.active_guard_names() and self.energy > 22:
                self.start_state("watchtower", assigned_building.pos, assigned_building)
            elif self.name in game.active_guard_names() and self.energy > 22:
                self.start_state("guard", self.guard_pos)
            else:
                self.start_state("sleep", self.home_pos)
            return

        options = {
            "gather_wood": 1.0 if game.available_node("wood") else -999,
            "forage": 1.0 if game.available_node("food") else -999,
            "scavenge": 0.8 if game.available_node("scrap") else -999,
            "repair": 0.7 if game.has_damaged_barricade() and game.wood > 0 else -999,
            "cook": 0.6 if game.food > 0 and game.available_fuel() > 0 else -999,
            "sawmill": 0.7 if game.logs >= 2 else -999,
            "clinic": 0.6 if game.most_injured_actor() and game.has_medical_supplies() else -999,
            "tend_fire": 0.5 if game.available_fuel() > 0 else -999,
            "socialize": 0.5,
            "guard": 0.3,
        }

        if game.logs < 12:
            options["gather_wood"] += 2.6
        if game.wood < 14:
            options["sawmill"] += 2.5
        if game.food < 14:
            options["forage"] += 2.4
        if game.meals < 8:
            options["cook"] += 2.2
        if game.scrap < 8:
            options["scavenge"] += 1.7
        if game.weakest_barricade_health() < 60:
            options["repair"] += 2.9
        if game.average_morale() < 56:
            options["cook"] += 1.4
            options["socialize"] += 2.2
        if game.average_health() < 72:
            options["clinic"] += 2.3
        if game.bonfire_heat < 34:
            options["tend_fire"] += 3.2
        elif game.bonfire_ember_bed < 20:
            options["tend_fire"] += 2.1
        if self.exhaustion > 58:
            options["socialize"] -= 0.8
            options["guard"] -= 0.8
            options["gather_wood"] -= 1.2
            options["repair"] -= 1.0
            options["sawmill"] -= 0.9

        command_factor = 0.45 + self.trust_leader / 100
        if self.has_trait("leal"):
            command_factor += 0.18
        if self.has_trait("teimoso"):
            command_factor -= 0.1
        if game.focus_mode == "supply":
            options["gather_wood"] += 2.4 * command_factor
            options["forage"] += 2.2 * command_factor
            options["scavenge"] += 2.0 * command_factor
            options["sawmill"] += 1.8 * command_factor
            options["cook"] += 1.1 * command_factor
        elif game.focus_mode == "fortify":
            options["repair"] += 3.0 * command_factor
            options["guard"] += 1.5 * command_factor
        elif game.focus_mode == "morale":
            options["cook"] += 2.5 * command_factor
            options["tend_fire"] += 2.8 * command_factor
            options["socialize"] += 2.8 * command_factor
            options["clinic"] += 1.4 * command_factor

        if self.has_trait("corajoso"):
            options["guard"] += 1.9
        if self.has_trait("sociavel"):
            options["socialize"] += 2.3
            options["cook"] += 0.8
        if self.has_trait("paranoico"):
            options["guard"] += 1.6
            options["socialize"] -= 1.4
        if self.has_trait("gentil"):
            options["clinic"] += 1.7
            options["cook"] += 0.9
        if self.has_trait("rancoroso"):
            options["socialize"] -= 1.8
            options["guard"] += 0.6
        if self.has_trait("teimoso"):
            options["repair"] += 1.3
            options["gather_wood"] += 0.9

        preferred = {
            "lenhador": "gather_wood",
            "vigia": "guard",
            "batedora": "forage",
            "artesa": "repair",
            "cozinheiro": "cook",
            "mensageiro": "clinic",
        }[self.role]
        options[preferred] += 2.1

        choice = max(options.items(), key=lambda item: item[1] + random.uniform(-0.35, 0.35))[0]

        if choice == "gather_wood":
            node = game.closest_available_node("wood", self.pos)
            if node:
                target_pos = Vector2(node["pos"]) if isinstance(node, dict) else node.pos
                self.start_state("gather_wood", target_pos, node)
                return
        if choice == "forage":
            node = game.closest_available_node("food", self.pos)
            if node:
                self.start_state("forage", node.pos, node)
                return
        if choice == "scavenge":
            node = game.closest_available_node("scrap", self.pos)
            if node:
                self.start_state("scavenge", node.pos, node)
                return
        if choice == "repair":
            barricade = game.weakest_barricade()
            if barricade:
                self.start_state("repair", barricade.pos, barricade)
                return
        if choice == "cook":
            self.start_state("cook", game.kitchen_pos)
            return
        if choice == "sawmill":
            sawmill = game.nearest_building_of_kind("serraria", self.pos)
            if sawmill:
                self.start_state("sawmill", sawmill.pos, sawmill)
                return
        if choice == "clinic":
            infirmary = game.nearest_building_of_kind("enfermaria", self.pos)
            if infirmary:
                self.start_state("clinic", infirmary.pos, infirmary)
                return
        if choice == "tend_fire":
            self.start_state("tend_fire", game.bonfire_pos)
            return
        if choice == "guard":
            self.start_state("guard", self.guard_pos)
            return
        self.start_state("socialize", game.bonfire_pos)

    def start_state(self, state: str, target: Vector2, ref: object | None = None) -> None:
        self.state = state
        self.target_pos = Vector2(target)
        self.target_ref = ref
        self.task_timer = 0.0
        labels = {
            "gather_wood": "coletando madeira",
            "forage": "forrageando",
            "scavenge": "buscando sucata",
            "repair": "reforcando palicadas",
            "cook": "organizando a cozinha",
            "cookhouse": "na cozinha",
            "socialize": "subindo a moral",
            "tend_fire": "cuidando do fogo",
            "guard": "de vigia",
            "watchtower": "na torre",
            "garden": "cuidando da horta",
            "workbench": "na oficina",
            "sawmill": "na serraria",
            "clinic": "na enfermaria",
            "rest": "descansando",
            "sleep": "dormindo",
            "eat": "comendo",
            "treatment": "em tratamento",
            "shelter": "protegido na tenda",
            "deliver": "levando suprimentos",
            "wander": "rondando a base",
        }
        self.state_label = labels.get(state, state)

    def update_state(self, game: "Game", dt: float) -> None:
        if self.state in {"gather_wood", "forage", "scavenge"}:
            if self.move_toward(self.target_pos, dt):
                if self.state == "gather_wood":
                    tree = self.target_ref if isinstance(self.target_ref, dict) else None
                    if not tree or not game.tree_is_harvestable(tree):
                        self.decision_timer = 0
                        return
                    self.task_timer += dt
                    if self.task_timer >= 4.2:
                        amount = game.harvest_tree(tree, effort=2)
                        if amount:
                            self.carry_bundle = {"logs": amount}
                            self.start_state("deliver", game.stockpile_pos)
                            self.state_label = "arrastando toras"
                            game.audio.play_impact("wood")
                        else:
                            self.task_timer = 0.0
                            self.state_label = "derrubando a arvore"
                    return

                node = self.target_ref if isinstance(self.target_ref, ResourceNode) else None
                if not node or not node.is_available():
                    self.decision_timer = 0
                    return
                self.task_timer += dt
                if self.task_timer >= 3.2:
                    amount = node.harvest()
                    if amount:
                        self.carry_bundle = game.resource_node_bundle(node, role=self.role)
                        self.start_state("deliver", game.stockpile_pos)
                        self.state_label = "carregando suprimentos"
                    else:
                        self.decision_timer = 0
            return

        if self.state == "deliver":
            if self.move_toward(self.target_pos, dt, 1.1):
                stored = game.add_resource_bundle(self.carry_bundle)
                game.spawn_floating_text(
                    game.bundle_summary(stored or self.carry_bundle),
                    self.pos,
                    PALETTE["accent_soft"],
                )
                self.carry_bundle = {}
                self.decision_timer = 0
            return

        if self.state == "repair":
            barricade = self.target_ref if isinstance(self.target_ref, Barricade) else None
            if not barricade or game.wood <= 0:
                self.decision_timer = 0
                return
            if self.move_toward(barricade.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 2.4:
                    game.wood -= 1
                    barricade.repair(18)
                    game.spawn_floating_text("palicada arrumada", barricade.pos, PALETTE["heal"])
                    self.task_timer = 0
                    self.decision_timer = 0.4
            return

        if self.state == "cook":
            if self.move_toward(game.kitchen_pos, dt):
                self.task_timer += dt
                if self.task_timer >= 3.3 and game.food > 0 and game.available_fuel() > 0:
                    game.food -= 1
                    game.consume_fuel(1)
                    game.add_resource_bundle({"meals": 1})
                    for survivor in game.survivors:
                        survivor.morale = clamp(survivor.morale + 2.5, 0, 100)
                    game.spawn_floating_text("refeicao pronta", game.kitchen_pos, PALETTE["morale"])
                    self.task_timer = 0
                    self.decision_timer = 1.2
            return

        if self.state == "cookhouse":
            kitchen = self.target_ref if isinstance(self.target_ref, Building) else None
            if not kitchen or game.food < 2 or game.available_fuel() <= 0:
                self.decision_timer = 0
                return
            if self.move_toward(kitchen.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 3.8:
                    produced = game.cookhouse_output(self.role)
                    if game.consume_resource("food", 2) and game.consume_fuel(1):
                        game.add_resource_bundle({"meals": produced})
                        for survivor in game.survivors:
                            survivor.morale = clamp(survivor.morale + 3.0, 0, 100)
                        game.spawn_floating_text(f"+{produced} refeicoes", kitchen.pos, PALETTE["morale"])
                        self.task_timer = 0.2
                        self.decision_timer = 1.0
            return

        if self.state == "socialize":
            if self.move_toward(game.bonfire_pos, dt):
                self.task_timer += dt
                if self.task_timer >= 3.6:
                    for survivor in game.survivors:
                        if survivor.distance_to(game.bonfire_pos) < 200:
                            survivor.morale = clamp(survivor.morale + 2.6, 0, 100)
                            if survivor.is_alive():
                                game.adjust_relationship(self, survivor, 2.4 if self.has_trait("sociavel") else 1.4)
                    game.spawn_floating_text("historia no fogo", game.bonfire_pos, PALETTE["morale"])
                    self.task_timer = 0.2
            return

        if self.state == "tend_fire":
            if game.available_fuel() <= 0:
                self.decision_timer = 0
                return
            if self.move_toward(game.bonfire_pos, dt):
                self.task_timer += dt
                if self.task_timer >= 2.0:
                    fed, label, color = game.add_fuel_to_bonfire()
                    if fed:
                        game.spawn_floating_text(label, game.bonfire_pos, color)
                        for survivor in game.survivors:
                            if survivor.distance_to(game.bonfire_pos) < 160:
                                survivor.morale = clamp(survivor.morale + 1.6, 0, 100)
                        game.emit_embers(game.bonfire_pos, 8)
                        game.audio.play_interact()
                    self.task_timer = 0.0
                    self.decision_timer = 2.4
            return

        if self.state == "watchtower":
            tower = self.target_ref if isinstance(self.target_ref, Building) else None
            if not tower:
                self.decision_timer = 0
                return
            if self.move_toward(tower.pos, dt):
                zombie = game.find_closest_zombie(tower.pos, 240)
                if zombie and self.attack_cooldown <= 0:
                    zombie.health -= 22
                    zombie.stagger = 0.15
                    self.attack_cooldown = 0.95
                    game.damage_pulses.append(DamagePulse(Vector2(zombie.pos), 12, 0.22, PALETTE["accent_soft"]))
                    game.spawn_floating_text("vigia", tower.pos, PALETTE["energy"])
                    game.audio.play_impact("body")
            return

        if self.state == "garden":
            garden = self.target_ref if isinstance(self.target_ref, Building) else None
            if not garden:
                self.decision_timer = 0
                return
            if self.move_toward(garden.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 4.8:
                    bundle = game.garden_harvest_bundle(self.role)
                    game.add_resource_bundle(bundle)
                    game.spawn_floating_text("colheita", garden.pos, PALETTE["heal"])
                    self.task_timer = 0.6
                    self.decision_timer = 1.8
            return

        if self.state == "workbench":
            workshop = self.target_ref if isinstance(self.target_ref, Building) else None
            weakest = game.weakest_barricade()
            if not workshop or not weakest or game.wood <= 0:
                self.decision_timer = 0
                return
            if self.move_toward(workshop.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 4.0:
                    game.wood -= 1
                    if game.scrap > 0:
                        game.scrap -= 1
                        weakest.repair(game.workbench_repair_amount())
                    else:
                        weakest.repair(game.workbench_repair_amount() * 0.7)
                    game.spawn_floating_text("kit de reparo", weakest.pos, PALETTE["heal"])
                    game.audio.play_interact("repair")
                    self.task_timer = 0.0
                    self.decision_timer = 1.2
            return

        if self.state == "sawmill":
            sawmill = self.target_ref if isinstance(self.target_ref, Building) else None
            if not sawmill or game.logs < 2:
                self.decision_timer = 0
                return
            if self.move_toward(sawmill.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 4.0:
                    produced = game.sawmill_output(self.role)
                    if game.consume_resource("logs", 2):
                        game.add_resource_bundle({"wood": produced})
                        game.spawn_floating_text(f"+{produced} tabuas", sawmill.pos, PALETTE["accent_soft"])
                        game.audio.play_interact("repair")
                        self.task_timer = 0.0
                        self.decision_timer = 1.0
            return

        if self.state == "clinic":
            infirmary = self.target_ref if isinstance(self.target_ref, Building) else None
            if not infirmary:
                self.decision_timer = 0
                return
            if self.move_toward(infirmary.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 3.6:
                    target = game.most_injured_actor()
                    if target and game.medicine > 0:
                        game.medicine -= 1
                        target.health = clamp(target.health + 24, 0, target.max_health)
                        if isinstance(target, Survivor):
                            target.morale = clamp(target.morale + 3, 0, 100)
                        game.spawn_floating_text("tratamento", infirmary.pos, PALETTE["heal"])
                    elif target and game.herbs > 0:
                        game.herbs -= 1
                        target.health = clamp(target.health + 14, 0, target.max_health)
                        game.spawn_floating_text("ervas", infirmary.pos, PALETTE["heal"])
                    elif game.herbs > 0 and game.scrap > 0:
                        game.herbs -= 1
                        game.scrap -= 1
                        produced = game.clinic_medicine_output()
                        game.add_resource_bundle({"medicine": produced})
                        game.spawn_floating_text(f"+{produced} remedio", infirmary.pos, PALETTE["heal"])
                    self.task_timer = 0.0
                    self.decision_timer = 1.2
            return

        if self.state == "treatment":
            infirmary = self.target_ref if isinstance(self.target_ref, Building) else None
            if not infirmary:
                self.decision_timer = 0
                return
            if self.move_toward(infirmary.pos, dt):
                self.task_timer += dt
                if self.task_timer >= 2.6:
                    if game.medicine > 0:
                        game.medicine -= 1
                        self.health = clamp(self.health + 20, 0, self.max_health)
                    elif game.herbs > 0:
                        game.herbs -= 1
                        self.health = clamp(self.health + 12, 0, self.max_health)
                    self.energy = clamp(self.energy + 6, 0, 100)
                    self.morale = clamp(self.morale + 3, 0, 100)
                    self.decision_timer = 0
            return

        if self.state == "guard":
            self.move_toward(self.guard_pos, dt)
            return

        if self.state == "wander":
            if self.move_toward(self.target_pos, dt, 0.92):
                self.morale = clamp(self.morale - 0.4 * dt, 0, 100)
                if self.task_timer <= 0:
                    self.target_pos = game.camp_perimeter_point(self.assigned_tent_index + random.randint(0, 3), jitter=58)
                    self.task_timer = 2.4
                else:
                    self.task_timer = max(0.0, self.task_timer - dt)
                if self.insanity < 58:
                    self.decision_timer = 0
            return

        if self.state == "sleep":
            if self.move_toward(self.home_pos, dt):
                self.energy = clamp(self.energy + 24 * dt, 0, 100)
                self.health = clamp(self.health + 5 * dt, 0, self.max_health)
                self.morale = clamp(self.morale + 1.4 * dt, 0, 100)
                self.exhaustion = clamp(self.exhaustion - 22 * dt, 0, 100)
                if self.energy >= 84 and self.sleep_debt <= 12:
                    self.decision_timer = 0
            return

        if self.state == "rest":
            if self.move_toward(self.home_pos, dt):
                self.energy = clamp(self.energy + 18 * dt, 0, 100)
                self.health = clamp(self.health + 6 * dt, 0, self.max_health)
                self.morale = clamp(self.morale + 2 * dt, 0, 100)
                self.exhaustion = clamp(self.exhaustion - 14 * dt, 0, 100)
                if self.energy >= 72:
                    self.decision_timer = 0
            return

        if self.state == "eat":
            if self.move_toward(game.kitchen_pos, dt):
                self.task_timer += dt
                if self.task_timer >= 1.4:
                    if game.meals > 0:
                        game.meals -= 1
                        self.hunger = clamp(self.hunger - 42, 0, 100)
                    elif game.food > 0:
                        game.food -= 1
                        self.hunger = clamp(self.hunger - 25, 0, 100)
                    self.energy = clamp(self.energy + 6, 0, 100)
                    self.morale = clamp(self.morale + 4, 0, 100)
                    self.exhaustion = clamp(self.exhaustion - 5, 0, 100)
                    if self.health < self.max_health - 10 and game.herbs > 0:
                        game.herbs -= 1
                        self.health = clamp(self.health + 8, 0, self.max_health)
                    self.decision_timer = 0
            return

        if self.state == "shelter":
            self.move_toward(self.home_pos, dt)
            if self.distance_to(self.home_pos) < 24:
                self.energy = clamp(self.energy + 10 * dt, 0, 100)
                self.morale = clamp(self.morale + 1 * dt, 0, 100)
            return

        self.decision_timer = 0


class Zombie(Actor):
    def __init__(self, pos: Vector2, day: int, *, boss_profile: dict[str, object] | None = None) -> None:
        base_speed = 82 + day * 4.2
        base_health = 82 + day * 10
        radius = 16.0
        self.variant = "walker"
        self.weapon_name = ""
        if boss_profile:
            radius = float(boss_profile.get("radius", 28))
            base_speed = float(boss_profile.get("speed", base_speed * 0.92))
            base_health = float(boss_profile.get("health", base_health * 4.2))
        super().__init__(pos, radius=radius, speed=base_speed, health=base_health)
        self.attack_cooldown = 0.0
        self.stagger = 0.0
        self.shamble = random.random() * math.tau
        self.day = day
        self.is_boss = boss_profile is not None
        self.boss_name = str(boss_profile.get("name", "")) if boss_profile else ""
        self.zone_key = tuple(boss_profile.get("zone_key", ())) if boss_profile else ()
        self.zone_label = str(boss_profile.get("zone_label", "")) if boss_profile else ""
        self.anchor = Vector2(boss_profile.get("anchor", pos)) if boss_profile else Vector2(pos)
        self.boss_body = tuple(boss_profile.get("body", (108, 128, 82))) if boss_profile else (108, 128, 82)
        self.boss_accent = tuple(boss_profile.get("accent", (54, 62, 44))) if boss_profile else (54, 62, 44)
        self.contact_damage = float(boss_profile.get("damage", 13 + day * 1.0)) if boss_profile else 13 + day * 1.0
        self.summon_cooldown = random.uniform(5.6, 8.8) if self.is_boss else 0.0
        self.death_processed = False
        self.alert_radius = 240.0
        self.pursuit_timer = 0.0
        self.howl_cooldown = random.uniform(7.0, 11.5)
        self.camp_pressure = random.uniform(0.4, 1.0)
        if not self.is_boss:
            roll = random.random()
            if roll < 0.17:
                self.variant = "runner"
                self.speed *= 1.24
                self.max_health *= 0.92
                self.health = self.max_health
                self.contact_damage *= 1.05
                self.alert_radius = 280
            elif roll < 0.3:
                self.variant = "brute"
                self.radius = 20
                self.speed *= 0.82
                self.max_health *= 1.55
                self.health = self.max_health
                self.contact_damage *= 1.5
                self.alert_radius = 220
            elif roll < 0.42:
                self.variant = "howler"
                self.speed *= 0.96
                self.max_health *= 1.08
                self.health = self.max_health
                self.alert_radius = 300
                self.howl_cooldown = random.uniform(4.8, 7.2)
            elif roll < 0.56:
                self.variant = "raider"
                self.speed *= 1.05
                self.max_health *= 1.12
                self.health = self.max_health
                self.contact_damage *= 1.24
                self.weapon_name = random.choice(("cano", "machado", "barra"))
                self.alert_radius = 260
        else:
            self.variant = str(boss_profile.get("variant", "boss"))
            self.weapon_name = str(boss_profile.get("weapon", "garras"))
            self.alert_radius = float(boss_profile.get("alert_radius", 340))

    def update(self, game: "Game", dt: float) -> None:
        if not self.is_alive():
            return
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.stagger = max(0.0, self.stagger - dt)
        self.pursuit_timer = max(0.0, self.pursuit_timer - dt)
        self.howl_cooldown = max(0.0, self.howl_cooldown - dt)
        self.shamble += dt * 3.0
        if self.is_boss:
            self.summon_cooldown = max(0.0, self.summon_cooldown - dt)
            if self.summon_cooldown <= 0 and self.distance_to(game.player.pos) < 340 and len(game.zombies) < 26:
                game.spawn_local_zombies(self.pos, 2, pressure=True)
                game.spawn_floating_text("eco da zona", self.pos, PALETTE["danger_soft"])
                game.screen_shake = max(game.screen_shake, 3.8)
                self.summon_cooldown = random.uniform(6.2, 9.4)
                if self.zone_key in game.named_regions:
                    game.named_regions[self.zone_key]["boss_active"] = True

        target_actor: Actor | None = game.closest_target(self.pos)
        nearest_barricade = game.closest_barricade(self.pos)
        target_visible = False
        if target_actor and self.distance_to(target_actor.pos) < self.alert_radius:
            self.pursuit_timer = max(self.pursuit_timer, 4.4 if self.variant == "runner" else 3.2)
            target_visible = True
        if self.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 240:
            self.pursuit_timer = max(self.pursuit_timer, 2.8 + self.camp_pressure * 1.8)
        if (
            self.howl_cooldown <= 0
            and len(game.zombies) < 30
            and (target_visible or self.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 140)
            and (self.variant in {"howler", "raider"} or self.is_boss)
        ):
            game.spawn_local_zombies(self.pos, 1 if self.variant != "howler" else 2, pressure=True)
            game.spawn_floating_text("chamado podre", self.pos, PALETTE["danger_soft"])
            self.howl_cooldown = random.uniform(4.8, 7.2) if self.variant == "howler" else random.uniform(7.5, 11.0)

        if nearest_barricade and not nearest_barricade.is_broken() and not game.point_in_camp_square(self.pos, padding=-40):
            barricade_scale = 0.98 if self.pursuit_timer > 0 else 0.78
            if self.move_toward(nearest_barricade.pos, dt, barricade_scale if self.stagger <= 0 else barricade_scale * 0.46):
                if self.attack_cooldown <= 0:
                    impact = 8 + self.day * 0.85
                    if self.is_boss:
                        impact *= 2.1
                    elif self.variant == "brute":
                        impact *= 1.55
                    elif self.variant == "raider":
                        impact *= 1.26
                    nearest_barricade.damage(impact)
                    self.attack_cooldown = 0.82 if self.is_boss else (0.9 if self.variant in {"runner", "raider"} else 1.05)
                    game.damage_pulses.append(
                        DamagePulse(Vector2(nearest_barricade.pos), 14, 0.24, PALETTE["danger"])
                    )
                    game.audio.play_impact("wood")
            return

        if target_actor and (target_visible or self.pursuit_timer > 0):
            speed_scale = 0.98 if self.is_boss else 0.9
            if self.variant == "runner":
                speed_scale = 1.12
            elif self.variant == "brute":
                speed_scale = 0.82
            if self.move_toward(target_actor.pos, dt, speed_scale if self.stagger <= 0 else speed_scale * 0.5):
                if self.attack_cooldown <= 0:
                    target_actor.health -= self.contact_damage
                    self.attack_cooldown = 0.88 if self.is_boss else (0.9 if self.variant == "runner" else 1.1)
                    game.damage_pulses.append(
                        DamagePulse(Vector2(target_actor.pos), 12, 0.24, PALETTE["danger_soft"])
                    )
                    game.audio.play_impact("body")
                    if isinstance(target_actor, Survivor):
                        target_actor.morale = clamp(target_actor.morale - (18 if self.is_boss else 12), 0, 100)
                        if hasattr(target_actor, "insanity"):
                            target_actor.insanity = clamp(target_actor.insanity + (12 if self.is_boss else 7), 0, 100)
                    else:
                        game.screen_shake = max(game.screen_shake, 6.2 if self.is_boss else 4.5)
            return

        if self.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 260 or self.camp_pressure > 0.7:
            ring = game.camp_clearance_radius() * (0.86 + 0.22 * self.camp_pressure)
            roam = CAMP_CENTER + angle_to_vector(self.shamble) * ring
            self.move_toward(roam, dt, 0.62 if self.variant == "runner" else 0.56)
            return

        roam_center = self.anchor if self.is_boss else self.anchor.lerp(CAMP_CENTER, 0.22)
        roam_radius = 160 if self.is_boss else 190 + self.camp_pressure * 80
        roam = roam_center + angle_to_vector(self.shamble) * roam_radius
        self.move_toward(roam, dt, 0.54 if self.is_boss else 0.58)
