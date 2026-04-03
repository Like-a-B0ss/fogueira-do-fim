from __future__ import annotations

from typing import TYPE_CHECKING

from ..infrastructure.savegame_repository import SaveGameLoadError
from ..core.scenes import SceneId

if TYPE_CHECKING:
    from ..app.session import Game


def reset_runtime_session(game: "Game", *, seed: int | None) -> None:
    runtime_settings = dict(game.runtime_settings)
    smoke_test = game.smoke_test
    game.__init__(seed=seed, smoke_test=smoke_test)
    game.runtime_settings.update(runtime_settings)
    game.audio.apply_settings(game.runtime_settings)


def begin_new_game_flow(game: "Game") -> None:
    reset_runtime_session(game, seed=game.seed)
    game.refresh_title_actions()
    game.begin_tips()


def restart_game_flow(game: "Game") -> None:
    game.audio.play_transition("restart")
    reset_runtime_session(game, seed=game.seed)


def load_saved_game_flow(game: "Game") -> tuple[bool, str]:
    if not game.save_exists():
        return False, "Nenhum save encontrado."
    try:
        data = game.save_repository.load()
    except SaveGameLoadError:
        return False, "Save corrompido ou ilegivel."
    seed = data.get("seed", game.seed)
    resolved_seed = seed if isinstance(seed, int) or seed is None else None
    reset_runtime_session(game, seed=resolved_seed)
    game.save_codec.apply(game, data)
    game.scenes.change(SceneId.GAMEPLAY)
    game.set_event_message("Save carregado. A clareira voltou a respirar do ponto salvo.", duration=5.4)
    return True, "Save carregado."







