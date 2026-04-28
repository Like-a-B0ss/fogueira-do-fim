from __future__ import annotations

import pygame
from pygame import Vector2

from ..entities import Actor, Survivor, Zombie
from ..core.config import PALETTE, clamp
from ..domain.camp import camp_construction, camp_interactions, camp_lifecycle, camp_priorities, camp_residents, camp_social, chief_tasks, economy
from ..domain.combat import threats
from ..domain.events import dynamic_events, expeditions
from ..domain.resources import resource_gathering, resource_generation
from ..domain.world import exploration, world_atmosphere, world_basics, world_context, world_generation, world_runtime, world_visuals, zones
from ..core.models import Barricade, Building, BuildingRequest, ChiefTask, DynamicEvent, InterestPoint, ResourceNode, WorldFeature


class WorldMixin:
    def unlimited_resources_enabled(self) -> bool:
        return world_basics.unlimited_resources_enabled(self)

    def maintain_unlimited_resources(self) -> None:
        world_basics.maintain_unlimited_resources(self)

    @property
    def is_night(self) -> bool:
        return world_basics.is_night(self)

    def daylight_factor(self) -> float:
        return world_atmosphere.daylight_factor(self)

    def weather_transition_factor(self) -> float:
        return world_atmosphere.weather_transition_factor(self)

    def weather_signature(self, kind: str, strength: float) -> dict[str, float]:
        return world_atmosphere.weather_signature(self, kind, strength)

    def blended_weather_signature(self) -> dict[str, float]:
        return world_atmosphere.blended_weather_signature(self)

    def weather_cloud_cover(self) -> float:
        return world_atmosphere.weather_cloud_cover(self)

    def weather_precipitation_factor(self) -> float:
        return world_atmosphere.weather_precipitation_factor(self)

    def weather_wind_factor(self) -> float:
        return world_atmosphere.weather_wind_factor(self)

    def weather_mist_factor(self) -> float:
        return world_atmosphere.weather_mist_factor(self)

    def weather_storm_factor(self) -> float:
        return world_atmosphere.weather_storm_factor(self)

    def visual_darkness_factor(self) -> float:
        return world_atmosphere.visual_darkness_factor(self)

    def daylight_phase_label(self) -> str:
        return world_atmosphere.daylight_phase_label(self)

    def weather_mood_label(self) -> str:
        return world_atmosphere.weather_mood_label(self)

    def random_world_pos(self, margin: float = 140) -> Vector2:
        return world_generation.random_world_pos(self, margin)

    def hash_noise(self, x: int, y: int, seed_offset: int = 0) -> float:
        return world_generation.hash_noise(self, x, y, seed_offset)

    def chunk_key_for_pos(self, pos: Vector2) -> tuple[int, int]:
        return world_generation.chunk_key_for_pos(self, pos)

    def chunk_origin(self, chunk_x: int, chunk_y: int) -> Vector2:
        return world_generation.chunk_origin(self, chunk_x, chunk_y)

    def region_chunk_span(self) -> int:
        return zones.region_chunk_span(self)

    def region_key_for_chunk(self, chunk_x: int, chunk_y: int) -> tuple[int, int]:
        return zones.region_key_for_chunk(self, chunk_x, chunk_y)

    def region_key_for_pos(self, pos: Vector2) -> tuple[int, int]:
        return zones.region_key_for_pos(self, pos)

    def region_origin(self, region_x: int, region_y: int) -> Vector2:
        return zones.region_origin(self, region_x, region_y)

    def chunk_biome_kind(self, chunk_x: int, chunk_y: int) -> str:
        return zones.chunk_biome_kind(self, chunk_x, chunk_y)

    def biome_palette(self, kind: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        return zones.biome_palette(self, kind)

    def biome_label(self, kind: str) -> str:
        return zones.biome_label(self, kind)

    def generate_region_name(self, biome: str, region_x: int, region_y: int) -> str:
        return zones.generate_region_name(self, biome, region_x, region_y)

    def region_has_zone_boss(self, anchor: Vector2, region_x: int, region_y: int) -> bool:
        return zones.region_has_zone_boss(self, anchor, region_x, region_y)

    def zone_boss_blueprint(self, biome: str, region_name: str, region_key: tuple[int, int], anchor: Vector2) -> dict[str, object]:
        return zones.zone_boss_blueprint(self, biome, region_name, region_key, anchor)

    def region_expedition_blueprint(self, biome: str, region_x: int, region_y: int) -> dict[str, object]:
        return zones.region_expedition_blueprint(self, biome, region_x, region_y)

    def ensure_named_region(self, region_x: int, region_y: int) -> dict[str, object]:
        return zones.ensure_named_region(self, region_x, region_y)

    def camp_clearance_radius(self) -> float:
        return zones.camp_clearance_radius(self)

    def ensure_endless_world(self, center: Vector2, radius: int = 3) -> None:
        world_generation.ensure_endless_world(self, center, radius)

    def generate_chunk(self, chunk_x: int, chunk_y: int) -> None:
        world_generation.generate_chunk(self, chunk_x, chunk_y)

    def camp_rect(self, padding: float = 0.0) -> pygame.Rect:
        return world_basics.camp_rect(self, padding)

    def camp_visual_ellipses(self, padding: float = 0.0) -> list[pygame.Rect]:
        return world_visuals.camp_visual_ellipses(self, padding)

    def camp_visual_bounds(self, padding: float = 0.0) -> pygame.Rect:
        return world_visuals.camp_visual_bounds(self, padding)

    def camp_ground_anchors(self) -> list[Vector2]:
        return world_visuals.camp_ground_anchors(self)

    def paint_camp_ground(self, surface: pygame.Surface) -> None:
        world_visuals.paint_camp_ground(self, surface)

    def point_in_camp_square(self, pos: Vector2, padding: float = 0.0) -> bool:
        return world_basics.point_in_camp_square(self, pos, padding)

    def camp_loop_points(self, inset: float = 0.0, *, segments_per_side: int = 4, jitter: float = 0.0) -> list[Vector2]:
        return world_visuals.camp_loop_points(self, inset, segments_per_side=segments_per_side, jitter=jitter)

    def camp_perimeter_point(self, seed_index: int = 0, *, jitter: float = 0.0) -> Vector2:
        return world_visuals.camp_perimeter_point(self, seed_index, jitter=jitter)

    def guard_posts(self) -> list[Vector2]:
        return world_basics.guard_posts(self)

    def layout_camp_core(self) -> None:
        world_basics.layout_camp_core(self)

    def create_recruit_pool(self) -> list[dict[str, object]]:
        return world_basics.create_recruit_pool(self)

    def create_build_recipes(self) -> list[dict[str, object]]:
        return camp_construction.create_build_recipes(self)

    def create_faction_standings(self) -> dict[str, float]:
        return dynamic_events.create_faction_standings(self)

    def faction_label(self, key: str) -> str:
        return dynamic_events.faction_label(self, key)

    def adjust_faction_standing(self, key: str, delta: float) -> float:
        return dynamic_events.adjust_faction_standing(self, key, delta)

    def faction_standing_label(self, key: str) -> str:
        return dynamic_events.faction_standing_label(self, key)

    def strongest_faction(self) -> tuple[str, float]:
        return dynamic_events.strongest_faction(self)

    def build_recipe_for(self, kind: str) -> dict[str, object]:
        return economy.build_recipe_for(self, kind)

    def economy_phase_score(self) -> int:
        return economy.economy_phase_score(self)

    def economy_phase_key(self) -> str:
        return economy.economy_phase_key(self)

    def economy_phase_label(self) -> str:
        return economy.economy_phase_label(self)

    def tower_defense_bonus(self) -> float:
        return economy.tower_defense_bonus(self)

    def kitchen_morale_bonus(self) -> float:
        return economy.kitchen_morale_bonus(self)

    def infirmary_safety_bonus(self) -> float:
        return economy.infirmary_safety_bonus(self)

    def sawmill_expansion_discount(self) -> float:
        return economy.sawmill_expansion_discount(self)

    def radio_signal_bonus(self) -> float:
        return economy.radio_signal_bonus(self)

    def build_cost_for(self, recipe_or_kind: dict[str, object] | str) -> tuple[int, int]:
        return economy.build_cost_for(self, recipe_or_kind)

    def sawmill_output(self, role: str) -> int:
        return economy.sawmill_output(self, role)

    def cookhouse_output(self, role: str) -> int:
        return economy.cookhouse_output(self, role)

    def garden_harvest_bundle(self, role: str) -> dict[str, int]:
        return economy.garden_harvest_bundle(self, role)

    def garden_regrow_duration(self) -> float:
        return economy.garden_regrow_duration(self)

    def garden_is_ready(self, building: Building | None) -> bool:
        return economy.garden_is_ready(self, building)

    def start_garden_regrow(self, building: Building) -> None:
        economy.start_garden_regrow(self, building)

    def update_buildings(self, dt: float) -> None:
        economy.update_buildings(self, dt)

    def clinic_medicine_output(self) -> int:
        return economy.clinic_medicine_output(self)

    def daily_ration_demand(self) -> int:
        return economy.daily_ration_demand(self)

    def apply_daily_rations(self) -> tuple[int, int, int]:
        return economy.apply_daily_rations(self)

    def expedition_provision_cost(self) -> dict[str, int]:
        return expeditions.expedition_provision_cost(self)

    def expedition_members(self) -> list[Survivor]:
        return expeditions.expedition_members(self)

    def expedition_visible_members(self) -> list[Survivor]:
        return expeditions.expedition_visible_members(self)

    def expedition_member_anchor(self, survivor: Survivor) -> Vector2:
        return expeditions.expedition_member_anchor(self, survivor)

    def nearest_downed_expedition_member(self, pos: Vector2, max_distance: float = 86.0) -> Survivor | None:
        return expeditions.nearest_downed_expedition_member(self, pos, max_distance)

    def revive_expedition_member(self, survivor: Survivor) -> None:
        expeditions.revive_expedition_member(self, survivor)

    def update_expedition_members(self, dt: float) -> None:
        expeditions.update_expedition_members(self, dt)

    def expedition_candidate_survivors(self) -> list[Survivor]:
        return expeditions.expedition_candidate_survivors(self)

    def best_expedition_region(self) -> dict[str, object] | None:
        return expeditions.best_expedition_region(self)

    def expedition_status_text(self, *, short: bool = False) -> str | None:
        return expeditions.expedition_status_text(self, short=short)

    def expedition_route_direction(self, expedition: dict[str, object] | None = None) -> Vector2:
        return expeditions.expedition_route_direction(self, expedition)

    def expedition_route_edge_point(self, expedition: dict[str, object] | None = None) -> Vector2:
        return expeditions.expedition_route_edge_point(self, expedition)

    def expedition_destination_point(self, expedition: dict[str, object] | None = None) -> Vector2:
        return expeditions.expedition_destination_point(self, expedition)

    def expedition_caravan_state(self) -> dict[str, object] | None:
        return expeditions.expedition_caravan_state(self)

    def expedition_distress_pos(self, expedition: dict[str, object] | None = None) -> Vector2:
        return expeditions.expedition_distress_pos(self, expedition)

    def expedition_skirmish_pos(self, expedition: dict[str, object] | None = None) -> Vector2:
        return expeditions.expedition_skirmish_pos(self, expedition)

    def spawn_expedition_skirmish(self, pos: Vector2, count: int) -> None:
        expeditions.spawn_expedition_skirmish(self, pos, count)

    def spawn_expedition_trailing_zombies(self, expedition: dict[str, object], count: int) -> None:
        expeditions.spawn_expedition_trailing_zombies(self, expedition, count)

    def launch_best_expedition(self) -> tuple[bool, str]:
        return expeditions.launch_best_expedition(self)

    def recall_active_expedition(self) -> tuple[bool, str]:
        return expeditions.recall_active_expedition(self)

    def resolve_active_expedition(self) -> None:
        expeditions.resolve_active_expedition(self)

    def update_active_expedition(self, dt: float) -> None:
        expeditions.update_active_expedition(self, dt)

    def building_count(self, kind: str) -> int:
        return camp_construction.building_count(self, kind)

    def requested_building_count(self, kind: str) -> int:
        return camp_construction.requested_building_count(self, kind)

    def build_specialty_role(self, kind: str) -> str | None:
        return camp_construction.build_specialty_role(self, kind)

    def build_request_by_uid(self, uid: int | None) -> BuildingRequest | None:
        return camp_construction.build_request_by_uid(self, uid)

    def active_build_requests(self) -> list[BuildingRequest]:
        return camp_construction.active_build_requests(self)

    def prune_build_requests(self) -> None:
        camp_construction.prune_build_requests(self)

    def pending_build_request_for_survivor(self, survivor: Survivor) -> BuildingRequest | None:
        return camp_construction.pending_build_request_for_survivor(self, survivor)

    def requested_building_total(self, kind: str) -> int:
        return camp_construction.requested_building_total(self, kind)

    def desired_survivor_build_kind(self, survivor: Survivor) -> str | None:
        return camp_construction.desired_survivor_build_kind(self, survivor)

    def find_build_request_site(self, kind: str, survivor: Survivor | None = None) -> Vector2 | None:
        return camp_construction.find_build_request_site(self, kind, survivor)

    def propose_survivor_build_request(self, survivor: Survivor) -> BuildingRequest | None:
        return camp_construction.propose_survivor_build_request(self, survivor)

    def approve_build_request(self, request: BuildingRequest) -> tuple[bool, str]:
        return camp_construction.approve_build_request(self, request)

    def complete_build_request(self, request: BuildingRequest) -> Building | None:
        return camp_construction.complete_build_request(self, request)

    def active_chief_tasks(self) -> list[ChiefTask]:
        return chief_tasks.active_chief_tasks(self)

    def generate_chief_tasks(self) -> None:
        chief_tasks.generate_chief_tasks(self)

    def update_chief_tasks(self) -> None:
        chief_tasks.update_chief_tasks(self)

    def complete_chief_task(self, task: ChiefTask) -> None:
        chief_tasks.complete_chief_task(self, task)

    def claim_chief_task_reward(self, task: ChiefTask) -> None:
        chief_tasks.claim_chief_task_reward(self, task)

    def notify_chief_task_progress(self, task_kind: str, **target: object) -> None:
        chief_tasks.notify_chief_task_progress(self, task_kind, **target)

    def camp_sleep_slots(self) -> list[dict[str, object]]:
        return camp_construction.camp_sleep_slots(self)

    def nearest_sleep_slot(self, pos: Vector2, max_distance: float = 82.0) -> dict[str, object] | None:
        return camp_construction.nearest_sleep_slot(self, pos, max_distance)

    def nearest_interaction_hint(self) -> tuple[Vector2, str] | None:
        return camp_interactions.nearest_interaction_hint(self)

    def mouse_interaction_target(self, cursor_world: Vector2) -> dict[str, object] | None:
        return camp_interactions.mouse_interaction_target(self, cursor_world)

    def hovered_interaction_target(self) -> dict[str, object] | None:
        return camp_interactions.hovered_interaction_target(self)

    def prompt_for_interaction_target(self, target: dict[str, object]) -> str | None:
        return camp_interactions.prompt_for_interaction_target(self, target)

    def total_bed_capacity(self) -> int:
        return camp_construction.total_bed_capacity(self)

    def expansion_cost(self) -> tuple[int, int]:
        return camp_construction.expansion_cost(self)

    def can_expand_camp(self) -> bool:
        return camp_construction.can_expand_camp(self)

    def spare_beds(self) -> int:
        return camp_construction.spare_beds(self)

    def building_by_id(self, uid: int | None) -> Building | None:
        return camp_construction.building_by_id(self, uid)

    def building_center_snapped(self, pos: Vector2) -> Vector2:
        return camp_construction.building_center_snapped(self, pos)

    def placement_size_for(self, kind: str) -> float:
        return camp_construction.placement_size_for(self, kind)

    def build_placement_profile(self, kind: str) -> dict[str, float]:
        return camp_construction.build_placement_profile(self, kind)

    def placement_collision_radius(self, kind: str) -> float:
        return camp_construction.placement_collision_radius(self, kind)

    def is_valid_build_position(self, kind: str, pos: Vector2) -> bool:
        return camp_construction.is_valid_build_position(self, kind, pos)

    def player_building_reach(self, kind: str) -> float:
        return camp_construction.player_building_reach(self, kind)

    def nearest_player_usable_building(self, pos: Vector2, max_distance: float = 116.0) -> Building | None:
        return camp_construction.nearest_player_usable_building(self, pos, max_distance)

    def player_building_prompt(self, building: Building, player) -> str:
        return camp_construction.player_building_prompt(self, building, player)

    def use_building_as_player(self, building: Building, player) -> bool:
        return camp_construction.use_building_as_player(self, building, player)

    def place_building(self, kind: str, pos: Vector2) -> bool:
        return camp_construction.place_building(self, kind, pos)

    def refresh_barricade_strength(self) -> None:
        camp_construction.refresh_barricade_strength(self)

    def barricade_upgrade_cost(self, barricade: Barricade) -> tuple[int, int]:
        return camp_construction.barricade_upgrade_cost(self, barricade)

    def can_upgrade_barricade(self, barricade: Barricade) -> bool:
        return camp_construction.can_upgrade_barricade(self, barricade)

    def upgrade_barricade(self, barricade: Barricade) -> bool:
        return camp_construction.upgrade_barricade(self, barricade)

    def workbench_repair_amount(self) -> float:
        return camp_construction.workbench_repair_amount(self)

    def can_use_workshop_saw(self) -> bool:
        return camp_construction.can_use_workshop_saw(self)

    def workshop_plank_bundle(self, role: str | None = None) -> dict[str, int]:
        return camp_construction.workshop_plank_bundle(self, role)

    def cut_planks_at_workshop(self, *, role: str | None = None) -> dict[str, int] | None:
        return camp_construction.cut_planks_at_workshop(self, role=role)

    def stockpile_capacity(self, resource: str) -> int:
        return economy.stockpile_capacity(self, resource)

    def normalize_stockpile(self) -> None:
        economy.normalize_stockpile(self)

    def add_resource_bundle(self, bundle: dict[str, int]) -> dict[str, int]:
        return economy.add_resource_bundle(self, bundle)

    def consume_resource(self, resource: str, amount: int) -> bool:
        return economy.consume_resource(self, resource, amount)

    def has_resource_bundle(self, bundle: dict[str, int]) -> bool:
        return economy.has_resource_bundle(self, bundle)

    def consume_resource_bundle(self, bundle: dict[str, int]) -> bool:
        return economy.consume_resource_bundle(self, bundle)

    def available_fuel(self) -> int:
        return economy.available_fuel(self)

    def consume_fuel(self, amount: int = 1) -> bool:
        return economy.consume_fuel(self, amount)

    def add_fuel_to_bonfire(self) -> tuple[bool, str, tuple[int, int, int]]:
        return economy.add_fuel_to_bonfire(self)

    def bonfire_stage(self) -> str:
        return economy.bonfire_stage(self)

    def update_bonfire(self, dt: float) -> None:
        economy.update_bonfire(self, dt)

    def buildings_of_kind(self, kind: str) -> list[Building]:
        return camp_construction.buildings_of_kind(self, kind)

    def nearest_building_of_kind(self, kind: str, pos: Vector2) -> Building | None:
        return camp_construction.nearest_building_of_kind(self, kind, pos)

    def resource_node_bundle(self, node: ResourceNode, *, role: str | None = None) -> dict[str, int]:
        return resource_gathering.resource_node_bundle(self, node, role=role)

    def bundle_summary(self, bundle: dict[str, int]) -> str:
        return resource_gathering.bundle_summary(self, bundle)

    def most_injured_actor(self) -> Actor | None:
        return camp_residents.most_injured_actor(self)

    def has_medical_supplies(self) -> bool:
        return camp_residents.has_medical_supplies(self)

    def can_treat_infirmary(self) -> bool:
        return camp_residents.can_treat_infirmary(self)

    def sync_survivor_assignments(self) -> None:
        camp_residents.sync_survivor_assignments(self)

    def resolve_actor_camp_collision(self, actor: Actor) -> None:
        camp_residents.resolve_actor_camp_collision(self, actor)

    def relationship_score(self, survivor_a: Survivor, survivor_b: Survivor) -> float:
        return camp_social.relationship_score(self, survivor_a, survivor_b)

    def adjust_relationship(self, survivor_a: Survivor, survivor_b: Survivor, delta: float) -> None:
        camp_social.adjust_relationship(self, survivor_a, survivor_b, delta)

    def adjust_trust(self, survivor: Survivor, delta: float) -> None:
        camp_social.adjust_trust(self, survivor, delta)

    def impact_burst(
        self,
        origin: Vector2,
        color: tuple[int, int, int],
        *,
        radius: float = 12,
        shake: float = 0.0,
        ember_count: int = 0,
        smoky: bool = False,
    ) -> None:
        camp_social.impact_burst(self, origin, color, radius=radius, shake=shake, ember_count=ember_count, smoky=smoky)

    def survivor_bark_options(self, survivor: Survivor) -> list[tuple[str, tuple[int, int, int]]]:
        return camp_social.survivor_bark_options(self, survivor)

    def trigger_survivor_bark(
        self,
        survivor: Survivor,
        text: str,
        color: tuple[int, int, int],
        *,
        duration: float = 2.8,
    ) -> None:
        camp_social.trigger_survivor_bark(self, survivor, text, color, duration=duration)

    def survivors_react_to_event(self, event: DynamicEvent, *, resolved: bool | None = None) -> None:
        camp_social.survivors_react_to_event(self, event, resolved=resolved)

    def update_survivor_barks(self, dt: float) -> None:
        camp_social.update_survivor_barks(self, dt)

    def average_trust(self) -> float:
        return camp_social.average_trust(self)

    def friendship_count(self) -> int:
        return camp_social.friendship_count(self)

    def feud_count(self) -> int:
        return camp_social.feud_count(self)

    def best_friend_name(self, survivor: Survivor) -> str | None:
        return camp_social.best_friend_name(self, survivor)

    def rival_name(self, survivor: Survivor) -> str | None:
        return camp_social.rival_name(self, survivor)

    def latest_social_memory(self, survivor: Survivor, topic: str | None = None) -> dict[str, object] | None:
        return camp_social.latest_social_memory(survivor, topic)

    def social_summary_text(self, survivor: Survivor) -> tuple[str, tuple[int, int, int]]:
        return camp_social.social_summary_text(self, survivor)

    def contextual_build_request_reason(self, survivor: Survivor, kind: str) -> tuple[str, str]:
        return camp_social.contextual_build_request_reason(self, survivor, kind)

    def initialize_survivor_relationships(self) -> None:
        camp_social.initialize_survivor_relationships(self)

    def update_social_dynamics(self, dt: float) -> None:
        camp_social.update_social_dynamics(self, dt)

    def assign_building_specialists(self) -> None:
        camp_social.assign_building_specialists(self)

    def active_guard_names(self) -> set[str]:
        return camp_social.active_guard_names(self)

    def should_survivor_sleep(self, survivor: Survivor) -> bool:
        return camp_social.should_survivor_sleep(self, survivor)

    def expand_camp(self) -> bool:
        return camp_construction.expand_camp(self)

    def recruit_survivor_from_profile(
        self,
        profile: dict[str, object],
        *,
        announce_message: str,
        floating_label: str = "novo morador",
    ) -> Survivor | None:
        return camp_residents.recruit_survivor_from_profile(
            self,
            profile,
            announce_message=announce_message,
            floating_label=floating_label,
        )

    def remove_survivor(self, survivor: Survivor) -> None:
        camp_residents.remove_survivor(self, survivor)

    def try_recruit_survivor(self) -> None:
        camp_residents.try_recruit_survivor(self)

    def generate_world_features(self) -> list[WorldFeature]:
        return exploration.generate_world_features(self)

    def generate_interest_points(self) -> list[InterestPoint]:
        return exploration.generate_interest_points(self)

    def create_fog_of_war_surface(self) -> pygame.Surface:
        return exploration.create_fog_of_war_surface(self)

    def fog_reveal_key(self, center: Vector2, radius: float) -> tuple[int, int, int]:
        return exploration.fog_reveal_key(self, center, radius)

    def record_fog_reveal(self, center: Vector2, radius: float) -> None:
        exploration.record_fog_reveal(self, center, radius)

    def visible_fog_reveals(self, view_rect: pygame.Rect) -> list[tuple[Vector2, float]]:
        return exploration.visible_fog_reveals(self, view_rect)

    def reveal_world_around_player(self) -> None:
        exploration.reveal_world_around_player(self)

    def feature_label(self, kind: str) -> str:
        return exploration.feature_label(self, kind)

    def named_region_at(self, pos: Vector2) -> dict[str, object] | None:
        return zones.named_region_at(self, pos)

    def feature_at_pos(self, pos: Vector2) -> WorldFeature | None:
        return world_context.feature_at_pos(self, pos)

    def surface_audio_at(self, pos: Vector2) -> str:
        return world_context.surface_audio_at(self, pos)

    def unresolved_interest_points(self) -> list[InterestPoint]:
        return world_context.unresolved_interest_points(self)

    def active_dynamic_event(self, kind: str | None = None) -> DynamicEvent | None:
        return dynamic_events.active_dynamic_event(self, kind)

    def dynamic_event_for_survivor(self, survivor: Survivor, kind: str | None = None) -> DynamicEvent | None:
        return dynamic_events.dynamic_event_for_survivor(self, survivor, kind)

    def dynamic_event_summary(self) -> str | None:
        return dynamic_events.dynamic_event_summary(self)

    def spawn_dynamic_event(
        self,
        kind: str,
        label: str,
        pos: Vector2,
        *,
        timer: float,
        urgency: float,
        target_name: str | None = None,
        building_uid: int | None = None,
        data: dict[str, object] | None = None,
    ) -> DynamicEvent:
        return dynamic_events.spawn_dynamic_event(
            self,
            kind,
            label,
            pos,
            timer=timer,
            urgency=urgency,
            target_name=target_name,
            building_uid=building_uid,
            data=data,
        )

    def choose_fire_site(self) -> tuple[Vector2, str, int | None, str]:
        return dynamic_events.choose_fire_site(self)

    def roadside_event_pos(self, *, side: str | None = None) -> Vector2:
        return dynamic_events.roadside_event_pos(self, side=side)

    def dynamic_event_candidates(self) -> list[tuple[str, float, dict[str, object]]]:
        return dynamic_events.dynamic_event_candidates(self)

    def maybe_spawn_dynamic_event(self) -> None:
        dynamic_events.maybe_spawn_dynamic_event(self)

    def resolve_dynamic_event(self, event: DynamicEvent, *, accepted: bool = True) -> bool:
        return dynamic_events.resolve_dynamic_event(self, event, accepted=accepted)

    def fail_dynamic_event(self, event: DynamicEvent) -> None:
        dynamic_events.fail_dynamic_event(self, event)

    def update_dynamic_events(self, dt: float) -> None:
        dynamic_events.update_dynamic_events(self, dt)

    def zone_boss_for_region(self, region_key: tuple[int, int]) -> Zombie | None:
        return zones.zone_boss_for_region(self, region_key)

    def current_named_region(self) -> dict[str, object] | None:
        return zones.current_named_region(self)

    def is_survivor_on_expedition(self, survivor: Survivor) -> bool:
        return bool(getattr(survivor, "on_expedition", False))

    def zone_boss_status_text(self, region: dict[str, object] | None, *, short: bool = False) -> str:
        return zones.zone_boss_status_text(self, region, short=short)

    def ensure_zone_boss_near_player(self) -> None:
        zones.ensure_zone_boss_near_player(self)

    def resolve_defeated_zone_bosses(self) -> None:
        zones.resolve_defeated_zone_bosses(self)

    def set_event_message(self, message: str, duration: float = 7.5) -> None:
        self.event_message = message
        self.event_timer = duration

    def resolve_interest_point(self, interest_point: InterestPoint) -> None:
        world_context.resolve_interest_point(self, interest_point)

    def spawn_local_zombies(
        self,
        center: Vector2,
        count: int,
        *,
        pressure: bool = False,
        spawn_source: str = "",
        summon_chain_budget: int | None = None,
    ) -> None:
        threats.spawn_local_zombies(
            self,
            center,
            count,
            pressure=pressure,
            spawn_source=spawn_source,
            summon_chain_budget=summon_chain_budget,
        )

    def spawn_forest_ambient_zombie(self, *, anchor: Vector2 | None = None, radius: float | None = None) -> None:
        threats.spawn_forest_ambient_zombie(self, anchor=anchor, radius=radius)

    def safe_zombie_spawn_position(self, center: Vector2, min_distance: float, max_distance: float) -> Vector2:
        return threats.safe_zombie_spawn_position(self, center, min_distance, max_distance)

    def update_player_biome(self) -> None:
        world_context.update_player_biome(self)

    def generate_path_network(self) -> list[list[Vector2]]:
        return world_visuals.generate_path_network(self)

    def make_path_points(
        self,
        start: Vector2,
        end: Vector2,
        *,
        variation: float,
        segments: int,
    ) -> list[Vector2]:
        return world_visuals.make_path_points(self, start, end, variation=variation, segments=segments)

    def is_near_path(self, pos: Vector2, radius: float) -> bool:
        return world_basics.is_near_path(self, pos, radius)

    def local_tree_density(self, pos: Vector2) -> float:
        return resource_generation.local_tree_density(self, pos)

    def generate_resource_position(
        self,
        preferred_kinds: tuple[str, ...],
        min_distance: float,
        max_distance: float,
        existing_nodes: list[ResourceNode],
        radius: float,
    ) -> Vector2:
        return resource_generation.generate_resource_position(self, preferred_kinds, min_distance, max_distance, existing_nodes, radius)

    def generate_tents(self) -> list[dict[str, Vector2 | float]]:
        return camp_construction.generate_tents(self)

    def generate_trees(self) -> list[dict[str, object]]:
        return resource_generation.generate_trees(self)

    def generate_resource_nodes(self) -> list[ResourceNode]:
        return resource_generation.generate_resource_nodes(self)

    def random_resource_pos(self, min_distance: float, max_distance: float) -> Vector2:
        return resource_generation.random_resource_pos(self, min_distance, max_distance)

    def generate_barricades(self) -> list[Barricade]:
        return camp_construction.generate_barricades(self)

    def reflow_barricades_for_current_camp_size(self) -> None:
        camp_construction.reflow_barricades_for_current_camp_size(self)

    def generate_survivors(self) -> list[Survivor]:
        return camp_residents.generate_survivors(self)

    def build_terrain_surface(self) -> pygame.Surface:
        return world_visuals.build_terrain_surface(self)

    def tree_is_harvestable(self, tree: dict[str, object]) -> bool:
        return resource_gathering.tree_is_harvestable(self, tree)

    def closest_available_tree(self, origin: Vector2) -> dict[str, object] | None:
        return resource_gathering.closest_available_tree(self, origin)

    def harvest_tree(self, tree: dict[str, object], *, effort: int = 1) -> int:
        return resource_gathering.harvest_tree(self, tree, effort=effort)

    def paint_feature(self, surface: pygame.Surface, feature: WorldFeature) -> None:
        world_visuals.paint_feature(self, surface, feature)

    def draw_path(
        self,
        surface: pygame.Surface,
        points: list[Vector2],
        *,
        base_width: int = 44,
        highlight_width: int = 12,
        base_alpha: int = 160,
        highlight_alpha: int = 90,
    ) -> None:
        world_visuals.draw_path(
            self,
            surface,
            points,
            base_width=base_width,
            highlight_width=highlight_width,
            base_alpha=base_alpha,
            highlight_alpha=highlight_alpha,
        )

    def available_node(self, kind: str) -> bool:
        return resource_gathering.available_node(self, kind)

    def closest_available_node(self, kind: str, origin: Vector2) -> object | None:
        return resource_gathering.closest_available_node(self, kind, origin)

    def has_damaged_barricade(self) -> bool:
        return world_runtime.has_damaged_barricade(self)

    def weakest_barricade(self) -> Barricade | None:
        return world_runtime.weakest_barricade(self)

    def weakest_barricade_health(self) -> float:
        return world_runtime.weakest_barricade_health(self)

    def average_morale(self) -> float:
        return camp_lifecycle.average_morale(self)

    def average_insanity(self) -> float:
        return camp_lifecycle.average_insanity(self)

    def average_health(self) -> float:
        return camp_lifecycle.average_health(self)

    def audio_tension(self) -> float:
        return camp_lifecycle.audio_tension(self)

    def tension_label(self) -> str:
        return camp_lifecycle.tension_label(self)

    def living_survivors(self) -> list[Survivor]:
        return camp_lifecycle.living_survivors(self)

    def camp_invader_zombies(self) -> list[Zombie]:
        return threats.camp_invader_zombies(self)

    def active_zombie_cap(self, *, pressure: bool = False) -> int:
        return threats.active_zombie_cap(self, pressure=pressure)

    def living_zombie_count(self) -> int:
        return threats.living_zombie_count(self)

    def can_spawn_zombie(self, *, pressure: bool = False) -> bool:
        return threats.can_spawn_zombie(self, pressure=pressure)

    def closest_defense_target(self, survivor: Survivor) -> Zombie | None:
        return threats.closest_defense_target(self, survivor)

    def survivor_focus_override(self, survivor: Survivor) -> tuple[str, object | Vector2 | None] | None:
        return camp_priorities.survivor_focus_override(self, survivor)

    def survivor_should_seek_shelter(self, survivor: Survivor, zombie: Zombie) -> bool:
        return threats.survivor_should_seek_shelter(self, survivor, zombie)

    def survivor_should_engage(self, survivor: Survivor, zombie: Zombie) -> bool:
        return threats.survivor_should_engage(self, survivor, zombie)

    def survivor_attack_damage(self, survivor: Survivor) -> float:
        return threats.survivor_attack_damage(self, survivor)

    def spawn_floating_text(
        self,
        text: str,
        pos: Vector2,
        color: tuple[int, int, int],
    ) -> None:
        world_runtime.spawn_floating_text(self, text, pos, color)

    def emit_embers(self, origin: Vector2, amount: int, *, smoky: bool = False) -> None:
        world_runtime.emit_embers(self, origin, amount, smoky=smoky)

    def screen_to_world(self, position: Vector2) -> Vector2:
        return world_runtime.screen_to_world(self, position)

    def world_to_screen(self, position: Vector2) -> Vector2:
        return world_runtime.world_to_screen(self, position)

    def closest_barricade(self, pos: Vector2) -> Barricade | None:
        return world_runtime.closest_barricade(self, pos)

    def closest_target(self, pos: Vector2) -> Actor | None:
        return world_runtime.closest_target(self, pos)

    def find_closest_zombie(self, pos: Vector2, radius: float) -> Zombie | None:
        return threats.find_closest_zombie(self, pos, radius)

    def create_horde_boss_profile(self) -> dict[str, object]:
        return threats.create_horde_boss_profile(self)

    def begin_night(self) -> None:
        camp_lifecycle.begin_night(self)

    def begin_day(self) -> None:
        camp_lifecycle.begin_day(self)

    def spawn_night_zombie(self) -> None:
        threats.spawn_night_zombie(self)
