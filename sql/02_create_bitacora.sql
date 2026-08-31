-- ======================================================
-- 02_create_bitacora.sql - Tabla de bitácora / historial
-- Para SQL Server (bd_pkm_pro)
-- Guarda como estaba el registro antes de modificarlo
-- ======================================================

-- 1. Tabla principal de bitácora genérica
IF OBJECT_ID('BitacoraCambios', 'U') IS NULL
BEGIN
    CREATE TABLE BitacoraCambios (
        id INT IDENTITY(1,1) PRIMARY KEY,
        fecha DATETIME DEFAULT GETDATE(),
        tabla NVARCHAR(50) NOT NULL,          -- Ej: 'Moves', 'Pokemon', 'Rankings'
        registroId NVARCHAR(100) NOT NULL,    -- Ej: moveId, pokemonId, id de ranking
        campo NVARCHAR(100) NOT NULL,         -- Ej: 'power', 'energy', 'baseAtk'
        valorAnterior NVARCHAR(MAX) NULL,
        valorNuevo NVARCHAR(MAX) NULL,
        accion NVARCHAR(20) NOT NULL,         -- UPDATE, DELETE, INSERT
        usuario NVARCHAR(100) NULL,           -- SUSER_SNAME()
        motivo NVARCHAR(200) NULL
    );
    PRINT 'Tabla BitacoraCambios creada.';
END
ELSE
    PRINT 'Tabla BitacoraCambios ya existe.';
GO

-- 2. Tabla para guardar Rankings completos antes de regenerar (snapshot)
IF OBJECT_ID('Rankings_Historico', 'U') IS NULL
BEGIN
    CREATE TABLE Rankings_Historico (
        historicoId INT IDENTITY(1,1) PRIMARY KEY,
        fecha DATETIME DEFAULT GETDATE(),
        motivo NVARCHAR(200),
        -- Copia exacta de Rankings + fecha
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
    PRINT 'Tabla Rankings_Historico creada.';
END
GO

-- ======================================================
-- 3. TRIGGERS para Moves - Guarda automáticamente el antes y después
-- ======================================================
IF OBJECT_ID('trg_Moves_Log', 'TR') IS NOT NULL DROP TRIGGER trg_Moves_Log;
GO
CREATE TRIGGER trg_Moves_Log
ON Moves
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    -- Solo logueamos si realmente cambió algún campo importante
    INSERT INTO BitacoraCambios (tabla, registroId, campo, valorAnterior, valorNuevo, accion, usuario)
    SELECT 
        'Moves',
        ISNULL(d.moveId, i.moveId),
        'power',
        CAST(d.power AS NVARCHAR(MAX)),
        CAST(i.power AS NVARCHAR(MAX)),
        CASE WHEN i.moveId IS NULL THEN 'DELETE' ELSE 'UPDATE' END,
        SUSER_SNAME()
    FROM deleted d
    LEFT JOIN inserted i ON d.moveId = i.moveId
    WHERE ISNULL(d.power, -999) <> ISNULL(i.power, -999)

    UNION ALL
    SELECT 'Moves', ISNULL(d.moveId, i.moveId), 'energy', CAST(d.energy AS NVARCHAR), CAST(i.energy AS NVARCHAR), CASE WHEN i.moveId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.moveId = i.moveId WHERE ISNULL(d.energy, -999) <> ISNULL(i.energy, -999)

    UNION ALL
    SELECT 'Moves', ISNULL(d.moveId, i.moveId), 'energyGain', CAST(d.energyGain AS NVARCHAR), CAST(i.energyGain AS NVARCHAR), CASE WHEN i.moveId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.moveId = i.moveId WHERE ISNULL(d.energyGain, -999) <> ISNULL(i.energyGain, -999)

    UNION ALL
    SELECT 'Moves', ISNULL(d.moveId, i.moveId), 'type', CAST(d.type AS NVARCHAR), CAST(i.type AS NVARCHAR), CASE WHEN i.moveId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.moveId = i.moveId WHERE ISNULL(d.type,'') <> ISNULL(i.type,'')

    UNION ALL
    SELECT 'Moves', ISNULL(d.moveId, i.moveId), 'cooldown', CAST(d.cooldown AS NVARCHAR), CAST(i.cooldown AS NVARCHAR), CASE WHEN i.moveId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.moveId = i.moveId WHERE ISNULL(d.cooldown, -999) <> ISNULL(i.cooldown, -999)

    UNION ALL
    SELECT 'Moves', ISNULL(d.moveId, i.moveId), 'nameEs', CAST(d.nameEs AS NVARCHAR), CAST(i.nameEs AS NVARCHAR), CASE WHEN i.moveId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.moveId = i.moveId WHERE ISNULL(d.nameEs,'') <> ISNULL(i.nameEs,'');
END;
GO

-- ======================================================
-- 4. TRIGGER para Pokemon (base stats)
-- ======================================================
IF OBJECT_ID('trg_Pokemon_Log', 'TR') IS NOT NULL DROP TRIGGER trg_Pokemon_Log;
GO
CREATE TRIGGER trg_Pokemon_Log
ON Pokemon
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO BitacoraCambios (tabla, registroId, campo, valorAnterior, valorNuevo, accion, usuario)
    SELECT 'Pokemon', d.pokemonId, 'baseAtk', CAST(d.baseAtk AS NVARCHAR), CAST(i.baseAtk AS NVARCHAR), CASE WHEN i.pokemonId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.pokemonId = i.pokemonId WHERE ISNULL(d.baseAtk,-1) <> ISNULL(i.baseAtk,-1)
    UNION ALL
    SELECT 'Pokemon', d.pokemonId, 'baseDef', CAST(d.baseDef AS NVARCHAR), CAST(i.baseDef AS NVARCHAR), CASE WHEN i.pokemonId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.pokemonId = i.pokemonId WHERE ISNULL(d.baseDef,-1) <> ISNULL(i.baseDef,-1)
    UNION ALL
    SELECT 'Pokemon', d.pokemonId, 'baseSta', CAST(d.baseSta AS NVARCHAR), CAST(i.baseSta AS NVARCHAR), CASE WHEN i.pokemonId IS NULL THEN 'DELETE' ELSE 'UPDATE' END, SUSER_SNAME()
    FROM deleted d LEFT JOIN inserted i ON d.pokemonId = i.pokemonId WHERE ISNULL(d.baseSta,-1) <> ISNULL(i.baseSta,-1);
END;
GO

-- ======================================================
-- 5. TRIGGER para relaciones N:M de movimientos
-- ======================================================
IF OBJECT_ID('trg_PokemonFastMoves_Log', 'TR') IS NOT NULL DROP TRIGGER trg_PokemonFastMoves_Log;
GO
CREATE TRIGGER trg_PokemonFastMoves_Log
ON PokemonFastMoves
AFTER INSERT, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO BitacoraCambios (tabla, registroId, campo, valorAnterior, valorNuevo, accion, usuario)
    SELECT 'PokemonFastMoves', d.pokemonId, 'fastMove', d.moveId, NULL, 'DELETE', SUSER_SNAME() FROM deleted d
    UNION ALL
    SELECT 'PokemonFastMoves', i.pokemonId, 'fastMove', NULL, i.moveId, 'INSERT', SUSER_SNAME() FROM inserted i;
END;
GO

IF OBJECT_ID('trg_PokemonChargedMoves_Log', 'TR') IS NOT NULL DROP TRIGGER trg_PokemonChargedMoves_Log;
GO
CREATE TRIGGER trg_PokemonChargedMoves_Log
ON PokemonChargedMoves
AFTER INSERT, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO BitacoraCambios (tabla, registroId, campo, valorAnterior, valorNuevo, accion, usuario)
    SELECT 'PokemonChargedMoves', d.pokemonId, 'chargedMove', d.moveId, NULL, 'DELETE', SUSER_SNAME() FROM deleted d
    UNION ALL
    SELECT 'PokemonChargedMoves', i.pokemonId, 'chargedMove', NULL, i.moveId, 'INSERT', SUSER_SNAME() FROM inserted i;
END;
GO

-- Verificación
-- SELECT TOP 20 * FROM BitacoraCambios ORDER BY fecha DESC;
-- SELECT * FROM Rankings_Historico ORDER BY fecha DESC;
