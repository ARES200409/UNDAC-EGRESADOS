-- NEXO UNDAC V8 - migracion incremental, NO borra ni altera tablas anteriores.
-- Hacer copia de seguridad antes de ejecutar.
-- Requiere usuario MySQL con permiso CREATE sobre seguimiento_egresados.
-- No contiene datos personales ni registros ficticios.
USE seguimiento_egresados;

CREATE TABLE IF NOT EXISTS ofertas_guardadas (
  id_guardado INT NOT NULL AUTO_INCREMENT,
  id_egresado INT NOT NULL,
  id_oferta INT NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_guardado),
  UNIQUE KEY uq_guardado_egresado_oferta (id_egresado, id_oferta),
  KEY ix_guardado_oferta (id_oferta),
  CONSTRAINT fk_guardado_egresado FOREIGN KEY (id_egresado)
      REFERENCES egresados (id_egresado) ON DELETE CASCADE,
  CONSTRAINT fk_guardado_oferta FOREIGN KEY (id_oferta)
      REFERENCES ofertas_laborales (id_oferta) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS postulaciones (
  id_postulacion INT NOT NULL AUTO_INCREMENT,
  id_egresado INT NOT NULL,
  id_oferta INT NOT NULL,
  mensaje TEXT NULL,
  estado ENUM('enviada','en_revision','seleccionado','no_seleccionado') NOT NULL DEFAULT 'enviada',
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_postulacion),
  UNIQUE KEY uq_postulacion_egresado_oferta (id_egresado,id_oferta),
  KEY ix_postulacion_oferta (id_oferta),
  CONSTRAINT fk_postulacion_egresado FOREIGN KEY (id_egresado)
      REFERENCES egresados (id_egresado) ON DELETE CASCADE,
  CONSTRAINT fk_postulacion_oferta FOREIGN KEY (id_oferta)
      REFERENCES ofertas_laborales (id_oferta) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT TABLE_NAME FROM information_schema.tables
WHERE TABLE_SCHEMA='seguimiento_egresados'
  AND TABLE_NAME IN ('ofertas_guardadas','postulaciones');
