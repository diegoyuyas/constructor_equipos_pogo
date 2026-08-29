"""
<<<<<<< HEAD
data_loader.py - Conexión a SQL Server (desarrollo) y SQLite (producción/nube).

Este archivo es el puente entre la BD y toda la app.
Soporta:
- Desarrollo local: SQL Server Express LOCALHOST\SQLEXPRESS, bd_pkm_pro, Windows Auth
- Producción nube: archivo pogo_data.sqlite que subes a GitHub

Para un principiante:
- No necesitas entender todo. Solo usa las funciones load_pokemon_df(), load_moves_df(), load_rankings()
- Si ves error de conexión, revisa que el archivo pogo_data.sqlite esté en la misma carpeta que app.py
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd

# Intento de importar pyodbc solo si está disponible (en la nube no lo está)
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False

# Rutas donde buscar el SQLite
BASE_DIR = Path(__file__).parent
SQLITE_CANDIDATES = [
    BASE_DIR / "pogo_data.sqlite",
    BASE_DIR / "data" / "pogo_data.sqlite",
    Path.cwd() / "pogo_data.sqlite",
]

SQL_SERVER_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=LOCALHOST\\SQLEXPRESS;"
    "DATABASE=bd_pkm_pro;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

def find_sqlite_file() -> Optional[Path]:
    for p in SQLITE_CANDIDATES:
        if p.exists():
            return p
    return None

def is_sqlite_available() -> bool:
    return find_sqlite_file() is not None

def get_sqlite_connection():
    sqlite_path = find_sqlite_file()
    if not sqlite_path:
        raise FileNotFoundError(
            f"No se encontró pogo_data.sqlite. Busqué en: {', '.join(str(p) for p in SQLITE_CANDIDATES)}"
        )
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    return conn

def get_sql_server_connection():
    if not PYODBC_AVAILABLE:
        raise ImportError("pyodbc no está instalado. Instala con: pip install -r requirements-local.txt")
    try:
        conn = pyodbc.connect(SQL_SERVER_CONN_STR, timeout=5)
        return conn
    except Exception as e:
        raise ConnectionError(
            f"No se pudo conectar a SQL Server LOCALHOST\\SQLEXPRESS. "
            f"Verifica que SQL Server Express esté corriendo y que la BD bd_pkm_pro exista. Error: {e}"
        )

def get_connection():
    """
    Devuelve conexión activa.
    Prioridad:
    1. SQLite si existe archivo (producción/nube)
    2. SQL Server si pyodbc disponible (desarrollo local)
    """
    sqlite_file = find_sqlite_file()
    if sqlite_file:
        return get_sqlite_connection(), "sqlite"

    if PYODBC_AVAILABLE:
        try:
            return get_sql_server_connection(), "sqlserver"
        except Exception:
            pass

    # Si llegamos aquí, no hay BD
    raise RuntimeError(
        "No se encontró ninguna base de datos. "
        "En local necesitas SQL Server Express con bd_pkm_pro. "
        "En la nube necesitas pogo_data.sqlite en la carpeta del proyecto. "
        "Ejecuta export_to_sqlite.py para generarlo desde tu SQL Server."
    )

def _is_sqlite_conn(conn) -> bool:
    return isinstance(conn, sqlite3.Connection)

def _execute_df(conn, query: str, params=None) -> pd.DataFrame:
    """Ejecuta query y devuelve DataFrame, compatible con ambos motores."""
    if _is_sqlite_conn(conn):
        # SQLite usa ?
        if params:
            return pd.read_sql_query(query, conn, params=params)
        return pd.read_sql_query(query, conn)
    else:
        # pyodbc usa ? también, pero pandas lo maneja
        if params:
            return pd.read_sql(query, conn, params=params)
        return pd.read_sql(query, conn)

# ----------------------------------------------------------------------
# Funciones de carga principales
# ----------------------------------------------------------------------

def load_pokemon_df() -> pd.DataFrame:
    conn, db_type = get_connection()
    try:
        query = "SELECT pokemonId, dex, name, type1, type2, baseAtk, baseDef, baseSta, family, isShadow FROM Pokemon"
        df = _execute_df(conn, query)
        return df
    finally:
        conn.close()

def load_moves_df() -> pd.DataFrame:
    conn, db_type = get_connection()
    try:
        query = "SELECT moveId, name, nameEs, type, power, energy, energyGain, isFast, cooldown FROM Moves"
        df = _execute_df(conn, query)
        # Normalizar BIT a bool/int
        if "isFast" in df.columns:
            df["isFast"] = df["isFast"].astype(int)
        if "isShadow" in df.columns:
            df["isShadow"] = df["isShadow"].astype(int)
        return df
    finally:
        conn.close()

def load_rankings(league: int, cup: str = "all", category: str = "overall", limit: int = 500) -> pd.DataFrame:
    """
    league: 500, 1500, 2500, 10000 (Master)
    cup: 'all', 'timeless', etc.
    category: 'overall', 'leads', 'closers', etc.
    """
    conn, db_type = get_connection()
    try:
        if _is_sqlite_conn(conn):
            query = """
                SELECT id, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail
                FROM Rankings
                WHERE league = ? AND cup = ? AND category = ?
                ORDER BY rank ASC
                LIMIT ?
            """
            params = (league, cup, category, limit)
        else:
            query = f"""
                SELECT TOP {limit} id, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail
                FROM Rankings
                WHERE league = ? AND cup = ? AND category = ?
                ORDER BY rank ASC
            """
            params = (league, cup, category)
        df = _execute_df(conn, query, params)
        return df
    finally:
        conn.close()

def load_cups() -> pd.DataFrame:
    conn, db_type = get_connection()
    try:
        query = "SELECT cupName, description FROM Cups"
        df = _execute_df(conn, query)
        return df
    except Exception:
        # Tabla Cups puede no existir en versiones viejas
        return pd.DataFrame(columns=["cupName", "description"])
    finally:
        conn.close()

def get_pokemon_by_id(pokemon_id: str) -> Optional[Dict[str, Any]]:
    conn, db_type = get_connection()
    try:
        query = "SELECT * FROM Pokemon WHERE pokemonId = ?"
        df = _execute_df(conn, query, (pokemon_id,))
        if df.empty:
            return None
        return df.iloc[0].to_dict()
    finally:
        conn.close()

def get_move_by_id(move_id: str) -> Optional[Dict[str, Any]]:
    conn, db_type = get_connection()
    try:
        query = "SELECT * FROM Moves WHERE moveId = ?"
        df = _execute_df(conn, query, (move_id,))
        if df.empty:
            return None
        return df.iloc[0].to_dict()
    finally:
        conn.close()

def get_pokemon_fast_moves(pokemon_id: str) -> List[str]:
    conn, db_type = get_connection()
    try:
        query = "SELECT moveId FROM PokemonFastMoves WHERE pokemonId = ?"
        df = _execute_df(conn, query, (pokemon_id,))
        return df["moveId"].tolist() if not df.empty else []
    finally:
        conn.close()

def get_pokemon_charged_moves(pokemon_id: str) -> List[str]:
    conn, db_type = get_connection()
    try:
        query = "SELECT moveId FROM PokemonChargedMoves WHERE pokemonId = ?"
        df = _execute_df(conn, query, (pokemon_id,))
        return df["moveId"].tolist() if not df.empty else []
    finally:
        conn.close()

def get_moves_dict() -> Dict[str, Dict]:
    """Devuelve dict {moveId: row_dict} para acceso rápido."""
    df = load_moves_df()
    result = {}
    for _, row in df.iterrows():
        result[str(row["moveId"]).upper()] = row.to_dict()
    return result

def parse_score_detail(score_detail_str) -> Dict:
    """Parsea el JSON de scoreDetail de PvPoke."""
    if not score_detail_str:
        return {}
    if isinstance(score_detail_str, dict):
        return score_detail_str
    try:
        if isinstance(score_detail_str, bytes):
            score_detail_str = score_detail_str.decode("utf-8")
        return json.loads(score_detail_str)
    except Exception:
        return {}

def get_ranking_entry(pokemon_id: str, league: int, cup: str = "all", category: str = "overall") -> Optional[Dict]:
    conn, db_type = get_connection()
    try:
        query = """
            SELECT * FROM Rankings WHERE pokemonId = ? AND league = ? AND cup = ? AND category = ?
        """
        if not _is_sqlite_conn(conn):
            query = f"SELECT TOP 1 * FROM Rankings WHERE pokemonId = ? AND league = ? AND cup = ? AND category = ?"

        df = _execute_df(conn, query, (pokemon_id, league, cup, category))
        if df.empty:
            return None
        row = df.iloc[0].to_dict()
        row["parsedDetail"] = parse_score_detail(row.get("scoreDetail"))
        return row
    finally:
        conn.close()

# Helper para debugging
def test_connection():
    try:
        conn, db_type = get_connection()
        conn.close()
        return True, f"Conexión OK usando {db_type}. SQLite encontrado: {find_sqlite_file()}"
    except Exception as e:
        return False, str(e)
=======
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
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
