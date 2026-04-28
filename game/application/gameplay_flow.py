from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame import Vector2

from ..core.config import PALETTE

if TYPE_CHECKING:
    from ..app.session import Game


def begin_player_sleep(game: "Game", slot: dict[str, object]) -> None:
    game.player_sleeping = True
    game.player_sleep_slot = dict(slot)
    game.player_sleep_elapsed = 0.0
    game.player.velocity *= 0.0
    game.player.pos = Vector2(slot["sleep_pos"])
    game.build_menu_open = False
    game.set_event_message(
        "Você deitou na barraca. O tempo corre e a sociedade segura o campo sem ordens diretas.",
        duration=5.8,
    )
    game.spawn_floating_text("dormindo", game.player.pos, PALETTE["muted"])


def wake_player(game: "Game", message: str | None = None) -> None:
    if not game.player_sleeping:
        return
    slot = game.player_sleep_slot
    game.player_sleeping = False
    game.player_sleep_slot = None
    game.player_sleep_elapsed = 0.0
    if slot:
        game.player.pos = Vector2(slot["interact_pos"])
    if message:
        game.set_event_message(message, duration=4.8)
        game.spawn_floating_text("acordado", game.player.pos, PALETTE["accent_soft"])


def audio_debug_rows(game: "Game") -> tuple[list[str], pygame.Rect, int, int]:
    cues = game.audio.debug_cue_names() if hasattr(game.audio, "debug_cue_names") else []
    screen_width, screen_height = game.screen.get_size()
    panel = pygame.Rect(0, 0, min(760, screen_width - 80), min(660, screen_height - 80))
    panel.center = (screen_width // 2, screen_height // 2)
    row_height = 28
    visible_rows = max(1, (panel.height - 118) // row_height)
    return cues, panel, row_height, visible_rows


def handle_audio_debug_input(game: "Game") -> bool:
    if game.input_state.audio_debug_pressed:
        game.audio_debug_open = not getattr(game, "audio_debug_open", False)
        game.audio_debug_index = 0
        game.audio_debug_scroll = 0
        game.audio.play_ui("focus" if game.audio_debug_open else "back")
        return True
    if not getattr(game, "audio_debug_open", False):
        return False

    cues, panel, row_height, visible_rows = audio_debug_rows(game)
    if not cues:
        if game.input_state.cancel_pressed:
            game.audio_debug_open = False
            game.audio.play_ui("back")
        return True

    if game.input_state.cancel_pressed:
        game.audio_debug_open = False
        game.audio.play_ui("back")
        return True
    if game.input_state.menu_up:
        game.audio_debug_index = max(0, game.audio_debug_index - 1)
        game.audio.play_ui("focus")
    if game.input_state.menu_down:
        game.audio_debug_index = min(len(cues) - 1, game.audio_debug_index + 1)
        game.audio.play_ui("focus")
    if game.input_state.mouse_wheel_y:
        game.audio_debug_index = max(0, min(len(cues) - 1, game.audio_debug_index - game.input_state.mouse_wheel_y))
    if game.input_state.confirm_pressed or game.input_state.interact_pressed:
        game.audio.play_debug_cue(cues[game.audio_debug_index])

    game.audio_debug_scroll = max(0, min(game.audio_debug_scroll, max(0, len(cues) - visible_rows)))
    if game.audio_debug_index < game.audio_debug_scroll:
        game.audio_debug_scroll = game.audio_debug_index
    elif game.audio_debug_index >= game.audio_debug_scroll + visible_rows:
        game.audio_debug_scroll = game.audio_debug_index - visible_rows + 1

    if game.input_state.attack_pressed:
        mouse_pos = game.input_state.mouse_screen
        list_top = panel.y + 74
        list_rect = pygame.Rect(panel.x + 18, list_top, panel.width - 36, visible_rows * row_height)
        if list_rect.collidepoint(mouse_pos):
            row = int((mouse_pos.y - list_top) // row_height)
            index = game.audio_debug_scroll + row
            if 0 <= index < len(cues):
                game.audio_debug_index = index
                game.audio.play_debug_cue(cues[index])
        return True

    return True


def handle_events(game: "Game") -> None:
    game.input_state = game.input.poll()

    if handle_audio_debug_input(game):
        return

    if game.input_state.quit_requested:
        if game.scenes.is_gameplay():
            game.open_exit_prompt()
        else:
            game.running = False
        return

    # Verificar painel de comandos primeiro
    if game.controls_panel_open:
        game.handle_controls_panel_input()
        return

    if game.handle_exit_prompt_input():
        return

    if game.input_state.cancel_pressed:
        if game.scenes.is_splash():
            game.running = False
            return
        if game.scenes.is_title() and game.title_settings_open:
            game.title_settings_open = False
            game.audio.play_ui("back")
            return
        if game.scenes.is_gameplay() and game.gameplay_settings_open:
            game.gameplay_settings_open = False
            game.audio.play_ui("back")
            return
        if game.scenes.is_gameplay() and game.active_dialog_survivor():
            game.close_survivor_dialog()
            game.audio.play_ui("back")
            return
        if game.build_menu_open:
            game.build_menu_open = False
            game.audio.play_ui("back")
            return
        if game.scenes.is_tips():
            game.skip_tips_to_gameplay()
            return
        if game.scenes.is_gameplay():
            game.open_exit_prompt()
        else:
            game.running = False
        return

    if game.scenes.is_splash():
        if (
            game.input_state.confirm_pressed
            or game.input_state.interact_pressed
            or game.input_state.attack_pressed
            or game.input_state.alt_interact_pressed
        ) and game.splash_elapsed >= 2.4:
            game.splash_elapsed = game.splash_min_duration
            game.title_intro_alpha = 0.0
            game.scenes.change("title")
            game.audio.play_ui("focus")
        return

    if game.scenes.is_title():
        game.handle_title_input()
        return

    if game.scenes.is_tips():
        game.handle_tips_input()
        return

    if game.scenes.is_game_over() and game.input_state.confirm_pressed:
        game.restart_game()
        return

    if not game.scenes.is_gameplay():
        return

    if game.input_state.runtime_panel_pressed:
        game.gameplay_settings_open = not game.gameplay_settings_open
        game.audio.play_ui("focus" if game.gameplay_settings_open else "back")
        return

    if game.input_state.load_pressed:
        success, message = game.load_game()
        if success:
            game.audio.play_transition("start")
        else:
            game.set_event_message(message, duration=5.2)
            game.audio.play_alert()
        return

    if game.input_state.save_pressed:
        success, message = game.save_game()
        game.set_event_message(message, duration=4.8)
        game.spawn_floating_text(
            "save" if success else "falhou",
            game.player.pos,
            PALETTE["accent_soft"] if success else PALETTE["danger_soft"],
        )
        if success:
            game.audio.play_ui("focus")
        else:
            game.audio.play_alert()

    game.audio.set_listener_position(game.player.pos)

    if game.player_sleeping:
        if (
            game.input_state.move.length_squared() > 0
            or game.input_state.interact_pressed
            or game.input_state.alt_interact_pressed
            or game.input_state.attack_pressed
            or game.input_state.confirm_pressed
            or game.input_state.cancel_pressed
            or game.input_state.build_menu_pressed
            or game.input_state.focus_slot is not None
        ):
            game.wake_player("Você acordou e retomou o controle da clareira.")
        return

    if game.handle_chat_panel_input():
        return

    if game.handle_society_panel_input():
        return

    if game.handle_directive_panel_input():
        return

    if game.handle_hud_input():
        return

    if game.handle_runtime_settings_input():
        return

    if game.input_state.hud_toggle_pressed:
        game.hud_compact_mode = not game.hud_compact_mode
        game.audio.play_ui("focus" if game.hud_compact_mode else "back")
        game.set_event_message(
            "HUD compacta ativada." if game.hud_compact_mode else "HUD completa restaurada.",
            duration=3.2,
        )
        return

    if game.input_state.build_menu_pressed:
        game.build_menu_open = not game.build_menu_open
        game.audio.play_ui("focus" if game.build_menu_open else "back")
        return

    if game.build_menu_open and game.input_state.focus_slot and 1 <= game.input_state.focus_slot <= len(game.build_recipes):
        game.selected_build_slot = int(game.input_state.focus_slot)
        game.audio.play_ui("focus")
    elif game.input_state.focus_slot == 1:
        game.focus_mode = "balanced"
        game.spawn_floating_text("foco: equilibrio", game.player.pos, PALETTE["text"])
        game.audio.play_ui("focus")
    elif game.input_state.focus_slot == 2:
        game.focus_mode = "supply"
        game.spawn_floating_text("foco: suprimentos", game.player.pos, PALETTE["accent_soft"])
        game.audio.play_ui("focus")
    elif game.input_state.focus_slot == 3:
        game.focus_mode = "fortify"
        game.spawn_floating_text("foco: fortificar", game.player.pos, PALETTE["heal"])
        game.audio.play_ui("focus")
    elif game.input_state.focus_slot == 4:
        game.focus_mode = "morale"
        game.spawn_floating_text("foco: moral", game.player.pos, PALETTE["morale"])
        game.audio.play_ui("focus")

    if game.build_menu_open and game.input_state.attack_pressed:
        recipe = game.selected_build_recipe()
        placed = game.place_building(str(recipe["kind"]), game.screen_to_world(game.input_state.mouse_screen))
        if placed:
            game.audio.play_ui()
        else:
            game.audio.play_alert()
        return

    if game.input_state.interact_pressed:
        game.player.perform_interaction(game, hardline=False)
    if game.input_state.alt_interact_pressed:
        game.player.perform_interaction(game, hardline=True)
    if game.input_state.mouse_interact_pressed:
        game.player.perform_mouse_interaction(game)
    if game.input_state.attack_pressed:
        game.player.perform_attack(game)
