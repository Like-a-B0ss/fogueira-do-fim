from __future__ import annotations

import argparse
import math
import random

import pygame
from pygame import Vector2

from ..application import gameplay_flow, runtime_update, session_lifecycle, title_flow, weather_service
from ..entities import Player, Zombie
from ..audio import AudioSystem
from ..core.camera import CameraRig
from ..core.config import (
    CAMP_CENTER,
    FPS,
    DISPLAY_SETTINGS,
    GAMEPLAY_SETTINGS,
    MINUTES_PER_SECOND,
    PALETTE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    START_TIME_MINUTES,
    UI_SETTINGS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    load_font,
)
from ..core.input import InputState, InputSystem
from ..infrastructure.savegame_codec import SaveGameCodec
from ..infrastructure.savegame_repository import JsonSaveGameRepository, SaveGameWriteError
from ..core.models import Building, BuildingRequest, DamagePulse, DynamicEvent, Ember, FloatingText, FogMote
from ..rendering import RenderMixin
from ..core.scenes import SceneId, SceneManager
from ..ui import dialogue_helpers, ui_helpers
from ..worlding import WorldMixin


class Game(WorldMixin, RenderMixin):
    """Coordena o loop principal e conecta os subsistemas do jogo."""

    def __init__(self, *, seed: int | None = None, smoke_test: bool = False) -> None:
        self.seed = seed
        self.seed_value = seed if seed is not None else 0
        self.random = random.Random(seed)
        random.seed(seed)
        pygame.init()
        pygame.display.set_caption("Fogueira do Fim")
        fullscreen = bool(DISPLAY_SETTINGS.get("fullscreen", True))
        if fullscreen and not smoke_test:
            display_info = pygame.display.Info()
            display_size = (
                max(1, int(display_info.current_w or SCREEN_WIDTH)),
                max(1, int(display_info.current_h or SCREEN_HEIGHT)),
            )
            flags = pygame.FULLSCREEN
        else:
            display_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
            flags = 0
        self.screen = pygame.display.set_mode(display_size, flags)
        self.sync_viewport_constants(*self.screen.get_size())
        self.clock = pygame.time.Clock()
        self.running = True
        self.smoke_test = smoke_test
        self.audio = AudioSystem()
        self.input = InputSystem()
        self.input_state = InputState()
        self.save_repository = JsonSaveGameRepository()
        self.save_codec = SaveGameCodec()
        self.scenes = SceneManager(SceneId.GAMEPLAY if smoke_test else SceneId.SPLASH)

        self.title_font = load_font(62, title=True)
        self.heading_font = load_font(24, title=True)
        self.body_font = load_font(18)
        self.small_font = load_font(15)
        self.ui_small_font = load_font(16)
        self.runtime_settings: dict[str, float] = {
            key: float(value)
            for key, value in dict(UI_SETTINGS.get("runtime_defaults", {})).items()
        }
        self.title_actions = ()
        self.title_action_index = 0
        self.title_setting_index = 0
        self.title_settings_open = False
        self.tips_index = 0
        self.title_bg_phase = 0.0
        spawn_range = UI_SETTINGS.get("title_background_spawn_range", [7.0, 12.0])
        self.title_bg_spawn_timer = float(spawn_range[0])
        self.bark_timer = 3.2
        self.exit_prompt_open = False
        self.exit_prompt_options = ("Salvar e Sair", "Sair sem Salvar", "Cancelar")
        self.exit_prompt_index = 0
        self.society_panel_collapsed = False
        self.society_scroll = 0.0
        self.society_selected_survivor_name: str | None = None
        self.hud_compact_mode = False
        self.chat_messages: list[dict[str, object]] = []
        self.chat_scroll = 0.0
        self.dialog_survivor_name: str | None = None
        self.title_setting_entries = tuple(
            (
                key,
                str(entry["label"]),
                float(entry["step"]),
                float(entry["min"]),
                float(entry["max"]),
            )
            for key, entry in dict(UI_SETTINGS.get("runtime_ranges", {})).items()
        )
        self.audio.apply_settings(self.runtime_settings)
        self.refresh_title_actions()
        self.tutorial_pages = self.create_tutorial_pages()
        self.seed_chat_log()
        self.splash_elapsed = 0.0
        self.splash_min_duration = 1.4
        self.splash_hint_pulse = 0.0
        self.title_intro_alpha = 0.0
        self.title_intro_speed = 320.0

        self.player = Player(CAMP_CENTER + Vector2(20, 40))
        self.day = 1
        self.time_minutes = START_TIME_MINUTES
        self.previous_night = self.is_night
        self.focus_mode = "balanced"
        # Estoque inicial mais folgado para o early game nao travar antes da primeira noite.
        starting_resources = dict(GAMEPLAY_SETTINGS.get("starting_resources", {}))
        self.logs = int(starting_resources.get("logs", 9))
        self.wood = int(starting_resources.get("wood", 8))
        self.food = int(starting_resources.get("food", 8))
        self.herbs = int(starting_resources.get("herbs", 2))
        self.scrap = int(starting_resources.get("scrap", 5))
        self.meals = int(starting_resources.get("meals", 2))
        self.medicine = int(starting_resources.get("medicine", 1))
        self.camp_level = int(GAMEPLAY_SETTINGS.get("camp_level_start", 0))
        self.max_camp_level = int(GAMEPLAY_SETTINGS.get("max_camp_level", 5))
        bonfire_start = dict(GAMEPLAY_SETTINGS.get("bonfire_start", {}))
        self.bonfire_heat = float(bonfire_start.get("heat", 64.0))
        self.bonfire_ember_bed = float(bonfire_start.get("ember_bed", 52.0))
        self.event_message = "O campo desperta no meio da mata."
        self.event_timer = 8.0
        self.morale_flash = 0.0
        self.screen_shake = 0.0
        self.social_timer = 2.4
        gameplay_timers = dict(GAMEPLAY_SETTINGS.get("timers", {}))
        self.dynamic_event_cooldown = float(gameplay_timers.get("dynamic_event_cooldown", 28.0))
        self.next_dynamic_event_uid = 1
        self.active_dynamic_events: list[DynamicEvent] = []
        self.active_expedition: dict[str, object] | None = None
        self.spawn_timer = float(gameplay_timers.get("spawn_timer", 4.0))
        self.spawn_budget = 0
        self.horde_active = False
        self.day_spawn_timer = float(gameplay_timers.get("day_spawn_timer", 18.0))
        self.floating_texts: list[FloatingText] = []
        self.embers: list[Ember] = []
        self.fog_motes: list[FogMote] = []
        self.damage_pulses: list[DamagePulse] = []
        self.recruit_pool = self.create_recruit_pool()
        self.next_recruit_index = 0
        self.build_menu_open = False
        self.selected_build_slot = 1
        self.next_building_uid = 1
        self.build_requests: list[BuildingRequest] = []
        self.next_build_request_uid = 1
        self.player_sleeping = False
        self.player_sleep_slot: dict[str, object] | None = None
        self.player_sleep_elapsed = 0.0

        self.layout_camp_core()
        self.weather_kind = "clear"
        self.weather_strength = 0.0
        self.weather_target_kind = "clear"
        self.weather_target_strength = 0.0
        self.weather_timer = 0.0
        self.weather_front_progress = 1.0
        self.weather_front_duration = 0.0
        self.weather_gust_phase = self.random.uniform(0.0, math.tau)
        self.weather_gust_strength = 0.0
        self.weather_flash = 0.0
        self.weather_flash_timer = 0.0
        self.weather_label = "ceu limpo"
        self.faction_standings = self.create_faction_standings()
        self.build_recipes = self.create_build_recipes()

        self.world_features = self.generate_world_features()
        self.endless_features = []
        self.named_regions: dict[tuple[int, int], dict[str, object]] = {}
        self.generated_chunks: dict[tuple[int, int], dict[str, object]] = {}
        self.path_network = self.generate_path_network()
        self.interest_points = self.generate_interest_points()
        self.tents = self.generate_tents()
        self.trees = self.generate_trees()
        self.resource_nodes = self.generate_resource_nodes()
        self.buildings: list[Building] = []
        self.barricades = self.generate_barricades()
        self.refresh_barricade_strength()
        self.survivors = self.generate_survivors()
        self.sync_survivor_assignments()
        self.initialize_survivor_relationships()
        self.assign_building_specialists()

        self.terrain_surface = self.build_terrain_surface()
        self.fog_of_war = self.create_fog_of_war_surface()
        self.map_fog_overlay_surface: pygame.Surface | None = None
        self.map_reveal_cache: dict[int, pygame.Surface] = {}
        # O mundo explora chunks procedurais para longe da clareira, entao a
        # camera do gameplay precisa continuar solta para seguir o jogador.
        self.camera = CameraRig(SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT, bounded=False)
        self.current_biome_label = "Clareira do Campo"
        self.current_biome_key = "camp"
        self.current_region_label = "Clareira do Campo"
        self.current_region_key: tuple[int, int] | str = "camp"
        self.current_zone_boss_label = "centro seguro"
        self.roll_weather(initial=True)
        self.ensure_endless_world(self.player.pos)
        self.maintain_unlimited_resources()

        for _ in range(26):
            self.fog_motes.append(
                FogMote(
                    pos=Vector2(
                        self.random.uniform(-120, WORLD_WIDTH + 120),
                        self.random.uniform(-120, WORLD_HEIGHT + 120),
                    ),
                    velocity=Vector2(self.random.uniform(-12, 12), self.random.uniform(-4, 6)),
                    radius=self.random.uniform(80, 180),
                    alpha=self.random.randint(18, 40),
                )
            )

        self.zombies: list[Zombie] = []

    def sync_viewport_constants(self, width: int, height: int) -> None:
        """Sincroniza os modulos que usam largura/altura da viewport em tempo de execucao."""
        from ..core import config as config_module
        from ..rendering import hud_rendering_helpers as hud_module
        from ..rendering import ui_build_rendering as build_rendering_module
        from ..rendering import ui_hud_rendering as hud_rendering_module
        from ..rendering import ui_screen_rendering as screen_rendering_module
        from ..rendering import mixin as rendering_module
        from ..rendering import world_base_rendering as world_base_module
        from ..rendering import world_resource_rendering as world_resource_module
        from ..rendering import world_scenery_rendering as world_scenery_module
        from ..rendering import world_signals_rendering as world_signals_module
        from ..ui import ui_helpers as ui_module

        globals()["SCREEN_WIDTH"] = int(width)
        globals()["SCREEN_HEIGHT"] = int(height)
        config_module.SCREEN_WIDTH = int(width)
        config_module.SCREEN_HEIGHT = int(height)
        rendering_module.SCREEN_WIDTH = int(width)
        rendering_module.SCREEN_HEIGHT = int(height)
        ui_module.SCREEN_WIDTH = int(width)
        ui_module.SCREEN_HEIGHT = int(height)
        hud_module.SCREEN_WIDTH = int(width)
        hud_module.SCREEN_HEIGHT = int(height)
        hud_rendering_module.SCREEN_WIDTH = int(width)
        hud_rendering_module.SCREEN_HEIGHT = int(height)
        build_rendering_module.SCREEN_WIDTH = int(width)
        build_rendering_module.SCREEN_HEIGHT = int(height)
        screen_rendering_module.SCREEN_WIDTH = int(width)
        screen_rendering_module.SCREEN_HEIGHT = int(height)
        world_base_module.SCREEN_WIDTH = int(width)
        world_base_module.SCREEN_HEIGHT = int(height)
        world_resource_module.SCREEN_WIDTH = int(width)
        world_resource_module.SCREEN_HEIGHT = int(height)
        world_scenery_module.SCREEN_WIDTH = int(width)
        world_scenery_module.SCREEN_HEIGHT = int(height)
        world_signals_module.SCREEN_WIDTH = int(width)
        world_signals_module.SCREEN_HEIGHT = int(height)
        self.map_fog_overlay_surface = None
        self.map_reveal_cache = {}

    @property
    def state(self) -> str:
        return self.scenes.current_name

    @state.setter
    def state(self, value: str) -> None:
        self.scenes.change(value)

    def start_gameplay(self) -> None:
        self.scenes.change(SceneId.GAMEPLAY)
        self.audio.play_transition("start")

    def begin_new_game_flow(self) -> None:
        session_lifecycle.begin_new_game_flow(self)

    def begin_tips(self) -> None:
        self.tips_index = 0
        self.scenes.change(SceneId.TIPS)
        self.set_event_message("Leia as dicas rapido ou pule quando quiser. A clareira continua respirando atras da tela.", duration=6.2)

    def skip_tips_to_gameplay(self) -> None:
        self.start_gameplay()

    def restart_game(self) -> None:
        session_lifecycle.restart_game_flow(self)

    def open_exit_prompt(self) -> None:
        title_flow.open_exit_prompt(self)

    def close_exit_prompt(self) -> None:
        title_flow.close_exit_prompt(self)

    def exit_prompt_layout(self) -> dict[str, object]:
        return title_flow.exit_prompt_layout(self)

    def confirm_exit_prompt(self, choice: str | None = None) -> None:
        title_flow.confirm_exit_prompt(self, choice)

    def handle_exit_prompt_input(self) -> bool:
        return title_flow.handle_exit_prompt_input(self)

    def refresh_title_actions(self) -> None:
        title_flow.refresh_title_actions(self)

    def create_tutorial_pages(self) -> tuple[dict[str, object], ...]:
        return title_flow.create_tutorial_pages()

    def normalize_chat_text(self, text: str) -> str:
        return dialogue_helpers.normalize_chat_text(self, text)

    def seed_chat_log(self) -> None:
        dialogue_helpers.seed_chat_log(self)

    def add_chat_message(
        self,
        speaker: str,
        text: str,
        color: tuple[int, int, int] | None = None,
        *,
        source: str = "system",
    ) -> None:
        dialogue_helpers.add_chat_message(self, speaker, text, color, source=source)

    def chat_panel_layout(self) -> dict[str, pygame.Rect]:
        return ui_helpers.chat_panel_layout(self)

    def chat_message_height(self, entry: dict[str, object], width: int) -> int:
        return dialogue_helpers.chat_message_height(self, entry, width)

    def chat_content_height(self) -> int:
        return dialogue_helpers.chat_content_height(self)

    def chat_max_scroll(self) -> float:
        return dialogue_helpers.chat_max_scroll(self)

    def clamp_chat_scroll(self) -> None:
        dialogue_helpers.clamp_chat_scroll(self)

    def adjust_chat_scroll(self, delta: float) -> None:
        dialogue_helpers.adjust_chat_scroll(self, delta)

    def directive_label(self, directive: str) -> str:
        return dialogue_helpers.directive_label(self, directive)

    def directive_from_text(self, normalized_text: str) -> str | None:
        return dialogue_helpers.directive_from_text(self, normalized_text)

    def focus_from_text(self, normalized_text: str) -> str | None:
        return dialogue_helpers.focus_from_text(self, normalized_text)

    def targeted_survivors_from_text(self, normalized_text: str) -> list[object]:
        return dialogue_helpers.targeted_survivors_from_text(self, normalized_text)

    def focus_label_for_mode(self, mode: str) -> str:
        return dialogue_helpers.focus_label_for_mode(self, mode)

    def active_dialog_survivor(self) -> object | None:
        return dialogue_helpers.active_dialog_survivor(self)

    def open_survivor_dialog(self, survivor: object) -> None:
        dialogue_helpers.open_survivor_dialog(self, survivor)

    def close_survivor_dialog(self) -> None:
        dialogue_helpers.close_survivor_dialog(self)

    def survivor_role_directive(self, survivor: object) -> tuple[str, str]:
        return dialogue_helpers.survivor_role_directive(self, survivor)

    def conversation_options_for_survivor(self, survivor: object) -> list[dict[str, str]]:
        return dialogue_helpers.conversation_options_for_survivor(self, survivor)

    def execute_survivor_dialog_action(self, survivor: object, action: str) -> None:
        dialogue_helpers.execute_survivor_dialog_action(self, survivor, action)

    def set_focus_from_chat(self, mode: str) -> None:
        dialogue_helpers.set_focus_from_chat(self, mode)

    def try_assign_directive(self, survivor: object, directive: str, *, duration: float) -> bool:
        return dialogue_helpers.try_assign_directive(self, survivor, directive, duration=duration)

    def issue_chat_order(self, targets: list[object], directive: str) -> bool:
        return dialogue_helpers.issue_chat_order(self, targets, directive)

    def chat_status_report(self) -> None:
        dialogue_helpers.chat_status_report(self)

    def random_chat_reply(self, player_text: str) -> None:
        dialogue_helpers.random_chat_reply(self, player_text)

    def submit_chat_message(self, text: str) -> None:
        dialogue_helpers.submit_chat_message(self, text)

    def save_exists(self) -> bool:
        return self.save_repository.exists()

    def vec_to_list(self, value: Vector2) -> list[float]:
        return self.save_codec.vec_to_list(value)

    def list_to_vec(self, value: object, fallback: Vector2 | None = None) -> Vector2:
        return self.save_codec.list_to_vec(value, fallback)

    def make_json_safe(self, value: object) -> object:
        return self.save_codec.make_json_safe(value)

    def serialize_save_data(self) -> dict[str, object]:
        return self.save_codec.serialize(self)

    def save_game(self, *, auto: bool = False) -> tuple[bool, str]:
        if self.smoke_test:
            return False, "Smoke test nao grava save."
        try:
            self.save_repository.save(self.serialize_save_data())
        except SaveGameWriteError:
            return False, "Falha ao gravar o save."
        self.refresh_title_actions()
        return True, "Auto-save concluido." if auto else "Jogo salvo."

    def apply_loaded_data(self, data: dict[str, object]) -> None:
        self.save_codec.apply(self, data)

    def load_game(self) -> tuple[bool, str]:
        return session_lifecycle.load_saved_game_flow(self)

    def selected_build_recipe(self) -> dict[str, object]:
        index = max(0, min(len(self.build_recipes) - 1, self.selected_build_slot - 1))
        return self.build_recipes[index]

    def adjust_runtime_setting(self, key: str, delta: float, low: float, high: float) -> None:
        title_flow.adjust_runtime_setting(self, key, delta, low, high)

    def title_setting_value_label(self, key: str) -> str:
        return title_flow.title_setting_value_label(self, key)

    def title_ui_layout(self) -> dict[str, object]:
        return ui_helpers.title_ui_layout(self)

    def tips_ui_layout(self) -> dict[str, pygame.Rect]:
        return ui_helpers.tips_ui_layout(self)

    def society_panel_layout(self) -> dict[str, pygame.Rect]:
        return ui_helpers.society_panel_layout(self)

    def hud_toggle_rect(self) -> pygame.Rect:
        return ui_helpers.hud_toggle_rect(self)

    def society_card_step(self, survivor: object | None = None) -> int:
        return ui_helpers.society_card_step(self, survivor)

    def society_card_height(self, survivor: object) -> int:
        return ui_helpers.society_card_height(self, survivor)

    def society_content_height(self) -> int:
        return ui_helpers.society_content_height(self)

    def society_max_scroll(self) -> float:
        return ui_helpers.society_max_scroll(self)

    def clamp_society_scroll(self) -> None:
        ui_helpers.clamp_society_scroll(self)

    def adjust_society_scroll(self, delta: float) -> None:
        ui_helpers.adjust_society_scroll(self, delta)

    def handle_chat_panel_input(self) -> bool:
        return ui_helpers.handle_chat_panel_input(self)

    def handle_society_panel_input(self) -> bool:
        return ui_helpers.handle_society_panel_input(self)

    def handle_hud_input(self) -> bool:
        return ui_helpers.handle_hud_input(self)

    def handle_title_input(self) -> None:
        title_flow.handle_title_input(self)

    def handle_tips_input(self) -> None:
        title_flow.handle_tips_input(self)

    def begin_player_sleep(self, slot: dict[str, object]) -> None:
        gameplay_flow.begin_player_sleep(self, slot)

    def wake_player(self, message: str | None = None) -> None:
        gameplay_flow.wake_player(self, message)

    def weather_strength_range(self, kind: str) -> tuple[float, float]:
        return weather_service.weather_strength_range(self, kind)

    def weather_duration_range(self, kind: str) -> tuple[float, float]:
        return weather_service.weather_duration_range(self, kind)

    def weather_display_name(self, kind: str, strength: float) -> str:
        return weather_service.weather_display_name(self, kind, strength)

    def weather_transition_options(self, previous_kind: str) -> tuple[tuple[str, ...], tuple[float, ...]]:
        return weather_service.weather_transition_options(self, previous_kind)

    def roll_weather(self, *, initial: bool = False) -> None:
        weather_service.roll_weather(self, initial=initial)

    def update_weather(self, dt: float) -> None:
        weather_service.update_weather(self, dt)

    def handle_events(self) -> None:
        gameplay_flow.handle_events(self)

    def update(self, dt: float) -> None:
        runtime_update.update(self, dt)

    def update_background_simulation(self, dt: float) -> None:
        runtime_update.update_background_simulation(self, dt)

    def run(self) -> int:
        smoke_frames = 0
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            if self.smoke_test:
                smoke_frames += 1
                if smoke_frames >= 90:
                    return 0
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fogueira do Fim")
    parser.add_argument("--seed", type=int, default=None, help="semente opcional para reproducao")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="executa alguns frames e sai; util para verificacao automatica",
    )
    args = parser.parse_args(argv)

    game = Game(seed=args.seed, smoke_test=args.smoke_test)
    try:
        return game.run()
    finally:
        pygame.quit()
















