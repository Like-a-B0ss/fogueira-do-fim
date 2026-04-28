from __future__ import annotations

import pygame

from ..entities import Survivor
from ..core.config import FOCUS_LABELS, PALETTE, clamp


def draw_chat_panel(game) -> None:
    """Desenha o painel inferior de conversa e historico do acampamento."""
    layout = game.chat_panel_layout()
    panel = layout["panel"]
    viewport = layout["viewport"]

    # Renderizar estado colapsado
    if layout.get("collapsed", False):
        pygame.draw.rect(game.screen, PALETTE["ui_panel"], panel, border_radius=12)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], panel, 1, border_radius=12)

        # Ícone/título colapsado
        icon = "💬" if not game.chat_messages else "📨"
        title = game.body_font.render(f"{icon} Vozes da Clareira", True, PALETTE["text"])

        # Indicador de mensagens não lidas
        if game.chat_messages:
            indicator_pos = (panel.x + panel.width - 28, panel.y + panel.height // 2)
            pygame.draw.circle(game.screen, PALETTE["accent_soft"], (int(indicator_pos[0]), int(indicator_pos[1])), 6)
            count = len(game.chat_messages)
            count_text = game.small_font.render(str(min(count, 9)), True, (20, 20, 20))
            count_rect = count_text.get_rect(center=indicator_pos)
            game.screen.blit(count_text, count_rect)

        # Hint para expandir
        hint = game.small_font.render("Clique para expandir", True, PALETTE["muted"])

        title_rect = title.get_rect(center=(panel.x + 80, panel.centery))
        game.screen.blit(title, title_rect)
        hint_rect = hint.get_rect(center=(panel.x + panel.width - 100, panel.centery))
        game.screen.blit(hint, hint_rect)

        return

    # Renderizar estado expandido
    game.draw_panel(panel)
    survivor = game.active_dialog_survivor()
    if survivor:
        title = game.heading_font.render(f"Falando com {survivor.name}", True, PALETTE["text"])
        subtitle_base = f"{survivor.role}  |  {survivor.primary_trait()}  |  estado {survivor.state_label}"
        subtitle_max = panel.width - title.get_width() - 54
        subtitle_text = game.fit_text_to_width(game.ui_small_font, subtitle_base, max(180, subtitle_max))
    else:
        title = game.heading_font.render("Vozes da Clareira", True, PALETTE["text"])
        subtitle_text = game.fit_text_to_width(
            game.ui_small_font,
            "Aproxime-se de um morador e aperte E para conversar direto.",
            panel.width - title.get_width() - 54,
        )
    subtitle = game.ui_small_font.render(subtitle_text, True, PALETTE["muted"])
    game.screen.blit(title, (panel.x + 14, panel.y + 8))
    subtitle_x = panel.x + 20 + title.get_width() + 14
    game.screen.blit(subtitle, (subtitle_x, panel.y + 13))

    # Botão para colapsar
    collapse_hint = game.small_font.render("▲ Clique para colapsar", True, PALETTE["muted"])
    game.screen.blit(collapse_hint, (panel.right - collapse_hint.get_width() - 14, panel.y + 8))

    # Resto da renderização (apenas quando expandido)
    previous_clip = game.screen.get_clip()
    game.screen.set_clip(viewport)
    y = viewport.y - int(game.chat_max_scroll() - game.chat_scroll)
    for entry in game.chat_messages:
        speaker = str(entry.get("speaker", "radio"))
        label = f"{speaker}: {entry.get('text', '')}"
        color = tuple(entry.get("color", PALETTE["text"]))
        lines = game.wrap_text_lines(game.ui_small_font, label, viewport.width - 18)
        line_height = game.ui_small_font.get_linesize()
        block_height = len(lines) * line_height + max(0, len(lines) - 1) * 2 + 8
        if y + block_height >= viewport.y - 8 and y <= viewport.bottom + 8:
            for index, line in enumerate(lines):
                rendered = game.ui_small_font.render(line, True, color if index == 0 else PALETTE["muted"])
                game.screen.blit(rendered, (viewport.x + 4, y + index * (line_height + 2)))
        y += block_height + 4
    game.screen.set_clip(previous_clip)
    pygame.draw.rect(game.screen, (18, 22, 24), viewport, 1, border_radius=10)

    scroll_track = layout["scrollbar"]
    pygame.draw.rect(game.screen, (28, 36, 38), scroll_track, border_radius=6)
    max_scroll = game.chat_max_scroll()
    if max_scroll > 0:
        total_height = max(viewport.height, game.chat_content_height())
        thumb_height = max(26, int(viewport.height * (viewport.height / max(1, total_height))))
        thumb_range = max(0, scroll_track.height - thumb_height)
        thumb_ratio = game.chat_scroll / max_scroll if max_scroll > 0 else 0.0
        thumb = pygame.Rect(
            scroll_track.x,
            scroll_track.y + int(thumb_range * thumb_ratio),
            scroll_track.width,
            thumb_height,
        )
        pygame.draw.rect(game.screen, PALETTE["accent_soft"], thumb, border_radius=6)

    mouse_pos = game.input_state.mouse_screen
    if survivor:
        for rect, option in zip(layout["buttons"], game.conversation_options_for_survivor(survivor)):
            hover = rect.collidepoint(mouse_pos)
            pygame.draw.rect(game.screen, (42, 54, 58) if hover else (30, 38, 41), rect, border_radius=9)
            pygame.draw.rect(game.screen, PALETTE["accent_soft"] if hover else PALETTE["ui_line"], rect, 1, border_radius=9)
            label = game.ui_small_font.render(
                game.fit_text_to_width(game.ui_small_font, str(option["label"]), rect.width - 10),
                True,
                PALETTE["text"],
            )
            game.screen.blit(label, label.get_rect(center=rect.center))
    else:
        # Hint com bounds garantidos
        hint_text = "Historico do campo. Conversa aberta por morador."
        hint = game.ui_small_font.render(hint_text, True, PALETTE["muted"])
        # Verificar se cabe no espaço
        hint_x = panel.x + 16
        hint_y = panel.bottom - 28
        if hint_x + hint.get_width() <= panel.right - 8:
            game.screen.blit(hint, (hint_x, hint_y))


def draw_survivor_card(
    game,
    x: int,
    y: int,
    width: int,
    height: int,
    survivor: Survivor,
) -> None:
    rect = pygame.Rect(x, y, width, height)
    selected = getattr(game, "society_selected_survivor_name", None) == survivor.name
    bg = PALETTE["ui_panel"] if survivor.is_alive() else (42, 26, 26)
    if getattr(survivor, "on_expedition", False):
        bg = (30, 42, 54)
    elif survivor.conflict_cooldown > 0:
        bg = (58, 34, 34)
    elif survivor.exhaustion > 72:
        bg = (44, 38, 28)
    elif getattr(survivor, "insanity", 0.0) > 70:
        bg = (56, 46, 24)
    pygame.draw.rect(game.screen, bg, rect, border_radius=12)
    pygame.draw.rect(
        game.screen,
        PALETTE["accent_soft"] if selected else PALETTE["ui_line"],
        rect,
        1,
        border_radius=12,
    )
    avatar_y = y + 22 if selected else y + height // 2
    pygame.draw.circle(game.screen, survivor.color, (x + 18, avatar_y), 8)
    name_text = game.fit_text_to_width(game.body_font, survivor.name, width - 120)
    name = game.body_font.render(name_text, True, PALETTE["text"])
    role_label = f"{survivor.role} / {survivor.primary_trait()}"
    if getattr(survivor, "assigned_building_kind", None) == "torre":
        role_label += " / torre"
    elif getattr(survivor, "assigned_building_kind", None) == "horta":
        role_label += " / horta"
    elif getattr(survivor, "assigned_building_kind", None) == "anexo":
        role_label += " / anexo"
    elif getattr(survivor, "assigned_building_kind", None) == "serraria":
        role_label += " / serraria"
    elif getattr(survivor, "assigned_building_kind", None) == "cozinha":
        role_label += " / cozinha"
    elif getattr(survivor, "assigned_building_kind", None) == "enfermaria":
        role_label += " / enfermaria"
    role = game.ui_small_font.render(game.fit_text_to_width(game.ui_small_font, role_label, width - 138), True, PALETTE["muted"])
    state_label = survivor.state_label
    if getattr(survivor, "on_expedition", False):
        state_label = "em expedição"
    elif survivor.conflict_cooldown > 0:
        rival = game.rival_name(survivor)
        state_label = f"briga com {rival.lower()}" if rival else "apos briga"
    elif getattr(survivor, "insanity", 0.0) > 82:
        state_label = "quase rompendo"
    elif getattr(survivor, "insanity", 0.0) > 68:
        state_label = "rondando a base"
    elif survivor.exhaustion > 72:
        state_label = "exausto"
    elif survivor.trust_leader < 32:
        state_label = "desconfiado"
    state = game.ui_small_font.render(
        game.fit_text_to_width(game.ui_small_font, state_label if survivor.is_alive() else "perdido", width - 116),
        True,
        PALETTE["danger_soft"] if not survivor.is_alive() else PALETTE["text"],
    )
    game.screen.blit(name, (x + 34, y + 4))
    game.screen.blit(role, (x + 34, y + 22))
    game.screen.blit(state, (x + 34, y + 38))

    toggle_text = "-" if selected else "+"
    toggle = game.body_font.render(toggle_text, True, PALETTE["muted"])
    game.screen.blit(toggle, toggle.get_rect(topright=(rect.right - 12, rect.y + 4)))

    if not selected:
        summary = f"{survivor.state_label}  |  moral {int(survivor.morale)}"
        summary_surface = game.small_font.render(game.fit_text_to_width(game.small_font, summary, width - 112), True, PALETTE["muted"])
        game.screen.blit(summary_surface, (x + 34, y + 52))
        return

    detail_top = y + 64
    detail_left = x + 16
    bar_width = width - 32

    def draw_inline_bar(offset_y: int, label: str, ratio: float, color: tuple[int, int, int], value_text: str) -> None:
        label_surface = game.small_font.render(label, True, PALETTE["muted"])
        value_surface = game.small_font.render(value_text, True, PALETTE["text"])
        bar_y = detail_top + offset_y
        game.screen.blit(label_surface, (detail_left, bar_y))
        game.screen.blit(value_surface, (rect.right - 16 - value_surface.get_width(), bar_y))
        track = pygame.Rect(detail_left, bar_y + 14, bar_width, 10)
        pygame.draw.rect(game.screen, (18, 22, 24), track, border_radius=6)
        fill = max(6, int(track.width * clamp(ratio, 0, 1))) if ratio > 0 else 0
        if fill > 0:
            pygame.draw.rect(game.screen, color, (track.x, track.y, fill, track.height), border_radius=6)
        pygame.draw.rect(game.screen, PALETTE["ui_line"], track, 1, border_radius=6)

    draw_inline_bar(0, "Vida", survivor.health / max(1.0, survivor.max_health), PALETTE["danger_soft"], f"{int(survivor.health)}/{int(survivor.max_health)}")
    draw_inline_bar(30, "Energia", survivor.energy / 100, PALETTE["energy"], f"{int(survivor.energy)}")
    draw_inline_bar(60, "Moral", survivor.morale / 100, PALETTE["morale"], f"{int(survivor.morale)}")
    draw_inline_bar(90, "Confianca", survivor.trust_leader / 100, PALETTE["accent_soft"], f"{int(survivor.trust_leader)}")


def current_objectives(game) -> list[str]:
    """Mostra apenas tarefas persistentes do chefe, sem objetivos genericos."""
    task_directives = []
    if hasattr(game, "active_chief_tasks"):
        if hasattr(game, "generate_chief_tasks"):
            game.generate_chief_tasks()
        for task in game.active_chief_tasks():
            if task.completed and task.claimed:
                continue
            resource_reward = {
                key: int(value)
                for key, value in dict(task.reward).items()
                if key in {"logs", "wood", "food", "herbs", "scrap", "meals", "medicine"} and int(value) > 0
            }
            reward = game.bundle_summary(resource_reward) if resource_reward else ""
            suffix = f" Recompensa: {reward}." if reward else ""
            task_directives.append(f"Tarefa: {task.title}. {task.description}{suffix}")
            if len(task_directives) >= 3:
                break
    return task_directives or ["Sem tarefas ativas no momento."]
