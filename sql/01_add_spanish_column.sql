<<<<<<< HEAD
-- Migración: agrega columna nameEs para nombres oficiales en español
-- Ejecutar en SQL Server en la base bd_pkm_pro

IF COL_LENGTH('Moves', 'nameEs') IS NULL
BEGIN
    ALTER TABLE Moves ADD nameEs NVARCHAR(100) NULL;
    PRINT 'Columna nameEs agregada correctamente.';
END
ELSE
BEGIN
    PRINT 'La columna nameEs ya existe.';
END
GO

-- Verificación rápida (descomenta si quieres revisar):
-- SELECT TOP 20 moveId, name, nameEs, type, power FROM Moves ORDER BY nameEs;
=======
-- 01_add_spanish_column.sql
-- Ejecutar UNA sola vez en tu base de datos bd_pkm_pro (SSMS -> Nueva consulta)
-- Agrega una columna para guardar el nombre del movimiento en español.

USE bd_pkm_pro;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Moves') AND name = 'nameEs'
)
BEGIN
    ALTER TABLE Moves ADD nameEs NVARCHAR(100) NULL;
    PRINT 'Columna nameEs agregada a Moves.';
END
ELSE
BEGIN
    PRINT 'La columna nameEs ya existía, no se hizo nada.';
END
GO
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
