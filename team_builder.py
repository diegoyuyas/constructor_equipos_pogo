"""
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
