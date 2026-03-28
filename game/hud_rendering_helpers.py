from __future__ import annotations

import pygame

from .actors import Survivor
from .config import FOCUS_LABELS, PALETTE, ROLE_COLORS, SCREEN_HEIGHT, SCREEN_WIDTH, clamp, format_clock


def draw_chat_panel(game) -> None:
    """Desenha o painel inferior de conversa e historico do acampamento."""
    layout = game.chat_panel_layout()
    panel = layout["panel"]
    viewport = layout["viewport"]
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
        hint = game.ui_small_font.render(
            "O historico do campo segue aqui. A conversa e aberta morador por morador.",
            True,
            PALETTE["muted"],
        )
        game.screen.blit(hint, (panel.x + 16, panel.bottom - 28))


def draw_hud(game) -> None:
    """Desenha os paineis centrais da HUD do gameplay."""
    compact_mode = bool(getattr(game, "hud_compact_mode", False))
    ribbon = pygame.Rect(SCREEN_WIDTH // 2 - 280, 16, 560, 66)
    game.draw_panel(ribbon)
    ribbon_title_text = game.fit_text_to_width(
        game.body_font,
        f"{game.weather_label}  |  {game.daylight_phase_label()}  |  tensao {game.tension_label()}  |  zumbis {len(game.zombies)}",
        ribbon.width - 36,
    )
    ribbon_sub_text = game.fit_text_to_width(
        game.ui_small_font,
        f"{game.weather_mood_label()}  |  Noite de horda ativa"
        if getattr(game, "horde_active", False)
        else (game.expedition_status_text(short=True) or f"{game.current_region_label} sob {game.weather_mood_label()}"),
        ribbon.width - 44,
    )
    ribbon_title = game.body_font.render(ribbon_title_text, True, PALETTE["text"])
    ribbon_sub = game.ui_small_font.render(
        ribbon_sub_text,
        True,
        PALETTE["danger_soft"] if getattr(game, "horde_active", False) else PALETTE["muted"],
    )
    game.screen.blit(ribbon_title, ribbon_title.get_rect(center=(ribbon.centerx, ribbon.y + 20)))
    game.screen.blit(ribbon_sub, ribbon_sub.get_rect(center=(ribbon.centerx, ribbon.y + 44)))
    toggle_rect = game.hud_toggle_rect()
    hover = toggle_rect.collidepoint(game.input_state.mouse_screen)
    pygame.draw.rect(game.screen, (62, 80, 84) if hover else PALETTE["ui_panel"], toggle_rect, border_radius=8)
    pygame.draw.rect(game.screen, PALETTE["accent_soft"] if hover else PALETTE["ui_line"], toggle_rect, 1, border_radius=8)
    toggle_label = "+" if compact_mode else "-"
    toggle_text = game.body_font.render(toggle_label, True, PALETTE["text"])
    game.screen.blit(toggle_text, toggle_text.get_rect(center=toggle_rect.center))

    panel = pygame.Rect(18, 16, 358, 182 if compact_mode else 248)
    game.draw_panel(panel)
    title = game.heading_font.render("Acampamento da Clareira", True, PALETTE["text"])
    game.screen.blit(title, (panel.x + 18, panel.y + 14))

    subtitle = game.ui_small_font.render(
        f"Dia {game.day}  |  {format_clock(game.time_minutes)}  |  foco {FOCUS_LABELS[game.focus_mode]}",
        True,
        PALETTE["muted"],
    )
    game.screen.blit(subtitle, (panel.x + 18, panel.y + 44))
    info_y = game.draw_wrapped_text(
        game.ui_small_font,
        f"Regiao atual: {game.current_region_label}",
        PALETTE["accent_soft"],
        panel.x + 18,
        panel.y + 62,
        panel.width - 36,
        line_gap=0,
    ) + 2
    info_y = game.draw_wrapped_text(
        game.ui_small_font,
        f"Bioma {game.current_biome_label}  |  boss {game.current_zone_boss_label}",
        PALETTE["muted"],
        panel.x + 18,
        info_y,
        panel.width - 36,
        line_gap=0,
    ) + 2
    info_bottom = game.draw_wrapped_text(
        game.ui_small_font,
        f"Base {game.camp_level + 1}  |  fase {game.economy_phase_label()}  |  camas {len(game.survivors)}/{game.total_bed_capacity()}  |  fogo {game.bonfire_stage()}",
        PALETTE["muted"],
        panel.x + 18,
        info_y,
        panel.width - 36,
        line_gap=0,
    )

    if compact_mode:
        game.draw_resource_meter(panel.x + 18, panel.y + 112, 72, game.logs, "Toras", (170, 130, 78))
        game.draw_resource_meter(panel.x + 102, panel.y + 112, 72, game.wood, "Tabuas", PALETTE["accent_soft"])
        game.draw_resource_meter(panel.x + 186, panel.y + 112, 72, game.scrap, "Sucata", ROLE_COLORS["mensageiro"])
        game.draw_resource_meter(panel.x + 270, panel.y + 112, 72, game.meals, "Refeic.", PALETTE["morale"])
        game.draw_resource_bar(panel.x + 18, panel.y + 166, 152, 12, game.bonfire_heat / 100, "Chama", PALETTE["light"])
        game.draw_resource_bar(panel.x + 190, panel.y + 166, 152, 12, game.bonfire_ember_bed / 100, "Brasa", (214, 122, 78))
    else:
        meter_y = max(panel.y + 128, info_bottom + 10)
        second_row_y = meter_y + 50
        bar_y = second_row_y + 50
        game.draw_resource_meter(panel.x + 18, meter_y, 72, game.logs, "Toras", (170, 130, 78))
        game.draw_resource_meter(panel.x + 102, meter_y, 72, game.wood, "Tabuas", PALETTE["accent_soft"])
        game.draw_resource_meter(panel.x + 186, meter_y, 72, game.food, "Insumos", PALETTE["heal"])
        game.draw_resource_meter(panel.x + 270, meter_y, 72, game.herbs, "Ervas", (124, 176, 102))
        game.draw_resource_meter(panel.x + 18, second_row_y, 72, game.scrap, "Sucata", ROLE_COLORS["mensageiro"])
        game.draw_resource_meter(panel.x + 102, second_row_y, 72, game.meals, "Refeic.", PALETTE["morale"])
        game.draw_resource_meter(panel.x + 186, second_row_y, 72, game.medicine, "Remed.", (194, 130, 130))
        game.draw_resource_bar(panel.x + 18, bar_y, 152, 12, game.bonfire_heat / 100, "Chama", PALETTE["light"])
        game.draw_resource_bar(panel.x + 190, bar_y, 152, 12, game.bonfire_ember_bed / 100, "Brasa", (214, 122, 78))

    player_panel = pygame.Rect(18, 212 if compact_mode else panel.bottom + 12, 358, 92 if compact_mode else 128)
    game.draw_panel(player_panel)
    heading = game.heading_font.render("Chefe do Acampamento", True, PALETTE["text"])
    game.screen.blit(heading, (player_panel.x + 18, player_panel.y + 14))
    if not compact_mode:
        game.draw_wrapped_text(
            game.ui_small_font,
            "Dormindo e acelerando o tempo" if game.player_sleeping else "E perto da barraca para dormir",
            PALETTE["morale"] if game.player_sleeping else PALETTE["muted"],
            player_panel.x + 18,
            player_panel.y + 40,
            player_panel.width - 36,
            line_gap=0,
        )
        game.draw_resource_bar(player_panel.x + 18, player_panel.y + 68, 320, 14, game.player.health / game.player.max_health, "Vida", PALETTE["danger_soft"])
        game.draw_resource_bar(player_panel.x + 18, player_panel.y + 100, 320, 14, game.player.stamina / game.player.max_stamina, "Folego", PALETTE["energy"])
    else:
        game.draw_resource_bar(player_panel.x + 18, player_panel.y + 42, 320, 12, game.player.health / game.player.max_health, "Vida", PALETTE["danger_soft"])
        game.draw_resource_bar(player_panel.x + 18, player_panel.y + 68, 320, 12, game.player.stamina / game.player.max_stamina, "Folego", PALETTE["energy"])

    society_layout = game.society_panel_layout()
    society_panel = society_layout["panel"]
    game.draw_panel(society_panel)
    mouse_pos = game.input_state.mouse_screen
    header = society_layout["header"]
    toggle = society_layout["toggle"]
    header_hover = header.collidepoint(mouse_pos)
    pygame.draw.rect(
        game.screen,
        (46, 60, 64) if header_hover else PALETTE["ui_panel"],
        header,
        border_radius=14,
    )
    pygame.draw.rect(
        game.screen,
        PALETTE["accent_soft"] if header_hover else PALETTE["ui_line"],
        header,
        1,
        border_radius=14,
    )
    pygame.draw.rect(
        game.screen,
        (72, 88, 92) if toggle.collidepoint(mouse_pos) else (54, 68, 72),
        toggle,
        border_radius=7,
    )
    pygame.draw.rect(game.screen, PALETTE["ui_line"], toggle, 1, border_radius=7)
    toggle_label = "+" if game.society_panel_collapsed else "-"
    toggle_text = game.body_font.render(toggle_label, True, PALETTE["text"])
    game.screen.blit(toggle_text, toggle_text.get_rect(center=toggle.center))

    society_title = game.heading_font.render("Sociedade do Campo", True, PALETTE["text"])
    game.screen.blit(society_title, (society_panel.x + 18, society_panel.y + 14))
    strongest_faction = game.strongest_faction()[0]
    effective_collapsed = game.society_panel_collapsed or compact_mode
    if effective_collapsed:
        compact_text = game.fit_text_to_width(
            game.ui_small_font,
            f"{len(game.survivors)} moradores  |  moral {game.average_morale():.0f}  |  ins {game.average_insanity():.0f}",
            society_panel.width - 64,
        )
        compact_surface = game.ui_small_font.render(compact_text, True, PALETTE["muted"])
        game.screen.blit(compact_surface, (society_panel.x + 18, society_panel.y + 48))
    else:
        line_one = game.fit_text_to_width(
            game.ui_small_font,
            f"moral {game.average_morale():.0f}  |  insanidade {game.average_insanity():.0f}  |  feudos {game.feud_count()}",
            society_panel.width - 64,
        )
        line_two = game.fit_text_to_width(
            game.ui_small_font,
            f"{game.faction_label(strongest_faction)} {game.faction_standing_label(strongest_faction)}",
            society_panel.width - 64,
        )
        game.screen.blit(game.ui_small_font.render(line_one, True, PALETTE["muted"]), (society_panel.x + 18, society_panel.y + 46))
        game.screen.blit(game.ui_small_font.render(line_two, True, PALETTE["muted"]), (society_panel.x + 18, society_panel.y + 66))

        game.clamp_society_scroll()
        viewport = society_layout["viewport"]
        previous_clip = game.screen.get_clip()
        game.screen.set_clip(viewport)
        card_y = viewport.y - int(game.society_scroll)
        for survivor in game.survivors:
            card_height = game.society_card_height(survivor)
            game.draw_survivor_card(viewport.x, card_y, viewport.width, card_height, survivor)
            card_y += game.society_card_step(survivor)
        game.screen.set_clip(previous_clip)

        pygame.draw.rect(game.screen, (18, 22, 24), viewport, 1, border_radius=12)
        scroll_track = society_layout["scrollbar"]
        pygame.draw.rect(game.screen, (28, 36, 38), scroll_track, border_radius=6)
        max_scroll = game.society_max_scroll()
        if max_scroll > 0:
            total_height = max(viewport.height, game.society_content_height())
            thumb_height = max(32, int(viewport.height * (viewport.height / max(1, total_height))))
            thumb_range = max(0, scroll_track.height - thumb_height)
            thumb_ratio = game.society_scroll / max_scroll if max_scroll > 0 else 0.0
            thumb = pygame.Rect(
                scroll_track.x,
                scroll_track.y + int(thumb_range * thumb_ratio),
                scroll_track.width,
                thumb_height,
            )
            pygame.draw.rect(game.screen, PALETTE["accent_soft"], thumb, border_radius=6)
        else:
            pygame.draw.rect(game.screen, (72, 90, 94), scroll_track.inflate(0, -scroll_track.height // 2), border_radius=6)

    if not compact_mode:
        chat_panel = game.chat_panel_layout()["panel"]
        directive_y = society_panel.bottom + 16
        directive_height = max(148, chat_panel.y - directive_y - 14)
        directive_panel = pygame.Rect(SCREEN_WIDTH - 346, directive_y, 328, directive_height)
        game.draw_panel(directive_panel)
        directive_title = game.heading_font.render("Tarefas do Chefe", True, PALETTE["text"])
        game.screen.blit(directive_title, (directive_panel.x + 18, directive_panel.y + 14))
        bullet_y = directive_panel.y + 52
        previous_clip = game.screen.get_clip()
        objective_view = pygame.Rect(directive_panel.x + 14, directive_panel.y + 46, directive_panel.width - 28, directive_panel.height - 58)
        game.screen.set_clip(objective_view)
        for index, line in enumerate(game.current_objectives()[:3]):
            bullet_y = game.draw_wrapped_text(
                game.ui_small_font,
                f"{index + 1}. {line}",
                PALETTE["text"],
                directive_panel.x + 18,
                bullet_y,
                directive_panel.width - 32,
                line_gap=1,
            ) + 8
        game.screen.set_clip(previous_clip)

    if not compact_mode or game.active_dialog_survivor():
        game.draw_chat_panel()

    if not compact_mode:
        chat_panel = game.chat_panel_layout()["panel"]
        info_panel = pygame.Rect(chat_panel.right + 18, chat_panel.y, SCREEN_WIDTH - chat_panel.right - 36, chat_panel.height)
        game.draw_panel(info_panel)
        controls = (
            "WASD mover  |  Shift correr  |  Clique/espaco atacar",
            "E agir  |  botao direito interage  |  F5/F9 salvar",
            game.event_message if game.event_timer > 0 else (game.dynamic_event_summary() or game.expedition_status_text(short=False) or "Chegue perto de um morador e aperte E para conversar."),
        )
        line_y = info_panel.y + 12
        for index, line in enumerate(controls):
            font = game.ui_small_font if index < 2 else game.body_font
            color = PALETTE["text"] if index < 2 else (PALETTE["danger_soft"] if game.active_dynamic_events else PALETTE["muted"])
            line_y = game.draw_wrapped_text(
                font,
                line,
                color,
                info_panel.x + 14,
                line_y,
                info_panel.width - 28,
                line_gap=2,
            ) + 6

    if game.morale_flash > 0:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 224, 154, int(game.morale_flash * 24)))
        game.screen.blit(overlay, (0, 0))


def draw_panel(game, rect: pygame.Rect) -> None:
    """Desenha um painel base reutilizado por toda a interface."""
    panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    contrast = float(game.runtime_settings.get("ui_contrast", 1.0))
    bg_alpha = int(clamp(220 + (contrast - 1.0) * 56, 172, 250))
    line_alpha = int(clamp(126 + (contrast - 1.0) * 84, 92, 224))
    gloss_alpha = int(clamp(12 + (contrast - 1.0) * 16, 6, 32))
    pygame.draw.rect(panel_surface, (*PALETTE["ui_bg"], bg_alpha), panel_surface.get_rect(), border_radius=18)
    pygame.draw.rect(panel_surface, (*PALETTE["ui_line"], line_alpha), panel_surface.get_rect(), 1, border_radius=18)
    pygame.draw.rect(panel_surface, (255, 255, 255, gloss_alpha), pygame.Rect(1, 1, rect.width - 2, 20), border_radius=18)
    pygame.draw.rect(panel_surface, (0, 0, 0, 20), pygame.Rect(2, rect.height - 18, rect.width - 4, 14), border_radius=16)
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
        state_label = "em expedicao"
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

    detail_top = y + 60
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
    draw_inline_bar(28, "Energia", survivor.energy / 100, PALETTE["energy"], f"{int(survivor.energy)}")
    draw_inline_bar(56, "Moral", survivor.morale / 100, PALETTE["morale"], f"{int(survivor.morale)}")
    draw_inline_bar(84, "Confianca", survivor.trust_leader / 100, PALETTE["accent_soft"], f"{int(survivor.trust_leader)}")


def current_objectives(game) -> list[str]:
    """Resume as prioridades imediatas do chefe conforme o estado do mundo."""
    weakest = game.weakest_barricade_health()
    unresolved = len(game.unresolved_interest_points())
    active_event = game.active_dynamic_event()
    current_region = game.current_named_region()
    directives = []
    if active_event:
        directives.append(f"Crise ativa: {active_event.label}")
        if active_event.kind == "doenca":
            directives.append("Aproxime-se do doente com E e use a enfermaria para segurar a febre.")
        elif active_event.kind == "incendio":
            directives.append("Corra ate o foco do incendio e interaja antes que a estrutura ceda.")
        elif active_event.kind == "alarme":
            directives.append("Chegue na cerca que tremeu e use E para segurar a linha antes do rombo.")
        elif active_event.kind == "expedicao":
            directives.append("Siga o foguete vermelho na trilha e entregue socorro antes da equipe quebrar.")
        elif active_event.kind == "faccao":
            directives.append("E escolhe a saida humana. Q escolhe a saida dura e pragmatica.")
        elif active_event.kind == "abrigo":
            directives.append("Va ate o limite da mata e decida se ha espaco para acolher o forasteiro.")
        else:
            directives.append("Encontre o morador em crise e use a sua presenca para impedir a perda.")
        return directives[:3]
    if game.active_expedition:
        directives.append(game.expedition_status_text(short=False) or "A equipe esta fora da base.")
        if any(getattr(survivor, "expedition_downed", False) for survivor in game.expedition_members()):
            directives.append("Ha gente caida na trilha. Chegue perto e use E para por o esquadrao de pe.")
        elif str(game.active_expedition.get("skirmish_state", "")) == "active":
            directives.append("A coluna travou combate na trilha. Intercepte os mortos antes que a equipe quebre.")
        elif not bool(game.active_expedition.get("escort_bonus", False)):
            directives.append("Acompanhe a caravana ate a borda da clareira para reduzir o risco da rota.")
    phase = game.economy_phase_key()
    if phase == "early":
        directives.append("Fase de escassez: segure o estoque curto e aceite que a base ainda nao produz bem.")
    elif phase == "mid":
        directives.append("Fase de estabilizacao: serraria, cozinha e enfermaria precisam girar todo amanhecer.")
    else:
        directives.append("Fase de expedicoes: a base consome mais e o mapa distante virou fonte principal.")
    if game.bonfire_heat < 28 or game.bonfire_ember_bed < 18:
        directives.append("Reacenda a fogueira antes que o campo fique so em brasas.")
    else:
        directives.append("Circule pelo campo e sustente a presenca do lider.")
    if game.logs < 10:
        directives.append("Derrube arvores para encher o estoque de toras antes do entardecer.")
    elif not game.buildings_of_kind("serraria") and game.logs > 0:
        directives.append("Use a oficina para cortar algumas tabuas e destravar a serraria.")
    elif game.wood < 12:
        directives.append("Passe toras pela serraria para levantar tabuas de construcao.")
    elif current_region and current_region.get("boss_blueprint") and not current_region.get("boss_defeated"):
        boss = game.zone_boss_for_region(tuple(current_region["key"]))
        if boss:
            directives.append(f"{boss.boss_name} domina a regiao. Bata, recue e nao lute cansado.")
        else:
            directives.append(f"{current_region['name']} guarda {current_region['boss_blueprint']['name']}. Entre com estoque pronto.")
    if game.spare_beds() <= 0 and game.camp_level < game.max_camp_level:
        log_cost, scrap_cost = game.expansion_cost()
        directives.append(f"Leve {log_cost} toras e {scrap_cost} sucata para ampliar a oficina.")
    elif game.spare_beds() > 0 and len(game.survivors) < game.total_bed_capacity():
        directives.append("Mantenha moral e defesa altas para atrair novos moradores.")
    elif not game.buildings_of_kind("serraria"):
        directives.append("Corte tabuas na oficina e depois erga uma serraria para ganhar escala.")
    elif not game.buildings_of_kind("cozinha"):
        directives.append("Monte uma cozinha para converter insumos em refeicoes de verdade.")
    elif not game.buildings_of_kind("enfermaria"):
        directives.append("Levante uma enfermaria para estabilizar feridos e fabricar remedios.")
    if unresolved > 0:
        directives.append(f"Explore {unresolved} sinal(is) perdidos alem da nevoa do mapa.")
    elif current_region and current_region.get("boss_defeated"):
        directives.append("A zona atual foi limpa. Avance para nomear outra regiao e achar um novo boss.")
    elif weakest < 55:
        directives.append("Reforce a palicada mais ferida antes da proxima investida.")
    elif game.average_insanity() > 62:
        directives.append("A insanidade do grupo subiu. Fogo, comida e presenca perto das barracas viraram prioridade.")
    elif game.average_trust() < 46:
        directives.append("A confianca no lider caiu. Circule pelo campo e reorganize a sociedade.")
    elif game.feud_count() > 0:
        directives.append("Existe atrito no grupo. Mantenha comida, fogo e presenca para evitar mais brigas.")
    elif min(game.faction_standings.values()) < -24:
        directives.append("Uma faccao humana esta azedando com a base. Pese bem a proxima decisao moral.")
    elif game.average_health() < 72 and game.can_treat_infirmary():
        directives.append("Leve os feridos para a enfermaria e preserve as ervas do estoque.")
    elif game.best_expedition_region() and not game.active_expedition and game.player.pos.distance_to(game.radio_pos) < 220:
        directives.append(f"Use o radio para enviar uma equipe a {game.best_expedition_region()['name']}.")
    else:
        directives.append("Colete recursos externos para o proximo amanhecer.")
    if game.is_night:
        directives.append("Segure os zumbis no anel defensivo." + (" Ha uma horda ativa nesta noite." if getattr(game, "horde_active", False) else ""))
    else:
        directives.append(f"Defina o foco comunitario com 1-4. Atual: {FOCUS_LABELS[game.focus_mode]}.")
    return directives[:3]
