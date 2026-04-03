from __future__ import annotations

from pygame import Vector2

from .config import clamp


class CameraRig:
    def __init__(self, viewport_width: int, viewport_height: int, world_width: int, world_height: int, *, bounded: bool = True) -> None:
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.world_width = world_width
        self.world_height = world_height
        self.bounded = bounded
        self.position = Vector2()

    @property
    def x(self) -> float:
        return self.position.x

    @property
    def y(self) -> float:
        return self.position.y

    def center_on(self, target: Vector2) -> None:
        target_camera = Vector2(
            target.x - self.viewport_width / 2,
            target.y - self.viewport_height / 2,
        )
        if not self.bounded:
            self.position = target_camera
            return
        self.position = Vector2(
            clamp(target_camera.x, 0, self.world_width - self.viewport_width),
            clamp(target_camera.y, 0, self.world_height - self.viewport_height),
        )

    def snap_to(self, top_left: Vector2) -> None:
        if not self.bounded:
            self.position = Vector2(top_left)
            return
        self.position = Vector2(
            clamp(top_left.x, 0, self.world_width - self.viewport_width),
            clamp(top_left.y, 0, self.world_height - self.viewport_height),
        )

    def screen_to_world(self, position: Vector2) -> Vector2:
        return Vector2(position) + self.position

    def world_to_screen(self, position: Vector2) -> Vector2:
        return Vector2(position) - self.position








