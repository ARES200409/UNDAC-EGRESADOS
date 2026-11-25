-- NEXO UNDAC V10.6. Ejecutar en MySQL Workbench conectado con usuario con ALTER.
-- REQUIERE RESPALDO previo; ALTER TABLE genera commit implícito en MySQL.
-- Afecta únicamente la posibilidad de dejar anio_inicio en NULL.
USE seguimiento_egresados;
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='curriculas' AND COLUMN_NAME='anio_inicio';

ALTER TABLE curriculas MODIFY COLUMN anio_inicio YEAR NULL;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='curriculas' AND COLUMN_NAME='anio_inicio';
-- Resultado esperado: IS_NULLABLE = YES.
