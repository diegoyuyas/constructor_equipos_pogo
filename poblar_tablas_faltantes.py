"""
poblar_tablas_faltantes.py - Crea y puebla PokemonFastMoves y PokemonChargedMoves desde PvPoke

Usa los archivos oficiales de PvPoke:
- https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster/pokemon.json
- https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster/moves.json

Esto arregla el error "no such table: PokemonFastMoves" cuando tu bd_pkm_pro solo tiene
Pokemon, Moves y Rankings.

Uso:
    python poblar_tablas_faltantes.py

Requisitos:
    pip install requests pandas pyodbc
    SQL Server LOCALHOST\SQLEXPRESS corriendo
"""

import json
import requests
import pandas as pd
from pathlib import Path

from data_loader import get_connection, _is_sqlite_conn

POKEMON_URL = "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster/pokemon.json"
MOVES_URL = "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster/moves.json"

def fetch_json(url):
    print(f"Descargando {url} ...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()

def ensure_tables(conn):
    print("Creando tablas si no existen...")
    if _is_sqlite_conn(conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS PokemonFastMoves (
                pokemonId TEXT NOT NULL,
                moveId TEXT NOT NULL,
                PRIMARY KEY (pokemonId, moveId)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS PokemonChargedMoves (
                pokemonId TEXT NOT NULL,
                moveId TEXT NOT NULL,
                PRIMARY KEY (pokemonId, moveId)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Cups (
                cupName TEXT PRIMARY KEY,
                description TEXT
            )
        """)
        conn.commit()
    else:
        cur = conn.cursor()
        cur.execute("""
            IF OBJECT_ID('PokemonFastMoves', 'U') IS NULL
            CREATE TABLE PokemonFastMoves (
                pokemonId NVARCHAR(100) NOT NULL,
                moveId NVARCHAR(100) NOT NULL,
                CONSTRAINT PK_PokemonFastMoves PRIMARY KEY (pokemonId, moveId)
            );
        """)
        cur.execute("""
            IF OBJECT_ID('PokemonChargedMoves', 'U') IS NULL
            CREATE TABLE PokemonChargedMoves (
                pokemonId NVARCHAR(100) NOT NULL,
                moveId NVARCHAR(100) NOT NULL,
                CONSTRAINT PK_PokemonChargedMoves PRIMARY KEY (pokemonId, moveId)
            );
        """)
        cur.execute("""
            IF OBJECT_ID('Cups', 'U') IS NULL
            CREATE TABLE Cups (
                cupName NVARCHAR(100) PRIMARY KEY,
                description NVARCHAR(500) NULL
            );
        """)
        conn.commit()

def populate_from_pvpoke(conn):
    # Descargar datos
    try:
        pokemon_data = fetch_json(POKEMON_URL)
        print(f"Pokémon descargados: {len(pokemon_data)}")
    except Exception as e:
        print(f"ERROR descargando pokemon.json: {e}")
        print("Intenta descargar manual desde: https://github.com/pvpoke/pvpoke/tree/master/src/data/gamemaster")
        return False

    # Limpiar tablas N:M antes de poblar (opcional)
    print("Limpiando tablas N:M existentes...")
    if _is_sqlite_conn(conn):
        conn.execute("DELETE FROM PokemonFastMoves")
        conn.execute("DELETE FROM PokemonChargedMoves")
        conn.commit()
    else:
        cur = conn.cursor()
        cur.execute("DELETE FROM PokemonFastMoves")
        cur.execute("DELETE FROM PokemonChargedMoves")
        conn.commit()

    # Poblar
    fast_count = 0
    charged_count = 0
    missing_moves = set()

    # Para verificar qué moves existen en tabla Moves
    if _is_sqlite_conn(conn):
        existing_moves_df = pd.read_sql_query("SELECT moveId FROM Moves", conn)
    else:
        existing_moves_df = pd.read_sql("SELECT moveId FROM Moves", conn)
    existing_moves = set(existing_moves_df["moveId"].str.upper().tolist())

    print(f"Moves existentes en BD: {len(existing_moves)}")

    for poke in pokemon_data:
        # PvPoke formato: speciesId es pokemonId
        pid = poke.get("speciesId") or poke.get("pokemonId")
        if not pid:
            continue

        fast_moves = poke.get("fastMoves", [])
        charged_moves = poke.get("chargedMoves", [])

        for fm in fast_moves:
            fm_upper = fm.upper()
            if fm_upper not in existing_moves:
                missing_moves.add(fm_upper)
                continue
            try:
                if _is_sqlite_conn(conn):
                    conn.execute("INSERT OR IGNORE INTO PokemonFastMoves (pokemonId, moveId) VALUES (?, ?)", (pid, fm_upper))
                else:
                    cur = conn.cursor()
                    cur.execute("IF NOT EXISTS (SELECT 1 FROM PokemonFastMoves WHERE pokemonId=? AND moveId=?) INSERT INTO PokemonFastMoves (pokemonId, moveId) VALUES (?, ?)", (pid, fm_upper, pid, fm_upper))
                fast_count += 1
            except Exception as e:
                print(f"Error insert fast {pid} {fm}: {e}")

        for cm in charged_moves:
            cm_upper = cm.upper()
            if cm_upper not in existing_moves:
                missing_moves.add(cm_upper)
                continue
            try:
                if _is_sqlite_conn(conn):
                    conn.execute("INSERT OR IGNORE INTO PokemonChargedMoves (pokemonId, moveId) VALUES (?, ?)", (pid, cm_upper))
                else:
                    cur = conn.cursor()
                    cur.execute("IF NOT EXISTS (SELECT 1 FROM PokemonChargedMoves WHERE pokemonId=? AND moveId=?) INSERT INTO PokemonChargedMoves (pokemonId, moveId) VALUES (?, ?)", (pid, cm_upper, pid, cm_upper))
                charged_count += 1
            except Exception as e:
                print(f"Error insert charged {pid} {cm}: {e}")

    conn.commit()
    print(f"\n¡Poblado completo!")
    print(f"  PokemonFastMoves insertados: {fast_count}")
    print(f"  PokemonChargedMoves insertados: {charged_count}")
    if missing_moves:
        print(f"  Moves que estaban en pokemon.json pero NO en tu tabla Moves ({len(missing_moves)}):")
        print(f"  {sorted(list(missing_moves))[:20]} ...")
        print(f"  Considera actualizar tu tabla Moves desde moves.json de PvPoke")

    # Verificación final
    if _is_sqlite_conn(conn):
        fast_total = conn.execute("SELECT COUNT(*) FROM PokemonFastMoves").fetchone()[0]
        charged_total = conn.execute("SELECT COUNT(*) FROM PokemonChargedMoves").fetchone()[0]
    else:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM PokemonFastMoves")
        fast_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM PokemonChargedMoves")
        charged_total = cur.fetchone()[0]

    print(f"\nTotales finales en BD:")
    print(f"  PokemonFastMoves: {fast_total}")
    print(f"  PokemonChargedMoves: {charged_total}")

    return True

def main():
    print("=== Poblar tablas faltantes desde PvPoke ===")
    try:
        conn, db_type = get_connection()
        print(f"Conectado a {db_type}")
    except Exception as e:
        print(f"ERROR conexión: {e}")
        print("Si estás usando pogo_data.sqlite, borralo para forzar SQL Server, o crea las tablas en SQL Server primero")
        return

    try:
        ensure_tables(conn)
        success = populate_from_pvpoke(conn)
        if success:
            print("\n¡Listo! Ahora ejecuta:")
            print("  python export_to_sqlite.py")
            print("  python regenerar_rankings.py --league 1500 --top 200")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
