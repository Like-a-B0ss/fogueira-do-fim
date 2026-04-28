from __future__ import annotations

import pygame

from ..core.config import PALETTE, SCREEN_HEIGHT, SCREEN_WIDTH, load_font


def draw_splash_screen(game) -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 252))
    game.screen.blit(overlay, (0, 0))

    progress = min(1.0, game.splash_elapsed / max(0.01, game.splash_min_duration))
    fade_out = min(1.0, max(0.0, (progress - 0.92) / 0.08))
    alpha_scale = max(0.0, 1.0 - fade_out)

    text_alpha = int(255 * alpha_scale)
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2

    credit_font = load_font(38, title=True)
    connector_font = load_font(32, title=True)
    presents_font = load_font(30, title=True)
    support_font = load_font(46, title=True)
    credit = credit_font.render("LEONARDO", True, PALETTE["text"])
    connector = connector_font.render("e", True, PALETTE["muted"])
    co_credit = credit_font.render("MARIANO", True, PALETTE["text"])
    presents = presents_font.render("apresentam", True, PALETTE["muted"])
    support = support_font.render("Fogueira do Fim", True, PALETTE["text"])

    for text_surface in (credit, connector, co_credit, presents, support):
        text_surface.set_alpha(text_alpha)

    total_width = credit.get_width() + 24 + connector.get_width() + 24 + co_credit.get_width()
    row_left = center_x - total_width // 2
    row_y = center_y - 58
    game.screen.blit(credit, (row_left, row_y))
    game.screen.blit(connector, (row_left + credit.get_width() + 24, row_y + 6))
    game.screen.blit(co_credit, (row_left + credit.get_width() + 24 + connector.get_width() + 24, row_y))
    game.screen.blit(presents, presents.get_rect(center=(center_x, center_y + 24)))
    game.screen.blit(support, support.get_rect(center=(center_x, center_y + 82)))

    if game.splash_elapsed >= 2.4:
        pulse = 0.55 + 0.45 * ((pygame.math.Vector2(1, 0).rotate(game.splash_hint_pulse * 160).x + 1) * 0.5)
        hint = game.ui_small_font.render("Pressione Enter, clique ou E para pular", True, PALETTE["text"])
        hint.set_alpha(int(255 * pulse))
        game.screen.blit(hint, hint.get_rect(center=(center_x, SCREEN_HEIGHT - 54)))


def draw_title_screen(game) -> None:
    layout = game.title_ui_layout()
    intro_alpha = int(max(0, min(255, getattr(game, "title_intro_alpha", 255.0))))
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 10, 12, int(112 * (intro_alpha / 255 if intro_alpha else 0))))
    game.screen.blit(overlay, (0, 0))

    mist = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for index in range(4):
        band = pygame.Rect(0, 80 + index * 160, SCREEN_WIDTH, 120)
        pygame.draw.ellipse(mist, (12, 16, 18, int(34 * (intro_alpha / 255 if intro_alpha else 0))), band.inflate(180, 60))
    game.screen.blit(mist, (0, 0))

    panel = layout["panel"]
    frame = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(frame, (8, 12, 14, int(132 * (intro_alpha / 255 if intro_alpha else 0))), frame.get_rect(), border_radius=28)
    pygame.draw.rect(frame, (124, 96, 70, int(70 * (intro_alpha / 255 if intro_alpha else 0))), frame.get_rect(), 1, border_radius=28)
    game.screen.blit(frame, panel.topleft)

    # Título e subtítulo melhorados
    title = game.title_font.render("Fogueira do Fim", True, PALETTE["text"])
    subtitle = game.body_font.render(
        "Liderança. Sobrevivência. Redenção. Em um mundo que não perdoa.",
        True,
        PALETTE["accent_soft"],
    )
    game.screen.blit(title, (panel.x + 38, panel.y + 34))
    game.screen.blit(subtitle, (panel.x + 42, panel.y + 96))
    live_tag = game.ui_small_font.render("Simulação viva ao fundo", True, PALETTE["morale"])
    game.screen.blit(live_tag, (panel.right - live_tag.get_width() - 40, panel.y + 48))

    # Card esquerdo - Narrativa motivadora
    left_card = layout["left_card"]
    game.draw_panel(left_card, alpha_scale=0.7)

    # Seção com texto seguro e alinhado
    section_title = "Sua Jornada Começa"
    section = game.heading_font.render(section_title, True, PALETTE["text"])
    game.screen.blit(section, (left_card.x + 20, left_card.y + 18))

    # Texto motivador e descritivo com bounds garantidos
    pitch_lines = [
        "Você sobreviveu sozinho por meses. Então uma voz no rádio pediu ajuda.",
        "Entre os sobreviventes, uma menina que lembra o que você perdeu.",
        "Agora você é o líder. Cada decisão pesa: quem come, quem dorme.",
        "Construa seu acampamento. Gerencie conflitos. Proteja quem restou.",
    ]
    paragraph_y = left_card.y + 64
    text_width = left_card.width - 40
    max_paragraph_y = left_card.bottom - 140  # Reserva espaço para feature_box

    for line in pitch_lines:
        if paragraph_y >= max_paragraph_y:
            break  # Não ultrapassar o box
        paragraph_y = game.draw_wrapped_text(
            game.body_font,
            line,
            PALETTE["text"],
            left_card.x + 20,
            paragraph_y,
            text_width,
            line_gap=3,
        ) + 10

    feature_box = pygame.Rect(left_card.x + 18, left_card.bottom - 126, left_card.width - 36, 92)
    pygame.draw.rect(game.screen, PALETTE["ui_panel"], feature_box, border_radius=14)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], feature_box, 1, border_radius=14)

    # Feature lines com bounds garantidos
    feature_lines = [
        "Não existem escolhas fáceis. Existem as que você consegue viver.",
        "Cada partida é única. Construa sua história neste mundo.",
    ]
    feature_y = feature_box.y + 14
    max_feature_y = feature_box.bottom - 8

    for index, line in enumerate(feature_lines):
        if feature_y >= max_feature_y:
            break
        feature_y = game.draw_wrapped_text(
            game.ui_small_font,
            line,
            PALETTE["muted"] if index == 0 else PALETTE["accent_soft"],
            feature_box.x + 14,
            feature_y,
            feature_box.width - 28,
            line_gap=1,
        ) + 5

    # Card direito - Menu de ações
    right_card = layout["right_card"]
    game.draw_panel(right_card, alpha_scale=0.7)
    mouse_pos = game.input_state.mouse_screen if hasattr(game, "input_state") else pygame.Vector2()

    # Menu title com bounds garantidos
    menu_title_text = "Entrar na Clareira"
    menu_title = game.heading_font.render(menu_title_text, True, PALETTE["text"])
    game.screen.blit(menu_title, (right_card.x + 20, right_card.y + 18))

    # Subtitle com quebra de linha segura
    subtitle_text = "O acampamento espera. O mundo não espera."
    game.draw_wrapped_text(
        game.ui_small_font,
        subtitle_text,
        PALETTE["muted"],
        right_card.x + 20,
        right_card.y + 48,
        right_card.width - 40,
        line_gap=1,
    )

    if not game.title_settings_open:
        for index, action in enumerate(game.title_actions):
            row = layout["action_rows"][index]
            active = game.title_action_index == index or row.collidepoint(mouse_pos)
            pygame.draw.rect(game.screen, (52, 68, 72) if active else PALETTE["ui_panel"], row, border_radius=14)
            pygame.draw.rect(game.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], row, 1, border_radius=14)

            # Label do botão com truncamento se necessário
            label_text = str(action)
            label = game.body_font.render(label_text, True, PALETTE["text"])
            max_label_width = row.width - 32
            if label.get_width() > max_label_width:
                label = game.body_font.render(label_text[:18] + "...", True, PALETTE["text"])
            game.screen.blit(label, (row.x + 16, row.y + 9))

            # Prompt com bounds garantidos
            if action == "Continuar":
                prompt_text = "Retomar sua jornada. Seu acampamento espera."
            elif action == "Novo Jogo":
                prompt_text = "Começar do zero. Nova história. Nova chance."
            elif action == "Configurações":
                prompt_text = "Ajustar som, vídeo e interface."
            else:
                prompt_text = "Fechar o jogo e voltar ao mundo real."

            # Clip para garantir que o prompt não ultrapasse o botão
            prompt_y = row.y + 27
            max_prompt_y = row.bottom - 4
            if prompt_y < max_prompt_y:
                previous_clip = game.screen.get_clip()
                game.screen.set_clip(pygame.Rect(row.x + 16, prompt_y, row.width - 32, max_prompt_y - prompt_y))
                game.draw_wrapped_text(
                    game.ui_small_font,
                    prompt_text,
                    PALETTE["muted"],
                    row.x + 16,
                    prompt_y,
                    row.width - 32,
                    line_gap=0,
                )
                game.screen.set_clip(previous_clip)
    else:
        settings_panel = layout["settings_panel"]
        game.draw_panel(settings_panel)
        settings_title = game.heading_font.render("Configurações", True, PALETTE["text"])

        # Subtitle com quebra de linha segura
        settings_subtitle_text = "Use -/+ ou A/D para ajustar."
        settings_subtitle = game.ui_small_font.render(settings_subtitle_text, True, PALETTE["muted"])

        back_hover = layout["settings_back"].collidepoint(mouse_pos)
        pygame.draw.rect(
            game.screen,
            (70, 84, 88) if back_hover else PALETTE["ui_panel"],
            layout["settings_back"],
            border_radius=10,
        )
        pygame.draw.rect(game.screen, PALETTE["ui_line"], layout["settings_back"], 1, border_radius=10)
        back_text = game.ui_small_font.render("Voltar", True, PALETTE["text"])

        # Bounds garantidos para títulos
        title_y = settings_panel.y + 16
        max_title_y = settings_panel.y + 40
        if title_y < max_title_y:
            game.screen.blit(settings_title, (settings_panel.x + 18, title_y))

        subtitle_y = settings_panel.y + 46
        max_subtitle_y = settings_panel.y + 62
        if subtitle_y < max_subtitle_y:
            game.screen.blit(settings_subtitle, (settings_panel.x + 18, subtitle_y))

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

            # Label com truncamento se necessário
            max_label_width = item["value"].x - row.x - 16
            left = game.ui_small_font.render(label, True, PALETTE["text"])
            if left.get_width() > max_label_width:
                # Truncar label longo
                truncated_label = label[:18] + "..." if len(label) > 18 else label
                left = game.ui_small_font.render(truncated_label, True, PALETTE["text"])

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
def draw_loading_screen(game, alpha_override: int | None = None) -> None:
    alpha_scale = max(0.0, min(1.0, (alpha_override if alpha_override is not None else 255) / 255))
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 7, 9, int(208 * alpha_scale)))
    game.screen.blit(overlay, (0, 0))

    haze = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    phase = float(getattr(game, "loading_phase", 0.0))
    sway = int((pygame.math.Vector2(1, 0).rotate(phase * 120).x + 1.0) * 36)
    pygame.draw.ellipse(
        haze,
        (184, 122, 72, int(28 * alpha_scale)),
        pygame.Rect(120 - sway, 84, SCREEN_WIDTH - 240, 180),
    )
    pygame.draw.ellipse(
        haze,
        (88, 110, 102, int(22 * alpha_scale)),
        pygame.Rect(90 + sway // 2, SCREEN_HEIGHT - 280, SCREEN_WIDTH - 180, 170),
    )
    game.screen.blit(haze, (0, 0))

    panel = pygame.Rect(0, 0, min(820, SCREEN_WIDTH - 140), 340)
    panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    game.draw_panel(panel, alpha_scale=0.92 * alpha_scale)

    eyebrow = game.small_font.render("TRAVESSIA ENTRE CENAS", True, PALETTE["morale"])
    title = game.title_font.render(str(getattr(game, "loading_title", "Carregando")), True, PALETTE["text"])
    subtitle = game.body_font.render(str(getattr(game, "loading_subtitle", "")), True, PALETTE["accent_soft"])
    eyebrow.set_alpha(int(255 * alpha_scale))
    title.set_alpha(int(255 * alpha_scale))
    subtitle.set_alpha(int(255 * alpha_scale))
    game.screen.blit(eyebrow, (panel.x + 42, panel.y + 30))
    game.screen.blit(title, (panel.x + 38, panel.y + 64))
    game.screen.blit(subtitle, (panel.x + 44, panel.y + 132))

    progress = max(0.0, min(1.0, float(getattr(game, "loading_progress", 0.0))))
    bar = pygame.Rect(panel.x + 42, panel.y + 206, panel.width - 84, 22)
    pygame.draw.rect(game.screen, (18, 24, 26), bar, border_radius=11)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], bar, 1, border_radius=11)
    fill_width = int((bar.width - 6) * progress)
    if fill_width > 0:
        pygame.draw.rect(
            game.screen,
            PALETTE["accent_soft"],
            (bar.x + 3, bar.y + 3, fill_width, bar.height - 6),
            border_radius=9,
        )

    progress_text = game.heading_font.render(f"{int(progress * 100):02d}%", True, PALETTE["text"])
    status_text = game.ui_small_font.render(
        "Nada de tela preta: a clareira continua respirando.",
        True,
        PALETTE["muted"],
    )
    progress_text.set_alpha(int(255 * alpha_scale))
    status_text.set_alpha(int(255 * alpha_scale))
    game.screen.blit(progress_text, (bar.right - progress_text.get_width(), bar.y - 44))
    game.screen.blit(status_text, (panel.x + 44, panel.y + 248))

    tips = (
        "Novo jogo recompõe o mundo base.",
        "Continuar reconstrói o save ativo.",
        "Reiniciar limpa a pressão e volta ao início.",
    )
    tip_y = panel.y + 280
    for line in tips:
        text = game.ui_small_font.render(line, True, PALETTE["muted"])
        text.set_alpha(int(255 * alpha_scale))
        game.screen.blit(text, (panel.x + 44, tip_y))
        tip_y += 22


def draw_runtime_settings_overlay(game) -> None:
    layout = game.gameplay_runtime_layout()
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 6, 8, 186))
    game.screen.blit(overlay, (0, 0))

    panel = layout["panel"]
    game.draw_panel(panel)
    title = game.heading_font.render("Volume em Partida", True, PALETTE["text"])
    subtitle = game.ui_small_font.render("Use M para abrir/fechar. Setas ou clique em - e + ajustam.", True, PALETTE["muted"])
    game.screen.blit(title, (panel.x + 22, panel.y + 20))
    game.screen.blit(subtitle, (panel.x + 22, panel.y + 50))

    mouse_pos = game.input_state.mouse_screen
    close_hover = layout["close"].collidepoint(mouse_pos)
    pygame.draw.rect(game.screen, (70, 84, 88) if close_hover else PALETTE["ui_panel"], layout["close"], border_radius=10)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], layout["close"], 1, border_radius=10)
    close_text = game.ui_small_font.render("Fechar", True, PALETTE["text"])
    game.screen.blit(close_text, close_text.get_rect(center=layout["close"].center))

    for index, ((key, label, _, _, _), item) in enumerate(zip(game.gameplay_setting_entries, layout["setting_rows"])):
        row = item["row"]
        active = game.gameplay_setting_index == index or row.collidepoint(mouse_pos)
        minus_hover = item["minus"].collidepoint(mouse_pos)
        plus_hover = item["plus"].collidepoint(mouse_pos)
        pygame.draw.rect(game.screen, (44, 58, 62) if active else PALETTE["ui_panel"], row, border_radius=12)
        pygame.draw.rect(game.screen, PALETTE["accent_soft"] if active else PALETTE["ui_line"], row, 1, border_radius=12)
        pygame.draw.rect(game.screen, (70, 84, 88) if minus_hover else (54, 66, 70), item["minus"], border_radius=7)
        pygame.draw.rect(game.screen, (70, 84, 88) if plus_hover else (54, 66, 70), item["plus"], border_radius=7)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], item["minus"], 1, border_radius=7)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], item["plus"], 1, border_radius=7)
        pygame.draw.rect(game.screen, (32, 40, 42), item["value"], border_radius=7)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], item["value"], 1, border_radius=7)
        left = game.ui_small_font.render(label, True, PALETTE["text"])
        value = game.ui_small_font.render(game.title_setting_value_label(str(key)), True, PALETTE["morale"] if active else PALETTE["text"])
        minus = game.body_font.render("-", True, PALETTE["text"])
        plus = game.body_font.render("+", True, PALETTE["text"])
        game.screen.blit(left, (row.x + 12, row.y + 6))
        game.screen.blit(value, value.get_rect(center=item["value"].center))
        game.screen.blit(minus, minus.get_rect(center=item["minus"].center))
        game.screen.blit(plus, plus.get_rect(center=item["plus"].center))


def draw_audio_debug_overlay(game) -> None:
    cues = game.audio.debug_cue_names() if hasattr(game.audio, "debug_cue_names") else []
    screen_width, screen_height = game.screen.get_size()
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((3, 5, 7, 204))
    game.screen.blit(overlay, (0, 0))

    panel = pygame.Rect(0, 0, min(760, screen_width - 80), min(660, screen_height - 80))
    panel.center = (screen_width // 2, screen_height // 2)
    game.draw_panel(panel)

    title = game.heading_font.render("Teste de Audio", True, PALETTE["text"])
    subtitle = game.ui_small_font.render("F10 fecha  |  setas/scroll navegam  |  Enter ou clique toca", True, PALETTE["muted"])
    game.screen.blit(title, (panel.x + 22, panel.y + 18))
    game.screen.blit(subtitle, (panel.x + 22, panel.y + 48))

    if not cues:
        text = game.body_font.render("Banco de sons indisponivel.", True, PALETTE["danger_soft"])
        game.screen.blit(text, text.get_rect(center=panel.center))
        return

    row_height = 28
    visible_rows = max(1, (panel.height - 118) // row_height)
    selected = max(0, min(len(cues) - 1, int(getattr(game, "audio_debug_index", 0))))
    scroll = max(0, min(int(getattr(game, "audio_debug_scroll", 0)), max(0, len(cues) - visible_rows)))
    list_top = panel.y + 74
    list_rect = pygame.Rect(panel.x + 18, list_top, panel.width - 36, visible_rows * row_height)
    pygame.draw.rect(game.screen, (16, 22, 24), list_rect, border_radius=12)
    pygame.draw.rect(game.screen, PALETTE["ui_line"], list_rect, 1, border_radius=12)

    for row in range(visible_rows):
        index = scroll + row
        if index >= len(cues):
            break
        rect = pygame.Rect(list_rect.x + 6, list_rect.y + 6 + row * row_height, list_rect.width - 12, row_height - 4)
        cue = cues[index]
        active = index == selected
        if active:
            pygame.draw.rect(game.screen, (50, 66, 70), rect, border_radius=7)
            pygame.draw.rect(game.screen, PALETTE["accent_soft"], rect, 1, border_radius=7)
        category = "musica" if cue.startswith("music_") else ("ambiente" if cue.startswith(("ambient_", "zombie_")) else "sfx")
        label = game.ui_small_font.render(f"{index + 1:02d}. {cue}", True, PALETTE["text"] if active else PALETTE["muted"])
        tag = game.ui_small_font.render(category, True, PALETTE["morale"] if category == "ambiente" else PALETTE["accent_soft"])
        game.screen.blit(label, (rect.x + 10, rect.y + 5))
        game.screen.blit(tag, (rect.right - tag.get_width() - 10, rect.y + 5))

    footer = game.ui_small_font.render(f"{selected + 1}/{len(cues)} selecionado: {cues[selected]}", True, PALETTE["accent_soft"])
    game.screen.blit(footer, (panel.x + 22, panel.bottom - 32))


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
        "Dicas essenciais para entrar na primeira vigia. Enter avança, Esc pula.",
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
        (layout["next_button"], "Entrar no Jogo" if last_page else "Próxima", next_hover),
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
    reason = str(
        getattr(
            game,
            "game_over_reason",
            "A fogueira se apagou, a moral quebrou ou o chefe não resistiu.",
        )
        or "A fogueira se apagou, a moral quebrou ou o chefe não resistiu."
    )
    retry = game.body_font.render("Pressione Enter para recomeçar a vigia.", True, PALETTE["morale"])
    game.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 78)))
    reason_lines = game.wrap_text_lines(game.body_font, reason, panel.width - 84)
    reason_line_height = game.body_font.get_linesize()
    reason_total_height = len(reason_lines) * reason_line_height + max(0, len(reason_lines) - 1) * 2
    reason_y = panel.y + 126 - reason_total_height // 2
    for index, line in enumerate(reason_lines):
        subtitle = game.body_font.render(line, True, PALETTE["text"])
        game.screen.blit(
            subtitle,
            subtitle.get_rect(center=(panel.centerx, reason_y + index * (reason_line_height + 2))),
        )
    game.screen.blit(retry, retry.get_rect(center=(panel.centerx, panel.y + 188)))


def draw_exit_prompt(game) -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 6, 8, 186))
    game.screen.blit(overlay, (0, 0))
    layout = game.exit_prompt_layout()
    panel = layout["panel"]
    game.draw_panel(panel)
    title = game.heading_font.render("Voltar ao Menu Principal?", True, PALETTE["text"])
    game.screen.blit(title, (panel.x + 26, panel.y + 18))

    subtitle_y = game.draw_wrapped_text(
        game.body_font,
        "Escolha se quer salvar antes de voltar ao menu principal.",
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
