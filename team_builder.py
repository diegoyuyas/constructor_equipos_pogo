"""
<<<<<<< HEAD
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
=======
team_builder.py
----------------
Lógica central del generador de equipos.

Idea del algoritmo (nivel Intermedio: tipos + roles):

1. Cada Pokémon en los rankings de PvPoke trae:
   - "matchups": los 5 rivales contra los que MEJOR le va (a quién le gana)
   - "counters":  los 5 rivales contra los que PEOR le va (quién le gana a él, sus amenazas)

2. Para encontrar buenos COMPAÑEROS de equipo para un Pokémon "ancla" (anchor):
   - Tomamos sus "counters" -> esas son las amenazas que el equipo necesita cubrir.
   - Buscamos, entre todo el meta, qué Pokémon tienen buenos "matchups" contra
     esas mismas amenazas. Ese Pokémon "cubre" al ancla.
   - Esto es exactamente la filosofía de PvP de Pokémon GO: "cubre lo que te gana".

3. Además, calculamos un ROL aproximado para cada Pokémon, usando sus stats:
   - LEAD (líder): buen "rating" general (le va bien contra el meta amplio) y
     bulk (def*hp) medio-alto -> aguanta el primer choque a ciegas.
   - SWITCH (cambio seguro): bulk muy alto (def*hp) -> se usa para entrar sin
     miedo cuando el líder cae.
   - CLOSER (cerrador): ataque alto -> se usa al final para rematar con daño.

4. El equipo final intenta tener 3 roles distintos (lead + switch + closer)
   además de una buena cobertura de amenazas.
"""

from dataclasses import dataclass, field
from moves import format_moveset


@dataclass
class TeamMember:
    species_id: str
    species_name: str
    rating: float
    synergy_score: float
    role: str
    covers: list  # amenazas del ancla que este compañero cubre
    moveset: dict
    stats: dict


def _bulk(mon: dict) -> float:
    s = mon.get("stats", {})
    return s.get("def", 0) * s.get("hp", 0)


def classify_role(mon: dict, all_ratings: list, all_bulk: list, all_atk: list) -> str:
    """
    Clasifica un Pokémon como 'Lead', 'Switch' o 'Closer' usando percentiles
    relativos al resto del meta (para que sea comparable entre ligas distintas).
    """
    def percentile(value, population):
        if not population:
            return 0.5
        below = sum(1 for v in population if v <= value)
        return below / len(population)

    rating = mon.get("rating", 0)
    bulk = _bulk(mon)
    atk = mon.get("stats", {}).get("atk", 0)

    p_rating = percentile(rating, all_ratings)
    p_bulk = percentile(bulk, all_bulk)
    p_atk = percentile(atk, all_atk)

    lead_score = 0.6 * p_rating + 0.4 * p_bulk
    switch_score = p_bulk
    closer_score = p_atk

    scores = {"Líder (Lead)": lead_score, "Cambio seguro (Switch)": switch_score, "Cerrador (Closer)": closer_score}
    return max(scores, key=scores.get)


def find_best_partners(rankings: list, anchor_id: str, top_pool: int = 60, num_results: int = 8):
    """
    Dado un Pokémon ancla (anchor_id) y la lista completa de rankings de una liga,
    devuelve una lista ordenada de los mejores compañeros de equipo.

    - top_pool: cuántos de los Pokémon mejor rankeados se consideran como candidatos
      (para no recomendar algo totalmente fuera del meta).
    - num_results: cuántos compañeros devolver en total (los primeros 2 son los
      "mejores", el resto son alternativas).
    """
    anchor = next((m for m in rankings if m["speciesId"] == anchor_id), None)
    if anchor is None:
        return None, []

    # Amenazas del ancla: quién le gana
    threats = {c["opponent"] for c in anchor.get("counters", [])}
    threat_weight = {c["opponent"]: c.get("rating", 500) for c in anchor.get("counters", [])}

    # Pool de candidatos: los mejores N del meta (evita recomendar Pokémon irrelevantes)
    pool = sorted(rankings, key=lambda m: -m.get("rating", 0))[:top_pool]

    # Datos para clasificar roles de forma relativa a TODO el meta (no solo el pool)
    all_ratings = [m.get("rating", 0) for m in rankings]
    all_bulk = [_bulk(m) for m in rankings]
    all_atk = [m.get("stats", {}).get("atk", 0) for m in rankings]

    candidates = []
    for mon in pool:
        if mon["speciesId"] == anchor_id:
            continue

        # ¿Qué tan bien cubre este candidato a las amenazas del ancla?
        mon_matchups = {m["opponent"]: m.get("rating", 500) for m in mon.get("matchups", [])}
        covers = [t for t in threats if t in mon_matchups]

        # Puntaje de sinergia: promedio de qué tan fuerte gana el candidato
        # contra las amenazas que sí cubre, ponderado por cuántas amenazas cubre.
        if covers:
            avg_matchup_strength = sum(mon_matchups[t] for t in covers) / len(covers)
            coverage_ratio = len(covers) / max(len(threats), 1)
        else:
            avg_matchup_strength = 0
            coverage_ratio = 0

        # También sumamos un poco el propio "rating" general del candidato
        # (que sea bueno en general, no solo contra las amenazas del ancla)
        synergy_score = (
            0.55 * avg_matchup_strength / 10  # normalizado aprox a 0-100
            + 0.30 * coverage_ratio * 100
            + 0.15 * mon.get("rating", 0) / 10
        )

        role = classify_role(mon, all_ratings, all_bulk, all_atk)

        candidates.append(TeamMember(
            species_id=mon["speciesId"],
            species_name=mon["speciesName"],
            rating=mon.get("rating", 0),
            synergy_score=round(synergy_score, 1),
            role=role,
            covers=covers,
            moveset=format_moveset(mon.get("moveset", [])),
            stats=mon.get("stats", {}),
        ))

    candidates.sort(key=lambda c: -c.synergy_score)
    return anchor, candidates[:num_results]


def build_suggested_team(anchor, partners: list):
    """
    A partir del ancla y la lista de compañeros ya ordenada por sinergia,
    arma un equipo sugerido de 3 intentando variar roles (lead/switch/closer).
    Devuelve (team_of_3, alternatives).
    """
    if not partners:
        return [], []

    anchor_role = "Ancla (tu elección)"
    team = [{"role": anchor_role, "member": None, "is_anchor": True}]

    used_roles = set()
    alternatives = []

    for p in partners:
        if len(team) >= 3:
            alternatives.append(p)
            continue
        if p.role not in used_roles or len(used_roles) >= 3:
            team.append({"role": p.role, "member": p, "is_anchor": False})
            used_roles.add(p.role)
        else:
            alternatives.append(p)

    # Si no se llenó por variedad de roles, completar con los mejores restantes
    idx = 0
    while len(team) < 3 and idx < len(alternatives):
        team.append({"role": alternatives[idx].role, "member": alternatives[idx], "is_anchor": False})
        idx += 1
    alternatives = alternatives[idx:]

    return team, alternatives
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
