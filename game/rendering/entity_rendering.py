from __future__ import annotations

import math

import pygame
from pygame import Vector2

from ..entities import Survivor, Zombie
from ..core.config import PALETTE, clamp


def draw_entities(game, shake_offset: Vector2) -> None:
    all_entities = []
    all_entities.append(("player", game.player, game.player.pos.y))
    all_entities.extend(
        ("survivor", survivor, survivor.pos.y)
        for survivor in game.survivors
        if survivor.is_alive() and (not game.is_survivor_on_expedition(survivor) or survivor in game.expedition_visible_members())
    )
    all_entities.extend(("zombie", zombie, zombie.pos.y) for zombie in game.zombies if zombie.is_alive())

    for kind, entity, _ in sorted(all_entities, key=lambda item: item[2]):
        pos = game.world_to_screen(entity.pos) + shake_offset
        pygame.draw.ellipse(
            game.screen,
            (11, 15, 16),
            pygame.Rect(pos.x - entity.radius * 0.92, pos.y + entity.radius * 0.48, entity.radius * 1.84, entity.radius * 0.86),
        )
        if kind == "player":
            player_expression = "calmo"
            if game.player.attack_flash > 0:
                player_expression = "focado"
            elif game.player.health < game.player.max_health * 0.35:
                player_expression = "ferido"
            elif game.player.stamina < game.player.max_stamina * 0.28:
                player_expression = "cansado"
            draw_character(
                game,
                pos,
                (228, 208, 156),
                (44, 54, 63),
                entity.radius,
                "chefe",
                expression=player_expression,
            )
            if game.player.attack_flash > 0:
                swing = pygame.Surface((160, 160), pygame.SRCALPHA)
                center = Vector2(80, 80)
                start = center + game.player.facing.rotate(-56) * 52
                end = center + game.player.facing.rotate(56) * 76
                points = [center, start, end]
                alpha = int(140 * (game.player.attack_flash / 0.22))
                pygame.draw.polygon(swing, (255, 202, 134, alpha), points)
                game.screen.blit(swing, pos - center)
        elif kind == "survivor":
            survivor: Survivor = entity
            if getattr(survivor, "expedition_downed", False):
                body = pygame.Rect(0, 0, int(entity.radius * 2.2), int(entity.radius * 1.08))
                body.center = (int(pos.x), int(pos.y))
                pygame.draw.ellipse(game.screen, (18, 20, 20), body.inflate(8, 6))
                pygame.draw.ellipse(game.screen, survivor.color, body)
                pygame.draw.ellipse(game.screen, (52, 44, 36), body, 2)
                pygame.draw.circle(
                    game.screen,
                    (228, 208, 156),
                    (int(pos.x - entity.radius * 0.28), int(pos.y - entity.radius * 0.24)),
                    int(entity.radius * 0.34),
                )
            else:
                survivor_expression = survivor_expression_for(survivor)
                draw_character(
                    game,
                    pos,
                    survivor.color,
                    (52, 44, 36),
                    entity.radius,
                    survivor.name,
                    role=survivor.role,
                    expression=survivor_expression,
                )
            draw_status_orb(game, pos, survivor)
            draw_survivor_bark(game, pos, survivor)
        else:
            zombie: Zombie = entity
            if getattr(zombie, "is_boss", False):
                aura = pygame.Surface((220, 220), pygame.SRCALPHA)
                center = Vector2(aura.get_width() / 2, aura.get_height() / 2)
                glow_radius = int(entity.radius * (2.8 + getattr(zombie, "enrage_level", 0) * 0.35))
                aura_center = (int(center.x), int(center.y))
                outer_alpha = 34 + getattr(zombie, "enrage_level", 0) * 16
                ring_alpha = 76 + getattr(zombie, "enrage_level", 0) * 22
                pygame.draw.circle(aura, (*zombie.boss_accent, outer_alpha), aura_center, glow_radius)
                pygame.draw.circle(aura, (*zombie.boss_body, ring_alpha), aura_center, int(entity.radius * 1.9), 3)
                if getattr(zombie, "visual_state", "") == "enraged":
                    pygame.draw.circle(aura, (*PALETTE["danger_soft"], 92), aura_center, int(entity.radius * 2.4), 2)
                game.screen.blit(aura, pos - center)
                draw_character(
                    game,
                    pos,
                    zombie.boss_body,
                    zombie.boss_accent,
                    entity.radius,
                    zombie.boss_name,
                    zombie=True,
                    expression="agressivo",
                )
                ratio = zombie.health / max(1.0, zombie.max_health)
                bar_rect = pygame.Rect(0, 0, 88, 8)
                bar_rect.midbottom = (pos.x, pos.y - entity.radius * 2.0)
                pygame.draw.rect(game.screen, (18, 24, 26), bar_rect, border_radius=5)
                pygame.draw.rect(
                    game.screen,
                    PALETTE["danger_soft"],
                    (bar_rect.x + 1, bar_rect.y + 1, int((bar_rect.width - 2) * clamp(ratio, 0, 1)), bar_rect.height - 2),
                    border_radius=5,
                )
                pygame.draw.rect(game.screen, PALETTE["ui_line"], bar_rect, 1, border_radius=5)
            else:
                body = (88, 124, 82) if zombie.health > 45 else (126, 96, 76)
                accent = (41, 58, 39)
                if getattr(zombie, "variant", "walker") == "runner":
                    body = (92, 138, 88)
                    accent = (34, 60, 34)
                elif getattr(zombie, "variant", "walker") == "brute":
                    body = (128, 104, 82)
                    accent = (62, 46, 36)
                elif getattr(zombie, "variant", "walker") == "howler":
                    body = (104, 132, 110)
                    accent = (48, 66, 58)
                elif getattr(zombie, "variant", "walker") == "raider":
                    body = (118, 120, 88)
                    accent = (72, 58, 40)
                visual_state = getattr(zombie, "visual_state", "")
                if visual_state == "charging":
                    streak = pygame.Surface((120, 120), pygame.SRCALPHA)
                    streak_center = Vector2(60, 60)
                    facing = getattr(zombie, "facing", Vector2(1, 0))
                    for spread in (-16, 0, 16):
                        start = streak_center - facing * 8 + facing.rotate(spread) * 12
                        end = streak_center - facing * 34 + facing.rotate(spread) * 22
                        pygame.draw.line(streak, (*PALETTE["danger_soft"], 110), start, end, 3)
                    game.screen.blit(streak, pos - streak_center)
                elif visual_state == "howling":
                    howl = pygame.Surface((140, 140), pygame.SRCALPHA)
                    pygame.draw.circle(howl, (*PALETTE["danger_soft"], 80), (70, 70), int(entity.radius * 2.1), 2)
                    pygame.draw.circle(howl, (*accent, 64), (70, 70), int(entity.radius * 2.8), 2)
                    game.screen.blit(howl, pos - Vector2(70, 70))
                elif visual_state == "slamming":
                    slam = pygame.Surface((160, 160), pygame.SRCALPHA)
                    pygame.draw.circle(slam, (*PALETTE["danger"], 84), (80, 80), int(entity.radius * 2.4), 3)
                    game.screen.blit(slam, pos - Vector2(80, 80))
                zombie_expression = "agressivo" if getattr(zombie, "variant", "walker") in {"runner", "raider", "howler"} else "vazio"
                draw_character(game, pos, body, accent, entity.radius, None, zombie=True, expression=zombie_expression)
                if getattr(zombie, "weapon_name", ""):
                    draw_zombie_weapon(game, pos, zombie)
                ratio = zombie.health / max(1.0, zombie.max_health)
                bar_rect = pygame.Rect(0, 0, 42, 5)
                bar_rect.midbottom = (pos.x, pos.y - entity.radius * 1.72)
                pygame.draw.rect(game.screen, (18, 24, 26), bar_rect, border_radius=4)
                pygame.draw.rect(
                    game.screen,
                    PALETTE["danger_soft"],
                    (bar_rect.x + 1, bar_rect.y + 1, int((bar_rect.width - 2) * clamp(ratio, 0, 1)), bar_rect.height - 2),
                    border_radius=4,
                )
                pygame.draw.rect(game.screen, PALETTE["ui_line"], bar_rect, 1, border_radius=4)


def draw_character(
    game,
    pos: Vector2,
    clothing: tuple[int, int, int],
    accent: tuple[int, int, int],
    radius: float,
    label: str | None,
    *,
    zombie: bool = False,
    role: str | None = None,
    expression: str = "calmo",
) -> None:
    scale = max(0.85, radius / 11.0)
    head_color = (224, 214, 188) if not zombie else (148, 165, 119)
    outline = tuple(max(0, channel - 34) for channel in clothing)
    tick = pygame.time.get_ticks() / 1000.0
    phase = tick * (1.55 if zombie else 1.9) + (sum(clothing) * 0.0031) + (sum(accent) * 0.0017)
    bob = math.sin(phase) * (1.2 * scale)
    sway = math.sin(phase * 0.7) * (0.8 * scale)
    arm_swing = math.sin(phase * 1.7) * (2.6 * scale)
    arm_lift = math.cos(phase * 1.5) * (1.4 * scale)
    animated_pos = pos + Vector2(sway, bob)

    shadow = pygame.Rect(0, 0, int(28 * scale), int(10 * scale))
    shadow.center = (int(pos.x), int(pos.y + 14 * scale))
    pygame.draw.ellipse(game.screen, (12, 16, 16), shadow)

    pygame.draw.line(
        game.screen,
        (64, 54, 42),
        animated_pos + Vector2(-4 * scale, 13 * scale),
        animated_pos + Vector2(-2 * scale - arm_swing * 0.12, 2 * scale),
        max(2, int(3 * scale)),
    )
    pygame.draw.line(
        game.screen,
        (64, 54, 42),
        animated_pos + Vector2(4 * scale, 13 * scale),
        animated_pos + Vector2(2 * scale + arm_swing * 0.12, 2 * scale),
        max(2, int(3 * scale)),
    )
    pygame.draw.line(
        game.screen,
        (76, 64, 48),
        animated_pos + Vector2(0, -2 * scale),
        animated_pos + Vector2(0, 8 * scale),
        max(2, int(4 * scale)),
    )
    left_shoulder = animated_pos + Vector2(-5 * scale, -7 * scale)
    right_shoulder = animated_pos + Vector2(5 * scale, -7 * scale)
    left_hand = animated_pos + Vector2(-10 * scale - arm_swing, -2 * scale + arm_lift)
    right_hand = animated_pos + Vector2(10 * scale + arm_swing, -1 * scale - arm_lift)
    pygame.draw.line(game.screen, accent, left_shoulder, left_hand, max(2, int(3 * scale)))
    pygame.draw.line(game.screen, accent, right_shoulder, right_hand, max(2, int(3 * scale)))
    pygame.draw.circle(game.screen, head_color, (int(left_hand.x), int(left_hand.y)), max(1, int(1.25 * scale)))
    pygame.draw.circle(game.screen, head_color, (int(right_hand.x), int(right_hand.y)), max(1, int(1.25 * scale)))
    if role and not zombie:
        draw_role_tool(game, right_hand, role, scale, accent)

    torso = pygame.Rect(0, 0, int(18 * scale), int(20 * scale))
    torso.center = (int(animated_pos.x), int(animated_pos.y - 2 * scale))
    pygame.draw.ellipse(game.screen, clothing, torso)
    pygame.draw.ellipse(game.screen, outline, torso, 1)

    head = pygame.Rect(0, 0, int(14 * scale), int(14 * scale))
    head.center = (int(animated_pos.x), int(animated_pos.y - 18 * scale - arm_lift * 0.15))
    pygame.draw.ellipse(game.screen, head_color, head)
    face_center = Vector2(animated_pos.x, animated_pos.y - 18 * scale - arm_lift * 0.15)
    draw_face(game, face_center, scale, expression, zombie=zombie)
    if label:
        text = game.small_font.render(label, True, PALETTE["text"])
        box = pygame.Rect(0, 0, text.get_width() + 10, text.get_height() + 4)
        box.midbottom = (animated_pos.x, animated_pos.y - radius * 2.18)
        pygame.draw.rect(game.screen, (18, 24, 26), box, border_radius=8)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], box, 1, border_radius=8)
        game.screen.blit(text, text.get_rect(center=box.center))


def draw_role_tool(game, hand_pos: Vector2, role: str, scale: float, accent: tuple[int, int, int]) -> None:
    if role == "lenhador":
        pygame.draw.line(game.screen, (106, 82, 58), hand_pos + Vector2(-1 * scale, -6 * scale), hand_pos + Vector2(6 * scale, 5 * scale), max(2, int(2 * scale)))
        head = [hand_pos + Vector2(2 * scale, -7 * scale), hand_pos + Vector2(8 * scale, -4 * scale), hand_pos + Vector2(4 * scale, 0)]
        pygame.draw.polygon(game.screen, (136, 142, 148), head)
    elif role == "vigia":
        pygame.draw.line(game.screen, (118, 108, 88), hand_pos + Vector2(0, -8 * scale), hand_pos + Vector2(0, 6 * scale), max(2, int(2 * scale)))
        tip = [hand_pos + Vector2(0, -11 * scale), hand_pos + Vector2(-3 * scale, -5 * scale), hand_pos + Vector2(3 * scale, -5 * scale)]
        pygame.draw.polygon(game.screen, (162, 176, 184), tip)
    elif role == "batedora":
        lens_left = hand_pos + Vector2(-3 * scale, -2 * scale)
        lens_right = hand_pos + Vector2(3 * scale, -2 * scale)
        pygame.draw.circle(game.screen, (86, 96, 108), (int(lens_left.x), int(lens_left.y)), max(2, int(2 * scale)))
        pygame.draw.circle(game.screen, (86, 96, 108), (int(lens_right.x), int(lens_right.y)), max(2, int(2 * scale)))
        pygame.draw.line(game.screen, (66, 74, 84), lens_left + Vector2(2 * scale, 0), lens_right - Vector2(2 * scale, 0), 1)
    elif role == "artesa":
        pygame.draw.line(game.screen, (122, 92, 64), hand_pos + Vector2(-1 * scale, -5 * scale), hand_pos + Vector2(5 * scale, 4 * scale), max(2, int(2 * scale)))
        pygame.draw.rect(
            game.screen,
            (128, 132, 138),
            pygame.Rect(int(hand_pos.x + 2 * scale), int(hand_pos.y - 8 * scale), max(4, int(5 * scale)), max(3, int(4 * scale))),
            border_radius=2,
        )
    elif role == "cozinheiro":
        pygame.draw.line(game.screen, (132, 116, 92), hand_pos + Vector2(-1 * scale, -6 * scale), hand_pos + Vector2(5 * scale, 5 * scale), max(2, int(2 * scale)))
        pygame.draw.circle(game.screen, (92, 104, 114), (int(hand_pos.x + 6 * scale), int(hand_pos.y - 5 * scale)), max(2, int(2 * scale)))
    elif role == "mensageiro":
        bag = pygame.Rect(0, 0, max(5, int(7 * scale)), max(6, int(8 * scale)))
        bag.center = (int(hand_pos.x + 4 * scale), int(hand_pos.y - 1 * scale))
        pygame.draw.rect(game.screen, (96, 78, 116), bag, border_radius=2)
        pygame.draw.rect(game.screen, tuple(max(0, c - 28) for c in accent), bag, 1, border_radius=2)


def draw_face(game, center: Vector2, scale: float, expression: str, *, zombie: bool = False) -> None:
    eye_color = (30, 26, 22) if not zombie else (40, 54, 34)
    mouth_color = (96, 72, 54) if not zombie else (62, 84, 58)
    brow_color = (72, 54, 38) if not zombie else (56, 78, 52)
    eye_y = center.y - 2 * scale
    left_eye = Vector2(center.x - 3 * scale, eye_y)
    right_eye = Vector2(center.x + 3 * scale, eye_y)
    eye_radius = max(1, int(1.15 * scale))

    pygame.draw.circle(game.screen, eye_color, (int(left_eye.x), int(left_eye.y)), eye_radius)
    pygame.draw.circle(game.screen, eye_color, (int(right_eye.x), int(right_eye.y)), eye_radius)

    if expression in {"focado", "agressivo", "irritado"}:
        pygame.draw.line(game.screen, brow_color, left_eye + Vector2(-2 * scale, -2 * scale), left_eye + Vector2(2 * scale, -1 * scale), 1)
        pygame.draw.line(game.screen, brow_color, right_eye + Vector2(-2 * scale, -1 * scale), right_eye + Vector2(2 * scale, -2 * scale), 1)
        pygame.draw.line(game.screen, mouth_color, center + Vector2(-2.2 * scale, 4 * scale), center + Vector2(2.2 * scale, 4 * scale), 1)
    elif expression in {"triste", "ferido"}:
        pygame.draw.line(game.screen, brow_color, left_eye + Vector2(-2 * scale, -1 * scale), left_eye + Vector2(2 * scale, -2 * scale), 1)
        pygame.draw.line(game.screen, brow_color, right_eye + Vector2(-2 * scale, -2 * scale), right_eye + Vector2(2 * scale, -1 * scale), 1)
        pygame.draw.arc(
            game.screen,
            mouth_color,
            pygame.Rect(center.x - 4 * scale, center.y + 2.8 * scale, 8 * scale, 5 * scale),
            3.35,
            6.05,
            1,
        )
    elif expression == "cansado":
        pygame.draw.line(game.screen, brow_color, left_eye + Vector2(-2 * scale, -1 * scale), left_eye + Vector2(2 * scale, -1 * scale), 1)
        pygame.draw.line(game.screen, brow_color, right_eye + Vector2(-2 * scale, -1 * scale), right_eye + Vector2(2 * scale, -1 * scale), 1)
        pygame.draw.line(game.screen, mouth_color, center + Vector2(-2.4 * scale, 4.2 * scale), center + Vector2(2.4 * scale, 4.2 * scale), 1)
    elif expression == "assustado":
        pygame.draw.circle(game.screen, eye_color, (int(left_eye.x), int(left_eye.y)), max(1, int(1.5 * scale)))
        pygame.draw.circle(game.screen, eye_color, (int(right_eye.x), int(right_eye.y)), max(1, int(1.5 * scale)))
        pygame.draw.circle(game.screen, mouth_color, (int(center.x), int(center.y + 4 * scale)), max(1, int(1.2 * scale)), 1)
    elif expression == "sorrindo":
        pygame.draw.arc(
            game.screen,
            mouth_color,
            pygame.Rect(center.x - 4 * scale, center.y + 1.4 * scale, 8 * scale, 6 * scale),
            0.15,
            2.95,
            1,
        )
    else:
        pygame.draw.arc(
            game.screen,
            mouth_color,
            pygame.Rect(center.x - 4 * scale, center.y + 2.1 * scale, 8 * scale, 5 * scale),
            0.2,
            2.9,
            1,
        )


def survivor_expression_for(survivor: Survivor) -> str:
    if not survivor.is_alive():
        return "ferido"
    if getattr(survivor, "insanity", 0.0) > 78:
        return "assustado"
    if survivor.conflict_cooldown > 0:
        return "irritado"
    if survivor.health < survivor.max_health * 0.38:
        return "ferido"
    if survivor.exhaustion > 76 or survivor.energy < 24:
        return "cansado"
    if survivor.morale < 34:
        return "triste"
    if survivor.morale > 72 and survivor.trust_leader > 56:
        return "sorrindo"
    return "calmo"


def draw_survivor_bark(game, pos: Vector2, survivor: Survivor) -> None:
    bark_text = str(getattr(survivor, "bark_text", "")).strip()
    bark_timer = float(getattr(survivor, "bark_timer", 0.0))
    if not bark_text or bark_timer <= 0:
        return
    color = tuple(getattr(survivor, "bark_color", PALETTE["text"]))
    alpha_ratio = clamp(bark_timer / 2.6, 0, 1)
    lines = game.wrap_text_lines(game.ui_small_font, bark_text, 140)
    text_surfaces = [game.ui_small_font.render(line, True, color) for line in lines]
    width = max(surface.get_width() for surface in text_surfaces) + 18
    height = len(text_surfaces) * game.ui_small_font.get_linesize() + max(0, len(text_surfaces) - 1) * 2 + 12
    bubble = pygame.Surface((width, height + 7), pygame.SRCALPHA)
    bubble_rect = pygame.Rect(0, 0, width, height)
    pygame.draw.rect(bubble, (14, 18, 20, int(210 * alpha_ratio)), bubble_rect, border_radius=11)
    pygame.draw.rect(bubble, (*color, int(136 * alpha_ratio)), bubble_rect, 1, border_radius=11)
    tail = [(width // 2 - 8, height - 2), (width // 2 + 8, height - 2), (width // 2, height + 7)]
    pygame.draw.polygon(bubble, (14, 18, 20, int(210 * alpha_ratio)), tail)
    pygame.draw.polygon(bubble, (*color, int(120 * alpha_ratio)), tail, 1)
    text_y = 6
    for surface in text_surfaces:
        bubble.blit(surface, surface.get_rect(center=(width // 2, text_y + surface.get_height() // 2)))
        text_y += game.ui_small_font.get_linesize() + 2
    bubble_pos = pos - Vector2(width / 2, 58 + height)
    game.screen.blit(bubble, bubble_pos)


def draw_status_orb(game, pos: Vector2, survivor: Survivor) -> None:
    color = PALETTE["heal"]
    if survivor.conflict_cooldown > 0 or survivor.morale < 45:
        color = PALETTE["danger_soft"]
    elif survivor.exhaustion > 68 or survivor.energy < 35:
        color = PALETTE["energy"]
    elif getattr(survivor, "insanity", 0.0) > 68:
        color = PALETTE["morale"]
    elif survivor.trust_leader < 34:
        color = PALETTE["muted"]
    orb_pos = pos + Vector2(20, -26)
    pygame.draw.circle(game.screen, (18, 24, 24), orb_pos, 8)
    pygame.draw.circle(game.screen, color, orb_pos, 5)


def draw_zombie_weapon(game, pos: Vector2, zombie: Zombie) -> None:
    if zombie.weapon_name == "cano":
        pygame.draw.line(game.screen, (112, 118, 126), pos + Vector2(2, -8), pos + Vector2(18, 8), 4)
    elif zombie.weapon_name == "machado":
        pygame.draw.line(game.screen, (108, 84, 56), pos + Vector2(0, -6), pos + Vector2(14, 10), 3)
        pygame.draw.polygon(
            game.screen,
            (164, 168, 172),
            [pos + Vector2(12, 6), pos + Vector2(22, 2), pos + Vector2(18, 12)],
        )
    elif zombie.weapon_name == "barra":
        pygame.draw.line(game.screen, (134, 114, 90), pos + Vector2(-2, -8), pos + Vector2(14, 12), 3)








