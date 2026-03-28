from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SceneId(str, Enum):
    TITLE = "title"
    GAMEPLAY = "playing"
    GAME_OVER = "game_over"


@dataclass(frozen=True)
class SceneDefinition:
    scene_id: SceneId
    allows_world_update: bool
    overlay: str | None = None


SCENE_LIBRARY = {
    SceneId.TITLE: SceneDefinition(SceneId.TITLE, allows_world_update=False, overlay="title"),
    SceneId.GAMEPLAY: SceneDefinition(SceneId.GAMEPLAY, allows_world_update=True, overlay=None),
    SceneId.GAME_OVER: SceneDefinition(SceneId.GAME_OVER, allows_world_update=False, overlay="game_over"),
}


class SceneManager:
    def __init__(self, start_scene: SceneId) -> None:
        self.current = SCENE_LIBRARY[start_scene]

    @property
    def current_id(self) -> SceneId:
        return self.current.scene_id

    @property
    def current_name(self) -> str:
        return self.current.scene_id.value

    @property
    def allows_world_update(self) -> bool:
        return self.current.allows_world_update

    def change(self, scene_id: SceneId | str) -> None:
        if isinstance(scene_id, str):
            scene_id = SceneId(scene_id)
        self.current = SCENE_LIBRARY[scene_id]

    def is_gameplay(self) -> bool:
        return self.current.scene_id is SceneId.GAMEPLAY

    def is_title(self) -> bool:
        return self.current.scene_id is SceneId.TITLE

    def is_game_over(self) -> bool:
        return self.current.scene_id is SceneId.GAME_OVER
