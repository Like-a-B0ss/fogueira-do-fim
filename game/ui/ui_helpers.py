from __future__ import annotations

import pygame

from ..core.config import SCREEN_HEIGHT, SCREEN_WIDTH, clamp

HUD_MARGIN = 18
HUD_PANEL_GAP = 18
HUD_SIDE_PANEL_WIDTH = 328
HUD_LEFT_PANEL_WIDTH = 358


def title_ui_layout(game) -> dict[str, object]:
    """Define a geometria da tela inicial em um unico lugar."""
    panel = pygame.Rect(46, 42, SCREEN_WIDTH - 92, SCREEN_HEIGHT - 84)
    left_card = pygame.Rect(panel.x + 38, panel.y + 148, int(panel.width * 0.48), panel.height - 204)
    right_card = pygame.Rect(left_card.right + 28, panel.y + 148, panel.right - left_card.right - 66, panel.height - 204)
    action_rows = []
    if not game.title_settings_open:
        action_rows = [
            pygame.Rect(right_card.x + 20, right_card.y + 86 + index * 66, right_card.width - 40, 52)
            for index, _ in enumerate(game.title_actions)
        ]
    settings_panel = pygame.Rect(right_card.x + 20, right_card.y + 70, right_card.width - 40, right_card.height - 92)
    settings_back = pygame.Rect(settings_panel.right - 112, settings_panel.y + 14, 88, 34)
    setting_rows = []
    if game.title_settings_open:
        settings_top = settings_panel.y + 74
        for index, _entry in enumerate(game.title_setting_entries):
            row = pygame.Rect(settings_panel.x + 12, settings_top + index * 38, settings_panel.width - 24, 30)
            minus = pygame.Rect(row.right - 116, row.y + 4, 24, 22)
            plus = pygame.Rect(row.right - 30, row.y + 4, 24, 22)
            value_box = pygame.Rect(row.right - 88, row.y + 4, 50, 22)
            setting_rows.append({"row": row, "minus": minus, "plus": plus, "value": value_box})
    return {
        "panel": panel,
        "left_card": left_card,
        "right_card": right_card,
        "action_rows": action_rows,
        "settings_panel": settings_panel,
        "settings_back": settings_back,
        "setting_rows": setting_rows,
    }


def hud_toggle_rect(_game) -> pygame.Rect:
    return pygame.Rect(SCREEN_WIDTH // 2 + 240, HUD_MARGIN + 12, 28, 24)


def tips_ui_layout(_game) -> dict[str, pygame.Rect]:
    panel = pygame.Rect(0, 0, min(1120, SCREEN_WIDTH - 120), min(620, SCREEN_HEIGHT - 120))
    panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    content = pygame.Rect(panel.x + 42, panel.y + 92, panel.width - 84, panel.height - 188)
    skip_button = pygame.Rect(panel.right - 194, panel.bottom - 66, 150, 42)
    next_button = pygame.Rect(skip_button.x - 170, skip_button.y, 150, 42)
    return {
        "panel": panel,
        "content": content,
        "skip_button": skip_button,
        "next_button": next_button,
    }


def society_panel_layout(game) -> dict[str, pygame.Rect]:
    compact = bool(getattr(game, "hud_compact_mode", False))
    height = 92 if game.society_panel_collapsed or compact else 372
    panel = pygame.Rect(SCREEN_WIDTH - HUD_SIDE_PANEL_WIDTH - HUD_MARGIN, HUD_MARGIN, HUD_SIDE_PANEL_WIDTH, height)
    header = pygame.Rect(panel.x + 12, panel.y + 10, panel.width - 24, 54)
    toggle = pygame.Rect(panel.right - 38, panel.y + 16, 20, 20)
    viewport = pygame.Rect(panel.x + 16, panel.y + 106, 284, max(0, panel.height - 124))
    scrollbar = pygame.Rect(panel.right - 16, viewport.y, 8, viewport.height)
    return {
        "panel": panel,
        "header": header,
        "toggle": toggle,
        "viewport": viewport,
        "scrollbar": scrollbar,
    }


def society_card_height(game, survivor) -> int:
    selected = getattr(game, "society_selected_survivor_name", None) == getattr(survivor, "name", None)
    return 184 if selected else 72


def chat_panel_layout(_game) -> dict[str, pygame.Rect]:
    """Centraliza a geometria do painel inferior de conversa."""
    right_column_x = SCREEN_WIDTH - HUD_SIDE_PANEL_WIDTH - HUD_MARGIN
    panel_width = max(420, right_column_x - HUD_PANEL_GAP - HUD_MARGIN)
    panel = pygame.Rect(HUD_MARGIN, SCREEN_HEIGHT - 174, panel_width, 156)
    header = pygame.Rect(panel.x + 14, panel.y + 10, panel.width - 28, 26)
    viewport = pygame.Rect(panel.x + 14, panel.y + 42, panel.width - 36, 70)
    scrollbar = pygame.Rect(panel.right - 16, viewport.y, 8, viewport.height)
    buttons = []
    survivor = _game.active_dialog_survivor()
    option_count = len(_game.conversation_options_for_survivor(survivor)) if survivor else 0
    columns = 3 if option_count > 4 else 2
    button_gap = 6
    button_width = (panel.width - 28 - button_gap * (columns - 1)) // columns
    button_height = 22
    top = viewport.bottom + 8
    for index in range(max(4, option_count)):
        col = index % columns
        row = index // columns
        buttons.append(
            pygame.Rect(
                panel.x + 14 + col * (button_width + button_gap),
                top + row * (button_height + 8),
                button_width,
                button_height,
            )
        )
    return {
        "panel": panel,
        "header": header,
        "viewport": viewport,
        "scrollbar": scrollbar,
        "buttons": buttons,
    }


def society_card_step(game, survivor=None) -> int:
    if survivor is None:
        return 80
    return society_card_height(game, survivor) + 8


def society_content_height(game) -> int:
    if not game.survivors:
        return 0
    return sum(society_card_step(game, survivor) for survivor in game.survivors) - 8


def society_max_scroll(game) -> float:
    if game.society_panel_collapsed:
        return 0.0
    viewport = society_panel_layout(game)["viewport"]
    return max(0.0, float(society_content_height(game) - viewport.height))


def clamp_society_scroll(game) -> None:
    game.society_scroll = clamp(game.society_scroll, 0.0, society_max_scroll(game))


def adjust_society_scroll(game, delta: float) -> None:
    game.society_scroll = clamp(game.society_scroll + delta, 0.0, society_max_scroll(game))


def handle_chat_panel_input(game) -> bool:
    """Trata scroll do historico e clique nas opcoes de conversa direta."""
    if getattr(game, "hud_compact_mode", False) and not game.active_dialog_survivor():
        return False
    layout = game.chat_panel_layout()
    mouse_pos = game.input_state.mouse_screen
    panel_hit = layout["panel"].collidepoint(mouse_pos)
    if game.input_state.mouse_wheel_y and panel_hit:
        game.adjust_chat_scroll(-game.input_state.mouse_wheel_y * 36)
        return True
    if game.input_state.attack_pressed and panel_hit:
        if game.chat_max_scroll() > 0 and layout["scrollbar"].collidepoint(mouse_pos):
            track = layout["scrollbar"]
            ratio = clamp((mouse_pos.y - track.y) / max(1, track.height), 0.0, 1.0)
            game.chat_scroll = game.chat_max_scroll() * ratio
            game.audio.play_ui("focus")
            return True
        survivor = game.active_dialog_survivor()
        if survivor:
            for rect, option in zip(layout["buttons"], game.conversation_options_for_survivor(survivor)):
                if rect.collidepoint(mouse_pos):
                    game.execute_survivor_dialog_action(survivor, str(option["action"]))
                    return True
        return True

    return False


def handle_society_panel_input(game) -> bool:
    """Mantem a HUD social isolada do resto do clique do mundo."""
    layout = society_panel_layout(game)
    mouse_pos = game.input_state.mouse_screen
    effective_collapsed = game.society_panel_collapsed or bool(getattr(game, "hud_compact_mode", False))
    if game.input_state.mouse_wheel_y and not effective_collapsed and layout["panel"].collidepoint(mouse_pos):
        game.adjust_society_scroll(-game.input_state.mouse_wheel_y * 32)

    if not game.input_state.attack_pressed:
        return False

    if effective_collapsed:
        if getattr(game, "hud_compact_mode", False):
            return layout["panel"].collidepoint(mouse_pos)
        if layout["panel"].collidepoint(mouse_pos):
            game.society_panel_collapsed = False
            game.audio.play_ui("focus")
            return True
        return False

    if layout["header"].collidepoint(mouse_pos) or layout["toggle"].collidepoint(mouse_pos):
        game.society_panel_collapsed = True
        game.audio.play_ui("back")
        return True

    max_scroll = game.society_max_scroll()
    if max_scroll > 0 and layout["scrollbar"].collidepoint(mouse_pos):
        track = layout["scrollbar"]
        ratio = clamp((mouse_pos.y - track.y) / max(1, track.height), 0.0, 1.0)
        game.society_scroll = max_scroll * ratio
        game.audio.play_ui("focus")
        return True

    viewport = layout["viewport"]
    if viewport.collidepoint(mouse_pos):
        card_y = viewport.y - int(game.society_scroll)
        for survivor in game.survivors:
            height = society_card_height(game, survivor)
            rect = pygame.Rect(viewport.x, card_y, viewport.width, height)
            if rect.collidepoint(mouse_pos):
                if game.society_selected_survivor_name == survivor.name:
                    game.society_selected_survivor_name = None
                    game.audio.play_ui("back")
                else:
                    game.society_selected_survivor_name = survivor.name
                    game.audio.play_ui("focus")
                game.clamp_society_scroll()
                return True
            card_y += society_card_step(game, survivor)

    return layout["panel"].collidepoint(mouse_pos)


def handle_hud_input(game) -> bool:
    """Permite alternar a densidade da HUD pelo mouse sem conflitar com o mundo."""
    if not game.scenes.is_gameplay() or not game.input_state.attack_pressed:
        return False
    toggle = hud_toggle_rect(game)
    if toggle.collidepoint(game.input_state.mouse_screen):
        game.hud_compact_mode = not game.hud_compact_mode
        game.audio.play_ui("focus" if game.hud_compact_mode else "back")
        game.set_event_message(
            "HUD compacta ativada." if game.hud_compact_mode else "HUD completa restaurada.",
            duration=3.2,
        )
        return True
    return False







