-- NEXO UNDAC V9. Ejecutar UNA SOLA VEZ sobre un backup reciente.
-- No altera ni elimina registros previos. Requiere migracion_v8.sql ya aplicada.
USE seguimiento_egresados;
CREATE TABLE IF NOT EXISTS seguimiento_externo (
 id_seguimiento INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 id_egresado INT NOT NULL,
 id_oferta INT NOT NULL,
 estado ENUM('visitado','postulado','entrevista','contratacion_reportada','no_seleccionado','desistio') NOT NULL DEFAULT 'visitado',
 visitas INT NOT NULL DEFAULT 0,
 observacion VARCHAR(500) NULL,
 fecha_postulacion DATE NULL,
 fecha_contratacion DATE NULL,
 creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 UNIQUE KEY uq_seg_externo_persona_oferta (id_egresado, id_oferta),
 INDEX ix_seguimiento_externo_estado (estado),
 INDEX ix_seguimiento_externo_actualizado (actualizado_en),
 CONSTRAINT fk_v9_seg_egresado FOREIGN KEY (id_egresado) REFERENCES egresados (id_egresado) ON DELETE CASCADE,
 CONSTRAINT fk_v9_seg_oferta FOREIGN KEY (id_oferta) REFERENCES ofertas_laborales (id_oferta) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'seguimiento_egresados' AND TABLE_NAME = 'seguimiento_externo';
