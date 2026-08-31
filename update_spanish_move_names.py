"""
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

if __name__ == "__main__":
    main()
