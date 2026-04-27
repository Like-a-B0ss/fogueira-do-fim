from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH, clamp

if TYPE_CHECKING:
    from ..app.session import Game


def open_exit_prompt(game: "Game") -> None:
    game.exit_prompt_open = True
    game.exit_prompt_index = 0
    game.build_menu_open = False
    game.close_survivor_dialog()
    game.audio.play_ui("back")


def close_exit_prompt(game: "Game") -> None:
    if not game.exit_prompt_open:
        return
    game.exit_prompt_open = False
    game.audio.play_ui("back")


def exit_prompt_layout(_game: "Game") -> dict[str, object]:
    panel = pygame.Rect(0, 0, 560, 332)
    panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    buttons: list[pygame.Rect] = []
    row_y = panel.y + 146
    for _ in ("Salvar e Sair", "Sair sem Salvar", "Cancelar"):
        buttons.append(pygame.Rect(panel.x + 28, row_y, panel.width - 56, 40))
        row_y += 54
    return {"panel": panel, "buttons": buttons}


def confirm_exit_prompt(game: "Game", choice: str | None = None) -> None:
    selected = choice or game.exit_prompt_options[game.exit_prompt_index]
    if selected == "Salvar e Sair":
        success, message = game.save_game()
        game.set_event_message(message, duration=4.8)
        game.spawn_floating_text(
            "save" if success else "falhou",
            game.player.pos,
            PALETTE["accent_soft"] if success else PALETTE["danger_soft"],
        )
        if success:
            game.audio.play_ui("focus")
            game.running = False
        else:
            game.audio.play_alert()
        return
    if selected == "Sair sem Salvar":
        game.running = False
        return
    close_exit_prompt(game)


def handle_exit_prompt_input(game: "Game") -> bool:
    if not game.exit_prompt_open:
        return False
    layout = game.exit_prompt_layout()
    mouse_pos = game.input_state.mouse_screen
    clicked = game.input_state.attack_pressed
    hovered = next(
        (index for index, rect in enumerate(layout["buttons"]) if rect.collidepoint(mouse_pos)),
        None,
    )
    if hovered is not None and hovered != game.exit_prompt_index:
        game.exit_prompt_index = hovered
    if game.input_state.menu_up:
        game.exit_prompt_index = (game.exit_prompt_index - 1) % len(game.exit_prompt_options)
        game.audio.play_ui("focus")
        return True
    if game.input_state.menu_down:
        game.exit_prompt_index = (game.exit_prompt_index + 1) % len(game.exit_prompt_options)
        game.audio.play_ui("focus")
        return True
    if game.input_state.cancel_pressed:
        game.close_exit_prompt()
        return True
    if clicked and hovered is not None:
        game.confirm_exit_prompt(game.exit_prompt_options[hovered])
        return True
    if game.input_state.confirm_pressed or game.input_state.interact_pressed:
        game.confirm_exit_prompt()
        return True
    return True


def refresh_title_actions(game: "Game") -> None:
    actions = ["Novo Jogo", "Configurações", "Sair"]
    if game.save_exists():
        actions.insert(0, "Continuar")
    game.title_actions = tuple(actions)
    game.title_action_index = max(0, min(game.title_action_index, len(game.title_actions) - 1))


def _legacy_tutorial_pages() -> tuple[dict[str, object], ...]:
    return (
        {
            "eyebrow": "Lideranca da Clareira",
            "title": "Você é o chefe do acampamento",
            "body": "Sua presença segura moral, rotina e defesa. O grupo trabalha sozinho, mas depende de foco, fogo e direção para não quebrar.",
            "bullets": (
                "WASD move o chefe pela base e pela mata.",
                "E interage com barracas, rádio, oficina, fogueira, eventos e sobreviventes.",
                "1-4 muda a prioridade social do dia.",
            ),
        },
        {
            "eyebrow": "Sobrevivencia",
            "title": "Tudo gira em torno de estoque e tempo",
            "body": "O acampamento precisa de toras, tábuas, comida, remédios e sucata. A noite aperta mais, e a fogueira segura o centro da sociedade.",
            "bullets": (
                "Clique esquerdo ou Espaço ataca e derruba árvores.",
                "B abre a construção; 1-8 escolhe o edifício.",
                "E na oficina amplia a base quando houver toras e sucata.",
            ),
        },
        {
            "eyebrow": "Pressao do Mundo",
            "title": "Explore, decida e não deixe o campo ruir",
            "body": "Zumbis rondam a floresta, facções cobram respostas, expedições pedem resgate e a sociedade pode enlouquecer se você sumir demais.",
            "bullets": (
                "Q resolve decisões duras em eventos morais e facções.",
                "F5 salva e F9 carrega sem sair da partida.",
                "Enter avanca as dicas; Esc pula tudo e entra no jogo.",
            ),
        },
    )


def create_tutorial_pages() -> tuple[dict[str, object], ...]:
    return (
        {
            "eyebrow": "Mundo Comum",
            "title": "Você aprendeu a sobreviver sozinho",
            "body": "Depois da explosão, da doença e da casa perdida, o chefe ficou frio. Coletar, evitar risco e não se apegar viraram regra.",
            "bullets": (
                "WASD move o chefe pela base e pela mata.",
                "Clique esquerdo ou Espaço ataca e derruba árvores.",
                "A fogueira é abrigo, calor e o centro moral do grupo.",
            ),
        },
        {
            "eyebrow": "Chamado",
            "title": "Uma voz pediu ajuda no rádio",
            "body": "O grupo está faminto, quebrado e desorganizado. Entre eles há uma menina que lembra o chefe do que ele tentou enterrar.",
            "bullets": (
                "E interage com moradores, rádio, oficina, fogueira e eventos.",
                "Conversar aumenta confiança e revela medo, passado e relações.",
                "As tarefas do chefe mostram o que precisa ser feito agora.",
            ),
        },
        {
            "eyebrow": "Primeira Noite",
            "title": "Ficar é atravessar o limiar",
            "body": "A noite vai testar a fogueira, a vigia e a confiança do grupo. Sobreviver sozinho era simples; liderar gente assustada cobra mais.",
            "bullets": (
                "Alimente a fogueira, fale com um morador e mande alguém vigiar.",
                "B abre construção; 1-8 escolhe edifícios quando houver recursos.",
                "Enter entra no jogo; Esc pula as dicas.",
            ),
        },
    )


def adjust_runtime_setting(game: "Game", key: str, delta: float, low: float, high: float) -> None:
    game.runtime_settings[key] = clamp(game.runtime_settings.get(key, 0.0) + delta, low, high)
    game.audio.apply_settings(game.runtime_settings)


def title_setting_value_label(game: "Game", key: str) -> str:
    return f"{int(round(game.runtime_settings.get(key, 0.0) * 100))}%"


def handle_title_input(game: "Game") -> None:
    layout = game.title_ui_layout()
    mouse_pos = game.input_state.mouse_screen
    clicked = game.input_state.attack_pressed
    hovered_action = next(
        (index for index, rect in enumerate(layout["action_rows"]) if rect.collidepoint(mouse_pos)),
        None,
    ) if layout["action_rows"] else None
    hovered_setting = next(
        (index for index, row in enumerate(layout["setting_rows"]) if row["row"].collidepoint(mouse_pos)),
        None,
    )
    hovered_back = layout["settings_back"].collidepoint(mouse_pos) if game.title_settings_open else False

    if hovered_action is not None and hovered_action != game.title_action_index:
        game.title_action_index = hovered_action
        game.audio.play_ui("focus")
    if hovered_setting is not None and hovered_setting != game.title_setting_index:
        game.title_setting_index = hovered_setting
        game.audio.play_ui("focus")

    if game.title_settings_open:
        if game.input_state.menu_up:
            game.title_setting_index = (game.title_setting_index - 1) % len(game.title_setting_entries)
            game.audio.play_ui("focus")
        elif game.input_state.menu_down:
            game.title_setting_index = (game.title_setting_index + 1) % len(game.title_setting_entries)
            game.audio.play_ui("focus")
    else:
        if game.input_state.menu_up:
            game.title_action_index = (game.title_action_index - 1) % len(game.title_actions)
            game.audio.play_ui("focus")
        elif game.input_state.menu_down:
            game.title_action_index = (game.title_action_index + 1) % len(game.title_actions)
            game.audio.play_ui("focus")
    if game.title_settings_open and (game.input_state.menu_left or game.input_state.menu_right):
        key, _, step, low, high = game.title_setting_entries[game.title_setting_index]
        direction = -1.0 if game.input_state.menu_left else 1.0
        game.adjust_runtime_setting(str(key), float(step) * direction, float(low), float(high))
        game.audio.play_ui("focus")

    if clicked and hovered_back:
        game.title_settings_open = False
        game.audio.play_ui("back")
        return

    if clicked and hovered_setting is not None:
        key, _, step, low, high = game.title_setting_entries[hovered_setting]
        setting_ui = layout["setting_rows"][hovered_setting]
        if setting_ui["minus"].collidepoint(mouse_pos):
            game.adjust_runtime_setting(str(key), -float(step), float(low), float(high))
            game.audio.play_ui("focus")
            return
        if setting_ui["plus"].collidepoint(mouse_pos):
            game.adjust_runtime_setting(str(key), float(step), float(low), float(high))
            game.audio.play_ui("focus")
            return

    if game.title_settings_open:
        return

    if not (game.input_state.confirm_pressed or (clicked and hovered_action is not None)):
        return

    choice_index = hovered_action if hovered_action is not None and clicked else game.title_action_index
    choice = game.title_actions[choice_index]
    if clicked or game.input_state.confirm_pressed:
        game.audio.play_ui()
    if choice == "Continuar":
        success, message = game.load_game()
        if success:
            game.audio.play_transition("start")
        else:
            game.set_event_message(message, duration=5.2)
            game.audio.play_alert()
    elif choice == "Novo Jogo":
        game.begin_new_game_flow()
    elif choice == "Configurações":
        game.title_settings_open = True
        game.audio.play_ui("focus")
    elif choice == "Sair":
        game.running = False


def handle_tips_input(game: "Game") -> None:
    layout = game.tips_ui_layout()
    mouse_pos = game.input_state.mouse_screen
    clicked = game.input_state.attack_pressed
    page_count = len(game.tutorial_pages)
    on_last = game.tips_index >= page_count - 1

    if game.input_state.cancel_pressed or game.input_state.alt_interact_pressed:
        game.skip_tips_to_gameplay()
        return

    if clicked and layout["skip_button"].collidepoint(mouse_pos):
        game.audio.play_ui()
        game.skip_tips_to_gameplay()
        return

    if (
        game.input_state.confirm_pressed
        or game.input_state.interact_pressed
        or (clicked and layout["next_button"].collidepoint(mouse_pos))
    ):
        if on_last:
            game.audio.play_ui()
            game.start_gameplay()
        else:
            game.tips_index = min(page_count - 1, game.tips_index + 1)
            game.audio.play_ui("focus")
        return







