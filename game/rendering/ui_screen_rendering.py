from __future__ import annotations

import pygame

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH


def draw_title_screen(game) -> None:
    layout = game.title_ui_layout()
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 10, 12, 112))
    game.screen.blit(overlay, (0, 0))

    mist = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for index in range(4):
        band = pygame.Rect(0, 80 + index * 160, SCREEN_WIDTH, 120)
        pygame.draw.ellipse(mist, (12, 16, 18, 34), band.inflate(180, 60))
    game.screen.blit(mist, (0, 0))

    panel = layout["panel"]
    frame = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(frame, (8, 12, 14, 132), frame.get_rect(), border_radius=28)
    pygame.draw.rect(frame, (124, 96, 70, 70), frame.get_rect(), 1, border_radius=28)
    game.screen.blit(frame, panel.topleft)

    title = game.title_font.render("Fogueira do Fim", True, PALETTE["text"])
    subtitle = game.body_font.render(
        "Sociedade, acampamento e zumbis em um mundo procedural hostil.",
        True,
        PALETTE["accent_soft"],
    )
    game.screen.blit(title, (panel.x + 38, panel.y + 34))
    game.screen.blit(subtitle, (panel.x + 42, panel.y + 96))
    live_tag = game.ui_small_font.render("Simulacao viva ao fundo", True, PALETTE["morale"])
    game.screen.blit(live_tag, (panel.right - live_tag.get_width() - 40, panel.y + 48))

    left_card = layout["left_card"]
    game.draw_panel(left_card, alpha_scale=0.7)
    section = game.heading_font.render("Noite Sobre a Clareira", True, PALETTE["text"])
    game.screen.blit(section, (left_card.x + 20, left_card.y + 18))
    pitch_lines = [
        "Ao fundo, o campo continua respirando: sobreviventes rondam, fogo pulsa e a floresta nunca dorme.",
        "Voce lidera gente exausta no meio da mata, administrando sono, fome, medo e lealdade.",
        "A base cresce por barracas, oficinas, barricadas e expedicoes para muito alem da primeira linha de arvores.",
        "Cada noite cobra leitura social e defesa; cada dia cobra recurso, risco e presenca.",
    ]
    paragraph_y = left_card.y + 64
    text_width = left_card.width - 40
    for line in pitch_lines:
        paragraph_y = game.draw_wrapped_text(
            game.body_font,
            line,
            PALETTE["text"],
            left_card.x + 20,
            paragraph_y,
            text_width,
            line_gap=4,
        ) + 12

    feature_box = pygame.Rect(left_card.x + 18, left_card.bottom - 126, left_card.width - 36, 92)
    pygame.draw.rect(game.screen, PALETTE["ui_panel"], feature_box, border_radius=14)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], feature_box, 1, border_radius=14)
    feature_lines = [
        "Comece um novo turno, revise o ultimo save ou ajuste a apresentacao antes de entrar.",
        "Ao iniciar um jogo novo, uma sequencia curta de dicas aparece e pode ser pulada a qualquer momento.",
    ]
    feature_y = feature_box.y + 16
    for index, line in enumerate(feature_lines):
        feature_y = game.draw_wrapped_text(
            game.ui_small_font,
            line,
            PALETTE["muted"] if index == 0 else PALETTE["accent_soft"],
            feature_box.x + 14,
            feature_y,
            feature_box.width - 28,
            line_gap=2,
        ) + 6

    right_card = layout["right_card"]
    game.draw_panel(right_card, alpha_scale=0.7)
    mouse_pos = game.input_state.mouse_screen if hasattr(game, "input_state") else pygame.Vector2()
    menu_title = game.heading_font.render("Entrada da Clareira", True, PALETTE["text"])
    game.screen.blit(menu_title, (right_card.x + 20, right_card.y + 18))
    game.draw_wrapped_text(
        game.ui_small_font,
        "Tela cheia, mouse ativo e simulacao viva atras do menu principal.",
        PALETTE["muted"],
        right_card.x + 20,
        right_card.y + 48,
        right_card.width - 40,
        line_gap=2,
    )

    if not game.title_settings_open:
        for index, action in enumerate(game.title_actions):
            row = layout["action_rows"][index]
            active = game.title_action_index == index or row.collidepoint(mouse_pos)
            pygame.draw.rect(game.screen, (52, 68, 72) if active else PALETTE["ui_panel"], row, border_radius=14)
            pygame.draw.rect(game.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], row, 1, border_radius=14)
            label = game.body_font.render(action, True, PALETTE["text"])
            if action == "Continuar":
                prompt_text = "Retomar o ultimo acampamento salvo."
            elif action == "Novo Jogo":
                prompt_text = "Entrar na clareira."
            elif action == "Configuracoes":
                prompt_text = "Abrir a aba de ajustes."
            else:
                prompt_text = "Fechar a sessao."
            game.screen.blit(label, (row.x + 16, row.y + 9))
            game.draw_wrapped_text(
                game.ui_small_font,
                prompt_text,
                PALETTE["muted"],
                row.x + 16,
                row.y + 27,
                row.width - 32,
                line_gap=0,
            )
    else:
        settings_panel = layout["settings_panel"]
        game.draw_panel(settings_panel)
        settings_title = game.heading_font.render("Configuracoes", True, PALETTE["text"])
        settings_subtitle = game.ui_small_font.render(
            "Clique em - e + ou use A e D para ajustar a linha marcada.",
            True,
            PALETTE["muted"],
        )
        back_hover = layout["settings_back"].collidepoint(mouse_pos)
        pygame.draw.rect(
            game.screen,
            (70, 84, 88) if back_hover else PALETTE["ui_panel"],
            layout["settings_back"],
            border_radius=10,
        )
        pygame.draw.rect(game.screen, PALETTE["ui_line"], layout["settings_back"], 1, border_radius=10)
        back_text = game.ui_small_font.render("Voltar", True, PALETTE["text"])
        game.screen.blit(settings_title, (settings_panel.x + 18, settings_panel.y + 16))
        game.screen.blit(settings_subtitle, (settings_panel.x + 18, settings_panel.y + 46))
        game.screen.blit(back_text, back_text.get_rect(center=layout["settings_back"].center))

        for index, ((key, label, _, _, _), item) in enumerate(zip(game.title_setting_entries, layout["setting_rows"])):
            row = item["row"]
            active = game.title_setting_index == index or row.collidepoint(mouse_pos)
            pygame.draw.rect(game.screen, (44, 58, 62) if active else PALETTE["ui_panel"], row, border_radius=12)
            pygame.draw.rect(game.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], row, 1, border_radius=12)
            minus_hover = item["minus"].collidepoint(mouse_pos)
            plus_hover = item["plus"].collidepoint(mouse_pos)
            pygame.draw.rect(game.screen, (70, 84, 88) if minus_hover else (54, 66, 70), item["minus"], border_radius=7)
            pygame.draw.rect(game.screen, (70, 84, 88) if plus_hover else (54, 66, 70), item["plus"], border_radius=7)
            pygame.draw.rect(game.screen, PALETTE["ui_line"], item["minus"], 1, border_radius=7)
            pygame.draw.rect(game.screen, PALETTE["ui_line"], item["plus"], 1, border_radius=7)
            pygame.draw.rect(game.screen, (32, 40, 42), item["value"], border_radius=7)
            pygame.draw.rect(game.screen, PALETTE["ui_line"], item["value"], 1, border_radius=7)
            left = game.ui_small_font.render(label, True, PALETTE["text"])
            value = game.ui_small_font.render(
                game.title_setting_value_label(str(key)),
                True,
                PALETTE["morale"] if active else PALETTE["text"],
            )
            minus = game.body_font.render("-", True, PALETTE["text"])
            plus = game.body_font.render("+", True, PALETTE["text"])
            game.screen.blit(left, (row.x + 12, row.y + 5))
            game.screen.blit(value, value.get_rect(center=item["value"].center))
            game.screen.blit(minus, minus.get_rect(center=item["minus"].center))
            game.screen.blit(plus, plus.get_rect(center=item["plus"].center))

    footer_text = (
        game.event_message
        if getattr(game, "event_timer", 0) > 0
        else "Enter confirma  |  Esc fecha  |  Novo Jogo abre as dicas antes da vigia."
    )
    footer_width = panel.width - 160
    footer_lines = game.wrap_text_lines(game.ui_small_font, footer_text, footer_width)
    footer_line_height = game.ui_small_font.get_linesize()
    footer_total = len(footer_lines) * footer_line_height + max(0, len(footer_lines) - 1) * 2
    footer_y = panel.bottom - 26 - footer_total
    for index, line in enumerate(footer_lines):
        footer = game.ui_small_font.render(line, True, PALETTE["muted"])
        game.screen.blit(
            footer,
            footer.get_rect(
                center=(panel.centerx, footer_y + index * (footer_line_height + 2) + footer_line_height // 2)
            ),
        )


def draw_tips_screen(game) -> None:
    layout = game.tips_ui_layout()
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 10, 12, 124))
    game.screen.blit(overlay, (0, 0))

    panel = layout["panel"]
    game.draw_panel(panel)
    page = game.tutorial_pages[game.tips_index]
    mouse_pos = game.input_state.mouse_screen if hasattr(game, "input_state") else pygame.Vector2()
    next_hover = layout["next_button"].collidepoint(mouse_pos)
    skip_hover = layout["skip_button"].collidepoint(mouse_pos)
    last_page = game.tips_index >= len(game.tutorial_pages) - 1

    eyebrow = game.small_font.render(str(page["eyebrow"]).upper(), True, PALETTE["morale"])
    title = game.title_font.render(str(page["title"]), True, PALETTE["text"])
    body = game.body_font.render(str(page["body"]), True, PALETTE["accent_soft"])
    game.screen.blit(eyebrow, (panel.x + 42, panel.y + 24))
    game.screen.blit(title, (panel.x + 38, panel.y + 52))
    game.screen.blit(body, (panel.x + 44, panel.y + 118))

    content = layout["content"]
    box = pygame.Rect(content.x, content.y + 18, content.width, content.height - 36)
    pygame.draw.rect(game.screen, (24, 32, 34), box, border_radius=22)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], box, 1, border_radius=22)
    hint = game.small_font.render(
        "Dicas essenciais para entrar na primeira vigia. Enter avanca, Esc pula.",
        True,
        PALETTE["muted"],
    )
    game.screen.blit(hint, (box.x + 22, box.y + 18))

    for index, bullet in enumerate(page["bullets"]):
        pill = pygame.Rect(box.x + 20, box.y + 56 + index * 72, box.width - 40, 52)
        pygame.draw.rect(game.screen, PALETTE["ui_panel"], pill, border_radius=16)
        pygame.draw.rect(
            game.screen,
            PALETTE["accent_soft"] if index == game.tips_index else PALETTE["ui_line"],
            pill,
            1,
            border_radius=16,
        )
        num = game.body_font.render(f"{index + 1}", True, PALETTE["morale"])
        text = game.body_font.render(str(bullet), True, PALETTE["text"])
        game.screen.blit(num, (pill.x + 16, pill.y + 14))
        game.screen.blit(text, (pill.x + 44, pill.y + 14))

    for index in range(len(game.tutorial_pages)):
        color = PALETTE["accent_soft"] if index == game.tips_index else (68, 82, 86)
        pygame.draw.circle(game.screen, color, (panel.x + 52 + index * 20, panel.bottom - 44), 5)

    for rect, label, hover in (
        (layout["next_button"], "Entrar no Jogo" if last_page else "Proxima", next_hover),
        (layout["skip_button"], "Pular Dicas", skip_hover),
    ):
        pygame.draw.rect(game.screen, (62, 80, 84) if hover else PALETTE["ui_panel"], rect, border_radius=14)
        pygame.draw.rect(game.screen, PALETTE["accent_soft"] if hover else PALETTE["ui_line"], rect, 1, border_radius=14)
        text = game.body_font.render(label, True, PALETTE["text"])
        game.screen.blit(text, text.get_rect(center=rect.center))


def draw_game_over(game) -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((18, 6, 8, 182))
    game.screen.blit(overlay, (0, 0))
    panel = pygame.Rect(0, 0, 620, 260)
    panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    game.draw_panel(panel)
    title = game.title_font.render("O campo caiu", True, PALETTE["danger_soft"])
    subtitle = game.body_font.render(
        "A fogueira se apagou, a moral quebrou ou o chefe nao resistiu.",
        True,
        PALETTE["text"],
    )
    retry = game.body_font.render("Pressione Enter para recomecar a vigia.", True, PALETTE["morale"])
    game.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 78)))
    game.screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.y + 136)))
    game.screen.blit(retry, retry.get_rect(center=(panel.centerx, panel.y + 188)))


def draw_exit_prompt(game) -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 6, 8, 186))
    game.screen.blit(overlay, (0, 0))
    layout = game.exit_prompt_layout()
    panel = layout["panel"]
    game.draw_panel(panel)
    title = game.heading_font.render("Sair da vigia?", True, PALETTE["text"])
    game.screen.blit(title, (panel.x + 26, panel.y + 18))

    subtitle_y = game.draw_wrapped_text(
        game.body_font,
        "Escolha se quer salvar antes de fechar o jogo.",
        PALETTE["muted"],
        panel.x + 26,
        panel.y + 58,
        panel.width - 52,
        line_gap=2,
    )
    game.draw_wrapped_text(
        game.ui_small_font,
        "Enter confirma  |  Esc cancela",
        PALETTE["accent_soft"],
        panel.x + 26,
        subtitle_y + 8,
        panel.width - 52,
        line_gap=0,
    )

    mouse_pos = game.input_state.mouse_screen
    for index, (rect, label) in enumerate(zip(layout["buttons"], game.exit_prompt_options)):
        active = game.exit_prompt_index == index or rect.collidepoint(mouse_pos)
        fill = (70, 88, 92) if active else (34, 47, 50)
        pygame.draw.rect(game.screen, fill, rect, border_radius=14)
        pygame.draw.rect(
            game.screen,
            PALETTE["accent_soft"] if active else PALETTE["ui_line"],
            rect,
            1,
            border_radius=14,
        )
        text = game.body_font.render(
            game.fit_text_to_width(game.body_font, label, rect.width - 28),
            True,
            PALETTE["text"],
        )
        game.screen.blit(text, text.get_rect(center=rect.center))








