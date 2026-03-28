from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import pygame
from pygame import Vector2

from .actors import Player, Zombie
from .audio import AudioSystem
from .camera import CameraRig
from .config import (
    CAMP_CENTER,
    FPS,
    MINUTES_PER_SECOND,
    PALETTE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    START_TIME_MINUTES,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    clamp,
    load_font,
)
from .input import InputState, InputSystem
from .models import Building, BuildingRequest, DamagePulse, DynamicEvent, Ember, FloatingText, FogMote
from .rendering import RenderMixin
from .scenes import SceneId, SceneManager
from . import dialogue_helpers, ui_helpers
from .world import WorldMixin

SAVE_FILE = Path("savegame.json")
SAVE_FOG_FILE = Path("savegame_fog.png")


class Game(WorldMixin, RenderMixin):
    """Coordena o loop principal e conecta os subsistemas do jogo."""

    def __init__(self, *, seed: int | None = None, smoke_test: bool = False) -> None:
        self.seed = seed
        self.seed_value = seed if seed is not None else 0
        self.random = random.Random(seed)
        random.seed(seed)
        pygame.init()
        pygame.display.set_caption("Fogueira do Fim")
        flags = (pygame.SCALED | pygame.FULLSCREEN) if not smoke_test else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        self.clock = pygame.time.Clock()
        self.running = True
        self.smoke_test = smoke_test
        self.audio = AudioSystem()
        self.input = InputSystem()
        self.input_state = InputState()
        self.scenes = SceneManager(SceneId.GAMEPLAY if smoke_test else SceneId.TITLE)

        self.title_font = load_font(62, title=True)
        self.heading_font = load_font(24, title=True)
        self.body_font = load_font(18)
        self.small_font = load_font(15)
        self.ui_small_font = load_font(16)
        self.runtime_settings: dict[str, float] = {
            "master_volume": 0.86,
            "ambience_volume": 0.92,
            "music_volume": 0.84,
            "screen_shake_scale": 1.0,
            "fog_strength": 0.95,
            "ui_contrast": 1.0,
        }
        self.title_actions = ()
        self.title_action_index = 0
        self.title_setting_index = 0
        self.title_settings_open = False
        self.tips_index = 0
        self.title_bg_phase = 0.0
        self.title_bg_spawn_timer = 8.0
        self.bark_timer = 3.2
        self.exit_prompt_open = False
        self.exit_prompt_options = ("Salvar e Sair", "Sair sem Salvar", "Cancelar")
        self.exit_prompt_index = 0
        self.society_panel_collapsed = False
        self.society_scroll = 0.0
        self.society_selected_survivor_name: str | None = None
        self.chat_messages: list[dict[str, object]] = []
        self.chat_scroll = 0.0
        self.dialog_survivor_name: str | None = None
        self.title_setting_entries = (
            ("master_volume", "Volume Geral", 0.05, 0.0, 1.0),
            ("ambience_volume", "Ambiencia", 0.05, 0.0, 1.0),
            ("music_volume", "Musica", 0.05, 0.0, 1.0),
            ("screen_shake_scale", "Tremor de Tela", 0.1, 0.0, 1.4),
            ("fog_strength", "Forca da Neblina", 0.1, 0.35, 1.25),
            ("ui_contrast", "Contraste da HUD", 0.1, 0.7, 1.4),
        )
        self.audio.apply_settings(self.runtime_settings)
        self.refresh_title_actions()
        self.tutorial_pages = self.create_tutorial_pages()
        self.seed_chat_log()

        self.player = Player(CAMP_CENTER + Vector2(20, 40))
        self.day = 1
        self.time_minutes = START_TIME_MINUTES
        self.previous_night = self.is_night
        self.focus_mode = "balanced"
        self.logs = 7
        self.wood = 6
        self.food = 6
        self.herbs = 1
        self.scrap = 4
        self.meals = 1
        self.medicine = 0
        self.camp_level = 0
        self.max_camp_level = 5
        self.bonfire_heat = 58.0
        self.bonfire_ember_bed = 46.0
        self.event_message = "O campo desperta no meio da mata."
        self.event_timer = 8.0
        self.morale_flash = 0.0
        self.screen_shake = 0.0
        self.social_timer = 2.4
        self.dynamic_event_cooldown = 18.0
        self.next_dynamic_event_uid = 1
        self.active_dynamic_events: list[DynamicEvent] = []
        self.active_expedition: dict[str, object] | None = None
        self.spawn_timer = 4.0
        self.spawn_budget = 0
        self.horde_active = False
        self.day_spawn_timer = 12.0
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
        self.weather_timer = 0.0
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
        self.camera = CameraRig(SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT, bounded=False)
        self.current_biome_label = "Clareira do Campo"
        self.current_biome_key = "camp"
        self.current_region_label = "Clareira do Campo"
        self.current_region_key: tuple[int, int] | str = "camp"
        self.current_zone_boss_label = "centro seguro"
        self.roll_weather(initial=True)
        self.ensure_endless_world(self.player.pos)

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
        settings_snapshot = dict(self.runtime_settings)
        self.__init__(seed=self.seed, smoke_test=self.smoke_test)
        self.runtime_settings.update(settings_snapshot)
        self.audio.apply_settings(self.runtime_settings)
        self.refresh_title_actions()
        self.begin_tips()

    def begin_tips(self) -> None:
        self.tips_index = 0
        self.scenes.change(SceneId.TIPS)
        self.set_event_message("Leia as dicas rapido ou pule quando quiser. A clareira continua respirando atras da tela.", duration=6.2)

    def skip_tips_to_gameplay(self) -> None:
        self.start_gameplay()

    def restart_game(self) -> None:
        self.audio.play_transition("restart")
        settings_snapshot = dict(self.runtime_settings)
        self.__init__(seed=self.seed, smoke_test=self.smoke_test)
        self.runtime_settings.update(settings_snapshot)
        self.audio.apply_settings(self.runtime_settings)

    def open_exit_prompt(self) -> None:
        self.exit_prompt_open = True
        self.exit_prompt_index = 0
        self.build_menu_open = False
        self.close_survivor_dialog()
        self.audio.play_ui("back")

    def close_exit_prompt(self) -> None:
        if not self.exit_prompt_open:
            return
        self.exit_prompt_open = False
        self.audio.play_ui("back")

    def exit_prompt_layout(self) -> dict[str, object]:
        panel = pygame.Rect(0, 0, 520, 252)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        buttons: list[pygame.Rect] = []
        row_y = panel.y + 132
        for _ in self.exit_prompt_options:
            buttons.append(pygame.Rect(panel.x + 26, row_y, panel.width - 52, 38))
            row_y += 48
        return {"panel": panel, "buttons": buttons}

    def confirm_exit_prompt(self, choice: str | None = None) -> None:
        selected = choice or self.exit_prompt_options[self.exit_prompt_index]
        if selected == "Salvar e Sair":
            success, message = self.save_game()
            self.set_event_message(message, duration=4.8)
            self.spawn_floating_text("save" if success else "falhou", self.player.pos, PALETTE["accent_soft"] if success else PALETTE["danger_soft"])
            if success:
                self.audio.play_ui("focus")
                self.running = False
            else:
                self.audio.play_alert()
            return
        if selected == "Sair sem Salvar":
            self.running = False
            return
        self.close_exit_prompt()

    def handle_exit_prompt_input(self) -> bool:
        if not self.exit_prompt_open:
            return False
        layout = self.exit_prompt_layout()
        mouse_pos = self.input_state.mouse_screen
        clicked = self.input_state.attack_pressed
        hovered = next((index for index, rect in enumerate(layout["buttons"]) if rect.collidepoint(mouse_pos)), None)
        if hovered is not None and hovered != self.exit_prompt_index:
            self.exit_prompt_index = hovered
        if self.input_state.menu_up:
            self.exit_prompt_index = (self.exit_prompt_index - 1) % len(self.exit_prompt_options)
            self.audio.play_ui("focus")
            return True
        if self.input_state.menu_down:
            self.exit_prompt_index = (self.exit_prompt_index + 1) % len(self.exit_prompt_options)
            self.audio.play_ui("focus")
            return True
        if self.input_state.cancel_pressed:
            self.close_exit_prompt()
            return True
        if clicked and hovered is not None:
            self.confirm_exit_prompt(self.exit_prompt_options[hovered])
            return True
        if self.input_state.confirm_pressed or self.input_state.interact_pressed:
            self.confirm_exit_prompt()
            return True
        return True

    def refresh_title_actions(self) -> None:
        actions = ["Novo Jogo", "Configuracoes", "Sair"]
        if self.save_exists():
            actions.insert(0, "Continuar")
        self.title_actions = tuple(actions)
        self.title_action_index = max(0, min(self.title_action_index, len(self.title_actions) - 1))

    def create_tutorial_pages(self) -> tuple[dict[str, object], ...]:
        return (
            {
                "eyebrow": "Lideranca da Clareira",
                "title": "Voce e o chefe do acampamento",
                "body": "Sua presenca segura moral, rotina e defesa. O grupo trabalha sozinho, mas depende de foco, fogo e direcao para nao quebrar.",
                "bullets": (
                    "WASD move o chefe pela base e pela mata.",
                    "E interage com barracas, radio, oficina, fogueira, eventos e sobreviventes.",
                    "1-4 muda a prioridade social do dia.",
                ),
            },
            {
                "eyebrow": "Sobrevivencia",
                "title": "Tudo gira em torno de estoque e tempo",
                "body": "O acampamento precisa de toras, tabuas, comida, remedios e sucata. A noite aperta mais, e a fogueira segura o centro da sociedade.",
                "bullets": (
                    "Clique esquerdo ou Espaco ataca e derruba arvores.",
                    "B abre a construcao; 1-7 escolhe o edificio.",
                    "E na oficina amplia a base quando houver toras e sucata.",
                ),
            },
            {
                "eyebrow": "Pressao do Mundo",
                "title": "Explore, decida e nao deixe o campo ruir",
                "body": "Zumbis rondam a floresta, faccoes cobram respostas, expedicoes pedem resgate e a sociedade pode enlouquecer se voce sumir demais.",
                "bullets": (
                    "Q resolve decisoes duras em eventos morais e faccoes.",
                    "F5 salva e F9 carrega sem sair da partida.",
                    "Enter avanca as dicas; Esc pula tudo e entra no jogo.",
                ),
            },
        )

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
        return SAVE_FILE.exists()

    def vec_to_list(self, value: Vector2) -> list[float]:
        return [round(float(value.x), 3), round(float(value.y), 3)]

    def list_to_vec(self, value: object, fallback: Vector2 | None = None) -> Vector2:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return Vector2(float(value[0]), float(value[1]))
        return Vector2(fallback) if fallback is not None else Vector2()

    def serialize_save_data(self) -> dict[str, object]:
        sleep_slot = None
        if self.player_sleep_slot:
            sleep_slot = {
                key: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                for key, value in self.player_sleep_slot.items()
            }
        active_expedition = None
        if self.active_expedition:
            active_expedition = {
                key: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                for key, value in self.active_expedition.items()
            }
        return {
            "version": 1,
            "seed": self.seed,
            "runtime_settings": dict(self.runtime_settings),
            "chat_messages": list(self.chat_messages[-48:]),
            "chat_scroll": self.chat_scroll,
            "scene": SceneId.GAMEPLAY,
            "day": self.day,
            "time_minutes": self.time_minutes,
            "previous_night": self.previous_night,
            "focus_mode": self.focus_mode,
            "logs": self.logs,
            "wood": self.wood,
            "food": self.food,
            "herbs": self.herbs,
            "scrap": self.scrap,
            "meals": self.meals,
            "medicine": self.medicine,
            "camp_level": self.camp_level,
            "bonfire_heat": self.bonfire_heat,
            "bonfire_ember_bed": self.bonfire_ember_bed,
            "event_message": self.event_message,
            "event_timer": self.event_timer,
            "morale_flash": self.morale_flash,
            "screen_shake": self.screen_shake,
            "social_timer": self.social_timer,
            "dynamic_event_cooldown": self.dynamic_event_cooldown,
            "next_dynamic_event_uid": self.next_dynamic_event_uid,
            "spawn_timer": self.spawn_timer,
            "spawn_budget": self.spawn_budget,
            "horde_active": self.horde_active,
            "day_spawn_timer": self.day_spawn_timer,
            "next_recruit_index": self.next_recruit_index,
            "next_building_uid": self.next_building_uid,
            "next_build_request_uid": self.next_build_request_uid,
            "player_sleeping": self.player_sleeping,
            "player_sleep_slot": sleep_slot,
            "player_sleep_elapsed": self.player_sleep_elapsed,
            "weather_kind": self.weather_kind,
            "weather_strength": self.weather_strength,
            "weather_timer": self.weather_timer,
            "weather_label": self.weather_label,
            "faction_standings": dict(self.faction_standings),
            "named_regions": {
                f"{key[0]},{key[1]}": {
                    field: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                    for field, value in region.items()
                }
                for key, region in self.named_regions.items()
            },
            "generated_chunks": {
                f"{key[0]},{key[1]}": dict(chunk)
                for key, chunk in self.generated_chunks.items()
            },
            "endless_features": [
                {
                    "kind": feature.kind,
                    "pos": self.vec_to_list(feature.pos),
                    "radius": feature.radius,
                    "accent": feature.accent,
                }
                for feature in self.endless_features
            ],
            "interest_points": [
                {
                    "feature_kind": point.feature_kind,
                    "event_kind": point.event_kind,
                    "label": point.label,
                    "pos": self.vec_to_list(point.pos),
                    "radius": point.radius,
                    "pulse": point.pulse,
                    "resolved": point.resolved,
                }
                for point in self.interest_points
            ],
            "trees": [
                {
                    key: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                    for key, value in tree.items()
                }
                for tree in self.trees
            ],
            "resource_nodes": [
                {
                    "kind": node.kind,
                    "pos": self.vec_to_list(node.pos),
                    "amount": node.amount,
                    "radius": node.radius,
                    "variant": node.variant,
                    "cooldown": node.cooldown,
                    "renewable": node.renewable,
                    "respawn_delay": node.respawn_delay,
                }
                for node in self.resource_nodes
            ],
            "buildings": [
                {
                    "uid": building.uid,
                    "kind": building.kind,
                    "pos": self.vec_to_list(building.pos),
                    "size": building.size,
                    "assigned_to": building.assigned_to,
                    "work_phase": building.work_phase,
                }
                for building in self.buildings
            ],
            "build_requests": [
                {
                    "uid": request.uid,
                    "requester_name": request.requester_name,
                    "kind": request.kind,
                    "label": request.label,
                    "pos": self.vec_to_list(request.pos),
                    "size": request.size,
                    "approved": request.approved,
                    "progress": request.progress,
                    "assigned_to": request.assigned_to,
                }
                for request in self.build_requests
            ],
            "barricades": [
                {
                    "angle": barricade.angle,
                    "pos": self.vec_to_list(barricade.pos),
                    "tangent": self.vec_to_list(barricade.tangent),
                    "span": barricade.span,
                    "tier": barricade.tier,
                    "spike_level": getattr(barricade, "spike_level", 0),
                    "max_health": barricade.max_health,
                    "health": barricade.health,
                }
                for barricade in self.barricades
            ],
            "survivors": [
                {
                    "name": survivor.name,
                    "role": survivor.role,
                    "traits": list(survivor.traits),
                    "pos": self.vec_to_list(survivor.pos),
                    "home_pos": self.vec_to_list(survivor.home_pos),
                    "guard_pos": self.vec_to_list(survivor.guard_pos),
                    "health": survivor.health,
                    "max_health": survivor.max_health,
                    "velocity": self.vec_to_list(survivor.velocity),
                    "facing": self.vec_to_list(survivor.facing),
                    "hunger": survivor.hunger,
                    "energy": survivor.energy,
                    "morale": survivor.morale,
                    "attack_cooldown": survivor.attack_cooldown,
                    "carry_bundle": dict(survivor.carry_bundle),
                    "sleep_shift": survivor.sleep_shift,
                    "sleep_debt": survivor.sleep_debt,
                    "exhaustion": survivor.exhaustion,
                    "insanity": survivor.insanity,
                    "trust_leader": survivor.trust_leader,
                    "relations": dict(survivor.relations),
                    "conflict_cooldown": survivor.conflict_cooldown,
                    "bond_cooldown": survivor.bond_cooldown,
                    "assigned_tent_index": survivor.assigned_tent_index,
                    "sleep_slot_kind": survivor.sleep_slot_kind,
                    "sleep_slot_building_uid": survivor.sleep_slot_building_uid,
                    "assigned_building_id": survivor.assigned_building_id,
                    "assigned_building_kind": survivor.assigned_building_kind,
                    "on_expedition": survivor.on_expedition,
                    "expedition_downed": survivor.expedition_downed,
                    "expedition_attack_cooldown": survivor.expedition_attack_cooldown,
                    "leader_directive": survivor.leader_directive,
                    "leader_directive_timer": survivor.leader_directive_timer,
                    "build_request_cooldown": survivor.build_request_cooldown,
                }
                for survivor in self.survivors
            ],
            "player": {
                "pos": self.vec_to_list(self.player.pos),
                "health": self.player.health,
                "max_health": self.player.max_health,
                "stamina": self.player.stamina,
                "max_stamina": self.player.max_stamina,
                "attack_cooldown": self.player.attack_cooldown,
                "attack_flash": self.player.attack_flash,
                "interact_cooldown": self.player.interact_cooldown,
                "last_move": self.vec_to_list(self.player.last_move),
                "velocity": self.vec_to_list(self.player.velocity),
                "facing": self.vec_to_list(self.player.facing),
            },
            "zombies": [
                {
                    "pos": self.vec_to_list(zombie.pos),
                    "day": zombie.day,
                    "health": zombie.health,
                    "max_health": zombie.max_health,
                    "radius": zombie.radius,
                    "speed": zombie.speed,
                    "velocity": self.vec_to_list(zombie.velocity),
                    "facing": self.vec_to_list(zombie.facing),
                    "attack_cooldown": zombie.attack_cooldown,
                    "stagger": zombie.stagger,
                    "shamble": zombie.shamble,
                    "is_boss": zombie.is_boss,
                    "boss_name": zombie.boss_name,
                    "zone_key": list(zombie.zone_key),
                    "zone_label": zombie.zone_label,
                    "anchor": self.vec_to_list(zombie.anchor),
                    "boss_body": list(zombie.boss_body),
                    "boss_accent": list(zombie.boss_accent),
                    "contact_damage": zombie.contact_damage,
                    "summon_cooldown": zombie.summon_cooldown,
                    "death_processed": zombie.death_processed,
                    "alert_radius": zombie.alert_radius,
                    "pursuit_timer": zombie.pursuit_timer,
                    "howl_cooldown": zombie.howl_cooldown,
                    "camp_pressure": zombie.camp_pressure,
                    "variant": zombie.variant,
                    "weapon_name": zombie.weapon_name,
                    "expedition_skirmish": bool(getattr(zombie, "expedition_skirmish", False)),
                }
                for zombie in self.zombies
            ],
            "active_dynamic_events": [
                {
                    "uid": event.uid,
                    "kind": event.kind,
                    "label": event.label,
                    "pos": self.vec_to_list(event.pos),
                    "timer": event.timer,
                    "urgency": event.urgency,
                    "target_name": event.target_name,
                    "building_uid": event.building_uid,
                    "data": dict(event.data),
                    "resolved": event.resolved,
                }
                for event in self.active_dynamic_events
            ],
            "active_expedition": active_expedition,
        }

    def save_game(self, *, auto: bool = False) -> tuple[bool, str]:
        if self.smoke_test:
            return False, "Smoke test nao grava save."
        try:
            save_data = self.serialize_save_data()
            SAVE_FILE.write_text(json.dumps(save_data, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
            pygame.image.save(self.fog_of_war, str(SAVE_FOG_FILE))
        except (OSError, TypeError, ValueError, pygame.error):
            return False, "Falha ao gravar o save."
        self.refresh_title_actions()
        return True, "Auto-save concluido." if auto else "Jogo salvo."

    def apply_loaded_data(self, data: dict[str, object]) -> None:
        self.runtime_settings.update({key: float(value) for key, value in dict(data.get("runtime_settings", {})).items()})
        self.audio.apply_settings(self.runtime_settings)
        self.chat_messages = list(data.get("chat_messages", []))
        self.chat_scroll = float(data.get("chat_scroll", 0.0))
        self.dialog_survivor_name = None
        self.day = int(data.get("day", self.day))
        self.time_minutes = float(data.get("time_minutes", self.time_minutes))
        self.previous_night = bool(data.get("previous_night", self.previous_night))
        self.focus_mode = str(data.get("focus_mode", self.focus_mode))
        self.logs = int(data.get("logs", self.logs))
        self.wood = int(data.get("wood", self.wood))
        self.food = int(data.get("food", self.food))
        self.herbs = int(data.get("herbs", self.herbs))
        self.scrap = int(data.get("scrap", self.scrap))
        self.meals = int(data.get("meals", self.meals))
        self.medicine = int(data.get("medicine", self.medicine))
        self.camp_level = int(data.get("camp_level", self.camp_level))
        self.bonfire_heat = float(data.get("bonfire_heat", self.bonfire_heat))
        self.bonfire_ember_bed = float(data.get("bonfire_ember_bed", self.bonfire_ember_bed))
        self.event_message = str(data.get("event_message", self.event_message))
        self.event_timer = float(data.get("event_timer", self.event_timer))
        self.morale_flash = float(data.get("morale_flash", self.morale_flash))
        self.screen_shake = float(data.get("screen_shake", self.screen_shake))
        self.social_timer = float(data.get("social_timer", self.social_timer))
        self.dynamic_event_cooldown = float(data.get("dynamic_event_cooldown", self.dynamic_event_cooldown))
        self.next_dynamic_event_uid = int(data.get("next_dynamic_event_uid", self.next_dynamic_event_uid))
        self.spawn_timer = float(data.get("spawn_timer", self.spawn_timer))
        self.spawn_budget = int(data.get("spawn_budget", self.spawn_budget))
        self.horde_active = bool(data.get("horde_active", self.horde_active))
        self.day_spawn_timer = float(data.get("day_spawn_timer", self.day_spawn_timer))
        self.next_recruit_index = int(data.get("next_recruit_index", self.next_recruit_index))
        self.next_building_uid = int(data.get("next_building_uid", self.next_building_uid))
        self.next_build_request_uid = int(data.get("next_build_request_uid", self.next_build_request_uid))
        self.player_sleeping = bool(data.get("player_sleeping", False))
        slot_data = data.get("player_sleep_slot")
        self.player_sleep_slot = dict(slot_data) if isinstance(slot_data, dict) else None
        if self.player_sleep_slot:
            for key in ("pos", "sleep_pos", "interact_pos"):
                if key in self.player_sleep_slot:
                    self.player_sleep_slot[key] = self.list_to_vec(self.player_sleep_slot.get(key), Vector2())
        self.player_sleep_elapsed = float(data.get("player_sleep_elapsed", 0.0))
        self.weather_kind = str(data.get("weather_kind", self.weather_kind))
        self.weather_strength = float(data.get("weather_strength", self.weather_strength))
        self.weather_timer = float(data.get("weather_timer", self.weather_timer))
        self.weather_label = str(data.get("weather_label", self.weather_label))
        self.faction_standings = {str(key): float(value) for key, value in dict(data.get("faction_standings", {})).items()}

        player_data = dict(data.get("player", {}))
        self.player.pos = self.list_to_vec(player_data.get("pos"), self.player.pos)
        self.player.health = float(player_data.get("health", self.player.health))
        self.player.max_health = float(player_data.get("max_health", self.player.max_health))
        self.player.stamina = float(player_data.get("stamina", self.player.stamina))
        self.player.max_stamina = float(player_data.get("max_stamina", self.player.max_stamina))
        self.player.attack_cooldown = float(player_data.get("attack_cooldown", self.player.attack_cooldown))
        self.player.attack_flash = float(player_data.get("attack_flash", self.player.attack_flash))
        self.player.interact_cooldown = float(player_data.get("interact_cooldown", self.player.interact_cooldown))
        self.player.last_move = self.list_to_vec(player_data.get("last_move"), self.player.last_move)
        self.player.velocity = self.list_to_vec(player_data.get("velocity"), self.player.velocity)
        self.player.facing = self.list_to_vec(player_data.get("facing"), self.player.facing)

        self.named_regions = {}
        for key, region in dict(data.get("named_regions", {})).items():
            if not isinstance(key, str):
                continue
            chunk_x, chunk_y = key.split(",", 1)
            region_data = dict(region)
            for field in ("anchor",):
                region_data[field] = self.list_to_vec(region_data.get(field), Vector2())
            self.named_regions[(int(chunk_x), int(chunk_y))] = region_data

        self.generated_chunks = {}
        for key, chunk in dict(data.get("generated_chunks", {})).items():
            if not isinstance(key, str):
                continue
            chunk_x, chunk_y = key.split(",", 1)
            self.generated_chunks[(int(chunk_x), int(chunk_y))] = dict(chunk)

        from .models import Barricade, Building, DynamicEvent, InterestPoint, ResourceNode, WorldFeature
        from .actors import Survivor, Zombie

        self.endless_features = [
            WorldFeature(
                str(feature.get("kind", "forest")),
                self.list_to_vec(feature.get("pos"), Vector2()),
                float(feature.get("radius", 120.0)),
                float(feature.get("accent", 0.5)),
            )
            for feature in list(data.get("endless_features", []))
        ]
        self.interest_points = [
            InterestPoint(
                str(point.get("feature_kind", "forest")),
                str(point.get("event_kind", "")),
                str(point.get("label", "")),
                self.list_to_vec(point.get("pos"), Vector2()),
                float(point.get("radius", 24.0)),
                float(point.get("pulse", 0.0)),
                bool(point.get("resolved", False)),
            )
            for point in list(data.get("interest_points", []))
        ]
        self.trees = []
        for tree in list(data.get("trees", [])):
            restored = {}
            for key, value in dict(tree).items():
                restored[key] = self.list_to_vec(value, Vector2()) if key == "pos" else value
            self.trees.append(restored)
        self.resource_nodes = [
            ResourceNode(
                str(node.get("kind", "food")),
                self.list_to_vec(node.get("pos"), Vector2()),
                int(node.get("amount", 1)),
                int(node.get("radius", 22)),
                variant=str(node.get("variant", "")),
                cooldown=float(node.get("cooldown", 0.0)),
                renewable=bool(node.get("renewable", False)),
                respawn_delay=float(node.get("respawn_delay", 180.0)),
            )
            for node in list(data.get("resource_nodes", []))
        ]
        self.buildings = [
            Building(
                uid=int(building.get("uid", 0)),
                kind=str(building.get("kind", "barraca")),
                pos=self.list_to_vec(building.get("pos"), Vector2()),
                size=float(building.get("size", 30.0)),
                assigned_to=building.get("assigned_to"),
                work_phase=float(building.get("work_phase", 0.0)),
            )
            for building in list(data.get("buildings", []))
        ]
        self.build_requests = [
            BuildingRequest(
                uid=int(request.get("uid", 0)),
                requester_name=str(request.get("requester_name", "")),
                kind=str(request.get("kind", "barraca")),
                label=str(request.get("label", "Obra")),
                pos=self.list_to_vec(request.get("pos"), Vector2()),
                size=float(request.get("size", 30.0)),
                approved=bool(request.get("approved", False)),
                progress=float(request.get("progress", 0.0)),
                assigned_to=request.get("assigned_to"),
            )
            for request in list(data.get("build_requests", []))
        ]
        self.barricades = [
            Barricade(
                angle=float(barricade.get("angle", 0.0)),
                pos=self.list_to_vec(barricade.get("pos"), Vector2()),
                tangent=self.list_to_vec(barricade.get("tangent"), Vector2(1, 0)),
                span=float(barricade.get("span", 74.0)),
                tier=int(barricade.get("tier", 1)),
                spike_level=int(barricade.get("spike_level", 0)),
                max_health=float(barricade.get("max_health", 100.0)),
                health=float(barricade.get("health", 100.0)),
            )
            for barricade in list(data.get("barricades", []))
        ]
        self.survivors = []
        for saved in list(data.get("survivors", [])):
            survivor = Survivor(
                str(saved.get("name", "Sem Nome")),
                str(saved.get("role", "vigia")),
                self.list_to_vec(saved.get("pos"), Vector2()),
                self.list_to_vec(saved.get("home_pos"), Vector2()),
                self.list_to_vec(saved.get("guard_pos"), Vector2()),
                tuple(saved.get("traits", [])),
            )
            survivor.health = float(saved.get("health", survivor.health))
            survivor.max_health = float(saved.get("max_health", survivor.max_health))
            survivor.velocity = self.list_to_vec(saved.get("velocity"), survivor.velocity)
            survivor.facing = self.list_to_vec(saved.get("facing"), survivor.facing)
            survivor.hunger = float(saved.get("hunger", survivor.hunger))
            survivor.energy = float(saved.get("energy", survivor.energy))
            survivor.morale = float(saved.get("morale", survivor.morale))
            survivor.attack_cooldown = float(saved.get("attack_cooldown", 0.0))
            survivor.carry_bundle = {str(key): int(value) for key, value in dict(saved.get("carry_bundle", {})).items()}
            survivor.sleep_shift = int(saved.get("sleep_shift", survivor.sleep_shift))
            survivor.sleep_debt = float(saved.get("sleep_debt", survivor.sleep_debt))
            survivor.exhaustion = float(saved.get("exhaustion", survivor.exhaustion))
            survivor.insanity = float(saved.get("insanity", survivor.insanity))
            survivor.trust_leader = float(saved.get("trust_leader", survivor.trust_leader))
            survivor.relations = {str(key): float(value) for key, value in dict(saved.get("relations", {})).items()}
            survivor.conflict_cooldown = float(saved.get("conflict_cooldown", 0.0))
            survivor.bond_cooldown = float(saved.get("bond_cooldown", 0.0))
            survivor.assigned_tent_index = int(saved.get("assigned_tent_index", survivor.assigned_tent_index))
            survivor.sleep_slot_kind = str(saved.get("sleep_slot_kind", survivor.sleep_slot_kind))
            survivor.sleep_slot_building_uid = saved.get("sleep_slot_building_uid")
            survivor.assigned_building_id = saved.get("assigned_building_id")
            survivor.assigned_building_kind = saved.get("assigned_building_kind")
            survivor.on_expedition = bool(saved.get("on_expedition", False))
            survivor.expedition_downed = bool(saved.get("expedition_downed", False))
            survivor.expedition_attack_cooldown = float(saved.get("expedition_attack_cooldown", 0.0))
            survivor.leader_directive = saved.get("leader_directive")
            survivor.leader_directive_timer = float(saved.get("leader_directive_timer", 0.0))
            survivor.build_request_cooldown = float(saved.get("build_request_cooldown", survivor.build_request_cooldown))
            survivor.state = "expedition" if survivor.on_expedition else "idle"
            survivor.state_label = "em expedicao" if survivor.on_expedition else "reorganizando"
            self.survivors.append(survivor)

        self.zombies = []
        for saved in list(data.get("zombies", [])):
            boss_profile = None
            if bool(saved.get("is_boss", False)):
                boss_profile = {
                    "name": str(saved.get("boss_name", "")),
                    "zone_key": tuple(saved.get("zone_key", [])),
                    "zone_label": str(saved.get("zone_label", "")),
                    "anchor": self.list_to_vec(saved.get("anchor"), Vector2()),
                    "body": tuple(saved.get("boss_body", (108, 128, 82))),
                    "accent": tuple(saved.get("boss_accent", (54, 62, 44))),
                    "damage": float(saved.get("contact_damage", 13.0)),
                    "radius": float(saved.get("radius", 28.0)),
                    "speed": float(saved.get("speed", 82.0)),
                    "health": float(saved.get("max_health", 280.0)),
                }
            zombie = Zombie(self.list_to_vec(saved.get("pos"), Vector2()), int(saved.get("day", self.day)), boss_profile=boss_profile)
            zombie.health = float(saved.get("health", zombie.health))
            zombie.max_health = float(saved.get("max_health", zombie.max_health))
            zombie.radius = float(saved.get("radius", zombie.radius))
            zombie.speed = float(saved.get("speed", zombie.speed))
            zombie.velocity = self.list_to_vec(saved.get("velocity"), zombie.velocity)
            zombie.facing = self.list_to_vec(saved.get("facing"), zombie.facing)
            zombie.attack_cooldown = float(saved.get("attack_cooldown", 0.0))
            zombie.stagger = float(saved.get("stagger", 0.0))
            zombie.shamble = float(saved.get("shamble", 0.0))
            zombie.zone_key = tuple(saved.get("zone_key", []))
            zombie.zone_label = str(saved.get("zone_label", zombie.zone_label))
            zombie.anchor = self.list_to_vec(saved.get("anchor"), zombie.anchor)
            zombie.boss_body = tuple(saved.get("boss_body", zombie.boss_body))
            zombie.boss_accent = tuple(saved.get("boss_accent", zombie.boss_accent))
            zombie.contact_damage = float(saved.get("contact_damage", zombie.contact_damage))
            zombie.summon_cooldown = float(saved.get("summon_cooldown", 0.0))
            zombie.death_processed = bool(saved.get("death_processed", False))
            zombie.alert_radius = float(saved.get("alert_radius", zombie.alert_radius))
            zombie.pursuit_timer = float(saved.get("pursuit_timer", 0.0))
            zombie.howl_cooldown = float(saved.get("howl_cooldown", 0.0))
            zombie.camp_pressure = float(saved.get("camp_pressure", zombie.camp_pressure))
            zombie.variant = str(saved.get("variant", zombie.variant))
            zombie.weapon_name = str(saved.get("weapon_name", zombie.weapon_name))
            zombie.expedition_skirmish = bool(saved.get("expedition_skirmish", False))
            self.zombies.append(zombie)

        self.active_dynamic_events = [
            DynamicEvent(
                uid=int(event.get("uid", 0)),
                kind=str(event.get("kind", "")),
                label=str(event.get("label", "")),
                pos=self.list_to_vec(event.get("pos"), Vector2()),
                timer=float(event.get("timer", 0.0)),
                urgency=float(event.get("urgency", 0.0)),
                target_name=event.get("target_name"),
                building_uid=event.get("building_uid"),
                data=dict(event.get("data", {})),
                resolved=bool(event.get("resolved", False)),
            )
            for event in list(data.get("active_dynamic_events", []))
        ]
        active_expedition = data.get("active_expedition")
        self.active_expedition = dict(active_expedition) if isinstance(active_expedition, dict) else None
        if self.active_expedition and self.active_expedition.get("skirmish_pos") is not None:
            self.active_expedition["skirmish_pos"] = self.list_to_vec(self.active_expedition.get("skirmish_pos"), Vector2())

        self.layout_camp_core()
        self.terrain_surface = self.build_terrain_surface()
        if SAVE_FOG_FILE.exists():
            self.fog_of_war = pygame.image.load(str(SAVE_FOG_FILE)).convert_alpha()
        self.refresh_barricade_strength()
        self.prune_build_requests()
        self.assign_building_specialists()
        self.refresh_title_actions()
        if not self.chat_messages:
            self.seed_chat_log()
        self.clamp_chat_scroll()

    def load_game(self) -> tuple[bool, str]:
        if not self.save_exists():
            return False, "Nenhum save encontrado."
        try:
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, "Save corrompido ou ilegivel."
        seed = data.get("seed", self.seed)
        current_smoke_test = self.smoke_test
        self.__init__(seed=seed if isinstance(seed, int) or seed is None else None, smoke_test=current_smoke_test)
        self.apply_loaded_data(data)
        self.scenes.change(SceneId.GAMEPLAY)
        self.set_event_message("Save carregado. A clareira voltou a respirar do ponto salvo.", duration=5.4)
        return True, "Save carregado."

    def selected_build_recipe(self) -> dict[str, object]:
        index = max(0, min(len(self.build_recipes) - 1, self.selected_build_slot - 1))
        return self.build_recipes[index]

    def adjust_runtime_setting(self, key: str, delta: float, low: float, high: float) -> None:
        self.runtime_settings[key] = clamp(self.runtime_settings.get(key, 0.0) + delta, low, high)
        self.audio.apply_settings(self.runtime_settings)

    def title_setting_value_label(self, key: str) -> str:
        return f"{int(round(self.runtime_settings.get(key, 0.0) * 100))}%"

    def title_ui_layout(self) -> dict[str, object]:
        return ui_helpers.title_ui_layout(self)

    def tips_ui_layout(self) -> dict[str, pygame.Rect]:
        return ui_helpers.tips_ui_layout(self)

    def society_panel_layout(self) -> dict[str, pygame.Rect]:
        return ui_helpers.society_panel_layout(self)

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

    def handle_title_input(self) -> None:
        layout = self.title_ui_layout()
        mouse_pos = self.input_state.mouse_screen
        clicked = self.input_state.attack_pressed
        hovered_action = next((index for index, rect in enumerate(layout["action_rows"]) if rect.collidepoint(mouse_pos)), None)
        hovered_setting = next((index for index, item in enumerate(layout["setting_rows"]) if item["row"].collidepoint(mouse_pos)), None)

        if hovered_action is not None and hovered_action != self.title_action_index:
            self.title_action_index = hovered_action
        if hovered_setting is not None and hovered_setting != self.title_setting_index:
            self.title_setting_index = hovered_setting

        if self.input_state.menu_up:
            self.title_action_index = (self.title_action_index - 1) % len(self.title_actions)
            self.audio.play_ui("focus")
        elif self.input_state.menu_down:
            self.title_action_index = (self.title_action_index + 1) % len(self.title_actions)
            self.audio.play_ui("focus")
        if self.title_settings_open and (self.input_state.menu_left or self.input_state.menu_right):
            key, _, step, low, high = self.title_setting_entries[self.title_setting_index]
            direction = -1.0 if self.input_state.menu_left else 1.0
            self.adjust_runtime_setting(str(key), float(step) * direction, float(low), float(high))
            self.audio.play_ui("focus")

        if clicked and hovered_setting is not None:
            key, _, step, low, high = self.title_setting_entries[hovered_setting]
            setting_ui = layout["setting_rows"][hovered_setting]
            if setting_ui["minus"].collidepoint(mouse_pos):
                self.adjust_runtime_setting(str(key), -float(step), float(low), float(high))
                self.audio.play_ui("focus")
                return
            if setting_ui["plus"].collidepoint(mouse_pos):
                self.adjust_runtime_setting(str(key), float(step), float(low), float(high))
                self.audio.play_ui("focus")
                return

        if not (self.input_state.confirm_pressed or (clicked and hovered_action is not None)):
            return

        choice_index = hovered_action if hovered_action is not None and clicked else self.title_action_index
        choice = self.title_actions[choice_index]
        if choice == "Continuar":
            success, message = self.load_game()
            if success:
                self.audio.play_transition("start")
            else:
                self.set_event_message(message, duration=5.2)
                self.audio.play_alert()
        elif choice == "Novo Jogo":
            self.begin_new_game_flow()
        elif choice == "Configuracoes":
            self.title_settings_open = not self.title_settings_open
            self.audio.play_ui("focus" if self.title_settings_open else "back")
        elif choice == "Sair":
            self.running = False

    def handle_tips_input(self) -> None:
        layout = self.tips_ui_layout()
        mouse_pos = self.input_state.mouse_screen
        clicked = self.input_state.attack_pressed
        page_count = len(self.tutorial_pages)
        on_last = self.tips_index >= page_count - 1

        if self.input_state.cancel_pressed or self.input_state.alt_interact_pressed:
            self.skip_tips_to_gameplay()
            return

        if clicked and layout["skip_button"].collidepoint(mouse_pos):
            self.skip_tips_to_gameplay()
            return

        if self.input_state.confirm_pressed or self.input_state.interact_pressed or (clicked and layout["next_button"].collidepoint(mouse_pos)):
            if on_last:
                self.start_gameplay()
            else:
                self.tips_index = min(page_count - 1, self.tips_index + 1)
                self.audio.play_ui("focus")
            return

    def begin_player_sleep(self, slot: dict[str, object]) -> None:
        self.player_sleeping = True
        self.player_sleep_slot = dict(slot)
        self.player_sleep_elapsed = 0.0
        self.player.velocity *= 0.0
        self.player.pos = Vector2(slot["sleep_pos"])
        self.build_menu_open = False
        self.set_event_message("Voce deitou na barraca. O tempo corre e a sociedade segura o campo sem ordens diretas.", duration=5.8)
        self.spawn_floating_text("dormindo", self.player.pos, PALETTE["muted"])

    def wake_player(self, message: str | None = None) -> None:
        if not self.player_sleeping:
            return
        slot = self.player_sleep_slot
        self.player_sleeping = False
        self.player_sleep_slot = None
        self.player_sleep_elapsed = 0.0
        if slot:
            self.player.pos = Vector2(slot["interact_pos"])
        if message:
            self.set_event_message(message, duration=4.8)
            self.spawn_floating_text("acordado", self.player.pos, PALETTE["accent_soft"])

    def roll_weather(self, *, initial: bool = False) -> None:
        previous_kind = self.weather_kind
        options = ("clear", "wind", "rain")
        weights = (0.42, 0.34, 0.24) if self.day <= 2 else (0.36, 0.34, 0.3)
        if not initial and self.random.random() < 0.34:
            next_kind = previous_kind
        else:
            next_kind = self.random.choices(options, weights=weights, k=1)[0]

        self.weather_kind = next_kind
        if next_kind == "clear":
            self.weather_strength = self.random.uniform(0.18, 0.58)
            self.weather_timer = self.random.uniform(30.0, 48.0)
            self.weather_label = "ceu limpo"
        elif next_kind == "wind":
            self.weather_strength = self.random.uniform(0.32, 0.86)
            self.weather_timer = self.random.uniform(26.0, 44.0)
            self.weather_label = "vento nas copas"
        else:
            self.weather_strength = self.random.uniform(0.38, 0.92)
            self.weather_timer = self.random.uniform(24.0, 40.0)
            self.weather_label = "chuva fina"

        if initial:
            return

        if next_kind != previous_kind:
            message = {
                "clear": "As nuvens abriram e a mata voltou a respirar.",
                "wind": "O vento virou e as copas comecaram a gemer.",
                "rain": "Uma chuva fina caiu sobre a clareira.",
            }[next_kind]
            self.set_event_message(message, duration=5.8)
        else:
            self.weather_timer *= 0.82

    def update_weather(self, dt: float) -> None:
        self.weather_timer -= dt
        if self.weather_timer <= 0:
            self.roll_weather()

    def handle_events(self) -> None:
        self.input_state = self.input.poll()

        if self.input_state.quit_requested:
            if self.scenes.is_gameplay():
                self.open_exit_prompt()
            else:
                self.running = False
            return

        if self.handle_exit_prompt_input():
            return

        if self.input_state.cancel_pressed:
            if self.scenes.is_gameplay() and self.active_dialog_survivor():
                self.close_survivor_dialog()
                self.audio.play_ui("back")
                return
            if self.build_menu_open:
                self.build_menu_open = False
                self.audio.play_ui("back")
                return
            if self.scenes.is_tips():
                self.skip_tips_to_gameplay()
                return
            if self.scenes.is_gameplay():
                self.open_exit_prompt()
            else:
                self.running = False
            return

        if self.scenes.is_title():
            self.handle_title_input()
            return

        if self.scenes.is_tips():
            self.handle_tips_input()
            return

        if self.scenes.is_game_over() and self.input_state.confirm_pressed:
            self.restart_game()
            return

        if not self.scenes.is_gameplay():
            return

        if self.input_state.load_pressed:
            success, message = self.load_game()
            if success:
                self.audio.play_transition("start")
            else:
                self.set_event_message(message, duration=5.2)
                self.audio.play_alert()
            return

        if self.input_state.save_pressed:
            success, message = self.save_game()
            self.set_event_message(message, duration=4.8)
            self.spawn_floating_text("save" if success else "falhou", self.player.pos, PALETTE["accent_soft"] if success else PALETTE["danger_soft"])
            if success:
                self.audio.play_ui("focus")
            else:
                self.audio.play_alert()

        if self.player_sleeping:
            if (
                self.input_state.move.length_squared() > 0
                or self.input_state.interact_pressed
                or self.input_state.alt_interact_pressed
                or self.input_state.attack_pressed
                or self.input_state.confirm_pressed
                or self.input_state.cancel_pressed
                or self.input_state.build_menu_pressed
                or self.input_state.focus_slot is not None
            ):
                self.wake_player("Voce acordou e retomou o controle da clareira.")
            return

        if self.handle_chat_panel_input():
            return

        if self.handle_society_panel_input():
            return

        if self.input_state.build_menu_pressed:
            self.build_menu_open = not self.build_menu_open
            self.audio.play_ui("focus" if self.build_menu_open else "back")
            return

        if self.build_menu_open and self.input_state.focus_slot and 1 <= self.input_state.focus_slot <= len(self.build_recipes):
            self.selected_build_slot = int(self.input_state.focus_slot)
            self.audio.play_ui("focus")
        elif self.input_state.focus_slot == 1:
            self.focus_mode = "balanced"
            self.spawn_floating_text("foco: equilibrio", self.player.pos, PALETTE["text"])
            self.audio.play_ui("focus")
        elif self.input_state.focus_slot == 2:
            self.focus_mode = "supply"
            self.spawn_floating_text("foco: suprimentos", self.player.pos, PALETTE["accent_soft"])
            self.audio.play_ui("focus")
        elif self.input_state.focus_slot == 3:
            self.focus_mode = "fortify"
            self.spawn_floating_text("foco: fortificar", self.player.pos, PALETTE["heal"])
            self.audio.play_ui("focus")
        elif self.input_state.focus_slot == 4:
            self.focus_mode = "morale"
            self.spawn_floating_text("foco: moral", self.player.pos, PALETTE["morale"])
            self.audio.play_ui("focus")

        if self.build_menu_open and self.input_state.attack_pressed:
            recipe = self.selected_build_recipe()
            placed = self.place_building(str(recipe["kind"]), self.screen_to_world(self.input_state.mouse_screen))
            if placed:
                self.audio.play_ui()
            else:
                self.audio.play_alert()
            return

        if self.input_state.interact_pressed:
            self.player.perform_interaction(self, hardline=False)
        if self.input_state.alt_interact_pressed:
            self.player.perform_interaction(self, hardline=True)
        if self.input_state.attack_pressed:
            self.player.perform_attack(self)

    def update(self, dt: float) -> None:
        if self.scenes.is_title() or self.scenes.is_tips():
            self.update_background_simulation(dt)
            return

        if self.exit_prompt_open and self.scenes.is_gameplay():
            return

        if not self.scenes.allows_world_update:
            self.camera.center_on(CAMP_CENTER)
            return

        sim_scale = 7.0 if self.player_sleeping else 1.0
        sim_dt = dt * sim_scale
        self.time_minutes = (self.time_minutes + sim_dt * MINUTES_PER_SECOND) % (24 * 60)
        now_night = self.is_night
        if now_night and not self.previous_night:
            self.begin_night()
        if not now_night and self.previous_night:
            self.begin_day()
        self.previous_night = now_night

        self.update_bonfire(sim_dt)
        self.morale_flash = max(0.0, self.morale_flash - sim_dt * 0.45)
        self.screen_shake = max(0.0, self.screen_shake - sim_dt * 8)
        self.event_timer = max(0.0, self.event_timer - sim_dt)
        self.update_weather(sim_dt)

        self.player.update(self, sim_dt if self.player_sleeping else dt)
        self.ensure_endless_world(self.player.pos)
        self.update_player_biome()
        self.ensure_zone_boss_near_player()
        self.reveal_world_around_player()
        self.prune_build_requests()
        self.assign_building_specialists()
        self.update_dynamic_events(sim_dt)
        self.update_survivor_barks(sim_dt)
        self.update_active_expedition(sim_dt)
        self.resolve_actor_camp_collision(self.player)

        for node in self.resource_nodes:
            node.update(sim_dt)
        for survivor in self.survivors:
            survivor.update(self, sim_dt)
            self.resolve_actor_camp_collision(survivor)
        self.update_social_dynamics(sim_dt)
        for zombie in self.zombies:
            zombie.update(self, sim_dt)

        self.normalize_stockpile()
        self.resolve_defeated_zone_bosses()
        self.zombies = [zombie for zombie in self.zombies if zombie.is_alive()]
        for floating in list(self.floating_texts):
            if not floating.update(sim_dt):
                self.floating_texts.remove(floating)
        for ember in list(self.embers):
            if not ember.update(sim_dt):
                self.embers.remove(ember)
        for pulse in list(self.damage_pulses):
            if not pulse.update(sim_dt):
                self.damage_pulses.remove(pulse)
        for mote in self.fog_motes:
            mote.update(sim_dt * (1.2 if now_night else 0.75))

        if now_night:
            self.spawn_timer -= sim_dt
            if self.spawn_budget > 0 and self.spawn_timer <= 0:
                self.spawn_night_zombie()
                self.spawn_timer = max(0.95 if self.horde_active else 1.2, (2.7 if self.horde_active else 3.5) - self.day * 0.06)
        else:
            self.day_spawn_timer -= sim_dt
            if (
                self.day_spawn_timer <= 0
                and self.player.pos.distance_to(CAMP_CENTER) > self.camp_clearance_radius() + 220
                and len(self.zombies) < 12
                and self.random.random() < 0.42
            ):
                self.spawn_forest_ambient_zombie()
                self.day_spawn_timer = self.random.uniform(14.0, 24.0)
            elif self.day_spawn_timer <= 0:
                self.day_spawn_timer = self.random.uniform(12.0, 18.0)

        if self.player_sleeping:
            self.player_sleep_elapsed += sim_dt
            if self.active_dynamic_events:
                self.wake_player("Uma crise bateu no campo e arrancou voce do sono.")
            elif self.find_closest_zombie(self.player.pos, 160):
                self.wake_player("Barulho demais perto das barracas. Voce acordou no susto.")
            if self.player.stamina >= self.player.max_stamina - 1 and self.player.health >= self.player.max_health - 1 and self.player_sleep_elapsed >= 60:
                self.wake_player("Voce acordou depois de algumas horas e o campo ainda segue de pe.")

        if self.average_morale() <= 8:
            self.scenes.change(SceneId.GAME_OVER)
            self.audio.play_alert()
        if not self.player.is_alive():
            self.scenes.change(SceneId.GAME_OVER)
            self.audio.play_alert()
        if not self.living_survivors():
            self.scenes.change(SceneId.GAME_OVER)
            self.audio.play_alert()

        self.camera.center_on(self.player.pos)
        self.audio.update(self, dt)

    def update_background_simulation(self, dt: float) -> None:
        self.title_bg_phase += dt
        self.event_timer = max(0.0, self.event_timer - dt)
        self.screen_shake = max(0.0, self.screen_shake - dt * 8)
        self.morale_flash = max(0.0, self.morale_flash - dt * 0.45)

        for node in self.resource_nodes:
            node.update(dt * 0.5)
        for survivor in self.survivors:
            survivor.update(self, dt * 0.5)
            self.resolve_actor_camp_collision(survivor)
        for zombie in self.zombies:
            zombie.update(self, dt * 0.5)
        self.update_survivor_barks(dt * 0.5)
        self.zombies = [zombie for zombie in self.zombies if zombie.is_alive()]

        for floating in list(self.floating_texts):
            if not floating.update(dt):
                self.floating_texts.remove(floating)
        for ember in list(self.embers):
            if not ember.update(dt):
                self.embers.remove(ember)
        for pulse in list(self.damage_pulses):
            if not pulse.update(dt):
                self.damage_pulses.remove(pulse)
        for mote in self.fog_motes:
            mote.update(dt * 0.85)

        self.title_bg_spawn_timer -= dt
        if self.title_bg_spawn_timer <= 0:
            if len(self.zombies) < 5 and self.random.random() < 0.72:
                self.spawn_forest_ambient_zombie()
            self.title_bg_spawn_timer = self.random.uniform(7.0, 12.0)

        orbit = CAMP_CENTER + Vector2(
            math.cos(self.title_bg_phase * 0.18) * 170,
            math.sin(self.title_bg_phase * 0.24) * 96,
        )
        self.camera.center_on(orbit)
        self.audio.update(self, dt)

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
