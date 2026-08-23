"""
moves.py
--------
Formatea los moveId crudos de PvPoke (ej. "SHADOW_CLAW", "WEATHER_BALL_FIRE")
en nombres legibles en español para mostrar en la interfaz.
"""

# Sufijos de tipo que aparecen en algunos movimientos (Weather Ball, Hidden Power, Techno Blast...)
_TYPE_SUFFIX_ES = {
    "FIRE": "Fuego", "WATER": "Agua", "GRASS": "Planta", "ELECTRIC": "Eléctrico",
    "ICE": "Hielo", "FIGHTING": "Lucha", "POISON": "Veneno", "GROUND": "Tierra",
    "FLYING": "Volador", "PSYCHIC": "Psíquico", "BUG": "Bicho", "ROCK": "Roca",
    "GHOST": "Fantasma", "DRAGON": "Dragón", "DARK": "Siniestro", "STEEL": "Acero",
    "FAIRY": "Hada", "NORMAL": "Normal",
}

# Traducciones específicas para nombres que no se ven bien solo con title-case
_SPECIAL_NAMES_ES = {
    "HYDRO_CANNON": "Hidrocañón",
    "HYDRO_PUMP": "Hidrobomba",
    "DRAGON_BREATH": "Aliento de Dragón",
    "SHADOW_CLAW": "Garra Sombra",
    "SHADOW_SNEAK": "Ataque Furtivo Sombrío",
    "SHADOW_BALL": "Bola Sombra",
    "SHADOW_PUNCH": "Puño Sombra",
    "SKY_ATTACK": "Ataque Aéreo",
    "PLAY_ROUGH": "Golpe Duro",
    "FRUSTRATION": "Frustración",
    "GIGATON_HAMMER": "Martillo Gigatón",
    "BRUTAL_SWING": "Golpe Brutal",
    "DYNAMIC_PUNCH": "Puño Dinámico",
    "FOUL_PLAY": "Juego Sucio",
    "DRAIN_PUNCH": "Puño Drenaje",
    "MUD_SHOT": "Disparo Lodo",
    "MUD_BOMB": "Bomba Fango",
    "AQUA_TAIL": "Cola de Agua",
    "EARTHQUAKE": "Terremoto",
    "ROCK_SLIDE": "Avalancha",
    "ICE_BEAM": "Rayo Hielo",
    "AIR_CUTTER": "Corte Aéreo",
    "SAND_ATTACK": "Ataque Arena",
    "VOLT_SWITCH": "Cambio de Voltios",
    "SUCKER_PUNCH": "Golpe Bajo",
    "QUICK_ATTACK": "Ataque Rápido",
    "BODY_SLAM": "Golpe Cuerpo",
    "ROLLOUT": "Rodada",
    "COUNTER": "Contraataque",
    "PSYCHO_CUT": "Psicocorte",
    "FIRE_SPIN": "Giro Fuego",
    "FEINT_ATTACK": "Finta",
    "SNARL": "Gruñido Feroz",
    "LAST_RESORT": "Último Recurso",
    "DAZZLING_GLEAM": "Destello",
    "MOONBLAST": "Meteorobola",
}


def format_move(move_id: str) -> str:
    """Convierte un moveId crudo (ej. WEATHER_BALL_FIRE, COUNTER) en un nombre
    legible en español.

    Si el valor ya viene formateado (ej. "Shadow Claw" desde la tabla Moves
    de la base de datos, con mayúsculas y minúsculas mezcladas), se devuelve
    tal cual sin tocarlo.
    """
    if not move_id:
        return "-"

    # Un moveId crudo siempre viene todo en MAYÚSCULAS (con o sin guion bajo,
    # ej. "SHADOW_CLAW" o "COUNTER"). Si ya trae minúsculas, asumimos que
    # viene formateado desde la base de datos y no lo tocamos.
    if move_id != move_id.upper():
        return move_id

    if move_id in _SPECIAL_NAMES_ES:
        return _SPECIAL_NAMES_ES[move_id]

    parts = move_id.split("_")
    # Detectar sufijo de tipo (ej. WEATHER_BALL_FIRE -> "Weather Ball" + "(Fuego)")
    if len(parts) > 1 and parts[-1] in _TYPE_SUFFIX_ES:
        type_suffix = _TYPE_SUFFIX_ES[parts[-1]]
        base = " ".join(w.capitalize() for w in parts[:-1])
        return f"{base} ({type_suffix})"

    return " ".join(w.capitalize() for w in parts)


def format_moveset(moveset: list) -> dict:
    """
    Recibe ["FAST", "CHARGE1", "CHARGE2"] (formato de PvPoke: primero el rápido)
    y devuelve un dict legible.
    """
    if not moveset:
        return {"fast": "-", "charged": []}
    fast = format_move(moveset[0])
    charged = [format_move(m) for m in moveset[1:]]
    return {"fast": fast, "charged": charged}
