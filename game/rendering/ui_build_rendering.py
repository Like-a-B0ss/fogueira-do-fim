from __future__ import annotations

import pygame
from pygame import Vector2

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH
from ..ui.ui_helpers import HUD_MARGIN, HUD_SIDE_PANEL_WIDTH


def draw_build_preview(game, shake_offset: Vector2) -> None:
    recipe = game.selected_build_recipe()
    build_pos = game.building_center_snapped(game.screen_to_world(game.input_state.mouse_screen))
    screen_pos = game.world_to_screen(build_pos) + shake_offset
    size = float(recipe["size"])
    valid = game.is_valid_build_position(str(recipe["kind"]), build_pos)
    color = PALETTE["heal"] if valid else PALETTE["danger_soft"]
    footprint = pygame.Rect(0, 0, int(size * 1.8), int(size * 1.34))
    footprint.center = (int(screen_pos.x), int(screen_pos.y + 4))
    preview = pygame.Surface((footprint.width + 40, footprint.height + 48), pygame.SRCALPHA)
    inner = pygame.Rect(20, 12, footprint.width, footprint.height)
    pygame.draw.rect(preview, (*color, 28), inner, border_radius=16)
    pygame.draw.rect(preview, (*color, 138), inner, 2, border_radius=16)
    pygame.draw.ellipse(preview, (8, 12, 12, 64), pygame.Rect(inner.x + 8, inner.bottom - 4, inner.width - 16, 18))
    game.screen.blit(preview, (footprint.x - 20, footprint.y - 12))
    label = game.small_font.render(recipe["label"], True, color)
    hint = game.small_font.render("Clique para erguer" if valid else "Espaco ocupado", True, PALETTE["muted"])
    label_box = pygame.Rect(0, 0, max(label.get_width(), hint.get_width()) + 14, label.get_height() + hint.get_height() + 10)
    label_box.midbottom = (int(screen_pos.x), int(footprint.y - 8))
    pygame.draw.rect(game.screen, (16, 22, 24, 0), label_box, border_radius=10)
    pygame.draw.rect(game.screen, (18, 24, 26), label_box, border_radius=10)
    pygame.draw.rect(game.screen, color, label_box, 1, border_radius=10)
    game.screen.blit(label, label.get_rect(midtop=(label_box.centerx, label_box.y + 3)))
    game.screen.blit(hint, hint.get_rect(midtop=(label_box.centerx, label_box.y + 3 + label.get_height())))


def draw_build_menu(game) -> None:
    panel_height = 78 + len(game.build_recipes) * 38
    panel = pygame.Rect(
        SCREEN_WIDTH - HUD_SIDE_PANEL_WIDTH - HUD_MARGIN,
        SCREEN_HEIGHT - panel_height - HUD_MARGIN,
        HUD_SIDE_PANEL_WIDTH,
        panel_height,
    )
    game.draw_panel(panel)
    title = game.heading_font.render("Menu de Construcao", True, PALETTE["text"])
    subtitle = game.small_font.render(
        f"B abre/fecha  |  1-{len(game.build_recipes)} seleciona  |  fase {game.economy_phase_label()}",
        True,
        PALETTE["muted"],
    )
    game.screen.blit(title, (panel.x + 18, panel.y + 14))
    game.screen.blit(subtitle, (panel.x + 18, panel.y + 42))

    for index, recipe in enumerate(game.build_recipes, start=1):
        rect = pygame.Rect(panel.x + 16, panel.y + 66 + (index - 1) * 38, 296, 32)
        wood_cost, scrap_cost = game.build_cost_for(recipe)
        affordable = game.wood >= wood_cost and game.scrap >= scrap_cost
        active = game.selected_build_slot == index
        base_color = (42, 55, 58) if active else PALETTE["ui_panel"]
        pygame.draw.rect(game.screen, base_color, rect, border_radius=10)
        pygame.draw.rect(game.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], rect, 1, border_radius=10)
        label = game.body_font.render(f"{index}. {recipe['label']}", True, PALETTE["text"])
        cost = game.small_font.render(
            f"{wood_cost} tábuas  |  {scrap_cost} sucata  |  {recipe['hint']}",
            True,
            PALETTE["muted"] if affordable else PALETTE["danger_soft"],
        )
        game.screen.blit(label, (rect.x + 10, rect.y + 4))
        game.screen.blit(cost, (rect.x + 10, rect.y + 18))








