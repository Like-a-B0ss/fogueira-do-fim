from __future__ import annotations

import pygame
from pygame import Vector2

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH, angle_to_vector, clamp


def draw_resource_nodes(game, shake_offset: Vector2) -> None:
    for node in game.resource_nodes:
        pos = game.world_to_screen(node.pos) + shake_offset
        if pos.x < -80 or pos.x > SCREEN_WIDTH + 80 or pos.y < -80 or pos.y > SCREEN_HEIGHT + 80:
            continue
        if node.kind == "food":
            draw_food_node(game, pos, node.radius, node.variant)
        else:
            draw_scrap_node(game, pos, node.radius, node.variant)

        if not node.is_available():
            overlay = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (18, 20, 20, 120), (40, 40), node.radius + 7)
            game.screen.blit(overlay, pos - Vector2(40, 40))


def draw_food_node(game, pos: Vector2, radius: int, variant: str = "") -> None:
    shadow = pygame.Rect(0, 0, int(radius * 1.9), int(radius * 0.88))
    shadow.center = (int(pos.x), int(pos.y + radius * 0.55))
    pygame.draw.ellipse(game.screen, (14, 18, 16), shadow)
    bush_colors = ((36, 79, 46), (52, 98, 58), (69, 124, 74))
    leaf_offsets = (
        Vector2(-radius * 0.46, 2),
        Vector2(radius * 0.08, -radius * 0.36),
        Vector2(radius * 0.5, 4),
        Vector2(-4, radius * 0.28),
    )
    for color, offset, scale in zip(bush_colors * 2, leaf_offsets, (0.78, 0.66, 0.7, 0.62)):
        pygame.draw.circle(game.screen, color, (int(pos.x + offset.x), int(pos.y + offset.y)), int(radius * scale))
    if variant in {"mushrooms", "roots"}:
        stem = (214, 198, 164)
        cap = (174, 98, 84) if variant == "mushrooms" else (146, 118, 82)
        for offset in (Vector2(-8, 4), Vector2(0, -3), Vector2(9, 6)):
            stem_pos = pos + offset
            pygame.draw.line(game.screen, stem, stem_pos + Vector2(0, 6), stem_pos, 2)
            pygame.draw.ellipse(game.screen, cap, pygame.Rect(stem_pos.x - 5, stem_pos.y - 2, 10, 6))
    elif variant == "flowers":
        for offset in (Vector2(-8, -4), Vector2(3, -8), Vector2(9, 5), Vector2(-5, 8)):
            flower = pos + offset
            pygame.draw.circle(game.screen, (236, 206, 122), flower, 3)
            pygame.draw.circle(game.screen, (191, 116, 88), flower + Vector2(2, 1), 3)
    elif variant == "herbs":
        for offset in (Vector2(-6, 5), Vector2(2, -7), Vector2(10, 2)):
            herb = pos + offset
            pygame.draw.line(game.screen, (90, 142, 74), herb + Vector2(0, 9), herb, 2)
            pygame.draw.circle(game.screen, (118, 176, 96), herb + Vector2(-2, -2), 3)
            pygame.draw.circle(game.screen, (106, 164, 88), herb + Vector2(2, -1), 3)
    else:
        for offset in (Vector2(-8, -4), Vector2(3, -8), Vector2(9, 5), Vector2(-5, 8), Vector2(6, -1)):
            berry_pos = pos + offset
            pygame.draw.circle(game.screen, (202, 72, 77), berry_pos, 4)
            pygame.draw.circle(game.screen, (238, 145, 128), berry_pos + Vector2(-1, -1), 2)


def draw_scrap_node(game, pos: Vector2, radius: int, variant: str = "") -> None:
    shadow = pygame.Rect(0, 0, int(radius * 1.8), int(radius * 0.82))
    shadow.center = (int(pos.x), int(pos.y + radius * 0.55))
    pygame.draw.ellipse(game.screen, (14, 18, 16), shadow)
    if variant in {"ore", "stonecache"}:
        colors = ((128, 134, 140), (96, 104, 112), (154, 164, 170))
        for index, offset in enumerate((Vector2(-10, 4), Vector2(8, -2), Vector2(2, -10))):
            rock = pygame.Rect(0, 0, 18 + index * 3, 14 + (index % 2) * 4)
            rock.center = (int(pos.x + offset.x), int(pos.y + offset.y))
            pygame.draw.rect(game.screen, colors[index], rock, border_radius=5)
            pygame.draw.rect(game.screen, (68, 74, 80), rock, 1, border_radius=5)
        return
    pieces = (
        pygame.Rect(int(pos.x - 14), int(pos.y - 6), 18, 14),
        pygame.Rect(int(pos.x - 4), int(pos.y - 14), 20, 12),
        pygame.Rect(int(pos.x + 6), int(pos.y - 1), 14, 11),
    )
    colors = ((93, 98, 107), (129, 136, 145), (75, 79, 86))
    for rect, color in zip(pieces, colors):
        pygame.draw.rect(game.screen, color, rect, border_radius=4)
        pygame.draw.rect(game.screen, (54, 57, 63), rect, 1, border_radius=4)
    wheel_center = (int(pos.x - 10), int(pos.y + 7))
    pygame.draw.circle(game.screen, (48, 51, 57), wheel_center, 7, 3)
    pygame.draw.line(game.screen, (160, 116, 72), (int(pos.x - 4), int(pos.y - 10)), (int(pos.x + 12), int(pos.y + 6)), 2)


def draw_barricades(game, shake_offset: Vector2) -> None:
    for barricade in game.barricades:
        pos = game.world_to_screen(barricade.pos) + shake_offset
        tangent = barricade.tangent
        normal = angle_to_vector(barricade.angle)
        span = barricade.span
        spike_level = getattr(barricade, "spike_level", 0)
        color = PALETTE["danger"] if barricade.health < barricade.max_health * 0.35 else PALETTE["wood"]
        if barricade.is_broken():
            color = (62, 50, 40)
        elif spike_level >= 2:
            color = (152, 116, 74)
        shadow_points = [
            pos + tangent * span * 0.52 + normal * 13,
            pos - tangent * span * 0.52 + normal * 13,
            pos - tangent * span * 0.52 - normal * 5,
            pos + tangent * span * 0.52 - normal * 5,
        ]
        pygame.draw.polygon(game.screen, (17, 18, 17), shadow_points)

        stake_count = 4 + barricade.tier
        for index in range(stake_count):
            t = 0.0 if stake_count == 1 else index / (stake_count - 1)
            offset = -span * 0.48 + span * 0.96 * t
            center = pos + tangent * offset
            stake_height = 22 + barricade.tier * 5 + (index % 2) * 4
            base_left = center - tangent * 4 - normal * 10
            base_right = center + tangent * 4 - normal * 10
            tip = center + normal * stake_height
            pygame.draw.polygon(game.screen, color, [base_left, tip, base_right])
            pygame.draw.polygon(game.screen, PALETTE["wood_dark"], [base_left, tip, base_right], 1)

        brace_a = [
            pos - tangent * span * 0.5 - normal * 4,
            pos + normal * 8,
            pos + tangent * span * 0.5 - normal * 4,
        ]
        brace_b = [
            pos - tangent * span * 0.5 + normal * 4,
            pos - normal * 8,
            pos + tangent * span * 0.5 + normal * 4,
        ]
        pygame.draw.lines(game.screen, PALETTE["wood_dark"], False, brace_a, 4)
        pygame.draw.lines(game.screen, PALETTE["wood_dark"], False, brace_b, 4)

        if spike_level > 0 and not barricade.is_broken():
            spike_color = (188, 176, 164) if spike_level >= 2 else (128, 120, 114)
            spike_count = 2 + spike_level * 2
            for index in range(spike_count):
                t = (index + 0.5) / spike_count
                offset = -span * 0.42 + span * 0.84 * t
                anchor = pos + tangent * offset + normal * (8 + barricade.tier * 1.6)
                tip = anchor + normal * (9 + spike_level * 3)
                left = anchor - tangent * (2 + spike_level * 0.6)
                right = anchor + tangent * (2 + spike_level * 0.6)
                pygame.draw.polygon(game.screen, spike_color, [left, tip, right])
                pygame.draw.polygon(game.screen, (72, 70, 68), [left, tip, right], 1)

        ratio = barricade.health / barricade.max_health
        bar_rect = pygame.Rect(0, 0, 52, 6)
        bar_rect.midbottom = (pos.x, pos.y - 18)
        pygame.draw.rect(game.screen, (26, 28, 28), bar_rect, border_radius=4)
        pygame.draw.rect(
            game.screen,
            PALETTE["heal"] if ratio > 0.5 else PALETTE["danger_soft"],
            (bar_rect.x + 1, bar_rect.y + 1, int((bar_rect.width - 2) * clamp(ratio, 0, 1)), bar_rect.height - 2),
            border_radius=4,
        )
        if spike_level > 0:
            spike_label = game.small_font.render(f"S{spike_level}", True, PALETTE["accent_soft"])
            game.screen.blit(spike_label, spike_label.get_rect(midbottom=(pos.x, bar_rect.y - 2)))








