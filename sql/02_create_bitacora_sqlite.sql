-- 02_create_bitacora_sqlite.sql - Version SQLite para pogo_data.sqlite
-- Ejecutar con: sqlite3 pogo_data.sqlite < sql/02_create_bitacora_sqlite.sql
-- O desde Python: crear_bitacora.py

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

-- Triggers SQLite para Moves
DROP TRIGGER IF EXISTS trg_Moves_Log_Update;
CREATE TRIGGER trg_Moves_Log_Update
AFTER UPDATE ON Moves
FOR EACH ROW
WHEN OLD.power <> NEW.power OR OLD.energy <> NEW.energy OR OLD.energyGain <> NEW.energyGain OR OLD.type <> NEW.type OR OLD.cooldown <> NEW.cooldown
BEGIN
    INSERT INTO BitacoraCambios (tabla, registroId, campo, valorAnterior, valorNuevo, accion, usuario)
    VALUES ('Moves', OLD.moveId, 'power/energy/type', 
            'power=' || OLD.power || ',energy=' || OLD.energy || ',gain=' || OLD.energyGain || ',type=' || OLD.type,
            'power=' || NEW.power || ',energy=' || NEW.energy || ',gain=' || NEW.energyGain || ',type=' || NEW.type,
            'UPDATE', 'sqlite_user');
END;

DROP TRIGGER IF EXISTS trg_Pokemon_Log_Update;
CREATE TRIGGER trg_Pokemon_Log_Update
AFTER UPDATE ON Pokemon
FOR EACH ROW
WHEN OLD.baseAtk <> NEW.baseAtk OR OLD.baseDef <> NEW.baseDef OR OLD.baseSta <> NEW.baseSta
BEGIN
    INSERT INTO BitacoraCambios (tabla, registroId, campo, valorAnterior, valorNuevo, accion, usuario)
    VALUES ('Pokemon', OLD.pokemonId, 'baseStats',
            'Atk=' || OLD.baseAtk || ',Def=' || OLD.baseDef || ',Sta=' || OLD.baseSta,
            'Atk=' || NEW.baseAtk || ',Def=' || NEW.baseDef || ',Sta=' || NEW.baseSta,
            'UPDATE', 'sqlite_user');
END;

-- Índices para bitácora
CREATE INDEX IF NOT EXISTS idx_bitacora_tabla_registro ON BitacoraCambios(tabla, registroId);
CREATE INDEX IF NOT EXISTS idx_bitacora_fecha ON BitacoraCambios(fecha);
CREATE INDEX IF NOT EXISTS idx_rankings_hist_fecha ON Rankings_Historico(fecha);
