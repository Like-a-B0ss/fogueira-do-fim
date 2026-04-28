from __future__ import annotations

import math

import pygame
from pygame import Vector2

from . import entity_rendering
from . import hud_rendering_helpers
from . import ui_build_rendering
from . import world_base_rendering
from . import ui_screen_rendering
from . import world_overlay_rendering
from . import world_resource_rendering
from . import world_scenery_rendering
from . import world_signals_rendering
from ..application import title_flow
from ..entities import Survivor, Zombie
from ..core.config import (
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
    """Utilitários de renderização com lógica realizada no mixin."""
    
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
        """Orquestra a renderização de todos os subsistemas."""
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
        world_base_rendering.draw_procedural_ground(self, shake_offset)
        terrain_offset = (
            int(round(-self.camera.x + shake_offset.x)),
            int(round(-self.camera.y + shake_offset.y)),
        )
        self.screen.blit(self.terrain_surface, terrain_offset)

        world_base_rendering.draw_world_features(self, shake_offset)
        world_scenery_rendering.draw_camp(self, shake_offset)
        world_scenery_rendering.draw_buildings(self, shake_offset)
        world_resource_rendering.draw_resource_nodes(self, shake_offset)
        world_resource_rendering.draw_barricades(self, shake_offset)
        world_signals_rendering.draw_interest_points(self, shake_offset)
        world_signals_rendering.draw_dynamic_events(self, shake_offset)
        entity_rendering.draw_entities(self, shake_offset)
        world_overlay_rendering.draw_weather_overlay(self, shake_offset)
        world_signals_rendering.draw_interaction_prompt(self, shake_offset)
        world_signals_rendering.draw_particles(self, shake_offset)
        world_overlay_rendering.draw_fog(self, shake_offset)
        world_overlay_rendering.draw_lighting(self)
        if self.player.hurt_flash > 0:
            hurt_overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            alpha = int(92 * clamp(self.player.hurt_flash / 0.42, 0, 1))
            hurt_overlay.fill((138, 28, 24, alpha))
            self.screen.blit(hurt_overlay, (0, 0))
        world_overlay_rendering.draw_map_fog(self, shake_offset)
        if self.scenes.is_gameplay():
            hud_rendering_helpers.draw_hud(self)
        if self.build_menu_open and self.scenes.is_gameplay():
            ui_build_rendering.draw_build_preview(self, shake_offset)
            ui_build_rendering.draw_build_menu(self)
        if self.controls_panel_open:
            title_flow.draw_controls_panel(self)
        if self.exit_prompt_open and self.scenes.is_gameplay():
            ui_screen_rendering.draw_exit_prompt(self)
        if self.gameplay_settings_open and self.scenes.is_gameplay():
            ui_screen_rendering.draw_runtime_settings_overlay(self)

        if self.scenes.is_splash():
            ui_screen_rendering.draw_splash_screen(self)
        elif self.scenes.is_title():
            ui_screen_rendering.draw_title_screen(self)
        elif self.scenes.is_loading():
            ui_screen_rendering.draw_loading_screen(self)
        elif self.scenes.is_tips():
            ui_screen_rendering.draw_tips_screen(self)
        elif self.scenes.is_game_over():
            ui_screen_rendering.draw_game_over(self)

        if getattr(self, "audio_debug_open", False):
            ui_screen_rendering.draw_audio_debug_overlay(self)

        if self.loading_overlay_active and not self.scenes.is_loading():
            self.update_loading_overlay_state()
            if self.loading_overlay_active:
                ui_screen_rendering.draw_loading_screen(
                    self,
                    alpha_override=int(self.loading_overlay_alpha),
                )

        pygame.display.flip()

    # Delegates para módulos de renderização - Mantidos para compatibilidade
    # TODO: Refatoração futura pode remover esses padrão-throughs se a lógica
    # de orquestração for movida para módulos específicos
    
    def draw_panel(self, rect: pygame.Rect, *, alpha_scale: float = 1.0) -> None:
        hud_rendering_helpers.draw_panel(self, rect, alpha_scale=alpha_scale)

    def draw_chat_panel(self) -> None:
        hud_rendering_helpers.draw_chat_panel(self)

    def draw_resource_meter(
        self,
        x: int,
        y: int,
        width: int,
        value: int,
        label: str,
        color: tuple[int, int, int],
        capacity: int | None = None,
    ) -> None:
        hud_rendering_helpers.draw_resource_meter(self, x, y, width, value, label, color, capacity)

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









