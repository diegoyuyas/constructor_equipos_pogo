"""
data_loader.py
---------------
Lee los datos de PvP desde una de dos fuentes, detectando automáticamente
cuál usar:

1. MODO NUBE (por defecto si existe "pogo_data.sqlite" junto a este archivo):
   lee de ese archivo SQLite. Esto es lo que usa la app cuando está
   desplegada en Streamlit Community Cloud, porque ahí no hay acceso a tu
   SQL Server local.

2. MODO LOCAL (si no existe ese archivo): se conecta directamente a tu
   SQL Server Express (bd_pkm_pro) vía pyodbc. Útil mientras desarrollas
   en tu propia PC con datos siempre frescos.

Para actualizar los datos de la nube: corre `python export_to_sqlite.py`
en tu PC (con SQL Server) y sube el pogo_data.sqlite resultante a GitHub.
"""

import json
import os
import sqlite3

import streamlit as st

# ---------- Configuración de conexión a SQL Server (modo local) ----------
SERVER = r"LOCALHOST\SQLEXPRESS"
DATABASE = "bd_pkm_pro"
DRIVER = "{ODBC Driver 17 for SQL Server}"  # si falla, prueba "{ODBC Driver 18 for SQL Server}" o "{SQL Server}"

# ---------- Archivo SQLite (modo nube) ----------
SQLITE_FILE = os.path.join(os.path.dirname(__file__), "pogo_data.sqlite")

DEFAULT_CUP = "all"
DEFAULT_CATEGORY = "overall"

LEAGUES = {
    "great": {"name": "Great League (Super Liga)", "cp": 1500},
    "ultra": {"name": "Ultra League", "cp": 2500},
    "master": {"name": "Master League", "cp": 10000},
}

QUERY = """
    SELECT
        r.pokemonId,
        p.name,
        r.score,
        r.scoreDetail,
        COALESCE(fm.nameEs, fm.name) AS fastMoveName,
        COALESCE(cm1.nameEs, cm1.name) AS charged1Name,
        COALESCE(cm2.nameEs, cm2.name) AS charged2Name,
        p.baseAtk, p.baseDef, p.baseSta
    FROM Rankings r
    JOIN Pokemon p ON r.pokemonId = p.pokemonId
    LEFT JOIN Moves fm  ON r.bestFastMove = fm.moveId
    LEFT JOIN Moves cm1 ON r.bestChargedMove1 = cm1.moveId
    LEFT JOIN Moves cm2 ON r.bestChargedMove2 = cm2.moveId
    WHERE r.league = ? AND r.cup = ? AND r.category = ?
    ORDER BY r.rank ASC
"""


def using_sqlite() -> bool:
    """True si debemos leer del archivo SQLite (modo nube)."""
    return os.path.exists(SQLITE_FILE)


def _run_query(league_cp: int, cup: str, category: str):
    """
    Ejecuta la consulta en el backend que corresponda y devuelve una lista
    de dicts (uno por fila), sin importar si vino de SQLite o SQL Server.
    """
    if using_sqlite():
        conn = sqlite3.connect(SQLITE_FILE)
        cursor = conn.cursor()
        cursor.execute(QUERY, (league_cp, cup, category))
        columns = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
        conn.close()
    else:
        import pyodbc  # solo se importa si realmente hace falta (no está disponible en la nube)
        conn_str = (
            f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
        )
        try:
            conn = pyodbc.connect(conn_str, timeout=10)
        except pyodbc.Error as e:
            raise RuntimeError(
                f"No se pudo conectar a SQL Server ({SERVER} / {DATABASE}). "
                f"Verifica que el servicio 'SQL Server (SQLEXPRESS)' esté corriendo. "
                f"Detalle técnico: {e}"
            )
        cursor = conn.cursor()
        cursor.execute(QUERY, league_cp, cup, category)
        columns = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
        conn.close()

    return [dict(zip(columns, row)) for row in rows]


def _safe_json_loads(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _row_to_pokemon_dict(row: dict):
    """
    Convierte una fila (ya en dict) en el formato que espera team_builder.py:
    speciesId, speciesName, rating, matchups, counters, moveset, stats
    """
    detail = _safe_json_loads(row.get("scoreDetail"))

    matchups = detail.get("matchups", [])
    counters = detail.get("counters", [])

    stats = detail.get("stats")
    if not stats:
        atk, dfe, hp = row.get("baseAtk") or 0, row.get("baseDef") or 0, row.get("baseSta") or 0
        stats = {"atk": atk, "def": dfe, "hp": hp, "product": atk * dfe * hp}

    rating = detail.get("rating")
    if rating is None:
        rating = (row.get("score") or 0) * 10

    moveset = [m for m in (row.get("fastMoveName"), row.get("charged1Name"), row.get("charged2Name")) if m]

    return {
        "speciesId": row["pokemonId"],
        "speciesName": row["name"],
        "rating": rating,
        "score": row.get("score"),
        "matchups": matchups,
        "counters": counters,
        "moveset": moveset,
        "stats": stats,
    }


@st.cache_data(ttl=60 * 30, show_spinner=False)
def load_rankings(league_key: str, cup: str = DEFAULT_CUP, category: str = DEFAULT_CATEGORY):
    if league_key not in LEAGUES:
        raise ValueError(f"Liga desconocida: {league_key}")

    league_cp = LEAGUES[league_key]["cp"]
    rows = _run_query(league_cp, cup, category)

    if not rows:
        raise RuntimeError(
            f"La consulta no devolvió resultados para league={league_cp}, "
            f"cup='{cup}', category='{category}'. Revisa que existan datos "
            f"cargados con esos valores exactos."
        )

    return [_row_to_pokemon_dict(row) for row in rows]


def get_pokemon_by_id(rankings: list, species_id: str):
    for mon in rankings:
        if mon["speciesId"] == species_id:
            return mon
    return None


def search_pokemon(rankings: list, query: str, limit: int = 15):
    query = query.strip().lower()
    if not query:
        return []
    results = [
        mon for mon in rankings
        if query in mon["speciesName"].lower() or query in mon["speciesId"].lower()
    ]
    results.sort(key=lambda m: (not m["speciesName"].lower().startswith(query), -m.get("rating", 0)))
    return results[:limit]
