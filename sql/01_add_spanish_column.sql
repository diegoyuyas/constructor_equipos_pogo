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
