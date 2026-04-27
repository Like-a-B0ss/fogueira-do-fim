from __future__ import annotations

import math

from pygame import Vector2


def update(audio, game, dt: float) -> None:
    if not audio.available:
        return
    scene_tag = game.scenes.current_name
    if scene_tag != audio.scene_music_tag:
        audio.scene_music_tag = scene_tag
        audio.music_timer = 0.0
        audio.ambience_timer = 0.0
        audio.weather_timer = 0.0
        audio.zombie_timer = 0.8
        audio.frontend_phrase_index = 0
    if not game.scenes.is_gameplay():
        update_frontend_music(audio, game, dt)
        return
    audio.set_listener_position(game.player.pos)

    audio.bonfire_timer -= dt
    audio.ambience_timer -= dt
    audio.weather_timer -= dt
    audio.zombie_timer -= dt
    audio.music_timer -= dt

    update_player_steps(audio, game, dt)
    update_bonfire(audio, game)
    update_biome_ambience(audio, game)
    update_weather(audio, game)
    update_zombie_ambience(audio, game)
    update_music(audio, game)


def update_frontend_music(audio, game, dt: float) -> None:
    if not (game.scenes.is_splash() or game.scenes.is_title() or game.scenes.is_tips()):
        return
    audio.music_timer -= dt
    if audio.music_timer > 0:
        return
    if game.scenes.is_splash():
        sequence = (
            ("music_frontend_veil", 0.48, (3.95, 4.25)),
            ("music_frontend_lift", 0.5, (3.8, 4.15)),
        )
    elif game.scenes.is_tips():
        sequence = (
            ("music_frontend_glow", 0.4, (3.55, 3.95)),
            ("music_frontend_resolve", 0.42, (3.75, 4.1)),
            ("music_frontend_veil", 0.38, (3.9, 4.2)),
        )
    else:
        sequence = (
            ("music_frontend_veil", 0.52, (3.95, 4.25)),
            ("music_frontend_lift", 0.54, (3.7, 4.0)),
            ("music_frontend_glow", 0.53, (3.6, 3.95)),
            ("music_frontend_resolve", 0.55, (3.9, 4.25)),
        )

    phrase_index = audio.frontend_phrase_index % len(sequence)
    cue, volume, interval = sequence[phrase_index]
    audio._play(cue, volume_scale=volume, category="music")
    audio.frontend_phrase_index += 1
    audio.music_timer = audio.rng.uniform(*interval)


def update_player_steps(audio, game, dt: float) -> None:
    if not game.player.is_alive():
        return

    speed = game.player.velocity.length()
    if speed < 22:
        audio.step_timer = min(audio.step_timer, 0.06)
        return

    speed_ratio = max(0.5, min(1.9, speed / max(1.0, game.player.speed)))
    sprinting = speed_ratio > 1.18
    audio.step_timer -= dt * speed_ratio
    if audio.step_timer > 0:
        return

    surface = game.surface_audio_at(game.player.pos)
    cue = {
        "camp": "step_camp",
        "path": "step_path",
        "meadow": "step_meadow",
        "swamp": "step_swamp",
        "ruin": "step_ruin",
    }.get(surface, "step_forest")
    volume = 0.11 + (0.05 if sprinting else 0.0)
    if surface == "swamp":
        volume += 0.04
    elif surface == "ruin":
        volume += 0.03
    elif surface == "path":
        volume += 0.02
    audio._play(cue, volume_scale=volume)

    cadence = 0.36 if not sprinting else 0.24
    if surface == "swamp":
        cadence += 0.05
    elif surface == "path":
        cadence -= 0.03
    audio.step_timer = max(0.11, cadence * audio.rng.uniform(0.88, 1.08))


def update_bonfire(audio, game) -> None:
    if audio.bonfire_timer > 0:
        return
    intensity = min(1.0, (game.bonfire_heat * 0.65 + game.bonfire_ember_bed * 0.35) / 100)
    if intensity <= 0.12:
        return
    audio._play(
        "ambient_bonfire",
        volume_scale=0.08 + intensity * 0.22,
        category="ambience",
        source_pos=game.bonfire_pos,
        max_distance=320.0,
    )
    audio.bonfire_timer = audio.rng.uniform(0.22, 0.62) * (1.25 - intensity * 0.38)


def update_biome_ambience(audio, game) -> None:
    if audio.ambience_timer > 0:
        return

    biome = getattr(game, "current_biome_key", "camp")
    daylight = game.daylight_factor() if hasattr(game, "daylight_factor") else (0.0 if game.is_night else 1.0)
    precipitation = game.weather_precipitation_factor() if hasattr(game, "weather_precipitation_factor") else 0.0
    mist = game.weather_mist_factor() if hasattr(game, "weather_mist_factor") else 0.0
    storm = game.weather_storm_factor() if hasattr(game, "weather_storm_factor") else 0.0
    wind = game.weather_wind_factor() if hasattr(game, "weather_wind_factor") else 0.0

    if daylight < 0.18:
        options = [("ambient_night", 0.32), ("ambient_dread", 0.24)]
        if biome == "swamp":
            options.append(("ambient_swamp", 0.3))
        elif biome == "ruin":
            options.append(("ambient_ruin", 0.26))
        if biome == "grove" and wind > 0.12:
            options.append(("ambient_wind", 0.16 + wind * 0.1))
        cue, volume = audio.rng.choice(options)
        audio._play(cue, volume_scale=volume, category="ambience")
        audio.ambience_timer = audio.rng.uniform(2.6, 4.4)
        return

    if storm > 0.26 or precipitation > 0.28:
        if biome == "swamp":
            audio._play("ambient_swamp", volume_scale=0.26 + storm * 0.06, category="ambience")
        else:
            audio._play("ambient_wind", volume_scale=0.18 + wind * 0.1 + storm * 0.05, category="ambience")
        audio.ambience_timer = audio.rng.uniform(3.0, 5.0)
        return
    if mist > 0.24 or game.weather_cloud_cover() > 0.34:
        options = [("ambient_day", 0.18)]
        if biome == "swamp":
            options.append(("ambient_swamp", 0.22))
        elif biome == "ruin":
            options.append(("ambient_ruin", 0.23))
        elif biome == "grove" and wind > 0.1:
            options.append(("ambient_wind", 0.15 + wind * 0.08))
        cue, volume = audio.rng.choice(options)
        audio._play(cue, volume_scale=volume, category="ambience")
        audio.ambience_timer = audio.rng.uniform(3.0, 5.2)
        return

    options = [("ambient_day", 0.23)]
    if biome == "swamp":
        options.append(("ambient_swamp", 0.25))
    elif biome == "ruin":
        options.append(("ambient_ruin", 0.24))
    elif biome == "grove" and wind > 0.1:
        options.append(("ambient_wind", 0.15 + wind * 0.09))
    cue, volume = audio.rng.choice(options)
    audio._play(cue, volume_scale=volume, category="ambience")
    audio.ambience_timer = audio.rng.uniform(3.2, 5.8)


def update_weather(audio, game) -> None:
    if audio.weather_timer > 0:
        return

    precipitation = game.weather_precipitation_factor() if hasattr(game, "weather_precipitation_factor") else 0.0
    wind = game.weather_wind_factor() if hasattr(game, "weather_wind_factor") else 0.0
    gust = float(getattr(game, "weather_gust_strength", wind))
    wind_force = max(wind, gust)
    storm = game.weather_storm_factor() if hasattr(game, "weather_storm_factor") else 0.0
    mist = game.weather_mist_factor() if hasattr(game, "weather_mist_factor") else 0.0
    if precipitation > 0.34:
        audio._play("ambient_rain", volume_scale=0.14 + precipitation * 0.12 + storm * 0.05, category="ambience")
        if wind_force > 0.22 and audio.rng.random() < 0.35 + wind_force * 0.32 + storm * 0.2:
            audio._play("ambient_wind", volume_scale=0.16 + wind_force * 0.16 + storm * 0.05, category="ambience")
        audio.weather_timer = audio.rng.uniform(3.6, 5.8)
    elif mist > 0.32:
        if wind_force > 0.08 and audio.rng.random() < 0.42 + wind_force * 0.42:
            audio._play("ambient_wind", volume_scale=0.13 + wind_force * 0.14 + mist * 0.03, category="ambience")
        audio.weather_timer = audio.rng.uniform(2.2, 4.0)
    elif wind_force > 0.08:
        audio._play("ambient_wind", volume_scale=0.14 + wind_force * 0.2 + storm * 0.04, category="ambience")
        audio.weather_timer = audio.rng.uniform(
            max(1.2, 3.6 - wind_force * 2.0),
            max(2.0, 5.2 - wind_force * 2.4),
        )
    else:
        audio.weather_timer = audio.rng.uniform(3.8, 5.8)


def update_zombie_ambience(audio, game) -> None:
    if audio.zombie_timer > 0:
        return

    visible_threat = len(game.zombies)
    distant_threat = max(0.0, game.spawn_budget / 12) if game.is_night else 0.0
    pressure = min(1.0, visible_threat / 12 + distant_threat * 0.35)
    if pressure <= 0.06:
        if game.is_night and audio.rng.random() < 0.58:
            angle = audio.rng.uniform(0.0, math.tau)
            distance = audio.rng.uniform(180.0, 320.0)
            source_pos = audio.listener_pos + Vector2(math.cos(angle), math.sin(angle)) * distance
            audio._play(
                "zombie_far",
                volume_scale=0.08 + distant_threat * 0.08,
                category="ambience",
                source_pos=source_pos,
                max_distance=420.0,
            )
            audio.zombie_timer = audio.rng.uniform(3.8, 6.0)
            return
        audio.zombie_timer = audio.rng.uniform(4.8, 7.2)
        return

    source_pos = None
    if game.zombies:
        nearest = min(game.zombies, key=lambda zombie: audio.listener_pos.distance_to(zombie.pos))
        source_pos = Vector2(nearest.pos)

    if visible_threat >= 7 or game.audio_tension() >= 0.82:
        audio._play(
            "zombie_horde",
            volume_scale=0.16 + pressure * 0.18,
            category="ambience",
            source_pos=source_pos,
            max_distance=520.0,
        )
    else:
        audio._play(
            "zombie_groan",
            volume_scale=0.13 + pressure * 0.16,
            category="ambience",
            source_pos=source_pos,
            max_distance=420.0,
        )

    interval_low = 2.0 + (1.0 - pressure) * 2.2
    interval_high = 3.8 + (1.0 - pressure) * 3.4
    audio.zombie_timer = audio.rng.uniform(interval_low, interval_high)


def update_music(audio, game) -> None:
    if audio.music_timer > 0:
        return

    tension = game.audio_tension()
    tension = min(1.0, tension + game.weather_precipitation_factor() * 0.08)
    tension = min(1.0, tension + game.weather_mist_factor() * 0.03)
    tension = min(1.0, tension + game.weather_wind_factor() * 0.04)
    tension = min(1.0, tension + game.weather_storm_factor() * 0.07)
    dread = max(
        0.0,
        (0.14 if game.is_night else 0.0)
        + game.weather_mist_factor() * 0.26
        + game.weather_cloud_cover() * 0.18
        + game.weather_storm_factor() * 0.24,
    )

    if tension >= 0.82:
        audio._play("music_horde", volume_scale=0.36 + tension * 0.16, category="music")
        audio.music_timer = audio.rng.uniform(2.2, 3.5)
    elif tension >= 0.46:
        audio._play("music_threat", volume_scale=0.31 + tension * 0.14, category="music")
        audio.music_timer = audio.rng.uniform(3.0, 4.8)
    elif dread >= 0.2:
        audio._play("music_dread", volume_scale=0.26 + dread * 0.12, category="music")
        audio.music_timer = audio.rng.uniform(3.8, 6.0)
    elif not game.is_night:
        audio._play("music_calm", volume_scale=0.28, category="music")
        audio.music_timer = audio.rng.uniform(4.0, 6.4)
    else:
        audio._play("music_dread", volume_scale=0.22, category="music")
        audio.music_timer = audio.rng.uniform(4.2, 6.6)







