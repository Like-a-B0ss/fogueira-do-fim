from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Vector2

if TYPE_CHECKING:
    from ...core.models import ResourceNode
    from ...app.session import Game


def resource_node_bundle(game: "Game", node: "ResourceNode", *, role: str | None = None) -> dict[str, int]:
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


def bundle_summary(_game: "Game", bundle: dict[str, int]) -> str:
    labels = {
        "logs": "tora",
        "wood": "tabua",
        "food": "insumo",
        "herbs": "erva",
        "scrap": "sucata",
        "meals": "refeicao",
        "medicine": "remédio",
    }
    parts = [f"+{amount} {labels.get(resource, resource)}" for resource, amount in bundle.items() if amount > 0]
    return "  ".join(parts) if parts else "estoque cheio"


def tree_is_harvestable(_game: "Game", tree: dict[str, object]) -> bool:
    return bool(not tree.get("harvested", False))


def closest_available_tree(game: "Game", origin: Vector2) -> dict[str, object] | None:
    candidates = [tree for tree in game.trees if game.tree_is_harvestable(tree)]
    if not candidates:
        return None
    return min(candidates, key=lambda tree: Vector2(tree["pos"]).distance_to(origin))


def harvest_tree(game: "Game", tree: dict[str, object], *, effort: int = 1) -> int:
    if not game.tree_is_harvestable(tree):
        return 0
    effort_required = int(tree.get("effort_required", 2))
    effort_progress = int(tree.get("effort_progress", 0)) + max(1, effort)
    tree["effort_progress"] = effort_progress
    if effort_progress < effort_required:
        return 0
    tree["harvested"] = True
    return int(tree["wood_yield"])


def available_node(game: "Game", kind: str) -> bool:
    if kind == "wood":
        return any(game.tree_is_harvestable(tree) for tree in game.trees)
    return any(node.kind == kind and node.is_available() for node in game.resource_nodes)


def closest_available_node(game: "Game", kind: str, origin: Vector2) -> object | None:
    if kind == "wood":
        return game.closest_available_tree(origin)
    candidates = [node for node in game.resource_nodes if node.kind == kind and node.is_available()]
    if not candidates:
        return None
    return min(candidates, key=lambda node: node.pos.distance_to(origin))
