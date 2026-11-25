-- ============================================================================
-- NEXO UNDAC - ROLLBACK DE MIGRACION FASE 3
-- Elimina únicamente las tablas y columnas introducidas en Fase 3.
-- NO toca datos ni tablas previas V8/V9.
-- ============================================================================

USE seguimiento_egresados;

DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS notificaciones;
DROP TABLE IF EXISTS inscripciones_capacitacion;
DROP TABLE IF EXISTS capacitaciones;
DROP TABLE IF EXISTS campanas_seguimiento;
DROP TABLE IF EXISTS autorizaciones_documentales;
DROP TABLE IF EXISTS historial_validacion_documental;
DROP TABLE IF EXISTS documentos_egresado;

ALTER TABLE usuarios DROP FOREIGN KEY fk_usuario_empresa;
ALTER TABLE usuarios
    DROP COLUMN id_empresa,
    DROP COLUMN intentos_fallidos,
    DROP COLUMN bloqueado_hasta,
    DROP COLUMN actualizado_en;

ALTER TABLE egresados
    DROP COLUMN situacion_laboral,
    DROP COLUMN perfil_publico,
    DROP COLUMN actualizado_en;

ALTER TABLE empleos
    DROP COLUMN relacion_carrera,
    DROP COLUMN modalidad,
    DROP COLUMN rango_remuneracion,
    DROP COLUMN es_independiente;

ALTER TABLE empresas
    DROP COLUMN motivo_rechazo,
    DROP COLUMN validado_por,
    DROP COLUMN fecha_validacion;

ALTER TABLE ofertas_laborales
    DROP COLUMN carrera_requerida,
    DROP COLUMN experiencia_requerida;

ALTER TABLE postulaciones
    DROP COLUMN id_documento_cv,
    DROP COLUMN observacion_empresa,
    DROP COLUMN actualizado_en;

DELETE FROM roles WHERE nombre = 'empresa';
