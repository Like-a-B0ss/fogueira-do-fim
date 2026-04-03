from __future__ import annotations

import math

import pygame
from pygame import Vector2

from ...core.config import CAMP_CENTER, PALETTE, WORLD_HEIGHT, WORLD_WIDTH, angle_to_vector, lerp
from ...core.models import WorldFeature


def camp_visual_ellipses(world, padding: float = 0.0) -> list[pygame.Rect]:
    """Retorna manchas elipticas para desenhar a clareira de forma mais organica."""
    half = world.camp_half_size + padding
    specs = (
        (-0.04, -0.01, 2.08, 1.72),
        (0.03, 0.10, 1.76, 1.34),
        (-0.26, 0.20, 0.96, 0.68),
        (0.30, -0.15, 0.88, 0.62),
        (0.22, 0.27, 0.76, 0.54),
        (-0.33, -0.18, 0.78, 0.56),
    )
    ellipses: list[pygame.Rect] = []
    for offset_x, offset_y, width_scale, height_scale in specs:
        width = half * width_scale
        height = half * height_scale
        center = CAMP_CENTER + Vector2(half * offset_x, half * offset_y)
        rect = pygame.Rect(0, 0, int(width), int(height))
        rect.center = (int(center.x), int(center.y))
        ellipses.append(rect)
    return ellipses


def camp_visual_bounds(world, padding: float = 0.0) -> pygame.Rect:
    ellipses = camp_visual_ellipses(world, padding)
    if not ellipses:
        return world.camp_rect(padding)
    bounds = ellipses[0].copy()
    for rect in ellipses[1:]:
        bounds.union_ip(rect)
    return bounds


def camp_ground_anchors(world) -> list[Vector2]:
    """Pontos importantes usados para desenhar desgaste e trilhas internas da clareira."""
    anchors = [
        Vector2(CAMP_CENTER),
        Vector2(world.stockpile_pos),
        Vector2(world.workshop_pos),
        Vector2(world.kitchen_pos),
        Vector2(world.radio_pos),
    ]
    anchors.extend(Vector2(tent["pos"]) for tent in world.tents)
    return anchors


def paint_camp_ground(world, surface: pygame.Surface) -> None:
    """Desenha uma clareira mais organica, com terra batida e desgaste de uso."""
    camp_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
    earth_dark = (88, 63, 42)
    earth_mid = (118, 85, 56)
    earth_light = (154, 114, 74)
    earth_dust = (176, 136, 92)
    clearing_layers = (
        (camp_visual_ellipses(world, 102), (*PALETTE["clearing"], 56)),
        (camp_visual_ellipses(world, 42), (*earth_mid, 44)),
        (camp_visual_ellipses(world, -6), (*earth_light, 34)),
    )
    for ellipses, color in clearing_layers:
        for ellipse in ellipses:
            pygame.draw.ellipse(camp_surface, color, ellipse)

    packed_earth = (
        (pygame.Rect(int(CAMP_CENTER.x - world.camp_half_size * 0.98), int(CAMP_CENTER.y - world.camp_half_size * 0.62), int(world.camp_half_size * 1.96), int(world.camp_half_size * 1.24)), (*earth_dark, 54)),
        (pygame.Rect(int(CAMP_CENTER.x - world.camp_half_size * 0.86), int(CAMP_CENTER.y - world.camp_half_size * 0.54), int(world.camp_half_size * 1.72), int(world.camp_half_size * 1.08)), (*earth_mid, 72)),
        (pygame.Rect(int(CAMP_CENTER.x - world.camp_half_size * 0.62), int(CAMP_CENTER.y - world.camp_half_size * 0.38), int(world.camp_half_size * 1.24), int(world.camp_half_size * 0.76)), (*earth_light, 54)),
        (pygame.Rect(int(world.stockpile_pos.x - 104), int(world.stockpile_pos.y - 58), 208, 116), (*earth_mid, 58)),
        (pygame.Rect(int(world.workshop_pos.x - 94), int(world.workshop_pos.y - 52), 188, 104), (*earth_mid, 54)),
        (pygame.Rect(int(world.kitchen_pos.x - 88), int(world.kitchen_pos.y - 48), 176, 96), (*earth_mid, 50)),
        (pygame.Rect(int(world.radio_pos.x - 72), int(world.radio_pos.y - 42), 144, 84), (*earth_light, 38)),
    )
    for rect, color in packed_earth:
        pygame.draw.ellipse(camp_surface, color, rect)

    anchor_paths = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
    center = Vector2(CAMP_CENTER)
    for anchor in camp_ground_anchors(world):
        if anchor.distance_to(center) < 8:
            continue
        sway = Vector2((anchor.y - center.y) * 0.04, (center.x - anchor.x) * 0.04)
        points = [center, center.lerp(anchor, 0.45) + sway, anchor]
        pygame.draw.lines(anchor_paths, (*earth_dark, 82), False, points, 44)
        pygame.draw.lines(anchor_paths, (*earth_mid, 76), False, points, 26)
        pygame.draw.lines(anchor_paths, (*earth_light, 42), False, points, 10)
    camp_surface.blit(anchor_paths, (0, 0))

    worn_patches = (
        pygame.Rect(int(CAMP_CENTER.x - world.camp_half_size * 0.78), int(CAMP_CENTER.y - 26), int(world.camp_half_size * 1.56), 74),
        pygame.Rect(int(CAMP_CENTER.x - 62), int(CAMP_CENTER.y - world.camp_half_size * 0.62), 124, int(world.camp_half_size * 1.18)),
        pygame.Rect(int(world.workshop_pos.x - 74), int(world.workshop_pos.y - 42), 148, 84),
        pygame.Rect(int(world.kitchen_pos.x - 72), int(world.kitchen_pos.y - 40), 144, 80),
        pygame.Rect(int(world.radio_pos.x - 58), int(world.radio_pos.y - 34), 116, 68),
        pygame.Rect(int(CAMP_CENTER.x - 88), int(CAMP_CENTER.y - 70), 176, 140),
    )
    patch_colors = (
        (102, 74, 50, 42),
        (126, 91, 60, 34),
        (158, 116, 78, 26),
    )
    for index, patch in enumerate(worn_patches):
        pygame.draw.ellipse(camp_surface, patch_colors[index % len(patch_colors)], patch)

    for _ in range(320):
        offset = Vector2(
            world.random.uniform(-world.camp_half_size * 0.94, world.camp_half_size * 0.94),
            world.random.uniform(-world.camp_half_size * 0.82, world.camp_half_size * 0.82),
        )
        pos = CAMP_CENTER + offset
        if not world.point_in_camp_square(pos, -12):
            continue
        width = world.random.randint(6, 16)
        height = world.random.randint(3, 9)
        dust = pygame.Rect(0, 0, width, height)
        dust.center = (int(pos.x), int(pos.y))
        dust_color = (*earth_dust, world.random.randint(20, 42))
        pygame.draw.ellipse(camp_surface, dust_color, dust)

    edge_tufts = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
    for ellipse in camp_visual_ellipses(world, 84):
        for _ in range(18):
            angle = world.random.random() * math.tau
            rim = Vector2(ellipse.width * 0.5 * math.cos(angle), ellipse.height * 0.5 * math.sin(angle))
            pos = Vector2(ellipse.center) + rim * world.random.uniform(0.82, 1.03)
            tuft = pygame.Rect(0, 0, world.random.randint(18, 34), world.random.randint(8, 16))
            tuft.center = (int(pos.x), int(pos.y))
            color = (54, 84, 47, world.random.randint(26, 40))
            pygame.draw.ellipse(edge_tufts, color, tuft)
    camp_surface.blit(edge_tufts, (0, 0))

    ember_ring = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
    for radius, alpha in ((132, 10), (94, 16), (62, 22)):
        rect = pygame.Rect(0, 0, radius * 2, int(radius * 1.45))
        rect.center = (int(world.bonfire_pos.x), int(world.bonfire_pos.y + 10))
        pygame.draw.ellipse(ember_ring, (184, 136, 82, alpha), rect)
    camp_surface.blit(ember_ring, (0, 0))

    for _ in range(120):
        offset = Vector2(
            world.random.uniform(-world.camp_half_size * 0.92, world.camp_half_size * 0.92),
            world.random.uniform(-world.camp_half_size * 0.92, world.camp_half_size * 0.92),
        )
        pos = CAMP_CENTER + offset
        if not world.point_in_camp_square(pos, 10):
            continue
        stone = pygame.Rect(0, 0, world.random.randint(4, 10), world.random.randint(2, 5))
        stone.center = (int(pos.x), int(pos.y))
        pygame.draw.ellipse(camp_surface, (96, 98, 82, world.random.randint(18, 34)), stone)

    surface.blit(camp_surface, (0, 0))


def camp_loop_points(world, inset: float = 0.0, *, segments_per_side: int = 4, jitter: float = 0.0) -> list[Vector2]:
    half = world.camp_half_size - inset
    corners = [
        Vector2(CAMP_CENTER.x - half, CAMP_CENTER.y - half),
        Vector2(CAMP_CENTER.x + half, CAMP_CENTER.y - half),
        Vector2(CAMP_CENTER.x + half, CAMP_CENTER.y + half),
        Vector2(CAMP_CENTER.x - half, CAMP_CENTER.y + half),
    ]
    points: list[Vector2] = []
    for index in range(4):
        start = corners[index]
        end = corners[(index + 1) % 4]
        for step in range(segments_per_side):
            t = step / segments_per_side
            point = start.lerp(end, t)
            if jitter:
                point += Vector2(
                    world.random.uniform(-jitter, jitter),
                    world.random.uniform(-jitter, jitter),
                )
            points.append(point)
    points.append(Vector2(points[0]))
    return points


def camp_perimeter_point(world, seed_index: int = 0, *, jitter: float = 0.0) -> Vector2:
    points = camp_loop_points(world, 26, segments_per_side=3)
    point = Vector2(points[seed_index % max(1, len(points) - 1)])
    if jitter:
        point += Vector2(
            world.random.uniform(-jitter, jitter),
            world.random.uniform(-jitter, jitter),
        )
    return point


def generate_path_network(world) -> list[list[Vector2]]:
    paths: list[list[Vector2]] = []
    anchors = (
        (Vector2(-80, CAMP_CENTER.y - 180), CAMP_CENTER + Vector2(135, -36)),
        (Vector2(CAMP_CENTER.x + 80, -60), CAMP_CENTER + Vector2(12, 112)),
        (Vector2(WORLD_WIDTH + 50, CAMP_CENTER.y + 210), CAMP_CENTER + Vector2(-24, 88)),
    )
    for start, end in anchors:
        paths.append(make_path_points(world, start, end, variation=240, segments=28))

    feature_targets = [feature for feature in world.world_features if feature.kind in {"ruin", "meadow"}]
    world.random.shuffle(feature_targets)
    for feature in feature_targets[:3]:
        offset = angle_to_vector(feature.accent * math.tau) * 48
        paths.append(
            make_path_points(
                world,
                CAMP_CENTER + offset * 0.35,
                feature.pos + offset,
                variation=170,
                segments=24,
            )
        )

    paths.append(camp_loop_points(world, 38, segments_per_side=4, jitter=10))
    return paths


def make_path_points(
    world,
    start: Vector2,
    end: Vector2,
    *,
    variation: float,
    segments: int,
) -> list[Vector2]:
    control_a = start.lerp(end, 0.3) + Vector2(
        world.random.uniform(-variation, variation),
        world.random.uniform(-variation, variation),
    )
    control_b = start.lerp(end, 0.68) + Vector2(
        world.random.uniform(-variation, variation),
        world.random.uniform(-variation, variation),
    )
    points = []
    for step in range(segments):
        t = step / max(1, segments - 1)
        p0 = start.lerp(control_a, t)
        p1 = control_a.lerp(control_b, t)
        p2 = control_b.lerp(end, t)
        q0 = p0.lerp(p1, t)
        q1 = p1.lerp(p2, t)
        points.append(q0.lerp(q1, t))
    return points


def paint_feature(world, surface: pygame.Surface, feature: WorldFeature) -> None:
    pos = (int(feature.pos.x), int(feature.pos.y))
    radius = int(feature.radius)
    accent_angle = feature.accent * math.tau

    if feature.kind == "grove":
        pygame.draw.circle(surface, (22, 45, 31, 118), pos, radius)
        pygame.draw.circle(
            surface,
            (37, 68, 42, 84),
            (
                int(feature.pos.x + math.cos(accent_angle) * radius * 0.24),
                int(feature.pos.y + math.sin(accent_angle) * radius * 0.18),
            ),
            int(radius * 0.72),
        )
        for index in range(11):
            angle = accent_angle + index * 0.54
            offset = angle_to_vector(angle) * (radius * (0.16 + (index % 4) * 0.12))
            pygame.draw.circle(
                surface,
                (30, 58, 37, 46),
                (int(feature.pos.x + offset.x), int(feature.pos.y + offset.y)),
                int(radius * 0.15),
            )
    elif feature.kind == "meadow":
        pygame.draw.circle(surface, (89, 119, 72, 98), pos, radius)
        pygame.draw.circle(
            surface,
            (118, 148, 82, 58),
            (
                int(feature.pos.x - math.cos(accent_angle) * radius * 0.22),
                int(feature.pos.y + math.sin(accent_angle) * radius * 0.18),
            ),
            int(radius * 0.58),
        )
        for index in range(10):
            angle = accent_angle + index * 0.62
            offset = angle_to_vector(angle) * (radius * (0.18 + (index % 3) * 0.16))
            pygame.draw.circle(
                surface,
                (166, 166, 92, 34),
                (int(feature.pos.x + offset.x), int(feature.pos.y + offset.y)),
                6,
            )
    elif feature.kind == "swamp":
        swamp_rect = pygame.Rect(0, 0, int(radius * 1.7), int(radius * 1.1))
        swamp_rect.center = pos
        pygame.draw.ellipse(surface, (22, 53, 50, 126), swamp_rect)
        pygame.draw.ellipse(
            surface,
            (59, 85, 74, 62),
            swamp_rect.inflate(-int(radius * 0.36), -int(radius * 0.28)),
        )
        pygame.draw.circle(surface, (73, 82, 54, 44), pos, int(radius * 0.92))
    elif feature.kind == "ruin":
        pygame.draw.circle(surface, (87, 78, 66, 104), pos, radius)
        pygame.draw.circle(surface, (107, 92, 73, 52), pos, int(radius * 0.62))
        for index in range(7):
            angle = accent_angle + index * 0.76
            offset = angle_to_vector(angle) * (radius * 0.45)
            rubble = pygame.Rect(0, 0, 18 + index % 3 * 4, 12 + index % 2 * 3)
            rubble.center = (int(feature.pos.x + offset.x), int(feature.pos.y + offset.y))
            pygame.draw.rect(surface, (124, 118, 110, 120), rubble, border_radius=4)


def draw_path(
    world,
    surface: pygame.Surface,
    points: list[Vector2],
    *,
    base_width: int = 44,
    highlight_width: int = 12,
    base_alpha: int = 160,
    highlight_alpha: int = 90,
) -> None:
    if len(points) > 1:
        pygame.draw.lines(surface, (*PALETTE["path"], base_alpha), False, points, base_width)
        pygame.draw.lines(surface, (*PALETTE["path_light"], highlight_alpha), False, points, highlight_width)


def build_terrain_surface(world) -> pygame.Surface:
    surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
    surface.fill(PALETTE["forest_floor"])

    for _ in range(540):
        radius = world.random.randint(20, 80)
        color = (
            lerp(PALETTE["forest_floor_dark"][0], PALETTE["forest_floor_light"][0], world.random.random()),
            lerp(PALETTE["forest_floor_dark"][1], PALETTE["forest_floor_light"][1], world.random.random()),
            lerp(PALETTE["forest_floor_dark"][2], PALETTE["forest_floor_light"][2], world.random.random()),
        )
        pygame.draw.circle(
            surface,
            tuple(int(channel) for channel in color),
            (world.random.randint(0, WORLD_WIDTH), world.random.randint(0, WORLD_HEIGHT)),
            radius,
        )

    feature_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
    for feature in world.world_features:
        world.paint_feature(feature_surface, feature)
    surface.blit(feature_surface, (0, 0))

    world.paint_camp_ground(surface)

    path_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
    for index, path in enumerate(world.path_network):
        if index == len(world.path_network) - 1:
            world.draw_path(path_surface, path, base_width=28, highlight_width=10, base_alpha=110)
        else:
            world.draw_path(path_surface, path)
    surface.blit(path_surface, (0, 0))
    return surface









