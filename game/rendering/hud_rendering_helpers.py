from __future__ import annotations

import pygame

from . import ui_hud_panels
from . import ui_hud_rendering
from ..entities import Survivor
from ..core.config import PALETTE, clamp


def draw_chat_panel(game) -> None:
    ui_hud_panels.draw_chat_panel(game)


def draw_hud(game) -> None:
    ui_hud_rendering.draw_hud(game)


def draw_panel(game, rect: pygame.Rect, *, alpha_scale: float = 1.0) -> None:
    """Desenha um painel base reutilizado por toda a interface."""
    panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    contrast = float(game.runtime_settings.get("ui_contrast", 1.0))
    alpha_scale = clamp(alpha_scale, 0.4, 1.2)
    bg_alpha = int(clamp((220 + (contrast - 1.0) * 56) * alpha_scale, 92, 250))
    line_alpha = int(clamp((126 + (contrast - 1.0) * 84) * alpha_scale, 56, 224))
    pygame.draw.rect(panel_surface, (*PALETTE["ui_bg"], bg_alpha), panel_surface.get_rect(), border_radius=18)
    pygame.draw.rect(panel_surface, (*PALETTE["ui_line"], line_alpha), panel_surface.get_rect(), 1, border_radius=18)
    game.screen.blit(panel_surface, rect.topleft)


def draw_resource_meter(
    game,
    x: int,
    y: int,
    width: int,
    value: int,
    label: str,
    color: tuple[int, int, int],
) -> None:
    rect = pygame.Rect(x, y, width, 36)
    pygame.draw.rect(game.screen, PALETTE["ui_panel"], rect, border_radius=12)
    pygame.draw.rect(game.screen, (18, 22, 24), pygame.Rect(x + 1, y + 1, width - 2, 34), 1, border_radius=12)
    pygame.draw.rect(game.screen, color, pygame.Rect(x + 8, y + 8, 20, 20), border_radius=7)
    label_surface = game.small_font.render(label, True, PALETTE["muted"])
    value_surface = game.body_font.render(str(value), True, PALETTE["text"])
    game.screen.blit(label_surface, (x + 36, y + 6))
    game.screen.blit(value_surface, (x + 36, y + 16))


def draw_resource_bar(
    game,
    x: int,
    y: int,
    width: int,
    height: int,
    ratio: float,
    label: str,
    color: tuple[int, int, int],
) -> None:
    ratio = clamp(ratio, 0, 1)
    label_surface = game.small_font.render(label, True, PALETTE["muted"])
    game.screen.blit(label_surface, (x, y - 18))
    pygame.draw.rect(game.screen, PALETTE["ui_panel"], (x, y, width, height), border_radius=8)
    pygame.draw.rect(game.screen, (18, 22, 24), (x, y, width, height), 1, border_radius=8)
    pygame.draw.rect(game.screen, color, (x, y, int(width * ratio), height), border_radius=8)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], (x, y, width, height), 1, border_radius=8)


def draw_survivor_card(
    game,
    x: int,
    y: int,
    width: int,
    height: int,
    survivor: Survivor,
) -> None:
    ui_hud_panels.draw_survivor_card(game, x, y, width, height, survivor)


def current_objectives(game) -> list[str]:
    return ui_hud_panels.current_objectives(game)








