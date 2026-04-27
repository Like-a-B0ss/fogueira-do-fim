from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import Vector2

from ..core.config import CAMP_CENTER, MINUTES_PER_SECOND, UI_SETTINGS

if TYPE_CHECKING:
    from ..app.session import Game


def update(game: "Game", dt: float) -> None:
    if game.scenes.is_splash():
        game.splash_elapsed += dt
        game.splash_hint_pulse += dt
        game.update_background_simulation(dt)
        if game.splash_elapsed >= game.splash_min_duration:
            game.title_intro_alpha = 0.0
            game.scenes.change("title")
        return

    if game.scenes.is_title() or game.scenes.is_tips() or game.scenes.is_game_over():
        if game.scenes.is_title():
            game.title_intro_alpha = min(255.0, game.title_intro_alpha + game.title_intro_speed * dt)
        game.update_background_simulation(dt)
        return

    if (game.exit_prompt_open or getattr(game, "gameplay_settings_open", False)) and game.scenes.is_gameplay():
        return

    if not game.scenes.allows_world_update:
        game.camera.center_on(CAMP_CENTER)
        return

    sim_scale = 7.0 if game.player_sleeping else 1.0
    sim_dt = dt * sim_scale
    game.maintain_unlimited_resources()
    game.time_minutes = (game.time_minutes + sim_dt * MINUTES_PER_SECOND) % (24 * 60)
    now_night = game.is_night
    if now_night and not game.previous_night:
        game.begin_night()
    if not now_night and game.previous_night:
        game.begin_day()
    game.previous_night = now_night

    game.update_bonfire(sim_dt)
    game.morale_flash = max(0.0, game.morale_flash - sim_dt * 0.45)
    game.screen_shake = max(0.0, game.screen_shake - sim_dt * 8)
    game.event_timer = max(0.0, game.event_timer - sim_dt)
    game.update_weather(sim_dt)

    game.player.update(game, sim_dt if game.player_sleeping else dt)
    game.ensure_endless_world(game.player.pos)
    game.update_player_biome()
    game.ensure_zone_boss_near_player()
    game.prune_build_requests()
    game.assign_building_specialists()
    game.update_dynamic_events(sim_dt)
    game.update_chief_tasks()
    game.update_survivor_barks(sim_dt)
    game.update_active_expedition(sim_dt)
    game.resolve_actor_camp_collision(game.player)

    for node in game.resource_nodes:
        node.update(sim_dt)
    game.update_buildings(sim_dt)
    for survivor in game.survivors:
        survivor.update(game, sim_dt)
        game.resolve_actor_camp_collision(survivor)
    game.reveal_world_around_player()
    game.update_social_dynamics(sim_dt)
    for zombie in game.zombies:
        zombie.update(game, sim_dt)

    game.normalize_stockpile()
    game.maintain_unlimited_resources()
    game.resolve_defeated_zone_bosses()
    game.zombies = [zombie for zombie in game.zombies if zombie.is_alive()]
    for floating in list(game.floating_texts):
        if not floating.update(sim_dt):
            game.floating_texts.remove(floating)
    for ember in list(game.embers):
        if not ember.update(sim_dt):
            game.embers.remove(ember)
    for pulse in list(game.damage_pulses):
        if not pulse.update(sim_dt):
            game.damage_pulses.remove(pulse)
    for mote in game.fog_motes:
        mote.update(sim_dt * (1.2 if now_night else 0.75))

    if now_night:
        game.spawn_timer -= sim_dt
        if game.spawn_budget > 0 and game.spawn_timer <= 0:
            game.spawn_night_zombie()
            if game.horde_active:
                base_interval = 3.45 if game.day <= 3 else 3.05
                min_interval = 1.45
            elif game.day <= 2:
                base_interval = 7.2 if game.day == 1 else 6.1
                min_interval = 4.2
            else:
                base_interval = 4.9 if game.day <= 3 else 4.1
                min_interval = 1.8
            tower_delay = game.tower_defense_bonus() * 2.2
            game.spawn_timer = max(min_interval, base_interval + tower_delay - game.day * 0.06)
    else:
        game.day_spawn_timer -= sim_dt
        if (
            game.day_spawn_timer <= 0
            and game.day >= 3
            and game.player.pos.distance_to(CAMP_CENTER) > game.camp_clearance_radius() + 220
            and game.can_spawn_zombie()
            and game.random.random() < (0.18 if game.day <= 4 else 0.28)
        ):
            game.spawn_forest_ambient_zombie()
            game.day_spawn_timer = game.random.uniform(18.0, 30.0)
        elif game.day_spawn_timer <= 0:
            game.day_spawn_timer = game.random.uniform(16.0, 24.0)

    if game.player_sleeping:
        game.player_sleep_elapsed += sim_dt
        if game.active_dynamic_events:
            game.wake_player("Uma crise bateu no campo e arrancou você do sono.")
        elif game.find_closest_zombie(game.player.pos, 160):
            game.wake_player("Barulho demais perto das barracas. Você acordou no susto.")
        if (
            game.player.stamina >= game.player.max_stamina - 1
            and game.player.health >= game.player.max_health - 1
            and game.player_sleep_elapsed >= 60
        ):
            game.wake_player("Você acordou depois de algumas horas e o campo ainda segue de pé.")

    defeat_reason = evaluate_defeat_reason(game)
    if defeat_reason:
        game.game_over_reason = defeat_reason
        game.set_event_message(defeat_reason, duration=8.0)
        game.scenes.change("game_over")
        game.audio.play_alert()
        return

    game.camera.center_on(game.player.pos)
    game.audio.update(game, dt)


def evaluate_defeat_reason(game: "Game") -> str | None:
    if not game.player.is_alive():
        return "O chefe caiu antes de conseguir manter a clareira de pé."

    alive_survivors = [survivor for survivor in game.survivors if survivor.is_alive()]
    if not alive_survivors:
        return "Não restou nenhum morador vivo para manter a sociedade."

    if game.average_morale() <= 0:
        return "A moral zerou e a sociedade desfez."

    return None


def update_background_simulation(game: "Game", dt: float) -> None:
    game.title_bg_phase += dt
    game.event_timer = max(0.0, game.event_timer - dt)
    game.screen_shake = max(0.0, game.screen_shake - dt * 8)
    game.morale_flash = max(0.0, game.morale_flash - dt * 0.45)

    for node in game.resource_nodes:
        node.update(dt * 0.5)
    for survivor in game.survivors:
        survivor.update(game, dt * 0.5)
        game.resolve_actor_camp_collision(survivor)
    for zombie in game.zombies:
        zombie.update(game, dt * 0.5)
    game.update_survivor_barks(dt * 0.5)
    game.zombies = [zombie for zombie in game.zombies if zombie.is_alive()]

    for floating in list(game.floating_texts):
        if not floating.update(dt):
            game.floating_texts.remove(floating)
    for ember in list(game.embers):
        if not ember.update(dt):
            game.embers.remove(ember)
    for pulse in list(game.damage_pulses):
        if not pulse.update(dt):
            game.damage_pulses.remove(pulse)
    for mote in game.fog_motes:
        mote.update(dt * 0.85)

    game.title_bg_spawn_timer -= dt
    if game.title_bg_spawn_timer <= 0:
        if len(game.zombies) < 5 and game.random.random() < 0.72:
            game.spawn_forest_ambient_zombie()
        spawn_range = UI_SETTINGS.get("title_background_spawn_range", [7.0, 12.0])
        game.title_bg_spawn_timer = game.random.uniform(float(spawn_range[0]), float(spawn_range[1]))

    orbit = CAMP_CENTER + Vector2(
        math.cos(game.title_bg_phase * 0.18) * 170,
        math.sin(game.title_bg_phase * 0.24) * 96,
    )
    game.camera.center_on(orbit)
    game.audio.update(game, dt)







