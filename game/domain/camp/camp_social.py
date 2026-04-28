from __future__ import annotations

from pygame import Vector2

from ...core.config import PALETTE, clamp
from ...core.models import DamagePulse


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


def remember_social_event(
    _game,
    survivor,
    text: str,
    color: tuple[int, int, int],
    *,
    topic: str = "general",
    impact: float = 0.0,
    duration: float = 120.0,
) -> None:
    memory = {
        "text": str(text),
        "color": tuple(color),
        "topic": str(topic),
        "impact": float(impact),
        "timer": float(duration),
    }
    memories = list(getattr(survivor, "social_memories", []))
    memories.append(memory)
    survivor.social_memories = memories[-8:]


def latest_social_memory(survivor, topic: str | None = None) -> dict[str, object] | None:
    memories = list(getattr(survivor, "social_memories", []))
    if topic is not None:
        memories = [memory for memory in memories if memory.get("topic") == topic]
    memories = [memory for memory in memories if float(memory.get("timer", 0.0)) > 0.0]
    if not memories:
        return None
    return max(memories, key=lambda memory: (abs(float(memory.get("impact", 0.0))), float(memory.get("timer", 0.0))))


def remember_leader_trust_state(game, survivor) -> None:
    if survivor.trust_leader >= 78 and latest_social_memory(survivor, "leader_trust") is None:
        remember_social_event(
            game,
            survivor,
            "O chefe cumpriu comigo. Eu sigo essa voz.",
            PALETTE["heal"],
            topic="leader_trust",
            impact=2.4,
            duration=260.0,
        )
    elif survivor.trust_leader <= 24 and latest_social_memory(survivor, "leader_doubt") is None:
        remember_social_event(
            game,
            survivor,
            "Não sei se o chefe ainda enxerga a gente.",
            PALETTE["danger_soft"],
            topic="leader_doubt",
            impact=-2.4,
            duration=260.0,
        )


def remember_survivor_loss(game, lost_name: str, witnesses: list[object] | None = None) -> None:
    candidates = witnesses if witnesses is not None else game.living_survivors()
    for survivor in candidates:
        if not survivor.is_alive() or survivor.name == lost_name:
            continue
        relation = survivor.relations.get(lost_name, 0.0)
        if relation > 24:
            text = f"{lost_name} era meu amigo. A clareira ficou menor."
            impact = -3.2
        elif relation < -24:
            text = f"Até {lost_name} sumiu. Ninguém está seguro aqui."
            impact = -1.4
        else:
            text = f"{lost_name} não voltou. Isso pesa no campo."
            impact = -2.1
        remember_social_event(
            game,
            survivor,
            text,
            PALETTE["danger_soft"],
            topic="loss",
            impact=impact,
            duration=280.0,
        )


def social_memory_bias(survivor, *, topic: str | None = None) -> float:
    memories = list(getattr(survivor, "social_memories", []))
    if topic is not None:
        memories = [memory for memory in memories if memory.get("topic") == topic]
    if not memories:
        return 0.0
    weighted_total = 0.0
    total_weight = 0.0
    for memory in memories:
        timer = clamp(float(memory.get("timer", 0.0)) / 120.0, 0.15, 1.0)
        weight = abs(float(memory.get("impact", 0.0))) * timer + 0.3
        weighted_total += float(memory.get("impact", 0.0)) * weight
        total_weight += weight
    return weighted_total / max(0.001, total_weight)


def social_summary_text(game, survivor) -> tuple[str, tuple[int, int, int]]:
    memory = latest_social_memory(survivor)
    if memory:
        return str(memory.get("text", "")), tuple(memory.get("color", PALETTE["text"]))
    friend = game.best_friend_name(survivor)
    rival = game.rival_name(survivor)
    if rival and relationship_score(game, survivor, next((other for other in game.survivors if other.name == rival), survivor)) < -35:
        return f"Ainda estou atravessado com {rival}.", PALETTE["danger_soft"]
    if friend and survivor.morale > 55:
        return f"{friend} ainda me mantem no eixo.", PALETTE["accent_soft"]
    if survivor.trust_leader < 34:
        return "Ainda estou segurando isso no osso.", PALETTE["muted"]
    return "Ainda estou em pe.", PALETTE["text"]


def ambient_conversation_lines(game, survivor_a, survivor_b) -> tuple[str, str, tuple[int, int, int], str, float]:
    relation = relationship_score(game, survivor_a, survivor_b)
    low_food = game.food + game.meals <= max(2, len(game.living_survivors()) // 2)
    low_fire = game.bonfire_heat < 32 or game.bonfire_ember_bed < 20
    night = getattr(game, "is_night", False)

    if relation >= 42:
        if low_fire:
            return (
                "Fica perto. O fogo baixo deixa tudo maior.",
                "Eu fico. Só não deixa eu pensar sozinho.",
                PALETTE["morale"],
                "bond",
                1.2,
            )
        if low_food:
            return (
                "Quando a comida voltar, eu divido minha parte com você.",
                "Guarda promessa para quando tiver prato. Mas eu ouvi.",
                PALETTE["accent_soft"],
                "bond",
                1.0,
            )
        return (
            "Lembra de quando a gente achava silêncio bom?",
            "Lembro. Hoje silêncio precisa provar que não morde.",
            PALETTE["morale"],
            "bond",
            1.1,
        )

    if relation <= -30:
        return (
            "Você pisa como se o campo fosse seu.",
            "E você reclama como se isso levantasse cerca.",
            PALETTE["danger_soft"],
            "feud",
            -1.1,
        )

    if night:
        return (
            "Você também ouviu isso na linha das árvores?",
            "Ouvi. Fala baixo e continua andando.",
            PALETTE["muted"],
            "fear",
            -0.4,
        )
    if survivor_a.state == survivor_b.state and survivor_a.state not in {"idle", "sleep"}:
        return (
            "Se a gente terminar isso junto, sobra um pouco de força.",
            "Então não para. Eu acompanho.",
            PALETTE["accent_soft"],
            "work",
            0.6,
        )
    return (
        "Você ainda pensa em antes?",
        "Penso. Só tento não morar lá.",
        PALETTE["text"],
        "past",
        0.4,
    )


def maybe_start_ambient_conversation(game, survivor_a, survivor_b, relation: float, pressure: float) -> bool:
    if survivor_a.social_comment_cooldown > 0 or survivor_b.social_comment_cooldown > 0:
        return False
    if survivor_a.state in {"sleep", "guard", "watchtower"} or survivor_b.state in {"sleep", "guard", "watchtower"}:
        return False
    chance = 0.035
    if survivor_a.distance_to(game.bonfire_pos) < 190 and survivor_b.distance_to(game.bonfire_pos) < 190:
        chance += 0.035
    if relation >= 35:
        chance += 0.03
    elif relation <= -28:
        chance += 0.018 + pressure * 0.02
    if game.random.random() >= chance:
        return False

    first, second, color, topic, impact = ambient_conversation_lines(game, survivor_a, survivor_b)
    trigger_survivor_bark(game, survivor_a, first, color, duration=3.2)
    if game.random.random() < 0.86:
        game.add_chat_message(survivor_b.name, second, color, source="npc")
    remember_social_event(game, survivor_a, f"{survivor_b.name}: {second}", color, topic=topic, impact=impact, duration=150.0)
    remember_social_event(game, survivor_b, f"{survivor_a.name}: {first}", color, topic=topic, impact=impact, duration=150.0)
    adjust_relationship(game, survivor_a, survivor_b, clamp(impact, -1.2, 1.4))
    survivor_a.social_comment_cooldown = game.random.uniform(18.0, 30.0)
    survivor_b.social_comment_cooldown = game.random.uniform(18.0, 30.0)
    return True


def contextual_build_request_reason(game, survivor, kind: str) -> tuple[str, str]:
    friend = game.best_friend_name(survivor)
    rival = game.rival_name(survivor)
    if kind == "barraca":
        bark = "Chefe, a gente ta dormindo apertado."
        reason = "faltam leitos e o acampamento esta espremido"
        if friend:
            reason = f"faltam leitos e {friend} ja esta virando a noite sem canto"
        return bark, reason
    if kind == "serraria":
        bark = "Chefe, sem serraria a madeira emperra."
        reason = "as toras estao chegando cruas demais para a oficina segurar"
        return bark, reason
    if kind == "cozinha":
        bark = "Chefe, precisamos de cozinha de verdade."
        reason = "a comida esta curta e o campo precisa de refeicao mais firme"
        return bark, reason
    if kind == "enfermaria":
        bark = "Chefe, precisamos de enfermaria."
        reason = "os feridos e a pressão da mata pedem cuidado mais sério"
        return bark, reason
    if kind == "horta":
        bark = "Chefe, a terra podia trabalhar pra gente."
        reason = "a panela esta vazia demais para depender so da mata"
        if rival and survivor.has_trait("paranoico"):
            reason = f"a panela esta vazia e {rival} ja esta ficando sem paciencia com a fome"
        return bark, reason
    if kind == "anexo":
        bark = "Chefe, a linha precisa de apoio."
        reason = "as barricadas estao sentindo o peso e falta manutencao perto da cerca"
        return bark, reason
    if kind == "torre":
        bark = "Chefe, precisamos de olho alto na mata."
        reason = "a cerca precisa ler a trilha antes do impacto chegar"
        return bark, reason
    return f"Chefe, precisamos de {kind}.", "essa obra ajudaria a clareira a respirar melhor"


def survivor_by_name(game, name: str | None):
    if not name:
        return None
    return next((survivor for survivor in game.survivors if survivor.name == name and survivor.is_alive()), None)


def directive_compliance_modifier(game, survivor, directive: str) -> float:
    modifier = 0.0
    modifier += social_memory_bias(survivor) * 0.045
    if directive == "rest" and (survivor.exhaustion > 62 or survivor.sleep_debt > 44):
        modifier += 0.12
    if directive in {"guard", "repair"} and latest_social_memory(survivor, "alarme"):
        modifier += 0.08
    if directive in {"wood", "food"} and latest_social_memory(survivor, "feud"):
        modifier -= 0.05
    if latest_social_memory(survivor, "leader_trust"):
        modifier += 0.09
    if latest_social_memory(survivor, "leader_doubt"):
        modifier -= 0.1
    if latest_social_memory(survivor, "loss") and directive not in {"rest", "clinic", "fire"}:
        modifier -= 0.05
    if latest_social_memory(survivor, "expedition_saved") and directive in {"guard", "repair", "food"}:
        modifier += 0.06
    if survivor.trust_leader < 30 and directive not in {"rest", "fire"}:
        modifier -= 0.06
    return modifier


def nearby_assignment_affinity(game, survivor, building) -> float:
    score = 0.0
    for other_building in game.buildings:
        if other_building.uid == building.uid or not other_building.assigned_to:
            continue
        if other_building.pos.distance_to(building.pos) > 120:
            continue
        other = survivor_by_name(game, other_building.assigned_to)
        if not other or other.name == survivor.name:
            continue
        relation = relationship_score(game, survivor, other)
        score += relation * 0.06
    return score


def survivor_bark_options(game, survivor) -> list[tuple[str, tuple[int, int, int]]]:
    """Escolhe frases curtas que resumem o estado social do morador."""
    lines: list[tuple[str, tuple[int, int, int]]] = []
    crisis = game.dynamic_event_for_survivor(survivor)
    active_event = game.active_dynamic_event()
    if crisis and crisis.kind == "doenca":
        lines.extend((("Tô queimando por dentro.", PALETTE["danger_soft"]), ("Não me deixa apagar aqui.", PALETTE["danger_soft"])))
    elif crisis and crisis.kind in {"fuga", "desercao"}:
        lines.extend((("Não dá mais pra segurar!", PALETTE["danger_soft"]), ("Eu preciso sumir da trilha.", PALETTE["danger_soft"])))
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
        lines.extend((("Preciso de curativo.", PALETTE["heal"]), ("Não aguento mais um golpe.", PALETTE["heal"])))
    if survivor.insanity > 74:
        lines.extend((("A mata ta falando comigo.", PALETTE["morale"]), ("Tem olho demais na escuridao.", PALETTE["morale"])))
    if survivor.trust_leader < 34:
        lines.extend((("Chefe, você sumiu demais.", PALETTE["muted"]), ("A gente tá segurando isso no osso.", PALETTE["muted"])))
    if survivor.has_trait("leal") and game.player.distance_to(survivor.pos) < 150:
        lines.extend((("Eu seguro contigo, chefe.", PALETTE["heal"]), ("Da a ordem que eu vou.", PALETTE["heal"])))
    if survivor.has_trait("sociavel") and game.player.distance_to(game.bonfire_pos) < 180:
        lines.extend((("Fica perto do fogo com a gente.", PALETTE["morale"]), ("Uma historia segura mais que faca.", PALETTE["morale"])))
    if survivor.has_trait("paranoico") and game.is_night:
        lines.extend((("Tem coisa na linha das árvores.", PALETTE["danger_soft"]), ("Não confio nesse silêncio.", PALETTE["danger_soft"])))

    friend = game.best_friend_name(survivor)
    rival = game.rival_name(survivor)
    if friend and survivor.morale > 58 and game.random.random() < 0.35:
        lines.append((f"{friend} ainda segura meu juizo.", PALETTE["accent_soft"]))
    if rival and survivor.conflict_cooldown <= 0 and game.random.random() < 0.28:
        lines.append((f"{rival} vai me fazer explodir.", PALETTE["danger_soft"]))
    memory = latest_social_memory(survivor)
    if memory and game.random.random() < 0.42:
        lines.append((str(memory.get("text", "")), tuple(memory.get("color", PALETTE["text"]))))

    if not lines:
        lines.extend(
            (
                ("Mais um turno e a gente segura.", PALETTE["text"]),
                ("Se o fogo fica vivo, eu fico tambem.", PALETTE["text"]),
                ("Essa mata cobra tudo da gente.", PALETTE["muted"]),
                ("Só não me deixa sem rumo, chefe.", PALETTE["muted"]),
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
        "faccao": ("Eles vão lembrar disso.", PALETTE["accent_soft"]) if resolved else ("Ninguém sai limpo disso.", PALETTE["muted"]),
        "alarme": ("Linha segura por enquanto.", PALETTE["heal"]) if resolved else ("Eles acharam a cerca.", PALETTE["danger_soft"]),
    }
    text, color = event_reactions.get(event.kind, ("Segura firme.", PALETTE["text"]))
    for survivor in living[:2]:
        trigger_survivor_bark(game, survivor, text, color, duration=2.4)
    for survivor in game.living_survivors():
        distance = survivor.distance_to(event.pos)
        heard = distance < 240
        duration = 160.0 if heard else 96.0
        impact = 0.0
        topic = event.kind
        if resolved:
            impact = 1.6 if event.kind in {"incendio", "doenca", "alarme", "expedicao"} else 1.0
            if event.kind in {"abrigo", "faccao"}:
                impact = 0.7
        else:
            impact = -1.8 if event.kind in {"desercao", "doenca", "fuga"} else -1.1
        remember_social_event(game, survivor, text, color, topic=topic, impact=impact, duration=duration)


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
            latest_social_memory(survivor) is None or survivor.social_comment_cooldown > 0,
            game.dynamic_event_for_survivor(survivor) is None,
            survivor.insanity,
            -survivor.trust_leader,
            -survivor.morale,
        ),
    )
    chosen = weighted[0]
    text, color = game.random.choice(game.survivor_bark_options(chosen))
    game.trigger_survivor_bark(chosen, text, color)
    if latest_social_memory(chosen):
        chosen.social_comment_cooldown = game.random.uniform(12.0, 22.0)
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
    """Atualiza amizade, conflitos e pressão social ao longo do tempo."""
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
        drift += social_memory_bias(survivor, topic="abrigo") * 0.05
        drift += social_memory_bias(survivor, topic="faccao") * 0.04
        drift -= pressure * 0.55
        drift -= survivor.exhaustion / 320
        if survivor.has_trait("paranoico"):
            drift -= 0.15
        if survivor.has_trait("leal"):
            drift += 0.18
        game.adjust_trust(survivor, drift)
        remember_leader_trust_state(game, survivor)
        insanity_shift = pressure * 5.2 + (0.8 if survivor.has_trait("paranoico") else 0.0)
        insanity_shift -= social_memory_bias(survivor) * 0.12
        insanity_shift += max(0.0, 48 - survivor.morale) * 0.035
        insanity_shift += max(0.0, survivor.exhaustion - 58) * 0.03
        if game.player.distance_to(survivor.pos) < 150:
            insanity_shift -= 1.0
        if survivor.state in {"sleep", "rest", "socialize"}:
            insanity_shift -= 1.6
        survivor.insanity = clamp(survivor.insanity + insanity_shift, 0, 100)
        if survivor.state == "socialize" and latest_social_memory(survivor, "bond"):
            survivor.morale = clamp(survivor.morale + 0.4, 0, 100)
        if survivor.state in {"guard", "watchtower"} and latest_social_memory(survivor, "feud"):
            survivor.morale = clamp(survivor.morale - 0.3, 0, 100)

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
                remember_social_event(game, survivor_a, f"Não esqueci a briga com {survivor_b.name}.", PALETTE["danger_soft"], topic="feud", impact=-2.8, duration=180.0)
                remember_social_event(game, survivor_b, f"{survivor_a.name} ainda ta atravessado comigo.", PALETTE["danger_soft"], topic="feud", impact=-2.8, duration=180.0)
                survivor_a.social_comment_cooldown = game.random.uniform(6.0, 10.0)
                survivor_b.social_comment_cooldown = game.random.uniform(6.0, 10.0)
                if game.random.random() < 0.5:
                    game.add_chat_message("radio", f"O campo ouviu a briga entre {survivor_a.name} e {survivor_b.name}.", PALETTE["danger_soft"], source="system")
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
                remember_social_event(game, survivor_a, f"{survivor_b.name} segurou o clima comigo no fogo.", PALETTE["morale"], topic="bond", impact=2.1, duration=170.0)
                remember_social_event(game, survivor_b, f"{survivor_a.name} me devolveu um pouco de folego.", PALETTE["morale"], topic="bond", impact=2.1, duration=170.0)
                survivor_a.social_comment_cooldown = game.random.uniform(6.0, 10.0)
                survivor_b.social_comment_cooldown = game.random.uniform(6.0, 10.0)
                if game.random.random() < 0.45:
                    game.add_chat_message("radio", f"{survivor_a.name} e {survivor_b.name} baixaram a guarda perto da fogueira.", PALETTE["morale"], source="system")
                continue

        if relation <= -12 and same_zone and pressure < 0.24 and survivor_a.bond_cooldown <= 0 and survivor_b.bond_cooldown <= 0:
            chance = 0.04 + max(0.0, 24 + relation) * 0.002
            if game.random.random() < chance:
                game.adjust_relationship(survivor_a, survivor_b, 2.2)
                survivor_a.bond_cooldown = 12.0
                survivor_b.bond_cooldown = 12.0
                remember_social_event(game, survivor_a, f"{survivor_b.name} baixou a guarda por um minuto.", PALETTE["accent_soft"], topic="repair", impact=0.9, duration=120.0)
                remember_social_event(game, survivor_b, f"{survivor_a.name} não veio pra cima dessa vez.", PALETTE["accent_soft"], topic="repair", impact=0.9, duration=120.0)
                continue

        if maybe_start_ambient_conversation(game, survivor_a, survivor_b, relation, pressure):
            continue

        if same_job and relation < 20:
            game.adjust_relationship(survivor_a, survivor_b, 0.8)
        if same_job and relation >= 38:
            survivor_a.energy = clamp(survivor_a.energy + 1.1, 0, 100)
            survivor_b.energy = clamp(survivor_b.energy + 1.1, 0, 100)
            survivor_a.morale = clamp(survivor_a.morale + 0.8, 0, 100)
            survivor_b.morale = clamp(survivor_b.morale + 0.8, 0, 100)
        elif same_job and relation <= -28:
            survivor_a.energy = clamp(survivor_a.energy - 0.8, 0, 100)
            survivor_b.energy = clamp(survivor_b.energy - 0.8, 0, 100)
            survivor_a.morale = clamp(survivor_a.morale - 0.6, 0, 100)
            survivor_b.morale = clamp(survivor_b.morale - 0.6, 0, 100)


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
        chosen = max(
            candidates,
            key=lambda survivor: (
                survivor.energy + survivor.morale * 0.6 + nearby_assignment_affinity(game, survivor, building),
                survivor.morale,
                -survivor.exhaustion,
            ),
        )
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
