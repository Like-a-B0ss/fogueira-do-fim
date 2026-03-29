from __future__ import annotations

import math

import pygame
from pygame import Vector2

from . import hud_rendering_helpers
from .actors import Survivor, Zombie
from .config import (
    CAMP_CENTER,
    CAMP_RADIUS,
    CHUNK_SIZE,
    FOCUS_LABELS,
    PALETTE,
    ROLE_COLORS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    angle_to_vector,
    clamp,
    format_clock,
    lerp,
)


class RenderMixin:
    def wrap_text_lines(self, font: pygame.font.Font, text: str, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def fit_text_to_width(self, font: pygame.font.Font, text: str, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        ellipsis = "..."
        clipped = text
        while clipped and font.size(clipped + ellipsis)[0] > max_width:
            clipped = clipped[:-1]
        return (clipped + ellipsis) if clipped else ellipsis

    def draw_wrapped_text(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
        *,
        line_gap: int = 6,
    ) -> int:
        lines = self.wrap_text_lines(font, text, max_width)
        line_height = font.get_linesize()
        for index, line in enumerate(lines):
            rendered = font.render(line, True, color)
            self.screen.blit(rendered, (x, y + index * (line_height + line_gap)))
        return y + len(lines) * line_height + max(0, len(lines) - 1) * line_gap

    def draw(self) -> None:
        shake_strength = self.screen_shake * float(self.runtime_settings.get("screen_shake_scale", 1.0))
        shake_offset = (
            Vector2(
                self.random.uniform(-shake_strength, shake_strength),
                self.random.uniform(-shake_strength, shake_strength),
            )
            if shake_strength > 0
            else Vector2()
        )

        self.screen.fill(PALETTE["bg"])
        self.draw_procedural_ground(shake_offset)
        terrain_offset = (
            int(round(-self.camera.x + shake_offset.x)),
            int(round(-self.camera.y + shake_offset.y)),
        )
        self.screen.blit(self.terrain_surface, terrain_offset)

        self.draw_world_features(shake_offset)
        self.draw_camp(shake_offset)
        self.draw_buildings(shake_offset)
        self.draw_resource_nodes(shake_offset)
        self.draw_barricades(shake_offset)
        self.draw_interest_points(shake_offset)
        self.draw_dynamic_events(shake_offset)
        self.draw_entities(shake_offset)
        self.draw_weather_overlay(shake_offset)
        self.draw_interaction_prompt(shake_offset)
        self.draw_particles(shake_offset)
        self.draw_fog(shake_offset)
        self.draw_lighting()
        self.draw_map_fog(shake_offset)
        if self.scenes.is_gameplay():
            self.draw_hud()
        if self.build_menu_open and self.scenes.is_gameplay():
            self.draw_build_preview(shake_offset)
            self.draw_build_menu()
        if self.exit_prompt_open and self.scenes.is_gameplay():
            self.draw_exit_prompt()

        if self.scenes.is_title():
            self.draw_title_screen()
        elif self.scenes.is_tips():
            self.draw_tips_screen()
        elif self.scenes.is_game_over():
            self.draw_game_over()

        pygame.display.flip()

    def draw_world_features(self, shake_offset: Vector2) -> None:
        for feature in [*self.world_features, *self.endless_features]:
            pos = self.world_to_screen(feature.pos) + shake_offset
            if pos.x < -240 or pos.x > SCREEN_WIDTH + 240 or pos.y < -240 or pos.y > SCREEN_HEIGHT + 240:
                continue

            accent_angle = feature.accent * math.tau
            if feature.kind == "meadow":
                for index in range(12):
                    angle = accent_angle + index * 0.51
                    distance = feature.radius * (0.14 + (index % 4) * 0.11)
                    flower = pos + angle_to_vector(angle) * distance
                    pygame.draw.circle(self.screen, (228, 207, 118), flower, 2)
                    pygame.draw.circle(self.screen, (189, 111, 84), flower + Vector2(2, 1), 2)
            elif feature.kind == "swamp":
                for index in range(8):
                    angle = accent_angle + index * 0.72
                    root = pos + angle_to_vector(angle) * feature.radius * 0.34
                    pygame.draw.line(
                        self.screen,
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
                    pygame.draw.rect(self.screen, (111, 108, 101), rubble, border_radius=4)
                    pygame.draw.rect(self.screen, (72, 69, 63), rubble, 1, border_radius=4)
            elif feature.kind == "grove":
                for index in range(5):
                    angle = accent_angle + index * 1.08
                    offset = angle_to_vector(angle) * feature.radius * 0.28
                    stump = pygame.Rect(0, 0, 16, 10)
                    stump.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                    pygame.draw.ellipse(self.screen, (86, 66, 42), stump)
                    pygame.draw.ellipse(self.screen, (127, 97, 58), stump.inflate(-4, -3))
            elif feature.kind == "ashland":
                for index in range(7):
                    angle = accent_angle + index * 0.88
                    offset = angle_to_vector(angle) * feature.radius * 0.34
                    ember = pygame.Rect(0, 0, 14, 8)
                    ember.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                    pygame.draw.ellipse(self.screen, (118, 86, 68), ember)
            elif feature.kind == "redwood":
                for index in range(6):
                    angle = accent_angle + index * 0.96
                    offset = angle_to_vector(angle) * feature.radius * 0.4
                    trunk = pygame.Rect(0, 0, 12, 28)
                    trunk.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                    pygame.draw.rect(self.screen, (90, 58, 39), trunk, border_radius=5)
            elif feature.kind == "quarry":
                for index in range(8):
                    angle = accent_angle + index * 0.7
                    offset = angle_to_vector(angle) * feature.radius * 0.38
                    rock = pygame.Rect(0, 0, 16 + index % 3 * 3, 10 + index % 2 * 4)
                    rock.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                    pygame.draw.rect(self.screen, (136, 142, 148), rock, border_radius=4)
                    pygame.draw.rect(self.screen, (82, 89, 94), rock, 1, border_radius=4)

    def draw_procedural_ground(self, shake_offset: Vector2) -> None:
        left = math.floor((self.camera.x - CHUNK_SIZE) / CHUNK_SIZE)
        top = math.floor((self.camera.y - CHUNK_SIZE) / CHUNK_SIZE)
        right = math.ceil((self.camera.x + SCREEN_WIDTH + CHUNK_SIZE) / CHUNK_SIZE)
        bottom = math.ceil((self.camera.y + SCREEN_HEIGHT + CHUNK_SIZE) / CHUNK_SIZE)
        daylight = self.daylight_factor()
        cloud_cover = self.weather_cloud_cover()
        precipitation = self.weather_precipitation_factor()
        mist = self.weather_mist_factor()
        storm = self.weather_storm_factor()
        global_darkness = self.visual_darkness_factor()
        weather_cool = clamp(cloud_cover * 0.58 + precipitation * 0.18 + mist * 0.08 + storm * 0.12, 0.0, 0.88)
        for chunk_x in range(left, right + 1):
            for chunk_y in range(top, bottom + 1):
                biome = self.chunk_biome_kind(chunk_x, chunk_y)
                origin = self.chunk_origin(chunk_x, chunk_y)
                rect = pygame.Rect(
                    int(origin.x - self.camera.x + shake_offset.x),
                    int(origin.y - self.camera.y + shake_offset.y),
                    CHUNK_SIZE + 1,
                    CHUNK_SIZE + 1,
                )
                dark, light = self.biome_palette(biome)
                center = origin + Vector2(CHUNK_SIZE * 0.5, CHUNK_SIZE * 0.5)
                distance_to_camp = center.distance_to(CAMP_CENTER)
                depth = clamp(
                    (distance_to_camp - (self.camp_clearance_radius() + 260)) / 2600,
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
                pygame.draw.rect(self.screen, dark, rect)
                accent_seed = self.hash_noise(chunk_x, chunk_y, 83)
                for index in range(4):
                    circle_pos = Vector2(
                        rect.x + 40 + (index * 67 + accent_seed * 90) % max(80, CHUNK_SIZE - 80),
                        rect.y + 48 + (index * 53 + accent_seed * 70) % max(90, CHUNK_SIZE - 90),
                    )
                    pygame.draw.circle(self.screen, light, circle_pos, 42 + (index % 3) * 10)
                if depth > 0.04:
                    veil = pygame.Surface(rect.size, pygame.SRCALPHA)
                    veil.fill((10, 14, 16, int(22 + depth * 72)))
                    self.screen.blit(veil, rect.topleft)

    def draw_weather_overlay(self, shake_offset: Vector2) -> None:
        precipitation = self.weather_precipitation_factor()
        wind = self.weather_wind_factor()
        storm = self.weather_storm_factor()
        if precipitation <= 0.12:
            return

        tick = pygame.time.get_ticks() / 1000.0
        rain_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        streaks = int(18 + precipitation * 34 + storm * 18)
        fall = 18 + precipitation * 20 + storm * 8
        drift = 4 + wind * 7 + storm * 4
        rain_vector = Vector2(drift, fall)
        for index in range(streaks):
            phase = tick * (140 + precipitation * 70 + storm * 35) + index * 43
            x = (phase * 1.11 + index * 53 - self.camera.x * 0.92) % (SCREEN_WIDTH + 160) - 80
            y = (phase * 1.83 + index * 79 - self.camera.y * 1.04) % (SCREEN_HEIGHT + 220) - 110
            start = Vector2(x + shake_offset.x * 0.2, y + shake_offset.y * 0.2)
            end = start + rain_vector
            pygame.draw.line(rain_surface, (154, 176, 188, int(18 + precipitation * 16 + storm * 8)), start, end, 1)
        self.screen.blit(rain_surface, (0, 0))

    def draw_interest_points(self, shake_offset: Vector2) -> None:
        time_value = pygame.time.get_ticks() / 260
        for interest_point in self.interest_points:
            pos = self.world_to_screen(interest_point.pos) + shake_offset
            if pos.x < -90 or pos.x > SCREEN_WIDTH + 90 or pos.y < -90 or pos.y > SCREEN_HEIGHT + 90:
                continue

            pulse = 0.5 + 0.5 * math.sin(time_value + interest_point.pulse)
            if interest_point.feature_kind == "grove":
                pygame.draw.ellipse(self.screen, (74, 60, 34), pygame.Rect(pos.x - 12, pos.y + 8, 24, 10))
                pygame.draw.line(self.screen, (88, 74, 42), pos + Vector2(-4, 8), pos + Vector2(2, -14), 3)
                pygame.draw.circle(self.screen, (114, 143, 82), pos + Vector2(0, -18), 9)
            elif interest_point.feature_kind == "meadow":
                pygame.draw.line(self.screen, (92, 111, 67), pos + Vector2(0, 12), pos + Vector2(0, -12), 3)
                pygame.draw.circle(self.screen, (223, 202, 123), pos + Vector2(-5, -14), 5)
                pygame.draw.circle(self.screen, (191, 116, 88), pos + Vector2(4, -12), 4)
            elif interest_point.feature_kind == "swamp":
                pygame.draw.rect(self.screen, (73, 76, 69), pygame.Rect(pos.x - 12, pos.y - 6, 24, 14), border_radius=4)
                pygame.draw.rect(self.screen, (117, 124, 114), pygame.Rect(pos.x - 8, pos.y - 3, 16, 8), border_radius=4)
            else:
                pygame.draw.rect(self.screen, (111, 108, 101), pygame.Rect(pos.x - 10, pos.y - 10, 20, 20), border_radius=4)
                pygame.draw.line(self.screen, (70, 66, 62), pos + Vector2(-6, 0), pos + Vector2(6, 0), 2)

            if not interest_point.resolved:
                ring_radius = int(18 + pulse * 4)
                pygame.draw.circle(self.screen, PALETTE["accent_soft"], pos, ring_radius, 2)
                if self.player.distance_to(interest_point.pos) < 150:
                    label = self.small_font.render(interest_point.label, True, PALETTE["text"])
                    box = pygame.Rect(0, 0, label.get_width() + 12, label.get_height() + 4)
                    box.midbottom = (pos.x, pos.y - 18)
                    pygame.draw.rect(self.screen, (18, 24, 26), box, border_radius=7)
                    pygame.draw.rect(self.screen, PALETTE["ui_line"], box, 1, border_radius=7)
                    self.screen.blit(label, label.get_rect(center=box.center))

    def draw_dynamic_events(self, shake_offset: Vector2) -> None:
        time_value = pygame.time.get_ticks() / 220
        for event in self.active_dynamic_events:
            pos = self.world_to_screen(event.pos) + shake_offset
            if pos.x < -120 or pos.x > SCREEN_WIDTH + 120 or pos.y < -120 or pos.y > SCREEN_HEIGHT + 120:
                continue
            pulse = 0.5 + 0.5 * math.sin(time_value + event.uid)
            ring_color = PALETTE["danger_soft"] if event.urgency > 0.55 else PALETTE["morale"]
            if event.kind in {"abrigo", "faccao"}:
                self.draw_event_visitor(pos, event, pulse)
            pygame.draw.circle(self.screen, ring_color, pos, int(18 + pulse * 5), 3)
            pygame.draw.circle(self.screen, (18, 24, 26), pos, 9)
            inner = (
                (222, 148, 98)
                if event.kind == "incendio"
                else (
                    (214, 184, 96)
                    if event.kind == "alarme"
                    else ((176, 210, 126) if event.kind == "abrigo" else ((124, 176, 220) if event.kind == "expedicao" else ring_color))
                )
            )
            pygame.draw.circle(self.screen, inner, pos, 5)
            if self.player.distance_to(event.pos) < 170:
                detail = self.fit_text_to_width(self.small_font, event.label, 294)
                if event.kind == "faccao":
                    humane = dict(event.data.get("humane", {}))
                    hardline = dict(event.data.get("hardline", {}))
                    detail = self.fit_text_to_width(
                        self.small_font,
                        f"E {humane.get('title', 'ceder')}  |  Q {hardline.get('title', 'pressionar')}",
                        294,
                    )
                label = self.small_font.render(detail, True, PALETTE["text"])
                box = pygame.Rect(0, 0, min(320, label.get_width() + 12), label.get_height() + 6)
                box.midbottom = (pos.x, pos.y - 18)
                pygame.draw.rect(self.screen, (18, 24, 26), box, border_radius=8)
                pygame.draw.rect(self.screen, PALETTE["ui_line"], box, 1, border_radius=8)
                self.screen.blit(label, label.get_rect(center=box.center))

    def draw_event_visitor(self, pos: Vector2, event, pulse: float) -> None:
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
        pygame.draw.ellipse(self.screen, (12, 16, 16), shadow)

        pygame.draw.line(self.screen, (64, 54, 42), body_pos + Vector2(-4, 14), body_pos + Vector2(-2, 2), 3)
        pygame.draw.line(self.screen, (64, 54, 42), body_pos + Vector2(4, 14), body_pos + Vector2(2, 2), 3)
        pygame.draw.line(self.screen, (76, 64, 48), body_pos + Vector2(0, -2), body_pos + Vector2(0, 8), 4)
        arm_lift = math.sin(tick * 2.6 + event.uid * 0.41) * 1.5
        pygame.draw.line(self.screen, accent_color, body_pos + Vector2(-10, arm_lift), body_pos + Vector2(10, 2 - arm_lift), 3)
        torso = pygame.Rect(0, 0, 18, 20)
        torso.center = (int(body_pos.x), int(body_pos.y - 2))
        pygame.draw.ellipse(self.screen, body_color, torso)
        pygame.draw.ellipse(self.screen, tuple(max(0, c - 34) for c in body_color), torso, 1)
        head = pygame.Rect(0, 0, 14, 14)
        head.center = (int(body_pos.x), int(body_pos.y - 18))
        pygame.draw.ellipse(self.screen, (224, 214, 188), head)
        pygame.draw.circle(self.screen, (40, 34, 28), (int(body_pos.x - 3), int(body_pos.y - 20)), 1)
        pygame.draw.circle(self.screen, (40, 34, 28), (int(body_pos.x + 3), int(body_pos.y - 20)), 1)
        pygame.draw.arc(self.screen, (96, 72, 54), pygame.Rect(body_pos.x - 4, body_pos.y - 18, 8, 6), 0.2, 2.9, 1)

        if prop == "bag":
            pack = pygame.Rect(0, 0, 10, 12)
            pack.center = (int(body_pos.x + 11 + sway * 0.6), int(body_pos.y - 1))
            pygame.draw.rect(self.screen, (98, 84, 62), pack, border_radius=3)
            pygame.draw.rect(self.screen, (64, 52, 38), pack, 1, border_radius=3)
        elif prop == "crate":
            crate = pygame.Rect(0, 0, 14, 10)
            crate.center = (int(body_pos.x + 14 + sway * 0.3), int(body_pos.y + 8))
            pygame.draw.rect(self.screen, (118, 92, 62), crate, border_radius=2)
            pygame.draw.rect(self.screen, (72, 50, 32), crate, 1, border_radius=2)
        elif prop == "pole":
            pole_tip = body_pos + Vector2(12, -18)
            pole_base = body_pos + Vector2(12, 16)
            pygame.draw.line(self.screen, (132, 118, 96), pole_base, pole_tip, 2)
            cloth_sway = math.sin(tick * 2.2 + event.uid * 0.53) * 2.2
            cloth = [pole_tip + Vector2(0, 2), pole_tip + Vector2(10 + cloth_sway, 6), pole_tip + Vector2(0, 10)]
            pygame.draw.polygon(self.screen, accent_color, cloth)

        glow = pygame.Surface((54, 54), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*accent_color, int(18 + pulse * 10)), (27, 27), 14)
        self.screen.blit(glow, pos - Vector2(27, 27))
        if self.player.distance_to(event.pos) < 148:
            self.draw_event_visitor_bubble(body_pos, event, accent_color)

    def event_visitor_bark(self, event) -> str:
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

    def draw_event_visitor_bubble(self, pos: Vector2, event, color: tuple[int, int, int]) -> None:
        bark_text = self.event_visitor_bark(event)
        if not bark_text:
            return
        lines = self.wrap_text_lines(self.ui_small_font, bark_text, 180)
        text_surfaces = [self.ui_small_font.render(line, True, PALETTE["text"]) for line in lines]
        width = max(surface.get_width() for surface in text_surfaces) + 20
        height = len(text_surfaces) * self.ui_small_font.get_linesize() + max(0, len(text_surfaces) - 1) * 2 + 12
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
            text_y += self.ui_small_font.get_linesize() + 2
        bubble_pos = pos - Vector2(width / 2, 56 + height)
        self.screen.blit(bubble, bubble_pos)

    def draw_interaction_prompt(self, shake_offset: Vector2) -> None:
        hovered_target = self.hovered_interaction_target()
        reachable = False
        label_text: str | None = None
        if hovered_target and not self.player_sleeping:
            world_pos = Vector2(hovered_target["pos"])
            label_text = self.prompt_for_interaction_target(hovered_target)
            reachable = self.player.distance_to(world_pos) <= float(hovered_target.get("reach", 112.0))
            if not label_text:
                hovered_target = None
        if not hovered_target:
            hint = self.nearest_interaction_hint()
            if not hint or self.player_sleeping:
                return
            world_pos, label_text = hint
            reachable = True
        else:
            world_pos = Vector2(hovered_target["pos"])
        if not label_text:
            return
        pos = self.world_to_screen(world_pos) + shake_offset
        if pos.x < -140 or pos.x > SCREEN_WIDTH + 140 or pos.y < -140 or pos.y > SCREEN_HEIGHT + 140:
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 210)
        ring_radius = 18 + pulse * 4
        ring_color = PALETTE["accent_soft"] if reachable else PALETTE["muted"]
        pygame.draw.circle(self.screen, ring_color, pos, ring_radius, 2)
        if label_text.startswith("E "):
            label_text = label_text.replace("E ", "E / botao direito ", 1)
        if hovered_target and not reachable:
            label_text = self.fit_text_to_width(self.body_font, f"{label_text}  |  chegue mais perto", 440)
        label = self.body_font.render(label_text, True, PALETTE["text"])
        box = pygame.Rect(0, 0, min(360, label.get_width() + 18), label.get_height() + 10)
        box.midbottom = (pos.x, pos.y - 20)
        pygame.draw.rect(self.screen, (16, 22, 24), box, border_radius=10)
        pygame.draw.rect(self.screen, ring_color, box, 1, border_radius=10)
        self.screen.blit(label, label.get_rect(center=box.center))

    def draw_camp(self, shake_offset: Vector2) -> None:
        for tree in self.trees:
            self.draw_tree(tree, shake_offset)

        world_bounds = self.camp_visual_bounds(118)
        screen_bounds = world_bounds.move(shake_offset.x, shake_offset.y)
        camp_surface = pygame.Surface((world_bounds.width, world_bounds.height), pygame.SRCALPHA)
        outline_sets = (
            (self.camp_visual_ellipses(28), (118, 112, 78, 18), 2),
            (self.camp_visual_ellipses(-18), (142, 136, 96, 14), 1),
        )
        for ellipses, color, width in outline_sets:
            for ellipse in ellipses:
                local = ellipse.move(-world_bounds.x, -world_bounds.y)
                pygame.draw.ellipse(camp_surface, color, local, width)
        self.screen.blit(camp_surface, screen_bounds.topleft)

        for tent in self.tents:
            pos = self.world_to_screen(Vector2(tent["pos"])) + shake_offset
            self.draw_player_tent(pos, float(tent["angle"]), float(tent["scale"]), float(tent.get("tone", 0.5)))

        self.draw_stockpile(shake_offset)
        self.draw_station(self.workshop_pos, "oficina", PALETTE["wood"], shake_offset)
        self.draw_station(self.kitchen_pos, "fogao", (162, 126, 82), shake_offset)
        self.draw_station(self.radio_pos, "radio", (100, 114, 124), shake_offset)
        self.draw_expedition_caravan(shake_offset)
        self.draw_bonfire(shake_offset)

    def draw_expedition_caravan(self, shake_offset: Vector2) -> None:
        caravan = self.expedition_caravan_state()
        if not caravan:
            return
        start = self.world_to_screen(self.radio_pos) + shake_offset
        edge = self.world_to_screen(self.expedition_route_edge_point()) + shake_offset
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
            pygame.draw.ellipse(self.screen, (12, 15, 16), pygame.Rect(walker.x - 8, walker.y + 7, 16, 6))
            pygame.draw.circle(self.screen, (146, 162, 174), (int(walker.x), int(walker.y - 10)), 5)
            pygame.draw.line(self.screen, (88, 102, 114), walker + Vector2(0, -6), walker + Vector2(0, 4), 2)

        cart = center + unit * 10
        body = pygame.Rect(0, 0, 22, 12)
        body.center = (int(cart.x), int(cart.y))
        pygame.draw.rect(self.screen, (102, 84, 58), body, border_radius=4)
        pygame.draw.rect(self.screen, (68, 52, 36), body, 2, border_radius=4)
        wheel_a = (int(cart.x - 8), int(cart.y + 8))
        wheel_b = (int(cart.x + 8), int(cart.y + 8))
        pygame.draw.circle(self.screen, (34, 30, 26), wheel_a, 4)
        pygame.draw.circle(self.screen, (34, 30, 26), wheel_b, 4)
        pygame.draw.circle(self.screen, (110, 98, 78), wheel_a, 2)
        pygame.draw.circle(self.screen, (110, 98, 78), wheel_b, 2)

        label_text = "saindo" if caravan["phase"] == "outbound" else "voltando"
        label = self.small_font.render(f"caravana {label_text}", True, PALETTE["text"])
        box = pygame.Rect(0, 0, label.get_width() + 10, label.get_height() + 4)
        box.midbottom = (int(center.x), int(center.y - 16))
        pygame.draw.rect(self.screen, (18, 24, 26), box, border_radius=7)
        pygame.draw.rect(self.screen, PALETTE["ui_line"], box, 1, border_radius=7)
        self.screen.blit(label, label.get_rect(center=box.center))

        expedition = self.active_expedition
        if expedition and str(expedition.get("skirmish_state", "")) == "active" and expedition.get("skirmish_pos") is not None:
            skirmish = self.world_to_screen(Vector2(expedition["skirmish_pos"])) + shake_offset
            ring_color = PALETTE["danger_soft"]
            pygame.draw.circle(self.screen, ring_color, skirmish, 24, 3)
            pygame.draw.circle(self.screen, (18, 24, 26), skirmish, 10)
            pygame.draw.circle(self.screen, (128, 164, 208), skirmish, 6)
            for offset in (-18, 0, 18):
                walker = skirmish + lateral * (offset * 0.4)
                pygame.draw.ellipse(self.screen, (12, 15, 16), pygame.Rect(walker.x - 8, walker.y + 7, 16, 6))
                pygame.draw.circle(self.screen, (146, 162, 174), (int(walker.x), int(walker.y - 10)), 5)
                pygame.draw.line(self.screen, (88, 102, 114), walker + Vector2(0, -6), walker + Vector2(0, 4), 2)
            alert = self.small_font.render("coluna em combate", True, PALETTE["text"])
            alert_box = pygame.Rect(0, 0, alert.get_width() + 12, alert.get_height() + 4)
            alert_box.midbottom = (int(skirmish.x), int(skirmish.y - 18))
            pygame.draw.rect(self.screen, (18, 24, 26), alert_box, border_radius=7)
            pygame.draw.rect(self.screen, ring_color, alert_box, 1, border_radius=7)
            self.screen.blit(alert, alert.get_rect(center=alert_box.center))

    def draw_tree(self, tree: dict[str, object], shake_offset: Vector2) -> None:
        pos = self.world_to_screen(Vector2(tree["pos"])) + shake_offset
        radius = int(tree["radius"])
        if pos.x < -100 or pos.x > SCREEN_WIDTH + 100 or pos.y < -100 or pos.y > SCREEN_HEIGHT + 100:
            return

        if tree.get("harvested", False):
            stump_rect = pygame.Rect(0, 0, int(radius * 0.9), int(radius * 0.46))
            stump_rect.center = (int(pos.x), int(pos.y + radius * 0.72))
            pygame.draw.ellipse(self.screen, (14, 18, 16), stump_rect.inflate(8, 10))
            pygame.draw.ellipse(self.screen, (96, 70, 44), stump_rect)
            pygame.draw.ellipse(self.screen, (62, 43, 28), stump_rect, 2)
            ring_rect = stump_rect.inflate(-10, -8)
            if ring_rect.width > 2 and ring_rect.height > 2:
                pygame.draw.ellipse(self.screen, (156, 126, 82), ring_rect)
            fallen = pygame.Rect(0, 0, int(radius * 1.1), int(radius * 0.26))
            fallen.center = (int(pos.x + radius * 0.72), int(pos.y + radius * 0.46))
            pygame.draw.ellipse(self.screen, (88, 61, 39), fallen)
            pygame.draw.ellipse(self.screen, (60, 40, 26), fallen, 2)
            return

        height = float(tree["height"])
        lean = float(tree["lean"])
        spread = float(tree["spread"])
        branch_bias = float(tree["branch_bias"])
        tone = float(tree["tone"])
        wind = self.weather_wind_factor()
        storm = self.weather_storm_factor()
        tick = pygame.time.get_ticks() / 1000.0
        sway = math.sin(tick * (0.9 + wind * 1.3) + float(tree.get("sway_seed", tone * 4.6))) * (wind * 4.0 + storm * 3.0)
        pos = pos + Vector2(sway * 0.18, 0)
        lean = lean + sway * 0.016

        crown_color = (
            int(lerp(35, 69, tone)),
            int(lerp(59, 116, tone)),
            int(lerp(40, 68, tone)),
        )
        crown_dark = tuple(max(0, int(channel * 0.76)) for channel in crown_color)
        crown_light = tuple(min(255, int(channel * 1.1)) for channel in crown_color)

        shadow_rect = pygame.Rect(0, 0, int(radius * 2.15), int(radius * 0.92))
        shadow_rect.center = (int(pos.x + lean * 12), int(pos.y + radius * 0.72))
        pygame.draw.ellipse(self.screen, (10, 14, 13), shadow_rect)

        trunk_base = pos + Vector2(0, radius * 0.72)
        trunk_top = pos + Vector2(lean * radius * 0.9, -radius * (0.66 + height * 0.26))
        trunk_half = max(6, int(radius * 0.18))
        trunk_points = [
            trunk_base + Vector2(-trunk_half * 0.9, 0),
            trunk_top + Vector2(-trunk_half * 0.55, -2),
            trunk_top + Vector2(trunk_half * 0.55, 2),
            trunk_base + Vector2(trunk_half * 0.9, 0),
        ]
        pygame.draw.polygon(self.screen, (93, 66, 44), trunk_points)
        pygame.draw.polygon(self.screen, (58, 37, 25), trunk_points, 2)

        for root_dir in (-1, 1):
            root_start = trunk_base + Vector2(root_dir * 2, -2)
            root_mid = root_start + Vector2(root_dir * radius * 0.24, radius * 0.07)
            root_end = root_mid + Vector2(root_dir * radius * 0.18, radius * 0.05)
            pygame.draw.lines(self.screen, (74, 50, 34), False, [root_start, root_mid, root_end], 3)

        for index in range(3):
            bark_y = trunk_top.lerp(trunk_base, 0.28 + index * 0.22)
            pygame.draw.line(
                self.screen,
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
            pygame.draw.line(self.screen, (74, 50, 34), branch_start, branch_end, 3)

        cluster_centers = [
            trunk_top + Vector2(-radius * 0.52 * spread, radius * 0.08),
            trunk_top + Vector2(radius * 0.1 * branch_bias, -radius * 0.38),
            trunk_top + Vector2(radius * 0.56 * spread, -radius * 0.02),
            trunk_top + Vector2(radius * 0.12, radius * 0.26),
        ]
        cluster_sizes = [0.86, 0.78, 0.72, 0.66]
        for center, size in zip(cluster_centers, cluster_sizes):
            pygame.draw.circle(self.screen, crown_dark, (int(center.x), int(center.y + radius * 0.12)), int(radius * size))
            pygame.draw.circle(self.screen, crown_color, (int(center.x), int(center.y)), int(radius * size))
            pygame.draw.circle(
                self.screen,
                crown_light,
                (int(center.x - radius * 0.22), int(center.y - radius * 0.18)),
                int(radius * size * 0.5),
            )

    def draw_buildings(self, shake_offset: Vector2) -> None:
        for building in self.buildings:
            pos = self.world_to_screen(building.pos) + shake_offset
            if pos.x < -120 or pos.x > SCREEN_WIDTH + 120 or pos.y < -120 or pos.y > SCREEN_HEIGHT + 120:
                continue
            if building.kind == "barraca":
                self.draw_player_tent(pos, 0.0, 0.92, 0.62)
            elif building.kind == "torre":
                self.draw_watchtower(pos)
            elif building.kind == "horta":
                self.draw_garden_plot(pos)
            elif building.kind == "anexo":
                self.draw_workshop_annex(pos)
            elif building.kind == "serraria":
                self.draw_sawmill(pos)
            elif building.kind == "cozinha":
                self.draw_cookhouse(pos)
            elif building.kind == "enfermaria":
                self.draw_infirmary(pos)

            if building.assigned_to:
                text = self.small_font.render(building.assigned_to.lower(), True, PALETTE["text"])
                box = pygame.Rect(0, 0, text.get_width() + 12, text.get_height() + 4)
                box.midbottom = (pos.x, pos.y - building.size * 0.7)
                pygame.draw.rect(self.screen, (18, 24, 26), box, border_radius=8)
                pygame.draw.rect(self.screen, PALETTE["ui_line"], box, 1, border_radius=8)
                self.screen.blit(text, text.get_rect(center=box.center))

    def draw_player_tent(self, pos: Vector2, angle: float, scale: float, tone: float = 0.5) -> None:
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
        pygame.draw.ellipse(self.screen, (10, 14, 13), shadow)

        back_panel = [tip, left, right]
        left_flap = [tip, left, entrance]
        right_flap = [tip, entrance, right]
        ground = [front_left, left, right, front_right]
        pygame.draw.polygon(self.screen, (72, 54, 34), ground)
        pygame.draw.polygon(self.screen, canvas_base, back_panel)
        pygame.draw.polygon(self.screen, canvas_light, left_flap)
        pygame.draw.polygon(self.screen, canvas_dark, right_flap)
        pygame.draw.polygon(self.screen, PALETTE["wood_dark"], back_panel, 2)
        pygame.draw.polygon(self.screen, PALETTE["wood_dark"], left_flap, 1)
        pygame.draw.polygon(self.screen, PALETTE["wood_dark"], right_flap, 1)

        door = pygame.Rect(0, 0, int(16 * scale), int(18 * scale))
        door.center = (int(entrance.x), int(entrance.y + 8 * scale))
        pygame.draw.ellipse(self.screen, (38, 28, 22), door)
        bedroll = pygame.Rect(0, 0, int(26 * scale), int(8 * scale))
        bedroll.center = (int(pos.x), int(pos.y + 14 * scale))
        pygame.draw.ellipse(self.screen, (92, 116, 124), bedroll)
        pygame.draw.ellipse(self.screen, (58, 72, 76), bedroll, 1)

        pole_top = tip + Vector2(0, -4 * scale)
        pygame.draw.line(self.screen, (86, 62, 40), tip, pole_top, 2)
        for anchor, offset in ((left, -1), (right, 1)):
            peg = anchor + forward * (10 * scale) + side * (offset * 8 * scale)
            pygame.draw.line(self.screen, (96, 84, 64), anchor, peg, 1)
            pygame.draw.line(self.screen, (84, 62, 46), peg, peg + Vector2(0, 6 * scale), 2)

    def draw_watchtower(self, pos: Vector2) -> None:
        shadow = pygame.Rect(0, 0, 48, 16)
        shadow.center = (int(pos.x), int(pos.y + 18))
        pygame.draw.ellipse(self.screen, (14, 18, 16), shadow)
        for offset in (-14, 14):
            pygame.draw.line(self.screen, PALETTE["wood_dark"], pos + Vector2(offset, 18), pos + Vector2(offset * 0.45, -16), 4)
        deck = pygame.Rect(0, 0, 42, 14)
        deck.center = (int(pos.x), int(pos.y - 20))
        pygame.draw.rect(self.screen, PALETTE["wood"], deck, border_radius=4)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"], deck, 2, border_radius=4)
        pygame.draw.line(self.screen, (156, 136, 102), (deck.x + 6, deck.y + 3), (deck.right - 6, deck.y + 3), 1)
        pygame.draw.line(self.screen, (92, 74, 50), (deck.x + 6, deck.bottom - 4), (deck.right - 6, deck.bottom - 4), 1)
        pygame.draw.line(self.screen, PALETTE["wood_dark"], deck.midtop, deck.midtop + Vector2(0, -18), 3)
        pygame.draw.polygon(self.screen, (148, 128, 82), [deck.midtop + Vector2(0, -24), deck.midtop + Vector2(-16, -6), deck.midtop + Vector2(16, -6)])
        lantern = deck.midtop + Vector2(12, -4)
        pygame.draw.circle(self.screen, (218, 176, 92), lantern, 3)
        glow = pygame.Surface((26, 26), pygame.SRCALPHA)
        pygame.draw.circle(glow, (236, 182, 92, 34), (13, 13), 10)
        self.screen.blit(glow, Vector2(lantern) - Vector2(13, 13))

    def draw_garden_plot(self, pos: Vector2) -> None:
        rect = pygame.Rect(0, 0, 54, 34)
        rect.center = (int(pos.x), int(pos.y))
        pygame.draw.rect(self.screen, (94, 74, 46), rect, border_radius=8)
        pygame.draw.rect(self.screen, (61, 45, 31), rect, 2, border_radius=8)
        fence = rect.inflate(10, 8)
        pygame.draw.rect(self.screen, (116, 92, 58), fence, 2, border_radius=10)
        for row in range(3):
            y = rect.y + 8 + row * 8
            pygame.draw.line(self.screen, (128, 95, 58), (rect.x + 4, y), (rect.right - 4, y), 2)
        for index, offset in enumerate((-16, -5, 8, 19)):
            sprout = pos + Vector2(offset, (-4, 2, 5, -1)[index])
            pygame.draw.line(self.screen, (62, 116, 64), sprout + Vector2(0, 10), sprout, 2)
            pygame.draw.circle(self.screen, (106, 162, 82), sprout + Vector2(-2, -2), 3)
            pygame.draw.circle(self.screen, (88, 148, 74), sprout + Vector2(2, -1), 3)
        bucket = pygame.Rect(0, 0, 10, 10)
        bucket.center = (int(pos.x + 24), int(pos.y + 10))
        pygame.draw.rect(self.screen, (96, 108, 118), bucket, border_radius=3)
        pygame.draw.rect(self.screen, (62, 74, 84), bucket, 1, border_radius=3)

    def draw_workshop_annex(self, pos: Vector2) -> None:
        rect = pygame.Rect(0, 0, 54, 40)
        rect.center = (int(pos.x), int(pos.y))
        pygame.draw.rect(self.screen, (112, 92, 66), rect, border_radius=8)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"], rect, 2, border_radius=8)
        roof = [rect.midtop + Vector2(0, -16), rect.topleft + Vector2(-6, 2), rect.topright + Vector2(6, 2)]
        pygame.draw.polygon(self.screen, (82, 72, 58), roof)
        pygame.draw.line(self.screen, (138, 124, 102), (rect.x + 14, rect.y + 12), (rect.right - 14, rect.y + 12), 2)
        pygame.draw.line(self.screen, (138, 124, 102), (rect.x + 14, rect.y + 22), (rect.right - 14, rect.y + 22), 2)
        pygame.draw.line(self.screen, (138, 124, 102), (rect.centerx, rect.y + 10), (rect.centerx, rect.bottom - 8), 2)
        tool_rack = pygame.Rect(rect.x + 8, rect.bottom - 10, 18, 6)
        pygame.draw.rect(self.screen, (74, 56, 38), tool_rack, border_radius=2)
        pygame.draw.line(self.screen, (162, 146, 120), tool_rack.midleft + Vector2(4, -8), tool_rack.midleft + Vector2(4, 0), 2)
        pygame.draw.line(self.screen, (144, 126, 98), tool_rack.midleft + Vector2(10, -7), tool_rack.midleft + Vector2(10, 0), 2)

    def draw_sawmill(self, pos: Vector2) -> None:
        base = pygame.Rect(0, 0, 58, 38)
        base.center = (int(pos.x), int(pos.y + 4))
        pygame.draw.rect(self.screen, (102, 84, 58), base, border_radius=8)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"], base, 2, border_radius=8)
        for offset in (-16, 0, 16):
            log = pygame.Rect(0, 0, 22, 8)
            log.center = (int(pos.x + offset * 0.65), int(pos.y + 10 + abs(offset) * 0.1))
            pygame.draw.ellipse(self.screen, (118, 82, 48), log)
            pygame.draw.ellipse(self.screen, (72, 46, 30), log, 2)
        blade = pygame.Rect(0, 0, 12, 28)
        blade.center = (int(pos.x + 16), int(pos.y - 10))
        pygame.draw.rect(self.screen, (142, 150, 154), blade, border_radius=4)
        pygame.draw.rect(self.screen, (82, 89, 94), blade, 1, border_radius=4)
        rail = pygame.Rect(base.x + 6, base.y + 6, 30, 6)
        pygame.draw.rect(self.screen, (132, 110, 72), rail, border_radius=3)
        stack = pygame.Rect(0, 0, 18, 12)
        stack.center = (int(pos.x - 18), int(pos.y - 10))
        pygame.draw.rect(self.screen, (136, 102, 64), stack, border_radius=3)
        pygame.draw.line(self.screen, (86, 62, 40), (stack.x + 3, stack.y + 4), (stack.right - 3, stack.y + 4), 1)
        pygame.draw.line(self.screen, (86, 62, 40), (stack.x + 3, stack.y + 8), (stack.right - 3, stack.y + 8), 1)

    def draw_cookhouse(self, pos: Vector2) -> None:
        rect = pygame.Rect(0, 0, 56, 42)
        rect.center = (int(pos.x), int(pos.y))
        pygame.draw.rect(self.screen, (128, 96, 64), rect, border_radius=10)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"], rect, 2, border_radius=10)
        roof = [rect.midtop + Vector2(0, -18), rect.topleft + Vector2(-6, 4), rect.topright + Vector2(6, 4)]
        pygame.draw.polygon(self.screen, (90, 74, 58), roof)
        oven = pygame.Rect(0, 0, 20, 16)
        oven.center = (int(pos.x), int(pos.y + 8))
        pygame.draw.rect(self.screen, (70, 56, 48), oven, border_radius=5)
        pygame.draw.rect(self.screen, (38, 24, 22), oven.inflate(-8, -4), border_radius=4)
        pygame.draw.circle(self.screen, (214, 164, 88), pos + Vector2(16, -4), 7)
        pygame.draw.circle(self.screen, (236, 196, 116), pos + Vector2(14, -6), 4)
        chimney = pygame.Rect(0, 0, 8, 16)
        chimney.midbottom = (int(pos.x + 14), int(rect.y + 6))
        pygame.draw.rect(self.screen, (74, 62, 58), chimney, border_radius=2)
        pygame.draw.circle(self.screen, (210, 210, 210), chimney.midtop + Vector2(-2, -6), 3)
        pygame.draw.circle(self.screen, (190, 190, 190), chimney.midtop + Vector2(3, -11), 2)

    def draw_infirmary(self, pos: Vector2) -> None:
        rect = pygame.Rect(0, 0, 54, 40)
        rect.center = (int(pos.x), int(pos.y))
        pygame.draw.rect(self.screen, (114, 124, 112), rect, border_radius=9)
        pygame.draw.rect(self.screen, (74, 82, 72), rect, 2, border_radius=9)
        roof = [rect.midtop + Vector2(0, -14), rect.topleft + Vector2(-4, 4), rect.topright + Vector2(4, 4)]
        pygame.draw.polygon(self.screen, (92, 102, 92), roof)
        pygame.draw.rect(self.screen, (228, 226, 212), pygame.Rect(rect.centerx - 9, rect.y + 8, 18, 18), border_radius=4)
        pygame.draw.rect(self.screen, (178, 62, 62), pygame.Rect(rect.centerx - 3, rect.y + 10, 6, 14), border_radius=2)
        pygame.draw.rect(self.screen, (178, 62, 62), pygame.Rect(rect.centerx - 7, rect.y + 14, 14, 6), border_radius=2)
        cot = pygame.Rect(0, 0, 18, 8)
        cot.center = (int(pos.x - 14), int(pos.y + 8))
        pygame.draw.rect(self.screen, (182, 196, 188), cot, border_radius=3)
        pygame.draw.rect(self.screen, (98, 112, 104), cot, 1, border_radius=3)
        lamp = pos + Vector2(16, -8)
        pygame.draw.circle(self.screen, (220, 196, 124), lamp, 3)

    def draw_station(
        self,
        pos: Vector2,
        label: str,
        color: tuple[int, int, int],
        shake_offset: Vector2,
    ) -> None:
        screen_pos = self.world_to_screen(pos) + shake_offset
        rect = pygame.Rect(0, 0, 72, 40)
        rect.center = (screen_pos.x, screen_pos.y)
        pygame.draw.rect(self.screen, (18, 22, 21), rect.move(0, 10), border_radius=11)
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"], rect, 2, border_radius=12)
        text = self.small_font.render(label, True, PALETTE["text"])
        self.screen.blit(text, text.get_rect(center=(screen_pos.x, screen_pos.y)))

    def draw_stockpile(self, shake_offset: Vector2) -> None:
        pos = self.world_to_screen(self.stockpile_pos) + shake_offset
        shadow = pygame.Rect(0, 0, 104, 34)
        shadow.center = (int(pos.x), int(pos.y + 22))
        pygame.draw.ellipse(self.screen, (16, 18, 18), shadow)

        for index in range(min(3, self.logs // 8 + (1 if self.logs > 0 else 0))):
            log = pygame.Rect(0, 0, 26, 10)
            log.center = (int(pos.x - 26 + index * 16), int(pos.y + 8 - index * 3))
            pygame.draw.ellipse(self.screen, (120, 84, 48), log)
            pygame.draw.ellipse(self.screen, (72, 44, 28), log, 2)

        crate = pygame.Rect(0, 0, 32, 24)
        crate.center = (int(pos.x + 20), int(pos.y + 2))
        pygame.draw.rect(self.screen, (104, 84, 60), crate, border_radius=6)
        pygame.draw.rect(self.screen, PALETTE["wood_dark"], crate, 2, border_radius=6)
        pygame.draw.line(self.screen, (148, 126, 92), (crate.x + 6, crate.y + 8), (crate.right - 6, crate.y + 8), 2)
        pygame.draw.line(self.screen, (148, 126, 92), (crate.x + 6, crate.y + 16), (crate.right - 6, crate.y + 16), 2)

        herb_box = pygame.Rect(0, 0, 22, 16)
        herb_box.center = (int(pos.x + 46), int(pos.y - 6))
        pygame.draw.rect(self.screen, (82, 102, 72), herb_box, border_radius=4)
        pygame.draw.rect(self.screen, (56, 68, 50), herb_box, 1, border_radius=4)
        if self.herbs > 0:
            pygame.draw.line(self.screen, (108, 168, 92), herb_box.center, herb_box.center + Vector2(-4, -8), 2)
            pygame.draw.line(self.screen, (108, 168, 92), herb_box.center, herb_box.center + Vector2(4, -6), 2)

    def draw_bonfire(self, shake_offset: Vector2) -> None:
        fire_pos = self.world_to_screen(self.bonfire_pos) + shake_offset
        heat_ratio = self.bonfire_heat / 100
        ember_ratio = self.bonfire_ember_bed / 100
        stage = self.bonfire_stage()
        night_glow = 0.18 + self.visual_darkness_factor() * 0.82
        pygame.draw.circle(self.screen, (34, 25, 19), fire_pos, 54)
        pygame.draw.circle(self.screen, (72, 56, 32), fire_pos, 38)
        for angle in (0.2, 1.8, 3.5):
            vec = angle_to_vector(angle) * 26
            pygame.draw.line(self.screen, PALETTE["wood_dark"], fire_pos - vec, fire_pos + vec, 7)

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
        self.screen.blit(ember_surface, fire_pos - Vector2(70, 70))

        if stage != "brasas":
            flame_height = 14 + 28 * heat_ratio + math.sin(pygame.time.get_ticks() / 160) * (2 + heat_ratio * 2)
            flame_width = 10 + 12 * heat_ratio
            pygame.draw.polygon(
                self.screen,
                (210, 122, 72),
                [
                    fire_pos + Vector2(0, -flame_height),
                    fire_pos + Vector2(-flame_width - 4, 10),
                    fire_pos + Vector2(0, 24),
                    fire_pos + Vector2(flame_width + 4, 10),
                ],
            )
            pygame.draw.polygon(
                self.screen,
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
            self.screen.blit(lick, fire_pos - Vector2(60, 60))

        if self.random.random() < (0.22 + heat_ratio * 0.34 + ember_ratio * 0.12):
            self.emit_embers(self.bonfire_pos + Vector2(self.random.uniform(-8, 8), -8), 1)

    def draw_resource_nodes(self, shake_offset: Vector2) -> None:
        for node in self.resource_nodes:
            pos = self.world_to_screen(node.pos) + shake_offset
            if pos.x < -80 or pos.x > SCREEN_WIDTH + 80 or pos.y < -80 or pos.y > SCREEN_HEIGHT + 80:
                continue
            if node.kind == "food":
                self.draw_food_node(pos, node.radius, node.variant)
            else:
                self.draw_scrap_node(pos, node.radius, node.variant)

            if not node.is_available():
                overlay = pygame.Surface((80, 80), pygame.SRCALPHA)
                pygame.draw.circle(overlay, (18, 20, 20, 120), (40, 40), node.radius + 7)
                self.screen.blit(overlay, pos - Vector2(40, 40))

    def draw_food_node(self, pos: Vector2, radius: int, variant: str = "") -> None:
        shadow = pygame.Rect(0, 0, int(radius * 1.9), int(radius * 0.88))
        shadow.center = (int(pos.x), int(pos.y + radius * 0.55))
        pygame.draw.ellipse(self.screen, (14, 18, 16), shadow)
        bush_colors = ((36, 79, 46), (52, 98, 58), (69, 124, 74))
        leaf_offsets = (
            Vector2(-radius * 0.46, 2),
            Vector2(radius * 0.08, -radius * 0.36),
            Vector2(radius * 0.5, 4),
            Vector2(-4, radius * 0.28),
        )
        for color, offset, scale in zip(bush_colors * 2, leaf_offsets, (0.78, 0.66, 0.7, 0.62)):
            pygame.draw.circle(
                self.screen,
                color,
                (int(pos.x + offset.x), int(pos.y + offset.y)),
                int(radius * scale),
            )
        if variant in {"mushrooms", "roots"}:
            stem = (214, 198, 164)
            cap = (174, 98, 84) if variant == "mushrooms" else (146, 118, 82)
            for offset in (Vector2(-8, 4), Vector2(0, -3), Vector2(9, 6)):
                stem_pos = pos + offset
                pygame.draw.line(self.screen, stem, stem_pos + Vector2(0, 6), stem_pos, 2)
                pygame.draw.ellipse(self.screen, cap, pygame.Rect(stem_pos.x - 5, stem_pos.y - 2, 10, 6))
        elif variant == "flowers":
            for offset in (Vector2(-8, -4), Vector2(3, -8), Vector2(9, 5), Vector2(-5, 8)):
                flower = pos + offset
                pygame.draw.circle(self.screen, (236, 206, 122), flower, 3)
                pygame.draw.circle(self.screen, (191, 116, 88), flower + Vector2(2, 1), 3)
        elif variant == "herbs":
            for offset in (Vector2(-6, 5), Vector2(2, -7), Vector2(10, 2)):
                herb = pos + offset
                pygame.draw.line(self.screen, (90, 142, 74), herb + Vector2(0, 9), herb, 2)
                pygame.draw.circle(self.screen, (118, 176, 96), herb + Vector2(-2, -2), 3)
                pygame.draw.circle(self.screen, (106, 164, 88), herb + Vector2(2, -1), 3)
        else:
            for offset in (Vector2(-8, -4), Vector2(3, -8), Vector2(9, 5), Vector2(-5, 8), Vector2(6, -1)):
                berry_pos = pos + offset
                pygame.draw.circle(self.screen, (202, 72, 77), berry_pos, 4)
                pygame.draw.circle(self.screen, (238, 145, 128), berry_pos + Vector2(-1, -1), 2)

    def draw_scrap_node(self, pos: Vector2, radius: int, variant: str = "") -> None:
        shadow = pygame.Rect(0, 0, int(radius * 1.8), int(radius * 0.82))
        shadow.center = (int(pos.x), int(pos.y + radius * 0.55))
        pygame.draw.ellipse(self.screen, (14, 18, 16), shadow)
        if variant in {"ore", "stonecache"}:
            colors = ((128, 134, 140), (96, 104, 112), (154, 164, 170))
            for index, offset in enumerate((Vector2(-10, 4), Vector2(8, -2), Vector2(2, -10))):
                rock = pygame.Rect(0, 0, 18 + index * 3, 14 + (index % 2) * 4)
                rock.center = (int(pos.x + offset.x), int(pos.y + offset.y))
                pygame.draw.rect(self.screen, colors[index], rock, border_radius=5)
                pygame.draw.rect(self.screen, (68, 74, 80), rock, 1, border_radius=5)
            return
        pieces = (
            pygame.Rect(int(pos.x - 14), int(pos.y - 6), 18, 14),
            pygame.Rect(int(pos.x - 4), int(pos.y - 14), 20, 12),
            pygame.Rect(int(pos.x + 6), int(pos.y - 1), 14, 11),
        )
        colors = ((93, 98, 107), (129, 136, 145), (75, 79, 86))
        for rect, color in zip(pieces, colors):
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, (54, 57, 63), rect, 1, border_radius=4)
        wheel_center = (int(pos.x - 10), int(pos.y + 7))
        pygame.draw.circle(self.screen, (48, 51, 57), wheel_center, 7, 3)
        pygame.draw.line(self.screen, (160, 116, 72), (int(pos.x - 4), int(pos.y - 10)), (int(pos.x + 12), int(pos.y + 6)), 2)

    def draw_barricades(self, shake_offset: Vector2) -> None:
        for barricade in self.barricades:
            pos = self.world_to_screen(barricade.pos) + shake_offset
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
            pygame.draw.polygon(self.screen, (17, 18, 17), shadow_points)

            stake_count = 4 + barricade.tier
            for index in range(stake_count):
                t = 0.0 if stake_count == 1 else index / (stake_count - 1)
                offset = -span * 0.48 + span * 0.96 * t
                center = pos + tangent * offset
                stake_height = 22 + barricade.tier * 5 + (index % 2) * 4
                base_left = center - tangent * 4 - normal * 10
                base_right = center + tangent * 4 - normal * 10
                tip = center + normal * stake_height
                pygame.draw.polygon(self.screen, color, [base_left, tip, base_right])
                pygame.draw.polygon(self.screen, PALETTE["wood_dark"], [base_left, tip, base_right], 1)

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
            pygame.draw.lines(self.screen, PALETTE["wood_dark"], False, brace_a, 4)
            pygame.draw.lines(self.screen, PALETTE["wood_dark"], False, brace_b, 4)

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
                    pygame.draw.polygon(self.screen, spike_color, [left, tip, right])
                    pygame.draw.polygon(self.screen, (72, 70, 68), [left, tip, right], 1)

            ratio = barricade.health / barricade.max_health
            bar_rect = pygame.Rect(0, 0, 52, 6)
            bar_rect.midbottom = (pos.x, pos.y - 18)
            pygame.draw.rect(self.screen, (26, 28, 28), bar_rect, border_radius=4)
            pygame.draw.rect(
                self.screen,
                PALETTE["heal"] if ratio > 0.5 else PALETTE["danger_soft"],
                (bar_rect.x + 1, bar_rect.y + 1, int((bar_rect.width - 2) * ratio), bar_rect.height - 2),
                border_radius=4,
            )
            if spike_level > 0:
                spike_label = self.small_font.render(f"S{spike_level}", True, PALETTE["accent_soft"])
                self.screen.blit(spike_label, spike_label.get_rect(midbottom=(pos.x, bar_rect.y - 2)))

    def draw_entities(self, shake_offset: Vector2) -> None:
        all_entities = []
        all_entities.append(("player", self.player, self.player.pos.y))
        all_entities.extend(
            ("survivor", survivor, survivor.pos.y)
            for survivor in self.survivors
            if survivor.is_alive() and (not self.is_survivor_on_expedition(survivor) or survivor in self.expedition_visible_members())
        )
        all_entities.extend(("zombie", zombie, zombie.pos.y) for zombie in self.zombies if zombie.is_alive())

        for kind, entity, _ in sorted(all_entities, key=lambda item: item[2]):
            pos = self.world_to_screen(entity.pos) + shake_offset
            pygame.draw.ellipse(
                self.screen,
                (11, 15, 16),
                pygame.Rect(pos.x - entity.radius * 0.92, pos.y + entity.radius * 0.48, entity.radius * 1.84, entity.radius * 0.86),
            )
            if kind == "player":
                player_expression = "calmo"
                if self.player.attack_flash > 0:
                    player_expression = "focado"
                elif self.player.health < self.player.max_health * 0.35:
                    player_expression = "ferido"
                elif self.player.stamina < self.player.max_stamina * 0.28:
                    player_expression = "cansado"
                self.draw_character(
                    pos,
                    (228, 208, 156),
                    (44, 54, 63),
                    entity.radius,
                    "chefe",
                    expression=player_expression,
                )
                if self.player.attack_flash > 0:
                    swing = pygame.Surface((160, 160), pygame.SRCALPHA)
                    center = Vector2(80, 80)
                    start = center + self.player.facing.rotate(-56) * 52
                    end = center + self.player.facing.rotate(56) * 76
                    points = [center, start, end]
                    alpha = int(140 * (self.player.attack_flash / 0.22))
                    pygame.draw.polygon(swing, (255, 202, 134, alpha), points)
                    self.screen.blit(swing, pos - center)
            elif kind == "survivor":
                survivor: Survivor = entity
                if getattr(survivor, "expedition_downed", False):
                    body = pygame.Rect(0, 0, int(entity.radius * 2.2), int(entity.radius * 1.08))
                    body.center = (int(pos.x), int(pos.y))
                    pygame.draw.ellipse(self.screen, (18, 20, 20), body.inflate(8, 6))
                    pygame.draw.ellipse(self.screen, survivor.color, body)
                    pygame.draw.ellipse(self.screen, (52, 44, 36), body, 2)
                    pygame.draw.circle(
                        self.screen,
                        (228, 208, 156),
                        (int(pos.x - entity.radius * 0.28), int(pos.y - entity.radius * 0.24)),
                        int(entity.radius * 0.34),
                    )
                else:
                    survivor_expression = self.survivor_expression(survivor)
                    self.draw_character(
                        pos,
                        survivor.color,
                        (52, 44, 36),
                        entity.radius,
                        survivor.name,
                        role=survivor.role,
                        expression=survivor_expression,
                    )
                self.draw_status_orb(pos, survivor)
                self.draw_survivor_bark(pos, survivor)
            else:
                zombie: Zombie = entity
                if getattr(zombie, "is_boss", False):
                    aura = pygame.Surface((220, 220), pygame.SRCALPHA)
                    center = Vector2(aura.get_width() / 2, aura.get_height() / 2)
                    glow_radius = int(entity.radius * 2.8)
                    aura_center = (int(center.x), int(center.y))
                    pygame.draw.circle(aura, (*zombie.boss_accent, 34), aura_center, glow_radius)
                    pygame.draw.circle(aura, (*zombie.boss_body, 76), aura_center, int(entity.radius * 1.9), 3)
                    self.screen.blit(aura, pos - center)
                    self.draw_character(
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
                    pygame.draw.rect(self.screen, (18, 24, 26), bar_rect, border_radius=5)
                    pygame.draw.rect(
                        self.screen,
                        PALETTE["danger_soft"],
                        (bar_rect.x + 1, bar_rect.y + 1, int((bar_rect.width - 2) * clamp(ratio, 0, 1)), bar_rect.height - 2),
                        border_radius=5,
                    )
                    pygame.draw.rect(self.screen, PALETTE["ui_line"], bar_rect, 1, border_radius=5)
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
                    zombie_expression = "agressivo" if getattr(zombie, "variant", "walker") in {"runner", "raider", "howler"} else "vazio"
                    self.draw_character(pos, body, accent, entity.radius, None, zombie=True, expression=zombie_expression)
                    if getattr(zombie, "weapon_name", ""):
                        self.draw_zombie_weapon(pos, zombie)
                    ratio = zombie.health / max(1.0, zombie.max_health)
                    bar_rect = pygame.Rect(0, 0, 42, 5)
                    bar_rect.midbottom = (pos.x, pos.y - entity.radius * 1.72)
                    pygame.draw.rect(self.screen, (18, 24, 26), bar_rect, border_radius=4)
                    pygame.draw.rect(
                        self.screen,
                        PALETTE["danger_soft"],
                        (bar_rect.x + 1, bar_rect.y + 1, int((bar_rect.width - 2) * clamp(ratio, 0, 1)), bar_rect.height - 2),
                        border_radius=4,
                    )
                    pygame.draw.rect(self.screen, PALETTE["ui_line"], bar_rect, 1, border_radius=4)

    def draw_character(
        self,
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
        pygame.draw.ellipse(self.screen, (12, 16, 16), shadow)

        pygame.draw.line(
            self.screen,
            (64, 54, 42),
            animated_pos + Vector2(-4 * scale, 13 * scale),
            animated_pos + Vector2(-2 * scale - arm_swing * 0.12, 2 * scale),
            max(2, int(3 * scale)),
        )
        pygame.draw.line(
            self.screen,
            (64, 54, 42),
            animated_pos + Vector2(4 * scale, 13 * scale),
            animated_pos + Vector2(2 * scale + arm_swing * 0.12, 2 * scale),
            max(2, int(3 * scale)),
        )
        pygame.draw.line(
            self.screen,
            (76, 64, 48),
            animated_pos + Vector2(0, -2 * scale),
            animated_pos + Vector2(0, 8 * scale),
            max(2, int(4 * scale)),
        )
        left_shoulder = animated_pos + Vector2(-5 * scale, -7 * scale)
        right_shoulder = animated_pos + Vector2(5 * scale, -7 * scale)
        left_hand = animated_pos + Vector2(-10 * scale - arm_swing, -2 * scale + arm_lift)
        right_hand = animated_pos + Vector2(10 * scale + arm_swing, -1 * scale - arm_lift)
        pygame.draw.line(self.screen, accent, left_shoulder, left_hand, max(2, int(3 * scale)))
        pygame.draw.line(self.screen, accent, right_shoulder, right_hand, max(2, int(3 * scale)))
        pygame.draw.circle(self.screen, head_color, (int(left_hand.x), int(left_hand.y)), max(1, int(1.25 * scale)))
        pygame.draw.circle(self.screen, head_color, (int(right_hand.x), int(right_hand.y)), max(1, int(1.25 * scale)))
        if role and not zombie:
            self.draw_role_tool(right_hand, role, scale, accent)

        torso = pygame.Rect(0, 0, int(18 * scale), int(20 * scale))
        torso.center = (int(animated_pos.x), int(animated_pos.y - 2 * scale))
        pygame.draw.ellipse(self.screen, clothing, torso)
        pygame.draw.ellipse(self.screen, outline, torso, 1)

        head = pygame.Rect(0, 0, int(14 * scale), int(14 * scale))
        head.center = (int(animated_pos.x), int(animated_pos.y - 18 * scale - arm_lift * 0.15))
        pygame.draw.ellipse(self.screen, head_color, head)
        face_center = Vector2(animated_pos.x, animated_pos.y - 18 * scale - arm_lift * 0.15)
        self.draw_face(face_center, scale, expression, zombie=zombie)
        if label:
            text = self.small_font.render(label, True, PALETTE["text"])
            box = pygame.Rect(0, 0, text.get_width() + 10, text.get_height() + 4)
            box.midbottom = (animated_pos.x, animated_pos.y - radius * 2.18)
            pygame.draw.rect(self.screen, (18, 24, 26), box, border_radius=8)
            pygame.draw.rect(self.screen, PALETTE["ui_line"], box, 1, border_radius=8)
            self.screen.blit(text, text.get_rect(center=box.center))

    def draw_role_tool(self, hand_pos: Vector2, role: str, scale: float, accent: tuple[int, int, int]) -> None:
        if role == "lenhador":
            pygame.draw.line(self.screen, (106, 82, 58), hand_pos + Vector2(-1 * scale, -6 * scale), hand_pos + Vector2(6 * scale, 5 * scale), max(2, int(2 * scale)))
            head = [hand_pos + Vector2(2 * scale, -7 * scale), hand_pos + Vector2(8 * scale, -4 * scale), hand_pos + Vector2(4 * scale, 0)]
            pygame.draw.polygon(self.screen, (136, 142, 148), head)
        elif role == "vigia":
            pygame.draw.line(self.screen, (118, 108, 88), hand_pos + Vector2(0, -8 * scale), hand_pos + Vector2(0, 6 * scale), max(2, int(2 * scale)))
            tip = [hand_pos + Vector2(0, -11 * scale), hand_pos + Vector2(-3 * scale, -5 * scale), hand_pos + Vector2(3 * scale, -5 * scale)]
            pygame.draw.polygon(self.screen, (162, 176, 184), tip)
        elif role == "batedora":
            lens_left = hand_pos + Vector2(-3 * scale, -2 * scale)
            lens_right = hand_pos + Vector2(3 * scale, -2 * scale)
            pygame.draw.circle(self.screen, (86, 96, 108), (int(lens_left.x), int(lens_left.y)), max(2, int(2 * scale)))
            pygame.draw.circle(self.screen, (86, 96, 108), (int(lens_right.x), int(lens_right.y)), max(2, int(2 * scale)))
            pygame.draw.line(self.screen, (66, 74, 84), lens_left + Vector2(2 * scale, 0), lens_right - Vector2(2 * scale, 0), 1)
        elif role == "artesa":
            pygame.draw.line(self.screen, (122, 92, 64), hand_pos + Vector2(-1 * scale, -5 * scale), hand_pos + Vector2(5 * scale, 4 * scale), max(2, int(2 * scale)))
            pygame.draw.rect(
                self.screen,
                (128, 132, 138),
                pygame.Rect(int(hand_pos.x + 2 * scale), int(hand_pos.y - 8 * scale), max(4, int(5 * scale)), max(3, int(4 * scale))),
                border_radius=2,
            )
        elif role == "cozinheiro":
            pygame.draw.line(self.screen, (132, 116, 92), hand_pos + Vector2(-1 * scale, -6 * scale), hand_pos + Vector2(5 * scale, 5 * scale), max(2, int(2 * scale)))
            pygame.draw.circle(self.screen, (92, 104, 114), (int(hand_pos.x + 6 * scale), int(hand_pos.y - 5 * scale)), max(2, int(2 * scale)))
        elif role == "mensageiro":
            bag = pygame.Rect(0, 0, max(5, int(7 * scale)), max(6, int(8 * scale)))
            bag.center = (int(hand_pos.x + 4 * scale), int(hand_pos.y - 1 * scale))
            pygame.draw.rect(self.screen, (96, 78, 116), bag, border_radius=2)
            pygame.draw.rect(self.screen, tuple(max(0, c - 28) for c in accent), bag, 1, border_radius=2)

    def draw_face(self, center: Vector2, scale: float, expression: str, *, zombie: bool = False) -> None:
        eye_color = (30, 26, 22) if not zombie else (40, 54, 34)
        mouth_color = (96, 72, 54) if not zombie else (62, 84, 58)
        brow_color = (72, 54, 38) if not zombie else (56, 78, 52)
        eye_y = center.y - 2 * scale
        left_eye = Vector2(center.x - 3 * scale, eye_y)
        right_eye = Vector2(center.x + 3 * scale, eye_y)
        eye_radius = max(1, int(1.15 * scale))

        pygame.draw.circle(self.screen, eye_color, (int(left_eye.x), int(left_eye.y)), eye_radius)
        pygame.draw.circle(self.screen, eye_color, (int(right_eye.x), int(right_eye.y)), eye_radius)

        if expression in {"focado", "agressivo", "irritado"}:
            pygame.draw.line(self.screen, brow_color, left_eye + Vector2(-2 * scale, -2 * scale), left_eye + Vector2(2 * scale, -1 * scale), 1)
            pygame.draw.line(self.screen, brow_color, right_eye + Vector2(-2 * scale, -1 * scale), right_eye + Vector2(2 * scale, -2 * scale), 1)
            pygame.draw.line(self.screen, mouth_color, center + Vector2(-2.2 * scale, 4 * scale), center + Vector2(2.2 * scale, 4 * scale), 1)
        elif expression in {"triste", "ferido"}:
            pygame.draw.line(self.screen, brow_color, left_eye + Vector2(-2 * scale, -1 * scale), left_eye + Vector2(2 * scale, -2 * scale), 1)
            pygame.draw.line(self.screen, brow_color, right_eye + Vector2(-2 * scale, -2 * scale), right_eye + Vector2(2 * scale, -1 * scale), 1)
            pygame.draw.arc(
                self.screen,
                mouth_color,
                pygame.Rect(center.x - 4 * scale, center.y + 2.8 * scale, 8 * scale, 5 * scale),
                3.35,
                6.05,
                1,
            )
        elif expression == "cansado":
            pygame.draw.line(self.screen, brow_color, left_eye + Vector2(-2 * scale, -1 * scale), left_eye + Vector2(2 * scale, -1 * scale), 1)
            pygame.draw.line(self.screen, brow_color, right_eye + Vector2(-2 * scale, -1 * scale), right_eye + Vector2(2 * scale, -1 * scale), 1)
            pygame.draw.line(self.screen, mouth_color, center + Vector2(-2.4 * scale, 4.2 * scale), center + Vector2(2.4 * scale, 4.2 * scale), 1)
        elif expression == "assustado":
            pygame.draw.circle(self.screen, eye_color, (int(left_eye.x), int(left_eye.y)), max(1, int(1.5 * scale)))
            pygame.draw.circle(self.screen, eye_color, (int(right_eye.x), int(right_eye.y)), max(1, int(1.5 * scale)))
            pygame.draw.circle(self.screen, mouth_color, (int(center.x), int(center.y + 4 * scale)), max(1, int(1.2 * scale)), 1)
        elif expression == "sorrindo":
            pygame.draw.arc(
                self.screen,
                mouth_color,
                pygame.Rect(center.x - 4 * scale, center.y + 1.4 * scale, 8 * scale, 6 * scale),
                0.15,
                2.95,
                1,
            )
        else:
            pygame.draw.arc(
                self.screen,
                mouth_color,
                pygame.Rect(center.x - 4 * scale, center.y + 2.1 * scale, 8 * scale, 5 * scale),
                0.2,
                2.9,
                1,
            )

    def survivor_expression(self, survivor: Survivor) -> str:
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

    def draw_survivor_bark(self, pos: Vector2, survivor: Survivor) -> None:
        bark_text = str(getattr(survivor, "bark_text", "")).strip()
        bark_timer = float(getattr(survivor, "bark_timer", 0.0))
        if not bark_text or bark_timer <= 0:
            return
        color = tuple(getattr(survivor, "bark_color", PALETTE["text"]))
        alpha_ratio = clamp(bark_timer / 2.6, 0, 1)
        lines = self.wrap_text_lines(self.ui_small_font, bark_text, 140)
        text_surfaces = [self.ui_small_font.render(line, True, color) for line in lines]
        width = max(surface.get_width() for surface in text_surfaces) + 18
        height = len(text_surfaces) * self.ui_small_font.get_linesize() + max(0, len(text_surfaces) - 1) * 2 + 12
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
            text_y += self.ui_small_font.get_linesize() + 2
        bubble_pos = pos - Vector2(width / 2, 58 + height)
        self.screen.blit(bubble, bubble_pos)

    def draw_status_orb(self, pos: Vector2, survivor: Survivor) -> None:
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
        pygame.draw.circle(self.screen, (18, 24, 24), orb_pos, 8)
        pygame.draw.circle(self.screen, color, orb_pos, 5)

    def draw_zombie_weapon(self, pos: Vector2, zombie: Zombie) -> None:
        if zombie.weapon_name == "cano":
            pygame.draw.line(self.screen, (112, 118, 126), pos + Vector2(2, -8), pos + Vector2(18, 8), 4)
        elif zombie.weapon_name == "machado":
            pygame.draw.line(self.screen, (108, 84, 56), pos + Vector2(0, -6), pos + Vector2(14, 10), 3)
            pygame.draw.polygon(
                self.screen,
                (164, 168, 172),
                [pos + Vector2(12, 6), pos + Vector2(22, 2), pos + Vector2(18, 12)],
            )
        elif zombie.weapon_name == "barra":
            pygame.draw.line(self.screen, (134, 114, 90), pos + Vector2(-2, -8), pos + Vector2(14, 12), 3)

    def draw_particles(self, shake_offset: Vector2) -> None:
        for pulse in self.damage_pulses:
            pos = self.world_to_screen(pulse.pos) + shake_offset
            alpha = int(180 * pulse.life / 0.28)
            surface = pygame.Surface((160, 160), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*pulse.color, alpha), (80, 80), int(pulse.radius), 3)
            self.screen.blit(surface, pos - Vector2(80, 80))

        for ember in self.embers:
            pos = self.world_to_screen(ember.pos) + shake_offset
            if pos.x < -20 or pos.x > SCREEN_WIDTH + 20 or pos.y < -20 or pos.y > SCREEN_HEIGHT + 20:
                continue
            alpha = int(190 * clamp(ember.life, 0, 1))
            surface = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*ember.color, alpha), (12, 12), int(ember.radius))
            self.screen.blit(surface, pos - Vector2(12, 12))

        for floating in self.floating_texts:
            pos = self.world_to_screen(floating.pos) + shake_offset
            alpha = int(255 * clamp(floating.life / 1.2, 0, 1))
            text = self.small_font.render(floating.text, True, floating.color)
            text.set_alpha(alpha)
            self.screen.blit(text, text.get_rect(center=(pos.x, pos.y)))

    def draw_fog(self, shake_offset: Vector2) -> None:
        fog_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        darkness = self.visual_darkness_factor()
        cloud_cover = self.weather_cloud_cover()
        factor = (0.09 + darkness * 0.24 + cloud_cover * 0.08) * float(self.runtime_settings.get("fog_strength", 1.0))
        for mote in self.fog_motes:
            pos = self.world_to_screen(mote.pos) + shake_offset
            if pos.x < -220 or pos.x > SCREEN_WIDTH + 220 or pos.y < -220 or pos.y > SCREEN_HEIGHT + 220:
                continue
            pygame.draw.circle(
                fog_surface,
                (*PALETTE["fog"], int(mote.alpha * factor)),
                (int(pos.x), int(pos.y)),
                int(mote.radius),
            )
        self.screen.blit(fog_surface, (0, 0))

    def carve_map_visibility(self, overlay: pygame.Surface, center: Vector2, radius: float) -> None:
        diameter = max(4, int(radius * 2.3))
        reveal = self.map_reveal_cache.get(diameter)
        if reveal is None:
            reveal = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
            center_xy = (diameter // 2, diameter // 2)
            pygame.draw.circle(reveal, (0, 0, 0, 220), center_xy, int(radius * 0.9))
            self.map_reveal_cache[diameter] = reveal
        reveal_center = Vector2(reveal.get_width() / 2, reveal.get_height() / 2)
        top_left = center - reveal_center
        overlay.blit(reveal, (int(top_left.x), int(top_left.y)), special_flags=pygame.BLEND_RGBA_SUB)

    def draw_map_fog(self, shake_offset: Vector2) -> None:
        view_rect = pygame.Rect(int(self.camera.x), int(self.camera.y), SCREEN_WIDTH, SCREEN_HEIGHT)
        fog_overlay = self.map_fog_overlay_surface
        if fog_overlay is None or fog_overlay.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            fog_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self.map_fog_overlay_surface = fog_overlay
        fog_strength = clamp(float(self.runtime_settings.get("fog_strength", 1.0)), 0.2, 1.25)
        fog_overlay.fill((0, 0, 0, int(224 * fog_strength)))

        for center, radius in self.visible_fog_reveals(view_rect):
            self.carve_map_visibility(fog_overlay, self.world_to_screen(center), radius)

        self.screen.blit(fog_overlay, (0, 0))

    def draw_lighting(self) -> None:
        darkness_factor = self.visual_darkness_factor()
        cloud_cover = self.weather_cloud_cover()
        daylight = self.daylight_factor()
        storm = self.weather_storm_factor()
        darkness = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        darkness.fill((*PALETTE["night"], int(12 + darkness_factor * 126)))
        if cloud_cover > 0.12:
            cloud_tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            cloud_tint.fill((38, 46, 52, int((4 + cloud_cover * 14 + storm * 6) * max(0.16, daylight * 0.75))))
            darkness.blit(cloud_tint, (0, 0))
        self.screen.blit(darkness, (0, 0))

        light_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fire_pos = self.world_to_screen(self.bonfire_pos)
        glow = self.bonfire_heat * 0.68 + self.bonfire_ember_bed * 0.32
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

        self.screen.blit(light_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        weather_flash = float(getattr(self, "weather_flash", 0.0))
        if weather_flash > 0.01:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((190, 210, 224, int(22 + weather_flash * 54)))
            self.screen.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, int(4 + darkness_factor * 24 + cloud_cover * 5 + storm * 4)), vignette.get_rect(), border_radius=22)
        self.screen.blit(vignette, (0, 0))

    def draw_chat_panel(self) -> None:
        hud_rendering_helpers.draw_chat_panel(self)

    def draw_hud(self) -> None:
        hud_rendering_helpers.draw_hud(self)

    def draw_build_preview(self, shake_offset: Vector2) -> None:
        recipe = self.selected_build_recipe()
        build_pos = self.building_center_snapped(self.screen_to_world(self.input_state.mouse_screen))
        screen_pos = self.world_to_screen(build_pos) + shake_offset
        size = float(recipe["size"])
        valid = self.is_valid_build_position(str(recipe["kind"]), build_pos)
        color = PALETTE["heal"] if valid else PALETTE["danger_soft"]
        footprint = pygame.Rect(0, 0, int(size * 1.8), int(size * 1.34))
        footprint.center = (int(screen_pos.x), int(screen_pos.y + 4))
        preview = pygame.Surface((footprint.width + 40, footprint.height + 48), pygame.SRCALPHA)
        inner = pygame.Rect(20, 12, footprint.width, footprint.height)
        pygame.draw.rect(preview, (*color, 28), inner, border_radius=16)
        pygame.draw.rect(preview, (*color, 138), inner, 2, border_radius=16)
        pygame.draw.ellipse(preview, (8, 12, 12, 64), pygame.Rect(inner.x + 8, inner.bottom - 4, inner.width - 16, 18))
        self.screen.blit(preview, (footprint.x - 20, footprint.y - 12))
        label = self.small_font.render(recipe["label"], True, color)
        hint = self.small_font.render("Clique para erguer" if valid else "Espaco ocupado", True, PALETTE["muted"])
        label_box = pygame.Rect(0, 0, max(label.get_width(), hint.get_width()) + 14, label.get_height() + hint.get_height() + 10)
        label_box.midbottom = (int(screen_pos.x), int(footprint.y - 8))
        pygame.draw.rect(self.screen, (16, 22, 24, 0), label_box, border_radius=10)
        pygame.draw.rect(self.screen, (18, 24, 26), label_box, border_radius=10)
        pygame.draw.rect(self.screen, color, label_box, 1, border_radius=10)
        self.screen.blit(label, label.get_rect(midtop=(label_box.centerx, label_box.y + 3)))
        self.screen.blit(hint, hint.get_rect(midtop=(label_box.centerx, label_box.y + 3 + label.get_height())))

    def draw_build_menu(self) -> None:
        panel_height = 78 + len(self.build_recipes) * 38
        panel = pygame.Rect(SCREEN_WIDTH - 346, SCREEN_HEIGHT - panel_height - 18, 328, panel_height)
        self.draw_panel(panel)
        title = self.heading_font.render("Menu de Construcao", True, PALETTE["text"])
        subtitle = self.small_font.render(
            f"B abre/fecha  |  1-7 seleciona  |  fase {self.economy_phase_label()}",
            True,
            PALETTE["muted"],
        )
        self.screen.blit(title, (panel.x + 18, panel.y + 14))
        self.screen.blit(subtitle, (panel.x + 18, panel.y + 42))

        for index, recipe in enumerate(self.build_recipes, start=1):
            rect = pygame.Rect(panel.x + 16, panel.y + 66 + (index - 1) * 38, 296, 32)
            wood_cost, scrap_cost = self.build_cost_for(recipe)
            affordable = self.wood >= wood_cost and self.scrap >= scrap_cost
            active = self.selected_build_slot == index
            base_color = (42, 55, 58) if active else PALETTE["ui_panel"]
            pygame.draw.rect(self.screen, base_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], rect, 1, border_radius=10)
            label = self.body_font.render(f"{index}. {recipe['label']}", True, PALETTE["text"])
            cost = self.small_font.render(
                f"{wood_cost} tabuas  |  {scrap_cost} sucata  |  {recipe['hint']}",
                True,
                PALETTE["muted"] if affordable else PALETTE["danger_soft"],
            )
            self.screen.blit(label, (rect.x + 10, rect.y + 4))
            self.screen.blit(cost, (rect.x + 10, rect.y + 18))

    def draw_panel(self, rect: pygame.Rect, *, alpha_scale: float = 1.0) -> None:
        hud_rendering_helpers.draw_panel(self, rect, alpha_scale=alpha_scale)

    def draw_resource_meter(
        self,
        x: int,
        y: int,
        width: int,
        value: int,
        label: str,
        color: tuple[int, int, int],
    ) -> None:
        hud_rendering_helpers.draw_resource_meter(self, x, y, width, value, label, color)

    def draw_resource_bar(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        ratio: float,
        label: str,
        color: tuple[int, int, int],
    ) -> None:
        hud_rendering_helpers.draw_resource_bar(self, x, y, width, height, ratio, label, color)

    def draw_survivor_card(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        survivor: Survivor,
    ) -> None:
        hud_rendering_helpers.draw_survivor_card(self, x, y, width, height, survivor)

    def current_objectives(self) -> list[str]:
        return hud_rendering_helpers.current_objectives(self)

    def draw_title_screen(self) -> None:
        layout = self.title_ui_layout()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 10, 12, 112))
        self.screen.blit(overlay, (0, 0))

        mist = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for index in range(4):
            band = pygame.Rect(0, 80 + index * 160, SCREEN_WIDTH, 120)
            pygame.draw.ellipse(mist, (12, 16, 18, 34), band.inflate(180, 60))
        self.screen.blit(mist, (0, 0))

        panel = layout["panel"]
        frame = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(frame, (8, 12, 14, 132), frame.get_rect(), border_radius=28)
        pygame.draw.rect(frame, (124, 96, 70, 70), frame.get_rect(), 1, border_radius=28)
        self.screen.blit(frame, panel.topleft)

        title = self.title_font.render("Fogueira do Fim", True, PALETTE["text"])
        subtitle = self.body_font.render(
            "Sociedade, acampamento e zumbis em um mundo procedural hostil.",
            True,
            PALETTE["accent_soft"],
        )
        self.screen.blit(title, (panel.x + 38, panel.y + 34))
        self.screen.blit(subtitle, (panel.x + 42, panel.y + 96))
        live_tag = self.ui_small_font.render("Simulacao viva ao fundo", True, PALETTE["morale"])
        self.screen.blit(live_tag, (panel.right - live_tag.get_width() - 40, panel.y + 48))

        left_card = layout["left_card"]
        self.draw_panel(left_card, alpha_scale=0.7)
        section = self.heading_font.render("Noite Sobre a Clareira", True, PALETTE["text"])
        self.screen.blit(section, (left_card.x + 20, left_card.y + 18))
        pitch_lines = [
            "Ao fundo, o campo continua respirando: sobreviventes rondam, fogo pulsa e a floresta nunca dorme.",
            "Voce lidera gente exausta no meio da mata, administrando sono, fome, medo e lealdade.",
            "A base cresce por barracas, oficinas, barricadas e expedicoes para muito alem da primeira linha de arvores.",
            "Cada noite cobra leitura social e defesa; cada dia cobra recurso, risco e presenca.",
        ]
        paragraph_y = left_card.y + 64
        text_width = left_card.width - 40
        for line in pitch_lines:
            paragraph_y = self.draw_wrapped_text(
                self.body_font,
                line,
                PALETTE["text"],
                left_card.x + 20,
                paragraph_y,
                text_width,
                line_gap=4,
            ) + 12

        feature_box = pygame.Rect(left_card.x + 18, left_card.bottom - 126, left_card.width - 36, 92)
        pygame.draw.rect(self.screen, PALETTE["ui_panel"], feature_box, border_radius=14)
        pygame.draw.rect(self.screen, PALETTE["ui_line"], feature_box, 1, border_radius=14)
        feature_lines = [
            "Comece um novo turno, revise o ultimo save ou ajuste a apresentacao antes de entrar.",
            "Ao iniciar um jogo novo, uma sequencia curta de dicas aparece e pode ser pulada a qualquer momento.",
        ]
        feature_y = feature_box.y + 16
        for index, line in enumerate(feature_lines):
            feature_y = self.draw_wrapped_text(
                self.ui_small_font,
                line,
                PALETTE["muted"] if index == 0 else PALETTE["accent_soft"],
                feature_box.x + 14,
                feature_y,
                feature_box.width - 28,
                line_gap=2,
            ) + 6

        right_card = layout["right_card"]
        self.draw_panel(right_card, alpha_scale=0.7)
        mouse_pos = self.input_state.mouse_screen if hasattr(self, "input_state") else Vector2()
        menu_title = self.heading_font.render("Entrada da Clareira", True, PALETTE["text"])
        self.screen.blit(menu_title, (right_card.x + 20, right_card.y + 18))
        self.draw_wrapped_text(
            self.ui_small_font,
            "Tela cheia, mouse ativo e simulacao viva atras do menu principal.",
            PALETTE["muted"],
            right_card.x + 20,
            right_card.y + 48,
            right_card.width - 40,
            line_gap=2,
        )

        if not self.title_settings_open:
            for index, action in enumerate(self.title_actions):
                row = layout["action_rows"][index]
                active = self.title_action_index == index or row.collidepoint(mouse_pos)
                pygame.draw.rect(self.screen, (52, 68, 72) if active else PALETTE["ui_panel"], row, border_radius=14)
                pygame.draw.rect(self.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], row, 1, border_radius=14)
                label = self.body_font.render(action, True, PALETTE["text"])
                if action == "Continuar":
                    prompt_text = "Retomar o ultimo acampamento salvo."
                elif action == "Novo Jogo":
                    prompt_text = "Entrar na clareira."
                elif action == "Configuracoes":
                    prompt_text = "Abrir a aba de ajustes."
                else:
                    prompt_text = "Fechar a sessao."
                self.screen.blit(label, (row.x + 16, row.y + 9))
                self.draw_wrapped_text(
                    self.ui_small_font,
                    prompt_text,
                    PALETTE["muted"],
                    row.x + 16,
                    row.y + 27,
                    row.width - 32,
                    line_gap=0,
                )
        else:
            settings_panel = layout["settings_panel"]
            self.draw_panel(settings_panel)
            settings_title = self.heading_font.render("Configuracoes", True, PALETTE["text"])
            settings_subtitle = self.ui_small_font.render(
                "Clique em - e + ou use A e D para ajustar a linha marcada.",
                True,
                PALETTE["muted"],
            )
            back_hover = layout["settings_back"].collidepoint(mouse_pos)
            pygame.draw.rect(
                self.screen,
                (70, 84, 88) if back_hover else PALETTE["ui_panel"],
                layout["settings_back"],
                border_radius=10,
            )
            pygame.draw.rect(self.screen, PALETTE["ui_line"], layout["settings_back"], 1, border_radius=10)
            back_text = self.ui_small_font.render("Voltar", True, PALETTE["text"])
            self.screen.blit(settings_title, (settings_panel.x + 18, settings_panel.y + 16))
            self.screen.blit(settings_subtitle, (settings_panel.x + 18, settings_panel.y + 46))
            self.screen.blit(back_text, back_text.get_rect(center=layout["settings_back"].center))

            for index, ((key, label, _, _, _), item) in enumerate(zip(self.title_setting_entries, layout["setting_rows"])):
                row = item["row"]
                active = self.title_setting_index == index or row.collidepoint(mouse_pos)
                pygame.draw.rect(self.screen, (44, 58, 62) if active else PALETTE["ui_panel"], row, border_radius=12)
                pygame.draw.rect(self.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], row, 1, border_radius=12)
                minus_hover = item["minus"].collidepoint(mouse_pos)
                plus_hover = item["plus"].collidepoint(mouse_pos)
                pygame.draw.rect(self.screen, (70, 84, 88) if minus_hover else (54, 66, 70), item["minus"], border_radius=7)
                pygame.draw.rect(self.screen, (70, 84, 88) if plus_hover else (54, 66, 70), item["plus"], border_radius=7)
                pygame.draw.rect(self.screen, PALETTE["ui_line"], item["minus"], 1, border_radius=7)
                pygame.draw.rect(self.screen, PALETTE["ui_line"], item["plus"], 1, border_radius=7)
                pygame.draw.rect(self.screen, (32, 40, 42), item["value"], border_radius=7)
                pygame.draw.rect(self.screen, PALETTE["ui_line"], item["value"], 1, border_radius=7)
                left = self.ui_small_font.render(label, True, PALETTE["text"])
                value = self.ui_small_font.render(self.title_setting_value_label(str(key)), True, PALETTE["morale"] if active else PALETTE["text"])
                minus = self.body_font.render("-", True, PALETTE["text"])
                plus = self.body_font.render("+", True, PALETTE["text"])
                self.screen.blit(left, (row.x + 12, row.y + 5))
                self.screen.blit(value, value.get_rect(center=item["value"].center))
                self.screen.blit(minus, minus.get_rect(center=item["minus"].center))
                self.screen.blit(plus, plus.get_rect(center=item["plus"].center))

        footer_text = (
            self.event_message
            if getattr(self, "event_timer", 0) > 0
            else "Enter confirma  |  Esc fecha  |  Novo Jogo abre as dicas antes da vigia."
        )
        footer_width = panel.width - 160
        footer_lines = self.wrap_text_lines(self.ui_small_font, footer_text, footer_width)
        footer_line_height = self.ui_small_font.get_linesize()
        footer_total = len(footer_lines) * footer_line_height + max(0, len(footer_lines) - 1) * 2
        footer_y = panel.bottom - 26 - footer_total
        for index, line in enumerate(footer_lines):
            footer = self.ui_small_font.render(line, True, PALETTE["muted"])
            self.screen.blit(footer, footer.get_rect(center=(panel.centerx, footer_y + index * (footer_line_height + 2) + footer_line_height // 2)))

    def draw_tips_screen(self) -> None:
        layout = self.tips_ui_layout()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 10, 12, 124))
        self.screen.blit(overlay, (0, 0))

        panel = layout["panel"]
        self.draw_panel(panel)
        page = self.tutorial_pages[self.tips_index]
        mouse_pos = self.input_state.mouse_screen if hasattr(self, "input_state") else Vector2()
        next_hover = layout["next_button"].collidepoint(mouse_pos)
        skip_hover = layout["skip_button"].collidepoint(mouse_pos)
        last_page = self.tips_index >= len(self.tutorial_pages) - 1

        eyebrow = self.small_font.render(str(page["eyebrow"]).upper(), True, PALETTE["morale"])
        title = self.title_font.render(str(page["title"]), True, PALETTE["text"])
        body = self.body_font.render(str(page["body"]), True, PALETTE["accent_soft"])
        self.screen.blit(eyebrow, (panel.x + 42, panel.y + 24))
        self.screen.blit(title, (panel.x + 38, panel.y + 52))
        self.screen.blit(body, (panel.x + 44, panel.y + 118))

        content = layout["content"]
        box = pygame.Rect(content.x, content.y + 18, content.width, content.height - 36)
        pygame.draw.rect(self.screen, (24, 32, 34), box, border_radius=22)
        pygame.draw.rect(self.screen, PALETTE["ui_line"], box, 1, border_radius=22)
        hint = self.small_font.render(
            "Dicas essenciais para entrar na primeira vigia. Enter avanca, Esc pula.",
            True,
            PALETTE["muted"],
        )
        self.screen.blit(hint, (box.x + 22, box.y + 18))

        for index, bullet in enumerate(page["bullets"]):
            pill = pygame.Rect(box.x + 20, box.y + 56 + index * 72, box.width - 40, 52)
            pygame.draw.rect(self.screen, PALETTE["ui_panel"], pill, border_radius=16)
            pygame.draw.rect(self.screen, PALETTE["accent_soft"] if index == self.tips_index else PALETTE["ui_line"], pill, 1, border_radius=16)
            num = self.body_font.render(f"{index + 1}", True, PALETTE["morale"])
            text = self.body_font.render(str(bullet), True, PALETTE["text"])
            self.screen.blit(num, (pill.x + 16, pill.y + 14))
            self.screen.blit(text, (pill.x + 44, pill.y + 14))

        for index in range(len(self.tutorial_pages)):
            color = PALETTE["accent_soft"] if index == self.tips_index else (68, 82, 86)
            pygame.draw.circle(self.screen, color, (panel.x + 52 + index * 20, panel.bottom - 44), 5)

        for rect, label, hover in (
            (layout["next_button"], "Entrar no Jogo" if last_page else "Proxima", next_hover),
            (layout["skip_button"], "Pular Dicas", skip_hover),
        ):
            pygame.draw.rect(self.screen, (62, 80, 84) if hover else PALETTE["ui_panel"], rect, border_radius=14)
            pygame.draw.rect(self.screen, PALETTE["accent_soft"] if hover else PALETTE["ui_line"], rect, 1, border_radius=14)
            text = self.body_font.render(label, True, PALETTE["text"])
            self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_game_over(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((18, 6, 8, 182))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(0, 0, 620, 260)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.draw_panel(panel)
        title = self.title_font.render("O campo caiu", True, PALETTE["danger_soft"])
        subtitle = self.body_font.render(
            "A fogueira se apagou, a moral quebrou ou o chefe nao resistiu.",
            True,
            PALETTE["text"],
        )
        retry = self.body_font.render("Pressione Enter para recomecar a vigia.", True, PALETTE["morale"])
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 78)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.y + 136)))
        self.screen.blit(retry, retry.get_rect(center=(panel.centerx, panel.y + 188)))

    def draw_exit_prompt(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 6, 8, 186))
        self.screen.blit(overlay, (0, 0))
        layout = self.exit_prompt_layout()
        panel = layout["panel"]
        self.draw_panel(panel)
        title = self.heading_font.render("Sair da vigia?", True, PALETTE["text"])
        self.screen.blit(title, (panel.x + 26, panel.y + 18))

        subtitle_y = self.draw_wrapped_text(
            self.body_font,
            "Escolha se quer salvar antes de fechar o jogo.",
            PALETTE["muted"],
            panel.x + 26,
            panel.y + 58,
            panel.width - 52,
            line_gap=2,
        )
        self.draw_wrapped_text(
            self.ui_small_font,
            "Enter confirma  |  Esc cancela",
            PALETTE["accent_soft"],
            panel.x + 26,
            subtitle_y + 8,
            panel.width - 52,
            line_gap=0,
        )

        mouse_pos = self.input_state.mouse_screen
        for index, (rect, label) in enumerate(zip(layout["buttons"], self.exit_prompt_options)):
            active = self.exit_prompt_index == index or rect.collidepoint(mouse_pos)
            fill = (70, 88, 92) if active else (34, 47, 50)
            pygame.draw.rect(self.screen, fill, rect, border_radius=14)
            pygame.draw.rect(self.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], rect, 1, border_radius=14)
            text = self.body_font.render(self.fit_text_to_width(self.body_font, label, rect.width - 28), True, PALETTE["text"])
            self.screen.blit(text, text.get_rect(center=rect.center))
