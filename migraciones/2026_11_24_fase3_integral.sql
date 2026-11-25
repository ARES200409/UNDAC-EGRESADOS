-- ============================================================================
-- NEXO UNDAC - FASE 3: MIGRACION INTEGRAL ADITIVA E IDEMPOTENTE (MySQL 8/9)
-- Fecha: 2026-11-24
-- Conserva el 100% de tablas, registros y triggers existentes.
-- ============================================================================

USE seguimiento_egresados;

-- 1. Nuevo rol institucional: empresa
INSERT IGNORE INTO roles (nombre, descripcion)
VALUES ('empresa', 'Empresa o empleador validado en bolsa laboral');

-- 2. Helper idempotente temporal para agregar columnas sin fallar si ya existen
DROP PROCEDURE IF EXISTS sp_add_col_si_falta;
DELIMITER $$
CREATE PROCEDURE sp_add_col_si_falta(
    IN p_tabla VARCHAR(64),
    IN p_columna VARCHAR(64),
    IN p_definicion VARCHAR(500)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_tabla
          AND COLUMN_NAME = p_columna
    ) THEN
        SET @sql_stmt = CONCAT('ALTER TABLE `', p_tabla, '` ADD COLUMN `', p_columna, '` ', p_definicion);
        PREPARE stmt FROM @sql_stmt;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- 3. Ampliación no destructiva de tablas existentes
CALL sp_add_col_si_falta('usuarios', 'id_empresa', 'INT NULL AFTER id_personal');
CALL sp_add_col_si_falta('usuarios', 'intentos_fallidos', 'INT NOT NULL DEFAULT 0 AFTER estado');
CALL sp_add_col_si_falta('usuarios', 'bloqueado_hasta', 'DATETIME NULL AFTER intentos_fallidos');
CALL sp_add_col_si_falta('usuarios', 'actualizado_en', 'DATETIME NULL AFTER ultimo_cambio_password');

CALL sp_add_col_si_falta('egresados', 'situacion_laboral', "ENUM('empleado','independiente','desempleado','buscando','estudiando','no_especificado') NOT NULL DEFAULT 'no_especificado' AFTER nivel_maximo");
CALL sp_add_col_si_falta('egresados', 'perfil_publico', 'TINYINT(1) NOT NULL DEFAULT 0 AFTER situacion_laboral');
CALL sp_add_col_si_falta('egresados', 'actualizado_en', 'DATETIME NULL AFTER creado_en');

CALL sp_add_col_si_falta('empleos', 'relacion_carrera', 'TINYINT(1) NULL AFTER es_actual');
CALL sp_add_col_si_falta('empleos', 'modalidad', "ENUM('presencial','remoto','hibrido') NULL AFTER relacion_carrera");
CALL sp_add_col_si_falta('empleos', 'rango_remuneracion', 'VARCHAR(80) NULL AFTER modalidad');
CALL sp_add_col_si_falta('empleos', 'es_independiente', 'TINYINT(1) NOT NULL DEFAULT 0 AFTER rango_remuneracion');

CALL sp_add_col_si_falta('empresas', 'motivo_rechazo', 'VARCHAR(300) NULL AFTER estado');
CALL sp_add_col_si_falta('empresas', 'validado_por', 'INT NULL AFTER motivo_rechazo');
CALL sp_add_col_si_falta('empresas', 'fecha_validacion', 'DATETIME NULL AFTER validado_por');

CALL sp_add_col_si_falta('ofertas_laborales', 'carrera_requerida', 'VARCHAR(150) NULL AFTER requisitos');
CALL sp_add_col_si_falta('ofertas_laborales', 'experiencia_requerida', 'VARCHAR(150) NULL AFTER carrera_requerida');

CALL sp_add_col_si_falta('postulaciones', 'id_documento_cv', 'INT NULL AFTER id_oferta');
CALL sp_add_col_si_falta('postulaciones', 'observacion_empresa', 'VARCHAR(500) NULL AFTER mensaje');
CALL sp_add_col_si_falta('postulaciones', 'actualizado_en', 'DATETIME NULL AFTER fecha');

-- Ampliar ENUM de postulaciones.estado preservando valores actuales ('enviada','en_revision','seleccionado','no_seleccionado')
ALTER TABLE postulaciones
    MODIFY COLUMN estado ENUM(
        'enviada','en_revision','preseleccionado','entrevista',
        'seleccionado','no_seleccionado','retirada'
    ) NOT NULL DEFAULT 'enviada';

DROP PROCEDURE IF EXISTS sp_add_col_si_falta;

-- FK de usuarios.id_empresa -> empresas.id_empresa (idempotente)
DROP PROCEDURE IF EXISTS sp_add_fk_usuario_empresa;
DELIMITER $$
CREATE PROCEDURE sp_add_fk_usuario_empresa()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = 'usuarios'
          AND CONSTRAINT_NAME = 'fk_usuario_empresa'
    ) THEN
        ALTER TABLE usuarios
            ADD CONSTRAINT fk_usuario_empresa
            FOREIGN KEY (id_empresa) REFERENCES empresas(id_empresa)
            ON DELETE SET NULL;
    END IF;
END$$
DELIMITER ;
CALL sp_add_fk_usuario_empresa();
DROP PROCEDURE IF EXISTS sp_add_fk_usuario_empresa;

-- 4. Nuevas tablas de la plataforma integral

-- 4.1 Gestión documental privada y certificaciones (Módulo 5)
CREATE TABLE IF NOT EXISTS documentos_egresado (
    id_documento INT NOT NULL AUTO_INCREMENT,
    id_egresado INT NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    categoria ENUM(
        'cv','certificado_estudios','capacitacion','curso','especializacion',
        'idioma','constancia_trabajo','certificado_laboral','diploma',
        'grado_academico','titulo_profesional','reconocimiento','practicas','otro'
    ) NOT NULL DEFAULT 'otro',
    descripcion VARCHAR(500) NULL,
    institucion_emisora VARCHAR(200) NULL,
    fecha_emision DATE NULL,
    fecha_vencimiento DATE NULL,
    nombre_original VARCHAR(255) NOT NULL,
    nombre_interno VARCHAR(120) NOT NULL,
    ruta_almacenamiento VARCHAR(300) NOT NULL,
    extension VARCHAR(15) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    tamano_bytes INT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    es_cv_principal TINYINT(1) NOT NULL DEFAULT 0,
    estado_validacion ENUM('pendiente','en_revision','validado','observado','rechazado') NOT NULL DEFAULT 'pendiente',
    observaciones VARCHAR(500) NULL,
    revisado_por INT NULL,
    fecha_revision DATETIME NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_documento),
    KEY idx_doc_egresado (id_egresado),
    KEY idx_doc_estado (estado_validacion),
    KEY idx_doc_categoria (categoria),
    CONSTRAINT fk_doc_egresado FOREIGN KEY (id_egresado) REFERENCES egresados(id_egresado) ON DELETE CASCADE,
    CONSTRAINT fk_doc_revisor FOREIGN KEY (revisado_por) REFERENCES personal(id_personal) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.2 Historial de validaciones documentales
CREATE TABLE IF NOT EXISTS historial_validacion_documental (
    id_historial INT NOT NULL AUTO_INCREMENT,
    id_documento INT NOT NULL,
    estado_anterior VARCHAR(30) NULL,
    estado_nuevo VARCHAR(30) NOT NULL,
    observacion VARCHAR(500) NULL,
    id_personal INT NULL,
    fecha_cambio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_historial),
    KEY idx_hist_doc (id_documento),
    CONSTRAINT fk_hist_doc FOREIGN KEY (id_documento) REFERENCES documentos_egresado(id_documento) ON DELETE CASCADE,
    CONSTRAINT fk_hist_personal FOREIGN KEY (id_personal) REFERENCES personal(id_personal) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.3 Autorizaciones granulares de privacidad documental hacia empresas/postulaciones
CREATE TABLE IF NOT EXISTS autorizaciones_documentales (
    id_autorizacion INT NOT NULL AUTO_INCREMENT,
    id_documento INT NOT NULL,
    id_egresado INT NOT NULL,
    id_empresa INT NULL,
    id_postulacion INT NULL,
    autorizado TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revocado_en DATETIME NULL,
    PRIMARY KEY (id_autorizacion),
    KEY idx_aut_doc (id_documento),
    KEY idx_aut_empresa (id_empresa),
    KEY idx_aut_postulacion (id_postulacion),
    CONSTRAINT fk_aut_doc FOREIGN KEY (id_documento) REFERENCES documentos_egresado(id_documento) ON DELETE CASCADE,
    CONSTRAINT fk_aut_egresado FOREIGN KEY (id_egresado) REFERENCES egresados(id_egresado) ON DELETE CASCADE,
    CONSTRAINT fk_aut_empresa FOREIGN KEY (id_empresa) REFERENCES empresas(id_empresa) ON DELETE CASCADE,
    CONSTRAINT fk_aut_postulacion FOREIGN KEY (id_postulacion) REFERENCES postulaciones(id_postulacion) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.4 Campañas de seguimiento laboral por cohortes/períodos (Módulo 6)
CREATE TABLE IF NOT EXISTS campanas_seguimiento (
    id_campana INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(200) NOT NULL,
    descripcion VARCHAR(500) NULL,
    periodo_tipo ENUM('al_egresar','6_meses','1_anio','2_anios','3_anios','personalizado') NOT NULL DEFAULT '1_anio',
    id_facultad INT NULL,
    id_programa INT NULL,
    fecha_inicio DATE NULL,
    fecha_fin DATE NULL,
    estado ENUM('borrador','activa','cerrada') NOT NULL DEFAULT 'borrador',
    creado_por INT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_campana),
    KEY idx_camp_estado (estado),
    CONSTRAINT fk_camp_facultad FOREIGN KEY (id_facultad) REFERENCES facultades(id_facultad) ON DELETE SET NULL,
    CONSTRAINT fk_camp_programa FOREIGN KEY (id_programa) REFERENCES programas_estudio(id_programa) ON DELETE SET NULL,
    CONSTRAINT fk_camp_personal FOREIGN KEY (creado_por) REFERENCES personal(id_personal) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.5 Capacitaciones y eventos (Módulo 9)
CREATE TABLE IF NOT EXISTS capacitaciones (
    id_capacitacion INT NOT NULL AUTO_INCREMENT,
    titulo VARCHAR(220) NOT NULL,
    tipo ENUM('curso','taller','seminario','conferencia','congreso','feria_laboral','networking','otro') NOT NULL DEFAULT 'curso',
    descripcion TEXT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NULL,
    horario VARCHAR(120) NULL,
    modalidad ENUM('presencial','virtual','hibrido') NOT NULL DEFAULT 'virtual',
    lugar_o_enlace VARCHAR(300) NULL,
    capacidad_maxima INT NULL,
    estado ENUM('borrador','publicada','finalizada','cancelada') NOT NULL DEFAULT 'publicada',
    creado_por INT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_capacitacion),
    KEY idx_cap_estado (estado),
    KEY idx_cap_fecha (fecha_inicio),
    CONSTRAINT fk_cap_personal FOREIGN KEY (creado_por) REFERENCES personal(id_personal) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.6 Inscripciones a capacitaciones y eventos
CREATE TABLE IF NOT EXISTS inscripciones_capacitacion (
    id_inscripcion INT NOT NULL AUTO_INCREMENT,
    id_capacitacion INT NOT NULL,
    id_egresado INT NOT NULL,
    estado ENUM('inscrito','asistio','no_asistio','cancelado') NOT NULL DEFAULT 'inscrito',
    codigo_constancia VARCHAR(64) NULL,
    fecha_inscripcion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_inscripcion),
    UNIQUE KEY uq_inscripcion_cap_egr (id_capacitacion, id_egresado),
    CONSTRAINT fk_ins_cap FOREIGN KEY (id_capacitacion) REFERENCES capacitaciones(id_capacitacion) ON DELETE CASCADE,
    CONSTRAINT fk_ins_egr FOREIGN KEY (id_egresado) REFERENCES egresados(id_egresado) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.7 Notificaciones internas (Módulo 10)
CREATE TABLE IF NOT EXISTS notificaciones (
    id_notificacion INT NOT NULL AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    tipo VARCHAR(40) NOT NULL DEFAULT 'sistema',
    titulo VARCHAR(180) NOT NULL,
    mensaje VARCHAR(500) NOT NULL,
    enlace VARCHAR(255) NULL,
    leida TINYINT(1) NOT NULL DEFAULT 0,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    leida_en DATETIME NULL,
    PRIMARY KEY (id_notificacion),
    KEY idx_notif_usuario_leida (id_usuario, leida),
    CONSTRAINT fk_notif_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4.8 Auditoría y trazabilidad (Módulo 13)
CREATE TABLE IF NOT EXISTS auditoria (
    id_auditoria BIGINT NOT NULL AUTO_INCREMENT,
    id_usuario INT NULL,
    accion VARCHAR(80) NOT NULL,
    modulo VARCHAR(60) NOT NULL,
    entidad VARCHAR(60) NULL,
    id_registro VARCHAR(60) NULL,
    resultado ENUM('exito','denegado','error') NOT NULL DEFAULT 'exito',
    detalle VARCHAR(500) NULL,
    ip_origen VARCHAR(45) NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_auditoria),
    KEY idx_aud_fecha (creado_en),
    KEY idx_aud_modulo_accion (modulo, accion),
    KEY idx_aud_usuario (id_usuario),
    CONSTRAINT fk_aud_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
