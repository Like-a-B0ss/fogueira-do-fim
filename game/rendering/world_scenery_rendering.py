from __future__ import annotations

import math

import pygame
from pygame import Vector2

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH, angle_to_vector, lerp


def draw_camp(game, shake_offset: Vector2) -> None:
    for tree in game.trees:
        draw_tree(game, tree, shake_offset)

    world_bounds = game.camp_visual_bounds(118)
    screen_bounds = world_bounds.move(shake_offset.x, shake_offset.y)
    camp_surface = pygame.Surface((world_bounds.width, world_bounds.height), pygame.SRCALPHA)
    outline_sets = (
        (game.camp_visual_ellipses(28), (118, 112, 78, 18), 2),
        (game.camp_visual_ellipses(-18), (142, 136, 96, 14), 1),
    )
    for ellipses, color, width in outline_sets:
        for ellipse in ellipses:
            local = ellipse.move(-world_bounds.x, -world_bounds.y)
            pygame.draw.ellipse(camp_surface, color, local, width)
    game.screen.blit(camp_surface, screen_bounds.topleft)

    for tent in game.tents:
        pos = game.world_to_screen(Vector2(tent["pos"])) + shake_offset
        draw_player_tent(game, pos, float(tent["angle"]), float(tent["scale"]), float(tent.get("tone", 0.5)))

    draw_stockpile(game, shake_offset)
    draw_station(game, game.workshop_pos, "oficina", PALETTE["wood"], shake_offset)
    draw_station(game, game.kitchen_pos, "fogao", (162, 126, 82), shake_offset)
    draw_station(game, game.radio_pos, "radio", (100, 114, 124), shake_offset)
    draw_expedition_caravan(game, shake_offset)
    draw_bonfire(game, shake_offset)


def draw_expedition_caravan(game, shake_offset: Vector2) -> None:
    caravan = game.expedition_caravan_state()
    if not caravan:
        return
    start = game.world_to_screen(game.radio_pos) + shake_offset
    edge = game.world_to_screen(game.expedition_route_edge_point()) + shake_offset
    direction = Vector2(edge - start)
    if direction.length_squared() <= 0.01:
        return
    unit = direction.normalize()
    lateral = Vector2(-unit.y, unit.x)
    progress = float(caravan["progress"])
    if caravan["phase"] == "outbound":
        center = start.lerp(edge, progress * 0.72)
    else:
        center = edge.lerp(start, progress * 0.72)

    for offset_index, offset_amount in enumerate((-18, 0, 18)):
        walker = center - unit * (16 * offset_index) + lateral * (offset_amount * 0.18)
        pygame.draw.ellipse(game.screen, (12, 15, 16), pygame.Rect(walker.x - 8, walker.y + 7, 16, 6))
        pygame.draw.circle(game.screen, (146, 162, 174), (int(walker.x), int(walker.y - 10)), 5)
        pygame.draw.line(game.screen, (88, 102, 114), walker + Vector2(0, -6), walker + Vector2(0, 4), 2)

    cart = center + unit * 10
    body = pygame.Rect(0, 0, 22, 12)
    body.center = (int(cart.x), int(cart.y))
    pygame.draw.rect(game.screen, (102, 84, 58), body, border_radius=4)
    pygame.draw.rect(game.screen, (68, 52, 36), body, 2, border_radius=4)
    wheel_a = (int(cart.x - 8), int(cart.y + 8))
    wheel_b = (int(cart.x + 8), int(cart.y + 8))
    pygame.draw.circle(game.screen, (34, 30, 26), wheel_a, 4)
    pygame.draw.circle(game.screen, (34, 30, 26), wheel_b, 4)
    pygame.draw.circle(game.screen, (110, 98, 78), wheel_a, 2)
    pygame.draw.circle(game.screen, (110, 98, 78), wheel_b, 2)

    label_text = "saindo" if caravan["phase"] == "outbound" else "voltando"
    label = game.small_font.render(f"caravana {label_text}", True, PALETTE["text"])
    box = pygame.Rect(0, 0, label.get_width() + 10, label.get_height() + 4)
    box.midbottom = (int(center.x), int(center.y - 16))
    pygame.draw.rect(game.screen, (18, 24, 26), box, border_radius=7)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], box, 1, border_radius=7)
    game.screen.blit(label, label.get_rect(center=box.center))

    expedition = game.active_expedition
    if expedition and str(expedition.get("skirmish_state", "")) == "active" and expedition.get("skirmish_pos") is not None:
        skirmish = game.world_to_screen(Vector2(expedition["skirmish_pos"])) + shake_offset
        ring_color = PALETTE["danger_soft"]
        pygame.draw.circle(game.screen, ring_color, skirmish, 24, 3)
        pygame.draw.circle(game.screen, (18, 24, 26), skirmish, 10)
        pygame.draw.circle(game.screen, (128, 164, 208), skirmish, 6)
        for offset in (-18, 0, 18):
            walker = skirmish + lateral * (offset * 0.4)
            pygame.draw.ellipse(game.screen, (12, 15, 16), pygame.Rect(walker.x - 8, walker.y + 7, 16, 6))
            pygame.draw.circle(game.screen, (146, 162, 174), (int(walker.x), int(walker.y - 10)), 5)
            pygame.draw.line(game.screen, (88, 102, 114), walker + Vector2(0, -6), walker + Vector2(0, 4), 2)
        alert = game.small_font.render("coluna em combate", True, PALETTE["text"])
        alert_box = pygame.Rect(0, 0, alert.get_width() + 12, alert.get_height() + 4)
        alert_box.midbottom = (int(skirmish.x), int(skirmish.y - 18))
        pygame.draw.rect(game.screen, (18, 24, 26), alert_box, border_radius=7)
        pygame.draw.rect(game.screen, ring_color, alert_box, 1, border_radius=7)
        game.screen.blit(alert, alert.get_rect(center=alert_box.center))


def draw_tree(game, tree: dict[str, object], shake_offset: Vector2) -> None:
    pos = game.world_to_screen(Vector2(tree["pos"])) + shake_offset
    radius = int(tree["radius"])
    if pos.x < -100 or pos.x > SCREEN_WIDTH + 100 or pos.y < -100 or pos.y > SCREEN_HEIGHT + 100:
        return

    if tree.get("harvested", False):
        stump_rect = pygame.Rect(0, 0, int(radius * 0.9), int(radius * 0.46))
        stump_rect.center = (int(pos.x), int(pos.y + radius * 0.72))
        pygame.draw.ellipse(game.screen, (14, 18, 16), stump_rect.inflate(8, 10))
        pygame.draw.ellipse(game.screen, (96, 70, 44), stump_rect)
        pygame.draw.ellipse(game.screen, (62, 43, 28), stump_rect, 2)
        ring_rect = stump_rect.inflate(-10, -8)
        if ring_rect.width > 2 and ring_rect.height > 2:
            pygame.draw.ellipse(game.screen, (138, 110, 72), ring_rect, 1)
        return

    tone = float(tree.get("tone", 0.5))
    spread = float(tree.get("spread", 1.0))
    branch_bias = float(tree.get("branch_bias", 0.0))
    trunk_top = pos + Vector2(0, -radius * 0.88)
    trunk_base = pos + Vector2(0, radius * 0.68)
    trunk_half = radius * 0.2
    crown_color = (
        int(lerp(68, 88, tone)),
        int(lerp(96, 122, tone)),
        int(lerp(52, 72, tone)),
    )
    crown_dark = tuple(max(0, int(channel * 0.72)) for channel in crown_color)
    crown_light = tuple(min(255, int(channel * 1.12)) for channel in crown_color)

    shadow = pygame.Rect(0, 0, int(radius * 2.2), int(radius * 0.96))
    shadow.center = (int(pos.x), int(pos.y + radius * 0.84))
    pygame.draw.ellipse(game.screen, (12, 16, 15), shadow)
    trunk_points = [
        trunk_top + Vector2(-trunk_half * 0.7, 0),
        trunk_top + Vector2(trunk_half * 0.7, 0),
        trunk_base + Vector2(trunk_half, 0),
        trunk_base + Vector2(-trunk_half, 0),
    ]
    pygame.draw.polygon(game.screen, (92, 66, 42), trunk_points)
    pygame.draw.polygon(game.screen, (62, 43, 28), trunk_points, 2)

    for bark_y in (
        trunk_top.lerp(trunk_base, 0.2),
        trunk_top.lerp(trunk_base, 0.45),
        trunk_top.lerp(trunk_base, 0.7),
    ):
        pygame.draw.line(
            game.screen,
            (119, 89, 55),
            bark_y + Vector2(-trunk_half * 0.3, 0),
            bark_y + Vector2(trunk_half * 0.25, 0),
            1,
        )

    for index in range(3):
        direction = -1 if index % 2 == 0 else 1
        branch_start = trunk_top.lerp(trunk_base, 0.2 + index * 0.16)
        branch_end = branch_start + Vector2(
            direction * radius * (0.38 + 0.12 * branch_bias),
            -radius * (0.16 + index * 0.05),
        )
        pygame.draw.line(game.screen, (74, 50, 34), branch_start, branch_end, 3)

    cluster_centers = [
        trunk_top + Vector2(-radius * 0.52 * spread, radius * 0.08),
        trunk_top + Vector2(radius * 0.1 * branch_bias, -radius * 0.38),
        trunk_top + Vector2(radius * 0.56 * spread, -radius * 0.02),
        trunk_top + Vector2(radius * 0.12, radius * 0.26),
    ]
    cluster_sizes = [0.86, 0.78, 0.72, 0.66]
    for center, size in zip(cluster_centers, cluster_sizes):
        pygame.draw.circle(game.screen, crown_dark, (int(center.x), int(center.y + radius * 0.12)), int(radius * size))
        pygame.draw.circle(game.screen, crown_color, (int(center.x), int(center.y)), int(radius * size))
        pygame.draw.circle(
            game.screen,
            crown_light,
            (int(center.x - radius * 0.22), int(center.y - radius * 0.18)),
            int(radius * size * 0.5),
        )


def draw_buildings(game, shake_offset: Vector2) -> None:
    for building in game.buildings:
        pos = game.world_to_screen(building.pos) + shake_offset
        if pos.x < -120 or pos.x > SCREEN_WIDTH + 120 or pos.y < -120 or pos.y > SCREEN_HEIGHT + 120:
            continue
        if building.kind == "barraca":
            draw_player_tent(game, pos, 0.0, 0.92, 0.62)
        elif building.kind == "torre":
            draw_watchtower(game, pos)
        elif building.kind == "horta":
            draw_garden_plot(game, pos, ready=game.garden_is_ready(building))
        elif building.kind == "anexo":
            draw_workshop_annex(game, pos)
        elif building.kind == "serraria":
            draw_sawmill(game, pos)
        elif building.kind == "cozinha":
            draw_cookhouse(game, pos)
        elif building.kind == "enfermaria":
            draw_infirmary(game, pos)

        if building.assigned_to:
            text = game.small_font.render(building.assigned_to.lower(), True, PALETTE["text"])
            box = pygame.Rect(0, 0, text.get_width() + 12, text.get_height() + 4)
            box.midbottom = (pos.x, pos.y - building.size * 0.7)
            pygame.draw.rect(game.screen, (18, 24, 26), box, border_radius=8)
            pygame.draw.rect(game.screen, PALETTE["ui_line"], box, 1, border_radius=8)
            game.screen.blit(text, text.get_rect(center=box.center))


def draw_player_tent(game, pos: Vector2, angle: float, scale: float, tone: float = 0.5) -> None:
    forward = angle_to_vector(angle)
    side = angle_to_vector(angle + math.pi / 2)
    base = 54 * scale
    depth = 34 * scale
    ridge = 36 * scale
    canvas_base = (
        int(lerp(116, 146, tone)),
        int(lerp(96, 128, tone)),
        int(lerp(68, 92, tone)),
    )
    canvas_light = tuple(min(255, int(channel * 1.14)) for channel in canvas_base)
    canvas_dark = tuple(max(0, int(channel * 0.72)) for channel in canvas_base)

    tent_back = pos - forward * depth * 0.52
    tip = pos + forward * ridge * 0.62
    left = tent_back + side * base * 0.52
    right = tent_back - side * base * 0.52
    front_left = pos + side * base * 0.28
    front_right = pos - side * base * 0.28
    entrance = pos + forward * 9 * scale

    shadow = pygame.Rect(0, 0, int(base * 1.36), int(depth * 0.92))
    shadow.center = (int(pos.x), int(pos.y + 20 * scale))
    pygame.draw.ellipse(game.screen, (10, 14, 13), shadow)

    back_panel = [tip, left, right]
    left_flap = [tip, left, entrance]
    right_flap = [tip, entrance, right]
    ground = [front_left, left, right, front_right]
    pygame.draw.polygon(game.screen, (72, 54, 34), ground)
    pygame.draw.polygon(game.screen, canvas_base, back_panel)
    pygame.draw.polygon(game.screen, canvas_light, left_flap)
    pygame.draw.polygon(game.screen, canvas_dark, right_flap)
    pygame.draw.polygon(game.screen, PALETTE["wood_dark"], back_panel, 2)
    pygame.draw.polygon(game.screen, PALETTE["wood_dark"], left_flap, 1)
    pygame.draw.polygon(game.screen, PALETTE["wood_dark"], right_flap, 1)

    door = pygame.Rect(0, 0, int(16 * scale), int(18 * scale))
    door.center = (int(entrance.x), int(entrance.y + 8 * scale))
    pygame.draw.ellipse(game.screen, (38, 28, 22), door)
    bedroll = pygame.Rect(0, 0, int(26 * scale), int(8 * scale))
    bedroll.center = (int(pos.x), int(pos.y + 14 * scale))
    pygame.draw.ellipse(game.screen, (92, 116, 124), bedroll)
    pygame.draw.ellipse(game.screen, (58, 72, 76), bedroll, 1)

    pole_top = tip + Vector2(0, -4 * scale)
    pygame.draw.line(game.screen, (86, 62, 40), tip, pole_top, 2)
    for anchor, offset in ((left, -1), (right, 1)):
        peg = anchor + forward * (10 * scale) + side * (offset * 8 * scale)
        pygame.draw.line(game.screen, (96, 84, 64), anchor, peg, 1)
        pygame.draw.line(game.screen, (84, 62, 46), peg, peg + Vector2(0, 6 * scale), 2)


def draw_watchtower(game, pos: Vector2) -> None:
    shadow = pygame.Rect(0, 0, 48, 16)
    shadow.center = (int(pos.x), int(pos.y + 18))
    pygame.draw.ellipse(game.screen, (14, 18, 16), shadow)
    for offset in (-14, 14):
        pygame.draw.line(game.screen, PALETTE["wood_dark"], pos + Vector2(offset, 18), pos + Vector2(offset * 0.45, -16), 4)
    deck = pygame.Rect(0, 0, 42, 14)
    deck.center = (int(pos.x), int(pos.y - 20))
    pygame.draw.rect(game.screen, PALETTE["wood"], deck, border_radius=4)
    pygame.draw.rect(game.screen, PALETTE["wood_dark"], deck, 2, border_radius=4)
    pygame.draw.line(game.screen, (156, 136, 102), (deck.x + 6, deck.y + 3), (deck.right - 6, deck.y + 3), 1)
    pygame.draw.line(game.screen, (92, 74, 50), (deck.x + 6, deck.bottom - 4), (deck.right - 6, deck.bottom - 4), 1)
    pygame.draw.line(game.screen, PALETTE["wood_dark"], deck.midtop, deck.midtop + Vector2(0, -18), 3)
    pygame.draw.polygon(game.screen, (148, 128, 82), [deck.midtop + Vector2(0, -24), deck.midtop + Vector2(-16, -6), deck.midtop + Vector2(16, -6)])
    lantern = deck.midtop + Vector2(12, -4)
    pygame.draw.circle(game.screen, (218, 176, 92), lantern, 3)
    glow = pygame.Surface((26, 26), pygame.SRCALPHA)
    pygame.draw.circle(glow, (236, 182, 92, 34), (13, 13), 10)
    game.screen.blit(glow, Vector2(lantern) - Vector2(13, 13))


def draw_garden_plot(game, pos: Vector2, *, ready: bool = True) -> None:
    rect = pygame.Rect(0, 0, 54, 34)
    rect.center = (int(pos.x), int(pos.y))
    pygame.draw.rect(game.screen, (94, 74, 46), rect, border_radius=8)
    pygame.draw.rect(game.screen, (61, 45, 31), rect, 2, border_radius=8)
    fence = rect.inflate(10, 8)
    pygame.draw.rect(game.screen, (116, 92, 58), fence, 2, border_radius=10)
    for row in range(3):
        y = rect.y + 8 + row * 8
        pygame.draw.line(game.screen, (128, 95, 58), (rect.x + 4, y), (rect.right - 4, y), 2)
    stem_color = (62, 116, 64) if ready else (88, 92, 76)
    leaf_light = (106, 162, 82) if ready else (118, 122, 96)
    leaf_dark = (88, 148, 74) if ready else (96, 102, 82)
    for index, offset in enumerate((-16, -5, 8, 19)):
        sprout = pos + Vector2(offset, (-4, 2, 5, -1)[index])
        pygame.draw.line(game.screen, stem_color, sprout + Vector2(0, 10), sprout, 2)
        pygame.draw.circle(game.screen, leaf_light, sprout + Vector2(-2, -2), 3)
        pygame.draw.circle(game.screen, leaf_dark, sprout + Vector2(2, -1), 3)
    bucket = pygame.Rect(0, 0, 10, 10)
    bucket.center = (int(pos.x + 24), int(pos.y + 10))
    pygame.draw.rect(game.screen, (96, 108, 118), bucket, border_radius=3)
    pygame.draw.rect(game.screen, (62, 74, 84), bucket, 1, border_radius=3)


def draw_workshop_annex(game, pos: Vector2) -> None:
    rect = pygame.Rect(0, 0, 54, 40)
    rect.center = (int(pos.x), int(pos.y))
    pygame.draw.rect(game.screen, (112, 92, 66), rect, border_radius=8)
    pygame.draw.rect(game.screen, PALETTE["wood_dark"], rect, 2, border_radius=8)
    roof = [rect.midtop + Vector2(0, -16), rect.topleft + Vector2(-6, 2), rect.topright + Vector2(6, 2)]
    pygame.draw.polygon(game.screen, (82, 72, 58), roof)
    pygame.draw.line(game.screen, (138, 124, 102), (rect.x + 14, rect.y + 12), (rect.right - 14, rect.y + 12), 2)
    pygame.draw.line(game.screen, (138, 124, 102), (rect.x + 14, rect.y + 22), (rect.right - 14, rect.y + 22), 2)
    pygame.draw.line(game.screen, (138, 124, 102), (rect.centerx, rect.y + 10), (rect.centerx, rect.bottom - 8), 2)
    tool_rack = pygame.Rect(rect.x + 8, rect.bottom - 10, 18, 6)
    pygame.draw.rect(game.screen, (74, 56, 38), tool_rack, border_radius=2)
    pygame.draw.line(game.screen, (162, 146, 120), tool_rack.midleft + Vector2(4, -8), tool_rack.midleft + Vector2(4, 0), 2)
    pygame.draw.line(game.screen, (144, 126, 98), tool_rack.midleft + Vector2(10, -7), tool_rack.midleft + Vector2(10, 0), 2)


def draw_sawmill(game, pos: Vector2) -> None:
    base = pygame.Rect(0, 0, 58, 38)
    base.center = (int(pos.x), int(pos.y + 4))
    pygame.draw.rect(game.screen, (102, 84, 58), base, border_radius=8)
    pygame.draw.rect(game.screen, PALETTE["wood_dark"], base, 2, border_radius=8)
    for offset in (-16, 0, 16):
        log = pygame.Rect(0, 0, 22, 8)
        log.center = (int(pos.x - 26 + offset * 0.65), int(pos.y + 10 + abs(offset) * 0.1))
        pygame.draw.ellipse(game.screen, (118, 82, 48), log)
        pygame.draw.ellipse(game.screen, (72, 46, 30), log, 2)
    blade = pygame.Rect(0, 0, 12, 28)
    blade.center = (int(pos.x + 16), int(pos.y - 10))
    pygame.draw.rect(game.screen, (142, 150, 154), blade, border_radius=4)
    pygame.draw.rect(game.screen, (82, 89, 94), blade, 1, border_radius=4)
    rail = pygame.Rect(base.x + 6, base.y + 6, 30, 6)
    pygame.draw.rect(game.screen, (132, 110, 72), rail, border_radius=3)
    stack = pygame.Rect(0, 0, 18, 12)
    stack.center = (int(pos.x - 18), int(pos.y - 10))
    pygame.draw.rect(game.screen, (136, 102, 64), stack, border_radius=3)
    pygame.draw.line(game.screen, (86, 62, 40), (stack.x + 3, stack.y + 4), (stack.right - 3, stack.y + 4), 1)
    pygame.draw.line(game.screen, (86, 62, 40), (stack.x + 3, stack.y + 8), (stack.right - 3, stack.y + 8), 1)


def draw_cookhouse(game, pos: Vector2) -> None:
    rect = pygame.Rect(0, 0, 56, 42)
    rect.center = (int(pos.x), int(pos.y))
    pygame.draw.rect(game.screen, (128, 96, 64), rect, border_radius=10)
    pygame.draw.rect(game.screen, PALETTE["wood_dark"], rect, 2, border_radius=10)
    roof = [rect.midtop + Vector2(0, -18), rect.topleft + Vector2(-6, 4), rect.topright + Vector2(6, 4)]
    pygame.draw.polygon(game.screen, (90, 74, 58), roof)
    oven = pygame.Rect(0, 0, 20, 16)
    oven.center = (int(pos.x), int(pos.y + 8))
    pygame.draw.rect(game.screen, (70, 56, 48), oven, border_radius=5)
    pygame.draw.rect(game.screen, (38, 24, 22), oven.inflate(-8, -4), border_radius=4)
    pygame.draw.circle(game.screen, (214, 164, 88), pos + Vector2(16, -4), 7)
    pygame.draw.circle(game.screen, (236, 196, 116), pos + Vector2(14, -6), 4)
    chimney = pygame.Rect(0, 0, 8, 16)
    chimney.midbottom = (int(pos.x + 14), int(rect.y + 6))
    pygame.draw.rect(game.screen, (74, 62, 58), chimney, border_radius=2)
    pygame.draw.circle(game.screen, (210, 210, 210), chimney.midtop + Vector2(-2, -6), 3)
    pygame.draw.circle(game.screen, (190, 190, 190), chimney.midtop + Vector2(3, -11), 2)


def draw_infirmary(game, pos: Vector2) -> None:
    rect = pygame.Rect(0, 0, 54, 40)
    rect.center = (int(pos.x), int(pos.y))
    pygame.draw.rect(game.screen, (114, 124, 112), rect, border_radius=9)
    pygame.draw.rect(game.screen, (74, 82, 72), rect, 2, border_radius=9)
    roof = [rect.midtop + Vector2(0, -14), rect.topleft + Vector2(-4, 4), rect.topright + Vector2(4, 4)]
    pygame.draw.polygon(game.screen, (92, 102, 92), roof)
    pygame.draw.rect(game.screen, (228, 226, 212), pygame.Rect(rect.centerx - 9, rect.y + 8, 18, 18), border_radius=4)
    pygame.draw.rect(game.screen, (178, 62, 62), pygame.Rect(rect.centerx - 3, rect.y + 10, 6, 14), border_radius=2)
    pygame.draw.rect(game.screen, (178, 62, 62), pygame.Rect(rect.centerx - 7, rect.y + 14, 14, 6), border_radius=2)
    cot = pygame.Rect(0, 0, 18, 8)
    cot.center = (int(pos.x - 14), int(pos.y + 8))
    pygame.draw.rect(game.screen, (182, 196, 188), cot, border_radius=3)
    pygame.draw.rect(game.screen, (98, 112, 104), cot, 1, border_radius=3)
    lamp = pos + Vector2(16, -8)
    pygame.draw.circle(game.screen, (220, 196, 124), lamp, 3)


def draw_station(game, pos: Vector2, label: str, color: tuple[int, int, int], shake_offset: Vector2) -> None:
    screen_pos = game.world_to_screen(pos) + shake_offset
    rect = pygame.Rect(0, 0, 72, 40)
    rect.center = (screen_pos.x, screen_pos.y)
    pygame.draw.rect(game.screen, (18, 22, 21), rect.move(0, 10), border_radius=11)
    pygame.draw.rect(game.screen, color, rect, border_radius=12)
    pygame.draw.rect(game.screen, PALETTE["wood_dark"], rect, 2, border_radius=12)
    text = game.small_font.render(label, True, PALETTE["text"])
    game.screen.blit(text, text.get_rect(center=(screen_pos.x, screen_pos.y)))


def draw_stockpile(game, shake_offset: Vector2) -> None:
    pos = game.world_to_screen(game.stockpile_pos) + shake_offset
    shadow = pygame.Rect(0, 0, 104, 34)
    shadow.center = (int(pos.x), int(pos.y + 22))
    pygame.draw.ellipse(game.screen, (16, 18, 18), shadow)

    for index in range(min(3, game.logs // 8 + (1 if game.logs > 0 else 0))):
        log = pygame.Rect(0, 0, 26, 10)
        log.center = (int(pos.x - 26 + index * 16), int(pos.y + 8 - index * 3))
        pygame.draw.ellipse(game.screen, (120, 84, 48), log)
        pygame.draw.ellipse(game.screen, (72, 44, 28), log, 2)

    crate = pygame.Rect(0, 0, 32, 24)
    crate.center = (int(pos.x + 20), int(pos.y + 2))
    pygame.draw.rect(game.screen, (104, 84, 60), crate, border_radius=6)
    pygame.draw.rect(game.screen, PALETTE["wood_dark"], crate, 2, border_radius=6)
    pygame.draw.line(game.screen, (148, 126, 92), (crate.x + 6, crate.y + 8), (crate.right - 6, crate.y + 8), 2)
    pygame.draw.line(game.screen, (148, 126, 92), (crate.x + 6, crate.y + 16), (crate.right - 6, crate.y + 16), 2)

    herb_box = pygame.Rect(0, 0, 22, 16)
    herb_box.center = (int(pos.x + 46), int(pos.y - 6))
    pygame.draw.rect(game.screen, (82, 102, 72), herb_box, border_radius=4)
    pygame.draw.rect(game.screen, (56, 68, 50), herb_box, 1, border_radius=4)
    if game.herbs > 0:
        pygame.draw.line(game.screen, (108, 168, 92), herb_box.center, herb_box.center + Vector2(-4, -8), 2)
        pygame.draw.line(game.screen, (108, 168, 92), herb_box.center, herb_box.center + Vector2(4, -6), 2)


def draw_bonfire(game, shake_offset: Vector2) -> None:
    fire_pos = game.world_to_screen(game.bonfire_pos) + shake_offset
    heat_ratio = game.bonfire_heat / 100
    ember_ratio = game.bonfire_ember_bed / 100
    stage = game.bonfire_stage()
    night_glow = 0.18 + game.visual_darkness_factor() * 0.82
    pygame.draw.circle(game.screen, (34, 25, 19), fire_pos, 54)
    pygame.draw.circle(game.screen, (72, 56, 32), fire_pos, 38)
    for angle in (0.2, 1.8, 3.5):
        vec = angle_to_vector(angle) * 26
        pygame.draw.line(game.screen, PALETTE["wood_dark"], fire_pos - vec, fire_pos + vec, 7)

    ember_surface = pygame.Surface((140, 140), pygame.SRCALPHA)
    ember_alpha = int((34 + ember_ratio * 42) * night_glow)
    ember_radius = int(18 + ember_ratio * 8)
    pygame.draw.circle(ember_surface, (196, 94, 54, ember_alpha), (70, 82), ember_radius)
    pygame.draw.circle(
        ember_surface,
        (226, 128, 78, int((8 + ember_ratio * 12) * night_glow)),
        (70, 82),
        int(ember_radius * 0.44),
    )
    game.screen.blit(ember_surface, fire_pos - Vector2(70, 70))

    if stage != "brasas":
        flame_height = 14 + 28 * heat_ratio + math.sin(pygame.time.get_ticks() / 160) * (2 + heat_ratio * 2)
        flame_width = 10 + 12 * heat_ratio
        pygame.draw.polygon(
            game.screen,
            (210, 122, 72),
            [
                fire_pos + Vector2(0, -flame_height),
                fire_pos + Vector2(-flame_width - 4, 10),
                fire_pos + Vector2(0, 24),
                fire_pos + Vector2(flame_width + 4, 10),
            ],
        )
        pygame.draw.polygon(
            game.screen,
            (255, 164, 96),
            [
                fire_pos + Vector2(0, -flame_height * 0.72),
                fire_pos + Vector2(-flame_width * 0.58, 8),
                fire_pos + Vector2(0, 18),
                fire_pos + Vector2(flame_width * 0.58, 8),
            ],
        )

    if stage == "alta":
        lick = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(lick, (214, 110, 72, int(10 * night_glow)), (60, 48), 20)
        game.screen.blit(lick, fire_pos - Vector2(60, 60))

    if game.random.random() < (0.22 + heat_ratio * 0.34 + ember_ratio * 0.12):
        game.emit_embers(game.bonfire_pos + Vector2(game.random.uniform(-8, 8), -8), 1)








