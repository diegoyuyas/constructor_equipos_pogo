-- 03_create_missing_tables.sql
-- Crea PokemonFastMoves, PokemonChargedMoves y Cups si no existen
-- Ejecutar en SQL Server bd_pkm_pro

IF OBJECT_ID('PokemonFastMoves', 'U') IS NULL
BEGIN
    CREATE TABLE PokemonFastMoves (
        pokemonId NVARCHAR(100) NOT NULL,
        moveId NVARCHAR(100) NOT NULL,
        CONSTRAINT PK_PokemonFastMoves PRIMARY KEY (pokemonId, moveId)
    );
    PRINT 'Tabla PokemonFastMoves creada';
END
ELSE PRINT 'PokemonFastMoves ya existe';

IF OBJECT_ID('PokemonChargedMoves', 'U') IS NULL
BEGIN
    CREATE TABLE PokemonChargedMoves (
        pokemonId NVARCHAR(100) NOT NULL,
        moveId NVARCHAR(100) NOT NULL,
        CONSTRAINT PK_PokemonChargedMoves PRIMARY KEY (pokemonId, moveId)
    );
    PRINT 'Tabla PokemonChargedMoves creada';
END
ELSE PRINT 'PokemonChargedMoves ya existe';

IF OBJECT_ID('Cups', 'U') IS NULL
BEGIN
    CREATE TABLE Cups (
        cupName NVARCHAR(100) PRIMARY KEY,
        description NVARCHAR(500) NULL
    );
    INSERT INTO Cups (cupName, description) VALUES 
    ('all', 'Meta abierto - todas las copas'),
    ('timeless', 'Timeless Cup'),
    ('fantasy', 'Fantasy Cup'),
    ('catch', 'Catch Cup');
    PRINT 'Tabla Cups creada con datos base';
END
ELSE PRINT 'Cups ya existe';

-- Verificacion
SELECT 'PokemonFastMoves' as tabla, COUNT(*) as filas FROM PokemonFastMoves
UNION ALL
SELECT 'PokemonChargedMoves', COUNT(*) FROM PokemonChargedMoves
UNION ALL
SELECT 'Cups', COUNT(*) FROM Cups;
