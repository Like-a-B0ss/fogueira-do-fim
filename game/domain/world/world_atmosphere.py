from __future__ import annotations

from ...core.config import DAWN_MINUTES, DUSK_MINUTES, clamp, lerp


def daylight_factor(world) -> float:
    """Retorna a luz do dia em valor continuo para amanhecer e entardecer suaves."""
    time_value = world.time_minutes % (24 * 60)
    sunrise_start = DAWN_MINUTES - 70
    sunrise_end = DAWN_MINUTES + 65
    sunset_start = DUSK_MINUTES - 78
    sunset_end = DUSK_MINUTES + 72

    if sunrise_end <= time_value < sunset_start:
        return 1.0
    if time_value < sunrise_start or time_value >= sunset_end:
        return 0.0

    def smooth_step(value: float) -> float:
        value = clamp(value, 0.0, 1.0)
        return value * value * (3.0 - 2.0 * value)

    if sunrise_start <= time_value < sunrise_end:
        blend = (time_value - sunrise_start) / max(1.0, sunrise_end - sunrise_start)
        return smooth_step(blend)

    blend = (time_value - sunset_start) / max(1.0, sunset_end - sunset_start)
    return 1.0 - smooth_step(blend)


def weather_transition_factor(world) -> float:
    return clamp(float(getattr(world, "weather_front_progress", 1.0)), 0.0, 1.0)


def weather_signature(world, kind: str, strength: float) -> dict[str, float]:
    """Traduz um tipo de clima em fatores reutilizaveis por render, audio e gameplay."""
    strength = clamp(float(strength), 0.0, 1.0)
    signatures = {
        "clear": {"cloud": 0.08 + strength * 0.08, "rain": 0.0, "wind": 0.12 + strength * 0.18, "mist": 0.0, "storm": 0.0, "gloom": 0.0},
        "cloudy": {"cloud": 0.34 + strength * 0.42, "rain": 0.0, "wind": 0.16 + strength * 0.22, "mist": 0.06 + strength * 0.12, "storm": 0.0, "gloom": 0.12 + strength * 0.16},
        "wind": {"cloud": 0.18 + strength * 0.24, "rain": 0.0, "wind": 0.34 + strength * 0.46, "mist": 0.0, "storm": 0.0, "gloom": 0.06 + strength * 0.08},
        "rain": {"cloud": 0.46 + strength * 0.34, "rain": 0.36 + strength * 0.46, "wind": 0.18 + strength * 0.22, "mist": 0.08 + strength * 0.1, "storm": 0.0, "gloom": 0.18 + strength * 0.16},
        "mist": {"cloud": 0.18 + strength * 0.18, "rain": 0.0, "wind": 0.04 + strength * 0.08, "mist": 0.38 + strength * 0.42, "storm": 0.0, "gloom": 0.08 + strength * 0.12},
        "storm": {"cloud": 0.64 + strength * 0.28, "rain": 0.58 + strength * 0.34, "wind": 0.46 + strength * 0.34, "mist": 0.1 + strength * 0.1, "storm": 0.48 + strength * 0.42, "gloom": 0.28 + strength * 0.2},
    }
    base = signatures.get(kind, signatures["clear"])
    return {key: clamp(value, 0.0, 1.0) for key, value in base.items()}


def blended_weather_signature(world) -> dict[str, float]:
    current_kind = getattr(world, "weather_kind", "clear")
    current_strength = float(getattr(world, "weather_strength", 0.0))
    target_kind = getattr(world, "weather_target_kind", current_kind)
    target_strength = float(getattr(world, "weather_target_strength", current_strength))
    blend = world.weather_transition_factor()
    current = world.weather_signature(current_kind, current_strength)
    target = world.weather_signature(target_kind, target_strength)
    return {key: lerp(current[key], target[key], blend) for key in current}


def weather_cloud_cover(world) -> float:
    """Converte o clima atual em cobertura de nuvens para render, audio e gameplay."""
    return clamp(world.blended_weather_signature()["cloud"], 0.0, 0.94)


def weather_precipitation_factor(world) -> float:
    return clamp(world.blended_weather_signature()["rain"], 0.0, 1.0)


def weather_wind_factor(world) -> float:
    return clamp(world.blended_weather_signature()["wind"], 0.0, 1.0)


def weather_mist_factor(world) -> float:
    return clamp(world.blended_weather_signature()["mist"], 0.0, 1.0)


def weather_storm_factor(world) -> float:
    return clamp(world.blended_weather_signature()["storm"], 0.0, 1.0)


def visual_darkness_factor(world) -> float:
    """Mistura noite e cobertura de nuvens em um unico fator de penumbra."""
    daylight = world.daylight_factor()
    signature = world.blended_weather_signature()
    cloud_cover = signature["cloud"]
    base_darkness = 1.0 - daylight
    cloud_darkness = cloud_cover * (0.42 * daylight + 0.14)
    weather_bias = signature["gloom"] + signature["storm"] * 0.08 + signature["mist"] * 0.04
    return clamp(base_darkness + cloud_darkness + weather_bias, 0.0, 1.0)


def daylight_phase_label(world) -> str:
    """Resume a faixa do dia em um texto curto para a HUD."""
    time_value = world.time_minutes % (24 * 60)
    if DAWN_MINUTES - 65 <= time_value < DAWN_MINUTES + 70:
        return "amanhecer"
    if DUSK_MINUTES - 85 <= time_value < DUSK_MINUTES + 75:
        return "entardecer"
    if time_value < 4 * 60 or time_value >= 22 * 60:
        return "noite funda"
    if world.daylight_factor() < 0.18:
        return "noite"
    if time_value < 12 * 60 + 30:
        return "manha"
    return "tarde"


def weather_mood_label(world) -> str:
    """Traduz a combinacao de clima e intensidade para uma leitura curta."""
    signature = world.blended_weather_signature()
    storm = signature["storm"]
    rain = signature["rain"]
    mist = signature["mist"]
    wind = signature["wind"]
    cloud = signature["cloud"]
    if storm > 0.32:
        return "tempestade armando" if storm < 0.62 else "tempestade pesada"
    if rain > 0.56:
        return "garoa fria" if rain < 0.72 else "chuva fechada"
    if mist > 0.46:
        return "bruma leve" if mist < 0.7 else "neblina grossa"
    if wind > 0.48:
        return "vento leve" if wind < 0.68 else "vento forte"
    if cloud > 0.34:
        return "nublado leve" if cloud < 0.62 else "nublado pesado"
    return "ceu aberto" if cloud < 0.14 else "claridade limpa"









