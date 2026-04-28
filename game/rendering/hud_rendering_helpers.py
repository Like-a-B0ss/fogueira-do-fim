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
    capacity: int | None = None,
) -> None:
    rect = pygame.Rect(x, y, width, 38)
    pygame.draw.rect(game.screen, PALETTE["ui_panel"], rect, border_radius=12)
    pygame.draw.rect(game.screen, (18, 22, 24), rect.inflate(-2, -2), 1, border_radius=12)
    pygame.draw.rect(game.screen, color, pygame.Rect(rect.right - 16, y + 7, 8, 8), border_radius=3)

    text_width = width - 16
    label_text = game.fit_text_to_width(game.small_font, label, text_width - 12)
    label_surface = game.small_font.render(label_text, True, PALETTE["muted"])
    if capacity is None:
        value_text = str(value)
        value_font = game.body_font
    else:
        value_text = str(value) if capacity >= 999 else f"{value}/{capacity}"
        value_font = game.small_font
    if value_font.size(value_text)[0] > text_width:
        value_text = str(value)
    value_text = game.fit_text_to_width(value_font, value_text, text_width)
    value_surface = value_font.render(value_text, True, PALETTE["text"])

    game.screen.blit(label_surface, (x + 8, y + 5))
    game.screen.blit(value_surface, (x + 8, y + 19))


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
