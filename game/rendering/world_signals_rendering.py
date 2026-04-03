from __future__ import annotations

import math

import pygame
from pygame import Vector2

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH, clamp


def draw_interest_points(game, shake_offset: Vector2) -> None:
    time_value = pygame.time.get_ticks() / 260
    for interest_point in game.interest_points:
        pos = game.world_to_screen(interest_point.pos) + shake_offset
        if pos.x < -90 or pos.x > SCREEN_WIDTH + 90 or pos.y < -90 or pos.y > SCREEN_HEIGHT + 90:
            continue

        pulse = 0.5 + 0.5 * math.sin(time_value + interest_point.pulse)
        if interest_point.feature_kind == "grove":
            pygame.draw.ellipse(game.screen, (74, 60, 34), pygame.Rect(pos.x - 12, pos.y + 8, 24, 10))
            pygame.draw.line(game.screen, (88, 74, 42), pos + Vector2(-4, 8), pos + Vector2(2, -14), 3)
            pygame.draw.circle(game.screen, (114, 143, 82), pos + Vector2(0, -18), 9)
        elif interest_point.feature_kind == "meadow":
            pygame.draw.line(game.screen, (92, 111, 67), pos + Vector2(0, 12), pos + Vector2(0, -12), 3)
            pygame.draw.circle(game.screen, (223, 202, 123), pos + Vector2(-5, -14), 5)
            pygame.draw.circle(game.screen, (191, 116, 88), pos + Vector2(4, -12), 4)
        elif interest_point.feature_kind == "swamp":
            pygame.draw.rect(game.screen, (73, 76, 69), pygame.Rect(pos.x - 12, pos.y - 6, 24, 14), border_radius=4)
            pygame.draw.rect(game.screen, (117, 124, 114), pygame.Rect(pos.x - 8, pos.y - 3, 16, 8), border_radius=4)
        else:
            pygame.draw.rect(game.screen, (111, 108, 101), pygame.Rect(pos.x - 10, pos.y - 10, 20, 20), border_radius=4)
            pygame.draw.line(game.screen, (70, 66, 62), pos + Vector2(-6, 0), pos + Vector2(6, 0), 2)

        if not interest_point.resolved:
            ring_radius = int(18 + pulse * 4)
            pygame.draw.circle(game.screen, PALETTE["accent_soft"], pos, ring_radius, 2)
            if game.player.distance_to(interest_point.pos) < 150:
                label = game.small_font.render(interest_point.label, True, PALETTE["text"])
                box = pygame.Rect(0, 0, label.get_width() + 12, label.get_height() + 4)
                box.midbottom = (pos.x, pos.y - 18)
                pygame.draw.rect(game.screen, (18, 24, 26), box, border_radius=7)
                pygame.draw.rect(game.screen, PALETTE["ui_line"], box, 1, border_radius=7)
                game.screen.blit(label, label.get_rect(center=box.center))


def draw_dynamic_events(game, shake_offset: Vector2) -> None:
    time_value = pygame.time.get_ticks() / 220
    for event in game.active_dynamic_events:
        pos = game.world_to_screen(event.pos) + shake_offset
        if pos.x < -120 or pos.x > SCREEN_WIDTH + 120 or pos.y < -120 or pos.y > SCREEN_HEIGHT + 120:
            continue
        pulse = 0.5 + 0.5 * math.sin(time_value + event.uid)
        ring_color = PALETTE["danger_soft"] if event.urgency > 0.55 else PALETTE["morale"]
        if event.kind in {"abrigo", "faccao"}:
            draw_event_visitor(game, pos, event, pulse)
        pygame.draw.circle(game.screen, ring_color, pos, int(18 + pulse * 5), 3)
        pygame.draw.circle(game.screen, (18, 24, 26), pos, 9)
        inner = (
            (222, 148, 98)
            if event.kind == "incendio"
            else (
                (214, 184, 96)
                if event.kind == "alarme"
                else ((176, 210, 126) if event.kind == "abrigo" else ((124, 176, 220) if event.kind == "expedicao" else ring_color))
            )
        )
        pygame.draw.circle(game.screen, inner, pos, 5)
        if game.player.distance_to(event.pos) < 170:
            detail = game.fit_text_to_width(game.small_font, event.label, 294)
            if event.kind == "faccao":
                humane = dict(event.data.get("humane", {}))
                hardline = dict(event.data.get("hardline", {}))
                detail = game.fit_text_to_width(
                    game.small_font,
                    f"E {humane.get('title', 'ceder')}  |  Q {hardline.get('title', 'pressionar')}",
                    294,
                )
            label = game.small_font.render(detail, True, PALETTE["text"])
            box = pygame.Rect(0, 0, min(320, label.get_width() + 12), label.get_height() + 6)
            box.midbottom = (pos.x, pos.y - 18)
            pygame.draw.rect(game.screen, (18, 24, 26), box, border_radius=8)
            pygame.draw.rect(game.screen, PALETTE["ui_line"], box, 1, border_radius=8)
            game.screen.blit(label, label.get_rect(center=box.center))


def draw_event_visitor(game, pos: Vector2, event, pulse: float) -> None:
    visitor = dict(getattr(event, "data", {}).get("visitor", {}))
    body_color = tuple(visitor.get("body", (142, 152, 134)))
    accent_color = tuple(visitor.get("accent", (108, 118, 94)))
    prop = str(visitor.get("prop", "bag"))
    tick = pygame.time.get_ticks() / 1000.0
    hover = math.sin(tick * 2.1 + event.uid * 0.37) * 2.4
    sway = math.sin(tick * 1.4 + event.uid * 0.23) * 1.6
    body_pos = pos + Vector2(sway, hover)

    shadow = pygame.Rect(0, 0, 36, 12)
    shadow.inflate_ip(int(abs(sway) * 2), 0)
    shadow.center = (int(pos.x), int(pos.y + 16))
    pygame.draw.ellipse(game.screen, (12, 16, 16), shadow)

    pygame.draw.line(game.screen, (64, 54, 42), body_pos + Vector2(-4, 14), body_pos + Vector2(-2, 2), 3)
    pygame.draw.line(game.screen, (64, 54, 42), body_pos + Vector2(4, 14), body_pos + Vector2(2, 2), 3)
    pygame.draw.line(game.screen, (76, 64, 48), body_pos + Vector2(0, -2), body_pos + Vector2(0, 8), 4)
    arm_lift = math.sin(tick * 2.6 + event.uid * 0.41) * 1.5
    pygame.draw.line(game.screen, accent_color, body_pos + Vector2(-10, arm_lift), body_pos + Vector2(10, 2 - arm_lift), 3)
    torso = pygame.Rect(0, 0, 18, 20)
    torso.center = (int(body_pos.x), int(body_pos.y - 2))
    pygame.draw.ellipse(game.screen, body_color, torso)
    pygame.draw.ellipse(game.screen, tuple(max(0, c - 34) for c in body_color), torso, 1)
    head = pygame.Rect(0, 0, 14, 14)
    head.center = (int(body_pos.x), int(body_pos.y - 18))
    pygame.draw.ellipse(game.screen, (224, 214, 188), head)
    pygame.draw.circle(game.screen, (40, 34, 28), (int(body_pos.x - 3), int(body_pos.y - 20)), 1)
    pygame.draw.circle(game.screen, (40, 34, 28), (int(body_pos.x + 3), int(body_pos.y - 20)), 1)
    pygame.draw.arc(game.screen, (96, 72, 54), pygame.Rect(body_pos.x - 4, body_pos.y - 18, 8, 6), 0.2, 2.9, 1)

    if prop == "bag":
        pack = pygame.Rect(0, 0, 10, 12)
        pack.center = (int(body_pos.x + 11 + sway * 0.6), int(body_pos.y - 1))
        pygame.draw.rect(game.screen, (98, 84, 62), pack, border_radius=3)
        pygame.draw.rect(game.screen, (64, 52, 38), pack, 1, border_radius=3)
    elif prop == "crate":
        crate = pygame.Rect(0, 0, 14, 10)
        crate.center = (int(body_pos.x + 14 + sway * 0.3), int(body_pos.y + 8))
        pygame.draw.rect(game.screen, (118, 92, 62), crate, border_radius=2)
        pygame.draw.rect(game.screen, (72, 50, 32), crate, 1, border_radius=2)
    elif prop == "pole":
        pole_tip = body_pos + Vector2(12, -18)
        pole_base = body_pos + Vector2(12, 16)
        pygame.draw.line(game.screen, (132, 118, 96), pole_base, pole_tip, 2)
        cloth_sway = math.sin(tick * 2.2 + event.uid * 0.53) * 2.2
        cloth = [pole_tip + Vector2(0, 2), pole_tip + Vector2(10 + cloth_sway, 6), pole_tip + Vector2(0, 10)]
        pygame.draw.polygon(game.screen, accent_color, cloth)

    glow = pygame.Surface((54, 54), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*accent_color, int(18 + pulse * 10)), (27, 27), 14)
    game.screen.blit(glow, pos - Vector2(27, 27))
    if game.player.distance_to(event.pos) < 148:
        draw_event_visitor_bubble(game, body_pos, event, accent_color)


def event_visitor_bark(event) -> str:
    if event.kind == "abrigo":
        return "Preciso de abrigo por esta noite."
    if event.kind == "faccao":
        faction = str(getattr(event, "data", {}).get("faction", ""))
        if faction == "andarilhos":
            return "Temos criancas e pouca comida."
        if faction == "ferro-velho":
            return "Trouxemos troca limpa e rapida."
        if faction == "vigias_da_estrada":
            return "Queremos resposta agora, chefe."
        return "Viemos tratar com a clareira."
    return ""


def draw_event_visitor_bubble(game, pos: Vector2, event, color: tuple[int, int, int]) -> None:
    bark_text = event_visitor_bark(event)
    if not bark_text:
        return
    lines = game.wrap_text_lines(game.ui_small_font, bark_text, 180)
    text_surfaces = [game.ui_small_font.render(line, True, PALETTE["text"]) for line in lines]
    width = max(surface.get_width() for surface in text_surfaces) + 20
    height = len(text_surfaces) * game.ui_small_font.get_linesize() + max(0, len(text_surfaces) - 1) * 2 + 12
    bubble = pygame.Surface((width, height + 7), pygame.SRCALPHA)
    bubble_rect = pygame.Rect(0, 0, width, height)
    pygame.draw.rect(bubble, (14, 18, 20, 214), bubble_rect, border_radius=11)
    pygame.draw.rect(bubble, (*color, 124), bubble_rect, 1, border_radius=11)
    tail = [(width // 2 - 8, height - 2), (width // 2 + 8, height - 2), (width // 2, height + 7)]
    pygame.draw.polygon(bubble, (14, 18, 20, 214), tail)
    pygame.draw.polygon(bubble, (*color, 116), tail, 1)
    text_y = 6
    for surface in text_surfaces:
        bubble.blit(surface, surface.get_rect(center=(width // 2, text_y + surface.get_height() // 2)))
        text_y += game.ui_small_font.get_linesize() + 2
    bubble_pos = pos - Vector2(width / 2, 56 + height)
    game.screen.blit(bubble, bubble_pos)


def draw_interaction_prompt(game, shake_offset: Vector2) -> None:
    hovered_target = game.hovered_interaction_target()
    reachable = False
    label_text: str | None = None
    if hovered_target and not game.player_sleeping:
        world_pos = Vector2(hovered_target["pos"])
        label_text = game.prompt_for_interaction_target(hovered_target)
        reachable = game.player.distance_to(world_pos) <= float(hovered_target.get("reach", 112.0))
        if not label_text:
            hovered_target = None
    if not hovered_target:
        hint = game.nearest_interaction_hint()
        if not hint or game.player_sleeping:
            return
        world_pos, label_text = hint
        reachable = True
    else:
        world_pos = Vector2(hovered_target["pos"])
    if not label_text:
        return
    pos = game.world_to_screen(world_pos) + shake_offset
    if pos.x < -140 or pos.x > SCREEN_WIDTH + 140 or pos.y < -140 or pos.y > SCREEN_HEIGHT + 140:
        return
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 210)
    ring_radius = 18 + pulse * 4
    ring_color = PALETTE["accent_soft"] if reachable else PALETTE["muted"]
    pygame.draw.circle(game.screen, ring_color, pos, ring_radius, 2)
    if label_text.startswith("E "):
        label_text = label_text.replace("E ", "E / botao direito ", 1)
    if hovered_target and not reachable:
        label_text = game.fit_text_to_width(game.body_font, f"{label_text}  |  chegue mais perto", 440)
    label = game.body_font.render(label_text, True, PALETTE["text"])
    box = pygame.Rect(0, 0, min(360, label.get_width() + 18), label.get_height() + 10)
    box.midbottom = (pos.x, pos.y - 20)
    pygame.draw.rect(game.screen, (16, 22, 24), box, border_radius=10)
    pygame.draw.rect(game.screen, ring_color, box, 1, border_radius=10)
    game.screen.blit(label, label.get_rect(center=box.center))


def draw_particles(game, shake_offset: Vector2) -> None:
    for pulse in game.damage_pulses:
        pos = game.world_to_screen(pulse.pos) + shake_offset
        alpha = int(180 * pulse.life / 0.28)
        surface = pygame.Surface((160, 160), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*pulse.color, alpha), (80, 80), int(pulse.radius), 3)
        game.screen.blit(surface, pos - Vector2(80, 80))

    for ember in game.embers:
        pos = game.world_to_screen(ember.pos) + shake_offset
        if pos.x < -20 or pos.x > SCREEN_WIDTH + 20 or pos.y < -20 or pos.y > SCREEN_HEIGHT + 20:
            continue
        alpha = int(190 * clamp(ember.life, 0, 1))
        surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*ember.color, alpha), (12, 12), int(ember.radius))
        game.screen.blit(surface, pos - Vector2(12, 12))

    for floating in game.floating_texts:
        pos = game.world_to_screen(floating.pos) + shake_offset
        alpha = int(255 * clamp(floating.life / 1.2, 0, 1))
        text = game.small_font.render(floating.text, True, floating.color)
        text.set_alpha(alpha)
        game.screen.blit(text, text.get_rect(center=(pos.x, pos.y)))








