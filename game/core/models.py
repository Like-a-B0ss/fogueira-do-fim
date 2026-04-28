from __future__ import annotations

import random
from dataclasses import dataclass, field

from pygame import Vector2

from .config import WORLD_HEIGHT, WORLD_WIDTH, clamp


@dataclass
class ResourceNode:
    kind: str
    pos: Vector2
    amount: int
    radius: int
    variant: str = ""
    cooldown: float = 0.0
    renewable: bool = False
    respawn_delay: float = 180.0

    def is_available(self) -> bool:
        return self.amount > 0

    def harvest(self) -> int:
        if self.amount <= 0:
            return 0
        self.amount -= 1
        self.cooldown = self.respawn_delay
        return 1

    def update(self, dt: float) -> None:
        if self.amount > 0 or not self.renewable:
            return
        if self.cooldown > 0:
            self.cooldown -= dt
        else:
            self.amount = 1
            self.cooldown = self.respawn_delay or random.uniform(140.0, 220.0)


@dataclass
class Barricade:
    angle: float
    pos: Vector2
    tangent: Vector2
    span: float = 74.0
    tier: int = 1
    spike_level: int = 0
    max_health: float = 100.0
    health: float = 100.0

    def is_broken(self) -> bool:
        return self.health <= 0

    def damage(self, amount: float) -> None:
        self.health = clamp(self.health - amount, 0.0, self.max_health)

    def repair(self, amount: float) -> None:
        self.health = clamp(self.health + amount, 0.0, self.max_health)


@dataclass
class FloatingText:
    text: str
    pos: Vector2
    color: tuple[int, int, int]
    life: float = 1.2
    velocity: Vector2 = field(default_factory=lambda: Vector2(0, -28))

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.pos += self.velocity * dt
        return self.life > 0


@dataclass
class Ember:
    pos: Vector2
    velocity: Vector2
    radius: float
    life: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.pos += self.velocity * dt
        self.velocity *= 0.98
        return self.life > 0


@dataclass
class FogMote:
    pos: Vector2
    velocity: Vector2
    radius: float
    alpha: int

    def update(self, dt: float) -> None:
        self.pos += self.velocity * dt
        if self.pos.x < -200:
            self.pos.x = WORLD_WIDTH + 200
        if self.pos.x > WORLD_WIDTH + 200:
            self.pos.x = -200
        if self.pos.y < -200:
            self.pos.y = WORLD_HEIGHT + 200
        if self.pos.y > WORLD_HEIGHT + 200:
            self.pos.y = -200


@dataclass
class DamagePulse:
    pos: Vector2
    radius: float
    life: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.radius += 60 * dt
        return self.life > 0


@dataclass
class WorldFeature:
    kind: str
    pos: Vector2
    radius: float
    accent: float


@dataclass
class Building:
    uid: int
    kind: str
    pos: Vector2
    size: float
    assigned_to: str | None = None
    work_phase: float = 0.0


@dataclass
class BuildingRequest:
    uid: int
    requester_name: str
    kind: str
    label: str
    pos: Vector2
    size: float
    approved: bool = False
    progress: float = 0.0
    assigned_to: str | None = None


@dataclass
class ChiefTask:
    uid: int
    kind: str
    title: str
    description: str
    target: dict[str, object]
    reward: dict[str, object]
    progress: float = 0.0
    completed: bool = False
    claimed: bool = False


@dataclass
class InterestPoint:
    feature_kind: str
    event_kind: str
    label: str
    pos: Vector2
    radius: float
    pulse: float
    resolved: bool = False


@dataclass
class DynamicEvent:
    uid: int
    kind: str
    label: str
    pos: Vector2
    timer: float
    urgency: float
    target_name: str | None = None
    building_uid: int | None = None
    data: dict[str, object] = field(default_factory=dict)
    resolved: bool = False
