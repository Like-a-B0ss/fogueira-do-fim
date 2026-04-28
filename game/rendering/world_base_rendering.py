from __future__ import annotations

import math

import pygame
from pygame import Vector2

from ..core.config import CAMP_CENTER, CHUNK_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH, angle_to_vector, clamp, lerp


def draw_world_features(game, shake_offset: Vector2) -> None:
    for feature in [*game.world_features, *game.endless_features]:
        pos = game.world_to_screen(feature.pos) + shake_offset
        if pos.x < -240 or pos.x > SCREEN_WIDTH + 240 or pos.y < -240 or pos.y > SCREEN_HEIGHT + 240:
            continue

        accent_angle = feature.accent * math.tau
        if feature.kind == "meadow":
            for index in range(12):
                angle = accent_angle + index * 0.51
                distance = feature.radius * (0.14 + (index % 4) * 0.11)
                flower = pos + angle_to_vector(angle) * distance
                pygame.draw.circle(game.screen, (228, 207, 118), flower, 2)
                pygame.draw.circle(game.screen, (189, 111, 84), flower + Vector2(2, 1), 2)
        elif feature.kind == "swamp":
            for index in range(8):
                angle = accent_angle + index * 0.72
                root = pos + angle_to_vector(angle) * feature.radius * 0.34
                pygame.draw.line(
                    game.screen,
                    (86, 106, 64),
                    root,
                    root + Vector2(0, -16 - (index % 3) * 4),
                    2,
                )
        elif feature.kind == "ruin":
            for index in range(6):
                angle = accent_angle + index * 0.84
                offset = angle_to_vector(angle) * feature.radius * 0.38
                rubble = pygame.Rect(0, 0, 18 + (index % 3) * 6, 12 + (index % 2) * 4)
                rubble.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                pygame.draw.rect(game.screen, (111, 108, 101), rubble, border_radius=4)
                pygame.draw.rect(game.screen, (72, 69, 63), rubble, 1, border_radius=4)
        elif feature.kind == "grove":
            for index in range(5):
                angle = accent_angle + index * 1.08
                offset = angle_to_vector(angle) * feature.radius * 0.28
                stump = pygame.Rect(0, 0, 16, 10)
                stump.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                pygame.draw.ellipse(game.screen, (86, 66, 42), stump)
                pygame.draw.ellipse(game.screen, (127, 97, 58), stump.inflate(-4, -3))
        elif feature.kind == "ashland":
            for index in range(7):
                angle = accent_angle + index * 0.88
                offset = angle_to_vector(angle) * feature.radius * 0.34
                ember = pygame.Rect(0, 0, 14, 8)
                ember.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                pygame.draw.ellipse(game.screen, (118, 86, 68), ember)
        elif feature.kind == "redwood":
            for index in range(6):
                angle = accent_angle + index * 0.96
                offset = angle_to_vector(angle) * feature.radius * 0.4
                trunk = pygame.Rect(0, 0, 12, 28)
                trunk.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                pygame.draw.rect(game.screen, (90, 58, 39), trunk, border_radius=5)
        elif feature.kind == "quarry":
            for index in range(8):
                angle = accent_angle + index * 0.7
                offset = angle_to_vector(angle) * feature.radius * 0.38
                rock = pygame.Rect(0, 0, 16 + index % 3 * 3, 10 + index % 2 * 4)
                rock.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                pygame.draw.rect(game.screen, (136, 142, 148), rock, border_radius=4)
                pygame.draw.rect(game.screen, (82, 89, 94), rock, 1, border_radius=4)


def draw_procedural_ground(game, shake_offset: Vector2) -> None:
    left = math.floor((game.camera.x - CHUNK_SIZE) / CHUNK_SIZE)
    top = math.floor((game.camera.y - CHUNK_SIZE) / CHUNK_SIZE)
    right = math.ceil((game.camera.x + SCREEN_WIDTH + CHUNK_SIZE) / CHUNK_SIZE)
    bottom = math.ceil((game.camera.y + SCREEN_HEIGHT + CHUNK_SIZE) / CHUNK_SIZE)
    daylight = game.daylight_factor()
    cloud_cover = game.weather_cloud_cover()
    precipitation = game.weather_precipitation_factor()
    mist = game.weather_mist_factor()
    storm = game.weather_storm_factor()
    global_darkness = game.visual_darkness_factor()
    weather_cool = clamp(cloud_cover * 0.58 + precipitation * 0.18 + mist * 0.08 + storm * 0.12, 0.0, 0.88)
    for chunk_x in range(left, right + 1):
        for chunk_y in range(top, bottom + 1):
            biome = game.chunk_biome_kind(chunk_x, chunk_y)
            origin = game.chunk_origin(chunk_x, chunk_y)
            rect = pygame.Rect(
                int(origin.x - game.camera.x + shake_offset.x),
                int(origin.y - game.camera.y + shake_offset.y),
                CHUNK_SIZE + 1,
                CHUNK_SIZE + 1,
            )
            dark, light = game.biome_palette(biome)
            center = origin + Vector2(CHUNK_SIZE * 0.5, CHUNK_SIZE * 0.5)
            distance_to_camp = center.distance_to(CAMP_CENTER)
            depth = clamp(
                (distance_to_camp - (game.camp_clearance_radius() + 260)) / 2600,
                0.0,
                1.0,
            )
            if biome != "forest":
                depth = clamp(depth + 0.08, 0.0, 1.0)
            weather_dim = cloud_cover * (0.16 + daylight * 0.12) + global_darkness * 0.18 + storm * 0.08
            dark_scale = max(0.34, 1.0 - depth * 0.46 - weather_dim * 0.38)
            light_scale = max(0.24, 1.0 - depth * 0.38 - weather_dim * 0.46)
            dark = tuple(int(lerp(channel * dark_scale, target, weather_cool * 0.52)) for channel, target in zip(dark, (26, 36, 40)))
            light = tuple(int(lerp(channel * light_scale, target, weather_cool * 0.45)) for channel, target in zip(light, (68, 82, 88)))
            pygame.draw.rect(game.screen, dark, rect)
            accent_seed = game.hash_noise(chunk_x, chunk_y, 83)
            for index in range(4):
                circle_pos = Vector2(
                    rect.x + 40 + (index * 67 + accent_seed * 90) % max(80, CHUNK_SIZE - 80),
                    rect.y + 48 + (index * 53 + accent_seed * 70) % max(90, CHUNK_SIZE - 90),
                )
                pygame.draw.circle(game.screen, light, circle_pos, 42 + (index % 3) * 10)
            if depth > 0.04:
                veil = pygame.Surface(rect.size, pygame.SRCALPHA)
                veil.fill((10, 14, 16, int(22 + depth * 72)))
                game.screen.blit(veil, rect.topleft)
