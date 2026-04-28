from __future__ import annotations

from typing import TYPE_CHECKING

from ..infrastructure.savegame_repository import SaveGameLoadError
from ..core.scenes import SceneId
from ..core.config import PALETTE
from ..domain.camp import chief_tasks

if TYPE_CHECKING:
    from ..app.session import Game


def reset_runtime_session(game: "Game", *, seed: int | None) -> None:
    runtime_settings = dict(game.runtime_settings)
    smoke_test = game.smoke_test
    game.__init__(seed=seed, smoke_test=smoke_test, reuse_display=True)
    game.runtime_settings.update(runtime_settings)
    game.audio.apply_settings(game.runtime_settings)


def configure_story_opening(game: "Game") -> None:
    game.time_minutes = 17 * 60 + 35
    game.previous_night = game.is_night
    game.bonfire_heat = min(game.bonfire_heat, 34.0)
    game.bonfire_ember_bed = min(game.bonfire_ember_bed, 22.0)
    game.spawn_budget = 0
    game.horde_active = False
    game.dynamic_event_cooldown = max(game.dynamic_event_cooldown, 42.0)
    game.event_message = "Uma voz no rádio: help. please help. child."
    game.event_timer = 12.0
    game.chat_messages = []
    game.add_chat_message(
        "system",
        "Você meses esqueceu como importar. Coletar, evitar risco, não se apegar - viraram lei.",
        PALETTE["muted"],
        source="system",
    )
    game.add_chat_message(
        "radio",
        "Then the radio cracked. A voice from the trees. Desperate. Asking for help.",
        PALETTE["accent_soft"],
        source="system",
    )
    game.add_chat_message(
        "menina",
        "Você vem? Please? A fogueira vai apagar.",
        PALETTE["morale"],
        source="npc",
    )
    for survivor in game.living_survivors():
        survivor.trust_leader = min(survivor.trust_leader, 58.0)
        survivor.morale = min(survivor.morale, 62.0)
        survivor.exhaustion = max(survivor.exhaustion, 28.0)

    chief_tasks.create_chief_task(
        game,
        "story_tend_fire",
        "Reacender a esperança",
        "A fogueira é o centro moral do grupo. Alimente-a antes que a noite caia.",
        {"id": "opening_fire"},
        {"morale": 2, "trust": 1, "wood": 1},
    )
    chief_tasks.create_chief_task(
        game,
        "talk_survivor",
        "Conhecer quem você protege",
        "Converse com um morador. Descubra seus nomes, medos e histórias.",
        {"id": "opening_talk"},
        {"morale": 1, "trust": 2},
    )
    chief_tasks.create_chief_task(
        game,
        "assign_guard",
        "Organizar a primeira vigia",
        "O grupo não sabe se defender. Mande alguém vigiar antes que os mortos cheguem.",
        {"id": "opening_guard"},
        {"trust": 2, "scrap": 1},
    )
    chief_tasks.create_chief_task(
        game,
        "survive_first_night",
        "Atravessar a primeira noite",
        "Sobreviver sozinho era simples. Agora você é responsável por todas essas vidas.",
        {"id": "opening_night"},
        {"morale": 4, "trust": 3, "meals": 1},
    )
    game.generate_chief_tasks()


def begin_new_game_flow(game: "Game") -> None:
    game.show_loading_screen(
        "O Chamado",
        "Uma voz no rádio quebrou seus meses de silêncio. Uma menina que precisava de ajuda.",
        progress=0.16,
        hold_seconds=0.34,
    )
    reset_runtime_session(game, seed=game.seed)
    configure_story_opening(game)
    game.update_loading_screen(
        subtitle="Atravessando o limiar: a primeira noite como líder.",
        progress=0.84,
        hold_seconds=0.24,
    )
    game.refresh_title_actions()
    game.begin_tips()
    game.complete_loading_transition(game.scenes.current_id, hold_frames=3)


def restart_game_flow(game: "Game") -> None:
    game.audio.play_transition("restart")
    game.show_loading_screen(
        "Remontando o acampamento",
        "Rebobinando a vigia e limpando a pressão da noite passada.",
        progress=0.2,
        hold_seconds=0.34,
    )
    reset_runtime_session(game, seed=game.seed)
    game.update_loading_screen(
        subtitle="A clareira foi refeita. Voltando para o começo da sessão.",
        progress=0.9,
        hold_seconds=0.24,
    )
    game.complete_loading_transition(SceneId.GAMEPLAY, hold_frames=3)


def load_saved_game_flow(game: "Game") -> tuple[bool, str]:
    if not game.save_exists():
        return False, "Nenhum save encontrado."
    previous_scene = game.scenes.current_id
    game.show_loading_screen(
        "Chamando o último fogo",
        "Lendo o save, recuperando moradores e reposicionando a noite.",
        progress=0.12,
        hold_seconds=0.34,
    )
    try:
        data = game.save_repository.load()
    except SaveGameLoadError:
        game.scenes.change(previous_scene)
        return False, "Save corrompido ou ilegível."
    game.update_loading_screen(
        subtitle="Reconstruindo o mundo salvo e religando a simulação.",
        progress=0.58,
        hold_seconds=0.2,
    )
    seed = data.get("seed", game.seed)
    resolved_seed = seed if isinstance(seed, int) or seed is None else None
    reset_runtime_session(game, seed=resolved_seed)
    game.update_loading_screen(
        subtitle="Aplicando estado do save e reacendendo a clareira.",
        progress=0.88,
        hold_seconds=0.24,
    )
    game.save_codec.apply(game, data)
    game.complete_loading_transition(SceneId.GAMEPLAY, hold_frames=3)
    game.set_event_message("Save carregado. A clareira voltou a respirar do ponto salvo.", duration=5.4)
    return True, "Save carregado."







