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


def return_to_title_screen(game: "Game") -> None:
    """Volta ao menu principal sem fechar o jogo."""
    close_exit_prompt(game)
    game.close_survivor_dialog()
    game.scenes.change("title")
    game.refresh_title_actions()
    game.exit_prompt_open = False
    game.audio.play_ui("focus")


def exit_prompt_layout(_game: "Game") -> dict[str, object]:
    panel = pygame.Rect(0, 0, 600, 380)  # Aumentado para 4 opções
    panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    buttons: list[pygame.Rect] = []
    row_y = panel.y + 146
    for _ in _game.exit_prompt_options:  # Usa as opções do jogo
        buttons.append(pygame.Rect(panel.x + 28, row_y, panel.width - 56, 40))
        row_y += 54
    return {"panel": panel, "buttons": buttons}


def confirm_exit_prompt(game: "Game", choice: str | None = None) -> None:
    selected = choice or game.exit_prompt_options[game.exit_prompt_index]
    if selected == "Salvar e Voltar ao Menu":
        success, message = game.save_game()
        game.set_event_message(message, duration=4.8)
        game.spawn_floating_text(
            "save" if success else "falhou",
            game.player.pos,
            PALETTE["accent_soft"] if success else PALETTE["danger_soft"],
        )
        if success:
            game.audio.play_ui("focus")
            return_to_title_screen(game)
        else:
            game.audio.play_alert()
        return
    if selected == "Voltar ao Menu sem Salvar":
        return_to_title_screen(game)
        return
    if selected == "Comandos":
        game.controls_panel_open = True
        game.audio.play_ui("focus")
        close_exit_prompt(game)
        return
    close_exit_prompt(game)


def controls_panel_layout(game: "Game") -> dict[str, object]:
    """Layout do painel de comandos com áreas bem definidas."""
    from ..core.config import SCREEN_HEIGHT, SCREEN_WIDTH

    # Painel principal com margens seguras
    panel = pygame.Rect(0, 0, min(SCREEN_WIDTH - 80, 920), min(SCREEN_HEIGHT - 80, 600))
    panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    # Área do título
    title_area = pygame.Rect(panel.x + 24, panel.y + 16, panel.width - 96, 40)

    # Botão fechar
    close = pygame.Rect(panel.right - 88, panel.y + 18, 72, 28)

    # Área de conteúdo (comandos)
    content_top = title_area.bottom + 16
    content_bottom = panel.bottom - 50  # Reserva espaço para footer
    content_height = content_bottom - content_top

    # Duas colunas com espaçamento
    col_gap = 32
    col_width = (panel.width - 72 - col_gap) // 2

    left_col_area = pygame.Rect(
        panel.x + 24,
        content_top,
        col_width,
        content_height
    )

    right_col_area = pygame.Rect(
        left_col_area.right + col_gap,
        content_top,
        col_width,
        content_height
    )

    # Footer area
    footer_area = pygame.Rect(
        panel.x + 24,
        panel.bottom - 40,
        panel.width - 48,
        32
    )

    # Comandos organizados
    all_commands = [
        ("WASD", "Mover o chefe"),
        ("Shift", "Correr"),
        ("Mouse", "Olhar na direção"),
        ("Espaço / Esq.", "Atacar"),
        ("E / Dir.", "Interagir"),
        ("Tab", "HUD compacta"),
        ("B", "Menu construção"),
        ("1-8", "Selecionar construção"),
        ("F5", "Salvar jogo"),
        ("F9", "Carregar jogo"),
        ("1-4", "Foco estratégia"),
        ("M", "Painel volume"),
        ("Esc", "Menu pausa"),
    ]

    # Dividir comandos em 2 colunas
    mid_point = (len(all_commands) + 1) // 2
    left_commands = all_commands[:mid_point]
    right_commands = all_commands[mid_point:]

    return {
        "panel": panel,
        "title_area": title_area,
        "close": close,
        "left_col_area": left_col_area,
        "right_col_area": right_col_area,
        "footer_area": footer_area,
        "left_commands": left_commands,
        "right_commands": right_commands,
    }


def draw_controls_panel(game: "Game") -> None:
    """Desenha o painel de comandos com layout organizado e sem sobreposição."""
    if not game.controls_panel_open:
        return

    layout = controls_panel_layout(game)
    panel = layout["panel"]

    # Overlay de fundo
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    game.screen.blit(overlay, (0, 0))

    # Painel principal
    game.draw_panel(panel)

    # Título dentro da área definida
    title = game.title_font.render("Comandos do Jogo", True, PALETTE["text"])
    title_rect = title.get_rect()
    title_rect.left = layout["title_area"].x
    title_rect.centery = layout["title_area"].centery
    game.screen.blit(title, title_rect)

    # Botão de fechar
    mouse_pos = game.input_state.mouse_screen if hasattr(game, "input_state") else pygame.Vector2()
    close_hover = layout["close"].collidepoint(mouse_pos)
    pygame.draw.rect(
        game.screen,
        (70, 84, 88) if close_hover else PALETTE["ui_panel"],
        layout["close"],
        border_radius=8,
    )
    pygame.draw.rect(game.screen, PALETTE["ui_line"], layout["close"], 1, border_radius=8)
    close_text = game.ui_small_font.render("Fechar", True, PALETTE["text"])
    game.screen.blit(close_text, close_text.get_rect(center=layout["close"].center))

    # Configurações de linha
    key_box_width = 120
    key_box_height = 32
    key_desc_gap = 12
    row_height = 42

    # Desenhar coluna esquerda dentro da área definida
    current_y = layout["left_col_area"].y
    for key, description in layout["left_commands"]:
        # Verificar limite vertical
        if current_y + key_box_height > layout["left_col_area"].bottom:
            break

        # Box da tecla
        key_box = pygame.Rect(
            layout["left_col_area"].x,
            current_y,
            key_box_width,
            key_box_height
        )

        # Descrição - calcula largura disponível
        desc_max_width = layout["left_col_area"].right - key_box.right - key_desc_gap
        desc_text = game.body_font.render(description, True, PALETTE["muted"])

        # Truncar se necessário
        if desc_text.get_width() > desc_max_width:
            desc_text = game.fit_text_to_width(
                game.body_font, description, desc_max_width
            )

        # Renderizar tecla
        pygame.draw.rect(game.screen, PALETTE["ui_panel"], key_box, border_radius=6)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], key_box, 1, border_radius=6)
        key_text = game.body_font.render(key, True, PALETTE["text"])
        game.screen.blit(key_text, key_text.get_rect(center=key_box.center))

        # Renderizar descrição
        desc_x = key_box.right + key_desc_gap
        desc_y = current_y + (key_box_height - desc_text.get_height()) // 2
        game.screen.blit(desc_text, (desc_x, desc_y))

        current_y += row_height

    # Desenhar coluna direita dentro da área definida
    current_y = layout["right_col_area"].y
    for key, description in layout["right_commands"]:
        # Verificar limite vertical
        if current_y + key_box_height > layout["right_col_area"].bottom:
            break

        # Box da tecla
        key_box = pygame.Rect(
            layout["right_col_area"].x,
            current_y,
            key_box_width,
            key_box_height
        )

        # Descrição - calcula largura disponível
        desc_max_width = layout["right_col_area"].right - key_box.right - key_desc_gap
        desc_text = game.body_font.render(description, True, PALETTE["muted"])

        # Truncar se necessário
        if desc_text.get_width() > desc_max_width:
            desc_text = game.fit_text_to_width(
                game.body_font, description, desc_max_width
            )

        # Renderizar tecla
        pygame.draw.rect(game.screen, PALETTE["ui_panel"], key_box, border_radius=6)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], key_box, 1, border_radius=6)
        key_text = game.body_font.render(key, True, PALETTE["text"])
        game.screen.blit(key_text, key_text.get_rect(center=key_box.center))

        # Renderizar descrição
        desc_x = key_box.right + key_desc_gap
        desc_y = current_y + (key_box_height - desc_text.get_height()) // 2
        game.screen.blit(desc_text, (desc_x, desc_y))

        current_y += row_height

    # Footer dentro da área definida
    footer_text = "Esc ou clique em Fechar para voltar ao jogo"
    footer = game.body_font.render(footer_text, True, PALETTE["muted"])
    footer_rect = footer.get_rect()
    footer_rect.centerx = layout["footer_area"].centerx
    footer_rect.centery = layout["footer_area"].centery

    # Garantir que o footer não ultrapasse a área
    footer_rect.clamp_ip(layout["footer_area"])
    game.screen.blit(footer, footer_rect)


def handle_controls_panel_input(game: "Game") -> bool:
    """Trata input do painel de comandos."""
    if not game.controls_panel_open:
        return False

    layout = controls_panel_layout(game)
    mouse_pos = game.input_state.mouse_screen
    clicked = game.input_state.attack_pressed

    # Verificar clique no botão fechar
    if clicked and layout["close"].collidepoint(mouse_pos):
        game.controls_panel_open = False
        game.audio.play_ui("back")
        return True

    # Esc fecha o painel
    if game.input_state.cancel_pressed:
        game.controls_panel_open = False
        game.audio.play_ui("back")
        return True

    return True


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
            "title": "Você sobreviveu sozinho",
            "body": "Antes do colapso, você tinha uma vida simples. Trabalhava, cuidava da casa e criava sua filha pequena. Depois da explosão, da doença e da perda, você aprendeu a não se apegar.",
            "bullets": (
                "WASD move o chefe pela base e pela mata.",
                "Clique esquerdo ou Espaço ataca e derruba árvores.",
                "A fogueira é abrigo, calor e o centro moral do grupo.",
            ),
        },
        {
            "eyebrow": "Chamado",
            "title": "Uma menina quebrou sua lógica",
            "body": "Meses depois, uma voz no rádio pediu ajuda. O grupo está faminto e desorganizado. Entre eles há uma menina - não é sua filha, mas o jeito de falar, os pequenos hábitos... isso quebrou você.",
            "bullets": (
                "E interage com moradores, rádio, oficina, fogueira e eventos.",
                "Conversar aumenta confiança e revela medo, passado e relações.",
                "As tarefas do chefe mostram o que precisa ser feito agora.",
            ),
        },
        {
            "eyebrow": "Travessia do Limiar",
            "title": "Primeira noite como líder",
            "body": "Você podia ter ido embora. Escolheu ficar. A primeira noite será o teste: barricadas improvisadas, ninguém sabe vigiar direito, pânico coletivo. Mas você assume o controle.",
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







