from __future__ import annotations

import unicodedata

from ..core.config import FOCUS_LABELS, PALETTE, clamp
from ..domain.camp import camp_social as social_system


def normalize_chat_text(game, text: str) -> str:
    """Normaliza o texto para comparacoes simples sem acento."""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def seed_chat_log(game) -> None:
    """Cria o historico inicial que explica como a conversa funciona."""
    game.chat_messages = []
    add_chat_message(
        game,
        "system",
        "Você meses sobreviveu sozinho. Então o rádio chiou.",
        PALETTE["accent_soft"],
        source="system",
    )
    add_chat_message(
        game,
        "system",
        "Agora você é responsável por todas essas vidas. Approxime-se de um morador e aperte E para conversar.",
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
    game.chat_panel_collapsed = False  # Expandir automaticamente ao abrir conversa
    summary_text, summary_color = game.social_summary_text(survivor)
    add_chat_message(game, "radio", f"{getattr(survivor, 'name', 'Morador')} te ouviu e esperou a ordem.", PALETTE["accent_soft"], source="system")
    add_chat_message(game, getattr(survivor, "name", "morador"), summary_text, summary_color, source="npc")
    if hasattr(game, "notify_chief_task_progress"):
        game.notify_chief_task_progress("talk_survivor", id="opening_talk")


def close_survivor_dialog(game) -> None:
    game.dialog_survivor_name = None
    game.chat_panel_collapsed = True  # Colapsar automaticamente ao fechar conversa


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
        {"label": "Como você está?", "action": "status"},
        {"label": "Sobre a vida", "action": "life"},
        {"label": "Seu passado", "action": "past"},
        {"label": "O grupo", "action": "people"},
        {"label": "Confia em mim?", "action": "leader"},
        {"label": "Memória recente", "action": "memory"},
        {"label": role_label, "action": role_directive},
        {"label": "Fica de vigia", "action": "guard"},
        {"label": "Vai descansar", "action": "rest"},
    ]
    return options


def survivor_condition_dialogue(game, survivor: object) -> tuple[str, tuple[int, int, int]]:
    if getattr(survivor, "health", 100.0) < 36:
        return "Estou de pé, mas cada movimento puxa dor. Se a enfermaria segurar, eu ainda sirvo.", PALETTE["heal"]
    if getattr(survivor, "hunger", 0.0) > 72:
        return "A fome deixa a cabeça curta. Eu começo a responder atravessado antes de perceber.", PALETTE["accent_soft"]
    if getattr(survivor, "exhaustion", 0.0) > 70 or getattr(survivor, "sleep_debt", 0.0) > 55:
        return "Estou cansado de um jeito que não passa só sentando. Preciso de um canto quieto e uma noite inteira.", PALETTE["muted"]
    if getattr(survivor, "insanity", 0.0) > 68:
        return "Tem hora que a mata parece chamar meu nome. Eu sei que é medo, mas o medo fala alto.", PALETTE["morale"]
    if getattr(survivor, "morale", 50.0) > 68:
        return "Hoje eu ainda consigo rir sem fingir. Isso não vence a noite, mas ajuda a atravessar.", PALETTE["morale"]
    if getattr(survivor, "trust_leader", 50.0) < 32:
        return "Estou aqui, mas preciso ver mais presença. Ordem distante parece vento: bate e some.", PALETTE["muted"]
    return "Estou inteiro o bastante para continuar. Não é paz, mas é um pedaço de chão sob o pé.", PALETTE["text"]


def survivor_past_dialogue(game, survivor: object) -> tuple[str, tuple[int, int, int]]:
    role = getattr(survivor, "role", "")
    trait = getattr(survivor, "primary_trait", lambda: "")()
    templates = {
        "lenhador": (
            "Antes disso tudo eu media o dia pelo som do machado. Madeira boa canta antes de cair.",
            "Eu aprendi cedo que árvore não perdoa pressa. Gente também não.",
        ),
        "vigia": (
            "Eu já passei noite olhando estrada vazia. O problema é quando a estrada começa a olhar de volta.",
            "Sempre fui bom em perceber silêncio errado. Aqui quase todo silêncio é errado.",
        ),
        "batedora": (
            "Eu conhecia trilha de caça, nascente escondida, pegada fresca. Agora procuro isso tudo com medo de achar outra coisa.",
            "Meu passado ficou espalhado em caminhos. Talvez por isso eu ainda volte para eles.",
        ),
        "artesa": (
            "Eu consertava porta, panela, cabo, telhado. Depois do fim, consertar virou uma forma de rezar.",
            "Minha mão lembra de casa quando pega ferramenta. Às vezes isso ajuda, às vezes pesa.",
        ),
        "cozinheiro": (
            "Eu cozinhava para mesa cheia. Hoje conto migalha como se fosse promessa.",
            "Comida não é só comida. É o jeito mais rápido de lembrar alguém que ainda está vivo.",
        ),
        "mensageiro": (
            "Eu levava notícia antes das notícias virarem ameaça. Palavra errada já derrubou gente demais.",
            "Meu ofício era chegar. Depois do fim, chegar vivo virou metade da mensagem.",
        ),
    }
    text = game.random.choice(templates.get(role, ("Eu tinha uma vida pequena e achava isso pouco. Hoje eu chamaria aquilo de milagre.",)))
    if trait == "paranoico":
        text += " Eu devia ter desconfiado antes; talvez alguém tivesse sobrevivido."
    elif trait == "leal":
        text += " Ainda acredito que gente junta aguenta mais que gente sozinha."
    elif trait == "rancoroso":
        text += " Tem coisa que eu não esqueci, e talvez nunca esqueça."
    elif trait == "gentil":
        text += " O que sobrou de mim tenta não endurecer por completo."
    return text, PALETTE["accent_soft"]


def survivor_people_dialogue(game, survivor: object) -> tuple[str, tuple[int, int, int]]:
    friend = game.best_friend_name(survivor)
    rival = game.rival_name(survivor)
    if rival and getattr(survivor, "relations", {}).get(rival, 0.0) < -36:
        return f"{rival} me atravessa fácil. Eu tento trabalhar perto, mas a voz dele já chega como faísca.", PALETTE["danger_soft"]
    if friend:
        return f"{friend} ainda me puxa para perto do fogo quando eu começo a me perder. Isso conta muito.", PALETTE["morale"]
    if game.friendship_count() >= 2:
        return "Tem laço nascendo aqui. Pouco, torto, mas real. O campo não é só cerca e estoque.", PALETTE["morale"]
    if game.feud_count() > 0:
        return "O grupo está cansado e isso faz qualquer palavra virar pedra. Se ninguém escuta, vira briga.", PALETTE["danger_soft"]
    return "Ainda estamos nos medindo. Ninguém quer precisar de ninguém, mas todo mundo precisa.", PALETTE["text"]


def survivor_leader_dialogue(game, survivor: object) -> tuple[str, tuple[int, int, int]]:
    trust = getattr(survivor, "trust_leader", 50.0)
    if trust >= 78:
        return "Eu confio. Não porque você acerta sempre, mas porque aparece quando errar custa caro.", PALETTE["heal"]
    if trust >= 55:
        return "Confio o bastante para seguir a ordem. Para dormir tranquilo, ainda falta o mundo ajudar.", PALETTE["accent_soft"]
    if trust >= 34:
        return "Eu escuto, mas olho o resultado. Nesse campo, confiança precisa comer todo dia.", PALETTE["muted"]
    return "Ainda não sei. Às vezes parece que você vê o mapa e esquece as pessoas dentro dele.", PALETTE["danger_soft"]


def survivor_memory_dialogue(game, survivor: object) -> tuple[str, tuple[int, int, int]]:
    memory = social_system.latest_social_memory(survivor)
    if memory:
        return str(memory.get("text", "")), tuple(memory.get("color", PALETTE["text"]))
    return "Nada ficou forte o bastante para virar lembrança recente. Talvez isso seja descanso, talvez seja só silêncio.", PALETTE["muted"]


def add_direct_dialogue_response(game, survivor: object, text: str, color: tuple[int, int, int]) -> None:
    game.trigger_survivor_bark(survivor, text, color, duration=3.4)
    add_chat_message(game, getattr(survivor, "name", "morador"), text, color, source="npc")


def execute_survivor_dialog_action(game, survivor: object, action: str) -> None:
    """Executa a conversa curta e transforma a fala em efeito pratico no acampamento."""
    if action == "status":
        text, color = survivor_condition_dialogue(game, survivor)
        add_direct_dialogue_response(game, survivor, text, color)
        survivor.morale = clamp(getattr(survivor, "morale", 50.0) + 2.4, 0, 100)
        game.adjust_trust(survivor, 1.6)
        game.audio.play_ui("focus")
        return
    if action == "life":
        text, color = survivor_condition_dialogue(game, survivor)
        add_direct_dialogue_response(game, survivor, text, color)
        survivor.morale = clamp(getattr(survivor, "morale", 50.0) + 1.2, 0, 100)
        game.adjust_trust(survivor, 0.8)
        game.audio.play_ui("focus")
        return
    if action == "past":
        text, color = survivor_past_dialogue(game, survivor)
        add_direct_dialogue_response(game, survivor, text, color)
        social_system.remember_social_event(game, survivor, text, color, topic="past", impact=0.8, duration=190.0)
        game.adjust_trust(survivor, 1.0)
        game.audio.play_ui("focus")
        return
    if action == "people":
        text, color = survivor_people_dialogue(game, survivor)
        add_direct_dialogue_response(game, survivor, text, color)
        game.audio.play_ui("focus")
        return
    if action == "leader":
        text, color = survivor_leader_dialogue(game, survivor)
        add_direct_dialogue_response(game, survivor, text, color)
        social_system.remember_social_event(game, survivor, text, color, topic="leader_talk", impact=0.6, duration=160.0)
        game.audio.play_ui("focus")
        return
    if action == "memory":
        text, color = survivor_memory_dialogue(game, survivor)
        add_direct_dialogue_response(game, survivor, text, color)
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
    compliance += social_system.directive_compliance_modifier(game, survivor, directive)
    accepted = game.random.random() <= clamp(compliance, 0.18, 0.96)
    if not accepted:
        text = game.random.choice(
            (
                "Não vou largar o que estou segurando agora.",
                "Essa ordem chegou tarde demais.",
                "Eu escutei, mas não compro isso agora.",
            )
        )
        game.trigger_survivor_bark(survivor, text, PALETTE["danger_soft"], duration=2.6)
        game.adjust_trust(survivor, -0.8)
        social_system.remember_social_event(game, survivor, "A ordem bateu torto comigo.", PALETTE["danger_soft"], topic="leader_order", impact=-1.2, duration=130.0)
        return False
    survivor.leader_directive = directive
    survivor.leader_directive_timer = duration
    survivor.decision_timer = 0.0
    game.adjust_trust(survivor, 1.2)
    if directive == "guard" and hasattr(game, "notify_chief_task_progress"):
        game.notify_chief_task_progress("assign_guard", id="opening_guard")
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
    social_system.remember_social_event(game, survivor, response, PALETTE["accent_soft"], topic="leader_order", impact=1.0, duration=120.0)
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
        f"toras {game.logs}, tábuas {game.wood}, insumos {game.food}, refeições {game.meals}, sucata {game.scrap}."
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
    if any(word in normalized for word in ("briga", "feudo", "treta", "richa")):
        feud_survivors = [survivor for survivor in living if social_system.latest_social_memory(survivor, "feud")]
        if feud_survivors:
            survivor = max(feud_survivors, key=lambda item: abs(social_system.social_memory_bias(item, topic="feud")))
            summary_text, summary_color = game.social_summary_text(survivor)
            game.trigger_survivor_bark(survivor, summary_text, summary_color, duration=2.8)
            return
    if any(word in normalized for word in ("morreu", "perdemos", "perdeu", "morte", "luto")):
        grieving = [survivor for survivor in living if social_system.latest_social_memory(survivor, "loss")]
        if grieving:
            survivor = max(grieving, key=lambda item: abs(social_system.social_memory_bias(item, topic="loss")))
            summary_text, summary_color = game.social_summary_text(survivor)
            game.trigger_survivor_bark(survivor, summary_text, summary_color, duration=3.0)
            return
    if any(word in normalized for word in ("expedicao", "trilha", "resgate", "salvo", "salvei")):
        expedition_marked = [
            survivor
            for survivor in living
            if social_system.latest_social_memory(survivor, "expedition_saved")
            or social_system.latest_social_memory(survivor, "expedition_success")
            or social_system.latest_social_memory(survivor, "expedition_hard")
        ]
        if expedition_marked:
            survivor = max(expedition_marked, key=lambda item: abs(social_system.social_memory_bias(item)))
            summary_text, summary_color = game.social_summary_text(survivor)
            game.trigger_survivor_bark(survivor, summary_text, summary_color, duration=3.0)
            return
    if any(word in normalized for word in ("confia", "confianca", "chefe", "ordem")):
        marked = [
            survivor
            for survivor in living
            if social_system.latest_social_memory(survivor, "leader_trust")
            or social_system.latest_social_memory(survivor, "leader_doubt")
        ]
        if marked:
            survivor = max(marked, key=lambda item: abs(social_system.social_memory_bias(item)))
            summary_text, summary_color = game.social_summary_text(survivor)
            game.trigger_survivor_bark(survivor, summary_text, summary_color, duration=3.0)
            return
    if any(word in normalized for word in ("amigo", "amizade", "junto", "unido")):
        bonded = [survivor for survivor in living if social_system.latest_social_memory(survivor, "bond")]
        if bonded:
            survivor = max(bonded, key=lambda item: social_system.social_memory_bias(item, topic="bond"))
            summary_text, summary_color = game.social_summary_text(survivor)
            game.trigger_survivor_bark(survivor, summary_text, summary_color, duration=2.8)
            return
    if any(word in normalized for word in ("quem ta mal", "quem esta mal", "quem ta ruim", "quem esta ruim", "clima")):
        survivor = max(living, key=lambda item: item.insanity + item.exhaustion * 0.45 - item.trust_leader * 0.2)
        summary_text, summary_color = game.social_summary_text(survivor)
        game.trigger_survivor_bark(survivor, summary_text, summary_color, duration=2.8)
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
