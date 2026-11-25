-- =============================================================
-- MIGRACIÓN: Registro inteligente por DNI – NEXO UNDAC V9
-- Fecha: 2026-11-25
-- Descripción: Nuevas columnas en egresados + tabla historial_sync_academico
-- =============================================================

-- Columnas nuevas en egresados (con IF NOT EXISTS vía verificación previa)
SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'egresados'
      AND COLUMN_NAME  = 'ultima_sync_undac'
);
SET @sql1 = IF(@col_exists = 0,
    'ALTER TABLE egresados ADD COLUMN ultima_sync_undac DATETIME NULL AFTER actualizado_en',
    'SELECT "columna ultima_sync_undac ya existe"');
PREPARE stmt FROM @sql1; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col2 = (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'egresados' AND COLUMN_NAME = 'ultima_sync_sunedu');
SET @sql2 = IF(@col2 = 0,
    'ALTER TABLE egresados ADD COLUMN ultima_sync_sunedu DATETIME NULL AFTER ultima_sync_undac',
    'SELECT "columna ultima_sync_sunedu ya existe"');
PREPARE stmt FROM @sql2; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col3 = (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'egresados' AND COLUMN_NAME = 'ultima_sync_reniec');
SET @sql3 = IF(@col3 = 0,
    'ALTER TABLE egresados ADD COLUMN ultima_sync_reniec DATETIME NULL AFTER ultima_sync_sunedu',
    'SELECT "columna ultima_sync_reniec ya existe"');
PREPARE stmt FROM @sql3; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col4 = (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'egresados' AND COLUMN_NAME = 'consentimiento_consulta');
SET @sql4 = IF(@col4 = 0,
    'ALTER TABLE egresados ADD COLUMN consentimiento_consulta TINYINT(1) NOT NULL DEFAULT 0 AFTER ultima_sync_reniec',
    'SELECT "columna consentimiento_consulta ya existe"');
PREPARE stmt FROM @sql4; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Tabla historial de sincronización académica
CREATE TABLE IF NOT EXISTS historial_sync_academico (
    id_sync       INT AUTO_INCREMENT PRIMARY KEY,
    id_egresado   INT NOT NULL,
    fuente        VARCHAR(30) NOT NULL COMMENT 'reniec | sunedu | undac_api | manual',
    campo         VARCHAR(60) NOT NULL,
    valor_anterior TEXT,
    valor_nuevo   TEXT,
    operador      ENUM('sistema','egresado','admin') NOT NULL DEFAULT 'sistema',
    creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_egresado) REFERENCES egresados(id_egresado) ON DELETE CASCADE,
    INDEX idx_hsa_egresado (id_egresado),
    INDEX idx_hsa_fuente   (fuente),
    INDEX idx_hsa_fecha    (creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
