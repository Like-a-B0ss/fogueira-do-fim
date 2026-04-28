from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from pygame import Vector2

from ..core.config import PALETTE, ROLE_COLORS, clamp
from ..domain.combat import player_actions, survivor_behavior, zombie_behavior

if TYPE_CHECKING:
    from ..app.session import Game


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
        self.hurt_flash = 0.0
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
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.interact_cooldown = max(0.0, self.interact_cooldown - dt)

    def perform_attack(self, game: "Game") -> None:
        player_actions.perform_attack(self, game)

    def perform_interaction(self, game: "Game", *, hardline: bool = False) -> None:
        player_actions.perform_interaction(self, game, hardline=hardline)

    def perform_mouse_interaction(
        self,
        game: "Game",
        *,
        target_override: dict[str, object] | None = None,
        hardline: bool = False,
    ) -> None:
        player_actions.perform_mouse_interaction(
            self,
            game,
            target_override=target_override,
            hardline=hardline,
        )


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
        self.leader_directive: str | None = None
        self.leader_directive_timer = 0.0
        self.bark_text = ""
        self.bark_timer = 0.0
        self.bark_color = PALETTE["text"]
        self.bark_cooldown = random.uniform(2.5, 5.5)
        self.build_request_cooldown = random.uniform(18.0, 34.0)
        self.social_memories: list[dict[str, object]] = []
        self.social_comment_cooldown = random.uniform(8.0, 16.0)

    def has_trait(self, trait: str) -> bool:
        return survivor_behavior.has_trait(self, trait)

    def primary_trait(self) -> str:
        return survivor_behavior.primary_trait(self)

    def update(self, game: "Game", dt: float) -> None:
        survivor_behavior.update_survivor(self, game, dt)

    def choose_next_task(self, game: "Game") -> None:
        survivor_behavior.choose_next_task(self, game)

    def start_state(self, state: str, target: Vector2, ref: object | None = None) -> None:
        survivor_behavior.start_state(self, state, target, ref)

    def update_state(self, game: "Game", dt: float) -> None:
        survivor_behavior.update_state(self, game, dt)


class Zombie(Actor):
    def __init__(self, pos: Vector2, day: int, *, boss_profile: dict[str, object] | None = None) -> None:
        radius, base_speed, base_health = zombie_behavior.base_stats(day, boss_profile)
        super().__init__(pos, radius=radius, speed=base_speed, health=base_health)
        zombie_behavior.configure_zombie(self, pos, day, boss_profile=boss_profile)

    def update(self, game: "Game", dt: float) -> None:
        zombie_behavior.update_zombie(self, game, dt)
