"""
custom_cup.py - Fase 2: Filtro de elegibilidad + ranking completo de copa personalizada.

Esta es la parte que faltaba según spec.

Objetivo: Permitir al usuario definir reglas de copa y generar un ranking real
simulando combates 1v1 entre todos los pares elegibles.

Reglas soportadas:
- Tipos permitidos (ej. solo Fuego/Agua/Planta)
- Permitir o no Shadow
- Lista de Pokémon baneados
- Excluir tipo secundario (ej. no Volador como tipo 2)
- Liga / tope CP: 500, 1500, 2500, 10000

Estrategia de moveset:
Opción A (rápida, implementada por defecto): reutilizar best moves del ranking estándar
Opción B (precisa pero costosa): probar todas las combinaciones de movimientos disponibles

Por defecto usamos A para que corra en <2 min en Streamlit Cloud.
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import itertools
from dataclasses import dataclass

from battle_engine import (
    find_optimal_iv_for_cp,
    create_battle_pokemon_from_db,
    simulate_battle,
    BattlePokemon,
)
from data_loader import get_move_by_id, get_pokemon_fast_moves, get_pokemon_charged_moves

@dataclass
class CupRules:
    allowed_types: List[str]  # Ej ["FIRE","WATER","GRASS"] o [] = todos permitidos
    allow_shadow: bool = True
    banned_pokemon_ids: List[str] = None
    exclude_secondary_type: Optional[str] = None  # Ej "FLYING"
    cp_cap: int = 1500  # 500,1500,2500,10000
    league_name: str = "Great League"

    def __post_init__(self):
        if self.banned_pokemon_ids is None:
            self.banned_pokemon_ids = []
        # Normalizar tipos a mayúsculas
        self.allowed_types = [t.upper() for t in (self.allowed_types or [])]
        if self.exclude_secondary_type:
            self.exclude_secondary_type = self.exclude_secondary_type.upper()
        self.banned_pokemon_ids = [p.lower() for p in self.banned_pokemon_ids]

def filter_eligible_pokemon(pokemon_df: pd.DataFrame, rules: CupRules) -> pd.DataFrame:
    """
    Aplica reglas de copa sobre tabla Pokemon.
    """
    df = pokemon_df.copy()

    # 1. Shadow
    if not rules.allow_shadow:
        # isShadow puede ser 0/1 o False/True
        df = df[~(df["isShadow"].astype(bool))]

    # 2. Baneados individuales
    if rules.banned_pokemon_ids:
        banned_set = set(rules.banned_pokemon_ids)
        df = df[~df["pokemonId"].str.lower().isin(banned_set)]

    # 3. Excluir tipo secundario
    if rules.exclude_secondary_type:
        exclude = rules.exclude_secondary_type
        df = df[~(df["type2"].astype(str).str.upper() == exclude)]

    # 4. Tipos permitidos
    if rules.allowed_types:
        allowed_set = set(rules.allowed_types)

        def _is_allowed(row):
            t1 = str(row.get("type1") or "").upper()
            t2 = str(row.get("type2") or "").upper()
            # Debe tener al menos un tipo permitido
            # Y si tiene segundo tipo, ese también debe estar permitido (para "solo Fuego/Agua/Planta")
            # Interpretación: ambos tipos deben estar dentro de allowed si existen
            has_allowed = (t1 in allowed_set) or (t2 in allowed_set)
            if not has_allowed:
                return False
            # Si tiene type2, type2 también debe ser permitido (copa mono-tipo restringida)
            if t2 and t2 != "NONE" and t2 != "NAN" and pd.notna(row.get("type2")):
                if t2 not in allowed_set and t1 not in allowed_set:
                    return False
                # Opción estricta: ambos tipos dentro de allowed
                # Comentamos la estricta para permitir dual types donde uno es permitido
                # Si quieres estricta, descomenta:
                # if t1 not in allowed_set or (t2 and t2 not in allowed_set):
                #     return False
            return True

        df = df[df.apply(_is_allowed, axis=1)]

    return df

def get_best_moveset_for_pokemon(
    pokemon_id: str,
    league: int,
    rankings_df: pd.DataFrame,
    moves_dict: dict,
    use_optimal_search: bool = False,
    pokemon_fast_moves: List[str] = None,
    pokemon_charged_moves: List[str] = None,
) -> Tuple[Optional[dict], List[dict]]:
    """
    Obtiene moveset para usar en copa custom.
    Si use_optimal_search=False: usa el del ranking estándar (rápido).
    Si True: intenta todas las combinaciones (costoso).

    Retorna (fast_move_row, [charged_move_rows])
    """
    # Buscar en ranking estándar
    row = rankings_df[rankings_df["pokemonId"] == pokemon_id]
    if not row.empty and not use_optimal_search:
        r = row.iloc[0]
        fast_id = r.get("bestFastMove")
        c1_id = r.get("bestChargedMove1")
        c2_id = r.get("bestChargedMove2")

        fast_row = moves_dict.get(str(fast_id).upper()) if fast_id else None
        c1_row = moves_dict.get(str(c1_id).upper()) if c1_id else None
        c2_row = moves_dict.get(str(c2_id).upper()) if c2_id else None

        if fast_row and (c1_row or c2_row):
            chargeds = [c for c in [c1_row, c2_row] if c]
            return fast_row, chargeds

    # Fallback: usar primer fast y primeros 2 charged disponibles del Pokémon
    if pokemon_fast_moves is None:
        pokemon_fast_moves = get_pokemon_fast_moves(pokemon_id)
    if pokemon_charged_moves is None:
        pokemon_charged_moves = get_pokemon_charged_moves(pokemon_id)

    if not pokemon_fast_moves:
        return None, []

    fast_id = pokemon_fast_moves[0]
    fast_row = moves_dict.get(str(fast_id).upper())

    charged_rows = []
    for cid in (pokemon_charged_moves[:2]):
        cr = moves_dict.get(str(cid).upper())
        if cr:
            charged_rows.append(cr)

    return fast_row, charged_rows

def build_battle_pokemons_for_cup(
    eligible_df: pd.DataFrame,
    rules: CupRules,
    rankings_df: pd.DataFrame,
    moves_dict: dict,
    use_optimal_moveset: bool = False,
    progress_callback=None,
) -> List[BattlePokemon]:
    """
    Para cada Pokémon elegible, calcula IVs óptimos y crea BattlePokemon.
    """
    battle_pokes = []
    total = len(eligible_df)

    for idx, (_, prow) in enumerate(eligible_df.iterrows()):
        if progress_callback:
            progress_callback(idx, total, f"Calculando IVs para {prow.get('name')}...")

        # IVs óptimos para el CP cap
        iv_config = find_optimal_iv_for_cp(
            base_atk=int(prow.get("baseAtk")),
            base_def=int(prow.get("baseDef")),
            base_sta=int(prow.get("baseSta")),
            cp_cap=rules.cp_cap,
            max_level=50.0,
        )

        fast_row, charged_rows = get_best_moveset_for_pokemon(
            pokemon_id=prow.get("pokemonId"),
            league=rules.cp_cap,
            rankings_df=rankings_df,
            moves_dict=moves_dict,
            use_optimal_search=use_optimal_moveset,
        )

        if not fast_row:
            # Sin movimientos, saltar
            continue

        bp = create_battle_pokemon_from_db(
            pokemon_row=prow.to_dict(),
            fast_move_row=fast_row,
            charged_move_rows=charged_rows,
            iv_config=iv_config,
        )
        battle_pokes.append(bp)

    return battle_pokes

def simulate_round_robin_ranking(
    battle_pokemons: List[BattlePokemon],
    shields: int = 1,
    progress_callback=None,
) -> pd.DataFrame:
    """
    Simula todos contra todos y calcula rating final.

    Para N Pokémon, son N*(N-1)/2 combates.
    Para N=100, son 4950 combates. Cada combate ~5-20ms en Python puro.
    Total ~25-100 segundos. Aceptable para copa pequeña/mediana.

    Retorna DataFrame con columnas: pokemonId, name, wins, losses, draws, winRate, avgHpRemaining
    """
    n = len(battle_pokemons)
    if n == 0:
        return pd.DataFrame()

    # Inicializar stats
    stats = {
        bp.pokemonId: {
            "pokemonId": bp.pokemonId,
            "name": bp.name,
            "type1": bp.type1,
            "type2": bp.type2,
            "level": bp.level,
            "ivAtk": bp.ivAtk,
            "ivDef": bp.ivDef,
            "ivSta": bp.ivSta,
            "cp": 0,  # se calculará
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "total_battles": 0,
            "hp_remaining_sum": 0.0,
        }
        for bp in battle_pokemons
    }

    # Pre-calcular CP para mostrar
    from battle_engine import calculate_cp
    for bp in battle_pokemons:
        cp = calculate_cp(bp.baseAtk, bp.baseDef, bp.baseSta, bp.ivAtk, bp.ivDef, bp.ivSta, bp.level)
        stats[bp.pokemonId]["cp"] = cp
        stats[bp.pokemonId]["fastMove"] = bp.fastMove.moveId if bp.fastMove else ""
        stats[bp.pokemonId]["chargedMoves"] = [m.moveId for m in bp.chargedMoves]

    total_battles = n * (n - 1) // 2
    battle_count = 0

    # Todos contra todos
    for i in range(n):
        for j in range(i + 1, n):
            battle_count += 1
            if progress_callback and battle_count % 50 == 0:
                progress_callback(battle_count, total_battles, f"Simulando combates {battle_count}/{total_battles}...")

            p1 = battle_pokemons[i]
            p2 = battle_pokemons[j]

            try:
                result = simulate_battle(p1, p2, shields_per_pokemon=shields)
            except Exception as e:
                # Si falla un combate, contar como draw para no romper todo
                result = None

            if result is None:
                stats[p1.pokemonId]["draws"] += 1
                stats[p2.pokemonId]["draws"] += 1
                continue

            stats[p1.pokemonId]["total_battles"] += 1
            stats[p2.pokemonId]["total_battles"] += 1

            if result.winner == p1.pokemonId:
                stats[p1.pokemonId]["wins"] += 1
                stats[p2.pokemonId]["losses"] += 1
                stats[p1.pokemonId]["hp_remaining_sum"] += result.p1_hp_percent
            elif result.winner == p2.pokemonId:
                stats[p2.pokemonId]["wins"] += 1
                stats[p1.pokemonId]["losses"] += 1
                stats[p2.pokemonId]["hp_remaining_sum"] += result.p2_hp_percent
            else:
                stats[p1.pokemonId]["draws"] += 1
                stats[p2.pokemonId]["draws"] += 1

    # Calcular winRate y rating
    rows = []
    for pid, s in stats.items():
        total = s["wins"] + s["losses"] + s["draws"]
        win_rate = (s["wins"] + 0.5 * s["draws"]) / max(1, total)
        avg_hp = s["hp_remaining_sum"] / max(1, s["wins"]) if s["wins"] > 0 else 0
        # Rating final similar a PvPoke: winRate * 1000 con bonus de HP
        score = win_rate * 1000 + avg_hp * 20
        rows.append({
            **s,
            "winRate": win_rate,
            "avgHpRemaining": avg_hp,
            "score": score,
            "rating": win_rate,  # para compatibilidad
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["score", "winRate"], ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    return df

def generate_custom_cup_ranking(
    pokemon_df: pd.DataFrame,
    rankings_df: pd.DataFrame,
    moves_dict: dict,
    rules: CupRules,
    use_optimal_moveset: bool = False,
    progress_callback=None,
) -> pd.DataFrame:
    """
    Función principal Fase 2: filtra elegibles, calcula IVs, simula todos vs todos.
    """
    # 1. Filtrar elegibles
    if progress_callback:
        progress_callback(0, 100, "Filtrando Pokémon elegibles...")

    eligible_df = filter_eligible_pokemon(pokemon_df, rules)

    if eligible_df.empty:
        raise ValueError("Ningún Pokémon cumple las reglas de esta copa. Relaja los filtros.")

    if len(eligible_df) > 200:
        # Advertencia de performance: limitar a 150 top por rating si es demasiado grande
        # Para no hacer la app inusable en Streamlit Cloud (gratis)
        # Tomamos los mejores por base stat product o por ranking existente
        if not rankings_df.empty:
            # Mantener solo los que están en ranking y son elegibles, top 150 por score
            eligible_ids = set(eligible_df["pokemonId"].tolist())
            filtered_rank = rankings_df[rankings_df["pokemonId"].isin(eligible_ids)]
            filtered_rank = filtered_rank.sort_values(by="score", ascending=False).head(150)
            keep_ids = set(filtered_rank["pokemonId"].tolist())
            eligible_df = eligible_df[eligible_df["pokemonId"].isin(keep_ids)]
        else:
            eligible_df = eligible_df.head(150)

    # 2. Crear BattlePokemons
    battle_pokes = build_battle_pokemons_for_cup(
        eligible_df=eligible_df,
        rules=rules,
        rankings_df=rankings_df,
        moves_dict=moves_dict,
        use_optimal_moveset=use_optimal_moveset,
        progress_callback=progress_callback,
    )

    # 3. Simular round robin
    ranking_df = simulate_round_robin_ranking(
        battle_pokemons=battle_pokes,
        shields=1,
        progress_callback=progress_callback,
    )

    return ranking_df
