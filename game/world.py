from __future__ import annotations

import math

import pygame
from pygame import Vector2

from .actors import Actor, Survivor, Zombie
from .config import (
    CAMP_CENTER,
    CAMP_RADIUS,
    CHUNK_SIZE,
    DAWN_MINUTES,
    DUSK_MINUTES,
    PALETTE,
    ROLE_COLORS,
    TESTING_SETTINGS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    angle_to_vector,
    clamp,
    lerp,
)
from .models import (
    Barricade,
    Building,
    BuildingRequest,
    DamagePulse,
    DynamicEvent,
    Ember,
    FloatingText,
    InterestPoint,
    ResourceNode,
    WorldFeature,
)
from . import world_social_system as social_system


class WorldMixin:
    def unlimited_resources_enabled(self) -> bool:
        return bool(TESTING_SETTINGS.get("unlimited_resources", False))

    def maintain_unlimited_resources(self) -> None:
        if not self.unlimited_resources_enabled():
            return
        reserves = {
            "logs": 9999,
            "wood": 9999,
            "food": 9999,
            "herbs": 9999,
            "scrap": 9999,
            "meals": 9999,
            "medicine": 9999,
        }
        for resource, amount in reserves.items():
            setattr(self, resource, amount)

    @property
    def is_night(self) -> bool:
        time_value = self.time_minutes % (24 * 60)
        return time_value < DAWN_MINUTES or time_value >= DUSK_MINUTES

    def daylight_factor(self) -> float:
        """Retorna a luz do dia em valor continuo para amanhecer e entardecer suaves."""
        time_value = self.time_minutes % (24 * 60)
        sunrise_start = DAWN_MINUTES - 70
        sunrise_end = DAWN_MINUTES + 65
        sunset_start = DUSK_MINUTES - 78
        sunset_end = DUSK_MINUTES + 72

        if sunrise_end <= time_value < sunset_start:
            return 1.0
        if time_value < sunrise_start or time_value >= sunset_end:
            return 0.0

        def smooth_step(value: float) -> float:
            value = clamp(value, 0.0, 1.0)
            return value * value * (3.0 - 2.0 * value)

        if sunrise_start <= time_value < sunrise_end:
            blend = (time_value - sunrise_start) / max(1.0, sunrise_end - sunrise_start)
            return smooth_step(blend)

        blend = (time_value - sunset_start) / max(1.0, sunset_end - sunset_start)
        return 1.0 - smooth_step(blend)

    def weather_transition_factor(self) -> float:
        return clamp(float(getattr(self, "weather_front_progress", 1.0)), 0.0, 1.0)

    def weather_signature(self, kind: str, strength: float) -> dict[str, float]:
        """Traduz um tipo de clima em fatores reutilizaveis por render, audio e gameplay."""
        strength = clamp(float(strength), 0.0, 1.0)
        signatures = {
            "clear": {"cloud": 0.08 + strength * 0.08, "rain": 0.0, "wind": 0.12 + strength * 0.18, "mist": 0.0, "storm": 0.0, "gloom": 0.0},
            "cloudy": {"cloud": 0.34 + strength * 0.42, "rain": 0.0, "wind": 0.16 + strength * 0.22, "mist": 0.06 + strength * 0.12, "storm": 0.0, "gloom": 0.12 + strength * 0.16},
            "wind": {"cloud": 0.18 + strength * 0.24, "rain": 0.0, "wind": 0.34 + strength * 0.46, "mist": 0.0, "storm": 0.0, "gloom": 0.06 + strength * 0.08},
            "rain": {"cloud": 0.46 + strength * 0.34, "rain": 0.36 + strength * 0.46, "wind": 0.18 + strength * 0.22, "mist": 0.08 + strength * 0.1, "storm": 0.0, "gloom": 0.18 + strength * 0.16},
            "mist": {"cloud": 0.18 + strength * 0.18, "rain": 0.0, "wind": 0.04 + strength * 0.08, "mist": 0.38 + strength * 0.42, "storm": 0.0, "gloom": 0.08 + strength * 0.12},
            "storm": {"cloud": 0.64 + strength * 0.28, "rain": 0.58 + strength * 0.34, "wind": 0.46 + strength * 0.34, "mist": 0.1 + strength * 0.1, "storm": 0.48 + strength * 0.42, "gloom": 0.28 + strength * 0.2},
        }
        base = signatures.get(kind, signatures["clear"])
        return {key: clamp(value, 0.0, 1.0) for key, value in base.items()}

    def blended_weather_signature(self) -> dict[str, float]:
        current_kind = getattr(self, "weather_kind", "clear")
        current_strength = float(getattr(self, "weather_strength", 0.0))
        target_kind = getattr(self, "weather_target_kind", current_kind)
        target_strength = float(getattr(self, "weather_target_strength", current_strength))
        blend = self.weather_transition_factor()
        current = self.weather_signature(current_kind, current_strength)
        target = self.weather_signature(target_kind, target_strength)
        return {key: lerp(current[key], target[key], blend) for key in current}

    def weather_cloud_cover(self) -> float:
        """Converte o clima atual em cobertura de nuvens para render, audio e gameplay."""
        return clamp(self.blended_weather_signature()["cloud"], 0.0, 0.94)

    def weather_precipitation_factor(self) -> float:
        return clamp(self.blended_weather_signature()["rain"], 0.0, 1.0)

    def weather_wind_factor(self) -> float:
        return clamp(self.blended_weather_signature()["wind"], 0.0, 1.0)

    def weather_mist_factor(self) -> float:
        return clamp(self.blended_weather_signature()["mist"], 0.0, 1.0)

    def weather_storm_factor(self) -> float:
        return clamp(self.blended_weather_signature()["storm"], 0.0, 1.0)

    def visual_darkness_factor(self) -> float:
        """Mistura noite e cobertura de nuvens em um unico fator de penumbra."""
        daylight = self.daylight_factor()
        signature = self.blended_weather_signature()
        cloud_cover = signature["cloud"]
        base_darkness = 1.0 - daylight
        cloud_darkness = cloud_cover * (0.42 * daylight + 0.14)
        weather_bias = signature["gloom"] + signature["storm"] * 0.08 + signature["mist"] * 0.04
        return clamp(base_darkness + cloud_darkness + weather_bias, 0.0, 1.0)

    def daylight_phase_label(self) -> str:
        """Resume a faixa do dia em um texto curto para a HUD."""
        time_value = self.time_minutes % (24 * 60)
        if DAWN_MINUTES - 65 <= time_value < DAWN_MINUTES + 70:
            return "amanhecer"
        if DUSK_MINUTES - 85 <= time_value < DUSK_MINUTES + 75:
            return "entardecer"
        if time_value < 4 * 60 or time_value >= 22 * 60:
            return "noite funda"
        if self.daylight_factor() < 0.18:
            return "noite"
        if time_value < 12 * 60 + 30:
            return "manha"
        return "tarde"

    def weather_mood_label(self) -> str:
        """Traduz a combinacao de clima e intensidade para uma leitura curta."""
        signature = self.blended_weather_signature()
        storm = signature["storm"]
        rain = signature["rain"]
        mist = signature["mist"]
        wind = signature["wind"]
        cloud = signature["cloud"]
        if storm > 0.32:
            return "tempestade armando" if storm < 0.62 else "tempestade pesada"
        if rain > 0.56:
            return "garoa fria" if rain < 0.72 else "chuva fechada"
        if mist > 0.46:
            return "bruma leve" if mist < 0.7 else "neblina grossa"
        if wind > 0.48:
            return "vento leve" if wind < 0.68 else "vento forte"
        if cloud > 0.34:
            return "nublado leve" if cloud < 0.62 else "nublado pesado"
        return "ceu aberto" if cloud < 0.14 else "claridade limpa"

    def random_world_pos(self, margin: float = 140) -> Vector2:
        return Vector2(
            self.random.uniform(margin, WORLD_WIDTH - margin),
            self.random.uniform(margin, WORLD_HEIGHT - margin),
        )

    def hash_noise(self, x: int, y: int, seed_offset: int = 0) -> float:
        value = math.sin((x * 127.1 + y * 311.7 + self.seed_value * 17 + seed_offset * 37) * 0.137)
        return (value + 1.0) * 0.5

    def chunk_key_for_pos(self, pos: Vector2) -> tuple[int, int]:
        return (math.floor(pos.x / CHUNK_SIZE), math.floor(pos.y / CHUNK_SIZE))

    def chunk_origin(self, chunk_x: int, chunk_y: int) -> Vector2:
        return Vector2(chunk_x * CHUNK_SIZE, chunk_y * CHUNK_SIZE)

    def region_chunk_span(self) -> int:
        return 3

    def region_key_for_chunk(self, chunk_x: int, chunk_y: int) -> tuple[int, int]:
        span = self.region_chunk_span()
        return (math.floor(chunk_x / span), math.floor(chunk_y / span))

    def region_key_for_pos(self, pos: Vector2) -> tuple[int, int]:
        return self.region_key_for_chunk(*self.chunk_key_for_pos(pos))

    def region_origin(self, region_x: int, region_y: int) -> Vector2:
        span = CHUNK_SIZE * self.region_chunk_span()
        return Vector2(region_x * span, region_y * span)

    def chunk_biome_kind(self, chunk_x: int, chunk_y: int) -> str:
        center = self.chunk_origin(chunk_x, chunk_y) + Vector2(CHUNK_SIZE * 0.5, CHUNK_SIZE * 0.5)
        if center.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 420:
            return "forest"
        heat = self.hash_noise(chunk_x, chunk_y, 3)
        moisture = self.hash_noise(chunk_x, chunk_y, 7)
        roughness = self.hash_noise(chunk_x, chunk_y, 11)
        if moisture > 0.72 and heat < 0.46:
            return "swamp"
        if moisture < 0.24 and roughness > 0.62:
            return "ashland"
        if roughness > 0.76 and moisture < 0.52:
            return "quarry"
        if moisture > 0.6 and heat > 0.52:
            return "redwood"
        if heat > 0.66 and moisture < 0.42:
            return "meadow"
        if roughness > 0.58:
            return "ruin"
        return "forest"

    def biome_palette(self, kind: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        palettes = {
            "forest": ((28, 48, 34), (55, 88, 58)),
            "meadow": ((78, 101, 62), (131, 154, 86)),
            "swamp": ((30, 57, 53), (70, 98, 84)),
            "ruin": ((82, 76, 66), (122, 112, 98)),
            "ashland": ((66, 58, 52), (110, 97, 88)),
            "redwood": ((48, 61, 42), (86, 112, 70)),
            "quarry": ((74, 82, 88), (122, 132, 138)),
        }
        return palettes.get(kind, palettes["forest"])

    def biome_label(self, kind: str) -> str:
        return {
            "forest": "Mata Profunda",
            "meadow": "Campos Altos",
            "swamp": "Brejo Antigo",
            "ruin": "Ruinas Perdidas",
            "ashland": "Cinzas Frias",
            "redwood": "Bosque Gigante",
            "quarry": "Pedreira Morta",
        }.get(kind, "Terras Distantes")

    def generate_region_name(self, biome: str, region_x: int, region_y: int) -> str:
        fragments = {
            "forest": (
                ("Vale", "Mata", "Passagem", "Ermo"),
                ("do Lenho Seco", "das Corujas Mortas", "do Lobo Oco", "das Agulhas Baixas"),
            ),
            "meadow": (
                ("Campo", "Coroa", "Terraco", "Planicie"),
                ("das Flores Tortas", "do Vento Claro", "do Capim Antigo", "da Bruma Rasa"),
            ),
            "swamp": (
                ("Brejo", "Baixio", "Lama", "Poente"),
                ("das Febres", "dos Juncos Negros", "da Agua Surda", "do Lodo Fundo"),
            ),
            "ruin": (
                ("Ruina", "Patio", "Passo", "Marco"),
                ("das Colunas Quebradas", "do Ferro Oco", "dos Sinos Mortos", "da Muralha Cega"),
            ),
            "ashland": (
                ("Cinza", "Braseiro", "Ermo", "Costela"),
                ("do Fumo Frio", "das Brasas Mortas", "da Fuligem Longa", "do Po Negro"),
            ),
            "redwood": (
                ("Bosque", "Catedral", "Corredor", "Trono"),
                ("das Sequoias Velhas", "do Tronco Alto", "das Copas Fundas", "da Casca Rubra"),
            ),
            "quarry": (
                ("Pedreira", "Corte", "Maciço", "Escarpa"),
                ("da Rocha Gasta", "dos Ecos Frios", "do Po de Ferro", "das Lajes Mortas"),
            ),
        }
        first_bank, second_bank = fragments.get(biome, fragments["forest"])
        first = first_bank[int(self.hash_noise(region_x, region_y, 91) * len(first_bank)) % len(first_bank)]
        second = second_bank[int(self.hash_noise(region_x, region_y, 97) * len(second_bank)) % len(second_bank)]
        return f"{first} {second}"

    def region_has_zone_boss(self, anchor: Vector2, region_x: int, region_y: int) -> bool:
        if anchor.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + CHUNK_SIZE * 4.4:
            return False
        return self.hash_noise(region_x, region_y, 149) > 0.7

    def zone_boss_blueprint(self, biome: str, region_name: str, region_key: tuple[int, int], anchor: Vector2) -> dict[str, object]:
        blueprints = {
            "forest": {
                "name": "Patriarca da Mata",
                "radius": 27,
                "speed": 82,
                "health": 280 + self.day * 24,
                "damage": 18 + self.day * 0.9,
                "body": (88, 121, 82),
                "accent": (45, 70, 41),
            },
            "meadow": {
                "name": "Arauto da Campina",
                "radius": 26,
                "speed": 92,
                "health": 260 + self.day * 22,
                "damage": 17 + self.day * 0.9,
                "body": (134, 128, 86),
                "accent": (84, 78, 44),
            },
            "swamp": {
                "name": "Matriarca do Brejo",
                "radius": 29,
                "speed": 78,
                "health": 300 + self.day * 26,
                "damage": 20 + self.day * 1.0,
                "body": (76, 117, 98),
                "accent": (36, 66, 58),
            },
            "ruin": {
                "name": "Sentinela da Ruina",
                "radius": 28,
                "speed": 80,
                "health": 310 + self.day * 25,
                "damage": 20 + self.day * 1.0,
                "body": (120, 112, 101),
                "accent": (69, 64, 58),
            },
            "ashland": {
                "name": "Rei das Cinzas",
                "radius": 30,
                "speed": 84,
                "health": 320 + self.day * 27,
                "damage": 21 + self.day * 1.1,
                "body": (132, 102, 78),
                "accent": (82, 52, 34),
            },
            "redwood": {
                "name": "Anciao das Sequoias",
                "radius": 31,
                "speed": 79,
                "health": 340 + self.day * 28,
                "damage": 22 + self.day * 1.1,
                "body": (96, 110, 72),
                "accent": (58, 48, 29),
            },
            "quarry": {
                "name": "Colosso da Pedreira",
                "radius": 33,
                "speed": 70,
                "health": 360 + self.day * 29,
                "damage": 24 + self.day * 1.2,
                "body": (124, 132, 138),
                "accent": (70, 78, 84),
            },
        }
        blueprint = dict(blueprints.get(biome, blueprints["forest"]))
        blueprint["zone_key"] = region_key
        blueprint["zone_label"] = region_name
        blueprint["anchor"] = Vector2(anchor)
        return blueprint

    def region_expedition_blueprint(self, biome: str, region_x: int, region_y: int) -> dict[str, object]:
        blueprints = {
            "forest": (
                ("resina seca", {"logs": 2, "wood": 2, "medicine": 1}),
                ("caixa de trilha", {"food": 2, "scrap": 2}),
            ),
            "meadow": (
                ("fardo de sementes", {"food": 3, "herbs": 1}),
                ("kit de pastor", {"food": 2, "meals": 1, "wood": 1}),
            ),
            "swamp": (
                ("bolsa de lodo curativo", {"herbs": 3, "medicine": 1}),
                ("caixote encharcado", {"scrap": 2, "food": 1, "herbs": 1}),
            ),
            "ruin": (
                ("gaveta tecnica", {"scrap": 4, "medicine": 1}),
                ("armario tombado", {"scrap": 3, "wood": 1}),
            ),
            "ashland": (
                ("saco de carvao duro", {"logs": 2, "wood": 2, "scrap": 1}),
                ("estojo chamuscado", {"scrap": 2, "medicine": 1, "wood": 1}),
            ),
            "redwood": (
                ("troncos antigos", {"logs": 4, "wood": 2}),
                ("caixa de seiva rubra", {"logs": 3, "medicine": 1}),
            ),
            "quarry": (
                ("lote de ferragens", {"scrap": 5, "wood": 1}),
                ("bau de minerio", {"scrap": 4, "medicine": 1}),
            ),
        }
        pool = blueprints.get(biome, blueprints["forest"])
        index = int(self.hash_noise(region_x, region_y, 181) * len(pool)) % len(pool)
        label, bundle = pool[index]
        danger = {
            "forest": 0.28,
            "meadow": 0.24,
            "swamp": 0.52,
            "ruin": 0.46,
            "ashland": 0.5,
            "redwood": 0.42,
            "quarry": 0.48,
        }.get(biome, 0.36)
        danger += self.hash_noise(region_x, region_y, 187) * 0.14
        sites = 1 + int(self.hash_noise(region_x, region_y, 191) > 0.66)
        return {
            "label": label,
            "bundle": dict(bundle),
            "danger": clamp(danger, 0.18, 0.82),
            "sites": sites,
        }

    def ensure_named_region(self, region_x: int, region_y: int) -> dict[str, object]:
        region_key = (region_x, region_y)
        if region_key in self.named_regions:
            return self.named_regions[region_key]

        span = CHUNK_SIZE * self.region_chunk_span()
        origin = self.region_origin(region_x, region_y)
        biome = self.chunk_biome_kind(region_x * self.region_chunk_span() + 1, region_y * self.region_chunk_span() + 1)
        anchor = origin + Vector2(span * 0.5, span * 0.5)
        anchor += Vector2(
            (self.hash_noise(region_x, region_y, 101) - 0.5) * span * 0.36,
            (self.hash_noise(region_x, region_y, 103) - 0.5) * span * 0.36,
        )
        name = self.generate_region_name(biome, region_x, region_y)
        boss_blueprint = (
            self.zone_boss_blueprint(biome, name, region_key, anchor)
            if self.region_has_zone_boss(anchor, region_x, region_y)
            else None
        )
        expedition = self.region_expedition_blueprint(biome, region_x, region_y)
        region = {
            "key": region_key,
            "name": name,
            "biome": biome,
            "anchor": anchor,
            "boss_blueprint": boss_blueprint,
            "boss_defeated": False,
            "boss_spawned": False,
            "boss_active": False,
            "expedition_label": expedition["label"],
            "expedition_bundle": expedition["bundle"],
            "expedition_danger": expedition["danger"],
            "expedition_sites": expedition["sites"],
            "expedition_last_outcome": "",
        }
        self.named_regions[region_key] = region
        return region

    def camp_clearance_radius(self) -> float:
        return max(CAMP_RADIUS, self.camp_half_size * 1.46)

    def ensure_endless_world(self, center: Vector2, radius: int = 3) -> None:
        base_x, base_y = self.chunk_key_for_pos(center)
        for chunk_x in range(base_x - radius, base_x + radius + 1):
            for chunk_y in range(base_y - radius, base_y + radius + 1):
                key = (chunk_x, chunk_y)
                if key not in self.generated_chunks:
                    self.generate_chunk(chunk_x, chunk_y)

    def generate_chunk(self, chunk_x: int, chunk_y: int) -> None:
        biome = self.chunk_biome_kind(chunk_x, chunk_y)
        region_key = self.region_key_for_chunk(chunk_x, chunk_y)
        region = self.ensure_named_region(*region_key)
        self.generated_chunks[(chunk_x, chunk_y)] = {
            "biome": biome,
            "region_key": region_key,
            "region_name": region["name"],
        }
        if biome == "forest" and self.chunk_origin(chunk_x, chunk_y).distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 380:
            return

        origin = self.chunk_origin(chunk_x, chunk_y)
        center = origin + Vector2(CHUNK_SIZE * 0.5, CHUNK_SIZE * 0.5)
        feature_radius = 120 + self.hash_noise(chunk_x, chunk_y, 19) * 80
        self.endless_features.append(WorldFeature(biome, center, feature_radius, self.hash_noise(chunk_x, chunk_y, 23)))

        tree_plan = {
            "forest": (7, 13),
            "redwood": (9, 16),
            "swamp": (4, 8),
            "meadow": (1, 3),
            "ashland": (0, 2),
            "quarry": (0, 1),
            "ruin": (1, 4),
        }
        tree_count = int(self.hash_noise(chunk_x, chunk_y, 29) * (tree_plan[biome][1] - tree_plan[biome][0]) + tree_plan[biome][0])
        for index in range(tree_count):
            px = origin.x + 36 + self.hash_noise(chunk_x * 17 + index, chunk_y * 13, 31) * (CHUNK_SIZE - 72)
            py = origin.y + 36 + self.hash_noise(chunk_x * 19, chunk_y * 11 + index, 37) * (CHUNK_SIZE - 72)
            pos = Vector2(px, py)
            if pos.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 110:
                continue
            radius = 22 + int(self.hash_noise(chunk_x * 7 + index, chunk_y * 5 + index, 41) * 26)
            if biome == "redwood":
                radius += 8
            elif biome == "ashland":
                radius = max(16, radius - 6)
            elif biome == "meadow":
                radius = max(18, radius - 8)
            tone = self.hash_noise(chunk_x * 3 + index, chunk_y * 7 + index, 43)
            self.trees.append(
                {
                    "pos": pos,
                    "radius": int(clamp(radius, 18, 56)),
                    "height": 0.84 + self.hash_noise(chunk_x * 5 + index, chunk_y * 9 + index, 47) * 0.6,
                    "tone": tone,
                    "lean": self.hash_noise(chunk_x * 13 + index, chunk_y * 3 + index, 53) * 0.44 - 0.22,
                    "spread": 0.82 + self.hash_noise(chunk_x * 2 + index, chunk_y * 17 + index, 59) * 0.46,
                    "branch_bias": self.hash_noise(chunk_x * 11 + index, chunk_y * 4 + index, 61) * 0.7 - 0.35,
                    "wood_yield": max(2, int(radius * (0.14 if biome == "redwood" else 0.11))),
                    "effort_required": 2 + int(radius >= 30) + int(radius >= 42),
                    "effort_progress": 0,
                    "harvested": False,
                    "biome": biome,
                }
            )

        resource_plan = {
            "forest": (("food", "berries"), ("food", "mushrooms"), ("scrap", "cache")),
            "redwood": (("food", "mushrooms"), ("scrap", "crate"), ("scrap", "relic")),
            "swamp": (("food", "herbs"), ("food", "reeds"), ("scrap", "bogmetal")),
            "meadow": (("food", "berries"), ("food", "flowers"), ("scrap", "cart")),
            "ashland": (("scrap", "charcoal"), ("scrap", "relic"), ("food", "roots")),
            "quarry": (("scrap", "ore"), ("scrap", "stonecache"), ("food", "roots")),
            "ruin": (("scrap", "crate"), ("scrap", "relic"), ("food", "herbs")),
        }
        node_count = 1 + int(self.hash_noise(chunk_x, chunk_y, 67) * 2)
        if self.hash_noise(chunk_x, chunk_y, 69) < 0.24:
            node_count = 0
        for index in range(node_count):
            variant_kind, variant_name = resource_plan[biome][index % len(resource_plan[biome])]
            pos = Vector2(
                origin.x + 44 + self.hash_noise(chunk_x * 23 + index, chunk_y * 5, 71) * (CHUNK_SIZE - 88),
                origin.y + 44 + self.hash_noise(chunk_x * 7, chunk_y * 29 + index, 73) * (CHUNK_SIZE - 88),
            )
            if pos.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 140:
                continue
            radius = 20 if variant_kind == "food" else 24
            self.resource_nodes.append(
                ResourceNode(
                    variant_kind,
                    pos,
                    amount=1,
                    radius=radius,
                    variant=variant_name,
                    renewable=False,
                )
            )

    def camp_rect(self, padding: float = 0.0) -> pygame.Rect:
        half = self.camp_half_size + padding
        return pygame.Rect(
            int(CAMP_CENTER.x - half),
            int(CAMP_CENTER.y - half),
            int(half * 2),
            int(half * 2),
        )

    def camp_visual_ellipses(self, padding: float = 0.0) -> list[pygame.Rect]:
        """Retorna manchas elipticas para desenhar a clareira de forma mais organica."""
        half = self.camp_half_size + padding
        specs = (
            (-0.04, -0.01, 2.08, 1.72),
            (0.03, 0.10, 1.76, 1.34),
            (-0.26, 0.20, 0.96, 0.68),
            (0.30, -0.15, 0.88, 0.62),
            (0.22, 0.27, 0.76, 0.54),
            (-0.33, -0.18, 0.78, 0.56),
        )
        ellipses: list[pygame.Rect] = []
        for offset_x, offset_y, width_scale, height_scale in specs:
            width = half * width_scale
            height = half * height_scale
            center = CAMP_CENTER + Vector2(half * offset_x, half * offset_y)
            rect = pygame.Rect(0, 0, int(width), int(height))
            rect.center = (int(center.x), int(center.y))
            ellipses.append(rect)
        return ellipses

    def camp_visual_bounds(self, padding: float = 0.0) -> pygame.Rect:
        ellipses = self.camp_visual_ellipses(padding)
        if not ellipses:
            return self.camp_rect(padding)
        bounds = ellipses[0].copy()
        for rect in ellipses[1:]:
            bounds.union_ip(rect)
        return bounds

    def camp_ground_anchors(self) -> list[Vector2]:
        """Pontos importantes usados para desenhar desgaste e trilhas internas da clareira."""
        anchors = [
            Vector2(CAMP_CENTER),
            Vector2(self.stockpile_pos),
            Vector2(self.workshop_pos),
            Vector2(self.kitchen_pos),
            Vector2(self.radio_pos),
        ]
        anchors.extend(Vector2(tent["pos"]) for tent in self.tents)
        return anchors

    def paint_camp_ground(self, surface: pygame.Surface) -> None:
        """Desenha uma clareira mais organica, com terra batida e desgaste de uso."""
        camp_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        earth_dark = (88, 63, 42)
        earth_mid = (118, 85, 56)
        earth_light = (154, 114, 74)
        earth_dust = (176, 136, 92)
        clearing_layers = (
            (self.camp_visual_ellipses(102), (*PALETTE["clearing"], 56)),
            (self.camp_visual_ellipses(42), (*earth_mid, 44)),
            (self.camp_visual_ellipses(-6), (*earth_light, 34)),
        )
        for ellipses, color in clearing_layers:
            for ellipse in ellipses:
                pygame.draw.ellipse(camp_surface, color, ellipse)

        packed_earth = (
            (pygame.Rect(int(CAMP_CENTER.x - self.camp_half_size * 0.98), int(CAMP_CENTER.y - self.camp_half_size * 0.62), int(self.camp_half_size * 1.96), int(self.camp_half_size * 1.24)), (*earth_dark, 54)),
            (pygame.Rect(int(CAMP_CENTER.x - self.camp_half_size * 0.86), int(CAMP_CENTER.y - self.camp_half_size * 0.54), int(self.camp_half_size * 1.72), int(self.camp_half_size * 1.08)), (*earth_mid, 72)),
            (pygame.Rect(int(CAMP_CENTER.x - self.camp_half_size * 0.62), int(CAMP_CENTER.y - self.camp_half_size * 0.38), int(self.camp_half_size * 1.24), int(self.camp_half_size * 0.76)), (*earth_light, 54)),
            (pygame.Rect(int(self.stockpile_pos.x - 104), int(self.stockpile_pos.y - 58), 208, 116), (*earth_mid, 58)),
            (pygame.Rect(int(self.workshop_pos.x - 94), int(self.workshop_pos.y - 52), 188, 104), (*earth_mid, 54)),
            (pygame.Rect(int(self.kitchen_pos.x - 88), int(self.kitchen_pos.y - 48), 176, 96), (*earth_mid, 50)),
            (pygame.Rect(int(self.radio_pos.x - 72), int(self.radio_pos.y - 42), 144, 84), (*earth_light, 38)),
        )
        for rect, color in packed_earth:
            pygame.draw.ellipse(camp_surface, color, rect)

        anchor_paths = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        center = Vector2(CAMP_CENTER)
        for anchor in self.camp_ground_anchors():
            if anchor.distance_to(center) < 8:
                continue
            sway = Vector2((anchor.y - center.y) * 0.04, (center.x - anchor.x) * 0.04)
            points = [center, center.lerp(anchor, 0.45) + sway, anchor]
            pygame.draw.lines(anchor_paths, (*earth_dark, 82), False, points, 44)
            pygame.draw.lines(anchor_paths, (*earth_mid, 76), False, points, 26)
            pygame.draw.lines(anchor_paths, (*earth_light, 42), False, points, 10)
        camp_surface.blit(anchor_paths, (0, 0))

        worn_patches = (
            pygame.Rect(int(CAMP_CENTER.x - self.camp_half_size * 0.78), int(CAMP_CENTER.y - 26), int(self.camp_half_size * 1.56), 74),
            pygame.Rect(int(CAMP_CENTER.x - 62), int(CAMP_CENTER.y - self.camp_half_size * 0.62), 124, int(self.camp_half_size * 1.18)),
            pygame.Rect(int(self.workshop_pos.x - 74), int(self.workshop_pos.y - 42), 148, 84),
            pygame.Rect(int(self.kitchen_pos.x - 72), int(self.kitchen_pos.y - 40), 144, 80),
            pygame.Rect(int(self.radio_pos.x - 58), int(self.radio_pos.y - 34), 116, 68),
            pygame.Rect(int(CAMP_CENTER.x - 88), int(CAMP_CENTER.y - 70), 176, 140),
        )
        patch_colors = (
            (102, 74, 50, 42),
            (126, 91, 60, 34),
            (158, 116, 78, 26),
        )
        for index, patch in enumerate(worn_patches):
            pygame.draw.ellipse(camp_surface, patch_colors[index % len(patch_colors)], patch)

        for _ in range(320):
            offset = Vector2(
                self.random.uniform(-self.camp_half_size * 0.94, self.camp_half_size * 0.94),
                self.random.uniform(-self.camp_half_size * 0.82, self.camp_half_size * 0.82),
            )
            pos = CAMP_CENTER + offset
            if not self.point_in_camp_square(pos, -12):
                continue
            width = self.random.randint(6, 16)
            height = self.random.randint(3, 9)
            dust = pygame.Rect(0, 0, width, height)
            dust.center = (int(pos.x), int(pos.y))
            dust_color = (*earth_dust, self.random.randint(20, 42))
            pygame.draw.ellipse(camp_surface, dust_color, dust)

        edge_tufts = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        for ellipse in self.camp_visual_ellipses(84):
            for _ in range(18):
                angle = self.random.random() * math.tau
                rim = Vector2(ellipse.width * 0.5 * math.cos(angle), ellipse.height * 0.5 * math.sin(angle))
                pos = Vector2(ellipse.center) + rim * self.random.uniform(0.82, 1.03)
                tuft = pygame.Rect(0, 0, self.random.randint(18, 34), self.random.randint(8, 16))
                tuft.center = (int(pos.x), int(pos.y))
                color = (54, 84, 47, self.random.randint(26, 40))
                pygame.draw.ellipse(edge_tufts, color, tuft)
        camp_surface.blit(edge_tufts, (0, 0))

        ember_ring = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        for radius, alpha in ((132, 10), (94, 16), (62, 22)):
            rect = pygame.Rect(0, 0, radius * 2, int(radius * 1.45))
            rect.center = (int(self.bonfire_pos.x), int(self.bonfire_pos.y + 10))
            pygame.draw.ellipse(ember_ring, (184, 136, 82, alpha), rect)
        camp_surface.blit(ember_ring, (0, 0))

        for _ in range(120):
            offset = Vector2(
                self.random.uniform(-self.camp_half_size * 0.92, self.camp_half_size * 0.92),
                self.random.uniform(-self.camp_half_size * 0.92, self.camp_half_size * 0.92),
            )
            pos = CAMP_CENTER + offset
            if not self.point_in_camp_square(pos, 10):
                continue
            stone = pygame.Rect(0, 0, self.random.randint(4, 10), self.random.randint(2, 5))
            stone.center = (int(pos.x), int(pos.y))
            pygame.draw.ellipse(camp_surface, (96, 98, 82, self.random.randint(18, 34)), stone)

        surface.blit(camp_surface, (0, 0))

    def point_in_camp_square(self, pos: Vector2, padding: float = 0.0) -> bool:
        rect = self.camp_rect(padding)
        return rect.left <= pos.x <= rect.right and rect.top <= pos.y <= rect.bottom

    def camp_loop_points(self, inset: float = 0.0, *, segments_per_side: int = 4, jitter: float = 0.0) -> list[Vector2]:
        half = self.camp_half_size - inset
        corners = [
            Vector2(CAMP_CENTER.x - half, CAMP_CENTER.y - half),
            Vector2(CAMP_CENTER.x + half, CAMP_CENTER.y - half),
            Vector2(CAMP_CENTER.x + half, CAMP_CENTER.y + half),
            Vector2(CAMP_CENTER.x - half, CAMP_CENTER.y + half),
        ]
        points: list[Vector2] = []
        for index in range(4):
            start = corners[index]
            end = corners[(index + 1) % 4]
            for step in range(segments_per_side):
                t = step / segments_per_side
                point = start.lerp(end, t)
                if jitter:
                    point += Vector2(
                        self.random.uniform(-jitter, jitter),
                        self.random.uniform(-jitter, jitter),
                    )
                points.append(point)
        points.append(Vector2(points[0]))
        return points

    def camp_perimeter_point(self, seed_index: int = 0, *, jitter: float = 0.0) -> Vector2:
        points = self.camp_loop_points(26, segments_per_side=3)
        point = Vector2(points[seed_index % max(1, len(points) - 1)])
        if jitter:
            point += Vector2(
                self.random.uniform(-jitter, jitter),
                self.random.uniform(-jitter, jitter),
            )
        return point

    def guard_posts(self) -> list[Vector2]:
        half = self.camp_half_size - 26
        return [
            CAMP_CENTER + Vector2(-half * 0.62, -half),
            CAMP_CENTER + Vector2(half * 0.62, -half),
            CAMP_CENTER + Vector2(half, -half * 0.22),
            CAMP_CENTER + Vector2(half, half * 0.22),
            CAMP_CENTER + Vector2(half * 0.62, half),
            CAMP_CENTER + Vector2(-half * 0.62, half),
            CAMP_CENTER + Vector2(-half, half * 0.22),
            CAMP_CENTER + Vector2(-half, -half * 0.22),
        ]

    def layout_camp_core(self) -> None:
        self.camp_half_size = 214 + self.camp_level * 88
        self.stockpile_pos = CAMP_CENTER + Vector2(-self.camp_half_size * 0.1, self.camp_half_size * 0.48)
        self.bonfire_pos = Vector2(CAMP_CENTER)
        self.kitchen_pos = CAMP_CENTER + Vector2(self.camp_half_size * 0.46, self.camp_half_size * 0.16)
        self.workshop_pos = CAMP_CENTER + Vector2(-self.camp_half_size * 0.54, self.camp_half_size * 0.08)
        self.radio_pos = CAMP_CENTER + Vector2(-self.camp_half_size * 0.04, -self.camp_half_size * 0.52)

    def create_recruit_pool(self) -> list[dict[str, object]]:
        return [
            {"name": "Ayla", "role": "batedora", "traits": ("sociavel", "corajoso")},
            {"name": "Ravi", "role": "lenhador", "traits": ("teimoso", "resiliente")},
            {"name": "Noa", "role": "vigia", "traits": ("corajoso", "paranoico")},
            {"name": "Breno", "role": "artesa", "traits": ("gentil", "leal")},
            {"name": "Tainah", "role": "cozinheiro", "traits": ("sociavel", "gentil")},
            {"name": "Cael", "role": "mensageiro", "traits": ("paranoico", "resiliente")},
            {"name": "Liora", "role": "batedora", "traits": ("leal", "sociavel")},
            {"name": "Davi", "role": "lenhador", "traits": ("teimoso", "rancoroso")},
            {"name": "Mina", "role": "vigia", "traits": ("corajoso", "leal")},
            {"name": "Icaro", "role": "artesa", "traits": ("gentil", "resiliente")},
            {"name": "Sara", "role": "cozinheiro", "traits": ("gentil", "paranoico")},
            {"name": "Joel", "role": "mensageiro", "traits": ("rancoroso", "resiliente")},
        ]

    def create_build_recipes(self) -> list[dict[str, object]]:
        return [
            {"kind": "barraca", "label": "Barraca", "wood": 5, "scrap": 1, "size": 34, "hint": "+2 camas"},
            {"kind": "torre", "label": "Torre", "wood": 8, "scrap": 4, "size": 28, "hint": "vigia especializado"},
            {"kind": "horta", "label": "Horta", "wood": 3, "scrap": 1, "size": 30, "hint": "mais comida"},
            {"kind": "anexo", "label": "Anexo", "wood": 7, "scrap": 5, "size": 32, "hint": "reforca barricadas"},
            {"kind": "serraria", "label": "Serraria", "wood": 7, "scrap": 2, "size": 34, "hint": "toras viram tabuas"},
            {"kind": "cozinha", "label": "Cozinha", "wood": 6, "scrap": 2, "size": 34, "hint": "refeicoes em lote"},
            {"kind": "enfermaria", "label": "Enfermaria", "wood": 6, "scrap": 4, "size": 34, "hint": "cura e remedios"},
        ]

    def create_faction_standings(self) -> dict[str, float]:
        return {
            "andarilhos": 12.0,
            "ferro-velho": 0.0,
            "vigias_da_estrada": -6.0,
        }

    def faction_label(self, key: str) -> str:
        return {
            "andarilhos": "Andarilhos",
            "ferro-velho": "Ferro-Velho",
            "vigias_da_estrada": "Vigias da Estrada",
        }.get(key, key)

    def adjust_faction_standing(self, key: str, delta: float) -> float:
        current = float(self.faction_standings.get(key, 0.0))
        current = clamp(current + delta, -100, 100)
        self.faction_standings[key] = current
        return current

    def faction_standing_label(self, key: str) -> str:
        score = float(self.faction_standings.get(key, 0.0))
        if score >= 55:
            return "aliados"
        if score >= 20:
            return "proximos"
        if score >= -10:
            return "neutros"
        if score >= -40:
            return "hostis"
        return "jurados"

    def strongest_faction(self) -> tuple[str, float]:
        return max(self.faction_standings.items(), key=lambda item: item[1])

    def build_recipe_for(self, kind: str) -> dict[str, object]:
        for recipe in self.build_recipes:
            if recipe["kind"] == kind:
                return recipe
        raise KeyError(kind)

    def economy_phase_score(self) -> int:
        infrastructure = sum(
            self.building_count(kind)
            for kind in ("serraria", "cozinha", "enfermaria", "horta", "anexo", "torre")
        )
        return max(0, self.day - 1) + self.camp_level * 2 + min(6, infrastructure)

    def economy_phase_key(self) -> str:
        score = self.economy_phase_score()
        if score >= 9:
            return "late"
        if score >= 4:
            return "mid"
        return "early"

    def economy_phase_label(self) -> str:
        return {
            "early": "escassez",
            "mid": "estabilizacao",
            "late": "expedicoes",
        }[self.economy_phase_key()]

    def build_cost_for(self, recipe_or_kind: dict[str, object] | str) -> tuple[int, int]:
        recipe = self.build_recipe_for(recipe_or_kind) if isinstance(recipe_or_kind, str) else recipe_or_kind
        phase = self.economy_phase_key()
        multiplier = {
            "early": 1.0,
            "mid": 1.06,
            "late": 1.14,
        }[phase]
        wood_cost = max(1, math.ceil(int(recipe["wood"]) * multiplier))
        scrap_cost = max(0, math.ceil(int(recipe["scrap"]) * multiplier))
        return wood_cost, scrap_cost

    def sawmill_output(self, role: str) -> int:
        base = 5 if role == "lenhador" else 4
        phase_bonus = {
            "early": -1,
            "mid": 0,
            "late": 1,
        }[self.economy_phase_key()]
        return max(3, base + phase_bonus)

    def cookhouse_output(self, role: str) -> int:
        base = 4 if role == "cozinheiro" else 3
        phase_bonus = {
            "early": 0,
            "mid": 0,
            "late": 1,
        }[self.economy_phase_key()]
        return max(2, base + phase_bonus)

    def garden_harvest_bundle(self, role: str) -> dict[str, int]:
        phase = self.economy_phase_key()
        if phase == "early":
            bundle = {"food": 1}
        elif phase == "mid":
            bundle = {"food": 1}
            if self.random.random() < 0.35:
                bundle["herbs"] = 1
        else:
            bundle = {"food": 2}
            if self.random.random() < (0.6 if role == "cozinheiro" else 0.4):
                bundle["herbs"] = 1
        if role == "cozinheiro" and phase != "early" and self.random.random() < 0.25:
            bundle["food"] = bundle.get("food", 0) + 1
        return bundle

    def garden_regrow_duration(self) -> float:
        return {
            "early": 38.0,
            "mid": 31.0,
            "late": 25.0,
        }[self.economy_phase_key()]

    def garden_is_ready(self, building: Building | None) -> bool:
        return bool(building and building.kind == "horta" and building.work_phase <= 0.0)

    def start_garden_regrow(self, building: Building) -> None:
        if building.kind == "horta":
            building.work_phase = self.garden_regrow_duration()

    def update_buildings(self, dt: float) -> None:
        for building in self.buildings:
            if building.kind != "horta" or building.work_phase <= 0.0:
                continue
            if self.is_night:
                continue
            building.work_phase = max(0.0, building.work_phase - dt)

    def clinic_medicine_output(self) -> int:
        return 2 if self.economy_phase_key() == "late" else 1

    def daily_ration_demand(self) -> int:
        population = 1 + len(self.living_survivors())
        phase = self.economy_phase_key()
        factor = {
            "early": 0.42,
            "mid": 0.72,
            "late": 0.96,
        }[phase]
        floor = {
            "early": 2,
            "mid": 3,
            "late": 4,
        }[phase]
        return max(floor, math.ceil(population * factor))

    def apply_daily_rations(self) -> tuple[int, int, int]:
        demand = self.daily_ration_demand()
        used_meals = 0
        used_food = 0
        while demand >= 2 and self.meals > 0:
            self.meals -= 1
            used_meals += 1
            demand -= 2
        while demand > 0 and self.food > 0:
            self.food -= 1
            used_food += 1
            demand -= 1

        deficit = max(0, demand)
        if deficit > 0:
            for survivor in self.living_survivors():
                survivor.morale = clamp(survivor.morale - deficit * 3.8, 0, 100)
                survivor.energy = clamp(survivor.energy - deficit * 2.5, 0, 100)
                self.adjust_trust(survivor, -deficit * 1.0)
        return used_meals, used_food, deficit

    def building_count(self, kind: str) -> int:
        return sum(1 for building in self.buildings if building.kind == kind)

    def requested_building_count(self, kind: str) -> int:
        return sum(1 for request in self.build_requests if request.kind == kind)

    def build_specialty_role(self, kind: str) -> str | None:
        return {
            "torre": "vigia",
            "horta": "cozinheiro",
            "anexo": "artesa",
            "serraria": "lenhador",
            "cozinha": "cozinheiro",
            "enfermaria": "mensageiro",
        }.get(kind)

    def build_request_by_uid(self, uid: int | None) -> BuildingRequest | None:
        if uid is None:
            return None
        for request in self.build_requests:
            if request.uid == uid:
                return request
        return None

    def active_build_requests(self) -> list[BuildingRequest]:
        return list(self.build_requests)

    def prune_build_requests(self) -> None:
        """Limpa pedidos que perderam o morador responsavel ou o espaco reservado."""
        valid_names = {survivor.name for survivor in self.survivors if survivor.is_alive()}
        kept: list[BuildingRequest] = []
        for request in self.build_requests:
            if request.requester_name not in valid_names:
                continue
            kept.append(request)
        self.build_requests = kept

    def pending_build_request_for_survivor(self, survivor: Survivor) -> BuildingRequest | None:
        for request in self.build_requests:
            if request.requester_name == survivor.name:
                return request
        return None

    def requested_building_total(self, kind: str) -> int:
        return self.building_count(kind) + self.requested_building_count(kind)

    def desired_survivor_build_kind(self, survivor: Survivor) -> str | None:
        """Escolhe a obra que o morador quer ver no acampamento antes de pedir ao chefe."""
        if self.pending_build_request_for_survivor(survivor):
            return None
        if self.active_dynamic_events or self.player_sleeping or self.is_night:
            return None
        if survivor.energy < 34 or survivor.health < 46 or survivor.exhaustion > 62:
            return None

        if self.spare_beds() <= 0 and self.requested_building_total("barraca") < max(1, 1 + self.camp_level):
            return "barraca"
        if survivor.role == "lenhador" and self.requested_building_total("serraria") < 1:
            return "serraria"
        if survivor.role == "cozinheiro" and self.requested_building_total("cozinha") < 1:
            return "cozinha"
        if survivor.role == "mensageiro" and self.requested_building_total("enfermaria") < 1:
            return "enfermaria"
        if survivor.role == "cozinheiro" and self.food < 10 and self.requested_building_total("horta") < max(1, self.camp_level):
            return "horta"
        if survivor.role == "artesa" and self.weakest_barricade_health() < 86 and self.requested_building_total("anexo") < max(1, self.camp_level):
            return "anexo"
        desired_towers = 1 + (1 if self.camp_level >= 2 else 0) + (1 if len(self.survivors) >= 8 else 0)
        if survivor.role == "vigia" and self.requested_building_total("torre") < desired_towers:
            return "torre"
        if self.economy_phase_key() != "early" and self.food < 8 and self.requested_building_total("horta") < max(1, self.camp_level):
            return "horta"
        return None

    def find_build_request_site(self, kind: str, survivor: Survivor | None = None) -> Vector2 | None:
        """Reserva um ponto valido dentro da base para a futura obra do morador."""
        rect = self.camp_rect(-48)
        origin = Vector2(survivor.pos) if survivor is not None else Vector2(CAMP_CENTER)
        candidates: list[tuple[float, Vector2]] = []
        for grid_y in range(int(rect.top), int(rect.bottom) + 1, 32):
            for grid_x in range(int(rect.left), int(rect.right) + 1, 32):
                candidate = self.building_center_snapped(Vector2(grid_x, grid_y))
                if not self.is_valid_build_position(kind, candidate):
                    continue
                score = candidate.distance_to(origin)
                score += candidate.distance_to(self.workshop_pos) * 0.18
                if kind == "torre":
                    score -= candidate.distance_to(CAMP_CENTER) * 0.32
                elif kind == "horta":
                    score += candidate.distance_to(self.kitchen_pos) * 0.08
                elif kind == "serraria":
                    score += candidate.distance_to(self.stockpile_pos) * 0.04
                elif kind == "enfermaria":
                    score += candidate.distance_to(self.kitchen_pos) * 0.06
                candidates.append((score, candidate))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return Vector2(candidates[0][1])

    def propose_survivor_build_request(self, survivor: Survivor) -> BuildingRequest | None:
        """Transforma a necessidade do morador em sugestao de chat, sem reservar obra no chao."""
        kind = self.desired_survivor_build_kind(survivor)
        if not kind:
            return None
        recipe = self.build_recipe_for(kind)
        survivor.build_request_cooldown = self.random.uniform(64.0, 92.0)
        wood_cost, scrap_cost = self.build_cost_for(kind)
        bark_text, reason = self.contextual_build_request_reason(survivor, kind)
        self.trigger_survivor_bark(survivor, bark_text, PALETTE["accent_soft"], duration=3.0)
        self.add_chat_message(
            survivor.name,
            f"acha que a base precisa de {str(recipe['label']).lower()} porque {reason}. Custo: {wood_cost} tabuas e {scrap_cost} sucata.",
            PALETTE["accent_soft"],
            source="npc",
        )
        self.set_event_message(f"{survivor.name} sugeriu {str(recipe['label']).lower()} no chat do acampamento.", duration=5.2)
        return None

    def approve_build_request(self, request: BuildingRequest) -> tuple[bool, str]:
        """Confirma o pedido do morador e libera os recursos da obra."""
        if request not in self.build_requests:
            return False, "Esse pedido nao existe mais."
        if request.approved:
            return False, "Essa obra ja foi aprovada."
        self.build_requests.remove(request)
        if not self.is_valid_build_position(request.kind, request.pos):
            return False, "O ponto reservado foi perdido. O morador precisa planejar de novo."
        self.build_requests.append(request)
        wood_cost, scrap_cost = self.build_cost_for(request.kind)
        if self.wood < wood_cost or self.scrap < scrap_cost:
            return False, f"Faltam {wood_cost} tabuas e {scrap_cost} sucata para liberar essa obra."
        self.wood -= wood_cost
        self.scrap -= scrap_cost
        request.approved = True
        request.assigned_to = request.requester_name
        requester = next((survivor for survivor in self.survivors if survivor.name == request.requester_name and survivor.is_alive()), None)
        if requester:
            requester.decision_timer = 0.0
            requester.morale = clamp(requester.morale + 4.0, 0, 100)
            self.adjust_trust(requester, 2.4)
            self.trigger_survivor_bark(requester, "Boa. Eu mesmo levanto isso.", PALETTE["heal"], duration=2.8)
        self.add_chat_message("radio", f"Obra aprovada: {request.label.lower()} vai sair do papel.", PALETTE["heal"], source="system")
        self.set_event_message(f"Voce aprovou {request.label.lower()}. Agora a equipe vai levantar a estrutura.", duration=5.2)
        return True, f"{request.label} aprovada."

    def complete_build_request(self, request: BuildingRequest) -> Building | None:
        """Transforma a obra aprovada em um predio pronto quando o trabalho acaba."""
        if request not in self.build_requests:
            return None
        self.build_requests.remove(request)
        if not self.is_valid_build_position(request.kind, request.pos):
            self.set_event_message(f"A obra de {request.label.lower()} perdeu espaco e foi cancelada.", duration=4.8)
            return None
        building = Building(
            uid=self.next_building_uid,
            kind=request.kind,
            pos=Vector2(request.pos),
            size=request.size,
        )
        self.next_building_uid += 1
        self.buildings.append(building)
        self.refresh_barricade_strength()
        self.assign_building_specialists()
        self.spawn_floating_text(request.label.lower(), request.pos, PALETTE["accent_soft"])
        self.emit_embers(request.pos, 6, smoky=True)
        self.set_event_message(f"{request.label} pronta na clareira.", duration=4.8)
        return building

    def camp_sleep_slots(self) -> list[dict[str, object]]:
        slots: list[dict[str, object]] = []
        for index, tent in enumerate(self.tents):
            base_pos = Vector2(tent["pos"])
            angle = float(tent["angle"])
            scale = float(tent["scale"])
            facing = angle_to_vector(angle)
            slots.append(
                {
                    "kind": "tent",
                    "index": index,
                    "building_uid": None,
                    "pos": base_pos,
                    "sleep_pos": base_pos - facing * (6 * scale),
                    "interact_pos": base_pos + facing * (24 * scale),
                    "radius": 20 + 8 * scale,
                    "label": "barraca",
                }
            )
        for building in self.buildings:
            if building.kind != "barraca":
                continue
            for bed_index, x_offset in enumerate((-12, 12)):
                slots.append(
                    {
                        "kind": "barraca",
                        "index": bed_index,
                        "building_uid": building.uid,
                        "pos": Vector2(building.pos),
                        "sleep_pos": Vector2(building.pos) + Vector2(x_offset, 4),
                        "interact_pos": Vector2(building.pos) + Vector2(0, 22),
                        "radius": building.size * 0.72,
                        "label": "barraca extra",
                    }
                )
        return slots

    def nearest_sleep_slot(self, pos: Vector2, max_distance: float = 82.0) -> dict[str, object] | None:
        candidates = []
        for slot in self.camp_sleep_slots():
            distance = Vector2(slot["interact_pos"]).distance_to(pos)
            if distance <= max_distance:
                candidates.append((distance, slot))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    def nearest_interaction_hint(self) -> tuple[Vector2, str] | None:
        player = self.player
        active_event = self.active_dynamic_event()
        if active_event:
            if active_event.kind == "faccao" and player.distance_to(active_event.pos) < 118:
                humane = dict(active_event.data.get("humane", {}))
                hardline = dict(active_event.data.get("hardline", {}))
                return active_event.pos, f"E {humane.get('title', 'ceder')}  |  Q {hardline.get('title', 'pressionar')}"
            if active_event.kind == "expedicao" and player.distance_to(active_event.pos) < 122:
                return active_event.pos, "E socorrer equipe na trilha"
            if active_event.kind == "abrigo" and player.distance_to(active_event.pos) < 114:
                return active_event.pos, "E acolher forasteiro"
            if active_event.kind == "incendio" and player.distance_to(active_event.pos) < 118:
                return active_event.pos, "E conter incendio"
            if active_event.kind == "alarme" and player.distance_to(active_event.pos) < 120:
                return active_event.pos, "E responder ao alarme da cerca"
            if active_event.kind in {"fuga", "desercao", "doenca"}:
                target = next(
                    (survivor for survivor in self.survivors if survivor.name == active_event.target_name and survivor.is_alive()),
                    None,
                )
                if target and player.distance_to(target.pos) < 96:
                    prompt_map = {
                        "fuga": "E acalmar morador",
                        "desercao": "E impedir desercao",
                        "doenca": "E estabilizar doente",
                    }
                    return target.pos, prompt_map.get(active_event.kind, "E interagir")

        downed_member = self.nearest_downed_expedition_member(player.pos)
        if downed_member:
            return downed_member.pos, f"E levantar {downed_member.name.lower()} na trilha"

        for interest_point in self.interest_points:
            if not interest_point.resolved and player.distance_to(interest_point.pos) < interest_point.radius + 34:
                return interest_point.pos, f"E investigar {interest_point.label}"

        for node in self.resource_nodes:
            if node.is_available() and player.distance_to(node.pos) < 92:
                prompt = "E colher suprimentos" if node.kind == "food" else "E vasculhar sucata"
                return node.pos, prompt

        for barricade in self.barricades:
            if barricade.health < barricade.max_health and self.wood >= 1 and player.distance_to(barricade.pos) < 92:
                return barricade.pos, "E reforcar barricada"
            if player.distance_to(barricade.pos) < 92:
                if getattr(barricade, "spike_level", 0) >= 3:
                    return barricade.pos, "Spikes no maximo"
                wood_cost, scrap_cost = self.barricade_upgrade_cost(barricade)
                return barricade.pos, f"E melhorar spikes ({wood_cost} tabuas, {scrap_cost} sucata)"

        if player.distance_to(self.workshop_pos) < 108:
            if self.can_use_workshop_saw():
                if self.can_expand_camp():
                    return self.workshop_pos, "E cortar tabuas  |  Q ampliar acampamento"
                return self.workshop_pos, "E cortar tabuas na oficina"
            if self.can_expand_camp():
                return self.workshop_pos, "E ampliar acampamento"
            if self.camp_level < self.max_camp_level:
                log_cost, scrap_cost = self.expansion_cost()
                return self.workshop_pos, f"Precisa {log_cost} toras e {scrap_cost} sucata"
            return self.workshop_pos, "Oficina livre"

        sleep_slot = self.nearest_sleep_slot(player.pos)
        if sleep_slot and not self.player_sleeping:
            if not self.active_dynamic_events:
                return Vector2(sleep_slot["interact_pos"]), "E dormir e acelerar o tempo"
            return Vector2(sleep_slot["interact_pos"]), "Crise ativa impede descanso"

        if player.distance_to(self.radio_pos) < 104:
            if self.active_expedition:
                return self.radio_pos, "E revisar expedicao  |  Q recolher equipe"
            target_region = self.best_expedition_region()
            if target_region:
                return self.radio_pos, f"E enviar expedicao para {target_region['name']}"
            return self.radio_pos, "Sem regiao conhecida para expedicao"

        if player.distance_to(self.bonfire_pos) < 100:
            if self.available_fuel() >= 1:
                return self.bonfire_pos, "E alimentar fogueira"
            return self.bonfire_pos, "Sem combustivel para o fogo"

        infirmary = self.nearest_building_of_kind("enfermaria", player.pos)
        if infirmary and player.distance_to(infirmary.pos) < 96:
            if self.has_medical_supplies() and player.health < player.max_health - 8:
                return infirmary.pos, "E tratar ferimentos"
            return infirmary.pos, "Enfermaria sem uso imediato"

        manual_building = self.nearest_player_usable_building(player.pos)
        if manual_building:
            return manual_building.pos, self.player_building_prompt(manual_building, player)

        for survivor in self.survivors:
            if survivor.distance_to(player.pos) < 92:
                return survivor.pos, f"E conversar com {survivor.name.lower()}"
        return None

    def mouse_interaction_target(self, cursor_world: Vector2) -> dict[str, object] | None:
        """Escolhe um alvo de interacao pelo mouse para aliviar a proximidade no acampamento."""
        candidates: list[tuple[float, dict[str, object]]] = []

        def consider(kind: str, pos: Vector2, *, radius: float, reach: float, obj: object | None = None) -> None:
            distance = cursor_world.distance_to(pos)
            if distance <= radius:
                candidates.append(
                    (
                        distance,
                        {
                            "kind": kind,
                            "pos": Vector2(pos),
                            "reach": reach,
                            "obj": obj,
                        },
                    )
                )

        active_event = self.active_dynamic_event()
        if active_event:
            consider(f"event:{active_event.kind}", Vector2(active_event.pos), radius=44, reach=132, obj=active_event)
            if active_event.kind in {"fuga", "desercao", "doenca"}:
                target = next(
                    (survivor for survivor in self.survivors if survivor.name == active_event.target_name and survivor.is_alive()),
                    None,
                )
                if target:
                    consider(f"event:{active_event.kind}", Vector2(target.pos), radius=36, reach=104, obj=active_event)

        downed_member = self.nearest_downed_expedition_member(cursor_world)
        if downed_member and cursor_world.distance_to(downed_member.pos) < 28:
            consider("downed_member", Vector2(downed_member.pos), radius=28, reach=112, obj=downed_member)

        for interest_point in self.interest_points:
            if not interest_point.resolved:
                consider("interest", Vector2(interest_point.pos), radius=max(28, interest_point.radius * 0.54), reach=136, obj=interest_point)

        for node in self.resource_nodes:
            if node.is_available():
                consider(f"node:{node.kind}", Vector2(node.pos), radius=30, reach=112, obj=node)

        for barricade in self.barricades:
            consider("barricade", Vector2(barricade.pos), radius=26, reach=118, obj=barricade)

        consider("workshop", Vector2(self.workshop_pos), radius=42, reach=136)
        consider("radio", Vector2(self.radio_pos), radius=42, reach=132)
        consider("bonfire", Vector2(self.bonfire_pos), radius=46, reach=130)

        for building in self.buildings:
            if building.kind in {"serraria", "cozinha", "horta", "anexo", "torre", "enfermaria"}:
                consider(
                    f"building:{building.kind}",
                    Vector2(building.pos),
                    radius=max(26, building.size * 0.72),
                    reach=self.player_building_reach(building.kind),
                    obj=building,
                )

        sleep_slot = self.nearest_sleep_slot(cursor_world)
        if sleep_slot and cursor_world.distance_to(Vector2(sleep_slot["interact_pos"])) < 44:
            consider("sleep", Vector2(sleep_slot["interact_pos"]), radius=44, reach=132, obj=sleep_slot)

        for survivor in self.survivors:
            if survivor.is_alive() and not self.is_survivor_on_expedition(survivor):
                consider("survivor", Vector2(survivor.pos), radius=28, reach=132, obj=survivor)

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def hovered_interaction_target(self) -> dict[str, object] | None:
        """Retorna o alvo atualmente sob o mouse na tela."""
        if not hasattr(self, "input_state"):
            return None
        return self.mouse_interaction_target(self.screen_to_world(self.input_state.mouse_screen))

    def prompt_for_interaction_target(self, target: dict[str, object]) -> str | None:
        """Traduz um alvo do mouse para o texto curto de interacao exibido na HUD."""
        kind = str(target.get("kind", ""))
        obj = target.get("obj")

        if kind.startswith("event:") and obj:
            event_kind = str(kind.split(":", 1)[1])
            if event_kind == "faccao":
                humane = dict(obj.data.get("humane", {}))
                hardline = dict(obj.data.get("hardline", {}))
                return f"E {humane.get('title', 'ceder')}  |  Q {hardline.get('title', 'pressionar')}"
            if event_kind == "expedicao":
                return "E socorrer equipe na trilha"
            if event_kind == "abrigo":
                return "E acolher forasteiro"
            if event_kind == "incendio":
                return "E conter incendio"
            if event_kind == "alarme":
                return "E responder ao alarme da cerca"
            if event_kind == "fuga":
                return "E acalmar morador"
            if event_kind == "desercao":
                return "E impedir desercao"
            if event_kind == "doenca":
                return "E estabilizar doente"
        if kind == "downed_member" and obj:
            return f"E levantar {obj.name.lower()} na trilha"
        if kind == "interest" and obj:
            return f"E investigar {obj.label}"
        if kind == "node:food":
            return "E colher suprimentos"
        if kind == "node:scrap":
            return "E vasculhar sucata"
        if kind == "barricade" and obj:
            if obj.health < obj.max_health and self.wood >= 1:
                return "E reforcar barricada"
            if getattr(obj, "spike_level", 0) >= 3:
                return "Spikes no maximo"
            wood_cost, scrap_cost = self.barricade_upgrade_cost(obj)
            return f"E melhorar spikes ({wood_cost} tabuas, {scrap_cost} sucata)"
        if kind == "workshop":
            if self.can_use_workshop_saw():
                if self.can_expand_camp():
                    return "E cortar tabuas  |  Q ampliar acampamento"
                return "E cortar tabuas na oficina"
            if self.can_expand_camp():
                return "E ampliar acampamento"
            if self.camp_level < self.max_camp_level:
                log_cost, scrap_cost = self.expansion_cost()
                return f"Precisa {log_cost} toras e {scrap_cost} sucata"
            return "Oficina livre"
        if kind == "radio":
            if self.active_expedition:
                return "E revisar expedicao  |  Q recolher equipe"
            target_region = self.best_expedition_region()
            if target_region:
                return f"E enviar expedicao para {target_region['name']}"
            return "Sem regiao conhecida para expedicao"
        if kind == "bonfire":
            return "E alimentar fogueira" if self.available_fuel() >= 1 else "Sem combustivel para o fogo"
        if kind == "sleep":
            return "E dormir e acelerar o tempo" if not self.active_dynamic_events else "Crise ativa impede descanso"
        if kind.startswith("building:") and obj:
            return self.player_building_prompt(obj, self.player)
        if kind == "survivor" and obj:
            return f"E conversar com {obj.name.lower()}"
        return None

    def total_bed_capacity(self) -> int:
        return len(self.camp_sleep_slots())

    def expansion_cost(self) -> tuple[int, int]:
        base_logs = 8 + self.camp_level * 5
        base_scrap = 4 + self.camp_level * 3
        phase = self.economy_phase_key()
        multiplier = {
            "early": 1.0,
            "mid": 1.04,
            "late": 1.12,
        }[phase]
        return max(1, math.ceil(base_logs * multiplier)), max(1, math.ceil(base_scrap * multiplier))

    def can_expand_camp(self) -> bool:
        log_cost, scrap_cost = self.expansion_cost()
        return self.camp_level < self.max_camp_level and self.logs >= log_cost and self.scrap >= scrap_cost

    def spare_beds(self) -> int:
        return max(0, self.total_bed_capacity() - len(self.survivors))

    def building_by_id(self, uid: int | None) -> Building | None:
        if uid is None:
            return None
        for building in self.buildings:
            if building.uid == uid:
                return building
        return None

    def building_center_snapped(self, pos: Vector2) -> Vector2:
        rect = self.camp_rect(-36)
        grid = 32
        snapped_x = round((pos.x - CAMP_CENTER.x) / grid) * grid + CAMP_CENTER.x
        snapped_y = round((pos.y - CAMP_CENTER.y) / grid) * grid + CAMP_CENTER.y
        snapped = Vector2(
            clamp(snapped_x, rect.left + 20, rect.right - 20),
            clamp(snapped_y, rect.top + 20, rect.bottom - 20),
        )
        return snapped

    def placement_size_for(self, kind: str) -> float:
        return float(self.build_recipe_for(kind)["size"])

    def build_placement_profile(self, kind: str) -> dict[str, float]:
        """Controla o quanto cada estrutura precisa respirar dentro da base."""
        profiles = {
            "barraca": {"edge": 10, "core": 26, "tent": 10, "building": 8, "wall": 16},
            "torre": {"edge": 12, "core": 34, "tent": 16, "building": 10, "wall": 12},
            "horta": {"edge": 10, "core": 22, "tent": 10, "building": 8, "wall": 14},
            "anexo": {"edge": 10, "core": 26, "tent": 12, "building": 10, "wall": 16},
            "serraria": {"edge": 12, "core": 28, "tent": 14, "building": 10, "wall": 16},
            "cozinha": {"edge": 12, "core": 28, "tent": 14, "building": 10, "wall": 16},
            "enfermaria": {"edge": 12, "core": 28, "tent": 14, "building": 10, "wall": 16},
        }
        return profiles.get(kind, {"edge": 12, "core": 28, "tent": 12, "building": 10, "wall": 16})

    def placement_collision_radius(self, kind: str) -> float:
        """Aproxima o footprint real da estrutura para liberar mais espaco util."""
        return self.placement_size_for(kind) * 0.72

    def is_valid_build_position(self, kind: str, pos: Vector2) -> bool:
        size = self.placement_size_for(kind)
        radius = self.placement_collision_radius(kind)
        profile = self.build_placement_profile(kind)
        if not self.point_in_camp_square(pos, padding=-(radius + profile["edge"])):
            return False
        core_positions = [
            self.bonfire_pos,
            self.stockpile_pos,
            self.kitchen_pos,
            self.workshop_pos,
            self.radio_pos,
        ]
        if any(pos.distance_to(core) < radius + profile["core"] for core in core_positions):
            return False
        if any(pos.distance_to(Vector2(tent["pos"])) < radius + profile["tent"] for tent in self.tents):
            return False
        if any(
            pos.distance_to(building.pos) < radius + building.size * 0.68 + profile["building"]
            for building in self.buildings
        ):
            return False
        if any(
            request.approved and pos.distance_to(request.pos) < radius + request.size * 0.68 + profile["building"]
            for request in self.build_requests
        ):
            return False
        if any(pos.distance_to(barricade.pos) < radius + profile["wall"] for barricade in self.barricades):
            return False
        return True

    def player_building_reach(self, kind: str) -> float:
        return {
            "serraria": 110.0,
            "cozinha": 104.0,
            "horta": 98.0,
            "anexo": 106.0,
            "torre": 112.0,
            "enfermaria": 104.0,
        }.get(kind, 100.0)

    def nearest_player_usable_building(self, pos: Vector2, max_distance: float = 116.0) -> Building | None:
        allowed = {"serraria", "cozinha", "horta", "anexo", "torre", "enfermaria"}
        candidates = [
            building
            for building in self.buildings
            if building.kind in allowed and building.pos.distance_to(pos) <= self.player_building_reach(building.kind)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda building: building.pos.distance_to(pos))

    def player_building_prompt(self, building: Building, player) -> str:
        kind = building.kind
        if kind == "serraria":
            if self.logs >= 2:
                return "E usar serraria"
            return "Serraria sem toras"
        if kind == "cozinha":
            if self.food >= 2 and self.available_fuel() > 0:
                return "E cozinhar em lote"
            if self.available_fuel() <= 0:
                return "Cozinha sem combustivel"
            return "Cozinha sem insumos"
        if kind == "horta":
            if self.is_night:
                return "Horta descansando a noite"
            if not self.garden_is_ready(building):
                return "Horta crescendo"
            return "E colher horta"
        if kind == "anexo":
            weakest = self.weakest_barricade()
            if weakest and weakest.health < weakest.max_health and self.wood > 0:
                return "E montar kit de reparo"
            return "Anexo pronto para manutencao"
        if kind == "torre":
            if self.find_closest_zombie(building.pos, 250):
                return "E usar torre de vigia"
            return "Torre em vigia"
        if kind == "enfermaria":
            if self.has_medical_supplies() and player.health < player.max_health - 8:
                return "E tratar ferimentos"
            if self.herbs > 0 and self.scrap > 0:
                return "E preparar remedio"
            return "Enfermaria tranquila"
        return "E usar estrutura"

    def use_building_as_player(self, building: Building, player) -> bool:
        kind = building.kind
        if kind == "serraria":
            if self.logs < 2:
                self.spawn_floating_text("faltam toras", building.pos, PALETTE["muted"])
                return False
            produced = self.sawmill_output("lenhador")
            if not self.consume_resource("logs", 2):
                return False
            stored = self.add_resource_bundle({"wood": produced})
            self.spawn_floating_text(self.bundle_summary(stored or {"wood": produced}), building.pos, PALETTE["accent_soft"])
            self.impact_burst(building.pos, PALETTE["accent_soft"], radius=12, shake=0.45, ember_count=3, smoky=True)
            self.set_event_message("A serraria mordeu as toras e soltou tabuas para a base.", duration=4.6)
            return True
        if kind == "cozinha":
            if self.food < 2:
                self.spawn_floating_text("faltam insumos", building.pos, PALETTE["muted"])
                return False
            if self.available_fuel() <= 0:
                self.spawn_floating_text("sem combustivel", building.pos, PALETTE["muted"])
                return False
            produced = self.cookhouse_output("cozinheiro")
            if not self.consume_resource("food", 2) or not self.consume_fuel(1):
                return False
            stored = self.add_resource_bundle({"meals": produced})
            self.spawn_floating_text(self.bundle_summary(stored or {"meals": produced}), building.pos, PALETTE["morale"])
            self.emit_embers(building.pos, 5)
            self.set_event_message("A cozinha encheu o ar com comida quente para a clareira.", duration=4.6)
            return True
        if kind == "horta":
            if self.is_night:
                self.spawn_floating_text("horta fechada", building.pos, PALETTE["muted"])
                return False
            if not self.garden_is_ready(building):
                self.spawn_floating_text("ainda crescendo", building.pos, PALETTE["muted"])
                return False
            bundle = self.garden_harvest_bundle("cozinheiro")
            stored = self.add_resource_bundle(bundle)
            self.start_garden_regrow(building)
            self.spawn_floating_text(self.bundle_summary(stored or bundle), building.pos, PALETTE["heal"])
            self.set_event_message("A horta rendeu um pouco de folego para o estoque.", duration=4.2)
            return True
        if kind == "anexo":
            weakest = self.weakest_barricade()
            if not weakest or weakest.health >= weakest.max_health or self.wood <= 0:
                self.spawn_floating_text("sem reparo urgente", building.pos, PALETTE["muted"])
                return False
            self.wood -= 1
            weakest.repair(self.workbench_repair_amount())
            self.spawn_floating_text("kit de reparo", weakest.pos, PALETTE["heal"])
            self.impact_burst(weakest.pos, PALETTE["heal"], radius=12, shake=0.55, ember_count=2, smoky=True)
            self.set_event_message("O anexo virou manutencao rapida na linha defensiva.", duration=4.4)
            return True
        if kind == "torre":
            zombie = self.find_closest_zombie(building.pos, 250)
            if not zombie:
                self.spawn_floating_text("sem alvo na mata", building.pos, PALETTE["muted"])
                return False
            zombie.health -= 28
            zombie.stagger = max(zombie.stagger, 0.18)
            self.damage_pulses.append(DamagePulse(Vector2(zombie.pos), 14, 0.24, PALETTE["accent_soft"]))
            self.spawn_floating_text("tiro da torre", building.pos, PALETTE["energy"])
            return True
        if kind == "enfermaria":
            if self.has_medical_supplies() and player.health < player.max_health - 8:
                if self.medicine > 0:
                    self.medicine -= 1
                    player.health = clamp(player.health + 26, 0, player.max_health)
                    self.spawn_floating_text("curativo pesado", building.pos, PALETTE["heal"])
                elif self.herbs > 0:
                    self.herbs -= 1
                    player.health = clamp(player.health + 14, 0, player.max_health)
                    self.spawn_floating_text("ervas medicinais", building.pos, PALETTE["heal"])
                return True
            if self.herbs > 0 and self.scrap > 0:
                self.herbs -= 1
                self.scrap -= 1
                produced = self.clinic_medicine_output()
                stored = self.add_resource_bundle({"medicine": produced})
                self.spawn_floating_text(self.bundle_summary(stored or {"medicine": produced}), building.pos, PALETTE["heal"])
                self.set_event_message("A enfermaria montou remedios de campo para a proxima crise.", duration=4.8)
                return True
            self.spawn_floating_text("sem uso imediato", building.pos, PALETTE["muted"])
            return False
        return False

    def place_building(self, kind: str, pos: Vector2) -> bool:
        recipe = self.build_recipe_for(kind)
        snapped = self.building_center_snapped(pos)
        wood_cost, scrap_cost = self.build_cost_for(recipe)
        if self.wood < wood_cost or self.scrap < scrap_cost:
            self.set_event_message("Faltam recursos para essa construcao.", duration=3.4)
            return False
        if not self.is_valid_build_position(kind, snapped):
            self.set_event_message("Nao ha espaco livre nesse ponto do acampamento.", duration=3.4)
            return False

        self.wood -= wood_cost
        self.scrap -= scrap_cost
        self.buildings.append(
            Building(
                uid=self.next_building_uid,
                kind=kind,
                pos=snapped,
                size=float(recipe["size"]),
            )
        )
        self.next_building_uid += 1
        self.refresh_barricade_strength()
        self.assign_building_specialists()
        self.spawn_floating_text(str(recipe["label"]).lower(), snapped, PALETTE["accent_soft"])
        self.set_event_message(f"{recipe['label']} erguida na clareira.", duration=4.8)
        self.emit_embers(snapped, 6, smoky=True)
        return True

    def refresh_barricade_strength(self) -> None:
        bonus_health = self.building_count("anexo") * 18
        bonus_tier = self.building_count("anexo")
        for barricade in self.barricades:
            ratio = 1.0 if barricade.max_health <= 0 else barricade.health / barricade.max_health
            spike_health = getattr(barricade, "spike_level", 0) * 18
            barricade.max_health = 110 + (1 + self.camp_level) * 28 + bonus_health + spike_health
            barricade.tier = 1 + self.camp_level + bonus_tier
            barricade.health = clamp(barricade.max_health * ratio, 0.0, barricade.max_health)

    def barricade_upgrade_cost(self, barricade: Barricade) -> tuple[int, int]:
        level = getattr(barricade, "spike_level", 0)
        wood_cost = 2 + level * 2
        scrap_cost = 1 + level
        return wood_cost, scrap_cost

    def can_upgrade_barricade(self, barricade: Barricade) -> bool:
        if getattr(barricade, "spike_level", 0) >= 3:
            return False
        wood_cost, scrap_cost = self.barricade_upgrade_cost(barricade)
        return self.wood >= wood_cost and self.scrap >= scrap_cost

    def upgrade_barricade(self, barricade: Barricade) -> bool:
        if getattr(barricade, "spike_level", 0) >= 3:
            self.spawn_floating_text("spikes no limite", barricade.pos, PALETTE["muted"])
            return False
        wood_cost, scrap_cost = self.barricade_upgrade_cost(barricade)
        if self.wood < wood_cost or self.scrap < scrap_cost:
            self.spawn_floating_text(
                f"precisa {wood_cost} tabuas e {scrap_cost} sucata",
                barricade.pos,
                PALETTE["muted"],
            )
            return False
        ratio = 1.0 if barricade.max_health <= 0 else barricade.health / barricade.max_health
        self.wood -= wood_cost
        self.scrap -= scrap_cost
        barricade.spike_level = getattr(barricade, "spike_level", 0) + 1
        self.refresh_barricade_strength()
        barricade.health = clamp(max(barricade.health, barricade.max_health * ratio + 12), 0.0, barricade.max_health)
        self.spawn_floating_text(f"spikes nv {barricade.spike_level}", barricade.pos, PALETTE["accent_soft"])
        self.set_event_message("As defesas ganharam spikes mais agressivos.", duration=4.6)
        self.impact_burst(barricade.pos, PALETTE["accent_soft"], radius=13, shake=0.7, ember_count=3, smoky=True)
        return True

    def workbench_repair_amount(self) -> float:
        phase_bonus = {
            "early": 0,
            "mid": 4,
            "late": 8,
        }[self.economy_phase_key()]
        return 18 + self.building_count("anexo") * 10 + phase_bonus

    def can_use_workshop_saw(self) -> bool:
        """Libera a oficina inicial para cortar toras em tabuas antes da serraria."""
        return not self.buildings_of_kind("serraria") and self.logs > 0

    def workshop_plank_bundle(self, role: str | None = None) -> dict[str, int]:
        """A oficina e lenta: serve para destravar o comeco, nao para substituir a serraria."""
        produced = 2
        if role in {"artesa", "lenhador"} and self.random.random() < 0.3:
            produced += 1
        return {"wood": produced}

    def cut_planks_at_workshop(self, *, role: str | None = None) -> dict[str, int] | None:
        """Converte uma tora em poucas tabuas, sem a eficiencia de uma serraria real."""
        if not self.can_use_workshop_saw():
            return None
        if not self.consume_resource("logs", 1):
            return None
        bundle = self.workshop_plank_bundle(role)
        stored = self.add_resource_bundle(bundle)
        if not stored:
            self.logs += 1
            return None
        return stored

    def stockpile_capacity(self, resource: str) -> int:
        if self.unlimited_resources_enabled():
            return 9999
        base = {
            "logs": 26,
            "wood": 34,
            "food": 24,
            "herbs": 12,
            "scrap": 24,
            "meals": 18,
            "medicine": 10,
        }[resource]
        camp_bonus = self.camp_level * 6
        annex_bonus = self.building_count("anexo") * 8
        specialty_bonus = {
            "logs": self.building_count("serraria") * 8,
            "wood": self.building_count("serraria") * 6,
            "food": self.building_count("cozinha") * 5 + self.building_count("horta") * 4,
            "herbs": self.building_count("enfermaria") * 4,
            "scrap": self.building_count("anexo") * 4,
            "meals": self.building_count("cozinha") * 6,
            "medicine": self.building_count("enfermaria") * 5,
        }[resource]
        bed_bonus = self.building_count("barraca") * 2
        return base + camp_bonus + annex_bonus + specialty_bonus + bed_bonus

    def normalize_stockpile(self) -> None:
        for resource in ("logs", "wood", "food", "herbs", "scrap", "meals", "medicine"):
            current = int(getattr(self, resource))
            setattr(self, resource, int(clamp(current, 0, self.stockpile_capacity(resource))))

    def add_resource_bundle(self, bundle: dict[str, int]) -> dict[str, int]:
        stored: dict[str, int] = {}
        for resource, amount in bundle.items():
            if amount <= 0:
                continue
            current = int(getattr(self, resource))
            capacity = self.stockpile_capacity(resource)
            accepted = max(0, min(amount, capacity - current))
            if accepted:
                setattr(self, resource, current + accepted)
                stored[resource] = accepted
        return stored

    def consume_resource(self, resource: str, amount: int) -> bool:
        if getattr(self, resource) < amount:
            return False
        setattr(self, resource, getattr(self, resource) - amount)
        return True

    def has_resource_bundle(self, bundle: dict[str, int]) -> bool:
        for resource, amount in bundle.items():
            if getattr(self, resource) < amount:
                return False
        return True

    def consume_resource_bundle(self, bundle: dict[str, int]) -> bool:
        if not self.has_resource_bundle(bundle):
            return False
        for resource, amount in bundle.items():
            setattr(self, resource, getattr(self, resource) - amount)
        return True

    def available_fuel(self) -> int:
        return self.logs + self.wood

    def consume_fuel(self, amount: int = 1) -> bool:
        spent = 0
        while spent < amount and self.logs > 0:
            self.logs -= 1
            spent += 1
        while spent < amount and self.wood > 0:
            self.wood -= 1
            spent += 1
        return spent == amount

    def add_fuel_to_bonfire(self) -> tuple[bool, str, tuple[int, int, int]]:
        if self.logs > 0:
            self.logs -= 1
            self.bonfire_heat = clamp(self.bonfire_heat + 18, 0, 100)
            self.bonfire_ember_bed = clamp(self.bonfire_ember_bed + 16, 0, 100)
            return True, "tora na fogueira", PALETTE["light"]
        if self.wood > 0:
            self.wood -= 1
            self.bonfire_heat = clamp(self.bonfire_heat + 10, 0, 100)
            self.bonfire_ember_bed = clamp(self.bonfire_ember_bed + 7, 0, 100)
            return True, "tabua no fogo", PALETTE["light"]
        return False, "sem combustivel", PALETTE["danger_soft"]

    def bonfire_stage(self) -> str:
        level = self.bonfire_heat * 0.7 + self.bonfire_ember_bed * 0.3
        if level >= 76:
            return "alta"
        if level >= 44:
            return "estavel"
        if level >= 18:
            return "fraca"
        return "brasas"

    def update_bonfire(self, dt: float) -> None:
        weather_drag = self.weather_precipitation_factor() * 0.38
        weather_drag += self.weather_wind_factor() * 0.14
        weather_drag += self.weather_mist_factor() * 0.05
        weather_drag += self.weather_storm_factor() * 0.16

        dark_factor = self.visual_darkness_factor()
        ember_decay = lerp(0.11, 0.18, dark_factor) + weather_drag * 0.55
        self.bonfire_ember_bed = clamp(self.bonfire_ember_bed - ember_decay * dt, 0, 100)

        target_heat = clamp(self.bonfire_ember_bed + lerp(10, 18, dark_factor), 0, 100)
        cooling = lerp(0.66, 1.08, dark_factor) + weather_drag
        if self.bonfire_heat > target_heat:
            overshoot = 1.0 + max(0.0, self.bonfire_heat - target_heat) / 38
            self.bonfire_heat = clamp(self.bonfire_heat - cooling * overshoot * dt, 0, 100)
        else:
            self.bonfire_heat = clamp(self.bonfire_heat + min(0.9, (target_heat - self.bonfire_heat) * 0.08) * dt, 0, 100)

    def buildings_of_kind(self, kind: str) -> list[Building]:
        return [building for building in self.buildings if building.kind == kind]

    def nearest_building_of_kind(self, kind: str, pos: Vector2) -> Building | None:
        matches = self.buildings_of_kind(kind)
        if not matches:
            return None
        return min(matches, key=lambda building: building.pos.distance_to(pos))

    def resource_node_bundle(self, node: ResourceNode, *, role: str | None = None) -> dict[str, int]:
        if node.kind == "food":
            bundles = {
                "berries": {"food": 2},
                "mushrooms": {"food": 2, "herbs": 1},
                "flowers": {"food": 1, "herbs": 1},
                "herbs": {"food": 1, "herbs": 1},
                "roots": {"food": 2},
                "reeds": {"food": 1, "herbs": 1},
            }
            bundle = dict(bundles.get(node.variant, {"food": 2}))
            if role == "batedora":
                bundle["food"] = bundle.get("food", 0) + 1
                if "herbs" in bundle:
                    bundle["herbs"] += 1
            return bundle

        bundles = {
            "cache": {"scrap": 2},
            "crate": {"scrap": 3},
            "ore": {"scrap": 3},
            "stonecache": {"scrap": 2},
            "bogmetal": {"scrap": 2},
            "charcoal": {"scrap": 1, "logs": 1},
            "cart": {"scrap": 1, "logs": 1},
            "relic": {"scrap": 1, "medicine": 1},
        }
        bundle = dict(bundles.get(node.variant, {"scrap": 2}))
        if role == "mensageiro":
            bundle["scrap"] = bundle.get("scrap", 0) + 1
        return bundle

    def bundle_summary(self, bundle: dict[str, int]) -> str:
        labels = {
            "logs": "tora",
            "wood": "tabua",
            "food": "insumo",
            "herbs": "erva",
            "scrap": "sucata",
            "meals": "refeicao",
            "medicine": "remedio",
        }
        parts = [f"+{amount} {labels.get(resource, resource)}" for resource, amount in bundle.items() if amount > 0]
        return "  ".join(parts) if parts else "estoque cheio"

    def most_injured_actor(self) -> Actor | None:
        candidates: list[Actor] = [self.player]
        candidates.extend(self.living_survivors())
        wounded = [actor for actor in candidates if actor.health < actor.max_health - 6]
        if not wounded:
            return None
        return min(wounded, key=lambda actor: actor.health / max(1, actor.max_health))

    def has_medical_supplies(self) -> bool:
        return self.medicine > 0 or self.herbs > 0

    def can_treat_infirmary(self) -> bool:
        return bool(self.buildings_of_kind("enfermaria") and self.has_medical_supplies())

    def sync_survivor_assignments(self) -> None:
        guard_posts = self.guard_posts()
        sleep_slots = self.camp_sleep_slots()
        for index, survivor in enumerate(self.survivors):
            if index < len(sleep_slots):
                slot = sleep_slots[index]
                survivor.home_pos = Vector2(slot["sleep_pos"])
                if survivor.distance_to(survivor.home_pos) < 34:
                    survivor.pos = Vector2(slot["sleep_pos"])
                survivor.sleep_slot_kind = str(slot["kind"])
                survivor.sleep_slot_building_uid = int(slot["building_uid"]) if slot["building_uid"] is not None else None
            survivor.guard_pos = Vector2(guard_posts[index % len(guard_posts)])
            survivor.assigned_tent_index = index
            survivor.assigned_building_id = None
            survivor.assigned_building_kind = None

    def resolve_actor_camp_collision(self, actor: Actor) -> None:
        allow_kind = None
        allow_index = None
        allow_building_uid = None
        state = getattr(actor, "state", "")
        if actor is self.player and getattr(self, "player_sleeping", False):
            slot = getattr(self, "player_sleep_slot", None)
            if slot:
                allow_kind = str(slot["kind"])
                allow_index = int(slot["index"])
                allow_building_uid = slot["building_uid"]
        elif state in {"sleep", "rest", "shelter"}:
            allow_kind = str(getattr(actor, "sleep_slot_kind", "tent"))
            allow_index = int(getattr(actor, "assigned_tent_index", 0))
            allow_building_uid = getattr(actor, "sleep_slot_building_uid", None)

        for slot in self.camp_sleep_slots():
            if (
                allow_kind == "barraca"
                and str(slot["kind"]) == "barraca"
                and allow_building_uid is not None
                and allow_building_uid == slot["building_uid"]
            ):
                continue
            if allow_kind == str(slot["kind"]) and allow_index == int(slot["index"]) and allow_building_uid == slot["building_uid"]:
                continue
            offset = actor.pos - Vector2(slot["pos"])
            min_distance = actor.radius + float(slot["radius"])
            distance = offset.length()
            if distance >= min_distance:
                continue
            if distance <= 0.01:
                offset = Vector2(1, 0)
                distance = 1.0
            actor.pos = Vector2(slot["pos"]) + offset.normalize() * min_distance

    def relationship_score(self, survivor_a: Survivor, survivor_b: Survivor) -> float:
        return social_system.relationship_score(self, survivor_a, survivor_b)

    def adjust_relationship(self, survivor_a: Survivor, survivor_b: Survivor, delta: float) -> None:
        social_system.adjust_relationship(self, survivor_a, survivor_b, delta)

    def adjust_trust(self, survivor: Survivor, delta: float) -> None:
        social_system.adjust_trust(self, survivor, delta)

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
        social_system.impact_burst(self, origin, color, radius=radius, shake=shake, ember_count=ember_count, smoky=smoky)

    def survivor_bark_options(self, survivor: Survivor) -> list[tuple[str, tuple[int, int, int]]]:
        return social_system.survivor_bark_options(self, survivor)
        lines: list[tuple[str, tuple[int, int, int]]] = []
        crisis = self.dynamic_event_for_survivor(survivor)
        active_event = self.active_dynamic_event()
        if crisis and crisis.kind == "doenca":
            lines.extend((("To queimando por dentro.", PALETTE["danger_soft"]), ("Nao me deixa apagar aqui.", PALETTE["danger_soft"])))
        elif crisis and crisis.kind in {"fuga", "desercao"}:
            lines.extend((("Nao da mais pra segurar!", PALETTE["danger_soft"]), ("Eu preciso sumir da trilha.", PALETTE["danger_soft"])))
        elif active_event and active_event.kind == "incendio":
            lines.extend((("Fogo no campo!", PALETTE["danger_soft"]), ("Traz agua, agora!", PALETTE["danger_soft"])))
        elif active_event and active_event.kind == "alarme":
            lines.extend((("Ouvi pancada na cerca!", PALETTE["danger_soft"]), ("Tem coisa rondando a linha!", PALETTE["danger_soft"])))
        elif active_event and active_event.kind == "expedicao":
            lines.extend((("A trilha ta pedindo socorro.", PALETTE["morale"]), ("Se cair a coluna, cai nossa moral.", PALETTE["morale"])))

        if self.is_night and getattr(self, "horde_active", False):
            lines.extend((("Segura a linha!", PALETTE["danger_soft"]), ("A mata inteira ta vindo.", PALETTE["danger_soft"])))
        elif self.is_night and self.find_closest_zombie(survivor.pos, 150):
            lines.extend((("Contato perto da paliçada.", PALETTE["danger_soft"]), ("Mortos na escuridao.", PALETTE["danger_soft"])))

        if self.bonfire_heat < 28 or self.bonfire_ember_bed < 18:
            lines.extend((("A fogueira ta morrendo.", PALETTE["morale"]), ("Sem fogo o campo desanda.", PALETTE["morale"])))
        if self.food + self.meals <= max(2, len(self.living_survivors()) // 2):
            lines.extend((("A panela ta vazia.", PALETTE["accent_soft"]), ("A fome vai virar briga.", PALETTE["accent_soft"])))
        if survivor.health < 42:
            lines.extend((("Preciso de curativo.", PALETTE["heal"]), ("Nao aguento mais um golpe.", PALETTE["heal"])))
        if survivor.insanity > 74:
            lines.extend((("A mata ta falando comigo.", PALETTE["morale"]), ("Tem olho demais na escuridao.", PALETTE["morale"])))
        if survivor.trust_leader < 34:
            lines.extend((("Chefe, voce sumiu demais.", PALETTE["muted"]), ("A gente ta segurando isso no osso.", PALETTE["muted"])))
        if survivor.has_trait("leal") and self.player.distance_to(survivor.pos) < 150:
            lines.extend((("Eu seguro contigo, chefe.", PALETTE["heal"]), ("Da a ordem que eu vou.", PALETTE["heal"])))
        if survivor.has_trait("sociavel") and self.player.distance_to(self.bonfire_pos) < 180:
            lines.extend((("Fica perto do fogo com a gente.", PALETTE["morale"]), ("Uma historia segura mais que faca.", PALETTE["morale"])))
        if survivor.has_trait("paranoico") and self.is_night:
            lines.extend((("Tem coisa na linha das arvores.", PALETTE["danger_soft"]), ("Nao confio nesse silencio.", PALETTE["danger_soft"])))

        friend = self.best_friend_name(survivor)
        rival = self.rival_name(survivor)
        if friend and survivor.morale > 58 and self.random.random() < 0.35:
            lines.append((f"{friend} ainda segura meu juizo.", PALETTE["accent_soft"]))
        if rival and survivor.conflict_cooldown <= 0 and self.random.random() < 0.28:
            lines.append((f"{rival} vai me fazer explodir.", PALETTE["danger_soft"]))

        if not lines:
            lines.extend(
                (
                    ("Mais um turno e a gente segura.", PALETTE["text"]),
                    ("Se o fogo fica vivo, eu fico tambem.", PALETTE["text"]),
                    ("Essa mata cobra tudo da gente.", PALETTE["muted"]),
                    ("So nao me deixa sem rumo, chefe.", PALETTE["muted"]),
                )
            )
        return lines

    def trigger_survivor_bark(
        self,
        survivor: Survivor,
        text: str,
        color: tuple[int, int, int],
        *,
        duration: float = 2.8,
    ) -> None:
        social_system.trigger_survivor_bark(self, survivor, text, color, duration=duration)

    def survivors_react_to_event(self, event: DynamicEvent, *, resolved: bool | None = None) -> None:
        social_system.survivors_react_to_event(self, event, resolved=resolved)

    def update_survivor_barks(self, dt: float) -> None:
        social_system.update_survivor_barks(self, dt)

    def average_trust(self) -> float:
        return social_system.average_trust(self)

    def friendship_count(self) -> int:
        return social_system.friendship_count(self)

    def feud_count(self) -> int:
        return social_system.feud_count(self)

    def best_friend_name(self, survivor: Survivor) -> str | None:
        return social_system.best_friend_name(self, survivor)

    def rival_name(self, survivor: Survivor) -> str | None:
        return social_system.rival_name(self, survivor)

    def latest_social_memory(self, survivor: Survivor, topic: str | None = None) -> dict[str, object] | None:
        return social_system.latest_social_memory(survivor, topic)

    def social_summary_text(self, survivor: Survivor) -> tuple[str, tuple[int, int, int]]:
        return social_system.social_summary_text(self, survivor)

    def contextual_build_request_reason(self, survivor: Survivor, kind: str) -> tuple[str, str]:
        return social_system.contextual_build_request_reason(self, survivor, kind)

    def initialize_survivor_relationships(self) -> None:
        social_system.initialize_survivor_relationships(self)

    def update_social_dynamics(self, dt: float) -> None:
        social_system.update_social_dynamics(self, dt)

    def assign_building_specialists(self) -> None:
        social_system.assign_building_specialists(self)

    def active_guard_names(self) -> set[str]:
        return social_system.active_guard_names(self)

    def should_survivor_sleep(self, survivor: Survivor) -> bool:
        return social_system.should_survivor_sleep(self, survivor)

    def expand_camp(self) -> bool:
        if not self.can_expand_camp():
            return False

        log_cost, scrap_cost = self.expansion_cost()
        self.logs -= log_cost
        self.scrap -= scrap_cost
        self.camp_level += 1
        self.layout_camp_core()
        self.path_network = self.generate_path_network()
        self.tents = self.generate_tents()
        self.reflow_barricades_for_current_camp_size()
        self.refresh_barricade_strength()
        self.sync_survivor_assignments()
        self.terrain_surface = self.build_terrain_surface()
        self.record_fog_reveal(CAMP_CENTER, self.camp_clearance_radius() + 120)
        self.set_event_message("A oficina abriu mais espaco e reforcou o quadrado do acampamento.", duration=7.0)
        self.spawn_floating_text("acampamento ampliado", self.workshop_pos, PALETTE["accent_soft"])
        self.emit_embers(self.workshop_pos, 10, smoky=True)
        return True

    def recruit_survivor_from_profile(
        self,
        profile: dict[str, object],
        *,
        announce_message: str,
        floating_label: str = "novo morador",
    ) -> Survivor | None:
        sleep_slots = self.camp_sleep_slots()
        if self.spare_beds() <= 0 or len(self.survivors) >= len(sleep_slots):
            return None
        slot = sleep_slots[len(self.survivors)]
        guard_pos = self.guard_posts()[len(self.survivors) % len(self.guard_posts())]
        newcomer = Survivor(
            str(profile["name"]),
            str(profile["role"]),
            Vector2(slot["sleep_pos"]),
            Vector2(slot["sleep_pos"]),
            Vector2(guard_pos),
            tuple(profile.get("traits", ())),
        )
        self.survivors.append(newcomer)
        self.sync_survivor_assignments()
        self.initialize_survivor_relationships()
        self.set_event_message(announce_message, duration=6.2)
        self.spawn_floating_text(floating_label, newcomer.pos, PALETTE["morale"])
        return newcomer

    def remove_survivor(self, survivor: Survivor) -> None:
        self.survivors = [member for member in self.survivors if member is not survivor]
        for member in self.survivors:
            member.relations.pop(survivor.name, None)
        self.sync_survivor_assignments()
        self.assign_building_specialists()

    def try_recruit_survivor(self) -> None:
        if self.spare_beds() <= 0 or self.next_recruit_index >= len(self.recruit_pool):
            return
        if any(event.kind == "abrigo" for event in self.active_dynamic_events):
            return
        if self.average_morale() < 54 or self.weakest_barricade_health() < 42:
            return
        arrival_chance = 0.36 + self.camp_level * 0.12
        if self.random.random() > arrival_chance:
            return

        profile = self.recruit_pool[self.next_recruit_index]
        self.next_recruit_index += 1
        self.recruit_survivor_from_profile(
            profile,
            announce_message=f"{profile['name']} encontrou cama e entrou para a clareira.",
        )

    def generate_world_features(self) -> list[WorldFeature]:
        plan = (
            ("grove", 4, (170, 290)),
            ("meadow", 3, (150, 250)),
            ("swamp", 2, (140, 220)),
            ("ruin", 2, (120, 180)),
        )
        features: list[WorldFeature] = []
        for kind, count, radius_range in plan:
            created = 0
            attempts = 0
            while created < count and attempts < 500:
                attempts += 1
                radius = self.random.uniform(*radius_range)
                pos = self.random_world_pos(180)
                if pos.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 320:
                    continue
                if any(pos.distance_to(feature.pos) < (radius + feature.radius) * 0.72 for feature in features):
                    continue
                features.append(WorldFeature(kind, pos, radius, self.random.random()))
                created += 1
        return features

    def generate_interest_points(self) -> list[InterestPoint]:
        templates = {
            "grove": [
                ("herb_cache", "ervas silvestres"),
                ("hunter_blind", "posto de cacador"),
            ],
            "meadow": [
                ("lost_cart", "carroca esquecida"),
                ("flower_shrine", "canteiro raro"),
            ],
            "swamp": [
                ("sunken_cache", "caixa semi-afundada"),
                ("reed_nest", "ninho entre juncos"),
            ],
            "ruin": [
                ("tool_crate", "caixote de oficina"),
                ("alarm_nest", "sirene quebrada"),
            ],
        }

        interest_points: list[InterestPoint] = []
        for feature in self.world_features:
            event_kind, label = self.random.choice(templates[feature.kind])
            angle = self.random.uniform(0, math.tau)
            offset = angle_to_vector(angle) * self.random.uniform(feature.radius * 0.18, feature.radius * 0.55)
            pos = Vector2(feature.pos) + offset
            pos.x = clamp(pos.x, 70, WORLD_WIDTH - 70)
            pos.y = clamp(pos.y, 70, WORLD_HEIGHT - 70)
            interest_points.append(
                InterestPoint(
                    feature_kind=feature.kind,
                    event_kind=event_kind,
                    label=label,
                    pos=pos,
                    radius=26 if feature.kind != "ruin" else 30,
                    pulse=self.random.uniform(0, math.tau),
                )
            )
        return interest_points

    def create_fog_of_war_surface(self) -> pygame.Surface:
        self.fog_reveals: list[tuple[Vector2, float]] = []
        self.fog_reveal_keys: set[tuple[int, int, int]] = set()
        self.record_fog_reveal(CAMP_CENTER, self.camp_clearance_radius() + 120)
        self.record_fog_reveal(self.player.pos, 156)
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    def fog_reveal_key(self, center: Vector2, radius: float) -> tuple[int, int, int]:
        return (int(center.x // 26), int(center.y // 26), int(radius // 8))

    def record_fog_reveal(self, center: Vector2, radius: float) -> None:
        key = self.fog_reveal_key(center, radius)
        if key in getattr(self, "fog_reveal_keys", set()):
            return
        self.fog_reveal_keys.add(key)
        self.fog_reveals.append((Vector2(center), float(radius)))

    def visible_fog_reveals(self, view_rect: pygame.Rect) -> list[tuple[Vector2, float]]:
        margin_rect = view_rect.inflate(420, 420)
        visible: list[tuple[Vector2, float]] = []
        for center, radius in getattr(self, "fog_reveals", []):
            if margin_rect.collidepoint(int(center.x), int(center.y)):
                visible.append((center, radius))
        return visible

    def reveal_world_around_player(self) -> None:
        self.record_fog_reveal(self.player.pos, 186)
        if self.player.distance_to(self.bonfire_pos) < self.camp_clearance_radius() + 40:
            self.record_fog_reveal(CAMP_CENTER, self.camp_clearance_radius() + 88)
        for survivor in self.living_survivors():
            self.record_fog_reveal(survivor.pos, 92)

    def feature_label(self, kind: str) -> str:
        return {
            "grove": "Bosque Fechado",
            "meadow": "Clareira Alta",
            "swamp": "Brejo Escuro",
            "ruin": "Ruinas Velhas",
            "forest": "Mata Profunda",
            "ashland": "Cinzas Frias",
            "redwood": "Bosque Gigante",
            "quarry": "Pedreira Morta",
            "camp": "Clareira do Campo",
        }.get(kind, "Mata Fechada")

    def named_region_at(self, pos: Vector2) -> dict[str, object] | None:
        if self.point_in_camp_square(pos, padding=140):
            return None
        return self.ensure_named_region(*self.region_key_for_pos(pos))

    def feature_at_pos(self, pos: Vector2) -> WorldFeature | None:
        inside = [
            feature
            for feature in [*self.world_features, *self.endless_features]
            if pos.distance_to(feature.pos) <= feature.radius * 0.96
        ]
        if inside:
            return min(inside, key=lambda feature: pos.distance_to(feature.pos))
        return None

    def surface_audio_at(self, pos: Vector2) -> str:
        if self.point_in_camp_square(pos, padding=-28):
            return "camp"
        if self.is_near_path(pos, 34):
            return "path"
        feature = self.feature_at_pos(pos)
        if not feature:
            return "forest"
        if feature.kind == "meadow":
            return "meadow"
        if feature.kind == "swamp":
            return "swamp"
        if feature.kind in {"ruin", "quarry", "ashland"}:
            return "ruin"
        return "forest"

    def unresolved_interest_points(self) -> list[InterestPoint]:
        return [point for point in self.interest_points if not point.resolved]

    def active_dynamic_event(self, kind: str | None = None) -> DynamicEvent | None:
        for event in self.active_dynamic_events:
            if not event.resolved and (kind is None or event.kind == kind):
                return event
        return None

    def dynamic_event_for_survivor(self, survivor: Survivor, kind: str | None = None) -> DynamicEvent | None:
        for event in self.active_dynamic_events:
            if event.resolved:
                continue
            if event.target_name == survivor.name and (kind is None or event.kind == kind):
                return event
        return None

    def dynamic_event_summary(self) -> str | None:
        event = self.active_dynamic_event()
        if not event:
            return None
        if event.kind == "faccao":
            humane = dict(event.data.get("humane", {}))
            hardline = dict(event.data.get("hardline", {}))
            return f"{self.faction_label(str(event.data.get('faction', 'andarilhos')))}: E {humane.get('title', 'negociar')}  |  Q {hardline.get('title', 'impor')}  |  {max(0, int(event.timer))}s"
        if event.kind == "expedicao":
            return f"Expedicao pede socorro: va ate o sinal vermelho e use E  |  {max(0, int(event.timer))}s"
        return f"{event.label} - {max(0, int(event.timer))}s"

    def zone_boss_for_region(self, region_key: tuple[int, int]) -> Zombie | None:
        for zombie in self.zombies:
            if zombie.is_alive() and getattr(zombie, "is_boss", False) and getattr(zombie, "zone_key", ()) == region_key:
                return zombie
        return None

    def current_named_region(self) -> dict[str, object] | None:
        return self.named_region_at(self.player.pos)

    def expedition_provision_cost(self) -> dict[str, int]:
        phase = self.economy_phase_key()
        if phase == "early":
            return {"food": 1}
        if phase == "mid":
            return {"food": 1, "meals": 1}
        return {"food": 2, "meals": 1}

    def is_survivor_on_expedition(self, survivor: Survivor) -> bool:
        return bool(getattr(survivor, "on_expedition", False))

    def expedition_members(self) -> list[Survivor]:
        if not self.active_expedition:
            return []
        member_names = set(self.active_expedition.get("members", []))
        return [survivor for survivor in self.survivors if survivor.is_alive() and survivor.name in member_names]

    def expedition_visible_members(self) -> list[Survivor]:
        expedition = self.active_expedition
        if not expedition:
            return []
        visible = self.expedition_caravan_state() is not None or str(expedition.get("skirmish_state", "")) in {"active", "resolved", "failed"}
        return self.expedition_members() if visible else []

    def expedition_member_anchor(self, survivor: Survivor) -> Vector2:
        expedition = self.active_expedition
        if not expedition:
            return Vector2(self.radio_pos)
        members = self.expedition_members()
        if survivor not in members:
            return Vector2(self.radio_pos)
        index = members.index(survivor)
        caravan = self.expedition_caravan_state()
        if caravan is not None:
            start = Vector2(self.radio_pos)
            edge = self.expedition_route_edge_point(expedition)
            direction = (edge - start)
            if direction.length_squared() <= 0.01:
                direction = Vector2(1, 0)
            else:
                direction = direction.normalize()
            lateral = Vector2(-direction.y, direction.x)
            if caravan["phase"] == "outbound":
                center = start.lerp(edge, float(caravan["progress"]) * 0.72)
            else:
                center = edge.lerp(start, float(caravan["progress"]) * 0.72)
            row_offset = Vector2(-direction.x, -direction.y) * (16 * index)
            side_offset = lateral * ((index - (len(members) - 1) * 0.5) * 14)
            return center + row_offset + side_offset
        skirmish_pos = expedition.get("skirmish_pos")
        if skirmish_pos is not None:
            center = Vector2(skirmish_pos)
            angle = index / max(1, len(members)) * math.tau
            return center + angle_to_vector(angle) * (24 + (index % 2) * 10)
        return Vector2(self.radio_pos)

    def nearest_downed_expedition_member(self, pos: Vector2, max_distance: float = 86.0) -> Survivor | None:
        downed = [
            survivor
            for survivor in self.expedition_visible_members()
            if getattr(survivor, "expedition_downed", False) and survivor.pos.distance_to(pos) <= max_distance
        ]
        if not downed:
            return None
        return min(downed, key=lambda survivor: survivor.pos.distance_to(pos))

    def revive_expedition_member(self, survivor: Survivor) -> None:
        survivor.expedition_downed = False
        survivor.health = clamp(max(22.0, survivor.health + 12), 0, survivor.max_health)
        survivor.energy = clamp(survivor.energy - 4, 0, 100)
        survivor.morale = clamp(survivor.morale + 4, 0, 100)
        survivor.state_label = "de pe na trilha"
        self.adjust_trust(survivor, 3.2)
        self.spawn_floating_text("levantou", survivor.pos, PALETTE["heal"])

    def update_expedition_members(self, dt: float) -> None:
        expedition = self.active_expedition
        if not expedition:
            return
        members = self.expedition_members()
        if not members:
            return
        expedition_zombies = [
            zombie
            for zombie in self.zombies
            if zombie.is_alive()
            and getattr(zombie, "expedition_skirmish", False)
            and (expedition.get("skirmish_pos") is None or zombie.pos.distance_to(Vector2(expedition["skirmish_pos"])) < 260)
        ]
        for survivor in members:
            survivor.expedition_attack_cooldown = max(0.0, getattr(survivor, "expedition_attack_cooldown", 0.0) - dt)
            anchor = self.expedition_member_anchor(survivor)
            if survivor.expedition_downed:
                survivor.pos = Vector2(anchor)
                survivor.state_label = "caido na trilha"
                continue
            state = str(expedition.get("skirmish_state", "idle"))
            if state == "active" and expedition_zombies:
                target = min(expedition_zombies, key=lambda zombie: zombie.pos.distance_to(survivor.pos))
                if survivor.pos.distance_to(target.pos) > 54:
                    survivor.move_toward(target.pos, dt, 0.9)
                elif survivor.expedition_attack_cooldown <= 0:
                    hit = 14 + (4 if survivor.role in {"batedora", "vigia"} else 0)
                    if survivor.has_trait("corajoso"):
                        hit += 3
                    target.health -= hit
                    target.stagger = 0.12
                    survivor.expedition_attack_cooldown = 0.82
                    self.damage_pulses.append(DamagePulse(Vector2(target.pos), 10, 0.18, PALETTE["accent_soft"]))
                survivor.state_label = "segurando a trilha"
            else:
                survivor.pos = survivor.pos.lerp(anchor, min(1.0, dt * 4.2))
                survivor.state_label = "em coluna" if self.expedition_caravan_state() is not None else "reagrupando"

            if survivor.health <= 18 and not survivor.expedition_downed:
                survivor.health = clamp(survivor.health, 10, survivor.max_health)
                survivor.expedition_downed = True
                survivor.state_label = "caido na trilha"
                self.spawn_floating_text("caido", survivor.pos, PALETTE["danger_soft"])

    def expedition_candidate_survivors(self) -> list[Survivor]:
        available = [
            survivor
            for survivor in self.survivors
            if survivor.is_alive()
            and not self.is_survivor_on_expedition(survivor)
            and self.dynamic_event_for_survivor(survivor) is None
            and survivor.health > 54
            and survivor.energy > 44
            and getattr(survivor, "exhaustion", 0.0) < 70
        ]
        role_priority = {"batedora": 0, "mensageiro": 1, "vigia": 2, "lenhador": 3, "artesa": 4, "cozinheiro": 5}
        available.sort(
            key=lambda survivor: (
                role_priority.get(survivor.role, 99),
                -(survivor.energy + survivor.health * 0.6 + survivor.morale * 0.35),
                survivor.name,
            )
        )
        return available

    def best_expedition_region(self) -> dict[str, object] | None:
        candidates = [
            region
            for region in self.named_regions.values()
            if int(region.get("expedition_sites", 0)) > 0 and Vector2(region["anchor"]).distance_to(CAMP_CENTER) > self.camp_clearance_radius() + 180
        ]
        if not candidates:
            return None
        phase = self.economy_phase_key()
        best_region: dict[str, object] | None = None
        best_score = -9999.0
        for region in candidates:
            distance = Vector2(region["anchor"]).distance_to(CAMP_CENTER)
            reward_bundle = dict(region.get("expedition_bundle", {}))
            reward_score = sum(int(value) for value in reward_bundle.values())
            reward_score += 2 if reward_bundle.get("medicine", 0) else 0
            reward_score += 1 if reward_bundle.get("meals", 0) else 0
            danger = float(region.get("expedition_danger", 0.35))
            if region.get("boss_blueprint") and not region.get("boss_defeated"):
                danger += 0.18
            if phase == "early":
                score = reward_score * 1.2 - danger * 11.0 - distance / 210
            elif phase == "mid":
                score = reward_score * 1.6 - danger * 8.8 - distance / 290
            else:
                score = reward_score * 2.0 - danger * 7.4 - distance / 360
            if region.get("boss_blueprint") and not region.get("boss_defeated") and phase != "late":
                score -= 2.4
            if score > best_score:
                best_score = score
                best_region = region
        return best_region

    def expedition_status_text(self, *, short: bool = False) -> str | None:
        expedition = self.active_expedition
        if not expedition:
            return None
        region_name = str(expedition["region_name"])
        members = ", ".join(str(name) for name in expedition["members"])
        timer = max(0, int(float(expedition["timer"])))
        if str(expedition.get("skirmish_state", "")) == "active":
            if short:
                return f"caravana em combate {timer}s"
            return f"Caravana em combate na trilha de {region_name}. Equipe: {members}. Retorno em {timer}s."
        if short:
            return f"expedicao {region_name} {timer}s"
        if bool(expedition.get("recall_ordered", False)):
            return f"Expedicao recolhendo de {region_name}. Equipe: {members}. Retorno em {timer}s."
        return f"Expedicao em {region_name}. Equipe: {members}. Retorno em {timer}s."

    def expedition_route_direction(self, expedition: dict[str, object] | None = None) -> Vector2:
        expedition = expedition or self.active_expedition
        if not expedition:
            return Vector2(1, 0)
        region = self.named_regions.get(tuple(expedition["region_key"]))
        anchor = Vector2(region["anchor"]) if region else Vector2(CAMP_CENTER + Vector2(1, 0))
        direction = anchor - self.radio_pos
        if direction.length_squared() <= 0.01:
            direction = Vector2(1, 0)
        else:
            direction = direction.normalize()
        return direction

    def expedition_route_edge_point(self, expedition: dict[str, object] | None = None) -> Vector2:
        direction = self.expedition_route_direction(expedition)
        return Vector2(self.radio_pos) + direction * (self.camp_clearance_radius() + 138)

    def expedition_caravan_state(self) -> dict[str, object] | None:
        expedition = self.active_expedition
        if not expedition:
            return None
        departure_window = float(expedition.get("departure_window", 7.0))
        return_window = float(expedition.get("return_window", 8.0))
        elapsed = float(expedition["duration"]) - float(expedition["timer"])
        if elapsed < departure_window:
            return {"phase": "outbound", "progress": clamp(elapsed / max(0.1, departure_window), 0.0, 1.0), "dir": self.expedition_route_direction(expedition)}
        if float(expedition["timer"]) < return_window:
            progress = 1.0 - float(expedition["timer"]) / max(0.1, return_window)
            return {"phase": "inbound", "progress": clamp(progress, 0.0, 1.0), "dir": self.expedition_route_direction(expedition)}
        return None

    def expedition_distress_pos(self, expedition: dict[str, object] | None = None) -> Vector2:
        expedition = expedition or self.active_expedition
        direction = self.expedition_route_direction(expedition)
        lateral = Vector2(-direction.y, direction.x)
        seed_angle = self.hash_noise(int(direction.x * 1000), int(direction.y * 1000), 211) - 0.5
        return self.expedition_route_edge_point(expedition) + lateral * (40 + seed_angle * 42)

    def expedition_skirmish_pos(self, expedition: dict[str, object] | None = None) -> Vector2:
        expedition = expedition or self.active_expedition
        direction = self.expedition_route_direction(expedition)
        lateral = Vector2(-direction.y, direction.x)
        seed_angle = self.hash_noise(int(direction.x * 1000), int(direction.y * 1200), 223) - 0.5
        return self.expedition_route_edge_point(expedition) + direction * 94 + lateral * (62 * seed_angle)

    def spawn_expedition_skirmish(self, pos: Vector2, count: int) -> None:
        for _ in range(count):
            angle = self.random.uniform(0, math.tau)
            distance = self.random.uniform(90, 170)
            spawn_pos = pos + angle_to_vector(angle) * distance
            zombie = Zombie(spawn_pos, self.day)
            zombie.anchor = Vector2(pos)
            zombie.camp_pressure = clamp(0.58 + pos.distance_to(CAMP_CENTER) / 1100, 0.35, 0.95)
            zombie.expedition_skirmish = True
            self.zombies.append(zombie)

    def launch_best_expedition(self) -> tuple[bool, str]:
        if self.active_expedition:
            return False, "Ja existe uma expedicao longe da base."
        if self.is_night:
            return False, "Expedicoes so saem com luz de dia."
        target_region = self.best_expedition_region()
        if not target_region:
            return False, "Nenhuma regiao conhecida ainda guarda saque raro."
        candidates = self.expedition_candidate_survivors()
        team_size = 2 if self.economy_phase_key() != "late" else 3
        if len(candidates) - team_size < 2:
            return False, "A base precisa manter gente suficiente dentro do quadrado."
        members = candidates[:team_size]
        provision_cost = self.expedition_provision_cost()
        if not self.consume_resource_bundle(provision_cost):
            return False, "Faltam racoes para abastecer a expedicao."

        distance = Vector2(target_region["anchor"]).distance_to(CAMP_CENTER)
        duration = 42.0 + distance / 120 + float(target_region.get("expedition_danger", 0.35)) * 20
        duration += self.weather_precipitation_factor() * 8.0
        duration += self.weather_wind_factor() * 4.0
        duration += self.weather_mist_factor() * 3.0
        duration += self.weather_storm_factor() * 6.0
        target_region["expedition_sites"] = max(0, int(target_region.get("expedition_sites", 1)) - 1)

        for survivor in members:
            survivor.on_expedition = True
            survivor.state = "expedition"
            survivor.state_label = "em expedicao"
            survivor.velocity *= 0.0
            survivor.pos = Vector2(self.radio_pos)

        self.active_expedition = {
            "region_key": tuple(target_region["key"]),
            "region_name": str(target_region["name"]),
            "region_biome": str(target_region["biome"]),
            "members": [survivor.name for survivor in members],
            "timer": duration,
            "duration": duration,
            "danger": float(target_region.get("expedition_danger", 0.35)),
            "loot_bundle": dict(target_region.get("expedition_bundle", {})),
            "loot_label": str(target_region.get("expedition_label", "saque raro")),
            "recall_ordered": False,
            "provision_cost": provision_cost,
            "departure_window": 7.0,
            "return_window": 8.0,
            "distress_checked": False,
            "distress_resolved": False,
            "escort_bonus": False,
            "skirmish_state": "idle",
            "skirmish_pos": None,
            "skirmish_timer": 0.0,
        }
        names = ", ".join(member.name for member in members)
        self.set_event_message(f"Expedicao saiu para {target_region['name']} atras de {target_region['expedition_label']}. Equipe: {names}.", duration=6.4)
        self.spawn_floating_text("expedicao saiu", self.radio_pos, PALETTE["accent_soft"])
        return True, f"Equipe a caminho de {target_region['name']}."

    def recall_active_expedition(self) -> tuple[bool, str]:
        expedition = self.active_expedition
        if not expedition:
            return False, "Nao ha expedicao para recolher."
        if bool(expedition.get("recall_ordered", False)):
            return False, "A equipe ja esta voltando."
        expedition["recall_ordered"] = True
        expedition["timer"] = min(float(expedition["timer"]), 14.0 + float(expedition["danger"]) * 8.0)
        self.set_event_message(f"Ordem de recolha enviada para {expedition['region_name']}.", duration=5.4)
        self.spawn_floating_text("recolher equipe", self.radio_pos, PALETTE["morale"])
        return True, "A equipe recebeu a ordem de retorno."

    def resolve_active_expedition(self) -> None:
        expedition = self.active_expedition
        if not expedition:
            return
        members = [survivor for survivor in self.survivors if survivor.name in expedition["members"] and survivor.is_alive()]
        if not members:
            self.active_expedition = None
            return

        region = self.named_regions.get(tuple(expedition["region_key"]))
        danger = float(expedition["danger"])
        if region and region.get("boss_blueprint") and not region.get("boss_defeated"):
            danger += 0.18
        danger += self.weather_precipitation_factor() * 0.1
        danger += self.weather_wind_factor() * 0.05
        danger += self.weather_mist_factor() * 0.04
        danger += self.weather_storm_factor() * 0.08
        if expedition.get("recall_ordered", False):
            danger += 0.08

        team_power = 0.0
        for survivor in members:
            team_power += survivor.health * 0.34 + survivor.energy * 0.28 + survivor.morale * 0.18 + survivor.trust_leader * 0.2
            if survivor.role in {"batedora", "mensageiro"}:
                team_power += 8
            if survivor.has_trait("corajoso"):
                team_power += 5
            if survivor.has_trait("paranoico"):
                team_power -= 3
        team_power = team_power / max(1, len(members) * 100)
        hazard_roll = self.random.random()
        severe_threshold = clamp(0.22 + danger * 0.28 - team_power * 0.16, 0.05, 0.34)
        moderate_threshold = clamp(severe_threshold + 0.26 + danger * 0.22 - team_power * 0.12, 0.24, 0.74)

        loot_bundle = dict(expedition["loot_bundle"])
        outcome_label = "voltou inteira"
        downed_members = [survivor for survivor in members if getattr(survivor, "expedition_downed", False)]
        if hazard_roll < severe_threshold:
            lost = min(
                downed_members or members,
                key=lambda survivor: (
                    survivor.health + survivor.energy * 0.7 + survivor.morale * 0.5,
                    survivor.name,
                ),
            )
            lost.on_expedition = False
            lost.expedition_downed = False
            self.remove_survivor(lost)
            loot_bundle = {key: max(0, int(value * 0.45)) for key, value in loot_bundle.items()}
            for survivor in members:
                if survivor is lost:
                    continue
                survivor.on_expedition = False
                survivor.expedition_downed = False
                survivor.pos = Vector2(self.radio_pos) + Vector2(self.random.uniform(-22, 22), self.random.uniform(-18, 18))
                survivor.health = clamp(survivor.health - 18, 0, survivor.max_health)
                survivor.energy = clamp(survivor.energy - 22, 0, 100)
                survivor.morale = clamp(survivor.morale - 12, 0, 100)
                survivor.insanity = clamp(survivor.insanity + 10, 0, 100)
                survivor.state_label = "voltou da mata"
            self.set_event_message(f"A expedicao voltou quebrada de {expedition['region_name']}. {lost.name} nao retornou.", duration=7.0)
            self.spawn_floating_text("expedicao ferida", self.radio_pos, PALETTE["danger_soft"])
            outcome_label = "perdeu gente"
        elif hazard_roll < moderate_threshold:
            loot_bundle = {key: max(0, int(value * 0.72)) for key, value in loot_bundle.items()}
            for survivor in members:
                survivor.on_expedition = False
                survivor.expedition_downed = False
                survivor.pos = Vector2(self.radio_pos) + Vector2(self.random.uniform(-22, 22), self.random.uniform(-18, 18))
                survivor.health = clamp(survivor.health - 12, 0, survivor.max_health)
                survivor.energy = clamp(survivor.energy - 18, 0, 100)
                survivor.morale = clamp(survivor.morale - 7, 0, 100)
                survivor.insanity = clamp(survivor.insanity + 6, 0, 100)
                survivor.state_label = "voltou ferido"
            self.set_event_message(f"A expedicao apanhou em {expedition['region_name']}, mas voltou com parte do saque.", duration=6.4)
            self.spawn_floating_text("retorno pesado", self.radio_pos, PALETTE["danger_soft"])
            outcome_label = "voltou ferida"
        else:
            if expedition.get("recall_ordered", False):
                loot_bundle = {key: max(0, int(value * 0.68)) for key, value in loot_bundle.items()}
            bonus_key = "medicine" if expedition["region_biome"] in {"swamp", "ruin"} else "scrap"
            loot_bundle[bonus_key] = loot_bundle.get(bonus_key, 0) + 1
            for survivor in members:
                survivor.on_expedition = False
                survivor.expedition_downed = False
                survivor.pos = Vector2(self.radio_pos) + Vector2(self.random.uniform(-22, 22), self.random.uniform(-18, 18))
                survivor.energy = clamp(survivor.energy - 10, 0, 100)
                survivor.morale = clamp(survivor.morale + 4, 0, 100)
                survivor.trust_leader = clamp(survivor.trust_leader + 2, 0, 100)
                survivor.state_label = "voltou da expedicao"
            self.set_event_message(f"A equipe voltou de {expedition['region_name']} com {expedition['loot_label']}.", duration=6.6)
            self.spawn_floating_text("expedicao voltou", self.radio_pos, PALETTE["morale"])

        stored = self.add_resource_bundle(loot_bundle)
        if stored:
            self.spawn_floating_text(self.bundle_summary(stored), self.stockpile_pos, PALETTE["accent_soft"])
        if region is not None:
            region["expedition_last_outcome"] = outcome_label
        self.active_expedition = None
        self.assign_building_specialists()

    def update_active_expedition(self, dt: float) -> None:
        expedition = self.active_expedition
        if not expedition:
            return
        self.update_expedition_members(dt)
        elapsed = float(expedition["duration"]) - float(expedition["timer"])
        departure_window = float(expedition.get("departure_window", 7.0))
        if (
            not bool(expedition.get("escort_bonus", False))
            and elapsed <= departure_window + 2.5
            and self.player.pos.distance_to(self.expedition_route_edge_point(expedition)) < 160
        ):
            expedition["escort_bonus"] = True
            expedition["danger"] = clamp(float(expedition["danger"]) - 0.08, 0.12, 0.95)
            for survivor in self.survivors:
                if survivor.name in expedition["members"]:
                    survivor.trust_leader = clamp(survivor.trust_leader + 2.0, 0, 100)
                    survivor.morale = clamp(survivor.morale + 2.0, 0, 100)
            self.set_event_message("Voce escoltou a coluna ate a borda da clareira. A equipe partiu mais segura.", duration=5.4)
            self.spawn_floating_text("coluna coberta", self.expedition_route_edge_point(expedition), PALETTE["heal"])

        if (
            str(expedition.get("skirmish_state", "idle")) == "idle"
            and elapsed >= departure_window * 0.62
            and float(expedition["timer"]) > float(expedition.get("return_window", 8.0)) + 12.0
        ):
            skirmish_pos = self.expedition_skirmish_pos(expedition)
            expedition["skirmish_state"] = "active"
            expedition["skirmish_pos"] = Vector2(skirmish_pos)
            expedition["skirmish_timer"] = 20.0 + float(expedition["danger"]) * 8.0
            wave_size = 3 + int(float(expedition["danger"]) * 3.2)
            self.spawn_expedition_skirmish(skirmish_pos, wave_size)
            self.set_event_message(f"A coluna trombou mortos na trilha de {expedition['region_name']}.", duration=5.8)
            self.spawn_floating_text("contato na trilha", skirmish_pos, PALETTE["danger_soft"])

        expedition["timer"] = float(expedition["timer"]) - dt
        if str(expedition.get("skirmish_state", "")) == "active":
            expedition["skirmish_timer"] = float(expedition.get("skirmish_timer", 0.0)) - dt
            skirmish_pos = Vector2(expedition["skirmish_pos"]) if expedition.get("skirmish_pos") is not None else self.expedition_skirmish_pos(expedition)
            living_zombies = [
                zombie
                for zombie in self.zombies
                if zombie.is_alive()
                and getattr(zombie, "expedition_skirmish", False)
                and zombie.pos.distance_to(skirmish_pos) < 240
            ]
            if not living_zombies:
                expedition["skirmish_state"] = "resolved"
                expedition["danger"] = clamp(float(expedition["danger"]) - 0.12, 0.1, 0.95)
                expedition["timer"] = max(8.0, float(expedition["timer"]) - 4.0)
                loot_bundle = dict(expedition.get("loot_bundle", {}))
                bonus_key = "scrap" if expedition["region_biome"] in {"ruin", "quarry", "ashland"} else "food"
                loot_bundle[bonus_key] = loot_bundle.get(bonus_key, 0) + 1
                expedition["loot_bundle"] = loot_bundle
                self.set_event_message(f"A caravana venceu a escaramuca e retomou a trilha de {expedition['region_name']}.", duration=5.8)
                self.spawn_floating_text("rota limpa", skirmish_pos, PALETTE["heal"])
            elif float(expedition.get("skirmish_timer", 0.0)) <= 0:
                expedition["skirmish_state"] = "failed"
                expedition["danger"] = clamp(float(expedition["danger"]) + 0.12, 0.18, 1.0)
                for survivor in self.survivors:
                    if survivor.name in expedition["members"]:
                        survivor.health = clamp(survivor.health - 8, 0, survivor.max_health)
                        survivor.energy = clamp(survivor.energy - 12, 0, 100)
                        survivor.morale = clamp(survivor.morale - 6, 0, 100)
                self.set_event_message(f"A caravana apanhou sozinha na trilha de {expedition['region_name']}.", duration=5.8)
                self.spawn_floating_text("coluna ferida", skirmish_pos, PALETTE["danger_soft"])

        distress_threshold = float(expedition["duration"]) * 0.46
        can_spawn_distress = (
            not bool(expedition.get("distress_checked", False))
            and elapsed >= distress_threshold
            and float(expedition["timer"]) > float(expedition.get("return_window", 8.0)) + 6.0
        )
        if can_spawn_distress:
            expedition["distress_checked"] = True
            distress_chance = 0.28 + float(expedition["danger"]) * 0.62
            distress_chance += self.weather_precipitation_factor() * 0.12
            distress_chance += self.weather_mist_factor() * 0.04
            distress_chance += self.weather_storm_factor() * 0.08
            if self.random.random() < distress_chance and not self.active_dynamic_events:
                distress_pos = self.expedition_distress_pos(expedition)
                self.spawn_dynamic_event(
                    "expedicao",
                    f"Socorro de expedicao: foguete vermelho riscou a trilha para {expedition['region_name']}.",
                    distress_pos,
                    timer=30.0,
                    urgency=0.78,
                    data={"expedition_region": expedition["region_name"]},
                )
        if expedition["timer"] <= 0:
            self.resolve_active_expedition()

    def zone_boss_status_text(self, region: dict[str, object] | None, *, short: bool = False) -> str:
        if not region:
            return "centro seguro"
        blueprint = region.get("boss_blueprint")
        if not blueprint:
            return "sem boss" if short else "Nenhum boss domina esta zona."
        boss_name = str(blueprint["name"])
        if region.get("boss_defeated"):
            return "boss abatido" if short else f"{boss_name} foi abatido nesta zona."
        boss = self.zone_boss_for_region(tuple(region["key"]))
        if boss:
            return f"{boss_name} ativo" if short else f"{boss_name} esta ativo em {region['name']}."
        return f"{boss_name} a espreita" if short else f"{boss_name} ainda ronda {region['name']}."

    def ensure_zone_boss_near_player(self) -> None:
        region = self.current_named_region()
        if not region or not region.get("boss_blueprint") or region.get("boss_defeated"):
            return
        if self.zone_boss_for_region(tuple(region["key"])):
            region["boss_active"] = True
            return
        living_bosses = [zombie for zombie in self.zombies if zombie.is_alive() and getattr(zombie, "is_boss", False)]
        if len(living_bosses) >= 2:
            return
        anchor = Vector2(region["anchor"])
        if self.player.pos.distance_to(anchor) > 430:
            return
        spawn_radius = 96 + self.hash_noise(int(anchor.x // 13), int(anchor.y // 13), 163) * 54
        spawn_pos = self.safe_zombie_spawn_position(anchor, spawn_radius, spawn_radius + 42)
        boss = Zombie(spawn_pos, self.day, boss_profile=dict(region["boss_blueprint"]))
        self.zombies.append(boss)
        region["boss_spawned"] = True
        region["boss_active"] = True
        self.spawn_floating_text(str(region["boss_blueprint"]["name"]).lower(), boss.pos, PALETTE["danger_soft"])
        self.set_event_message(f"{region['boss_blueprint']['name']} despertou em {region['name']}.")
        self.audio.play_alert(source_pos=boss.pos)

    def resolve_defeated_zone_bosses(self) -> None:
        for zombie in self.zombies:
            if zombie.is_alive() or not getattr(zombie, "is_boss", False) or getattr(zombie, "death_processed", False):
                continue
            zombie.death_processed = True
            region_key = tuple(getattr(zombie, "zone_key", ()))
            region = self.named_regions.get(region_key)
            if region:
                region["boss_defeated"] = True
                region["boss_active"] = False
            reward = {"scrap": 3, "medicine": 1}
            biome = str(region["biome"]) if region else "forest"
            if biome == "swamp":
                reward["herbs"] = 2
            elif biome == "ashland":
                reward["wood"] = 3
            elif biome == "quarry":
                reward["scrap"] = 5
            elif biome == "redwood":
                reward["logs"] = 4
            elif biome == "meadow":
                reward["meals"] = 2
            self.add_resource_bundle(reward)
            for survivor in self.living_survivors():
                survivor.morale = clamp(survivor.morale + 8, 0, 100)
                self.adjust_trust(survivor, 2.0)
            self.spawn_floating_text(f"{zombie.boss_name.lower()} caiu", zombie.pos, PALETTE["morale"])
            self.spawn_floating_text(self.bundle_summary(reward), zombie.pos + Vector2(0, -22), PALETTE["accent_soft"])
            if region:
                self.set_event_message(f"{zombie.boss_name} caiu em {region['name']}. A zona cedeu recursos raros ao campo.", duration=6.6)

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
        event = DynamicEvent(
            uid=self.next_dynamic_event_uid,
            kind=kind,
            label=label,
            pos=Vector2(pos),
            timer=timer,
            urgency=urgency,
            target_name=target_name,
            building_uid=building_uid,
            data=data or {},
        )
        self.next_dynamic_event_uid += 1
        self.active_dynamic_events = [event]
        self.dynamic_event_cooldown = self.random.uniform(18.0, 30.0)
        self.set_event_message(label, duration=max(5.0, min(8.0, timer * 0.5)))
        self.spawn_floating_text(label.lower(), pos, PALETTE["danger_soft"] if urgency > 0.55 else PALETTE["morale"])
        if kind in {"incendio", "alarme", "expedicao", "fuga", "desercao"}:
            burst_color = PALETTE["danger_soft"] if kind != "expedicao" else PALETTE["accent_soft"]
            self.impact_burst(pos, burst_color, radius=12, shake=0.7, ember_count=2, smoky=kind == "incendio")
        self.survivors_react_to_event(event)
        return event

    def choose_fire_site(self) -> tuple[Vector2, str, int | None, str]:
        if self.buildings:
            building = self.random.choice(self.buildings)
            return Vector2(building.pos), str(building.kind), building.uid, str(building.kind)
        core_sites = [
            (self.stockpile_pos, "stockpile", None, "estoque"),
            (self.kitchen_pos, "kitchen", None, "fogao"),
            (self.workshop_pos, "workshop", None, "oficina"),
        ]
        pos, site_kind, uid, label = self.random.choice(core_sites)
        return Vector2(pos), site_kind, uid, label

    def roadside_event_pos(self, *, side: str | None = None) -> Vector2:
        """Escolhe um ponto aleatorio nas laterais do acampamento para encontros humanos."""
        side = side or self.random.choice(("north", "south", "east", "west"))
        margin = 118.0
        lateral_jitter = self.random.uniform(-96, 96)
        if side == "north":
            return CAMP_CENTER + Vector2(lateral_jitter, -(self.camp_half_size + margin))
        if side == "south":
            return CAMP_CENTER + Vector2(lateral_jitter, self.camp_half_size + margin)
        if side == "east":
            return CAMP_CENTER + Vector2(self.camp_half_size + margin, lateral_jitter)
        return CAMP_CENTER + Vector2(-(self.camp_half_size + margin), lateral_jitter)

    def dynamic_event_candidates(self) -> list[tuple[str, float, dict[str, object]]]:
        living = self.living_survivors()
        if not living:
            return []

        candidates: list[tuple[str, float, dict[str, object]]] = []
        if self.spare_beds() > 0 and self.next_recruit_index < len(self.recruit_pool) and self.average_morale() > 48 and self.average_trust() > 42:
            profile = self.recruit_pool[self.next_recruit_index]
            outsider_pos = self.roadside_event_pos()
            candidates.append(
                (
                    "abrigo",
                    0.32 + self.camp_level * 0.05,
                    {
                        "pos": outsider_pos,
                        "profile": profile,
                        "visitor": {
                            "name": str(profile["name"]),
                            "title": "forasteiro",
                            "body": (144, 154, 132),
                            "accent": (112, 124, 98),
                            "prop": "bag",
                        },
                    },
                )
            )

        disease_target = max(living, key=lambda survivor: survivor.exhaustion + (100 - survivor.health))
        if (self.weather_precipitation_factor() > 0.26 or self.weather_mist_factor() > 0.34 or self.herbs <= 1 or self.average_health() < 74) and not self.dynamic_event_for_survivor(disease_target):
            severity = clamp((disease_target.exhaustion - 40) / 40, 0.0, 1.0)
            candidates.append(("doenca", 0.34 + severity * 0.24, {"target": disease_target}))

        if (self.weather_wind_factor() > 0.34 or self.weather_storm_factor() > 0.3 or self.bonfire_stage() == "alta") and (self.buildings or self.wood + self.logs > 12):
            fire_pos, site_kind, building_uid, site_label = self.choose_fire_site()
            candidates.append(
                (
                    "incendio",
                    0.26 + self.weather_wind_factor() * 0.16 + self.weather_storm_factor() * 0.22,
                    {"pos": fire_pos, "site_kind": site_kind, "building_uid": building_uid, "site_label": site_label},
                )
            )

        if self.is_night and self.barricades and (self.weakest_barricade_health() < 68 or len(self.zombies) >= 4 or getattr(self, "horde_active", False)):
            weakest = min(self.barricades, key=lambda barricade: barricade.health / max(1.0, barricade.max_health))
            candidates.append(
                (
                    "alarme",
                    0.24 + (1.0 - weakest.health / max(1.0, weakest.max_health)) * 0.4 + (0.18 if getattr(self, "horde_active", False) else 0.0),
                    {"pos": Vector2(weakest.pos), "angle": weakest.angle},
                )
            )

        low_trust = min(living, key=lambda survivor: (survivor.trust_leader, survivor.morale))
        if low_trust.trust_leader < 38 or (low_trust.morale < 34 and low_trust.exhaustion > 56):
            exit_pos = CAMP_CENTER + Vector2(-self.camp_half_size - 94, self.random.uniform(-64, 64))
            candidates.append(("fuga", 0.34 + max(0.0, 38 - low_trust.trust_leader) * 0.008, {"target": low_trust, "pos": exit_pos}))

        deserter = min(living, key=lambda survivor: (survivor.trust_leader + survivor.morale * 0.4, survivor.energy))
        if self.average_trust() < 42 and (self.feud_count() > 0 or self.average_morale() < 46) and deserter.trust_leader < 30:
            exit_pos = CAMP_CENTER + Vector2(self.camp_half_size + 108, self.random.uniform(-80, 80))
            candidates.append(("desercao", 0.24 + max(0.0, 30 - deserter.trust_leader) * 0.01, {"target": deserter, "pos": exit_pos}))

        faction_pool = [
            key
            for key, score in self.faction_standings.items()
            if abs(score) < 72
        ]
        if faction_pool and self.day >= 2 and self.average_trust() > 26:
            faction_key = self.random.choice(faction_pool)
            roadside_pos = self.roadside_event_pos()
            faction_visuals = {
                "andarilhos": {"name": "andarilhos", "title": "familia cansada", "body": (158, 170, 126), "accent": (112, 124, 84), "prop": "bag"},
                "ferro-velho": {"name": "ferro-velho", "title": "comerciante de sucata", "body": (146, 126, 104), "accent": (112, 98, 82), "prop": "crate"},
                "vigias_da_estrada": {"name": "vigias", "title": "patrulha armada", "body": (126, 138, 154), "accent": (84, 96, 118), "prop": "pole"},
            }
            candidates.append(
                (
                    "faccao",
                    0.22 + self.camp_level * 0.04 + max(0.0, self.average_trust() - 40) * 0.002,
                    {"faction": faction_key, "pos": roadside_pos, "visitor": dict(faction_visuals[faction_key])},
                )
            )

        return candidates

    def maybe_spawn_dynamic_event(self) -> None:
        if self.active_dynamic_events or self.dynamic_event_cooldown > 0:
            return
        candidates = self.dynamic_event_candidates()
        if not candidates:
            self.dynamic_event_cooldown = self.random.uniform(8.0, 14.0)
            return

        total_weight = sum(weight for _, weight, _ in candidates)
        roll = self.random.uniform(0, total_weight)
        chosen_kind = candidates[-1]
        running = 0.0
        for candidate in candidates:
            running += candidate[1]
            if roll <= running:
                chosen_kind = candidate
                break

        kind, _, payload = chosen_kind
        if kind == "abrigo":
            profile = payload["profile"]
            self.spawn_dynamic_event(
                "abrigo",
                f"Pedido de abrigo: {profile['name']} espera no limite da mata.",
                Vector2(payload["pos"]),
                timer=28.0,
                urgency=0.32,
                data={"profile": profile},
            )
        elif kind == "doenca":
            target: Survivor = payload["target"]
            self.spawn_dynamic_event(
                "doenca",
                f"Doenca: {target.name} caiu febril e precisa de cuidado.",
                Vector2(target.pos),
                timer=34.0,
                urgency=0.62,
                target_name=target.name,
            )
        elif kind == "incendio":
            self.spawn_dynamic_event(
                "incendio",
                f"Incendio: o {payload['site_label']} pegou fogo no acampamento.",
                Vector2(payload["pos"]),
                timer=24.0,
                urgency=0.84,
                building_uid=payload["building_uid"],
                data={"site_kind": payload["site_kind"], "site_label": payload["site_label"], "tick": 1.8},
            )
        elif kind == "fuga":
            target = payload["target"]
            self.spawn_dynamic_event(
                "fuga",
                f"Fuga: {target.name} entrou em panico e correu para fora do quadrado.",
                Vector2(payload["pos"]),
                timer=22.0,
                urgency=0.72,
                target_name=target.name,
            )
        elif kind == "desercao":
            target = payload["target"]
            self.spawn_dynamic_event(
                "desercao",
                f"Desercao: {target.name} arrumou a mochila e quer sumir pela trilha.",
                Vector2(payload["pos"]),
                timer=26.0,
                urgency=0.86,
                target_name=target.name,
            )
        elif kind == "faccao":
            faction = str(payload["faction"])
            pos = Vector2(payload["pos"])
            scenarios = {
                "andarilhos": {
                    "label": "Andarilhos pedem comida para uma familia ferida na trilha.",
                    "humane": {
                        "title": "Partilhar mantimentos",
                        "cost": {"meals": 2, "food": 1},
                        "reward": {"morale": 7, "trust": 4, "faction": 18, "future": {"medicine": 1}},
                        "message": "A clareira dividiu comida e os Andarilhos prometeram lembrar disso.",
                    },
                    "hardline": {
                        "title": "Cobrar sucata pela passagem",
                        "reward": {"scrap": 3, "faction": -16, "morale": -5, "trust": -6},
                        "message": "Voce fez negocio com a fome deles. O estoque cresceu, mas o boato correu.",
                    },
                },
                "ferro-velho": {
                    "label": "Ferro-Velho quer um acordo por uma carroca de metal raro.",
                    "humane": {
                        "title": "Troca justa",
                        "cost": {"food": 2},
                        "reward": {"scrap": 5, "faction": 14, "trust": 3, "morale": 2},
                        "message": "A troca foi limpa e o elo com Ferro-Velho ficou mais forte.",
                    },
                    "hardline": {
                        "title": "Tomar a carga na pressao",
                        "reward": {"scrap": 8, "faction": -20, "trust": -8, "morale": -4},
                        "message": "Voce arrancou a carga deles na pressao. Ganhou metal e perdeu palavra.",
                    },
                },
                "vigias_da_estrada": {
                    "label": "Os Vigias da Estrada capturaram um forasteiro e exigem sua posicao.",
                    "humane": {
                        "title": "Proteger o forasteiro",
                        "cost": {"wood": 2, "medicine": 1},
                        "reward": {"faction": -8, "trust": 8, "morale": 8, "future": {"survivor": True}},
                        "message": "Voce peitou os Vigias e puxou o ferido para dentro do anel do acampamento.",
                    },
                    "hardline": {
                        "title": "Entregar o homem e ganhar paz",
                        "reward": {"faction": 15, "trust": -12, "morale": -10, "food": 2},
                        "message": "Os Vigias sairam satisfeitos. O campo, nem tanto.",
                    },
                },
            }
            scenario = scenarios[faction]
            self.spawn_dynamic_event(
                "faccao",
                f"{self.faction_label(faction)}: {scenario['label']}",
                pos,
                timer=30.0,
                urgency=0.58,
                data={
                    "faction": faction,
                    "label": scenario["label"],
                    "humane": scenario["humane"],
                    "hardline": scenario["hardline"],
                },
            )
        elif kind == "alarme":
            angle = float(payload["angle"])
            if -0.75 <= angle <= 0.75:
                edge = "leste"
            elif 0.75 < angle < 2.35:
                edge = "sul"
            elif -2.35 < angle < -0.75:
                edge = "norte"
            else:
                edge = "oeste"
            self.spawn_dynamic_event(
                "alarme",
                f"Alarme: pancadas vieram da cerca {edge} e a linha tremeu.",
                Vector2(payload["pos"]),
                timer=20.0,
                urgency=0.78,
                data={"edge": edge, "tick": 1.2},
            )

    def resolve_dynamic_event(self, event: DynamicEvent, *, accepted: bool = True) -> bool:
        if event.resolved:
            return False

        if event.kind == "doenca":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if not target:
                event.resolved = True
                return False
            if self.medicine > 0:
                self.medicine -= 1
                target.health = clamp(target.health + 24, 0, target.max_health)
            elif self.herbs > 0:
                self.herbs -= 1
                target.health = clamp(target.health + 14, 0, target.max_health)
            else:
                self.set_event_message("A enfermaria esta sem remedios para tratar a febre.", duration=4.6)
                return False
            target.energy = clamp(target.energy + 8, 0, 100)
            target.morale = clamp(target.morale + 4, 0, 100)
            target.exhaustion = clamp(target.exhaustion - 12, 0, 100)
            self.adjust_trust(target, 2.8)
            self.set_event_message(f"{target.name} foi estabilizado na enfermaria.", duration=5.4)
            self.spawn_floating_text("febre contida", target.pos, PALETTE["heal"])

        elif event.kind == "incendio":
            self.set_event_message("O incendio foi contido antes de comer a estrutura.", duration=5.2)
            self.spawn_floating_text("fogo controlado", event.pos, PALETTE["heal"])
            self.impact_burst(event.pos, PALETTE["heal"], radius=16, shake=1.4, ember_count=10, smoky=True)

        elif event.kind == "alarme":
            nearest = self.closest_barricade(event.pos)
            if nearest:
                nearest.repair(10)
            for zombie in self.zombies:
                if zombie.pos.distance_to(event.pos) < 140:
                    zombie.stagger = max(zombie.stagger, 0.16)
                    zombie.health -= 8
            for survivor in self.living_survivors():
                if survivor.distance_to(event.pos) < 220:
                    survivor.morale = clamp(survivor.morale + 2.0, 0, 100)
                    self.adjust_trust(survivor, 1.8)
            self.set_event_message(f"Voce respondeu ao alarme da cerca {event.data.get('edge', 'externa')} e a linha segurou.", duration=5.6)
            self.spawn_floating_text("linha segurou", event.pos, PALETTE["heal"])
            self.impact_burst(event.pos, PALETTE["heal"], radius=14, shake=1.2, ember_count=6, smoky=True)

        elif event.kind == "fuga":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if not target:
                event.resolved = True
                return False
            target.morale = clamp(target.morale + 6, 0, 100)
            target.energy = clamp(target.energy + 4, 0, 100)
            self.adjust_trust(target, 8.0)
            self.set_event_message(f"{target.name} respirou fundo e voltou para dentro do anel da base.", duration=5.4)
            self.spawn_floating_text("segurou a fuga", target.pos, PALETTE["morale"])

        elif event.kind == "desercao":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if not target:
                event.resolved = True
                return False
            target.morale = clamp(target.morale + 4, 0, 100)
            self.adjust_trust(target, 10.0)
            self.set_event_message(f"{target.name} desistiu da trilha e ficou no campo.", duration=5.4)
            self.spawn_floating_text("ficou", target.pos, PALETTE["morale"])

        elif event.kind == "abrigo":
            profile = dict(event.data.get("profile", {}))
            if accepted and self.spare_beds() > 0:
                recruited = self.recruit_survivor_from_profile(
                    profile,
                    announce_message=f"{profile['name']} foi acolhido na clareira e ganhou uma cama.",
                    floating_label="abrigo aceito",
                )
                if not recruited:
                    self.set_event_message("O acampamento nao tem cama livre para acolher mais alguem.", duration=4.8)
                    return False
                if self.next_recruit_index < len(self.recruit_pool) and self.recruit_pool[self.next_recruit_index]["name"] == profile.get("name"):
                    self.next_recruit_index += 1
            else:
                self.set_event_message(f"{profile.get('name', 'O viajante')} se foi sem conseguir abrigo.", duration=4.8)
            self.morale_flash = min(1.0, self.morale_flash + 0.08)

        elif event.kind == "expedicao":
            expedition = self.active_expedition
            if not expedition:
                event.resolved = True
                self.active_dynamic_events = []
                return False
            expedition["distress_resolved"] = True
            expedition["danger"] = clamp(float(expedition["danger"]) - 0.16, 0.12, 0.95)
            expedition["timer"] = max(8.0, float(expedition["timer"]) - 5.0)
            loot_bundle = dict(expedition.get("loot_bundle", {}))
            bonus_key = "medicine" if expedition["region_biome"] in {"swamp", "ruin"} else "scrap"
            loot_bundle[bonus_key] = loot_bundle.get(bonus_key, 0) + 1
            expedition["loot_bundle"] = loot_bundle
            for survivor in self.survivors:
                if survivor.name in expedition["members"]:
                    survivor.trust_leader = clamp(survivor.trust_leader + 3.5, 0, 100)
                    survivor.morale = clamp(survivor.morale + 4.0, 0, 100)
            self.set_event_message(f"Voce abriu caminho e a expedicao retomou a rota para {expedition['region_name']}.", duration=6.0)
            self.spawn_floating_text("socorro entregue", event.pos, PALETTE["heal"])

        elif event.kind == "faccao":
            faction = str(event.data.get("faction", "andarilhos"))
            branch_key = "humane" if accepted else "hardline"
            branch = dict(event.data.get(branch_key, {}))
            cost_bundle = dict(branch.get("cost", {}))
            if cost_bundle and not self.consume_resource_bundle(cost_bundle):
                self.set_event_message("Faltam recursos para sustentar essa escolha moral agora.", duration=4.8)
                return False

            reward = dict(branch.get("reward", {}))
            resource_reward = {
                key: int(value)
                for key, value in reward.items()
                if key in {"logs", "wood", "food", "herbs", "scrap", "meals", "medicine"}
            }
            if resource_reward:
                self.add_resource_bundle(resource_reward)

            for survivor in self.living_survivors():
                self.adjust_trust(survivor, float(reward.get("trust", 0.0)) * (0.85 if accepted else 1.0))
                survivor.morale = clamp(survivor.morale + float(reward.get("morale", 0.0)), 0, 100)

            self.adjust_faction_standing(faction, float(reward.get("faction", 0.0)))
            future = dict(reward.get("future", {})) if isinstance(reward.get("future", {}), dict) else {}
            if future.get("medicine"):
                self.add_resource_bundle({"medicine": int(future["medicine"])})
            if future.get("survivor") and self.spare_beds() > 0 and self.next_recruit_index < len(self.recruit_pool):
                profile = self.recruit_pool[self.next_recruit_index]
                self.next_recruit_index += 1
                self.recruit_survivor_from_profile(
                    profile,
                    announce_message=f"{profile['name']} foi trazido pela confusao e pediu para ficar na clareira.",
                    floating_label="resgatado",
                )

            text_color = PALETTE["morale"] if accepted else PALETTE["danger_soft"]
            self.set_event_message(str(branch.get("message", "A faccao respondeu a sua escolha.")), duration=6.0)
            self.spawn_floating_text(self.faction_label(faction).lower(), event.pos, text_color)

        event.resolved = True
        self.survivors_react_to_event(event, resolved=True)
        self.active_dynamic_events = []
        self.dynamic_event_cooldown = self.random.uniform(18.0, 34.0)
        return True

    def fail_dynamic_event(self, event: DynamicEvent) -> None:
        if event.kind == "doenca":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if target:
                target.health = clamp(target.health - 18, 0, target.max_health)
                target.morale = clamp(target.morale - 10, 0, 100)
                target.exhaustion = clamp(target.exhaustion + 18, 0, 100)
                self.adjust_trust(target, -4.0)
                self.set_event_message(f"A febre de {target.name} piorou por falta de cuidado.", duration=5.6)
        elif event.kind == "incendio":
            site_kind = str(event.data.get("site_kind", "stockpile"))
            if event.building_uid is not None:
                building = self.building_by_id(event.building_uid)
                if building:
                    self.buildings = [item for item in self.buildings if item.uid != building.uid]
                    self.assign_building_specialists()
                    self.set_event_message(f"O incendio consumiu {building.kind} antes de ser apagado.", duration=5.8)
            elif site_kind == "stockpile":
                self.logs = max(0, self.logs - 4)
                self.wood = max(0, self.wood - 4)
                self.food = max(0, self.food - 2)
                self.set_event_message("As chamas comeram parte do estoque central.", duration=5.8)
            elif site_kind == "kitchen":
                self.food = max(0, self.food - 4)
                self.meals = max(0, self.meals - 3)
                self.herbs = max(0, self.herbs - 1)
                self.set_event_message("O fogo passou pelo fogao e estragou suprimentos da cozinha.", duration=5.8)
            else:
                self.wood = max(0, self.wood - 3)
                self.scrap = max(0, self.scrap - 3)
                self.set_event_message("A oficina perdeu material depois do incendio.", duration=5.8)
            self.impact_burst(event.pos, PALETTE["danger_soft"], radius=18, shake=4.4, ember_count=10, smoky=True)
        elif event.kind == "alarme":
            nearest = self.closest_barricade(event.pos)
            if nearest:
                nearest.health = clamp(nearest.health - 26, 0.0, nearest.max_health)
            for _ in range(2 + (1 if getattr(self, "horde_active", False) else 0)):
                self.spawn_forest_ambient_zombie(anchor=Vector2(event.pos), radius=120)
            for survivor in self.living_survivors():
                if survivor.distance_to(event.pos) < 220:
                    survivor.insanity = clamp(survivor.insanity + 8, 0, 100)
                    survivor.morale = clamp(survivor.morale - 5, 0, 100)
            self.set_event_message(f"O alarme estourou tarde demais e a cerca {event.data.get('edge', 'externa')} cedeu sob pancada.", duration=5.8)
            self.impact_burst(event.pos, PALETTE["danger_soft"], radius=20, shake=4.0, ember_count=8, smoky=True)
        elif event.kind == "fuga":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if target:
                target.morale = clamp(target.morale - 16, 0, 100)
                target.energy = clamp(target.energy - 12, 0, 100)
                target.trust_leader = clamp(target.trust_leader - 10, 0, 100)
                self.set_event_message(f"{target.name} sumiu por um tempo na mata e voltou abalado.", duration=5.8)
        elif event.kind == "desercao":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if target:
                self.remove_survivor(target)
                self.set_event_message(f"{target.name} desertou e levou sua funcao embora da clareira.", duration=6.0)
        elif event.kind == "abrigo":
            profile = event.data.get("profile", {})
            self.set_event_message(f"{profile.get('name', 'O viajante')} cansou de esperar e seguiu pela trilha.", duration=5.0)
        elif event.kind == "expedicao":
            expedition = self.active_expedition
            if expedition:
                expedition["danger"] = clamp(float(expedition["danger"]) + 0.2, 0.18, 1.0)
                expedition["timer"] = max(6.0, float(expedition["timer"]) - 2.0)
                self.set_event_message(f"O socorro falhou e a equipe sofreu mais na rota de {expedition['region_name']}.", duration=5.8)
            else:
                self.set_event_message("O pedido de socorro morreu no vento da mata.", duration=5.0)
        elif event.kind == "faccao":
            faction = str(event.data.get("faction", "andarilhos"))
            self.adjust_faction_standing(faction, -4.0)
            self.set_event_message(f"{self.faction_label(faction)} foi embora levando o impasse na memoria.", duration=5.0)

        self.survivors_react_to_event(event, resolved=False)
        self.active_dynamic_events = []
        self.dynamic_event_cooldown = self.random.uniform(20.0, 34.0)

    def update_dynamic_events(self, dt: float) -> None:
        self.dynamic_event_cooldown = max(0.0, self.dynamic_event_cooldown - dt)
        self.maybe_spawn_dynamic_event()
        if not self.active_dynamic_events:
            return

        event = self.active_dynamic_events[0]
        event.timer -= dt

        if event.kind == "doenca":
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if not target:
                self.active_dynamic_events = []
                return
            event.pos = Vector2(target.pos)
            target.health = clamp(target.health - 0.42 * dt, 0, target.max_health)
            target.energy = clamp(target.energy - 0.5 * dt, 0, 100)
            target.morale = clamp(target.morale - 0.22 * dt, 0, 100)
        elif event.kind == "incendio":
            tick = float(event.data.get("tick", 0.0)) - dt
            if tick <= 0:
                event.data["tick"] = 1.8
                self.emit_embers(event.pos, 6, smoky=True)
                if event.building_uid is None:
                    self.wood = max(0, self.wood - 1)
                    if str(event.data.get("site_kind")) == "kitchen":
                        self.food = max(0, self.food - 1)
                self.screen_shake = max(self.screen_shake, 1.4)
            else:
                event.data["tick"] = tick
        elif event.kind == "alarme":
            tick = float(event.data.get("tick", 0.0)) - dt
            if tick <= 0:
                event.data["tick"] = self.random.uniform(0.8, 1.4)
                self.impact_burst(event.pos, PALETTE["danger_soft"], radius=9, shake=0.65, ember_count=2, smoky=True)
                for survivor in self.living_survivors():
                    if survivor.distance_to(event.pos) < 220 and survivor.bark_cooldown <= 0:
                        self.trigger_survivor_bark(survivor, "Segura essa cerca!", PALETTE["danger_soft"], duration=1.8)
            else:
                event.data["tick"] = tick
        elif event.kind in {"fuga", "desercao"}:
            target = next((survivor for survivor in self.survivors if survivor.name == event.target_name and survivor.is_alive()), None)
            if not target:
                self.active_dynamic_events = []
                return
            event.pos = Vector2(event.pos)
            target.state_label = "em fuga" if event.kind == "fuga" else "desertando"
        elif event.kind == "expedicao":
            event.pos = self.expedition_distress_pos(self.active_expedition)
        elif event.kind == "abrigo":
            event.pos = Vector2(event.pos)

        if event.timer <= 0:
            self.fail_dynamic_event(event)

    def set_event_message(self, message: str, duration: float = 7.5) -> None:
        self.event_message = message
        self.event_timer = duration

    def resolve_interest_point(self, interest_point: InterestPoint) -> None:
        if interest_point.resolved:
            return

        interest_point.resolved = True
        living = self.living_survivors()

        if interest_point.event_kind == "herb_cache":
            self.add_resource_bundle({"food": 1, "herbs": 2})
            for survivor in living:
                survivor.health = clamp(survivor.health + 7, 0, survivor.max_health)
            self.player.health = clamp(self.player.health + 10, 0, self.player.max_health)
            self.set_event_message("Ervas silvestres renderam mantimentos e curativos.")
        elif interest_point.event_kind == "hunter_blind":
            self.add_resource_bundle({"logs": 1, "wood": 1, "food": 1})
            self.player.stamina = clamp(self.player.stamina + 14, 0, self.player.max_stamina)
            self.set_event_message("Um posto de cacador trouxe madeira seca e carne aproveitavel.")
        elif interest_point.event_kind == "lost_cart":
            self.add_resource_bundle({"food": 2, "logs": 1})
            for survivor in living:
                survivor.morale = clamp(survivor.morale + 4, 0, 100)
            self.set_event_message("A carroca esquecida ainda guardava provisoes intactas.")
        elif interest_point.event_kind == "flower_shrine":
            self.add_resource_bundle({"meals": 1, "herbs": 1})
            for survivor in living:
                survivor.morale = clamp(survivor.morale + 7, 0, 100)
            self.set_event_message("A clareira florida acalmou o grupo e elevou a moral.")
        elif interest_point.event_kind == "sunken_cache":
            self.add_resource_bundle({"scrap": 2})
            self.player.stamina = clamp(self.player.stamina - 10, 0, self.player.max_stamina)
            self.set_event_message("A caixa semi-afundada cedeu sucata util, mas drenou seu folego.")
        elif interest_point.event_kind == "reed_nest":
            self.add_resource_bundle({"food": 1, "herbs": 1})
            self.set_event_message("O ninho nos juncos virou refeicao para o campo.")
        elif interest_point.event_kind == "tool_crate":
            self.add_resource_bundle({"scrap": 2, "wood": 1})
            weakest = self.weakest_barricade()
            if weakest:
                weakest.repair(18)
            self.set_event_message("Ferramentas velhas renderam sucata e reforcaram a defesa.")
        elif interest_point.event_kind == "alarm_nest":
            self.add_resource_bundle({"scrap": 1})
            self.spawn_local_zombies(interest_point.pos, 2)
            self.screen_shake = max(self.screen_shake, 3.2)
            self.set_event_message("A sirene morta chiou e puxou dois zumbis da mata.")
            self.audio.play_alert(source_pos=interest_point.pos)
        else:
            self.add_resource_bundle({"food": 1})
            self.set_event_message("Algo util foi encontrado na exploracao.")

        self.spawn_floating_text(interest_point.label, interest_point.pos, PALETTE["accent_soft"])
        self.emit_embers(interest_point.pos, 4, smoky=True)
        self.audio.play_interact(source_pos=interest_point.pos)

    def spawn_local_zombies(self, center: Vector2, count: int, *, pressure: bool = False) -> None:
        for _ in range(count):
            pos = self.safe_zombie_spawn_position(center, 130, 220)
            zombie = Zombie(pos, self.day)
            zombie.anchor = Vector2(center)
            zombie.camp_pressure = clamp((0.78 if pressure else 0.52) + center.distance_to(CAMP_CENTER) / 950, 0.25, 1.0)
            self.zombies.append(zombie)

    def spawn_forest_ambient_zombie(self, *, anchor: Vector2 | None = None, radius: float | None = None) -> None:
        center = Vector2(anchor) if anchor is not None else Vector2(self.player.pos)
        if radius is None:
            min_distance = 260.0
            max_distance = 520.0
        else:
            min_distance = max(42.0, radius * 0.45)
            max_distance = max(68.0, radius)
        pos = self.safe_zombie_spawn_position(center, min_distance, max_distance)
        zombie = Zombie(pos, self.day)
        zombie.anchor = Vector2(center)
        zombie.camp_pressure = clamp(pos.distance_to(CAMP_CENTER) / 900, 0.18, 0.72)
        self.zombies.append(zombie)

    def safe_zombie_spawn_position(self, center: Vector2, min_distance: float, max_distance: float) -> Vector2:
        """Escolhe um ponto de spawn fora da zona segura do acampamento."""
        safe_radius = self.camp_clearance_radius() + 120
        for _ in range(48):
            angle = self.random.uniform(0, math.tau)
            distance = self.random.uniform(min_distance, max_distance)
            pos = Vector2(center) + angle_to_vector(angle) * distance
            if pos.distance_to(CAMP_CENTER) < safe_radius:
                continue
            if self.point_in_camp_square(pos, padding=96):
                continue
            if pos.distance_to(self.player.pos) < 120:
                continue
            return pos
        fallback = Vector2(center) - Vector2(CAMP_CENTER)
        if fallback.length_squared() <= 0.01:
            fallback = angle_to_vector(self.random.uniform(0, math.tau))
        else:
            fallback = fallback.normalize()
        return Vector2(CAMP_CENTER) + fallback * max(safe_radius + 36, min_distance)

    def update_player_biome(self) -> None:
        region = self.current_named_region()
        if self.point_in_camp_square(self.player.pos, padding=140):
            biome_key = "camp"
            region_key: tuple[int, int] | str = "camp"
            region_label = "Clareira do Campo"
        else:
            feature = self.feature_at_pos(self.player.pos)
            biome_key = feature.kind if feature else self.chunk_biome_kind(*self.chunk_key_for_pos(self.player.pos))
            region_key = tuple(region["key"]) if region else self.region_key_for_pos(self.player.pos)
            region_label = str(region["name"]) if region else self.feature_label(biome_key)
        label = self.feature_label(biome_key)
        self.current_zone_boss_label = self.zone_boss_status_text(region, short=True)
        if region_key != self.current_region_key:
            self.current_region_key = region_key
            self.current_region_label = region_label
            self.spawn_floating_text(region_label.lower(), self.player.pos + Vector2(0, -60), PALETTE["accent_soft"])
        if biome_key != self.current_biome_key:
            self.current_biome_key = biome_key
            self.current_biome_label = label
            self.spawn_floating_text(label.lower(), self.player.pos + Vector2(0, -38), PALETTE["muted"])

    def generate_path_network(self) -> list[list[Vector2]]:
        paths: list[list[Vector2]] = []
        anchors = (
            (Vector2(-80, CAMP_CENTER.y - 180), CAMP_CENTER + Vector2(135, -36)),
            (Vector2(CAMP_CENTER.x + 80, -60), CAMP_CENTER + Vector2(12, 112)),
            (Vector2(WORLD_WIDTH + 50, CAMP_CENTER.y + 210), CAMP_CENTER + Vector2(-24, 88)),
        )
        for start, end in anchors:
            paths.append(self.make_path_points(start, end, variation=240, segments=28))

        feature_targets = [feature for feature in self.world_features if feature.kind in {"ruin", "meadow"}]
        self.random.shuffle(feature_targets)
        for feature in feature_targets[:3]:
            offset = angle_to_vector(feature.accent * math.tau) * 48
            paths.append(
                self.make_path_points(
                    CAMP_CENTER + offset * 0.35,
                    feature.pos + offset,
                    variation=170,
                    segments=24,
                )
            )

        paths.append(self.camp_loop_points(38, segments_per_side=4, jitter=10))
        return paths

    def make_path_points(
        self,
        start: Vector2,
        end: Vector2,
        *,
        variation: float,
        segments: int,
    ) -> list[Vector2]:
        control_a = start.lerp(end, 0.3) + Vector2(
            self.random.uniform(-variation, variation),
            self.random.uniform(-variation, variation),
        )
        control_b = start.lerp(end, 0.68) + Vector2(
            self.random.uniform(-variation, variation),
            self.random.uniform(-variation, variation),
        )
        points = []
        for step in range(segments):
            t = step / max(1, segments - 1)
            p0 = start.lerp(control_a, t)
            p1 = control_a.lerp(control_b, t)
            p2 = control_b.lerp(end, t)
            q0 = p0.lerp(p1, t)
            q1 = p1.lerp(p2, t)
            points.append(q0.lerp(q1, t))
        return points

    def is_near_path(self, pos: Vector2, radius: float) -> bool:
        radius_sq = radius * radius
        for path in self.path_network:
            for point in path[::2]:
                if pos.distance_squared_to(point) <= radius_sq:
                    return True
        return False

    def local_tree_density(self, pos: Vector2) -> float:
        density = 0.72
        distance_to_camp = pos.distance_to(CAMP_CENTER)
        if distance_to_camp < self.camp_clearance_radius() + 170:
            density -= 0.42

        for feature in self.world_features:
            feature_range = feature.radius * 1.28
            distance = pos.distance_to(feature.pos)
            if distance > feature_range:
                continue
            influence = 1 - distance / feature_range
            if feature.kind == "grove":
                density += 0.65 * influence
            elif feature.kind == "meadow":
                density -= 0.7 * influence
            elif feature.kind == "swamp":
                density -= 0.48 * influence
            elif feature.kind == "ruin":
                density -= 0.25 * influence

        if self.is_near_path(pos, 32):
            density -= 0.16
        return clamp(density, 0.08, 0.98)

    def generate_resource_position(
        self,
        preferred_kinds: tuple[str, ...],
        min_distance: float,
        max_distance: float,
        existing_nodes: list[ResourceNode],
        radius: float,
    ) -> Vector2:
        for _ in range(90):
            pos: Vector2 | None = None
            matches = [feature for feature in self.world_features if feature.kind in preferred_kinds]
            if matches and self.random.random() < 0.82:
                feature = self.random.choice(matches)
                angle = self.random.uniform(0, math.tau)
                spread = self.random.uniform(feature.radius * 0.22, feature.radius * 0.92)
                pos = feature.pos + angle_to_vector(angle) * spread
                pos = Vector2(clamp(pos.x, 80, WORLD_WIDTH - 80), clamp(pos.y, 80, WORLD_HEIGHT - 80))
            else:
                pos = self.random_resource_pos(min_distance, max_distance)

            if pos.distance_to(CAMP_CENTER) < min_distance or pos.distance_to(CAMP_CENTER) > max_distance:
                continue
            if any(pos.distance_to(node.pos) < node.radius + radius + 18 for node in existing_nodes):
                continue
            return pos
        return self.random_resource_pos(min_distance, max_distance)

    def generate_tents(self) -> list[dict[str, Vector2 | float]]:
        base_offsets = [
            Vector2(-0.78, -0.5),
            Vector2(0.76, -0.5),
            Vector2(0.82, -0.06),
            Vector2(0.74, 0.38),
            Vector2(0.56, 0.72),
            Vector2(-0.56, 0.72),
            Vector2(-0.78, 0.36),
            Vector2(-0.82, -0.04),
        ]
        tents: list[dict[str, Vector2 | float]] = []
        initial_half_size = 214

        if hasattr(self, "tents") and len(getattr(self, "tents", [])) >= len(base_offsets):
            for tent in list(self.tents[: len(base_offsets)]):
                tents.append(
                    {
                        "pos": Vector2(tent["pos"]),
                        "angle": float(tent["angle"]),
                        "scale": float(tent["scale"]),
                        "tone": float(tent["tone"]),
                    }
                )
        else:
            for offset in base_offsets:
                pos = CAMP_CENTER + Vector2(offset.x * initial_half_size, offset.y * initial_half_size)
                facing = CAMP_CENTER - pos
                angle = math.atan2(facing.y, facing.x) if facing.length_squared() > 0 else 0.0
                tents.append(
                    {
                        "pos": pos,
                        "angle": angle,
                        "scale": self.random.uniform(0.94, 1.14),
                        "tone": self.random.uniform(0.0, 1.0),
                    }
                )
        return tents

    def generate_trees(self) -> list[dict[str, object]]:
        trees: list[dict[str, object]] = []
        attempts = 0
        while len(trees) < 190 and attempts < 6000:
            attempts += 1
            pos = Vector2(
                self.random.uniform(40, WORLD_WIDTH - 40),
                self.random.uniform(40, WORLD_HEIGHT - 40),
            )
            if pos.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + self.random.uniform(110, 250):
                continue
            if self.random.random() > self.local_tree_density(pos):
                continue

            tone = self.random.uniform(0.15, 0.85)
            radius = self.random.randint(24, 42)
            for feature in self.world_features:
                distance = pos.distance_to(feature.pos)
                if distance > feature.radius:
                    continue
                influence = 1 - distance / max(1, feature.radius)
                if feature.kind == "grove":
                    radius += int(8 * influence)
                    tone = clamp(tone + 0.08, 0.0, 1.0)
                elif feature.kind == "swamp":
                    tone = clamp(tone - 0.18, 0.0, 1.0)
                elif feature.kind == "meadow":
                    radius -= int(5 * influence)
                elif feature.kind == "ruin":
                    radius -= int(3 * influence)
            trees.append(
                {
                    "pos": pos,
                    "radius": int(clamp(radius, 18, 50)),
                    "height": self.random.uniform(0.8, 1.25),
                    "tone": tone,
                    "lean": self.random.uniform(-0.22, 0.22),
                    "spread": self.random.uniform(0.82, 1.28),
                    "branch_bias": self.random.uniform(-0.35, 0.35),
                    "wood_yield": max(2, int(radius * 0.1) + self.random.randint(0, 1)),
                    "effort_required": 2 + int(radius >= 29) + int(radius >= 40),
                    "effort_progress": 0,
                    "harvested": False,
                }
            )
        return trees

    def generate_resource_nodes(self) -> list[ResourceNode]:
        nodes: list[ResourceNode] = []
        base_distance = self.camp_clearance_radius()
        for _ in range(6):
            nodes.append(
                ResourceNode(
                    "food",
                    self.generate_resource_position(
                        ("meadow", "swamp"),
                        base_distance + 240,
                        base_distance + 620,
                        nodes,
                        22,
                    ),
                    amount=1,
                    radius=22,
                    variant="berries",
                    renewable=False,
                )
            )
        for _ in range(5):
            nodes.append(
                ResourceNode(
                    "scrap",
                    self.generate_resource_position(
                        ("ruin",),
                        base_distance + 300,
                        base_distance + 760,
                        nodes,
                        24,
                    ),
                    amount=1,
                    radius=24,
                    variant="crate",
                    renewable=False,
                )
            )
        return nodes

    def random_resource_pos(self, min_distance: float, max_distance: float) -> Vector2:
        angle = self.random.uniform(0, math.tau)
        distance = self.random.uniform(min_distance, max_distance)
        pos = CAMP_CENTER + angle_to_vector(angle) * distance
        return Vector2(clamp(pos.x, 80, WORLD_WIDTH - 80), clamp(pos.y, 80, WORLD_HEIGHT - 80))

    def generate_barricades(self) -> list[Barricade]:
        barricades: list[Barricade] = []
        segments_per_side = 4 + self.camp_level
        half = self.camp_half_size + 24
        spacing = (half * 2) / segments_per_side
        span = spacing * 0.84
        tier = 1 + self.camp_level
        max_health = 110 + tier * 28
        for index in range(segments_per_side):
            offset = -half + spacing * (index + 0.5)
            barricades.append(Barricade(-math.pi / 2, CAMP_CENTER + Vector2(offset, -half), Vector2(1, 0), span=span, tier=tier, max_health=max_health, health=max_health))
            barricades.append(Barricade(0.0, CAMP_CENTER + Vector2(half, offset), Vector2(0, 1), span=span, tier=tier, max_health=max_health, health=max_health))
            barricades.append(Barricade(math.pi / 2, CAMP_CENTER + Vector2(-offset, half), Vector2(-1, 0), span=span, tier=tier, max_health=max_health, health=max_health))
            barricades.append(Barricade(math.pi, CAMP_CENTER + Vector2(-half, -offset), Vector2(0, -1), span=span, tier=tier, max_health=max_health, health=max_health))
        return barricades

    def reflow_barricades_for_current_camp_size(self) -> None:
        """Redistribui os segmentos existentes ao redor do novo tamanho da base.

        A ideia aqui e preservar a quantidade atual de trechos e os upgrades de spikes,
        aumentando o comprimento e o espacamento da linha defensiva quando a base cresce.
        """
        if not self.barricades:
            self.barricades = self.generate_barricades()
            return

        half = self.camp_half_size + 24
        side_map: dict[str, list[Barricade]] = {"top": [], "right": [], "bottom": [], "left": []}

        for barricade in self.barricades:
            angle = float(barricade.angle)
            if abs(angle - (-math.pi / 2)) < 0.01:
                side_map["top"].append(barricade)
            elif abs(angle - 0.0) < 0.01:
                side_map["right"].append(barricade)
            elif abs(angle - (math.pi / 2)) < 0.01:
                side_map["bottom"].append(barricade)
            else:
                side_map["left"].append(barricade)

        side_map["top"].sort(key=lambda barricade: barricade.pos.x)
        side_map["right"].sort(key=lambda barricade: barricade.pos.y)
        side_map["bottom"].sort(key=lambda barricade: barricade.pos.x, reverse=True)
        side_map["left"].sort(key=lambda barricade: barricade.pos.y, reverse=True)

        for side, group in side_map.items():
            if not group:
                continue
            spacing = (half * 2) / len(group)
            span = spacing * 0.84
            for index, barricade in enumerate(group):
                offset = -half + spacing * (index + 0.5)
                if side == "top":
                    barricade.angle = -math.pi / 2
                    barricade.tangent = Vector2(1, 0)
                    barricade.pos = CAMP_CENTER + Vector2(offset, -half)
                elif side == "right":
                    barricade.angle = 0.0
                    barricade.tangent = Vector2(0, 1)
                    barricade.pos = CAMP_CENTER + Vector2(half, offset)
                elif side == "bottom":
                    barricade.angle = math.pi / 2
                    barricade.tangent = Vector2(-1, 0)
                    barricade.pos = CAMP_CENTER + Vector2(-offset, half)
                else:
                    barricade.angle = math.pi
                    barricade.tangent = Vector2(0, -1)
                    barricade.pos = CAMP_CENTER + Vector2(-half, -offset)
                barricade.span = span

    def generate_survivors(self) -> list[Survivor]:
        survivors = []
        initial_population = 6
        sleep_slots = self.camp_sleep_slots()
        for index, profile in enumerate(self.recruit_pool[:initial_population]):
            slot = sleep_slots[index]
            guard_pos = self.guard_posts()[index % len(self.guard_posts())]
            survivors.append(
                Survivor(
                    str(profile["name"]),
                    str(profile["role"]),
                    Vector2(slot["sleep_pos"]),
                    Vector2(slot["sleep_pos"]),
                    guard_pos,
                    tuple(profile.get("traits", ())),
                )
            )
        self.next_recruit_index = len(survivors)
        return survivors

    def build_terrain_surface(self) -> pygame.Surface:
        surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
        surface.fill(PALETTE["forest_floor"])

        for _ in range(540):
            radius = self.random.randint(20, 80)
            color = (
                lerp(PALETTE["forest_floor_dark"][0], PALETTE["forest_floor_light"][0], self.random.random()),
                lerp(PALETTE["forest_floor_dark"][1], PALETTE["forest_floor_light"][1], self.random.random()),
                lerp(PALETTE["forest_floor_dark"][2], PALETTE["forest_floor_light"][2], self.random.random()),
            )
            pygame.draw.circle(
                surface,
                tuple(int(channel) for channel in color),
                (self.random.randint(0, WORLD_WIDTH), self.random.randint(0, WORLD_HEIGHT)),
                radius,
            )

        feature_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        for feature in self.world_features:
            self.paint_feature(feature_surface, feature)
        surface.blit(feature_surface, (0, 0))

        self.paint_camp_ground(surface)

        path_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        for index, path in enumerate(self.path_network):
            if index == len(self.path_network) - 1:
                self.draw_path(path_surface, path, base_width=28, highlight_width=10, base_alpha=110)
            else:
                self.draw_path(path_surface, path)
        surface.blit(path_surface, (0, 0))
        return surface

    def tree_is_harvestable(self, tree: dict[str, object]) -> bool:
        return bool(not tree.get("harvested", False))

    def closest_available_tree(self, origin: Vector2) -> dict[str, object] | None:
        candidates = [tree for tree in self.trees if self.tree_is_harvestable(tree)]
        if not candidates:
            return None
        return min(candidates, key=lambda tree: Vector2(tree["pos"]).distance_to(origin))

    def harvest_tree(self, tree: dict[str, object], *, effort: int = 1) -> int:
        if not self.tree_is_harvestable(tree):
            return 0
        effort_required = int(tree.get("effort_required", 2))
        effort_progress = int(tree.get("effort_progress", 0)) + max(1, effort)
        tree["effort_progress"] = effort_progress
        if effort_progress < effort_required:
            return 0
        tree["harvested"] = True
        return int(tree["wood_yield"])

    def paint_feature(self, surface: pygame.Surface, feature: WorldFeature) -> None:
        pos = (int(feature.pos.x), int(feature.pos.y))
        radius = int(feature.radius)
        accent_angle = feature.accent * math.tau

        if feature.kind == "grove":
            pygame.draw.circle(surface, (22, 45, 31, 118), pos, radius)
            pygame.draw.circle(
                surface,
                (37, 68, 42, 84),
                (
                    int(feature.pos.x + math.cos(accent_angle) * radius * 0.24),
                    int(feature.pos.y + math.sin(accent_angle) * radius * 0.18),
                ),
                int(radius * 0.72),
            )
            for index in range(11):
                angle = accent_angle + index * 0.54
                offset = angle_to_vector(angle) * (radius * (0.16 + (index % 4) * 0.12))
                pygame.draw.circle(
                    surface,
                    (30, 58, 37, 46),
                    (int(feature.pos.x + offset.x), int(feature.pos.y + offset.y)),
                    int(radius * 0.15),
                )
        elif feature.kind == "meadow":
            pygame.draw.circle(surface, (89, 119, 72, 98), pos, radius)
            pygame.draw.circle(
                surface,
                (118, 148, 82, 58),
                (
                    int(feature.pos.x - math.cos(accent_angle) * radius * 0.22),
                    int(feature.pos.y + math.sin(accent_angle) * radius * 0.18),
                ),
                int(radius * 0.58),
            )
            for index in range(10):
                angle = accent_angle + index * 0.62
                offset = angle_to_vector(angle) * (radius * (0.18 + (index % 3) * 0.16))
                pygame.draw.circle(
                    surface,
                    (166, 166, 92, 34),
                    (int(feature.pos.x + offset.x), int(feature.pos.y + offset.y)),
                    6,
                )
        elif feature.kind == "swamp":
            swamp_rect = pygame.Rect(0, 0, int(radius * 1.7), int(radius * 1.1))
            swamp_rect.center = pos
            pygame.draw.ellipse(surface, (22, 53, 50, 126), swamp_rect)
            pygame.draw.ellipse(
                surface,
                (59, 85, 74, 62),
                swamp_rect.inflate(-int(radius * 0.36), -int(radius * 0.28)),
            )
            pygame.draw.circle(surface, (73, 82, 54, 44), pos, int(radius * 0.92))
        elif feature.kind == "ruin":
            pygame.draw.circle(surface, (87, 78, 66, 104), pos, radius)
            pygame.draw.circle(surface, (107, 92, 73, 52), pos, int(radius * 0.62))
            for index in range(7):
                angle = accent_angle + index * 0.76
                offset = angle_to_vector(angle) * (radius * 0.45)
                rubble = pygame.Rect(0, 0, 18 + index % 3 * 4, 12 + index % 2 * 3)
                rubble.center = (int(feature.pos.x + offset.x), int(feature.pos.y + offset.y))
                pygame.draw.rect(surface, (124, 118, 110, 120), rubble, border_radius=4)

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
        if len(points) > 1:
            pygame.draw.lines(surface, (*PALETTE["path"], base_alpha), False, points, base_width)
            pygame.draw.lines(surface, (*PALETTE["path_light"], highlight_alpha), False, points, highlight_width)

    def available_node(self, kind: str) -> bool:
        if kind == "wood":
            return any(self.tree_is_harvestable(tree) for tree in self.trees)
        return any(node.kind == kind and node.is_available() for node in self.resource_nodes)

    def closest_available_node(self, kind: str, origin: Vector2) -> object | None:
        if kind == "wood":
            return self.closest_available_tree(origin)
        candidates = [node for node in self.resource_nodes if node.kind == kind and node.is_available()]
        if not candidates:
            return None
        return min(candidates, key=lambda node: node.pos.distance_to(origin))

    def has_damaged_barricade(self) -> bool:
        return any(b.health < b.max_health for b in self.barricades)

    def weakest_barricade(self) -> Barricade | None:
        if not self.barricades:
            return None
        return min(self.barricades, key=lambda barricade: barricade.health)

    def weakest_barricade_health(self) -> float:
        weakest = self.weakest_barricade()
        return weakest.health if weakest else 100.0

    def average_morale(self) -> float:
        alive = [survivor.morale for survivor in self.survivors if survivor.is_alive()]
        return sum(alive) / len(alive) if alive else 0.0

    def average_insanity(self) -> float:
        alive = [getattr(survivor, "insanity", 0.0) for survivor in self.survivors if survivor.is_alive()]
        return sum(alive) / len(alive) if alive else 0.0

    def average_health(self) -> float:
        alive = [survivor.health for survivor in self.survivors if survivor.is_alive()]
        return sum(alive) / len(alive) if alive else 0.0

    def audio_tension(self) -> float:
        zombie_factor = clamp(len(self.zombies) / 10, 0.0, 1.0)
        spawn_factor = clamp(self.spawn_budget / 14, 0.0, 1.0) if self.is_night else 0.0
        fire_factor = 1.0 - clamp(self.bonfire_heat / 100, 0.0, 1.0)
        barricade_factor = 1.0 - clamp(self.weakest_barricade_health() / 100, 0.0, 1.0)
        health_factor = 1.0 - clamp(self.player.health / self.player.max_health, 0.0, 1.0)
        morale_factor = 1.0 - clamp(self.average_morale() / 100, 0.0, 1.0)
        insanity_factor = clamp(self.average_insanity() / 100, 0.0, 1.0)
        weather_factor = self.weather_precipitation_factor() * 0.08
        weather_factor += self.weather_mist_factor() * 0.05
        weather_factor += self.weather_wind_factor() * 0.04
        weather_factor += self.weather_storm_factor() * 0.08
        base = 0.18 if self.is_night else 0.04
        tension = (
            base
            + zombie_factor * 0.42
            + spawn_factor * 0.16
            + fire_factor * 0.12
            + barricade_factor * 0.14
            + health_factor * 0.1
            + morale_factor * 0.06
            + insanity_factor * 0.08
            + weather_factor
            + (0.12 if getattr(self, "horde_active", False) else 0.0)
        )
        return clamp(tension, 0.0, 1.0)

    def tension_label(self) -> str:
        tension = self.audio_tension()
        if getattr(self, "horde_active", False):
            return "Noite de horda"
        if tension >= 0.8:
            return "Horda em cima"
        if tension >= 0.56:
            return "Sob pressao"
        if tension >= 0.32:
            return "Inquieta"
        return "Estavel"

    def living_survivors(self) -> list[Survivor]:
        return [survivor for survivor in self.survivors if survivor.is_alive() and not self.is_survivor_on_expedition(survivor)]

    def camp_invader_zombies(self) -> list[Zombie]:
        """Lista mortos que ja pressionam a linha da base ou passaram da cerca."""
        invaders: list[Zombie] = []
        safe_radius = self.camp_clearance_radius() + 84
        for zombie in self.zombies:
            if not zombie.is_alive():
                continue
            if self.point_in_camp_square(zombie.pos, padding=54) or zombie.pos.distance_to(CAMP_CENTER) < safe_radius:
                invaders.append(zombie)
        return invaders

    def closest_defense_target(self, survivor: Survivor) -> Zombie | None:
        """Escolhe um alvo comum para a defesa, priorizando invasores da base."""
        invaders = self.camp_invader_zombies()
        if invaders:
            return min(
                invaders,
                key=lambda zombie: (
                    zombie.pos.distance_to(CAMP_CENTER),
                    zombie.pos.distance_to(self.player.pos),
                    zombie.pos.distance_to(survivor.pos),
                ),
            )
        nearby = [zombie for zombie in self.zombies if zombie.is_alive() and zombie.pos.distance_to(survivor.pos) < 128]
        if nearby:
            return min(nearby, key=lambda zombie: zombie.pos.distance_to(survivor.pos))
        if self.is_night:
            perimeter = [
                zombie
                for zombie in self.zombies
                if zombie.is_alive() and zombie.pos.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 180
            ]
            if perimeter:
                return min(perimeter, key=lambda zombie: zombie.pos.distance_to(survivor.pos))
        return None

    def survivor_focus_override(self, survivor: Survivor) -> tuple[str, object | Vector2 | None] | None:
        """Deixa o foco do chefe puxar a rotina antes do trabalho especializado quando fizer sentido."""
        assigned_building = self.building_by_id(getattr(survivor, "assigned_building_id", None))
        if self.focus_mode == "fortify":
            defense_target = self.closest_defense_target(survivor)
            if assigned_building and getattr(survivor, "assigned_building_kind", None) == "torre" and survivor.energy > 18:
                return ("watchtower", assigned_building)
            if defense_target and survivor.energy > 22:
                return ("guard", survivor.guard_pos)
            if self.has_damaged_barricade() and self.wood > 0 and survivor.energy > 24:
                barricade = self.weakest_barricade()
                if barricade:
                    return ("repair", barricade)
        elif self.focus_mode == "morale":
            if self.available_fuel() > 0 and (self.bonfire_heat < 60 or self.bonfire_ember_bed < 28):
                return ("tend_fire", self.bonfire_pos)
            if self.food >= 2 and self.available_fuel() > 0 and survivor.energy > 24:
                kitchen = assigned_building if assigned_building and getattr(survivor, "assigned_building_kind", None) == "cozinha" else None
                if kitchen:
                    return ("cookhouse", kitchen)
                return ("cook", self.kitchen_pos)
            if self.average_morale() < 64 and survivor.energy > 24:
                return ("socialize", self.bonfire_pos)
        elif self.focus_mode == "supply":
            if assigned_building and getattr(survivor, "assigned_building_kind", None) == "serraria" and self.logs >= 2 and survivor.energy > 24:
                return ("sawmill", assigned_building)
            if (
                assigned_building
                and getattr(survivor, "assigned_building_kind", None) == "horta"
                and not self.is_night
                and survivor.energy > 24
                and self.garden_is_ready(assigned_building)
            ):
                return ("garden", assigned_building)
            if not self.buildings_of_kind("serraria") and survivor.role in {"artesa", "lenhador"} and self.logs > 0 and survivor.energy > 24:
                return ("roughcut", self.workshop_pos)
        return None

    def survivor_should_seek_shelter(self, survivor: Survivor, zombie: Zombie) -> bool:
        """Define quando um morador deve recuar em vez de comprar briga."""
        if survivor.health < 38 or survivor.energy < 18:
            return True
        if survivor.state in {"sleep", "rest", "treatment"} and zombie.pos.distance_to(survivor.pos) < 140:
            return True
        if survivor.role in {"cozinheiro", "mensageiro"} and zombie.pos.distance_to(survivor.pos) < 170:
            return True
        if survivor.exhaustion > 84 or survivor.insanity > 88:
            return True
        return False

    def survivor_should_engage(self, survivor: Survivor, zombie: Zombie) -> bool:
        """Decide quem entra no combate e quem so segura a linha quando a base e invadida."""
        base_invaded = self.point_in_camp_square(zombie.pos, padding=54) or zombie.pos.distance_to(CAMP_CENTER) < self.camp_clearance_radius() + 92
        if survivor.role == "vigia":
            return survivor.energy > 18 and survivor.health > 28
        if survivor.has_trait("corajoso"):
            return survivor.energy > 24 and survivor.health > 34
        if survivor.has_trait("leal") and base_invaded:
            return survivor.energy > 24 and survivor.health > 34
        if survivor.role in {"lenhador", "artesa", "batedora"} and base_invaded:
            return survivor.energy > 30 and survivor.health > 48
        return zombie.pos.distance_to(survivor.pos) < 64 and survivor.health > 52 and survivor.energy > 32

    def survivor_attack_damage(self, survivor: Survivor) -> float:
        """Escala simples de dano para o combate automatico dos moradores."""
        damage = 14.0
        if survivor.role == "vigia":
            damage += 6.0
        elif survivor.role in {"lenhador", "artesa"}:
            damage += 3.0
        elif survivor.role == "batedora":
            damage += 2.0
        if survivor.has_trait("corajoso"):
            damage += 3.0
        if survivor.has_trait("teimoso"):
            damage += 1.0
        if survivor.has_trait("gentil"):
            damage -= 1.0
        return damage

    def spawn_floating_text(
        self,
        text: str,
        pos: Vector2,
        color: tuple[int, int, int],
    ) -> None:
        self.floating_texts.append(FloatingText(text, Vector2(pos), color))

    def emit_embers(self, origin: Vector2, amount: int, *, smoky: bool = False) -> None:
        for _ in range(amount):
            velocity = Vector2(self.random.uniform(-22, 22), self.random.uniform(-58, -18))
            color = PALETTE["ember"] if not smoky else (113, 101, 89)
            self.embers.append(
                Ember(
                    Vector2(origin),
                    velocity,
                    self.random.uniform(2, 4.5),
                    self.random.uniform(0.55, 1.3),
                    color,
                )
            )

    def screen_to_world(self, position: Vector2) -> Vector2:
        return self.camera.screen_to_world(position)

    def world_to_screen(self, position: Vector2) -> Vector2:
        return self.camera.world_to_screen(position)

    def closest_barricade(self, pos: Vector2) -> Barricade | None:
        if not self.barricades:
            return None
        return min(self.barricades, key=lambda barricade: barricade.pos.distance_to(pos))

    def closest_target(self, pos: Vector2) -> Actor | None:
        candidates: list[Actor] = [self.player]
        candidates.extend(self.living_survivors())
        candidates.extend(
            survivor
            for survivor in self.expedition_visible_members()
            if not getattr(survivor, "expedition_downed", False)
        )
        living = [actor for actor in candidates if actor.is_alive()]
        if not living:
            return None
        return min(living, key=lambda actor: actor.pos.distance_to(pos))

    def find_closest_zombie(self, pos: Vector2, radius: float) -> Zombie | None:
        living = [zombie for zombie in self.zombies if zombie.is_alive()]
        if not living:
            return None
        zombie = min(living, key=lambda item: item.pos.distance_to(pos))
        if zombie.pos.distance_to(pos) <= radius:
            return zombie
        return None

    def create_horde_boss_profile(self) -> dict[str, object]:
        return {
            "name": "Chefe da Horda",
            "variant": "boss",
            "weapon": "lamina presa",
            "radius": 34,
            "speed": 86 + self.day * 2.0,
            "health": 390 + self.day * 34,
            "damage": 24 + self.day * 1.25,
            "body": (130, 106, 84),
            "accent": (78, 46, 36),
            "zone_key": ("horda", self.day),
            "zone_label": "Noite da Horda",
            "anchor": Vector2(CAMP_CENTER),
            "alert_radius": 420,
        }

    def begin_night(self) -> None:
        # As tres primeiras noites seguram mais a mao para a base destravar serraria, cozinha e leitos.
        if self.day <= 3:
            horde_chance = 0.0
        else:
            horde_chance = min(0.04 + (self.day - 3) * 0.022, 0.32)
        self.horde_active = self.random.random() < horde_chance
        if self.day <= 2:
            self.spawn_budget = 1 + self.day + (1 if self.horde_active else 0)
            self.spawn_timer = 2.8
        else:
            self.spawn_budget = 2 + self.day + (2 if self.horde_active else 0)
            self.spawn_timer = 2.35
        self.bonfire_ember_bed = clamp(self.bonfire_ember_bed + 8, 0, 100)
        self.emit_embers(self.bonfire_pos, 20)
        self.spawn_floating_text("a floresta acordou", self.bonfire_pos, PALETTE["danger_soft"])
        if self.horde_active:
            boss_angle = self.random.uniform(0, math.tau)
            boss_distance = self.camp_clearance_radius() + self.random.uniform(250, 340)
            boss_pos = CAMP_CENTER + angle_to_vector(boss_angle) * boss_distance
            boss = Zombie(boss_pos, self.day, boss_profile=self.create_horde_boss_profile())
            boss.anchor = Vector2(CAMP_CENTER)
            boss.camp_pressure = 1.0
            self.zombies.append(boss)
            self.set_event_message("Anoiteceu com horda. Um chefe podre esta puxando a mata inteira para cima do acampamento.")
        else:
            self.set_event_message("Anoiteceu. A mata aperta o cerco ao redor do campo.")
        self.audio.play_transition("nightfall")

    def begin_day(self) -> None:
        self.day += 1
        self.horde_active = False
        used_meals, used_food, ration_deficit = self.apply_daily_rations()
        self.add_resource_bundle(
            {
                "food": self.building_count("horta"),
                "meals": 1 if self.building_count("cozinha") > 0 else 0,
                "herbs": 1 if self.building_count("enfermaria") > 0 else 0,
            }
        )
        self.bonfire_heat = clamp(self.bonfire_heat + 12, 0, 100)
        self.bonfire_ember_bed = clamp(self.bonfire_ember_bed + 10, 0, 100)
        for survivor in self.survivors:
            if survivor.is_alive():
                survivor.energy = clamp(survivor.energy + 25, 0, 100)
                survivor.morale = clamp(survivor.morale + 8, 0, 100)
                survivor.sleep_debt = clamp(getattr(survivor, "sleep_debt", 0.0) - 18, 0, 100)
        self.try_recruit_survivor()
        self.normalize_stockpile()
        self.spawn_floating_text(f"amanheceu - dia {self.day}", self.bonfire_pos, PALETTE["accent_soft"])
        phase_label = self.economy_phase_label()
        if ration_deficit > 0:
            self.set_event_message(
                f"O amanhecer cobrou caro. Faltaram racoes na fase de {phase_label} e a base sentiu o tranco.",
                duration=6.4,
            )
        elif used_meals > 0 or used_food > 0:
            self.set_event_message(
                f"O amanhecer consumiu {used_meals} refeicoes e {used_food} insumos. A base entrou em {phase_label}.",
                duration=6.2,
            )
        else:
            self.set_event_message(f"O amanhecer trouxe folego para a sociedade da clareira. Fase: {phase_label}.")
        self.audio.play_transition("daybreak")

    def spawn_night_zombie(self) -> None:
        spawn_center = CAMP_CENTER
        if self.player.pos.distance_to(CAMP_CENTER) > self.camp_clearance_radius() + 320:
            spawn_center = Vector2(self.player.pos)
        if spawn_center == CAMP_CENTER:
            pos = self.safe_zombie_spawn_position(
                spawn_center,
                self.camp_clearance_radius() + 480,
                self.camp_clearance_radius() + 690,
            )
        else:
            pos = self.safe_zombie_spawn_position(spawn_center, 240, 420)
        zombie = Zombie(pos, self.day)
        zombie.anchor = Vector2(spawn_center)
        zombie.camp_pressure = 0.92 if spawn_center == CAMP_CENTER or self.horde_active else 0.6
        self.zombies.append(zombie)
        self.spawn_budget -= 1
