from __future__ import annotations

import math

from pygame import Vector2


def update(audio, game, dt: float) -> None:
    if not audio.available or not game.scenes.is_gameplay():
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

    if daylight < 0.18:
        options = [("ambient_night", 0.18), ("ambient_dread", 0.11)]
        if biome == "swamp":
            options.append(("ambient_swamp", 0.17))
        elif biome == "grove":
            options.append(("ambient_grove", 0.13))
        elif biome == "ruin":
            options.append(("ambient_ruin", 0.14))
        cue, volume = audio.rng.choice(options)
        audio._play(cue, volume_scale=volume, category="ambience")
        audio.ambience_timer = audio.rng.uniform(4.2, 6.8)
        return

    if storm > 0.26 or precipitation > 0.28:
        if biome == "swamp":
            audio._play("ambient_swamp", volume_scale=0.14 + storm * 0.03, category="ambience")
        elif audio.rng.random() < 0.4:
            audio._play("ambient_grove", volume_scale=0.1 + mist * 0.02, category="ambience")
        audio.ambience_timer = audio.rng.uniform(5.6, 8.8)
        return
    if mist > 0.24 or game.weather_cloud_cover() > 0.34:
        options = [("ambient_day", 0.08)]
        if biome == "swamp":
            options.append(("ambient_swamp", 0.1))
        elif biome == "ruin":
            options.append(("ambient_ruin", 0.11))
        elif biome == "grove":
            options.append(("ambient_grove", 0.09))
        cue, volume = audio.rng.choice(options)
        audio._play(cue, volume_scale=volume, category="ambience")
        audio.ambience_timer = audio.rng.uniform(5.2, 8.2)
        return

    options = [("ambient_day", 0.12)]
    if biome == "grove":
        options.append(("ambient_grove", 0.12))
    elif biome == "swamp":
        options.append(("ambient_swamp", 0.13))
    elif biome == "ruin":
        options.append(("ambient_ruin", 0.12))
    cue, volume = audio.rng.choice(options)
    audio._play(cue, volume_scale=volume, category="ambience")
    audio.ambience_timer = audio.rng.uniform(5.4, 9.6)


def update_weather(audio, game) -> None:
    if audio.weather_timer > 0:
        return

    precipitation = game.weather_precipitation_factor() if hasattr(game, "weather_precipitation_factor") else 0.0
    wind = game.weather_wind_factor() if hasattr(game, "weather_wind_factor") else 0.0
    storm = game.weather_storm_factor() if hasattr(game, "weather_storm_factor") else 0.0
    mist = game.weather_mist_factor() if hasattr(game, "weather_mist_factor") else 0.0
    if precipitation > 0.22:
        audio._play("ambient_rain", volume_scale=0.14 + precipitation * 0.16 + storm * 0.08, category="ambience")
        if wind > 0.34 and audio.rng.random() < 0.4 + storm * 0.2:
            audio._play("ambient_wind", volume_scale=0.06 + wind * 0.08 + storm * 0.04, category="ambience")
        audio.weather_timer = audio.rng.uniform(1.5, 2.5)
    elif mist > 0.32:
        if audio.rng.random() < 0.46:
            audio._play("ambient_wind", volume_scale=0.03 + wind * 0.04 + mist * 0.02, category="ambience")
        audio.weather_timer = audio.rng.uniform(3.8, 6.4)
    elif wind > 0.26:
        audio._play("ambient_wind", volume_scale=0.08 + wind * 0.14 + storm * 0.04, category="ambience")
        audio.weather_timer = audio.rng.uniform(2.4, 4.2)
    else:
        if wind > 0.24 and audio.rng.random() < 0.42:
            audio._play("ambient_wind", volume_scale=0.05 + wind * 0.06, category="ambience")
        audio.weather_timer = audio.rng.uniform(5.4, 8.2)


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
        audio._play("music_horde", volume_scale=0.14 + tension * 0.08, category="music")
        audio.music_timer = audio.rng.uniform(2.8, 4.4)
    elif tension >= 0.46:
        audio._play("music_threat", volume_scale=0.12 + tension * 0.07, category="music")
        audio.music_timer = audio.rng.uniform(4.0, 6.2)
    elif dread >= 0.2:
        audio._play("music_dread", volume_scale=0.08 + dread * 0.05, category="music")
        audio.music_timer = audio.rng.uniform(5.2, 8.0)
    elif not game.is_night and audio.rng.random() < 0.62:
        audio._play("music_calm", volume_scale=0.08, category="music")
        audio.music_timer = audio.rng.uniform(6.0, 9.6)
    else:
        audio.music_timer = audio.rng.uniform(5.4, 8.4)







