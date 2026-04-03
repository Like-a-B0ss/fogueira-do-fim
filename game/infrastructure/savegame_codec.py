from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Vector2

from ..entities import Survivor, Zombie
from ..core.models import Barricade, Building, DynamicEvent, InterestPoint, ResourceNode, WorldFeature
from ..core.scenes import SceneId

if TYPE_CHECKING:
    from ..app.session import Game


class SaveGameCodec:
    """Maps the live pygame session into a persistence-friendly snapshot."""

    def vec_to_list(self, value: Vector2) -> list[float]:
        return [round(float(value.x), 3), round(float(value.y), 3)]

    def list_to_vec(self, value: object, fallback: Vector2 | None = None) -> Vector2:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return Vector2(float(value[0]), float(value[1]))
        return Vector2(fallback) if fallback is not None else Vector2()

    def make_json_safe(self, value: object) -> object:
        if isinstance(value, Vector2):
            return self.vec_to_list(value)
        if isinstance(value, dict):
            return {str(key): self.make_json_safe(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self.make_json_safe(item) for item in value]
        if isinstance(value, list):
            return [self.make_json_safe(item) for item in value]
        return value

    def serialize(self, game: "Game") -> dict[str, object]:
        sleep_slot = None
        if game.player_sleep_slot:
            sleep_slot = {
                key: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                for key, value in game.player_sleep_slot.items()
            }
        active_expedition = None
        if game.active_expedition:
            active_expedition = {
                key: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                for key, value in game.active_expedition.items()
            }
        return self.make_json_safe(
            {
                "version": 1,
                "seed": game.seed,
                "runtime_settings": dict(game.runtime_settings),
                "chat_messages": list(game.chat_messages[-48:]),
                "chat_scroll": game.chat_scroll,
                "scene": SceneId.GAMEPLAY,
                "day": game.day,
                "time_minutes": game.time_minutes,
                "previous_night": game.previous_night,
                "focus_mode": game.focus_mode,
                "logs": game.logs,
                "wood": game.wood,
                "food": game.food,
                "herbs": game.herbs,
                "scrap": game.scrap,
                "meals": game.meals,
                "medicine": game.medicine,
                "camp_level": game.camp_level,
                "bonfire_heat": game.bonfire_heat,
                "bonfire_ember_bed": game.bonfire_ember_bed,
                "event_message": game.event_message,
                "event_timer": game.event_timer,
                "morale_flash": game.morale_flash,
                "screen_shake": game.screen_shake,
                "social_timer": game.social_timer,
                "dynamic_event_cooldown": game.dynamic_event_cooldown,
                "next_dynamic_event_uid": game.next_dynamic_event_uid,
                "spawn_timer": game.spawn_timer,
                "spawn_budget": game.spawn_budget,
                "horde_active": game.horde_active,
                "day_spawn_timer": game.day_spawn_timer,
                "next_recruit_index": game.next_recruit_index,
                "next_building_uid": game.next_building_uid,
                "next_build_request_uid": game.next_build_request_uid,
                "player_sleeping": game.player_sleeping,
                "player_sleep_slot": sleep_slot,
                "player_sleep_elapsed": game.player_sleep_elapsed,
                "weather_kind": game.weather_kind,
                "weather_strength": game.weather_strength,
                "weather_target_kind": game.weather_target_kind,
                "weather_target_strength": game.weather_target_strength,
                "weather_timer": game.weather_timer,
                "weather_front_progress": game.weather_front_progress,
                "weather_front_duration": game.weather_front_duration,
                "weather_gust_phase": game.weather_gust_phase,
                "weather_gust_strength": game.weather_gust_strength,
                "weather_label": game.weather_label,
                "faction_standings": dict(game.faction_standings),
                "named_regions": {
                    f"{key[0]},{key[1]}": {
                        field: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                        for field, value in region.items()
                    }
                    for key, region in game.named_regions.items()
                },
                "generated_chunks": {
                    f"{key[0]},{key[1]}": dict(chunk)
                    for key, chunk in game.generated_chunks.items()
                },
                "endless_features": [
                    {
                        "kind": feature.kind,
                        "pos": self.vec_to_list(feature.pos),
                        "radius": feature.radius,
                        "accent": feature.accent,
                    }
                    for feature in game.endless_features
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
                    for point in game.interest_points
                ],
                "trees": [
                    {
                        key: (self.vec_to_list(value) if isinstance(value, Vector2) else value)
                        for key, value in tree.items()
                    }
                    for tree in game.trees
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
                    for node in game.resource_nodes
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
                    for building in game.buildings
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
                    for request in game.build_requests
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
                    for barricade in game.barricades
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
                        "social_memories": list(survivor.social_memories),
                        "social_comment_cooldown": survivor.social_comment_cooldown,
                    }
                    for survivor in game.survivors
                ],
                "player": {
                    "pos": self.vec_to_list(game.player.pos),
                    "health": game.player.health,
                    "max_health": game.player.max_health,
                    "stamina": game.player.stamina,
                    "max_stamina": game.player.max_stamina,
                    "attack_cooldown": game.player.attack_cooldown,
                    "attack_flash": game.player.attack_flash,
                    "interact_cooldown": game.player.interact_cooldown,
                    "last_move": self.vec_to_list(game.player.last_move),
                    "velocity": self.vec_to_list(game.player.velocity),
                    "facing": self.vec_to_list(game.player.facing),
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
                    for zombie in game.zombies
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
                    for event in game.active_dynamic_events
                ],
                "active_expedition": active_expedition,
                "fog_reveals": [
                    {"pos": self.vec_to_list(center), "radius": radius}
                    for center, radius in getattr(game, "fog_reveals", [])
                ],
            }
        )

    def apply(self, game: "Game", data: dict[str, object]) -> None:
        game.runtime_settings.update(
            {key: float(value) for key, value in dict(data.get("runtime_settings", {})).items()}
        )
        game.audio.apply_settings(game.runtime_settings)
        game.chat_messages = list(data.get("chat_messages", []))
        game.chat_scroll = float(data.get("chat_scroll", 0.0))
        game.dialog_survivor_name = None
        game.day = int(data.get("day", game.day))
        game.time_minutes = float(data.get("time_minutes", game.time_minutes))
        game.previous_night = bool(data.get("previous_night", game.previous_night))
        game.focus_mode = str(data.get("focus_mode", game.focus_mode))
        game.logs = int(data.get("logs", game.logs))
        game.wood = int(data.get("wood", game.wood))
        game.food = int(data.get("food", game.food))
        game.herbs = int(data.get("herbs", game.herbs))
        game.scrap = int(data.get("scrap", game.scrap))
        game.meals = int(data.get("meals", game.meals))
        game.medicine = int(data.get("medicine", game.medicine))
        game.camp_level = int(data.get("camp_level", game.camp_level))
        game.bonfire_heat = float(data.get("bonfire_heat", game.bonfire_heat))
        game.bonfire_ember_bed = float(data.get("bonfire_ember_bed", game.bonfire_ember_bed))
        game.event_message = str(data.get("event_message", game.event_message))
        game.event_timer = float(data.get("event_timer", game.event_timer))
        game.morale_flash = float(data.get("morale_flash", game.morale_flash))
        game.screen_shake = float(data.get("screen_shake", game.screen_shake))
        game.social_timer = float(data.get("social_timer", game.social_timer))
        game.dynamic_event_cooldown = float(data.get("dynamic_event_cooldown", game.dynamic_event_cooldown))
        game.next_dynamic_event_uid = int(data.get("next_dynamic_event_uid", game.next_dynamic_event_uid))
        game.spawn_timer = float(data.get("spawn_timer", game.spawn_timer))
        game.spawn_budget = int(data.get("spawn_budget", game.spawn_budget))
        game.horde_active = bool(data.get("horde_active", game.horde_active))
        game.day_spawn_timer = float(data.get("day_spawn_timer", game.day_spawn_timer))
        game.next_recruit_index = int(data.get("next_recruit_index", game.next_recruit_index))
        game.next_building_uid = int(data.get("next_building_uid", game.next_building_uid))
        game.next_build_request_uid = int(data.get("next_build_request_uid", game.next_build_request_uid))
        game.player_sleeping = bool(data.get("player_sleeping", False))
        slot_data = data.get("player_sleep_slot")
        game.player_sleep_slot = dict(slot_data) if isinstance(slot_data, dict) else None
        if game.player_sleep_slot:
            for key in ("pos", "sleep_pos", "interact_pos"):
                if key in game.player_sleep_slot:
                    game.player_sleep_slot[key] = self.list_to_vec(game.player_sleep_slot.get(key), Vector2())
        game.player_sleep_elapsed = float(data.get("player_sleep_elapsed", 0.0))
        game.weather_kind = str(data.get("weather_kind", game.weather_kind))
        game.weather_strength = float(data.get("weather_strength", game.weather_strength))
        game.weather_target_kind = str(data.get("weather_target_kind", game.weather_kind))
        game.weather_target_strength = float(data.get("weather_target_strength", game.weather_strength))
        game.weather_timer = float(data.get("weather_timer", game.weather_timer))
        game.weather_front_progress = float(data.get("weather_front_progress", 1.0))
        game.weather_front_duration = float(data.get("weather_front_duration", 0.0))
        game.weather_gust_phase = float(data.get("weather_gust_phase", game.weather_gust_phase))
        game.weather_gust_strength = float(data.get("weather_gust_strength", 0.0))
        game.weather_flash = 0.0
        game.weather_flash_timer = 0.0
        game.weather_label = str(data.get("weather_label", game.weather_label))
        game.faction_standings = {
            str(key): float(value) for key, value in dict(data.get("faction_standings", {})).items()
        }

        player_data = dict(data.get("player", {}))
        game.player.pos = self.list_to_vec(player_data.get("pos"), game.player.pos)
        game.player.health = float(player_data.get("health", game.player.health))
        game.player.max_health = float(player_data.get("max_health", game.player.max_health))
        game.player.stamina = float(player_data.get("stamina", game.player.stamina))
        game.player.max_stamina = float(player_data.get("max_stamina", game.player.max_stamina))
        game.player.attack_cooldown = float(player_data.get("attack_cooldown", game.player.attack_cooldown))
        game.player.attack_flash = float(player_data.get("attack_flash", game.player.attack_flash))
        game.player.interact_cooldown = float(
            player_data.get("interact_cooldown", game.player.interact_cooldown)
        )
        game.player.last_move = self.list_to_vec(player_data.get("last_move"), game.player.last_move)
        game.player.velocity = self.list_to_vec(player_data.get("velocity"), game.player.velocity)
        game.player.facing = self.list_to_vec(player_data.get("facing"), game.player.facing)

        game.named_regions = {}
        for key, region in dict(data.get("named_regions", {})).items():
            if not isinstance(key, str):
                continue
            chunk_x, chunk_y = key.split(",", 1)
            region_data = dict(region)
            region_data["anchor"] = self.list_to_vec(region_data.get("anchor"), Vector2())
            game.named_regions[(int(chunk_x), int(chunk_y))] = region_data

        game.generated_chunks = {}
        for key, chunk in dict(data.get("generated_chunks", {})).items():
            if not isinstance(key, str):
                continue
            chunk_x, chunk_y = key.split(",", 1)
            game.generated_chunks[(int(chunk_x), int(chunk_y))] = dict(chunk)

        game.endless_features = [
            WorldFeature(
                str(feature.get("kind", "forest")),
                self.list_to_vec(feature.get("pos"), Vector2()),
                float(feature.get("radius", 120.0)),
                float(feature.get("accent", 0.5)),
            )
            for feature in list(data.get("endless_features", []))
        ]
        game.interest_points = [
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
        game.trees = []
        for tree in list(data.get("trees", [])):
            restored = {}
            for key, value in dict(tree).items():
                restored[key] = self.list_to_vec(value, Vector2()) if key == "pos" else value
            game.trees.append(restored)
        game.resource_nodes = [
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
        game.buildings = [
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
        game.build_requests = []
        game.barricades = [
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
        game.survivors = []
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
            survivor.carry_bundle = {
                str(key): int(value) for key, value in dict(saved.get("carry_bundle", {})).items()
            }
            survivor.sleep_shift = int(saved.get("sleep_shift", survivor.sleep_shift))
            survivor.sleep_debt = float(saved.get("sleep_debt", survivor.sleep_debt))
            survivor.exhaustion = float(saved.get("exhaustion", survivor.exhaustion))
            survivor.insanity = float(saved.get("insanity", survivor.insanity))
            survivor.trust_leader = float(saved.get("trust_leader", survivor.trust_leader))
            survivor.relations = {
                str(key): float(value) for key, value in dict(saved.get("relations", {})).items()
            }
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
            survivor.build_request_cooldown = float(
                saved.get("build_request_cooldown", survivor.build_request_cooldown)
            )
            survivor.social_memories = [dict(memory) for memory in list(saved.get("social_memories", []))][-8:]
            survivor.social_comment_cooldown = float(
                saved.get("social_comment_cooldown", survivor.social_comment_cooldown)
            )
            survivor.state = "expedition" if survivor.on_expedition else "idle"
            survivor.state_label = "em expedicao" if survivor.on_expedition else "reorganizando"
            game.survivors.append(survivor)

        game.zombies = []
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
            zombie = Zombie(
                self.list_to_vec(saved.get("pos"), Vector2()),
                int(saved.get("day", game.day)),
                boss_profile=boss_profile,
            )
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
            game.zombies.append(zombie)

        game.active_dynamic_events = [
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
        game.active_expedition = dict(active_expedition) if isinstance(active_expedition, dict) else None
        if game.active_expedition and game.active_expedition.get("skirmish_pos") is not None:
            game.active_expedition["skirmish_pos"] = self.list_to_vec(
                game.active_expedition.get("skirmish_pos"),
                Vector2(),
            )

        game.layout_camp_core()
        game.terrain_surface = game.build_terrain_surface()
        game.create_fog_of_war_surface()
        loaded_reveals = list(data.get("fog_reveals", []))
        if loaded_reveals:
            game.fog_reveals = []
            game.fog_reveal_keys = set()
            for item in loaded_reveals:
                if not isinstance(item, dict):
                    continue
                center = self.list_to_vec(item.get("pos"), Vector2())
                radius = float(item.get("radius", 146.0))
                game.record_fog_reveal(center, radius)
        game.refresh_barricade_strength()
        game.prune_build_requests()
        game.assign_building_specialists()
        game.refresh_title_actions()
        if not game.chat_messages:
            game.seed_chat_log()
        game.clamp_chat_scroll()







