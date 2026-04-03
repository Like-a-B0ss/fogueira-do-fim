from __future__ import annotations

import pygame

from ..core.config import FOCUS_LABELS, PALETTE, ROLE_COLORS, SCREEN_HEIGHT, SCREEN_WIDTH, format_clock


def draw_hud(game) -> None:
    """Desenha os paineis centrais da HUD do gameplay."""
    compact_mode = bool(getattr(game, "hud_compact_mode", False))
    draw_ribbon(game, compact_mode)
    camp_panel = draw_camp_panel(game, compact_mode)
    player_panel = draw_player_panel(game, compact_mode, camp_panel)
    society_panel = draw_society_panel(game, compact_mode)
    if not compact_mode:
        draw_directive_panel(game, society_panel)
    if not compact_mode or game.active_dialog_survivor():
        game.draw_chat_panel()
    if not compact_mode:
        draw_info_panel(game)
    if game.morale_flash > 0:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 224, 154, int(game.morale_flash * 24)))
        game.screen.blit(overlay, (0, 0))


def draw_ribbon(game, compact_mode: bool) -> None:
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


def draw_camp_panel(game, compact_mode: bool) -> pygame.Rect:
    panel_width = 358
    panel_height = 182 if compact_mode else 248
    panel_x = 18
    panel_y = 16
    panel_inner_width = panel_width - 36
    region_text = f"Regiao atual: {game.current_region_label}"
    biome_text = f"Bioma {game.current_biome_label}  |  boss {game.current_zone_boss_label}"
    base_text = (
        f"Base {game.camp_level + 1}  |  fase {game.economy_phase_label()}  |  "
        f"camas {len(game.survivors)}/{game.total_bed_capacity()}  |  fogo {game.bonfire_stage()}"
    )
    if not compact_mode:
        line_height = game.ui_small_font.get_linesize()
        info_height = (
            len(game.wrap_text_lines(game.ui_small_font, region_text, panel_inner_width)) * line_height
            + len(game.wrap_text_lines(game.ui_small_font, biome_text, panel_inner_width)) * line_height
            + len(game.wrap_text_lines(game.ui_small_font, base_text, panel_inner_width)) * line_height
            + 4
        )
        estimated_info_bottom = panel_y + 62 + info_height
        estimated_meter_y = max(panel_y + 128, estimated_info_bottom + 10)
        estimated_bar_y = estimated_meter_y + 100
        panel_height = max(panel_height, estimated_bar_y - panel_y + 34)
    panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
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
        region_text,
        PALETTE["accent_soft"],
        panel.x + 18,
        panel.y + 62,
        panel.width - 36,
        line_gap=0,
    ) + 2
    info_y = game.draw_wrapped_text(
        game.ui_small_font,
        biome_text,
        PALETTE["muted"],
        panel.x + 18,
        info_y,
        panel.width - 36,
        line_gap=0,
    ) + 2
    info_bottom = game.draw_wrapped_text(
        game.ui_small_font,
        base_text,
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
    return panel


def draw_player_panel(game, compact_mode: bool, camp_panel: pygame.Rect) -> pygame.Rect:
    player_panel = pygame.Rect(18, 212 if compact_mode else camp_panel.bottom + 16, 358, 92 if compact_mode else 154)
    game.draw_panel(player_panel)
    heading = game.heading_font.render("Chefe do Acampamento", True, PALETTE["text"])
    game.screen.blit(heading, (player_panel.x + 18, player_panel.y + 14))
    if not compact_mode:
        status_bottom = game.draw_wrapped_text(
            game.ui_small_font,
            "Dormindo e acelerando o tempo" if game.player_sleeping else "E perto da barraca para dormir",
            PALETTE["morale"] if game.player_sleeping else PALETTE["muted"],
            player_panel.x + 18,
            player_panel.y + 40,
            player_panel.width - 36,
            line_gap=0,
        )
        health_bar_y = max(player_panel.y + 82, status_bottom + 14)
        stamina_bar_y = health_bar_y + 34
        game.draw_resource_bar(
            player_panel.x + 18,
            health_bar_y,
            320,
            14,
            game.player.health / game.player.max_health,
            "Vida",
            PALETTE["danger_soft"],
        )
        game.draw_resource_bar(
            player_panel.x + 18,
            stamina_bar_y,
            320,
            14,
            game.player.stamina / game.player.max_stamina,
            "Folego",
            PALETTE["energy"],
        )
    else:
        game.draw_resource_bar(player_panel.x + 18, player_panel.y + 42, 320, 12, game.player.health / game.player.max_health, "Vida", PALETTE["danger_soft"])
        game.draw_resource_bar(player_panel.x + 18, player_panel.y + 68, 320, 12, game.player.stamina / game.player.max_stamina, "Folego", PALETTE["energy"])
    return player_panel


def draw_society_panel(game, compact_mode: bool) -> pygame.Rect:
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
    return society_panel


def draw_directive_panel(game, society_panel: pygame.Rect) -> None:
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


def draw_info_panel(game) -> None:
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








