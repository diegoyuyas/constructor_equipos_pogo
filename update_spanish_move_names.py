"""
<<<<<<< HEAD
update_spanish_move_names.py - Llena Moves.nameEs consultando PokeAPI.

Hace:
- Lee todos los Moves de la BD (SQL Server o SQLite)
- Para cada moveId, consulta https://pokeapi.co/api/v2/move/{slug}/
- Extrae el nombre en idioma "es"
- Guarda en Moves.nameEs
- Usa caché local spanish_move_cache.json para no re-consultar

Manejo de sufijos: WEATHER_BALL_FIRE -> consulta WEATHER_BALL y luego formatea "Bola Meteoro (Fuego)"

Uso:
    python update_spanish_move_names.py

Requisitos:
    pip install requests pandas pyodbc (si usas SQL Server)
"""

import json
import time
import re
from pathlib import Path

import requests
import pandas as pd

from data_loader import get_connection, find_sqlite_file, _is_sqlite_conn
from moves import parse_move_id_with_suffix, TYPE_SPANISH, FALLBACK_SPANISH

BASE_DIR = Path(__file__).parent
CACHE_PATH = BASE_DIR / "spanish_move_cache.json"

# Cargar caché existente
def load_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def move_id_to_pokeapi_slug(move_id: str) -> str:
    """
    Convierte moveId de GO a slug de PokeAPI.
    Ej: THUNDERBOLT -> thunderbolt, WEATHER_BALL -> weather-ball, BUBBLE_BEAM -> bubble-beam
    """
    base_id, suffix = parse_move_id_with_suffix(move_id.upper())
    # Usar base para consultar
    slug = base_id.lower().replace("_", "-")
    return slug

def fetch_spanish_name_from_pokeapi(move_id: str, cache: dict) -> str:
    """
    Consulta PokeAPI y devuelve nombre en español, o None si falla.
    Usa caché.
    """
    base_id, suffix = parse_move_id_with_suffix(move_id.upper())
    slug = move_id_to_pokeapi_slug(move_id)

    # Chequear caché por slug
    if slug in cache:
        base_name_es = cache[slug]
    else:
        # Consultar API
        url = f"https://pokeapi.co/api/v2/move/{slug}/"
        print(f"  Consultando PokeAPI: {slug} ...", end=" ")
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Buscar nombre en español
                names = data.get("names", [])
                es_name = None
                for entry in names:
                    if entry.get("language", {}).get("name") == "es":
                        es_name = entry.get("name")
                        break
                if es_name:
                    print(f"-> {es_name}")
                    cache[slug] = es_name
                    base_name_es = es_name
                    time.sleep(0.2)  # respeto a la API
                else:
                    print("-> sin traducción es")
                    cache[slug] = None
                    base_name_es = None
            elif resp.status_code == 404:
                print("-> no existe en PokeAPI")
                cache[slug] = None
                base_name_es = None
            else:
                print(f"-> error {resp.status_code}")
                base_name_es = None
        except Exception as e:
            print(f"-> excepción {e}")
            base_name_es = None

    if not base_name_es:
        # Intentar fallback diccionario
        if move_id.upper() in FALLBACK_SPANISH:
            base_name_es = FALLBACK_SPANISH[move_id.upper()]
        elif base_id in FALLBACK_SPANISH:
            base_name_es = FALLBACK_SPANISH[base_id]

    if not base_name_es:
        return None

    # Si tiene sufijo de tipo, formatear
    if suffix:
        tipo_es = TYPE_SPANISH.get(suffix, suffix.title())
        return f"{base_name_es} ({tipo_es})"

    return base_name_es

def main():
    print("=== Actualizador de nombres en español (PokeAPI) ===")

    cache = load_cache()
    print(f"Caché cargada: {len(cache)} entradas")

    # Conectar BD
    try:
        conn, db_type = get_connection()
        print(f"Conectado a BD tipo: {db_type}")
    except Exception as e:
        print(f"ERROR conectando a BD: {e}")
        return

    try:
        # Leer Moves
        if _is_sqlite_conn(conn):
            df = pd.read_sql_query("SELECT moveId, name, nameEs FROM Moves", conn)
        else:
            df = pd.read_sql("SELECT moveId, name, nameEs FROM Moves", conn)

        print(f"Total movimientos en BD: {len(df)}")
        print(f"Con nameEs ya lleno: {df['nameEs'].notna().sum()}")

        updated = 0
        for _, row in df.iterrows():
            move_id = row["moveId"]
            current_es = row.get("nameEs")

            # Si ya tiene español y no forzamos, saltar
            if current_es and str(current_es).strip():
                continue

            spanish_name = fetch_spanish_name_from_pokeapi(move_id, cache)

            if spanish_name:
                print(f"  {move_id}: {spanish_name}")
                # Actualizar BD
                try:
                    if _is_sqlite_conn(conn):
                        conn.execute("UPDATE Moves SET nameEs = ? WHERE moveId = ?", (spanish_name, move_id))
                    else:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE Moves SET nameEs = ? WHERE moveId = ?", (spanish_name, move_id))
                        cursor.commit()
                    conn.commit()
                    updated += 1
                except Exception as e:
                    print(f"    Error actualizando BD para {move_id}: {e}")
            else:
                print(f"  {move_id}: sin traducción encontrada, se usará fallback en la app")

        save_cache(cache)
        print(f"\n¡Hecho! Actualizados {updated} movimientos.")
        print(f"Caché guardada en {CACHE_PATH} con {len(cache)} entradas")

    finally:
        conn.close()
=======
update_spanish_move_names.py
-----------------------------
Llena la columna Moves.nameEs con el nombre OFICIAL en español de cada
movimiento (el mismo que usa el juego, ej. SNARL -> "Alarido"), NO una
traducción literal del inglés.

Fuente: PokeAPI (https://pokeapi.co), que expone la base de datos abierta
"veekun/pokedex" con los nombres localizados oficiales de Nintendo/Game
Freak para cada idioma. Pokémon GO reutiliza estos mismos nombres oficiales
para sus movimientos, así que es una fuente confiable y gratuita (no
requiere API key).

Requisito previo: haber corrido sql/01_add_spanish_column.sql una vez.

Uso (en tu PC, con SQL Server e internet activos):
    pip install requests pyodbc
    python update_spanish_move_names.py

Es seguro correrlo varias veces: usa un archivo de caché local
(spanish_move_cache.json) para no volver a consultar PokeAPI por
movimientos que ya resolvió, así que las siguientes ejecuciones son
instantáneas.
"""

import json
import os
import time

import pyodbc
import requests

from data_loader import SERVER, DATABASE, DRIVER
from moves import format_move, _TYPE_SUFFIX_ES  # respaldo si PokeAPI falla

CACHE_FILE = os.path.join(os.path.dirname(__file__), "spanish_move_cache.json")
POKEAPI_MOVE_URL = "https://pokeapi.co/api/v2/move/{slug}"

# Overrides manuales para casos donde el moveId de Pokémon GO no coincide
# 1:1 con el identificador que usa PokeAPI. Agrega aquí cualquier moveId
# problemático que encuentres.
SLUG_OVERRIDES = {
    "VICE_GRIP": "vise-grip",
    "FUTURESIGHT": "future-sight",
}


def get_connection():
    conn_str = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str, timeout=10)


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def move_id_to_slug(move_id: str):
    """
    Convierte un moveId de Pokémon GO (ej. WEATHER_BALL_FIRE) al identificador
    que usa PokeAPI (ej. "weather-ball"). Devuelve (slug, sufijo_tipo) donde
    sufijo_tipo es el tipo en español si el movimiento tenía uno (para
    volver a agregarlo al nombre final, ej. "Bola Meteoro (Fuego)").
    """
    if move_id in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[move_id], None

    parts = move_id.split("_")
    type_suffix_es = None

    # Movimientos como WEATHER_BALL_FIRE, HIDDEN_POWER_ICE, TECHNO_BLAST_WATER:
    # el nombre base en PokeAPI no incluye el tipo, así que lo separamos.
    if len(parts) > 1 and parts[-1] in _TYPE_SUFFIX_ES:
        type_suffix_es = _TYPE_SUFFIX_ES[parts[-1]]
        parts = parts[:-1]

    slug = "-".join(p.lower() for p in parts)
    return slug, type_suffix_es


def fetch_spanish_name(move_id: str, cache: dict):
    """
    Devuelve el nombre oficial en español de un movimiento, usando (en este
    orden): caché local -> PokeAPI -> diccionario de respaldo de moves.py.
    """
    if move_id in cache:
        return cache[move_id], "cache"

    slug, type_suffix_es = move_id_to_slug(move_id)

    try:
        resp = requests.get(POKEAPI_MOVE_URL.format(slug=slug), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            es_name = next(
                (n["name"] for n in data.get("names", []) if n["language"]["name"] == "es"),
                None,
            )
            if es_name:
                if type_suffix_es:
                    es_name = f"{es_name} ({type_suffix_es})"
                cache[move_id] = es_name
                return es_name, "pokeapi"
    except requests.RequestException:
        pass  # seguimos al respaldo local

    # Respaldo: diccionario propio de moves.py (traducción aproximada)
    fallback = format_move(move_id)
    cache[move_id] = fallback
    return fallback, "fallback"


def main():
    print(f"Conectando a SQL Server ({SERVER} / {DATABASE})...")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT moveId FROM Moves")
    move_ids = [row.moveId for row in cursor.fetchall()]
    print(f"{len(move_ids)} movimientos encontrados.\n")

    cache = load_cache()
    stats = {"cache": 0, "pokeapi": 0, "fallback": 0}

    for i, move_id in enumerate(move_ids, 1):
        spanish_name, origin = fetch_spanish_name(move_id, cache)
        stats[origin] += 1

        cursor.execute("UPDATE Moves SET nameEs = ? WHERE moveId = ?", spanish_name, move_id)

        tag = {"cache": "💾", "pokeapi": "🌐", "fallback": "⚠️"}[origin]
        print(f"  {tag} {move_id:30s} -> {spanish_name}")

        # Solo pausamos entre llamadas REALES a la API, no entre hits de caché
        if origin == "pokeapi":
            time.sleep(0.15)

        # Guardamos la caché cada 20 movimientos, por si el script se corta a la mitad
        if i % 20 == 0:
            save_cache(cache)

    conn.commit()
    save_cache(cache)
    conn.close()

    print(f"\n✅ {len(move_ids)} filas actualizadas en Moves.nameEs.")
    print(f"   🌐 {stats['pokeapi']} obtenidos de PokeAPI (nombre oficial del juego)")
    print(f"   💾 {stats['cache']} reutilizados de la caché local")
    print(f"   ⚠️  {stats['fallback']} sin match en PokeAPI (se usó el respaldo de moves.py)")
    if stats["fallback"]:
        print(
            "\n   Revisa esos casos: puede que el moveId no exista en PokeAPI con ese "
            "nombre exacto. Agrega un override en SLUG_OVERRIDES si hace falta y "
            "vuelve a correr el script (borra su entrada en spanish_move_cache.json "
            "primero para forzar que se re-consulte)."
        )

>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1

if __name__ == "__main__":
    main()
