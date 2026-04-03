from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from pygame import Vector2

from ...core.config import CAMP_CENTER, PALETTE, angle_to_vector, clamp
from ...core.models import DamagePulse

if TYPE_CHECKING:
    from ...app.session import Game


def base_stats(day: int, boss_profile: dict[str, object] | None = None) -> tuple[float, float, float]:
    base_speed = 76 + day * 3.1
    base_health = 72 + day * 8.0
    radius = 16.0
    if boss_profile:
        radius = float(boss_profile.get("radius", 28))
        base_speed = float(boss_profile.get("speed", base_speed * 0.92))
        base_health = float(boss_profile.get("health", base_health * 4.2))
    return radius, base_speed, base_health


def configure_zombie(zombie, pos: Vector2, day: int, *, boss_profile: dict[str, object] | None = None) -> None:
    zombie.attack_cooldown = 0.0
    zombie.stagger = 0.0
    zombie.shamble = random.random() * math.tau
    zombie.day = day
    zombie.is_boss = boss_profile is not None
    zombie.boss_name = str(boss_profile.get("name", "")) if boss_profile else ""
    zombie.zone_key = tuple(boss_profile.get("zone_key", ())) if boss_profile else ()
    zombie.zone_label = str(boss_profile.get("zone_label", "")) if boss_profile else ""
    zombie.anchor = Vector2(boss_profile.get("anchor", pos)) if boss_profile else Vector2(pos)
    zombie.boss_body = tuple(boss_profile.get("body", (108, 128, 82))) if boss_profile else (108, 128, 82)
    zombie.boss_accent = tuple(boss_profile.get("accent", (54, 62, 44))) if boss_profile else (54, 62, 44)
    zombie.contact_damage = (
        float(boss_profile.get("damage", 10.5 + day * 0.75)) if boss_profile else 10.5 + day * 0.75
    )
    zombie.summon_cooldown = random.uniform(5.6, 8.8) if zombie.is_boss else 0.0
    zombie.death_processed = False
    zombie.alert_radius = 240.0
    zombie.pursuit_timer = 0.0
    zombie.howl_cooldown = random.uniform(7.0, 11.5)
    zombie.camp_pressure = random.uniform(0.4, 1.0)
    zombie.charge_cooldown = 0.0
    zombie.charge_timer = 0.0
    zombie.slam_cooldown = 0.0
    zombie.enrage_level = 0
    zombie.visual_state = ""

    if zombie.is_boss:
        _configure_boss(zombie, boss_profile or {})
        return
    _configure_variant(zombie)


def update_zombie(zombie, game: "Game", dt: float) -> None:
    if not zombie.is_alive():
        return

    _tick_timers(zombie, dt)
    _update_boss_state(zombie, game, dt)

    target_actor = game.closest_target(zombie.pos)
    nearest_barricade = game.closest_barricade(zombie.pos)
    target_visible = _refresh_pursuit(zombie, game, target_actor)
    _maybe_call_horde(zombie, game, target_visible)

    if _pressure_barricade(zombie, game, dt, nearest_barricade):
        return
    if _pressure_target(zombie, game, dt, target_actor, target_visible):
        return
    _roam(zombie, game, dt)


def _configure_variant(zombie) -> None:
    zombie.variant = "walker"
    zombie.weapon_name = ""
    roll = random.random()
    if roll < 0.17:
        zombie.variant = "runner"
        zombie.speed *= 1.18
        zombie.max_health *= 0.9
        zombie.health = zombie.max_health
        zombie.contact_damage *= 0.98
        zombie.alert_radius = 280
        zombie.charge_cooldown = random.uniform(1.8, 3.2)
    elif roll < 0.3:
        zombie.variant = "brute"
        zombie.radius = 20
        zombie.speed *= 0.82
        zombie.max_health *= 1.42
        zombie.health = zombie.max_health
        zombie.contact_damage *= 1.28
        zombie.alert_radius = 220
        zombie.slam_cooldown = random.uniform(3.6, 5.2)
    elif roll < 0.42:
        zombie.variant = "howler"
        zombie.speed *= 0.96
        zombie.max_health *= 1.08
        zombie.health = zombie.max_health
        zombie.alert_radius = 300
        zombie.howl_cooldown = random.uniform(4.8, 7.2)
    elif roll < 0.56:
        zombie.variant = "raider"
        zombie.speed *= 1.02
        zombie.max_health *= 1.08
        zombie.health = zombie.max_health
        zombie.contact_damage *= 1.12
        zombie.weapon_name = random.choice(("cano", "machado", "barra"))
        zombie.alert_radius = 260


def _configure_boss(zombie, boss_profile: dict[str, object]) -> None:
    zombie.variant = str(boss_profile.get("variant", "boss"))
    zombie.weapon_name = str(boss_profile.get("weapon", "garras"))
    zombie.alert_radius = float(boss_profile.get("alert_radius", 340))
    zombie.slam_cooldown = random.uniform(4.2, 6.0)


def _tick_timers(zombie, dt: float) -> None:
    zombie.attack_cooldown = max(0.0, zombie.attack_cooldown - dt)
    zombie.stagger = max(0.0, zombie.stagger - dt)
    zombie.pursuit_timer = max(0.0, zombie.pursuit_timer - dt)
    zombie.howl_cooldown = max(0.0, zombie.howl_cooldown - dt)
    zombie.charge_cooldown = max(0.0, zombie.charge_cooldown - dt)
    zombie.charge_timer = max(0.0, zombie.charge_timer - dt)
    zombie.slam_cooldown = max(0.0, zombie.slam_cooldown - dt)
    zombie.visual_state = ""
    zombie.shamble += dt * 3.0


def _update_boss_state(zombie, game: "Game", dt: float) -> None:
    if not zombie.is_boss:
        return

    health_ratio = zombie.health / max(1.0, zombie.max_health)
    if health_ratio < 0.72 and zombie.enrage_level < 1:
        zombie.enrage_level = 1
        zombie.speed *= 1.06
        zombie.contact_damage *= 1.08
        zombie.alert_radius += 24
        zombie.howl_cooldown = min(zombie.howl_cooldown, 2.8)
        zombie.visual_state = "enraged"
        game.spawn_floating_text("furia", zombie.pos, PALETTE["danger_soft"])
        game.damage_pulses.append(DamagePulse(Vector2(zombie.pos), 22, 0.3, PALETTE["danger_soft"]))
    if health_ratio < 0.38 and zombie.enrage_level < 2:
        zombie.enrage_level = 2
        zombie.speed *= 1.08
        zombie.contact_damage *= 1.1
        zombie.alert_radius += 28
        zombie.howl_cooldown = min(zombie.howl_cooldown, 1.4)
        zombie.visual_state = "enraged"
        game.spawn_floating_text("furia alta", zombie.pos, PALETTE["danger"])
        game.damage_pulses.append(DamagePulse(Vector2(zombie.pos), 26, 0.32, PALETTE["danger"]))

    zombie.summon_cooldown = max(0.0, zombie.summon_cooldown - dt)
    if zombie.summon_cooldown <= 0 and zombie.distance_to(game.player.pos) < 340 and len(game.zombies) < 26:
        game.spawn_local_zombies(zombie.pos, 2, pressure=True)
        game.spawn_floating_text("eco da zona", zombie.pos, PALETTE["danger_soft"])
        game.screen_shake = max(game.screen_shake, 3.8)
        zombie.summon_cooldown = random.uniform(6.2, 9.4)
        if zombie.zone_key in game.named_regions:
            game.named_regions[zombie.zone_key]["boss_active"] = True


def _refresh_pursuit(zombie, game: "Game", target_actor) -> bool:
    target_visible = False
    if target_actor and zombie.distance_to(target_actor.pos) < zombie.alert_radius:
        zombie.pursuit_timer = max(zombie.pursuit_timer, 4.4 if zombie.variant == "runner" else 3.2)
        target_visible = True
        if zombie.variant == "runner" and zombie.charge_cooldown <= 0 and 70 < zombie.distance_to(target_actor.pos) < 230:
            zombie.charge_timer = 0.82
            zombie.charge_cooldown = random.uniform(3.8, 5.6)
            zombie.visual_state = "charging"
            game.spawn_floating_text("arranco", zombie.pos, PALETTE["danger_soft"])
        elif zombie.variant == "howler" and zombie.howl_cooldown > 0.35:
            zombie.howl_cooldown = min(zombie.howl_cooldown, 0.35)
            zombie.visual_state = "howling"
    if zombie.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 240:
        zombie.pursuit_timer = max(zombie.pursuit_timer, 2.8 + zombie.camp_pressure * 1.8)
    return target_visible


def _maybe_call_horde(zombie, game: "Game", target_visible: bool) -> None:
    if (
        zombie.howl_cooldown <= 0
        and len(game.zombies) < 30
        and (target_visible or zombie.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 140)
        and (zombie.variant in {"howler", "raider"} or zombie.is_boss)
    ):
        game.spawn_local_zombies(zombie.pos, 1 if zombie.variant != "howler" else 2, pressure=True)
        game.spawn_floating_text("chamado podre", zombie.pos, PALETTE["danger_soft"])
        zombie.howl_cooldown = random.uniform(4.8, 7.2) if zombie.variant == "howler" else random.uniform(7.5, 11.0)


def _pressure_barricade(zombie, game: "Game", dt: float, nearest_barricade) -> bool:
    near_camp_defense = zombie.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 170
    if (
        not nearest_barricade
        or nearest_barricade.is_broken()
        or not near_camp_defense
        or game.point_in_camp_square(zombie.pos, padding=-40)
    ):
        return False

    barricade_scale = 0.98 if zombie.pursuit_timer > 0 else 0.78
    moving = barricade_scale if zombie.stagger <= 0 else barricade_scale * 0.46
    if zombie.move_toward(nearest_barricade.pos, dt, moving) and zombie.attack_cooldown <= 0:
        impact = 6.5 + zombie.day * 0.65
        if zombie.is_boss:
            impact *= 2.1
        elif zombie.variant == "brute":
            impact *= 1.55
        elif zombie.variant == "raider":
            impact *= 1.26
        nearest_barricade.damage(impact)
        zombie.attack_cooldown = 0.82 if zombie.is_boss else (0.9 if zombie.variant in {"runner", "raider"} else 1.05)
        game.damage_pulses.append(DamagePulse(Vector2(nearest_barricade.pos), 14, 0.24, PALETTE["danger"]))
        spike_damage = getattr(nearest_barricade, "spike_level", 0) * (4.5 if zombie.is_boss else 7.0)
        if spike_damage > 0:
            zombie.health -= spike_damage
            game.spawn_floating_text("spikes", zombie.pos, PALETTE["accent_soft"])
            game.impact_burst(zombie.pos, PALETTE["accent_soft"], radius=10, shake=0.25)
        game.audio.play_impact("wood", source_pos=nearest_barricade.pos)
    return True


def _pressure_target(zombie, game: "Game", dt: float, target_actor, target_visible: bool) -> bool:
    if not target_actor or not (target_visible or zombie.pursuit_timer > 0):
        return False

    speed_scale = 0.98 if zombie.is_boss else 0.9
    if zombie.variant == "runner":
        speed_scale = 1.12 if zombie.charge_timer <= 0 else 1.52
        if zombie.charge_timer > 0:
            zombie.visual_state = "charging"
    elif zombie.variant == "brute":
        speed_scale = 0.82
        if zombie.slam_cooldown <= 0 and zombie.distance_to(target_actor.pos) < 96:
            zombie.visual_state = "slamming"

    moving = speed_scale if zombie.stagger <= 0 else speed_scale * 0.5
    if zombie.move_toward(target_actor.pos, dt, moving) and zombie.attack_cooldown <= 0:
        _strike_target(zombie, game, target_actor)
    return True


def _strike_target(zombie, game: "Game", target_actor) -> None:
    hit_damage = zombie.contact_damage
    knockback = 14.0
    zombie.attack_cooldown = 0.88 if zombie.is_boss else (0.9 if zombie.variant == "runner" else 1.1)
    if zombie.variant == "runner" and zombie.charge_timer > 0:
        hit_damage *= 1.22
        knockback = 24.0
        zombie.attack_cooldown = 0.72
        zombie.charge_timer = 0.0
    elif zombie.variant == "brute":
        hit_damage *= 1.18
        knockback = 28.0
        zombie.attack_cooldown = 1.2
        zombie.slam_cooldown = random.uniform(4.2, 6.0)
        zombie.visual_state = "slamming"
    elif zombie.is_boss and zombie.enrage_level > 0:
        hit_damage *= 1.0 + zombie.enrage_level * 0.08
        knockback = 20.0 + zombie.enrage_level * 5.0

    target_actor.health -= hit_damage
    game.damage_pulses.append(DamagePulse(Vector2(target_actor.pos), 12, 0.24, PALETTE["danger_soft"]))
    game.audio.play_impact("body", source_pos=target_actor.pos)
    if target_actor.pos.distance_to(zombie.pos) > 0.01:
        target_actor.pos += (target_actor.pos - zombie.pos).normalize() * knockback
    if _is_survivor(target_actor):
        target_actor.morale = clamp(target_actor.morale - (18 if zombie.is_boss else 12), 0, 100)
        if hasattr(target_actor, "insanity"):
            target_actor.insanity = clamp(target_actor.insanity + (12 if zombie.is_boss else 7), 0, 100)
    else:
        target_actor.hurt_flash = max(
            getattr(target_actor, "hurt_flash", 0.0),
            0.34 if zombie.variant != "brute" else 0.42,
        )
        game.screen_shake = max(game.screen_shake, 7.0 if zombie.is_boss else (5.6 if zombie.variant == "brute" else 4.8))


def _is_survivor(actor) -> bool:
    return actor.__class__.__name__ == "Survivor"


def _roam(zombie, game: "Game", dt: float) -> None:
    if zombie.distance_to(CAMP_CENTER) < game.camp_clearance_radius() + 260 or zombie.camp_pressure > 0.7:
        ring = game.camp_clearance_radius() * (0.86 + 0.22 * zombie.camp_pressure)
        roam = CAMP_CENTER + angle_to_vector(zombie.shamble) * ring
        zombie.move_toward(roam, dt, 0.62 if zombie.variant == "runner" else 0.56)
        return

    roam_center = zombie.anchor if zombie.is_boss else zombie.anchor.lerp(CAMP_CENTER, 0.22)
    roam_radius = 160 if zombie.is_boss else 190 + zombie.camp_pressure * 80
    roam = roam_center + angle_to_vector(zombie.shamble) * roam_radius
    zombie.move_toward(roam, dt, 0.54 if zombie.is_boss else 0.58)









