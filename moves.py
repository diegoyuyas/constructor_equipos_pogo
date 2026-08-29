"""
<<<<<<< HEAD
moves.py - Manejo de nombres de movimientos en español oficial.

Este archivo sirve como fallback cuando PokeAPI no tiene el nombre
o cuando la BD aún no tiene nameEs poblado.

La fuente de verdad es:
1. Moves.nameEs de la BD (llenado vía PokeAPI)
2. Este diccionario fallback
3. El nombre en inglés original
"""

# Diccionario fallback con traducciones oficiales verificadas en el juego
# Clave = moveId en mayúsculas como en la BD de PvPoke
FALLBACK_SPANISH = {
    # Rápidos
    "COUNTER": "Contraataque",
    "MUD_SHOT": "Disparo Lodo",
    "VOLT_SWITCH": "Voltiocambio",
    "DRAGON_BREATH": "Dragoaliento",
    "WING_ATTACK": "Ataque Ala",
    "FAIRY_WIND": "Viento Feérico",
    "WATERFALL": "Cascada",
    "EMBER": "Ascuas",
    "FIRE_SPIN": "Giro Fuego",
    "BULLET_SEED": "Balas Semilla",
    "VINE_WHIP": "Látigo Cepa",
    "TACKLE": "Placaje",
    "POISON_STING": "Puya Nociva",
    "LICK": "Lengüetazo",
    "SHADOW_CLAW": "Garra Umbría",
    "CONFUSION": "Confusión",
    "PSYCHO_CUT": "Corte Psíquico",
    "SNARL": "Alboroto",
    "CHARM": "Encanto",
    "DRAGON_TAIL": "Cola Dragón",
    "INCINERATE": "Calcinación",
    "LOCK_ON": "Fijar Blanco",
    "THUNDER_SHOCK": "Impactrueno",
    "QUICK_ATTACK": "Ataque Rápido",
    "MUD_SLAP": "Bofetón Lodo",
    "ROCK_SMASH": "Golpe Roca",
    "WATER_GUN": "Pistola Agua",
    "BUG_BITE": "Picadura",
    # Cargados
    "AQUA_TAIL": "Cola Acua",
    "ICE_BEAM": "Rayo Hielo",
    "BODY_SLAM": "Golpe Cuerpo",
    "SHADOW_BALL": "Bola Sombra",
    "SLUDGE_BOMB": "Bomba Lodo",
    "THUNDERBOLT": "Rayo",
    "FLAMETHROWER": "Lanzallamas",
    "HYDRO_PUMP": "Hidrobomba",
    "EARTHQUAKE": "Terremoto",
    "BULLDOZE": "Terratemblor",
    "TWISTER": "Viento Hielo",  # En GO traducido como Ciclón en algunos casos
    "WATER_PULSE": "Pulso Agua",
    "GIGATON_HAMMER": "Martillo Colosal",
    "DISARMING_VOICE": "Voz Cautivadora",
    "MOONBLAST": "Fuerza Lunar",
    "PLAY_ROUGH": "Juego Sucio",
    "DRACO_METEOR": "Cometa Draco",
    "OUTRAGE": "Enfado",
    "CLOSE_COMBAT": "A Bocajarro",
    "FRENZY_PLANT": "Planta Feroz",
    "BLAST_BURN": "Anillo Ígneo",
    "HYDRO_CANNON": "Hidrocañón",
    "WEATHER_BALL": "Bola Meteoro",
    "ROCK_SLIDE": "Avalancha",
    "STONE_EDGE": "Roca Afilada",
    "FOUL_PLAY": "Juego Sucio",
    "BRAVE_BIRD": "Pájaro Osado",
    "SKY_ATTACK": "Ataque Aéreo",
}

# Traducción de tipos para sufijos como WEATHER_BALL_FIRE
TYPE_SPANISH = {
    "NORMAL": "Normal",
    "FIRE": "Fuego",
    "WATER": "Agua",
    "ELECTRIC": "Eléctrico",
    "GRASS": "Planta",
    "ICE": "Hielo",
    "FIGHTING": "Lucha",
    "POISON": "Veneno",
    "GROUND": "Tierra",
    "FLYING": "Volador",
    "PSYCHIC": "Psíquico",
    "BUG": "Bicho",
    "ROCK": "Roca",
    "GHOST": "Fantasma",
    "DRAGON": "Dragón",
    "DARK": "Siniestro",
    "STEEL": "Acero",
    "FAIRY": "Hada",
}

def parse_move_id_with_suffix(move_id: str):
    """
    Separa sufijos de tipo, ej: WEATHER_BALL_FIRE -> (WEATHER_BALL, FIRE)
    Retorna (base_move_id, suffix_type_or_None)
    """
    if not move_id:
        return move_id, None
    parts = move_id.split("_")
    # Si la última parte es un tipo válido y hay más de 1 parte, es sufijo
    if len(parts) >= 2 and parts[-1] in TYPE_SPANISH:
        base = "_".join(parts[:-1])
        suffix = parts[-1]
        # Evitar falsos positivos: ej. FIRE no siempre es sufijo si el move es FIRE_PUNCH (ese sí es tipo fuego pero no sufijo de weather ball)
        # Solo tratamos como sufijo para moves que sabemos que tienen variantes
        if base in ("WEATHER_BALL", "TECHNO_BLAST", "NATURE_POWER", "JUDGMENT", "REVELATION_DANCE"):
            return base, suffix
        # También para Weather Ball específicamente
        if base.startswith("WEATHER_BALL"):
            return "WEATHER_BALL", suffix
    return move_id, None

def get_spanish_name(move_id: str, name_en: str = None, name_es_db: str = None) -> str:
    """
    Obtiene el nombre en español con prioridad:
    1. nameEs de la BD (si existe)
    2. Fallback diccionario
    3. Inglés original
    """
    # 1. BD ya tiene traducción oficial
    if name_es_db and str(name_es_db).strip():
        return str(name_es_db).strip()

    if not move_id:
        return name_en or "Desconocido"

    move_id_upper = move_id.upper()

    # 2. Manejo de sufijos
    base_id, suffix = parse_move_id_with_suffix(move_id_upper)
    base_name_es = None

    if base_id in FALLBACK_SPANISH:
        base_name_es = FALLBACK_SPANISH[base_id]
    elif move_id_upper in FALLBACK_SPANISH:
        base_name_es = FALLBACK_SPANISH[move_id_upper]

    if base_name_es and suffix:
        tipo_es = TYPE_SPANISH.get(suffix, suffix)
        return f"{base_name_es} ({tipo_es})"

    if base_name_es:
        return base_name_es

    # 3. Si no hay traducción, devolver inglés limpio
    if name_en:
        return name_en

    # Último recurso: formatear el ID
    return move_id.replace("_", " ").title()

def format_moveset_display(fast_move_id, charged_move_ids, moves_dict):
    """
    Formatea un moveset completo en español para mostrar en la UI.
    moves_dict: dict {moveId: {name, nameEs, ...}}
    """
    def _get(m_id):
        if not m_id:
            return "-"
        info = moves_dict.get(m_id.upper(), {}) if moves_dict else {}
        return get_spanish_name(m_id, info.get("name"), info.get("nameEs"))

    fast = _get(fast_move_id)
    chargeds = [_get(c) for c in (charged_move_ids or []) if c]
    if chargeds:
        return f"{fast} + {' / '.join(chargeds)}"
    return fast
=======
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
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
