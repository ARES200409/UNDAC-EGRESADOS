# app/models.py
from app.extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Flask-Login necesita esta función para saber cómo cargar
# un usuario desde la base de datos dado su id de sesión
@login_manager.user_loader
def load_user(id_usuario):
    return db.session.get(Usuarios, int(id_usuario))


# ------------------------------------------------------------
# 1. ROLES
# ------------------------------------------------------------
class Roles(db.Model):
    __tablename__ = 'roles'
    id_rol      = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255))

    # N:M con Usuarios a través de usuario_roles
    usuarios = db.relationship('Usuarios', secondary='usuario_roles', backref='roles')


# ------------------------------------------------------------
# 2. PERSONAL
# ------------------------------------------------------------
class Personal(db.Model):
    __tablename__ = 'personal'
    id_personal      = db.Column(db.Integer, primary_key=True)
    nombres          = db.Column(db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    correo           = db.Column(db.String(150))
    telefono         = db.Column(db.String(30))
    estado           = db.Column(db.Enum('activo', 'inactivo'), default='activo')

    usuario      = db.relationship('Usuarios', backref='personal', uselist=False)
    asignaciones = db.relationship('AsignacionesPersonal', backref='personal', lazy=True)

    def nombre_completo(self):
        return f"{self.apellido_paterno} {self.apellido_materno or ''} {self.nombres}".strip()


# ------------------------------------------------------------
# 3. FACULTADES
# ------------------------------------------------------------
class Facultades(db.Model):
    __tablename__ = 'facultades'
    id_facultad = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(200), nullable=False, unique=True)
    codigo      = db.Column(db.String(10), unique=True)
    estado      = db.Column(db.Enum('activo', 'inactivo'), default='activo')

    programas = db.relationship('ProgramasEstudio', backref='facultad', lazy=True)


# ------------------------------------------------------------
# 4. PROGRAMAS DE ESTUDIO
# ------------------------------------------------------------
class ProgramasEstudio(db.Model):
    __tablename__ = 'programas_estudio'
    id_programa = db.Column(db.Integer, primary_key=True)
    id_facultad = db.Column(db.Integer, db.ForeignKey('facultades.id_facultad'), nullable=False)
    nombre      = db.Column(db.String(200), nullable=False)
    codigo      = db.Column(db.String(20), unique=True)
    estado      = db.Column(db.Enum('activo', 'inactivo'), default='activo')

    curriculas = db.relationship('Curriculas', backref='programa', lazy=True)


# ------------------------------------------------------------
# 5. CURRÍCULAS / PLANES DE ESTUDIO
# ------------------------------------------------------------
class Curriculas(db.Model):
    __tablename__ = 'curriculas'
    id_curricula = db.Column(db.Integer, primary_key=True)
    id_programa  = db.Column(db.Integer, db.ForeignKey('programas_estudio.id_programa'), nullable=False)
    nombre       = db.Column(db.String(50), nullable=False)   # '17A4SI', '13A4SI', '26A4SI'
    anio_inicio  = db.Column(db.Integer, nullable=True)       # YEAR: NULL = pendiente de validación oficial
    anio_fin     = db.Column(db.Integer, nullable=True)       # NULL = vigente
    estado       = db.Column(db.Enum('activo', 'inactivo'), default='activo')

    egresados = db.relationship('Egresados', backref='curricula', lazy=True)


# ------------------------------------------------------------
# 6. EGRESADOS
# ------------------------------------------------------------
class Egresados(db.Model):
    __tablename__ = 'egresados'
    id_egresado          = db.Column(db.Integer, primary_key=True)

    # Datos personales
    codigo_universitario = db.Column(db.String(10), nullable=True, unique=True)
    dni                  = db.Column(db.String(15), nullable=False, unique=True)
    apellido_paterno     = db.Column(db.String(80), nullable=False)
    apellido_materno     = db.Column(db.String(80))
    nombres              = db.Column(db.String(100), nullable=False)
    genero               = db.Column(db.String(1))   # 'M' / 'F'
    fecha_nacimiento     = db.Column(db.Date)

    # Contacto
    correo_institucional = db.Column(db.String(150))
    correo_personal      = db.Column(db.String(150))
    telefono             = db.Column(db.String(20))
    domicilio            = db.Column(db.String(255))
    distrito             = db.Column(db.String(100))
    provincia            = db.Column(db.String(100))
    region               = db.Column(db.String(100))
    pais                 = db.Column(db.String(80), nullable=False, default='Perú')

    # Redes sociales
    linkedin             = db.Column(db.String(255))
    facebook             = db.Column(db.String(255))
    tiktok               = db.Column(db.String(100))
    foto                 = db.Column(db.String(500))

    # Relación académica
    id_curricula         = db.Column(db.Integer, db.ForeignKey('curriculas.id_curricula'), nullable=False)
    anio_ingreso         = db.Column(db.Integer)
    periodo              = db.Column(db.String(20))
    anio_egreso          = db.Column(db.Integer)

    # Grados y títulos
    es_bachiller         = db.Column(db.SmallInteger, nullable=False, default=0)
    es_titulado          = db.Column(db.SmallInteger, nullable=False, default=0)
    tiene_maestria       = db.Column(db.SmallInteger, nullable=False, default=0)
    tiene_doctorado      = db.Column(db.SmallInteger, nullable=False, default=0)
    tiene_phd            = db.Column(db.SmallInteger, nullable=False, default=0)
    nivel_maximo         = db.Column(
        db.Enum('egresado', 'bachiller', 'titulado', 'maestria', 'doctorado', 'phd'),
        nullable=False, default='egresado'
    )

    # Perfil profesional
    titulo_cv            = db.Column(db.String(150))
    perfil_profesional   = db.Column(db.Text)
    situacion_laboral    = db.Column(
        db.Enum('empleado', 'independiente', 'desempleado', 'buscando', 'estudiando', 'no_especificado'),
        nullable=False, default='no_especificado'
    )
    perfil_publico       = db.Column(db.SmallInteger, nullable=False, default=0)

    # Control
    creado_en            = db.Column(db.DateTime, nullable=False, default=_utc_now)
    actualizado_en       = db.Column(db.DateTime, nullable=True, onupdate=_utc_now)

    # Relaciones
    usuario              = db.relationship('Usuarios', backref='egresado', uselist=False)
    empleos              = db.relationship('Empleos', backref='egresado', lazy=True)
    trayectoria          = db.relationship('TrayectoriaAcademica', backref='egresado', lazy=True)
    certificados         = db.relationship('Certificados', backref='egresado', lazy=True)
    habilidades          = db.relationship('Habilidades', backref='egresado', lazy=True)
    empresas_sugeridas   = db.relationship('Empresas', backref='sugeridor', lazy=True)

    def nombre_completo(self):
        return f"{self.apellido_paterno} {self.apellido_materno or ''} {self.nombres}".strip()

    def actualizar_nivel_maximo(self):
        """Recalcula nivel_maximo según los flags aprobados.
        Nota: el trigger 'actualizar_nivel_egresado' ya lo hace a nivel de BD
        al insertar en trayectoria_academica; este método sirve para
        recalcular manualmente desde la app si hace falta."""
        if self.tiene_phd:
            self.nivel_maximo = 'phd'
        elif self.tiene_doctorado:
            self.nivel_maximo = 'doctorado'
        elif self.tiene_maestria:
            self.nivel_maximo = 'maestria'
        elif self.es_titulado:
            self.nivel_maximo = 'titulado'
        elif self.es_bachiller:
            self.nivel_maximo = 'bachiller'
        else:
            self.nivel_maximo = 'egresado'


# ------------------------------------------------------------
# 7. USUARIOS
# ------------------------------------------------------------
class Usuarios(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id_usuario      = db.Column(db.Integer, primary_key=True)
    correo          = db.Column(db.String(150), nullable=False, unique=True)
    contrasena_hash = db.Column(db.String(255), nullable=False)

    id_egresado     = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'))
    id_personal     = db.Column(db.Integer, db.ForeignKey('personal.id_personal'))
    id_empresa      = db.Column(db.Integer, db.ForeignKey('empresas.id_empresa'))

    ultimo_acceso   = db.Column(db.DateTime)
    estado          = db.Column(db.Enum('activo', 'inactivo'), default='activo')
    intentos_fallidos = db.Column(db.Integer, nullable=False, default=0)
    bloqueado_hasta   = db.Column(db.DateTime, nullable=True)

    # Recuperación de contraseña
    token_recuperacion     = db.Column(db.String(255), nullable=True)
    token_expiracion       = db.Column(db.DateTime, nullable=True)
    ultimo_cambio_password = db.Column(db.DateTime, nullable=True)
    actualizado_en         = db.Column(db.DateTime, nullable=True, onupdate=_utc_now)

    # Flask-Login usa get_id() — por defecto usa 'id', le decimos cuál es el nuestro
    def get_id(self):
        return str(self.id_usuario)

    def es_admin(self):
        return any(r.nombre == 'administrador' for r in self.roles)

    def es_egresado(self):
        return self.id_egresado is not None

    def es_empresa(self):
        return self.id_empresa is not None

    def tiene_rol(self, nombre_rol):
        return any(r.nombre == nombre_rol for r in self.roles)

    def rol_activo_nombre(self):
        """Nombre del rol con el que inició sesión en esta sesión de navegador."""
        from flask import session
        rid = session.get('rol_activo')
        for r in self.roles:
            if r.id_rol == rid:
                return r.nombre
        return None


# ------------------------------------------------------------
# 8. USUARIO_ROLES (login: qué roles puede usar cada usuario)
# ------------------------------------------------------------
class UsuarioRoles(db.Model):
    __tablename__ = 'usuario_roles'
    id_usuario_rol = db.Column(db.Integer, primary_key=True)
    id_usuario     = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    id_rol         = db.Column(db.Integer, db.ForeignKey('roles.id_rol'), nullable=False)

    __table_args__ = (db.UniqueConstraint('id_usuario', 'id_rol'),)


# ------------------------------------------------------------
# 9. ASIGNACIONES DE PERSONAL (rol + ámbito de trabajo)
# ------------------------------------------------------------
class AsignacionesPersonal(db.Model):
    __tablename__ = 'asignaciones_personal'
    id_asignacion = db.Column(db.Integer, primary_key=True)
    id_personal   = db.Column(db.Integer, db.ForeignKey('personal.id_personal', ondelete='CASCADE'), nullable=False)
    id_rol        = db.Column(db.Integer, db.ForeignKey('roles.id_rol'), nullable=False)
    id_programa   = db.Column(db.Integer, db.ForeignKey('programas_estudio.id_programa'), nullable=True)
    id_facultad   = db.Column(db.Integer, db.ForeignKey('facultades.id_facultad'), nullable=True)
    fecha_inicio  = db.Column(db.Date, nullable=False)
    fecha_fin     = db.Column(db.Date, nullable=True)
    estado        = db.Column(db.Enum('activo', 'inactivo'), default='activo')

    rol       = db.relationship('Roles')
    programa  = db.relationship('ProgramasEstudio')
    facultad  = db.relationship('Facultades')


# ------------------------------------------------------------
# 10. SECTORES ECONÓMICOS
# ------------------------------------------------------------
class Sectores(db.Model):
    __tablename__ = 'sectores'
    id_sector   = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False, unique=True)

    empresas = db.relationship('Empresas', backref='sector', lazy=True)


# ------------------------------------------------------------
# 11. EMPRESAS
# ------------------------------------------------------------
class Empresas(db.Model):
    __tablename__ = 'empresas'
    id_empresa       = db.Column(db.Integer, primary_key=True)
    ruc              = db.Column(db.String(11), unique=True)
    razon_social     = db.Column(db.String(200), nullable=False)
    nombre_comercial = db.Column(db.String(200))
    id_sector        = db.Column(db.Integer, db.ForeignKey('sectores.id_sector'), nullable=True)
    tipo_empresa     = db.Column(db.String(80))
    direccion        = db.Column(db.String(255))
    distrito         = db.Column(db.String(100))
    provincia        = db.Column(db.String(100))
    region           = db.Column(db.String(100))
    pais             = db.Column(db.String(80), nullable=False, default='Perú')
    telefono         = db.Column(db.String(20))
    sitio_web        = db.Column(db.String(255))
    estado           = db.Column(db.Enum('activa', 'pendiente'), nullable=False, default='activa')
    motivo_rechazo   = db.Column(db.String(300))
    validado_por     = db.Column(db.Integer)
    fecha_validacion = db.Column(db.DateTime)
    sugerido_por     = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'))

    empleos = db.relationship('Empleos', backref='empresa', lazy=True)

    def nombre_display(self):
        """Devuelve nombre comercial si existe, si no la razón social."""
        return self.nombre_comercial or self.razon_social


# ------------------------------------------------------------
# 12. EMPLEOS
# ------------------------------------------------------------
class Empleos(db.Model):
    __tablename__ = 'empleos'
    id_empleo     = db.Column(db.Integer, primary_key=True)
    id_egresado   = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    id_empresa    = db.Column(db.Integer, db.ForeignKey('empresas.id_empresa'), nullable=False)
    cargo         = db.Column(db.String(150), nullable=False)
    tipo_contrato = db.Column(db.String(80))
    funciones     = db.Column(db.Text)
    fecha_inicio       = db.Column(db.Date, nullable=False)
    fecha_fin          = db.Column(db.Date)
    es_actual          = db.Column(db.SmallInteger, nullable=False, default=0)
    relacion_carrera   = db.Column(db.SmallInteger)
    modalidad          = db.Column(db.Enum('presencial', 'remoto', 'hibrido'))
    rango_remuneracion = db.Column(db.String(80))
    es_independiente   = db.Column(db.SmallInteger, nullable=False, default=0)


# ------------------------------------------------------------
# 13. TRAYECTORIA ACADÉMICA
# ------------------------------------------------------------
class TrayectoriaAcademica(db.Model):
    __tablename__ = 'trayectoria_academica'
    id_trayectoria  = db.Column(db.Integer, primary_key=True)
    id_egresado     = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    tipo            = db.Column(db.Enum('bachiller', 'titulado', 'maestria', 'doctorado', 'phd'), nullable=False)
    grado_titulo    = db.Column(db.String(300), nullable=False)
    institucion     = db.Column(db.String(200), nullable=False, default='Universidad Nacional Daniel Alcides Carrión')
    fecha_obtencion = db.Column(db.Date, nullable=False)
    fuente          = db.Column(db.String(50), nullable=False, default='SUNEDU')


# ------------------------------------------------------------
# 14. CERTIFICADOS
# ------------------------------------------------------------
class Certificados(db.Model):
    __tablename__ = 'certificados'
    id_certificado      = db.Column(db.Integer, primary_key=True)
    id_egresado         = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    nombre              = db.Column(db.String(255), nullable=False)
    institucion_emisora = db.Column(db.String(200), nullable=False)
    tipo                = db.Column(db.Enum('externo', 'interno'), nullable=False, default='externo')
    categoria           = db.Column(db.Enum('curso', 'capacitacion', 'diplomado', 'idioma', 'otro'), nullable=False, default='curso')
    nivel_idioma        = db.Column(db.Enum('basico', 'intermedio', 'avanzado'))
    fecha_emision       = db.Column(db.Date)
    url_credencial      = db.Column(db.String(500))
    ruta_archivo        = db.Column(db.String(500))

    def nombre_mostrar(self):
        """Nombre a mostrar en listados: agrega el nivel si es un idioma."""
        if self.categoria == 'idioma' and self.nivel_idioma:
            return f"{self.nombre} — {self.nivel_idioma.capitalize()}"
        return self.nombre


# ------------------------------------------------------------
# 15. OFERTAS LABORALES
# ------------------------------------------------------------
class OfertasLaborales(db.Model):
    __tablename__ = 'ofertas_laborales'
    id_oferta         = db.Column(db.Integer, primary_key=True)
    id_creado_por     = db.Column(db.Integer, db.ForeignKey('personal.id_personal'))
    id_empresa        = db.Column(db.Integer, db.ForeignKey('empresas.id_empresa'))
    titulo            = db.Column(db.String(255), nullable=False)
    empresa           = db.Column(db.String(200))  # respaldo si no está en el directorio
    telefono          = db.Column(db.String(20))
    descripcion           = db.Column(db.Text)
    requisitos            = db.Column(db.Text)
    carrera_requerida     = db.Column(db.String(150))
    experiencia_requerida = db.Column(db.String(150))
    modalidad         = db.Column(db.String(80))
    tipo_oferta       = db.Column(db.String(80))
    jornada           = db.Column(db.String(80))
    remuneracion      = db.Column(db.String(100))
    funciones         = db.Column(db.Text)
    ubicacion         = db.Column(db.String(150))
    ruta_imagen       = db.Column(db.String(500))
    url_original      = db.Column(db.Text)
    fuente            = db.Column(db.Enum('manual', 'automatico'), nullable=False, default='manual')
    fecha_publicacion = db.Column(db.Date, nullable=False, default=_utc_now)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    activa            = db.Column(db.SmallInteger, nullable=False, default=1)

    empresa_rel = db.relationship('Empresas', backref='ofertas')

    def nombre_empresa(self):
        """Devuelve el nombre a mostrar: del directorio si está enlazada, si no el texto libre, si no 'Desconocida'."""
        if self.empresa_rel:
            return self.empresa_rel.nombre_display()
        return self.empresa or 'Desconocida'


# ------------------------------------------------------------
# 16. ENCUESTAS
# ------------------------------------------------------------
class Encuesta(db.Model):
    __tablename__ = 'encuestas'
    id_encuesta  = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(200), nullable=False)
    descripcion  = db.Column(db.Text)
    anio         = db.Column(db.Integer, nullable=False)  # YEAR
    estado       = db.Column(db.Enum('borrador', 'publicada', 'cerrada'), nullable=False, default='borrador')
    fecha_inicio = db.Column(db.Date)
    fecha_fin    = db.Column(db.Date)

    preguntas = db.relationship('Preguntas', backref='encuesta', cascade='all, delete-orphan', lazy=True)


class Preguntas(db.Model):
    __tablename__ = 'preguntas'
    id_pregunta = db.Column(db.Integer, primary_key=True)
    id_encuesta = db.Column(db.Integer, db.ForeignKey('encuestas.id_encuesta', ondelete='CASCADE'), nullable=False)
    texto       = db.Column(db.Text, nullable=False)
    tipo        = db.Column(db.Enum('texto', 'numero', 'si_no', 'opcion_unica', 'opcion_multiple'), nullable=False)
    orden       = db.Column(db.Integer, nullable=False)
    obligatoria = db.Column(db.SmallInteger, nullable=False, default=0)

    opciones = db.relationship('Opciones', backref='pregunta', cascade='all, delete-orphan', lazy=True)


class Opciones(db.Model):
    __tablename__ = 'opciones'
    id_opcion   = db.Column(db.Integer, primary_key=True)
    id_pregunta = db.Column(db.Integer, db.ForeignKey('preguntas.id_pregunta', ondelete='CASCADE'), nullable=False)
    texto       = db.Column(db.String(255), nullable=False)
    orden       = db.Column(db.Integer, nullable=False)


class Respuestas(db.Model):
    __tablename__ = 'respuestas'
    id_respuesta        = db.Column(db.Integer, primary_key=True)
    id_encuesta          = db.Column(db.Integer, db.ForeignKey('encuestas.id_encuesta'), nullable=False)
    id_egresado          = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=True)
    id_pregunta          = db.Column(db.Integer, db.ForeignKey('preguntas.id_pregunta'), nullable=False)
    id_opcion            = db.Column(db.Integer, db.ForeignKey('opciones.id_opcion'), nullable=True)  # opcion_unica
    respuesta_texto      = db.Column(db.Text, nullable=True)                                    # texto
    respuesta_numero     = db.Column(db.Numeric(10, 2), nullable=True)                          # numero
    respuesta_booleana   = db.Column(db.SmallInteger, nullable=True)                            # si_no
    fecha_respuesta      = db.Column(db.DateTime, nullable=False, default=_utc_now)

    encuesta  = db.relationship('Encuesta', backref='respuestas')
    egresado  = db.relationship('Egresados', backref='respuestas')
    pregunta  = db.relationship('Preguntas', backref='respuestas')
    opcion    = db.relationship('Opciones', backref='respuestas')


# ------------------------------------------------------------
# 17. HABILIDADES Y APTITUDES
# ------------------------------------------------------------
class Habilidades(db.Model):
    __tablename__ = 'habilidades'
    id_habilidad = db.Column(db.Integer, primary_key=True)
    id_egresado  = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    nombre       = db.Column(db.String(100), nullable=False)
    tipo         = db.Column(db.Enum('habilidad', 'interes'), nullable=False, default='habilidad')

# V8: Seguimiento de oportunidades. Ejecutar primero SQL de migración V8.
class OfertasGuardadas(db.Model):
    __tablename__ = 'ofertas_guardadas'
    id_guardado = db.Column(db.Integer, primary_key=True)
    id_egresado = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    id_oferta = db.Column(db.Integer, db.ForeignKey('ofertas_laborales.id_oferta'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=_utc_now)
    oferta = db.relationship('OfertasLaborales')
    __table_args__ = (db.UniqueConstraint('id_egresado', 'id_oferta', name='uq_guardado_egresado_oferta'),)


class Postulaciones(db.Model):
    __tablename__ = 'postulaciones'
    id_postulacion      = db.Column(db.Integer, primary_key=True)
    id_egresado         = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    id_oferta           = db.Column(db.Integer, db.ForeignKey('ofertas_laborales.id_oferta'), nullable=False)
    id_documento_cv     = db.Column(db.Integer, nullable=True)
    mensaje             = db.Column(db.Text)
    observacion_empresa = db.Column(db.String(500))
    estado              = db.Column(
        db.Enum('enviada', 'en_revision', 'preseleccionado', 'entrevista', 'seleccionado', 'no_seleccionado', 'retirada'),
        nullable=False, default='enviada'
    )
    fecha               = db.Column(db.DateTime, nullable=False, default=_utc_now)
    actualizado_en      = db.Column(db.DateTime, nullable=True, onupdate=_utc_now)
    oferta              = db.relationship('OfertasLaborales')
    egresado            = db.relationship('Egresados')
    __table_args__ = (db.UniqueConstraint('id_egresado', 'id_oferta', name='uq_postulacion_egresado_oferta'),)


# V9: seguimiento autodeclarado de una visita o postulación externa.
class SeguimientoExterno(db.Model):
    __tablename__ = 'seguimiento_externo'
    id_seguimiento = db.Column(db.Integer, primary_key=True)
    id_egresado = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado'), nullable=False)
    id_oferta = db.Column(db.Integer, db.ForeignKey('ofertas_laborales.id_oferta'), nullable=False)
    estado = db.Column(db.Enum('visitado', 'postulado', 'entrevista', 'contratacion_reportada', 'no_seleccionado', 'desistio'), nullable=False, default='visitado')
    visitas = db.Column(db.Integer, nullable=False, default=0)
    observacion = db.Column(db.String(500))
    fecha_postulacion = db.Column(db.Date)
    fecha_contratacion = db.Column(db.Date)
    creado_en = db.Column(db.DateTime, nullable=False, default=_utc_now)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)
    oferta = db.relationship('OfertasLaborales')
    __table_args__ = (db.UniqueConstraint('id_egresado','id_oferta',name='uq_seg_externo_persona_oferta'),)


# ------------------------------------------------------------
# 18. GESTIÓN DOCUMENTAL PRIVADA Y CERTIFICACIONES (FASE 3)
# ------------------------------------------------------------
class DocumentosEgresado(db.Model):
    __tablename__ = 'documentos_egresado'
    id_documento        = db.Column(db.Integer, primary_key=True)
    id_egresado         = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado', ondelete='CASCADE'), nullable=False)
    nombre              = db.Column(db.String(200), nullable=False)
    categoria           = db.Column(
        db.Enum(
            'cv', 'certificado_estudios', 'capacitacion', 'curso', 'especializacion',
            'idioma', 'constancia_trabajo', 'certificado_laboral', 'diploma',
            'grado_academico', 'titulo_profesional', 'reconocimiento', 'practicas', 'otro'
        ),
        nullable=False, default='otro'
    )
    descripcion         = db.Column(db.String(500))
    institucion_emisora = db.Column(db.String(200))
    fecha_emision       = db.Column(db.Date)
    fecha_vencimiento   = db.Column(db.Date)
    nombre_original     = db.Column(db.String(255), nullable=False)
    nombre_interno      = db.Column(db.String(120), nullable=False)
    ruta_almacenamiento = db.Column(db.String(300), nullable=False)
    extension           = db.Column(db.String(15), nullable=False)
    mime_type           = db.Column(db.String(100), nullable=False)
    tamano_bytes        = db.Column(db.Integer, nullable=False)
    sha256              = db.Column(db.String(64), nullable=False)
    es_cv_principal     = db.Column(db.SmallInteger, nullable=False, default=0)
    estado_validacion   = db.Column(
        db.Enum('pendiente', 'en_revision', 'validado', 'observado', 'rechazado'),
        nullable=False, default='pendiente'
    )
    observaciones       = db.Column(db.String(500))
    revisado_por        = db.Column(db.Integer, db.ForeignKey('personal.id_personal', ondelete='SET NULL'))
    fecha_revision      = db.Column(db.DateTime)
    creado_en           = db.Column(db.DateTime, nullable=False, default=_utc_now)
    actualizado_en      = db.Column(db.DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)

    egresado  = db.relationship('Egresados', backref='documentos_digitales')
    revisor   = db.relationship('Personal')
    historial = db.relationship('HistorialValidacionDocumental', backref='documento', cascade='all, delete-orphan', lazy=True)


class HistorialValidacionDocumental(db.Model):
    __tablename__ = 'historial_validacion_documental'
    id_historial    = db.Column(db.Integer, primary_key=True)
    id_documento    = db.Column(db.Integer, db.ForeignKey('documentos_egresado.id_documento', ondelete='CASCADE'), nullable=False)
    estado_anterior = db.Column(db.String(30))
    estado_nuevo    = db.Column(db.String(30), nullable=False)
    observacion     = db.Column(db.String(500))
    id_personal     = db.Column(db.Integer, db.ForeignKey('personal.id_personal', ondelete='SET NULL'))
    fecha_cambio    = db.Column(db.DateTime, nullable=False, default=_utc_now)

    revisor = db.relationship('Personal')


class AutorizacionesDocumentales(db.Model):
    __tablename__ = 'autorizaciones_documentales'
    id_autorizacion = db.Column(db.Integer, primary_key=True)
    id_documento    = db.Column(db.Integer, db.ForeignKey('documentos_egresado.id_documento', ondelete='CASCADE'), nullable=False)
    id_egresado     = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado', ondelete='CASCADE'), nullable=False)
    id_empresa      = db.Column(db.Integer, db.ForeignKey('empresas.id_empresa', ondelete='CASCADE'))
    id_postulacion  = db.Column(db.Integer, db.ForeignKey('postulaciones.id_postulacion', ondelete='CASCADE'))
    autorizado      = db.Column(db.SmallInteger, nullable=False, default=1)
    creado_en       = db.Column(db.DateTime, nullable=False, default=_utc_now)
    revocado_en     = db.Column(db.DateTime)

    documento   = db.relationship('DocumentosEgresado')
    empresa     = db.relationship('Empresas')
    postulacion = db.relationship('Postulaciones')


# ------------------------------------------------------------
# 19. CAMPAÑAS, CAPACITACIONES, NOTIFICACIONES Y AUDITORÍA
# ------------------------------------------------------------
class CampanasSeguimiento(db.Model):
    __tablename__ = 'campanas_seguimiento'
    id_campana   = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(200), nullable=False)
    descripcion  = db.Column(db.String(500))
    periodo_tipo = db.Column(
        db.Enum('al_egresar', '6_meses', '1_anio', '2_anios', '3_anios', 'personalizado'),
        nullable=False, default='1_anio'
    )
    id_facultad  = db.Column(db.Integer, db.ForeignKey('facultades.id_facultad', ondelete='SET NULL'))
    id_programa  = db.Column(db.Integer, db.ForeignKey('programas_estudio.id_programa', ondelete='SET NULL'))
    fecha_inicio = db.Column(db.Date)
    fecha_fin    = db.Column(db.Date)
    estado       = db.Column(db.Enum('borrador', 'activa', 'cerrada'), nullable=False, default='borrador')
    creado_por   = db.Column(db.Integer, db.ForeignKey('personal.id_personal', ondelete='SET NULL'))
    creado_en    = db.Column(db.DateTime, nullable=False, default=_utc_now)


class Capacitaciones(db.Model):
    __tablename__ = 'capacitaciones'
    id_capacitacion  = db.Column(db.Integer, primary_key=True)
    titulo           = db.Column(db.String(220), nullable=False)
    tipo             = db.Column(
        db.Enum('curso', 'taller', 'seminario', 'conferencia', 'congreso', 'feria_laboral', 'networking', 'otro'),
        nullable=False, default='curso'
    )
    descripcion      = db.Column(db.Text)
    fecha_inicio     = db.Column(db.Date, nullable=False)
    fecha_fin        = db.Column(db.Date)
    horario          = db.Column(db.String(120))
    modalidad        = db.Column(db.Enum('presencial', 'virtual', 'hibrido'), nullable=False, default='virtual')
    lugar_o_enlace   = db.Column(db.String(300))
    capacidad_maxima = db.Column(db.Integer)
    estado           = db.Column(db.Enum('borrador', 'publicada', 'finalizada', 'cancelada'), nullable=False, default='publicada')
    creado_por       = db.Column(db.Integer, db.ForeignKey('personal.id_personal', ondelete='SET NULL'))
    creado_en        = db.Column(db.DateTime, nullable=False, default=_utc_now)

    inscripciones = db.relationship('InscripcionesCapacitacion', backref='capacitacion', cascade='all, delete-orphan', lazy=True)


class InscripcionesCapacitacion(db.Model):
    __tablename__ = 'inscripciones_capacitacion'
    id_inscripcion    = db.Column(db.Integer, primary_key=True)
    id_capacitacion   = db.Column(db.Integer, db.ForeignKey('capacitaciones.id_capacitacion', ondelete='CASCADE'), nullable=False)
    id_egresado       = db.Column(db.Integer, db.ForeignKey('egresados.id_egresado', ondelete='CASCADE'), nullable=False)
    estado            = db.Column(db.Enum('inscrito', 'asistio', 'no_asistio', 'cancelado'), nullable=False, default='inscrito')
    codigo_constancia = db.Column(db.String(64))
    fecha_inscripcion = db.Column(db.DateTime, nullable=False, default=_utc_now)

    egresado = db.relationship('Egresados')
    __table_args__ = (db.UniqueConstraint('id_capacitacion', 'id_egresado', name='uq_inscripcion_cap_egr'),)


class Notificaciones(db.Model):
    __tablename__ = 'notificaciones'
    id_notificacion = db.Column(db.Integer, primary_key=True)
    id_usuario      = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    tipo            = db.Column(db.String(40), nullable=False, default='sistema')
    titulo          = db.Column(db.String(180), nullable=False)
    mensaje         = db.Column(db.String(500), nullable=False)
    enlace          = db.Column(db.String(255))
    leida           = db.Column(db.SmallInteger, nullable=False, default=0)
    creado_en       = db.Column(db.DateTime, nullable=False, default=_utc_now)
    leida_en        = db.Column(db.DateTime)


class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    id_auditoria = db.Column(db.Integer, primary_key=True)
    id_usuario   = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='SET NULL'))
    accion       = db.Column(db.String(80), nullable=False)
    modulo       = db.Column(db.String(60), nullable=False)
    entidad      = db.Column(db.String(60))
    id_registro  = db.Column(db.String(60))
    resultado    = db.Column(db.Enum('exito', 'denegado', 'error'), nullable=False, default='exito')
    detalle      = db.Column(db.String(500))
    ip_origen    = db.Column(db.String(45))
    creado_en    = db.Column(db.DateTime, nullable=False, default=_utc_now)


# ------------------------------------------------------------
# HISTORIAL DE SINCRONIZACIÓN ACADÉMICA (módulo DNI)
# ------------------------------------------------------------
class HistorialSyncAcademico(db.Model):
    """Registro inmutable de cada cambio aplicado al perfil de un egresado.

    Permite auditar qué fuente externa modificó qué campo y cuándo,
    conservando los valores anterior y nuevo para su comparación.
    """
    __tablename__ = 'historial_sync_academico'
    id_sync       = db.Column(db.Integer, primary_key=True)
    id_egresado   = db.Column(
        db.Integer,
        db.ForeignKey('egresados.id_egresado', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    fuente        = db.Column(db.String(30), nullable=False)   # reniec | sunedu | undac_api | manual
    campo         = db.Column(db.String(60), nullable=False)
    valor_anterior = db.Column(db.Text)
    valor_nuevo   = db.Column(db.Text)
    operador      = db.Column(
        db.Enum('sistema', 'egresado', 'admin'),
        nullable=False,
        default='sistema',
    )
    creado_en     = db.Column(db.DateTime, nullable=False, default=_utc_now)

    egresado = db.relationship('Egresados', backref=db.backref('historial_sync', lazy=True))
