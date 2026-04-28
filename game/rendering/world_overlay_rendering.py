from __future__ import annotations

import math

import pygame
from pygame import Vector2

from ..core.config import PALETTE, clamp


def draw_weather_overlay(game, shake_offset: Vector2) -> None:
    screen_width, screen_height = game.screen.get_size()
    precipitation = game.weather_precipitation_factor()
    wind = game.weather_wind_factor()
    gust = float(getattr(game, "weather_gust_strength", wind))
    wind_force = max(wind, gust)
    mist = game.weather_mist_factor()
    storm = game.weather_storm_factor()
    if precipitation <= 0.22 and mist <= 0.16:
        return

    tick = pygame.time.get_ticks() / 1000.0
    if mist > 0.16:
        draw_camera_mist(game, shake_offset, tick, mist, wind_force, storm)

    if precipitation > 0.22:
        draw_rain_overlay(game, shake_offset, tick, precipitation, wind_force, storm)


def draw_rain_overlay(
    game,
    shake_offset: Vector2,
    tick: float,
    precipitation: float,
    wind: float,
    storm: float,
) -> None:
    screen_width, screen_height = game.screen.get_size()
    rain_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    intensity = clamp((precipitation - 0.22) / 0.72, 0.0, 1.0)

    if intensity > 0.18:
        veil = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        veil.fill((34, 44, 50, int(4 + intensity * 10 + storm * 5)))
        rain_surface.blit(veil, (0, 0))

    streaks = int(10 + intensity * 36 + storm * 16)
    fall = 16 + intensity * 24 + storm * 10
    drift = 3 + wind * 12 + storm * 5
    rain_vector = Vector2(drift, fall)
    speed = 112 + intensity * 86 + storm * 42
    alpha = int(clamp(14 + intensity * 28 + storm * 10, 0, 58))
    for index in range(streaks):
        phase = tick * speed + index * 47
        x = (phase * 1.06 + index * 59 - game.camera.x * 0.72) % (screen_width + 180) - 90
        y = (phase * 1.62 + index * 83 - game.camera.y * 0.84) % (screen_height + 240) - 120
        start = Vector2(x + shake_offset.x * 0.18, y + shake_offset.y * 0.18)
        end = start + rain_vector
        pygame.draw.line(
            rain_surface,
            (142, 166, 180, alpha),
            start,
            end,
            1,
        )
    game.screen.blit(rain_surface, (0, 0))


def draw_camera_mist(
    game,
    shake_offset: Vector2,
    tick: float,
    mist: float,
    wind: float,
    storm: float,
) -> None:
    screen_width, screen_height = game.screen.get_size()
    fog_strength = clamp(float(game.runtime_settings.get("fog_strength", 1.0)), 0.25, 1.25)
    mist_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)

    veil_alpha = int(clamp((3 + mist * 9 + storm * 3) * fog_strength, 0, 18))
    if veil_alpha > 0:
        mist_surface.fill((*PALETTE["fog"], veil_alpha))

    base_alpha = clamp((8 + mist * 28 + storm * 5) * fog_strength, 0, 38)
    drift_speed = 8 + wind * 28 + storm * 10
    band_count = 6
    for index in range(band_count):
        phase = tick * (0.16 + wind * 0.08) + index * 1.73
        width = int(screen_width * (0.82 + 0.12 * (index % 3)))
        height = int(screen_height * (0.17 + 0.025 * (index % 2)))
        x = (
            index * screen_width * 0.27
            + tick * drift_speed
            - game.camera.x * 0.04
            + math.sin(phase) * 34
        ) % (screen_width + width) - width
        y = (
            index * screen_height / band_count
            - game.camera.y * 0.025
            + math.sin(phase * 0.73) * 24
        ) % (screen_height + height) - height * 0.5
        rect = pygame.Rect(int(x + shake_offset.x * 0.1), int(y + shake_offset.y * 0.1), width, height)
        alpha = int(base_alpha * (0.55 + 0.13 * (index % 4)))
        pygame.draw.ellipse(mist_surface, (*PALETTE["fog"], alpha), rect)

    game.screen.blit(mist_surface, (0, 0))


def draw_fog(game, shake_offset: Vector2) -> None:
    screen_width, screen_height = game.screen.get_size()
    fog_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    darkness = game.visual_darkness_factor()
    cloud_cover = game.weather_cloud_cover()
    mist = game.weather_mist_factor()
    factor = (0.09 + darkness * 0.24 + cloud_cover * 0.08 + mist * 0.32) * float(
        game.runtime_settings.get("fog_strength", 1.0)
    )
    for mote in game.fog_motes:
        pos = game.world_to_screen(mote.pos) + shake_offset
        if pos.x < -220 or pos.x > screen_width + 220 or pos.y < -220 or pos.y > screen_height + 220:
            continue
        alpha = int(clamp(mote.alpha * factor, 0, 255))
        pygame.draw.circle(
            fog_surface,
            (*PALETTE["fog"], alpha),
            (int(pos.x), int(pos.y)),
            int(mote.radius),
        )
    game.screen.blit(fog_surface, (0, 0))


def carve_map_visibility(game, overlay: pygame.Surface, center: Vector2, radius: float) -> None:
    diameter = max(4, int(radius * 2.3))
    reveal = game.map_reveal_cache.get(diameter)
    if reveal is None:
        reveal = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        center_xy = (diameter // 2, diameter // 2)
        pygame.draw.circle(reveal, (0, 0, 0, 220), center_xy, int(radius * 0.9))
        game.map_reveal_cache[diameter] = reveal
    reveal_center = Vector2(reveal.get_width() / 2, reveal.get_height() / 2)
    top_left = center - reveal_center
    overlay.blit(reveal, (int(top_left.x), int(top_left.y)), special_flags=pygame.BLEND_RGBA_SUB)


def draw_map_fog(game, shake_offset: Vector2) -> None:
    screen_width, screen_height = game.screen.get_size()
    view_rect = pygame.Rect(int(game.camera.x), int(game.camera.y), screen_width, screen_height)
    fog_overlay = game.map_fog_overlay_surface
    if fog_overlay is None or fog_overlay.get_size() != (screen_width, screen_height):
        fog_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        game.map_fog_overlay_surface = fog_overlay
    fog_strength = clamp(float(game.runtime_settings.get("fog_strength", 1.0)), 0.2, 1.25)
    fog_alpha = int(clamp(224 * fog_strength, 0, 255))
    fog_overlay.fill((0, 0, 0, fog_alpha))

    for center, radius in game.visible_fog_reveals(view_rect):
        carve_map_visibility(game, fog_overlay, game.world_to_screen(center), radius)

    game.screen.blit(fog_overlay, (0, 0))


def draw_lighting(game) -> None:
    screen_width, screen_height = game.screen.get_size()
    darkness_factor = game.visual_darkness_factor()
    cloud_cover = game.weather_cloud_cover()
    daylight = game.daylight_factor()
    storm = game.weather_storm_factor()
    darkness = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    darkness.fill((*PALETTE["night"], int(12 + darkness_factor * 126)))
    if cloud_cover > 0.12:
        cloud_tint = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        cloud_tint.fill((38, 46, 52, int((4 + cloud_cover * 14 + storm * 6) * max(0.16, daylight * 0.75))))
        darkness.blit(cloud_tint, (0, 0))

    fire_pos = game.world_to_screen(game.bonfire_pos)
    glow = game.bonfire_heat * 0.68 + game.bonfire_ember_bed * 0.32
    light_strength = 0.08 + darkness_factor * 0.92
    tick = pygame.time.get_ticks() / 1000.0
    flicker = 0.94 + 0.04 * math.sin(tick * 3.1) + 0.025 * math.sin(tick * 7.7)
    radius = int((92 + glow * 1.12) * (0.62 + darkness_factor * 0.38) * flicker)
    carve_soft_fire_light(
        darkness,
        fire_pos,
        radius=max(58, radius),
        strength=light_strength * (0.26 + glow / 360),
    )
    game.screen.blit(darkness, (0, 0))

    tint_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    draw_soft_fire_tint(
        tint_surface,
        fire_pos,
        radius=max(44, int(radius * 0.74)),
        strength=light_strength * (0.08 + glow / 760),
    )
    game.screen.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    weather_flash = float(getattr(game, "weather_flash", 0.0))
    if weather_flash > 0.01:
        flash = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        flash.fill((190, 210, 224, int(22 + weather_flash * 54)))
        game.screen.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    vignette = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    pygame.draw.rect(
        vignette,
        (0, 0, 0, int(4 + darkness_factor * 24 + cloud_cover * 5 + storm * 4)),
        vignette.get_rect(),
        border_radius=22,
    )
    game.screen.blit(vignette, (0, 0))


def carve_soft_fire_light(surface: pygame.Surface, center: Vector2, *, radius: int, strength: float) -> None:
    """Abre a camada de escuridao com falloff suave, sem pintar por cima da fogueira."""
    x = int(center.x)
    y = int(center.y)
    strength = clamp(strength, 0.0, 1.0)

    light_cut = pygame.Surface((radius * 2, int(radius * 1.2)), pygame.SRCALPHA)
    light_center = (radius, int(radius * 0.62))
    for index in range(16, 0, -1):
        ratio = index / 16
        falloff = (1.0 - ratio) ** 2.35
        alpha = int(falloff * 74 * strength)
        if alpha <= 0:
            continue
        ellipse = pygame.Rect(0, 0, int(radius * 1.95 * ratio), int(radius * 1.05 * ratio))
        ellipse.center = light_center
        pygame.draw.ellipse(light_cut, (0, 0, 0, alpha), ellipse)
    surface.blit(light_cut, (x - radius, y - int(radius * 0.62)), special_flags=pygame.BLEND_RGBA_SUB)


def draw_soft_fire_tint(surface: pygame.Surface, center: Vector2, *, radius: int, strength: float) -> None:
    """Acrescenta apenas um toque quente, baixo o suficiente para não ocultar sprites."""
    x = int(center.x)
    y = int(center.y)
    strength = clamp(strength, 0.0, 1.0)
    for index in range(8, 0, -1):
        ratio = index / 8
        falloff = (1.0 - ratio) ** 2.1
        alpha = int(falloff * 12 * strength)
        if alpha <= 0:
            continue
        ellipse = pygame.Rect(0, 0, int(radius * 1.7 * ratio), int(radius * 0.9 * ratio))
        ellipse.center = (x, y + int(radius * 0.04))
        pygame.draw.ellipse(surface, (220, 138, 84, alpha), ellipse)
