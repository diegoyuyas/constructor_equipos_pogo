"""
export_to_sqlite.py
--------------------
Exporta las tablas relevantes de tu SQL Server local (bd_pkm_pro) a un
único archivo SQLite (pogo_data.sqlite), que es lo que subiremos a la nube.

Correr esto EN TU PC (donde sí tienes SQL Server), cada vez que quieras
actualizar los datos de la app en internet:

    python export_to_sqlite.py

Luego solo tienes que subir el archivo pogo_data.sqlite actualizado a
GitHub (junto con el resto del código) y Streamlit Cloud se actualiza solo.
"""

import os
import sqlite3
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
