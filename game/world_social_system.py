from __future__ import annotations

from pygame import Vector2

from .config import PALETTE, clamp
from .models import DamagePulse


def relationship_score(_game, survivor_a, survivor_b) -> float:
    return survivor_a.relations.get(survivor_b.name, 0.0)


def adjust_relationship(_game, survivor_a, survivor_b, delta: float) -> None:
    survivor_a.relations[survivor_b.name] = clamp(survivor_a.relations.get(survivor_b.name, 0.0) + delta, -100, 100)
    survivor_b.relations[survivor_a.name] = clamp(survivor_b.relations.get(survivor_a.name, 0.0) + delta, -100, 100)


def adjust_trust(_game, survivor, delta: float) -> None:
    if survivor.has_trait("leal"):
        delta *= 1.12
    if survivor.has_trait("teimoso"):
        delta *= 0.9
    if survivor.has_trait("paranoico") and delta < 0:
        delta *= 1.22
    survivor.trust_leader = clamp(survivor.trust_leader + delta, 0, 100)


def impact_burst(
    game,
    origin: Vector2,
    color: tuple[int, int, int],
    *,
    radius: float = 12,
    shake: float = 0.0,
    ember_count: int = 0,
    smoky: bool = False,
) -> None:
    """Cria um pequeno feedback visual para golpes, reparos e eventos."""
    game.damage_pulses.append(DamagePulse(Vector2(origin), radius, 0.24, color))
    if radius >= 11:
        game.damage_pulses.append(DamagePulse(Vector2(origin), radius * 1.45, 0.18, color))
    if ember_count > 0:
        game.emit_embers(origin, ember_count, smoky=smoky)
    if shake > 0:
        game.screen_shake = max(game.screen_shake, shake)


def survivor_bark_options(game, survivor) -> list[tuple[str, tuple[int, int, int]]]:
    """Escolhe frases curtas que resumem o estado social do morador."""
    lines: list[tuple[str, tuple[int, int, int]]] = []
    crisis = game.dynamic_event_for_survivor(survivor)
    active_event = game.active_dynamic_event()
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

    if game.is_night and getattr(game, "horde_active", False):
        lines.extend((("Segura a linha!", PALETTE["danger_soft"]), ("A mata inteira ta vindo.", PALETTE["danger_soft"])))
    elif game.is_night and game.find_closest_zombie(survivor.pos, 150):
        lines.extend((("Contato perto da palicada.", PALETTE["danger_soft"]), ("Mortos na escuridao.", PALETTE["danger_soft"])))

    if game.bonfire_heat < 28 or game.bonfire_ember_bed < 18:
        lines.extend((("A fogueira ta morrendo.", PALETTE["morale"]), ("Sem fogo o campo desanda.", PALETTE["morale"])))
    if game.food + game.meals <= max(2, len(game.living_survivors()) // 2):
        lines.extend((("A panela ta vazia.", PALETTE["accent_soft"]), ("A fome vai virar briga.", PALETTE["accent_soft"])))
    if survivor.health < 42:
        lines.extend((("Preciso de curativo.", PALETTE["heal"]), ("Nao aguento mais um golpe.", PALETTE["heal"])))
    if survivor.insanity > 74:
        lines.extend((("A mata ta falando comigo.", PALETTE["morale"]), ("Tem olho demais na escuridao.", PALETTE["morale"])))
    if survivor.trust_leader < 34:
        lines.extend((("Chefe, voce sumiu demais.", PALETTE["muted"]), ("A gente ta segurando isso no osso.", PALETTE["muted"])))
    if survivor.has_trait("leal") and game.player.distance_to(survivor.pos) < 150:
        lines.extend((("Eu seguro contigo, chefe.", PALETTE["heal"]), ("Da a ordem que eu vou.", PALETTE["heal"])))
    if survivor.has_trait("sociavel") and game.player.distance_to(game.bonfire_pos) < 180:
        lines.extend((("Fica perto do fogo com a gente.", PALETTE["morale"]), ("Uma historia segura mais que faca.", PALETTE["morale"])))
    if survivor.has_trait("paranoico") and game.is_night:
        lines.extend((("Tem coisa na linha das arvores.", PALETTE["danger_soft"]), ("Nao confio nesse silencio.", PALETTE["danger_soft"])))

    friend = game.best_friend_name(survivor)
    rival = game.rival_name(survivor)
    if friend and survivor.morale > 58 and game.random.random() < 0.35:
        lines.append((f"{friend} ainda segura meu juizo.", PALETTE["accent_soft"]))
    if rival and survivor.conflict_cooldown <= 0 and game.random.random() < 0.28:
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
    game,
    survivor,
    text: str,
    color: tuple[int, int, int],
    *,
    duration: float = 2.8,
) -> None:
    survivor.bark_text = text
    survivor.bark_color = color
    survivor.bark_timer = duration
    survivor.bark_cooldown = game.random.uniform(5.0, 10.0)
    if hasattr(game, "add_chat_message"):
        game.add_chat_message(survivor.name, text, color, source="npc")


def survivors_react_to_event(game, event, *, resolved: bool | None = None) -> None:
    living = [survivor for survivor in game.living_survivors() if survivor.distance_to(event.pos) < 240]
    if not living:
        living = game.living_survivors()
    if not living:
        return
    game.random.shuffle(living)
    event_reactions = {
        "incendio": ("Resolveu o fogo!", PALETTE["heal"]) if resolved else ("Fogo no campo!", PALETTE["danger_soft"]),
        "doenca": ("Ele vai segurar.", PALETTE["heal"]) if resolved else ("A febre pegou feio.", PALETTE["danger_soft"]),
        "fuga": ("Ele voltou pro anel.", PALETTE["morale"]) if resolved else ("A mata engoliu ele.", PALETTE["danger_soft"]),
        "desercao": ("Ainda ficamos inteiros.", PALETTE["morale"]) if resolved else ("Perdemos mais um.", PALETTE["danger_soft"]),
        "abrigo": ("Tem mais um no fogo.", PALETTE["morale"]) if resolved else ("Ele seguiu sozinho.", PALETTE["muted"]),
        "expedicao": ("A trilha respondeu.", PALETTE["heal"]) if resolved else ("A rota ficou pior.", PALETTE["danger_soft"]),
        "faccao": ("Eles vao lembrar disso.", PALETTE["accent_soft"]) if resolved else ("Ninguem sai limpo disso.", PALETTE["muted"]),
        "alarme": ("Linha segura por enquanto.", PALETTE["heal"]) if resolved else ("Eles acharam a cerca.", PALETTE["danger_soft"]),
    }
    text, color = event_reactions.get(event.kind, ("Segura firme.", PALETTE["text"]))
    for survivor in living[:2]:
        trigger_survivor_bark(game, survivor, text, color, duration=2.4)


def update_survivor_barks(game, dt: float) -> None:
    game.bark_timer = max(0.0, getattr(game, "bark_timer", 0.0) - dt)
    if game.bark_timer > 0:
        return
    candidates = [
        survivor
        for survivor in game.living_survivors()
        if survivor.bark_timer <= 0 and survivor.bark_cooldown <= 0 and game.player.distance_to(survivor.pos) < 240
    ]
    if not candidates:
        game.bark_timer = game.random.uniform(1.6, 3.2)
        return
    weighted = sorted(
        candidates,
        key=lambda survivor: (
            game.dynamic_event_for_survivor(survivor) is None,
            survivor.insanity,
            -survivor.trust_leader,
            -survivor.morale,
        ),
    )
    chosen = weighted[0]
    text, color = game.random.choice(game.survivor_bark_options(chosen))
    game.trigger_survivor_bark(chosen, text, color)
    game.bark_timer = game.random.uniform(2.8, 5.8)


def average_trust(game) -> float:
    alive = [survivor.trust_leader for survivor in game.survivors if survivor.is_alive()]
    return sum(alive) / len(alive) if alive else 0.0


def friendship_count(game) -> int:
    names_seen: set[tuple[str, str]] = set()
    total = 0
    for survivor in game.living_survivors():
        for other_name, score in survivor.relations.items():
            if score < 50:
                continue
            key = tuple(sorted((survivor.name, other_name)))
            if key in names_seen:
                continue
            names_seen.add(key)
            total += 1
    return total


def feud_count(game) -> int:
    names_seen: set[tuple[str, str]] = set()
    total = 0
    for survivor in game.living_survivors():
        for other_name, score in survivor.relations.items():
            if score > -45:
                continue
            key = tuple(sorted((survivor.name, other_name)))
            if key in names_seen:
                continue
            names_seen.add(key)
            total += 1
    return total


def best_friend_name(game, survivor) -> str | None:
    positives = [(name, score) for name, score in survivor.relations.items() if score > 24]
    if not positives:
        return None
    return max(positives, key=lambda item: item[1])[0]


def rival_name(game, survivor) -> str | None:
    negatives = [(name, score) for name, score in survivor.relations.items() if score < -18]
    if not negatives:
        return None
    return min(negatives, key=lambda item: item[1])[0]


def initialize_survivor_relationships(game) -> None:
    for survivor in game.survivors:
        survivor.relations = {
            other.name: survivor.relations.get(other.name, 0.0)
            for other in game.survivors
            if other is not survivor
        }

    for index, survivor in enumerate(game.survivors):
        for other in game.survivors[index + 1 :]:
            if other.name in survivor.relations and abs(survivor.relations[other.name]) > 0.01:
                continue
            score = game.random.uniform(-8, 12)
            if survivor.role == other.role:
                score += 6
            if set(survivor.traits) & set(other.traits):
                score += 7
            if survivor.has_trait("sociavel") or other.has_trait("sociavel"):
                score += 5
            if survivor.has_trait("rancoroso") or other.has_trait("rancoroso"):
                score -= 6
            if survivor.has_trait("paranoico") and other.has_trait("paranoico"):
                score -= 4
            if survivor.has_trait("gentil") and other.has_trait("gentil"):
                score += 4
            game.adjust_relationship(survivor, other, score)


def update_social_dynamics(game, dt: float) -> None:
    """Atualiza amizade, conflitos e pressao social ao longo do tempo."""
    game.social_timer -= dt
    if game.social_timer > 0:
        return
    game.social_timer = game.random.uniform(2.8, 4.8)
    living = game.living_survivors()
    if not living:
        return

    pressure = 0.0
    if game.bonfire_heat < 28 or game.bonfire_ember_bed < 18:
        pressure += 0.35
    if game.weakest_barricade_health() < 48:
        pressure += 0.25
    if game.meals <= max(1, len(living) // 3):
        pressure += 0.2
    if len(game.zombies) >= 5:
        pressure += 0.25
    if getattr(game, "horde_active", False):
        pressure += 0.36

    for survivor in living:
        drift = 0.0
        if game.player.distance_to(survivor.pos) < 130:
            drift += 0.45
        if game.average_morale() < 45:
            drift -= 0.3
        drift -= pressure * 0.55
        drift -= survivor.exhaustion / 320
        if survivor.has_trait("paranoico"):
            drift -= 0.15
        if survivor.has_trait("leal"):
            drift += 0.18
        game.adjust_trust(survivor, drift)
        insanity_shift = pressure * 5.2 + (0.8 if survivor.has_trait("paranoico") else 0.0)
        insanity_shift += max(0.0, 48 - survivor.morale) * 0.035
        insanity_shift += max(0.0, survivor.exhaustion - 58) * 0.03
        if game.player.distance_to(survivor.pos) < 150:
            insanity_shift -= 1.0
        if survivor.state in {"sleep", "rest", "socialize"}:
            insanity_shift -= 1.6
        survivor.insanity = clamp(survivor.insanity + insanity_shift, 0, 100)

    close_pairs = [
        (a, b)
        for index, a in enumerate(living)
        for b in living[index + 1 :]
        if a.distance_to(b.pos) < 84
    ]
    game.random.shuffle(close_pairs)

    for survivor_a, survivor_b in close_pairs[:4]:
        relation = game.relationship_score(survivor_a, survivor_b)
        same_zone = survivor_a.distance_to(game.bonfire_pos) < 180 and survivor_b.distance_to(game.bonfire_pos) < 180
        same_job = survivor_a.state == survivor_b.state and survivor_a.state not in {"guard", "watchtower"}
        tension = (
            pressure
            + (survivor_a.exhaustion + survivor_b.exhaustion) / 180
            + (0.18 if survivor_a.has_trait("rancoroso") or survivor_b.has_trait("rancoroso") else 0.0)
            + (0.12 if survivor_a.has_trait("teimoso") and survivor_b.has_trait("teimoso") else 0.0)
        )

        if relation <= -36 and survivor_a.conflict_cooldown <= 0 and survivor_b.conflict_cooldown <= 0:
            chance = 0.08 + max(0.0, -relation - 36) * 0.002 + tension * 0.08
            if game.random.random() < chance:
                game.adjust_relationship(survivor_a, survivor_b, -6.5)
                survivor_a.morale = clamp(survivor_a.morale - 8, 0, 100)
                survivor_b.morale = clamp(survivor_b.morale - 8, 0, 100)
                survivor_a.energy = clamp(survivor_a.energy - 5, 0, 100)
                survivor_b.energy = clamp(survivor_b.energy - 5, 0, 100)
                game.adjust_trust(survivor_a, -1.8)
                game.adjust_trust(survivor_b, -1.8)
                survivor_a.conflict_cooldown = 18.0
                survivor_b.conflict_cooldown = 18.0
                survivor_a.state_label = "discutindo"
                survivor_b.state_label = "discutindo"
                survivor_a.decision_timer = max(survivor_a.decision_timer, 1.6)
                survivor_b.decision_timer = max(survivor_b.decision_timer, 1.6)
                midpoint = survivor_a.pos.lerp(survivor_b.pos, 0.5)
                game.spawn_floating_text("briga", midpoint, PALETTE["danger_soft"])
                game.set_event_message(f"{survivor_a.name} e {survivor_b.name} bateram de frente no campo.", duration=4.8)
                continue

        if relation >= 30 and same_zone and survivor_a.bond_cooldown <= 0 and survivor_b.bond_cooldown <= 0:
            chance = 0.08 + max(0.0, relation - 30) * 0.0015
            if game.random.random() < chance:
                gain = 2.4 if survivor_a.has_trait("sociavel") or survivor_b.has_trait("sociavel") else 1.6
                game.adjust_relationship(survivor_a, survivor_b, gain)
                survivor_a.morale = clamp(survivor_a.morale + 3, 0, 100)
                survivor_b.morale = clamp(survivor_b.morale + 3, 0, 100)
                survivor_a.bond_cooldown = 16.0
                survivor_b.bond_cooldown = 16.0
                game.spawn_floating_text("amizade", survivor_a.pos.lerp(survivor_b.pos, 0.5), PALETTE["morale"])
                continue

        if same_job and relation < 20:
            game.adjust_relationship(survivor_a, survivor_b, 0.8)


def assign_building_specialists(game) -> None:
    for building in game.buildings:
        building.assigned_to = None
    for survivor in game.survivors:
        survivor.assigned_building_id = None
        survivor.assigned_building_kind = None

    available = [survivor for survivor in game.survivors if survivor.is_alive() and not game.is_survivor_on_expedition(survivor)]
    taken: set[str] = set()
    role_priority = {"vigia": 0, "cozinheiro": 1, "lenhador": 2, "mensageiro": 3, "artesa": 4}
    for building in sorted(game.buildings, key=lambda item: role_priority.get(game.build_specialty_role(item.kind) or "", 99)):
        needed_role = game.build_specialty_role(building.kind)
        if not needed_role:
            building.assigned_to = None
            continue
        candidates = [survivor for survivor in available if survivor.name not in taken and survivor.role == needed_role]
        if not candidates:
            candidates = [survivor for survivor in available if survivor.name not in taken and survivor.energy > 28]
        if not candidates:
            building.assigned_to = None
            continue
        chosen = max(candidates, key=lambda survivor: (survivor.energy, survivor.morale))
        chosen.assigned_building_id = building.uid
        chosen.assigned_building_kind = building.kind
        building.assigned_to = chosen.name
        taken.add(chosen.name)


def active_guard_names(game) -> set[str]:
    living = [survivor for survivor in game.survivors if survivor.is_alive() and not game.is_survivor_on_expedition(survivor)]
    if not living:
        return set()
    ordered = sorted(
        living,
        key=lambda survivor: (
            survivor.role != "vigia",
            survivor.assigned_building_kind != "torre",
            getattr(survivor, "assigned_tent_index", 0),
            survivor.name,
        ),
    )
    desired = 2 + game.building_count("torre") + (1 if len(living) >= 8 else 0) + (1 if game.camp_level >= 2 else 0)
    shift_index = int((game.time_minutes % (24 * 60)) / 150)
    rotation = shift_index % len(ordered)
    rotated = ordered[rotation:] + ordered[:rotation]
    ready = [survivor for survivor in rotated if survivor.energy > 18 and getattr(survivor, "exhaustion", 0.0) < 76]
    roster = ready if len(ready) >= desired else rotated
    return {survivor.name for survivor in roster[:desired]}


def should_survivor_sleep(game, survivor) -> bool:
    time_value = game.time_minutes % (24 * 60)
    deep_night = time_value >= 21 * 60 or time_value < 5 * 60 + 30
    afternoon_lull = 13 * 60 <= time_value < 15 * 60
    on_guard = survivor.name in game.active_guard_names()
    if deep_night and not on_guard:
        return True
    if getattr(survivor, "sleep_debt", 0.0) > 58:
        return True
    if getattr(survivor, "exhaustion", 0.0) > 74:
        return True
    if afternoon_lull and survivor.energy < 54 and getattr(survivor, "sleep_debt", 0.0) > 30:
        return True
    return survivor.energy < 22
