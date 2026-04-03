from __future__ import annotations

import pygame
from pygame import Vector2

from ..core.config import PALETTE, clamp


def draw_weather_overlay(game, shake_offset: Vector2) -> None:
    screen_width, screen_height = game.screen.get_size()
    precipitation = game.weather_precipitation_factor()
    wind = game.weather_wind_factor()
    storm = game.weather_storm_factor()
    if precipitation <= 0.12:
        return

    tick = pygame.time.get_ticks() / 1000.0
    rain_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    streaks = int(18 + precipitation * 34 + storm * 18)
    fall = 18 + precipitation * 20 + storm * 8
    drift = 4 + wind * 7 + storm * 4
    rain_vector = Vector2(drift, fall)
    for index in range(streaks):
        phase = tick * (140 + precipitation * 70 + storm * 35) + index * 43
        x = (phase * 1.11 + index * 53 - game.camera.x * 0.92) % (screen_width + 160) - 80
        y = (phase * 1.83 + index * 79 - game.camera.y * 1.04) % (screen_height + 220) - 110
        start = Vector2(x + shake_offset.x * 0.2, y + shake_offset.y * 0.2)
        end = start + rain_vector
        pygame.draw.line(
            rain_surface,
            (154, 176, 188, int(18 + precipitation * 16 + storm * 8)),
            start,
            end,
            1,
        )
    game.screen.blit(rain_surface, (0, 0))


def draw_fog(game, shake_offset: Vector2) -> None:
    screen_width, screen_height = game.screen.get_size()
    fog_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    darkness = game.visual_darkness_factor()
    cloud_cover = game.weather_cloud_cover()
    factor = (0.09 + darkness * 0.24 + cloud_cover * 0.08) * float(game.runtime_settings.get("fog_strength", 1.0))
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
    game.screen.blit(darkness, (0, 0))

    light_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    fire_pos = game.world_to_screen(game.bonfire_pos)
    glow = game.bonfire_heat * 0.68 + game.bonfire_ember_bed * 0.32
    light_strength = 0.08 + darkness_factor * 0.92
    radius = int((76 + glow * 1.18) * (0.56 + darkness_factor * 0.44))
    pygame.draw.circle(
        light_surface,
        (226, 122, 76, int((10 + glow * 0.04) * light_strength)),
        fire_pos,
        radius,
    )
    pygame.draw.circle(
        light_surface,
        (236, 144, 94, int((3 + glow * 0.012) * light_strength)),
        fire_pos,
        int(radius * 0.34),
    )

    game.screen.blit(light_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

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








