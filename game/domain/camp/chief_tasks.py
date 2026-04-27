from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.config import PALETTE, clamp
from ...core.models import ChiefTask

if TYPE_CHECKING:
    from ...app.session import Game


TASK_RESOURCE_KEYS = {"logs", "wood", "food", "herbs", "scrap", "meals", "medicine"}


def active_chief_tasks(game: "Game") -> list[ChiefTask]:
    return [task for task in game.chief_tasks if not task.claimed]


def chief_task_key(kind: str, target: dict[str, object]) -> tuple[str, str]:
    if "kind" in target:
        return kind, str(target["kind"])
    if "event_kind" in target:
        return kind, str(target["event_kind"])
    if "region_name" in target:
        return kind, str(target["region_name"])
    return kind, str(target.get("id", "global"))


def has_chief_task(game: "Game", kind: str, target: dict[str, object]) -> bool:
    key = chief_task_key(kind, target)
    for task in game.chief_tasks:
        if chief_task_key(task.kind, task.target) != key:
            continue
        if not task.claimed:
            return True
        if int(task.target.get("day", -1)) == int(game.day):
            return True
    return False


def create_chief_task(
    game: "Game",
    kind: str,
    title: str,
    description: str,
    target: dict[str, object],
    reward: dict[str, object],
) -> ChiefTask | None:
    if has_chief_task(game, kind, target):
        return None
    task = ChiefTask(
        uid=game.next_chief_task_uid,
        kind=kind,
        title=title,
        description=description,
        target={**dict(target), "day": int(game.day)},
        reward=dict(reward),
    )
    game.next_chief_task_uid += 1
    game.chief_tasks.append(task)
    return task


def generate_chief_tasks(game: "Game") -> None:
    game.chief_tasks = [
        task
        for task in game.chief_tasks
        if not (task.completed and task.claimed and int(task.target.get("day", -1)) < int(game.day) - 1)
    ]
    if len(active_chief_tasks(game)) >= 4:
        return

    active_event = game.active_dynamic_event()
    if active_event:
        create_chief_task(
            game,
            "resolve_crisis",
            "Responder a crise",
            f"Resolva: {active_event.label}",
            {"event_kind": active_event.kind},
            {"trust": 2, "morale": 2, "scrap": 1},
        )

    if game.bonfire_heat < 34 or game.bonfire_ember_bed < 24:
        create_chief_task(
            game,
            "tend_fire",
            "Reacender a fogueira",
            "Alimente a fogueira antes que o campo perca calor.",
            {"id": "bonfire"},
            {"morale": 2, "trust": 1},
        )

    weakest = game.weakest_barricade_health()
    if weakest < 68 and game.wood > 0:
        create_chief_task(
            game,
            "repair_barricade",
            "Segurar a palicada",
            "Reforce uma barricada ferida antes da próxima investida.",
            {"id": "barricade"},
            {"wood": 1, "trust": 1},
        )

    missing_buildings = [
        ("serraria", "Erguer serraria", "Construa uma serraria para transformar toras em tábuas."),
        ("cozinha", "Montar cozinha", "Construa uma cozinha para produzir refeicoes em lote."),
        ("enfermaria", "Levantar enfermaria", "Construa uma enfermaria para estabilizar feridos."),
    ]
    for kind, title, description in missing_buildings:
        if not game.buildings_of_kind(kind):
            create_chief_task(
                game,
                "build",
                title,
                description,
                {"kind": kind},
                {"trust": 2, "morale": 2, "scrap": 1},
            )
            break

    unresolved = game.unresolved_interest_points()
    if unresolved:
        create_chief_task(
            game,
            "explore_interest",
            "Investigar sinal",
            "Explore um sinal perdido além da névoa do mapa.",
            {"id": "interest"},
            {"food": 1, "trust": 1},
        )

    if game.best_expedition_region() and not game.active_expedition:
        create_chief_task(
            game,
            "launch_expedition",
            "Enviar expedição",
            "Use o rádio para mandar uma equipe a uma região conhecida.",
            {"id": "radio"},
            {"trust": 2, "morale": 1},
        )
    if game.active_expedition:
        create_chief_task(
            game,
            "return_expedition",
            "Receber a expedição",
            f"Acompanhe o retorno da equipe de {game.active_expedition['region_name']}.",
            {"region_name": str(game.active_expedition["region_name"])},
            {"trust": 2, "morale": 2, "medicine": 1},
        )


def update_chief_tasks(game: "Game") -> None:
    generate_chief_tasks(game)
    for task in list(active_chief_tasks(game)):
        if task.completed:
            continue
        if task.kind in {"tend_fire", "story_tend_fire"} and game.bonfire_heat >= 48 and game.bonfire_ember_bed >= 30:
            complete_chief_task(game, task)
        elif task.kind == "repair_barricade" and game.weakest_barricade_health() >= 72:
            complete_chief_task(game, task)
        elif task.kind == "build" and game.buildings_of_kind(str(task.target.get("kind", ""))):
            complete_chief_task(game, task)
        elif task.kind == "explore_interest" and not game.unresolved_interest_points():
            complete_chief_task(game, task)
        elif task.kind == "assign_guard" and any(
            getattr(survivor, "leader_directive", None) == "guard"
            for survivor in game.living_survivors()
        ):
            complete_chief_task(game, task)


def notify_chief_task_progress(game: "Game", task_kind: str, **target: object) -> None:
    for task in list(active_chief_tasks(game)):
        if task.completed or task.kind != task_kind:
            continue
        if task_kind == "build" and target.get("kind") != task.target.get("kind"):
            continue
        if task_kind == "resolve_crisis" and target.get("event_kind") != task.target.get("event_kind"):
            continue
        if "id" in task.target and "id" in target and target.get("id") != task.target.get("id"):
            continue
        complete_chief_task(game, task)


def complete_chief_task(game: "Game", task: ChiefTask) -> None:
    if task.completed:
        return
    task.progress = 1.0
    task.completed = True
    claim_chief_task_reward(game, task)


def claim_chief_task_reward(game: "Game", task: ChiefTask) -> None:
    if task.claimed:
        return
    reward = dict(task.reward)
    resource_reward = {
        key: int(value)
        for key, value in reward.items()
        if key in TASK_RESOURCE_KEYS and int(value) > 0
    }
    if resource_reward:
        stored = game.add_resource_bundle(resource_reward)
        if stored:
            game.spawn_floating_text(game.bundle_summary(stored), game.stockpile_pos, PALETTE["accent_soft"])

    trust_delta = float(reward.get("trust", 0.0))
    morale_delta = float(reward.get("morale", 0.0))
    if trust_delta or morale_delta:
        for survivor in game.living_survivors():
            if trust_delta:
                game.adjust_trust(survivor, trust_delta)
            if morale_delta:
                survivor.morale = clamp(survivor.morale + morale_delta, 0, 100)

    task.claimed = True
    game.set_event_message(f"Tarefa concluida: {task.title}. Recompensa aplicada.", duration=4.8)
    game.spawn_floating_text("tarefa concluida", game.player.pos, PALETTE["morale"])
