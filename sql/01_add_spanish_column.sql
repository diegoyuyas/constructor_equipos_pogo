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
