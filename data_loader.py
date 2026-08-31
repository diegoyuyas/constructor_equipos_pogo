"""
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
