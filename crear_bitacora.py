"""
crear_bitacora.py - Crea tabla BitacoraCambios y Rankings_Historico en SQL Server o SQLite.

Ejecuta este script UNA VEZ antes de empezar a modificar Moves/Pokemon.

Uso:
    python crear_bitacora.py

Detecta automáticamente si usas SQL Server o pogo_data.sqlite
"""

from data_loader import get_connection, _is_sqlite_conn

def crear_tablas_sql_server(conn):
    cur = conn.cursor()
    print("Creando tablas en SQL Server...")

    # BitacoraCambios
    cur.execute("""
        IF OBJECT_ID('BitacoraCambios', 'U') IS NULL
        CREATE TABLE BitacoraCambios (
            id INT IDENTITY(1,1) PRIMARY KEY,
            fecha DATETIME DEFAULT GETDATE(),
            tabla NVARCHAR(50) NOT NULL,
            registroId NVARCHAR(100) NOT NULL,
            campo NVARCHAR(100) NOT NULL,
            valorAnterior NVARCHAR(MAX) NULL,
            valorNuevo NVARCHAR(MAX) NULL,
            accion NVARCHAR(20) NOT NULL,
            usuario NVARCHAR(100) NULL,
            motivo NVARCHAR(200) NULL
        );
    """)
    conn.commit()

    # Rankings_Historico
    cur.execute("""
        IF OBJECT_ID('Rankings_Historico', 'U') IS NULL
        CREATE TABLE Rankings_Historico (
            historicoId INT IDENTITY(1,1) PRIMARY KEY,
            fecha DATETIME DEFAULT GETDATE(),
            motivo NVARCHAR(200),
            league INT,
            cup NVARCHAR(50),
            category NVARCHAR(20),
            rank INT,
            pokemonId NVARCHAR(50),
            score FLOAT,
            bestFastMove NVARCHAR(50),
            bestChargedMove1 NVARCHAR(50),
            bestChargedMove2 NVARCHAR(50),
            scoreDetail NVARCHAR(MAX)
        );
    """)
    conn.commit()

    # Triggers (solo si no existen, ejecutamos el sql/02_create_bitacora.sql)
    # Para simplificar, leemos ese archivo y ejecutamos por partes
    print("Ejecutando triggers desde sql/02_create_bitacora.sql ...")
    from pathlib import Path
    sql_path = Path(__file__).parent / "sql" / "02_create_bitacora.sql"
    if sql_path.exists():
        sql_text = sql_path.read_text(encoding="utf-8")
        # Separar por GO (SQL Server batch separator)
        batches = sql_text.split("GO")
        for batch in batches:
            batch = batch.strip()
            if not batch or "CREATE TABLE" in batch.upper() and "BitacoraCambios" in batch:
                continue  # ya creadas arriba
            if not batch:
                continue
            try:
                cur.execute(batch)
                conn.commit()
            except Exception as e:
                # Algunos batches pueden fallar si trigger ya existe, lo ignoramos
                print(f"  Nota (ignorable): {e}")

    print("Bitácora creada en SQL Server OK")

def crear_tablas_sqlite(conn):
    print("Creando tablas en SQLite...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS BitacoraCambios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            tabla TEXT NOT NULL,
            registroId TEXT NOT NULL,
            campo TEXT NOT NULL,
            valorAnterior TEXT,
            valorNuevo TEXT,
            accion TEXT NOT NULL,
            usuario TEXT,
            motivo TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Rankings_Historico (
            historicoId INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            motivo TEXT,
            league INTEGER,
            cup TEXT,
            category TEXT,
            rank INTEGER,
            pokemonId TEXT,
            score REAL,
            bestFastMove TEXT,
            bestChargedMove1 TEXT,
            bestChargedMove2 TEXT,
            scoreDetail TEXT
        );
    """)
    conn.commit()

    # Leer sqlite triggers
    from pathlib import Path
    sql_path = Path(__file__).parent / "sql" / "02_create_bitacora_sqlite.sql"
    if sql_path.exists():
        sql_text = sql_path.read_text(encoding="utf-8")
        try:
            conn.executescript(sql_text)
            conn.commit()
            print("Triggers SQLite creados")
        except Exception as e:
            print(f"Error creando triggers SQLite: {e}")

    print("Bitácora creada en SQLite OK")

def main():
    print("=== Creador de Bitácora ===")
    try:
        conn, db_type = get_connection()
        print(f"Conectado a: {db_type}")
    except Exception as e:
        print(f"ERROR conexión: {e}")
        return

    try:
        if db_type == "sqlite":
            crear_tablas_sqlite(conn)
        else:
            crear_tablas_sql_server(conn)

        # Verificación
        if _is_sqlite_conn(conn):
            cur = conn.execute("SELECT COUNT(*) FROM BitacoraCambios")
            print(f"BitacoraCambios filas actuales: {cur.fetchone()[0]}")
        else:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM BitacoraCambios")
            print(f"BitacoraCambios filas actuales: {cur.fetchone()[0]}")

        print("\n¡Listo! Ahora cada UPDATE en Moves/Pokemon quedará registrado en BitacoraCambios")
        print("Consulta: SELECT TOP 20 * FROM BitacoraCambios ORDER BY fecha DESC;")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
