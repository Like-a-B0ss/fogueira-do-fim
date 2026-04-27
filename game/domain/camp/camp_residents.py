from __future__ import annotations

from pygame import Vector2

from ...core.config import PALETTE
from ...entities import Survivor
from . import camp_social


def most_injured_actor(world):
    candidates = [world.player]
    candidates.extend(world.living_survivors())
    wounded = [actor for actor in candidates if actor.health < actor.max_health - 6]
    if not wounded:
        return None
    return min(wounded, key=lambda actor: actor.health / max(1, actor.max_health))


def has_medical_supplies(world) -> bool:
    return world.medicine > 0 or world.herbs > 0


def can_treat_infirmary(world) -> bool:
    return bool(world.buildings_of_kind("enfermaria") and world.has_medical_supplies())


def sync_survivor_assignments(world) -> None:
    guard_posts = world.guard_posts()
    sleep_slots = world.camp_sleep_slots()
    for index, survivor in enumerate(world.survivors):
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


def resolve_actor_camp_collision(world, actor) -> None:
    allow_kind = None
    allow_index = None
    allow_building_uid = None
    state = getattr(actor, "state", "")
    if actor is world.player and getattr(world, "player_sleeping", False):
        slot = getattr(world, "player_sleep_slot", None)
        if slot:
            allow_kind = str(slot["kind"])
            allow_index = int(slot["index"])
            allow_building_uid = slot["building_uid"]
    elif state in {"sleep", "rest", "shelter"}:
        allow_kind = str(getattr(actor, "sleep_slot_kind", "tent"))
        allow_index = int(getattr(actor, "assigned_tent_index", 0))
        allow_building_uid = getattr(actor, "sleep_slot_building_uid", None)

    for slot in world.camp_sleep_slots():
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


def generate_survivors(world) -> list[Survivor]:
    survivors = []
    initial_population = 6
    sleep_slots = world.camp_sleep_slots()
    for index, profile in enumerate(world.recruit_pool[:initial_population]):
        slot = sleep_slots[index]
        guard_pos = world.guard_posts()[index % len(world.guard_posts())]
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
    world.next_recruit_index = len(survivors)
    return survivors


def recruit_survivor_from_profile(
    world,
    profile: dict[str, object],
    *,
    announce_message: str,
    floating_label: str = "novo morador",
):
    sleep_slots = world.camp_sleep_slots()
    if world.spare_beds() <= 0 or len(world.survivors) >= len(sleep_slots):
        return None
    slot = sleep_slots[len(world.survivors)]
    guard_pos = world.guard_posts()[len(world.survivors) % len(world.guard_posts())]
    newcomer = Survivor(
        str(profile["name"]),
        str(profile["role"]),
        Vector2(slot["sleep_pos"]),
        Vector2(slot["sleep_pos"]),
        Vector2(guard_pos),
        tuple(profile.get("traits", ())),
    )
    world.survivors.append(newcomer)
    world.sync_survivor_assignments()
    world.initialize_survivor_relationships()
    world.set_event_message(announce_message, duration=6.2)
    world.spawn_floating_text(floating_label, newcomer.pos, PALETTE["morale"])
    return newcomer


def remove_survivor(world, survivor) -> None:
    camp_social.remember_survivor_loss(world, survivor.name)
    world.survivors = [member for member in world.survivors if member is not survivor]
    for member in world.survivors:
        member.relations.pop(survivor.name, None)
    world.sync_survivor_assignments()
    world.assign_building_specialists()


def try_recruit_survivor(world) -> None:
    if world.spare_beds() <= 0 or world.next_recruit_index >= len(world.recruit_pool):
        return
    if any(event.kind == "abrigo" for event in world.active_dynamic_events):
        return
    if world.average_morale() < 54 or world.weakest_barricade_health() < 42:
        return
    arrival_chance = 0.36 + world.camp_level * 0.12
    if world.random.random() > arrival_chance:
        return

    profile = world.recruit_pool[world.next_recruit_index]
    world.next_recruit_index += 1
    world.recruit_survivor_from_profile(
        profile,
        announce_message=f"{profile['name']} encontrou cama e entrou para a clareira.",
    )









