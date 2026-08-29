"""
<<<<<<< HEAD
export_to_sqlite.py - Exporta SQL Server -> pogo_data.sqlite para la nube.

Este script es para tu máquina local (Windows con SQL Server Express).
Hace:
1. Conecta a LOCALHOST\SQLEXPRESS, bd_pkm_pro
2. Lee todas las tablas
3. Crea pogo_data.sqlite con mismo esquema (compatible)
4. Lo deja listo para subir a GitHub junto con el código

Uso:
    python export_to_sqlite.py

Requisitos:
    pip install -r requirements-local.txt
    - pyodbc + driver ODBC 17
    - SQL Server Express corriendo
=======
export_to_sqlite.py
--------------------
Exporta las tablas relevantes de tu SQL Server local (bd_pkm_pro) a un
único archivo SQLite (pogo_data.sqlite), que es lo que subiremos a la nube.

Correr esto EN TU PC (donde sí tienes SQL Server), cada vez que quieras
actualizar los datos de la app en internet:

    python export_to_sqlite.py

Luego solo tienes que subir el archivo pogo_data.sqlite actualizado a
GitHub (junto con el resto del código) y Streamlit Cloud se actualiza solo.
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
"""

import os
import sqlite3
<<<<<<< HEAD
from pathlib import Path

try:
    import pyodbc
    import pandas as pd
except ImportError as e:
    print("Falta dependencia. Instala con: pip install -r requirements-local.txt")
    print(f"Error: {e}")
    exit(1)

BASE_DIR = Path(__file__).parent
SQLITE_PATH = BASE_DIR / "pogo_data.sqlite"

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=LOCALHOST\\SQLEXPRESS;"
    "DATABASE=bd_pkm_pro;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

TABLES = ["Pokemon", "Moves", "PokemonFastMoves", "PokemonChargedMoves", "Rankings", "Cups"]

def export_table(sql_conn, sqlite_conn, table_name):
    print(f"\n-> Exportando {table_name}...")

    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", sql_conn)
    except Exception as e:
        print(f"   Advertencia: no se pudo leer {table_name}: {e}")
        return

    if df.empty:
        print(f"   Tabla vacía, saltando.")
        return

    print(f"   Filas: {len(df)}")

    # Crear tabla en SQLite con tipos adaptados
    # Simplificación: usar pandas to_sql con if_exists replace
    # Pero primero limpiar SQLite
    sqlite_conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Ajustar tipos para SQLite (BIT -> INTEGER, NVARCHAR(MAX) -> TEXT)
    df.to_sql(table_name, sqlite_conn, if_exists="replace", index=False)

    # Crear índices útiles para performance en la app
    if table_name == "Rankings":
        sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_rankings_league_cup_cat ON Rankings(league, cup, category)")
        sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_rankings_pokemonId ON Rankings(pokemonId)")
        sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_rankings_rank ON Rankings(rank)")
    elif table_name == "Pokemon":
        sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_id ON Pokemon(pokemonId)")
    elif table_name == "Moves":
        sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_moves_id ON Moves(moveId)")

    sqlite_conn.commit()
    print(f"   OK en SQLite.")

def main():
    print("=== Exportador SQL Server -> SQLite ===")
    print(f"Origen: LOCALHOST\\SQLEXPRESS / bd_pkm_pro")
    print(f"Destino: {SQLITE_PATH}")

    if SQLITE_PATH.exists():
        print(f"\nArchivo existente será sobrescrito: {SQLITE_PATH}")
        os.remove(SQLITE_PATH)

    print("\nConectando a SQL Server...")
    try:
        sql_conn = pyodbc.connect(CONN_STR)
    except Exception as e:
        print(f"ERROR conectando a SQL Server: {e}")
        print("\nVerifica:")
        print(" - Que SQL Server Express esté corriendo")
        print(" - Que la instancia se llame LOCALHOST\\SQLEXPRESS")
        print(" - Que la base bd_pkm_pro exista")
        print(" - Que tengas ODBC Driver 17 instalado")
        return

    print("Conectado a SQL Server OK.")

    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))

    for table in TABLES:
        export_table(sql_conn, sqlite_conn, table)

    # Verificación final
    print("\n=== Verificación ===")
    cur = sqlite_conn.cursor()
    for table in TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"{table}: {count} filas")
        except Exception:
            print(f"{table}: no existe")

    sqlite_conn.close()
    sql_conn.close()

    size_mb = SQLITE_PATH.stat().st_size / (1024*1024)
    print(f"\n¡Listo! Archivo creado: {SQLITE_PATH} ({size_mb:.2f} MB)")
    print("\nPróximos pasos:")
    print("1. Verifica que el archivo no pese >100 MB (límite GitHub). Si pesa mucho, reduce Rankings a solo cup='all' y category='overall'")
    print("2. Agrégalo a tu repo: git add pogo_data.sqlite")
    print("3. Haz push a GitHub")
    print("4. En Streamlit Cloud, la app lo detectará automáticamente y usará SQLite en vez de SQL Server")

if __name__ == "__main__":
    main()
=======
import pyodbc

from data_loader import SERVER, DATABASE, DRIVER

SQLITE_FILE = os.path.join(os.path.dirname(__file__), "pogo_data.sqlite")

# Tablas que necesitamos copiar (en este orden, por las llaves foráneas)
TABLES_TO_COPY = [
    "Pokemon",
    "Moves",
    "PokemonFastMoves",
    "PokemonChargedMoves",
    "Cups",
    "Rankings",
]


def get_sqlserver_connection():
    conn_str = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str, timeout=10)


def export():
    if os.path.exists(SQLITE_FILE):
        os.remove(SQLITE_FILE)  # empezamos limpio cada vez, para no arrastrar datos viejos

    print(f"Conectando a SQL Server ({SERVER} / {DATABASE})...")
    src_conn = get_sqlserver_connection()
    src_cursor = src_conn.cursor()

    dst_conn = sqlite3.connect(SQLITE_FILE)
    dst_cursor = dst_conn.cursor()

    for table in TABLES_TO_COPY:
        print(f"Exportando tabla {table}...")
        src_cursor.execute(f"SELECT * FROM {table}")
        columns = [col[0] for col in src_cursor.description]
        rows = src_cursor.fetchall()

        col_defs = ", ".join(f'"{c}"' for c in columns)
        dst_cursor.execute(f'CREATE TABLE "{table}" ({col_defs})')

        placeholders = ", ".join("?" for _ in columns)
        dst_cursor.executemany(
            f'INSERT INTO "{table}" VALUES ({placeholders})',
            [tuple(row) for row in rows],
        )
        print(f"  -> {len(rows)} filas copiadas.")

    # Índice equivalente al que tienes en SQL Server, para que las consultas
    # sigan siendo rápidas también en SQLite.
    dst_cursor.execute(
        'CREATE INDEX IX_Rankings_League_Cup ON Rankings(league, cup, category, rank)'
    )

    dst_conn.commit()
    dst_conn.close()
    src_conn.close()

    size_kb = os.path.getsize(SQLITE_FILE) / 1024
    print(f"\n✅ Listo: {SQLITE_FILE} ({size_kb:.0f} KB)")
    print("Ahora sube este archivo junto con el resto del proyecto a GitHub.")


if __name__ == "__main__":
    export()
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
