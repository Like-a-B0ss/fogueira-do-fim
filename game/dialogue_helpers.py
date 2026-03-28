from __future__ import annotations

import unicodedata

from .config import FOCUS_LABELS, PALETTE, clamp


def normalize_chat_text(game, text: str) -> str:
    """Normaliza o texto para comparacoes simples sem acento."""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def seed_chat_log(game) -> None:
    """Cria o historico inicial que explica como a conversa funciona."""
    game.chat_messages = []
    add_chat_message(
        game,
        "radio",
        "A clareira esta falando sozinha. Chegue perto de um morador e aperte E para conversar.",
        PALETTE["accent_soft"],
        source="system",
    )
    add_chat_message(
        game,
        "radio",
        "As vozes do campo passam por aqui, mas as ordens agora saem na conversa direta.",
        PALETTE["muted"],
        source="system",
    )


def add_chat_message(
    game,
    speaker: str,
    text: str,
    color: tuple[int, int, int] | None = None,
    *,
    source: str = "system",
) -> None:
    """Empilha mensagens curtas que ajudam a ler o clima social do acampamento."""
    clean_text = " ".join(str(text).strip().split())
    if not clean_text:
        return
    entry = {
        "speaker": str(speaker),
        "text": clean_text,
        "color": tuple(color or PALETTE["text"]),
        "source": source,
    }
    if game.chat_messages and game.chat_messages[-1]["speaker"] == entry["speaker"] and game.chat_messages[-1]["text"] == entry["text"]:
        return
    game.chat_messages.append(entry)
    game.chat_messages = game.chat_messages[-72:]
    game.chat_scroll = 0.0


def chat_message_height(game, entry: dict[str, object], width: int) -> int:
    speaker = str(entry.get("speaker", "radio"))
    label = f"{speaker}: {entry.get('text', '')}"
    lines = game.wrap_text_lines(game.ui_small_font, label, max(40, width))
    return len(lines) * game.ui_small_font.get_linesize() + max(0, len(lines) - 1) * 2 + 8


def chat_content_height(game) -> int:
    viewport_width = game.chat_panel_layout()["viewport"].width - 12
    return sum(chat_message_height(game, entry, viewport_width) + 4 for entry in game.chat_messages)


def chat_max_scroll(game) -> float:
    viewport = game.chat_panel_layout()["viewport"]
    return max(0.0, float(chat_content_height(game) - viewport.height))


def clamp_chat_scroll(game) -> None:
    game.chat_scroll = clamp(game.chat_scroll, 0.0, chat_max_scroll(game))


def adjust_chat_scroll(game, delta: float) -> None:
    game.chat_scroll = clamp(game.chat_scroll + delta, 0.0, chat_max_scroll(game))


def directive_label(_game, directive: str) -> str:
    return {
        "rest": "descanso",
        "guard": "vigia",
        "wood": "toras",
        "food": "comida",
        "repair": "barricadas",
        "cook": "cozinha",
        "clinic": "enfermaria",
        "fire": "fogueira",
    }.get(directive, directive)


def directive_from_text(_game, normalized_text: str) -> str | None:
    if any(word in normalized_text for word in ("descansa", "descansar", "dorme", "dormir", "repousa")):
        return "rest"
    if any(word in normalized_text for word in ("vigia", "vigiar", "guarda", "guardar", "patrulh")):
        return "guard"
    if any(word in normalized_text for word in ("madeira", "toras", "lenha", "arvore", "arvores")):
        return "wood"
    if any(word in normalized_text for word in ("comida", "insumo", "forrage", "colhe", "coleta alimento")):
        return "food"
    if any(word in normalized_text for word in ("barricada", "barricadas", "repar", "reforc", "fortific", "cerca")):
        return "repair"
    if any(word in normalized_text for word in ("cozinha", "cozin", "panela", "refeic")):
        return "cook"
    if any(word in normalized_text for word in ("enfermaria", "cura", "curar", "trata", "remedio", "medic")):
        return "clinic"
    if any(word in normalized_text for word in ("fogueira", "fogo", "brasa")):
        return "fire"
    return None


def focus_from_text(_game, normalized_text: str) -> str | None:
    if "equilibr" in normalized_text or "balance" in normalized_text:
        return "balanced"
    if any(word in normalized_text for word in ("suprimento", "supply", "recurso", "estoque")):
        return "supply"
    if any(word in normalized_text for word in ("fortific", "defesa", "barricada", "vigia")):
        return "fortify"
    if any(word in normalized_text for word in ("moral", "descanso", "fogo", "cozinha", "calma")):
        return "morale"
    return None


def targeted_survivors_from_text(game, normalized_text: str) -> list[object]:
    if any(word in normalized_text for word in ("todos", "todas", "grupo", "equipe", "acampamento", "geral")):
        return [survivor for survivor in game.survivors if survivor.is_alive() and not game.is_survivor_on_expedition(survivor)]
    matches = []
    for survivor in game.survivors:
        if not survivor.is_alive() or game.is_survivor_on_expedition(survivor):
            continue
        if normalize_chat_text(game, survivor.name) in normalized_text:
            matches.append(survivor)
    return matches


def focus_label_for_mode(_game, mode: str) -> str:
    return FOCUS_LABELS.get(mode, mode)


def active_dialog_survivor(game) -> object | None:
    if not game.dialog_survivor_name:
        return None
    for survivor in game.survivors:
        if (
            survivor.name == game.dialog_survivor_name
            and survivor.is_alive()
            and not game.is_survivor_on_expedition(survivor)
            and survivor.distance_to(game.player.pos) < 122
        ):
            return survivor
    game.dialog_survivor_name = None
    return None


def open_survivor_dialog(game, survivor: object) -> None:
    game.dialog_survivor_name = getattr(survivor, "name", None)
    add_chat_message(game, "radio", f"{getattr(survivor, 'name', 'Morador')} te ouviu e esperou a ordem.", PALETTE["accent_soft"], source="system")


def close_survivor_dialog(game) -> None:
    game.dialog_survivor_name = None


def survivor_role_directive(_game, survivor: object) -> tuple[str, str]:
    role = getattr(survivor, "role", "")
    mapping = {
        "lenhador": ("wood", "Puxa madeira"),
        "batedora": ("food", "Busca comida"),
        "artesa": ("repair", "Reforca a cerca"),
        "cozinheiro": ("cook", "Segura a cozinha"),
        "mensageiro": ("clinic", "Cuida dos feridos"),
        "vigia": ("guard", "Segura a linha"),
    }
    return mapping.get(role, ("wood", "Ajuda no estoque"))


def conversation_options_for_survivor(game, survivor: object) -> list[dict[str, str]]:
    role_directive, role_label = survivor_role_directive(game, survivor)
    options = [
        {"label": "Como voce esta?", "action": "status"},
        {"label": role_label, "action": role_directive},
        {"label": "Fica de vigia", "action": "guard"},
        {"label": "Vai descansar", "action": "rest"},
    ]
    request = game.pending_build_request_for_survivor(survivor)
    if request and not request.approved:
        wood_cost, scrap_cost = game.build_cost_for(request.kind)
        options.append(
            {
                "label": f"Aprovar {request.label} ({wood_cost}T {scrap_cost}S)",
                "action": f"approve_build:{request.uid}",
            }
        )
    elif request and request.approved:
        progress = int(clamp(request.progress, 0.0, 1.0) * 100)
        options.append(
            {
                "label": f"Obra em andamento {progress}%",
                "action": "build_status",
            }
        )
    return options


def execute_survivor_dialog_action(game, survivor: object, action: str) -> None:
    """Executa a conversa curta e transforma a fala em efeito pratico no acampamento."""
    if action.startswith("approve_build:"):
        raw_uid = action.split(":", 1)[1]
        request = game.build_request_by_uid(int(raw_uid)) if raw_uid.isdigit() else None
        success, message = game.approve_build_request(request) if request else (False, "Pedido invalido.")
        color = PALETTE["heal"] if success else PALETTE["danger_soft"]
        game.spawn_floating_text(message.lower(), survivor.pos, color)
        if success:
            game.audio.play_ui("order")
        else:
            game.audio.play_alert()
        return
    if action == "build_status":
        request = game.pending_build_request_for_survivor(survivor)
        if request and request.approved:
            progress = int(clamp(request.progress, 0.0, 1.0) * 100)
            text = f"Tua obra esta em {progress}%."
            game.trigger_survivor_bark(survivor, text, PALETTE["accent_soft"], duration=2.6)
            game.audio.play_ui("focus")
        return
    if action == "status":
        text, color = game.random.choice(game.survivor_bark_options(survivor))
        game.trigger_survivor_bark(survivor, text, color, duration=2.8)
        survivor.morale = clamp(getattr(survivor, "morale", 50.0) + 2.4, 0, 100)
        game.adjust_trust(survivor, 1.6)
        game.audio.play_ui("focus")
        return
    if action in {"rest", "guard", "wood", "food", "repair", "cook", "clinic", "fire"}:
        try_assign_directive(game, survivor, action, duration=150.0)
        game.audio.play_ui("order")


def set_focus_from_chat(game, mode: str) -> None:
    game.focus_mode = mode
    color = {
        "balanced": PALETTE["text"],
        "supply": PALETTE["accent_soft"],
        "fortify": PALETTE["heal"],
        "morale": PALETTE["morale"],
    }.get(mode, PALETTE["text"])
    game.spawn_floating_text(f"foco: {focus_label_for_mode(game, mode).lower()}", game.player.pos, color)
    add_chat_message(game, "radio", f"Foco comunitario ajustado para {focus_label_for_mode(game, mode).lower()}.", color, source="system")


def try_assign_directive(game, survivor: object, directive: str, *, duration: float) -> bool:
    """Aplica uma ordem do lider respeitando confianca, traços e resistencia do morador."""
    if not getattr(survivor, "is_alive", lambda: False)() or game.is_survivor_on_expedition(survivor):
        return False
    compliance = 0.52 + getattr(survivor, "trust_leader", 50.0) / 110.0
    if getattr(survivor, "has_trait", lambda _trait: False)("leal"):
        compliance += 0.18
    if getattr(survivor, "has_trait", lambda _trait: False)("teimoso"):
        compliance -= 0.12
    if getattr(survivor, "has_trait", lambda _trait: False)("paranoico") and directive not in {"guard", "repair"}:
        compliance -= 0.08
    accepted = game.random.random() <= clamp(compliance, 0.18, 0.96)
    if not accepted:
        text = game.random.choice(
            (
                "Nao vou largar o que estou segurando agora.",
                "Essa ordem chegou tarde demais.",
                "Eu escutei, mas nao compro isso agora.",
            )
        )
        game.trigger_survivor_bark(survivor, text, PALETTE["danger_soft"], duration=2.6)
        game.adjust_trust(survivor, -0.8)
        return False
    survivor.leader_directive = directive
    survivor.leader_directive_timer = duration
    survivor.decision_timer = 0.0
    game.adjust_trust(survivor, 1.2)
    response = {
        "rest": "Certo. Vou baixar a marcha.",
        "guard": "To indo pra linha.",
        "wood": "Vou buscar toras.",
        "food": "Vou atras de comida.",
        "repair": "Ja to fechando a cerca.",
        "cook": "Panela vai girar.",
        "clinic": "Vou segurar os feridos.",
        "fire": "Eu cuido do fogo.",
    }.get(directive, "Recebido.")
    game.trigger_survivor_bark(survivor, response, PALETTE["accent_soft"], duration=2.4)
    return True


def issue_chat_order(game, targets: list[object], directive: str) -> bool:
    if not targets:
        return False
    accepted = 0
    for survivor in targets:
        if try_assign_directive(game, survivor, directive, duration=138.0 if len(targets) == 1 else 96.0):
            accepted += 1
    if directive in {"wood", "food"}:
        game.focus_mode = "supply"
    elif directive in {"repair", "guard"}:
        game.focus_mode = "fortify"
    elif directive in {"rest", "cook", "clinic", "fire"}:
        game.focus_mode = "morale"
    label = directive_label(game, directive)
    if accepted > 0:
        add_chat_message(game, "radio", f"Ordem fechada: {accepted}/{len(targets)} seguiram para {label}.", PALETTE["accent_soft"], source="system")
        game.audio.play_ui("order")
        return True
    add_chat_message(game, "radio", f"Ninguem comprou a ordem de {label} agora.", PALETTE["danger_soft"], source="system")
    game.audio.play_alert()
    return True


def chat_status_report(game) -> None:
    report = (
        f"Dia {game.day}, {game.weather_label}, foco {focus_label_for_mode(game, game.focus_mode).lower()}, "
        f"moral {game.average_morale():.0f}, insanidade {game.average_insanity():.0f}, "
        f"toras {game.logs}, tabuas {game.wood}, insumos {game.food}, refeicoes {game.meals}, sucata {game.scrap}."
    )
    add_chat_message(game, "radio", report, PALETTE["muted"], source="system")


def random_chat_reply(game, player_text: str) -> None:
    living = [survivor for survivor in game.survivors if survivor.is_alive() and not game.is_survivor_on_expedition(survivor)]
    if not living:
        return
    normalized = normalize_chat_text(game, player_text)
    if "obrig" in normalized:
        survivor = max(living, key=lambda item: item.trust_leader)
        game.trigger_survivor_bark(survivor, "A gente segue junto, chefe.", PALETTE["heal"], duration=2.6)
        return
    if "quem" in normalized or "ai" in normalized:
        survivor = max(living, key=lambda item: item.morale)
        game.trigger_survivor_bark(survivor, "Ainda tem gente de pe aqui.", PALETTE["text"], duration=2.6)
        return
    stressed = max(living, key=lambda item: item.insanity + item.exhaustion * 0.4)
    game.trigger_survivor_bark(stressed, game.random.choice(game.survivor_bark_options(stressed))[0], PALETTE["muted"], duration=2.4)


def submit_chat_message(game, text: str) -> None:
    """Mantido como utilitario legado para testes e eventos futuros do acampamento."""
    clean_text = " ".join(text.strip().split())
    if not clean_text:
        return
    add_chat_message(game, "chefe", clean_text, PALETTE["text"], source="player")
    normalized = normalize_chat_text(game, clean_text)
    if any(word in normalized for word in ("ajuda", "comando", "comandos", "ordens")):
        add_chat_message(game, "radio", "O historico segue vivo aqui, mas as ordens principais agora saem na conversa direta com cada morador.", PALETTE["accent_soft"], source="system")
        game.audio.play_ui("focus")
        return
    if "como estamos" in normalized or "status" in normalized or "situacao" in normalized or "relatorio" in normalized:
        chat_status_report(game)
        game.audio.play_ui("focus")
        return
    directive = directive_from_text(game, normalized)
    targets = targeted_survivors_from_text(game, normalized)
    if directive and targets:
        issue_chat_order(game, targets, directive)
        return
    if normalized.startswith("foco ") or "foco" in normalized:
        focus_mode = focus_from_text(game, normalized)
        if focus_mode:
            set_focus_from_chat(game, focus_mode)
            game.audio.play_ui("focus")
            return
    if directive and any(word in normalized for word in ("todos", "todas", "grupo", "equipe", "geral")):
        issue_chat_order(game, targeted_survivors_from_text(game, normalized), directive)
        return
    random_chat_reply(game, clean_text)
    game.audio.play_ui("focus")
