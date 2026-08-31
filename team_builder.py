"""
team_builder.py - Algoritmo de sinergia para generar equipos PvP.

Lógica (según spec 5.1):
1. Toma los counters del ancla (quién le gana) = amenazas a cubrir
2. Busca entre los mejores del meta quién tiene buenos matchups contra esas amenazas
3. Clasifica cada candidato en rol por percentiles: Líder, Switch, Closer
4. Arma equipo de 3 intentando variar roles

También incluye ranking filtrado por tipo (5.3).
"""

import json
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np

from data_loader import parse_score_detail

# ----------------------------------------------------------------------
# Helpers para parsear scoreDetail
# ----------------------------------------------------------------------

def get_counters_from_detail(detail: dict, top_n=10) -> List[str]:
    """
    Extrae los counters (quienes le ganan al Pokémon).
    En formato PvPoke: detail["counters"] = [{"opponent":"pokemonId","rating":...}, ...]
    Los counters son los que tienen rating alto contra nosotros.
    """
    if not detail:
        return []
    counters = detail.get("counters", [])
    # Ordenar por rating descendente (los que más nos ganan primero)
    counters = sorted(counters, key=lambda x: x.get("rating", 0), reverse=True)
    return [c.get("opponent") for c in counters[:top_n] if c.get("opponent")]

def get_matchups_from_detail(detail: dict) -> Dict[str, float]:
    """
    Devuelve dict {opponentId: rating} de matchups favorables.
    rating >500 significa que ganamos ese matchup (en escala 0-1000 de PvPoke)
    """
    if not detail:
        return {}
    matchups = detail.get("matchups", [])
    return {m.get("opponent"): m.get("rating", 0) for m in matchups if m.get("opponent")}

def calculate_coverage_score(candidate_detail: dict, threats: List[str]) -> Tuple[int, float]:
    """
    Cuántas amenazas cubre el candidato y con qué fuerza.
    Retorna (num_threats_covered, avg_rating_vs_threats)
    """
    if not candidate_detail or not threats:
        return 0, 0.0

    matchups = get_matchups_from_detail(candidate_detail)
    covered = 0
    total_rating = 0

    for threat in threats:
        rating = matchups.get(threat, 0)
        if rating > 500:  # gana el matchup
            covered += 1
            total_rating += rating

    avg = total_rating / covered if covered > 0 else 0
    return covered, avg

# ----------------------------------------------------------------------
# Roles por percentiles
# ----------------------------------------------------------------------

def calculate_roles(meta_df: pd.DataFrame, pokemon_df: pd.DataFrame) -> Dict[str, str]:
    """
    Clasifica cada Pokémon del meta en un rol aproximado:
    - Switch / Cambio Seguro: bulk muy alto (Def*Sta alto)
    - Closer / Cerrador: ataque alto
    - Líder: rating alto + bulk medio

    meta_df debe tener score, y hacemos join con pokemon_df para stats base.
    """
    if meta_df.empty or pokemon_df.empty:
        return {}

    # Merge para obtener base stats
    merged = meta_df.merge(pokemon_df[["pokemonId","baseAtk","baseDef","baseSta"]], on="pokemonId", how="left")

    merged["bulk"] = merged["baseDef"] * merged["baseSta"]
    merged["atk_stat"] = merged["baseAtk"]

    # Percentiles
    bulk_80 = merged["bulk"].quantile(0.80)
    bulk_40 = merged["bulk"].quantile(0.40)
    bulk_70 = merged["bulk"].quantile(0.70)
    atk_75 = merged["atk_stat"].quantile(0.75)
    score_70 = merged["score"].quantile(0.70) if "score" in merged.columns else 0

    roles = {}
    for _, row in merged.iterrows():
        pid = row["pokemonId"]
        bulk = row["bulk"]
        atk = row["atk_stat"]
        score = row.get("score", 0)

        if bulk >= bulk_80:
            roles[pid] = "Switch"
        elif atk >= atk_75:
            roles[pid] = "Closer"
        elif score >= score_70 and bulk >= bulk_40 and bulk <= bulk_70:
            roles[pid] = "Líder"
        else:
            # Fallback
            if bulk >= bulk_70:
                roles[pid] = "Switch"
            elif atk >= atk_75:
                roles[pid] = "Closer"
            else:
                roles[pid] = "Líder"

    return roles

# ----------------------------------------------------------------------
# Generador de equipos core
# ----------------------------------------------------------------------

def build_team(
    anchor_id: str,
    league: int,
    rankings_df: pd.DataFrame,
    pokemon_df: pd.DataFrame,
    moves_dict: dict,
    top_n_candidates: int = 100,
    num_alternatives: int = 6,
) -> Dict:
    """
    Genera equipo de 3 con ancla + 2 compañeros.

    rankings_df: ranking de la liga (ya ordenado por rank)
    pokemon_df: datos de Pokemon
    moves_dict: dict de Moves para mostrar nombres

    Retorna dict con:
    - anchor: info ancla
    - threats: lista de amenazas
    - team: lista de 2 compañeros principales (con score de sinergia, rol, etc.)
    - alternatives: lista adicional
    """
    if rankings_df.empty:
        raise ValueError(f"No hay ranking para liga {league}. Verifica la BD.")

    # Buscar ancla en ranking
    anchor_row = rankings_df[rankings_df["pokemonId"] == anchor_id]
    if anchor_row.empty:
        # Si ancla no está en top N, buscar su entrada aunque esté más abajo
        # (para obtener sus counters)
        raise ValueError(f"El Pokémon {anchor_id} no está en el ranking top {len(rankings_df)} de la liga {league}. Prueba con otro ancla más meta o aumenta el límite.")

    anchor_row = anchor_row.iloc[0]
    anchor_detail = parse_score_detail(anchor_row.get("scoreDetail"))

    threats = get_counters_from_detail(anchor_detail, top_n=12)

    # Calcular roles para todo el meta
    roles = calculate_roles(rankings_df, pokemon_df)

    # Evaluar candidatos (excluir el ancla mismo)
    candidates = []
    # Tomar top N candidatos del meta
    top_candidates_df = rankings_df.head(top_n_candidates)
    for _, cand_row in top_candidates_df.iterrows():
        cand_id = cand_row["pokemonId"]
        if cand_id == anchor_id:
            continue

        cand_detail = parse_score_detail(cand_row.get("scoreDetail"))
        covered, avg_rating = calculate_coverage_score(cand_detail, threats)

        # Score de sinergia: ponderar cobertura + rating base del candidato
        # Fórmula: (covered * 100) + (avg_rating * 0.5) + (cand_row.score * 0.3)
        synergy = (covered * 120) + (avg_rating * 0.4) + (cand_row.get("score", 0) * 0.3)

        # Bonus por rol diferente al ancla (para variedad)
        anchor_role = roles.get(anchor_id, "Líder")
        cand_role = roles.get(cand_id, "Líder")
        if cand_role != anchor_role:
            synergy += 15

        candidates.append({
            "pokemonId": cand_id,
            "score": cand_row.get("score", 0),
            "rank": cand_row.get("rank", 999),
            "bestFastMove": cand_row.get("bestFastMove"),
            "bestChargedMove1": cand_row.get("bestChargedMove1"),
            "bestChargedMove2": cand_row.get("bestChargedMove2"),
            "detail": cand_detail,
            "covered": covered,
            "avgRatingVsThreats": avg_rating,
            "synergy": synergy,
            "role": cand_role,
        })

    # Ordenar por sinergia descendente
    candidates.sort(key=lambda x: x["synergy"], reverse=True)

    # Armar equipo intentando variar roles
    team = []
    used_roles = {roles.get(anchor_id, "Líder")}

    for cand in candidates:
        if len(team) >= 2:
            break
        # Preferir rol no usado aún
        if cand["role"] not in used_roles or len(team) == 1:
            team.append(cand)
            used_roles.add(cand["role"])

    # Si no llenamos 2 por variedad de roles, rellenar con los mejores restantes
    if len(team) < 2:
        for cand in candidates:
            if cand not in team:
                team.append(cand)
            if len(team) >= 2:
                break

    alternatives = [c for c in candidates if c not in team][:num_alternatives]

    # Enriquecer con datos de Pokemon (nombre, tipos)
    def enrich(c):
        p = pokemon_df[pokemon_df["pokemonId"] == c["pokemonId"]]
        if not p.empty:
            p = p.iloc[0]
            c["name"] = p.get("name")
            c["type1"] = p.get("type1")
            c["type2"] = p.get("type2")
            c["isShadow"] = bool(p.get("isShadow"))
        else:
            c["name"] = c["pokemonId"]
            c["type1"] = "UNKNOWN"
            c["type2"] = None
            c["isShadow"] = False
        return c

    return {
        "anchor": {
            "pokemonId": anchor_id,
            "name": pokemon_df[pokemon_df["pokemonId"]==anchor_id].iloc[0].get("name") if not pokemon_df[pokemon_df["pokemonId"]==anchor_id].empty else anchor_id,
            "rank": anchor_row.get("rank"),
            "score": anchor_row.get("score"),
            "bestFastMove": anchor_row.get("bestFastMove"),
            "bestChargedMove1": anchor_row.get("bestChargedMove1"),
            "bestChargedMove2": anchor_row.get("bestChargedMove2"),
            "role": roles.get(anchor_id, "Líder"),
            "type1": pokemon_df[pokemon_df["pokemonId"]==anchor_id].iloc[0].get("type1") if not pokemon_df[pokemon_df["pokemonId"]==anchor_id].empty else None,
            "type2": pokemon_df[pokemon_df["pokemonId"]==anchor_id].iloc[0].get("type2") if not pokemon_df[pokemon_df["pokemonId"]==anchor_id].empty else None,
        },
        "threats": threats,
        "team": [enrich(c) for c in team],
        "alternatives": [enrich(c) for c in alternatives],
        "roles": roles,
    }

# ----------------------------------------------------------------------
# Ranking filtrado por tipo (5.3)
# ----------------------------------------------------------------------

def filter_ranking_by_type(
    rankings_df: pd.DataFrame,
    pokemon_df: pd.DataFrame,
    allowed_types: List[str],
    limit: int = 100,
) -> pd.DataFrame:
    """
    Filtra ranking por tipo, reutilizando rating ya calculado contra meta abierto.
    Mismo enfoque que usa el filtro de tipo de PvPoke.com

    allowed_types: lista de tipos ej ["FIRE"] o ["FIRE","WATER"]
    Retorna DataFrame filtrado ordenado por score descendente
    """
    if not allowed_types:
        return rankings_df.head(limit)

    allowed_upper = [t.upper() for t in allowed_types]

    merged = rankings_df.merge(
        pokemon_df[["pokemonId","name","type1","type2","baseAtk","baseDef","baseSta"]],
        on="pokemonId", how="left"
    )

    def _has_allowed_type(row):
        t1 = str(row.get("type1") or "").upper()
        t2 = str(row.get("type2") or "").upper()
        return (t1 in allowed_upper) or (t2 in allowed_upper)

    filtered = merged[merged.apply(_has_allowed_type, axis=1)]
    # Re-ordenar por score (ya viene por rank, pero por si acaso)
    filtered = filtered.sort_values(by="score", ascending=False)
    return filtered.head(limit)
